#!/usr/bin/env python3
"""Validate a slot card and print the generation package for it.

Usage:
    python tools/check_card.py cards/round10l/S5_clean.md
    python tools/check_card.py --set cards/round10l

A card that fails validation must not be used to generate an image.
Rules are documented in standard/CARD_SPEC.md. Standard library only.
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
CANVAS_BY_KIND = {"M": "1:1", "S": "4:5", "P": "2.44:1"}
FORMAT_TEXT = {
    "1:1": "square 1:1",
    "4:5": "vertical 4:5 portrait",
    "2.44:1": (
        "wide horizontal banner, about 2.44:1. Keep the product, the pet and the "
        "action inside the middle horizontal band; leave the top 20% and the "
        "bottom 20% free of important content"
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
TOP_KEYS = [
    "card_version", "product", "slot", "canvas", "selling_point", "evidence",
    "human_action", "pet", "pet_action", "camera", "scene", "light",
    "text_area", "headline", "subtitle", "hero_number", "refs",
]
ENGLISH_FIELDS = [
    "evidence", "human_action", "pet", "pet_action", "scene", "light",
    "headline", "subtitle", "hero_number",
]
MAX_HEADLINE_WORDS = 6
MAX_SUBTITLE_WORDS = 10
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
        if key not in TOP_KEYS:
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
    for line in read(ROOT / "standard" / "prompt_base.txt").splitlines():
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


def validate(path, index):
    """Return (errors, warnings, context). context is None when the card is unusable."""
    fields, refs, errors = parse_card(path)
    warnings = []
    if errors and not fields:
        return errors, warnings, None

    for key in TOP_KEYS:
        if key not in fields:
            errors.append(f"missing field '{key}'")
    for key in REF_SLOTS:
        if key not in refs and not any(key in e for e in errors):
            errors.append(f"missing ref slot '{key}' (write 'none' if not used)")
    if errors:
        return errors, warnings, None

    if fields["card_version"] != "1":
        errors.append("card_version must be 1")

    # Slot and canvas
    slot = fields["slot"]
    match = re.fullmatch(r"(M1|S[1-9]|P[1-8])", slot)
    kind = slot[0] if match else None
    if not match:
        errors.append("slot must be M1, S1-S9 or P1-P8")
    elif fields["canvas"] != CANVAS_BY_KIND[kind]:
        errors.append(f"canvas for {slot} must be {CANVAS_BY_KIND[kind]}")

    # Product card
    product = fields["product"]
    product_md = ROOT / "products" / product / "PRODUCT.md"
    facts, identity, product_forbidden = {}, [], []
    if not re.fullmatch(r"[a-z0-9_]+", product) or not product_md.is_file():
        errors.append(f"product '{product}' has no products/{product}/PRODUCT.md")
    else:
        product_text = read(product_md)
        facts = md_facts(product_text)
        identity = md_section_bullets(product_text, "Identity (prompt)")
        product_forbidden = md_section_bullets(product_text, "禁用词")
        if not identity:
            errors.append(f"products/{product}/PRODUCT.md has no 'Identity (prompt)' bullets")

    # Selling point
    selling_point = fields["selling_point"]
    fact = None
    if is_none(selling_point):
        if kind != "M":
            errors.append("selling_point is required (a fact id such as F5) except for M1")
    elif selling_point not in facts:
        errors.append(
            f"selling_point '{selling_point}' is not a fact id in products/{product}/PRODUCT.md"
        )
    else:
        fact = facts[selling_point]

    # Camera and text area
    if fields["camera"] not in CAMERAS:
        errors.append("camera must be one of: " + ", ".join(CAMERAS))
    if kind == "M":
        for key in ("pet", "pet_action", "human_action", "headline", "subtitle", "hero_number"):
            if not is_none(fields[key]):
                errors.append(f"M1 is product only on white: '{key}' must be none")
        if fields["text_area"].lower() != "none":
            errors.append("M1 has no text: text_area must be none")
    else:
        for key in ("evidence", "scene", "light", "headline", "subtitle"):
            if is_none(fields[key]):
                errors.append(f"'{key}' is required for {slot}")
        if fields["text_area"] not in TEXT_AREAS:
            errors.append("text_area must be one of: " + ", ".join(sorted(TEXT_AREAS)))
        if is_none(fields["pet"]) != is_none(fields["pet_action"]):
            errors.append("pet and pet_action must both be filled or both be none")
        if is_none(fields["pet"]) and is_none(fields["human_action"]):
            warnings.append("no pet and no hands: check that the image can still show the selling point")
        if not is_none(fields["light"]) and not DIRECTION.search(fields["light"]):
            warnings.append("light does not say where the light comes from (left, right, behind ...)")

    # Language
    for key in ENGLISH_FIELDS:
        if CJK.search(fields[key]):
            errors.append(f"'{key}' must be written in English (it goes into the image prompt)")

    # Copy rules
    copy_parts = [fields[k] for k in ("headline", "subtitle", "hero_number") if not is_none(fields[k])]
    copy = " ".join(copy_parts)
    if not is_none(fields["headline"]) and len(fields["headline"].split()) > MAX_HEADLINE_WORDS:
        errors.append(f"headline has more than {MAX_HEADLINE_WORDS} words")
    if not is_none(fields["subtitle"]) and len(fields["subtitle"].split()) > MAX_SUBTITLE_WORDS:
        errors.append(f"subtitle has more than {MAX_SUBTITLE_WORDS} words")
    if not is_none(fields["hero_number"]) and not NUMBER.search(fields["hero_number"]):
        errors.append("hero_number must contain a number, or be none")
    global_forbidden = md_section_bullets(read(ROOT / "standard" / "CORE.md"), "禁用词")
    for word in find_forbidden(copy, global_forbidden):
        errors.append(f"copy contains a word forbidden by standard/CORE.md: '{word}'")
    for word in find_forbidden(copy, product_forbidden):
        errors.append(f"copy contains a word forbidden for {product}: '{word}'")
    if fact is not None:
        unknown = normalise_numbers(copy) - normalise_numbers(fact["allowed"])
        for number in sorted(unknown):
            errors.append(
                f"number '{number}' in the copy is not in the allowed copy of {selling_point} "
                f"({fact['allowed']})"
            )
    elif copy and NUMBER.search(copy):
        errors.append("copy contains numbers but no valid selling_point to check them against")

    # References
    attach = []
    for slot_name in ("product", "anchor", "expression", "layout"):
        ref = refs.get(slot_name)
        if ref is None:
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
            allowed = " or ".join(sorted(REF_SLOTS[slot_name]))
            errors.append(
                f"ref {slot_name}: '{clean}' is type '{row['type']}' in the index, needs {allowed}"
            )
            continue
        if slot_name == "product" and not row["key"].startswith(product + "/"):
            errors.append(f"ref product: '{clean}' belongs to '{row['key']}', not to {product}")
            continue
        attach.append((slot_name, clean, purpose))

    if refs.get("product") is None:
        errors.append("ref product is required")
    if kind == "M":
        for slot_name in ("anchor", "expression", "layout"):
            if refs.get(slot_name) is not None:
                errors.append(f"M1 takes only the product reference: ref {slot_name} must be none")
    if kind == "S" and refs.get("layout") is not None:
        errors.append("layout references are for P slots only: ref layout must be none")
    if refs.get("expression") is not None and is_none(fields["pet"]):
        errors.append("ref expression is set but the card has no pet")

    context = None
    if not errors:
        context = {"fields": fields, "kind": kind, "identity": identity, "attach": attach, "fact": fact}
    return errors, warnings, context


def build_prompt(context, blocks):
    fields, kind = context["fields"], context["kind"]
    out = [f"FORMAT: {FORMAT_TEXT[fields['canvas']]}."]
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
        area = fields["text_area"].replace("_", " ")
        out.append(f"TEXT: {blocks['TEXT_RULES']} Clear area: {area}.")
    else:
        out.append("TEXT: " + blocks["TEXT_RULES"])
    refs = [
        f"Attached image {i} is the {REF_LABEL[slot]}, use it for: {purpose.rstrip('.')}."
        for i, (slot, _path, purpose) in enumerate(context["attach"], start=1)
    ]
    out.append("REFERENCES: " + " ".join(refs) + " " + blocks["REFERENCE_RULES"])
    out.append("AVOID: " + blocks["AVOID"])
    return "\n\n".join(out)


def print_package(path, context, blocks):
    fields = context["fields"]
    print("== ATTACH THESE FILES TO THE IMAGE CALL, IN THIS ORDER ==")
    for i, (slot, ref_path, _purpose) in enumerate(context["attach"], start=1):
        print(f"{i}. {ref_path}   ({REF_LABEL[slot]})")
    print()
    print("== PROMPT (use as is) ==")
    print(build_prompt(context, blocks))
    print()
    print("== TYPESET AFTER GENERATION (standard/CORE.md section 5) ==")
    if context["kind"] == "M":
        print("No text on M1.")
    else:
        print(f"area: {fields['text_area']}")
        print(f"headline (Poppins Bold, #0F2438): {fields['headline']}")
        print(f"subtitle (Poppins Regular, about 0.4x headline): {fields['subtitle']}")
        if not is_none(fields["hero_number"]):
            print(f"hero number (Poppins Bold, #F47A21): {fields['hero_number']}")


def check_set(folder, index):
    cards = sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))
    if not cards:
        print(f"no cards in {folder}")
        return 1
    failed, valid = 0, []
    for card in cards:
        errors, warnings, context = validate(card, index)
        rel = card.relative_to(ROOT).as_posix()
        if errors:
            failed += 1
            print(f"FAIL  {rel}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK    {rel}")
            valid.append((card, context))
        for warning in warnings:
            print(f"  ! {warning}")

    def order(item):
        slot = item[1]["fields"]["slot"]
        return ("MSP".index(slot[0]), int(slot[1:]))

    valid.sort(key=order)
    notes, seen_slots, seen_facts = [], {}, {}
    for card, context in valid:
        f = context["fields"]
        if f["slot"] in seen_slots:
            notes.append(f"slot {f['slot']} appears in two cards: {seen_slots[f['slot']]} and {card.name}")
        seen_slots[f["slot"]] = card.name
        if context["kind"] == "S" and not is_none(f["selling_point"]):
            if f["selling_point"] in seen_facts:
                notes.append(
                    f"{f['selling_point']} is the selling point of two S cards: "
                    f"{seen_facts[f['selling_point']]} and {card.name}"
                )
            seen_facts[f["selling_point"]] = card.name
    for kind in "SP":
        group = [c for _card, c in valid if c["kind"] == kind]
        cameras = [c["fields"]["camera"] for c in group]
        for a, b, ca, cb in zip(group, group[1:], cameras, cameras[1:]):
            if ca == cb:
                notes.append(
                    f"{a['fields']['slot']} and {b['fields']['slot']} use the same camera ({ca})"
                )
        if cameras.count("eye_level") > 1:
            notes.append(f"{kind} set has more than one eye_level card")
        if kind == "S" and len(group) >= 6:
            if not {"top_down", "down_45"} & set(cameras):
                notes.append("S set has no overhead card (top_down or down_45)")
            if cameras.count("low_angle") < 2:
                notes.append("S set has fewer than two low_angle cards")
    if notes:
        print("\nSet notes (fix these when writing cards; they do not block a single image):")
        for note in notes:
            print(f"  ! {note}")
    print(f"\n{len(cards) - failed} of {len(cards)} cards valid")
    return 1 if failed else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="a card file, or a folder of cards with --set")
    parser.add_argument("--set", action="store_true", help="check every card in a folder")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    index = load_index()

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
    print_package(target, context, load_prompt_blocks())
    return 0


if __name__ == "__main__":
    sys.exit(main())
