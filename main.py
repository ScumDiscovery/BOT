import io
import requests
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request

# Flask app
app = Flask(__name__)

# Webhook Discorda
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1383407890663997450/hr2zvr2PjO20IDLIk5nZd8juZDxG9kYkOOZ0c2_sqzGtuXra8Dz-HbhtnhtF3Yb0Hsgi"

# Stałe
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
GAME_WORLD_SIZE = 16  # 16x16 km mapa SCUM

def parse_log_entry(log_line):
    """
    Parsuje dane z loga SCUM:
    - zabójca
    - ofiara
    - broń
    - współrzędne X, Y
    """
    try:
        parts = log_line.split("killed")
        killer_info = parts[0].split("]")[-2].split("[")[0].strip()
        victim_info = parts[1].split("with")[0].strip()
        weapon = parts[1].split("with")[1].split("at")[0].strip()
        coords_str = parts[1].split("at")[1].strip()
        x = float(coords_str.split("X=")[1].split(",")[0])
        y = float(coords_str.split("Y=")[1].split(",")[0])
        return killer_info, victim_info, weapon, x, y
    except Exception as e:
        print(f"Błąd parsowania loga: {e}")
        return None, None, None, None, None

def world_to_map(x, y):
    scale = MAP_WIDTH / (GAME_WORLD_SIZE * 1000.0)
    return int(x * scale), int((GAME_WORLD_SIZE * 1000.0 - y) * scale)

def generate_image(x, y, killer, victim, weapon):
    base_map = Image.open("assets/scum_map.png").convert("RGBA")
    draw = ImageDraw.Draw(base_map)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # może wymagać zmiany lokalnie
    try:
        font = ImageFont.truetype(font_path, 40)
    except:
        font = ImageFont.load_default()

    # Pozycja punktu
    map_x, map_y = world_to_map(x, y)
    radius = 12
    draw.ellipse((map_x - radius, map_y - radius, map_x + radius, map_y + radius), fill=(255, 0, 0, 255), outline=(0, 0, 0))

    # Tekst
    text = f"{killer} zabił {victim} przy użyciu {weapon}"
    draw.text((50, 50), text, fill="white", font=font)

    # Zapis do bufora
    output = io.BytesIO()
    base_map.save(output, format="PNG")
    output.seek(0)
    return output

def send_to_discord(image_bytes, text):
    files = {
        "file": ("map.png", image_bytes, "image/png")
    }
    data = {
        "content": text
    }
    response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
    print("Status:", response.status_code)
    return response.status_code == 204 or response.status_code == 200

@app.route("/log", methods=["POST"])
def handle_log():
    data = request.json
    log_line = data.get("log")

    if not log_line:
        return {"error": "Brak loga"}, 400

    killer, victim, weapon, x, y = parse_log_entry(log_line)

    if None in (killer, victim, weapon, x, y):
        return {"error": "Nieprawidłowe dane loga"}, 400

    image = generate_image(x, y, killer, victim, weapon)
    content = f"☠️ {killer} zabił {victim} przy użyciu `{weapon}` na współrzędnych **X={int(x)}, Y={int(y)}**"

    send_to_discord(image, content)
    return {"status": "OK"}, 200

if __name__ == "__main__":
    app.run(debug=True)
