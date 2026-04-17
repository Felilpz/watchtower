import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"variável ausente no .env: {key}")
    return value


TELEGRAM_TOKEN   = _require("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")

PFSENSE_HOST = _require("PFSENSE_HOST")
PFSENSE_USER = _require("PFSENSE_USER")
PFSENSE_PASS = _require("PFSENSE_PASS")
PFSENSE_PORT = int(_require("PFSENSE_PORT"))

STATIC_JSON_PATH = os.path.join(os.path.dirname(__file__), "static.json")

GATEWAYS = {
    "CONNECTJA": "8.8.8.8",
    "ALTERNA":   "1.1.1.1",
}

PING_INTERVAL_SECONDS = 30
PING_TIMEOUT_SECONDS  = 3
PING_COUNT            = 3