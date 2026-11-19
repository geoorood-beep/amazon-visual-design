"""Optional product form (产品资料表): category templates -> AI draft -> self-contained page.

The form is never a gate. A product goes on through the normal flow whether or not
the user opens it; the form only lets the user correct the AI's draft so less work is redone.
How the category library works: references/categories/README.md.

    python tools/product_form.py detect   --product <id> [--text "用户需求原话"]
    python tools/product_form.py skeleton --product <id> --category <id>[,<id>] [--variant <id>,...] [--text "..."]
    python tools/product_form.py build    --sheet outputs/<id>/product_form_draft.json
    python tools/product_form.py check

detect   ranks the categories by keywords in the product card, the request text and photo
         names, and prints each candidate's visual cues so the AI can confirm against the photos.
skeleton writes outputs/<id>/product_form_draft.json from the category template(s), the product
         card facts, ref_views.csv and the photos. Every part starts as 推定; the AI then edits the
         draft against the photos (see "ai_todo" inside the draft) before building.
build    renders grok/product_template.html with the draft into outputs/<id>/product_form_vNN.html
         (small JPEG previews embedded, never overwrites) and keeps the JSON beside it.
check    validates references/categories/*.json.
"""
import argparse
import base64
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE_REL = os.path.join("grok", "product_template.html")
CATEGORY_REL = os.path.join("references", "categories")
TYPES = ["组成部件", "可拆件", "耗材", "随附配件", "宿主产品", "外部物品"]
FORMS = ("立体", "扁平")
LENGTH_UNITS = ("mm", "cm", "m", "in", "ft")
UNITS = LENGTH_UNITS + ("L", "ml", "g", "kg")
PHOTO_EXT = (".png", ".jpg", ".jpeg", ".webp")
OPEN = '<script id="sheet" type="application/json">\n'
INLINE_RE = re.compile(r'<link[^>]*data-inline="([^"]+)"[^>]*>|<script[^>]*data-inline="([^"]+)"[^>]*></script>')
CLOSE = "\n</script>"
SHOWN_QUESTIONS = 3
PREVIEW_EDGE = 480
PREVIEW_QUALITY = 70

# (slot, label, ref_views match, filename token sets). Standard views come first in every form.
STANDARD_SLOTS = {
    "立体": [
        ("front", "正面平视", {"view": "front", "not_camera": "top_down"}, [["front"]]),
        ("side_left", "左侧平视", {"view": "side_left"}, [["side", "left"]]),
        ("side_right", "右侧平视", {"view": "side_right"}, [["side", "right"]]),
        ("top_down", "正俯拍", {"camera": "top_down"}, [["top"]]),
        ("three_quarter_left", "左前 45°", {"view": "three_quarter_left"}, [["three", "quarter", "left"], ["three", "quarter"]]),
        ("three_quarter_right", "右前 45°", {"view": "three_quarter_right"}, [["three", "quarter", "right"]]),
        ("rear", "背面平视", {"view": "rear"}, [["rear"], ["back"]]),
        ("low_angle", "低机位（宠物视角）", {"camera": "low_angle"}, [["low"]]),
    ],
    "扁平": [
        ("top", "正俯拍上面", {"camera": "top_down"}, [["top"]]),
        ("bottom", "翻过来拍下面", {}, [["bottom"]]),
        ("long_edge", "贴着台面拍长边", {}, [["long", "edge"], ["long"]]),
        ("short_edge", "贴着台面拍短边", {}, [["short", "edge"], ["short"]]),
        ("three_quarter", "斜上方 45°", {"view": "three_quarter_left"}, [["three", "quarter"]]),
    ],
}
SPEC_SLOTS = [
    ("spec_ruler_top", "规格照：正俯拍＋尺子", "素色底，尺子放在旁边"),
    ("spec_side_flat", "规格照：贴着台面拍侧面", "镜头贴着桌面，看厚度和边缘"),
    ("spec_hand", "规格照：手放在旁边", "定大小用"),
]
NOT_WHOLE_PRODUCT = ("accessory", "part", "detail", "pump", "connection", "panel", "exploded")
SIZE_WHY = ("量了：比例写进提示词，验收能量长宽比，宠物和产品的大小关系能统一。"
            "不量：照参考图的比例画，总览标「比例推定」，照样往下做。")
