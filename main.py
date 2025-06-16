import os
import time
import ftplib
import requests
import threading
from flask import Flask
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Flask app do uruchomienia serwera HTTP
app = Flask(__name__)

# Prosta strona główna, by Render wykrył port
@app.route("/")
def index():
    return "SCUM bot działa 🎯"

# Funkcja do wysyłania wiadomości na Discorda
def send_discord_message(content):
    data = {"content": content}
    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        print(f"[Discord] Status: {response.status_code}")
    except Exception as e:
        print(f"[Discord error] {e}")

# Główna logika bota – łączy się z FTP i szuka plików kill_*.log
def bot_loop():
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            with ftplib.FTP() as ftp:
                ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd(FTP_PATH)
                files = ftp.nlst()

                kill_files = [f for f in files if f.startswith("kill_") and f.endswith(".log")]
                print(f"[BOT] Znalezione pliki: {kill_files}")

                # Na tym etapie możesz dodać dalszą analizę plików i wysyłkę do Discorda
                # send_discord_message(f"Znalezione pliki: {kill_files}")

        except Exception as e:
            print(f"[BOT ERROR] {e}")
        time.sleep(15)

# Start bota w osobnym wątku
def start_bot():
    thread = threading.Thread(target=bot_loop)
    thread.daemon = True
    thread.start()

# Uruchom Flask serwer i bota
if __name__ == "__main__":
    start_bot()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
