#!/usr/bin/env python3
"""رندرر فاز ۲ — معادل کد خالص huashu (بدون نیاز به مرورگر).

قواعد huashu اعمال‌شده: نما ≤۸ث؛ هر صحنه ۱ حرکت اصلی (دوربین/قهرمان) + ۲ حلقهٔ موتیف
(مهٔ شناور + ذرات)؛ ترکیب‌بندی متفاوت نماهای مجاور (چرخش قالب نما و حرکت دوربین)؛
نماهای صرفاً متنی فقط تیتراژ و سه واژهٔ سکانس ۷ (کمتر از ۱۰٪)؛ بدون زیرنویس.
خروجی: segments/seg_*.mp4 — ‎1920×1080 @24fps‎ بی‌صدا (صدا در مونتاژ نهایی).
"""
import argparse, json, math, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "pylibs"))
import numpy as np
from PIL import Image, ImageDraw
import imageio_ffmpeg
import stylelib as S

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent.parent
W, H, FPS = 1920, 1080, 24
OW, OH = 2200, 1238
SEGDIR = ROOT / "segments"; SEGDIR.mkdir(exist_ok=True)
STITLES = ["گردهمایی خانواده", "وداع‌های رؤیا", "جهنم خالی", "بازار خدایان", "مذاکره‌ها و تهدیدها",
           "بخشش نادا", "سپردن کلید", "لوسیفر در ساحل", "جهنم جدید", "تولد دوباره"]

def place(bg, sprite, cx, cy, h_frac):
    th = int(OH * h_frac); tw = int(sprite.width * th / sprite.height)
    sp = sprite.resize((tw, th), Image.LANCZOS)
    bg.paste(sp, (int(OW * cx - tw / 2), int(OH * cy - th / 2)), sp)
    return bg

def figure_at(bg, cx, base_y, h_frac, **kw):
    sp = S.spr_figure(640, **kw)
    th = int(OH * h_frac); tw = int(sp.width * th / sp.height)
    sp = sp.resize((tw, th), Image.LANCZOS)
    bg.paste(sp, (int(OW * cx - tw / 2), int(OH * base_y - th)), sp)
    return bg

