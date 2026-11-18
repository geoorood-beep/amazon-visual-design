#!/usr/bin/env python3
"""Validate references/INDEX.csv and list new cases waiting in references/inbox/.

Usage:
    python tools/check_index.py            validate every row (UTA_STYLE.md 2.5)
    python tools/check_index.py --inbox    list images waiting in references/inbox/ (UTA_STYLE.md 3.6)
    python tools/check_index.py --digest   rewrite references/CASES.md, the card writer's case digest

Standard library only.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLUMNS = ["path", "type", "key", "note", "learn", "story", "structure", "light",
           "style_id", "fits", "avoid", "grade"]
TYPES = {"product", "anchor", "scene", "expression", "layout"}
LEARN = {"story", "emotion", "expression", "light", "composition", "layout", "scene", "material"}
STRUCTURE = {"simultaneous", "side_by_side", "converge", "before_after", "unnoticed",
             "macro_proof", "scale", "none"}
LIGHT = {"side", "side_back", "back", "low_sun", "night_lamp"}
FITS = {"容量", "材质", "安静", "多宠", "清洁", "可视", "开场", "参数"}
GRADES = {"A", "B", "C"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
CASE_DIR = "docs/uta_style_v3/assets/key"
NAME_RE = re.compile(r"^[A-Za-z0-9_]+\.(png|jpg|jpeg|webp)$")
TECH_COLUMNS = ["id", "dimension", "brand", "name", "how", "transfer", "fits", "avoid"]
TECH_DIMENSIONS = {"story", "selling", "scene", "headline", "interaction", "emotion", "expression"}
TECH_ID_RE = re.compile(r"^T\d{2,3}$")


def split(val):
    return [v.strip() for v in (val or "").split(";") if v.strip()]


def load_styles(root):
    path = os.path.join(root, "pools", "styles.csv")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["id"].strip() for r in csv.DictReader(fh)}


def validate(root=ROOT, index_path=None):
    """Return a list of error strings for the index."""
    index_path = index_path or os.path.join(root, "references", "INDEX.csv")
    errors = []
    with open(index_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            return ["表头必须是：" + ",".join(COLUMNS)]
        rows = list(reader)
    styles = load_styles(root)
    seen = set()
    for n, r in enumerate(rows, 2):
        where = "第 %d 行 %s" % (n, r["path"])
        if r["path"] in seen:
            errors.append(where + "：路径重复")
        seen.add(r["path"])
        if r["path"].startswith("references/inbox/"):
            errors.append(where + "：inbox 里的图要先按 3.6 入库，不能直接登记")
        if not os.path.isfile(os.path.join(root, r["path"])):
            errors.append(where + "：文件不存在")
        if r["type"] not in TYPES:
            errors.append(where + "：type 不认识：%s" % r["type"])
        if r["type"] == "product":
            continue
        bad = [v for v in split(r["learn"]) if v not in LEARN]
        if bad:
            errors.append(where + "：learn 不认识：%s" % ",".join(bad))
        bad = [v for v in split(r["structure"]) if v not in STRUCTURE]
        if bad:
            errors.append(where + "：structure 不认识：%s" % ",".join(bad))
        if r["light"] and r["light"] not in LIGHT:
            errors.append(where + "：light 不认识：%s" % r["light"])
        if r["style_id"] and r["style_id"] not in styles:
            errors.append(where + "：style_id 不在风格池里：%s" % r["style_id"])
        bad = [v for v in split(r["fits"]) if v not in FITS]
        if bad:
            errors.append(where + "：fits 不认识：%s" % ",".join(bad))
        if r["grade"] not in GRADES:
            errors.append(where + "：grade 要写 A、B 或 C")
        if "story" in split(r["learn"]) and not r["story"].strip():
            errors.append(where + "：learn 写了 story，story 却是空的")
        if r["grade"] in ("A", "B") and not split(r["learn"]):
            errors.append(where + "：A、B 级要写 learn")
        if not r["avoid"].strip() and r["grade"] != "A":
            errors.append(where + "：avoid 不能空（A 级如果真的没有不能学的，也写「无」）")
    return errors


FIT_ORDER = ["开场", "多宠", "容量", "材质", "安静", "清洁", "可视", "参数"]


def validate_techniques(root=ROOT, path=None):
    """references/techniques.csv: brand techniques Grok may borrow from (UTA_STYLE.md 1.14)."""
    path = path or os.path.join(root, "references", "techniques.csv")
    errors = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != TECH_COLUMNS:
            return ["techniques.csv 表头要是：" + ",".join(TECH_COLUMNS)]
        seen = set()
        for n, row in enumerate(reader, 2):
            tid = (row["id"] or "").strip()
            where = "techniques.csv 第 %d 行 %s" % (n, tid)
            if not TECH_ID_RE.match(tid):
                errors.append(where + "：id 要写成 T 加两到三位数字")
            if tid in seen:
                errors.append(where + "：id 重复")
            seen.add(tid)
            if row["dimension"] not in TECH_DIMENSIONS:
                errors.append(where + "：dimension 要写 " + " / ".join(sorted(TECH_DIMENSIONS)))
            for col in ("brand", "name", "how", "transfer", "avoid"):
                if not (row[col] or "").strip():
                    errors.append(where + "：%s 不能空" % col)
    return errors


def digest_text(root=ROOT):
    """The card writer's digest: A and B cases grouped by their first selling-point type."""
    with open(os.path.join(root, "references", "INDEX.csv"), encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["type"] != "product"]
    keep = [r for r in rows if r["grade"] in ("A", "B")]
    na = sum(1 for r in keep if r["grade"] == "A")
    nb = len(keep) - na
    nc = sum(1 for r in rows if r["grade"] == "C")
    lines = ["案例摘要：A 级 %d 张、B 级 %d 张（C 级 %d 张只留档，不列出）。" % (na, nb, nc), "",
             "由 `tools/check_index.py --digest` 从 `references/INDEX.csv` 生成，不要手改。路径和索引完全一致，写卡时照抄路径。",
             "每行：路径｜等级｜能学什么｜画面结构｜光型｜风格｜故事｜不能学。", ""]
    groups = {}
    for r in keep:
        fits = split(r["fits"])
        key = fits[0] if fits else "其他"
        groups.setdefault(key, []).append(r)
    order = [f for f in FIT_ORDER if f in groups] + sorted(k for k in groups if k not in FIT_ORDER)
    for key in order:
        lines.append("## %s" % key)
        lines.append("")
        for r in sorted(groups[key], key=lambda r: (r["grade"], r["path"])):
            lines.append("- `%s`｜%s｜%s｜%s｜%s｜%s｜%s｜%s" % (
                r["path"], r["grade"], r["learn"] or "-", r["structure"] or "-", r["light"] or "-",
                r["style_id"] or "-", r["story"] or "无故事", r["avoid"] or "-"))
        lines.append("")
    return "\n".join(lines)


