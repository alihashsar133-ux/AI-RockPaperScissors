#!/usr/bin/env python3
"""Pull frames out of the assembled scene so the review pass has something real
to look at (one row per clip, three moments each)."""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
FF = imageio_ffmpeg.get_ffmpeg_exe()


def grab(path, t):
    p = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    import io
    return Image.open(io.BytesIO(p.stdout)).convert("RGB")


def main():
    scene = ROOT / "scene_04" / "scene_04.mp4"
    clip_len = 8.0
    times = [(i * clip_len + d) for i in range(6) for d in (1.0, 4.0, 7.0)]
    thumbs = [grab(scene, t) for t in times]
    tw, th = 480, 270
    cols, rows = 3, 6
    pad, head = 10, 60
    sheet = Image.new("RGB", (cols * tw + pad * (cols + 1), head + rows * (th + 26) + pad), (8, 11, 20))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16), "S4 REVIEW SHEET - frames pulled from scene_04.mp4", fill=(220, 230, 245))
    d.text((pad, 34), "one row per clip: t+1s, t+4s, t+7s", fill=(140, 160, 190))
    for i, im in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = head + r * (th + 26)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 2, y + th + 6), f"clip_{r + 1:02d}  t={times[i]:.1f}s", fill=(150, 170, 200))
    out = ROOT / "scene_04" / "review_sheet.png"
    sheet.save(out)
    print("wrote", out, sheet.size)
    # also keep individual frames for close inspection
    raw = ROOT / "scene_04" / "frames" / "review"
    raw.mkdir(parents=True, exist_ok=True)
    for t, im in zip(times, thumbs):
        im.save(raw / f"scene_t{t:05.2f}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
