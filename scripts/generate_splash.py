from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import argparse

def generate_splash(version=None):
    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    logo_path = base_dir / "src" / "switchcraft" / "assets" / "switchcraft_logo.png"
    output_path = base_dir / "src" / "switchcraft" / "assets" / "splash.png"

    # Fonts (Windows standard)
    font_dir = Path("C:/Windows/Fonts")
    try:
        font_main = ImageFont.truetype(str(font_dir / "segoeuib.ttf"), 60) # Segoe UI Bold
        font_sub = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 22)   # Segoe UI
        font_hint = ImageFont.truetype(str(font_dir / "segoeui.ttf"), 16)  # Segoe UI
        font_ver = ImageFont.truetype(str(font_dir / "consola.ttf"), 14)   # Consolas (Monospace)
    except Exception:
        # Fallback to default if fonts not found
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_hint = ImageFont.load_default()
        font_ver = ImageFont.load_default()

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
        logo_y = height // 2 - logo.height - 50
        img.paste(logo, (logo_x, logo_y), logo)

    # Add Text
    # "SwitchCraft"
    text_main = "SwitchCraft"
    bbox_main = draw.textbbox((0, 0), text_main, font=font_main)
    w_main = bbox_main[2] - bbox_main[0]
    draw.text(((width - w_main) // 2, height // 2), text_main, font=font_main, fill=(255, 255, 255))

    # Tagline
    text_sub = "The Ultimate Packaging Suite for IT Professionals"
    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_sub)
    w_sub = bbox_sub[2] - bbox_sub[0]
    draw.text(((width - w_sub) // 2, height // 2 + 70), text_sub, font=font_sub, fill=(200, 200, 200))

    # Hint
    text_hint = "Starting..."
    bbox_hint = draw.textbbox((0, 0), text_hint, font=font_hint)
    w_hint = bbox_hint[2] - bbox_hint[0]
    draw.text(((width - w_hint) // 2, height - 50), text_hint, font=font_hint, fill=(150, 150, 150))

    # Footer
    text_footer = "Brought to you by FaserF"
    bbox_footer = draw.textbbox((0, 0), text_footer, font=font_hint)
    w_footer = bbox_footer[2] - bbox_footer[0]
    draw.text((width - w_footer - 20, height - 30), text_footer, font=font_hint, fill=(100, 100, 100))

    # Version (if provided) - Bottom Left
    if version:
        text_ver = f"{version}"
        draw.text((20, height - 30), text_ver, font=font_ver, fill=(100, 100, 100))

        # Check for Beta/Dev and add banner
        v_lower = version.lower()
        banner_text = ""
        banner_color = (0, 0, 0)

        if "dev" in v_lower:
            banner_text = "DEV BUILD"
            banner_color = (255, 50, 50) # Red
        elif "beta" in v_lower:
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

            # Optional: Add a slight background or border for the banner?
            # Request asked for "Warnbanner", let's make it text for now but perhaps with a rectangle behind it?
            # User said "Beta in auffälligem dunklen Orange, dev in rotem Text" (Beta in striking dark orange, dev in red text)
            # Just changing text color might be enough as per specifically "text" request, but lets add a small border/box for "Banner" feel if needed.
            # "Warnbanner steht" implies a banner. Let's do a simple rounded rect background maybe?
            # Actually, "dev in rotem Text" suggests the text itself is colored.
            # Let's stick to colored text with a small background pill for better visibility against dark bg.

            # Draw semi-transparent background for the banner?
            # The background is (30, 30, 40).
            # Let's just draw the text clearly.

            # Draw text
            draw.text((x_banner, y_banner), banner_text, font=font_banner, fill=banner_color)

            # Add a small line/box under/around it?
            # Let's add a rectangle border with the same color
            padding = 5
            draw.rectangle(
                (x_banner - padding, y_banner - padding, x_banner + w_banner + padding, y_banner + h_banner + padding + 5),
                outline=banner_color,
                width=2
            )

    # Backup original splash if it exists and backup doesn't
    backup_path = output_path.with_suffix(".png.bak")
    if output_path.exists() and not backup_path.exists():
        import shutil
        shutil.copy2(output_path, backup_path)
        print(f"Backed up original splash to: {backup_path}")

    # Save
    img.save(output_path)
    print(f"Splash screen generated at: {output_path}")

def restore_splash():
    base_dir = Path(__file__).resolve().parent.parent
    splash_path = base_dir / "src" / "switchcraft" / "assets" / "splash.png"
    backup_path = splash_path.with_suffix(".png.bak")

    if backup_path.exists():
        import shutil
        shutil.copy2(backup_path, splash_path)
        print(f"Restored original splash from: {backup_path}")
        # Optional: Delete backup? User might want to keep it safe.
        # But if we want to ensure 'git status' is clean, we should keep the original 'splash.png'
        # intact. The backup file is untracked usually.
        # Let's remove the backup to keep folder clean.
        os.remove(backup_path)
        print("Removed backup file.")
    else:
        print("No backup found to restore.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", help="Version string to display", default=None)
    parser.add_argument("--restore", help="Restore original splash screen", action="store_true")
    args = parser.parse_args()

    if args.restore:
        restore_splash()
    else:
        generate_splash(args.version)
