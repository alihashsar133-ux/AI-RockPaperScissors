# -*- coding: utf-8 -*-
"""
ساخت پوستر/جدول تناوبی ۳۸ عنصر نخست به‌صورت PDF.

خروجی: output/periodic-table-first-38-elements.pdf  (A3 افقی)

نیازمندی‌ها:
    pip install reportlab arabic_reshaper python-bidi

اجرا:
    python build_periodic_table.py
"""

from __future__ import annotations

import os

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from elements_data import CATEGORIES, CATEGORY_ORDER, ELEMENTS

# ----------------------------------------------------------------------------- مسیرها
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "assets", "fonts")
OUT_DIR = os.path.join(HERE, "output")
OUT_PDF = os.path.join(OUT_DIR, "periodic-table-first-38-elements.pdf")

WEIGHTS = ["Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black"]
F = {}  # نام فونت ثبت‌شده در reportlab


def register_fonts():
    for w in WEIGHTS:
        path = os.path.join(FONT_DIR, f"Vazirmatn-{w}.ttf")
        if not os.path.exists(path):
            raise SystemExit(f"فونت یافت نشد: {path}")
        name = f"Vazir-{w}"
        pdfmetrics.registerFont(TTFont(name, path))
        F[w] = name


# ----------------------------------------------------------------------------- متن فارسی
def fa(text: str) -> str:
    """حروف‌چینی درست فارسی: تبدیل به فرم‌های چسبان + ترتیب بصری (bidi)."""
    return get_display(arabic_reshaper.reshape(text))


def _alpha_of(color):
    """آلفایِ درونِ خودِ شیءِ رنگ (reportlab هنگام setFillColor آن را نادیده می‌گیرد)."""
    a = getattr(color, "alpha", 1.0)
    return 1.0 if a is None else a


def _set(c, font, size, color, alpha=1.0):
    c.setFont(font, size)
    c.setFillColor(color)
    # setFillAlpha آلفایِ درونِ رنگ را بازنویسی می‌کند؛ پس باید در آن ضرب شود
    c.setFillAlpha(_alpha_of(color) * alpha)


def txt_r(c, x, y, s, font, size, color, alpha=1.0, shaped=True):
    """راست‌چین (پیش‌فرض: متن فارسی با shaping)."""
    c.saveState()
    _set(c, font, size, color, alpha)
    c.drawRightString(x, y, fa(s) if shaped else s)
    c.restoreState()


def txt_c(c, x, y, s, font, size, color, alpha=1.0, shaped=True):
    """وسط‌چین."""
    c.saveState()
    _set(c, font, size, color, alpha)
    c.drawCentredString(x, y, fa(s) if shaped else s)
    c.restoreState()


def txt_l(c, x, y, s, font, size, color, alpha=1.0, shaped=False):
    """چپ‌چین (پیش‌فرض: متن لاتین/عدد، بدون shaping)."""
    c.saveState()
    _set(c, font, size, color, alpha)
    c.drawString(x, y, fa(s) if shaped else s)
    c.restoreState()


def width_of(s, font, size, shaped=True):
    return pdfmetrics.stringWidth(fa(s) if shaped else s, font, size)


# ----------------------------------------------------------------------------- رنگ
def hx(h):
    return HexColor(h)


def mix(c1, c2, t):
    """ترکیب دو رنگ: t=0 -> c1 ، t=1 -> c2"""
    return Color(
        c1.red + (c2.red - c1.red) * t,
        c1.green + (c2.green - c1.green) * t,
        c1.blue + (c2.blue - c1.blue) * t,
    )


def lighten(c, t):
    return mix(c, Color(1, 1, 1), t)


def with_alpha(c, a):
    return Color(c.red, c.green, c.blue, a)


# رنگِ میانگینِ پس‌زمینه: چون توقف‌هایِ آلفادار در گرادیانِ reportlab «تخت» رندر می‌شوند،
# هاله‌ها را به‌جایِ محو شدن به شفاف، به همین رنگ محو می‌کنیم تا با زمینه یکی شوند.
BG_FADE = hx("#0E1526")


def rrect(c, x, y, w, h, r, fill=None, stroke=None, sw=0.8, alpha=1.0):
    c.saveState()
    c.setLineWidth(sw)
    c.setLineJoin(1)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setStrokeAlpha(_alpha_of(stroke) * alpha)
    if fill is not None:
        c.setFillColor(fill)
        c.setFillAlpha(_alpha_of(fill) * alpha)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke is not None else 0,
                fill=1 if fill is not None else 0)
    c.restoreState()


