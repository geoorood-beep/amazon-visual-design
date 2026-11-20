"""Photo and size sheet (xlsx) for the person holding the product: angle photos, body size, accessory photos and sizes.

    python tools/photo_sheet.py build --form outputs/<产品>/product_form_vNN.json   (or the form's .html, or a draft)
    python tools/photo_sheet.py read <filled.xlsx>

build makes outputs/<产品>/photo_sheet_vNN.xlsx from a product form (UTA_STYLE.md 1.15): one row per photo slot,
the body's size rows, one row per part. read takes the filled sheet back: it pulls out every pasted photo
(floating pictures, Excel "place in cell", WPS "embed in cell"), saves them in outputs/<产品>/photo_sheet_in_NN/
and prints a UTA-PRODUCT v1 block that 3.9 writes into the product card, exactly like the form's.
Rows carry their slot or part id in a hidden "key" column, so deleted or added rows are read correctly.
"""
import argparse
import base64
import datetime
import io
import json
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

import product_form as pf

ROOT = pf.ROOT
MAGIC = "UTA-PHOTO-SHEET v1"
GUIDE, PHOTOS, SIZE, PARTS, META = "填写说明", "多角度照片", "主机尺寸", "配件", "_uta"
PHOTO_COLS = ["序号", "角度", "怎么拍", "示例（已有的照片或参考图）", "你的照片（贴在这里）", "拍了吗", "照片文件名", "备注", "key"]
PART_COLS = ["序号", "配件名", "关系类型", "包装里几件", "示例（已有的参考图）", "你的照片（贴在这里）", "长", "宽", "高或直径",
             "线长（有线的填）", "单位", "装在哪、跟谁连着", "照片文件名", "备注", "key"]
SIZE_COLS = ["项目", "怎么量", "数值", "单位", "示例值（别的产品，只看格式）", "备注", "key"]
EXTRA_SLOTS = [("flatlay", "包装里全部东西平铺", "把包装里所有东西摊开拍一张")]
TYPES = ["组成部件", "可拆件", "耗材", "随附配件", "宿主产品", "外部物品"]
NOUN = {"L": "length", "W": "depth", "H": "height"}
TO_MM = {"mm": 1, "cm": 10, "m": 1000, "in": 25.4, "ft": 304.8}
EXAMPLE = {"mm": (300, 220, 180), "cm": (30, 22, 18), "m": (1.5, 1.2, 1)}
NEW_ROWS = 5
HEADER_ROW = 3

FONT = "Arial"
INPUT = PatternFill("solid", fgColor="FFF2CC")
NOTE = PatternFill("solid", fgColor="EEEEEE")
HEAD = PatternFill("solid", fgColor="1F2630")
SUB = PatternFill("solid", fgColor="DDE5EE")
BOX = Border(*(Side(style="thin", color="BBBBBB"),) * 4)
WRAP = Alignment(wrap_text=True, vertical="center")
CENTER = Alignment(wrap_text=True, vertical="center", horizontal="center")
BODY = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
BLUE = Font(name=FONT, size=10, color="0000FF", italic=True)
GUESS = Font(name=FONT, size=10, color="555555", italic=True)
GREY = Font(name=FONT, size=9, color="888888")

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "rd": "http://schemas.microsoft.com/office/spreadsheetml/2017/richdata",
}
R_EMBED = "{%s}embed" % NS["r"]
R_ID = "{%s}id" % NS["r"]


class SheetError(Exception):
    pass


def num_text(x):
    """Numbers as the form writes them: 310, 1.68, 1.2 (JavaScript's default)."""
    s = repr(round(float(x), 2))
    return s[:-2] if s.endswith(".0") else s


def col_letter(i):
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


# ---------- build ----------

def load_form(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.lower().endswith((".html", ".htm")):
        if pf.OPEN not in text:
            raise SheetError("%s has no product form data" % path)
        start = text.index(pf.OPEN) + len(pf.OPEN)
        text = text[start:text.index(pf.CLOSE, start)]
    form = json.loads(text)
    if not form.get("product"):
        raise SheetError("the form has no 'product'")
    return form


def normalize_size(size):
    """Older forms leave out units, nouns and ratios; fill them the way the form's script does."""
    size = json.loads(json.dumps(size or {}))
    dims = size.setdefault("dims", {})
    for k, d in dims.items():
        d.setdefault("unit", "mm")
        d.setdefault("noun", NOUN.get(k, k))
    for e in size.setdefault("extra", []):
        e.setdefault("unit", "mm")
    if not size.get("ratios"):
        size["ratios"] = [r for r in (["L", "H"], ["W", "H"]) if r[0] in dims and r[1] in dims]
    return size


def image_bytes(root, src):
    if not src:
        return None
    if src.startswith("data:"):
        return base64.b64decode(src.split(",", 1)[1])
    path = os.path.join(root, src)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def thumb(root, src, edge=118):
    """A small JPEG for the sheet, or None when the image is missing or unreadable."""
    data = image_bytes(root, src)
    if not data:
        return None
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.thumbnail((edge * 2, edge * 2))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=78)
        buf.seek(0)
        img = XLImage(buf)
    except Exception:
        return None
    ratio = img.width / float(img.height)
    img.width, img.height = (edge, int(edge / ratio)) if ratio >= 1 else (int(edge * ratio), edge)
    return img


