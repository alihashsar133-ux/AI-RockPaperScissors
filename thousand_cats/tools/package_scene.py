#!/usr/bin/env python3
"""Build SCENE_04_delivery_<timestamp>.zip, verify it, and only then report it.

Naming and contents follow Section 2 of the production prompt. The ZIP is
verified before it is ever presented: it must open, every file in the manifest
must be inside, every MP4 must be silent and the right length, every character
PNG must carry an alpha channel, and no cache/temp file may sneak in.
"""
import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
S4 = ROOT / "scene_04"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def probe_duration(path):
    p = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    txt = p.stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", txt)
    dur = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else None
    return dur, "Audio:" in txt


def write_manifest(qa, specs, zpath_files, stage):
    sigs = specs[0]["surreal_signatures"]
    lines = [
        "# SCENE MANIFEST — S4 · THE GATHERING",
        "",
        "**Project:** A DREAM OF A THOUSAND CATS — adaptation of Sandman #18",
        "**Scene:** S4, the gathering (first scene in the agreed production order)",
        "**Look:** 1930s surrealist oil painting in the language of Dalí — layered 2D, painterly,",
        "cold night light, no 3D, no photoreal, no anime, no cartoon.",
        "",
        "## Format",
        "",
        "| item | value |",
        "|---|---|",
        "| picture | 1920×1080, 24 fps, H.264, yuv420p |",
        "| aspect | 2.39:1 letterboxed inside 1920×1080 (picture area 1920×804, bars 138 px) |",
        "| audio | none — zero audio track (`-an`, verified) |",
        "| on-screen text | none |",
        "| watermark | disabled (\"Made with huashu-motion\" not rendered) |",
        "",
        "## Palette (Global Color Arc, Phase II — The Gathering)",
        "",
        "| role | hex |",
        "|---|---|",
        "| deep cobalt | `#101f3c` |",
        "| night blue | `#1b2c50` |",
        "| silver | `#c9d6e8` |",
        "| moon white | `#e9eef6` |",
        "| indigo mist | `#3a3474` |",
        "| stone grey | `#6c7a8c` |",
        "| amber (only warm accent, eyes) | `#d99a3f` |",
        "",
        "## Surreal signatures present (Section 7 / Section 8)",
        "",
    ]
    for s in sigs:
        lines.append(f"- `{s}`")
    lines += [
        "- impossibility of scale: the camera never leaves knee height, so the moon sits *behind*",
        "  the monument and the gravestone rows run to a vanishing point that is too far away",
        "",
        "## Clips",
        "",
        "| file | duration | cues | camera |",
        "|---|---|---|---|",
    ]
    cam = {
        "clip_01": "pan left 150 px + hand-held drift (wide establishing)",
        "clip_02": "push 1.08 → 1.26 to a medium on the cross head and the prophet",
        "clip_03": "pan left 120 px + tilt up (rise +46 → −58), two-shot on the witnesses",
        "clip_04": "push 1.06 → 1.16 anchored on the rows of stones",
        "clip_05": "push 1.14 → 1.32, close on the prophet against the moon",
        "clip_06": "pull back 1.32 → 1.02, pan 40 px, exposure 1.02 → 1.20 (wide reveal)",
    }
    for clip, d in qa["per_clip"].items():
        lines.append(f"| `clips/{clip}.mp4` | {d['duration']:.2f} s | {d['cues']} active | {cam.get(clip, '')} |")
    total = sum(d["duration"] for d in qa["per_clip"].values())
    lines += [
        "",
        f"**Scene duration:** {total:.2f} s across 6 clips (target 45–60 s).",
        "",
        "## Assets — reused vs new",
        "",
        "| asset | status |",
        "|---|---|",
        "| white kitten (`assets_characters/white_kitten.png`) | **new**, approved here, reused S5–S12 |",
        "| brown tabby (`assets_characters/brown_tabby.png`) | **new**, approved here, reused S5–S12 |",
        "| Siamese prophet (`assets_characters/siamese_prophet.png`) | **new**, approved here, reused S5–S12 |",
        "| stone cross, gravestones, mist, eye clusters, cemetery plate | **new** for S4 |",
        "| S1–S3 assets | not yet produced (S4 is first in production order) |",
        "",
        "## QA",
        "",
        f"- checks: {sum(1 for r in qa['results'] if r['pass'])}/{len(qa['results'])} passed",
        f"- failed: {[r['check'] for r in qa['results'] if not r['pass']] or 'none'}",
        "- per-clip motion, palette, signature evidence and format numbers: see `qa_report.txt`",
        "",
        "## Files in this ZIP",
        "",
    ]
    for f in zpath_files:
        lines.append(f"- `{f}`")
    lines += ["", f"_packaged {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC_", ""]
    (stage / "scene_manifest.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="")
    ap.add_argument("--timestamp", default=None)
    args = ap.parse_args()

    ts = args.timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    qa_file = S4 / "qa" / "qa.json"
    if not qa_file.exists():
        raise SystemExit("run tools/qa.py first")
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    failed = [r["check"] for r in qa["results"] if not r["pass"]]
    if failed:
        print("QA has failures - refusing to package:")
        for f in failed:
            print(" -", f)
        raise SystemExit(1)

    specs = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted((S4 / "json_specs").glob("clip_*.json"))]

    stage = ROOT / "_stage" / "SCENE_04"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "assets").mkdir(parents=True)
    (stage / "clips").mkdir()
    (stage / "json_specs").mkdir()

    shutil.copy2(S4 / "scene_04.mp4", stage / "scene_04.mp4")
    shutil.copy2(S4 / "keyframes" / "final_keyframe_B.png", stage / "final_keyframe.png")
    shutil.copy2(S4 / "asset_preview_sheet.png", stage / "asset_preview_sheet.png")
    shutil.copy2(S4 / "镜头表.md", stage / "shot_list.md")
    shutil.copy2(S4 / "qa_report.txt", stage / "qa_report.txt")
    shutil.copy2(ROOT / "审片" / "scene_04_review.md", stage / "review_report.md")
    raw = stage / "assets" / "sources"
    raw.mkdir()
    for p in sorted((S4 / "assets").glob("*.png")):
        dest = raw if p.name.startswith("layer_") else stage / "assets"
        shutil.copy2(p, dest / p.name)
    for p in sorted((S4 / "assets").glob("*.json")):
        shutil.copy2(p, stage / "assets" / p.name)
    for p in sorted((S4 / "json_specs").glob("*.json")):
        shutil.copy2(p, stage / "json_specs" / p.name)
    for p in sorted((S4 / "clips").glob("clip_*.mp4")):
        shutil.copy2(p, stage / "clips" / p.name)

    zfiles = sorted(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file())
    write_manifest(qa, specs, zfiles + ["scene_manifest.md"], stage)
    zfiles = sorted(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file())

    approvals = ROOT / "scene_04" / ".." / "_approvals"
    approvals = (S4.parent / "_approvals")
    approvals.mkdir(parents=True, exist_ok=True)
    vtag = f"_{args.version}" if args.version else ""
    zpath = approvals / f"SCENE_04_delivery{vtag}_{ts}.zip"

    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in zfiles:
            z.write(stage / f, f)

    # ---------------- verification ----------------
    problems = []
    with zipfile.ZipFile(zpath) as z:
        if z.testzip() is not None:
            problems.append("zip integrity")
        names = set(z.namelist())
        for f in zfiles:
            if f not in names:
                problems.append(f"missing {f}")
        for n in names:
            if "__pycache__" in n or n.endswith((".tmp", ".DS_Store", ".cache")):
                problems.append(f"junk file {n}")
    for clip in qa["per_clip"]:
        dur, audio = probe_duration(stage / "clips" / f"{clip}.mp4")
        if audio:
            problems.append(f"{clip} has audio")
        if not (5.9 <= (dur or 0) <= 8.1):
            problems.append(f"{clip} duration {dur}")
    dur, audio = probe_duration(stage / "scene_04.mp4")
    if audio:
        problems.append("scene has audio")
    if not (44.9 <= (dur or 0) <= 60.1):
        problems.append(f"scene duration {dur}")
    for p in sorted((stage / "assets").glob("*_rgba.png")):
        im = Image.open(p)
        if im.mode != "RGBA":
            problems.append(f"{p.name} lost alpha")
        a = np.asarray(im)[..., 3]
        if a.min() != 0 or a.max() != 255:
            problems.append(f"{p.name} alpha range {a.min()}..{a.max()}")
    for p in sorted((stage / "assets").glob("*.png")):
        im = Image.open(p)
        if im.size != (1920, 804):
            problems.append(f"{p.name} size {im.size} != (1920, 804)")
    if not list((stage / "assets" / "sources").glob("layer_*.png")):
        problems.append("raw AI source plates missing from assets/sources")

    size = zpath.stat().st_size / 1e6
    print(f"ZIP: {zpath}  ({size:.1f} MB, {len(zfiles)} files, scene {dur:.2f}s, silent={not audio})")
    if problems:
        print("VERIFICATION FAILED:")
        for p in problems:
            print(" -", p)
        raise SystemExit(1)
    print("verification: OK - zip opens, manifest matches, all MP4 silent, 2.39:1 PNG layers, no junk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