FACT_ROW = re.compile(r"^\|\s*(F\d+)\s*\|([^|]*)\|([^|]*)\|")


class FormError(Exception):
    pass


# ---------- reading ----------

def category_dir(root):
    return os.path.join(root, CATEGORY_REL)


def load_category(root, cid):
    path = os.path.join(category_dir(root), cid + ".json")
    if not os.path.isfile(path):
        known = ", ".join(sorted(list_categories(root)))
        raise FormError("no category '%s' (known: %s)" % (cid, known))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def list_categories(root):
    folder = category_dir(root)
    if not os.path.isdir(folder):
        return []
    return [n[:-5] for n in sorted(os.listdir(folder)) if n.endswith(".json")]


def read_text(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def product_dir(root, product):
    return os.path.join(root, "products", product)


def card_summary(text):
    """The one-line description under the title of a product card."""
    for line in text.splitlines()[1:]:
        line = line.strip()
        if line and not line.startswith(("#", "|", "-", "来源", ">")):
            return line
    return ""


def card_facts(text):
    """[(id, fact + 画面可写)] -- 不可写成 is left out on purpose (it names what the product is not)."""
    facts = []
    for line in text.splitlines():
        m = FACT_ROW.match(line)
        if m:
            facts.append((m.group(1), (m.group(2) + " " + m.group(3)).strip()))
    return facts


def read_ref_views(root, product):
    path = os.path.join(product_dir(root, product), "ref_views.csv")
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not row.get("path"):
                continue
            rows.append({
                "path": row["path"].strip(),
                "view": (row.get("product_view") or "").strip(),
                "cameras": [c.strip() for c in (row.get("cameras") or "").split(";") if c.strip()],
                "parts": [p.strip() for p in (row.get("parts") or "").split(";") if p.strip()],
                "checked": (row.get("checked") or "").strip().lower() == "yes",
            })
    return rows


def photo_files(root, product):
    folder = os.path.join(product_dir(root, product), "photos")
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join("products", product, "photos", n).replace(os.sep, "/")
                  for n in os.listdir(folder) if n.lower().endswith(PHOTO_EXT))


def tokens(name):
    stem = os.path.splitext(os.path.basename(name))[0].lower()
    return set(t for t in re.split(r"[^a-z0-9]+", stem) if t)


# ---------- detect ----------

def detect(root, product=None, text=""):
    """[(score, category, hits)] best first. generic is never scored; it is the fallback."""
    sources = []
    if product:
        card = read_text(os.path.join(product_dir(root, product), "PRODUCT.md"))
        title = card.splitlines()[0] if card else ""
        sources.append((3, title + " " + card_summary(card)))
        sources.append((1, " ".join(f for _, f in card_facts(card))))
        sources.append((1, " ".join(os.path.basename(p) for p in photo_files(root, product))))
    if text:
        sources.append((3, text))
    ranked = []
    for cid in list_categories(root):
        if cid == "generic":
            continue
        cat = load_category(root, cid)
        score, hits = 0, []
        for alias in cat.get("aliases", []):
            for weight, src in sources:
                if keyword_in(alias, src):
                    score += weight
                    if alias not in hits:
                        hits.append(alias)
        ranked.append((score, cat, hits))
    ranked.sort(key=lambda r: -r[0])
    return ranked


def cmd_detect(args, root, out):
    ranked = detect(root, args.product, args.text or "")
    best = [r for r in ranked if r[0] > 0]
    if not best:
        out.write("CATEGORY generic  (no keyword matched; look at the photos: if it is one of the categories below, use it)\n")
    for score, cat, hits in best[:3]:
        out.write("CATEGORY %s  %s  score %d  hits: %s\n" % (cat["id"], cat["name"], score, ", ".join(hits)))
    if len(best) > 1 and best[1][0] >= max(2, 0.6 * best[0][0]):
        out.write("COMBO? %s + %s both match: a product that is both (e.g. feeder plus fountain) takes --category %s,%s\n"
                  % (best[0][1]["id"], best[1][1]["id"], best[0][1]["id"], best[1][1]["id"]))
    shown = best[:2] if best else [(0, c, []) for _, c, _ in ranked]
    for _, cat, _ in shown:
        out.write("\nLOOK at the photos for %s:\n" % cat["id"])
        for cue in cat.get("cues", []):
            out.write("  - %s\n" % cue)
        if cat.get("variants"):
            out.write("VARIANTS (pass the ones the photos show with --variant):\n")
            for v in cat["variants"]:
                out.write("  %s  %s — %s\n" % (v["id"], v["name"], v.get("cue", "")))
    pick = best[0][1]["id"] if best else "generic"
    out.write("\nNEXT: python tools/product_form.py skeleton --product %s --category %s [--variant ...]\n"
              % (args.product or "<id>", pick))
    return 0


