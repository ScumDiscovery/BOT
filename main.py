from flask import Flask
from threading import Thread
import time
import ftplib

app = Flask(__name__)

FTP_HOST = '176.57.174.10'
FTP_PORT = 50021
FTP_USER = 'gpftp37275281717442833'
FTP_PASS = 'TWOJE_HASLO_TUTAJ'  # Wstaw swoje hasło
LOGS_PATH = '/SCUM/Saved/SaveFiles/Logs'

def ftp_loop():
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
            ftp.login(FTP_USER, FTP_PASS)
            print("[BOT] Połączono z FTP")

            print(f"[BOT] Przechodzę do katalogu {LOGS_PATH}")
            ftp.cwd(LOGS_PATH)

            files = ftp.nlst()
            print(f"[BOT] Pliki na FTP: {files}")

            kill_logs = [f for f in files if f.startswith('kill_') and f.endswith('.log')]
            print(f"[BOT] Znalezione pliki kill logów: {kill_logs}")

            ftp.quit()
        except Exception as e:
            print(f"[BOT][BŁĄD] Problem z FTP: {e}")

        time.sleep(15)

@app.route('/')
def home():
    return "Bot SCUM działa!"

if __name__ == '__main__':
    thread = Thread(target=ftp_loop, daemon=True)
    thread.start()

    # Ważne: wyłączamy debug i reloader, żeby Flask nie uruchamiał się dwa razy
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
