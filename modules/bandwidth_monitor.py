import psutil
from modules.telegram_alert import send_alert

last_sent = 0
last_recv = 0

def check_bandwidth():

    global last_sent
    global last_recv

    counters = psutil.net_io_counters()

    sent = counters.bytes_sent
    recv = counters.bytes_recv

    upload = (sent - last_sent) / 1024 / 1024
    download = (recv - last_recv) / 1024 / 1024

    last_sent = sent
    last_recv = recv

    send_alert(
            f"📊 Uso de rede\n⬆ Upload: {upload:.2f} MB\n⬇ Download: {download:.2f} MB"
    )