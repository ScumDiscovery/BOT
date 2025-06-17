import os
import re
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

TILE_SIZE = 256
MAP_TILE_URL = "https://scum-map.com/api/maps/1/tiles/0/{x}/{y}.png"

# Czaszka – lokalnie lub URL
SKULL_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Skull_icon.svg/240px-Skull_icon.svg.png"

def fetch_tile(x, y):
    try:
        url = MAP_TILE_URL.format(x=x, y=y)
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Tile error {x},{y}: {e}")
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 255))

def fetch_icon(url, size=(48, 48)):
    try:
        response = requests.get(url)
        response.raise_for_status()
        icon = Image.open(BytesIO(response.content)).convert("RGBA")
        return icon.resize(size)
    except Exception as e:
        print(f"Icon fetch failed: {e}")
        return None

def map_coords_to_tile(x, y):
    """SCUM map is approx 6x6 km, tiles go from 0–7 on each axis"""
    px = int(x / TILE_SIZE)
    py = int(abs(y) / TILE_SIZE)
    return px, py

def generate_kill_image(killer, victim, weapon, distance, location):
    # Ustawiamy środek na zabójstwo
    x, y = location
    center_tile_x, center_tile_y = map_coords_to_tile(x, y)

    # Składamy mapę 3x3
    map_image = Image.new("RGBA", (TILE_SIZE * 3, TILE_SIZE * 3))
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile = fetch_tile(center_tile_x + dx, center_tile_y + dy)
            map_image.paste(tile, ((dx + 1) * TILE_SIZE, (dy + 1) * TILE_SIZE))

    # Przeliczenie pozycji czaszki
    offset_x = int(x % TILE_SIZE) + TILE_SIZE
    offset_y = int(abs(y % TILE_SIZE)) + TILE_SIZE

    skull = fetch_icon(SKULL_ICON_URL)
    if skull:
        map_image.paste(skull, (offset_x - 24, offset_y - 24), mask=skull)

    # Dodajemy tekst
    draw = ImageDraw.Draw(map_image)
    font = ImageFont.load_default()

    info = f"{killer} ➜ {victim}\n{weapon}\n📏 {distance:.1f} m"
    draw.text((10, 10), info, fill="red", font=font)

    output_path = "kill_output.png"
    map_image.save(output_path)
    return output_path

def send_to_discord(file_path, message):
    with open(file_path, "rb") as f:
        response = requests.post(
            WEBHOOK_URL,
            files={"file": (os.path.basename(file_path), f)},
            data={"content": message}
        )
    if response.status_code >= 400:
        print(f"Webhook error: {response.status_code} {response.text}")

@app.route("/", methods=["GET"])
def index():
    return "<h3>SCUM Killfeed Bot działa</h3>", 200

@app.route("/kill", methods=["POST"])
def kill():
    data = request.get_json()

    killer = data.get("Killer", {}).get("ProfileName", "Unknown")
    victim = data.get("Victim", {}).get("ProfileName", "Unknown")
    weapon_raw = data.get("Weapon", "Unknown Weapon")
    weapon = weapon_raw.split(" [")[0]  # np. "2H_Katana_C_..." → "2H_Katana_C_..."

    # Lokacja zabójcy
    loc = data.get("Killer", {}).get("ServerLocation", {})
    x = float(loc.get("X", 55000))
    y = float(loc.get("Y", 51000))  # Uwaga: SCUM ma oś Y ujemną

    # Próbujemy wydobyć dystans z logu, jeśli podano
    distance_match = re.search(r"Distance:\s*([\d\.]+)\s*m", weapon_raw)
    distance = float(distance_match.group(1)) if distance_match else 0.0

    image_path = generate_kill_image(killer, victim, weapon, distance, (x, y))
    message = f"💀 {killer} zabił {victim} ({distance:.1f} m) przy użyciu `{weapon}`"
    send_to_discord(image_path, message)

    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
