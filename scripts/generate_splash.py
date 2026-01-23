from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def generate_splash():
    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    logo_path = base_dir / "src" / "switchcraft" / "assets" / "switchcraft_logo.png"
    output_path = base_dir / "src" / "switchcraft" / "assets" / "splash.png"

    # Fonts (Windows standard)
    font_dir = Path("C:/Windows/Fonts")
    try:
        font_main = ImageFont.truetype(str(font_dir / "segoeuib.ttf"), 60) # Segoe UI Bold
        font_sub = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 24)   # Segoe UI
        font_hint = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 18)  # Segoe UI
    except Exception:
        # Fallback to default if fonts not found
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_hint = ImageFont.load_default()

    # Create background (Modern Dark Gray/Blue)
    width, height = 800, 500
    background_color = (30, 30, 40) # Dark Navy Gray
    img = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)

    # Load and scale logo
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        # Resize logo to fit well
        logo_size = 200
        logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)

        # Center logo horizontally, slightly above middle
        logo_x = (width - logo.width) // 2
        logo_y = height // 2 - logo.height - 40
        img.paste(logo, (logo_x, logo_y), logo)

    # Add Text
    # "SwitchCraft"
    text_main = "SwitchCraft"
    bbox_main = draw.textbbox((0, 0), text_main, font=font_main)
    w_main = bbox_main[2] - bbox_main[0]
    draw.text(((width - w_main) // 2, height // 2), text_main, font=font_main, fill=(255, 255, 255))

    # Tagline
    text_sub = "Your comprehensive packaging assistant"
    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_sub)
    w_sub = bbox_sub[2] - bbox_sub[0]
    draw.text(((width - w_sub) // 2, height // 2 + 80), text_sub, font=font_sub, fill=(200, 200, 200))

    # Hint
    text_hint = "Starting..."
    bbox_hint = draw.textbbox((0, 0), text_hint, font=font_hint)
    w_hint = bbox_hint[2] - bbox_hint[0]
    draw.text(((width - w_hint) // 2, height - 60), text_hint, font=font_hint, fill=(150, 150, 150))

    # Save
    img.save(output_path)
    print(f"Splash screen generated at: {output_path}")

if __name__ == "__main__":
    generate_splash()
