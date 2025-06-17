import os
import re
import json
import io
import requests
from flask import Flask, send_file
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

app = Flask(__name__)

# Ustawienia środowiska
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Map bounds (przybliżone na podstawie SCUM)
MAP_WIDTH = 2048
MAP_HEIGHT = 2048
MAP_X_MIN = 500000
MAP_X_MAX = 530000
MAP_Y_MIN = -195000
MAP_Y_MAX = -190000

FONT_PATH = "assets/Roboto-Bold.ttf"

def fetch_map_image():
    """Pobiera mapę z internetu"""
    url = "https://scum-map.com/static/media/full-map.2d9bd6d4.png"
    response = requests.get(url)
    img = Image.open(io.BytesIO(response.content)).convert("RGBA")
    return img.resize((MAP_WIDTH, MAP_HEIGHT))

def fetch_weapon_icon(weapon_name):
    """Pobiera ikonę broni z fandom wiki"""
    search_term = weapon_name.replace("_", " ")
    url = f"https://scum.fandom.com/wiki/{search_term}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    img_tag = soup.select_one(".infobox .image img")
    if img_tag and "src" in img_tag.attrs:
        img_url = "https:" + img_tag["src"]
        res = requests.get(img_url)
        icon = Image.open(io.BytesIO(res.content)).convert("RGBA")
        return icon.resize((64, 64))
    return None

def map_coords_to_pixels(x, y):
    """Konwertuje współrzędne świata gry na piksele na mapie"""
    px = int(((x - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN)) * MAP_WIDTH)
    py = int(((y - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN)) * MAP_HEIGHT)
    return px, MAP_HEIGHT - py

def generate_kill_image(killer, victim, weapon, distance, location):
    map_img = fetch_map_image()
    icon = fetch_weapon_icon(weapon) or Image.new("RGBA", (64, 64), (255, 0, 0, 128))

    draw = ImageDraw.Draw(map_img)
    px, py = map_coords_to_pixels(*location)
    map_img.paste(icon, (px - 32, py - 32), icon)

    font = ImageFont.truetype(FONT_PATH, 32)
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

    files = {"file": ("killmap.png", image_buf, "image/png")}
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)

    if response.status_code != 204:
        print("❌ Błąd wysyłki do Discorda:", response.status_code, response.text)
    else:
        print("✅ Wysłano grafikę na Discorda.")

@app.route("/test", methods=["GET"])
def test_log():
    log = """
2025.06.15-14.25.15: Died: Milo (76561199447029491), Killer: Anu (76561197992396189) Weapon: 2H_Katana_C_2147327617 [Melee] S:[KillerLoc : 525405.75, -192209.70, 1195.30 VictimLoc: 525345.62, -192173.53, 1195.31, Distance: 0.70 m]
2025.06.15-14.25.15: {"Killer":{"ServerLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"ClientLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"IsInGameEvent": false,"ProfileName": "Anu","UserId": "76561197992396189"},"Victim":{"ServerLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"ClientLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"IsInGameEvent": false,"ProfileName": "Milo","UserId": "76561199447029491"},"Weapon": "2H_Katana_C_2147327617 [Melee]","TimeOfDay": "06:17:04"}
""".strip()

    lines = log.splitlines()
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

    dist_match = re.search(r"Distance:\s*([\d\.]+)\s*m", lines[0])
    distance = float(dist_match.group(1)) if dist_match else 0.0

    image_buf = generate_kill_image(killer, victim, weapon, distance, (x, y))
    message = f"{killer} zabił {victim} ({weapon}) z {distance:.1f} m"
    send_to_discord(image_buf, message)

    image_buf.seek(0)
    return send_file(image_buf, mimetype="image/png")

@app.route("/")
def home():
    return "Serwer działa. Użyj /test aby wygenerować mapę."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
