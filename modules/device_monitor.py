import time
import logging
import subprocess
import platform
import re
import json
import requests
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, STATIC_JSON_PATH

logger = logging.getLogger(__name__)

DEVICE_PING_INTERVAL = 60
PING_TIMEOUT         = 2
PING_COUNT           = 2

# { "SWITCH 01": True/False/None }
_estado: dict[str, bool | None] = {}


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
        logger.error(f"erro ao enviar alerta device: {e}")


def _ping(host: str) -> bool:
    sistema = platform.system().lower()
    if sistema == "windows":
        cmd = ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT * 1000), host]
    else:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), host]

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=PING_TIMEOUT * PING_COUNT + 3,
        )
        return resultado.returncode == 0
    except Exception:
        return False


def _carregar_devices() -> dict:
    try:
        with open(STATIC_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"erro ao carregar static.json: {e}")
        return {}


def _verificar_devices():
    devices = _carregar_devices()
    if not devices:
        return

    for nome, ip in devices.items():
        online = _ping(ip)
        anterior = _estado.get(nome)

        if anterior is None:
            _estado[nome] = online
            logger.info(f"[device] {nome} ({ip}) estado inicial: {'online' if online else 'offline'}")
            continue

        if anterior is True and not online:
            logger.warning(f"[device] {nome} ({ip}) caiu")
            _send(
                f"🔴 <b>DISPOSITIVO OFFLINE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🖥 <b>Nome:</b> {nome}\n"
                f"🎯 <b>IP:</b> <code>{ip}</code>\n"
                f"⏱ <b>Detectado:</b> {_now()}"
            )
            _estado[nome] = False

        elif anterior is False and online:
            logger.info(f"[device] {nome} ({ip}) voltou")
            _send(
                f"🟢 <b>DISPOSITIVO ONLINE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🖥 <b>Nome:</b> {nome}\n"
                f"🎯 <b>IP:</b> <code>{ip}</code>\n"
                f"⏱ <b>Restaurado:</b> {_now()}"
            )
            _estado[nome] = True


def iniciar_monitor_devices():
    devices = _carregar_devices()
    logger.info(f"monitor devices iniciado | {len(devices)} dispositivos | intervalo: {DEVICE_PING_INTERVAL}s")

    while True:
        try:
            _verificar_devices()
        except Exception as e:
            logger.error(f"erro no loop device monitor: {e}")
        time.sleep(DEVICE_PING_INTERVAL)