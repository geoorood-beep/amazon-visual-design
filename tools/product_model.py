"""Product source (UTA_STYLE.md 1.18, 3.10): the 3D model gives the product's shape at any angle; Codex
generates everything else, then the result is compared with the same-angle render and regenerated if it drifts.

    python tools/product_model.py status --product <产品>
    python tools/product_model.py check

A product uses its 3D model only when products/<产品>/model/model.json says "status": "ready" (converted,
axes set, parts and states mapped, scaled against one real measurement, approved by the user). Then every
image card, M1 included, takes the route render_ref:

    render_ref   render the product at this card's view, camera, shot, lens and state (shape only), attach it
                 as the shape reference next to the product photo (colour and material), generate the whole
                 picture, compare the product with the render (tools/shape_check.py), regenerate on drift
    generate     no ready model, or no renderer on this machine: generate as before (the round does not stop)

The CAD and render files never go into the repository (it is public); .gitignore keeps them out.
Standard library only.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTES = ("render_ref", "generate")
STATUSES = ("draft", "ready")
MODEL_EXT = (".stp", ".step", ".igs", ".iges", ".glb", ".gltf", ".fbx", ".obj", ".stl", ".blend", ".usdz")
BLENDER_PATHS = ("/Applications/Blender.app/Contents/MacOS/Blender",
                 os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"))
REQUIRED = ("product", "source", "status", "unit")
AXES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")

# ---- the card -> camera table (1.18): the same for every product -------------------------------------------
# azimuth: degrees around the product from its front; negative = the product's left side seen by the camera
VIEW_AZIMUTH = {"front": 0, "front_left": -20, "front_right": 20, "three_quarter_left": -40,
                "three_quarter_right": 40, "side_left": -90, "side_right": 90, "rear": 180, "cutaway": 0}
# elevation: degrees above the aim point; low_angle sits near the floor and looks slightly up
CAMERA_ELEVATION = {"top_down": 88, "down_45": 45, "eye_level": 8, "low_angle": -8}
# how much of the frame the aimed-at thing fills; close shots aim at the focus part, the others at the product
SHOT_FILL = {"extreme_close": ("part", 0.92), "close": ("part", 0.72), "medium": ("whole", 0.78),
             "full": ("whole", 0.56), "wide": ("whole", 0.32)}
LENS_MM = {"standard": 50, "wide_close": 24, "ground_level": 28, "action_freeze": 50, "peek_frame": 50,
           "pet_pov": 35, "hero_low": 28, "surface_wide": 24, "reach_in": 24, "hero_wide": 24}
CANVAS_PX = {"1:1": (1024, 1024), "4:5": (1024, 1280), "3:2": (1200, 800), "2.44:1": (1464, 600)}
# M1 has no shot fields: a calm front three-quarter, standard lens, product filling the square
MAIN_JOB = {"view": "front_left", "camera": "eye_level", "shot": "medium", "lens": "standard",
            "state": "assembled", "focus": "whole", "canvas": "1:1", "elevation": 12, "fill": 0.86}


def model_dir(root, product):
    return os.path.join(root, "products", product, "model")


def model_path(root, product):
    return os.path.join(model_dir(root, product), "model.json")


def load_model(root, product, path=None):
    """model.json as a dict, or None when the product has no model."""
    path = path or model_path(root, product)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        model = json.load(fh)
    model["_dir"] = os.path.dirname(os.path.abspath(path))
    return model


def model_problems(root, product, model):
    out = []
    for key in REQUIRED:
        if not str(model.get(key, "")).strip():
            out.append("model.json is missing '%s'" % key)
    if model.get("status") not in STATUSES:
        out.append("status must be draft or ready")
    if model.get("product") and model["product"] != product:
        out.append("model.json is for '%s', not '%s'" % (model["product"], product))
    axes = model.get("axes") or {}
    for key in ("front", "up"):
        if key in axes and axes[key] not in AXES:
            out.append("axes.%s must be one of %s" % (key, ", ".join(AXES)))
    for state, spec in (model.get("states") or {}).items():
        if not isinstance(spec, dict):
            out.append("states.%s must be an object (hide / move / rotate)" % state)
    if model.get("status") == "ready":
        check = model.get("scale_check") or {}
        if not (check.get("model_mm") and check.get("measured_mm")):
            out.append("a ready model needs scale_check with model_mm and measured_mm (one real measurement)")
        elif abs(float(check["model_mm"]) - float(check["measured_mm"])) > max(3.0, 0.02 * float(check["measured_mm"])):
            out.append("scale_check: model %s mm vs measured %s mm differ by more than 2%%" % (check["model_mm"], check["measured_mm"]))
        if not str(model.get("approved", "")).strip():
            out.append("a ready model needs 'approved' (who looked at the renders against the photos, and when)")
        if not (axes.get("front") and axes.get("up")):
            out.append("a ready model needs axes.front and axes.up (which way the product faces and stands)")
        if not str(model.get("mesh", "")).strip():
            out.append("a ready model needs 'mesh' (the converted .glb next to model.json)")
    return out


def is_ready(root, product):
    model = load_model(root, product)
    return bool(model) and model.get("status") == "ready" and not model_problems(root, product, model)


def renderer():
    """Path to Blender, or None."""
    found = shutil.which("blender")
    if found:
        return found
    return next((p for p in BLENDER_PATHS if os.path.exists(p)), None)


def route(slot, interaction="", lens="", ready=False, has_renderer=True):
    """Which product source one image card takes (1.18): the 3D shape reference whenever it can be had."""
    return "render_ref" if ready and has_renderer else "generate"


STEPS = {
    "render_ref": ("attach the render below FIRST as the shape reference (outline, proportions, every part's "
                   "position), the product photo for colour and material; generate the whole picture; then run "
                   "tools/shape_check.py on the result and regenerate with its FIX line if the product drifted"),
    "generate": "generate as usual (no ready model, or no renderer on this machine)",
}


def job_for(slot, fields):
    """The render job a card needs. fields: product_view, camera, shot_size, lens, product_state, focus, canvas."""
    if slot == "M1":
        return dict(MAIN_JOB)
    shot = fields.get("shot_size") or "medium"
    aim, fill = SHOT_FILL.get(shot, SHOT_FILL["medium"])
    focus = fields.get("focus") or "whole"
    return {
        "view": fields.get("product_view") or "front",
        "camera": fields.get("camera") or "eye_level",
        "shot": shot,
        "lens": fields.get("lens") or "standard",
        "state": fields.get("product_state") or "assembled",
        "focus": focus if aim == "part" else "whole",
        "canvas": fields.get("canvas") or "1:1",
        "elevation": CAMERA_ELEVATION.get(fields.get("camera") or "eye_level", 8),
        "fill": fill,
    }


def job_id(job, model):
    """Stable name for a render: the same angle of the same model revision is rendered once and reused."""
    key = json.dumps({"job": job, "revision": (model or {}).get("revision", 1),
                      "mesh": (model or {}).get("mesh", "")}, sort_keys=True)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def render_dir(root, product):
    return os.path.join(root, "outputs", product, "renders")


def render_path(root, product, jid):
    return os.path.join(render_dir(root, product), jid + ".png")


def shown(path, root=ROOT):
    full, base = os.path.abspath(path), os.path.abspath(root)
    return os.path.relpath(full, base).replace(os.sep, "/") if full.startswith(base + os.sep) else full


def save_jobs(root, product, jobs):
    """Merge {id: job} into outputs/<产品>/renders/jobs.json, which tools/render_refs.py reads."""
    folder = render_dir(root, product)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "jobs.json")
    current = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            current = json.load(fh)
    current.update(jobs)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(current, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return path


def cmd_status(args, root, out):
    model = load_model(root, args.product)
    if model is None:
        out.write("MODEL none: %s has no products/%s/model/model.json; every card is generated\n" % (args.product, args.product))
        return 0
    problems = model_problems(root, args.product, model)
    out.write("MODEL %s  status=%s  source=%s  mesh=%s\n" % (args.product, model.get("status"), model.get("source"), model.get("mesh")))
    for p in problems:
        out.write("! %s\n" % p)
    out.write("renderer: %s\n" % (renderer() or "not installed (cards fall back to generate)"))
    out.write("3D route: %s\n" % ("on" if is_ready(root, args.product) else "off"))
    return 1 if problems else 0


def cmd_check(args, root, out):
    bad = 0
    base = os.path.join(root, "products")
    for product in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        model = load_model(root, product)
        if model is None:
            continue
        for p in model_problems(root, product, model):
            out.write("FAIL %s: %s\n" % (product, p))
            bad += 1
    out.write("OK  model.json files\n" if not bad else "%d problem(s)\n" % bad)
    return 1 if bad else 0


def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Product source: the 3D model gives the shape; Codex the rest.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status")
    p.add_argument("--product", required=True)
    sub.add_parser("check")
    args = parser.parse_args(argv)
    return {"status": cmd_status, "check": cmd_check}[args.cmd](args, root, out)


if __name__ == "__main__":
    sys.exit(main())
