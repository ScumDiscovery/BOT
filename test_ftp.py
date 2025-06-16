import ftplib
import os
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/SCUM/Saved/SaveFiles/Logs")

def test_ftp_connection():
    try:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
        ftp.login(FTP_USER, FTP_PASS)
        print("✅ Połączono z FTP!")

        ftp.cwd(FTP_PATH)
        files = ftp.nlst("kill_*.log")
        print(f"🗂️ Znaleziono plików: {len(files)}")

        if files:
            latest_file = sorted(files)[-1]
            print(f"📄 Ostatni plik: {latest_file}")

            memfile = BytesIO()
            ftp.retrbinary(f"RETR {latest_file}", memfile.write)
            memfile.seek(0)
            text = memfile.read().decode("windows-1250", errors="ignore")
            print("\n🧾 Zawartość pliku:\n")
            print(text[:1000])  # pokaż pierwsze 1000 znaków

        ftp.quit()
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    test_ftp_connection()
