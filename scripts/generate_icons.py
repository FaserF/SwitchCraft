
# Script to generate PWA icons from source logo
from PIL import Image
import os

source_path = "src/switchcraft/assets/switchcraft_logo.png"
assets_dir = "src/switchcraft/assets"

if os.path.exists(source_path):
    img = Image.open(source_path)
    # Generate 192x192
    img.resize((192, 192), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "icon-192.png"))
    # Generate 512x512
    img.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "icon-512.png"))
    # Generate apple-touch-icon (180x180 usually, or 192)
    img.resize((180, 180), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "apple-touch-icon.png"))
    print("Icons generated successfully.")
else:
    print(f"Source image not found at {source_path}")
