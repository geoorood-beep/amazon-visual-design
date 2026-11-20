"""Shape references from the 3D model, all at once (UTA_STYLE.md 1.18, 3.10).

    python tools/render_refs.py run --product <产品>                    # every job check_set.py listed, once
    python tools/render_refs.py views --product <产品> [--views front,side_left,...]   # a labelled sheet
    python tools/render_refs.py convert --product <产品>                # STP/STEP -> GLB (needs cascadio)

check_set.py writes each card's job (view, camera, shot, lens, state, focus, canvas) to
outputs/<产品>/renders/jobs.json; `run` opens Blender ONCE and renders every job that has no picture yet. A job
seen before (same angle, same model revision) is reused. Each job gives <id>.png (the product on a plain light
grey ground: the shape reference to attach), <id>_mask.png (white product, black ground) and <id>.json.
`--model` points at a model.json outside products/ (for a trial). Pillow makes the grey and mask files; without
it only <id>_rgba.png is written.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import product_model as pm

ROOT = pm.ROOT
GROUND = (219, 219, 217)
TABLE = {"VIEW_AZIMUTH": pm.VIEW_AZIMUTH, "LENS_MM": pm.LENS_MM, "CANVAS_PX": pm.CANVAS_PX}


class RenderError(Exception):
    pass


def model_for(root, product, path=None):
    model = pm.load_model(root, product, path)
    if model is None:
        raise RenderError("no model.json for %s (products/%s/model/model.json)" % (product, product))
    if not model.get("mesh") or not os.path.exists(os.path.join(model["_dir"], model["mesh"])):
        raise RenderError("the mesh %r is missing next to model.json; run `convert` first" % model.get("mesh"))
    return model


def read_jobs(root, product):
    path = os.path.join(pm.render_dir(root, product), "jobs.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def missing(root, product, jobs):
    return {jid: job for jid, job in jobs.items() if not os.path.exists(pm.render_path(root, product, jid))}


def finish(folder, jid):
    """<id>_rgba.png -> <id>.png on a light grey ground and <id>_mask.png."""
    try:
        from PIL import Image
    except ImportError:
        return False
    src = os.path.join(folder, jid + "_rgba.png")
    if not os.path.exists(src):
        return False
    rgba = Image.open(src).convert("RGBA")
    ground = Image.new("RGBA", rgba.size, GROUND + (255,))
    ground.alpha_composite(rgba)
    ground.convert("RGB").save(os.path.join(folder, jid + ".png"))
    alpha = rgba.split()[3].point(lambda a: 255 if a > 127 else 0)
    alpha.save(os.path.join(folder, jid + "_mask.png"))
    return True


def blender_run(model, jobs, folder, blender=None, timeout=3600):
    blender = blender or pm.renderer()
    if not blender:
        raise RenderError("Blender is not installed; cards fall back to generate (UTA_STYLE.md 1.18)")
    os.makedirs(folder, exist_ok=True)
    payload = {"model": model, "jobs": jobs, "out": os.path.abspath(folder), "table": TABLE}
    fd, path = tempfile.mkstemp(prefix="uta_jobs_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    script = os.path.join(ROOT, "tools", "blender_refs.py")
    try:
        proc = subprocess.run([blender, "-b", "--python", script, "--", path], capture_output=True, text=True,
                              timeout=timeout)
    finally:
        os.remove(path)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("RENDERED", "ALL"))]
    if proc.returncode != 0 or not any(l.startswith("ALL") for l in lines):
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-15:])
        raise RenderError("Blender failed:\n" + tail)
    return lines


def render(root, product, jobs, model, out, blender=None):
    folder = pm.render_dir(root, product)
    todo = {jid: job for jid, job in jobs.items() if not os.path.exists(pm.render_path(root, product, jid))}
    if not todo:
        out.write("RENDERS all %d already there (%s)\n" % (len(jobs), pm.shown(folder, root)))
        return []
    t = time.time()
    lines = blender_run(model, todo, folder, blender)
    for jid in todo:
        finish(folder, jid)
    out.write("RENDERED %d new, %d reused, %.0fs  -> %s\n" % (len(todo), len(jobs) - len(todo), time.time() - t,
                                                              pm.shown(folder, root)))
    return lines


def cmd_run(args, root, out):
    model = model_for(root, args.product, args.model)
    jobs = read_jobs(root, args.product)
    if not jobs:
        out.write("NO JOBS: run check_set.py on a task first (it lists the angles each card needs)\n")
        return 0
    render(root, args.product, jobs, model, out, args.blender)
    return 0


def cmd_views(args, root, out):
    model = model_for(root, args.product, args.model)
    views = [v.strip() for v in args.views.split(",") if v.strip()]
    jobs = {}
    for v in views:
        if v not in pm.VIEW_AZIMUTH:
            raise RenderError("unknown view %s (one of %s)" % (v, ", ".join(pm.VIEW_AZIMUTH)))
        job = pm.job_for("S0", {"product_view": v, "camera": args.camera, "shot_size": "medium",
                                "lens": "standard", "product_state": args.state, "focus": "whole", "canvas": "1:1"})
        jobs[pm.job_id(job, model)] = job
    render(root, args.product, jobs, model, out, args.blender)
    sheet = contact_sheet(root, args.product, jobs, views)
    if sheet:
        out.write("SHEET %s\n" % pm.shown(sheet, root))
    return 0


def contact_sheet(root, product, jobs, labels):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    folder = pm.render_dir(root, product)
    cells = []
    for (jid, _job), label in zip(jobs.items(), labels):
        im = Image.open(os.path.join(folder, jid + ".png")).convert("RGB")
        im.thumbnail((360, 360))
        cells.append((im, label))
    cols = min(4, len(cells)) or 1
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 380, rows * 400), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(cells):
        x, y = (i % cols) * 380 + 10, (i // cols) * 400 + 30
        sheet.paste(im, (x, y))
        draw.text((x, y - 22), label, fill=(60, 60, 60))
    path = os.path.join(folder, "views_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
    sheet.save(path)
    return path


def cmd_convert(args, root, out):
    model = pm.load_model(root, args.product, args.model)
    if model is None:
        raise RenderError("write model.json first (product, source, status: draft, unit)")
    src = os.path.join(model["_dir"], model["source"])
    if not os.path.exists(src):
        raise RenderError("source %s not found next to model.json" % model["source"])
    try:
        import cascadio
    except ImportError:
        raise RenderError("converting STEP needs cascadio: pip install cascadio")
    glb = os.path.splitext(model["source"])[0] + ".glb"
    t = time.time()
    cascadio.step_to_glb(src, os.path.join(model["_dir"], glb), tol_linear=0.05, tol_angular=0.3)
    path = args.model or pm.model_path(root, args.product)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data["mesh"] = glb
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    out.write("CONVERTED %s -> %s in %.0fs\n" % (model["source"], glb, time.time() - t))
    return 0


def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Shape references from the product's 3D model.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("run", "views", "convert"):
        p = sub.add_parser(name)
        p.add_argument("--product", required=True)
        p.add_argument("--model", help="model.json outside products/ (a trial)")
        p.add_argument("--blender")
        if name == "views":
            p.add_argument("--views", default="front,front_left,three_quarter_left,side_left,rear,side_right,three_quarter_right")
            p.add_argument("--camera", default="eye_level")
            p.add_argument("--state", default="assembled")
    args = parser.parse_args(argv)
    try:
        return {"run": cmd_run, "views": cmd_views, "convert": cmd_convert}[args.cmd](args, root, out)
    except RenderError as e:
        out.write("ERROR %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