# ---------- skeleton ----------

def pick_ref(rows, rule):
    if not rule:
        return None
    for want_checked in (True, False):
        for r in rows:
            if r["checked"] != want_checked or "whole" not in r["parts"]:
                continue
            if any(t in r["path"].lower() for t in NOT_WHOLE_PRODUCT):
                continue
            if "view" in rule and r["view"] != rule["view"]:
                continue
            if "camera" in rule and rule["camera"] not in r["cameras"]:
                continue
            if "not_camera" in rule and rule["not_camera"] in r["cameras"] and len(r["cameras"]) == 1:
                continue
            return r
    return None


def pick_photo(files, token_sets, used):
    for wanted in token_sets:
        for path in files:
            if path in used:
                continue
            tk = tokens(path)
            if any(t in tk for t in NOT_WHOLE_PRODUCT):
                continue
            if all(w in tk for w in wanted):
                return path
    return None


def build_photos(root, product, cats):
    form = form_of(cats)
    rows = read_ref_views(root, product) if product else []
    files = photo_files(root, product) if product else []
    used, slots = set(), []
    for slot, label, rule, token_sets in STANDARD_SLOTS[form]:
        entry = {"slot": slot, "label": label, "img": "", "tip": ""}
        photo = pick_photo(files, token_sets, used)
        ref = pick_ref(rows, rule)
        if photo:
            entry.update(img=photo, src="实拍")
            used.add(photo)
        elif ref:
            entry.update(img=ref["path"], src="已登记参考" + ("" if ref["checked"] else "（没核对）"))
            if "baseline_" in os.path.basename(ref["path"]):
                entry["src"] = "造型基准图"
        if not entry["img"]:
            entry["tip"] = "没有这个角度的照片：补拍一张，斜角和低机位最容易画变形"
        slots.append(entry)
    for slot, label, tip in SPEC_SLOTS:
        slots.append({"slot": slot, "label": label, "img": "", "tip": tip})
    seen = set(s["slot"] for s in slots)
    for cat in cats:
        for p in cat.get("photo_slots", []):
            if p["slot"] not in seen:
                seen.add(p["slot"])
                slots.append({"slot": p["slot"], "label": p["label"], "img": "", "tip": p.get("tip", "")})
    return slots


def form_of(cats, variants=()):
    form = cats[0].get("form", "立体")
    for cat in cats:
        for v in cat.get("variants", []):
            if v["id"] in variants and v.get("form") in FORMS:
                form = v["form"]
    return form if form in FORMS else "立体"


def part_images(rows, part, is_root):
    want = [t for t in part.get("refs", [part["key"]]) if is_root or t != "whole"]
    hits = [r for r in rows if any(t in r["parts"] for t in want)]
    hits.sort(key=lambda r: (not r["checked"], len(r["parts"])))
    return [r["path"] for r in hits[:2]]


def build_parts(cats, variants, rows):
    parts, n = [], 0
    for cat in cats:
        keep = [p for p in cat.get("parts", []) if not p.get("variant") or p["variant"] in variants]
        ids = {}
        for p in keep:
            n += 1
            ids[p["key"]] = "P%d" % n
        for p in keep:
            is_root = not p.get("parent") or p["parent"] not in ids
            imgs = part_images(rows, p, is_root and p["type"] != "外部物品")
            basis = "品类常识：%s（还没对照照片）" % cat["name"]
            if imgs:
                basis += "；参考图里可能拍到了，见右边"
            parts.append({
                "id": ids[p["key"]], "key": p["key"], "category": cat["id"],
                "parent": ids.get(p.get("parent", ""), ""), "conf": "推定", "type": p["type"],
                "name": p["name"], "en": p.get("en", ""), "where": p.get("where", ""),
                "detach": p.get("detach", ""), "visible": p.get("visible", ""),
                "pitfall": p.get("pitfall", ""), "basis": basis, "imgs": imgs,
            })
    return parts


