import os
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Ścieżki do zasobów
MAP_PATH = "assets/map.png"
PIN_PATH = "assets/pin.png"
FONT_PATH = "assets/font.ttf"

# Rozmiar mapy SCUM i jej offsety (na bazie https://scum-map.com)
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
WORLD_MIN_X = 0
WORLD_MAX_X = 600_000
WORLD_MIN_Y = -300_000
WORLD_MAX_Y = 0

def world_to_image_coords(x, y):
    norm_x = (x - WORLD_MIN_X) / (WORLD_MAX_X - WORLD_MIN_X)
    norm_y = (y - WORLD_MIN_Y) / (WORLD_MAX_Y - WORLD_MIN_Y)
    pixel_x = int(norm_x * MAP_WIDTH)
    pixel_y = int(norm_y * MAP_HEIGHT)
    return pixel_x, pixel_y

def draw_overlay(victim_name, killer_name, weapon_name, distance, pos_x, pos_y):
    base = Image.open(MAP_PATH).convert("RGBA")
    pin = Image.open(PIN_PATH).convert("RGBA").resize((48, 48))

    pin_x, pin_y = world_to_image_coords(pos_x, pos_y)
    base.paste(pin, (pin_x - 24, pin_y - 48), pin)

    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(FONT_PATH, 32)

    text = f"{killer_name} ➤ {victim_name}\n🔪 {weapon_name} | 📏 {distance:.1f}m"
    draw.text((pin_x + 20, pin_y - 40), text, font=font, fill=(255, 255, 255, 255))

    output_path = "output/kill_overlay.png"
    os.makedirs("output", exist_ok=True)
    base.save(output_path)

    return output_path

@app.route("/webhook-image", methods=["POST"])
def webhook_image():
    data = request.json

    victim_name = data["Victim"]["ProfileName"]
    killer_name = data["Killer"]["ProfileName"]
    weapon_str = data["Weapon"]
    distance = float(data.get("Distance", 0))
    pos_x = float(data["Victim"]["ServerLocation"]["X"])
    pos_y = float(data["Victim"]["ServerLocation"]["Y"])

    # Wyodrębnij tylko nazwę broni
    weapon_clean = weapon_str.split()[0].replace("_", " ")

    image_path = draw_overlay(victim_name, killer_name, weapon_clean, distance, pos_x, pos_y)
    return send_file(image_path, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
