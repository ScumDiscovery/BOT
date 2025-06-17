import os
import re
import json
import requests
from PIL import Image, ImageDraw, ImageFont

# === ŚCIEŻKI I USTAWIENIA ===
LOG_PATH = "logs/scum_log.txt"
MAP_PATH = "assets/map_full.jpg"
WEAPON_ICON = "assets/katana.png"
FONT_PATH = "assets/font.ttf"
OUTPUT_PATH = "output/death_report.jpg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1383407890663997450/hr2zvr2PjO20IDLIk5nZd8juZDxG9kYkOOZ0c2_sqzGtuXra8Dz-HbhtnhtF3Yb0Hsgi"

# === FUNKCJE ===
def parse_log(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in reversed(lines):
        if "Died:" in line:
            data_line = line.strip()
        if line.strip().startswith("{") and "Killer" in line:
            json_line = line.strip()
            break

    data = json.loads(json_line)
    killer = data['Killer']['ProfileName']
    victim = data['Victim']['ProfileName']
    weapon = data['Weapon'].split()[0]
    time_of_day = data['TimeOfDay']
    killer_coords = data['Killer']['ServerLocation']
    victim_coords = data['Victim']['ServerLocation']

    return {
        "killer": killer,
        "victim": victim,
        "weapon": weapon,
        "time": time_of_day,
        "killer_coords": killer_coords,
        "victim_coords": victim_coords
    }

def crop_map(center_coords, zoom=300):
    map_img = Image.open(MAP_PATH).convert("RGB")
    x = int(center_coords["X"])
    y = int(-center_coords["Y"])  # odwrócenie osi Y

    width, height = map_img.size
    crop_box = (
        max(0, x - zoom),
        max(0, y - zoom),
        min(width, x + zoom),
        min(height, y + zoom)
    )
    cropped = map_img.crop(crop_box)
    return cropped.resize((400, 400))

def generate_image(data):
    bg = Image.new("RGB", (800, 400), (20, 20, 20))
    draw = ImageDraw.Draw(bg)

    # Mapa
    map_img = crop_map(data["killer_coords"])
    bg.paste(map_img, (20, 0))

    # Broń
    if os.path.exists(WEAPON_ICON):
        weapon_icon = Image.open(WEAPON_ICON).convert("RGBA").resize((100, 100))
        bg.paste(weapon_icon, (680, 20), weapon_icon)

    # Tekst
    font_title = ImageFont.truetype(FONT_PATH, 28)
    font_info = ImageFont.truetype(FONT_PATH, 20)

    draw.text((440, 40), "DISCOVERY BOT – REPORT", font=font_title, fill=(255, 255, 255))
    draw.text((440, 100), f"☠️  {data['victim']} zginął z rąk {data['killer']}", font=font_info, fill=(220, 220, 220))
    draw.text((440, 140), f"🔪  Broń: {data['weapon']}", font=font_info, fill=(200, 200, 200))
    draw.text((440, 180), f"🕒  Czas: {data['time']}", font=font_info, fill=(180, 180, 180))

    # Zapisz obraz
    bg.save(OUTPUT_PATH)
    return OUTPUT_PATH

def send_to_discord(image_path):
    with open(image_path, "rb") as img_file:
        payload = {
            "content": "**Zgłoszenie śmierci**",
            "username": "Discovery Bot"
        }
        files = {"file": img_file}
        response = requests.post(WEBHOOK_URL, data=payload, files=files)
        if response.status_code == 204:
            print("✅ Wysłano obraz na Discord.")
        else:
            print("❌ Błąd wysyłania:", response.text)

# === WYKONANIE ===
if __name__ == "__main__":
    try:
        data = parse_log(LOG_PATH)
        image_path = generate_image(data)
        send_to_discord(image_path)
    except Exception as e:
        print("❌ Błąd:", e)
