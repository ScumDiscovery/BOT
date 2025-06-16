import os
import time
import json
from ftplib import FTP
import requests
from flask import Flask

app = Flask(__name__)

# Konfiguracja (ustaw swoje dane)
FTP_HOST = "176.57.174.10"
FTP_PORT = 50021
FTP_USER = "gpftp37275281717442833"
FTP_PASS = "LXNdGShY"
LOGS_PATH = "/SCUM/Saved/SaveFiles/Logs"
WEBHOOK_URL = "https://discord.com/api/webhooks/1383407890663997450/hr2zvr2PjO20IDLIk5nZd8juZDxG9kYkOOZ0c2_sqzGtuXra8Dz-HbhtnhtF3Yb0Hsgi"

def send_discord_message(content):
    data = {"content": content}
    try:
        resp = requests.post(WEBHOOK_URL, json=data)
        if resp.status_code != 204:
            print(f"[BOT][ERROR] Webhook zwrócił kod {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[BOT][ERROR] Błąd podczas wysyłania webhooka: {e}")

def parse_kill_log(lines):
    """
    Parsuje zawartość pliku kill_*.log.
    Szuka linii zaczynających się od "Died:" i następnej linii JSON z danymi o zabójstwie.
    Zwraca listę słowników z informacjami o zabójstwach.
    """
    kills = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Died:"):
            # Następna linia to JSON
            if i + 1 < len(lines):
                try:
                    kill_data = json.loads(lines[i + 1])
                    kills.append(kill_data)
                    i += 2
                    continue
                except Exception as e:
                    print(f"[BOT][WARN] Błąd parsowania JSON w pliku kill log: {e}")
        i += 1
    return kills

def format_kill_message(kill):
    # Przykładowa formatka wiadomości o zabójstwie
    killer = kill.get("killerName", "Unknown")
    victim = kill.get("victimName", "Unknown")
    weapon = kill.get("weaponName", "Unknown")
    distance = kill.get("distance", "Unknown")
    return f"💀 {killer} zabił {victim} używając {weapon} z odległości {distance}m."

def ftp_loop():
    print("[BOT] ftp_loop startuje")
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            ftp = FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=15)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(LOGS_PATH)
            print(f"[BOT] Zawartość katalogu FTP {LOGS_PATH}: {ftp.nlst()}")

            files = ftp.nlst()
            kill_files = [f for f in files if f.startswith("kill_") and f.endswith(".log")]

            if not kill_files:
                print("[BOT] Brak plików kill_*.log do przetworzenia.")
            else:
                for filename in kill_files:
                    print(f"[BOT] Pobieram plik: {filename}")
                    lines = []
                    ftp.retrlines(f"RETR {filename}", lines.append)
                    
                    kills = parse_kill_log(lines)
                    if kills:
                        for kill in kills:
                            msg = format_kill_message(kill)
                            print(f"[BOT] Wysyłam wiadomość: {msg}")
                            send_discord_message(msg)
                    else:
                        print(f"[BOT] Nie znaleziono zabójstw w pliku {filename}")

                    # Opcjonalnie: usuń plik po przetworzeniu, aby go nie czytać ponownie
                    # ftp.delete(filename)
                    # print(f"[BOT] Usunięto plik {filename} z FTP.")

            ftp.quit()
        except Exception as e:
            print(f"[BOT][BŁĄD] Problem z FTP lub przetwarzaniem: {e}")

        print("[BOT] Czekam 15 sekund przed kolejnym sprawdzeniem...")
        time.sleep(15)

@app.route("/")
def index():
    return "SCUM Bot działa!"

if __name__ == "__main__":
    from threading import Thread
    # Start FTP loop w osobnym wątku, żeby Flask działał równolegle
    Thread(target=ftp_loop, daemon=True).start()
    # Uruchom serwer Flask (np. na porcie 10000)
    app.run(host="0.0.0.0", port=10000)