def build_bg(key, idx):
    """برگرداندن (پس‌زمینهٔ اووراسکن, فرادادهٔ نما) — قالب‌ها بر اساس idx می‌چرخند."""
    seed = abs(hash((key, idx))) % 100000
    v = idx % 4
    meta = {"hero": None, "keyword": None, "waves": False, "particle": "dust",
            "pcolor": (200, 208, 230), "mist": ((203, 212, 235), 50), "seed": seed}
    if key == "open":
        bg = S.env_mistfield(OW, OH, seed)
        bg = S.glow(bg, OW * 0.5, OH * 0.20, int(OH * 0.22), (70, 60, 20), 85)
        place(bg, S.spr_key(560), 0.5, 0.20, 0.24)
        meta["particle"] = "dust"
    elif key == "s01":
        bg = S.env_garden(OW, OH, seed, 1 if v in (0, 3) else 0)
        if v == 1:
            place(bg, S.spr_book(620), 0.34, 0.46, 0.42)
        if v == 2:
            figure_at(bg, 0.62, 0.80, 0.44, cloak=(18, 18, 26), rim=(215, 175, 105), ruby=True)
            figure_at(bg, 0.40, 0.80, 0.36, cloak=(24, 20, 24), rim=(230, 200, 150))
        meta.update(particle="leaves", pcolor=(180, 130, 64), mist=((225, 205, 170), 44))
    elif key == "s02":
        bg = S.env_castle(OW, OH, seed, v % 2)
        if v == 1:
            figure_at(bg, 0.42, 0.84, 0.52, ruby=True)
        if v == 3:
            figure_at(bg, 0.66, 0.84, 0.62, ruby=True)
        if v == 2:
            place(bg, S.spr_key(520, gold=(196, 202, 220), dark=(110, 118, 140)), 0.5, 0.46, 0.4)
        bg = S.brush_strokes(bg, seed, [(70, 95, 150), (120, 140, 190), (45, 60, 105), (180, 190, 220)], 300, 52, swirl=True)
        meta.update(particle="dust", pcolor=(190, 200, 225))
    elif key == "s03":
        bg = S.env_hell(OW, OH, seed, 0 if v in (0, 3) else 1)
        if v == 1:
            figure_at(bg, 0.5, 0.88, 0.58, white=True, wings=True, rim=(255, 170, 110))
        if v == 2:
            meta["hero"] = ("feather", S.spr_feather(460))
        if v == 3:
            bg = S.glow(bg, OW * 0.5, OH * 0.48, int(OH * 0.26), (110, 70, 15), 95)
            place(bg, S.spr_key(620), 0.5, 0.48, 0.46)
        meta.update(particle="ash", pcolor=(200, 190, 180), mist=((210, 160, 140), 40))
    elif key == "s04":
        bg = S.env_castle(OW, OH, seed, 1, banners=True)
        if v == 0:
            for i, fx in enumerate((0.28, 0.42, 0.56, 0.7)):
                figure_at(bg, fx, 0.84, 0.40 + 0.04 * (i % 2), cloak=(20 + i * 8, 20, 30), rim=(200, 180, 140))
            place(bg, S.spr_raven(220), 0.2, 0.2, 0.1); place(bg, S.spr_raven(180), 0.8, 0.16, 0.09)
        if v == 1:
            figure_at(bg, 0.36, 0.84, 0.5, white=True, wings=True)
            figure_at(bg, 0.62, 0.84, 0.5, cloak=(24, 24, 36), wings=True)
        if v == 2:
            for i, fx in enumerate((0.22, 0.5, 0.78)):
                figure_at(bg, fx, 0.84, 0.46, cloak=(30, 22, 20 + i * 10), rim=(230, 170, 90))
        if v == 3:
            figure_at(bg, 0.5, 0.84, 0.66, ruby=True)
        meta.update(particle="dust", pcolor=(220, 200, 160))
    elif key == "s05":
        bg = S.env_castle(OW, OH, seed, 1, base_top=(34, 24, 34), base_bot=(14, 10, 18), accent=(200, 120, 110))
        if v in (0, 2):
            meta["hero"] = ("eye", S.spr_eye_blob(680, seed % 97))
        if v == 1:
            figure_at(bg, 0.34, 0.84, 0.5, ruby=True); figure_at(bg, 0.66, 0.84, 0.44, cloak=(36, 14, 16), rim=(200, 80, 70))
            place(bg, S.spr_key(420), 0.5, 0.62, 0.26)
        if v == 3:
            bg = S.glow(bg, OW * 0.5, OH * 0.5, int(OH * 0.3), (40, 50, 90), 80)
            figure_at(bg, 0.5, 0.86, 0.68, ruby=True)
        meta.update(particle="embers", pcolor=(240, 140, 80), mist=((200, 170, 180), 48))
    elif key == "s06":
        if v == 1:
            bg = S.env_savanna(OW, OH, seed)
            figure_at(bg, 0.44, 0.76, 0.40, cloak=(60, 36, 20), rim=(255, 205, 120))
            figure_at(bg, 0.58, 0.76, 0.44, cloak=(20, 20, 30), rim=(255, 205, 120), ruby=True)
        elif v == 3:
            bg = S.env_mistfield(OW, OH, seed, top=(120, 126, 140), bot=(200, 202, 205))
            figure_at(bg, 0.38, 0.82, 0.42, cloak=(30, 30, 40), rim=(255, 240, 210), ruby=True)
            figure_at(bg, 0.64, 0.82, 0.40, cloak=(90, 70, 60), rim=(255, 240, 210))
            meta["hero"] = ("breathe", None)
        else:
            bg = S.env_room(OW, OH, seed)
            figure_at(bg, 0.36, 0.84, 0.5, ruby=True); figure_at(bg, 0.60, 0.84, 0.46, cloak=(40, 34, 40), rim=(240, 220, 180))
        bg = S.brush_strokes(bg, seed, [(90, 110, 160), (200, 160, 95)], 100, 20, swirl=True)
        meta.update(particle="dust", pcolor=(235, 220, 190), mist=((230, 220, 200), 50))
    elif key == "s07":
        bg = S.env_castle(OW, OH, seed, 1, base_top=(36, 48, 84), base_bot=(16, 20, 40), accent=(240, 220, 160))
        kws = {1: "کلید", 3: "جهنم", 5: "تعادل"}
        if idx in kws:
            meta["keyword"] = kws[idx]
        if v == 0:
            bg = S.glow(bg, OW * 0.5, OH * 0.46, int(OH * 0.28), (110, 85, 25), 90)
            place(bg, S.spr_scales(640), 0.5, 0.48, 0.5)
        if v == 2:
            figure_at(bg, 0.38, 0.84, 0.52, cloak=(22, 22, 34), wings=True)
            figure_at(bg, 0.62, 0.84, 0.52, white=True, wings=True)
            place(bg, S.spr_key(420), 0.5, 0.58, 0.28)
        if v == 3 and idx != 3:
            meta["hero"] = ("key", S.spr_key(560))
        meta.update(particle="dust", pcolor=(240, 226, 180))
    elif key == "s08":
        bg = S.env_beach(OW, OH, seed, v % 2)
        meta.update(waves=True, particle="dust", pcolor=(255, 215, 180), mist=((240, 200, 180), 28))
    elif key == "s09":
        bg = S.env_hell(OW, OH, seed, 1, new=True)
        if v in (0, 2):
            figure_at(bg, 0.44, 0.86, 0.5, white=True, wings=True, rim=(255, 226, 150))
            figure_at(bg, 0.58, 0.86, 0.5, cloak=(26, 24, 32), wings=True, rim=(255, 226, 150))
        if v == 1:
            bg = S.glow(bg, OW * 0.5, OH * 0.4, int(OH * 0.24), (120, 90, 30), 80)
            place(bg, S.spr_key(520), 0.5, 0.44, 0.38)
        meta.update(particle="embers", pcolor=(230, 160, 90), mist=((215, 185, 160), 42))
    elif key == "s10":
        if v == 1:
            bg = S.env_castle(OW, OH, seed, 0)
        else:
            bg = S.env_room(OW, OH, seed)
            place(bg, S.spr_cradle(600), 0.44, 0.62, 0.4)
            if v == 0:
                figure_at(bg, 0.70, 0.84, 0.54, ruby=True)
            meta["hero"] = ("breathe", None)
        meta.update(particle="dust", pcolor=(200, 212, 240))
    elif key == "close":
        bg = S.env_mistfield(OW, OH, seed)
        place(bg, S.spr_key(460), 0.5, 0.30, 0.24)
    bg = S.vignette(bg, 0.38)
    return bg, meta