def keyword_in(keyword, text):
    """Chinese keywords match anywhere; English ones only as whole words, so 'L' or 'lid' never hit 'wireless'."""
    k = keyword.strip().lower()
    if len(k) < 2:
        return False
    if re.fullmatch(r"[a-z0-9 .\-]+", k):
        return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", text.lower()) is not None
    return k in text.lower()


def build_states(cats, facts):
    states, seen = [], set()
    for cat in cats:
        for s in cat.get("states", []):
            if s["id"] in seen:
                continue
            seen.add(s["id"])
            kws = s.get("keywords", [])
            hit = [fid for fid, text in facts if any(keyword_in(k, text) for k in kws)]
            states.append({
                "id": s["id"], "conf": "推定", "name": s["name"],
                "for": " ".join(hit) if hit else "关键词：" + "、".join(s.get("keywords", [])[:6]),
                "show": s.get("show", ""), "hide": s.get("hide", ""), "never": s.get("never", ""),
            })
    return states


def build_functions(cats, facts):
    """One row per confirmed fact: the state it most likely needs and what the picture must show (all 推定)."""
    states = [s for c in cats for s in c.get("states", [])]
    rows = []
    for fid, text in facts:
        hit = [s for s in states if any(keyword_in(k, text) for k in s.get("keywords", []))]
        pick = next((s for s in hit if s["id"] != "assembled"), hit[0] if hit else None)
        rows.append({
            "fact": fid, "text": text[:60], "how": "", "proof": pick.get("show", "") if pick else "",
            "state": pick["name"] if pick else "", "angle": "", "effect": "", "conf": "推定",
        })
    return rows


def build_questions(cats, variants=()):
    """A question whose `decides` variants were already picked (from the photos or the request) is not asked."""
    qs = []
    for cat in cats:
        for q in cat.get("questions", []):
            if set(q.get("decides", [])) & set(variants):
                continue
            qs.append(q)
    out = []
    for i, q in enumerate(qs, 1):
        out.append({
            "id": "Q%d" % i, "key": q["key"], "text": q["text"], "why": q.get("why", ""),
            "options": q["options"], "rec": q.get("rec", -1),
            "write": [j for j, o in enumerate(q["options"]) if "写一句" in o], "imgs": [],
        })
    return out[:SHOWN_QUESTIONS], out[SHOWN_QUESTIONS:]


def build_updates(card):
    ups = []
    if not card:
        return ups
    if "## 产品理解" not in card:
        ups.append({"id": "C%d" % (len(ups) + 1), "text": "产品卡还没有「产品理解」和「产品状态」两节（规范 1.15）",
                    "fix": "用这张表的部件表和状态表补上这两节，以后每张卡的状态、证据都从这里出发。"})
    m = re.search(r"## Parts \(prompt\)\s*\n(.*?)(\n## |\Z)", card, re.S)
    if m is not None and not re.search(r"^\s*-\s+\S", m.group(1), re.M):
        ups.append({"id": "C%d" % (len(ups) + 1), "text": "产品卡的 Parts (prompt) 是空的",
                    "fix": "确认后按部件表里「随附配件」「可拆件」写，每件一行英文。"})
    return ups


AI_TODO = [
    "打开 photos/ 和 ref/ 的图，逐个部件对照：看得见的改成「确定」，依据写哪张图；照片里没有、这款也不会有的删掉；照片里有、模板没有的加一行。",
    "部件的「在哪、能拆吗、看得见吗」按这款产品改写，不照抄模板；关系类型不对就改 type。",
    "问题只留最影响画面的 3 个：能从照片或产品卡判断的删掉，可以从 questions_more 换上来。",
    "summary 写一句：这是什么、给谁用、在哪里用；flow 写怎么用（3–6 步）；functions 每条补「怎么做到」「推荐拍法」，证据改成这款产品的。",
    "老产品：把产品卡里和这张表冲突的地方写进 updates。",
    "改完运行 python tools/product_form.py build --sheet <这个文件>。",
]


