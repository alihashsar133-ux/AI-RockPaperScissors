# A DREAM OF A THOUSAND CATS — production notes

Adaptation of "A Midsummer Night's Dream" (Sandman #18) · 2D layered animation · painterly
surrealism after Dalí · silent · no on-screen text · 1920×1080 / 24 fps / 2.39:1 letterbox.

Workflow: **one scene = one ZIP = one "How is it?" gate** (production prompt v4.0, Section 1).

| path | what |
|---|---|
| `tools/render_scene.py` | the renderer: reads a clip spec, composites the AI-painted layers, warps the wax cross, drives mist / eyes / camera, pipes to ffmpeg |
| `tools/normalize_assets.py` | chroma-keys the AI green-screen layers to RGBA, normalises everything to the 1920×804 picture area |
| `tools/eye_clusters.py` | finds the amber eye-pairs so each cluster can ignite and blink on its own |
| `tools/make_specs.py` | writes the six clip specs (cues, palette, signatures) |
| `tools/qa.py` | the Section 13 checklist, measured on every clip and on the assembled scene |
| `tools/assemble.py` | hard-cut concat into `scene_XX.mp4` |
| `tools/contact_sheet.py`, `tools/review_sheet.py` | asset preview sheet and the frames the review pass looks at |
| `tools/package_scene.py` | builds and verifies the Scene Delivery ZIP |
| `assets_characters/` | approved character PNGs, reused unchanged in every later scene (Section 10) |
| `scene_04/` | everything for scene 04: keyframe, layers, specs, clips, QA, shot list |
| `_approvals/` | the delivery ZIPs |

Pipeline per scene: keyframe → green-screen layers painted on the keyframe's coordinates
(skill route B) → keying → JSON specs (6–8 s, ≥2 cues) → render → qa.py → independent review →
concat → ZIP → "How is it?".

## Delivery archive (off-repo)

The scene ZIPs are large, so they are not committed. Scene 04 is uploaded here:

- **S4 THE GATHERING** — `SCENE_04_delivery_20261106_064801.zip` (54.9 MB, 34 files)
  https://drive.google.com/file/d/1_GNZDoXwDz9N65CkZ3gwm1ESQvtVOyFN/view
  rebuild with: `python3 tools/render_scene.py` (per clip) → `tools/assemble.py` →
  `tools/qa.py --scene scene_04/scene_04.mp4` → `tools/package_scene.py`
  (the renderer is deterministic: a rebuild reproduces the same 54,945,428-byte ZIP)