def radial_spot(c, cx, cy, r, colors, alpha=1.0):
    """لکهٔ نوریِ شعاعی که فقط تا شعاع r کشیده می‌شود.

    دو نکتهٔ مهم دربارهٔ reportlab:
      * بدون محدود کردن مسیر (clip)، دستور شیدینگ کل ناحیهٔ جاری را پر می‌کند؛
      * توقف‌هایِ رنگِ آلفادار باعث می‌شوند گرادیان یکدست (تخت) رندر شود؛
        پس رنگ‌ها باید کدر باشند و شفافیت با setFillAlpha اعمال شود.
    """
    c.saveState()
    p = c.beginPath()
    p.circle(cx, cy, r)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillAlpha(alpha)
    c.radialGradient(cx, cy, r, colors)
    c.restoreState()


def grad_rrect(c, x, y, w, h, r, top, bottom, border=None, bw=0.8, ba=1.0):
    """مستطیل گوشه‌گرد با پرشوندهٔ گرادیانی عمودی."""
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(x, y + h, x, y, [top, bottom])
    c.restoreState()
    if border is not None:
        c.saveState()
        c.setLineWidth(bw)
        c.setStrokeColor(border)
        c.setStrokeAlpha(_alpha_of(border))
        c.setLineJoin(1)
        c.roundRect(x, y, w, h, r, stroke=1, fill=0)
        c.restoreState()


# ----------------------------------------------------------------------------- هندسهٔ صفحه
PAGE_W, PAGE_H = landscape(A3)          # 1190.55 x 841.89 pt
ML = MR = 40.0
MT = 40.0

HEADER_H = 86.0
HEADER_RULE_Y = PAGE_H - MT - HEADER_H - 6          # خط جداکنندهٔ سربرگ
GROUP_NUM_Y = 700.0                                  # شمارهٔ گروه‌ها / برچسب دوره
GRID_TOP = 690.0

CARD_W = 54.0
CARD_H = 76.0
GAP_Y = 8.0
PERIOD_COL_W = 30.0

GRID_X0 = ML + PERIOD_COL_W
GRID_W = PAGE_W - ML - MR - PERIOD_COL_W
COL_PITCH = GRID_W / 18.0
GAP_X = COL_PITCH - CARD_W
GRID_H = 5 * CARD_H + 4 * GAP_Y
GRID_BOTTOM = GRID_TOP - GRID_H

BAND_TOP = GRID_BOTTOM - 22.0
BAND_BOTTOM = 58.0
FOOTER_Y = 40.0

INK = hx("#F4F7FC")        # متن اصلی
DIM = hx("#A9B5CE")        # متن ثانوی
FAINT = hx("#75819F")      # متن کم‌رنگ
HAIR = hx("#8FA0C4")       # خط‌های ظریف
CARD_BASE = hx("#131B2E")


def col_x(group):
    """x سمت چپ ستون یک گروه (۱ تا ۱۸)."""
    return GRID_X0 + (group - 1) * COL_PITCH


def row_y(period):
    """y پایین سطر یک دوره (۱ تا ۵)."""
    return GRID_TOP - (period - 1) * (CARD_H + GAP_Y) - CARD_H


