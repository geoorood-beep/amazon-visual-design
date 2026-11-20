#!/usr/bin/env python3
"""Validate slot cards and print the generation package for them.

Usage:
    python tools/check_card.py --task outputs/task.md     a task sheet from the card writer
    python tools/check_card.py cards/round10l/S5_clean.md one card: attach list, prompt, typesetting
    python tools/check_card.py --set cards/round10l       every card in a folder
    python tools/check_card.py --baseline <product>       shape baseline renders for a new product (UTA_STYLE 1.12)

A card that fails validation must not be used to generate an image.
Rules are documented in UTA_STYLE.md section 2. Standard library only.

Three kinds of card:
    image card   M1, S1-S9, a P slot with module: scene, or a panel such as P6a
    module card  a P slot with module: grid, steps or specs; it lists its panels
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import icons as icon_lib  # noqa: E402

CAMERAS = {
    "low_angle": "low angle close to the floor or counter, camera looking slightly up",
    "eye_level": "eye-level view",
    "down_45": "about 45 degrees looking down",
    "top_down": "straight top-down view",
    "close_up": "close-up, product detail fills most of the frame",
    "wide": "wide view showing the whole room and the whole product",
}
MODULES = ("scene", "grid", "steps", "specs", "number", "contrast", "overview", "bento", "split", "cards3", "fit", "trust")
PREMIUM_MODULES = {"number", "contrast", "overview", "bento", "split", "cards3", "fit", "trust"}
ONE_FACT_MODULES = {"steps", "number", "contrast", "split", "fit"}
LABELLED_MODULES = {"grid", "steps", "contrast", "overview", "bento", "cards3", "fit"}
DISTINCT_FACT_MODULES = {"grid", "overview", "bento", "cards3"}
LINE_MODULES = {"specs": (2, 4), "trust": (2, 4), "split": (0, 3)}
SEAM_MODULES = {"scene", "number"}
PANEL_COUNT = {"grid": (2, 4), "steps": (2, 4), "specs": (1, 1), "number": (1, 1), "contrast": (2, 2),
               "overview": (4, 8), "bento": (4, 4), "split": (1, 1), "cards3": (3, 3), "fit": (2, 4), "trust": (1, 1)}
EDITIONS = ("standard", "premium")
TONES = ("light", "dark")
FORMAT_TEXT = {
    "M": "square 1:1",
    "S": "vertical 4:5 portrait",
    "P": (
        "horizontal 3:2. Keep the product, the pet and the action inside the middle 60% "
        "of the height. The top 20% and the bottom 20% are plain background such as "
        "wall, floor or counter, because they will be cropped away"
    ),
    "panel": (
        "square 1:1. Keep the product, the pet and the action inside the central 60% "
        "of the frame. The outer area is plain background, because the image will be "
        "cropped to different shapes. Keep the lower-left corner calm and low in detail"
    ),
    "panel_wide": (
        "horizontal 3:2. Keep the product, the pet and the action inside the middle 60% "
        "of the height. The top 20% and the bottom 20% are plain background, because "
        "they will be cropped away. Keep the lower-left corner calm and low in detail"
    ),
}
TEXT_AREAS = {
    "top", "top_left", "top_right", "bottom", "bottom_left", "bottom_right",
    "left", "right",
}
REF_SLOTS = {
    "product": {"product"},
    "anchor": {"anchor", "scene"},
    "expression": {"expression"},
    "layout": {"layout"},
}
REF_LEARN = {
    "anchor": {"light", "composition", "scene", "story", "material"},
    "expression": {"expression", "emotion"},
    "layout": {"layout"},
}
REF_LABEL = {
    "product": "product reference",
    "anchor": "style reference",
    "expression": "pet expression reference",
    "layout": "layout reference",
}
IMAGE_KEYS = [
    "card_version", "product", "slot", "canvas", "selling_point", "evidence",
    "human_action", "pet", "pet_action", "camera", "scene", "light",
    "text_area", "headline", "subtitle", "hero_number", "refs",
]
MODULE_KEYS = [
    "card_version", "product", "slot", "canvas", "module", "selling_point",
    "headline", "subtitle", "hero_number", "panels", "lines", "refs",
]
OPTIONAL_KEYS = ["module", "label", "panels", "lines", "edition", "tone", "eyebrow", "fix", "seam", "product_source",
                 "render_ref"]
ALL_KEYS = set(IMAGE_KEYS) | set(MODULE_KEYS) | set(OPTIONAL_KEYS)
ENGLISH_FIELDS = [
    "evidence", "human_action", "pet", "pet_action", "scene", "light",
    "headline", "subtitle", "hero_number", "label", "lines", "eyebrow", "fix",
]
MAX_HEADLINE_WORDS = 6
MAX_SUBTITLE_WORDS = 10
MAX_LABEL_WORDS = 4
MAX_EYEBROW_WORDS = 4
MAX_FIX_WORDS = 25  # review rework note (UTA_STYLE 2.4, 4.5)
SLOT = re.compile(r"(M1|S[1-9]|P[1-8])([a-d]?)")
CJK = re.compile(r"[　-〿㐀-鿿＀-￯]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
DIRECTION = re.compile(r"\b(left|right|behind|back|rear|front|side|above|overhead)\b", re.I)


def read(path):
    return path.read_text(encoding="utf-8-sig")


def is_none(value):
    return value is None or value.strip().lower() in ("", "none")


def parse_card(path):
    """Return (fields, refs, errors). refs maps slot -> (path, purpose) or None."""
    errors = []
    lines = read(path).splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, {}, ["first line must be '---'"]
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, {}, ["closing '---' line not found"]

    fields, refs, in_refs = {}, {}, False
    for number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            errors.append(f"line {number}: expected 'key: value'")
            continue
        key, value = raw.split(":", 1)
        indented = raw[:1] in (" ", "\t")
        key, value = key.strip(), value.strip()
        if indented:
            if not in_refs:
                errors.append(f"line {number}: indented line outside 'refs:'")
                continue
            if key not in REF_SLOTS:
                errors.append(f"line {number}: unknown ref slot '{key}'")
                continue
            if key in refs:
                errors.append(f"line {number}: ref slot '{key}' appears twice")
                continue
            if is_none(value):
                refs[key] = None
            elif "|" not in value:
                errors.append(
                    f"line {number}: ref '{key}' must be 'path | what to take from it'"
                )
            else:
                ref_path, purpose = (part.strip() for part in value.split("|", 1))
                refs[key] = (ref_path, purpose)
            continue
        in_refs = key == "refs"
        if key not in ALL_KEYS:
            errors.append(f"line {number}: unknown field '{key}'")
            continue
        if key in fields:
            errors.append(f"line {number}: field '{key}' appears twice")
            continue
        fields[key] = value
    return fields, refs, errors


def md_section_bullets(text, heading):
    """Bullets under '## heading' up to the next '## '."""
    bullets, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside and line.strip().startswith("- "):
            bullets.append(line.strip()[2:].strip())
    return bullets


def md_facts(text):
    """Rows like '| F1 | fact | allowed copy | not allowed |'."""
    facts = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*(F\d+)\s*\|", line)
        if match:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 3:
                facts[match.group(1)] = {"fact": cells[1], "allowed": cells[2]}
    return facts


def load_index():
    index = {}
    with (ROOT / "references" / "INDEX.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            index[row["path"].strip()] = row
    return index


def load_prompt_blocks():
    blocks, name = {}, None
    for line in read(ROOT / "tools" / "prompt_base.txt").splitlines():
        if line.startswith("#"):
            continue
        match = re.match(r"^\[([A-Z_]+)\]\s*$", line)
        if match:
            name = match.group(1)
            blocks[name] = []
        elif name and line.strip():
            blocks[name].append(line.strip())
    return {key: " ".join(value) for key, value in blocks.items()}


def find_forbidden(text, words):
    hits = []
    for word in words:
        pattern = r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])"
        if re.search(pattern, text, re.I):
            hits.append(word)
    return hits


def normalise_numbers(text):
    return {n.replace(",", ".") for n in NUMBER.findall(text)}


def load_product(product, errors):
    """Return (facts, identity bullets, forbidden words, geometry bullets) for a product id."""
    product_md = ROOT / "products" / product / "PRODUCT.md"
    if not re.fullmatch(r"[a-z0-9_]+", product) or not product_md.is_file():
        errors.append(f"product '{product}' has no products/{product}/PRODUCT.md")
        return {}, [], [], []
    text = read(product_md)
    identity = md_section_bullets(text, "Identity (prompt)")
    if not identity:
        errors.append(f"products/{product}/PRODUCT.md has no 'Identity (prompt)' bullets")
    geometry = md_section_bullets(text, "Geometry (prompt)")
    return md_facts(text), identity, md_section_bullets(text, "禁用词"), geometry


BASELINE_VIEWS = [
    ("front", "straight-on front view at eye level, the whole product centred"),
    ("back", "straight-on back view at eye level, the whole product centred"),
    ("side", "straight-on side view at the height of the product, showing its thickness and edge profile"),
    ("top_down", "camera directly above looking straight down, the full outline and any curve visible"),
    ("three_quarter", "front three-quarter view from about 45 degrees to the side and slightly above"),
]
FLAT_BASELINE_VIEWS = [
    ("top", "camera directly above looking straight down at the upper face, the full outline and any curve visible"),
    ("bottom", "the product turned over, camera directly above looking straight down at the underside, the full outline visible"),
    ("long_edge", "camera level with the surface, looking straight at the long edge, showing thickness and edge profile along the whole length"),
    ("short_edge", "camera level with the surface at one end, looking straight at the short edge, showing the thickness and the cross-section of the end"),
    ("three_quarter", "from about 45 degrees above one corner, the upper face and the thickness visible together"),
]
BASELINE_FORMS = {"立体": BASELINE_VIEWS, "扁平": FLAT_BASELINE_VIEWS}
PHOTO_EXT = {".png", ".jpg", ".jpeg", ".webp"}
# Which baseline views a real photo already shows, judged from its file name (UTA_STYLE 1.12 fast baseline).
PHOTO_VIEW_HINTS = {
    "front": ("front", "正面", "正视"), "back": ("back", "rear", "背面", "背视"), "side": ("side", "侧面", "侧视", "left", "right"),
    "top_down": ("top", "俯视", "俯拍"), "top": ("top", "俯视", "俯拍"), "bottom": ("bottom", "底面"),
    # Names written from Grok's view-positioning table (UTA_STYLE 1.12), e.g. 05_three_quarter.png.
    "three_quarter": ("three_quarter", "45deg", "45度", "斜角"),
    "long_edge": ("long_edge", "长边"), "short_edge": ("short_edge", "短边"),
}
ALL_VIEW_HINTS = ("five_view", "five-view", "五视", "multi_view", "三视", "turnaround")
MIN_BASELINE = {"立体": ["front", "three_quarter", "side"], "扁平": ["top", "three_quarter", "long_edge"]}
BASELINE_MINUTES = 15


def baseline_field(product, key):
    """Value of 'key：...' under '## 造型基准'; '' if the section lacks it, None if no section."""
    product_md = ROOT / "products" / product / "PRODUCT.md"
    if not product_md.is_file():
        return None
    inside, found = False, False
    for line in read(product_md).splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == "造型基准"
            found = found or inside
            continue
        if inside:
            match = re.match(r"^\s*" + re.escape(key) + r"\s*[:：]\s*(.+?)\s*$", line)
            if match:
                return match.group(1)
    return "" if found else None


def baseline_status(product):
    """Status text under '## 造型基准', '' if the section has no status line, None if no section."""
    return baseline_field(product, "状态")


def check_baseline_gate(product, errors, warnings):
    status = baseline_status(product)
    if status is None:
        warnings.append(
            f"products/{product}/PRODUCT.md has no '造型基准' section: "
            "the product shape was never confirmed on its own (UTA_STYLE 1.12)"
        )
    elif not status.startswith("已确认"):
        errors.append(
            f"products/{product}: 造型基准 is '{status or '未填'}', not 已确认. "
            "Make and confirm the shape baseline before any scene image (UTA_STYLE 1.12, 3.5)"
        )


def print_baseline(product, photos_dir=None):
    """Print the attach list and one prompt per baseline view. Return an exit code."""
    errors = []
    _facts, identity, _forbidden, geometry = load_product(product, errors)
    if errors:
        print(f"FAIL  {product}")
        for error in errors:
            print(f"  - {error}")
        return 1
    product_dir = ROOT / "products" / product
    parts = md_section_bullets(read(product_dir / "PRODUCT.md"), "Parts (prompt)")
    photos_dir = Path(photos_dir) if photos_dir else product_dir / "photos"
    photos = sorted(p for p in photos_dir.glob("*") if p.suffix.lower() in PHOTO_EXT) if photos_dir.is_dir() else []
    if not photos:
        print(f"FAIL  {product}")
        print(f"  - no real photos in products/{product}/photos/ (png, jpg, webp). Ask the user for them.")
        return 1
    done = [int(d.name[1:]) for d in (product_dir / "baseline").glob("v[0-9][0-9]") if d.is_dir()]
    version = f"v{(max(done) + 1) if done else 1:02d}"
    out_dir = f"products/{product}/baseline/{version}"
    blocks = load_prompt_blocks()

    form = baseline_field(product, "形态") or "立体"
    if form not in BASELINE_FORMS:
        print(f"FAIL  {product}")
        print(f"  - 造型基准 形态 must be one of: {', '.join(BASELINE_FORMS)} (got '{form}')")
        return 1
    views = list(BASELINE_FORMS[form])
    details = [b for b in identity if not b.lower().startswith("no ")]
    views += [(f"detail_{i}", f"extreme close-up of this feature only: {b}; the rest of the product may be cut off by the frame")
              for i, b in enumerate(details, start=1)]
    views += [(f"part_{i}", f"this part alone, separate from the main product, three-quarter view from slightly above: {b}")
              for i, b in enumerate(parts, start=1)]

    print(f"BASELINE {product} {version}  形态 {form}  (UTA_STYLE 1.12, 3.5)\n")
    print("ATTACH (real photos, in this order, for every view):")
    for i, photo in enumerate(photos, start=1):
        try:
            shown = photo.relative_to(ROOT).as_posix()
        except ValueError:
            shown = photo.as_posix()
        print(f"  {i}. {shown}")
    if not geometry:
        print("\n! no 'Geometry (prompt)' in the product card: proportions come from the photos only. Mark the sheet 比例推定.")
    if not parts:
        print("! no 'Parts (prompt)' in the product card: no part_<n> views. Accessories without real photos are 缺实拍.")
    product_line = "PRODUCT: " + "; ".join(identity) + "."
    if geometry:
        product_line += " SIZE AND PARTS: " + "; ".join(geometry) + "."
    main_views = list(BASELINE_FORMS[form])
    covered = {}
    for photo in photos:
        low = photo.name.lower()
        for name, _view in main_views:
            hints = PHOTO_VIEW_HINTS.get(name, ())
            sheet = name != "three_quarter" and any(h in low for h in ALL_VIEW_HINTS)  # five-view sheets are straight-on only
            if any(h in low for h in hints) or sheet:
                covered.setdefault(name, photo.name)
    missing = [(n, v) for n, v in main_views if n not in covered]
    print(f"\n== FAST (default, UTA_STYLE 1.12): finish within {BASELINE_MINUTES} minutes ==")
    print("1. Views the real photos already show: cut the product out onto plain mid-grey, do not regenerate:")
    for name, _view in main_views:
        if name in covered:
            print(f"   {name}: {covered[name]}")
    if not covered:
        print("   (none recognised from file names; check the photos yourself)")
    if missing:
        print("2. Generate every remaining view in ONE image, a turnaround sheet, attaching all real photos:")
        cells = "; ".join(f"cell {i}: {v}" for i, (_n, v) in enumerate(missing, start=1))
        print("   PROMPT: " + " ".join([
            blocks["BASELINE"],
            f"One clean product turnaround sheet on a plain mid-grey background: the very same product shown "
            f"{len(missing)} times in a neat grid, identical in every cell except the viewing angle; {cells}.",
            product_line, blocks["BASELINE_RULES"]]))
        print(f"   SAVE: {out_dir}/sheet_generated.png, then crop each cell to {out_dir}/<view>.png")
    if details:
        print("3. Detail close-ups: crop them from the real photos; generate a detail only if no photo shows it.")
    print("4. Minimum to confirm and start scene work: " + ", ".join(MIN_BASELINE[form]) +
          ". A view that fails twice is skipped and marked 缺; it never holds up the rest.")
    print("\n== SLOW (only for a view the fast route could not give) ==")
    for name, view in views:
        print(f"\n=== {name} ===")
        print(f"SAVE: {out_dir}/{name}.png")
        print("PROMPT:")
        print(" ".join([blocks["BASELINE"], f"VIEW: {view}.", product_line, blocks["BASELINE_RULES"]]))
    print(f"\nTHEN: one contact sheet {out_dir}/sheet.png, each cell labelled with the view name and "
          "有实拍 / 无实拍，推定 / 缺实拍. Report one line per cell and ask the user to answer 对 or 不对 for each.")
    return 0


def check_copy(copy, allowed_texts, product, product_forbidden, errors, what="copy", fact_id=None):
    """Forbidden words and numbers. allowed_texts: the 'allowed copy' of the facts in play."""
    from copy_exceptions import duration_hits, invented_feature_hits, load_claims, load_grants

    global_forbidden = md_section_bullets(read(ROOT / "UTA_STYLE.md"), "禁用词")
    for word in find_forbidden(copy, global_forbidden):
        errors.append(f"{what} contains a word forbidden by UTA_STYLE.md: '{word}'")
    held = load_grants(ROOT, product).get(fact_id or "", set())
    for word in duration_hits(copy, held):
        errors.append(f"{what} contains a duration that is not allowed for this fact: '{word}'")
    for word in invented_feature_hits(copy, load_claims(ROOT, product)):
        errors.append(f"{what} states a feature the product card does not confirm: '{word}'")
    for word in find_forbidden(copy, product_forbidden):
        errors.append(f"{what} contains a word forbidden for {product}: '{word}'")
    allowed = set()
    for text in allowed_texts:
        allowed |= normalise_numbers(text)
    for number in sorted(normalise_numbers(copy) - allowed):
        if allowed_texts:
            errors.append(
                f"number '{number}' in the {what} is not in the allowed copy of the selling point "
                f"({' / '.join(allowed_texts)})"
            )
        else:
            errors.append(f"number '{number}' in the {what} has no selling point to check it against")


def check_words(fields, key, limit, errors):
    if not is_none(fields.get(key)) and len(fields[key].split()) > limit:
        errors.append(f"{key} has more than {limit} words")


def check_refs(refs, allowed_slots, product, index, errors):
    """Validate reference lines. Return the attach list [(slot, path, purpose)]."""
    attach = []
    for slot_name in ("product", "anchor", "expression", "layout"):
        ref = refs.get(slot_name)
        if ref is None:
            continue
        if slot_name not in allowed_slots:
            errors.append(f"ref {slot_name} must be none for this card")
            continue
        ref_path, purpose = ref
        clean = ref_path.replace("\\", "/")
        if clean != ref_path or clean.startswith(("/", "http")) or ".." in clean.split("/"):
            errors.append(f"ref {slot_name}: path must be repo-relative with forward slashes")
            continue
        if not purpose:
            errors.append(f"ref {slot_name}: say what to take from it after '|'")
        elif CJK.search(purpose):
            errors.append(f"ref {slot_name}: the purpose after '|' must be in English")
        row = index.get(clean)
        if row is None:
            errors.append(f"ref {slot_name}: '{clean}' is not listed in references/INDEX.csv")
            continue
        if not (ROOT / clean).is_file():
            errors.append(f"ref {slot_name}: file '{clean}' does not exist")
            continue
        learn = {v.strip() for v in (row.get("learn") or "").split(";") if v.strip()}
        if slot_name != "product" and (row.get("grade") or "").strip() == "C":
            errors.append(f"ref {slot_name}: '{clean}' is grade C in the index (archive only, UTA_STYLE 2.5)")
            continue
        if row["type"] not in REF_SLOTS[slot_name] and not (learn & REF_LEARN.get(slot_name, set())):
            needed = " or ".join(sorted(REF_SLOTS[slot_name]))
            errors.append(
                f"ref {slot_name}: '{clean}' is type '{row['type']}' in the index, needs {needed}"
            )
            continue
        if slot_name == "product" and not row["key"].startswith(product + "/"):
            errors.append(f"ref product: '{clean}' belongs to '{row['key']}', not to {product}")
            continue
        attach.append((slot_name, clean, purpose))
    return attach


def validate(path, index):
    """Return (errors, warnings, context). context is None when the card is unusable."""
    fields, refs, errors = parse_card(path)
    warnings = []
    if errors and not fields:
        return errors, warnings, None

    match = SLOT.fullmatch(fields.get("slot", ""))
    if not match:
        errors.append("slot must be M1, S1-S9, P1-P8, or a panel such as P6a")
        return errors, warnings, None
    kind, is_panel = fields["slot"][0], bool(match.group(2))
    if is_panel and kind != "P":
        errors.append("only P slots have panels")
        return errors, warnings, None

    module = fields.get("module", "none").strip().lower()
    if kind == "P" and not is_panel:
        if module not in MODULES:
            errors.append("a P slot needs 'module:' set to one of: " + ", ".join(MODULES))
            return errors, warnings, None
    elif not is_none(module):
        errors.append("'module' is only for P1-P8 cards (panels and M/S cards leave it out)")

    edition = (fields.get("edition") or "standard").strip().lower()
    tone = (fields.get("tone") or "light").strip().lower()
    if kind == "P" and not is_panel:
        if edition not in EDITIONS:
            errors.append("edition must be standard or premium")
        if tone not in TONES:
            errors.append("tone must be light or dark")
        if edition == "standard" and tone == "dark":
            errors.append("tone: dark is only for the premium edition")
        if edition == "standard" and module in PREMIUM_MODULES:
            errors.append(f"module: {module} is only for the premium edition")
    elif not is_none(fields.get("edition")) or not is_none(fields.get("tone")):
        errors.append("'edition' and 'tone' are only for P1-P8 cards, not for panels, M1 or S cards")
    look = {"edition": edition, "tone": tone, "icons": {}}
    source = (fields.get("product_source") or "generate").strip()
    if source not in ("render_ref", "generate"):
        errors.append("product_source must be render_ref or generate (UTA_STYLE.md 1.18)")
    render_ref = (fields.get("render_ref") or "").split("|")[0].strip()
    if source == "render_ref" and not render_ref:
        errors.append("product_source: render_ref needs a render_ref line (written by check_set.py)")
    look["product_source"] = source
    look["render_ref"] = render_ref if source == "render_ref" else ""
    for key, value in list(fields.items()):
        if "{icon:" not in (value or ""):
            continue
        if key not in ("hero_number", "label", "lines"):
            errors.append(f"{key}: an icon only goes before hero_number, a panel label or a spec line (UTA_STYLE.md 1.5)")
        elif key != "lines":
            icon, rest, problem = icon_lib.split_icon(value)
            if problem:
                errors.append(f"{key}: {problem}")
            else:
                look["icons"][key] = icon
            fields[key] = rest
    seam = (fields.get("seam") or "none").strip().lower()
    if not is_none(seam):
        if kind != "P" or is_panel:
            errors.append("'seam' is only for P1-P8 screen cards")
        elif seam != "next":
            errors.append("seam must be 'next' (this screen joins the next one), or left out")
        elif edition != "premium":
            errors.append("seam: only the premium edition joins two screens")
        elif module not in SEAM_MODULES:
            errors.append("seam: only a scene or number screen joins the screen below it")
    look["seam"] = seam if seam == "next" else ""
    if not is_none(fields.get("eyebrow")):
        if kind != "P" or is_panel:
            errors.append("'eyebrow' is only for P1-P8 screen cards, not for panels, M1 or S cards")
        elif edition != "premium":
            errors.append("eyebrow: only the premium edition has an eyebrow line")
        check_words(fields, "eyebrow", MAX_EYEBROW_WORDS, errors)

    if kind == "P" and not is_panel and module != "scene":
        return validate_module(path, fields, refs, errors, warnings, module, look, index)
    return validate_image(path, fields, refs, errors, warnings, kind, is_panel, look, index)


def validate_image(path, fields, refs, errors, warnings, kind, is_panel, look, index):
    slot = fields["slot"]
    for key in IMAGE_KEYS:
        if key not in fields:
            errors.append(f"missing field '{key}'")
    for key in REF_SLOTS:
        if key not in refs and not any(f"'{key}'" in e for e in errors):
            errors.append(f"missing ref slot '{key}' (write 'none' if not used)")
    for key in ("panels", "lines"):
        if not is_none(fields.get(key)):
            errors.append(f"'{key}' is only for module cards")
    if errors:
        return errors, warnings, None

    if fields["card_version"] != "1":
        errors.append("card_version must be 1")
    if is_panel:
        if fields["canvas"] not in ("1:1", "3:2"):
            errors.append("canvas for a panel must be 1:1, or 3:2 for the lead panel of a premium module")
    else:
        canvas = {"M": "1:1", "S": "4:5", "P": "2.44:1"}[kind]
        if fields["canvas"] != canvas:
            errors.append(f"canvas for {slot} must be {canvas}")

    product = fields["product"]
    facts, identity, product_forbidden, geometry = load_product(product, errors)
    if not any("PRODUCT.md" in e for e in errors):
        check_baseline_gate(product, errors, warnings)
    if fields["product"] and not geometry and not any("PRODUCT.md" in e for e in errors):
        warnings.append(
            f"products/{product}/PRODUCT.md has no 'Geometry (prompt)' bullets: "
            "size, outline and parts are not locked (UTA_STYLE 1.11)"
        )

    selling_point, fact = fields["selling_point"], None
    if is_none(selling_point):
        if kind != "M":
            errors.append("selling_point is required (a fact id such as F5) except for M1")
    elif selling_point not in facts:
        errors.append(
            f"selling_point '{selling_point}' is not a fact id in products/{product}/PRODUCT.md"
        )
    else:
        fact = facts[selling_point]
    for key, icon in look.get("icons", {}).items():
        text = (fact["fact"] + " " + fact["allowed"]) if fact else ""
        problem = icon_lib.icon_problem(ROOT, icon, text, key)
        if problem:
            errors.append(f"{key}: {problem}")

    if fields["camera"] not in CAMERAS:
        errors.append("camera must be one of: " + ", ".join(CAMERAS))

    label = fields.get("label", "none")
    if not is_panel and not is_none(label):
        errors.append("'label' is only for panel cards such as P6a")
    if kind == "M" or is_panel:
        who = "M1 is product only on white" if kind == "M" else "a panel carries no text of its own"
        text_keys = ("headline", "subtitle", "hero_number")
        if kind == "M":
            text_keys += ("pet", "pet_action", "human_action")
        for key in text_keys:
            if not is_none(fields[key]):
                errors.append(f"{who}: '{key}' must be none")
        if fields["text_area"].lower() != "none":
            errors.append(f"{who}: text_area must be none")
    if kind != "M":
        required = ("evidence", "scene", "light")
        if not is_panel:
            required += ("headline", "subtitle")
        for key in required:
            if is_none(fields[key]):
                errors.append(f"'{key}' is required for {slot}")
        if not is_panel:
            areas = {"left", "right"} if kind == "P" else TEXT_AREAS
            if fields["text_area"] not in areas:
                errors.append("text_area must be one of: " + ", ".join(sorted(areas)))
        if is_none(fields["pet"]) != is_none(fields["pet_action"]):
            errors.append("pet and pet_action must both be filled or both be none")
        if not is_panel and is_none(fields["pet"]) and is_none(fields["human_action"]):
            warnings.append("no pet and no hands: check that the image can still show the selling point")
        if not is_none(fields["light"]) and not DIRECTION.search(fields["light"]):
            warnings.append("light does not say where the light comes from (left, right, behind ...)")

    for key in ENGLISH_FIELDS:
        if CJK.search(fields.get(key, "")):
            errors.append(f"'{key}' must be written in English (it goes into the image prompt)")

    check_words(fields, "headline", MAX_HEADLINE_WORDS, errors)
    check_words(fields, "subtitle", MAX_SUBTITLE_WORDS, errors)
    check_words(fields, "label", MAX_LABEL_WORDS, errors)
    check_words(fields, "fix", MAX_FIX_WORDS, errors)
    if not is_none(fields.get("fix")):
        hits = find_forbidden(fields["fix"], product_forbidden)
        if hits:
            errors.append(f"fix contains a word forbidden by the product card: '{hits[0]}'")
    if not is_none(fields["hero_number"]) and not NUMBER.search(fields["hero_number"]):
        errors.append("hero_number must contain a number, or be none")
    copy = " ".join(
        fields[k] for k in ("eyebrow", "headline", "subtitle", "hero_number", "label") if not is_none(fields.get(k))
    )
    selling = fields.get("selling_point", "")
    bound = selling if re.fullmatch(r"F\d+", selling or "") else None
    check_copy(copy, [fact["allowed"]] if fact else [], product, product_forbidden, errors, fact_id=bound)

    allowed_slots = {"product"}
    if kind != "M":
        allowed_slots |= {"anchor", "expression"}
    if kind == "P" and not is_panel:
        allowed_slots.add("layout")
    attach = check_refs(refs, allowed_slots, product, index, errors)
    if refs.get("product") is None:
        errors.append("ref product is required")
    if refs.get("expression") is not None and is_none(fields["pet"]):
        errors.append("ref expression is set but the card has no pet")

    if errors:
        return errors, warnings, None
    context = {
        "type": "image", "fields": fields, "kind": kind, "panel": is_panel,
        "identity": identity, "geometry": geometry, "attach": attach, "path": path, **look,
    }
    return errors, warnings, context


def panel_canvas(module, edition, count, position):
    """The frame each panel image must be generated in."""
    if module in ("number", "split"):
        return "3:2"
    if module == "grid" and edition == "premium" and count == 3 and position == 0:
        return "3:2"
    if module == "bento" and position < 2:
        return "3:2"
    return "1:1"


def validate_module(path, fields, refs, errors, warnings, module, look, index):
    slot = fields["slot"]
    for key in MODULE_KEYS:
        if key not in fields:
            errors.append(f"missing field '{key}'")
    for key in IMAGE_KEYS:
        if key not in MODULE_KEYS and not is_none(fields.get(key)):
            errors.append(f"'{key}' belongs on the panel cards, not on a {module} module card")
    if not is_none(fields.get("label")):
        errors.append("'label' belongs on the panel cards")
    if not is_none(fields.get("fix")):
        errors.append("'fix' is only for cards that become one picture; a module is rebuilt from its panels")
    if errors:
        return errors, warnings, None

    if fields["card_version"] != "1":
        errors.append("card_version must be 1")
    if fields["canvas"] != "2.44:1":
        errors.append(f"canvas for {slot} must be 2.44:1")
    product = fields["product"]
    facts, _identity, product_forbidden, _geometry = load_product(product, errors)

    for key in ("headline", "subtitle"):
        if is_none(fields[key]):
            errors.append(f"'{key}' is required for {slot}")
    check_words(fields, "headline", MAX_HEADLINE_WORDS, errors)
    check_words(fields, "subtitle", MAX_SUBTITLE_WORDS, errors)
    if not is_none(fields["hero_number"]) and not NUMBER.search(fields["hero_number"]):
        errors.append("hero_number must contain a number, or be none")
    for key in ENGLISH_FIELDS:
        if CJK.search(fields.get(key, "")):
            errors.append(f"'{key}' must be written in English")

    # Panels: listed in order, each with its own valid card next to this one.
    edition = look["edition"]
    low, high = PANEL_COUNT[module]
    if module == "grid" and edition == "premium":
        high = 3
    names = [name.strip() for name in fields["panels"].split(",") if name.strip()]
    expected = [slot + letter for letter in "abcdefgh"[: len(names)]]
    if not low <= len(names) <= high:
        count = str(low) if low == high else f"{low} to {high}"
        errors.append(f"a {module} module needs {count} panel(s), got {len(names)}")
    elif names != expected:
        errors.append(f"panels must be listed as {', '.join(expected)}")
    panels = []
    for position, name in enumerate(names if names == expected else []):
        found = sorted(path.parent.glob(f"{name}_*.md")) + sorted(path.parent.glob(f"{name}.md"))
        if len(found) != 1:
            errors.append(f"panel {name}: expected exactly one card named {name}_<name>.md, found {len(found)}")
            continue
        panel_errors, panel_warnings, panel_context = validate(found[0], index)
        errors += [f"panel {name}: {error}" for error in panel_errors]
        warnings += [f"panel {name}: {warning}" for warning in panel_warnings]
        if panel_context is None:
            continue
        panel_fields = panel_context["fields"]
        if panel_fields["product"] != product:
            errors.append(f"panel {name}: product differs from the module's product")
        if module in LABELLED_MODULES and is_none(panel_fields.get("label")):
            errors.append(f"panel {name}: 'label' is required in a {module} module")
        if module not in LABELLED_MODULES and not is_none(panel_fields.get("label")):
            errors.append(f"panel {name}: 'label' must be none in a {module} module")
        needed = panel_canvas(module, edition, len(names), position)
        if panel_fields["canvas"] != needed:
            why = " (the lead panel of this premium module is wide)" if needed == "3:2" else ""
            errors.append(f"panel {name}: canvas must be {needed}{why}")
        panels.append(panel_context)

    # Selling points
    panel_facts = [p["fields"]["selling_point"] for p in panels]
    used_facts = set(panel_facts)
    module_fact = fields["selling_point"]
    if module in ONE_FACT_MODULES:
        if is_none(module_fact) or module_fact not in facts:
            errors.append(f"a {module} module needs selling_point set to one fact id")
        elif any(f != module_fact for f in panel_facts):
            errors.append(f"every panel of a {module} module must use {module_fact}")
        used_facts.add(module_fact)
        if module == "number" and is_none(fields["hero_number"]):
            errors.append("a number module needs hero_number")
    else:
        if not is_none(module_fact):
            errors.append(f"selling_point must be none on a {module} module card")
        if module in DISTINCT_FACT_MODULES and len(set(panel_facts)) != len(panel_facts):
            errors.append(f"each panel of a {module} module must show a different fact")

    # Spec lines: 'F1 | 10 L ; F2 | 304 Stainless Steel'
    lines, line_icons = [], []
    if module in LINE_MODULES:
        parts = [part.strip() for part in fields["lines"].split(";") if part.strip()] if not is_none(fields["lines"]) else []
        low, high = LINE_MODULES[module]
        if not low <= len(parts) <= high:
            errors.append(f"a {module} module needs {low} to {high} lines, written 'F1 | text ; F2 | text'")
        for part in parts:
            if "|" not in part:
                errors.append(f"line '{part}' must be 'fact id | text'")
                continue
            fact_id, text = (piece.strip() for piece in part.split("|", 1))
            if fact_id not in facts:
                errors.append(f"line '{part}': '{fact_id}' is not a fact id")
                continue
            icon, text, problem = icon_lib.split_icon(text)
            if problem:
                errors.append(f"line '{part}': {problem}")
            elif icon:
                problem = icon_lib.icon_problem(ROOT, icon, facts[fact_id]["fact"] + " " + facts[fact_id]["allowed"],
                                                "lines", module)
                if problem:
                    errors.append(f"line '{part}': {problem}")
            line_icons.append(icon)
            if len(text.split()) > MAX_LABEL_WORDS:
                errors.append(f"line '{text}' has more than {MAX_LABEL_WORDS} words")
            check_copy(
                text, [facts[fact_id]["allowed"]], product, product_forbidden, errors,
                what=f"line '{text}'", fact_id=fact_id,
            )
            used_facts.add(fact_id)
            lines.append((fact_id, text))
        if module == "split":
            if any(fact_id != module_fact for fact_id, _text in lines):
                errors.append(f"every line of a split module must use its fact {module_fact}")
        elif len({fact_id for fact_id, _text in lines}) != len(lines):
            errors.append(f"each line of a {module} module must use a different fact")
    elif not is_none(fields["lines"]):
        errors.append("'lines' is only for a specs, trust or split module")

    copy = " ".join(fields[k] for k in ("eyebrow", "headline", "subtitle", "hero_number") if not is_none(fields.get(k)))
    allowed_texts = [facts[f]["allowed"] for f in sorted(used_facts) if f in facts]
    if look.get("icons", {}).get("hero_number"):
        text = " ".join(facts[f]["fact"] + " " + facts[f]["allowed"] for f in sorted(used_facts) if f in facts)
        problem = icon_lib.icon_problem(ROOT, look["icons"]["hero_number"], text, "hero_number", module)
        if problem:
            errors.append(f"hero_number: {problem}")
    check_copy(copy, allowed_texts, product, product_forbidden, errors)

    attach = check_refs(refs, {"layout"}, product, index, errors)

    if errors:
        return errors, warnings, None
    context = {
        "type": "module", "fields": fields, "kind": "P", "panel": False, "module": module,
        "panels": panels, "lines": lines, "line_icons": line_icons, "attach": attach, "path": path, **look,
    }
    return errors, warnings, context


def build_prompt(context, blocks):
    fields, kind, is_panel = context["fields"], context["kind"], context["panel"]
    if is_panel:
        frame = "panel_wide" if fields["canvas"] == "3:2" else "panel"
    else:
        frame = kind
    out = [f"FORMAT: {FORMAT_TEXT[frame]}."]
    if context.get("render_ref"):
        out.append(
            "SHAPE: The first attached picture is a plain 3D render of this exact product from this angle. Copy its "
            "outline, proportions and the position and size of every part exactly. Take colours, materials and finish "
            "from the product photo, not from the render; the render's grey ground is not part of the scene.")
    if kind == "M":
        out.append(
            "Studio product photograph on a pure white background (RGB 255,255,255). "
            "Product only: no props, no pets, no people, no text. Soft studio light with "
            "a clear highlight band on the brushed steel and a soft contact shadow."
        )
    else:
        out.append("STYLE: " + blocks["STYLE"])
    out.append("PRODUCT: " + "; ".join(context["identity"]) + ". " + blocks["PRODUCT_RULES"])
    if context.get("geometry"):
        out.append("SIZE AND PARTS: " + "; ".join(context["geometry"]) + ". " + blocks["GEOMETRY_RULES"])
    if kind != "M":
        out.append("SCENE: " + fields["scene"].rstrip(".") + ".")
        action = ["WHAT IS HAPPENING: " + fields["evidence"].rstrip(".") + "."]
        if not is_none(fields["human_action"]):
            action.append("Hands: " + fields["human_action"].rstrip(".") + ".")
        if not is_none(fields["pet"]):
            action.append(f"Pet ({fields['pet']}): " + fields["pet_action"].rstrip(".") + ".")
        out.append(" ".join(action))
    if kind == "M":
        out.append("CAMERA: the same front view from slightly above as the product reference, whole product in frame.")
    else:
        out.append("CAMERA: " + CAMERAS[fields["camera"]] + ".")
    if kind != "M":
        out.append("LIGHT: " + fields["light"].rstrip(".") + ". " + blocks["LIGHT"])
        if not is_none(fields["pet"]):
            out.append("PET: " + blocks["PET_RULES"])
    if kind == "M" or is_panel:
        out.append("TEXT: " + blocks["TEXT_RULES"])
    elif kind == "P":
        out.append(
            f"TEXT: {blocks['TEXT_RULES']} Clear area: the {fields['text_area']} third of the "
            "frame, inside the middle band."
        )
        if context.get("edition") == "premium":
            out[-1] += (
                " Keep the lower half of that side especially calm and low in detail, "
                "because on the phone the text sits there."
            )
    else:
        area = fields["text_area"].replace("_", " ")
        out.append(f"TEXT: {blocks['TEXT_RULES']} Clear area: {area}.")
    refs = [
        f"Attached image {i} is the {REF_LABEL[slot]}, use it for: {purpose.rstrip('.')}."
        for i, (slot, _path, purpose) in enumerate(context["attach"], start=1)
    ]
    out.append("REFERENCES: " + " ".join(refs) + " " + blocks["REFERENCE_RULES"])
    out.append("AVOID: " + blocks["AVOID"])
    if not is_none(fields.get("fix")):
        out.append("FIX: " + fields["fix"].rstrip(".") + ".")
    return "\n\n".join(out)


def output_stem(context):
    path = context["path"]
    return f"outputs/{context['fields']['product']}/{path.stem}"


SEAM_NOTE = ("seam: next -> this screen and the one below are one design (UTA_STYLE.md 1.9): "
             "carry the bottom strip of this base image down as the next screen's background, "
             "fading to its colour within its top 30%; keep 40 px on both sides of the seam free of "
             "product, faces, action and text")
MODULE_NOTES = {
    "overview": "overview: square cells in one row (4 or 6) or two rows of 4; label in each cell's lower left",
    "bento": "bento: big cell a on the left, wide cell b top right, c and d below it; titles on cell a",
    "split": "split: text on the left 44% (headline, subtitle, lines with amber dots), scene cell on the right",
    "cards3": "cards3: three tall cards; picture on top, a light data strip below with the label",
    "fit": "fit: laid out like a grid; one kind of pet, household or space per cell",
    "trust": "trust: laid out like specs; one product-and-box cell, an outline icon before each line",
}


def icon_note(icons, key):
    icon = (icons or {}).get(key)
    return f"   icon before it: {icon_lib.icon_path(icon)} (same colour, about the text height, UTA_STYLE.md 1.5)" if icon else ""


def print_copy(fields, icons=None):
    if not is_none(fields.get("eyebrow")):
        print(f"eyebrow (amber, all caps): {fields['eyebrow']}")
    print(f"headline: {fields['headline']}")
    print(f"subtitle: {fields['subtitle']}")
    if not is_none(fields["hero_number"]):
        print(f"hero number (amber): {fields['hero_number']}{icon_note(icons, 'hero_number')}")


def print_package(context, blocks):
    if context["type"] == "module":
        print_module(context)
        return
    fields, kind = context["fields"], context["kind"]
    stem = output_stem(context)
    print("== ATTACH THESE FILES TO THE IMAGE CALL, IN THIS ORDER ==")
    for i, (slot, ref_path, _purpose) in enumerate(context["attach"], start=1):
        print(f"{i}. {ref_path}   ({REF_LABEL[slot]})")
    print()
    if context.get("product_source", "generate") != "generate":
        import product_model
        print(f"== PRODUCT SOURCE: {context['product_source']} (UTA_STYLE.md 1.18, 3.10) ==")
        print(product_model.STEPS[context["product_source"]])
        if context.get("render_ref"):
            ready = (ROOT / context["render_ref"]).is_file()
            print(f"shape reference, attach it FIRST: {context['render_ref']}"
                  + ("" if ready else f"   (not rendered yet: python tools/render_refs.py run --product {fields['product']})"))
            print(f"after generation: python tools/shape_check.py run --product {fields['product']} --image <the picture> "
                  f"--render {context['render_ref']} --slot {fields['slot']}")
        print()
    print("== PROMPT (use as is) ==")
    print(build_prompt(context, blocks))
    print()
    if context["panel"]:
        print("== AFTER GENERATION ==")
        print(f"save the image without text as: {stem}_v01.png")
        if not is_none(fields.get("label")):
            print(f"label, added when {fields['slot'][:2]} is composed: {fields['label']}{icon_note(context.get('icons'), 'label')}")
        print(f"do not typeset this panel; compose it with its module card {fields['slot'][:2]}")
    elif kind == "M":
        print("== AFTER GENERATION ==")
        print(f"save as: {stem}_v01.png   (no text on M1)")
    elif kind == "P":
        print("== TYPESET AFTER GENERATION: two files from this one image (UTA_STYLE.md 1.9) ==")
        print(f"save the image without text as: {stem}_base_v01.png")
        if context["edition"] == "premium":
            print(f"desktop {stem}_desktop_1464x600_v01.png : full bleed, white text on a gradient on the {fields['text_area']}")
            print(f"mobile  {stem}_mobile_600x450_v01.png  : full bleed, text on the image at the lower {fields['text_area']}")
            if context.get("seam"):
                print(SEAM_NOTE)
        else:
            print(f"desktop {stem}_desktop_1464x600_v01.png : crop the middle band, text on the {fields['text_area']}")
            print(f"mobile  {stem}_mobile_600x450_v01.png  : text band on top, image below")
        print(f"edition: {context['edition']}   tone: {context['tone']}")
        print_copy(fields, context.get('icons'))
    else:
        print("== TYPESET AFTER GENERATION (UTA_STYLE.md 1.5) ==")
        print(f"save the image without text as: {stem}_base_v01.png")
        print(f"save the typeset image as: {stem}_v01.png")
        print(f"text area: {fields['text_area']}")
        print_copy(fields, context.get('icons'))


def print_module(context):
    fields, module = context["fields"], context["module"]
    stem = output_stem(context)
    print(f"== MODULE {fields['slot']} ({module}): no image is generated for this card ==")
    print("1. Generate the panel images first, one at a time:")
    for panel in context["panels"]:
        print(f"   python tools/check_card.py {panel['path'].relative_to(ROOT).as_posix()}")
    print("2. Compose two files from those panel images (UTA_STYLE.md 1.9):")
    print(f"   desktop {stem}_desktop_1464x600_v01.png")
    print(f"   mobile  {stem}_mobile_600x450_v01.png")
    print()
    print("== CONTENT ==")
    print(f"edition: {context['edition']}   tone: {context['tone']}")
    if module in MODULE_NOTES:
        print(MODULE_NOTES[module])
    if context.get("seam"):
        print(SEAM_NOTE)
    print_copy(fields, context.get('icons'))
    for number, panel in enumerate(context["panels"], start=1):
        panel_fields = panel["fields"]
        label = "" if is_none(panel_fields.get("label")) else f"   label: {panel_fields['label']}{icon_note(panel.get('icons'), 'label')}"
        step = f"step {number}  " if module == "steps" else ""
        if module == "contrast":
            step = "before  " if number == 1 else "after  "
        print(f"panel {panel_fields['slot']}: {step}{output_stem(panel)}_v01.png{label}")
    for (fact_id, text), icon in zip(context["lines"], context.get("line_icons") or [None] * len(context["lines"])):
        print(f"line ({fact_id}): {text}{icon_note({'l': icon}, 'l')}")
    for _slot, ref_path, purpose in context["attach"]:
        print(f"layout reference, for the arrangement only: {ref_path}   ({purpose})")


def slot_order(item):
    match = SLOT.fullmatch(item[1]["fields"]["slot"])
    return ("MSP".index(match.group(1)[0]), int(match.group(1)[1:]), match.group(2))


def set_notes(valid):
    """Whole-set reminders for a list of (card path, context). Sorts the list by slot."""
    valid.sort(key=slot_order)
    notes, seen_slots, seen_facts = [], {}, {}
    for card, context in valid:
        fields = context["fields"]
        if fields["slot"] in seen_slots:
            notes.append(f"slot {fields['slot']} appears in two cards: {seen_slots[fields['slot']]} and {card.name}")
        seen_slots[fields["slot"]] = card.name
        if context["kind"] == "S":
            fact = fields["selling_point"]
            if fact in seen_facts:
                notes.append(f"{fact} is the selling point of two S cards: {seen_facts[fact]} and {card.name}")
            seen_facts[fact] = card.name
    module_panels = {
        p["fields"]["slot"] for _card, c in valid if c["type"] == "module" for p in c["panels"]
    }
    for card, context in valid:
        if context["panel"] and context["fields"]["slot"] not in module_panels:
            notes.append(f"panel {context['fields']['slot']} ({card.name}) is not listed by any module card")
    screens = [c for _card, c in valid if c["kind"] == "P" and not c["panel"]]
    if len({c["edition"] for c in screens}) > 1:
        notes.append("the A+ screens mix the standard and the premium edition; use one edition for the whole page")
    dark = [c["fields"]["slot"] for c in screens if c["tone"] == "dark"]
    if len(dark) > 2:
        notes.append(f"more than two dark screens ({', '.join(dark)}); a page takes one or two")
    for a, b in zip(screens, screens[1:]):
        if a["tone"] == b["tone"] == "dark":
            notes.append(f"{a['fields']['slot']} and {b['fields']['slot']} are both dark; do not place dark screens next to each other")
    for kind in "SP":
        group = [c for _card, c in valid if c["kind"] == kind and c["type"] == "image" and not c["panel"]]
        cameras = [c["fields"]["camera"] for c in group]
        for a, b, ca, cb in zip(group, group[1:], cameras, cameras[1:]):
            if ca == cb:
                notes.append(f"{a['fields']['slot']} and {b['fields']['slot']} use the same camera ({ca})")
        if cameras.count("eye_level") > 1:
            notes.append(f"{kind} set has more than one eye_level card")
        if kind == "S" and len(group) >= 6:
            if not {"top_down", "down_45"} & set(cameras):
                notes.append("S set has no overhead card (top_down or down_45)")
            if cameras.count("low_angle") < 2:
                notes.append("S set has fewer than two low_angle cards")
    return notes


def check_cards(cards, index, states=None):
    """Validate a list of card paths and print one line each. Return (valid, failed)."""
    failed, valid = [], []
    for card in cards:
        errors, warnings, context = validate(card, index)
        rel = card.relative_to(ROOT).as_posix() if ROOT in card.parents else card.name
        state = f"  ({states[card]})" if states else ""
        if errors:
            failed.append(rel)
            print(f"FAIL  {rel}{state}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK    {rel}{state}")
            valid.append((card, context))
        for warning in warnings:
            print(f"  ! {warning}")
    return valid, failed


def check_set(folder, index):
    cards = sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))
    if not cards:
        print(f"no cards in {folder}")
        return 1
    valid, failed = check_cards(cards, index)
    notes = set_notes(valid)
    if notes:
        print("\nSet notes (fix these when writing cards; they do not block a single image):")
        for note in notes:
            print(f"  ! {note}")
    print(f"\n{len(valid)} of {len(cards)} cards valid")
    return 1 if failed else 0


TASK_HEADER = "UTA-TASK v1"
TASK_MARKER = re.compile(r"^=== (cards/([a-z0-9_]+)/([A-Za-z0-9][A-Za-z0-9_\-]*\.md)) ===\s*$")


def parse_task(text):
    """Split a task sheet into cards. Return (product, [(path, body)], errors)."""
    errors = []
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if not line.strip().startswith("```")]
    # A short instruction line such as "按 UTA style 执行下面这份任务单。" may come first.
    start = next((i for i, line in enumerate(lines) if line.strip() == TASK_HEADER), None)
    if start is None:
        return None, [], [f"no '{TASK_HEADER}' line found"]
    lines = lines[start:]

    header, cards, current = {}, [], None
    for line in lines[1:]:
        match = TASK_MARKER.match(line)
        if match:
            current = (match.group(1), match.group(2), [])
            cards.append(current)
        elif line.startswith("==="):
            errors.append(f"bad card marker: {line}  (expected '=== cards/<product>/<slot>_<name>.md ===')")
        elif current is not None:
            current[2].append(line)
        elif ":" in line:
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip()
        elif line.strip():
            errors.append(f"unexpected line before the first card: {line}")

    product = header.get("product")
    if not product:
        errors.append("missing 'product:' line under the header")
    declared = header.get("cards", "")
    if not declared.isdigit():
        errors.append("missing 'cards: <number>' line under the header")
    elif int(declared) != len(cards):
        errors.append(
            f"header says cards: {declared} but {len(cards)} card(s) were found "
            "(the task sheet may be cut off)"
        )
    if not cards:
        errors.append("no cards found")

    result, seen = [], set()
    for path, path_product, body in cards:
        if path in seen:
            errors.append(f"{path} appears twice")
        seen.add(path)
        if product and path_product != product:
            errors.append(f"{path} is not under cards/{product}/")
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        result.append((path, "\n".join(body) + "\n"))
    return product, result, errors


def run_task(task_file, index):
    product, cards, errors = parse_task(read(task_file))
    if not errors:
        for rel, body in cards:
            fields = dict(
                line.split(":", 1) for line in body.splitlines() if ":" in line and not line.startswith(" ")
            )
            slot = fields.get("slot", "").strip()
            name = Path(rel).name
            if slot and not (name.startswith(slot + "_") or name == slot + ".md"):
                errors.append(f"{rel}: file name must start with its slot '{slot}_'")
            if fields.get("product", "").strip() not in ("", product):
                errors.append(f"{rel}: card product differs from the task product '{product}'")
    if errors:
        print("TASK ERROR  the task sheet is not usable; nothing was written")
        for error in errors:
            print(f"  - {error}")
        print("\nDo not generate. Send these lines back to the card writer.")
        return 2

    # Write every card first: a module card is checked together with its panel cards.
    states, paths = {}, []
    for rel, body in cards:
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            states[target] = "new"
        elif read(target).replace("\r\n", "\n") == body:
            states[target] = "unchanged"
        else:
            states[target] = "updated"
        target.write_text(body, encoding="utf-8", newline="\n")
        paths.append(target)

    valid, failed = check_cards(paths, index, states)
    notes = set_notes(valid)
    if notes:
        print("\nSet notes (for the card writer; they do not block these images):")
        for note in notes:
            print(f"  ! {note}")
    print(f"\n{len(valid)} of {len(cards)} cards valid")

    modules = [(card, c) for card, c in valid if c["type"] == "module"]
    ready_panels = {p["fields"]["slot"] for _card, c in modules for p in c["panels"]}
    images = [
        (card, c) for card, c in valid
        if c["type"] == "image" and (not c["panel"] or c["fields"]["slot"] in ready_panels)
    ]
    if images:
        print("\nNEXT  generate one image at a time, in this order. For each card run:")
        for card, _context in images:
            print(f"  python tools/check_card.py {card.relative_to(ROOT).as_posix()}")
    if modules:
        print("\nTHEN COMPOSE  after their panel images exist. For each module run:")
        for card, _context in modules:
            print(f"  python tools/check_card.py {card.relative_to(ROOT).as_posix()}")
    if failed:
        print("\nRETURN TO THE CARD WRITER  do not generate these; quote the FAIL lines above:")
        for rel in failed:
            print(f"  {rel}")
    return 1 if failed else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="a card file, a folder with --set, a task sheet with --task, or a product with --baseline")
    parser.add_argument("--set", action="store_true", help="check every card in a folder")
    parser.add_argument("--task", action="store_true", help="split a task sheet into cards and check them")
    parser.add_argument("--baseline", action="store_true", help="shape baseline renders for a product id (UTA_STYLE 1.12)")
    args = parser.parse_args()
    if args.baseline:
        return print_baseline(args.target)

    target = Path(args.target)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    index = load_index()

    if args.task:
        if not target.is_file():
            print(f"not a file: {args.target}")
            return 2
        return run_task(target, index)
    if args.set:
        if not target.is_dir():
            print(f"not a folder: {args.target}")
            return 2
        return check_set(target, index)

    if not target.is_file():
        print(f"not a file: {args.target}")
        return 2
    errors, warnings, context = validate(target, index)
    for warning in warnings:
        print(f"! {warning}")
    if errors:
        print(f"FAIL  {args.target}")
        for error in errors:
            print(f"  - {error}")
        print("\nDo not generate. Send these lines back to the card writer.")
        return 1
    print(f"OK    {args.target}\n")
    print_package(context, load_prompt_blocks())
    return 0


if __name__ == "__main__":
    sys.exit(main())
