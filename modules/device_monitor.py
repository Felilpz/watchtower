import subprocess
from modules.telegram_alert import send_alert

known_devices = {}

def scan_network():
    result = subprocess.check_output(
        ["arp-scan", "--localnet"], text=True
    )

    devices = {}

    for line in result.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and "." in parts[0]:
            ip = parts[0]
            mac = parts[1]

            devices[mac] = ip

    return devices

def check_devices():
    global known_devices

    devices = scan_network()

    # novo dispositivo
    for mac, ip in devices.items():
        if mac not in known_devices:
            send_alert(f"🟢 Novo dispositivo\nIP: {ip}\nMAC: {mac}")

    # dispositivo mudou de ip
    for mac, ip in devices.items():
        if mac in known_devices and known_devices[mac] != ip:
            send_alert(
                send_alert(f"🟢 Novo dispositivo\nIP: {ip}\nMAC: {mac}")
            )

    known_devices = devices