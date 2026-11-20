"""Photo and size sheet (xlsx): one sheet, one row for the product body and one row per part.

    python tools/photo_sheet.py build --form outputs/<产品>/product_form_vNN.json   (or the form's .html, or a draft)
    python tools/photo_sheet.py read <filled.xlsx>

Each row takes five photos (front, back, left, right, top); other angles are left to the AI. The body row and
every part row also take length, width and height. Everything is optional. build makes
outputs/<产品>/photo_sheet_vNN.xlsx from a product form (UTA_STYLE.md 1.15). read takes the filled sheet back:
it pulls out every pasted photo (floating pictures, Excel "place in cell", WPS "embed in cell"), saves them in
outputs/<产品>/photo_sheet_in_NN/ and prints a UTA-PRODUCT v1 block that 3.9 writes into the product card,
exactly like the form's. Rows carry their id in a hidden "key" column, so deleted or added rows read correctly.
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
MAGIC = "UTA-PHOTO-SHEET v2"
SHEET, META = "填写表", "_uta"
VIEWS = [("正面", "front"), ("背面", "rear"), ("左侧", "side_left"), ("右侧", "side_right"), ("俯视（上）", "top_down")]
COLS = ["序号", "名称", "关系类型", "现有参考", *[v[0] for v in VIEWS], "长", "宽", "高", "单位", "备注", "key"]
WIDTHS = [6, 20, 10, 15, 15, 15, 15, 15, 15, 7, 7, 7, 7, 24, 8]
TYPES = ["组成部件", "可拆件", "耗材", "随附配件", "宿主产品", "外部物品"]
NOUN = {"L": "length", "W": "depth", "H": "height"}
TO_MM = {"mm": 1, "cm": 10, "m": 1000, "in": 25.4, "ft": 304.8}
NEW_ROWS = 5
HEADER_ROW = 4
BODY_KEY = "body"
SKIP_KEYS = ("guide", "example")
DIRECTIONS = {"长": "左右", "宽": "前后", "高": "上下"}
# What each photo shows of the three sizes, so a row's numbers can be checked against its own photos.
VIEW_SHOWS = {"正面": "看得到 长 × 高", "背面": "看得到 长 × 高", "左侧": "看得到 宽 × 高", "右侧": "看得到 宽 × 高",
              "俯视（上）": "看得到 长 × 宽"}
EXAMPLES = [
    {"名称": "立式滤芯（示例，不是这款的配件）", "关系类型": "可拆件", "长": 40, "宽": 40, "高": 120, "单位": "mm",
     "备注": "装在机器上的配件，按装好时的方向量：从主体正面看左右 40、前后 40、上下 120。它竖着插，竖的那一边写在「高」"},
    {"名称": "清洁刷（示例，不是这款的配件）", "关系类型": "随附配件", "长": 150, "宽": 20, "高": 20, "单位": "mm",
     "备注": "不装在机器上的配件，平放在桌上量：最长那一边朝左右，写在「长」150；前后 20；上下（厚）20"},
]

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


def col_of(label):
    return COLS.index(label) + 1


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
    if not dims:
        dims.update({k: {"short": s, "en": e} for k, s, e in (("L", "长", "long"), ("W", "宽", "deep"), ("H", "高", "tall"))})
    for k, d in dims.items():
        d.setdefault("unit", "mm")
        d.setdefault("noun", NOUN.get(k, k))
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


def thumb(root, src, edge=100):
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


def put(ws, row, col, value=None, font=BODY, fill=None, align=WRAP):
    c = ws.cell(row=row, column=col)
    if value is not None:
        c.value = value
    c.font, c.alignment, c.border = font, align, BOX
    if fill:
        c.fill = fill
    return c


def front_face(form):
    """Which face counts as the front, in the user's words: the water-window side when the body has one."""
    body = (form.get("parts") or [{}])[0]
    if "水位窗" in body.get("where", "") + body.get("visible", ""):
        return "有水位窗的那一面"
    return "正面平视照片里朝镜头的那一面"


def body_of(form):
    """(name, reference image, parts) where parts leaves out the body itself and props."""
    parts = form.get("parts") or []
    body = parts[0] if parts and not parts[0].get("parent") else None
    rest = [p for p in (parts[1:] if body else parts) if p.get("type") != "外部物品"]
    front = next((s.get("img") for s in form.get("photos", []) if s.get("slot") == "front" and s.get("img")), "")
    name = (body or {}).get("name") or (form.get("title") or form["product"]).split(" · ")[0]
    return name, front or ((body or {}).get("imgs") or [""])[0], rest


