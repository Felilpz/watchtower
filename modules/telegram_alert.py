import requests
from config import TOKEN, CHAT_ID

def send_alert (message):
    url = f"https://api.telegram.org/bot{x}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=5)
        print("Alerta enviado:", message)

    except Exception as e:
        print("Erro ao enviar alerta", e)