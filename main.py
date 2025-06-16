import ftplib
import time
import os
import requests
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/SCUM/Saved/SaveFiles/Logs")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 15))

processed_files = set()

def connect_ftp():
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
    ftp.login(FTP_USER, FTP_PASS)
    return ftp

def get_kill_lines_from_log(log_text):
    lines = log_text.splitlines()
    kill_entries = []
    for line in lines:
        if "Died:" in line:
            kill_entries.append(line.strip())
    return kill_entries

def send_to_discord(message):
    if WEBHOOK_URL:
        data = {"content": message}
        requests.post(WEBHOOK_URL, json=data)

def process_logs():
    global processed_files
    ftp = connect_ftp()
    ftp.cwd(FTP_PATH)
    files = ftp.nlst("kill_*.log")

    for filename in files:
        if filename in processed_files:
            continue

        memfile = BytesIO()
        ftp.retrbinary(f"RETR {filename}", memfile.write)
        memfile.seek(0)
        text = memfile.read().decode("windows-1250", errors="ignore")

        kill_lines = get_kill_lines_from_log(text)
        for line in kill_lines:
            send_to_discord(f"🔪 Zabójstwo: {line}")

        processed_files.add(filename)

    ftp.quit()

def main():
    print("SCUM bot uruchomiony...")
    while True:
        try:
            process_logs()
        except Exception as e:
            print(f"[Błąd] {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
