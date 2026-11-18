"""How the product is used: states, and what each fact must show on screen (UTA_STYLE.md 1.15).

A product card may spell this out in two optional sections:

  ## 产品状态          | id | 名称 | 看得见 | 拿掉或看不见 | Prompt |
  ## 事实的画面要求    | 事实 | 状态 | 必须看得见（英文） | 不能出现（英文） | 推荐朝向 | 推荐机位 | 推荐景别 | 特效 |
  ## 内部结构          | 部件 | 英文名 | 位置 | 来源 |

The last four columns of 事实的画面要求 are optional; values are separated by ";".

When it does not, the requirement for a fact is inferred from references/fact_visuals.csv:
up to two rules whose keywords appear in the fact's own text or its 「画面可写」 column are
merged, the one whose keyword appears earliest first (state, camera and effect advice from the
first, visible evidence from both).
The 「不可写成」 column is never matched, so a card that forbids "拆解" does not trigger
the disassembly rule.
"""
import csv
import os
import re

GENERIC_STATES = {
    "assembled": "",
    "disassembled": ("The removable part is taken off and set aside, so the opened product and the detached "
                     "part are both clearly visible."),
    "loading": "The product is open and being filled; the contents are visibly going in.",
}
MAX_MERGED_RULES = 2
STATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
FACT_ROW_RE = re.compile(r"^\|\s*(F\d+)\s*\|([^|]*)\|([^|]*)\|")
RUNNING_RE = re.compile(
    r"\b(flowing|ripples?|starts to move|water starts|water falling|flow begins|"
    r"is running|keeps running|fountain runs)\b",
    re.I,
)
# Only a statement that this frame itself is not operating turns the light off.
# "if not shown running", "otherwise do not paint", "not an outlet", and
# "when the fountain is not running" are other sentences in the same card.
FRAME_OFF_RE = re.compile(r"not an operating shot", re.I)
WINDOW_OUT_RE = re.compile(r"keep the water window out of this (?:frame|cell)", re.I)
FRONT_VIEWS = {"front", "front_left", "front_right", "three_quarter_left", "three_quarter_right"}
COPY_KEYS = ("evidence", "story", "pet_action", "human_action")
WINDOW_LIGHT = (
    "While water is flowing and the front water window is in frame, a blue light is visible "
    "inside that window and the real water level stays readable through it, including the "
    "MAX and MIN marks already on that window."
)


def _section(text, heading):
    lines = text.splitlines()
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == heading
            continue
        if inside:
            out.append(line)
    return out


