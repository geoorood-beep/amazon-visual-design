"""Product source (UTA_STYLE.md 1.18, 3.10): generated, or rendered from the product's 3D model.

    python tools/product_model.py status --product <产品>
    python tools/product_model.py check

A product takes the 3D route only when products/<产品>/model/model.json says "status": "ready" (converted,
materials set, calibrated against the real photos, renders approved by the user). Without it every card is
generated exactly as before. The route of each card is decided here, not by the card writer:

    render            M1: the whole picture is a render on white
    render_composite  the product alone (interaction product_only) or the hero wide lens: render the product
                      layer, generate the scene around it, then harmonise
    render_ref        everything else: generate as before, with a same-angle render as the product reference
    generate          no ready model, or no renderer on this machine (the round does not stop)

The CAD files themselves never go into the repository (it is public); .gitignore keeps them out.
Standard library only.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTES = ("render", "render_composite", "render_ref", "generate")
STATUSES = ("draft", "ready")
MODEL_EXT = (".stp", ".step", ".igs", ".iges", ".glb", ".gltf", ".fbx", ".obj", ".stl", ".blend", ".usdz")
BLENDER_PATHS = ("/Applications/Blender.app/Contents/MacOS/Blender",)
REQUIRED = ("product", "source", "status", "unit")


def model_dir(root, product):
    return os.path.join(root, "products", product, "model")


def load_model(root, product):
    """model.json as a dict, or None when the product has no model."""
    path = os.path.join(model_dir(root, product), "model.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def model_problems(root, product, model):
    out = []
    for key in REQUIRED:
        if not str(model.get(key, "")).strip():
            out.append("model.json is missing '%s'" % key)
    if model.get("status") not in STATUSES:
        out.append("status must be draft or ready")
    if model.get("product") and model["product"] != product:
        out.append("model.json is for '%s', not '%s'" % (model["product"], product))
    if model.get("status") == "ready":
        check = model.get("scale_check") or {}
        if not (check.get("model_mm") and check.get("measured_mm")):
            out.append("a ready model needs scale_check with model_mm and measured_mm (one real measurement)")
        elif abs(float(check["model_mm"]) - float(check["measured_mm"])) > max(3.0, 0.02 * float(check["measured_mm"])):
            out.append("scale_check: model %s mm vs measured %s mm differ by more than 2%%" % (check["model_mm"], check["measured_mm"]))
        if not str(model.get("approved", "")).strip():
            out.append("a ready model needs 'approved' (who looked at the renders against the photos, and when)")
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
    """Which product source one image card takes (1.18)."""
    if not ready or not has_renderer:
        return "generate"
    if slot == "M1":
        return "render"
    if interaction == "product_only" or lens == "hero_wide":
        return "render_composite"
    return "render_ref"


STEPS = {
    "render": "render the whole picture from the model on pure white (no generation), camera and light from the card",
    "render_composite": ("render the product layer at the card's view, camera, lens and light; generate the scene "
                         "around it with the product masked; harmonise shadow, contact and reflections; paste the "
                         "product's outline back from the render; then typeset"),
    "render_ref": ("render the product at this card's product_view and camera first and attach that render as the "
                   "product reference; then generate as usual"),
    "generate": "generate as usual (no ready model, or no renderer on this machine)",
}


def cmd_status(args, root, out):
    model = load_model(root, args.product)
    if model is None:
        out.write("MODEL none: %s has no products/%s/model/model.json; every card is generated\n" % (args.product, args.product))
        return 0
    problems = model_problems(root, args.product, model)
    out.write("MODEL %s  status=%s  source=%s\n" % (args.product, model.get("status"), model.get("source")))
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
    parser = argparse.ArgumentParser(description="Product source: generated or rendered from a 3D model.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status")
    p.add_argument("--product", required=True)
    sub.add_parser("check")
    args = parser.parse_args(argv)
    return {"status": cmd_status, "check": cmd_check}[args.cmd](args, root, out)


if __name__ == "__main__":
    sys.exit(main())
