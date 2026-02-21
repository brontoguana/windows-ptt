"""Generate tray icon and .ico from hires_mic.png source image."""
from PIL import Image

def generate_icons():
    # Load the hi-res microphone image (already has alpha transparency)
    src = Image.open("assets/hires_mic.png").convert("RGBA")

    # Crop to the bounding box of non-transparent pixels (trim whitespace)
    bbox = src.getbbox()
    if bbox:
        src = src.crop(bbox)

    # Add a small margin and resize to 256x256 master (largest ICO size)
    master_size = 256
    margin = int(master_size * 0.08)
    inner = master_size - 2 * margin

    # Fit the mic into the inner area, preserving aspect ratio
    src.thumbnail((inner, inner), Image.LANCZOS)
    master = Image.new("RGBA", (master_size, master_size), (0, 0, 0, 0))
    offset_x = (master_size - src.width) // 2
    offset_y = (master_size - src.height) // 2
    master.paste(src, (offset_x, offset_y), src)

    # Generate all needed sizes as separate images
    sizes = [256, 128, 64, 48, 32, 16]
    images = [master.resize((s, s), Image.LANCZOS) for s in sizes]

    # Save PNG (64x64 for pystray)
    images[2].save("assets/icon.png")  # 64x64
    print("Saved assets/icon.png")

    # Save ICO with all sizes using append_images for proper multi-size ICO
    images[0].save(
        "assets/icon.ico",
        format="ICO",
        append_images=images[1:],
    )
    print("Saved assets/icon.ico")


if __name__ == "__main__":
    generate_icons()
