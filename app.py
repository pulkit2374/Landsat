import os
import json
import hashlib
import base64
from flask import Flask, jsonify, send_file, abort
from PIL import Image
from io import BytesIO
import random

LETTER_DB_DIR = "letter_db"
PATCH_SIZE = 128

app = Flask(__name__)

# Load metadata
metadata_path = os.path.join(LETTER_DB_DIR, "metadata.json")
if not os.path.exists(metadata_path):
    raise FileNotFoundError("metadata.json missing in letter_db.")
with open(metadata_path, "r") as f:
    LETTER_META = json.load(f)

# Load all letter image variants
LETTER_VARIANTS = {}
for ch, variants in LETTER_META.items():
    loaded = []
    for v in variants:
        path = os.path.join(LETTER_DB_DIR, v["file"])
        if os.path.exists(path):
            img = Image.open(path).convert("RGB")
            loaded.append({
                "image": img,
                "variant": v["variant"],
                "file": v["file"],
                "lat": v["lat"],
                "lon": v["lon"],
                "scene_id": v["scene_id"]
            })
    if loaded:
        LETTER_VARIANTS[ch] = loaded
        # print(f"Loaded variants for {ch}: {[v['file'] for v in loaded]}")

def deterministic_choice(name, index, variants):
    seed = f"{name}_{index}"
    hashval = hashlib.sha256(seed.encode()).hexdigest()
    return variants[int(hashval, 16) % len(variants)]

@app.route("/")
def index():
    return send_file("index.html")

# 
@app.route("/generate_name/<name>")
def generate_name(name):
    name = name.upper()
    random.letter_images = []
    letters_meta = []

    for i, ch in enumerate(name):
        if ch == " ":
            random.letter_images.append(None)
            letters_meta.append({"character": " ", "variant": None})
            continue

        if ch not in LETTER_VARIANTS:
            continue

        # Pick a random variant instead of deterministic
        chosen = random.choice(LETTER_VARIANTS[ch])
        patch = chosen["image"].copy()
        random.letter_images.append(patch)
        letters_meta.append({
            "character": ch,
            "variant": chosen["variant"],
            "file": chosen["file"],
            "lat": chosen["lat"],
            "lon": chosen["lon"],
            "scene_id": chosen["scene_id"]
        })

    if not any(random.letter_images):
        return abort(400, "No valid letters found.")

    buf = BytesIO()
    composite = Image.new("RGB", (1, 1))  # Not actually used
    composite.save(buf, format="PNG")  # Dummy
    buf.seek(0)
    img_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    return jsonify({
        "image": img_data_url,
        "letters": letters_meta
    })

from flask import send_from_directory

@app.route('/letter_db/<path:filename>')
def serve_letter_image(filename):
    return send_from_directory('letter_db', filename)

if __name__ == "__main__":
    app.run(debug=True)


