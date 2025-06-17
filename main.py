
import os
import json
import requests
from PIL import Image, ImageDraw, ImageFont

LOG_PATH = "logs/scum_log.txt"
WEBHOOK_URL = "https://discord.com/api/webhooks/1383407890663997450/hr2zvr2PjO20IDLIk5nZd8juZDxG9kYkOOZ0c2_sqzGtuXra8Dz-HbhtnhtF3Yb0Hsgi"

def parse_latest_kill(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        if "Died:" in line:
            parts = line.split("Died:")[1].split("Weapon:")
            killer_data = parts[0].split("Killer:")
            victim = killer_data[0].strip().split(" ")[0]
            killer = killer_data[1].strip().split(" ")[0]
            weapon = parts[1].split("[")[0].strip()
            return killer, victim, weapon
    return None, None, None

def create_kill_image(killer, victim, weapon):
    bg = Image.open("assets/background.png").convert("RGBA")
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype("assets/Orbitron.ttf", 42)

    text = f"{killer} eliminated {victim}\nwith {weapon}"
    draw.multiline_text((60, 380), text, font=font, fill=(255, 255, 255), spacing=10)
    
    output_path = "kill_report.png"
    bg.save(output_path)
    return output_path

def send_to_discord(image_path):
    with open(image_path, "rb") as img_file:
        payload = {
            "username": "Discovery Bot",
            "content": "🗡️ Nowe zabójstwo zgłoszone!"
        }
        files = {"file": (os.path.basename(image_path), img_file)}
        requests.post(WEBHOOK_URL, data=payload, files=files)

def main():
    if not os.path.exists(LOG_PATH):
        print("❌ Plik loga nie istnieje.")
        return

    killer, victim, weapon = parse_latest_kill(LOG_PATH)
    if not killer:
        print("❌ Nie znaleziono zabójstwa w logu.")
        return

    image_path = create_kill_image(killer, victim, weapon)
    send_to_discord(image_path)
    print("✅ Zgłoszono do Discorda.")

if __name__ == "__main__":
    main()
