#!/usr/bin/env python3
"""UTA Style v3.2: whole-set check and card_version 2 -> 1 compiler.

Usage (Codex, UTA_STYLE.md 3.2 step 2):
    python tools/check_set.py --task outputs/task.md --emit outputs/task_v1.md
    python tools/check_card.py --task outputs/task_v1.md

What it does:
  * UTA-TASK v2: checks the v2 fields of every card (UTA_STYLE.md 1.4, 2.4),
    product-reference coverage from products/<product>/ref_views.csv (1.4),
    the numbered whole-set rules S-*, A-*, G-* (2.6). Cards that pass are
    compiled to card_version 1 (the format check_card.py already knows) and
    written to --emit. Shot size, product view, focus, light setup and
    foreground become sentences inside evidence, light and scene.
  * UTA-TASK v1 (legacy): no hard set checks. Prints WARN lines only and,
    with --emit, copies the task unchanged so the old flow keeps working.

Exit codes: 0 no FAIL; 1 some cards FAIL (the rest emitted);
            2 SET FAIL or TASK ERROR (nothing emitted).

Standard library only. Does not read or modify check_card.py.
"""
import argparse
import csv
import math
import os
import re
import sys

VERSION = "3.21"

V2_IMAGE_FIELDS = ["shot_size", "product_view", "focus", "interaction",
                   "light_setup", "foreground"]
POOL_FIELDS = ["evidence_id", "scene_id", "pet_id", "person_id", "person_mood_id", "expression_id"]
FACE_SHOWN = {"half_body", "full_body", "group"}
V2_ONLY_FIELDS = set(V2_IMAGE_FIELDS) | {"beat", "story"} | set(POOL_FIELDS)
MAX_STORY_WORDS = 35
CJK_RE = re.compile(r"[\u3400-\u9fff]")
POOL_FILES = {"scenes": "scenes.csv", "pets": "pets.csv", "people": "people.csv",
              "expressions": "expressions.csv", "styles": "styles.csv", "moods": "moods.csv"}

SHOT_ORDER = ["extreme_close", "close", "medium", "full", "wide"]
CLOSE_SHOTS = {"extreme_close", "close"}
FAR_SHOTS = {"full", "wide"}
CAMERA_V2 = ["top_down", "down_45", "eye_level", "low_angle"]
OVERHEAD = {"top_down", "down_45"}
PRODUCT_VIEWS = ["front", "front_left", "front_right", "three_quarter_left",
                 "three_quarter_right", "side_left", "side_right", "rear",
                 "cutaway"]
INTERACTIONS = {
    "share_drink": "pet", "drink": "pet", "wait": "pet", "inspect": "pet",
    "paw_touch": "pet", "rest": "pet",
    "human_fill": "human", "human_rinse": "human", "human_wipe": "human",
    "human_check": "human",
    "product_only": "none",
}
LIGHT_SETUPS = ["side", "side_back", "back", "low_sun", "night_lamp"]
BEATS = ["hook", "life", "detail", "routine", "close"]
MODULES = ["scene", "grid", "steps", "specs", "number", "contrast"]
COMPOSITE = {"grid", "steps", "contrast"}
SINGLE = {"scene", "number"}

SHOT_TEXT = {
    "extreme_close": "Extreme close-up with a macro-lens look: {focus} fills more than half of the frame, very shallow depth of field; the frame may cut off the rest of the product.",
    "close": "Close shot with a short-telephoto look: {focus} and the action around it fill the frame; the background is compressed and soft; the frame may cut off part of the product.",
    "medium": "Medium shot with a standard-lens look: the whole product and the action fill the middle of the frame.",
    "full": "Full shot: the whole product, the full bodies of the pets or the upper body of the person, and one or two pieces of furniture around them.",
    "wide": "Wide shot with a wide-angle look: the room around the product shows depth; the product is small but its shape stays clear and recognisable.",
}
VIEW_TEXT = {
    "front": "The product is seen from the front.",
    "front_left": "The product is seen from the front, the camera a little to the left of centre (within about 15 degrees).",
    "front_right": "The product is seen from the front, the camera a little to the right of centre (within about 15 degrees).",
    "three_quarter_left": "The product is seen at about 45 degrees from the front-left.",
    "three_quarter_right": "The product is seen at about 45 degrees from the front-right.",
    "side_left": "The product is seen from its left side.",
    "side_right": "The product is seen from its right side.",
    "rear": "The product is seen from the back.",
    "cutaway": "A cutaway view that follows the registered structure reference exactly.",
}
CAMERA_TEXT = {
    "top_down": "Camera straight above, looking down.",
    "down_45": "Camera looking down at about 45 degrees.",
    "eye_level": "Camera level with the subject.",
    "low_angle": "Camera close to the floor or table, looking slightly up.",
}
LIGHT_TEXT = {
    "side": "Light setup: hard side light from one window at about 90 degrees, a clear highlight band on the steel, the other side falling darker, short crisp shadows.",
    "side_back": "Light setup: window light from the side and slightly behind, rim light on fur and on the water stream, depth in the room, the front of the product still readable.",
    "back": "Light setup: backlight from behind the subject, bright edges on fur and water, the camera does not look into the light source, the front of the product readable from room bounce, not a silhouette, the product does not glow.",
    "low_sun": "Light setup: low warm sun through a window, long directional shadows across the floor, natural colours, not orange overall.",
    "night_lamp": "Light setup: night, one warm indoor lamp on one side, the rest of the room falls dark, the product is lit only by that lamp and neither the product nor the water window glows.",
}
REF_ONLY_TEXT = ("Use the product reference image only for shape, parts, proportions "
                 "and finish; do not copy its camera angle or framing.")
CASE_CAMERA_TEXT = ("Take the camera height, framing and composition from the style reference; "
                    "the product itself always follows the product reference.")

POINT_RE = re.compile(r"\b(point|points|pointed|pointing)\b|\bindex finger\b", re.I)
STRUCTURE_RE = re.compile(
    r"\b(x-?ray|cut-?away|cross[- ]section|exploded|see-through|internal structure|"
    r"inner structure|pump|filter|filters|cartridge|LED|light-up)\b", re.I)
NEGATION = {"no", "not", "without", "never", "nor"}
DURATION_RE = re.compile(
    r"\b(day|days|week|weeks|month|months|vacation|vacations|holiday|holidays|"
    r"travel|trip|trips|weekend|weekends)\b", re.I)
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
DOG_WORDS = re.compile(
    r"\b(dog|dogs|puppy|retriever|terrier|shepherd|poodle|corgi|labrador|husky|"
    r"beagle|spaniel|collie|bulldog|dachshund)\b", re.I)
CAT_WORDS = re.compile(r"\b(cat|cats|kitten|ragdoll|tabby)\b", re.I)
HEADER_RE = re.compile(r"^UTA-TASK v([12])\s*$")
BLOCK_RE = re.compile(r"^=== (cards/\S+\.md) ===\s*$")
SLOT_S = re.compile(r"^S(\d+)$")
SLOT_P = re.compile(r"^P(\d+)$")
SLOT_PANEL = re.compile(r"^P(\d+)([a-z])$")
STOP = set("""the a an and of to in on at by with from into over its it is are be
both each one two same side sides while who that this which their them they
clearly visible kept stay stays toward towards slightly""".split())


