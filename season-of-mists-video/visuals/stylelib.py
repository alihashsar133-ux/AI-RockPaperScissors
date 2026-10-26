#!/usr/bin/env python3
"""کتابخانهٔ تصویر «فصل مه‌ها» — تفسیر نقاشانهٔ اصیل، کد خالص (معادل scenes در huashu).

هیچ تصویر یا آرتِ کمیکی استفاده نمی‌شود؛ همهٔ فرم‌ها با چندضلعی و قلم‌مو ساخته می‌شوند.
شخصیت‌ها فقط سیلوئت و نشانه‌اند (بدون چهره)، طبق قاعدهٔ کیفیت شخصیت huashu.
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "pylibs"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

FONTD = Path(__file__).parent.parent / "assets" / "fonts"
_CACHE = {}
def F(name, size):
    k = (name, size)
    if k not in _CACHE:
        _CACHE[k] = ImageFont.truetype(str(FONTD / f"Vazirmatn-{name}.ttf"), size)
    return _CACHE[k]

def fa(s):
    return get_display(arabic_reshaper.reshape(s))

def wrap_fa(draw, s, font, max_w):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(fa(t), font=font) > max_w and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines

def jit(c, amt, rng):
    return tuple(int(max(0, min(255, v + rng.integers(-amt, amt + 1)))) for v in c)

def lerp_c(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def gradient(W, H, stops):
    """stops: [(pos0..1, (r,g,b)), ...] عمودی"""
    y = np.linspace(0, 1, H)
    rows = np.zeros((H, 3), np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        m = (y >= p0) & (y <= p1)
        t = ((y[m] - p0) / max(1e-6, p1 - p0))[:, None]
        rows[m] = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    rows[y < stops[0][0]] = stops[0][1]; rows[y > stops[-1][0]] = stops[-1][1]
    img = np.repeat(rows[:, None, :], W, axis=1)
    return Image.fromarray(img.astype(np.uint8), "RGB")

def add_noise_texture(img, seed, amt=14, scale=90):
    rng = np.random.default_rng(seed)
    W, H = img.size
    small = rng.integers(0, 256, (max(2, H // scale), max(2, W // scale)), dtype=np.uint8)
    tex = Image.fromarray(small, "L").resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(img).astype(np.float32)
    a += (np.asarray(tex).astype(np.float32)[:, :, None] - 128) / 128.0 * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

def brush_strokes(img, seed, colors, n=240, alpha=60, wmin=6, wmax=20, swirl=False):
    """ضربه‌قلم‌های پست‌امپرسیونیستی (سبک کارت ون‌گوگ huashu، با ترکیب تازه)"""
    rng = np.random.default_rng(seed)
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        L = rng.uniform(30, 130)
        ang = math.atan2(y - H * 0.45, x - W * 0.5) + math.pi / 2 if swirl else rng.uniform(-0.5, 0.5)
        x2, y2 = x + L * math.cos(ang), y + L * math.sin(ang) * 0.4
        c = jit(colors[int(rng.integers(0, len(colors)))], 22, rng)
        d.line([x, y, x2, y2], fill=c + (int(alpha * rng.uniform(0.5, 1.2)),),
               width=int(rng.integers(wmin, wmax + 1)))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def glow(img, cx, cy, r, color, peak=110):
    W, H = img.size
    g = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(g); gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=peak)
    g = g.filter(ImageFilter.GaussianBlur(r * 0.55))
    a = np.asarray(img).astype(np.float32)
    a += (np.asarray(g).astype(np.float32) / 255.0)[:, :, None] * np.array(color, np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

def vignette(img, strength=0.42):
    W, H = img.size
    yy, xx = np.mgrid[0:H, 0:W]
    r2 = ((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2
    m = np.clip(1 - strength * np.clip(r2 - 0.35, 0, None), 0, 1)
    a = np.asarray(img).astype(np.float32) * m[:, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

# ---------------- نمادها (اسپرایت RGBA) ----------------
def spr_key(S=520, gold=(222, 178, 92), dark=(120, 88, 34)):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = S * 0.30, S * 0.30, S * 0.185
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=gold + (255,), width=int(S * 0.045))
    d.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45], outline=dark + (255,), width=int(S * 0.02))
    x0, y0, x1, y1 = cx + r * 0.55, cy + r * 0.55, S * 0.90, S * 0.90
    d.line([x0, y0, x1, y1], fill=gold + (255,), width=int(S * 0.055))
    for t, l in [(0.72, 0.13), (0.86, 0.17)]:
        px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        d.line([px, py, px + S * 0.02, py + S * l], fill=gold + (255,), width=int(S * 0.04))
    d.line([cx - r * 0.5, cy - r * 0.6, cx + r * 0.1, cy - r * 0.85], fill=(255, 236, 180, 200), width=max(2, int(S * 0.014)))
    return im

def spr_book(S=560, cover=(96, 62, 38), page=(226, 208, 168)):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([S * 0.16, S * 0.24, S * 0.84, S * 0.80], 18, fill=cover + (255,))
    d.rounded_rectangle([S * 0.21, S * 0.28, S * 0.79, S * 0.75], 10, fill=page + (255,))
    d.line([S * 0.5, S * 0.28, S * 0.5, S * 0.75], fill=(170, 150, 110, 255), width=int(S * 0.012))
    rng = np.random.default_rng(7)
    for side in (0, 1):
        for i in range(6):
            y = S * (0.34 + i * 0.06); x0 = S * (0.26 if side == 0 else 0.55)
            d.line([x0, y, x0 + S * rng.uniform(0.11, 0.17), y], fill=(120, 100, 70, 200), width=max(2, int(S * 0.008)))
    for i in range(9):  # زنجیر روی جلد
        x = S * (0.20 + i * 0.075); y = S * 0.20 + (S * 0.05 if i % 2 else 0)
        d.ellipse([x, y, x + S * 0.06, y + S * 0.035], outline=(150, 140, 125, 255), width=max(2, int(S * 0.010)))
    return im

def spr_scales(S=560, gold=(214, 176, 96)):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = S * 0.5; w = max(3, int(S * 0.016))
    d.line([cx, S * 0.16, cx, S * 0.82], fill=gold + (255,), width=w)
    d.line([S * 0.16, S * 0.24, S * 0.84, S * 0.24], fill=gold + (255,), width=w)
    d.ellipse([cx - S * 0.035, S * 0.12, cx + S * 0.035, S * 0.19], fill=gold + (255,))
    for px in (S * 0.16, S * 0.84):
        d.line([px, S * 0.24, px - S * 0.085, S * 0.46], fill=gold + (255,), width=w // 2 + 1)
        d.line([px, S * 0.24, px + S * 0.085, S * 0.46], fill=gold + (255,), width=w // 2 + 1)
        d.pieslice([px - S * 0.11, S * 0.38, px + S * 0.11, S * 0.55], 0, 180, fill=gold + (255,))
    d.line([S * 0.38, S * 0.84, S * 0.62, S * 0.84], fill=gold + (255,), width=w)
    return im

def spr_feather(S=460, tone=(238, 240, 248)):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts_l = [(S * 0.5 + S * 0.001, S * 0.06)]
    for i in range(11):
        t = i / 10; pts_l.append((S * (0.5 - 0.175 * math.sin(t * math.pi)), S * (0.06 + 0.72 * t)))
    pts_r = [(S * (0.5 + 0.175 * math.sin(t * math.pi)), S * (0.06 + 0.72 * t)) for t in [i / 10 for i in range(10, -1, -1)]]
    d.polygon(pts_l + pts_r, fill=tone + (235,))
    d.line([S * 0.5, S * 0.05, S * 0.5, S * 0.92], fill=(190, 192, 205, 255), width=max(2, int(S * 0.012)))
    for i in range(1, 8):
        y = S * (0.12 + i * 0.085); L = S * 0.20 * math.sin((i / 8) * math.pi)
        d.line([S * 0.5, y, S * 0.5 - L, y + S * 0.07], fill=(205, 208, 220, 160), width=2)
        d.line([S * 0.5, y, S * 0.5 + L, y + S * 0.07], fill=(205, 208, 220, 160), width=2)
    return im

def spr_eye_blob(S=620, seed=3):
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    for i in range(26):
        a = i / 26 * 2 * math.pi; r = S * 0.36 * (0.82 + 0.30 * rng.random())
        pts.append((S * 0.5 + r * math.cos(a), S * 0.5 + r * 0.78 * math.sin(a)))
    d.polygon(pts, fill=(10, 6, 10, 245))
    # چشم سرخ
    ex, ey = S * 0.5, S * 0.48
    d.polygon([(ex - S * 0.17, ey), (ex, ey - S * 0.075), (ex + S * 0.17, ey), (ex, ey + S * 0.075)], fill=(176, 30, 26, 255))
    d.ellipse([ex - S * 0.035, ey - S * 0.045, ex + S * 0.035, ey + S * 0.045], fill=(30, 4, 4, 255))
    return im

def spr_figure(H=640, cloak=(14, 16, 26), rim=(150, 170, 205), ruby=False, white=False, wings=False):
    W = int(H * 0.52)
    im = Image.new("RGBA", (W * 2, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = W
    body = [(cx, H * 0.10), (cx + W * 0.20, H * 0.30), (cx + W * 0.30, H * 0.97),
            (cx + W * 0.10, H * 0.99), (cx - W * 0.10, H * 0.99), (cx - W * 0.30, H * 0.97), (cx - W * 0.20, H * 0.30)]
    if wings:
        for s in (-1, 1):
            wing = [(cx + s * W * 0.10, H * 0.30), (cx + s * W * 0.95, H * 0.08),
                    (cx + s * W * 0.78, H * 0.34), (cx + s * W * 0.92, H * 0.42),
                    (cx + s * W * 0.55, H * 0.58), (cx + s * W * 0.18, H * 0.62)]
            d.polygon(wing, fill=((196, 204, 224, 240) if white else (30, 30, 42, 235)), outline=((110, 116, 140, 200) if white else (60, 64, 84, 160)))
    d.polygon([(x + W * 0.03, y) for x, y in body], fill=rim + (120,))
    c = (232, 232, 238) if white else cloak
    d.polygon(body, fill=c + (255,))
    d.ellipse([cx - W * 0.11, H * 0.015, cx + W * 0.11, H * 0.165], fill=c + (255,))
    if ruby:
        d.polygon([(cx, H * 0.30), (cx + W * 0.045, H * 0.36), (cx, H * 0.43), (cx - W * 0.045, H * 0.36)], fill=(200, 40, 48, 255))
    return im

def spr_cradle(S=560, wood=(110, 78, 50), cloth=(220, 214, 200)):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.pieslice([S * 0.14, S * 0.34, S * 0.86, S * 0.78], 0, 180, fill=wood + (255,))
    d.rectangle([S * 0.14, S * 0.34, S * 0.86, S * 0.42], fill=wood + (255,))
    d.pieslice([S * 0.24, S * 0.22, S * 0.76, S * 0.5], 180, 360, fill=cloth + (255,))
    d.arc([S * 0.12, S * 0.52, S * 0.88, S * 0.9], 15, 165, fill=wood + (255,), width=int(S * 0.03))
    for x in (S * 0.3, S * 0.7):
        d.line([x, S * 0.40, x, S * 0.18], fill=wood + (255,), width=int(S * 0.022))
    d.line([S * 0.3, S * 0.18, S * 0.7, S * 0.18], fill=wood + (255,), width=int(S * 0.02))
    return im

def spr_raven(S=200):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); b = (8, 8, 12, 255)
    d.ellipse([S * 0.28, S * 0.38, S * 0.72, S * 0.62], fill=b)
    d.ellipse([S * 0.62, S * 0.26, S * 0.82, S * 0.46], fill=b)
    d.polygon([(S * 0.8, S * 0.36), (S * 0.97, S * 0.42), (S * 0.8, S * 0.46)], fill=b)
    d.polygon([(S * 0.32, S * 0.5), (S * 0.04, S * 0.62), (S * 0.34, S * 0.62)], fill=b)
    return im

# ---------------- محیط‌ها (پس‌زمینهٔ اووراسکن) ----------------
def sil_color(base, f):
    return tuple(int(v * f) for v in base)

def env_garden(W, H, seed, variant):
    rng = np.random.default_rng(seed)
    img = gradient(W, H, [(0, (122, 92, 52)), (0.55, (168, 128, 74)), (1, (74, 52, 30))])
    img = glow(img, W * 0.72, H * 0.22, int(H * 0.34), (120, 84, 30), 90)
    d = ImageDraw.Draw(img, "RGBA")
    # درختان خشک باغ تقدیر
    def branch(x, y, ang, L, wdt, depth):
        if depth == 0 or L < 8: return
        x2, y2 = x + L * math.cos(ang), y - L * math.sin(ang)
        d.line([x, y, x2, y2], fill=(38, 28, 18, 255), width=max(1, wdt))
        branch(x2, y2, ang + rng.uniform(0.15, 0.5), L * 0.72, max(1, wdt - 2), depth - 1)
        branch(x2, y2, ang - rng.uniform(0.15, 0.5), L * 0.72, max(1, wdt - 2), depth - 1)
    for fx in (0.12, 0.30, 0.86) if variant else (0.16, 0.80):
        branch(W * fx, H * 0.78, math.pi / 2 + rng.uniform(-0.1, 0.1), H * 0.17, int(H * 0.014), 5)
    d.rectangle([0, H * 0.76, W, H], fill=(56, 40, 24, 255))
    for _ in range(160):
        x, y = rng.uniform(0, W), rng.uniform(H * 0.77, H)
        d.ellipse([x, y, x + rng.uniform(6, 20), y + rng.uniform(3, 7)], fill=jit((150, 104, 52), 40, rng) + (160,))
    if variant == 1:  # میز سنگی گردهمایی و هفت سیلوئت
        cx, cy = W * 0.5, H * 0.70
        d.ellipse([cx - W * 0.20, cy - H * 0.035, cx + W * 0.20, cy + H * 0.045], fill=(44, 34, 24, 255))
        figs = []
        for i in range(7):
            t = i / 6; x = W * (0.30 + 0.40 * t); back = i % 2 == 0
            fh = int(H * (0.30 if back else 0.36))
            figs.append((spr_figure(fh, cloak=(16, 14, 20), rim=(210, 170, 100), ruby=(i == 3)), int(x - fh * 0.52), int(H * (0.62 if back else 0.66))))
        for sp, x, y in figs:
            img.paste(sp, (x, y), sp)
    return add_noise_texture(img, seed + 5, 12)

def env_castle(W, H, seed, variant, base_top=(22, 32, 58), base_bot=(10, 14, 28), accent=(172, 186, 214), banners=False):
    rng = np.random.default_rng(seed)
    img = gradient(W, H, [(0, base_top), (0.62, lerp_c(base_top, base_bot, 0.5)), (1, base_bot)])
    d = ImageDraw.Draw(img, "RGBA")
    if variant == 0:  # نمای بیرونی برج‌های قلعه
        for i, fx in enumerate((0.08, 0.30, 0.52, 0.74, 0.92)):
            tw, th = W * rng.uniform(0.07, 0.11), H * rng.uniform(0.42, 0.66)
            x, ytop = W * fx, H * 0.86 - th
            col = sil_color((52, 64, 96), 0.75 + 0.08 * i)
            d.rectangle([x, ytop, x + tw, H * 0.86], fill=col + (255,))
            d.polygon([(x - tw * 0.12, ytop), (x + tw * 0.5, ytop - H * 0.09), (x + tw * 1.12, ytop)], fill=sil_color(col, 0.7) + (255,))
            for wy in np.linspace(ytop + H * 0.05, H * 0.78, 4):
                if rng.random() < 0.75:
                    d.rectangle([x + tw * 0.38, wy, x + tw * 0.62, wy + H * 0.025], fill=(240, 196, 120, 230))
        d.rectangle([0, H * 0.84, W, H], fill=sil_color((30, 38, 60), 0.8) + (255,))
    else:  # تالار: طاق‌های نوک‌تیز و ستون
        for i in range(6):
            cx = W * (0.06 + i * 0.185); aw, ah = W * 0.115, H * 0.62
            col = sil_color((64, 78, 112), 0.9)
            d.pieslice([cx, H * 0.14, cx + aw, H * 0.14 + aw], 180, 360, fill=col + (255,))
            d.rectangle([cx, H * 0.14 + aw / 2, cx + aw, H * 0.82], fill=col + (255,))
            inner = lerp_c(base_bot, accent, 0.12)
            d.pieslice([cx + aw * 0.16, H * 0.16, cx + aw * 0.84, H * 0.16 + aw * 0.68], 180, 360, fill=inner + (255,))
            d.rectangle([cx + aw * 0.16, H * 0.16 + aw * 0.34, cx + aw * 0.84, H * 0.82], fill=inner + (255,))
            if banners:
                bc = [(150, 40, 42), (44, 90, 120), (160, 120, 40), (60, 110, 80), (120, 60, 130), (170, 90, 40)][i]
                bx = cx + aw * 0.30
                d.polygon([(bx, H * 0.20), (bx + aw * 0.4, H * 0.20), (bx + aw * 0.4, H * 0.42), (bx + aw * 0.2, H * 0.37), (bx, H * 0.42)], fill=bc + (235,))
        d.rectangle([0, H * 0.80, W, H], fill=sil_color((36, 46, 72), 0.85) + (255,))
        for i in range(9):
            d.line([W * i / 8, H * 0.80, W * (i / 8 - 0.06), H], fill=accent + (40,), width=2)
    return add_noise_texture(img, seed + 3, 10)

def env_hell(W, H, seed, variant, new=False):
    rng = np.random.default_rng(seed)
    top = (70, 44, 36) if new else (88, 34, 16)
    bot = (38, 26, 22) if new else (26, 10, 8)
    img = gradient(W, H, [(0, top), (0.55, lerp_c(top, bot, 0.55)), (1, bot)])
    img = glow(img, W * 0.5, H * 0.86, int(H * 0.4), (90, 32, 8) if not new else (60, 30, 16), 80)
    d = ImageDraw.Draw(img, "RGBA")
    for layer, f in ((0, 0.55), (1, 0.8)):
        pts = [(0, H)]
        x = 0
        while x < W:
            x += rng.uniform(W * 0.05, W * 0.13)
            pts.append((x, H * rng.uniform(0.30 + layer * 0.18, 0.62 + layer * 0.14)))
            pts.append((x + rng.uniform(10, 50), H * rng.uniform(0.55 + layer * 0.15, 0.8)))
        pts += [(W, H)]
        d.polygon(pts, fill=sil_color((40, 22, 18), f) + (255,))
    if variant == 0:  # دروازهٔ عظیم خالی
        cx, gw, gh = W * 0.5, W * 0.30, H * 0.62
        d.rectangle([cx - gw / 2 - W * 0.03, H * 0.86 - gh, cx - gw / 2, H * 0.86], fill=(16, 12, 12, 255))
        d.rectangle([cx + gw / 2, H * 0.86 - gh, cx + gw / 2 + W * 0.03, H * 0.86], fill=(16, 12, 12, 255))
        d.pieslice([cx - gw / 2 - W * 0.03, H * 0.86 - gh - gw * 0.35, cx + gw / 2 + W * 0.03, H * 0.86 - gh + gw * 0.35], 180, 360, fill=(16, 12, 12, 255))
        d.pieslice([cx - gw / 2, H * 0.86 - gh - gw * 0.28, cx + gw / 2, H * 0.86 - gh + gw * 0.28], 180, 360, fill=(8, 6, 8, 255))
        d.rectangle([cx - gw / 2, H * 0.86 - gh, cx + gw / 2, H * 0.86], fill=(8, 6, 8, 255))
    if not new:
        for _ in range(7):  # ترک‌های مذاب
            x, y = rng.uniform(0, W), rng.uniform(H * 0.78, H * 0.98)
            pts = [(x, y)]
            for _ in range(5):
                x += rng.uniform(-90, 130); y += rng.uniform(-12, 26); pts.append((x, y))
            d.line(pts, fill=(255, 120, 40, 190), width=int(rng.integers(2, 5)))
    else:  # شعاع نور رستگاری
        d.polygon([(W * 0.46, 0), (W * 0.55, 0), (W * 0.66, H * 0.88), (W * 0.36, H * 0.88)], fill=(255, 226, 150, 24))
    return add_noise_texture(img, seed + 9, 13)

def env_beach(W, H, seed, variant):
    img = gradient(W, H, [(0, (74, 48, 96)), (0.34, (176, 84, 74)), (0.5, (240, 146, 72)), (0.56, (120, 74, 92)), (0.78, (80, 60, 84)), (1, (52, 40, 52))])
    img = glow(img, W * 0.5, H * 0.50, int(H * 0.30), (150, 70, 20), 100)
    d = ImageDraw.Draw(img, "RGBA")
    d.pieslice([W * 0.435, H * 0.36, W * 0.565, H * 0.56], 180, 360, fill=(255, 196, 110, 255))
    rng = np.random.default_rng(seed)
    for i in range(26):
        y = H * (0.54 + i * 0.008); x = W * (0.5 + rng.uniform(-0.06, 0.06)); L = W * rng.uniform(0.01, 0.05)
        d.line([x - L, y, x + L, y], fill=(255, 190, 110, 150), width=2)
    d.rectangle([0, H * 0.84, W, H], fill=(44, 34, 40, 255))
    # پیکر نشسته رو به دریا
    cx = W * (0.68 if variant == 0 else 0.34); by = H * 0.90
    d.polygon([(cx - W * 0.035, by), (cx - W * 0.028, by - H * 0.10), (cx - W * 0.008, by - H * 0.155),
               (cx + W * 0.018, by - H * 0.15), (cx + W * 0.03, by - H * 0.09), (cx + W * 0.055, by)], fill=(18, 14, 22, 255))
    d.ellipse([cx - W * 0.016, by - H * 0.205, cx + W * 0.016, by - H * 0.145], fill=(18, 14, 22, 255))
    return add_noise_texture(img, seed + 2, 9)

def env_savanna(W, H, seed):  # فلش‌بک طلایی نادا
    img = gradient(W, H, [(0, (196, 120, 48)), (0.5, (232, 170, 84)), (1, (120, 72, 36))])
    img = glow(img, W * 0.30, H * 0.30, int(H * 0.3), (140, 80, 20), 90)
    d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(seed)
    for fx, s in ((0.68, 1.0), (0.16, 0.6)):
        x, y = W * fx, H * 0.74
        d.line([x, y, x + W * 0.01 * s, y - H * 0.20 * s], fill=(52, 34, 20, 255), width=int(H * 0.012 * s))
        for a in (-0.9, -0.4, 0.1, 0.55, 0.95):
            d.line([x + W * 0.01 * s, y - H * 0.20 * s, x + W * 0.11 * s * math.sin(a + math.pi / 2), y - H * (0.26 + 0.03 * abs(a)) * s],
                   fill=(52, 34, 20, 255), width=int(H * 0.006 * s))
        for ox, oy, ow in ((-0.10, -0.285, 0.11), (-0.045, -0.305, 0.12), (0.02, -0.29, 0.10), (0.07, -0.275, 0.08)):
            d.ellipse([x + W * ox * s, y + H * oy * s, x + W * (ox + ow) * s, y + H * (oy + 0.045) * s], fill=(58, 38, 22, 255))
    d.rectangle([0, H * 0.72, W, H], fill=(92, 54, 28, 255))
    for _ in range(240):
        x, y = rng.uniform(0, W), rng.uniform(H * 0.73, H)
        d.line([x, y, x + rng.uniform(-4, 4), y - rng.uniform(6, 18)], fill=jit((200, 150, 80), 40, rng) + (170,), width=2)
    return add_noise_texture(img, seed + 4, 12)

def env_room(W, H, seed, warm=False):
    base = gradient(W, H, [(0, (26, 32, 52)), (1, (12, 14, 26))]) if not warm else gradient(W, H, [(0, (70, 48, 34)), (1, (30, 20, 16))])
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle([W * 0.62, H * 0.10, W * 0.86, H * 0.58], outline=(140, 150, 180, 255), width=int(H * 0.012))
    d.rectangle([W * 0.63, H * 0.11, W * 0.85, H * 0.57], fill=(52, 64, 96, 255) if not warm else (150, 96, 52, 255))
    d.ellipse([W * 0.75, H * 0.15, W * 0.81, H * 0.25], fill=(238, 238, 235, 255))
    d.ellipse([W * 0.765, H * 0.14, W * 0.825, H * 0.24], fill=(52, 64, 96, 255) if not warm else (150, 96, 52, 255))
    d.polygon([(W * 0.63, H * 0.57), (W * 0.85, H * 0.57), (W * 0.70, H * 0.98), (W * 0.42, H * 0.98)], fill=(200, 210, 240, 26))
    d.rectangle([0, H * 0.80, W, H], fill=(14, 16, 26, 255))
    return add_noise_texture(base, seed + 6, 8)

def env_mistfield(W, H, seed, top=(18, 22, 44), bot=(8, 10, 20)):
    img = gradient(W, H, [(0, top), (1, bot)])
    img = brush_strokes(img, seed, [(60, 80, 130), (90, 110, 160), (40, 50, 90)], n=170, alpha=36, swirl=True)
    return vignette(add_noise_texture(img, seed + 1, 10), 0.35)

def make_mist_tile(W, H, seed, rgb=(205, 214, 235), peak=70):
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 256, (10, 60), dtype=np.uint8)
    a = Image.fromarray(small, "L").resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    alpha = (np.asarray(a).astype(np.float32) / 255.0 * peak).astype(np.uint8)
    yy = np.linspace(0, 1, H)
    fade = (np.sin(yy * math.pi) ** 1.5 * 255).astype(np.uint8)
    alpha = (alpha.astype(np.float32) * (fade / 255.0)[:, None]).astype(np.uint8)
    tile = np.zeros((H, W, 4), np.uint8); tile[:, :, :3] = rgb; tile[:, :, 3] = alpha
    return Image.fromarray(tile, "RGBA")
