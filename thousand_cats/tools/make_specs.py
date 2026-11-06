#!/usr/bin/env python3
"""Write the six S4 clip specs.

Each clip: 8 s @ 24 fps, silent, no on-screen text, at least two (in practice
five or six) active cues, cold blue + silver + indigo palette, and the three S4
surreal signatures present. The camera has an arc across the six clips: pan
left / push in / track low / pan left / push in on the prophet / pull back.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scene_04" / "json_specs"
OUT.mkdir(parents=True, exist_ok=True)

PALETTE = {
    "deep_cobalt": "#101f3c",
    "night_blue": "#1b2c50",
    "silver": "#c9d6e8",
    "moon_white": "#e9eef6",
    "indigo_mist": "#3a3474",
    "stone_grey": "#6c7a8c",
    "amber_eye": "#d99a3f",
}

SIG = ["wax_bending_cross", "gravestones_on_crutches", "glowing_eyes_in_mist"]

COMMON = {
    "scene": "S4",
    "title_scene": "THE GATHERING",
    "duration_s": 8.0,
    "fps": 24,
    "resolution": [1920, 1080],
    "picture": [1920, 804],
    "aspect": "2.39:1 letterboxed inside 1920x1080",
    "audio": None,
    "text": None,
    "watermark": False,
    "palette": PALETTE,
    "surreal_signatures": SIG,
}

CLIPS = [
    {
        "clip": "clip_01",
        "seed": 401,
        "note": "Opening. Low angle on the moon and the wax cross in the right third; the camera begins its slow pan left and the first eye-clusters wake in the mist.",
        "cues": [
            {"type": "camera_pan", "element": "camera", "t": [0, 8],
             "params": {"value": 150, "ease": "sine_in_out"},
             "note": "slow pan left, 150 px across the picture"},
            {"type": "camera_drift", "element": "camera", "t": [0, 8],
             "params": {"value": 2.4, "hz": 0.11}, "note": "hand-held breath, 2.4 px"},
            {"type": "cross_wax", "element": "cross", "t": [0.4, 8],
             "params": {"sag_from": 0.10, "sag_to": 0.40, "arm_from": 0.10, "arm_to": 0.38},
             "note": "the stone cross starts to slump like warm wax"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": -90, "dy": -10, "rise": -6,
                        "alpha_from": 0.95, "alpha_to": 1.05},
             "note": "indigo mist slides left across the foreground"},
            {"type": "mist", "element": "mist_back", "t": [0, 8],
             "params": {"layer": "back", "dx": 60, "dy": 6, "alpha_from": 0.85, "alpha_to": 0.95},
             "note": "back mist drifts the other way, depth"},
            {"type": "eyes_ignite", "element": "eyes", "t": [0.6, 8],
             "params": {"clusters": [1, 2, 3, 8, 0, 7], "stagger": 0.9, "glow": 1.0},
             "note": "six eye clusters wake one after another"},
            {"type": "moon_glow", "element": "moon", "t": [0, 8],
             "params": {"value": 1.0, "hz": 0.11, "base": 0.5}, "note": "moon light breathes"},
            {"type": "stone_sway", "element": "gravestones", "t": [0, 8],
             "params": {"value": 1.2, "hz": 0.075},
             "note": "the leaning stones breathe on their crutches from the first frame"},
        ],
    },
    {
        "clip": "clip_02",
        "seed": 402,
        "note": "Push in on the cross and the prophet. The wax sag deepens until the arm visibly hangs; the eye clusters in the mist blink out of sync.",
        "cues": [
            {"type": "camera_push", "element": "camera", "t": [0, 8],
             "params": {"from": 1.08, "to": 1.26, "ease": "sine_in_out", "anchor": [1050, 250]},
             "note": "slow push to a medium on the cross head and the prophet"},
            {"type": "cross_wax", "element": "cross", "t": [0, 8],
             "params": {"sag_from": 0.40, "sag_to": 0.78, "arm_from": 0.38, "arm_to": 0.72},
             "note": "the cross melts further, arms bending down at the tips"},
            {"type": "prophet_breath", "element": "prophet", "t": [0, 8],
             "params": {"value": 1.2, "hz": 0.20}, "note": "the Siamese breathes, neck sways"},
            {"type": "eyes_blink", "element": "eyes", "t": [0, 8],
             "params": {"clusters": [3, 4, 5, 6], "hz": 0.35, "seed": 11},
             "note": "four clusters blink independently"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": -40, "dy": -8, "alpha_from": 1.0, "alpha_to": 0.9},
             "note": "foreground mist thins as we get closer"},
            {"type": "moon_glow", "element": "moon", "t": [0, 8],
             "params": {"value": 0.8, "hz": 0.15, "base": 0.55}, "note": "moon glow narrows"},
            {"type": "stone_sway", "element": "gravestones", "t": [0, 8],
             "params": {"value": 1.6, "hz": 0.07}, "note": "the rows keep breathing behind the cross"},
        ],
    },
    {
        "clip": "clip_03",
        "seed": 403,
        "note": "Down at ground level with the two witnesses: the white kitten tilts its head, the tabby's tail moves, the gravestones on their crutches sway as if breathing.",
        "cues": [
            {"type": "camera_pan", "element": "camera", "t": [0, 8],
             "params": {"value": 120, "ease": "ease_out"}, "note": "pan left, decelerating onto the witnesses"},
            {"type": "camera_push", "element": "camera", "t": [0, 8],
             "params": {"from": 1.10, "to": 1.16, "ease": "sine_in_out", "anchor": [330, 600]},
             "note": "hold the two cats big in the lower third"},
            {"type": "camera_rise", "element": "camera", "t": [0.5, 8],
             "params": {"from": 46, "to": -58, "ease": "sine_in_out"},
             "note": "tilt up out of the two-shot to the moon"},
            {"type": "kitten_tilt", "element": "kitten", "t": [0.6, 7.4],
             "params": {"deg": 1.4, "hz": 0.30}, "note": "the kitten tilts its head, ears leading"},
            {"type": "tabby_tail", "element": "tabby", "t": [0, 8],
             "params": {"value": 0.014, "hz": 0.15}, "note": "the tabby's tail swings slowly"},
            {"type": "stone_sway", "element": "gravestones", "t": [0, 8],
             "params": {"value": 2.6, "hz": 0.08}, "note": "the rows of leaning stones sway on their crutches"},
            {"type": "eyes_blink", "element": "eyes", "t": [0, 8],
             "params": {"clusters": [0, 1, 2, 8], "hz": 0.5, "seed": 3},
             "note": "the nearest clusters blink fast, nervous"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": -70, "dy": -6, "rise": -8,
                        "alpha_from": 1.0, "alpha_to": 1.1},
             "note": "mist climbs, half hiding the ground"},
            {"type": "cross_wax", "element": "cross", "t": [0, 8],
             "params": {"sag_from": 0.78, "sag_to": 0.84, "arm_from": 0.72, "arm_to": 0.78},
             "note": "the cross keeps melting at the edge of frame (continuous with clip_02)"},
        ],
    },
    {
        "clip": "clip_04",
        "seed": 404,
        "note": "The pan left continues along the tilted gravestone rows; the crutches creak, the mist crosses the frame the other way, new eyes appear deeper in.",
        "cues": [
            {"type": "camera_pan", "element": "camera", "t": [0, 8],
             "params": {"value": 130, "ease": "sine_in_out"}, "note": "pan left along the rows"},
            {"type": "camera_push", "element": "camera", "t": [0, 8],
             "params": {"from": 1.06, "to": 1.16, "ease": "sine_in_out", "anchor": [430, 330]},
             "note": "eases into the rows of stones instead of the cross"},
            {"type": "stone_sway", "element": "gravestones", "t": [0, 8],
             "params": {"value": 3.2, "hz": 0.07}, "note": "the leaning rows sway further"},
            {"type": "cross_wax", "element": "cross", "t": [0, 8],
             "params": {"sag_from": 0.84, "sag_to": 0.90, "arm_from": 0.78, "arm_to": 0.84},
             "note": "the wax keeps going at the edge of frame"},
            {"type": "mist", "element": "mist_back", "t": [0, 8],
             "params": {"layer": "back", "dx": 90, "dy": 10, "alpha_from": 0.85, "alpha_to": 1.0},
             "note": "back mist pushes right"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": -120, "dy": -12, "rise": -14,
                        "alpha_from": 1.0, "alpha_to": 0.95},
             "note": "front mist races the other way"},
            {"type": "eyes_ignite", "element": "eyes", "t": [1.0, 8],
             "params": {"clusters": [4, 5, 6, 9], "stagger": 0.7, "glow": 1.05},
             "note": "four more clusters open deeper in the mist"},
        ],
    },
    {
        "clip": "clip_05",
        "seed": 405,
        "note": "Close on the prophet against the moon; the wax arm sags under her weight, the moon brightens, the last near clusters blink.",
        "cues": [
            {"type": "camera_push", "element": "camera", "t": [0, 8],
             "params": {"from": 1.14, "to": 1.32, "ease": "sine_in_out", "anchor": [1035, 215]},
             "note": "push in to a close shot of her silhouette against the moon"},
            {"type": "prophet_breath", "element": "prophet", "t": [0, 8],
             "params": {"value": 1.6, "hz": 0.16}, "note": "long neck breathing, slow"},
            {"type": "cross_wax", "element": "cross", "t": [0, 8],
             "params": {"sag_from": 0.90, "sag_to": 0.97, "arm_from": 0.84, "arm_to": 0.92},
             "note": "the arm under her sags to its deepest point"},
            {"type": "moon_glow", "element": "moon", "t": [0, 8],
             "params": {"value": 1.2, "hz": 0.10, "base": 0.45}, "note": "the moon swells with light"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": -30, "dy": -5, "alpha_from": 0.90, "alpha_to": 0.80},
             "note": "mist sinks away from the moon"},
            {"type": "eyes_blink", "element": "eyes", "t": [0, 8],
             "params": {"clusters": [0, 7, 8], "hz": 0.30, "seed": 21},
             "note": "three clusters blink, half asleep"},
            {"type": "stone_sway", "element": "gravestones", "t": [0, 8],
             "params": {"value": 2.0, "hz": 0.06}, "note": "the rows sway under the moon"},
        ],
    },
    {
        "clip": "clip_06",
        "seed": 406,
        "note": "Pull back: the whole gathering. Mist swells, every cluster wakes, hundreds of far glints bloom in the dark, the pull comes to rest.",
        "cues": [
            {"type": "camera_pull", "element": "camera", "t": [0, 8],
             "params": {"from": 1.32, "to": 1.02, "ease": "sine_in_out", "anchor": [1035, 215]},
             "note": "pull all the way back out of the close shot, to the whole gathering"},
            {"type": "camera_pan", "element": "camera", "t": [0, 8],
             "params": {"value": 40, "ease": "ease_out"}, "note": "final pan left, settling"},
            {"type": "swell", "element": "mist_front", "t": [0, 8],
             "params": {"mist_from": 1.0, "mist_to": 1.05, "eyes_from": 0.0, "eyes_to": 1.0},
             "note": "mist swells and the far crowd blooms"},
            {"type": "eyes_ignite", "element": "eyes", "t": [0.4, 8],
             "params": {"clusters": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "stagger": 0.22, "glow": 1.25},
             "note": "all ten clusters wake, a thousand cats watching"},
            {"type": "mist", "element": "mist_back", "t": [0, 8],
             "params": {"layer": "back", "dx": -100, "dy": -8, "alpha_from": 0.95, "alpha_to": 1.1},
             "note": "back mist rolls left"},
            {"type": "mist", "element": "mist_front", "t": [0, 8],
             "params": {"layer": "front", "dx": 40, "dy": -18, "rise": -20,
                        "alpha_from": 1.0, "alpha_to": 1.12},
             "note": "front mist rises in the foreground"},
            {"type": "moon_glow", "element": "moon", "t": [0, 8],
             "params": {"value": 1.15, "hz": 0.09, "base": 0.6}, "note": "moonlight lifts the last shot"},
            {"type": "cross_wax", "element": "cross", "t": [0, 8],
             "params": {"sag_from": 0.97, "sag_to": 1.0, "arm_from": 0.92, "arm_to": 0.95},
             "note": "the cross comes to rest at its deepest melt (continuous with clip_05)"},
            {"type": "exposure", "element": "camera", "t": [0, 8],
             "params": {"from": 1.02, "to": 1.20, "ease": "sine_in_out"},
             "note": "the reveal lifts: as the camera pulls back, the moonlight opens up"},
        ],
    },
]


def main():
    for c in CLIPS:
        spec = {**COMMON, **c}
        assert len(spec["cues"]) >= 2, spec["clip"]
        for cue in spec["cues"]:
            assert cue["type"] in {
                "camera_pan", "camera_push", "camera_pull", "camera_drift", "camera_rise", "cross_wax",
                "exposure",
                "prophet_breath", "kitten_tilt", "tabby_tail", "mist", "eyes_ignite",
                "eyes_blink", "moon_glow", "stone_sway", "swell",
            }, cue["type"]
        p = OUT / f"{c['clip']}.json"
        p.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        print("wrote", p.name, len(spec["cues"]), "cues")


if __name__ == "__main__":
    main()