def skeleton(root, product, category_ids, variants=(), text=""):
    cats = [load_category(root, c) for c in category_ids]
    known = set(v["id"] for c in cats for v in c.get("variants", []))
    bad = [v for v in variants if v not in known]
    if bad:
        raise FormError("unknown variant(s) %s for %s (known: %s)" % (
            ", ".join(bad), ",".join(category_ids), ", ".join(sorted(known)) or "none"))
    card = read_text(os.path.join(product_dir(root, product), "PRODUCT.md"))
    facts = card_facts(card)
    rows = read_ref_views(root, product)
    shown, more = build_questions(cats, variants)
    variant_names = [v["name"] for c in cats for v in c.get("variants", []) if v["id"] in variants]
    size = json.loads(json.dumps(cats[0].get("size", {})))
    size.setdefault("why", SIZE_WHY)
    pitfalls, forbidden = [], []
    for c in cats:
        pitfalls += c.get("pitfalls", [])
        forbidden += c.get("forbidden", [])
    names = "、".join(c["name"] for c in cats)
    return {
        "product": product,
        "title": "%s · 产品资料（选填）" % product,
        "form": "",
        "generated": datetime.date.today().isoformat(),
        "by": "AI 草稿：品类模板「%s」，还没对照照片" % names,
        "categories": [{"id": c["id"], "name": c["name"], "version": c.get("version", 1)} for c in cats],
        "variants": list(variants),
        "variant_names": variant_names,
        "request": text,
        "base": "",
        "types": TYPES,
        "summary": card_summary(card) or text,
        "questions": shown,
        "questions_more": more,
        "parts": build_parts(cats, set(variants), rows),
        "states": build_states(cats, facts),
        "functions": build_functions(cats, facts),
        "flow": [],
        "internal": [],
        "updates": build_updates(card),
        "size": size,
        "photos": build_photos_form(root, product, cats, variants),
        "pitfalls": pitfalls,
        "forbidden": forbidden,
        "ai_todo": AI_TODO,
    }


def build_photos_form(root, product, cats, variants):
    form = form_of(cats, variants)
    if form == form_of(cats):
        return build_photos(root, product, cats)
    swapped = [dict(c, form=form) for c in cats]
    return build_photos(root, product, swapped)


def cmd_skeleton(args, root, out):
    cats = [c.strip() for c in args.category.split(",") if c.strip()]
    variants = [v.strip() for v in (args.variant or "").split(",") if v.strip()]
    sheet = skeleton(root, args.product, cats, variants, args.text or "")
    path = args.out or os.path.join(root, "outputs", args.product, "product_form_draft.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sheet, fh, ensure_ascii=False, indent=1)
    filled = sum(1 for p in sheet["photos"] if p["img"])
    out.write("DRAFT %s  parts %d  states %d  questions %d (+%d more)  photos %d/%d  updates %d\n" % (
        shown_path(path, root), len(sheet["parts"]), len(sheet["states"]),
        len(sheet["questions"]), len(sheet["questions_more"]), filled, len(sheet["photos"]), len(sheet["updates"])))
    out.write("TODO before build (also inside the draft as ai_todo):\n")
    for i, t in enumerate(AI_TODO, 1):
        out.write("  %d. %s\n" % (i, t))
    return 0


# ---------- build ----------

def preview_uri(path):
    """Small JPEG preview as a data URI; the original bytes when sips is not available."""
    if shutil.which("sips"):
        tmp = tempfile.mkdtemp(prefix="uta_form_")
        try:
            dst = os.path.join(tmp, "p.jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(PREVIEW_QUALITY),
                            "-Z", str(PREVIEW_EDGE), path, "--out", dst],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(dst, "rb") as fh:
                return "data:image/jpeg;base64," + base64.b64encode(fh.read()).decode("ascii")
        except (OSError, subprocess.CalledProcessError):
            pass
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode("ascii"))


def inline_assets(root, html):
    """The template loads its style and script from the repo; a built form carries them inside, so it opens anywhere."""
    def sub(m):
        rel = m.group(1) or m.group(2)
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise FormError("template asset missing: %s" % rel)
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        if m.group(1):
            return "<style>\n%s\n</style>" % body
        return "<script>\n%s\n</script>" % body.replace("</script", "<\\/script")
    return INLINE_RE.sub(sub, html)


