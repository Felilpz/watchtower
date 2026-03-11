import subprocess
from ping3 import ping
from modules.telegram_alert import send_alert
from modules.pfsense_monitor import get_dhcp_leases

# Estado dos dispositivos { ip: bool }
_device_status = {}

def get_critical_devices() -> dict:
    """Retorna static mappings do pfSense: { ip: hostname }"""
    try:
        leases = get_dhcp_leases()
        # Filtra apenas os que têm hostname definido (static mappings)
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
    global _device_status

    devices = get_critical_devices()
    if not devices:
        return

    down = []
    up = []

    for ip, hostname in devices.items():
        is_up = ping_device(ip)
        was_up = _device_status.get(ip, True)  # assume online na primeira vez

        if not is_up and was_up:
            send_alert(f"🔴 DISPOSITIVO CAIU\nNome: {hostname}\nIP: {ip}")
            down.append((ip, hostname))

        elif is_up and not was_up:
            send_alert(f"🟢 DISPOSITIVO VOLTOU\nNome: {hostname}\nIP: {ip}")
            up.append((ip, hostname))

        _device_status[ip] = is_up

def send_critical_summary():
    """Envia resumo de todos os dispositivos críticos — comando /criticos"""
    devices = get_critical_devices()
    if not devices:
        send_alert("Nenhum dispositivo critico encontrado nos static mappings.")
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