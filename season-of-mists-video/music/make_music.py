#!/usr/bin/env python3
"""فاز ۳ — موسیقی و افکت اصیلِ سنتزی + میکس سه‌لایه.

همهٔ صداها از اسیلاتور و نویز ساخته می‌شوند؛ هیچ سمپل یا قطعهٔ ثالثی نیست
(سند تصمیم مجوز: MUSIC_LICENSE.md). خروجی: output/audio_mix_pre.wav
(استریو ۴۸k، پیش از loudnorm نهایی ‎-14 LUFS‎ در انکد مستر).
لایه‌ها: روایت (جلو) + پدهای چهار تم با داکینگ خودکار زیر روایت + افکت‌های امضا.
"""
import json, subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "pylibs"))
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent.parent
SR = 48000
rng = np.random.default_rng(20261026)

def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)

THEMES = {  # پیشرفت آکوردی هر تم (نت‌های میدی)
    "blue":   [[50, 53, 57, 64], [46, 50, 53, 57], [41, 48, 55, 57], [48, 52, 55, 59]],
    "hell":   [[38, 45, 51], [36, 43, 50], [38, 44, 50], [37, 43, 49]],
    "gold":   [[48, 55, 64, 62], [41, 53, 57, 64], [43, 55, 59, 62], [48, 52, 55, 59]],
    "sunset": [[41, 57, 60, 64], [48, 55, 59, 64], [45, 57, 60, 67], [43, 59, 62, 64]],
}

def pad_block(freqs, dur, amp, bright=1.0):
    n = int(dur * SR); t = np.arange(n, dtype=np.float64) / SR
    y = np.zeros(n)
    for i, f in enumerate(freqs):
        for det in (-1.5, 1.5):
            ph = rng.uniform(0, 6.28)
            y += np.sin(2 * np.pi * (f * (1 + det / 120000)) * t + ph)
            y += 0.42 * bright * np.sin(2 * np.pi * f * 2 * t + ph * 1.7)
            y += 0.16 * bright * np.sin(2 * np.pi * f * 3 * t + ph * 2.3)
        y *= (1 + 0.10 * np.sin(2 * np.pi * (0.05 + i * 0.013) * t))
    env = np.ones(n); m = int(min(n * 0.4, 2.6 * SR))
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, m))
    env[:m] = ramp; env[-m:] = ramp[::-1]
    return (y / max(1, len(freqs)) * amp * env).astype(np.float32)

def add_at(buf, sig, at_sec, chan_gain=(1.0, 1.0)):
    i0 = int(at_sec * SR); i1 = min(len(buf), i0 + len(sig))
    if i1 > i0:
        buf[i0:i1, 0] += sig[:i1 - i0] * chan_gain[0]
        buf[i0:i1, 1] += sig[:i1 - i0] * chan_gain[1]

