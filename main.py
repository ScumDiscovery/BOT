import os
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
WEAPON_ICON_URL_TEMPLATE = "https://static.wikia.nocookie.net/scum_gamepedia/images/{hash}.png"

# Tymczasowy fallback – docelowo można zbudować mapę ID → hash
WEAPON_ICON_OVERRIDES = {
    "BP_Weapon_AK47": "f/f0/AK-47_Icon.png",
    "BP_Weapon_M1": "3/3a/M1_Garand_Icon.png",
    "BP_Weapon_Deagle50": "b/bc/Deagle_Icon.png",
}

def fetch_tile(x, y):
    try:
        url = MAP_TILE_URL.format(x=x, y=y)
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to fetch tile {x},{y}: {e}")
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))

def get_weapon_icon(weapon_id):
    if weapon_id in WEAPON_ICON_OVERRIDES:
        hash = WEAPON_ICON_OVERRIDES[weapon_id]
        url = f"https://static.wikia.nocookie.net/scum_gamepedia/images/{hash}/revision/latest"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            print(f"Failed to load weapon icon for {weapon_id}: {e}")
    return None

def generate_kill_image(killer, victim, weapon_id, location):
    map_image = Image.new("RGBA", (TILE_SIZE * 3, TILE_SIZE * 3))
    base_x, base_y = int(location[0] / TILE_SIZE), int(location[1] / TILE_SIZE)

    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile_x = base_x + dx
            tile_y = base_y + dy
            tile = fetch_tile(tile_x, tile_y)
            map_image.paste(tile, ((dx + 1) * TILE_SIZE, (dy + 1) * TILE_SIZE))

    draw = ImageDraw.Draw(map_image)
    font = ImageFont.load_default()

    draw.text((10, 10), f"{killer} killed {victim}", fill="red", font=font)

    icon = get_weapon_icon(weapon_id)
    if icon:
        icon = icon.resize((64, 64))
        map_image.paste(icon, (10, 40), mask=icon)

    output_path = "kill_webhook_output.png"
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
        print(f"Discord webhook failed: {response.status_code} {response.text}")

@app.route("/", methods=["GET"])
def index():
    return "<h2>SCUM Killfeed Bot działa 🚀</h2>", 200

@app.route("/kill", methods=["POST"])
def kill():
    data = request.get_json()
    killer = data.get("killer", "Unknown Killer")
    victim = data.get("victim", "Unknown Victim")
    weapon_id = data.get("weapon", "UnknownWeapon")
    location = data.get("location", [55000, 51000])

    image_path = generate_kill_image(killer, victim, weapon_id, location)
    message = f"💀 {killer} zabił {victim} za pomocą `{weapon_id}`"
    send_to_discord(image_path, message)

    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
