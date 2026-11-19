#!/usr/bin/env python3
"""Make the frames for the hero's "clear, then glitch" portrait.

Run this locally; it needs Pillow and NumPy. It writes data/art.json, which scripts/build.py
turns into the animation in assets/hero.svg:

    python scripts/glitchify.py --photo me.png --crop 55,-40,1155,1217

The photo should be a PNG with a transparent background. The frames are:
clean (the photo as it is), rest (the glitch look it settles into) and three burst frames
used for the glitch itself and for the short twitches that repeat afterwards.
"""
import argparse
import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
BOX = (252, 288)                  # portrait box in the hero, in SVG units
SCALE = 2.5                       # stored pixels per SVG unit, for sharp results on high-density screens


def shifted(a, dx, dy=0):
    """Move an image by whole pixels, filling with transparent black instead of wrapping."""
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    out[yd, xd] = a[ys, xs]
    return out


def glitch(base, split, slices=(), jolt=0, tear=None, scan=True):
    """base: premultiplied RGBA float array. split: how far red goes right and blue goes left."""
    r = shifted(base[..., [0, 3]], split)
    g = base[..., [1, 3]]
    b = shifted(base[..., [2, 3]], -split)
    out = np.dstack([r[..., 0], g[..., 0], b[..., 0], np.maximum(np.maximum(r[..., 1], g[..., 1]), b[..., 1])])
    for y, h, dx in slices:                                   # displaced horizontal bands
        out[y:y + h] = shifted(out[y:y + h], dx)
    if tear:                                                  # a band where every row slips a different amount
        y0, y1, amount, seed = tear
        rng = np.random.default_rng(seed)
        for y in range(y0, y1):
            out[y:y + 1] = shifted(out[y:y + 1], int(rng.integers(-amount, amount + 1)))
    if jolt:
        out = shifted(out, jolt)
    if scan:                                                  # faint scanlines, on the person only
        lines = (np.arange(out.shape[0]) % 10 < 3)[:, None]
        out[..., :3] *= np.where(lines, 0.88, 1.0)[..., None]
    return out


def bands(seed, count, height, width, reach):
    rng = np.random.default_rng(seed)
    return [(int(rng.integers(0, height - 40)), int(rng.integers(4, 26)), int(rng.integers(-reach, reach + 1)))
            for _ in range(count)]


def encode(pre):
    a = pre[..., 3:4]
    rgb = np.where(a > 0, pre[..., :3] / np.maximum(a, 1e-6), 0)
    arr = (np.clip(np.dstack([rgb, a]), 0, 1) * 255 + 0.5).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "WEBP", quality=80, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photo", required=True, help="portrait with a transparent background")
    ap.add_argument("--crop", help="left,top,right,bottom in photo pixels")
    ap.add_argument("--out", default=str(ROOT / "data" / "art.json"))
    args = ap.parse_args()

    img = ImageOps.exif_transpose(Image.open(args.photo)).convert("RGBA")
    if args.crop:
        img = img.crop(tuple(int(n) for n in args.crop.split(",")))
    W, H = round(BOX[0] * SCALE), round(BOX[1] * SCALE)
    img = ImageOps.fit(img, (W, H), Image.LANCZOS, centering=(0.5, 0.35))
    rgba = np.asarray(img, np.float32) / 255

    # soft fade at the bottom and sides, so the portrait melts into the terminal instead of ending in a line
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fade = np.clip(np.minimum.reduce([(H - 1 - yy) / (H * 0.16), (xx + 1) / (W * 0.07), (W - xx) / (W * 0.07)]), 0, 1)
    rgba[..., 3] *= fade ** 0.6
    base = np.dstack([rgba[..., :3] * rgba[..., 3:4], rgba[..., 3:4]])     # premultiplied

    frames = {
        "clean": encode(base),
        "rest": encode(glitch(base, 6, bands(3, 3, H, W, 10))),
        "burst": [
            encode(glitch(base, 18, bands(11, 7, H, W, 45), jolt=8)),
            encode(glitch(base, -26, bands(12, 10, H, W, 60), tear=(int(H * 0.30), int(H * 0.40), 30, 5))),
            encode(glitch(base, 12, [(y, h * 2, dx) for y, h, dx in bands(13, 4, H, W, 70)], jolt=-10)),
        ],
    }
    art = {"w": BOX[0], "h": BOX[1], "dots": [], "glitch": {"x": 0, "y": 0, "w": BOX[0], "h": BOX[1], **frames}}
    Path(args.out).write_text(json.dumps(art, separators=(",", ":")), encoding="utf-8")
    sizes = [len(frames["clean"]), len(frames["rest"])] + [len(f) for f in frames["burst"]]
    print(f"wrote {args.out}: 5 frames, {sum(sizes) // 1024} KB. Now run: python scripts/build.py")


if __name__ == "__main__":
    main()
