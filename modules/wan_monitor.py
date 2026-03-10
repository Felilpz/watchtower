from ping3 import ping
from modules.telegram_alert import send_alert
from config import WAN1_TARGET, WAN2_TARGET

wan1_status = True
wan2_status = True

def check_wans():
    global wan1_status
    global wan2_status
    
    r1 = ping(WAN1_TARGET, timeout=2)
    r2 = ping(WAN2_TARGET, timeout=2)

    if r1 is None (wan1_status):
        send_alert("wan1 caiu")
        wan1_status = False

    if r1 is None (wan1_status):
        send_alert("wan1 voltou")
        wan1_status = True
    
    if r2 is None (wan2_status):
        send_alert("wan2 caiu")
        wan2_status = False

    if r2 is None (wan2_status):
        send_alert("wan2 voltou")
        wan2_status = True