def next_form_path(root, product):
    folder = os.path.join(root, "outputs", product)
    n = 1
    while os.path.exists(os.path.join(folder, "product_form_v%02d.html" % n)):
        n += 1
    return os.path.join(folder, "product_form_v%02d.html" % n)


def embed(root, sheet):
    cache, missing = {}, []

    def conv(p):
        if not p or p.startswith(("data:", "http:", "https:")):
            return p
        if p not in cache:
            full = os.path.join(root, p)
            if os.path.isfile(full):
                cache[p] = preview_uri(full)
            else:
                missing.append(p)
                cache[p] = ""
        return cache[p]

    for q in sheet.get("questions", []):
        q["imgs"] = [x for x in (conv(i) for i in q.get("imgs", [])) if x]
    for p in sheet.get("parts", []):
        p["imgs"] = [x for x in (conv(i) for i in p.get("imgs", [])) if x]
    for ph in sheet.get("photos", []):
        ph["img"] = conv(ph.get("img", ""))
    return len([v for v in cache.values() if v]), missing


def build(root, sheet_path, out_path=None):
    with open(sheet_path, encoding="utf-8") as fh:
        sheet = json.load(fh)
    product = sheet.get("product")
    if not product:
        raise FormError("the sheet has no 'product'")
    with open(os.path.join(root, TEMPLATE_REL), encoding="utf-8") as fh:
        html = inline_assets(root, fh.read())
    if OPEN not in html:
        raise FormError("template has no sheet block")
    out_path = out_path or next_form_path(root, product)
    if os.path.exists(out_path):
        raise FormError("%s exists; forms are never overwritten" % out_path)
    sheet["form"] = shown_path(out_path, root)
    sheet["base"] = ""
    raw = json.loads(json.dumps(sheet))
    count, missing = embed(root, sheet)
    start = html.index(OPEN) + len(OPEN)
    end = html.index(CLOSE, start)
    body = json.dumps(sheet, ensure_ascii=False, indent=1).replace("</", "<\\/")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html[:start] + body + html[end:])
    with open(os.path.splitext(out_path)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=1)
    return out_path, count, missing


def shown_path(path, root):
    full, base = os.path.abspath(path), os.path.abspath(root)
    if full.startswith(base + os.sep):
        return os.path.relpath(full, base).replace(os.sep, "/")
    return full


def cmd_build(args, root, out):
    path, count, missing = build(root, args.sheet, args.out)
    out.write("FORM %s  images %d  size %.0f KB\n" % (shown_path(path, root), count, os.path.getsize(path) / 1024.0))
    for m in missing:
        out.write("! missing image: %s\n" % m)
    out.write("Open it in a browser; the user may fill it or skip it. Nothing waits on it.\n")
    return 0


# ---------- check ----------

