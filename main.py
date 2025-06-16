import ftplib
import io
import json
import re
import time
import requests
from threading import Thread
from flask import Flask

# --- KONFIGURACJA ---
FTP_HOST = "176.57.174.10"
FTP_PORT = 50021
FTP_USER = "gpftp37275281717442833"
FTP_PASS = "LXNdGShY"
FTP_LOG_DIR = "/SCUM/Saved/SaveFiles/Logs"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/xxx/yyy"

POLL_INTERVAL = 15  # sekund

app = Flask(__name__)

processed_files = set()  # pliki już przetworzone

def send_discord_message(content: str):
    data = {"content": content}
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=data)
        if resp.status_code != 204 and resp.status_code != 200:
            print(f"[!] Discord webhook error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[!] Discord webhook exception: {e}")

def parse_log_content(log_content: str):
    """
    Parsuje zawartość pliku log (tekst), wyciąga zabójstwa i wysyła na Discord.
    Format pliku wg WhalleyBot:
    - linia z "Died:"
    - następna linia to JSON z info o zabójstwie
    """
    lines = log_content.splitlines()
    for i, line in enumerate(lines):
        if "Died:" in line:
            if i + 1 < len(lines):
                json_line = lines[i + 1].strip()
                try:
                    data = json.loads(json_line)
                    killer = data.get("KillerName", "Unknown")
                    victim = data.get("PlayerName", "Unknown")
                    weapon = data.get("KillerWeapon", "Unknown")
                    msg = f"💀 {victim} został zabity przez {killer} bronią {weapon}"
                    print(f"[INFO] {msg}")
                    send_discord_message(msg)
                except json.JSONDecodeError:
                    print("[!] Nie udało się sparsować JSON-a w logu")
            else:
                print("[!] Brak JSON-a po linii 'Died:'")

def ftp_loop():
    global processed_files
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(FTP_LOG_DIR)

            files = ftp.nlst()
            kill_logs = [f for f in files if f.startswith("kill_") and f.endswith(".log")]

            for filename in kill_logs:
                if filename in processed_files:
                    continue

                print(f"[BOT] Pobieram i analizuję: {filename}")
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {filename}", bio.write)
                bio.seek(0)
                content = bio.read().decode("utf-8", errors="ignore")

                parse_log_content(content)

                processed_files.add(filename)
            ftp.quit()
        except Exception as e:
            print(f"[!] Błąd FTP lub parsowania: {e}")

        time.sleep(POLL_INTERVAL)

# Flask endpoint do health checka
@app.route("/")
def index():
    return "SCUM Bot działa!"

if __name__ == "__main__":
    print("[BOT] Startuję pętlę FTP w tle...")
    thread = Thread(target=ftp_loop, daemon=True)
    thread.start()

    # Uruchom flask na porcie 10000, dostępny z każdego IP (ważne na Render)
    app.run(host="0.0.0.0", port=10000)
