import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def test_webhook():
    if not WEBHOOK_URL:
        print("❌ Brak ustawionego WEBHOOKA.")
        return
    test_message = {
        "content": "✅ Testowa wiadomość z SCUM bota. Webhook działa poprawnie!"
    }
    response = requests.post(WEBHOOK_URL, json=test_message)
    if response.status_code == 204:
        print("📡 Wiadomość wysłana poprawnie.")
    else:
        print(f"❌ Błąd wysyłki: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_webhook()
