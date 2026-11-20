"""Compare a generated picture's product with the same-angle 3D render (UTA_STYLE.md 1.18, 3.10, 4.7).

    python tools/shape_check.py run --product <产品> --image <成图> --render outputs/<产品>/renders/<id>.png [--slot S2]
    python tools/shape_check.py batch --product <产品> --task <check_set 写出的任务单> [--images outputs/<产品>] [--jobs 4]
    python tools/shape_check.py prompt --product <产品>        # the prompt and schema, for another reviewer

`batch` checks a whole round at once, several pictures in parallel: for every card with a render_ref line it
takes the newest picture of that slot (the text-free base when there is one) and prints one line per slot plus
every FIX line, so the failed slots are regenerated together.

A fresh reviewer that has not seen the card gets two pictures: the generated one and the plain render, whose
shape is right. It compares only the product's shape (outline, proportions, which parts there are, where and how
big), not colour, light, background, food, water, pets or people. On a drift it returns one English FIX line;
Codex appends it to the prompt (4.3) and regenerates. Results go to outputs/<产品>/shape_check.json.
Uses the same reviewer plumbing as tools/blind_check.py.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import re
import sys

import blind_check
import product_model as pm

ROOT = pm.ROOT
PROPORTIONS = ["same", "taller", "shorter", "wider", "narrower", "unsure"]
PROMPT = """You are checking product shape only.
Picture 1 is a generated product picture. Picture 2 is a plain 3D render of the same product from the same
angle; the shape in picture 2 is correct by definition.

Compare ONLY the product's shape in picture 1 with picture 2:
- the outline and the height-to-width proportions of the whole product;
- which parts there are, how many, where they sit and how big they are. Named parts: {parts}.

Ignore: colour, material, brightness, reflections, background, food, water, pets, people, hands, text, and
small camera differences (a slightly different angle, distance or lens is fine). If part of the product is
hidden in picture 1, judge only what you can see; do not report hidden parts as missing.

Answer:
- same_product: "yes" if picture 1 shows this product with the same shape, "no" if the shape clearly differs,
  "unsure" if you cannot tell.
- proportion: the whole product in picture 1 compared with picture 2: same, taller, shorter, wider, narrower,
  or unsure.
- differences: up to 5 shape differences, each a part name, what is wrong (missing, extra, moved, too big,
  too small, wrong shape) and a severity. "major": a part is missing or extra, sits somewhere else, has a
  different shape, or is clearly more than about 15% too big or too small. "minor": a small size or position
  difference that a slightly different camera angle or distance could explain. Leave it empty when there
  are none.
- fix_en: one English sentence of at most 25 words telling an image generator what to change so the product
  matches picture 2. Empty when nothing needs changing.
"""


def schema():
    return {
        "type": "object", "additionalProperties": False,
        "required": ["same_product", "proportion", "differences", "fix_en"],
        "properties": {
            "same_product": {"type": "string", "enum": ["yes", "no", "unsure"]},
            "proportion": {"type": "string", "enum": PROPORTIONS},
            "differences": {"type": "array", "maxItems": 5, "items": {
                "type": "object", "additionalProperties": False, "required": ["part", "problem", "severity"],
                "properties": {"part": {"type": "string"}, "problem": {"type": "string"},
                               "severity": {"type": "string", "enum": ["major", "minor"]}}}},
            "fix_en": {"type": "string"},
        },
    }


def prompt_for(model):
    parts = sorted((model or {}).get("parts") or {})
    return PROMPT.format(parts=", ".join(parts) if parts else "(not named; describe what you see)")


def parse_object(text):
    """The whole answer object (the first JSON object that carries same_product), not a nested one."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict) and "same_product" in obj:
            return obj
    raise blind_check.CheckError("the reviewer gave no shape answer")


def verdict(answer):
    """FAIL on a different product, a different overall proportion or any major difference; minor ones pass.
    UNSURE (cannot tell) goes to the normal blind check (4.7) and does not trigger a regeneration."""
    same, prop = answer.get("same_product"), answer.get("proportion")
    major = [d for d in answer.get("differences") or [] if d.get("severity") == "major"]
    if same == "no" or major or prop in ("taller", "shorter", "wider", "narrower"):
        return "FAIL"
    if same == "unsure":
        return "UNSURE"
    return "PASS"


def fix_line(answer):
    fix = (answer.get("fix_en") or "").strip()
    if not fix:
        bits = ["%s: %s" % (d.get("part", ""), d.get("problem", "")) for d in answer.get("differences") or []
                if d.get("severity") == "major"]
        if answer.get("proportion") not in (None, "same", "unsure"):
            bits.insert(0, "the whole product is %s than the reference" % answer["proportion"])
        fix = "Match the product shape exactly to the reference render: " + "; ".join(bits) if bits else ""
    words = fix.split()
    return " ".join(words[:30])


def save(root, product, entry):
    folder = os.path.join(root, "outputs", product)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "shape_check.json")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    rows.append(entry)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    return path


def check(root, product, image, render, slot="", reviewer=None, model_json=None, timeout=300, model=None):
    """Ask the reviewer; return the entry (nothing written yet)."""
    m = pm.load_model(root, product, model_json)
    answer = blind_check.ask([image, render], prompt_for(m), schema(), reviewer=reviewer, timeout=timeout, model=model,
                             parse=parse_object)
    return {"time": datetime.datetime.now().isoformat(timespec="seconds"), "slot": slot, "image": image,
            "render": render, "answer": answer, "verdict": verdict(answer)}


