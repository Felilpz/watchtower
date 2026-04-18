import time
import logging
import requests
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

LOG_PATH = "/var/log/pfsense/all.log"


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


def _processar_linha(linha: str):
    if "php-fpm" not in linha or "/index.php" not in linha:
        return

    # extrai usuario e ip da linha
    # formato: php-fpm[x]: /index.php: <mensagem> for user 'X' from: Y
    try:
        partes = linha.split("/index.php:")[-1].strip()
        usuario = partes.split("'")[1] if "'" in partes else "desconhecido"
        origem = partes.split("from:")[-1].strip().split()[0] if "from:" in partes else "?"
    except Exception:
        usuario, origem = "desconhecido", "?"

    if "Successful login" in linha:
        _send(
            f"🔐 <b>LOGIN — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"✅ <b>Status:</b> Autenticado\n"
            f"⏱ {_now()}"
        )
    elif "logged out" in linha.lower():
        _send(
            f"🔓 <b>LOGOUT — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"⏱ {_now()}"
        )
    elif "Failed login" in linha or "invalid" in linha.lower():
        _send(
            f"🚨 <b>FALHA DE LOGIN — webConfigurator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Usuário:</b> <code>{usuario}</code>\n"
            f"🌐 <b>IP:</b> <code>{origem}</code>\n"
            f"❌ <b>Status:</b> Credencial inválida\n"
            f"⏱ {_now()}"
        )


def iniciar_monitor_pfsense():
    logger.info(f"monitor pfsense iniciado | arquivo: {LOG_PATH}")

    try:
        f = open(LOG_PATH, "r", encoding="utf-8", errors="ignore")
        f.seek(0, 2)  # vai para o final do arquivo
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