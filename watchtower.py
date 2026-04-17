import logging
import threading
from modules.wan_monitor import iniciar_monitoramento_wan

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("watchtower")


def main():
    logger.info("=" * 50)
    logger.info("  WatchTower Bot iniciando...")
    logger.info("=" * 50)

    # monitor WAN em thread separada
    t_wan = threading.Thread(
        target=iniciar_monitoramento_wan,
        name="wan-monitor",
        daemon=True,
    )
    t_wan.start()
    logger.info("Thread WAN Monitor: OK")

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("WatchTower encerrado pelo usuário.")


if __name__ == "__main__":
    main()