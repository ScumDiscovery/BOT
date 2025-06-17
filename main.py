import os
import requests
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TILE_URL = "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}.png"
TILE_SIZE = 256
ZOOM = 6

# Example static weapon icon fallback (override below with dynamic)
STATIC_ICONS = {
    "BP_Weapon_AK47": "https://static.wikia.nocookie.net/scum/images/5/5b/AK-47.png",
}

# Map SCUM coordinates to tile grid (approximate)
def coords_to_tile(x, y):
    return int(x / 1000), int(y / 1000)

def get_tile(x, y):
    url = TILE_URL.format(z=ZOOM, x=x, y=y)
    try:
        r = requests.get(url)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"Failed to fetch tile {x},{y}: {e}")
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), color=(50, 50, 50))

def stitch_map(center_x, center_y):
    base = Image.new("RGB", (TILE_SIZE * 3, TILE_SIZE * 3))
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile = get_tile(center_x + dx, center_y + dy)
            base.paste(tile, ((dx + 1) * TILE_SIZE, (dy + 1) * TILE_SIZE))
    return base

def get_weapon_icon(weapon_id):
    # Dynamic fetch from SCUM wiki by weapon_id
    try:
        if weapon_id in STATIC_ICONS:
            url = STATIC_ICONS[weapon_id]
        else:
            url = f"https://scum.fandom.com/wiki/Special:FilePath/{weapon_id.replace('BP_Weapon_', '')}.png"
        r = requests.get(url)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        print(f"Could not fetch icon for {weapon_id}: {e}")
        return None

def create_kill_image(killer, victim, weapon_id, location):
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 32)

    tile_x, tile_y = coords_to_tile(*location)
    map_img = stitch_map(tile_x, tile_y).convert("RGBA")
    draw = ImageDraw.Draw(map_img)

    # Draw text
    text = f"{killer} killed {victim}"
    draw.rectangle((20, 20, 700, 80), fill=(0, 0, 0, 180))
    draw.text((30, 30), text, font=font, fill=(255, 255, 255, 255))

    # Weapon icon
    icon = get_weapon_icon(weapon_id)
    if icon:
        icon = icon.resize((64, 64))
        map_img.paste(icon, (740, 20), icon)

    output_path = "kill_webhook_output.png"
    map_img.save(output_path)
    return output_path

@app.route("/kill", methods=["POST"])
def kill():
    data = request.get_json()
    killer = data.get("killer")
    victim = data.get("victim")
    weapon = data.get("weapon")
    location = data.get("location")

    if not all([killer, victim, weapon, location]):
        return jsonify({"error": "Missing fields"}), 400

    img_path = create_kill_image(killer, victim, weapon, location)

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        with open(img_path, "rb") as f:
            files = {"file": f}
            r = requests.post(webhook_url, files=files)
            print("Discord response:", r.status_code)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
