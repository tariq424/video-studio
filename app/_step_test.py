"""One-off: Beat 1 of job 20261008_210038, round-2 prompt (fixed) at 8 and 12 steps, seeds 5100-5102, next to the 4-step images;
every image judged by the new check (against the visual description). Results in F:/code/video-studio/_tests/step_test/."""
import json, sys, shutil, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio import config, render, ladder, footage
from studio.wangp import WanGP
cfg = config.load(); log = lambda m: print(m, flush=True)
T = config.ROOT / "_tests"; out = T / "step_test"; out.mkdir(parents=True, exist_ok=True)
r2 = json.loads((T / "prompt_test2" / "result.json").read_text(encoding="utf-8"))
prompt = r2["new_prompt"]; visual = prompt.replace(render.STYLE, ""); vo = r2["narration"]
job = Path(cfg["jobs_dir"]) / "20261008_210038"
sec = json.loads((job / "short" / "plan.json").read_text(encoding="utf-8"))["sections"][0]
res = {"prompt": prompt, "negative": render.negative("air"), "images": []}
for seed in (5100, 5101, 5102):
    shutil.copy2(T / "prompt_test2" / f"new_seed{seed}.jpg", out / f"s4_seed{seed}.jpg"); res["images"].append({"file": f"s4_seed{seed}.jpg", "steps": 4, "seed": seed})
wg = WanGP(cfg)
for steps in (8, 12):
    for seed in (5100, 5101, 5102):
        t0 = time.time()
        g = wg.gen({"model_type": cfg["still_model"], "prompt": prompt, "negative_prompt": render.negative("air"), "resolution": "1088x1920",
                    "num_inference_steps": steps, "seed": seed}, log, f"{steps} steps seed {seed}", tries=1)
        im = {"steps": steps, "seed": seed, "secs": round(time.time() - t0)}
        if g["ok"]: f = out / f"s{steps}_seed{seed}.jpg"; shutil.copy(g["file"], f); im["file"] = f.name
        else: im["err"] = g.get("err")
        res["images"].append(im); log(json.dumps(im))
shutil.copy2(job / "short" / "fallback" / "b0_0.jpg", out / "original.jpg"); res["images"].append({"file": "original.jpg", "steps": 4, "seed": 5100, "note": "old prompt"})
footage.ensure_vet_model(cfg, log)
for im in res["images"]:
    if im.get("file"):
        ok, why = ladder.check(cfg, out / im["file"], vo, sec.get("subject"), visual=visual); im["check_ok"], im["check"] = ok, why
footage.unload_vet_model(cfg)
(out / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
log("DONE " + json.dumps([{k: i.get(k) for k in ("file", "secs", "check_ok", "check")} for i in res["images"]]))
