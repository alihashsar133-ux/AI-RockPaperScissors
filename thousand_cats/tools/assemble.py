#!/usr/bin/env python3
"""Assemble the six S4 clips into scene_04.mp4 (hard cuts, silent, 24 fps)."""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
FF = imageio_ffmpeg.get_ffmpeg_exe()
CLIPS = ROOT / "scene_04" / "clips"
OUT = ROOT / "scene_04" / "scene_04.mp4"


def main():
    files = sorted(CLIPS.glob("clip_*.mp4"))
    assert len(files) == 6, f"expected 6 clips, found {len(files)}"
    lst = CLIPS / "concat_list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in files), encoding="utf-8")
    cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-r", "24", "-movflags", "+faststart", str(OUT)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:], file=sys.stderr)
        raise SystemExit(1)
    print(f"assembled {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
