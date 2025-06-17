import os
import re
import json
import io
import math
import requests
from flask import Flask, send_file, request
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

app = Flask(__name__)

# Config
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
FONT_PATH = "assets/Roboto-Bold.ttf"
TILE_SIZE = 256  # rozmiar kafla z mapy

# Zakres koordynat, dostosuj do swojej mapy
MAP_X_MIN, MAP_X_MAX = 500000, 530000
MAP_Y_MIN, MAP_Y_MAX = -195000, -190000
MAP_ZOOM = 5  # dostosuj w zależności od poziomu szczegółów

def map_coords_to_pixels(x, y, map_img):
    width, height = map_img.size
    px = ((x - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN)) * width
    py = ((y - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN)) * height
    return int(px), int(height - py)

def fetch_map_for_location(x, y):
    """Pobiera 3x3 kafle centrowane na lokalizacji (x, y)"""
    # Przekształć na tile coords (przykład – zależy od implementacji Serwera)
    def world_to_tile(wx, wy, zoom):
        tx = int((wx - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN) * (2**zoom))
        ty = int((wy - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN) * (2**zoom))
        return tx, ty

    center_tx, center_ty = world_to_tile(x, y, MAP_ZOOM)
    full = Image.new("RGBA", (TILE_SIZE*3, TILE_SIZE*3))

    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tx, ty = center_tx+dx, center_ty+dy
            url = f"https://scum-map.com/tiles/{MAP_ZOOM}/{tx}/{ty}.png"
            resp = requests.get(url)
            if resp.status_code == 200:
                tile = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            else:
                tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0,0,0,0))
            full.paste(tile, ((dx+1)*TILE_SIZE, (dy+1)*TILE_SIZE))
    return full

def fetch_weapon_icon(weapon_id):
    """Pobiera z fandom np. 2H_Katana_C_2147327617"""
    url = "https://scum.fandom.com/wiki/Item_IDs/Weapons"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    img = soup.find("img", alt=lambda a: a and weapon_id in a)
    if img:
        icon_url = img.get("src")
        resp2 = requests.get(icon_url)
        return Image.open(io.BytesIO(resp2.content)).convert("RGBA").resize((64,64))
    else:
        return Image.new("RGBA", (64,64), (255,0,0,128))  # fallback

def generate_kill_image(killer, victim, weapon_id, distance, location):
    x, y = location
    map_img = fetch_map_for_location(x, y)
    weapon_icon = fetch_weapon_icon(weapon_id)
    draw = ImageDraw.Draw(map_img)
    px, py = map_coords_to_pixels(x, y, map_img)
    map_img.paste(weapon_icon, (px-32, py-32), weapon_icon)

    font = ImageFont.truetype(FONT_PATH, 32)
    txt = f"{killer} → {victim}\n{weapon_id} ({distance:.1f} m)"
    draw.text((20,20), txt, font=font, fill=(255,255,255,255))

    buf = io.BytesIO()
    map_img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def send_to_discord(image_buf, message):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ No webhook URL.")
        return
    files = {"file": ("kill.png", image_buf, "image/png")}
    data = {"content": message}
    resp = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
    if resp.status_code != 204:
        print("📛 Discord send error:", resp.status_code, resp.text)

@app.route("/kill", methods=["POST"])
def kill_endpoint():
    data = request.json or {}
    for key in ("killer","victim","weapon","distance","x","y"):
        if key not in data:
            return {"error": f"Missing '{key}'"}, 400

    killer = data["killer"]
    victim = data["victim"]
    weapon = data["weapon"]
    distance = float(data["distance"])
    x, y = float(data["x"]), float(data["y"])

    img_buf = generate_kill_image(killer, victim, weapon, distance, (x,y))
    send_to_discord(img_buf, f"{killer} killed {victim} with {weapon} ({distance:.1f} m)")
    img_buf.seek(0)
    return send_file(img_buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
