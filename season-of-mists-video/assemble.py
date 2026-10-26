#!/usr/bin/env python3
"""فاز ۴ — مونتاژ مستر نهایی: concat سگمنت‌ها + loudnorm دومرحله‌ای ‎-14 LUFS‎
خروجی: output/master_final.mp4 (H.264 ‏۸٫۲–۹٫۸ Mbps، ‏1920×1080@24، ‏AAC ‏192k)
"""
import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "pylibs"))
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent
SEGS = sorted((ROOT / "segments").glob("seg_*.mp4"))
lst = ROOT / "segments" / "concat.txt"
lst.write_text("\n".join(f"file '{s.resolve()}'" for s in SEGS), encoding="utf-8")

mix = ROOT / "output" / "audio_mix_pre.wav"
print("loudnorm analysis...")
o = subprocess.run([FF, "-i", str(mix), "-vn", "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True)
m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", o.stderr, re.S).group(0))
lin = "true" if m.get("normalization_type") == "linear" else "false"
print({k: m[k] for k in ("input_i", "input_tp", "input_lra", "target_offset", "normalization_type")})
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:" 
      f"offset={m['target_offset']}:linear={lin}")
out = ROOT / "output" / "master_final.mp4"
cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(mix),
       "-vf", "fps=24,format=yuv420p", "-af", af, "-r", "24", "-vsync", "cfr",
       "-c:v", "libx264", "-preset", "veryfast", "-b:v", "9M", "-minrate", "8.2M",
       "-maxrate", "9.8M", "-bufsize", "20M", "-c:a", "aac", "-b:a", "192k",
       "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
       "-metadata", "title=Season of Mists — Analytical Study (Persian)",
       "-metadata", "comment=Educational analysis of Sandman: Season of Mists (#21-28) by Neil Gaiman (DC Comics). Original code-generated visuals and original Persian analysis. No subtitles.",
       str(out)]
print("encoding master..."); subprocess.run(cmd, check=True)
print("done:", out, f"{out.stat().st_size / 1e6:.1f} MB")