def validate_category(cat, cid):
    e = []
    where = "%s.json" % cid

    def err(msg):
        e.append("%s: %s" % (where, msg))

    for key in ("id", "name", "version", "form", "aliases", "cues", "variants", "parts", "states",
                "questions", "photo_slots", "size", "pitfalls", "forbidden"):
        if key not in cat:
            err("missing '%s'" % key)
    if e:
        return e
    if cat["id"] != cid:
        err("id '%s' does not match the file name" % cat["id"])
    if cat["form"] not in FORMS:
        err("form must be 立体 or 扁平")
    if cid != "generic" and not cat["aliases"]:
        err("aliases are empty: detect could never pick this category")
    vids = [v.get("id") for v in cat["variants"]]
    if len(set(vids)) != len(vids):
        err("duplicate variant ids")
    keys = [p.get("key") for p in cat["parts"]]
    if len(set(keys)) != len(keys):
        err("duplicate part keys")
    for v in cat["variants"]:
        for a in v.get("adds", []):
            if a not in keys:
                err("variant %s adds unknown part '%s'" % (v.get("id"), a))
        if "form" in v and v["form"] not in FORMS:
            err("variant %s form must be 立体 or 扁平" % v.get("id"))
    for p in cat["parts"]:
        label = "part %s" % p.get("key")
        for key in ("key", "name", "type", "where", "visible"):
            if not p.get(key):
                err("%s has no %s" % (label, key))
        if p.get("type") not in TYPES:
            err("%s type '%s' is not one of %s" % (label, p.get("type"), "/".join(TYPES)))
        if p.get("parent") and p["parent"] not in keys:
            err("%s parent '%s' is not a part key" % (label, p["parent"]))
        if p.get("parent") == p.get("key"):
            err("%s is its own parent" % label)
        if p.get("variant") and p["variant"] not in vids:
            err("%s variant '%s' is not a variant id" % (label, p["variant"]))
    sids = [s.get("id") for s in cat["states"]]
    if len(set(sids)) != len(sids):
        err("duplicate state ids")
    if "assembled" not in sids:
        err("no 'assembled' state")
    for s in cat["states"]:
        if not s.get("keywords"):
            err("state %s has no keywords" % s.get("id"))
        if not s.get("show"):
            err("state %s has no 'show'" % s.get("id"))
    qkeys = [q.get("key") for q in cat["questions"]]
    if len(set(qkeys)) != len(qkeys):
        err("duplicate question keys")
    for q in cat["questions"]:
        opts = q.get("options") or []
        if len(opts) < 2:
            err("question %s needs at least 2 options" % q.get("key"))
        for v in q.get("decides", []):
            if v not in vids:
                err("question %s decides unknown variant '%s'" % (q.get("key"), v))
        rec = q.get("rec", -1)
        if not isinstance(rec, int) or rec < -1 or rec >= len(opts):
            err("question %s rec out of range" % q.get("key"))
    slots = [p.get("slot") for p in cat["photo_slots"]]
    if len(set(slots)) != len(slots):
        err("duplicate photo slots")
    size = cat["size"]
    dims = size.get("dims", {})
    for k in ("L", "W", "H"):
        d = dims.get(k)
        if not d:
            err("size.dims.%s missing" % k)
            continue
        for key in ("short", "label", "en", "noun", "unit"):
            if not d.get(key):
                err("size.dims.%s has no %s" % (k, key))
        if d.get("unit") and d["unit"] not in LENGTH_UNITS:
            err("size.dims.%s unit must be a length unit (%s)" % (k, "/".join(LENGTH_UNITS)))
    for pair in size.get("ratios", []):
        if len(pair) != 2 or any(x not in ("L", "W", "H") for x in pair) or pair[0] == pair[1]:
            err("size.ratios entry %s is not a pair of L/W/H" % (pair,))
    for x in size.get("extra", []):
        if not x.get("key") or not x.get("label"):
            err("size.extra entry without key or label")
        if x.get("unit") not in UNITS:
            err("size.extra %s unit must be one of %s" % (x.get("key"), "/".join(UNITS)))
        if "{v}" not in x.get("en", ""):
            err("size.extra %s en needs a {v} placeholder" % x.get("key"))
    return e


def validate(root=ROOT):
    errors = []
    cids = list_categories(root)
    if "generic" not in cids:
        errors.append("references/categories/generic.json is missing (the fallback category)")
    for cid in cids:
        try:
            cat = load_category(root, cid)
        except ValueError as exc:
            errors.append("%s.json: not valid JSON (%s)" % (cid, exc))
            continue
        errors += validate_category(cat, cid)
    return errors


def cmd_check(args, root, out):
    errors = validate(root)
    for line in errors:
        out.write("CATEGORY ERROR %s\n" % line)
    if not errors:
        out.write("CATEGORIES OK  %s\n" % ", ".join(list_categories(root)))
    return 1 if errors else 0


def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Optional product form from category templates.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("detect")
    p.add_argument("--product")
    p.add_argument("--text", help="the user's request, as written")
    p = sub.add_parser("skeleton")
    p.add_argument("--product", required=True)
    p.add_argument("--category", required=True, help="one id, or two joined by a comma for a combined product")
    p.add_argument("--variant", help="variant ids the photos show, comma separated")
    p.add_argument("--text")
    p.add_argument("--out")
    p = sub.add_parser("build")
    p.add_argument("--sheet", required=True)
    p.add_argument("--out")
    sub.add_parser("check")
    args = parser.parse_args(argv)
    try:
        return {"detect": cmd_detect, "skeleton": cmd_skeleton, "build": cmd_build, "check": cmd_check}[args.cmd](args, root, out)
    except FormError as exc:
        out.write("FORM ERROR %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