class TaskError(Exception):
    pass


# ---------------------------------------------------------------- parsing
class Card:
    def __init__(self, path, body_lines):
        self.path = path
        self.items = []          # [key, value, extra_raw_lines]
        self.fields = {}
        self.refs = {}
        self.parse_errors = []
        current = None
        for raw in body_lines:
            if not raw.strip():
                continue
            if raw.startswith(" ") and current == "refs":
                key, sep, val = raw.strip().partition(":")
                if not sep:
                    self.parse_errors.append("refs 这一行看不懂：%s" % raw.strip())
                    continue
                self.refs[key.strip()] = val.strip()
                self.items[-1][2].append(raw)
                continue
            key, sep, val = raw.partition(":")
            if not sep:
                self.parse_errors.append("这一行看不懂：%s" % raw.strip())
                continue
            key, val = key.strip(), val.strip()
            self.items.append([key, val, []])
            self.fields[key] = val
            current = key

    # convenience
    def f(self, key, default=""):
        return self.fields.get(key, default)

    @property
    def slot(self):
        return self.f("slot")

    @property
    def kind(self):
        s = self.slot
        if s == "M1":
            return "main"
        if SLOT_S.match(s):
            return "sub"
        if SLOT_P.match(s):
            return "screen"
        if SLOT_PANEL.match(s):
            return "panel"
        return "unknown"

    @property
    def module(self):
        return self.f("module", "scene") if self.kind == "screen" else None

    @property
    def is_image(self):
        """Cards that become one generated picture (not M1, not a module card)."""
        if self.kind in ("sub", "panel"):
            return True
        return self.kind == "screen" and self.module == "scene"

    def is_none(self, key):
        return self.f(key, "none").strip().lower() in ("", "none")


def parse_task(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if HEADER_RE.match(line.strip()):
            start = i
            break
    if start is None:
        raise TaskError("没有找到 `UTA-TASK v2`（或旧的 `UTA-TASK v1`）这一行")
    version = int(HEADER_RE.match(lines[start].strip()).group(1))
    header = {}
    i = start + 1
    while i < len(lines) and not BLOCK_RE.match(lines[i].strip()):
        line = lines[i].strip()
        if line and not line.startswith("```"):
            key, sep, val = line.partition(":")
            if not sep:
                raise TaskError("头部第 %d 行看不懂：%s" % (i + 1, line))
            header[key.strip()] = val.strip()
        i += 1
    cards = []
    while i < len(lines):
        line = lines[i].strip()
        m = BLOCK_RE.match(line)
        if not m:
            if line and not line.startswith("```"):
                raise TaskError("第 %d 行不在任何一张卡里：%s" % (i + 1, line))
            i += 1
            continue
        path = m.group(1)
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines) or lines[i].strip() != "---":
            raise TaskError("%s：卡要以 --- 开始" % path)
        i += 1
        body = []
        while i < len(lines) and lines[i].strip() != "---":
            body.append(lines[i])
            i += 1
        if i >= len(lines):
            raise TaskError("%s：卡要以 --- 结束" % path)
        i += 1
        cards.append(Card(path, body))
    if "product" not in header:
        raise TaskError("头部缺少 product:")
    if "cards" not in header:
        raise TaskError("头部缺少 cards:")
    try:
        declared = int(header["cards"])
    except ValueError:
        raise TaskError("cards: 后面要写数字")
    if declared != len(cards):
        raise TaskError("cards: 写的是 %d，实际有 %d 张卡" % (declared, len(cards)))
    scope = header.get("scope", "full")
    if scope not in ("full", "patch"):
        raise TaskError("scope: 只能写 full 或 patch")
    slots = [c.slot for c in cards]
    dup = sorted({s for s in slots if slots.count(s) > 1})
    if dup:
        raise TaskError("图位重复：%s" % ", ".join(dup))
    return version, header, cards


def load_views(path):
    if not os.path.exists(path):
        raise TaskError("缺少产品参考视角表 %s（UTA_STYLE.md 1.4）" % path)
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        need = {"path", "product_view", "cameras", "parts", "checked"}
        if not reader.fieldnames or not need.issubset(set(reader.fieldnames)):
            raise TaskError("%s 的表头要有：path,product_view,cameras,parts,checked" % path)
        for n, row in enumerate(reader, 2):
            view = row["product_view"].strip()
            cams = [c.strip() for c in row["cameras"].split(";") if c.strip()]
            parts = [p.strip() for p in row["parts"].split(";") if p.strip()]
            if view not in PRODUCT_VIEWS:
                raise TaskError("%s 第 %d 行：product_view 不认识：%s" % (path, n, view))
            bad = [c for c in cams if c not in CAMERA_V2]
            if bad:
                raise TaskError("%s 第 %d 行：cameras 不认识：%s" % (path, n, ",".join(bad)))
            rows.append({"path": row["path"].strip(), "view": view, "cameras": cams,
                         "parts": parts, "checked": row["checked"].strip().lower() == "yes"})
    if not rows:
        raise TaskError("%s 里没有任何参考图" % path)
    return rows


def load_pools(root):
    """pools/*.csv -> {name: {id: row}} (UTA_STYLE.md 1.13)."""
    pools = {}
    for name, fname in POOL_FILES.items():
        path = os.path.join(root, "pools", fname)
        if not os.path.exists(path):
            raise TaskError("缺少选项池 pools/%s（UTA_STYLE.md 1.13）" % fname)
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        pools[name] = {r["id"].strip(): r for r in rows if r.get("id", "").strip()}
    return pools


def load_evidence(root, product):
    """products/<product>/evidence_options.csv -> {id: row}, or None when the product has none."""
    path = os.path.join(root, "products", product, "evidence_options.csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["id"].strip(): r for r in csv.DictReader(fh) if r.get("id", "").strip()}


# ---------------------------------------------------------------- helpers
def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def pet_key(card):
    pet = card.f("pet", "none")
    if pet.strip().lower() in ("", "none"):
        return "none"
    has_cat = bool(CAT_WORDS.search(pet))
    has_dog = bool(DOG_WORDS.search(pet))
    if has_cat and has_dog:
        return "cat+dog"
    if has_cat:
        return "cat"
    if has_dog:
        return "dog"
    return "other"


def positive_hits(regex, text):
    """Matches that are not negated by no/not/without within the 4 words before."""
    hits = []
    for m in regex.finditer(text or ""):
        before = re.findall(r"[A-Za-z']+", text[:m.start()])[-4:]
        if any(w.lower() in NEGATION for w in before):
            continue
        hits.append(m.group(0))
    return hits


def join_sentence(val, extra):
    """Append extra after val, closing val with a full stop first."""
    val = val.rstrip()
    if val and val[-1] not in ".!?":
        val += "."
    return (val + " " + extra) if val else extra


def focus_label(focus):
    return "the whole product" if focus == "whole" else "the " + focus.replace("_", " ")


def product_ref_path(card):
    return card.refs.get("product", "").split("|")[0].strip()


def ceil_half(n):
    return int(math.ceil(n / 2.0))


def words(text):
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 3 and w not in STOP}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def legacy_interaction(card):
    ev = (card.f("evidence") + " " + card.f("pet_action") + " " + card.f("human_action")).lower()
    pk = pet_key(card)
    if card.is_none("pet") and card.is_none("human_action"):
        return "product_only"
    if "rins" in ev:
        return "human_rinse"
    if "wip" in ev:
        return "human_wipe"
    if POINT_RE.search(card.f("human_action")):
        return "human_point"
    if "drink" in ev:
        return "share_drink" if pk == "cat+dog" else "drink"
    if "asleep" in ev or "sleep" in ev:
        return "rest"
    if "paw" in ev:
        return "paw_touch"
    return "inspect"


