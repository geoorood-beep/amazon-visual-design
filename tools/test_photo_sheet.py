"""Tests for tools/photo_sheet.py: the photo and size sheet is built from a product form and read back (1.15, 3.9).

    python -m unittest discover -s tools -p "test_photo_sheet.py" -v
"""
import base64
import io
import os
import re
import shutil
import tempfile
import unittest
import zipfile

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

import photo_sheet as ps

ROOT = ps.ROOT
FORM = os.path.join(ROOT, "tools", "fixtures", "product_form_pw002_s.json")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def png(color):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(buf, "PNG")
    return buf.getvalue()


def row_of(ws, key):
    col = [c.value for c in ws[ps.HEADER_ROW]].index("key") + 1
    for r in range(ps.HEADER_ROW + 1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == key:
            return r
    raise AssertionError(key)


def col_of(ws, label):
    return [c.value for c in ws[ps.HEADER_ROW]].index(label) + 1


def patch(path, sheet, cell, new_cell, files):
    """Rewrite one cell of a sheet and add parts, the way Excel or WPS would store an in-cell picture."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin:
        target = ps.sheet_parts(zin)[sheet]
        with zipfile.ZipFile(tmp, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == target:
                    xml = data.decode("utf-8")
                    xml, n = re.subn(r'<c r="%s"[^>]*?(?:/>|>.*?</c>)' % cell, new_cell, xml, count=1, flags=re.S)
                    assert n == 1, cell
                    data = xml.encode("utf-8")
                zout.writestr(item, data)
            for name, data in files.items():
                zout.writestr(name, data)
    os.replace(tmp, path)


RICH = {
    "xl/metadata.xml": '<metadata xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:xlrd="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata">'
    '<metadataTypes count="1"><metadataType name="XLRICHVALUE" minSupportedVersion="120000"/></metadataTypes>'
    '<futureMetadata name="XLRICHVALUE" count="1"><bk><extLst><ext uri="{3e2802c4-a4d2-4d8b-9148-e3be6c30e623}">'
    '<xlrd:rvb i="0"/></ext></extLst></bk></futureMetadata>'
    '<valueMetadata count="1"><bk><rc t="1" v="0"/></bk></valueMetadata></metadata>',
    "xl/richData/rdrichvaluestructure.xml": '<rvStructures xmlns="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata" '
    'count="1"><s t="_localImage"><k n="_rvRel:LocalImageIdentifier" t="i"/><k n="CalcOrigin" t="i"/></s></rvStructures>',
    "xl/richData/rdrichvalue.xml": '<rvData xmlns="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata" count="1">'
    '<rv s="0"><v>0</v><v>5</v></rv></rvData>',
    "xl/richData/richValueRel.xml": '<richValueRels xmlns="http://schemas.microsoft.com/office/spreadsheetml/2022/richvaluerel" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><rel r:id="rId1"/></richValueRels>',
    "xl/richData/_rels/richValueRel.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    'Target="../media/excel_in_cell.png"/></Relationships>',
}
WPS = {
    "xl/cellimages.xml": '<etc:cellImages xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:etc="http://www.wps.cn/officeDocument/2017/etCustomData"><etc:cellImage><xdr:pic><xdr:nvPicPr>'
    '<xdr:cNvPr id="2" name="ID_4F1A" descr=""/><xdr:cNvPicPr/></xdr:nvPicPr><xdr:blipFill><a:blip r:embed="rId1"/>'
    '</xdr:blipFill><xdr:spPr/></xdr:pic></etc:cellImage></etc:cellImages>',
    "xl/_rels/cellimages.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    'Target="media/wps_in_cell.png"/></Relationships>',
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.xlsx, _, _ = ps.build(ROOT, FORM, os.path.join(self.tmp, "sheet.xlsx"))

    def read(self):
        block, folder, _ = ps.read(ROOT, self.xlsx, os.path.join(self.tmp, "in"))
        return block, folder


class BuildTest(Base):
    def test_layout(self):
        wb = load_workbook(self.xlsx)
        self.assertEqual(wb.sheetnames, [ps.GUIDE, ps.PHOTOS, ps.SIZE, ps.PARTS, ps.META])
        self.assertEqual(wb[ps.META].sheet_state, "hidden")
        for name in (ps.PHOTOS, ps.SIZE, ps.PARTS):
            ws = wb[name]
            key = ps.col_letter([c.value for c in ws[ps.HEADER_ROW]].index("key") + 1)
            self.assertTrue(ws.column_dimensions[key].hidden, name)
        photos = wb[ps.PHOTOS]
        for slot in ("front", "three_quarter_left", "rear", "spec_hand", "flatlay"):
            row_of(photos, slot)
        parts = wb[ps.PARTS]
        self.assertRaises(AssertionError, row_of, parts, "P1")
        self.assertEqual(parts.cell(row=row_of(parts, "P2"), column=2).value, "水泵头组件（一个整体）")
        row_of(parts, "new5")
        self.assertGreater(len(photos._images), 5)

    def test_formulas_have_blank_cached_values(self):
        wb = load_workbook(self.xlsx, data_only=True)
        formulas = load_workbook(self.xlsx)[ps.SIZE]
        cells = [c.coordinate for row in formulas.iter_rows() for c in row if str(c.value or "").startswith("=")]
        self.assertGreaterEqual(len(cells), 3)
        for ref in cells:
            self.assertIn(wb[ps.SIZE][ref].value, (None, ""), ref)

    def test_never_overwrites_and_reads_the_form_html(self):
        self.assertRaises(ps.SheetError, ps.build, ROOT, FORM, self.xlsx)
        html = os.path.join(self.tmp, "form.html")
        with open(FORM, encoding="utf-8") as fh:
            body = fh.read()
        with open(html, "w", encoding="utf-8") as fh:
            fh.write("<html>" + ps.pf.OPEN + body + ps.pf.CLOSE + "</html>")
        path, slots, parts = ps.build(ROOT, html, os.path.join(self.tmp, "from_html.xlsx"))
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(parts, 8)


class OldFormTest(unittest.TestCase):
    def test_a_form_without_units_or_ratios_gets_the_defaults(self):
        size = ps.normalize_size({"dims": {"L": {"short": "长", "en": "long"}, "H": {"short": "高", "en": "tall"}},
                                  "extra": [{"key": "head", "en": "rises {v} mm"}]})
        self.assertEqual(size["dims"]["L"]["unit"], "mm")
        self.assertEqual(size["dims"]["H"]["noun"], "height")
        self.assertEqual(size["ratios"], [["L", "H"]])
        self.assertEqual(size["extra"][0]["unit"], "mm")


class ReadTest(Base):
    def test_untouched_sheet_agrees_with_the_draft(self):
        block, _ = self.read()
        self.assertIn("changed: 0（全部按 AI 草稿）", block)
        self.assertIn("parts: 同意 P2 P3 P4 P5 P6 P7 P8 P9\n", block)
        self.assertIn("size: 未填", block)
        self.assertIn("photos: 没有新照片", block)

    def fill(self):
        wb = load_workbook(self.xlsx)
        size = wb[ps.SIZE]
        for key, value in (("dim:L", 310), ("dim:W", "23cm"), ("dim:H", 185), ("extra:head", 55)):
            size.cell(row=row_of(size, key), column=3, value=value)
        size.cell(row=row_of(size, "size_ref"), column=3, value="高度到成年猫的肩膀")
        photos = wb[ps.PHOTOS]
        shot = col_of(photos, "你的照片（贴在这里）")
        rear = row_of(photos, "rear")
        img = XLImage(io.BytesIO(png("red")))
        photos.add_image(img, "%s%d" % (ps.col_letter(shot), rear))
        photos.cell(row=row_of(photos, "low_angle"), column=col_of(photos, "拍了吗"), value="不适用")
        photos.cell(row=row_of(photos, "spec_hand"), column=col_of(photos, "照片文件名"), value="IMG_2210.jpg")
        parts = wb[ps.PARTS]
        p2 = row_of(parts, "P2")
        parts.cell(row=p2, column=col_of(parts, "关系类型"), value="组成部件")
        for label, value in (("长", 60), ("宽", 50), ("高或直径", 210), ("包装里几件", 1)):
            parts.cell(row=p2, column=col_of(parts, label), value=value)
        parts.add_image(XLImage(io.BytesIO(png("blue"))), "F%d" % row_of(parts, "P3"))
        parts.cell(row=row_of(parts, "P4"), column=col_of(parts, "长"), value="约6")
        new = row_of(parts, "new1")
        for label, value in (("配件名", "清洁刷"), ("关系类型", "随附配件"), ("长", 15), ("宽", 2), ("高或直径", 2),
                             ("单位", "cm"), ("备注", "白色")):
            parts.cell(row=new, column=col_of(parts, label), value=value)
        parts.delete_rows(row_of(parts, "P9"))
        wb.save(self.xlsx)
        front, side = row_of(photos, "front"), row_of(photos, "side_left")
        col = ps.col_letter(shot)
        patch(self.xlsx, ps.PHOTOS, "%s%d" % (col, front),
              '<c r="%s%d" t="str"><f>_xlfn.DISPIMG("ID_4F1A",1)</f><v>=DISPIMG("ID_4F1A",1)</v></c>' % (col, front),
              dict(WPS, **{"xl/media/wps_in_cell.png": png("green")}))
        patch(self.xlsx, ps.PHOTOS, "%s%d" % (col, side), '<c r="%s%d" vm="1" t="e"><v>#VALUE!</v></c>' % (col, side),
              dict(RICH, **{"xl/media/excel_in_cell.png": png("white")}))

    def test_filled_sheet(self):
        self.fill()
        block, folder = self.read()
        self.assertIn("size: 长 310 mm × 宽 23 cm × 高 185 mm；控制头高出盆沿 55 mm", block)
        self.assertIn("ratio: 长/高 1.68；宽/高 1.24", block)
        self.assertIn("size_ref: 高度到成年猫的肩膀", block)
        self.assertIn("geometry_prompt:\n- about 310 mm long, 23 cm deep, 185 mm tall to the rim\n"
                      "- length about 1.68 times the height; depth about 1.24 times the height\n"
                      "- the control head rises about 55 mm above the rim", block)
        self.assertIn("  P2: 类型 可拆件 → 组成部件", block)
        self.assertIn("  P9: 不对 → 表里删掉了这一行", block)
        self.assertIn("  新增: 清洁刷 → 随附配件", block)
        self.assertIn("- P2 水泵头组件（一个整体）: 60 × 50 × 210 mm；包装里 1 件", block)
        self.assertIn("- 新增 清洁刷: 15 × 2 × 2 cm", block)
        self.assertIn("warnings: 黑色圆柱（上宽下窄） 的长 写的「约6」不是数字，没用", block)
        self.assertIn("清洁刷 备注：白色", block)
        self.assertIn("photos_missing: 低机位（宠物视角） 不适用", block)
        self.assertIn("spec_hand=IMG_2210.jpg（新增）（表里没贴图，原图另发）", block)
        for name, color in (("front", "green"), ("side_left", "white"), ("rear", "red"), ("part_P3", "blue")):
            path = os.path.join(folder, name + ".png")
            self.assertTrue(os.path.isfile(path), name)
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), png(color), name)
        self.assertIn("front=", block)
        self.assertIn("front.png（替换）", block)
        self.assertIn("rear.png（新增）", block)
        self.assertNotIn("example", block)
        with open(os.path.join(folder, "uta_product.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), block + "\n")

    def test_a_sheet_without_metadata_is_refused(self):
        other = os.path.join(self.tmp, "plain.xlsx")
        from openpyxl import Workbook
        Workbook().save(other)
        out = io.StringIO()
        self.assertEqual(ps.main(["read", other], out=out), 2)
        self.assertIn("not a photo sheet", out.getvalue())


class WiringTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_skill_agents(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("**照片尺寸表（选填）。**", "tools/photo_sheet.py build", "tools/photo_sheet.py read", "`part_sizes`"):
            self.assertIn(marker, guide)
        self.assertIn("照片尺寸表", self.read("grok", "grok-UTAstyle-skill.md"))
        self.assertIn("tools/photo_sheet.py", self.read("AGENTS.md"))
        self.assertIn("tools/photo_sheet.py", self.read("README.md"))


if __name__ == "__main__":
    unittest.main()
