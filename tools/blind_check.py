"""Blind structural check of finished images (UTA_STYLE.md 4.7).

The model that drew an image is the worst judge of it: in the pw002_s round every image
passed its own V1 check, including one with the water window on the wrong wall. Here a
fresh reviewer sees only the image (plus the product reference when a question needs it)
and a fixed list of questions with closed options. It never sees the card, the prompt or
the story. This script compares its answers with what the product card says.

    python tools/blind_check.py run --task outputs/task_v1.md [--only S1,S2]
    python tools/blind_check.py run --product pw002_s --image outputs/pw002_s/S2_capacity_v01.png [--state assembled]
    python tools/blind_check.py prompt --product pw002_s --image <file> [--state ...]   # for any other model
    python tools/blind_check.py score --product pw002_s --image <file> --answers answers.json
    python tools/blind_check.py check

Questions: references/checks_common.csv (every product) + products/<product>/checks.csv.
A product row with the same id replaces the common one; status 不用 drops it. Only rows with
status 已确认 decide pass or fail. 提示 rows (subjective ones such as "same as the reference?",
which in trials also flagged near-perfect images) are shown on the review form but never fail
an image; 待确认 rows (from unconfirmed guesses) are shown for reference.

Results go to outputs/<product>/blind_check.json (merged by image file name). An image with
any 已确认 answer wrong is a V1 failure: redo it with the printed FIX line (4.3).
"""
import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMON = os.path.join("references", "checks_common.csv")
COLUMNS = ["id", "question", "options", "expect", "may_hide", "states", "status", "source", "fix_en", "ref"]
STATUSES = ("已确认", "提示", "待确认", "不用")
HIDE_PREFIX = ("看不到", "看不清")
DEFAULT_STATE = "assembled"
CODEX = ("codex", "exec", "--skip-git-repo-check", "-s", "read-only")
PROMPT_HEAD = (
    "你在核对一张产品图。只根据图片回答下面的问题：不要猜，不要读任何文件，也不要运行命令。\n"
    "每题从给出的选项里选一个，答案原样抄写选项文字。看不清就选「看不到……」或「看不清」那一项。\n")
PROMPT_REF = "第一张图是要核对的图。第二张图是产品参考照片，只在题目问到它时用。\n"
PROMPT_TAIL = "\n按要求的 JSON 格式回答：每个题号对应一个选项文字，不要加别的内容。\n"


class CheckError(Exception):
    pass


# ---------- questions ----------

