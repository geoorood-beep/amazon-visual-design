"""Icon library (UTA_STYLE.md 1.5): a small line icon before a hero number, a panel label or a spec line.

A card writes {icon:<id>} at the very start of hero_number, label or one spec line's text, for example
'label: {icon:cord-free} Cord-Free' or 'lines: F1 | {icon:capacity} 10 L'. The id must be in
references/icons/icons.csv, and the fact behind that text must mention one of the icon's match words, so an
icon never claims something the product card does not confirm (no battery icon on a plug-in product).
Standard library only; check_card.py and check_set.py both use it.
"""
import csv
import os
import re

ICON_DIR = os.path.join("references", "icons")
TOKEN = re.compile(r"\{icon:([^}]*)\}")
LEAD = re.compile(r"^\s*\{icon:([^}]*)\}\s*")
ICON_FIELDS = ("hero_number", "label", "lines")
_cache = {}


def load_icons(root):
    """references/icons/icons.csv -> {id: row}."""
    path = os.path.join(str(root), ICON_DIR, "icons.csv")
    if path not in _cache:
        rows = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                rows = {r["id"].strip(): r for r in csv.DictReader(fh) if (r.get("id") or "").strip()}
        _cache[path] = rows
    return _cache[path]


def icon_path(icon_id):
    return "%s/%s.svg" % (ICON_DIR.replace(os.sep, "/"), icon_id)


def strip_icons(text):
    return re.sub(r"\s+", " ", TOKEN.sub(" ", text or "")).strip()


def split_icon(text):
    """(icon id or None, text without the icon, problem or None). The icon may only open the text, once."""
    text = text or ""
    found = TOKEN.findall(text)
    if not found:
        return None, text, None
    lead = LEAD.match(text)
    if len(found) > 1:
        return None, strip_icons(text), "only one icon per line"
    if not lead:
        return None, strip_icons(text), "the icon must come first, before the number or words"
    return lead.group(1).strip(), text[lead.end():].strip(), None


def icon_problem(root, icon_id, fact_text, field, module=""):
    """Why this icon cannot stand before this text, or None. fact_text: the fact and its allowed copy."""
    icons = load_icons(root)
    row = icons.get(icon_id)
    if row is None:
        return "unknown icon '%s' (see %s/icons.csv)" % (icon_id, ICON_DIR.replace(os.sep, "/"))
    only = (row.get("only") or "").strip()
    if only and not (field == "lines" and module == only):
        return "icon '%s' only goes on the lines of a %s screen" % (icon_id, only)
    words = [w.strip() for w in (row.get("match") or "").split(";") if w.strip()]
    if words and fact_text is not None:
        low = fact_text.lower()
        if not any(w.lower() in low for w in words):
            return "icon '%s' (%s) needs a fact that mentions one of: %s" % (icon_id, row.get("name", ""), ", ".join(words))
    return None