def style(c, font=BODY, fill=None, align=WRAP):
    c.font, c.alignment, c.border = font, align, BOX
    if fill:
        c.fill = fill
    return c


def put(ws, row, col, value=None, font=BODY, fill=None, align=WRAP):
    c = ws.cell(row=row, column=col)
    if value is not None:
        c.value = value
    return style(c, font, fill, align)


def table(ws, title, sub, cols, widths):
    ws["A1"], ws["A2"] = title, sub
    ws["A1"].font = Font(name=FONT, size=15, bold=True)
    ws["A2"].font = Font(name=FONT, size=10, color="555555")
    for i, label in enumerate(cols, 1):
        put(ws, HEADER_ROW, i, label, Font(name=FONT, size=10, bold=True, color="FFFFFF"), HEAD, CENTER)
        ws.column_dimensions[col_letter(i)].width = widths[i - 1]
    ws.column_dimensions[col_letter(len(cols))].hidden = True
    ws.freeze_panes = "C%d" % (HEADER_ROW + 1)


def guide_sheet(wb, form):
    ws = wb.active
    ws.title = GUIDE
    ws.column_dimensions["A"].width = 110
    hint = (form.get("size") or {}).get("hint", "量外轮廓；高从桌面量到最高的固定部分。")
    lines = [
        ("%s 多角度照片和尺寸填写表" % (form.get("title") or form["product"]).split(" · ")[0], "title"),
        ("给拿着实物、卷尺和手机的人填。填完把这个文件和原始照片一起发回；没填完也可以先发，填了多少用多少。", "sub"),
        ("", None), ("颜色说明", "h"),
        ("黄色格子：要你填的。照片贴在这里，数字和文字写在这里。", "input"),
        ("灰色格子：说明和示例图，不用改。", "note"),
        ("蓝字那一行：示例，只是让你看格式，可以删。", "blue"),
        ("灰色斜体字：AI 先推的内容（比如配件名），不对直接改；整行不对就删掉这一行。", "guess"),
        ("", None), ("怎么拍", "h"),
        ("· 白色或浅灰的素色背景，柔光，避开直射灯：亮面和金属很容易反光。", None),
        ("· 平视：手机和产品中间一样高，正对那一面。俯拍：手机在产品正上方。", None),
        ("· 一张只拍一个角度，产品放在画面中间，四周留一点空。", None),
        ("· 规格照（旁边放尺子、旁边放一只手）是给 AI 定大小用的，拍清楚比拍好看重要。", None),
        ("", None), ("怎么量", "h"),
        ("· 单位看「单位」那一格，可以改；拿不准就量两次，写中间的数。", None),
        ("· " + hint, None),
        ("· 配件平放量最长、最宽、最厚；有线的，把线拉直量长度。", None),
        ("", None), ("怎么把照片贴进格子", "h"),
        ("· 新版 Excel：点黄色格子 → 插入 → 图片 → 放置在单元格中。", None),
        ("· WPS：插入 → 图片 → 嵌入单元格。", None),
        ("· 旧版 Excel 或 Numbers：把照片拖到黄色格子上面，左上角落在格子里就行。", None),
        ("· 表里的照片可能被压缩，原始照片请一起发，文件名写在「照片文件名」那一列。", None),
        ("", None), ("填完以后", "h"),
        ("· 把这个文件和原始照片一起发给 Grok 或 Codex：照片按角度存进产品的 photos 文件夹，尺寸写进产品卡的「物理边界」"
         "和 Geometry，配件写进部件清单。", None),
        ("· 不要改最右边隐藏的那一列，也不要改表名：读表靠它们。", None),
    ]
    looks = {"title": Font(name=FONT, size=16, bold=True), "sub": Font(name=FONT, size=10, color="555555"),
             "h": Font(name=FONT, size=12, bold=True), "blue": BLUE, "guess": GUESS}
    fills = {"h": SUB, "input": INPUT, "note": NOTE}
    for i, (text, kind) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=text)
        c.alignment, c.font = WRAP, looks.get(kind, BODY)
        if kind in fills:
            c.fill = fills[kind]
        if kind in ("input", "note", "blue", "guess"):
            c.border = BOX


