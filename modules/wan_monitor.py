from ping3 import ping
from modules.telegram_alert import send_alert
from config import WAN1_TARGET, WAN2_TARGET

wan1_up = True
wan2_up = True

def _check_wan(target: str, name: str, current_status: bool) -> bool:
    result = ping(target, timeout=2)
    is_up = result is not None
    if not is_up and current_status:
        send_alert(f"🔴 *{name} CAIU!*\nAlvo: `{target}`", parse_mode="Markdown")
    elif is_up and not current_status:
        send_alert(f"🟢 *{name} VOLTOU!*\nAlvo: `{target}`", parse_mode="Markdown")
    return is_up

def check_wans():
    global wan1_up, wan2_up
    wan1_up = _check_wan(WAN1_TARGET, "WAN1", wan1_up)
    wan2_up = _check_wan(WAN2_TARGET, "WAN2", wan2_up)

def get_wan_status() -> str:
    w1 = "🟢 Online" if wan1_up else "🔴 Offline"
    w2 = "🟢 Online" if wan2_up else "🔴 Offline"
    return f"📡 *Status WAN*\nWAN1: {w1}\nWAN2: {w2}"
