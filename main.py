import os
import json
import requests
from PIL import Image, ImageDraw, ImageFont
from config import WEBHOOK_URL, MAP_PATH, BASE_TEMPLATE_PATH, WEAPON_ICONS_PATH

def parse_log(log_text):
    lines = log_text.splitlines()
    for line in lines:
        if "Died:" in line and "KillerLoc" in line:
            coords_start = line.find("KillerLoc :") + len("KillerLoc :")
            coords_end = line.find("VictimLoc")
            killer_coords = line[coords_start:coords_end].strip().strip(',').split(',')
            killer_x = float(killer_coords[0])
            killer_y = float(killer_coords[1])
        if line.startswith("{\"Killer\""):
            data = json.loads(line)
            return {
                "killer": data["Killer"]["ProfileName"],
                "victim": data["Victim"]["ProfileName"],
                "weapon": data["Weapon"].split(' ')[0],
                "location": (killer_x, killer_y),
                "time": data["TimeOfDay"]
            }
    return None

def crop_map(location, size=400):
    x, y = location
    full_map = Image.open(MAP_PATH)
    map_width, map_height = full_map.size
    game_map_width = 600000
    game_map_height = 600000
    px = int((x / game_map_width) * map_width)
    py = int((abs(y) / game_map_height) * map_height)
    left = max(px - size // 2, 0)
    top = max(py - size // 2, 0)
    right = min(px + size // 2, map_width)
    bottom = min(py + size // 2, map_height)
    return full_map.crop((left, top, right, bottom)).resize((size, size))

def generate_image(data):
    base = Image.open(BASE_TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(base)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 24)

    cropped_map = crop_map(data["location"], size=300)
    base.paste(cropped_map, (30, 30))

    weapon_icon_path = os.path.join(WEAPON_ICONS_PATH, "katana.png")
    if os.path.exists(weapon_icon_path):
        weapon_icon = Image.open(weapon_icon_path).convert("RGBA").resize((64, 64))
        base.paste(weapon_icon, (360, 30), weapon_icon)

    draw.text((30, 350), f"Killer: {data['killer']}", font=font, fill="white")
    draw.text((30, 390), f"Victim: {data['victim']}", font=font, fill="white")
    draw.text((30, 430), f"Weapon: {data['weapon']}", font=font, fill="white")
    draw.text((30, 470), f"Time: {data['time']}", font=font, fill="white")

    out_path = "kill_report.png"
    base.save(out_path)
    return out_path

def send_to_discord(image_path):
    with open(image_path, "rb") as f:
        files = {"file": (image_path, f)}
        data = {"content": "🎯 Nowe zabójstwo zgłoszone przez Discovery Bot"}
        response = requests.post(WEBHOOK_URL, data=data, files=files)
        if response.status_code != 204:
            print("Błąd wysyłania do Discord:", response.status_code, response.text)

if __name__ == "__main__":
    with open("log.txt", "r") as file:
        log_text = file.read()

    parsed = parse_log(log_text)
    if parsed:
        image = generate_image(parsed)
        send_to_discord(image)
    else:
        print("Nie znaleziono danych w logu.")
