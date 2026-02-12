"""
Generate Nexus application icon (nexus.ico) with crisp font-hinted N at all sizes.

Uses Segoe UI Bold (Windows system font) for the N letterform instead of downscaling
an SVG path. Font hinting ensures the N is sharp at every pixel size, especially
the critical 16x16 (title bar) and 32x32 (taskbar) sizes.

Pillow's ICO save() only auto-resizes from one base image and ignores append_images,
so we manually construct the ICO binary with independently-rendered PNG frames.

Usage:
    python assets/generate_icon.py
"""

import io
import os
import struct
from PIL import Image, ImageDraw, ImageFont

# Icon sizes required for Windows 10/11
ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]

# Brand color
BLUE = (26, 115, 232)  # #1a73e8

# Font config
FONT_PATH = "C:/Windows/Fonts/segoeuib.ttf"  # Segoe UI Bold
FALLBACK_FONT = "C:/Windows/Fonts/arialbd.ttf"  # Arial Bold


def get_font(size):
    """Load the best available bold font at the given size."""
    for path in [FONT_PATH, FALLBACK_FONT]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    if r <= 0:
        draw.rectangle(xy, fill=fill)
        return
    draw.pieslice([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=fill)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x0 + r, y1 - r], fill=fill)
    draw.rectangle([x1 - r, y0 + r, x1, y1 - r], fill=fill)


def generate_icon_image(size):
    """Generate a single icon image at the given pixel size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: square for tiny sizes, rounded for larger
    if size <= 24:
        draw.rectangle([0, 0, size - 1, size - 1], fill=BLUE)
    elif size <= 48:
        radius = max(2, size // 12)
        draw_rounded_rect(draw, [0, 0, size - 1, size - 1], radius, BLUE)
    else:
        radius = size // 6
        draw_rounded_rect(draw, [0, 0, size - 1, size - 1], radius, BLUE)

    # Render "N" with font hinting
    font_size = max(8, int(size * 0.65))
    font = get_font(font_size)

    bbox = font.getbbox("N")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]

    draw.text((x, y), "N", fill="white", font=font)

    return img


def build_ico(images, output_path):
    """
    Build a multi-size ICO file from a list of RGBA PIL Images.

    Pillow's ICO save() only auto-resizes from one base image, so we manually
    construct the ICO binary format with independently-rendered PNG frames.

    ICO format:
      - ICONDIR: 6 bytes (reserved, type=1, count)
      - ICONDIRENTRY[]: 16 bytes each (width, height, colors, reserved, planes, bpp, size, offset)
      - Image data: PNG bytes for each entry
    """
    # Encode each image as PNG
    png_data = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data.append(buf.getvalue())

    count = len(images)

    # ICONDIR header
    header = struct.pack("<HHH", 0, 1, count)  # reserved=0, type=1 (icon), count

    # Calculate offsets: header(6) + entries(16*count) + image data
    data_offset = 6 + 16 * count

    entries = b""
    for i, img in enumerate(images):
        w = img.width if img.width < 256 else 0  # 0 means 256 in ICO format
        h = img.height if img.height < 256 else 0
        size = len(png_data[i])
        offset = data_offset + sum(len(d) for d in png_data[:i])

        entries += struct.pack(
            "<BBBBHHII",
            w,       # width (0 = 256)
            h,       # height (0 = 256)
            0,       # color palette count (0 for RGBA)
            0,       # reserved
            1,       # color planes
            32,      # bits per pixel
            size,    # image data size
            offset,  # offset to image data
        )

    with open(output_path, "wb") as f:
        f.write(header)
        f.write(entries)
        for d in png_data:
            f.write(d)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("Generating Nexus icon with font-hinted N...")
    print(f"  Font: {FONT_PATH}")
    print(f"  Sizes: {ICON_SIZES}")

    images = []
    for size in ICON_SIZES:
        img = generate_icon_image(size)
        images.append(img)
        print(f"  Generated {size}x{size}")

    # Build ICO with all sizes as independent PNG frames
    ico_path = os.path.join(script_dir, "nexus.ico")
    build_ico(images, ico_path)
    print(f"\n  Saved: {ico_path}")

    # Verify the ICO
    ico_check = Image.open(ico_path)
    print(f"  ICO sizes: {ico_check.info.get('sizes', 'unknown')}")

    # Save 256px PNG reference
    png_path = os.path.join(script_dir, "nexus.png")
    images[-1].save(png_path, format="PNG")
    print(f"  Saved: {png_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
