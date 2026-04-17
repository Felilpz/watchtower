import logging
import subprocess
import platform
import re
import time
from config import GATEWAYS, PING_INTERVAL_SECONDS, PING_TIMEOUT_SECONDS, PING_COUNT
from modules.telegram_alert import alerta_gateway_caiu, alerta_gateway_voltou

logger = logging.getLogger(__name__)

_estado: dict[str, bool | None] = {nome: None for nome in GATEWAYS}


def _ping(host: str) -> tuple[bool, float | None]:
    sistema = platform.system().lower()

    if sistema == "windows":
        cmd = ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT_SECONDS * 1000), host]
    else:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT_SECONDS), host]

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=PING_TIMEOUT_SECONDS * PING_COUNT + 5,
        )
        saida = resultado.stdout.decode(errors="ignore")

        if resultado.returncode != 0:
            return False, None

        return True, _extrair_latencia(saida, sistema)

    except subprocess.TimeoutExpired:
        return False, None
    except Exception as e:
        logger.error(f"erro ao pingar {host}: {e}")
        return False, None


def _extrair_latencia(saida: str, sistema: str) -> float | None:
    try:
        if sistema == "windows":
            match = re.search(r"[Mm][eé]dia\s*=\s*(\d+)", saida)
        else:
            match = re.search(r"[\d.]+/([\d.]+)/[\d.]+/[\d.]+ ms", saida)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def ping_host(host: str) -> tuple[bool, float | None]:
    return _ping(host)


def status_gateways() -> dict:
    resultado = {}
    for nome, alvo in GATEWAYS.items():
        online, latencia = _ping(alvo)
        resultado[nome] = {"alvo": alvo, "online": online, "latencia": latencia}
    return resultado


def _verificar_gateways():
    for nome, alvo in GATEWAYS.items():
        online, latencia = _ping(alvo)
        anterior = _estado[nome]

        if anterior is None:
            _estado[nome] = online
            logger.info(f"[{nome}] estado inicial: {'online' if online else 'offline'}")
            continue

        if anterior is True and not online:
            logger.warning(f"[{nome}] caiu")
            alerta_gateway_caiu(nome, alvo)
            _estado[nome] = False

        elif anterior is False and online:
            logger.info(f"[{nome}] voltou")
            alerta_gateway_voltou(nome, alvo, latencia)
            _estado[nome] = True


def iniciar_monitoramento_wan():
    logger.info(f"wan monitor iniciado | gateways: {list(GATEWAYS.keys())} | intervalo: {PING_INTERVAL_SECONDS}s")
    while True:
        try:
            _verificar_gateways()
        except Exception as e:
            logger.error(f"erro no loop wan: {e}")
        time.sleep(PING_INTERVAL_SECONDS)