# ---------------------------------------------------------------- card checks
def bound_fact(card):
    fact = card.f("selling_point", "").strip()
    return fact if re.fullmatch(r"F\d+", fact) else ""


def report_copy_limits(text, fact_id, grants, errs, where, claims=None):
    """Duration stays fact-bound. wireless/battery are claims, not forbidden words."""
    from copy_exceptions import duration_hits, invented_feature_hits

    held = (grants or {}).get(fact_id, set())
    hits = duration_hits(text, held)
    if hits:
        errs.append("%s 写了时长说法（%s），不在已确认事实里（2.7）" % (where, ", ".join(sorted(set(hits)))))
    words = invented_feature_hits(text, claims)
    if words:
        errs.append("%s 写了产品卡没有确认的功能（%s）（2.7）" % (
            where, ", ".join(sorted(set(words)))))


def check_copy(card, errs, grants=None, claims=None):
    from copy_exceptions import line_bindings

    head = card.f("headline", "none")
    hero = card.f("hero_number", "none")
    if hero.strip().lower() not in ("", "none") and head.strip().lower() not in ("", "none"):
        same = [n for n in NUM_RE.findall(hero) if n in NUM_RE.findall(head)]
        if same:
            errs.append("headline 里重复了强调数字 %s：数字只放在 hero_number，主标题写好处（1.5）" % ", ".join(same))
    fact = bound_fact(card)
    for key in ("eyebrow", "headline", "subtitle", "hero_number", "label", "lines"):
        text = card.f(key)
        if key == "lines":
            for line_fact, body in line_bindings(text):
                report_copy_limits(body, line_fact, grants, errs, "lines", claims)
        else:
            report_copy_limits(text, fact, grants, errs, key, claims)


def check_scene_words(card, errs):
    if POINT_RE.search(card.f("human_action")):
        errs.append("human_action 写了指着产品的动作：换成加水、冲洗、擦拭、查看这类真实动作（1.2）")
    for key in ("evidence", "scene", "light", "human_action", "pet_action", "foreground"):
        hits = positive_hits(STRUCTURE_RE, card.f(key))
        if hits:
            errs.append("%s 写了参考图看不到的结构或特效（%s）（1.4、2.7）" % (key, ", ".join(sorted(set(hits)))))


def check_card_v2(card, views, pools=None, evidence=None, grants=None, claims=None):
    errs = list(card.parse_errors)
    if card.f("card_version") != "2":
        errs.append("这是 UTA-TASK v2，卡要写 card_version: 2")
    kind = card.kind
    if kind == "unknown":
        errs.append("slot 看不懂：%s" % card.slot)
        return errs
    if kind == "main":
        for key in V2_IMAGE_FIELDS:
            if key in card.fields and not card.is_none(key):
                errs.append("M1 的 %s 要写 none" % key)
        if "beat" in card.fields:
            errs.append("M1 不写 beat")
        return errs
    if kind == "screen":
        mod = card.module
        if mod not in MODULES:
            errs.append("module 不认识：%s" % mod)
        if card.f("beat") not in BEATS:
            errs.append("beat 要写 %s 之一" % " / ".join(BEATS))
        if mod != "scene":
            present = [k for k in V2_IMAGE_FIELDS if k in card.fields]
            if present:
                errs.append("模块卡不写 %s（写在小格卡里）" % ", ".join(present))
            check_copy(card, errs, grants, claims)
            return errs
    if kind == "panel" and "beat" in card.fields:
        errs.append("小格卡不写 beat")
    # image card
    missing = [k for k in V2_IMAGE_FIELDS if k not in card.fields]
    if missing:
        errs.append("缺少字段：%s" % ", ".join(missing))
        return errs
    shot, cam = card.f("shot_size"), card.f("camera")
    view, focus = card.f("product_view"), card.f("focus")
    inter, light = card.f("interaction"), card.f("light_setup")
    if shot not in SHOT_ORDER:
        errs.append("shot_size 要写 %s 之一" % " / ".join(SHOT_ORDER))
    if cam not in CAMERA_V2:
        errs.append("camera 要写 %s 之一（close_up、wide 改写进 shot_size）" % " / ".join(CAMERA_V2))
    if view not in PRODUCT_VIEWS:
        errs.append("product_view 不认识：%s" % view)
    if inter not in INTERACTIONS:
        errs.append("interaction 不认识：%s" % inter)
    if light not in LIGHT_SETUPS:
        errs.append("light_setup 要写 %s 之一" % " / ".join(LIGHT_SETUPS))
    if not card.f("foreground"):
        errs.append("foreground 要写内容或 none")
    if errs:
        return errs
    # coverage (1.4): product references give the shape, case references give the camera.
    if view == "cutaway" and not [r for r in views if r["view"] == "cutaway"]:
        errs.append("cutaway 只有 ref_views.csv 登记了 cutaway 那一行（真实结构图或拆解照片）才能用（1.4）")
    parts = set(p for r in views for p in r["parts"])
    if focus != "whole" and focus not in parts:
        errs.append("focus=%s 不在任何产品参考图的 parts 里（%s）；谁也没拍过的部位不画（1.4）"
                    % (focus, ";".join(sorted(parts))))
    ref = product_ref_path(card)
    if ref and ref not in [r["path"] for r in views]:
        errs.append("refs.product 用的 %s 没有登记在 ref_views.csv 里（1.4）" % ref)
    if shot in CLOSE_SHOTS and focus == "whole":
        errs.append("%s 的 focus 不能是 whole，写出焦点部位" % shot)
    need = INTERACTIONS[inter]
    if need == "pet" and card.is_none("pet"):
        errs.append("interaction=%s 是宠物的动作，pet 不能是 none" % inter)
    if need == "human" and card.is_none("human_action"):
        errs.append("interaction=%s 是人手的动作，human_action 不能是 none" % inter)
    if need == "none" and not (card.is_none("pet") and card.is_none("human_action")):
        errs.append("interaction=product_only 时 pet 和 human_action 都写 none")
    check_scene_words(card, errs)
    check_copy(card, errs, grants, claims)
    if pools is not None:
        check_pool_fields(card, pools, evidence, errs)
        check_story(card, errs, grants, claims)
        style = pools.get("style_row")
        if style and card.f("light_setup") not in split_list(style["lights"]):
            errs.append("风格 %s（%s）只配光型 %s，这张卡是 %s" % (style["id"], style["name"], style["lights"], card.f("light_setup")))
    return errs


