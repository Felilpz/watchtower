import logging
import threading
import requests
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from modules.wan_monitor import iniciar_monitoramento_wan
from modules.pfsense_monitor import iniciar_monitor_pfsense
from modules.device_monitor import iniciar_monitor_devices
from modules.system_monitor import iniciar_monitor_sistema
from modules.bot_commands import (
    cmd_start, cmd_wan, cmd_ping, cmd_devices,
    cmd_logins, cmd_status, cmd_uptime,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("watchtower")


def _enviar_boot():
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto = (
        "🟢 <b>WatchTower iniciado</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "📡 <b>WAN</b>\n"
        "  /wan — status dos links\n\n"
        "🖥 <b>Dispositivos</b>\n"
        "  /devices — listar todos\n"
        "  /ping &lt;nome&gt; — pingar dispositivo\n\n"
        "📊 <b>Sistema</b>\n"
        "  /status — CPU, RAM, disco e temperatura\n"
        "  /uptime — tempo online das máquinas\n\n"
        "🔐 <b>Segurança</b>\n"
        "  /logins — últimos acessos ao pfSense\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ {now}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"erro ao enviar mensagem de boot: {e}")


def main():
    logger.info("watchtower iniciando...")

    threads = [
        ("wan-monitor",     iniciar_monitoramento_wan),
        ("pfsense-monitor", iniciar_monitor_pfsense),
        ("device-monitor",  iniciar_monitor_devices),
        ("system-monitor",  iniciar_monitor_sistema),
    ]

    for nome, alvo in threads:
        threading.Thread(target=alvo, name=nome, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("wan",     cmd_wan))
    app.add_handler(CommandHandler("ping",    cmd_ping))
    app.add_handler(CommandHandler("devices", cmd_devices))
    app.add_handler(CommandHandler("logins",  cmd_logins))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("uptime",  cmd_uptime))

    _enviar_boot()

    logger.info("bot aguardando comandos...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()