def write_digest(root=ROOT):
    path = os.path.join(root, "references", "CASES.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(digest_text(root))
    return path


def inbox(root=ROOT, out=sys.stdout):
    folder = os.path.join(root, "references", "inbox")
    files = sorted(f for f in os.listdir(folder)
                   if os.path.splitext(f)[1].lower() in IMAGE_EXT) if os.path.isdir(folder) else []
    if not files:
        print("references/inbox/ 里没有待入库的图。", file=out)
        return 0
    existing = set(os.listdir(os.path.join(root, CASE_DIR)))
    print("待入库 %d 张（UTA_STYLE.md 3.6）：" % len(files), file=out)
    for f in files:
        base, ext = os.path.splitext(f)
        clean = re.sub(r"[^A-Za-z0-9_]+", "_", base).strip("_") or "case"
        name = "NEW_%s%s" % (clean, ext.lower())
        k = 2
        while name in existing:
            name = "NEW_%s_%d%s" % (clean, k, ext.lower())
            k += 1
        existing.add(name)
        print("  references/inbox/%s -> %s/%s  （前缀 NEW_ 换成来源，例如 XHS_、AMZ_）" % (f, CASE_DIR, name), file=out)
    print("\n索引模板（每张一行，照实填后加到 references/INDEX.csv 末尾）：", file=out)
    print(",".join(COLUMNS), file=out)
    print('"%s/<文件名>","<type>","<类别/类别>","<可学/不可学>","<learn>","<story>","<structure>","<light>","<style_id>","<fits>","<avoid>","<grade>"' % CASE_DIR, file=out)
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inbox", action="store_true", help="list images waiting in references/inbox/")
    ap.add_argument("--digest", action="store_true", help="rewrite references/CASES.md from the index")
    args = ap.parse_args(argv)
    if args.inbox:
        return inbox()
    if args.digest:
        print("WROTE " + os.path.relpath(write_digest(), ROOT))
        return 0
    errors = validate() + validate_techniques()
    cases = os.path.join(ROOT, "references", "CASES.md")
    current = open(cases, encoding="utf-8").read() if os.path.exists(cases) else ""
    if current != digest_text():
        errors.append("references/CASES.md 和索引不一致：运行 python tools/check_index.py --digest")
    for e in errors:
        print("FAIL " + e)
    if errors:
        print("索引有 %d 处错误。" % len(errors))
        return 1
    print("OK  references/INDEX.csv, references/techniques.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
