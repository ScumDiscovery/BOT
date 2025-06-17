import os
import re
import io
import json
import requests
from flask import Flask, send_file
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

app = Flask(__name__)

# Ścieżki lokalne (do czcionki)
FONT_PATH = "assets/Roboto-Bold.ttf"

# Wymiary mapy (muszą być znane z https://scum-map.com/)
MAP_WIDTH = 2048
MAP_HEIGHT = 2048
MAP_X_MIN = 500000
MAP_X_MAX = 530000
MAP_Y_MIN = -195000
MAP_Y_MAX = -190000

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def map_coords_to_pixels(x, y):
    px = int(((x - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN)) * MAP_WIDTH)
    py = int(((y - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN)) * MAP_HEIGHT)
    return px, MAP_HEIGHT - py

def download_map_image():
    url = "https://scum-map.com/map.jpg"
    response = requests.get(url)
    image = Image.open(io.BytesIO(response.content)).convert("RGBA")
    return image.resize((MAP_WIDTH, MAP_HEIGHT))

def find_weapon_image(weapon_name):
    page = requests.get("https://scum.fandom.com/wiki/Item_IDs")
    soup = BeautifulSoup(page.content, "html.parser")
    images = soup.select("img")
    for img in images:
        if weapon_name.lower() in img.get("alt", "").lower():
            src = img.get("src")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://scum.fandom.com" + src
                return src
    return None

def generate_kill_image(killer, victim, weapon, distance, location, weapon_image_url=None):
    map_img = download_map_image()

    draw = ImageDraw.Draw(map_img)
    font = ImageFont.truetype(FONT_PATH, 32)

    # Weapon image
    if weapon_image_url:
        try:
            icon_resp = requests.get(weapon_image_url)
            icon = Image.open(io.BytesIO(icon_resp.content)).convert("RGBA")
            icon = icon.resize((64, 64))
            map_img.paste(icon, (20, 100), icon)
        except Exception as e:
            print("❗ Nie udało się pobrać ikonki broni:", e)

    # Skull marker
    px, py = map_coords_to_pixels(*location)
    draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill=(255, 0, 0, 255))

    text = f"{killer} → {victim}\n{weapon} ({distance:.1f} m)"
    draw.text((20, 20), text, font=font, fill=(255, 255, 255, 255))

    buf = io.BytesIO()
    map_img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def send_to_discord(image_buf, message):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Brak DISCORD_WEBHOOK_URL — pomijam wysyłkę.")
        return

    files = {
        "file": ("killmap.png", image_buf, "image/png")
    }
    data = {
        "content": message
    }
    response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
    if response.status_code != 204:
        print("❌ Błąd wysyłki:", response.status_code, response.text)
    else:
        print("✅ Wysłano grafikę na Discorda.")

@app.route("/test", methods=["GET"])
def test_manual_log():
    log_text = """
2025.06.15-14.01.01: Game version: 0.9.694.94612
2025.06.15-14.25.15: Died: Milo (76561199447029491), Killer: Anu (76561197992396189) Weapon: 2H_Katana_C_2147327617 [Melee] S:[KillerLoc : 525405.75, -192209.70, 1195.30 VictimLoc: 525345.62, -192173.53, 1195.31, Distance: 0.70 m]
2025.06.15-14.25.15: {"Killer":{"ServerLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"ClientLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"IsInGameEvent": false,"ProfileName": "Anu","UserId": "76561197992396189","HasImmortality": false},"Victim":{"ServerLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"ClientLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"IsInGameEvent": false,"ProfileName": "Milo","UserId": "76561199447029491"},"Weapon": "2H_Katana_C_2147327617 [Melee]","TimeOfDay": "06:17:04"}
""".strip()

    lines = log_text.splitlines()
    json_line = [l for l in lines if l.strip().endswith("}")]
    if not json_line:
        return {"error": "Nie znaleziono danych JSON"}, 400

    log_data = json.loads(json_line[0].split(":", 1)[-1].strip())

    killer = log_data["Killer"]["ProfileName"]
    victim = log_data["Victim"]["ProfileName"]
    weapon_full = log_data["Weapon"]
    weapon = weapon_full.split(" [")[0]
    x = float(log_data["Killer"]["ServerLocation"]["X"])
    y = float(log_data["Killer"]["ServerLocation"]["Y"])

    dist_match = re.search(r"Distance:\s*([\d\.]+)\s*m", lines[1])
    distance = float(dist_match.group(1)) if dist_match else 0.0

    weapon_img_url = find_weapon_image(weapon)
    image_buf = generate_kill_image(killer, victim, weapon, distance, (x, y), weapon_img_url)
    message = f"{killer} zabił {victim} ({weapon}) z dystansu {distance:.1f} m"
    send_to_discord(image_buf, message)

    return "✅ Obraz wysłany na Discorda."

@app.route("/")
def home():
    return "Serwer działa. Użyj /test aby wygenerować mapę i wysłać ją na Discorda."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
