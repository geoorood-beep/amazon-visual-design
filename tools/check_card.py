#!/usr/bin/env python3
"""Validate slot cards and print the generation package for them.

Usage:
    python tools/check_card.py --task outputs/task.md     a task sheet from the card writer
    python tools/check_card.py cards/round10l/S5_clean.md one card: attach list, prompt, typesetting
    python tools/check_card.py --set cards/round10l       every card in a folder

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

CAMERAS = {
    "low_angle": "low angle close to the floor or counter, camera looking slightly up",
    "eye_level": "eye-level view",
    "down_45": "about 45 degrees looking down",
    "top_down": "straight top-down view",
    "close_up": "close-up, product detail fills most of the frame",
    "wide": "wide view showing the whole room and the whole product",
}
MODULES = ("scene", "grid", "steps", "specs")
PANEL_COUNT = {"grid": (2, 4), "steps": (2, 4), "specs": (1, 1)}
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
        "cropped to different shapes"
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
OPTIONAL_KEYS = ["module", "label", "panels", "lines"]
ALL_KEYS = set(IMAGE_KEYS) | set(MODULE_KEYS) | set(OPTIONAL_KEYS)
ENGLISH_FIELDS = [
    "evidence", "human_action", "pet", "pet_action", "scene", "light",
    "headline", "subtitle", "hero_number", "label", "lines",
]
MAX_HEADLINE_WORDS = 6
MAX_SUBTITLE_WORDS = 10
MAX_LABEL_WORDS = 4
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
    """Return (facts, identity bullets, forbidden words) for a product id."""
    product_md = ROOT / "products" / product / "PRODUCT.md"
    if not re.fullmatch(r"[a-z0-9_]+", product) or not product_md.is_file():
        errors.append(f"product '{product}' has no products/{product}/PRODUCT.md")
        return {}, [], []
    text = read(product_md)
    identity = md_section_bullets(text, "Identity (prompt)")
    if not identity:
        errors.append(f"products/{product}/PRODUCT.md has no 'Identity (prompt)' bullets")
    return md_facts(text), identity, md_section_bullets(text, "禁用词")


def check_copy(copy, allowed_texts, product, product_forbidden, errors, what="copy"):
    """Forbidden words and numbers. allowed_texts: the 'allowed copy' of the facts in play."""
    global_forbidden = md_section_bullets(read(ROOT / "UTA_STYLE.md"), "禁用词")
    for word in find_forbidden(copy, global_forbidden):
        errors.append(f"{what} contains a word forbidden by UTA_STYLE.md: '{word}'")
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
        if row["type"] not in REF_SLOTS[slot_name]:
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

    if kind == "P" and not is_panel and module != "scene":
        return validate_module(path, fields, refs, errors, warnings, module, index)
    return validate_image(path, fields, refs, errors, warnings, kind, is_panel, index)


def validate_image(path, fields, refs, errors, warnings, kind, is_panel, index):
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
    canvas = "1:1" if (kind == "M" or is_panel) else {"S": "4:5", "P": "2.44:1"}[kind]
    if fields["canvas"] != canvas:
        errors.append(f"canvas for {slot} must be {canvas}")

    product = fields["product"]
    facts, identity, product_forbidden = load_product(product, errors)

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
    if not is_none(fields["hero_number"]) and not NUMBER.search(fields["hero_number"]):
        errors.append("hero_number must contain a number, or be none")
    copy = " ".join(
        fields[k] for k in ("headline", "subtitle", "hero_number", "label") if not is_none(fields.get(k))
    )
    check_copy(copy, [fact["allowed"]] if fact else [], product, product_forbidden, errors)

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
        "identity": identity, "attach": attach, "path": path,
    }
    return errors, warnings, context


def validate_module(path, fields, refs, errors, warnings, module, index):
    slot = fields["slot"]
    for key in MODULE_KEYS:
        if key not in fields:
            errors.append(f"missing field '{key}'")
    for key in IMAGE_KEYS:
        if key not in MODULE_KEYS and not is_none(fields.get(key)):
            errors.append(f"'{key}' belongs on the panel cards, not on a {module} module card")
    if not is_none(fields.get("label")):
        errors.append("'label' belongs on the panel cards")
    if errors:
        return errors, warnings, None

    if fields["card_version"] != "1":
        errors.append("card_version must be 1")
    if fields["canvas"] != "2.44:1":
        errors.append(f"canvas for {slot} must be 2.44:1")
    product = fields["product"]
    facts, _identity, product_forbidden = load_product(product, errors)

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
    low, high = PANEL_COUNT[module]
    names = [name.strip() for name in fields["panels"].split(",") if name.strip()]
    expected = [slot + letter for letter in "abcd"[: len(names)]]
    if not low <= len(names) <= high:
        count = str(low) if low == high else f"{low} to {high}"
        errors.append(f"a {module} module needs {count} panel(s), got {len(names)}")
    elif names != expected:
        errors.append(f"panels must be listed as {', '.join(expected)}")
    panels = []
    for name in names if names == expected else []:
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
        if module in ("grid", "steps") and is_none(panel_fields.get("label")):
            errors.append(f"panel {name}: 'label' is required in a {module} module")
        if module == "specs" and not is_none(panel_fields.get("label")):
            errors.append(f"panel {name}: 'label' must be none in a specs module")
        panels.append(panel_context)

    # Selling points
    panel_facts = [p["fields"]["selling_point"] for p in panels]
    used_facts = set(panel_facts)
    module_fact = fields["selling_point"]
    if module == "steps":
        if is_none(module_fact) or module_fact not in facts:
            errors.append("a steps module needs selling_point set to one fact id")
        elif any(f != module_fact for f in panel_facts):
            errors.append(f"every panel of a steps module must use {module_fact}")
        used_facts.add(module_fact)
    else:
        if not is_none(module_fact):
            errors.append(f"selling_point must be none on a {module} module card")
        if module == "grid" and len(set(panel_facts)) != len(panel_facts):
            errors.append("each panel of a grid module must show a different fact")

    # Spec lines: 'F1 | 10 L ; F2 | 304 Stainless Steel'
    lines = []
    if module == "specs":
        parts = [part.strip() for part in fields["lines"].split(";") if part.strip()]
        if is_none(fields["lines"]) or not 2 <= len(parts) <= 4:
            errors.append("a specs module needs 2 to 4 lines, written 'F1 | text ; F2 | text'")
        for part in parts if not is_none(fields["lines"]) else []:
            if "|" not in part:
                errors.append(f"line '{part}' must be 'fact id | text'")
                continue
            fact_id, text = (piece.strip() for piece in part.split("|", 1))
            if fact_id not in facts:
                errors.append(f"line '{part}': '{fact_id}' is not a fact id")
                continue
            if len(text.split()) > MAX_LABEL_WORDS:
                errors.append(f"line '{text}' has more than {MAX_LABEL_WORDS} words")
            check_copy(text, [facts[fact_id]["allowed"]], product, product_forbidden, errors, what=f"line '{text}'")
            used_facts.add(fact_id)
            lines.append((fact_id, text))
        if len({fact_id for fact_id, _text in lines}) != len(lines):
            errors.append("each line of a specs module must use a different fact")
    elif not is_none(fields["lines"]):
        errors.append("'lines' is only for a specs module")

    copy = " ".join(fields[k] for k in ("headline", "subtitle", "hero_number") if not is_none(fields[k]))
    allowed_texts = [facts[f]["allowed"] for f in sorted(used_facts) if f in facts]
    check_copy(copy, allowed_texts, product, product_forbidden, errors)

    attach = check_refs(refs, {"layout"}, product, index, errors)

    if errors:
        return errors, warnings, None
    context = {
        "type": "module", "fields": fields, "kind": "P", "panel": False, "module": module,
        "panels": panels, "lines": lines, "attach": attach, "path": path,
    }
    return errors, warnings, context


def build_prompt(context, blocks):
    fields, kind, is_panel = context["fields"], context["kind"], context["panel"]
    out = [f"FORMAT: {FORMAT_TEXT['panel' if is_panel else kind]}."]
    if kind == "M":
        out.append(
            "Studio product photograph on a pure white background (RGB 255,255,255). "
            "Product only: no props, no pets, no people, no text. Soft studio light with "
            "a clear highlight band on the brushed steel and a soft contact shadow."
        )
    else:
        out.append("STYLE: " + blocks["STYLE"])
    out.append("PRODUCT: " + "; ".join(context["identity"]) + ". " + blocks["PRODUCT_RULES"])
    if kind != "M":
        out.append("SCENE: " + fields["scene"].rstrip(".") + ".")
        action = ["WHAT IS HAPPENING: " + fields["evidence"].rstrip(".") + "."]
        if not is_none(fields["human_action"]):
            action.append("Hands: " + fields["human_action"].rstrip(".") + ".")
        if not is_none(fields["pet"]):
            action.append(f"Pet ({fields['pet']}): " + fields["pet_action"].rstrip(".") + ".")
        out.append(" ".join(action))
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
    else:
        area = fields["text_area"].replace("_", " ")
        out.append(f"TEXT: {blocks['TEXT_RULES']} Clear area: {area}.")
    refs = [
        f"Attached image {i} is the {REF_LABEL[slot]}, use it for: {purpose.rstrip('.')}."
        for i, (slot, _path, purpose) in enumerate(context["attach"], start=1)
    ]
    out.append("REFERENCES: " + " ".join(refs) + " " + blocks["REFERENCE_RULES"])
    out.append("AVOID: " + blocks["AVOID"])
    return "\n\n".join(out)


def output_stem(context):
    path = context["path"]
    return f"outputs/{context['fields']['product']}/{path.stem}"


def print_copy(fields):
    print(f"headline: {fields['headline']}")
    print(f"subtitle: {fields['subtitle']}")
    if not is_none(fields["hero_number"]):
        print(f"hero number (amber): {fields['hero_number']}")


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
    print("== PROMPT (use as is) ==")
    print(build_prompt(context, blocks))
    print()
    if context["panel"]:
        print("== AFTER GENERATION ==")
        print(f"save the image without text as: {stem}_v01.png")
        if not is_none(fields.get("label")):
            print(f"label, added when {fields['slot'][:2]} is composed: {fields['label']}")
        print(f"do not typeset this panel; compose it with its module card {fields['slot'][:2]}")
    elif kind == "M":
        print("== AFTER GENERATION ==")
        print(f"save as: {stem}_v01.png   (no text on M1)")
    elif kind == "P":
        print("== TYPESET AFTER GENERATION: two files from this one image (UTA_STYLE.md 1.9) ==")
        print(f"save the image without text as: {stem}_base_v01.png")
        print(f"desktop {stem}_desktop_1464x600_v01.png : crop the middle band, text on the {fields['text_area']}")
        print(f"mobile  {stem}_mobile_600x450_v01.png  : text band on top, image below")
        print_copy(fields)
    else:
        print("== TYPESET AFTER GENERATION (UTA_STYLE.md 1.5) ==")
        print(f"save the image without text as: {stem}_base_v01.png")
        print(f"save the typeset image as: {stem}_v01.png")
        print(f"text area: {fields['text_area']}")
        print_copy(fields)


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
    print_copy(fields)
    for number, panel in enumerate(context["panels"], start=1):
        panel_fields = panel["fields"]
        label = "" if is_none(panel_fields.get("label")) else f"   label: {panel_fields['label']}"
        step = f"step {number}  " if module == "steps" else ""
        print(f"panel {panel_fields['slot']}: {step}{output_stem(panel)}_v01.png{label}")
    for fact_id, text in context["lines"]:
        print(f"line ({fact_id}): {text}")
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
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines or lines[0].strip() != TASK_HEADER:
        return None, [], [f"first line must be '{TASK_HEADER}'"]

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
    parser.add_argument("target", help="a card file, a folder with --set, or a task sheet with --task")
    parser.add_argument("--set", action="store_true", help="check every card in a folder")
    parser.add_argument("--task", action="store_true", help="split a task sheet into cards and check them")
    args = parser.parse_args()

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
