#!/usr/bin/env python3
"""S4 renderer - "A Dream of a Thousand Cats", scene 04 (The Gathering).

Route B of the huashu-art-motion skill: the AI painted every layer, the code
moves them. Nothing is redrawn here - layers are transformed, the wax cross is
warped, mist and eye-light are modulated, the camera arcs.

    python3 tools/render_scene.py --spec scene_04/json_specs/clip_01.json \
        --out scene_04/clips/clip_01.mp4
    python3 tools/render_scene.py --spec ... --still 0,3.5,7.9 --still-out scene_04/frames/clip_01

The spec is the source of truth: duration, fps, palette, surreal signatures and
the cue list all come from it, and qa.py cross-checks the rendered clip against
the same file. Every cue type here is implemented in CUE_IMPL; an unknown cue
fails loudly instead of silently rendering a dead frame.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "scene_04" / "assets"

PIC_W, PIC_H = 1920, 804
OUT_W, OUT_H = 1920, 1080
BAR = (OUT_H - PIC_H) // 2

# parallax weight per layer: 0 = glued to the sky, >1 = closer than the subject
PARALLAX = {
    "bg": 0.42, "mist_back": 0.62, "eyes": 0.90, "cross": 1.0,
    "prophet": 1.0, "kitten": 1.16, "tabby": 1.16, "mist_front": 1.34,
}

# placement corrections measured against the keyframe (px in 1920x804 space)
PLACEMENT = {
    "cross": {"dx": 0, "dy": 0, "scale": 1.0},
    "prophet": {"dx": 26, "dy": 30, "scale": 1.0},
    "kitten": {"dx": 0, "dy": 0, "scale": 1.0},
    "tabby": {"dx": 0, "dy": 0, "scale": 1.0},
}


# --------------------------------------------------------------------------- #
# maths helpers
# --------------------------------------------------------------------------- #
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def smooth(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def sine_io(t):
    t = clamp01(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


EASES = {"linear": lambda t: clamp01(t), "sine_in_out": sine_io,
         "ease_out": ease_out, "smooth": smooth}


def progress(t, t0, t1, ease="sine_in_out"):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return EASES[ease]((t - t0) / (t1 - t0))


def affine_matrix(scale, rot, shear, dx, dy, anchor, origin):
    """Forward map: local layer pixel -> picture pixel."""
    ca, sa = math.cos(rot), math.sin(rot)
    R = np.array([[ca, -sa], [sa, ca]], np.float64)
    Sh = np.array([[1.0, shear], [0.0, 1.0]], np.float64)
    M = (np.array([[scale, 0.0], [0.0, scale]]) @ R @ Sh)
    a = np.array(anchor, np.float64)
    o = np.array(origin, np.float64)
    d = np.array([dx, dy], np.float64)
    return M, M @ (o - a) + a + d


def pil_coeffs(scale, dx, dy, anchor):
    """Inverse affine coefficients for PIL.transform (scale + translation)."""
    ax, ay = anchor
    inv = 1.0 / scale
    return (inv, 0.0, -((ax + dx) * inv) + ax,
            0.0, inv, -((ay + dy) * inv) + ay)


def sample_bilinear(src, xs, ys):
    h, w = src.shape[:2]
    xs = np.clip(xs, 0, w - 1.001)
    ys = np.clip(ys, 0, h - 1.001)
    x0 = xs.astype(np.int32)
    y0 = ys.astype(np.int32)
    fx = (xs - x0)[..., None]
    fy = (ys - y0)[..., None]
    a = src[y0, x0]
    b = src[y0, x0 + 1]
    c = src[y0 + 1, x0]
    d = src[y0 + 1, x0 + 1]
    return (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy)
            + c * (1 - fx) * fy + d * fx * fy)


def fast_interp(x, xp, fp):
    """np.interp without the per-call overhead, for monotonic xp."""
    i = np.searchsorted(xp, x, side="right") - 1
    i = np.clip(i, 0, len(xp) - 2)
    x0, x1 = xp[i], xp[i + 1]
    f0, f1 = fp[i], fp[i + 1]
    w = np.where(x1 > x0, (x - x0) / np.maximum(x1 - x0, 1e-6), 0.0)
    return f0 + (f1 - f0) * w


# --------------------------------------------------------------------------- #
# layers
# --------------------------------------------------------------------------- #
class Layer:
    def __init__(self, path, crop=True):
        im = Image.open(path).convert("RGBA")
        if im.size != (PIC_W, PIC_H):
            im = im.resize((PIC_W, PIC_H), Image.LANCZOS)
        arr = np.asarray(im).astype(np.float32) / 255.0
        if crop:
            alpha = arr[..., 3]
            ys, xs = np.where(alpha > 0.02)
            pad = 6
            x0, x1 = max(int(xs.min()) - pad, 0), min(int(xs.max()) + pad + 1, arr.shape[1])
            y0, y1 = max(int(ys.min()) - pad, 0), min(int(ys.max()) + pad + 1, arr.shape[0])
            arr = arr[y0:y1, x0:x1]
            self.ox, self.oy = x0, y0
        else:
            self.ox, self.oy = 0, 0
        self.pm = arr.copy()
        self.pm[..., :3] *= arr[..., 3:4]        # premultiplied, for numpy warps
        self.h, self.w = arr.shape[:2]
        self.pil = Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8), "RGBA")

    def empty(self):
        return Image.new("RGBA", (PIC_W, PIC_H), (0, 0, 0, 0))


def load_layers():
    return {
        "bg": Layer(A / "bg_plate.png", crop=False),
        "cross": Layer(A / "cross_rgba.png"),
        "prophet": Layer(A / "prophet_rgba.png"),
        "kitten": Layer(A / "kitten_rgba.png"),
        "tabby": Layer(A / "tabby_rgba.png"),
        "mist": Layer(A / "mist_rgba.png", crop=False),
        "eyes": Layer(A / "eyes_rgba.png", crop=False),
    }


def place_numpy(L, scale=1.0, rot=0.0, shear=0.0, dx=0.0, dy=0.0,
                anchor=(0.5, 0.5), data=None):
    """Affine a (cropped) layer in numpy and return a picture-space patch."""
    M, b = affine_matrix(scale, rot, shear, dx, dy,
                         (anchor[0] * PIC_W, anchor[1] * PIC_H), (L.ox, L.oy))
    corners = np.array([[0, 0], [L.w, 0], [0, L.h], [L.w, L.h]], np.float64)
    pts = corners @ M.T + b
    x0 = max(int(math.floor(pts[:, 0].min())) - 2, 0)
    y0 = max(int(math.floor(pts[:, 1].min())) - 2, 0)
    x1 = min(int(math.ceil(pts[:, 0].max())) + 2, PIC_W)
    y1 = min(int(math.ceil(pts[:, 1].max())) + 2, PIC_H)
    if x1 <= x0 or y1 <= y0:
        return None, (0, 0)
    xs = np.arange(x0, x1, dtype=np.float32) + 0.5
    ys = np.arange(y0, y1, dtype=np.float32) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    Mi = np.linalg.inv(M)
    qx = Mi[0, 0] * (gx - b[0]) + Mi[0, 1] * (gy - b[1])
    qy = Mi[1, 0] * (gx - b[0]) + Mi[1, 1] * (gy - b[1])
    src = L.pm if data is None else data
    patch = sample_bilinear(src, qx, qy)
    a = np.clip(patch[..., 3:4], 0, 1)
    rgb = np.where(a > 1e-4, patch[..., :3] / np.maximum(a, 1e-4), 0.0)
    out = np.concatenate([np.clip(rgb, 0, 1), a], axis=2) * 255.0
    return out.astype(np.uint8), (x0, y0)


def paste_patch(canvas_img, patch, off):
    if patch is None:
        return canvas_img
    canvas = canvas_img
    layer = Image.new("RGBA", (PIC_W, PIC_H), (0, 0, 0, 0))
    layer.paste(Image.fromarray(patch, "RGBA"), off)
    return Image.alpha_composite(canvas, layer)


def warp_cross(L, sag, arm):
    """Dalí wax: the upright droops, the arm tips bend down and stretch outward.

    Built as a proper forward map (source -> target) and inverted with a
    monotonic interpolation, so no column can fold back over another.
    """
    h, w = L.h, L.w
    cx = w * 0.5
    half = max(w * 0.5, 1.0)
    sag_px = 46.0 * sag
    arm_px = 38.0 * arm

    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    drop = np.abs(xs - cx) / half

    # horizontal: content is pushed away from the trunk, more at the tips
    xt = xs - np.sign(xs - cx) * (arm_px * 0.6) * drop ** 1.7
    tx = xs
    sx = np.interp(tx, xt, xs)

    # vertical: the tips drop, and the whole upper body melts downward
    arm_dy = arm_px * drop ** 2.1
    yt = ys + sag_px * ((h - ys) / h) ** 1.6
    ty = ys[:, None] - arm_dy[None, :]
    sy = np.interp(ty, yt, ys)

    return sample_bilinear(L.pm, np.broadcast_to(sx[None, :].astype(np.float32), (h, w)),
                           sy.astype(np.float32))


# --------------------------------------------------------------------------- #
# cue system
# --------------------------------------------------------------------------- #
class Ctx:
    def __init__(self, t, dur):
        self.t, self.dur = t, dur
        self.cam_pan = 0.0
        self.cam_zoom = 1.0
        self.cam_anchor = (PIC_W * 0.62, PIC_H * 0.42)
        self.cam_drift = (0.0, 0.0)
        self.cam_lift = 0.0
        self.cross_sag = 0.10
        self.cross_arm = 0.10
        self.prophet = {"scale": 1.0, "shear": 0.0, "dx": 0.0, "dy": 0.0}
        self.kitten = {"rot": 0.0, "scale": 1.0, "dy": 0.0}
        self.tabby = {"rot": 0.0, "shear": 0.0, "dy": 0.0}
        self.mist_back = {"dx": 0.0, "dy": 0.0, "alpha": 1.0}
        self.mist_front = {"dx": 0.0, "dy": 0.0, "alpha": 1.0}
        self.eye_gain = np.ones(64, np.float32)
        self.eye_glow = 1.0
        self.deep_eyes = 0.0
        self.moon_glow = 0.0
        self.exposure = 1.0
        self.stone_sway = 0.0


def cue_pan(c, p):
    c.cam_pan += p.get("value", 100.0) * progress(c.t, *p.get("t_range", [0, c.dur]),
                                                  p.get("ease", "sine_in_out"))


def cue_push(c, p):
    z0, z1 = p.get("from", 1.0), p.get("to", 1.06)
    k = progress(c.t, *p.get("t_range", [0, c.dur]), p.get("ease", "sine_in_out"))
    c.cam_zoom *= z0 + (z1 - z0) * k
    if "anchor" in p:
        c.cam_anchor = tuple(p["anchor"])


def cue_pull(c, p):
    cue_push(c, {**p, "from": p.get("from", 1.08), "to": p.get("to", 1.0)})


def cue_rise(c, p):
    """A slow tilt: every layer slides vertically together (composition change)."""
    k = progress(c.t, *p.get("t_range", [0, c.dur]), p.get("ease", "sine_in_out"))
    c.cam_lift += p.get("from", 0.0) + (p.get("to", 0.0) - p.get("from", 0.0)) * k


def cue_drift(c, p):
    amp, f, ph = p.get("value", 3.0), p.get("hz", 0.11), p.get("phase", 0.0)
    c.cam_drift = (amp * math.sin(2 * math.pi * f * c.t + ph),
                   amp * 0.6 * math.sin(2 * math.pi * f * 0.73 * c.t + ph + 1.3))


def cue_cross_wax(c, p):
    k = progress(c.t, *p.get("t_range", [0, c.dur]), p.get("ease", "sine_in_out"))
    c.cross_sag = p.get("sag_from", 0.12) + (p.get("sag_to", 0.85) - p.get("sag_from", 0.12)) * k
    c.cross_arm = p.get("arm_from", 0.10) + (p.get("arm_to", 0.80) - p.get("arm_from", 0.10)) * k


def cue_prophet_breath(c, p):
    ph = 2 * math.pi * p.get("hz", 0.22) * c.t
    a = p.get("value", 1.0)
    c.prophet["scale"] = 1.0 + 0.012 * a * math.sin(ph)
    c.prophet["shear"] = 0.010 * a * math.sin(ph * 0.5 + 0.7)
    c.prophet["dy"] = -1.6 * a * math.sin(ph)


def cue_kitten_tilt(c, p):
    k = progress(c.t, *p.get("t_range", [0, c.dur]), "sine_in_out")
    c.kitten["rot"] = math.radians(p.get("deg", 1.2)) * (0.35 + 0.65 * math.sin(math.pi * k))
    c.kitten["dy"] = -1.2 * math.sin(2 * math.pi * p.get("hz", 0.35) * c.t)


def cue_tabby_tail(c, p):
    ph = 2 * math.pi * p.get("hz", 0.17) * c.t
    c.tabby["shear"] = p.get("value", 0.012) * math.sin(ph)
    c.tabby["dy"] = 0.8 * math.sin(ph * 1.7)


def cue_mist(c, p):
    k = progress(c.t, *p.get("t_range", [0, c.dur]), "linear")
    tgt = c.mist_front if p.get("layer", "front") == "front" else c.mist_back
    tgt["dx"] = p.get("dx", -70) * k
    tgt["dy"] = p.get("dy", -12) * math.sin(math.pi * k) + p.get("rise", 0.0) * k
    tgt["alpha"] = p.get("alpha_from", 1.0) + (p.get("alpha_to", 1.0) - p.get("alpha_from", 1.0)) * k


def cue_eyes_ignite(c, p):
    ids, stagger = p.get("clusters", []), p.get("stagger", 0.55)
    t0 = p.get("t_range", [0, c.dur])[0]
    for i, cid in enumerate(ids):
        k = smooth((c.t - (t0 + i * stagger)) / 0.7)
        if cid < len(c.eye_gain):
            c.eye_gain[cid] = min(c.eye_gain[cid], 0.06 + 0.94 * k)
    c.eye_glow = p.get("glow", 1.0)


def cue_eyes_blink(c, p):
    hz, seed = p.get("hz", 0.42), p.get("seed", 7)
    for cid in p.get("clusters", []):
        ph = (seed * 0.37 + cid * 0.618) % 1.0
        u = (c.t * hz + ph) % 1.0
        shut = smooth(u / 0.045) * (1 - smooth((u - 0.045) / 0.06))
        if cid < len(c.eye_gain):
            c.eye_gain[cid] *= (1.0 - 0.92 * shut)


def cue_exposure(c, p):
    k = progress(c.t, *p.get("t_range", [0, c.dur]), p.get("ease", "sine_in_out"))
    c.exposure = p.get("from", 1.0) + (p.get("to", 1.0) - p.get("from", 1.0)) * k


def cue_moon_glow(c, p):
    k = 0.5 - 0.5 * math.cos(2 * math.pi * p.get("hz", 0.13) * c.t)
    base = p.get("base", 0.55)
    c.moon_glow = p.get("value", 1.0) * (base + (1 - base) * k)


def cue_stone_sway(c, p):
    c.stone_sway = p.get("value", 2.2) * math.sin(2 * math.pi * p.get("hz", 0.09) * c.t)


def cue_swell(c, p):
    k = progress(c.t, *p.get("t_range", [0, c.dur]), "sine_in_out")
    c.mist_front["alpha"] *= p.get("mist_from", 1.0) + (p.get("mist_to", 1.3) - p.get("mist_from", 1.0)) * k
    c.deep_eyes = p.get("eyes_from", 0.0) + (p.get("eyes_to", 1.0) - p.get("eyes_from", 0.0)) * k


CUE_IMPL = {
    "camera_pan": cue_pan, "camera_rise": cue_rise, "camera_push": cue_push, "camera_pull": cue_pull,
    "camera_drift": cue_drift, "cross_wax": cue_cross_wax,
    "prophet_breath": cue_prophet_breath, "kitten_tilt": cue_kitten_tilt,
    "tabby_tail": cue_tabby_tail, "mist": cue_mist,
    "eyes_ignite": cue_eyes_ignite, "eyes_blink": cue_eyes_blink,
    "moon_glow": cue_moon_glow, "stone_sway": cue_stone_sway, "swell": cue_swell,
    "exposure": cue_exposure,
}


# --------------------------------------------------------------------------- #
# scene
# --------------------------------------------------------------------------- #
class Scene:
    def __init__(self, spec):
        self.spec = spec
        self.dur = float(spec["duration_s"])
        self.fps = int(spec["fps"])
        self.L = load_layers()
        self.clusters = json.loads((A / "eye_clusters.json").read_text())["clusters"]
        self.warp_cache = {}

        bg = np.asarray(self.L["bg"].pil.convert("L"), np.float32)
        mask = bg > 215
        ys, xs = np.where(mask)
        self.moon = (float(xs.mean()) if len(xs) else PIC_W * 0.63,
                     float(ys.mean()) if len(ys) else PIC_H * 0.30)
        yy, xx = np.mgrid[0:PIC_H, 0:PIC_W].astype(np.float32)
        d = np.sqrt((xx - self.moon[0]) ** 2 + (yy - self.moon[1]) ** 2) / 300.0
        self.glow = (np.clip(1.0 - d, 0, 1) ** 2.4)[..., None].astype(np.float32)
        nx = (xx / PIC_W - 0.5) * 2
        ny = (yy / PIC_H - 0.5) * 2
        self.vig = np.clip(1.0 - 0.30 * (nx ** 2 + ny ** 2) ** 1.15, 0.35, 1.0)[..., None].astype(np.float32)

        gh, gw = PIC_H // 8 + 1, PIC_W // 8 + 1
        gy, gx = np.mgrid[0:gh, 0:gw].astype(np.float32) * 8.0
        self.gain_blobs = []
        for c in self.clusters:
            r = max(c["h"], c["w"]) * 0.75 + 12
            self.gain_blobs.append(
                np.exp(-(((gx - c["cx"]) ** 2 + (gy - c["cy"]) ** 2) / (2 * r * r))).astype(np.float32))
        self.gain_shape = (gh, gw)

        eb = json.loads((A / "key_report.json").read_text())["eyes_rgba.png"]["bbox_px"]
        self.eye_box = (max(eb[0] - 30, 0), max(eb[1] - 30, 0),
                        min(eb[2] + 30, PIC_W), min(eb[3] + 30, PIC_H))
        lin = np.arange(256, dtype=np.float32)
        lut = np.repeat((np.power(lin / 255.0, 0.94) * 1.015 * 255.0)[:, None], 3, axis=1)
        lut[:, 2] *= 1.012
        self.lut = np.clip(lut, 0, 255).astype(np.uint8)

        # amber bloom around every eye-pair: this is what makes them glow
        self.glow_sprites = []
        for cl in self.clusters:
            r = max(cl["h"], cl["w"]) * 1.05 + 8
            rr = int(r * 2)
            g1 = np.arange(-rr, rr + 1, dtype=np.float32) / r
            f = np.clip(1.0 - np.sqrt(g1[:, None] ** 2 + g1[None, :] ** 2), 0, 1) ** 2.2
            spr = np.stack([f * 1.00, f * 0.62, f * 0.24], axis=2) * 255.0
            self.glow_sprites.append(spr)

        rng = np.random.default_rng(404)
        n = 380
        self.deep = np.stack([rng.uniform(0, PIC_W, n), rng.uniform(PIC_H * 0.56, PIC_H * 0.88, n),
                              rng.uniform(0.6, 1.9, n), rng.uniform(0.0, 1.0, n)], axis=1)

    def state(self, t):
        c = Ctx(t, self.dur)
        for cue in self.spec["cues"]:
            fn = CUE_IMPL.get(cue["type"])
            if fn is None:
                raise SystemExit(f"unknown cue type {cue['type']!r} in {self.spec['file']}")
            fn(c, {**cue.get("params", {}), "t_range": cue.get("t", [0, self.dur])})
        return c

    def eye_gain_map(self, c):
        f = np.ones(self.gain_shape, np.float32)
        for i, g in enumerate(self.gain_blobs):
            gain = c.eye_gain[i] if i < len(c.eye_gain) else 1.0
            if gain < 0.999:
                f -= (1.0 - gain) * g
        f = np.clip(f, 0.0, 1.0) * c.eye_glow
        return np.repeat(np.repeat(f, 8, axis=0), 8, axis=1)[:PIC_H, :PIC_W]

    def cam_params(self, name, c):
        p = PARALLAX[name]
        pl = PLACEMENT.get(name, {"dx": 0.0, "dy": 0.0, "scale": 1.0})
        zoom = 1.0 + (c.cam_zoom - 1.0) * p
        dx = (pl["dx"] + c.cam_pan * p + c.cam_drift[0] * p
              + (c.cam_anchor[0] - PIC_W / 2) * (1 - zoom))
        dy = (pl["dy"] + c.cam_drift[1] * p + c.cam_lift * (0.55 + 0.45 * p)
              + (c.cam_anchor[1] - PIC_H / 2) * (1 - zoom))
        if name == "bg":
            dx += c.stone_sway
        scale = pl["scale"] * zoom
        if name == "bg":
            scale *= 1.06                      # overscan: the pan must never show a seam
        return scale, dx, dy

    def render_frame(self, t):
        c = self.state(t)

        # 1 - background plate
        s, dx, dy = self.cam_params("bg", c)
        canvas = self.L["bg"].pil.transform((PIC_W, PIC_H), Image.AFFINE,
                                            pil_coeffs(s, dx, dy, (PIC_W / 2, PIC_H / 2)),
                                            Image.BILINEAR)

        # 2 - back mist (soft, so nearest is plenty)
        mb = c.mist_back
        zs = min(max((1.0 + (c.cam_zoom - 1.0) * PARALLAX["mist_back"]), 0.99), 1.14) * 1.07
        m = self.L["mist"].pil.transform(
            (PIC_W, PIC_H), Image.AFFINE,
            pil_coeffs(zs, -mb["dx"] - 20, -mb["dy"] + 20,
                       (c.cam_anchor[0], c.cam_anchor[1])), Image.NEAREST)
        arr = np.asarray(m).astype(np.float32)
        arr[380:] *= (0.62 * mb["alpha"])
        m = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        canvas = Image.alpha_composite(canvas, m)

        # 3 - the crowd's eyes
        ze = min(max((1.0 + (c.cam_zoom - 1.0) * PARALLAX["eyes"]), 0.99), 1.16) * 1.05
        e = self.L["eyes"].pil.transform(
            (PIC_W, PIC_H), Image.AFFINE,
            pil_coeffs(ze, -c.cam_pan * PARALLAX["eyes"] - c.cam_drift[0],
                       -c.cam_drift[1] * 0.9, (c.cam_anchor[0], c.cam_anchor[1])), Image.NEAREST)
        ea = np.asarray(e).astype(np.float32)
        gain = self.eye_gain_map(c)[..., None]
        ex0, ey0, ex1, ey1 = self.eye_box
        ea[ey0:ey1, ex0:ex1, :3] *= gain[ey0:ey1, ex0:ex1]
        ea[..., :3] = np.clip(ea[..., :3] * 1.45 + 6.0, 0, 255)
        ea[..., :3] *= (ea[..., 3:4] / 255.0)
        canvas = Image.alpha_composite(canvas, Image.fromarray(np.clip(ea, 0, 255).astype(np.uint8)))
        carr = np.asarray(canvas).astype(np.float32)
        carr[ey0:ey1, ex0:ex1, :3] += ea[ey0:ey1, ex0:ex1, :3] * 1.35
        canvas = Image.fromarray(np.clip(carr, 0, 255).astype(np.uint8))

        # 4 - the wax cross
        key = (round(c.cross_sag, 2), round(c.cross_arm, 2))
        if key not in self.warp_cache:
            self.warp_cache[key] = warp_cross(self.L["cross"], c.cross_sag, c.cross_arm)
            if len(self.warp_cache) > 60:
                self.warp_cache.pop(next(iter(self.warp_cache)))
        s, dx, dy = self.cam_params("cross", c)
        patch, off = place_numpy(self.L["cross"], scale=s, dx=dx, dy=dy,
                                 anchor=(0.5, 0.5), data=self.warp_cache[key])
        canvas = paste_patch(canvas, patch, off)

        # 5 - the prophet
        s, dx, dy = self.cam_params("prophet", c)
        pr = c.prophet
        # the seat follows the wax: the arm drops and bends outward under her
        dx += pr["dx"] - 9.0 * c.cross_arm
        dy += pr["dy"] + 34.0 * c.cross_sag + 13.0 * c.cross_arm
        patch, off = place_numpy(self.L["prophet"], scale=s * pr["scale"], shear=pr["shear"],
                                 rot=c.cross_arm * 0.012,
                                 dx=dx, dy=dy, anchor=(0.5, 0.92))
        canvas = paste_patch(canvas, patch, off)

        # 6 - the two witnesses
        s, dx, dy = self.cam_params("kitten", c)
        patch, off = place_numpy(self.L["kitten"], scale=s * c.kitten["scale"], rot=c.kitten["rot"],
                                 dx=dx, dy=dy + c.kitten["dy"], anchor=(0.5, 0.94))
        if patch is not None:
            patch = np.clip(patch.astype(np.float32) * np.array([1.14, 1.14, 1.16, 1.0]), 0, 255).astype(np.uint8)
        canvas = paste_patch(canvas, patch, off)
        s, dx, dy = self.cam_params("tabby", c)
        patch, off = place_numpy(self.L["tabby"], scale=s, shear=c.tabby["shear"],
                                 dx=dx, dy=dy + c.tabby["dy"], anchor=(0.45, 0.95))
        canvas = paste_patch(canvas, patch, off)

        # 7 - front mist
        mf = c.mist_front
        zf = min(max((1.0 + (c.cam_zoom - 1.0) * PARALLAX["mist_front"]), 0.99), 1.12) * 1.09
        m = self.L["mist"].pil.transform(
            (PIC_W, PIC_H), Image.AFFINE,
            pil_coeffs(zf, -mf["dx"] + 30, -mf["dy"] - 58,
                       (c.cam_anchor[0], c.cam_anchor[1])), Image.NEAREST)
        arr = np.asarray(m).astype(np.float32)
        arr[380:] *= (0.52 * mf["alpha"])
        canvas = Image.alpha_composite(canvas, Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))

        # 8 - moon light + eye bloom + vignette + far crowd glints
        rgb = np.asarray(canvas.convert("RGB")).astype(np.float32)
        rgb = self.eye_bloom(rgb, c)
        if c.moon_glow > 0:
            rgb += self.glow * (16.0 * c.moon_glow)
        if c.exposure != 1.0:
            rgb *= c.exposure
        rgb *= self.vig
        pic = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        pic = pic.filter(ImageFilter.UnsharpMask(radius=2.0, percent=55, threshold=2))
        rgb = np.asarray(pic).astype(np.float32)
        out8 = np.take(self.lut, np.clip(rgb, 0, 255).astype(np.uint8))
        if c.deep_eyes > 0.01:
            rgb = out8.astype(np.float32)
            rgb = self.deep_glints(rgb, c)
        out = np.clip(rgb, 0, 255).astype(np.uint8)

        frame = np.zeros((OUT_H, OUT_W, 3), np.uint8)
        frame[BAR:BAR + PIC_H] = out
        return frame

    def eye_bloom(self, rgb, c):
        ze = 1.0 + (c.cam_zoom - 1.0) * PARALLAX["eyes"]
        ax, ay = c.cam_anchor
        for i, cl in enumerate(self.clusters):
            g = c.eye_gain[i] if i < len(c.eye_gain) else 1.0
            if g < 0.05:
                continue
            px = ze * (cl["cx"] - ax) + ax - c.cam_pan * PARALLAX["eyes"] - c.cam_drift[0]
            py = ze * (cl["cy"] - ay) + ay - c.cam_drift[1] * 0.9
            spr = self.glow_sprites[i]
            h, w = spr.shape[:2]
            x0, y0 = int(px) - w // 2, int(py) - h // 2
            x1, y1 = x0 + w, y0 + h
            sx0, sy0 = max(0, -x0), max(0, -y0)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1, y1 = min(x1, PIC_W), min(y1, PIC_H)
            if x1 <= x0 or y1 <= y0:
                continue
            sub = spr[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
            rgb[y0:y1, x0:x1] += sub * (0.30 * g * c.eye_glow)
        return rgb

    def deep_glints(self, rgb, c):
        t = c.t
        for x, y, sz, ph in self.deep:
            tw = 0.5 + 0.5 * math.sin(t * 1.9 + ph * 6.28)
            a = c.deep_eyes * (0.18 + 0.55 * tw)
            if a < 0.02:
                continue
            xi, yi = int(x), int(y)
            r = max(int(round(sz * 1.9)), 1)
            x0, x1 = max(xi - r, 0), min(xi + r + 1, PIC_W)
            y0, y1 = max(yi - r, 0), min(yi + r + 1, PIC_H)
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1]
            d = np.sqrt((xx - xi) ** 2 + (yy - yi) ** 2) / (sz * 1.9)
            k = np.clip(1 - d, 0, 1) ** 2 * a
            rgb[y0:y1, x0:x1, 0] += 255 * k * 1.25
            rgb[y0:y1, x0:x1, 1] += 182 * k * 1.25
            rgb[y0:y1, x0:x1, 2] += 78 * k * 1.25
        return np.clip(rgb, 0, 255)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--still", default=None)
    ap.add_argument("--still-out", default=None)
    args = ap.parse_args()

    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["file"] = str(spec_path)
    sc = Scene(spec)

    if args.still:
        outdir = Path(args.still_out or (ROOT / "scene_04" / "frames"))
        outdir.mkdir(parents=True, exist_ok=True)
        for t in [float(x) for x in args.still.split(",")]:
            fr = sc.render_frame(min(t, sc.dur - 1e-3))
            Image.fromarray(fr).save(outdir / f"{spec['clip']}_t{t:05.2f}.png")
        print(f"stills -> {outdir}")
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(sc.dur * sc.fps))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
           "-r", str(sc.fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            proc.stdin.write(sc.render_frame(i / sc.fps).tobytes())
            if i % 48 == 0:
                print(f"  {spec['clip']}: {i}/{n}", flush=True)
        proc.stdin.close()
    except BrokenPipeError:
        print(proc.stderr.read().decode()[-2000:], file=sys.stderr)
        raise SystemExit(1)
    rc = proc.wait()
    if rc != 0:
        print(proc.stderr.read().decode()[-2000:], file=sys.stderr)
        raise SystemExit(rc)
    print(f"rendered {out} ({n} frames, {sc.dur}s @ {sc.fps}fps, silent)")


if __name__ == "__main__":
    main()