def split_list(val, sep=";"):
    return [v.strip() for v in (val or "").split(sep) if v.strip()]


def pool_ids(card, key):
    return [] if card.is_none(key) else split_list(card.f(key), "+")


def check_pool_fields(card, pools, evidence, errs):
    """1.13: the pool ids on an image card exist and agree with the card."""
    missing = [k for k in POOL_FIELDS if k not in card.fields]
    if missing:
        errs.append("缺少选项池字段：%s（1.13）" % ", ".join(missing))
        return
    inter = card.f("interaction")
    ev = card.f("evidence_id").strip()
    if ev.lower() in ("", "none"):
        if evidence and not (card.kind == "panel" and inter == "product_only"):
            errs.append("evidence_id 要写证据方案表里的编号；只有产品单独出镜的小格可以写 none")
    elif ev != "custom":
        row = (evidence or {}).get(ev)
        if row is None:
            errs.append("evidence_id %s 不在这个产品的 evidence_options.csv 里" % ev)
        elif row["fact"].strip() != card.f("selling_point"):
            errs.append("evidence_id %s 属于 %s，不是这张卡的 %s" % (ev, row["fact"].strip(), card.f("selling_point")))
    sc = card.f("scene_id").strip()
    row = pools["scenes"].get(sc)
    if row is None:
        errs.append("scene_id %s 不在场景池 pools/scenes.csv 里" % sc)
    else:
        if card.f("light_setup") not in split_list(row["lights"]):
            errs.append("场景 %s（%s）只配光型 %s，这张卡是 %s" % (sc, row["name"], row["lights"], card.f("light_setup")))
        keys = split_list(row["keywords"])
        if not any(k.lower() in card.f("scene").lower() for k in keys):
            errs.append("scene 要写出场景 %s（%s）的地点，含 %s 之一" % (sc, row["name"], " / ".join(keys)))
    pets = pool_ids(card, "pet_id")
    if card.is_none("pet") != (not pets):
        errs.append("pet 和 pet_id 要同填或同为 none")
    for pid in pets:
        row = pools["pets"].get(pid)
        if row is None:
            errs.append("pet_id %s 不在宠物池 pools/pets.csv 里" % pid)
        elif row["look_en"].strip().lower() not in card.f("pet").lower():
            errs.append("pet 要写出宠物池 %s 的样子：%s" % (pid, row["look_en"].strip()))
    exprs = pool_ids(card, "expression_id")
    if bool(pets) != bool(exprs):
        errs.append("有宠物就写 expression_id，没有宠物写 none")
    key = "human" if inter.startswith("human_") else inter
    for eid in exprs:
        row = pools["expressions"].get(eid)
        if row is None:
            errs.append("expression_id %s 不在表情池 pools/expressions.csv 里" % eid)
        elif key not in split_list(row["interactions"]):
            errs.append("表情 %s（%s）不配互动 %s，它配 %s" % (eid, row["name"], inter, row["interactions"]))
    if card.is_none("human_action") != card.is_none("person_id"):
        errs.append("human_action 和 person_id 要同填或同为 none")
    elif not card.is_none("person_id"):
        hid = card.f("person_id").strip()
        row = pools["people"].get(hid)
        if row is None:
            errs.append("person_id %s 不在人物池 pools/people.csv 里" % hid)
        elif INTERACTIONS.get(inter) == "human" and row["shown"].strip() != "hands":
            errs.append("演示操作只出手和小臂（1.7）：%s 是 %s" % (hid, row["shown"].strip()))
        elif row["shown"].strip() in FACE_SHOWN and card.is_none("person_mood_id"):
            errs.append("情景里出镜的人物 %s 要写 person_mood_id（人物情绪池，1.7）" % hid)
        elif row["shown"].strip() == "hands" and not card.is_none("person_mood_id"):
            errs.append("只出手的人物看不到脸，person_mood_id 写 none")
    if card.is_none("person_id") and not card.is_none("person_mood_id"):
        errs.append("没有人物时 person_mood_id 写 none")
    if not card.is_none("person_mood_id"):
        mid = card.f("person_mood_id").strip()
        if mid not in pools["moods"]:
            errs.append("person_mood_id %s 不在人物情绪池 pools/moods.csv 里" % mid)


def check_story(card, errs, grants=None, claims=None):
    """1.14: a card with a pet or a person carries a one-sentence English story."""
    story = card.f("story", "").strip()
    needs = not (card.is_none("pet") and card.is_none("human_action"))
    if story.lower() in ("", "none"):
        if needs:
            errs.append("有宠物或人物的图要写 story：一句英文，谁、什么时刻、什么情绪、卖点怎么被看见（1.14）")
        return
    if CJK_RE.search(story):
        errs.append("story 要用英文写")
    if len(story.split()) > MAX_STORY_WORDS:
        errs.append("story 超过 %d 个词，写成一句话" % MAX_STORY_WORDS)
    report_copy_limits(story, bound_fact(card), grants, errs, "story", claims)
    hits = positive_hits(STRUCTURE_RE, story)
    if hits:
        errs.append("story 写了参考图看不到的结构或特效（%s）（1.14、2.7）" % ", ".join(sorted(set(hits))))
    if POINT_RE.search(story):
        errs.append("story 写了指着产品的动作（1.2）")


def check_card_legacy(card):
    warns = []
    check_scene_words(card, warns)
    check_copy(card, warns)
    return warns


# ---------------------------------------------------------------- set model
class TaskSet:
    def __init__(self, cards):
        self.cards = cards
        self.by_slot = {c.slot: c for c in cards}
        self.subs = sorted([c for c in cards if c.kind == "sub"],
                           key=lambda c: int(SLOT_S.match(c.slot).group(1)))
        self.screens = sorted([c for c in cards if c.kind == "screen"],
                              key=lambda c: int(SLOT_P.match(c.slot).group(1)))
        self.panels = [c for c in cards if c.kind == "panel"]

    def panels_of(self, screen):
        names = [p.strip() for p in screen.f("panels", "none").split(",")]
        return [n for n in names if n and n.lower() != "none"]

    def main_image(self, screen):
        if screen.module == "scene":
            return screen
        names = self.panels_of(screen)
        return self.by_slot.get(names[0]) if names else None

    def aplus_images(self):
        out = []
        for s in self.screens:
            if s.module == "scene":
                out.append(s)
            for n in self.panels_of(s):
                if n in self.by_slot:
                    out.append(self.by_slot[n])
        return out

    def edition(self):
        eds = {s.f("edition", "standard") for s in self.screens}
        return eds.pop() if len(eds) == 1 else "mixed"


