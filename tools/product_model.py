"""Product source (UTA_STYLE.md 1.18, 3.10): the 3D model gives the product's shape at any angle; Codex
generates everything else, then the result is compared with the same-angle render and regenerated if it drifts.

    python tools/product_model.py status --product <产品>
    python tools/product_model.py check

A product uses its 3D model only when products/<产品>/model/model.json says "status": "ready" (converted,
axes set, parts and states mapped, scale_check within 6% on every compared axis, approved by the user).
A passing scale check does not set status to ready by itself. Then every
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
import math
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
# scale item only (1.18): abs(CAD - measured) / measured * 100, worst axis. Not the shape-compare threshold.
SCALE_LIMIT_PCT = 6.0

# ---- the card -> camera table (1.18): the same for every product -------------------------------------------
# azimuth: degrees around the product from its front; negative = the camera moves to the left of a person standing
# in front of the product (check_set.VIEW_TEXT: "the camera a little to the left of centre")
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
# optional camera numbers on a card (1.18): all three replace the table's azimuth, elevation and focal length
CAM_FIELDS = ("cam_az", "cam_el", "cam_focal")
CAM_RANGE = {"cam_az": (-180, 180), "cam_el": (-15, 88), "cam_focal": (14, 135)}
RES_SCALE = 2     # a card with camera numbers renders at twice its canvas pixels, so Codex can crop and zoom
RENDER_RIG = 2    # bump when the renderer changes what a job looks like; every older render is redone once


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


def _as_mm(value):
    """Finite number of millimetres, or None when the value cannot be used (blank, text, bool, NaN)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        value = text
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _mm_text(value):
    number = _as_mm(value)
    if number is None:
        return repr(value)
    if number.is_integer():
        return str(int(number))
    return ("%.4f" % number).rstrip("0").rstrip(".")


def _scope_text(check):
    if not isinstance(check, dict):
        return "part/range not recorded"
    part = str(check.get("part") or "").strip()
    span = str(check.get("range") or "").strip()
    bits = []
    if part:
        bits.append("part %s" % part)
    if span:
        bits.append("range %s" % span)
    return ", ".join(bits) if bits else "part/range not recorded"


def _over_scale(pct):
    return pct > SCALE_LIMIT_PCT and not math.isclose(pct, SCALE_LIMIT_PCT, rel_tol=0.0, abs_tol=1e-6)


def scale_axis_pairs(check):
    """(pairs, structural_errors). Each pair is (label, model_mm, measured_mm)."""
    if not isinstance(check, dict):
        return [], ["scale_check must be an object; unknown size cannot pass"]
    pairs, errors = [], []
    if "axes" in check:
        listed = check["axes"]
        if not isinstance(listed, list) or not listed:
            errors.append("scale_check.axes must be a non-empty list; this shape cannot pass")
        else:
            for index, row in enumerate(listed, 1):
                if not isinstance(row, dict):
                    errors.append("scale_check.axes[%d] must be an object; unknown size cannot pass" % (index - 1))
                    continue
                label = str(row.get("axis") or row.get("dim") or ("axis%d" % index)).strip() or ("axis%d" % index)
                pairs.append((label, row.get("model_mm"), row.get("measured_mm")))
    if "model_mm" in check or "measured_mm" in check:
        label = str(check.get("axis") or check.get("dim") or "axis").strip() or "axis"
        pairs.append((label, check.get("model_mm"), check.get("measured_mm")))
    return pairs, errors


def scale_problems(check, unit="mm"):
    """Failures of the scale item (UTA_STYLE.md 1.18). [] means every recorded axis is within 6%.

    Per axis: abs(CAD - measured) / measured * 100. The worst axis decides.
    Unknown, blank, non-numeric, or non-positive measured size cannot pass. Does not change model status.
    """
    pairs, errors = scale_axis_pairs(check)
    out = list(errors)
    scope = _scope_text(check)
    if isinstance(check, dict):
        stated = str(check.get("unit") or "").strip()
        expected = str(unit or "").strip()
        if stated and expected and stated.lower() != expected.lower():
            out.append("scale_check: unit %s is not %s; compare CAD and the measurement in the same unit (%s)"
                       % (stated, expected, scope))
    if not pairs and not errors:
        out.append("scale_check: no axis to compare; unknown size cannot pass (%s)" % scope)
    judged = []
    for label, model_mm, measured_mm in pairs:
        cad, measured = _as_mm(model_mm), _as_mm(measured_mm)
        if cad is None or measured is None or measured <= 0:
            out.append("scale_check: axis %s CAD %s vs measured %s is unknown or zero and cannot pass (%s)"
                       % (label, _mm_text(model_mm), _mm_text(measured_mm), scope))
            continue
        pct = abs(cad - measured) / measured * 100.0
        judged.append((label, model_mm, measured_mm, pct))
    if any(_over_scale(pct) for *_, pct in judged):
        worst = max(pct for *_, pct in judged)
        detail = "; ".join(
            "%s CAD %s vs measured %s = %.2f%%" % (label, _mm_text(model_mm), _mm_text(measured_mm), pct)
            for label, model_mm, measured_mm, pct in judged)
        out.append("scale_check: max axis %.2f%% is over 6%% (%s). %s. Stop and check these numbers. "
                   "Do not stretch the model or rewrite the measurement." % (worst, scope, detail))
    return out


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
        out.extend(scale_problems(model.get("scale_check") or {}, model.get("unit") or ""))
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


