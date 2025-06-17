import os
import re
import json
import io
from flask import Flask, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

FONT_PATH = "assets/Roboto-Bold.ttf"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Zakres mapy (dostosuj do własnych danych)
MAP_WIDTH = 2048
MAP_HEIGHT = 2048
MAP_X_MIN = 500000
MAP_X_MAX = 530000
MAP_Y_MIN = -195000
MAP_Y_MAX = -190000

def map_coords_to_pixels(x, y):
    px = int(((x - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN)) * MAP_WIDTH)
    py = int(((y - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN)) * MAP_HEIGHT)
    return px, MAP_HEIGHT - py

def download_map_image():
    # Pobierz mapę z https://scum-map.com/
    url = "https://scum-map.com/images/fullmap.jpg"
    response = requests.get(url)
    return Image.open(io.BytesIO(response.content)).convert("RGBA")

def get_weapon_icon_url(weapon_id):
    # Wejdź na stronę z ID broni i znajdź ikonę odpowiadającą broni
    url = "https://scum.fandom.com/wiki/Item_IDs"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Przeszukujemy komórki tabeli po fragmencie ID
    cells = soup.select("table tr td")
    for td in cells:
        if weapon_id in td.text:
            img_tag = td.find_previous("img")
            if img_tag and "src" in img_tag.attrs:
                return "https://scum.fandom.com" + img_tag["src"]
    return None

def generate_kill_image(killer, victim, weapon, weapon_id, distance, location):
    map_img = download_map_image()

    draw = ImageDraw.Draw(map_img)
    px, py = map_coords_to_pixels(*location)

    # Ikona broni
    icon_url = get_weapon_icon_url(weapon_id)
    if icon_url:
        try:
            icon_resp = requests.get(icon_url)
            weapon_icon = Image.open(io.BytesIO(icon_resp.content)).convert("RGBA")
            weapon_icon = weapon_icon.resize((64, 64))
            map_img.paste(weapon_icon, (px - 32, py - 32), weapon_icon)
        except:
            print("❌ Nie udało się pobrać ikony broni.")
    else:
        print(f"❌ Nie znaleziono ikony broni dla {weapon_id}")

    # Tekst
    font = ImageFont.truetype(FONT_PATH, 32)
    text = f"{killer} → {victim}\n{weapon} ({distance:.1f} m)"
    draw.text((20, 20), text, font=font, fill=(255, 255, 255, 255))

    buf = io.BytesIO()
    map_img.save(buf, format="PNG")
    buf.seek(0)
    return buf

@app.route("/test", methods=["GET"])
def test_manual_log():
    log_utf16le = """
2025.06.15-14.01.01: Game version: 0.9.694.94612
2025.06.15-14.25.15: Died: Milo (76561199447029491), Killer: Anu (76561197992396189) Weapon: 2H_Katana_C_2147327617 [Melee] S:[KillerLoc : 525405.75, -192209.70, 1195.30 VictimLoc: 525345.62, -192173.53, 1195.31, Distance: 0.70 m]
2025.06.15-14.25.15: {"Killer":{"ServerLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"ClientLocation":{"X": 525405.75,"Y": -192209.703125,"Z": 1195.2999267578125},"IsInGameEvent": false,"ProfileName": "Anu","UserId": "76561197992396189","HasImmortality": false},"Victim":{"ServerLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"ClientLocation":{"X": 525345.625,"Y": -192173.53125,"Z": 1195.3099365234375},"IsInGameEvent": false,"ProfileName": "Milo","UserId": "76561199447029491"},"Weapon": "2H_Katana_C_2147327617 [Melee]","TimeOfDay": "06:17:04"}
""".strip()

    lines = log_utf16le.splitlines()
    json_line = [l for l in lines if l.strip().endswith("}")]
    if not json_line:
        return {"error": "Nie znaleziono danych JSON"}, 400

    log_data = json.loads(json_line[0].split(":", 1)[-1].strip())

    killer = log_data["Killer"]["ProfileName"]
    victim = log_data["Victim"]["ProfileName"]
    weapon_full = log_data["Weapon"]
    weapon = weapon_full.split(" [")[0]
    weapon_id = weapon_full.split("_")[-1].split(" ")[0]

    x = float(log_data["Killer"]["ServerLocation"]["X"])
    y = float(log_data["Killer"]["ServerLocation"]["Y"])

    dist_match = re.search(r"Distance:\s*([\d\.]+)\s*m", lines[1])
    distance = float(dist_match.group(1)) if dist_match else 0.0

    image_buf = generate_kill_image(killer, victim, weapon, weapon_id, distance, (x, y))

    return send_file(image_buf, mimetype="image/png")

@app.route("/")
def hello():
    return "Serwer działa. Użyj /test aby wygenerować mapę."
