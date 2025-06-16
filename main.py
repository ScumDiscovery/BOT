import os
import threading
import time
from ftplib import FTP
from flask import Flask

app = Flask(__name__)

# --- FTP settings (wstaw swoje dane) ---
FTP_HOST = "176.57.174.10"
FTP_PORT = 50021
FTP_USER = "gpftp37275281717442833"
FTP_PASS = "LXNdGShY"
FTP_PATH = "/SCUM/Saved/SaveFiles/Logs"

# --- Twój webhook Discord ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/xxx/yyy"

def process_log_content(content):
    # Tu napisz analizę logów, parsowanie, wysyłanie na Discord, itp.
    print("[BOT] Przetwarzam logi FTP (tutaj implementuj logikę)...")

def ftp_loop():
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            with FTP() as ftp:
                ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd(FTP_PATH)

                filenames = ftp.nlst()
                for filename in filenames:
                    if filename.startswith("kill_") and filename.endswith(".log"):
                        print(f"[BOT] Pobieram {filename}...")
                        lines = []
                        ftp.retrlines(f"RETR {filename}", lines.append)
                        content = "\n".join(lines)
                        process_log_content(content)

            print("[BOT] Pętla FTP - czekam 15 sekund...")
        except Exception as e:
            print(f"[BOT] Błąd FTP: {e}")

        time.sleep(15)


@app.route("/")
def index():
    return "Bot SCUM działa!"


if __name__ == "__main__":
    # Start pętli FTP w osobnym wątku
    threading.Thread(target=ftp_loop, daemon=True).start()

    # Pobierz port od Render lub domyślnie 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
