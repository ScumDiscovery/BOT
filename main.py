from flask import Flask
from threading import Thread
import time
import ftplib
import json

app = Flask(__name__)

FTP_HOST = '176.57.174.10'
FTP_PORT = 50021
FTP_USER = 'gpftp37275281717442833'
FTP_PASS = 'TWOJE_PRAWDZIWE_HASLO'  # <-- wpisz tutaj swoje prawdziwe hasło FTP
LOGS_PATH = '/SCUM/Saved/SaveFiles/Logs'

def ftp_loop():
    print("[BOT] ftp_loop startuje")  # drukuje info o starcie wątku
    processed_files = set()
    while True:
        try:
            print("[BOT] Łączenie z FTP...")
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
            ftp.login(FTP_USER, FTP_PASS)
            print("[BOT] Połączono z FTP")

            ftp.cwd(LOGS_PATH)
            files = ftp.nlst()
            kill_logs = [f for f in files if f.startswith('kill_') and f.endswith('.log')]

            new_logs = [f for f in kill_logs if f not in processed_files]
            print(f"[BOT] Nowe pliki do przetworzenia: {new_logs}")

            for filename in new_logs:
                print(f"[BOT] Pobieram i analizuję plik: {filename}")
                lines = []
                ftp.retrlines(f'RETR {filename}', lines.append)
                for i, line in enumerate(lines):
                    if line.startswith("Died:"):
                        print(f"  --> {line.strip()}")
                        if i + 1 < len(lines):
                            try:
                                data = json.loads(lines[i+1])
                                print(f"      Parsed JSON: {data}")
                            except json.JSONDecodeError as e:
                                print(f"      Błąd parsowania JSON: {e}")
                processed_files.add(filename)

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

    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
