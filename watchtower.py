import time

from modules.telegram_alert import send_alert
from modules.wan_monitor import check_wans
from modules.latency_monitor import check_latency
from modules.device_monitor import check_devices
from modules.bandwidth_monitor import check_bandwidth

from config import PING_INTERVAL

print("🚀 Watchtower iniciado")

send_alert("🟢 Watchtower iniciado\nMonitoramento de rede ativo")

while True:
    check_wans()
    check_latency()
    check_devices()
    check_bandwidth()

    time.sleep(PING_INTERVAL)