def cam_rect(mode, t, dur):
    p = 0.5 if dur <= 0 else min(1, max(0, t / dur))
    ease = p * p * (3 - 2 * p)
    if mode == "push":
        cw = 2080 - 300 * ease; cx = OW / 2; cy = OH / 2
    elif mode == "pull":
        cw = 1780 + 300 * ease; cx = OW / 2; cy = OH / 2
    elif mode == "panL":
        cw = 1920; cx = OW / 2 + 110 - 220 * ease; cy = OH / 2
    elif mode == "panR":
        cw = 1920; cx = OW / 2 - 110 + 220 * ease; cy = OH / 2
    else:
        cw = 2000; cx = OW / 2 + 18 * math.sin(t * 0.25); cy = OH / 2 + 10 * math.cos(t * 0.2)
    ch = cw * 9 / 16
    x = min(max(0, cx - cw / 2), OW - cw); y = min(max(0, cy - ch / 2), OH - ch)
    return (int(x), int(y), int(x + cw), int(y + ch))

def make_particles(seed, n=85):
    rng = np.random.default_rng(seed)
    return (rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(-9, 9, n), rng.uniform(-6, 6, n),
            rng.uniform(0.3, 1.0, n), rng.uniform(0, 6.28, n), rng.uniform(1.0, 3.0, n))

