#!/usr/bin/env python3
"""فاز ۱ (تکمیل): پالایش صدای هر سکانس + narration_final.wav + timing.json

مراحل: بکاپ خام -> برش سکوت ابتدا/انتها و فشرده‌سازی مکث‌های بلند (numpy)
-> تنظیم سرعت یکنواخت با atempo تا narration_final برابر TARGET شود
-> چسباندن با مکث ۰٫۷ ثانیه‌ای بین سکانس‌ها -> ساخت timing.json
فرمت خروجی روایت نهایی: WAV، 24000Hz، مونو، ۱۶ بیت (مطابق مشخصات پروژه).
"""
import json, re, shutil, subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "pylibs"))
import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = Path(__file__).parent
ROOT = HERE.parent
TARGET_NARRATION = 575.0      # + تیتراژ ۱۵ و ۱۰ ثانیه = ۶۰۰ ثانیه ویدیو
GAP = 0.7
TITLES = [
    "فصل مه‌ها چیست؟ — معرفی اثر و گردهمایی خانواده",
    "وداع‌های رؤیا — آماده‌سازی برای سفری بی‌بازگشت",
    "جهنم خالی — استعفای لوسیفر و پایان یک عصر",
    "بازار خدایان — اسطوره‌ها در آستانهٔ یک قلمرو خالی",
    "مذاکره‌ها و تهدیدها — سیاست کیهانی و گروگان‌گیری نادا",
    "بخشش نادا — نقطهٔ چرخش اخلاقی رؤیا",
    "سپردن کلید — تعادل جدید میان بهشت و جهنم",
    "لوسیفر در ساحل — آزادی، بی‌هدفی و پایان یک نقش",
    "جهنم جدید — آیا رستگاری ممکن است؟",
    "تولد دوباره — چرخهٔ بخشش و رهایی",
]

def read_wav(p):
    with wave.open(str(p)) as w:
        sr, n, sw, ch = w.getframerate(), w.getnframes(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return x, sr

def write_wav(p, x, sr):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def dur(p, x=None, sr=24000):
    return len(x) / sr

def compress_pauses(x, sr, thresh=0.004, keep=0.40, mindur=0.5):
    """سکوت‌های طولانی‌تر از mindur را به keep ثانیه برش می‌زند؛ ابتدا/انتها حذف کامل."""
    win = int(0.01 * sr)
    n = len(x) // win
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    sil = rms < thresh
    out, i = [], 0
    # ابتدا
    while i < n and sil[i]:
        i += 1
    while i < n:
        if not sil[i]:
            out.append(x[i * win:(i + 1) * win]); i += 1
        else:
            j = i
            while j < n and sil[j]:
                j += 1
            run = (j - i) * 0.01
            if j < n:  # انتها حذف کامل
                k = keep if run > mindur else run
                out.append(x[i * win:i * win + int(k * sr)])
            i = j
    return np.concatenate(out) if out else x

def main():
    raws = sorted(HERE.glob("scene_*.wav"))
    rawdir = HERE / "raw"; rawdir.mkdir(exist_ok=True)
    text = (ROOT / "narration_fa.txt").read_text(encoding="utf-8")
    words = {m.group(1): len(m.group(2).split()) for m in
             re.finditer(r"\[(SCENE_\d+)\]\n(.*?)(?=\n\[|\Z)", text, re.S)}
    rows, tmp = [], HERE / "tmp"; tmp.mkdir(exist_ok=True)

    # ۱) بکاپ + فشرده‌سازی مکث
    total1 = 0.0
    for f in raws:
        shutil.copy(f, rawdir / (f.stem + "_raw.wav"))
        x, sr = read_wav(f)
        d0 = dur(f, x, sr)
        y = compress_pauses(x, sr)
        write_wav(tmp / f.name, y, sr)
        total1 += dur(f, y, sr)
        rows.append({"file": f.name, "raw_sec": round(d0, 2), "trimmed_sec": round(dur(f, y, sr), 2)})
    print(f"جمع بعد از برش مکث‌ها: {total1:.1f}s")

    # ۲) سرعت یکنواخت با atempo تا رسیدن به هدف (شامل گپ‌ها)
    speech_target = TARGET_NARRATION - GAP * (len(rows) - 1)
    tempo = min(max(total1 / speech_target, 1.0), 1.22)
    print(f"atempo = {tempo:.3f}")
    finals = []
    for r in rows:
        src, dst = tmp / r["file"], HERE / r["file"]
        subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-af",
                        f"atempo={tempo:.4f},loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "24000", "-ac", "1", str(dst)], check=True)
        x, sr = read_wav(dst)
        r["final_sec"] = round(dur(dst, x, sr), 3)
        finals.append(dst)

    # ۳) چسباندن با گپ ۰٫۷ ثانیه‌ای
    sil = tmp / "gap.wav"
    write_wav(sil, np.zeros(int(GAP * 24000), dtype=np.float32), 24000)
    lst = tmp / "concat.txt"
    lines = []
    for k, f in enumerate(finals):
        lines.append(f"file '{f.resolve()}'")
        if k < len(finals) - 1:
            lines.append(f"file '{sil.resolve()}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(HERE / "narration_final.wav")], check=True)
    x, sr = read_wav(HERE / "narration_final.wav")
    total_narr = dur(None, x, sr)
    print(f"narration_final.wav = {total_narr:.1f}s | کل ویدیو با تیتراژ = {total_narr + 25:.1f}s")

    # ۴) timing.json — سکانس → فایل → بازه (هم در فایل روایت، هم در تایم‌لاین ویدیو)
    timing = {
        "project": "ویدیوی تحلیلی «فصل مه‌ها» — سندمن، نیل گیمن (ارائهٔ درسی)",
        "target_total_video_sec": 600,
        "opening_credits": {"start_sec": 0.0, "end_sec": 15.0, "type": "on-screen text, no narration"},
        "closing_credits": {"start_sec": round(15.0 + total_narr, 3), "end_sec": round(25.0 + total_narr, 3),
                            "type": "on-screen text, no narration"},
        "total_video_duration_sec": round(25.0 + total_narr, 3),
        "narration_file": "audio/narration_final.wav",
        "narration_format": "WAV 24000 Hz, mono, 16-bit",
        "tts_engine_note": "Piper 1.8.0 installed; Persian voice model (HuggingFace) unreachable in sandbox -> fallback neural TTS, voice selected by user audition (voice-00). Rebuild path: audio/make_narration_piper.py",
        "processing": f"trim+compress pauses; uniform atempo={tempo:.3f}; per-scene loudnorm I=-16; gap {GAP}s between scenes",
        "subtitles": "none (by project decision)",
        "scenes": [],
    }
    t_narr, t_video = 0.0, 15.0
    for k, r in enumerate(rows):
        tag = f"SCENE_{k + 1:02d}"
        timing["scenes"].append({
            "scene": tag, "title_fa": TITLES[k], "file": f"audio/{r['file']}",
            "words": words[tag], "duration_sec": r["final_sec"],
            "raw_tts_duration_sec": r["raw_sec"],
            "narration_range_sec": [round(t_narr, 3), round(t_narr + r["final_sec"], 3)],
            "video_range_sec": [round(t_video, 3), round(t_video + r["final_sec"], 3)],
            "tts_engine": "arena-neural-tts (fallback for Piper/Mana)", "voice_source": "voice-00",
        })
        t_narr += r["final_sec"] + GAP; t_video += r["final_sec"] + GAP
    (ROOT / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    print("timing.json نوشته شد.")

if __name__ == "__main__":
    main()
