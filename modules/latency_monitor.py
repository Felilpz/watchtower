from ping3 import ping
from modules.telegram_alert import send_alert
from config import WAN1_TARGET, WAN2_TARGET, LATENCY_THRESHOLD

def _check_latency(target: str, name: str):
    result = ping(target, timeout=2)
    if result is None:
        return  # WAN offline, wan_monitor já cuida disso
    
    latency = result * 1000
    if latency > LATENCY_THRESHOLD:
        send_alert(
            f"⚠️ *Latência alta na {name}*\n"
            f"Alvo: `{target}`\n"
            f"Latência: `{round(latency)} ms` (limite: {LATENCY_THRESHOLD} ms)",
            parse_mode="Markdown"
        )

def check_latency():
    _check_latency(WAN1_TARGET, "WAN1")
    _check_latency(WAN2_TARGET, "WAN2")