def _written(fields, key):
    value = str(fields.get(key) or "").strip()
    return bool(value) and value.lower() != "none"


def _number(value):
    try:
        x = float(str(value).strip())
    except ValueError:
        return None
    if not math.isfinite(x):
        return None
    return int(x) if x.is_integer() else x


def _nearest(value, table, circular=False):
    """The rows of table nearest to value (several when they tie)."""
    gaps = {}
    for key, row in table.items():
        d = abs(value - row)
        gaps[key] = min(d, 360 - d) if circular else d
    best = min(gaps.values())
    return sorted(k for k, g in gaps.items() if g - best < 1e-6)


def cam_errors(fields, view=None, camera=None):
    """What is wrong with a card's camera numbers (1.18); [] when the card writes none of them or they are fine.
    view and camera are the card's product_view and camera: each must be the row nearest to its number."""
    written = [k for k in CAM_FIELDS if _written(fields, k)]
    if not written:
        return []
    if len(written) < len(CAM_FIELDS):
        return ["cam_az、cam_el、cam_focal 要三个一起写，或者都不写；现在只写了 %s（1.18）" % "、".join(written)]
    out, nums = [], {}
    for key in CAM_FIELDS:
        x, (lo, hi) = _number(fields[key]), CAM_RANGE[key]
        if x is None:
            out.append("%s 要写数字，现在是 %s（1.18）" % (key, fields[key]))
        elif not lo <= x <= hi:
            out.append("%s 要在 %d 到 %d 之间，现在是 %s（1.18）" % (key, lo, hi, fields[key]))
        else:
            nums[key] = x
    if out:
        return out
    if view in VIEW_AZIMUTH:
        near = _nearest(nums["cam_az"], VIEW_AZIMUTH, circular=True)
        if view not in near:
            out.append("cam_az=%s 时 product_view 要写离它最近的一档 %s，现在是 %s（1.18）"
                       % (fields["cam_az"], " 或 ".join(near), view))
    if camera in CAMERA_ELEVATION:
        near = _nearest(nums["cam_el"], CAMERA_ELEVATION)
        if camera not in near:
            out.append("cam_el=%s 时 camera 要写离它最近的一档 %s，现在是 %s（1.18）"
                       % (fields["cam_el"], " 或 ".join(near), camera))
    return out


def cam_numbers(fields):
    """{'azimuth', 'elevation', 'focal_mm'} from a card's camera numbers, or None when it writes none of them
    (or they are wrong: check_set.py reports that and the card does not get this far)."""
    if not any(_written(fields, k) for k in CAM_FIELDS) or cam_errors(fields):
        return None
    return {"azimuth": _number(fields["cam_az"]), "elevation": _number(fields["cam_el"]),
            "focal_mm": _number(fields["cam_focal"])}


def job_for(slot, fields):
    """The render job a card needs. fields: product_view, camera, shot_size, lens, product_state, focus, canvas,
    and optionally cam_az, cam_el, cam_focal (all three or none). The numbers replace the table's azimuth,
    elevation and focal length; the camera distance still follows the shot size, a close shot still aims at its
    focus part, and the render is twice the canvas pixels so Codex can crop and zoom (1.18)."""
    if slot == "M1":
        job = dict(MAIN_JOB)
    else:
        shot = fields.get("shot_size") or "medium"
        aim, fill = SHOT_FILL.get(shot, SHOT_FILL["medium"])
        focus = fields.get("focus") or "whole"
        job = {
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
    nums = cam_numbers(fields)
    if nums:
        job.update(nums, res_scale=RES_SCALE)
    return job


def card_gaps(shot, focus, state, model):
    """What a card asks of the model that the model cannot show yet (1.18). Without this the render would quietly
    fall back to the whole product (an unknown focus part) or the assembled product (an unknown state)."""
    out = []
    if SHOT_FILL.get(shot, ("whole",))[0] == "part" and focus and focus != "whole" \
            and focus not in (model.get("parts") or {}):
        out.append("3D 模型的 parts 里没有 %s：这张特写会退回拍整机。在 model.json 的 parts 里写上它对应哪些零件，"
                   "或者这张卡改写别的焦点部位（1.18）" % focus)
    if state and state != "assembled" and state not in (model.get("states") or {}):
        out.append("3D 模型的 states 里没有 %s：会退回渲染成组装好的样子。在 model.json 的 states 里写上这个状态要隐藏、"
                   "移动、旋转哪些零件（1.18）" % state)
    return out


def job_id(job, model):
    """Stable name for a render: the same angle of the same model revision is rendered once and reused."""
    key = json.dumps({"job": job, "revision": (model or {}).get("revision", 1),
                      "mesh": (model or {}).get("mesh", ""), "rig": RENDER_RIG}, sort_keys=True)
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
