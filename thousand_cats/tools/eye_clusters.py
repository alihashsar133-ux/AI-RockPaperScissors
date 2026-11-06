#!/usr/bin/env python3
"""Find the amber eye-pairs inside eyes_rgba.png and store them as clusters.

S4's surreal signature "glowing eyes in the mist" only reads if the eyes behave:
they ignite one cluster at a time as the camera pans, and they blink
independently. For that the renderer needs a list of cluster centres, so we
label the alpha mask on a coarse grid (fast, deterministic) and merge cells.
"""
import json
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "scene_04" / "assets"
CELL = 12  # grid cell in px


def main():
    im = Image.open(A / "eyes_rgba.png")
    a = np.asarray(im)[..., 3].astype(np.float32) / 255.0
    H, W = a.shape
    gh, gw = H // CELL, W // CELL
    grid = a[: gh * CELL, : gw * CELL].reshape(gh, CELL, gw, CELL).max(axis=(1, 3))
    mass = grid > 0.25
    seen = np.zeros_like(mass)
    clusters = []
    for y in range(gh):
        for x in range(gw):
            if mass[y, x] and not seen[y, x]:
                q, cells = deque([(y, x)]), []
                seen[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    cells.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < gh and 0 <= nx < gw and mass[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((ny, nx))
                ys = np.array([c[0] for c in cells]) * CELL + CELL / 2
                xs = np.array([c[1] for c in cells]) * CELL + CELL / 2
                clusters.append({
                    "cx": int(xs.mean()), "cy": int(ys.mean()),
                    "w": int(xs.max() - xs.min() + CELL),
                    "h": int(ys.max() - ys.min() + CELL),
                    "px": len(cells) * CELL * CELL,
                })
    clusters.sort(key=lambda c: (c["px"]), reverse=True)
    for i, c in enumerate(clusters):
        c["id"] = i
    out = {"count": len(clusters), "clusters": clusters}
    (A / "eye_clusters.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps([{k: c[k] for k in ("id", "cx", "cy", "px")} for c in clusters], indent=0))


if __name__ == "__main__":
    main()
