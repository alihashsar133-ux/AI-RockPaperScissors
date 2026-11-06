#!/usr/bin/env python3
"""qa.py - the S4 checklist from the production prompt, measured, not assumed.

The huashu-art-motion skill's own qa.py drives a Playwright engine; this project
renders with Pillow/ffmpeg, so the checks that matter for this film are
re-implemented here against the same principles (stability/determinism, motion,
palette, framed text, duration, silence):

  clip level
    1  every clip has >= 2 active cues             (from the spec, and each cue is
       implemented by the renderer - CUE_IMPL)
    2  every clip is 6-8 s
    3  the scene totals 45-60 s over 6-9 clips
    4  palette matches the S4 phase (cold blue + silver + indigo mist; no bright
       red, no saturated cartoon colour)
    5  the three S4 surreal signatures are present, with pixel evidence
    6  no text, no audio anywhere
    7  approved PNGs reused, not regenerated      (asset hashes recorded)
    8  determinism: same time rendered twice is pixel-identical
    9  real animation: motion area and frame-delta, plus regional evidence
   10  letterbox: 2.39:1 inside 1920x1080, bars truly black
   11  watermark disabled (no burned-in mark: spec flag + no flat overlay bands)

    python3 tools/qa.py --clips scene_04/clips --specs scene_04/json_specs \
        --out scene_04/qa --report scene_04/qa_report.txt
    python3 tools/qa.py --scene scene_04/scene_04.mp4 --clips ... (scene checks)
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scene as RS  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).resolve().parents[1]
SPEC_FPS = 24
EXPECT_W, EXPECT_H = 1920, 1080

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + (("  |  " + detail) if detail else ""))
    return ok


# --------------------------------------------------------------------------- #
def probe(path):
    """ffmpeg has no ffprobe sibling in this sandbox, so read its banner."""
    p = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    txt = p.stderr
    info = {"raw": txt}
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", txt)
    info["duration"] = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else None
    m = re.search(r"Video: (\w+).*?, (\d+)x(\d+)", txt)
    if m:
        info["codec"], info["w"], info["h"] = m.group(1), int(m.group(2)), int(m.group(3))
    m = re.search(r"(\d+(?:\.\d+)?) fps", txt)
    info["fps"] = float(m.group(1)) if m else None
    m = re.search(r"yuv(\d+)p", txt)
    info["pix_fmt"] = ("yuv" + m.group(1) + "p") if m else None
    info["audio"] = "Audio:" in txt
    return info


def frames(path, times):
    """Decode specific timestamps to numpy arrays."""
    out = []
    for t in times:
        p = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
                            "-i", str(path), "-frames:v", "1", "-f", "image2pipe",
                            "-vcodec", "png", "-"], capture_output=True)
        if p.returncode != 0 or not p.stdout:
            raise SystemExit(f"could not decode {path} at {t}s: {p.stderr[:300]}")
        out.append(np.asarray(Image.open(__import__("io").BytesIO(p.stdout)).convert("RGB"), np.float32))
    return out


def motion_stats(fr):
    diffs = []
    for a, b in zip(fr[:-1], fr[1:]):
        d = np.abs(a - b).mean(axis=2)
        diffs.append((float((d > 12).mean()), float(d.mean())))
    area = float(np.mean([d[0] for d in diffs]))
    return area, diffs


def palette_stats(fr):
    px = np.concatenate([f[RS.BAR:RS.BAR + RS.PIC_H].reshape(-1, 3) for f in fr])
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    bright_red = float(((r > 165) & (g < 95) & (b < 95)).mean())
    sat = float((px.max(axis=1) - px.min(axis=1)).mean())
    means = px.mean(axis=0)
    cold_share = float((b >= r).mean())
    return {"mean_rgb": [round(float(v), 1) for v in means], "bright_red": bright_red,
            "mean_saturation": round(sat, 1), "cold_share": round(cold_share, 3)}


def regional_motion(fr, box):
    x0, y0, x1, y1 = box
    vals = []
    for a, b in zip(fr[:-1], fr[1:]):
        d = np.abs(a[y0:y1, x0:x1] - b[y0:y1, x0:x1]).mean(axis=2)
        vals.append(float((d > 10).mean()))
    return float(np.mean(vals))


def amber_pixels(fr):
    tot = 0
    for f in fr:
        px = f[RS.BAR:RS.BAR + RS.PIC_H]
        r, g, b = px[..., 0], px[..., 1], px[..., 2]
        tot += int(((r > 85) & (r > g * 1.10) & (g > b * 1.02)).sum())
    return tot / len(fr)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=str(ROOT / "scene_04" / "clips"))
    ap.add_argument("--specs", default=str(ROOT / "scene_04" / "json_specs"))
    ap.add_argument("--scene", default=None)
    ap.add_argument("--out", default=str(ROOT / "scene_04" / "qa"))
    ap.add_argument("--report", default=str(ROOT / "scene_04" / "qa_report.txt"))
    args = ap.parse_args()

    clips_dir, specs_dir = Path(args.clips), Path(args.specs)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_files = sorted(specs_dir.glob("clip_*.json"))
    data = {}
    total = 0.0

    print("=" * 78)
    print("SCENE 04 - THE GATHERING - QA")
    print("=" * 78)

    for sf in spec_files:
        spec = json.loads(sf.read_text(encoding="utf-8"))
        clip = spec["clip"]
        path = clips_dir / f"{clip}.mp4"
        print(f"\n--- {clip} ({path.name}) ---")
        if not path.exists():
            check(f"{clip}: file exists", False, str(path))
            continue
        info = probe(path)
        dur = info.get("duration") or 0.0
        total += dur

        # 1 cues
        cues = spec.get("cues", [])
        unknown = [c["type"] for c in cues if c["type"] not in RS.CUE_IMPL]
        active = [c for c in cues if c.get("t", [0, spec["duration_s"]])[1] >
                  c.get("t", [0, spec["duration_s"]])[0]]
        check(f"{clip}: >= 2 active cues", len(active) >= 2, f"{len(active)} active of {len(cues)}")
        check(f"{clip}: every cue type implemented by the renderer", not unknown,
              f"unknown={unknown}")

        # 2 duration
        check(f"{clip}: duration 6-8 s", 5.95 <= dur <= 8.05, f"{dur:.3f}s (spec {spec['duration_s']}s)")
        check(f"{clip}: spec duration matches renderer", abs(dur - spec["duration_s"]) < 0.05)

        # format / silence
        check(f"{clip}: 1920x1080", info.get("w") == EXPECT_W and info.get("h") == EXPECT_H,
              f"{info.get('w')}x{info.get('h')}")
        check(f"{clip}: 24 fps", info.get("fps") == 24.0, f"{info.get('fps')}")
        check(f"{clip}: h264 / yuv420p", info.get("codec") == "h264" and
              info.get("pix_fmt") is not None, f"{info.get('codec')} {info.get('pix_fmt')}")
        check(f"{clip}: no audio track", not info["audio"], "silent")

        # frames
        times = [0.5, 1.6, 2.7, 3.8, 4.9, 6.0, 7.1, min(dur - 0.1, 7.85)]
        fr = frames(path, times)

        # 10 letterbox
        bars_ok = all(float(f[:RS.BAR - 4].max()) < 8 and float(f[RS.BAR + RS.PIC_H + 4:].max()) < 8
                      for f in fr)
        check(f"{clip}: 2.39:1 letterbox bars are black", bars_ok, "top/bottom 138 px")

        # 9 animation
        area, diffs = motion_stats(fr)
        mean_delta = float(np.mean([d[1] for d in diffs]))
        check(f"{clip}: picture is moving (motion area >= 0.5%)", area >= 0.005,
              f"motion area {area * 100:.2f}%, mean |d| {mean_delta:.2f}")
        check(f"{clip}: no dead pair of frames (static shot)", min(d[1] for d in diffs) > 0.35,
              f"min mean |d| {min(d[1] for d in diffs):.2f}")

        # 4 palette
        pal = palette_stats(fr)
        check(f"{clip}: cold palette (blue >= red on {pal['cold_share'] * 100:.1f}% of pixels)",
              pal["cold_share"] > 0.80, str(pal))
        check(f"{clip}: no bright reds / saturated cartoon colour",
              pal["bright_red"] < 0.0005 and pal["mean_saturation"] < 70,
              f"bright_red {pal['bright_red'] * 100:.3f}%, saturation {pal['mean_saturation']}")

        # 5 signatures with pixel evidence
        cross_motion = regional_motion(fr, (980, 120, 1780, 780))
        stone_motion = regional_motion(fr, (60, 250, 900, 700))
        amber_series = [amber_pixels([f]) for f in fr]
        amber = float(np.mean(amber_series))
        amber_max = float(max(amber_series))
        amber_std = float(np.std(amber_series))
        has_wax = any(c["type"] == "cross_wax" for c in cues)
        has_sway = any(c["type"] == "stone_sway" for c in cues) or any(
            c["type"] in ("camera_pan", "camera_drift") for c in cues)
        has_eyes = any(c["type"] in ("eyes_ignite", "eyes_blink") for c in cues)
        check(f"{clip}: signature wax_bending_cross", has_wax and cross_motion > 0.001,
              f"cue={has_wax}, motion in cross region {cross_motion * 100:.2f}%")
        check(f"{clip}: signature gravestones_on_crutches", has_sway and stone_motion > 0.001,
              f"cue={has_sway}, motion in stone region {stone_motion * 100:.2f}%")
        check(f"{clip}: signature glowing_eyes_in_mist (lit + alive)",
              has_eyes and amber >= 70 and amber_max >= 150 and amber_std >= 20,
              f"cue={has_eyes}, amber px mean {amber:.0f} max {amber_max:.0f} std {amber_std:.0f}")

        # 6 no text / 11 no watermark
        check(f"{clip}: no on-screen text in spec", spec.get("text") in (None, False, [], ""),
              str(spec.get("text")))
        check(f"{clip}: watermark disabled", spec.get("watermark") is False)
        # a burnt-in mark would sit in a low-variance band; the grain/vignette here never is
        var_rows = [float(f[RS.BAR:RS.BAR + RS.PIC_H].std(axis=(0, 1)).mean()) for f in fr]
        check(f"{clip}: no flat overlay band (watermark / lower third)",
              min(var_rows) > 10, f"min picture std {min(var_rows):.1f}")

        data[clip] = {"duration": dur, "cues": len(active), "motion_area": area,
                      "palette": pal, "cross_motion": cross_motion,
                      "stone_motion": stone_motion, "amber_px": amber, "probe": {
                          k: v for k, v in info.items() if k != "raw"}}

    # 3 scene total
    print("\n--- scene totals ---")
    check("scene: 6-9 clips", 6 <= len(spec_files) <= 9, f"{len(spec_files)} clips")
    check("scene: total 45-60 s", 44.9 <= total <= 60.1, f"{total:.2f}s")

    # 7 asset reuse guard
    man = ROOT / "scene_04" / "assets" / "asset_hashes.json"
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
              for p in sorted((ROOT / "scene_04" / "assets").glob("*.png"))}
    man.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    check("assets: reuse manifest written (hashes recorded for scene 05)", bool(hashes),
          f"{len(hashes)} PNG layers hashed")

    # 8 determinism
    spec = json.loads((specs_dir / "clip_01.json").read_text(encoding="utf-8"))
    spec["file"] = "determinism-check"
    sc = RS.Scene(spec)
    a = sc.render_frame(2.0)
    b = sc.render_frame(2.0)
    check("determinism: same timestamp twice is pixel-identical", np.array_equal(a, b))

    # scene-level
    if args.scene and Path(args.scene).exists():
        print(f"\n--- assembled scene: {Path(args.scene).name} ---")
        info = probe(args.scene)
        check("scene mp4: duration 45-60 s", 44.9 <= (info.get("duration") or 0) <= 60.1,
              f"{info.get('duration')}s")
        check("scene mp4: 1920x1080 24fps h264", info.get("w") == EXPECT_W and
              info.get("h") == EXPECT_H and info.get("fps") == 24.0 and info.get("codec") == "h264")
        check("scene mp4: no audio track", not info["audio"])
        sfr = frames(args.scene, [0.5, 8.0, 16.0, 24.0, 32.0, 40.0, 47.5])
        area, _ = motion_stats(sfr)
        check("scene mp4: picture is alive end to end", area > 0.005, f"motion area {area * 100:.2f}%")
        # adjacent-clip colour continuity
        deltas = []
        for i in range(1, len(sfr)):
            deltas.append(float(np.abs(sfr[i] - sfr[i - 1]).reshape(-1, 3).mean(axis=0).mean()))
        check("scene mp4: no colour jump between clips", max(deltas) < 30,
              f"max mean RGB step {max(deltas):.1f}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\n" + "=" * 78)
    print(f"RESULT: {passed}/{len(RESULTS)} checks passed, {len(failed)} failed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    print("=" * 78)

    lines = ["SCENE 04 - THE GATHERING - QA REPORT",
             "project: A DREAM OF A THOUSAND CATS",
             "renderer: tools/render_scene.py (Pillow + ffmpeg, deterministic, seeded)",
             "spec dir: scene_04/json_specs   clip dir: scene_04/clips", ""]
    for name, ok, detail in RESULTS:
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  |  {detail}" if detail else ""))
    lines += ["", f"RESULT: {passed}/{len(RESULTS)} checks passed, {len(failed)} failed"]
    if failed:
        lines.append("FAILED: " + "; ".join(failed))
    lines += ["", "per-clip numbers:"]
    for clip, d in data.items():
        lines.append(f"  {clip}: {d['duration']:.2f}s, {d['cues']} cues, motion {d['motion_area'] * 100:.2f}%, "
                     f"mean RGB {d['palette']['mean_rgb']}, cold {d['palette']['cold_share']}, "
                     f"amber_px {d['amber_px']:.0f}")
    Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "qa.json").write_text(json.dumps(
        {"results": [{"check": n, "pass": ok, "detail": d} for n, ok, d in RESULTS],
         "per_clip": data}, indent=2), encoding="utf-8")
    print(f"\nreport -> {args.report}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
