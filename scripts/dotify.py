#!/usr/bin/env python3
"""Turn a photo (or a monogram) into the dot-matrix art shown in the hero.

Run this locally; it needs Pillow (`pip install pillow`). It writes
data/art.json, which scripts/build.py embeds into assets/hero.svg.

    python scripts/dotify.py --photo me.png              # portrait, photo colours
    python scripts/dotify.py --photo me.png --green      # portrait, green phosphor
    python scripts/dotify.py --photo me.png --crop 105,500,565,1026
    python scripts/dotify.py --text GJ                   # monogram

A PNG with a transparent background gives the cleanest portrait: only the
person is drawn, and dark hair or clothing still shows against the black hero.
"""
import argparse
import colorsys
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
TEXT_BOX, TEXT_PITCH = (230, 250), 5         # art box in the hero (px) and dot spacing
PHOTO_BOX, PHOTO_PITCH = (252, 288), 2.4
DIM = "#21262d"                              # unlit dots
GREENS = [(14, 68, 41), (0, 109, 50), (38, 166, 65), (57, 211, 83), (126, 231, 135)]


def lerp_ramp(ramp, t):
    t = max(0.0, min(1.0, t)) * (len(ramp) - 1)
    i = min(int(t), len(ramp) - 2)
    f = t - i
    return tuple(round(ramp[i][k] + (ramp[i + 1][k] - ramp[i][k]) * f) for k in range(3))


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def grid(box, pitch):
    """Columns, rows, and a function giving each dot's centre, with the grid centred in the box."""
    cols, rows = int(box[0] // pitch), int(box[1] // pitch)
    ox, oy = (box[0] - cols * pitch) / 2, (box[1] - rows * pitch) / 2

    def centre(col, row):
        return round(ox + col * pitch + pitch / 2, 1), round(oy + row * pitch + pitch / 2, 1)

    return cols, rows, centre


def from_text(text):
    cols, rows, centre = grid(TEXT_BOX, TEXT_PITCH)
    scale = 8
    img = Image.new("L", (cols * scale, rows * scale), 0)
    draw = ImageDraw.Draw(img)
    font = None
    for name in ("ariblk.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        for size in range(400, 40, -8):
            try:
                f = ImageFont.truetype(name, size)
            except OSError:
                break
            box = draw.textbbox((0, 0), text, font=f)
            if box[2] - box[0] <= img.width * 0.9 and box[3] - box[1] <= img.height * 0.6:
                font = f
                break
        if font:
            break
    if font is None:
        raise SystemExit("No bold TrueType font found; install Arial or DejaVu Sans.")
    box = draw.textbbox((0, 0), text, font=font)
    x = (img.width - (box[2] - box[0])) / 2 - box[0]
    y = (img.height - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), text, fill=255, font=font)
    small = img.resize((cols, rows), Image.LANCZOS)

    dots = []
    for row in range(rows):
        for col in range(cols):
            a = small.getpixel((col, row)) / 255
            cx, cy = centre(col, row)
            if a < 0.08:
                dots.append([cx, cy, 0.6, DIM])
            else:
                t = 0.35 + 0.65 * (col / cols * 0.6 + (1 - row / rows) * 0.4)
                dots.append([cx, cy, round(0.8 + 1.5 * a, 2), hexc(lerp_ramp(GREENS, t))])
    return TEXT_BOX, dots


def from_photo(path, green, crop=None, pitch=PHOTO_PITCH):
    cols, rows, centre = grid(PHOTO_BOX, pitch)
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    if crop:
        img = img.crop(crop)
    img = ImageOps.fit(img, (cols * 8, rows * 8), Image.LANCZOS, centering=(0.5, 0.35))
    alpha = img.getchannel("A")
    rgb = Image.composite(img.convert("RGB"), Image.new("RGB", img.size, (0, 0, 0)), alpha)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=8, percent=140, threshold=2))

    # stretch brightness using the person only, so a dark background cannot flatten the face
    lum = ImageOps.autocontrast(rgb.convert("L"), cutoff=(1, 2.5), mask=alpha)   # clip glare on glasses
    lum, rgb, alpha = (im.resize((cols, rows), Image.LANCZOS) for im in (lum, rgb, alpha))

    slate = (0.72, 0.80, 0.92)                 # tint for near-black areas such as hair
    dots = []
    for row in range(rows):
        for col in range(cols):
            if alpha.getpixel((col, row)) < 128:
                continue                       # background: draw nothing
            # dissolve towards the bottom and side edges instead of ending in a hard line
            edge = min(1.0, (rows - 1 - row) / (rows * 0.16), (col + 1) / (cols * 0.07), (cols - col) / (cols * 0.07))
            if edge < 0.1:
                continue
            v = (lum.getpixel((col, row)) / 255) ** 0.62
            shown = 0.2 + 0.8 * v              # floor keeps black hair and clothes visible
            if green:
                colour = lerp_ramp(GREENS, 0.1 + 0.9 * v)
            else:
                r, g, b = (c / 255 for c in rgb.getpixel((col, row)))
                hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
                keep = min(1.0, val / 0.3)     # trust the photo's hue less where it is nearly black
                pure = colorsys.hsv_to_rgb(hue, min(1.0, sat * 1.12), 1.0)
                colour = tuple(min(255, 8 * round(255 * shown * (pure[k] * keep + slate[k] * (1 - keep)) / 8))
                               for k in range(3))
            cx, cy = centre(col, row)
            dots.append([cx, cy, round(pitch * (0.16 + 0.36 * shown) * edge ** 0.6, 2), hexc(colour)])
    return PHOTO_BOX, dots


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--photo", help="path to a portrait photo (a transparent PNG works best)")
    src.add_argument("--text", help="one to three letters for a monogram")
    ap.add_argument("--green", action="store_true", help="tint a photo green instead of using its colours")
    ap.add_argument("--crop", help="left,top,right,bottom in photo pixels (default: centred, upper part)")
    ap.add_argument("--pitch", type=float, default=PHOTO_PITCH, help="dot spacing for photos; smaller is finer")
    ap.add_argument("--out", default=str(ROOT / "data" / "art.json"), help="where to write the art")
    args = ap.parse_args()

    crop = tuple(int(n) for n in args.crop.split(",")) if args.crop else None
    box, dots = from_text(args.text) if args.text else from_photo(args.photo, args.green, crop, args.pitch)
    out = Path(args.out)
    out.write_text(json.dumps({"w": box[0], "h": box[1], "dots": dots}, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} ({len(dots)} dots). Now run: python scripts/build.py")


if __name__ == "__main__":
    main()
