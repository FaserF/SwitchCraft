from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import argparse
import re

def generate_splash(version=None, output_path=None):
    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    logo_path = base_dir / "src" / "switchcraft" / "assets" / "switchcraft_logo.png"

    if output_path:
        target_path = Path(output_path)
    else:
        target_path = base_dir / "src" / "switchcraft" / "assets" / "splash.png"

    # Ensure directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Fonts (Windows standard)
    font_dir = Path("C:/Windows/Fonts")
    try:
        # Reduced font sizes by 20%
        font_main = ImageFont.truetype(str(font_dir / "segoeuib.ttf"), 48) # Reduced from 60
        font_sub = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 18)   # Reduced from 22
        font_hint = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 13)  # Reduced from 16
        font_ver = ImageFont.truetype(str(font_dir / "consola.ttf"), 11)   # Reduced from 14
    except Exception:
        # Fallback to default if fonts not found
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_hint = ImageFont.load_default()
        font_ver = ImageFont.load_default()

    # Create background (Modern Dark Gray/Blue)
    # Reduced image dimensions by 20%
    width, height = 640, 400 # Reduced from 800, 500
    background_color = (30, 30, 40) # Dark Navy Gray
    img = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)

    # Load and scale logo
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        # Resize logo to fit well (Reduced from 200 to 160)
        logo_size = 160
        logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)

        # Center logo horizontally, slightly above middle
        logo_x = (width - logo.width) // 2
        logo_y = height // 2 - logo.height - 40 # Reduced offset
        img.paste(logo, (logo_x, logo_y), logo)

    # Add Text
    # "SwitchCraft"
    text_main = "SwitchCraft"
    bbox_main = draw.textbbox((0, 0), text_main, font=font_main)
    w_main = bbox_main[2] - bbox_main[0]
    draw.text(((width - w_main) // 2, height // 2 - 10), text_main, font=font_main, fill=(255, 255, 255))

    # Tagline
    text_sub = "The Ultimate Packaging Suite for IT Professionals"
    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_sub)
    w_sub = bbox_sub[2] - bbox_sub[0]
    draw.text(((width - w_sub) // 2, height // 2 + 55), text_sub, font=font_sub, fill=(200, 200, 200))

    # Hint
    text_hint = "Starting..."
    bbox_hint = draw.textbbox((0, 0), text_hint, font=font_hint)
    w_hint = bbox_hint[2] - bbox_hint[0]
    draw.text(((width - w_hint) // 2, height - 40), text_hint, font=font_hint, fill=(150, 150, 150))

    # Footer
    text_footer = "Brought to you by FaserF"
    bbox_footer = draw.textbbox((0, 0), text_footer, font=font_hint)
    w_footer = bbox_footer[2] - bbox_footer[0]
    draw.text((width - w_footer - 15, height - 25), text_footer, font=font_hint, fill=(100, 100, 100))

    # Version (if provided) - Bottom Left
    if version:
        text_ver = f"{version}"
        draw.text((15, height - 25), text_ver, font=font_ver, fill=(100, 100, 100))

        # Check for Beta/Dev/Alpha and add banner
        v_lower = version.lower()
        banner_text = ""
        banner_color = (0, 0, 0)

        # Improved matching logic
        if "dev" in v_lower or "alpha" in v_lower:
            banner_text = "DEV BUILD"
            banner_color = (255, 50, 50) # Red
        elif "beta" in v_lower or "rc" in v_lower or re.search(r'b\d+$', v_lower):
            # Matches 'beta', 'rc', or 'b1', 'b2' etc ending
            banner_text = "BETA RELEASE"
            banner_color = (255, 140, 0) # Dark Orange

        if banner_text:
            # Create a simple banner in top right
            # Font for banner
            try:
                 font_banner = ImageFont.truetype(str(font_dir / "segoeuib.ttf"), 20)
            except Exception:
                 font_banner = ImageFont.load_default()

            bbox_banner = draw.textbbox((0, 0), banner_text, font=font_banner)
            w_banner = bbox_banner[2] - bbox_banner[0]
            h_banner = bbox_banner[3] - bbox_banner[1]

            # Position: Top Right with some padding
            margin = 20
            x_banner = width - w_banner - margin
            y_banner = margin

            # Draw text
            draw.text((x_banner, y_banner), banner_text, font=font_banner, fill=banner_color)

            # Add a small line/box under/around it
            padding = 5
            draw.rectangle(
                (x_banner - padding, y_banner - padding, x_banner + w_banner + padding, y_banner + h_banner + padding + 5),
                outline=banner_color,
                width=2
            )

    # Save
    # Only backup if no custom output path is specified (overwriting source logic)
    if not output_path:
        backup_path = target_path.with_suffix(".png.bak")
        if target_path.exists() and not backup_path.exists():
            import shutil
            shutil.copy2(target_path, backup_path)
            print(f"Backed up original splash to: {backup_path}")

    img.save(target_path)
    print(f"Splash screen generated at: {target_path}")

def restore_splash():
    base_dir = Path(__file__).resolve().parent.parent
    splash_path = base_dir / "src" / "switchcraft" / "assets" / "splash.png"
    backup_path = splash_path.with_suffix(".png.bak")

    if backup_path.exists():
        import shutil
        shutil.copy2(backup_path, splash_path)
        print(f"Restored original splash from: {backup_path}")
        os.remove(backup_path)
        print("Removed backup file.")
    else:
        print("No backup found to restore.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", help="Version string to display", default=None)
    parser.add_argument("--output", help="Specific output path. If not set, modifies src asset.", default=None)
    parser.add_argument("--restore", help="Restore original splash screen", action="store_true")
    args = parser.parse_args()

    if args.restore:
        restore_splash()
    else:
        generate_splash(args.version, args.output)
