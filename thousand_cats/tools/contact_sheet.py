#!/usr/bin/env python3
"""asset_preview_sheet.png - every PNG layer used by scene 04, on one sheet."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "scene_04" / "assets"

ORDER = [
    ("bg_plate.png", "bg_plate - night sky, moon, tilted stones (opaque)"),
    ("cross_rgba.png", "cross - wax-bending stone cross"),
    ("prophet_rgba.png", "prophet - Siamese, sits on the sagging arm"),
    ("kitten_rgba.png", "kitten - the witness"),
    ("tabby_rgba.png", "tabby - the guide"),
    ("mist_rgba.png", "mist - luminous indigo bands (screen/over)"),
    ("eyes_rgba.png", "eyes - amber eye-pairs, split into 10 clusters"),
]

CELL_W, CELL_H = 620, 300


def thumb(im, w, h, checker=True):
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    cell = Image.new("RGBA", (w, h), (18, 22, 34, 255))
    if checker:
        d = ImageDraw.Draw(cell)
        for y in range(0, h, 20):
            for x in range(0, w, 20):
                if (x // 20 + y // 20) % 2 == 0:
                    d.rectangle([x, y, x + 19, y + 19], fill=(28, 34, 50, 255))
    cell.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return cell


def main():
    cols = 2
    rows = (len(ORDER) + cols - 1) // cols
    pad, head = 16, 84
    W = cols * CELL_W + pad * (cols + 1)
    H = head + rows * (CELL_H + 40) + pad
    sheet = Image.new("RGB", (W, H), (10, 13, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), "SCENE 04 - ASSET PREVIEW SHEET", fill=(220, 230, 245))
    d.text((pad, 40), "every PNG layer used in the render - 1920x804 picture space, 2.39:1", fill=(140, 160, 190))
    d.text((pad, 58), "palette #101f3c #1b2c50 #c9d6e8 #e9eef6 #3a3474 #6c7a8c  amber accent #d99a3f",
           fill=(140, 160, 190))
    for i, (name, label) in enumerate(ORDER):
        r, c = divmod(i, cols)
        x = pad + c * (CELL_W + pad)
        y = head + r * (CELL_H + 40)
        img = Image.open(A / name).convert("RGBA")
        sheet.paste(thumb(img, CELL_W, CELL_H).convert("RGB"), (x, y))
        d.text((x + 4, y + CELL_H + 8), f"{name}", fill=(210, 220, 240))
        d.text((x + 4, y + CELL_H + 22), label, fill=(130, 150, 180))
    out = ROOT / "scene_04" / "asset_preview_sheet.png"
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