# ----------------------------------------------------------------------------- پس‌زمینه
def draw_background(c):
    # گرادیان پایهٔ کل صفحه
    c.saveState()
    p = c.beginPath()
    p.rect(0, 0, PAGE_W, PAGE_H)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(0, PAGE_H, PAGE_W * 0.25, 0,
                     [hx("#0A0E1C"), hx("#101A31"), hx("#0C1322")])
    # هاله‌های نور — محو به رنگِ زمینه (توقف‌ها باید کدر باشند)
    c.setFillAlpha(1.0)
    c.radialGradient(PAGE_W * 0.88, PAGE_H * 0.94, 470,
                     [mix(hx("#3B4FA0"), BG_FADE, 0.15), BG_FADE])
    c.radialGradient(PAGE_W * 0.06, PAGE_H * 0.12, 400,
                     [mix(hx("#2C7C86"), BG_FADE, 0.30), BG_FADE])
    c.radialGradient(PAGE_W * 0.52, PAGE_H * 0.30, 420,
                     [mix(hx("#8A4F9E"), BG_FADE, 0.30), BG_FADE])
    c.restoreState()

    # شبکهٔ نقطه‌ای ظریف
    c.saveState()
    c.setFillColor(hx("#9FB4E0"))
    c.setFillAlpha(0.075)
    step = 26.0
    y = 24.0
    while y < PAGE_H - 12:
        x = 24.0
        while x < PAGE_W - 12:
            c.circle(x, y, 0.62, stroke=0, fill=1)
            x += step
        y += step
    c.restoreState()

    # دو مدار تزئینی در گوشه‌ها
    c.saveState()
    c.setLineWidth(0.7)
    for cx, cy, r, col, al in (
        (PAGE_W + 30, PAGE_H + 10, 300, hx("#6F86D6"), 0.10),
        (PAGE_W + 30, PAGE_H + 10, 400, hx("#6F86D6"), 0.07),
        (-60, -80, 250, hx("#5AC8C8"), 0.09),
        (-60, -80, 340, hx("#5AC8C8"), 0.06),
    ):
        c.setStrokeColor(col)
        c.setStrokeAlpha(al)
        c.circle(cx, cy, r, stroke=1, fill=0)
    c.restoreState()


# ----------------------------------------------------------------------------- سربرگ
def draw_atom_logo(c, cx, cy, r=33):
    c.saveState()
    # هاله
    radial_spot(c, cx, cy, r * 1.75,
                [mix(hx("#5B9DFF"), BG_FADE, 0.25), BG_FADE])
    ring_colors = [hx("#FF7A6B"), hx("#3FD9A0"), hx("#FFD75E")]
    c.saveState()
    c.translate(cx, cy)
    for i, ang in enumerate((0, 60, 120)):
        c.saveState()
        c.rotate(ang)
        c.setStrokeColor(ring_colors[i])
        c.setStrokeAlpha(0.85)
        c.setLineWidth(1.1)
        c.ellipse(-r, -r * 0.36, r, r * 0.36, stroke=1, fill=0)
        # الکترون
        c.setFillColor(lighten(ring_colors[i], 0.25))
        ex, ey = r * 0.72, r * 0.26
        c.circle(ex, ey, 2.3, stroke=0, fill=1)
        c.restoreState()
    c.restoreState()
    # هسته
    radial_spot(c, cx, cy, 11, [hx("#FFFFFF"), hx("#7FB2FF")])
    c.saveState()
    c.setFillColor(hx("#0A0E1C"))
    c.setFillAlpha(0.35)
    c.circle(cx, cy, 4.0, stroke=0, fill=1)
    c.restoreState()
    c.restoreState()


def draw_header(c):
    right = PAGE_W - MR
    title = "جدول تناوبی عنصرها"
    tsize = 31
    txt_r(c, right, PAGE_H - MT - 30, title, F["Black"], tsize, INK)
    tw = width_of(title, F["Black"], tsize)

    # میلهٔ گرادیانی کنار عنوان
    bar_x = right - tw - 16
    bar_y = PAGE_H - MT - 40
    c.saveState()
    p = c.beginPath()
    p.roundRect(bar_x, bar_y, 4.5, 50, 2.2)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(bar_x, bar_y + 50, bar_x, bar_y,
                     [hx("#FF7A6B"), hx("#B389FF"), hx("#3FD9A0")])
    c.restoreState()

    txt_r(c, right, PAGE_H - MT - 56,
          "۳۸ عنصر نخست — از هیدروژن (H) تا استرانسیم (Sr)",
          F["Medium"], 12.5, hx("#C2CDE4"))
    txt_r(c, right, PAGE_H - MT - 74,
          "عدد اتمی  ·  عدد جرمی  ·  جرم اتمی میانگین",
          F["Regular"], 10, FAINT)

    draw_atom_logo(c, ML + 44, PAGE_H - MT - 42, 32)
    txt_c(c, ML + 44, PAGE_H - MT - 84, "Z = 1 … 38", F["Medium"], 8.5, FAINT)

    # خط جداکنندهٔ سربرگ (گرادیان محو)
    c.saveState()
    p = c.beginPath()
    p.rect(ML, HEADER_RULE_Y, PAGE_W - ML - MR, 1.1)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillAlpha(0.9)
    c.linearGradient(ML, 0, PAGE_W - MR, 0,
                     [BG_FADE, mix(hx("#8FA0C4"), BG_FADE, 0.55), hx("#8A6CD8")])
    c.restoreState()