def split(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def read_rows(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise CheckError("%s: missing columns %s" % (path, ", ".join(missing)))
        rows = []
        for r in reader:
            if not (r.get("id") or "").strip():
                continue
            rows.append({
                "id": r["id"].strip(), "question": r["question"].strip(), "options": split(r["options"]),
                "expect": split(r["expect"]), "may_hide": (r["may_hide"] or "").strip().lower() == "yes",
                "states": split(r["states"]), "status": (r["status"] or "").strip(), "source": (r["source"] or "").strip(),
                "fix_en": (r["fix_en"] or "").strip(), "ref": (r["ref"] or "").strip(),
            })
        return rows


def load_checks(root, product):
    merged = {}
    for row in read_rows(os.path.join(root, COMMON)) + read_rows(os.path.join(root, "products", product, "checks.csv")):
        merged.pop(row["id"], None)
        merged[row["id"]] = row
    return [r for r in merged.values() if r["status"] != "不用"]


def for_state(checks, state):
    return [c for c in checks if not c["states"] or state in c["states"]]


def validate_rows(rows, where):
    errors, seen = [], set()
    for r in rows:
        tag = "%s %s" % (where, r["id"])
        if r["id"] in seen:
            errors.append("%s: duplicate id" % tag)
        seen.add(r["id"])
        if not r["question"]:
            errors.append("%s: no question" % tag)
        if len(r["options"]) < 2:
            errors.append("%s: needs at least two options" % tag)
        if not r["expect"]:
            errors.append("%s: no expected answer" % tag)
        for e in r["expect"]:
            if e not in r["options"]:
                errors.append("%s: expected answer '%s' is not an option" % (tag, e))
        if r["status"] not in STATUSES:
            errors.append("%s: status must be one of %s" % (tag, "/".join(STATUSES)))
        if r["may_hide"] and not any(o.startswith(HIDE_PREFIX) for o in r["options"]):
            errors.append("%s: may_hide is yes but no option starts with 看不到/看不清" % tag)
        if r["status"] == "已确认" and not r["fix_en"]:
            errors.append("%s: no fix_en (needed for the redo line)" % tag)
        if r["status"] == "已确认" and not r["source"]:
            errors.append("%s: no source (which confirmed line it comes from)" % tag)
    return errors


def validate(root=ROOT):
    errors = []
    try:
        errors += validate_rows(read_rows(os.path.join(root, COMMON)), COMMON)
    except CheckError as exc:
        errors.append(str(exc))
    products = os.path.join(root, "products")
    for name in sorted(os.listdir(products)) if os.path.isdir(products) else []:
        path = os.path.join(products, name, "checks.csv")
        if not os.path.isfile(path):
            continue
        try:
            rows = read_rows(path)
        except CheckError as exc:
            errors.append(str(exc))
            continue
        where = "products/%s/checks.csv" % name
        errors += validate_rows(rows, where)
        for r in rows:
            if r["ref"] and not os.path.isfile(os.path.join(root, r["ref"])):
                errors.append("%s %s: ref %s does not exist" % (where, r["id"], r["ref"]))
    return errors


# ---------- prompt and reviewer ----------

def build_prompt(checks):
    has_ref = any(c["ref"] for c in checks)
    lines = [PROMPT_HEAD + (PROMPT_REF if has_ref else "")]
    for n, c in enumerate(checks, 1):
        lines.append("%d. [%s] %s\n   选项：%s" % (n, c["id"], c["question"], "；".join(c["options"])))
    return "\n".join(lines) + PROMPT_TAIL


def build_schema(checks):
    return {
        "type": "object",
        "properties": {c["id"]: {"type": "string", "enum": c["options"]} for c in checks},
        "required": [c["id"] for c in checks],
        "additionalProperties": False,
    }


def ref_images(root, checks):
    refs = []
    for c in checks:
        if c["ref"] and c["ref"] not in refs:
            refs.append(c["ref"])
    return [os.path.join(root, r) for r in refs[:1]]


def parse_answers(text):
    """The last JSON object in the text; accepts {"K1": "..."} or {"answers": {...}}."""
    dec = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            found = obj
    if found is None:
        raise CheckError("the reviewer gave no JSON answer")
    if isinstance(found.get("answers"), dict):
        found = found["answers"]
    return {str(k): str(v).strip() for k, v in found.items()}


def ask(images, prompt, schema, reviewer=None, timeout=300, model=None, parse=None):
    """Run the reviewer in an empty folder so it has nothing to read but what it is given.

    Image paths are made absolute first: the reviewer runs in that empty folder, and a relative
    path would silently attach nothing (it then answers 看不到 to everything)."""
    images = [os.path.abspath(i) for i in images]
    for img in images:
        if not os.path.isfile(img):
            raise CheckError("image not found: %s" % img)
    work = tempfile.mkdtemp(prefix="uta_blind_")
    try:
        prompt_file = os.path.join(work, "prompt.txt")
        schema_file = os.path.join(work, "schema.json")
        out_file = os.path.join(work, "answer.json")
        with open(prompt_file, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        with open(schema_file, "w", encoding="utf-8") as fh:
            json.dump(schema, fh, ensure_ascii=False)
        if reviewer:
            cmd = reviewer.format(prompt=shlex.quote(prompt_file), schema=shlex.quote(schema_file),
                                  out=shlex.quote(out_file), workdir=shlex.quote(work),
                                  images=" ".join(shlex.quote(i) for i in images))
            proc = subprocess.run(cmd, shell=True, cwd=work, capture_output=True, text=True, timeout=timeout)
        else:
            exe = shutil.which(CODEX[0])
            if not exe:
                raise CheckError("codex is not installed; pass --reviewer, or use `prompt` and `score` with another model")
            argv = [exe] + list(CODEX[1:]) + ["-C", work, "--output-schema", schema_file, "-o", out_file]
            if model:
                argv += ["-m", model]
            for img in images:
                argv += ["-i", img]
            argv.append("-")
            proc = subprocess.run(argv, input=prompt, cwd=work, capture_output=True, text=True, timeout=timeout)
        text = ""
        if os.path.isfile(out_file):
            with open(out_file, encoding="utf-8") as fh:
                text = fh.read()
        if not text.strip():
            text = proc.stdout or ""
        if proc.returncode != 0 and not text.strip():
            raise CheckError("reviewer failed (exit %d): %s" % (proc.returncode, (proc.stderr or "").strip()[-300:]))
        return (parse or parse_answers)(text)
    except subprocess.TimeoutExpired:
        raise CheckError("reviewer timed out after %ds" % timeout)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- scoring ----------

def verdict(check, answer):
    if answer is None:
        return "没答"
    if answer not in check["options"]:
        return "无效"
    if answer in check["expect"]:
        return "对"
    if check["may_hide"] and answer.startswith(HIDE_PREFIX):
        return "看不到"
    return "错"


def score(checks, answers):
    results, fails = [], []
    for c in checks:
        v = verdict(c, answers.get(c["id"]))
        counts = c["status"] == "已确认"
        results.append({"id": c["id"], "question": c["question"], "answer": answers.get(c["id"]),
                        "expect": c["expect"], "verdict": v, "counts": counts, "hint": c["status"] == "提示",
                        "fix_en": c["fix_en"]})
        if counts and v in ("错", "无效", "没答"):
            fails.append(c)
    summary = {k: sum(1 for r in results if r["counts"] and r["verdict"] == k) for k in ("对", "错", "看不到", "无效", "没答")}
    summary["参考"] = sum(1 for r in results if not r["counts"])
    summary["提示"] = sum(1 for r in results if r["hint"] and r["verdict"] == "错")
    fix = "; ".join(c["fix_en"] for c in fails if c["fix_en"])
    return {"results": results, "summary": summary, "passed": not fails, "fix": fix}


def results_path(root, product):
    return os.path.join(root, "outputs", product, "blind_check.json")


def save(root, product, entries):
    path = results_path(root, product)
    data = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    for e in entries:
        data[os.path.basename(e["image"])] = e
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return path


def report(entry, out):
    s = entry["summary"]
    head = "BLIND %s %s  对 %d  错 %d  看不到 %d  参考 %d" % (
        entry.get("slot") or "-", os.path.basename(entry["image"]), s["对"], s["错"] + s["无效"] + s["没答"],
        s["看不到"], s["参考"])
    if not entry.get("seen", True):
        out.write(head + "  UNSEEN（审核方说画面里没有产品：先确认图片真的传进去了，再请人看一眼）\n")
        return
    out.write(head + ("" if entry["passed"] else "  V1 FAIL") + "\n")
    for r in entry["results"]:
        if r["counts"] and r["verdict"] in ("错", "无效", "没答"):
            out.write("  ✗ %s %s\n    答「%s」，应为「%s」\n" % (r["id"], r["question"], r["answer"], "」或「".join(r["expect"])))
        elif r.get("hint") and r["verdict"] == "错":
            out.write("  ! %s（提示，不算不合格）答「%s」\n" % (r["id"], r["answer"]))
        elif not r["counts"] and r["verdict"] == "错":
            out.write("  ? %s（待确认，不算）答「%s」\n" % (r["id"], r["answer"]))
    if not entry["passed"] and entry["fix"]:
        out.write("  FIX: %s\n" % entry["fix"])


def check_image(root, product, image, state, reviewer=None, timeout=300, model=None, slot=""):
    checks = for_state(load_checks(root, product), state)
    if not checks:
        raise CheckError("no questions for %s in state %s (products/%s/checks.csv)" % (product, state, product))
    images = [image] + ref_images(root, checks)
    answers = ask(images, build_prompt(checks), build_schema(checks), reviewer, timeout, model)
    entry = finish(score(checks, answers), answers)
    entry.update(image=os.path.relpath(os.path.abspath(image), root).replace(os.sep, "/"), slot=slot, state=state,
                 reviewer=reviewer or "codex exec (read-only, empty folder)")
    return entry


def finish(entry, answers):
    """A reviewer that saw no product at all did not really look (the image may not have arrived).
    That is not a verdict on the image: mark it unseen so a person looks, and do not use its FIX."""
    entry["seen"] = answers.get("G3") != "0"
    if not entry["seen"]:
        entry["passed"] = False
        entry["fix"] = ""
    return entry


# ---------- commands ----------

def task_images(root, task, only):
    sys.path.insert(0, HERE)
    import check_set
    import review_form
    with open(task, encoding="utf-8-sig") as fh:
        _v, header, cards = check_set.parse_task(fh.read())
    product = header["product"]
    folder = os.path.join(root, "outputs", product)
    jobs = []
    for card in cards:
        if only and card.slot not in only:
            continue
        state = (card.f("product_state") or "").strip() or DEFAULT_STATE
        if state.lower() == "none":
            state = DEFAULT_STATE
        for _label, path in review_form.card_images(card, folder):
            jobs.append((card.slot, path, state))
    return product, jobs


def cmd_run(args, root, out):
    only = set(s.strip() for s in (args.only or "").split(",") if s.strip())
    if args.task:
        product, jobs = task_images(root, args.task, only)
    else:
        if not args.product or not args.image:
            raise CheckError("run needs --task, or --product with one or more --image")
        product = args.product
        jobs = [("", img, args.state or DEFAULT_STATE) for img in args.image]
    if not jobs:
        out.write("BLIND nothing to check (no finished images found)\n")
        return 0
    entries, failed, errors, unseen = [], [], [], []
    for slot, img, state in jobs:
        try:
            entry = check_image(root, product, img, state, args.reviewer, args.timeout, args.model, slot)
        except CheckError as exc:
            errors.append("%s %s: %s" % (slot or "-", os.path.basename(img), exc))
            out.write("BLIND ERROR %s %s: %s\n" % (slot or "-", os.path.basename(img), exc))
            continue
        entries.append(entry)
        report(entry, out)
        if not entry.get("seen", True):
            unseen.append(slot or os.path.basename(img))
        elif not entry["passed"]:
            failed.append(slot or os.path.basename(img))
    path = save(root, product, entries) if entries else ""
    out.write("SUMMARY %d images checked  V1 fail %d%s  unseen %d%s  errors %d%s\n" % (
        len(entries), len(failed), (" (" + ", ".join(failed) + ")") if failed else "",
        len(unseen), (" (" + ", ".join(unseen) + ")") if unseen else "", len(errors),
        ("  results " + os.path.relpath(path, root).replace(os.sep, "/")) if path else ""))
    return 1 if errors and not entries else 0


def cmd_prompt(args, root, out):
    checks = for_state(load_checks(root, args.product), args.state or DEFAULT_STATE)
    out.write("ATTACH: %s\n\n" % " ".join([args.image] + [os.path.relpath(r, root) for r in ref_images(root, checks)]))
    out.write(build_prompt(checks))
    out.write("\nSCHEMA:\n%s\n" % json.dumps(build_schema(checks), ensure_ascii=False, indent=1))
    return 0


def cmd_score(args, root, out):
    checks = for_state(load_checks(root, args.product), args.state or DEFAULT_STATE)
    with open(args.answers, encoding="utf-8") as fh:
        answers = parse_answers(fh.read())
    entry = finish(score(checks, answers), answers)
    entry.update(image=os.path.relpath(os.path.abspath(args.image), root).replace(os.sep, "/"), slot=args.slot or "",
                 state=args.state or DEFAULT_STATE, reviewer="manual")
    report(entry, out)
    save(root, args.product, [entry])
    return 0


def cmd_check(args, root, out):
    errors = validate(root)
    for e in errors:
        out.write("CHECKS ERROR %s\n" % e)
    if not errors:
        out.write("CHECKS OK\n")
    return 1 if errors else 0


def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Blind structural check of finished images (UTA_STYLE.md 4.7).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--task")
    p.add_argument("--only", help="slots, comma separated")
    p.add_argument("--product")
    p.add_argument("--image", action="append")
    p.add_argument("--state")
    p.add_argument("--reviewer", help="shell command with {prompt} {schema} {out} {images} {workdir}; default codex exec")
    p.add_argument("--model")
    p.add_argument("--timeout", type=int, default=300)
    p = sub.add_parser("prompt")
    p.add_argument("--product", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--state")
    p = sub.add_parser("score")
    p.add_argument("--product", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--state")
    p.add_argument("--slot")
    sub.add_parser("check")
    args = parser.parse_args(argv)
    try:
        return {"run": cmd_run, "prompt": cmd_prompt, "score": cmd_score, "check": cmd_check}[args.cmd](args, root, out)
    except CheckError as exc:
        out.write("BLIND ERROR %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
