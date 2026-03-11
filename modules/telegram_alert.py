import requests
from config import TOKEN, CHAT_ID

def send_alert(message: str, parse_mode: str = None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(url, data=payload, timeout=5)
        if not r.json().get("ok"):
            print(f"[Telegram] Erro API: {r.text}")
    except Exception as e:
        print(f"[Telegram] Erro ao enviar: {e}")