def body_rule(size):
    """'长：左右最宽处；宽：前后最深处；高：桌面到盆沿。量外轮廓……' from the category's size definition."""
    labels = "；".join(d.get("label", "") for d in list((size.get("dims") or {}).values())[:3] if d.get("label"))
    hint = size.get("hint", "量外轮廓。")
    return ("%s。%s " % (labels, hint)) if labels else hint + " "


def item_row(ws, root, r, n, key, name, kind, ref, unit, guess=True):
    put(ws, r, 1, n, BODY, NOTE, CENTER)
    put(ws, r, 2, name, GUESS if guess else BOLD, INPUT if key != BODY_KEY else NOTE)
    put(ws, r, 3, kind, GUESS if key != BODY_KEY else BOLD, INPUT if key != BODY_KEY else NOTE, CENTER)
    img = thumb(root, ref)
    put(ws, r, 4, None if img or not name else "暂无", GREY, NOTE, CENTER)
    for c in range(5, 5 + len(VIEWS) + 3):
        put(ws, r, c, None, BODY, INPUT, CENTER)
    put(ws, r, col_of("单位"), unit, BODY, INPUT, CENTER)
    put(ws, r, col_of("备注"), None, BODY, INPUT)
    put(ws, r, len(COLS), key)
    if img:
        ws.add_image(img, "D%d" % r)
    ws.row_dimensions[r].height = 80


def build_sheet(wb, root, form):
    ws = wb.active
    ws.title = SHEET
    size = form["size"]
    title = (form.get("title") or form["product"]).split(" · ")[0]
    last = col_letter(len(COLS) - 1)
    lines = [
        ("%s 参考图和尺寸填写表" % title, Font(name=FONT, size=15, bold=True), 24),
        ("全部选填，填多少用多少。黄色格子是能填的地方：每行贴前、后、左、右、上五面照片（只拍这五面，其他角度 AI 推），"
         "再写长、宽、高。长宽高都按装好时的方向量：长＝从主体正面看过去的左右，宽＝前后，高＝上下（从桌面往上）。"
         "主体那一行：%s装在主体上的配件按装好时的方向量，竖着插的那一边写在「高」；不装在主体上的配件平放着量，"
         "最长那一边算「长」。看下面两行蓝字示例。" % body_rule(size),
         BODY, 44),
        ("贴照片：新版 Excel 插入 → 图片 → 放置在单元格中；WPS 插入 → 图片 → 嵌入单元格；或直接把照片拖到格子上。"
         "灰色斜体是 AI 推的，不对直接改；包装里没有的配件整行删掉，漏的写进下面空行。蓝字是示例，可以删。原始照片请一起发。",
         Font(name=FONT, size=10, color="555555"), 32),
    ]
    for i, (text, font, height) in enumerate(lines, 1):
        ws.merge_cells("A%d:%s%d" % (i, last, i))
        ws["A%d" % i] = text
        ws["A%d" % i].font, ws["A%d" % i].alignment = font, WRAP
        ws.row_dimensions[i].height = height
    for i, label in enumerate(COLS, 1):
        put(ws, HEADER_ROW, i, label, Font(name=FONT, size=10, bold=True, color="FFFFFF"), HEAD, CENTER)
        ws.column_dimensions[col_letter(i)].width = WIDTHS[i - 1]
    ws.column_dimensions[col_letter(len(COLS))].hidden = True
    ws.freeze_panes = "C%d" % (HEADER_ROW + 1)

    r = HEADER_ROW + 1
    guide = dict(VIEW_SHOWS, **DIRECTIONS)
    guide.update({"序号": "怎么量", "名称": "长宽高按装好时的方向", "关系类型": "", "现有参考": "", "单位": "",
                  "备注": "主体正面＝" + front_face(form)})
    for i, label in enumerate(COLS[:-1], 1):
        put(ws, r, i, guide.get(label), Font(name=FONT, size=9, bold=label in DIRECTIONS, color="1F2630"), SUB, CENTER)
    put(ws, r, len(COLS), "guide")
    ws.row_dimensions[r].height = 30
    for example in EXAMPLES:
        r += 1
        example = dict(example, 序号="示例")
        for i, label in enumerate(COLS[:-1], 1):
            put(ws, r, i, example.get(label), BLUE, INPUT if i > 4 else NOTE, WRAP if label in ("名称", "备注") else CENTER)
        put(ws, r, len(COLS), "example")
        ws.row_dimensions[r].height = 58
    first_example = HEADER_ROW + 2

    name, ref, parts = body_of(form)
    dims = list(size["dims"].values())
    r += 1
    item_row(ws, root, r, "主体", BODY_KEY, name, "主体", ref, dims[0].get("unit", "mm") if dims else "mm", guess=False)
    body_row = r
    ws.cell(row=r, column=col_of("长")).comment = Comment(
        "；".join(d.get("label", "") for d in dims[:3]) or "长宽高量外轮廓", "UTA")
    rows = [(p["id"], p) for p in parts] + [("new%d" % k, None) for k in range(1, NEW_ROWS + 1)]
    for n, (key, p) in enumerate(rows, 1):
        r += 1
        item_row(ws, root, r, n, key, p and p.get("name"), p and p.get("type"), (p.get("imgs") or [""])[0] if p else "", "mm")
    kinds = DataValidation(type="list", formula1='"%s"' % ",".join(TYPES), allow_blank=True)
    units = DataValidation(type="list", formula1='"mm,cm,m"', allow_blank=True)
    for dv, col, first in ((kinds, "C", body_row + 1), (units, col_letter(col_of("单位")), first_example)):
        ws.add_data_validation(dv)
        dv.add("%s%d:%s%d" % (col, first, col, r))
    ws.cell(row=HEADER_ROW, column=3).comment = Comment(
        "组成部件：长在产品上；可拆件：会拆下来洗、加东西；耗材：定期换；随附配件：包装里另附；"
        "宿主产品：卖配件时它要装上去的那台产品；外部物品：水、粮、宠物这类道具。", "UTA")
    ws.page_setup.orientation = "landscape"
    return parts