def report(entry, out):
    answer, result = entry["answer"], entry["verdict"]
    out.write("SHAPE %s %s\n" % (result, entry["slot"] or os.path.basename(entry["image"])))
    for d in answer.get("differences") or []:
        out.write("  - [%s] %s: %s\n" % (d.get("severity", "?"), d.get("part"), d.get("problem")))
    if result == "FAIL":
        out.write("FIX: %s\n" % fix_line(answer))
    elif result == "UNSURE":
        out.write("UNSURE: judge it in the blind check (4.7); do not regenerate on this alone\n")


def run(root, product, image, render, slot="", reviewer=None, model_json=None, timeout=300, model=None, out=sys.stdout):
    entry = check(root, product, image, render, slot, reviewer, model_json, timeout, model)
    save(root, product, entry)
    report(entry, out)
    return entry["verdict"]


CARD_MARK = re.compile(r"^=== cards/[^/]+/(.+)\.md ===\s*$")
VERSION = re.compile(r"_v(\d+)\.(png|jpg|jpeg|webp)$", re.I)


def render_refs_of(task_text):
    """[(slot, card stem, render path)] for every card in an emitted task that carries a render_ref line."""
    rows, stem, slot = [], None, None
    for line in task_text.splitlines():
        m = CARD_MARK.match(line)
        if m:
            stem, slot = m.group(1), m.group(1).split("_")[0]
            continue
        if stem and line.startswith("slot:"):
            slot = line.split(":", 1)[1].strip() or slot
        if stem and line.startswith("render_ref:"):
            rows.append((slot, stem, line.split(":", 1)[1].split("|")[0].strip()))
    return rows


def newest_picture(folder, slot):
    """The newest picture of a slot: the text-free base first, never the A+ desktop/mobile crops."""
    best = {}
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        m = VERSION.search(name)
        if not m or not name.startswith(slot + "_") or "_desktop_" in name or "_mobile_" in name:
            continue
        rank = (1 if "_base_v" in name else 0, int(m.group(1)))
        kind = "base" if rank[0] else "plain"
        if kind not in best or best[kind][0] < rank[1]:
            best[kind] = (rank[1], os.path.join(folder, name))
    pick = best.get("base") or best.get("plain")
    return pick[1] if pick else None


def batch(root, product, task, images=None, jobs=4, reviewer=None, model_json=None, timeout=300, model=None,
          out=sys.stdout):
    with open(task, encoding="utf-8") as fh:
        rows = render_refs_of(fh.read())
    images = images or os.path.join(root, "outputs", product)
    pairs, missing = [], []
    for slot, _stem, ref in rows:
        render = ref if os.path.isabs(ref) else os.path.join(root, ref)
        image = newest_picture(images, slot)
        if not image or not os.path.exists(render):
            missing.append((slot, "no picture yet" if not image else "no render (python tools/render_refs.py run)"))
        else:
            pairs.append((slot, image, render))
    entries, errors = {}, {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(check, root, product, image, render, slot, reviewer, model_json, timeout, model): slot
                   for slot, image, render in pairs}
        for f in concurrent.futures.as_completed(futures):
            try:
                entries[futures[f]] = f.result()
            except Exception as e:  # one stuck reviewer must not lose the others' answers
                errors[futures[f]] = str(e) or e.__class__.__name__
    counts = {"PASS": 0, "FAIL": 0, "UNSURE": 0}
    for slot, _image, _render in pairs:
        if slot in entries:
            save(root, product, entries[slot])
            report(entries[slot], out)
            counts[entries[slot]["verdict"]] += 1
        else:
            out.write("SHAPE ERROR %s: %s\n" % (slot, errors.get(slot)))
    for slot, why in missing:
        out.write("SHAPE SKIP %s: %s\n" % (slot, why))
    failed = [s for s, _i, _r in pairs if s in entries and entries[s]["verdict"] == "FAIL"]
    out.write("SHAPE BATCH %d checked: PASS %d, FAIL %d, UNSURE %d, error %d, skipped %d%s\n"
              % (len(pairs), counts["PASS"], counts["FAIL"], counts["UNSURE"], len(errors), len(missing),
                 ("  -> regenerate with the FIX lines: " + " ".join(failed)) if failed else ""))
    return counts, failed


def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Compare a generated product with its same-angle 3D render.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--product", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--render", required=True)
    p.add_argument("--slot", default="")
    p.add_argument("--model-json")
    p.add_argument("--reviewer", help="command template like blind_check.py --reviewer")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--model")
    p = sub.add_parser("batch")
    p.add_argument("--product", required=True)
    p.add_argument("--task", required=True, help="the task check_set.py emitted (cards with render_ref lines)")
    p.add_argument("--images", help="folder with the generated pictures (default outputs/<产品>)")
    p.add_argument("--jobs", type=int, default=4, help="pictures checked at the same time")
    p.add_argument("--model-json")
    p.add_argument("--reviewer")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--model")
    p = sub.add_parser("prompt")
    p.add_argument("--product", required=True)
    p.add_argument("--model-json")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "prompt":
            out.write(prompt_for(pm.load_model(root, args.product, args.model_json)) + "\n")
            out.write(json.dumps(schema(), indent=1) + "\n")
            return 0
        if args.cmd == "batch":
            _counts, failed = batch(root, args.product, args.task, args.images, args.jobs, args.reviewer,
                                    args.model_json, args.timeout, args.model, out)
            return 1 if failed else 0
        result = run(root, args.product, args.image, args.render, args.slot, args.reviewer, args.model_json,
                     args.timeout, args.model, out)
        return 0 if result != "FAIL" else 1
    except blind_check.CheckError as e:
        out.write("ERROR %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