_GLOW = {}
def soft_glow(peak):
    if peak not in _GLOW:
        yy, xx = np.mgrid[0:256, 0:256]
        r = np.sqrt((xx - 128) ** 2 + (yy - 128) ** 2) / 128.0
        a = (np.clip(1 - r, 0, 1) ** 2 * peak).astype(np.uint8)
        im = np.zeros((256, 256, 4), np.uint8); im[:, :, :3] = (255, 216, 156); im[:, :, 3] = a
        _GLOW[peak] = Image.fromarray(im, "RGBA")
    return _GLOW[peak]

def draw_particles(d, P, t, kind, color):
    x0, y0, vx, vy, sp, ph, sz = P
    if kind == "ash": vy = -np.abs(vy) - 6
    if kind == "embers": vy = np.abs(vy) * 0.7 + 2; vx = vx * 0.5
    if kind == "leaves": vy = np.abs(vy) + 5
    x = (x0 + vx * t * sp + 16 * np.sin(t * 0.7 * sp + ph)) % W
    y = (y0 + vy * t * sp + 10 * np.cos(t * 0.5 * sp + ph)) % H
    for i in range(len(x)):
        a = int(26 + 48 * (0.5 + 0.5 * math.sin(t * sp[i] + ph[i])))
        s = sz[i] * (2.2 if kind == "leaves" else 1.0)
        if kind == "leaves":
            d.ellipse([x[i] - s, y[i] - s * 0.45, x[i] + s, y[i] + s * 0.45], fill=color + (a,))
        else:
            d.ellipse([x[i] - s, y[i] - s, x[i] + s, y[i] + s], fill=color + (a,))

def draw_waves(d, t):
    for k in range(6):
        yb = H * (0.56 + k * 0.045); pts = []
        for x in range(0, W + 1, 48):
            pts.append((x, yb + 7 * math.sin(x * 0.006 + t * (1.1 + k * 0.13) + k * 1.7)))
        d.line(pts, fill=(255, 205, 150, int(120 - k * 13)), width=3)

def text_block(d, lines, font, cx, cy, color, alpha=255, lh=1.65):
    hs = [d.textbbox((0, 0), S.fa(x), font=font)[3] for x in lines]
    total = sum(hs) * lh; y = cy - total / 2
    for x, hh in zip(lines, hs):
        d.text((cx, y + hh / 2), S.fa(x), font=font, fill=color + (int(alpha),), anchor="mm")
        y += hh * lh

def envelope(t, a, b, fade=0.8):
    if t < a or t > b: return 0.0
    return min(1.0, (t - a) / fade, (b - t) / fade)

