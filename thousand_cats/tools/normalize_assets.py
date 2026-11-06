#!/usr/bin/env python3
"""S4 asset normalisation + chroma key.

Route B of the skill (references/03-一帧先行四条路线.md): AI paints every layer
full-frame on flat #00FF00 at the *same* coordinates as the keyframe, then code
keys it out and composites. Nothing is cropped, so the pixel grid of every layer
is the keyframe grid and offsets are real placement decisions, not guesses.

Outputs (all 1920x804 = the 2.39:1 picture area inside 1920x1080):
    assets/bg_plate.png       RGB   opaque background plate
    assets/cross_rgba.png     RGBA  wax-bending cross
    assets/prophet_rgba.png   RGBA  Siamese prophet
    assets/kitten_rgba.png    RGBA  white kitten
    assets/tabby_rgba.png     RGBA  brown tabby
    assets/mist_rgba.png      RGBA  luminous mist (screen-blended)
    assets/eyes_rgba.png      RGBA  amber eye clusters split out of the mist
    assets/key_report.json    measurements used by qa.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

PIC_W, PIC_H = 1920, 804
ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "scene_04" / "assets"


def load_pic(name):
    im = Image.open(A / name).convert("RGB")
    return im.resize((PIC_W, PIC_H), Image.LANCZOS)


def smoothstep(x, a, b):
    t = np.clip((x - a) / max(b - a, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def key_green(rgb):
    """Chroma key a flat-green AI layer. Returns float alpha in [0,1]."""
    a = np.asarray(rgb).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dominance = g - np.maximum(r, b)          # flat green -> large positive
    green_level = g                            # dark green vignette still green
    alpha = 1.0 - smoothstep(dominance, 12, 55)
    alpha *= 1.0 - smoothstep(green_level, 60, 110) * smoothstep(dominance, 8, 40)
    alpha = np.clip(alpha, 0, 1)
    # erode 1px so no green rim survives, then feather 1px
    m = Image.fromarray((alpha * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    alpha = np.asarray(m).astype(np.float32) / 255.0
    # spill suppression: pull green down to the other channels' max
    spill = np.minimum(a[..., 1], np.maximum(a[..., 0], a[..., 2]) * 1.08)
    a[..., 1] = np.where(alpha > 0.02, spill, a[..., 1])
    out = np.dstack([np.clip(a, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def bbox(alpha, thr=0.35):
    m = alpha > thr
    if not m.any():
        return None
    ys, xs = np.where(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def split_eyes(mist):
    """Amber eye-pairs live in the warm corner of the mist plate."""
    a = np.asarray(mist).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    warm = (r > 55) & (r > g * 1.12) & (g > b * 1.02)
    warm_img = Image.fromarray((smoothstep((r - g * 1.12), 0, 14) * warm * 255).astype(np.uint8))
    warm_img = warm_img.filter(ImageFilter.GaussianBlur(0.6))
    eye_alpha = np.asarray(warm_img).astype(np.float32) / 255.0
    eyes = a.copy()
    rest = a.copy()
    eyes[..., 3] = (eye_alpha * a[..., 3] / 255.0 * 255)
    rest[..., 3] = a[..., 3] * (1.0 - eye_alpha)
    return (Image.fromarray(eyes.astype(np.uint8), "RGBA"),
            Image.fromarray(rest.astype(np.uint8), "RGBA"))


def main():
    report = {}

    # --- opaque background plate -----------------------------------------
    bg = load_pic("bg_plate.png")
    bg.save(A / "bg_plate.png")

    # --- keyed character/prop layers -------------------------------------
    for src, dst in [
        ("layer_cross.png", "cross_rgba.png"),
        ("layer_prophet.png", "prophet_rgba.png"),
        ("layer_kitten.png", "kitten_rgba.png"),
        ("layer_tabby.png", "tabby_rgba.png"),
    ]:
        rgba = key_green(load_pic(src))
        rgba.save(A / dst)
        alpha = np.asarray(rgba)[..., 3] / 255.0
        report[dst] = {"bbox_px": bbox(alpha), "coverage": round(float((alpha > 0.35).mean()), 5)}

    # --- luminous mist + eyes --------------------------------------------
    mist_rgb = load_pic("layer_mist_eyes.png")
    mist_f = np.asarray(mist_rgb).astype(np.float32)
    lum = mist_f.max(axis=2)
    mist_alpha = np.clip((lum - 6) / 90.0, 0, 1) ** 0.85
    mist = np.dstack([mist_f, mist_alpha * 255]).astype(np.uint8)
    mist_img = Image.fromarray(mist, "RGBA")
    eyes_img, mist_only = split_eyes(mist_img)
    mist_only.save(A / "mist_rgba.png")

    # the eye-pairs are only ~3 px each in the painting: give them a warm core
    # and a small halo so "glowing eyes in mist" actually reads at 1080p
    ea = np.asarray(eyes_img).astype(np.float32)
    core_a = ea[..., 3:4] / 255.0
    core = ea[..., :3] * 1.55
    halo = np.asarray(Image.fromarray((core_a[..., 0] * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(2.4)), np.float32) / 255.0
    halo = np.clip(halo * 1.5, 0, 1)[..., None]
    amber = np.array([255, 176, 78], np.float32)
    a_out = np.clip(core_a * 1.0 + halo * 0.9, 0, 1)
    rgb_out = (core * core_a + amber * halo * 0.9) / np.maximum(a_out, 1e-3)
    eyes2 = np.dstack([np.clip(rgb_out, 0, 255), a_out * 255]).astype(np.uint8)
    eyes_img = Image.fromarray(eyes2, "RGBA")
    eyes_img.save(A / "eyes_rgba.png")
    for name, img in [("mist_rgba.png", mist_only), ("eyes_rgba.png", eyes_img)]:
        alpha = np.asarray(img)[..., 3] / 255.0
        report[name] = {"bbox_px": bbox(alpha), "coverage": round(float((alpha > 0.3).mean()), 5)}

    report["picture"] = [PIC_W, PIC_H]
    (A / "key_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
