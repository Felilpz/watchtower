import psutil
from modules.telegram_alert import send_alert

_last_sent = 0
_last_recv = 0

def check_bandwidth(interface: str = None):
    global _last_sent, _last_recv

    if interface:
        counters = psutil.net_io_counters(pernic=True).get(interface)
        if not counters:
            send_alert(f"⚠️ Interface `{interface}` não encontrada.", parse_mode="Markdown")
            return
    else:
        counters = psutil.net_io_counters()

    sent = counters.bytes_sent
    recv = counters.bytes_recv

    # Primeira execução — só inicializa
    if _last_sent == 0 and _last_recv == 0:
        _last_sent = sent
        _last_recv = recv
        return

    upload_mb = (sent - _last_sent) / 1024 / 1024
    download_mb = (recv - _last_recv) / 1024 / 1024

    _last_sent = sent
    _last_recv = recv

    send_alert(
        f"📊 *Uso de rede (últimos 10 min)*\n"
        f"⬆️ Upload: `{upload_mb:.2f} MB`\n"
        f"⬇️ Download: `{download_mb:.2f} MB`",
        parse_mode="Markdown"
    )