def box_lp(x, k=480, passes=2):
    y = x.astype(np.float64)
    for _ in range(passes):
        c = np.concatenate([[0], np.cumsum(y)])
        y = (c[k:] - c[:-k]) / k
        y = np.pad(y, (k // 2, len(x) - len(y) - k // 2), mode="edge")[:len(x)]
    return y.astype(np.float32)

def noise_burst(dur, lp_k=240):
    return box_lp(rng.standard_normal(int(dur * SR)).astype(np.float32), lp_k)

def metallic_ping(t0_decay=0.35, base=2100.0):
    n = int(0.8 * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for f, a in ((base, 1.0), (base * 1.38, 0.6), (base * 2.1, 0.35), (320.0, 0.5)):
        y += a * np.sin(2 * np.pi * f * t) * np.exp(-t / t0_decay)
    return (y / 2.5).astype(np.float32)

def main():
    timing = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
    total = timing["total_video_duration_sec"]
    sc = timing["scenes"]
    bounds = [s["video_range_sec"] for s in sc]
    N = int(total * SR) + SR
    music = np.zeros((N, 2), np.float32)

    # خط زمانی تم‌ها (شروع، پایان، تم، حجم نسبی)
    TL = [(0.0, 15.0, "blue", 0.9),
          (bounds[0][0], bounds[0][1], "gold", 0.8),
          (bounds[1][0], bounds[1][1], "blue", 0.9),
          (bounds[2][0], bounds[2][1], "hell", 1.0),
          (bounds[3][0], bounds[3][1], "blue", 0.85),
          (bounds[4][0], bounds[4][1], "hell", 0.55),
          (bounds[5][0], sum(bounds[5]) / 2, "blue", 0.85),
          (sum(bounds[5]) / 2, bounds[5][1], "gold", 0.9),
          (bounds[6][0], bounds[6][1], "gold", 1.0),
          (bounds[7][0], bounds[7][1], "sunset", 1.0),
          (bounds[8][0], sum(bounds[8]) / 2, "hell", 0.8),
          (sum(bounds[8]) / 2, bounds[8][1], "gold", 0.8),
          (bounds[9][0], bounds[9][1], "blue", 0.8),
          (timing["closing_credits"]["start_sec"], total, "gold", 0.85)]
    for a, b, theme, vol in TL:
        chords = THEMES[theme]; bright = {"hell": 0.35, "gold": 1.15, "sunset": 1.0, "blue": 0.8}[theme]
        tsec, ci = a, 0
        while tsec < b - 4:
            blk = pad_block([hz(m) for m in chords[ci % len(chords)]], 11.4, 0.050 * vol, bright)
            add_at(music, blk, tsec, (0.94, 1.0))  # اختلاف ریز استریو
            tsec += 8.8; ci += 1
    print("music bed done, peak", float(np.abs(music).max()))

    # روایت ۴۸k
    tmp = ROOT / "music" / "_narr48.wav"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(ROOT / "audio" / "narration_final.wav"),
                    "-ar", "48000", "-ac", "1", str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        narr = (np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0)
    i0 = int(15.0 * SR)
    narr_full = np.zeros(N, np.float32); narr_full[i0:i0 + len(narr)] = narr

    # داکینگ: موسیقی زیر روایت خم می‌شود
    win = SR // 4
    _c = np.concatenate([[0.0], np.cumsum((narr_full ** 2).astype(np.float64))])
    _ms = (_c[win:] - _c[:-win]) / win
    _ms = np.pad(_ms, (win // 2, len(narr_full) - len(_ms) - win // 2), mode="edge")[:len(narr_full)]
    env = np.sqrt(_ms + 1e-9).astype(np.float32)
    env = box_lp(env, SR // 2, 1)
    gain = np.clip(1.0 / (1.0 + 7.0 * env), 0.34, 1.0).astype(np.float32)
    mix = music * gain[:, None]
    mix[:, 0] += narr_full; mix[:, 1] += narr_full

    # افکت‌های امضا
    s01, s03, s07, s08, s10 = bounds[0], bounds[2], bounds[6], bounds[7], bounds[9]
    page = noise_burst(0.6, 900) * np.hanning(int(0.6 * SR)).astype(np.float32)
    add_at(mix, page * 0.20, s01[0] + 1.2); add_at(mix, page * 0.16, s01[0] + 3.4)
    for dt, fr in ((5.0, 2100.0), (5.35, 2850.0), (5.8, 2400.0)):  # زنجیر کتاب تقدیر
        add_at(mix, metallic_ping(0.22, fr) * 0.20, s01[0] + dt)
    add_at(mix, metallic_ping(0.5, 1750.0) * 0.34, s03[0] + (s03[1] - s03[0]) * 0.70)   # کلید جهنم
    add_at(mix, metallic_ping(0.5, 1950.0) * 0.32, s07[0] + (s07[1] - s07[0]) * 0.55)   # سپردن کلید
    wind = box_lp(rng.standard_normal(int(22 * SR)).astype(np.float32), 2000)
    wenv = (0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, len(wind)))).astype(np.float32)
    add_at(mix, wind * wenv * 0.05, s03[0] + 1.0)
    wdur = s08[1] - s08[0] + 1.5
    waves = box_lp(rng.standard_normal(int(wdur * SR)).astype(np.float32), 1400)
    lfo = (0.55 + 0.45 * np.sin(np.linspace(0, wdur * 2 * np.pi / 7.0, len(waves)))).astype(np.float32)
    wv = waves * lfo; wv *= (0.075 / (np.abs(wv).max() + 1e-9))
    add_at(mix, wv.astype(np.float32), s08[0] - 0.5)
    for dt in (2.0, 7.5, 13.0):  # نفس آرام نوزاد (پالس نویز بسیار ملایم)
        br = noise_burst(1.1, 2600) * np.hanning(int(1.1 * SR)).astype(np.float32)
        add_at(mix, br * 0.035, s10[0] + dt)

    mix = mix[:int(total * SR)]
    peak = float(np.abs(mix).max()); mix *= (0.89 / peak)
    print(f"mix peak before norm {peak:.3f} -> 0.89 | {len(mix) / SR:.2f}s")
    out = ROOT / "output"; out.mkdir(exist_ok=True)
    with wave.open(str(out / "audio_mix_pre.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    tmp.unlink(missing_ok=True)
    print("saved output/audio_mix_pre.wav")

if __name__ == "__main__":
    main()
