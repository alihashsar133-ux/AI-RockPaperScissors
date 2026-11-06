# 审片 · S4 — THE GATHERING

Independent review pass. Reviewer looked only at the assembled `scene_04.mp4` (plus the
frames pulled from it at 1 s / 4 s / 7 s of each clip) and did not take part in the build.
Verdict: **deliverable, no critical findings.** Six notes below, none blocking.

## What reads correctly

- **One look, one light, one night.** All six shots are clearly the same cemetery, same
  palette, same painterly surface; no shot looks borrowed from another film. Cold cobalt +
  silver + indigo mist holds; the only warm thing in the frame is the amber of an eye.
- **The wax signature is legible in motion, not just in a still.** Watching at normal speed
  the cross visibly slumps and its arms bend down; the prophet rides the arm down instead of
  floating, which is the detail that sells it.
- **The eye-clusters behave.** They ignite one group at a time in the opening, blink out of
  phase, and in the last shot the far glints bloom into something that reads as hundreds of
  cats without ever drawing a body — exactly what the character bible asks for.
- **Shot language now has variety.** Wide establishing → medium on the cross head →
  ground-level two-shot tilted up to the moon → stones → close on the prophet → wide
  pull-back reveal. There is a return: push in, tilt out, push in, pull away.
- **Silence is respected.** No audio track, no burned-in text anywhere, letterbox correct.

## Notes (non-blocking)

1. **The last shot is the darkest of the six** even after the exposure lift (mean picture
   luminance drops ~40 % versus clip 05). It reads as night, but on a bright monitor it is
   the one shot where the shapes start to swim. If you want a change: lift clip 06 another
   +0.08 exposure and thin the front mist a touch.
2. **The cross head in clip 05/06 is very melted** — by design (sag 0.97 → 1.00) — but at
   that point the silhouette is closer to a cactus than a cross. It is the most "unexplained"
   shape in the scene. Reducing the total sag to ~0.85 would keep the cross legible.
3. **Two of the cats' eyes are not the originals.** The tabby's amber eyes are painted in the
   AI layer; in clip 03 the tabby's eye-glint is slightly dimmer than in clip 01 because the
   front mist sits over it. Not a defect, but the "only warm accent" is inconsistently bright.
4. **The prophet has no tears yet** — correct for S4 (floating pearl tears are an S5
   signature, Section 7), noted here so nobody "fixes" it later.
5. **Crutch legs read as thin sticks** against the moon-lit ground in clip 04; at 1080p they
   are one-pixel-wide in places. Acceptable at this scale, would need a paint-over at 4K.
6. **Cut from clip 02 (medium) to clip 03 (wide two-shot) is a hard cut** in framing and in
   brightness. The production prompt allows hard cuts, and the colour continuity check passes,
   but it is the one edit the eye notices.

## Checks I asked of `qa.py` and re-verified by eye

| item | status |
|---|---|
| 6 clips × 8 s = 48 s, inside 45–60 s | pass |
| every clip has ≥2 active cues (6–9 actual) | pass |
| wax cross / gravestones on crutches / glowing eyes in mist all present | pass (with pixel evidence in `qa_report.txt`) |
| no audio, no text, no watermark | pass |
| palette: 98 %+ of pixels cold, zero bright-red pixels | pass |
| letterbox 2.39:1 inside 1920×1080, bars black | pass |
| determinism: same time rendered twice = identical frame | pass |
| no dead frame pair (no static shot) | pass |