# ----------------------------------------------------------------------------- خانهٔ عنصر
def draw_card(c, x, y, w, h, rec, glow=True):
    z, sym, name, grp, per, A, weight, cat = rec
    col = hx(CATEGORIES[cat][1])

    if glow:  # هالهٔ نرم پشت کارت
        rrect(c, x - 2.2, y - 2.2, w + 4.4, h + 4.4, 9, fill=col, alpha=0.11)

    grad_rrect(
        c, x, y, w, h, 7,
        mix(col, CARD_BASE, 0.78), mix(col, CARD_BASE, 0.92),
        border=with_alpha(col, 0.42), bw=0.9,
    )

    # نوار رنگی بالای کارت
    c.saveState()
    c.setStrokeColor(lighten(col, 0.18))
    c.setStrokeAlpha(0.95)
    c.setLineWidth(h * 0.034)
    c.setLineCap(1)
    c.line(x + w * 0.22, y + h - h * 0.062, x + w * 0.78, y + h - h * 0.062)
    c.restoreState()

    # عدد اتمی (چپ) و عدد جرمی (راست)
    nsize = w * 0.175
    nbase = y + h * 0.755
    txt_l(c, x + w * 0.115, nbase, str(z), F["ExtraBold"], nsize, lighten(col, 0.42))
    txt_r(c, x + w * 0.885, nbase, str(A), F["Medium"], nsize, hx("#93A1C0"))

    # نماد شیمیایی
    ssize = w * 0.415
    txt_c(c, x + w / 2, y + h * 0.495, sym, F["Bold"], ssize, INK, shaped=False)

    # نام فارسی (با کوچک‌سازی خودکار)
    nmsize = w * 0.148
    maxw = w * 0.82
    while nmsize > w * 0.105 and width_of(name, F["Regular"], nmsize) > maxw:
        nmsize -= 0.15
    txt_c(c, x + w / 2, y + h * 0.352, name, F["Regular"], nmsize, hx("#BAC5DD"))

    # جرم اتمی میانگین
    px0, px1 = x + w * 0.105, x + w * 0.895
    py0 = y + h * 0.072
    ph = h * 0.175
    rrect(c, px0, py0, px1 - px0, ph, 4.2,
          fill=with_alpha(hx("#DCE6FA"), 0.075),
          stroke=with_alpha(hx("#DCE6FA"), 0.10), sw=0.6)
    vsize = w * 0.155
    while vsize > w * 0.10 and width_of(weight, F["SemiBold"], vsize, shaped=False) > (px1 - px0 - 6):
        vsize -= 0.15
    txt_c(c, x + w / 2, py0 + ph * 0.27, weight, F["SemiBold"], vsize,
          hx("#E8EEFA"), shaped=False)


def draw_grid(c):
    # شمارهٔ گروه‌ها + برچسب‌ها
    for g in range(1, 19):
        txt_c(c, col_x(g) + COL_PITCH / 2, GROUP_NUM_Y, str(g),
              F["Medium"], 9.5, FAINT, shaped=False)
    txt_c(c, ML + PERIOD_COL_W / 2 - 2, GROUP_NUM_Y, "دوره", F["Medium"], 8.5, FAINT)
    txt_r(c, PAGE_W - MR + 6, GROUP_NUM_Y, "گروه", F["Medium"], 8.5, FAINT)

    # شمارهٔ دوره‌ها
    for p in range(1, 6):
        y = row_y(p)
        txt_c(c, ML + PERIOD_COL_W / 2 - 2, y + CARD_H / 2 - 3.5, str(p),
              F["Medium"], 10, FAINT, shaped=False)

    # خانه‌ها
    for rec in ELEMENTS:
        z, sym, name, grp, per, A, weight, cat = rec
        draw_card(c, col_x(grp) + GAP_X / 2, row_y(per), CARD_W, CARD_H, rec)

    # ناحیهٔ خالی دورهٔ پنجم (عنصر ۳۹ به بعد)
    x0 = col_x(3) + GAP_X / 2 - 3
    x1 = col_x(18) + GAP_X / 2 + CARD_W + 3
    y0 = row_y(5) - 3
    y1 = y0 + CARD_H + 6
    c.saveState()
    c.setDash(3, 4)
    c.setLineWidth(0.8)
    c.setStrokeColor(HAIR)
    c.setStrokeAlpha(0.22)
    c.roundRect(x0, y0, x1 - x0, y1 - y0, 8, stroke=1, fill=0)
    c.restoreState()
    txt_c(c, (x0 + x1) / 2, (y0 + y1) / 2 - 3.5,
          "ادامهٔ جدول — عنصر ۳۹ (Y) و عنصرهای پس از آن",
          F["Regular"], 9.5, with_alpha(HAIR, 0.55))