def photo_sheet(wb, root, form):
    ws = wb.create_sheet(PHOTOS)
    table(ws, "多角度照片", "每个角度一张。有示例图的照着拍；没有示例的看「怎么拍」那一列。", PHOTO_COLS,
          [6, 18, 34, 22, 24, 9, 18, 26, 8])
    slots = [dict(s) for s in form.get("photos", [])]
    have = set(s["slot"] for s in slots)
    slots += [{"slot": k, "label": label, "img": "", "tip": tip} for k, label, tip in EXTRA_SLOTS if k not in have]
    sample = next((s for s in slots if thumb(root, s.get("img"))), None)
    r = HEADER_ROW + 1
    if sample:
        shown = "IMG_0001.jpg" if sample["img"].startswith("data:") else os.path.basename(sample["img"])
        values = ["示例", sample["label"], "（这一行是示例，看格式用，可以删）", None, None, "✓",
                  shown, "照片贴进「你的照片」，文件名写在旁边"]
        for i, v in enumerate(values, 1):
            put(ws, r, i, v, BLUE, INPUT if i >= 5 else NOTE, CENTER if i in (1, 6) else WRAP)
        put(ws, r, len(PHOTO_COLS), "example")
        for col in (4, 5):
            ws.add_image(thumb(root, sample["img"]), "%s%d" % (col_letter(col), r))
        ws.row_dimensions[r].height = 96
        r += 1
    for n, s in enumerate(slots, 1):
        src = s.get("src") or ""
        if s.get("img") and src == "实拍":
            how = "已经有实拍（左边那张）。想换一张更清楚的就重拍，不换就空着"
        elif s.get("tip"):
            how = s["tip"]
        elif s.get("img"):
            how = "现在只有%s，没有实拍：照这个角度补拍一张" % (src or "参考图")
        else:
            how = "没有这个角度的照片：补拍一张"
        put(ws, r, 1, n, BODY, NOTE, CENTER)
        put(ws, r, 2, s["label"], BOLD, NOTE)
        put(ws, r, 3, how, BODY, NOTE)
        img = thumb(root, s.get("img"))
        put(ws, r, 4, None if img else "暂无示例", GREY, NOTE, CENTER)
        for col in range(5, 9):
            put(ws, r, col, None, BODY, INPUT, CENTER if col == 6 else WRAP)
        put(ws, r, len(PHOTO_COLS), s["slot"])
        if img:
            ws.add_image(img, "D%d" % r)
        ws.row_dimensions[r].height = 96
        r += 1
    dv = DataValidation(type="list", formula1='"✓,✗,不适用"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("F%d:F%d" % (HEADER_ROW + 1, r - 1))
    return slots


def unit_factor(cell):
    return 'IF(%s="cm",10,IF(%s="m",1000,IF(%s="in",25.4,1)))' % (cell, cell, cell)


def size_sheet(wb, form):
    ws = wb.create_sheet(SIZE)
    size = form.get("size") or {}
    dims, extras = size.get("dims") or {}, size.get("extra") or []
    table(ws, "主机尺寸", size.get("hint", "") + " 只填黄色格子；下面「自动算」的部分不用填。", SIZE_COLS,
          [16, 34, 12, 8, 18, 34, 8])
    r, rows = HEADER_ROW + 1, {}
    units = DataValidation(type="list", formula1='"mm,cm,m"', allow_blank=False)
    ws.add_data_validation(units)
    for i, (k, d) in enumerate(dims.items()):
        u = d.get("unit", "mm")
        how = d.get("label", "").split("：", 1)[-1]
        put(ws, r, 1, d.get("short", k) + " " + k, BOLD, NOTE)
        put(ws, r, 2, how, BODY, NOTE)
        put(ws, r, 3, None, BODY, INPUT, CENTER)
        put(ws, r, 4, u, BODY, INPUT, CENTER)
        units.add("D%d" % r)
        put(ws, r, 5, EXAMPLE.get(u, EXAMPLE["mm"])[min(i, 2)], BLUE, NOTE, CENTER)
        put(ws, r, 6, None, BODY, INPUT)
        put(ws, r, 7, "dim:" + k)
        rows[k] = r
        r += 1
    for e in extras:
        u = e.get("unit", "mm")
        put(ws, r, 1, e.get("short") or e.get("label"), BOLD, NOTE)
        put(ws, r, 2, e.get("label", "") + "（选填）", BODY, NOTE)
        put(ws, r, 3, None, BODY, INPUT, CENTER)
        put(ws, r, 4, u, BODY, NOTE, CENTER)
        put(ws, r, 5, None, BLUE, NOTE, CENTER)
        put(ws, r, 6, None, BODY, INPUT)
        put(ws, r, 7, "extra:" + e["key"])
        r += 1
    put(ws, r, 1, "大小参照", BOLD, NOTE)
    put(ws, r, 2, "和一样大家都知道大小的东西比，一句话", BODY, NOTE)
    put(ws, r, 3, None, BODY, INPUT)
    put(ws, r, 4, None, BODY, NOTE)
    put(ws, r, 5, "高度大约到成年猫站着时的肩膀", BLUE, NOTE, CENTER)
    put(ws, r, 6, None, BODY, INPUT)
    put(ws, r, 7, "size_ref")
    ws.row_dimensions[r].height = 30
    r += 2
    put(ws, r, 1, "自动算（不用填）", Font(name=FONT, size=11, bold=True), SUB)
    for col in range(2, 7):
        put(ws, r, col, None, BODY, SUB)
    r += 1
    for a, b in size.get("ratios") or []:
        if a not in rows or b not in rows:
            continue
        ca, cb = "C%d" % rows[a], "C%d" % rows[b]
        fa, fb = unit_factor("D%d" % rows[a]), unit_factor("D%d" % rows[b])
        put(ws, r, 1, "%s / %s" % (dims[a].get("short", a), dims[b].get("short", b)), BOLD, NOTE)
        put(ws, r, 2, "换算成同一单位再除", BODY, NOTE)
        c = put(ws, r, 3, '=IF(AND(ISNUMBER(%s),ISNUMBER(%s),N(%s)>0),ROUND(%s*%s/(%s*%s),2),"")'
                % (ca, cb, cb, ca, fa, cb, fb), BODY, None, CENTER)
        c.number_format = "0.00"
        for col in (4, 5, 6):
            put(ws, r, col, None, BODY, NOTE)
        r += 1
    if rows:
        tests = ['AND(ISNUMBER(C{0}),OR(C{0}*{1}<10,C{0}*{1}>5000))'.format(rows[k], unit_factor("D%d" % rows[k]))
                 for k in rows]
        first, last = min(rows.values()), max(rows.values())
        put(ws, r, 1, "单位检查", BOLD, NOTE)
        put(ws, r, 2, "数字明显太小或太大时提醒", BODY, NOTE)
        put(ws, r, 3, '=IF(COUNT(C%d:C%d)=0,"",IF(OR(%s),"有个数看起来不对：看看单位，再量一次","看起来正常"))'
            % (first, last, ",".join(tests)), BODY)
        ws.merge_cells("C%d:F%d" % (r, r))
    return ws


def parts_sheet(wb, root, form):
    ws = wb.create_sheet(PARTS)
    table(ws, "配件", "每件一行：贴照片、量尺寸。配件名和关系类型是 AI 推的（灰色斜体），不对直接改；包装里没有的整行删掉，"
          "漏了的写进下面的空行。", PART_COLS, [6, 22, 11, 9, 22, 22, 8, 8, 9, 10, 7, 30, 16, 22, 8])
    parts = form.get("parts") or []
    if parts and not parts[0].get("parent"):
        parts = parts[1:]
    parts = [p for p in parts if p.get("type") != "外部物品"]
    r = HEADER_ROW + 1
    example = ["示例", "清洁刷（示例，不是这款的配件）", "随附配件", 1, None, None, 150, 20, 20, None, "mm",
               "单独放在包装里", "IMG_0801.jpg", "这一行是示例，可以删"]
    for i, v in enumerate(example, 1):
        put(ws, r, i, v, BLUE, INPUT if i >= 3 else NOTE, CENTER if i in (1, 3, 4, 7, 8, 9, 10, 11) else WRAP)
    put(ws, r, len(PART_COLS), "example")
    ws.row_dimensions[r].height = 30
    rows = [(p["id"], p) for p in parts] + [("new%d" % k, None) for k in range(1, NEW_ROWS + 1)]
    for n, (key, p) in enumerate(rows, 1):
        r += 1
        put(ws, r, 1, n, BODY, NOTE, CENTER)
        put(ws, r, 2, p and p.get("name"), GUESS, INPUT)
        put(ws, r, 3, p and p.get("type"), GUESS, INPUT, CENTER)
        put(ws, r, 4, None, BODY, INPUT, CENTER)
        img = thumb(root, (p.get("imgs") or [""])[0], 110) if p else None
        put(ws, r, 5, "暂无示例" if p and not img else None, GREY, NOTE, CENTER)
        for col in range(6, 11):
            put(ws, r, col, None, BODY, INPUT, CENTER)
        put(ws, r, 11, "mm", BODY, INPUT, CENTER)
        put(ws, r, 12, p and p.get("where"), GUESS, INPUT)
        put(ws, r, 13, None, BODY, INPUT)
        put(ws, r, 14, None, BODY, INPUT)
        put(ws, r, len(PART_COLS), key)
        if img:
            ws.add_image(img, "E%d" % r)
        ws.row_dimensions[r].height = 90
    kinds = DataValidation(type="list", formula1='"%s"' % ",".join(TYPES), allow_blank=True)
    units = DataValidation(type="list", formula1='"mm,cm,m"', allow_blank=True)
    for dv, col in ((kinds, "C"), (units, "K")):
        ws.add_data_validation(dv)
        dv.add("%s%d:%s%d" % (col, HEADER_ROW + 1, col, r))
    ws["C%d" % HEADER_ROW].comment = Comment(
        "组成部件：长在产品上；可拆件：会拆下来洗、加东西；耗材：定期换；随附配件：包装里另附；"
        "宿主产品：卖配件时它要装上去的那台产品；外部物品：水、粮、宠物这类道具。", "UTA")
    return parts


def meta_sheet(wb, form, slots, parts, form_path):
    ws = wb.create_sheet(META)
    ws.sheet_state = "hidden"
    size = form.get("size") or {}
    rows = [
        ("magic", MAGIC), ("product", form["product"]), ("form", form_path),
        ("generated", datetime.date.today().isoformat()),
        ("slots", json.dumps([{"slot": s["slot"], "label": s["label"], "replace": bool(s.get("img"))} for s in slots],
                             ensure_ascii=False)),
        ("parts", json.dumps([{k: p.get(k, "") for k in ("id", "name", "type", "where")} for p in parts],
                             ensure_ascii=False)),
        ("size", json.dumps({k: size.get(k) for k in ("dims", "extra", "ratios")}, ensure_ascii=False)),
    ]
    for i, (k, v) in enumerate(rows, 1):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)


