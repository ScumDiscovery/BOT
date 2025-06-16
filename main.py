import os
import time
import ftplib
import json
import requests
import threading
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

app = Flask(__name__)

@app.route("/")
def index():
    return "SCUM bot działa 🎯"

# Bufor przetworzonych plików
sent_logs = set()

# Funkcja do wysyłania wiadomości do Discorda
def send_discord_message(content):
    try:
        response = requests.post(DISCORD_WEBHOOK, json={"content": content})
        print(f"[Discord] Wysłano ({response.status_code})")
    except Exception as e:
        print(f"[Discord ERROR] {e}")

# Analiza zawartości pliku kill log
def parse_and_send_kill_log(filename, content):
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "Died:" in line and i + 1 < len(lines):
            try:
                data = json.loads(lines[i + 1])
                killer = data.get("killer", {}).get("playerName", "Nieznany")
                victim = data.get("victim", {}).get("playerName", "Nieznany")
                weapon = data.get("damageType", "brak informacji")
                msg = f"☠️ **{victim}** został zabity przez **{killer}** (broń: `{weapon}`)"
                send_discord_message(msg)
                print(f"[LOG] Wysłano info z pliku {filename}")
            except json.JSONDecodeError:
                print(f"[BŁĄD] Nieprawidłowy JSON w {filename}")

# Pobiera i przetwarza WSZYSTKIE kill logi na FTP
def process_all_kill_logs():
    print("[BOT] Pobieranie listy logów z FTP...")
    try:
        with ftplib.FTP() as ftp:
            ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(FTP_PATH)
            files = ftp.nlst()

            kill_logs = [f for f in files if f.startswith("kill_") and f.endswith(".log")]
            for fname in kill_logs:
                if fname in sent_logs:
                    continue
                try:
                    with open(fname, "wb") as local_file:
                        ftp.retrbinary(f"RETR {fname}", local_file.write)
                    with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    parse_and_send_kill_log(fname, content)
                    sent_logs.add(fname)
                except Exception as e:
                    print(f"[BŁĄD] Nie udało się przetworzyć {fname}: {e}")
                finally:
                    try:
                        os.remove(fname)
                    except:
                        pass
    except Exception as e:
        print(f"[BOT ERROR] {e}")

# Główna pętla co 15 sekund
def bot_loop():
    while True:
        process_all_kill_logs()
        time.sleep(15)

# Uruchomienie pętli bota
def start_bot():
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    start_bot()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
