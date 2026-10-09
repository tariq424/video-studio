"""One-off: post-generation attitude correction for Beat 1 of job 20261008_210038 (narration: a descent).
For two nose-up stills from that beat's prompt: blind pitch read (the vision model never sees the beat) -> rotate toward
20 deg nose-down (max 35) -> blind re-read -> depth layers -> parallax motion (same math as LayersBackdrop in Remotion).
Results in F:/code/video-studio/_tests/rotate_test/."""
import json, sys, shutil, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageFilter
from studio import config, depth, media
from studio.footage import _vision, ensure_vet_model, unload_vet_model
from studio.llm import parse_json
cfg = config.load(); log = lambda m: print(m, flush=True)
T = config.ROOT / "_tests"; out = T / "rotate_test"; out.mkdir(parents=True, exist_ok=True)
TARGET = -20.0   # descending beat: nose about 20 degrees below the horizon
PITCH = """Look only at the aircraft in this picture. Reply with ONLY JSON:
{"nose": "left" or "right" - the side of the picture the aircraft's nose points toward,
 "pitch": "nose_up", "level", "nose_down" or "ambiguous" - is the nose higher or lower than the tail in the picture,
 "angle": the angle in degrees between the fuselage line (tail to nose) and the horizontal: positive if the nose is higher
  than the tail, negative if lower, e.g. 25, 0, -20}"""
def read(img):
    try: j = parse_json(_vision(cfg, img, PITCH))
    except Exception as e: return {"pitch": "ambiguous", "err": str(e)[:80]}
    try: j["angle"] = float(j.get("angle", 0))
    except (TypeError, ValueError): j["angle"] = 0.0
    return j
def rotate(src, dst, ccw):
    im = Image.open(src).convert("RGB"); W, H = im.size
    bg = im.resize((int(W * 1.4), int(H * 1.4))).crop((int(W * .2), int(H * .2), int(W * .2) + W, int(H * .2) + H)).filter(ImageFilter.GaussianBlur(30))
    rot = im.rotate(ccw, resample=Image.BICUBIC, expand=False)
    mask = Image.new("L", (W, H), 255).rotate(ccw, resample=Image.BICUBIC, expand=False).filter(ImageFilter.GaussianBlur(6))
    bg.paste(rot, (0, 0), mask); z = 1.08   # a little zoom hides most of the blurred corners
    bg.resize((int(W * z), int(H * z)), Image.LANCZOS).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H)).save(dst, quality=93)
def parallax(layers, mp4, strip, dur=8.0, fps=15, size=(540, 960)):
    """Same transforms as LayersBackdrop: per layer depth .25/.65/1, x -40..40 px, y 10..-10 px (at 1080 wide), scale 1.08+.05*depth*e."""
    W, H = size; k = W / 1080; ims = [Image.open(p).convert("RGBA").resize(size, Image.LANCZOS) for p in layers]
    fd = mp4.parent / (mp4.stem + "_frames"); fd.mkdir(exist_ok=True); n = int(dur * fps); picks = []
    for f in range(n):
        p = f / (n - 1); e = 2 * p * p if p < .5 else 1 - (-2 * p + 2) ** 2 / 2
        fr = Image.new("RGBA", size, (0, 0, 0, 255))
        for i, im in enumerate(ims):
            dp = [.25, .65, 1.0][i]; x = (-40 + 80 * e) * dp * k; y = (10 - 20 * e) * dp * k; s = 1.08 + .05 * dp * e
            sw, sh = int(W * s), int(H * s); l = im.resize((sw, sh), Image.BILINEAR)
            fr.alpha_composite(l, (int((W - sw) / 2 + x), int((H - sh) / 2 + y)))
        fr.convert("RGB").save(fd / f"{f:04d}.jpg", quality=90)
        if f in (0, n // 2, n - 1): picks.append(fr.convert("RGB"))
    media.ff("-framerate", fps, "-i", fd / "%04d.jpg", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", 20, mp4)
    st = Image.new("RGB", (W * 3 + 20, H), (20, 20, 20))
    for i, im in enumerate(picks): st.paste(im, (i * (W + 10), 0))
    st.save(strip, quality=88)
res = []
ensure_vet_model(cfg, log)
cases = [("seed5100", T / "step_test" / "s4_seed5100.jpg"), ("seed5101", T / "step_test" / "s4_seed5101.jpg")]
for name, src in cases:
    shutil.copy2(src, out / f"{name}_original.jpg")
    r0 = read(out / f"{name}_original.jpg"); log(f"{name} blind read: {r0}")
    delta = TARGET - r0["angle"] if r0.get("pitch") != "ambiguous" else 0.0
    ccw = max(-35.0, min(35.0, delta if r0.get("nose") == "right" else -delta))   # PIL rotates counter-clockwise
    rotate(out / f"{name}_original.jpg", out / f"{name}_rotated.jpg", ccw)
    r1 = read(out / f"{name}_rotated.jpg"); log(f"{name} rotated {ccw:+.0f} deg (ccw); blind re-read: {r1}")
    res.append({"case": name, "before": r0, "rotation_ccw_deg": round(ccw, 1), "after": r1})
unload_vet_model(cfg)
for c in res:
    name = c["case"]
    lay = depth.layers(out / f"{name}_rotated.jpg", out / f"{name}_px", log, size=(1080, 1920))
    parallax(lay, out / f"{name}_parallax.mp4", out / f"{name}_parallax_frames.jpg")
(out / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
log("DONE " + json.dumps(res))
