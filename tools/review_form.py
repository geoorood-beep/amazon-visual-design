"""Build the review form (UTA_STYLE.md 4.5) after a round of images is done.

Usage (Codex, UTA_STYLE.md 3.2 step 10):

    python tools/review_form.py --task outputs/task.md --report outputs/report.md

It reads the task sheet (what each card asked for), finds the newest output
file of every card under outputs/<product>/ by the names check_card.py prints,
optionally reads the report (V1-V5 lines and the picture description), and
writes one self-contained page outputs/<product>/review_vNN.html from
grok/review_template.html. Images are embedded so the page opens anywhere;
pass --link to reference them by relative path instead.

The person reviewing writes a suggestion only under images that need work;
anything left blank passes. The page turns that into a UTA-REVIEW v1 block
for Grok, which edits the cards and sends a patch task back to Codex.

Standard library only.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_set  # noqa: E402

ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "grok", "review_template.html")
SHEET_RE = re.compile(r'(<script id="sheet" type="application/json">)(.*?)(</script>)', re.S)
IMAGE_EXT = ("png", "jpg", "jpeg", "webp")
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
FACT_ROW = re.compile(r"^\|\s*(F\d+)\s*\|\s*([^|]*)\|")
KIND_LABEL = {"main": "主图", "sub": "副图", "panel": "A+ 小格"}


def newest(folder, stem, suffix=""):
    """Newest '<stem><suffix>_vNN.<ext>' in folder, or None."""
    if not os.path.isdir(folder):
        return None
    pattern = re.compile(re.escape(stem + suffix) + r"_v(\d+)\.(%s)$" % "|".join(IMAGE_EXT), re.I)
    best = None
    for name in os.listdir(folder):
        m = pattern.match(name)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), name)
    return os.path.join(folder, best[1]) if best else None


def card_images(card, folder):
    stem = os.path.splitext(os.path.basename(card.path))[0]
    if card.kind == "screen":
        pairs = [("电脑端 1464×600", newest(folder, stem, "_desktop_1464x600")),
                 ("手机端 600×450", newest(folder, stem, "_mobile_600x450"))]
        found = [(label, path) for label, path in pairs if path]
        if found:
            return found
    single = newest(folder, stem)
    return [("成图", single)] if single else []


def image_src(path, out_path, link):
    if link:
        return os.path.relpath(path, os.path.dirname(os.path.abspath(out_path))).replace(os.sep, "/")
    ext = path.rsplit(".", 1)[-1].lower()
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (MIME.get(ext, "image/png"), base64.b64encode(fh.read()).decode("ascii"))


def load_facts(root, product):
    facts = {}
    path = os.path.join(root, "products", product, "PRODUCT.md")
    if os.path.isfile(path):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                m = FACT_ROW.match(line)
                if m:
                    facts[m.group(1)] = m.group(2).strip()
    return facts


def parse_report(text):
    """{slot: {'result', 'seen', 'checks', 'panels'}} from a 4.4 report."""
    blocks, slot = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"^图位[:：]\s*([A-Za-z0-9]+)", line)
        if m:
            slot = m.group(1)
            blocks[slot] = {"result": "", "seen": "", "checks": [], "panels": ""}
            continue
        if slot is None or not line:
            continue
        b = blocks[slot]
        if re.match(r"^V\d", line) or line.startswith("生成次数"):
            b["checks"].append(line)
        elif line.startswith("画面说明"):
            b["seen"] = re.split(r"[:：]", line, 1)[1].strip()
        elif line.startswith("小格"):
            b["panels"] = re.split(r"[:：]", line, 1)[1].strip()
            b["checks"].append(line)
        elif line.startswith("汇总"):
            slot = None
    for b in blocks.values():
        failed = [c.split()[0] for c in b["checks"] if re.match(r"^V\d", c) and re.search(r"不合格|不通过|未通过", c)]
        b["result"] = ("候选（%s 没过）" % "、".join(failed)) if failed else ("通过" if b["checks"] else "")
    return blocks


def panel_result(blocks, slot):
    module = re.match(r"(P\d)", slot).group(1)
    panels = blocks.get(module, {}).get("panels", "")
    m = re.search(re.escape(slot) + r"\s*([^，,；;]+)", panels)
    if not m:
        return {}
    status = m.group(1).strip()
    return {"result": status if "通过" in status else "候选（%s）" % status, "seen": "", "checks": []}


def has(v):
    return bool(v) and v.strip().lower() != "none"


def entry(card, facts, blocks, folder, out_path, link):
    f = card.f
    kind = KIND_LABEL.get(card.kind, "")
    if card.kind == "screen":
        kind = "A+ 单场景" if card.module == "scene" else "A+ 模块"
    pet = f("pet")
    person = f("human_action") if has(f("human_action")) else ""
    if has(f("person_id")) and f("person_id").strip() != "hands":
        person = (f("person_id") + " " + person).strip()
    codex = blocks.get(card.slot) or (panel_result(blocks, card.slot) if card.kind == "panel" else {})
    fact = f("selling_point")
    return {
        "slot": card.slot, "card": card.path, "kind": kind,
        "module": card.module if card.kind == "screen" and card.module != "scene" else "",
        "fact": fact if has(fact) else "", "fact_text": facts.get(fact, ""),
        "story": f("story") if has(f("story")) else "", "evidence": f("evidence") if has(f("evidence")) else "",
        "scene": f("scene") if has(f("scene")) else "", "pet": pet if has(pet) else "", "person": person,
        "lens": f("lens") if has(f("lens")) and f("lens") != "standard" else "",
        "shot": {"size": f("shot_size"), "camera": f("camera"), "view": f("product_view"), "light": f("light_setup")},
        "eyebrow": f("eyebrow"), "headline": f("headline"), "subtitle": f("subtitle"),
        "hero": f("hero_number"), "label": f("label"), "fix": f("fix") if has(f("fix")) else "",
        "codex": {"result": codex.get("result", ""), "seen": codex.get("seen", ""), "checks": codex.get("checks", [])},
        "images": [{"label": label, "name": os.path.basename(path), "src": image_src(path, out_path, link)}
                   for label, path in card_images(card, folder)],
    }


def next_form(folder):
    taken = [int(m.group(1)) for m in (re.match(r"review_v(\d+)\.html$", n) for n in
             (os.listdir(folder) if os.path.isdir(folder) else [])) if m]
    n = max(taken) + 1 if taken else 1
    return os.path.join(folder, "review_v%02d.html" % n), n


def build(task_path, report_path=None, out_path=None, link=False, root=ROOT, template=TEMPLATE):
    with open(task_path, encoding="utf-8-sig") as fh:
        _version, header, cards = check_set.parse_task(fh.read())
    product = header["product"]
    folder = os.path.join(root, "outputs", product)
    if out_path:
        m = re.search(r"review_v(\d+)\.html$", out_path)
        round_no = int(m.group(1)) if m else 1
    else:
        out_path, round_no = next_form(folder)
    blocks = {}
    if report_path and os.path.isfile(report_path):
        with open(report_path, encoding="utf-8-sig") as fh:
            blocks = parse_report(fh.read())
    facts = load_facts(root, product)
    items = [entry(c, facts, blocks, folder, out_path, link) for c in cards]
    data = {
        "product": product, "round": round_no,
        "form": os.path.relpath(out_path, root).replace(os.sep, "/"),
        "task": os.path.relpath(task_path, root).replace(os.sep, "/"),
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": items,
    }
    with open(template, encoding="utf-8") as fh:
        page = fh.read()
    payload = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    page, count = SHEET_RE.subn(lambda m: m.group(1) + "\n" + payload + "\n" + m.group(3), page, count=1)
    if count != 1:
        raise check_set.TaskError("模板里找不到 id 为 sheet 的 JSON：%s" % template)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return out_path, data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the review form (UTA_STYLE.md 4.5).")
    parser.add_argument("--task", default="outputs/task.md", help="task sheet of this round")
    parser.add_argument("--report", default="outputs/report.md", help="this round's report (4.4), optional")
    parser.add_argument("--out", help="output page; default outputs/<product>/review_vNN.html")
    parser.add_argument("--link", action="store_true", help="link images by relative path instead of embedding")
    args = parser.parse_args(argv)
    try:
        out_path, data = build(args.task, args.report, args.out, args.link)
    except (OSError, check_set.TaskError) as exc:
        print("REVIEW FORM ERROR: %s" % exc)
        return 1
    missing = [it["slot"] for it in data["items"] if not it["images"]]
    print("REVIEW FORM %s  round %d  cards %d  with images %d" % (
        os.path.relpath(out_path, ROOT).replace(os.sep, "/"), data["round"], len(data["items"]),
        len(data["items"]) - len(missing)))
    if missing:
        print("no image: %s" % ", ".join(missing))
    print("Add this line at the end of the report: 验收表单：%s" % data["form"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
