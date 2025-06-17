import os
import re
import requests
from PIL import Image, ImageDraw, ImageFont

# 🔧 KONFIGURACJA
WEBHOOK_URL = "https://discord.com/api/webhooks/1383407890663997450/hr2zvr2PjO20IDLIk5nZd8juZDxG9kYkOOZ0c2_sqzGtuXra8Dz-HbhtnhtF3Yb0Hsgi"
MAP_IMAGE_PATH = "assets/map_full.jpg"
WEAPON_ICONS = {
    "2H_Katana": "assets/katana.png"
}
FONT_PATH = "assets/font.ttf"
LOG_PATH = "logs/scum_log.txt"
OUTPUT_PATH = "output/final.png"

# 🔍 PARSER LOGÓW
def parse_log(log_path):
    with open(log_path, "r") as f:
        content = f.read()

    match = re.search(
        r"Died: (.+?) \((\d+)\), Killer: (.+?) \((\d+)\) Weapon: (.+?) \[.*?\] S:\[KillerLoc : ([\d\.-]+), ([\d\.-]+), .*? VictimLoc: ([\d\.-]+), ([\d\.-]+)",
        content
    )

    if not match:
        raise ValueError("Nie znaleziono poprawnych danych w logu.")

    victim, victim_id, killer, killer_id, weapon_str, killer_x, killer_y, victim_x, victim_y = match.groups()

    return {
        "killer": killer,
        "killer_id": killer_id,
        "victim": victim,
        "victim_id": victim_id,
        "weapon": weapon_str.split("_C_")[0],
        "killer_coords": (float(killer_x), float(killer_y)),
        "victim_coords": (float(victim_x), float(victim_y))
    }

# 🗺️ WYCIĘCIE FRAGMENTU MAPY
def crop_map(coords, size=300):
    map_img = Image.open(MAP_IMAGE_PATH)
    x, y = coords

    # Przeliczenie koordynatów gry na piksele obrazu (zakładamy proporcje mapy np. 6x6 km = 6000x6000 px)
    map_width, map_height = map_img.size
    px = int(x / 1000000 * map_width)
    py = int((abs(y)) / 1000000 * map_height)

    # Wycinamy fragment wokół koordynatów
    box = (px - size // 2, py - size // 2, px + size // 2, py + size // 2)
    cropped = map_img.crop(box)
    return cropped.resize((800, 800))

# 🎨 GENERATOR GRAFIKI
def create_image(data):
    base = crop_map(data["killer_coords"])
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(FONT_PATH, 40)

    # Tekst
    draw.text((30, 20), f"{data['killer']} zabił {data['victim']}", fill="white", font=font)
    draw.text((30, 80), f"Broń: {data['weapon']}", fill="orange", font=font)

    # Ikona broni
    weapon_key = next((key for key in WEAPON_ICONS if key in data["weapon"]), None)
    if weapon_key:
        weapon_img = Image.open(WEAPON_ICONS[weapon_key]).convert("RGBA").resize((128, 128))
        base.paste(weapon_img, (base.width - 150, 30), weapon_img)

    base.save(OUTPUT_PATH)
    return OUTPUT_PATH

# 📤 WYŚLIJ NA DISCORD
def send_to_discord(image_path):
    with open(image_path, 'rb') as img:
        files = {'file': (os.path.basename(image_path), img, 'image/png')}
        response = requests.post(WEBHOOK_URL, files=files)

    if response.status_code == 204:
        print("✅ Wysłano na Discord!")
    else:
        print(f"❌ Błąd wysyłania: {response.status_code}")

# ▶️ GŁÓWNE WYWOŁANIE
if __name__ == "__main__":
    try:
        data = parse_log(LOG_PATH)
        print("✅ Zparsowano dane:", data)
        img_path = create_image(data)
        send_to_discord(img_path)
    except Exception as e:
        print("❌ Błąd:", str(e))
