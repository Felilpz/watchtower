import time
import logging
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

LOG_PATH = "/var/log/pfsense/all.log"

BRUTE_LIMITE    = 5
BRUTE_JANELA    = timedelta(minutes=3)

# { ip: [datetime, datetime, ...] }
_falhas: dict[str, list] = defaultdict(list)


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _send(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"erro ao enviar alerta pfsense: {e}")


def _ip_interno(ip: str) -> bool:
    return ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")


def _registrar_falha(usuario: str, origem: str):
    agora = datetime.now()

    if not _ip_interno(origem):
        logger.warning(f"tentativa externa: {origem} user={usuario}")
        _send(
            f"🚨 <b>TENTATIVA EXTERNA — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"⚠️ IP fora da rede local\n"
            f"⏱ {_now()}"
        )
        return

    # limpa tentativas fora da janela
    _falhas[origem] = [t for t in _falhas[origem] if agora - t < BRUTE_JANELA]
    _falhas[origem].append(agora)

    total = len(_falhas[origem])
    logger.info(f"falha de login: {origem} user={usuario} ({total}/{BRUTE_LIMITE} na janela)")

    if total >= BRUTE_LIMITE:
        _send(
            f"🔴 <b>BRUTE FORCE DETECTADO — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário alvo:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"🔁 <b>Tentativas:</b> {total} em {BRUTE_JANELA.seconds // 60} minutos\n"
            f"⏱ {_now()}"
        )
        _falhas[origem].clear()


def _processar_linha(linha: str):
    if "php-fpm" not in linha or "/index.php" not in linha:
        return

    try:
        partes  = linha.split("/index.php:")[-1].strip()
        usuario = partes.split("'")[1] if "'" in partes else "desconhecido"
        origem  = partes.split("from:")[-1].strip().split()[0] if "from:" in partes else "?"
    except Exception:
        usuario, origem = "desconhecido", "?"

    if "Successful login" in linha:
        logger.info(f"login bem-sucedido: {origem} user={usuario}")
        _send(
            f"🔐 <b>LOGIN — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"✅ <b>Status:</b> Autenticado\n"
            f"⏱ {_now()}"
        )

    elif "logged out" in linha.lower():
        logger.info(f"logout: {origem} user={usuario}")
        _send(
            f"🔓 <b>LOGOUT — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"⏱ {_now()}"
        )

    elif "Failed login" in linha:
        _registrar_falha(usuario, origem)


def iniciar_monitor_pfsense():
    logger.info(f"monitor pfsense iniciado | arquivo: {LOG_PATH}")

    try:
        f = open(LOG_PATH, "r", encoding="utf-8", errors="ignore")
        f.seek(0, 2)
    except FileNotFoundError:
        logger.error(f"arquivo não encontrado: {LOG_PATH}")
        return

    while True:
        try:
            linha = f.readline()
            if linha:
                _processar_linha(linha)
            else:
                time.sleep(1)
        except Exception as e:
            logger.error(f"erro no monitor pfsense: {e}")
            time.sleep(5)