def meta_sheet(wb, form, parts, form_path):
    ws = wb.create_sheet(META)
    ws.sheet_state = "hidden"
    have = {s.get("slot") for s in form.get("photos", []) if s.get("img")}
    rows = [
        ("magic", MAGIC), ("product", form["product"]), ("form", form_path),
        ("generated", datetime.date.today().isoformat()),
        ("have", json.dumps(sorted(v for _l, v in VIEWS if v in have))),
        ("parts", json.dumps([{k: p.get(k, "") for k in ("id", "name", "type")} for p in parts], ensure_ascii=False)),
        ("size", json.dumps({k: form["size"].get(k) for k in ("dims", "ratios")}, ensure_ascii=False)),
    ]
    for i, (k, v) in enumerate(rows, 1):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)


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
    parts = build_sheet(wb, root, form)
    meta_sheet(wb, form, parts, pf.shown_path(form_path, root))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)
    return out_path, len(parts)


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
        if key and key not in SKIP_KEYS:
            out.append((key, r, {name: ws.cell(row=r, column=c).value for name, c in cols.items()}))
    return cols, out


def pictures_at(pictures, row, col):
    return [p for p in pictures if p[0] == row and p[1] <= col <= p[2]]


def read_meta(wb):
    if META not in wb.sheetnames or SHEET not in wb.sheetnames:
        raise SheetError("not a photo sheet: no %s sheet (make one with photo_sheet.py build)" % META)
    ws = wb[META]
    meta = {text(ws.cell(row=r, column=1).value): ws.cell(row=r, column=2).value for r in range(1, ws.max_row + 1)}
    if meta.get("magic") != MAGIC:
        raise SheetError("not a %s sheet; build a new one with photo_sheet.py build" % MAGIC)
    for k, empty in (("have", []), ("parts", []), ("size", {})):
        meta[k] = json.loads(meta.get(k) or "null") or empty
    return meta


def geometry(dims, ratios, got):
    """The form's geo(): the same English lines the product form writes."""
    lines, bits, rs = [], [], []
    mm = {k: got[k][0] * TO_MM[got[k][1]] for k in got if got[k][1] in TO_MM}
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


def row_photos(pictures, r, cols, out_dir, prefix, root):
    """{view: [saved paths]} for the five photo cells of one row."""
    found = {}
    for label, view in VIEWS:
        pics = pictures_at(pictures, r, cols[label])
        if pics:
            found[view] = save_pictures(out_dir, prefix + view, pics, root)
    return found


def row_size(v, unit, name, warnings):
    """[(value, unit)] for 长 宽 高; a unit typed into one cell applies to that cell only."""
    return [number(v.get(col), unit, "%s 的%s" % (name, col), warnings) for col in ("长", "宽", "高")]


