#!/usr/bin/env python3
"""L3 排版原型 + L4 事实白名单校验。

模型只应交付无字底图。本脚本用 Poppins 把 layout.json 里的文字画上去。
它不生成产品、宠物或场景，也不把测试底图当成 product_reference.png。

用法：
  python3 tools/layout_render.py --layout layout.json --out-dir DIR
      [--facts tools/facts.json] [--font-dir fonts/poppins]

校验失败时退出码为 1，不写 PNG。用法错误或底图打不开时退出码为 2。
成功时写出：
  *_master.png     在底图原始像素上排字，不放大底图
  *_upload.png     仅当底图正好是已记录母版尺寸时，单次缩小到上传尺寸
  *_report.json    字体解析、字号来源、未检查项

不能保证：
  - 产品外形。仓库没有 product_reference.png，本脚本不对照外形。
  - 表情、「能联想到」、错字以外的语义是否通顺。
  - 白名单只做短语覆盖和禁用词。若干已确认短语拼在一起，脚本不会判断这句是否因此变成新卖点。
  - 遮挡只比较 layout.json 的 avoid 矩形。没有矩形就不声称没有挡住产品。
  - 1600 宽标题用 92px（D2 / AGENTS §10.1.4）。副标题像素是 round(标题/2.5)，
    来自 UTA §6A.2 的约 2.5:1。AGENTS 表里的副标题仍是 44px。原型没有把 44 改成新规范。
  - A+ 文字放进上下各 20% 以外（UTA §6H.6 第16项）。AGENTS §10.2 的字顶 115px / 45px
    会落进这 20%。原型服从 §6H.6，并在报告里写明这一冲突。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FACTS = os.path.join(ROOT, "tools", "facts.json")
DEFAULT_FONTS = os.path.join(ROOT, "fonts", "poppins")

UPLOAD = {
    "S": (1600, 2000),
    "AP-PC": (1464, 600),
    "AP-M": (600, 450),
    "G1": (2000, 2000),
}
# 只接受文档里已经写过的母版/高清目标，不另造尺寸。
MASTER = {
    "S": (2000, 2500),
    "AP-PC": (2928, 1200),
    "AP-M": (1200, 900),
}
TITLE_PX = {"S": 92, "AP-PC": 52, "AP-M": 36}
LEFT_INSET = {"S": 32, "AP-PC": 120, "AP-M": 80}
HERO_COLOR = (244, 122, 33, 255)  # #F47A21，UTA §6
LIGHT_TEXT = (15, 36, 56, 255)  # #0F2438，UTA §6
DARK_TEXT = (255, 255, 255, 255)
CARD_FILL = (255, 255, 255, 230)  # 白色 alpha 约 0.90，落在 UTA §7 的 85%–95%


class LayoutError(Exception):
    pass


def fold_dashes(text):
    return (
        text.replace("\u2011", "-")
        .replace("\u2010", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def font_path(font_dir, weight):
    return os.path.join(font_dir, f"Poppins-{weight}.ttf")


def load_poppins(font_dir, weight, size):
    path = font_path(font_dir, weight)
    if not os.path.isfile(path):
        raise LayoutError(f"缺少 {path}。拒绝改用其他字体家族。")
    font = ImageFont.truetype(path, size=size)
    family, style = font.getname()
    if family != "Poppins":
        raise LayoutError(f"{path} 解析为 {family} {style}，不是 Poppins。拒绝静默替换。")
    return font, {
        "path": os.path.relpath(path, ROOT),
        "family": family,
        "style": style,
        "requested_weight": weight,
        "size_px": size,
        "silent_substitution": False,
    }


def english_words(line):
    return re.findall(r"[A-Za-z0-9<>]+", line)


def check_lines(text, label):
    lines = text.split("\n")
    if len(lines) > 2:
        raise LayoutError(f"{label} 超过 2 行（UTA §6A.2）")
    for line in lines:
        words = english_words(line)
        if len(words) > 5:
            raise LayoutError(f"{label} 有一行超过 5 个英文单词（UTA §6A.2）：{line}")
    return lines


def whitelist_field(text, phrases, forbidden):
    folded = fold_dashes(text)
    for item in forbidden:
        term = fold_dashes(item["term"])
        if term and term.lower() in folded.lower():
            raise LayoutError(
                f"文案含禁用词「{item['term']}」（{item['section']}）：{item['quote']}"
            )
    leftover = folded
    for phrase in sorted((fold_dashes(item["text"]) for item in phrases), key=len, reverse=True):
        if phrase:
            leftover = leftover.replace(phrase, " ")
    compact = re.sub(r"[\s\.,;:：、，。！!?？/|+\-–—]+", "", leftover)
    if compact:
        raise LayoutError(f"文案不在事实白名单内，剩余：{compact}")


def collect_uncertain(text, phrases):
    notes = []
    folded = fold_dashes(text)
    for item in phrases:
        if item.get("uncertain") and fold_dashes(item["text"]) in folded:
            notes.append({"text": item["text"], "section": item["section"], "uncertain": item["uncertain"]})
    return notes


def hero_ok(hero, pairs):
    number = fold_dashes(str(hero.get("number", "")).strip())
    unit = fold_dashes(str(hero.get("unit", "")).strip())
    for pair in pairs:
        if fold_dashes(pair["number"]) == number and fold_dashes(pair["unit"]) == unit:
            return pair
    raise LayoutError(f"hero「{number} {unit}」不是 UTA 已出现的数字和单位组合")


def ink_box(font, text, x, y):
    bbox = font.getbbox(text)
    return (x + bbox[0], y + bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])


def overlaps(box, rect):
    x, y, w, h = box
    rx, ry, rw, rh = rect
    return x < rx + rw and x + w > rx and y < ry + rh and y + h > ry


def inside(box, rect):
    x, y, w, h = box
    x0, y0, x1, y1 = rect
    return x >= x0 - 1e-6 and y >= y0 - 1e-6 and x + w <= x1 + 1e-6 and y + h <= y1 + 1e-6


def safe_rect(slot, width, height, scale):
    if slot == "S":
        inset = LEFT_INSET["S"] * scale
        # 底边 22% 来自 UTA §6A.3「占画面高度的 15–22%」。
        # 不额外发明顶边距；顶边就是画面上沿。左右用 AGENTS §10.1.4 的 32px。
        return (inset, 0, width - inset, 0.22 * height)
    if slot in ("AP-PC", "AP-M"):
        # UTA §6H.6 第16项：上下各 20% 不放重要内容。
        return (0, 0.20 * height, width, 0.80 * height)
    raise LayoutError(f"没有安全区定义：{slot}")


def layout_blocks(spec, fonts, scale):
    title_px = TITLE_PX[spec["slot"]] * scale
    subtitle_px = max(1, round(title_px / 2.5))
    hero_scale = float(spec["hero_scale"])
    if not 2.0 <= hero_scale <= 3.5:
        raise LayoutError("hero_scale 必须在 UTA §6A.2 的 2.0–3.5 内，原型不另选一个标准倍数")
    hero_px = max(1, round(title_px * hero_scale))
    unit_px = max(1, round(hero_px * 0.5))
    gap = 0.5 * subtitle_px
    title_font, title_meta = load_poppins(spec["font_dir"], "Bold", title_px)
    sub_font, sub_meta = load_poppins(spec["font_dir"], "Regular", subtitle_px)
    fonts_used = {"title": title_meta, "subtitle": sub_meta}
    placed = []
    y = 0
    title_width = 0
    for line in spec["title"].split("\n"):
        width, height, _ascent = measure(title_font, line)
        placed.append({"text": line, "font": title_font, "fill": spec["text_fill"], "x": 0, "y": y, "role": "title"})
        title_width = max(title_width, width)
        y += height
    y += gap
    sub_width = 0
    for line in spec["subtitle"].split("\n"):
        width, height, _ascent = measure(sub_font, line)
        placed.append({"text": line, "font": sub_font, "fill": spec["text_fill"], "x": 0, "y": y, "role": "subtitle"})
        sub_width = max(sub_width, width)
        y += height
    text_right = max(title_width, sub_width)
    block_bottom = y
    if spec["hero"] is not None:
        hero_font, hero_meta = load_poppins(spec["font_dir"], "ExtraBold", hero_px)
        unit_font, unit_meta = load_poppins(spec["font_dir"], "Bold", unit_px)
        fonts_used["hero"] = hero_meta
        fonts_used["unit"] = unit_meta
        number = str(spec["hero"]["number"])
        unit = str(spec["hero"].get("unit") or "")
        nw, nh, na = measure(hero_font, number)
        hx = text_right + gap
        placed.append({"text": number, "font": hero_font, "fill": HERO_COLOR, "x": hx, "y": 0, "role": "hero"})
        if unit:
            _uw, uh, ua = measure(unit_font, unit)
            unit_y = na - ua
            placed.append({"text": unit, "font": unit_font, "fill": HERO_COLOR, "x": hx + nw, "y": unit_y, "role": "unit"})
        block_bottom = max(block_bottom, nh)
    if spec["cards"]:
        card_font, card_meta = load_poppins(spec["font_dir"], "SemiBold", subtitle_px)
        fonts_used["card"] = card_meta
        cy = block_bottom + gap
        for line in spec["cards"]:
            _w, height, _a = measure(card_font, line)
            placed.append({
                "text": line,
                "font": card_font,
                "fill": spec["text_fill"],
                "x": 0,
                "y": cy,
                "role": "card",
                "card_bg": True,
            })
            cy += height + gap * 0.25
    return placed, fonts_used, {
        "title_px_at_upload": TITLE_PX[spec["slot"]],
        "title_px_rendered": title_px,
        "subtitle_px_rendered": subtitle_px,
        "subtitle_rule": "round(标题像素 / 2.5)，UTA §6A.2；不是 AGENTS 表内 44px",
        "hero_scale": hero_scale,
        "hero_px_rendered": hero_px if spec["hero"] is not None else None,
        "unit_px_rendered": unit_px if spec["hero"] is not None else None,
        "unit_rule": "数字高度的 0.5，UTA §6B.2 第3条「约一半」",
        "gap_rule": "副标题字高的 0.5，取 UTA §6A.2 间距 0.5–0.8 的下限，并复用为标题与 hero 的水平间距",
    }


def measure(font, text):
    ascent, descent = font.getmetrics()
    bbox = font.getbbox(text or " ")
    width = max(1, bbox[2] - bbox[0])
    return width, ascent + descent, ascent


def union_boxes(placed):
    boxes = []
    for item in placed:
        boxes.append(ink_box(item["font"], item["text"], item["x"], item["y"]))
    x0 = min(box[0] for box in boxes)
    y0 = min(box[1] for box in boxes)
    x1 = max(box[0] + box[2] for box in boxes)
    y1 = max(box[1] + box[3] for box in boxes)
    return boxes, (x0, y0, x1, y1)


def render(spec):
    if spec["slot"] not in UPLOAD:
        raise LayoutError("slot 只能是 G1、S、AP-PC、AP-M")
    if "avoid" not in spec:
        raise LayoutError("必须提供 avoid（可以是空数组）。没有这个字段就不能声称做过遮挡检查。")
    if not isinstance(spec["avoid"], list):
        raise LayoutError("avoid 必须是矩形数组")
    bg = Image.open(spec["bg"]).convert("RGBA")
    upload = UPLOAD[spec["slot"]]
    master = MASTER.get(spec["slot"])
    if bg.size == upload:
        scale = 1
        kind = "upload_native"
    elif master and bg.size == master:
        scale = master[0] / upload[0]
        kind = "documented_master"
    else:
        raise LayoutError(
            f"底图是 {bg.size[0]}×{bg.size[1]}，不是 {spec['slot']} 的上传尺寸 {upload[0]}×{upload[1]}"
            + (f" 或已记录母版 {master[0]}×{master[1]}" if master else "")
            + "。不拉伸，也不把其他尺寸当成母版。"
        )
    if spec["slot"] == "G1":
        if any((spec.get("title"), spec.get("subtitle"), spec.get("hero"), spec.get("cards"))):
            raise LayoutError("G1 白底主图不排文字（UTA §5A，AGENTS §9.1）")
        raise LayoutError("G1 没有需要渲染的文字。白底检查请用 grade_check.py --slot G1。")

    title = str(spec.get("title") or "")
    subtitle = str(spec.get("subtitle") or "")
    cards = list(spec.get("cards") or [])
    hero = spec.get("hero")
    if not title or not subtitle:
        raise LayoutError("S 与 A+ 必须同时有长标题和副标题（UTA §6H.4）")
    check_lines(title, "标题")
    check_lines(subtitle, "副标题")
    for line in cards:
        if "\n" in line:
            raise LayoutError("每张卡片文字只放一行")
        check_lines(line, "卡片")
    layers = ["title", "subtitle"]
    if hero:
        layers.append("hero")
    if cards:
        layers.append("cards")
    if len(layers) > 3:
        raise LayoutError(f"文字层为 {layers}，超过 UTA §6B.2 的 3 层。hero 和卡片不能同时出现。")
    facts = load_json(spec["facts"])
    phrases = facts["allowed_phrases"]
    forbidden = facts["forbidden"]
    uncertain = []
    for label, text in (("标题", title), ("副标题", subtitle)):
        whitelist_field(text, phrases, forbidden)
        uncertain.extend(collect_uncertain(text, phrases))
    for line in cards:
        whitelist_field(line, phrases, forbidden)
        uncertain.extend(collect_uncertain(line, phrases))
    hero_pair = None
    if hero:
        hero_pair = hero_ok(hero, facts["hero_pairs"])
        whitelist_field(f"{hero.get('number', '')} {hero.get('unit', '')}", phrases, forbidden)
    anchor = spec.get("anchor") or "top-left"
    if anchor not in ("top-left", "top-center"):
        raise LayoutError("anchor 只实现了 UTA §6A.3 的左上和顶部居中")
    mode = spec.get("mode") or "light"
    if mode not in ("light", "dark"):
        raise LayoutError("mode 只能是 light 或 dark")
    if "hero_scale" not in spec:
        raise LayoutError("必须写 hero_scale。未写时原型不擅自选取 2–3.5 之间的某个倍数。没有 hero 时仍要写，供记录；有卡片、没有 hero 时写 2.0 即可。")
    spec = dict(spec)
    spec["title"] = title
    spec["subtitle"] = subtitle
    spec["cards"] = cards
    spec["hero"] = hero
    spec["text_fill"] = DARK_TEXT if mode == "dark" else LIGHT_TEXT
    placed, fonts_used, size_notes = layout_blocks(spec, fonts_used := {}, scale)
    _boxes, (x0, y0, x1, y1) = union_boxes(placed)
    safe = safe_rect(spec["slot"], bg.size[0], bg.size[1], scale)
    if anchor == "top-left":
        dx = LEFT_INSET[spec["slot"]] * scale - x0
        dy = safe[1] - y0
    else:
        dx = ((safe[0] + safe[2]) / 2) - ((x0 + x1) / 2)
        dy = safe[1] - y0
    moved = []
    ink = []
    for item in placed:
        item = dict(item)
        item["x"] += dx
        item["y"] += dy
        box = ink_box(item["font"], item["text"], item["x"], item["y"])
        if item.get("card_bg"):
            pad = max(4, round(8 * scale))
            box = (box[0] - pad, box[1] - pad, box[2] + 2 * pad, box[3] + 2 * pad)
        if not inside(box, (0, 0, bg.size[0], bg.size[1])):
            raise LayoutError(f"{item['role']} 画出画面：{box}")
        if not inside(box, safe):
            raise LayoutError(f"{item['role']} 超出安全区 {safe}：{box}")
        for rect in spec["avoid"]:
            region = (rect["x"], rect["y"], rect["w"], rect["h"])
            if overlaps(box, region):
                raise LayoutError(f"{item['role']} 与标记区域相交：{region}")
        moved.append(item)
        ink.append({"role": item["role"], "box": [round(v, 2) for v in box]})
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)
    for item in moved:
        if item.get("card_bg"):
            box = ink_box(item["font"], item["text"], item["x"], item["y"])
            pad = max(4, round(8 * scale))
            draw.rounded_rectangle(
                (box[0] - pad, box[1] - pad, box[0] + box[2] + pad, box[1] + box[3] + pad),
                radius=max(2, round(8 * scale)),
                fill=CARD_FILL,
            )
        draw.text((item["x"], item["y"]), item["text"], font=item["font"], fill=item["fill"])
    master = canvas.convert("RGB")
    report = {
        "pass": True,
        "slot": spec["slot"],
        "bg": spec["bg"],
        "bg_size": list(bg.size),
        "canvas_kind": kind,
        "scale_from_upload": scale,
        "fonts": fonts_used,
        "sizes": size_notes,
        "layers": layers,
        "anchor": anchor,
        "mode": mode,
        "safe_rect": [round(v, 2) for v in safe],
        "ink": ink,
        "avoid_rectangles": len(spec["avoid"]),
        "occlusion_check": "CHECKED_MARKED_RECTANGLES" if spec["avoid"] else "NOT_CHECKED_NO_MARKED_REGION",
        "hero_source": None if hero_pair is None else {"section": hero_pair["section"], "quote": hero_pair["quote"]},
        "uncertain_terms": uncertain,
        "resample_count_for_upload": 0 if kind == "upload_native" else 1,
        "upload_size": list(upload),
        "limitations": [
            "不对照 product_reference.png；该文件不在仓库，外形检查保持阻塞。",
            "不判断表情和「能联想到」。",
            "遮挡只看 avoid 矩形，不做像素级产品分割。",
            "卡片只是文字衬底，不是 §6H.3 要求的带场景图的卡片。",
            "副标题像素由 2.5:1 换算，AGENTS §10.1.4 的 44px 仍保留在规范里，二者未用新数字消解。",
            "A+ 使用 §6H.6 的上下 20% 禁区，因此不采用 §10.2 的 115px / 45px 字顶。",
        ],
    }
    return master, upload, kind, report


def save_outputs(master, upload, kind, report, out_dir, stem):
    os.makedirs(out_dir, exist_ok=True)
    master_path = os.path.join(out_dir, f"{stem}_master.png")
    upload_path = os.path.join(out_dir, f"{stem}_upload.png")
    report_path = os.path.join(out_dir, f"{stem}_report.json")
    master.save(master_path, format="PNG")
    if kind == "upload_native":
        master.save(upload_path, format="PNG")
    else:
        resized = master.resize(tuple(upload), Image.Resampling.LANCZOS)
        resized.save(upload_path, format="PNG")
    report["files"] = {"master": master_path, "upload": upload_path, "report": report_path}
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def build_spec(payload, facts, font_dir):
    spec = dict(payload)
    spec["facts"] = facts
    spec["font_dir"] = font_dir
    return spec


def main(argv=None):
    parser = argparse.ArgumentParser(description="UTA 排版原型")
    parser.add_argument("--layout", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--facts", default=DEFAULT_FACTS)
    parser.add_argument("--font-dir", default=DEFAULT_FONTS)
    args = parser.parse_args(argv)
    try:
        payload = load_json(args.layout)
        spec = build_spec(payload, args.facts, args.font_dir)
        master, upload, kind, report = render(spec)
        stem = os.path.splitext(os.path.basename(args.layout))[0]
        report = save_outputs(master, upload, kind, report, args.out_dir, stem)
    except LayoutError as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"pass": False, "error": f"无法完成排版：{exc}"}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"pass": True, "report": report["files"], "fonts": report["fonts"], "occlusion_check": report["occlusion_check"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
