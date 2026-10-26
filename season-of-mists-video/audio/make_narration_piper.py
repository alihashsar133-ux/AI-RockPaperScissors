#!/usr/bin/env python3
"""فاز ۱ — تولید روایت با Piper (مسیر اصلی پروژه).

استفاده (وقتی فایل مدل فارسی در دسترس باشد):
  python make_narration_piper.py --model ../tools/Mana-Persian-Piper/fa_IR-mana-medium.onnx

رفتار: متن هر [SCENE_XX] از narration_fa.txt مستقیم به Piper داده می‌شود
(آوانویسی دستی لازم نیست)، مدت هر WAV با ماژول wave خوانده و timing.json
ساخته می‌شود، و در پایان narration_final.wav چسبانده می‌شود.
توجه: در محیط فعلی، میزبان مدل (huggingface.co) خارج از فهرست مجاز سندباکس
است؛ صداهای نهایی این تحویل با موتور جایگزین ساخته و در timing.json با
فیلد tts_engine ثبت شده‌اند. این اسکریپت مستند مسیر اصلی Piper است.
"""
import argparse, json, re, subprocess, sys, wave
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="fa_IR-mana-medium.onnx (همراه .onnx.json)")
    ap.add_argument("--text", default=str(ROOT / "narration_fa.txt"))
    a = ap.parse_args()
    text = Path(a.text).read_text(encoding="utf-8")
    scenes = re.findall(r"\[(SCENE_\d+)\]\n(.*?)(?=\n\[|\Z)", text, re.S)
    timing, files, start = [], [], 0.0
    for tag, body in scenes:
        out = HERE / (tag.lower() + ".wav")  # scene_01.wav ...
        subprocess.run([sys.executable, "-m", "piper", "--model", a.model,
                        "--output_file", str(out)], input=body.strip(),
                       text=True, check=True)
        with wave.open(str(out)) as w:
            dur = w.getnframes() / w.getframerate()
        timing.append({"scene": tag, "file": out.name, "start_sec": round(start, 3),
                       "end_sec": round(start + dur, 3), "duration_sec": round(dur, 3),
                       "tts_engine": "piper", "voice_source": Path(a.model).name})
        files.append(str(out)); start += dur
    concat = "concat:" + "|".join(files)
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", concat,
                    "-c", "copy", str(HERE / "narration_final.wav")], check=True)
    (ROOT / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK", HERE / "narration_final.wav", ROOT / "timing.json")

if __name__ == "__main__":
    main()