def compose_frame(seg, bg, meta, mist1, mist2, P, cam, t_shot, t_seg, shot_dur):
    fr = bg.crop(cam_rect(cam, t_shot, shot_dur)).resize((W, H), Image.BILINEAR).convert("RGBA")
    d = ImageDraw.Draw(fr, "RGBA")
    if meta["waves"]:
        draw_waves(d, t_seg)
    hero = meta.get("hero")
    if hero:
        mode, sp = hero
        if mode == "feather":
            cyc = 7.0; p = (t_shot % cyc) / cyc
            x = W * (0.47 + 0.10 * math.sin(t_shot * 1.4)); y = H * (0.06 + 0.78 * p)
            s2 = sp.rotate(24 * math.sin(t_shot * 1.1), resample=Image.BICUBIC, expand=True)
            a = int(255 * min(1, 6 * min(p, 1 - p) + 0.15))
            tmp = s2.copy(); tmp.putalpha(tmp.getchannel("A").point(lambda v: v * a // 255))
            fr.alpha_composite(tmp, (int(x - tmp.width / 2), int(y - tmp.height / 2)))
        elif mode == "eye":
            s = 1 + 0.035 * math.sin(t_shot * 1.6)
            tw, th = int(W * 0.42 * s), int(W * 0.42 * s)
            s2 = sp.resize((tw, th), Image.BILINEAR)
            fr.alpha_composite(s2, (int(W * 0.5 - tw / 2), int(H * 0.46 - th / 2)))
        elif mode == "key":
            p = min(1, t_shot / 2.2); e = 1 - (1 - p) ** 3
            y = H * (0.22 + 0.24 * e); tw = int(W * 0.34)
            s2 = sp.resize((tw, tw), Image.BILINEAR)
            fr.alpha_composite(s2, (int(W * 0.5 - tw / 2), int(y - tw / 2)))
        elif mode == "breathe":
            gs = soft_glow(int(64 + 26 * (0.5 + 0.5 * math.sin(t_shot * 1.05))))
            r = int(H * 0.30)
            g2 = gs.resize((r * 2, r * 2), Image.BILINEAR)
            fr.alpha_composite(g2, (int(W * 0.44 - r), int(H * 0.58 - r)))
    # دو حلقهٔ موتیف: مه + ذرات
    for tile, (spd, yy) in ((mist1, (14, H * 0.62)), (mist2, (-9, H * 0.30))):
        off = int((t_seg * spd) % W)
        fr.alpha_composite(tile, (off - W, int(yy))); fr.alpha_composite(tile, (off, int(yy)))
    draw_particles(d, P, t_seg, meta["particle"], meta["pcolor"])
    if meta.get("keyword"):
        p = min(1, t_shot / 1.1); size = int(90 + 130 * (1 - (1 - p) ** 3))
        a = int(240 * envelope(t_shot, 0, shot_dur, 0.9))
        d.text((W / 2, H * 0.46), S.fa(meta["keyword"]), font=S.F("Bold", size), fill=(245, 230, 190, a), anchor="mm")
    if seg["key"].startswith("s") and seg["key"] not in ("open",):
        a = envelope(t_seg, 0.7, 3.6, 0.7)
        if a > 0:
            i = int(seg["key"][1:]) - 1
            txt = f"سکانس {i + 1} — {STITLES[i]}"
            fnt = S.F("Medium", 40); tw = d.textlength(S.fa(txt), font=fnt)
            x1, y1 = W - 56, H - 86
            d.rounded_rectangle([x1 - tw - 44, y1 - 40, x1 + 8, y1 + 40], 14, fill=(5, 6, 10, int(150 * a)))
            d.text((x1, y1), S.fa(txt), font=fnt, fill=(240, 232, 210, int(255 * a)), anchor="rm")
    if seg["key"] == "open":
        a1 = envelope(t_seg, 0.4, 5.4, 1.0)
        if a1 > 0:
            d.text((W / 2, H * 0.48), S.fa("فصل مه‌ها"), font=S.F("Bold", 150), fill=(240, 214, 160, int(255 * a1)), anchor="mm")
            d.text((W / 2, H * 0.61), S.fa("تحلیلی بر یک قوس از کمیک سندمن، نوشتهٔ نیل گیمن"), font=S.F("Regular", 44), fill=(205, 214, 235, int(255 * a1)), anchor="mm")
        a2 = envelope(t_seg, 5.2, 14.6, 1.0)
        if a2 > 0:
            fnt = S.F("Regular", 42)
            lines = S.wrap_fa(d, "این ویدیو یک تحلیل درسی دربارهٔ قوس «فصل مه‌ها» از مجموعهٔ کمیک «سندمن» نوشتهٔ نیل گیمن (نشر دی‌سی کامیکس) است. تمام تصاویر، تفسیرهای هنری اصیل و تمام متن، تحلیل شخصی است.", fnt, 1380)
            text_block(d, lines, fnt, W / 2, H * 0.56, (228, 230, 238), 255 * a2)
    if seg["key"] == "close":
        a = envelope(t_seg, 0.3, 9.8, 1.2)
        if a > 0:
            f1, f2 = S.F("Medium", 46), S.F("Regular", 34)
            lines = S.wrap_fa(d, "منبع: سندمن: فصل مه‌ها، شماره‌های ۲۱ تا ۲۸، نوشتهٔ نیل گیمن، نشر دی‌سی کامیکس. این ویدیو برای ارائهٔ درسی تهیه شده است.", f1, 1400)
            text_block(d, lines, f1, W / 2, H * 0.55, (235, 232, 222), 255 * a)
            d.text((W / 2, H * 0.76), S.fa("تصویر: انیمیشن کدمحور اصیل بر پایهٔ نظام huashu-art-motion — موسیقی: ساختهٔ اصیل پروژه"), font=f2, fill=(190, 196, 214, int(255 * a)), anchor="mm")
    return fr.convert("RGB")

def segments():
    t = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
    segs = [{"key": "open", "start": 0.0, "end": 15.0}]
    sc = t["scenes"]
    for i, s in enumerate(sc):
        end = sc[i + 1]["video_range_sec"][0] if i < len(sc) - 1 else s["video_range_sec"][1]
        segs.append({"key": f"s{i + 1:02d}", "start": s["video_range_sec"][0], "end": end})
    segs.append({"key": "close", "start": t["closing_credits"]["start_sec"], "end": t["total_video_duration_sec"]})
    return segs

CAMS = ["push", "panL", "static", "panR", "pull"]

def shot_plan(dur):
    n = max(1, math.ceil(dur / 7.4))
    return [dur / n] * n

def render_segment(seg, idx, overwrite=False):
    name = f"seg_{idx:02d}_{seg['key']}.mp4"
    out = SEGDIR / name
    f0, f1 = round(seg["start"] * FPS), round(seg["end"] * FPS)
    nframes = f1 - f0
    if out.exists() and not overwrite:
        print(f"[skip] {name}"); return out
    dur = nframes / FPS
    shots = shot_plan(dur)
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
           "-b:v", "9M", "-minrate", "8.2M", "-maxrate", "9.8M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-g", "48", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time(); written = 0
    try:
        for si, sd in enumerate(shots):
            bg, meta = build_bg(seg["key"], si)
            rgbm, peak = meta["mist"]
            mist1 = S.make_mist_tile(W, 380, meta["seed"] + 11, rgbm, peak)
            mist2 = S.make_mist_tile(W, 300, meta["seed"] + 23, rgbm, int(peak * 0.7))
            P = make_particles(meta["seed"] + 31)
            cam = CAMS[(si + idx) % len(CAMS)]
            sf = round(sd * FPS) if si < len(shots) - 1 else nframes - written
            for f in range(0, sf, 2):
                fr = compose_frame(seg, bg, meta, mist1, mist2, P, cam,
                                   (f + sum(round(x * FPS) for x in shots[:si])) / FPS - sum(shots[:si]),
                                   (written + f) / FPS, sd)
                b = fr.tobytes()
                p.stdin.write(b)
                if written + f + 1 < nframes:
                    p.stdin.write(b)
            written += sf
            el = time.time() - t0
            print(f"  {name} shot {si + 1}/{len(shots)} [{cam}] frames={written}/{nframes} {el:.0f}s ({written / max(el, 1):.1f} fps)", flush=True)
    finally:
        p.stdin.close(); p.wait()
    print(f"[done] {name}: {written} frames, {time.time() - t0:.0f}s -> {out} ({out.stat().st_size / 1e6:.1f} MB)", flush=True)
    return out

def stills():
    od = ROOT / "visuals" / "stills"; od.mkdir(exist_ok=True)
    imgs = []
    for idx, seg in enumerate(segments()):
        dur = seg["end"] - seg["start"]
        shots = shot_plan(dur); si = min(1, len(shots) - 1)
        bg, meta = build_bg(seg["key"], si)
        rgbm, peak = meta["mist"]
        m1 = S.make_mist_tile(W, 380, meta["seed"] + 11, rgbm, peak)
        m2 = S.make_mist_tile(W, 300, meta["seed"] + 23, rgbm, int(peak * 0.7))
        P = make_particles(meta["seed"] + 31)
        fr = compose_frame(seg, bg, meta, m1, m2, P, CAMS[(si + idx) % 5], 3.0, 3.0 + shots[0], shots[si])
        pth = od / f"seg_{idx:02d}_{seg['key']}.png"
        fr.resize((960, 540), Image.LANCZOS).save(pth); imgs.append(fr.resize((640, 360), Image.LANCZOS))
        print("still", pth, flush=True)
    sheet = Image.new("RGB", (640 * 3, 360 * 4), (0, 0, 0))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
    sheet.save(od / "contact_sheet.png")
    print("sheet", od / "contact_sheet.png")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--seg", type=int, default=-1)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.stills:
        stills()
    else:
        segs = segments()
        rng = [a.seg] if a.seg >= 0 else range(len(segs))
        for i in rng:
            render_segment(segs[i], i, a.force)
