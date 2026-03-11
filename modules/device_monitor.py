import subprocess
import json
import os
from modules.telegram_alert import send_alert

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
            ["arp-scan", "--localnet"], text=True, stderr=subprocess.DEVNULL
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
            devices[mac] = {"ip": ip, "vendor": vendor}

    return devices

def get_network_summary(devices: dict, subnet: str = "192.168.1") -> str:
    """Retorna resumo de IPs usados e disponíveis na subnet /24"""
    used_ips = {int(d["ip"].split(".")[-1]) for d in devices.values() if d["ip"].startswith(subnet)}
    
    # IPs reservados: .0 (rede), .1 (gateway), .255 (broadcast)
    reserved = {0, 1, 255}
    total_available = 253  # .2 a .254
    used_count = len([ip for ip in used_ips if ip not in reserved])
    free_count = total_available - used_count

    return (
        f"📡 *Dispositivos na rede*\n"
        f"🟢 Conectados: {used_count}\n"
        f"⚪ IPs livres: {free_count}\n"
        f"📊 Total endereçável: {total_available}\n"
        f"━━━━━━━━━━━━━━━\n"
        + "\n".join(
            f"• `{d['ip']}` — {d['vendor'][:30]}"
            for d in sorted(devices.values(), key=lambda x: int(x["ip"].split(".")[-1]))
        )
    )

def check_devices(subnet: str = "192.168.1"):
    known = load_known_devices()
    current = scan_network()

    new_devices = []
    changed_ip = []

    for mac, info in current.items():
        if mac not in known:
            new_devices.append((mac, info))
        elif known[mac]["ip"] != info["ip"]:
            changed_ip.append((mac, known[mac]["ip"], info["ip"], info["vendor"]))

    # Notifica apenas novos e mudanças de IP
    for mac, info in new_devices:
        send_alert(
            f"🆕 *Novo dispositivo detectado*\n"
            f"IP: `{info['ip']}`\n"
            f"MAC: `{mac}`\n"
            f"Fabricante: {info['vendor']}"
        )

    for mac, old_ip, new_ip, vendor in changed_ip:
        send_alert(
            f"🔄 *Dispositivo trocou de IP*\n"
            f"MAC: `{mac}`\n"
            f"IP anterior: `{old_ip}` → Novo: `{new_ip}`\n"
            f"Fabricante: {vendor}"
        )

    save_known_devices(current)
    return current

def send_network_summary(subnet: str = "192.168.1"):
    """Envia resumo completo da rede — chame manualmente ou via comando /rede"""
    devices = scan_network()
    summary = get_network_summary(devices, subnet)
    send_alert(summary, parse_mode="Markdown")