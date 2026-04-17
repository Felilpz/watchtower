import logging
import requests
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _send(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"falha ao enviar mensagem: {e}")
        return False


def alerta_gateway_caiu(nome: str, alvo: str) -> bool:
    texto = (
        f"🔴 <b>GATEWAY CAIU</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Link:</b> <code>{nome}</code>\n"
        f"🎯 <b>Alvo:</b> <code>{alvo}</code>\n"
        f"📶 <b>Status:</b> OFFLINE\n"
        f"⏱ <b>Detectado:</b> {_now()}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Verifique o link imediatamente!"
    )
    return _send(texto)


def alerta_gateway_voltou(nome: str, alvo: str, latencia_ms: float | None = None) -> bool:
    lat_str = f"{latencia_ms:.1f} ms" if latencia_ms is not None else "—"
    texto = (
        f"🟢 <b>GATEWAY RESTAURADO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Link:</b> <code>{nome}</code>\n"
        f"🎯 <b>Alvo:</b> <code>{alvo}</code>\n"
        f"📶 <b>Status:</b> ONLINE\n"
        f"📊 <b>Latência:</b> {lat_str}\n"
        f"⏱ <b>Restaurado:</b> {_now()}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    return _send(texto)