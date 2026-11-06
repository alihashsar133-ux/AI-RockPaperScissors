#!/usr/bin/env python3
"""Promote the S4-approved cats into the reusable character library.

Section 10 of the production prompt: once a character PNG is approved (here, in
the S4 delivery ZIP) it is reused in every later scene and never regenerated.
These are tight alpha crops of the same paintings used in scene 04, so S5–S12
can place them at any size.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "scene_04" / "assets"
LIB = ROOT / "assets_characters"

MAP = {
    "siamese_prophet.png": ("prophet_rgba.png", "Siamese prophet - cream body, seal points, ice-blue eyes, overlong neck"),
    "white_kitten.png": ("kitten_rgba.png", "White kitten - oversized ears, grey-tipped tail, seen from behind"),
    "brown_tabby.png": ("tabby_rgba.png", "Brown tabby guide - amber eyes, notched ear, striped"),
}


def main():
    LIB.mkdir(exist_ok=True)
    meta = {}
    for out_name, (src, note) in MAP.items():
        im = Image.open(A / src).convert("RGBA")
        a = np.asarray(im)[..., 3]
        ys, xs = np.where(a > 6)
        pad = 8
        box = (max(int(xs.min()) - pad, 0), max(int(ys.min()) - pad, 0),
               min(int(xs.max()) + pad + 1, im.width), min(int(ys.max()) + pad + 1, im.height))
        crop = im.crop(box)
        crop.save(LIB / out_name)
        meta[out_name] = {"source_layer": src, "source_box_1920x804": list(box),
                          "size": list(crop.size), "note": note}
        print(out_name, crop.size, "from", src, box)
    (LIB / "characters.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
