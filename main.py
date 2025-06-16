import time
import json
import os
from ftplib import FTP
import requests

# Ustawienia FTP
FTP_HOST = '176.57.174.10'
FTP_PORT = 50021
FTP_USER = 'gpftp37275281717442833'
FTP_PASS = 'LXNdGShY'

# Katalog z logami na FTP
LOG_DIR = '/SCUM/Saved/SaveFiles/Logs'

# Webhook Discorda
WEBHOOK_URL = 'https://discord.com/api/webhooks/xxx/yyy'

# Plik do zapisywania postępu offsetu
OFFSET_FILE = 'processed_offsets.json'


def load_offsets():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_offsets(offsets):
    with open(OFFSET_FILE, 'w') as f:
        json.dump(offsets, f)


def send_to_discord(message):
    data = {"content": message}
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code != 204 and response.status_code != 200:
            print(f"[WARN] Discord webhook returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Błąd wysyłania do Discorda: {e}")


def connect_ftp():
    ftp = FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd(LOG_DIR)
    return ftp


def read_new_logs(ftp, offsets):
    files = ftp.nlst()
    kill_files = [f for f in files if f.startswith('kill_') and f.endswith('.log')]
    updated_offsets = offsets.copy()

    for filename in kill_files:
        try:
            # Pobierz rozmiar pliku
            size = ftp.size(filename)
            last_line_idx = offsets.get(filename, 0)

            # Pobierz cały plik (niestety FTP RETR nie obsługuje offsetu)
            new_data = []
            ftp.retrbinary(f"RETR {filename}", lambda d: new_data.append(d))
            content = b''.join(new_data).decode('utf-8', errors='ignore')
            lines = content.splitlines()

            # Jeśli plik został skasowany/nadpisany i jest krótszy niż offset, zacznij od początku
            if len(lines) < last_line_idx:
                print(f"[INFO] Plik {filename} został skrócony lub nadpisany, reset offsetu")
                last_line_idx = 0

            if len(lines) == last_line_idx:
                # Nic nowego w pliku
                continue

            # Przetwarzaj tylko nowe linie
            i = last_line_idx
            while i < len(lines):
                line = lines[i]
                if line.startswith("Died:"):
                    # Następna linia powinna być JSON-em
                    if i + 1 < len(lines):
                        json_line = lines[i + 1]
                        try:
                            data = json.loads(json_line)
                            killer = data.get("KillerName", "Unknown")
                            victim = data.get("VictimName", "Unknown")
                            weapon = data.get("WeaponName", "Unknown")
                            msg = f"💀 {victim} zginął od {killer} za pomocą {weapon}."
                            print(f"[INFO] Wykryto zabójstwo: {msg}")
                            send_to_discord(msg)
                        except json.JSONDecodeError:
                            print(f"[WARN] Niepoprawny JSON w pliku {filename} linia {i + 1}")
                    i += 2
                    continue
                i += 1

            updated_offsets[filename] = len(lines)

        except Exception as e:
            print(f"[ERROR] Błąd przetwarzania pliku {filename}: {e}")

    return updated_offsets


def main_loop():
    offsets = load_offsets()
    print("[BOT] Startuje pętla FTP...")
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            ftp = connect_ftp()
            new_offsets = read_new_logs(ftp, offsets)
            ftp.quit()
            if new_offsets != offsets:
                offsets = new_offsets
                save_offsets(offsets)
        except Exception as e:
            print(f"[ERROR] Błąd w pętli głównej: {e}")
        time.sleep(15)


if __name__ == '__main__':
    main_loop()
