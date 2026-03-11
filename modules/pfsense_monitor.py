import paramiko
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

PFSENSE_HOST = os.getenv("PFSENSE_HOST", "192.168.100.1")
PFSENSE_USER = os.getenv("PFSENSE_USER", "admin")
PFSENSE_PASS = os.getenv("PFSENSE_PASS", "")
PFSENSE_PORT = int(os.getenv("PFSENSE_PORT", 22))

def _ssh_command(command: str) -> str:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(PFSENSE_HOST, port=PFSENSE_PORT, username=PFSENSE_USER, password=PFSENSE_PASS, timeout=5)
    _, stdout, _ = client.exec_command(command)
    result = stdout.read().decode()
    client.close()
    return result

def get_dhcp_leases() -> dict:
    leases = {}
    try:
        # 1. Lê leases dinâmicos
        content = _ssh_command("cat /var/dhcpd/var/db/dhcpd.leases")
        current = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("lease "):
                current = {"ip": line.split()[1], "hostname": "", "mac": ""}
            elif line.startswith("hardware ethernet"):
                current["mac"] = line.split()[-1].rstrip(";").lower()
            elif line.startswith("client-hostname"):
                current["hostname"] = line.split('"')[1] if '"' in line else ""
            elif line == "}":
                mac = current.get("mac")
                if mac:
                    leases[mac] = {
                        "ip": current.get("ip", ""),
                        "hostname": current.get("hostname", "")
                    }
                current = {}

        # 2. Lê static mappings do config.xml
        xml_content = _ssh_command("cat /cf/conf/config.xml")
        root = ET.fromstring(xml_content)

        for dhcp in root.iter("dhcpd"):
            for subnet in dhcp:
                for mapping in subnet.findall("staticmap"):
                    mac = mapping.findtext("mac", "").lower().strip()
                    ip = mapping.findtext("ipaddr", "").strip()
                    hostname = mapping.findtext("hostname", "").strip()
                    if mac and ip and hostname:
                        leases[mac] = {"ip": ip, "hostname": hostname}

    except Exception as e:
        print(f"[pfSense SSH] Erro: {e}")

    return leases
