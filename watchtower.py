import logging
import threading
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN
from modules.wan_monitor import iniciar_monitoramento_wan
from modules.bot_commands import cmd_start, cmd_wan, cmd_ping, cmd_devices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("watchtower")


def main():
    logger.info("watchtower iniciando...")

    threading.Thread(
        target=iniciar_monitoramento_wan,
        name="wan-monitor",
        daemon=True,
    ).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("wan",     cmd_wan))
    app.add_handler(CommandHandler("ping",    cmd_ping))
    app.add_handler(CommandHandler("devices", cmd_devices))

    logger.info("bot aguardando comandos...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()