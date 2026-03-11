import subprocess
import json
import os
from modules.telegram_alert import send_alert
from modules.pfsense_monitor import get_dhcp_leases

KNOWN_DEVICES_FILE = os.path.join(os.path.dirname(__file__), "../data/known_devices.json")

def load_known_devices():
    if os.path.exists(KNOWN_DEVICES_FILE):
        with open(KNOWN_DEVICES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_known_devices(devices: dict):
    os.makedirs(os.path.dirname(KNOWN_DEVICES_FILE), exist_ok=True)
    with open(KNOWN_DEVICES_FILE, "w") as f:
        json.dump(devices, f, indent=2)

def scan_network() -> dict:
    try:
        result = subprocess.check_output(
            ["arp-scan", "-I", "enp6s18", "--localnet"],
            text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return {}

    devices = {}
    for line in result.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and "." in parts[0]:
            ip = parts[0]
            mac = parts[1].lower()
            vendor = " ".join(parts[2:]) if len(parts) > 2 else "Desconhecido"
            devices[mac] = {"ip": ip, "vendor": vendor, "hostname": ""}
    return devices

def enrich_with_hostnames(devices: dict) -> dict:
    try:
        leases = get_dhcp_leases()
        for mac, info in devices.items():
            if mac in leases and leases[mac].get("hostname"):
                info["hostname"] = leases[mac]["hostname"]
    except Exception as e:
        print(f"[DeviceMonitor] Erro ao buscar hostnames: {e}")
    return devices

def format_device_line(info: dict) -> str:
    name = info.get("hostname") or info.get("vendor", "Desconhecido")
    name = name[:28].replace("(", "").replace(")", "").replace("*", "").replace("_", "").replace("`", "")
    return f"• {info['ip']} — {name}"

def send_in_chunks(lines: list, header: str):
    chunk = header + "\n"
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:
            send_alert(chunk)
            chunk = "...continuacao\n"
        chunk += line + "\n"
    if chunk.strip():
        send_alert(chunk)

def check_devices(subnet: str = "192.168.100"):
    known = load_known_devices()
    current = scan_network()
    current = enrich_with_hostnames(current)

    for mac, info in current.items():
        name = info.get("hostname") or info.get("vendor", "Desconhecido")
        if mac not in known:
            send_alert(
                f"Novo dispositivo\nIP: {info['ip']}\nMAC: {mac}\nNome: {name}"
            )
        elif known[mac]["ip"] != info["ip"]:
            send_alert(
                f"Dispositivo trocou de IP\nNome: {name}\nMAC: {mac}\n{known[mac]['ip']} -> {info['ip']}"
            )

    save_known_devices(current)
    return current

def send_network_summary(subnet: str = "192.168.100"):
    devices = scan_network()
    devices = enrich_with_hostnames(devices)

    used_ips = {int(d["ip"].split(".")[-1]) for d in devices.values() if d["ip"].startswith(subnet)}
    reserved = {0, 1, 255}
    used_count = len([ip for ip in used_ips if ip not in reserved])
    free_count = 253 - used_count

    header = (
        f"Dispositivos na rede\n"
        f"Conectados: {used_count}\n"
        f"IPs livres: {free_count}\n"
        f"Total: 253\n"
        f"-------------------"
    )

    lines = [
        format_device_line(d)
        for d in sorted(devices.values(), key=lambda x: int(x["ip"].split(".")[-1]))
    ]

    send_in_chunks(lines, header)