# ----------------------------------------------------------------------------- نوار پایینی
def panel(c, x, y, w, h, title):
    rrect(c, x, y, w, h, 14, fill=with_alpha(hx("#DCE6FA"), 0.028),
          stroke=with_alpha(hx("#DCE6FA"), 0.075), sw=0.7)
    txt_r(c, x + w - 16, y + h - 20, title, F["SemiBold"], 11.5, hx("#D6DEF0"))


def draw_specimen(c, x, y, w, h, z=6):
    rec = next(r for r in ELEMENTS if r[0] == z)
    _, sym, name, grp, per, A, weight, cat = rec
    col = hx(CATEGORIES[cat][1])
    grad_rrect(c, x, y, w, h, 12,
               mix(col, CARD_BASE, 0.80), mix(col, CARD_BASE, 0.93),
               border=with_alpha(col, 0.45), bw=1.0)

    c.saveState()
    c.setStrokeColor(lighten(col, 0.15))
    c.setStrokeAlpha(0.9)
    c.setLineWidth(3.0)
    c.setLineCap(1)
    c.line(x + 40, y + h - 9, x + w - 40, y + h - 9)
    c.restoreState()

    # عدد اتمی
    txt_r(c, x + 100, y + h - 46, str(z), F["ExtraBold"], 25, lighten(col, 0.40), shaped=False)
    txt_r(c, x + 100, y + h - 61, "عدد اتمی (Z)", F["Regular"], 8.8, DIM)
    # عدد جرمی
    txt_r(c, x + w - 22, y + h - 46, str(A), F["ExtraBold"], 25, hx("#9FADCB"), shaped=False)
    txt_r(c, x + w - 22, y + h - 61, "عدد جرمی (A)", F["Regular"], 8.8, DIM)

    # نماد و نام
    txt_c(c, x + w / 2, y + h - 92, sym, F["Bold"], 36, INK, shaped=False)
    txt_c(c, x + w / 2, y + h - 108, name, F["Regular"], 11.5, hx("#C6D0E6"))

    # جداکننده
    c.saveState()
    c.setStrokeColor(HAIR)
    c.setStrokeAlpha(0.22)
    c.setLineWidth(0.8)
    c.line(x + 26, y + h - 118, x + w - 26, y + h - 118)
    c.restoreState()

    # جرم اتمی میانگین
    pill_w = 214
    pill_x = x + (w - pill_w) / 2
    pill_y = y + 14
    rrect(c, pill_x, pill_y, pill_w, 26, 13,
          fill=with_alpha(hx("#DCE6FA"), 0.08),
          stroke=with_alpha(hx("#DCE6FA"), 0.12), sw=0.7)
    txt_c(c, x + w / 2, pill_y + 8.4, f"جرم اتمی میانگین:  {weight} u",
          F["SemiBold"], 11, hx("#EDF2FC"))


def draw_legend(c, x, y, w, h):
    chip_w = (w - 32 - 8) / 2
    chip_h = 30
    top = y + h - 34
    for i, key in enumerate(CATEGORY_ORDER):
        name, hexcol = CATEGORIES[key]
        col = hx(hexcol)
        r = i // 2
        ci = i % 2
        cx = x + 16 + ci * (chip_w + 8)
        cy = top - (r + 1) * chip_h - r * 8
        rrect(c, cx, cy, chip_w, chip_h, 8,
              fill=with_alpha(col, 0.10), stroke=with_alpha(col, 0.32), sw=0.7)
        rrect(c, cx + chip_w - 24, cy + chip_h / 2 - 5.5, 11, 11, 3.4, fill=col)
        txt_r(c, cx + chip_w - 32, cy + chip_h / 2 - 3.6, name, F["Medium"], 9.5,
              hx("#D6DEF0"))


