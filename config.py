import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WAN1_TARGET = "8.8.8.8"
WAN2_TARGET = "1.1.1.1"

PING_INTERVAL = 15
LATENCY_THRESHOLD = 120