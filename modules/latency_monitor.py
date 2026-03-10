from ping3 import ping
from modules.telegram_alert import send_alert
from config import WAN1_TARGET, LATENCY_THRESHOLD

def check_latency():

    r = ping(WAN1_TARGET, timeout=2)

    if r:
        latency = r * 1000

        if latency > LATENCY_THRESHOLD:
            send_alert(f"⚠️ Latência alta: {round(latency)} ms")