def draw_notes(c, x, y, w, h):
    notes = [
        ("عدد اتمی (Z)", "شمار پروتون‌های هسته — گوشهٔ بالا-چپ هر خانه."),
        ("عدد جرمی (A)", "پروتون + نوترونِ فراوان‌ترین ایزوتوپ پایدار طبیعی؛"),
        ("", "گوشهٔ بالا-راست هر خانه."),
        ("جرم اتمی میانگین", "میانگین وزن‌دار جرم ایزوتوپ‌های طبیعی بر پایهٔ"),
        ("", "فراوانی آن‌ها، بر حسب واحد جرم اتمی (u)."),
        ("رنگ خانه", "نشان‌دهندهٔ دستهٔ عنصر است (راهنمای رنگ‌ها)."),
    ]
    right = x + w - 16
    cy = y + h - 42
    accent = hx("#8FA0C4")
    for i, (head, body) in enumerate(notes):
        if head:
            c.saveState()
            c.setFillColor(accent)
            c.setFillAlpha(0.55)
            c.circle(right - 4, cy + 3.2, 1.9, stroke=0, fill=1)
            c.restoreState()
            txt_r(c, right - 12, cy, head, F["SemiBold"], 9.8, hx("#C7D1E7"))
            bw = width_of(head, F["SemiBold"], 9.8)
            txt_r(c, right - 12 - bw - 7, cy, body, F["Regular"], 9.5, DIM)
        else:
            txt_r(c, right - 12, cy, body, F["Regular"], 9.5, DIM)
        cy -= 17.5

    cy -= 6
    c.saveState()
    c.setStrokeColor(HAIR)
    c.setStrokeAlpha(0.18)
    c.setLineWidth(0.7)
    c.line(x + 16, cy + 8, x + w - 16, cy + 8)
    c.restoreState()
    txt_r(c, right, cy - 6,
          "خانه‌های خالی، جای عنصرهایی با عدد اتمی بزرگ‌تر از ۳۸ است.",
          F["Regular"], 8.8, FAINT)
    txt_r(c, right, cy - 21,
          "جرم‌های اتمی: مقادیر استاندارد IUPAC-CIAAW (۲۰۲۱).",
          F["Regular"], 8.8, FAINT)


def draw_footer(c):
    txt_r(c, PAGE_W - MR, FOOTER_Y,
          "منبع: IUPAC CIAAW — جرم‌های اتمی استاندارد، ویرایش ۲۰۲۱",
          F["Regular"], 8.2, with_alpha(FAINT, 0.85))
    txt_l(c, ML, FOOTER_Y, "Vazirmatn · ReportLab", F["Regular"], 8.2,
          with_alpha(FAINT, 0.7), shaped=False)


# ----------------------------------------------------------------------------- ساخت PDF
def build(path=OUT_PDF):
    register_fonts()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("جدول تناوبی ۳۸ عنصر نخست")
    c.setAuthor("Arena.ai Agent Mode")
    c.setSubject("عدد اتمی، عدد جرمی و جرم اتمی میانگین برای عنصرهای ۱ تا ۳۸")
    c.setKeywords("periodic table, جدول تناوبی, IUPAC 2021, atomic weight")
    c.setCreator("build_periodic_table.py (ReportLab)")

    draw_background(c)
    draw_header(c)
    draw_grid(c)

    # سه ستون نوار پایینی
    gut = 10.0
    total_w = PAGE_W - ML - MR
    w_right = 360.0
    w_mid = 380.0
    w_left = total_w - w_right - w_mid - 2 * gut

    x_right = PAGE_W - MR - w_right
    x_mid = x_right - gut - w_mid
    x_left = ML

    bh = BAND_TOP - BAND_BOTTOM
    panel(c, x_right, BAND_BOTTOM, w_right, bh, "راهنمای خواندن خانهٔ عنصر")
    draw_specimen(c, x_right + 16, BAND_BOTTOM + 12, w_right - 32, 150)

    panel(c, x_mid, BAND_BOTTOM, w_mid, bh, "دسته‌بندی عنصرها (رنگ‌ها)")
    draw_legend(c, x_mid, BAND_BOTTOM, w_mid, bh)

    panel(c, x_left, BAND_BOTTOM, w_left, bh, "یادداشت‌ها")
    draw_notes(c, x_left, BAND_BOTTOM, w_left, bh)

    draw_footer(c)
    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    out = build()
    print(f"ساخته شد: {out}")
    print(f"اندازه: {os.path.getsize(out)/1024:.0f} KB")