def fact_counts(ts):
    counts = {}

    def add(f, where):
        f = f.strip()
        if f and f.lower() != "none":
            counts.setdefault(f, []).append(where)

    for s in ts.screens:
        mod = s.module
        if mod == "scene" or mod in ("steps", "number", "contrast"):
            add(s.f("selling_point"), s.slot)
        elif mod == "grid":
            for n in ts.panels_of(s):
                if n in ts.by_slot:
                    add(ts.by_slot[n].f("selling_point"), n)
        elif mod == "specs":
            for part in s.f("lines", "none").split(";"):
                if "|" in part:
                    add(part.split("|")[0], s.slot + " lines")
    return counts


def image_units(ts):
    """[(tag, name, [image cards])]: each S image, each A+ scene screen, each A+ module with its panels."""
    units = [("S", c.slot, [c]) for c in ts.subs]
    for s in ts.screens:
        if s.module == "scene":
            units.append(("P", s.slot, [s]))
        else:
            cards = [ts.by_slot[n] for n in ts.panels_of(s) if n in ts.by_slot]
            if cards:
                units.append(("P", s.slot, cards))
    return units


def pool_rules(ts, evidence, pools=None):
    """E-1, E-3, K-1, K-2 (2.6). Return (fails, warns)."""
    fails, warns = [], []
    units = [u for u in image_units(ts)
             if all("scene_id" in c.fields for c in u[2])]

    def ids(cards, key):
        out = []
        for c in cards:
            for v in pool_ids(c, key):
                if v not in out and v.lower() not in ("custom",):
                    out.append(v)
        return out

    used = {}
    for tag, name, cards in units:
        for ev in ids(cards, "evidence_id"):
            used.setdefault(ev, []).append(name)
        for c in cards:
            ev = c.f("evidence_id").strip()
            row = (evidence or {}).get(ev)
            if row is not None and row["status"].strip() != "ok":
                warns.append(("2.2", "%s 用的 %s 状态是 %s：要本轮用户确认或点名过" % (c.slot, ev, row["status"].strip())))
    for ev, names in sorted(used.items()):
        if len(names) > 1:
            fails.append(("E-1", "证据方案 %s 用了不止一次：%s" % (ev, ", ".join(names))))

    for tag in ("S", "P"):
        count = {}
        for t, name, cards in units:
            if t == tag:
                for sc in ids(cards, "scene_id"):
                    count.setdefault(sc, []).append(name)
        for sc, names in sorted(count.items()):
            if len(names) > 2:
                fails.append(("E-3", "场景 %s 在%s里用了 %d 次：%s，最多两次" %
                              (sc, "副图" if tag == "S" else " A+ ", len(names), ", ".join(names))))
    subs = [u for u in units if u[0] == "S"]
    for a, b in zip(subs, subs[1:]):
        same = set(ids(a[2], "scene_id")) & set(ids(b[2], "scene_id"))
        if same:
            fails.append(("E-3", "相邻两张副图 %s 和 %s 用同一个场景 %s" % (a[1], b[1], ", ".join(sorted(same)))))
    sub_scene = {}
    for t, name, cards in subs:
        for c in cards:
            sub_scene[c.f("selling_point")] = (name, c.f("scene_id").strip())
    for t, name, cards in units:
        if t != "P":
            continue
        for c in cards:
            s = sub_scene.get(c.f("selling_point"))
            if s and s[1] == c.f("scene_id").strip():
                warns.append(("E-3", "%s 和副图 %s 讲同一事实 %s，场景都是 %s；能换就换" %
                              (c.slot, s[0], c.f("selling_point"), s[1])))

    pet_units = [(name, ids(cards, "pet_id")) for t, name, cards in units if ids(cards, "pet_id")]
    m = len(pet_units)
    if m >= 4:
        count = {}
        for name, pets in pet_units:
            for pid in pets:
                count.setdefault(pid, []).append(name)
        if len(count) < 2:
            fails.append(("K-1", "%d 张有宠物的图全是同一只宠物 %s" % (m, ", ".join(count))))
        cap = ceil_half(m)
        for pid, names in sorted(count.items()):
            if len(names) > cap:
                fails.append(("K-1", "宠物 %s 出现在 %d 张图里（%s），最多 %d 张" % (pid, len(names), ", ".join(names), cap)))

    count = {}
    for t, name, cards in units:
        for eid in ids(cards, "expression_id"):
            count.setdefault(eid, []).append(name)
    for eid, names in sorted(count.items()):
        if len(names) > 2:
            fails.append(("K-2", "表情 %s 用了 %d 次：%s，最多两次" % (eid, len(names), ", ".join(names))))
    for a, b in zip(subs, subs[1:]):
        same = set(ids(a[2], "expression_id")) & set(ids(b[2], "expression_id"))
        if same:
            fails.append(("K-2", "相邻两张副图 %s 和 %s 用同一个表情 %s" % (a[1], b[1], ", ".join(sorted(same)))))

    def has_face(cards):
        for c in cards:
            row = (pools or {}).get("people", {}).get(c.f("person_id").strip())
            if row and row["shown"].strip() in FACE_SHOWN:
                return True
        return False

    used_refs = {}
    for t, name, cards in units:
        owners = list(cards)
        screen = ts.by_slot.get(name)
        if screen is not None and screen not in owners:
            owners.append(screen)
        seen = set()
        for c in owners:
            for slot in ("anchor", "expression", "layout"):
                ref = c.refs.get(slot, "").split("|")[0].strip()
                if ref and ref.lower() != "none" and ref not in seen:
                    seen.add(ref)
                    used_refs.setdefault(ref, []).append(name)
    for ref, names in sorted(used_refs.items()):
        if len(names) > 2:
            fails.append(("K-5", "案例 %s 用了 %d 次：%s，最多两次" % (ref.split("/")[-1], len(names), ", ".join(names))))

    stories = []
    for t, name, cards in units:
        text = " ".join(c.f("story") for c in cards if not c.is_none("story"))
        if text:
            stories.append((name, words(text)))
    for i, (a, wa) in enumerate(stories):
        for b, wb in stories[i + 1:]:
            sim = jaccard(wa, wb)
            if sim >= 0.5:
                warns.append(("K-4", "%s 和 %s 的故事相似度 %.2f：换一个时刻、人物或情绪" % (a, b, sim)))

    if len(subs) >= 5 and not any(has_face(u[2]) for u in subs):
        fails.append(("K-3", "副图有 %d 张，没有一张是有人物出镜的情景（只出手不算）" % len(subs)))
    aplus = [u for u in units if u[0] == "P"]
    if len(ts.screens) >= 4 and not any(has_face(u[2]) for u in aplus):
        fails.append(("K-3", "A+ 有 %d 屏，没有一屏是有人物出镜的情景（只出手不算）" % len(ts.screens)))
    return fails, warns


