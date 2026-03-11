import threading
import time
import requests
from config import TOKEN, CHAT_ID
from modules.telegram_alert import send_alert
from modules.wan_monitor import check_wans, get_wan_status
from modules.latency_monitor import check_latency
from modules.bandwidth_monitor import check_bandwidth
from modules.device_monitor import check_devices, send_network_summary

# Intervalos (segundos)
INTERVAL_WAN      = 30    # checa WAN a cada 30s
INTERVAL_LATENCY  = 60    # latência a cada 1 min
INTERVAL_BANDWIDTH = 600  # banda a cada 10 min
INTERVAL_DEVICES  = 300   # dispositivos a cada 5 min
POLL_INTERVAL     = 3    

_last_update_id = 0

def handle_commands():
    global _last_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": _last_update_id + 1, "timeout": 2}

    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
    except Exception:
        return

    for update in data.get("result", []):
        _last_update_id = update["update_id"]
        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "").strip().lower()

        if chat_id != str(CHAT_ID):
            continue  # ignora chats não autorizados

        if text == "/rede":
            send_network_summary()

        elif text == "/status":
            send_alert(get_wan_status(), parse_mode="Markdown")

        elif text == "/help":
            send_alert(
                "🤖 *WatchTower Commands*\n\n"
                "/rede — Lista dispositivos e IPs disponíveis\n"
                "/status — Status atual das WANs\n"
                "/help — Esta mensagem",
                parse_mode="Markdown"
            )

#  Loop genérico de tarefa periódica 
def run_periodically(func, interval: int, name: str):
    while True:
        try:
            func()
        except Exception as e:
            print(f"[{name}] Erro: {e}")
        time.sleep(interval)

#  Inicialização 
def main():
    send_alert("🚀 *WatchTower iniciado!*\nDigite /help para ver os comandos.", parse_mode="Markdown")

    tasks = [
        (check_wans,      INTERVAL_WAN,       "WAN Monitor"),
        (check_latency,   INTERVAL_LATENCY,   "Latency Monitor"),
        (check_bandwidth, INTERVAL_BANDWIDTH, "Bandwidth Monitor"),
        (check_devices,   INTERVAL_DEVICES,   "Device Monitor"),
    ]

    for func, interval, name in tasks:
        t = threading.Thread(target=run_periodically, args=(func, interval, name), daemon=True)
        t.start()
        print(f"[WatchTower] ✅ {name} iniciado (intervalo: {interval}s)")

    # Loop de comandos no thread principal
    print("[WatchTower] 🎧 Aguardando comandos Telegram...")
    while True:
        try:
            handle_commands()
        except Exception as e:
            print(f"[Commands] Erro: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()