import os
import math
import requests
from PIL import Image, ImageDraw, ImageFont

def world_to_tile_coords(x, y, zoom=6):
    map_size = 600000  # SCUM map dimension (in cm)
    normalized_x = (x / map_size) % 1.0
    normalized_y = (0.5 - (y / map_size)) % 1.0
    n = 2 ** zoom
    xtile = normalized_x * n
    ytile = normalized_y * n
    return xtile, ytile

def fetch_map_tiles(center_xtile, center_ytile, zoom, tile_size=256):
    image = Image.new("RGB", (tile_size * 3, tile_size * 3))
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tx = int(center_xtile) + dx
            ty = int(center_ytile) + dy
            url = f"https://scum-map.com/tiles/{zoom}/{tx}/{ty}.png"
            try:
                response = requests.get(url)
                tile = Image.open(requests.compat.BytesIO(response.content))
                image.paste(tile, ((dx + 1) * tile_size, (dy + 1) * tile_size))
            except Exception as e:
                print(f"Failed to fetch tile {tx},{ty}: {e}")
    return image

def draw_marker_on_map(image, xtile, ytile, tile_size=256):
    draw = ImageDraw.Draw(image)
    offset_x = (xtile % 1.0) * tile_size + tile_size
    offset_y = (ytile % 1.0) * tile_size + tile_size
    draw.ellipse((offset_x - 10, offset_y - 10, offset_x + 10, offset_y + 10), fill="red", outline="white", width=2)

def add_text_overlay(image, killer, victim, weapon, distance):
    draw = ImageDraw.Draw(image)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(font_path):
        font_path = None
    font = ImageFont.truetype(font_path, 20) if font_path else None
    text = f"{killer} killed {victim} with {weapon}\nDistance: {distance:.2f} m"
    draw.text((10, 10), text, fill="white", font=font)

def generate_kill_webhook_image(log_data, output_path="kill_webhook_output.png"):
    victim_x = log_data['Victim']['ServerLocation']['X']
    victim_y = log_data['Victim']['ServerLocation']['Y']
    xtile, ytile = world_to_tile_coords(victim_x, victim_y)
    zoom = 6
    map_img = fetch_map_tiles(xtile, ytile, zoom)
    draw_marker_on_map(map_img, xtile, ytile)

    killer = log_data['Killer']['ProfileName']
    victim = log_data['Victim']['ProfileName']
    weapon = log_data['Weapon'].split()[0].replace("_", " ")
    distance = math.dist([
        log_data['Killer']['ServerLocation']['X'],
        log_data['Killer']['ServerLocation']['Y']
    ], [
        log_data['Victim']['ServerLocation']['X'],
        log_data['Victim']['ServerLocation']['Y']
    ])

    add_text_overlay(map_img, killer, victim, weapon, distance)
    map_img.save(output_path)
    print(f"Saved image to {output_path}")

# Example usage
log = {
    "Killer": {
        "ServerLocation": {"X": 525405.75, "Y": -192209.703125, "Z": 1195.30},
        "ProfileName": "Anu"
    },
    "Victim": {
        "ServerLocation": {"X": 525345.625, "Y": -192173.53125, "Z": 1195.31},
        "ProfileName": "Milo"
    },
    "Weapon": "2H_Katana_C_2147327617 [Melee]"
}

if __name__ == "__main__":
    generate_kill_webhook_image(log)
