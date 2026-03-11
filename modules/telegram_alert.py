import requests
from config import TOKEN, CHAT_ID

def send_alert(message: str, parse_mode: str = "Markdown"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": parse_mode
    }
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"[Telegram] Erro ao enviar: {e}")