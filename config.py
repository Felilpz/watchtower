import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WAN1_TARGET = os.getenv("WAN1_TARGET", "8.8.8.8")
WAN2_TARGET = os.getenv("WAN2_TARGET", "1.1.1.1")
LATENCY_THRESHOLD = int(os.getenv("LATENCY_THRESHOLD", "150"))
PFSENSE_HOST = os.getenv("PFSENSE_HOST", "192.168.100.1")
PFSENSE_USER = os.getenv("PFSENSE_USER", "admin")
PFSENSE_PASS = os.getenv("PFSENSE_PASS", "")
PFSENSE_PORT = int(os.getenv("PFSENSE_PORT", 22))