def set_rules(ts, views, strict, evidence=None, pools=False):
    """Return (fails, warns). Each item is (rule_id, message)."""
    fails, warns = [], []
    if strict and pools:
        f2, w2 = pool_rules(ts, evidence, pools if isinstance(pools, dict) else None)
        fails += f2
        warns += w2
    out = fails if strict else warns

    def get(card, key):
        return card.f(key) if card is not None else ""

    # ---------------- S rules
    subs = ts.subs
    n = len(subs)
    if n:
        facts = [c.f("selling_point") for c in subs if not c.is_none("selling_point")]
        dup = sorted({f for f in facts if facts.count(f) > 1})
        if dup:
            out.append(("S-1", "同一个事实做了不止一张副图：%s" % ", ".join(dup)))
        cams = [c.f("camera") for c in subs]
        for a, b in zip(subs, subs[1:]):
            if a.f("camera") == b.f("camera"):
                out.append(("S-2", "相邻两张副图机位相同：%s 和 %s 都是 %s" % (a.slot, b.slot, a.f("camera"))))
        if cams.count("eye_level") > 1:
            out.append(("S-2", "eye_level 用了 %d 张，最多一张" % cams.count("eye_level")))
        if n >= 4:
            if not any(c in OVERHEAD for c in cams):
                out.append(("S-2", "副图里没有俯拍（down_45 或 top_down）"))
            if cams.count("low_angle") < 2:
                out.append(("S-2", "low_angle 只有 %d 张，至少两张" % cams.count("low_angle")))
    if n and strict:
        shots = [c.f("shot_size") for c in subs]
        distinct = len(set(shots))
        need = 3 if n >= 5 else (2 if n >= 3 else 1)
        if distinct < need:
            fails.append(("S-3", "副图只用了 %d 种景别（%s），至少 %d 种" % (distinct, ", ".join(sorted(set(shots))), need)))
        cap = max(2, int(math.ceil(n / 3.0)))
        for s in sorted(set(shots)):
            if shots.count(s) > cap:
                fails.append(("S-3", "景别 %s 用了 %d 张，最多 %d 张" % (s, shots.count(s), cap)))
        if n >= 4:
            if not CLOSE_SHOTS & set(shots):
                fails.append(("S-3", "副图里没有 close 或 extreme_close"))
            if not FAR_SHOTS & set(shots):
                fails.append(("S-3", "副图里没有 full 或 wide"))
        for a, b in zip(subs, subs[1:]):
            if a.f("shot_size") == b.f("shot_size"):
                fails.append(("S-3", "相邻两张副图景别相同：%s 和 %s 都是 %s" % (a.slot, b.slot, a.f("shot_size"))))
        lights = [c.f("light_setup") for c in subs]
        need = 3 if n >= 5 else (2 if n >= 3 else 1)
        if len(set(lights)) < need:
            fails.append(("S-4", "副图只用了 %d 种光型，至少 %d 种" % (len(set(lights)), need)))
        for l in sorted(set(lights)):
            if lights.count(l) > ceil_half(n):
                fails.append(("S-4", "光型 %s 用了 %d 张，最多 %d 张" % (l, lights.count(l), ceil_half(n))))
        inters = [c.f("interaction") for c in subs]
        for it in sorted(set(inters)):
            if inters.count(it) > 2:
                fails.append(("S-5", "互动 %s 用了 %d 张，最多两张" % (it, inters.count(it))))
        acting = sum(1 for i in inters if i != "product_only")
        if acting < ceil_half(n):
            fails.append(("S-5", "有人手或宠物动作的副图只有 %d 张，至少 %d 张" % (acting, ceil_half(n))))
        fg = sum(1 for c in subs if not c.is_none("foreground"))
        if fg < n // 3:
            fails.append(("S-7", "有前景的副图 %d 张，至少 %d 张" % (fg, n // 3)))
    if n:
        areas = [c.f("text_area") for c in subs if not c.is_none("text_area")]
        if len(areas) >= 2:
            for a in sorted(set(areas)):
                if areas.count(a) > ceil_half(len(areas)):
                    out.append(("S-6", "文字位置 %s 用了 %d 张，最多 %d 张" % (a, areas.count(a), ceil_half(len(areas)))))

    # ---------------- A rules
    scr = ts.screens
    m = len(scr)
    if m:
        ed = ts.edition()
        if ed == "mixed":
            out.append(("A-0", "各屏 edition 不一致，整页只能用一个版本"))
        first, last = scr[0], scr[-1]
        if first.module != "scene":
            out.append(("A-1", "第一屏要是 scene，现在是 %s" % first.module))
        if strict:
            if first.f("beat") != "hook":
                fails.append(("A-1", "第一屏的 beat 要是 hook"))
            if first.module == "scene" and first.f("shot_size") not in ("close", "medium"):
                fails.append(("A-1", "开场屏景别要是 close 或 medium，现在是 %s" % first.f("shot_size")))
        if first.module == "scene" and first.is_none("pet"):
            out.append(("A-1", "开场屏要有宠物"))
        if last.module != "specs":
            out.append(("A-2", "最后一屏要是 specs，现在是 %s" % last.module))
        if strict and last.f("beat") != "close":
            fails.append(("A-2", "最后一屏的 beat 要是 close"))
        mods = [s.module for s in scr]
        run = 0
        for s in scr:
            run = run + 1 if s.module in SINGLE else 0
            if run == 3:
                out.append(("A-3", "单图屏（scene、number）连续超过两屏，到 %s 为止" % s.slot))
        for mod, cap in (("grid", 2), ("steps", 1), ("contrast", 1)):
            if mods.count(mod) > cap:
                out.append(("A-3", "%s 用了 %d 屏，最多 %d 屏" % (mod, mods.count(mod), cap)))
        if ed == "premium":
            comps = [s for s in scr if s.module in COMPOSITE]
            if len(comps) < 2:
                out.append(("A-4", "高级版组合模块只有 %d 屏（grid/steps/contrast），至少两屏" % len(comps)))
            strong = [s for s in comps if s.module == "contrast" or
                      (s.module == "grid" and len(ts.panels_of(s)) == 3)]
            if not strong:
                out.append(("A-4", "高级版至少要有一屏三格拼盘或前后对照"))
        else:
            for mod in ("number", "contrast"):
                if mod in mods:
                    out.append(("A-4", "标准版不能用 %s" % mod))
            if mods.count("scene") * 2 < m:
                out.append(("A-4", "标准版 scene 只有 %d 屏，至少占一半" % mods.count("scene")))
        if strict:
            mains = [ts.main_image(s) for s in scr]
            for (a, ma), (b, mb) in zip(zip(scr, mains), zip(scr[1:], mains[1:])):
                if ma is not None and mb is not None and get(ma, "shot_size") == get(mb, "shot_size"):
                    fails.append(("A-5", "相邻两屏主图景别相同：%s 和 %s 都是 %s" % (a.slot, b.slot, get(ma, "shot_size"))))
        for a, b in zip(scr, scr[1:]):
            if a.module == "scene" and b.module == "scene" and a.f("text_area") == b.f("text_area"):
                out.append(("A-6", "相邻两个 scene 文字同在 %s：%s 和 %s" % (a.f("text_area"), a.slot, b.slot)))
        imgs = ts.aplus_images()
        if strict and m >= 4 and not any(c.f("shot_size") == "extreme_close" for c in imgs):
            fails.append(("A-7", "A+ 里没有 extreme_close"))
        if ed == "premium":
            tones = [s.f("tone", "light") for s in scr]
            darks = tones.count("dark")
            if darks < 1 or darks > 2:
                out.append(("A-8", "高级版深色屏 %d 屏，要一到两屏" % darks))
            for a, b in zip(scr, scr[1:]):
                if a.f("tone", "light") == "dark" and b.f("tone", "light") == "dark":
                    out.append(("A-8", "深色屏相邻：%s 和 %s" % (a.slot, b.slot)))
            if not any(s.module == "number" or (s.module == "scene" and not s.is_none("hero_number")) for s in scr):
                out.append(("A-8", "高级版至少一屏巨型数字（number，或带强调数字的 scene）"))
        if strict:
            inters = [c.f("interaction") for c in imgs]
            for it in sorted(set(inters)):
                if inters.count(it) > 2:
                    fails.append(("A-9", "A+ 里互动 %s 用了 %d 张，最多两张" % (it, inters.count(it))))
            if m >= 5:
                mains = [ts.main_image(s) for s in scr]
                ls = {get(x, "light_setup") for x in mains if x is not None}
                if len(ls) < 3:
                    fails.append(("A-9", "各屏主图只用了 %d 种光型，至少三种" % len(ls)))
            beats = [s.f("beat") for s in scr]
            for i in range(len(beats) - 2):
                if beats[i] == beats[i + 1] == beats[i + 2]:
                    fails.append(("A-10", "节拍 %s 连续三屏（%s 起）" % (beats[i], scr[i].slot)))
            if m >= 4:
                for need in ("detail", "life"):
                    if need not in beats:
                        fails.append(("A-10", "整页没有 %s 节拍" % need))
        for fact, where in sorted(fact_counts(ts).items()):
            if len(where) > 2:
                out.append(("A-11", "事实 %s 在整页出现 %d 次（%s），最多两次" % (fact, len(where), ", ".join(where))))
        if m > 8:
            out.append(("A-12", "A+ 有 %d 屏，最多八屏" % m))
        elif ed == "premium" and m > 7:
            warns.append(("A-12", "高级版第 %d 屏：第三方资料称 Premium A+ 最多 7 个模块（未在 Amazon 官方页面核实）" % m))

    # ---------------- G rules
    if strict:
        imgs = subs + ts.aplus_images()
        seen = {}
        for c in imgs:
            key = (c.f("interaction"), pet_key(c), c.f("shot_size"), c.f("camera"))
            if key in seen:
                fails.append(("G-1", "%s 和 %s 的互动、宠物、景别、机位四项全相同（%s）" % (seen[key], c.slot, " / ".join(key))))
            else:
                seen[key] = c.slot
        by_fact = {c.f("selling_point"): c for c in subs if not c.is_none("selling_point")}
        for c in ts.aplus_images():
            s = by_fact.get(c.f("selling_point"))
            if s is None:
                continue
            diff = sum(1 for k in ("interaction", "shot_size", "camera") if s.f(k) != c.f(k))
            if diff < 2:
                fails.append(("G-2", "%s 和副图 %s 讲同一事实 %s，互动、景别、机位只有 %d 项不同，至少两项" %
                              (c.slot, s.slot, c.f("selling_point"), diff)))
    else:
        imgs = subs + ts.aplus_images()
        seen = {}
        for c in imgs:
            key = (legacy_interaction(c), pet_key(c), c.f("camera"))
            seen.setdefault(key, []).append(c.slot)
        for key, slots in sorted(seen.items()):
            if len(slots) > 1:
                warns.append(("G-1", "互动（推断）、宠物、机位相同：%s（%s）" % (", ".join(slots), " / ".join(key))))
        pairs = {}
        for c in imgs:
            pairs.setdefault((legacy_interaction(c), pet_key(c)), []).append(c.slot)
        for key, slots in sorted(pairs.items()):
            if len(slots) >= 3 and key[0] != "product_only":
                warns.append(("G-1", "同一种互动和宠物组合出现 %d 次：%s（%s）；只换机位名、不换画面" %
                              (len(slots), ", ".join(slots), " / ".join(key))))
        if scr and scr[0].module == "scene" and scr[0].f("camera") == "wide":
            warns.append(("A-1", "开场屏 %s 是远景 wide，宠物和产品都小，钩不住人" % scr[0].slot))
        for i, a in enumerate(imgs):
            for b in imgs[i + 1:]:
                if a.f("selling_point") == b.f("selling_point"):
                    continue
                sim = jaccard(words(a.f("evidence")), words(b.f("evidence")))
                if sim >= 0.4:
                    warns.append(("V2", "%s（%s）和 %s（%s）讲不同事实，画面证据相似度 %.2f" %
                                  (a.slot, a.f("selling_point"), b.slot, b.f("selling_point"), sim)))
        sides = []
        for c in imgs:
            m = re.search(r"\b(left|right)\b", c.f("light").lower())
            if m:
                sides.append(m.group(1))
        for side in ("left", "right"):
            if sides and sides.count(side) * 3 > len(sides) * 2:
                warns.append(("S-4", "%d 张写了光向的图里 %d 张的主光都从 %s 来" % (len(sides), sides.count(side), side)))
    return fails, warns


# ---------------------------------------------------------------- compile
def compile_card(card, pools=None):
    out = []
    image = card.is_image and card.f("card_version") == "2"
    for key, val, extra in card.items:
        if key in V2_ONLY_FIELDS:
            continue
        if key == "card_version":
            val = "1"
        if image:
            if key == "evidence":
                f = card.fields
                if not card.is_none("story"):
                    val = join_sentence("Story: %s" % card.f("story").strip().rstrip("."), val)
                bits = [SHOT_TEXT[f["shot_size"]].format(focus=focus_label(f["focus"])),
                        VIEW_TEXT[f["product_view"]],
                        ("The sharpest point of the picture is %s." % focus_label(f["focus"]))
                        if f["focus"] != "whole" else "The whole product is in sharp focus.",
                        CAMERA_TEXT[f["camera"]], REF_ONLY_TEXT]
                if card.refs.get("anchor", "").strip():
                    bits.append(CASE_CAMERA_TEXT)
                val = join_sentence(val, " ".join(bits))
            elif key == "light":
                val = join_sentence(val, LIGHT_TEXT[card.f("light_setup")])
            elif key == "scene":
                if not card.is_none("foreground"):
                    val = join_sentence(val, "Foreground: %s, soft and out of focus, framing the subject." % card.f("foreground"))
                style = (pools or {}).get("style_row")
                if style:
                    val = join_sentence(val, "Style: %s." % style["look_en"].strip().rstrip("."))
            elif key == "human_action" and pools and not card.is_none("person_id"):
                row = pools["people"].get(card.f("person_id").strip())
                if row:
                    val = join_sentence(val, "Person: %s." % row["look_en"].strip().rstrip("."))
                    mood = pools.get("moods", {}).get(card.f("person_mood_id").strip())
                    if mood:
                        val = join_sentence(val, "Mood: %s; not looking at the camera." % mood["look_en"].strip().rstrip("."))
            elif key == "pet_action" and pools and not card.is_none("expression_id"):
                looks = [pools["expressions"][e]["look_en"].strip().rstrip(".")
                         for e in pool_ids(card, "expression_id") if e in pools["expressions"]]
                if looks:
                    val = join_sentence(val, "Expression: %s." % "; ".join(looks))
        out.append("%s: %s" % (key, val) if val else "%s:" % key)
        out.extend(extra)
    return out


def emit_task(path, product, cards, pools=None):
    lines = ["UTA-TASK v1", "product: %s" % product, "cards: %d" % len(cards), ""]
    for c in cards:
        lines.append("=== %s ===" % c.path)
        lines.append("---")
        lines.extend(compile_card(c, pools))
        lines.append("---")
        lines.append("")
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def task_text_from(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if HEADER_RE.match(line.strip()):
            body = [l for l in lines[i:] if not l.strip().startswith("```")]
            return "\n".join(body) + "\n"
    return text


# ---------------------------------------------------------------- main
def run(task_path, emit=None, views_path=None, root=".", state=None, out=sys.stdout):
    def p(*a):
        print(*a, file=out)

    p("check_set %s  task=%s" % (VERSION, task_path))
    try:
        text = read_text(task_path)
        version, header, cards = parse_task(text)
    except (OSError, TaskError) as e:
        p("TASK ERROR: %s" % e)
        return 2
    product = header["product"]
    scope = header.get("scope", "full")
    p("version=v%d  product=%s  scope=%s  cards=%d" % (version, product, scope, len(cards)))

    if version == 1:
        p("LEGACY v1: 只给警告，不做 2.6 的硬检查。")
        for c in cards:
            for w in check_card_legacy(c):
                p("WARN %s: %s" % (c.slot, w))
        vpath = views_path or os.path.join(root, "products", product, "ref_views.csv")
        try:
            lviews = load_views(vpath) if os.path.exists(vpath) else None
        except TaskError as e:
            p("WARN [1.4] %s" % e)
            lviews = None
        _, warns = set_rules(TaskSet(cards), lviews, strict=False)
        for rid, msg in warns:
            p("WARN [%s] %s" % (rid, msg))
        if emit:
            d = os.path.dirname(emit)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(emit, "w", encoding="utf-8") as fh:
                fh.write(task_text_from(text))
            p("EMIT %s（v1 原样）  下一步：python tools/check_card.py --task %s" % (emit, emit))
        return 0

    vpath = views_path or os.path.join(root, "products", product, "ref_views.csv")
    try:
        views = load_views(vpath)
    except TaskError as e:
        p("TASK ERROR: %s" % e)
        return 2
    for r in views:
        if not r["checked"]:
            p("WARN [1.4] %s 的覆盖范围还没有人对照原图确认（checked 不是 yes）" % r["path"])
    try:
        pools = load_pools(root)
    except TaskError as e:
        p("TASK ERROR: %s" % e)
        return 2
    style_id = header.get("style", "").strip()
    if style_id not in pools["styles"]:
        p("TASK ERROR: 头部要写 style: 风格池 pools/styles.csv 里的编号（1.13），现在是「%s」" % style_id)
        return 2
    pools["style_row"] = pools["styles"][style_id]
    evidence = load_evidence(root, product)
    from copy_exceptions import load_claims, load_grants
    grants = load_grants(root, product)
    claims = load_claims(root, product)

    card_errs = {}
    for c in cards:
        errs = check_card_v2(c, views, pools, evidence, grants, claims)
        if errs:
            card_errs[c.slot] = errs
    # a module and its panels pass or fail together
    ts_now = TaskSet(cards)
    for s in ts_now.screens:
        if s.module == "scene":
            continue
        group = [s.slot] + ts_now.panels_of(s)
        bad = [g for g in group if g in card_errs]
        if bad:
            for g in group:
                if g in ts_now.by_slot and g not in card_errs:
                    card_errs[g] = ["同一模块的 %s 没通过，整组一起退回" % ", ".join(bad)]
    for c in cards:
        if c.slot in card_errs:
            p("FAIL %s" % c.path)
            for e in card_errs[c.slot]:
                p("     - %s" % e)
        else:
            p("OK   %s" % c.path)

    state = state or os.path.join(os.path.dirname(task_path) or ".", "task_full_v2.md")
    set_cards = cards
    run_set = True
    if scope == "patch":
        if os.path.exists(state):
            try:
                _, _, base = parse_task(read_text(state))
                merged = {c.slot: c for c in base}
                for c in cards:
                    merged[c.slot] = c
                set_cards = list(merged.values())
                p("PATCH: 合进上一次的整套 %s 再查 2.6" % state)
            except TaskError as e:
                p("WARN [2.8] 上一次的整套 %s 读不了（%s），跳过 2.6" % (state, e))
                run_set = False
        else:
            p("WARN [2.8] 没有上一次的整套 %s，跳过 2.6" % state)
            run_set = False

    fails, warns = (set_rules(TaskSet(set_cards), views, strict=True, evidence=evidence, pools=pools)
                    if run_set else ([], []))
    for rid, msg in fails:
        p("SET FAIL [%s] %s" % (rid, msg))
    for rid, msg in warns:
        p("WARN [%s] %s" % (rid, msg))
    if fails:
        p("SET FAIL：整份任务单退回，不出图（2.9）。")
        return 2

    if scope == "full":
        d = os.path.dirname(state)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(state, "w", encoding="utf-8") as fh:
            fh.write(task_text_from(text))

    ok_cards = [c for c in cards if c.slot not in card_errs]
    if emit:
        emit_task(emit, product, ok_cards, pools)
        p("EMIT %s（%d 张卡，已换成 card_version 1）  下一步：python tools/check_card.py --task %s"
          % (emit, len(ok_cards), emit))
    p("汇总：%d 张卡，OK %d，FAIL %d，SET FAIL 0" % (len(cards), len(ok_cards), len(card_errs)))
    return 1 if card_errs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="UTA Style v3.2 whole-set check and v2->v1 compiler")
    ap.add_argument("--task", required=True, help="outputs/task.md")
    ap.add_argument("--emit", help="where to write the card_version 1 task for check_card.py")
    ap.add_argument("--views", help="override products/<product>/ref_views.csv")
    ap.add_argument("--root", default=".", help="repository root (default: current directory)")
    ap.add_argument("--state", help="saved full task for scope: patch (default: <task dir>/task_full_v2.md)")
    args = ap.parse_args(argv)
    return run(args.task, args.emit, args.views, args.root, args.state)


if __name__ == "__main__":
    sys.exit(main())