def size_text(vals):
    """'左右 60 × 前后 50 × 上下 210 mm': a part's size in its installed directions (长 宽 高)."""
    names = [DIRECTIONS[c] for c in ("长", "宽", "高")]
    units = set(u for x, u in vals if x)
    if len(units) == 1:
        return "%s %s" % (" × ".join("%s %s" % (n, num_text(x) if x else "?") for n, (x, _u) in zip(names, vals)),
                          units.pop())
    return " × ".join("%s %s" % (n, "%s %s" % (num_text(x), u) if x else "?") for n, (x, u) in zip(names, vals))


def read(root, xlsx, out_dir=None):
    wb = load_workbook(xlsx)
    meta = read_meta(wb)
    product = meta["product"]
    pictures = sheet_pictures(xlsx).get(SHEET, [])
    out_dir = out_dir or next_path(root, product, "photo_sheet_in_", "")
    warnings, notes = [], []
    size = meta["size"]
    dims = size.get("dims") or {}
    labels = dict((v, l) for l, v in VIEWS)
    cols, rows = rows_by_key(wb[SHEET])

    photos, got, body_seen = [], {}, False
    seen, agree, edits, sizes = set(), [], [], []
    original = {p["id"]: p for p in meta["parts"]}
    for key, r, v in rows:
        name, kind = text(v.get("名称")), text(v.get("关系类型"))
        unit = text(v.get("单位")) or "mm"
        if text(v.get("备注")):
            notes.append("%s 备注：%s" % (name or key, text(v.get("备注"))))
        if key == BODY_KEY:
            body_seen = True
            for view, saved in row_photos(pictures, r, cols, out_dir, "", root).items():
                how = "（替换）" if view in meta["have"] else "（新增）"
                photos.append("%s=%s%s" % (view, saved[0], how))
                photos += ["%s=%s（同一面的另一张）" % (view, p) for p in saved[1:]]
            for k, (val, u) in zip(dims, row_size(v, unit, name or "主体", warnings)):
                if val:
                    got[k] = (val, u)
            continue
        shots = row_photos(pictures, r, cols, out_dir, "part_%s_" % key, root)
        vals = row_size(v, unit, name or key, warnings)
        p = original.get(key)
        if p is None and not (name or kind or shots or any(x for x, _ in vals)):
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
            if lines:
                edits.append("\n".join(lines))
            else:
                agree.append(key)
        else:
            edits.append("  新增: %s → %s" % (name or "（没写名称）", kind or "类型没选"))
        bits = []
        if any(x for x, _ in vals):
            bits.append(size_text(vals))
        if shots:
            bits.append("照片 " + "、".join("%s %s" % (labels[view], "、".join(paths)) for view, paths in shots.items()))
        if bits:
            sizes.append("- %s: %s" % (label, "；".join(bits)))
    if not body_seen:
        warnings.append("主体那一行被删掉了，主机的照片和尺寸没读到")
    for key, p in original.items():
        if key not in seen:
            edits.append("  %s: 不对 → 表里删掉了这一行（原来是「%s」），按包装里没有处理" % (key, p.get("name")))

    geo, mm = geometry(dims, size.get("ratios"), got)
    for k, val in mm.items():
        if not 10 <= val <= 5000:
            warnings.append("%s %s %s 看起来不对：单位是不是填错了" % (dims[k].get("short", k), num_text(got[k][0]), got[k][1]))
    if got:
        size_line = "size: " + " × ".join(
            "%s %s" % (d.get("short", k), "%s %s" % (num_text(got[k][0]), got[k][1]) if k in got else "未填")
            for k, d in dims.items())
    else:
        size_line = "size: 未填（照参考图比例画，总览标「比例推定」）"
    ratio = ["%s/%s %s" % (dims[a].get("short", a), dims[b].get("short", b), num_text(mm[a] / mm[b]))
             for a, b in size.get("ratios") or [] if mm.get(a) and mm.get(b)]
    changed = len(photos) + len(got) + len(edits) + len(sizes)

    lines = ["UTA-PRODUCT v1", "product: " + product, "form: " + pf.shown_path(os.path.abspath(xlsx), root),
             "draft: " + text(meta.get("generated")), "source: photo_sheet（参考图和尺寸表：五面照片、尺寸、配件）",
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
    if geo:
        lines.append("geometry_prompt:")
        lines += ["- " + g for g in geo]
    lines.append("photos: " + ("；".join(photos) if photos else "没有新照片"))
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
            path, n_parts = build(root, args.form, args.out)
            out.write("SHEET %s  part rows %d\n" % (pf.shown_path(path, root), n_parts))
            out.write("Send it to whoever has the product; everything in it is optional and nothing waits on it.\n")
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
