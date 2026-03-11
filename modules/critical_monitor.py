from ping3 import ping
from modules.telegram_alert import send_alert
from modules.pfsense_monitor import get_dhcp_leases

_device_status = {}
_initialized = False

def get_critical_devices() -> dict:
    try:
        leases = get_dhcp_leases()
        return {
            info["ip"]: info["hostname"]
            for info in leases.values()
            if info.get("hostname") and info.get("ip")
        }
    except Exception as e:
        print(f"[CriticalMonitor] Erro ao buscar dispositivos: {e}")
        return {}

def ping_device(ip: str) -> bool:
    try:
        result = ping(ip, timeout=2, count=2)
        return result is not None
    except Exception:
        return False

def check_critical_devices():
    global _device_status, _initialized

    devices = get_critical_devices()
    if not devices:
        return

    for ip, hostname in devices.items():
        is_up = ping_device(ip)

        if not _initialized:
            # Primeira rodada — só popula o estado, sem notificar
            _device_status[ip] = is_up
            continue

        was_up = _device_status.get(ip, True)

        if not is_up and was_up:
            send_alert(f"DISPOSITIVO CAIU\nNome: {hostname}\nIP: {ip}")

        elif is_up and not was_up:
            send_alert(f"DISPOSITIVO VOLTOU\nNome: {hostname}\nIP: {ip}")

        _device_status[ip] = is_up

    _initialized = True

def send_critical_summary():
    devices = get_critical_devices()
    if not devices:
        send_alert("Nenhum dispositivo critico encontrado.")
        return

    online = []
    offline = []

    for ip, hostname in sorted(devices.items(), key=lambda x: int(x[0].split(".")[-1])):
        if ping_device(ip):
            online.append(f"  {ip} — {hostname}")
        else:
            offline.append(f"  {ip} — {hostname}")

    msg = (
        f"Dispositivos Criticos\n"
        f"Online: {len(online)} | Offline: {len(offline)}\n"
        f"-------------------\n"
    )

    if offline:
        msg += "OFFLINE:\n" + "\n".join(offline) + "\n"

    msg += "ONLINE:\n" + "\n".join(online)

    send_alert(msg)