def cache_blank_formulas(path, sheet_title):
    """Previewers that do not recalculate show a formula's cached value; give the empty sheet blanks, not 0."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin:
        target = sheet_parts(zin).get(sheet_title)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == target:
                    xml = data.decode("utf-8")
                    xml = re.sub(r'<c ([^>]*?)(?: t="[^"]*")?([^>]*)><f>(.*?)</f>(?:<v>.*?</v>|<v\s*/>)?</c>',
                                 lambda m: '<c %s%s t="str"><f>%s</f><v></v></c>' % (m.group(1), m.group(2), m.group(3)),
                                 xml, flags=re.S)
                    data = xml.encode("utf-8")
                zout.writestr(item, data)
    os.replace(tmp, path)


def next_path(root, product, stem, ext):
    folder = os.path.join(root, "outputs", product)
    n = 1
    while os.path.exists(os.path.join(folder, "%s%02d%s" % (stem, n, ext))):
        n += 1
    return os.path.join(folder, "%s%02d%s" % (stem, n, ext))


def build(root, form_path, out_path=None):
    form = load_form(form_path)
    form["size"] = normalize_size(form.get("size"))
    out_path = out_path or next_path(root, form["product"], "photo_sheet_v", ".xlsx")
    if os.path.exists(out_path):
        raise SheetError("%s exists; sheets are never overwritten" % out_path)
    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    guide_sheet(wb, form)
    slots = photo_sheet(wb, root, form)
    size_sheet(wb, form)
    parts = parts_sheet(wb, root, form)
    meta_sheet(wb, form, slots, parts, pf.shown_path(form_path, root))
    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)
    cache_blank_formulas(out_path, SIZE)
    return out_path, len(slots), len(parts)


# ---------- read: pictures ----------

def rels_of(z, part):
    path = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    if path not in z.namelist():
        return {}
    out = {}
    for rel in ET.fromstring(z.read(path)).iter("{%s}Relationship" % NS["rel"]):
        t = rel.get("Target", "")
        out[rel.get("Id")] = t.lstrip("/") if t.startswith("/") else posixpath.normpath(
            posixpath.join(posixpath.dirname(part), t))
    return out


def sheet_parts(z):
    """Sheet title -> worksheet part name."""
    rels = rels_of(z, "xl/workbook.xml")
    book = ET.fromstring(z.read("xl/workbook.xml"))
    return {s.get("name"): rels.get(s.get(R_ID)) for s in book.iter("{%s}sheet" % NS["main"])}


def drawing_pictures(z, sheet_part):
    """Floating pictures: (row, first col, last col, media part), rows and columns 1-based."""
    xml = z.read(sheet_part).decode("utf-8")
    m = re.search(r'<(?:\w+:)?drawing [^>]*?r:id="([^"]+)"', xml)
    if not m:
        return []
    drawing = rels_of(z, sheet_part).get(m.group(1))
    if not drawing or drawing not in z.namelist():
        return []
    media, out = rels_of(z, drawing), []
    for anchor in ET.fromstring(z.read(drawing)):
        frm = anchor.find("{%s}from" % NS["xdr"])
        blip = anchor.find(".//{%s}blip" % NS["a"])
        if frm is None or blip is None or blip.get(R_EMBED) not in media:
            continue
        fc, fr = int(frm.findtext("{%s}col" % NS["xdr"])), int(frm.findtext("{%s}row" % NS["xdr"]))
        to = anchor.find("{%s}to" % NS["xdr"])
        tc, tr = (int(to.findtext("{%s}col" % NS["xdr"])), int(to.findtext("{%s}row" % NS["xdr"]))) if to is not None else (fc, fr)
        out.append((fr + 1 + (tr - fr) // 2, fc + 1, tc + 1, media[blip.get(R_EMBED)]))
    return out


def rich_value_media(z):
    """Excel "place in cell": value-metadata index (1-based vm) -> media part."""
    names = z.namelist()
    if "xl/metadata.xml" not in names or "xl/richData/rdrichvalue.xml" not in names:
        return {}
    meta = ET.fromstring(z.read("xl/metadata.xml"))
    future = [int(b.get("i")) for b in meta.iter("{%s}rvb" % NS["rd"])]
    value_meta = []
    block = meta.find("{%s}valueMetadata" % NS["main"])
    for bk in (list(block) if block is not None else []):
        rc = bk.find("{%s}rc" % NS["main"])
        value_meta.append(int(rc.get("v")) if rc is not None else None)
    keys = []
    if "xl/richData/rdrichvaluestructure.xml" in names:
        for s in ET.fromstring(z.read("xl/richData/rdrichvaluestructure.xml")).iter("{%s}s" % NS["rd"]):
            keys.append([k.get("n") for k in s.iter("{%s}k" % NS["rd"])])
    values = []
    for rv in ET.fromstring(z.read("xl/richData/rdrichvalue.xml")).iter("{%s}rv" % NS["rd"]):
        vs = [v.text for v in rv.iter("{%s}v" % NS["rd"])]
        s = int(rv.get("s", "0"))
        names_ = keys[s] if s < len(keys) else []
        pos = names_.index("_rvRel:LocalImageIdentifier") if "_rvRel:LocalImageIdentifier" in names_ else 0
        values.append(int(vs[pos]) if pos < len(vs) and (vs[pos] or "").isdigit() else None)
    rel_part = next((n for n in names if n.startswith("xl/richData/") and n.lower().endswith("richvaluerel.xml")), None)
    if not rel_part:
        return {}
    ids = [r.get(R_ID) for r in ET.fromstring(z.read(rel_part)) if r.get(R_ID)]
    media = rels_of(z, rel_part)
    out = {}
    for vm in range(1, len(value_meta) + 1):
        f = value_meta[vm - 1]
        rv = future[f] if f is not None and f < len(future) else vm - 1
        rel = values[rv] if rv < len(values) else None
        if rel is not None and rel < len(ids) and ids[rel] in media:
            out[vm] = media[ids[rel]]
    return out


def wps_media(z):
    """WPS "embed in cell": picture name (ID_...) -> media part."""
    if "xl/cellimages.xml" not in z.namelist():
        return {}
    media, out = rels_of(z, "xl/cellimages.xml"), {}
    for pic in ET.fromstring(z.read("xl/cellimages.xml")).iter("{%s}pic" % NS["xdr"]):
        nv = pic.find(".//{%s}cNvPr" % NS["xdr"])
        blip = pic.find(".//{%s}blip" % NS["a"])
        if nv is not None and blip is not None and blip.get(R_EMBED) in media:
            out[nv.get("name")] = media[blip.get(R_EMBED)]
    return out


CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)


def sheet_pictures(path):
    """Sheet title -> list of (row, first col, last col, filename, bytes) for every picture, however it was pasted."""
    with zipfile.ZipFile(path) as z:
        rich, wps, out = rich_value_media(z), wps_media(z), {}
        for title, part in sheet_parts(z).items():
            if not part or part not in z.namelist():
                continue
            found = drawing_pictures(z, part)
            for m in CELL_RE.finditer(z.read(part).decode("utf-8")):
                col = 0
                for ch in m.group(1):
                    col = col * 26 + ord(ch) - 64
                row, attrs, body = int(m.group(2)), m.group(3), m.group(4) or ""
                vm = re.search(r'\bvm="(\d+)"', attrs)
                if vm and int(vm.group(1)) in rich:
                    found.append((row, col, col, rich[int(vm.group(1))]))
                pic = re.search(r'DISPIMG\((?:&quot;|")([^"&]+)', body)
                if pic and pic.group(1) in wps:
                    found.append((row, col, col, wps[pic.group(1)]))
            out[title] = [(r, a, b, posixpath.basename(p), z.read(p)) for r, a, b, p in found if p in z.namelist()]
    return out


# ---------- read: values ----------

NUM_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|毫米|厘米|米)?\s*$", re.I)
UNIT_WORDS = {"毫米": "mm", "厘米": "cm", "米": "m"}


def number(value, unit, label, warnings):
    """(value, unit) from a cell; a typed unit like '31cm' wins. Text that is not a number is reported, not used."""
    if value is None or value == "":
        return None, unit
    if isinstance(value, (int, float)):
        return float(value), unit
    m = NUM_RE.match(str(value))
    if not m:
        warnings.append("%s 写的「%s」不是数字，没用" % (label, value))
        return None, unit
    typed = (m.group(2) or "").lower()
    return float(m.group(1)), UNIT_WORDS.get(m.group(2), typed) or unit


def text(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v not in (None, "") else ""


def rows_by_key(ws):
    header = [text(c.value) for c in ws[HEADER_ROW]]
    if "key" not in header:
        raise SheetError("sheet %s has no key column; use a sheet made by photo_sheet.py build" % ws.title)
    cols = {name: i + 1 for i, name in enumerate(header) if name}
    out = []
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        key = text(ws.cell(row=r, column=cols["key"]).value)
        if key and key != "example":
            out.append((key, r, {name: ws.cell(row=r, column=c).value for name, c in cols.items()}))
    return cols, out


def pictures_at(pictures, row, col):
    return [p for p in pictures if p[0] == row and p[1] <= col <= p[2]]


def read_meta(wb):
    if META not in wb.sheetnames:
        raise SheetError("not a photo sheet: no %s sheet (make one with photo_sheet.py build)" % META)
    ws = wb[META]
    meta = {text(ws.cell(row=r, column=1).value): ws.cell(row=r, column=2).value for r in range(1, ws.max_row + 1)}
    if meta.get("magic") != MAGIC:
        raise SheetError("not a %s sheet" % MAGIC)
    for k in ("slots", "parts", "size"):
        meta[k] = json.loads(meta.get(k) or "null") or ({} if k == "size" else [])
    return meta


def geometry(dims, ratios, extras, got):
    """The form's geo(): the same English lines the product form writes."""
    lines, bits, rs = [], [], []
    mm = {k: got[k][0] * TO_MM.get(got[k][1], 1) for k in got if k in dims and got[k][1] in TO_MM}
    for k, d in dims.items():
        if k in got:
            bits.append(("" if bits else "about ") + "%s %s %s" % (num_text(got[k][0]), got[k][1], d.get("en", "")))
    if bits:
        lines.append(", ".join(bits))
    for a, b in ratios or []:
        if mm.get(a) and mm.get(b):
            rs.append("%s about %s times the %s" % (dims[a].get("noun", a), num_text(mm[a] / mm[b]), dims[b].get("noun", b)))
    if rs:
        lines.append("; ".join(rs))
    for e in extras:
        if e["key"] in got and e.get("en"):
            lines.append(e["en"].replace("{v}", num_text(got[e["key"]][0])))
    return lines, mm