def _split(val):
    return [v.strip() for v in (val or "").split(";") if v.strip()]


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def load_rules(root):
    path = os.path.join(root, "references", "fact_visuals.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["words"] = [w.strip().lower() for w in r["keywords"].split(";") if w.strip()]
    return rows


def load_usage(root, product, rules=None):
    path = os.path.join(root, "products", product, "PRODUCT.md")
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    facts = {}
    for line in text.splitlines():
        m = FACT_ROW_RE.match(line)
        if m:
            facts[m.group(1)] = (m.group(2) + " " + m.group(3)).strip()
    states = {}
    for line in _section(text, "## 产品状态"):
        cells = _cells(line)
        if len(cells) >= 5 and cells[0] != "id" and STATE_ID_RE.match(cells[0]):
            states[cells[0]] = cells[4]
    explicit = {}
    for line in _section(text, "## 事实的画面要求"):
        cells = _cells(line)
        if len(cells) >= 4 and re.fullmatch(r"F\d+", cells[0]):
            more = cells[4:8] + [""] * (8 - len(cells))
            explicit[cells[0]] = {"state": cells[1], "must_show": cells[2], "must_not": cells[3],
                                  "views": _split(more[0]), "cameras": _split(more[1]),
                                  "shots": _split(more[2]), "effect": more[3].strip(),
                                  "moods": [], "expressions": [], "lenses": [],
                                  "source": "产品卡「事实的画面要求」"}
    structure = []
    for line in _section(text, "## 内部结构"):
        cells = _cells(line)
        if len(cells) >= 4 and cells[0] not in ("部件", "") and not set(cells[0]) <= set("-: ") and cells[1]:
            structure.append({"part": cells[0], "part_en": cells[1], "where": cells[2], "source": cells[3]})
    understanding = ""
    for line in _section(text, "## 产品理解"):
        m = re.match(r"^状态[:：]\s*(\S+)", line.strip())
        if m:
            understanding = m.group(1)
            break
    return {
        "understanding": understanding,
        "facts": facts,
        "states": states or dict(GENERIC_STATES),
        "own_states": bool(states),
        "explicit": explicit,
        "structure": structure,
        "window_light": confirmed_window_light(text),
        "rules": rules if rules is not None else load_rules(root),
    }


def confirmed_window_light(text):
    """Positive sentence for a confirmed running water-window light, or ''."""
    body = "\n".join(_section(text or "", "## 运行外观"))
    if not re.search(r"状态\s*[:：]\s*已确认", body):
        return ""
    if "蓝光" not in body or "水位" not in body:
        return ""
    return WINDOW_LIGHT


def _copy(fields):
    return " ".join(fields.get(key) or "" for key in COPY_KEYS)


def window_in_frame(fields):
    """Front-family viewpoint or an explicit water-window focus. The word "side" in the copy is not a view."""
    if WINDOW_OUT_RE.search(_copy(fields)):
        return False
    focus = (fields.get("focus") or "").strip()
    view = (fields.get("product_view") or "").strip()
    if view in ("", "none"):
        return focus == "water_window"
    return view in FRONT_VIEWS


def water_running(fields):
    blob = _copy(fields)
    if FRAME_OFF_RE.search(blob):
        return False
    return bool(RUNNING_RE.search(blob))


def window_light_applies(usage, fields):
    """Running, window in frame, and this product card confirmed that light."""
    if not usage or not usage.get("window_light"):
        return False
    if not fields:
        return False
    return water_running(fields) and window_in_frame(fields)


def requirement(usage, fact_id):
    """The state and visible evidence a fact needs, or None."""
    if not usage or not fact_id:
        return None
    if fact_id in usage["explicit"]:
        return usage["explicit"][fact_id]
    text = usage["facts"].get(fact_id, "").lower()
    if not text:
        return None
    # The rule whose keyword appears earliest in the fact wins, so a caveat at the end of a fact
    # ("frequent sensing may shorten battery life") does not outrank its subject ("battery").
    found = []
    for order, r in enumerate(usage["rules"]):
        spots = [text.find(w) for w in r["words"] if w in text]
        if spots:
            found.append((min(spots), order, r))
    found.sort(key=lambda x: (x[0], x[1]))
    ranked = [r for _, _, r in found]
    # A second rule merges in only when its keyword is in the fact's first sentence.
    ends = [i for i in (text.find(c) for c in "。；;") if i >= 0]
    first_end = min(ends) if ends else len(text)
    hits = ranked[:1] + [r for pos, _, r in found[1:] if pos < first_end][:MAX_MERGED_RULES - 1]
    # A rule that changes the product's state (take apart, fill) must never be dropped.
    state_rule = next((r for r in ranked if r["state"] != "assembled"), None)
    if state_rule is not None:
        # Taken apart or being filled: only rules for that same state apply (no "water flowing" while washing).
        hits = [state_rule] + [r for r in ranked if r is not state_rule and r["state"] == state_rule["state"]]
        hits = hits[:MAX_MERGED_RULES]
    if not hits:
        return None
    first = hits[0]
    state = next((r["state"] for r in hits if r["state"] != "assembled"), "assembled")
    return {"state": state,
            "must_show": "; ".join(r["must_show_en"].strip().rstrip(".") for r in hits),
            "must_not": "; ".join(r["must_not_en"].strip().rstrip(".") for r in hits if r["must_not_en"].strip()),
            "views": _split(first.get("views")), "cameras": _split(first.get("cameras")),
            "shots": _split(first.get("shots")),
            "moods": _split(first.get("moods")), "expressions": _split(first.get("expressions")),
            "lenses": _split(first.get("lenses")),
            "effect": (first.get("effect") or "").strip(),
            "source": "推断规则 %s（references/fact_visuals.csv）" % "、".join(r["id"] for r in hits)}