def save_pictures(out_dir, name, pics, root):
    saved = []
    for i, (_r, _a, _b, filename, data) in enumerate(pics):
        ext = os.path.splitext(filename)[1].lower() or ".png"
        path = os.path.join(out_dir, "%s%s%s" % (name, "" if i == 0 else "_%d" % (i + 1), ext))
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        saved.append(pf.shown_path(path, root))
    return saved


def read(root, xlsx, out_dir=None):
    wb = load_workbook(xlsx)
    meta = read_meta(wb)
    product = meta["product"]
    pictures = sheet_pictures(xlsx)
    out_dir = out_dir or next_path(root, product, "photo_sheet_in_", "")
    warnings, notes, changed = [], [], 0

    # photos
    labels = {s["slot"]: s for s in meta["slots"]}
    cols, rows = rows_by_key(wb[PHOTOS])
    photos, missing = [], []
    for key, r, v in rows:
        label = labels.get(key, {}).get("label", key)
        pics = pictures_at(pictures.get(PHOTOS, []), r, cols["你的照片（贴在这里）"])
        name = text(v.get("照片文件名"))
        how = "（替换）" if labels.get(key, {}).get("replace") else "（新增）"
        if pics:
            saved = save_pictures(out_dir, key, pics, root)
            photos.append("%s=%s%s%s" % (key, saved[0], how, "；原图 " + name if name else ""))
            photos += ["%s=%s（同一角度的另一张）" % (key, p) for p in saved[1:]]
        elif name:
            photos.append("%s=%s%s（表里没贴图，原图另发）" % (key, name, how))
        elif text(v.get("拍了吗")) in ("✗", "不适用"):
            missing.append("%s %s" % (label, text(v.get("拍了吗"))))
        if text(v.get("备注")):
            notes.append("%s 备注：%s" % (label, text(v.get("备注"))))
    changed += len(photos)

    # size
    size = meta["size"]
    dims, extras = size.get("dims") or {}, size.get("extra") or []
    cols, rows = rows_by_key(wb[SIZE])
    got, size_ref = {}, ""
    for key, r, v in rows:
        if key == "size_ref":
            size_ref = text(v.get("数值"))
        elif ":" in key:
            kind, k = key.split(":", 1)
            unit = text(v.get("单位")) or "mm"
            val, unit = number(v.get("数值"), unit, text(v.get("项目")) or k, warnings)
            if val:
                got[k] = (val, unit)
        if text(v.get("备注")):
            notes.append("%s 备注：%s" % (text(v.get("项目")) or key, text(v.get("备注"))))
    geo, mm = geometry(dims, size.get("ratios"), extras, got)
    for k, v in mm.items():
        if not 10 <= v <= 5000:
            warnings.append("%s %s %s 看起来不对：单位是不是填错了" % (dims[k].get("short", k), num_text(got[k][0]), got[k][1]))
    ex = ["%s %s %s" % (e.get("short") or e.get("label"), num_text(got[e["key"]][0]), got[e["key"]][1])
          for e in extras if e["key"] in got]
    if any(k in got for k in dims):
        size_line = "size: " + " × ".join(
            "%s %s" % (d.get("short", k), "%s %s" % (num_text(got[k][0]), got[k][1]) if k in got else "未填")
            for k, d in dims.items()) + ("；" + "；".join(ex) if ex else "")
    elif ex:
        size_line = "size: %s未填；%s" % ("".join(d.get("short", k) for k, d in dims.items()), "；".join(ex))
    else:
        size_line = "size: 未填（照参考图比例画，总览标「比例推定」）"
    ratio = ["%s/%s %s" % (dims[a].get("short", a), dims[b].get("short", b), num_text(mm[a] / mm[b]))
             for a, b in size.get("ratios") or [] if mm.get(a) and mm.get(b)]
    changed += len(got) + bool(size_ref)

    # parts
    cols, rows = rows_by_key(wb[PARTS])
    seen, agree, edits, sizes = set(), [], [], []
    original = {p["id"]: p for p in meta["parts"]}
    for key, r, v in rows:
        name, kind, where = text(v.get("配件名")), text(v.get("关系类型")), text(v.get("装在哪、跟谁连着"))
        pics = pictures_at(pictures.get(PARTS, []), r, cols["你的照片（贴在这里）"])
        unit = text(v.get("单位")) or "mm"
        dim_vals = []
        for col in ("长", "宽", "高或直径"):
            val, unit = number(v.get(col), unit, "%s 的%s" % (name or key, col), warnings)
            dim_vals.append(val)
        cable, _ = number(v.get("线长（有线的填）"), unit, "%s 的线长" % (name or key), warnings)
        count = text(v.get("包装里几件"))
        p = original.get(key)
        if p is None and not (name or kind or where or pics or any(dim_vals) or cable or count):
            continue
        seen.add(key)
        label = "%s %s" % (key, name) if p else "新增 %s" % (name or "（没写名称）")
        if p:
            lines = []
            if kind and kind != p.get("type"):
                lines.append("  %s: 类型 %s → %s" % (key, p.get("type") or "未写", kind))
            if not name:
                lines.append("  %s: 不对 → 名称被清空了（原来是「%s」），按包装里没有处理" % (key, p.get("name")))
            elif name != text(p.get("name")):
                lines.append("  %s: 不对 → 名称改成「%s」" % (key, name))
            if where and where != text(p.get("where")):
                lines.append("  %s: 不对 → 装在哪改成「%s」" % (key, where))
            if lines:
                edits.append("\n".join(lines))
            else:
                agree.append(key)
        else:
            edits.append("  新增: %s → %s" % (name or "（没写名称）", "；".join(
                x for x in (kind or "类型没选", where) if x)))
        bits = []
        if any(dim_vals):
            bits.append("%s %s" % (" × ".join(num_text(x) if x else "?" for x in dim_vals), unit))
        if cable:
            bits.append("线长 %s %s" % (num_text(cable), unit))
        if count:
            bits.append("包装里 %s 件" % count)
        if pics:
            fname = "part_%s" % key
            saved = save_pictures(out_dir, fname, pics, root)
            bits.append("照片 " + "、".join(saved))
        elif text(v.get("照片文件名")):
            bits.append("照片 %s（原图另发）" % text(v.get("照片文件名")))
        if bits:
            sizes.append("- %s: %s" % (label, "；".join(bits)))
        if text(v.get("备注")):
            notes.append("%s 备注：%s" % (label, text(v.get("备注"))))
    for key, p in original.items():
        if key not in seen:
            edits.append("  %s: 不对 → 表里删掉了这一行（原来是「%s」），按包装里没有处理" % (key, p.get("name")))
    changed += len(edits) + len(sizes)

    lines = ["UTA-PRODUCT v1", "product: " + product, "form: " + pf.shown_path(os.path.abspath(xlsx), root),
             "draft: " + text(meta.get("generated")), "source: photo_sheet（照片尺寸表，只有尺寸、照片和配件）",
             "changed: %d%s" % (changed, "" if changed else "（全部按 AI 草稿）"), ""]
    if original or edits:
        lines.append("parts: 同意 %s%s" % (" ".join(agree) or "无", "；要改 %d" % len(edits) if edits else ""))
        lines += edits
    if sizes:
        lines.append("part_sizes:")
        lines += sizes
    lines.append(size_line)
    if ratio:
        lines.append("ratio: " + "；".join(ratio))
    if size_ref:
        lines.append("size_ref: " + size_ref)
    if geo:
        lines.append("geometry_prompt:")
        lines += ["- " + g for g in geo]
    lines.append("photos: " + ("；".join(photos) if photos else "没有新照片"))
    if missing:
        lines.append("photos_missing: " + "；".join(missing))
    if notes:
        lines.append("notes: " + "；".join(notes))
    if warnings:
        lines.append("warnings: " + "；".join(warnings))
    block = "\n".join(lines)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "uta_product.txt"), "w", encoding="utf-8") as fh:
        fh.write(block + "\n")
    return block, out_dir, warnings


# ---------- cli ----------

def main(argv=None, root=ROOT, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Photo and size sheet (xlsx): build it, read it back.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--form", required=True, help="product form JSON or HTML (outputs/<产品>/product_form_vNN.*)")
    p.add_argument("--out")
    p = sub.add_parser("read")
    p.add_argument("xlsx")
    p.add_argument("--out-dir")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "build":
            path, n_slots, n_parts = build(root, args.form, args.out)
            out.write("SHEET %s  photo rows %d  part rows %d\n" % (pf.shown_path(path, root), n_slots, n_parts))
            out.write("Send it to whoever has the product; nothing waits on it.\n")
        else:
            block, folder, _ = read(root, args.xlsx, args.out_dir)
            out.write(block + "\n\nSAVED %s\n" % pf.shown_path(folder, root))
            out.write("Next: write it into the product card by UTA_STYLE.md 3.9 (same as a UTA-PRODUCT from the form).\n")
    except (SheetError, OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        out.write("ERROR %s\n" % e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
