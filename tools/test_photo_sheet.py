"""Tests for tools/photo_sheet.py: the reference-photo and size sheet is built from a product form and read back (1.15, 3.9).

    python -m unittest discover -s tools -p "test_photo_sheet.py" -v
"""
import base64
import io
import json
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
        self.xlsx, _ = ps.build(ROOT, FORM, os.path.join(self.tmp, "sheet.xlsx"))

    def read(self):
        block, folder, _ = ps.read(ROOT, self.xlsx, os.path.join(self.tmp, "in"))
        return block, folder


class BuildTest(Base):
    def test_one_sheet_with_body_and_parts(self):
        wb = load_workbook(self.xlsx)
        self.assertEqual(wb.sheetnames, [ps.SHEET, ps.META])
        self.assertEqual(wb[ps.META].sheet_state, "hidden")
        ws = wb[ps.SHEET]
        self.assertTrue(ws.column_dimensions[ps.col_letter(len(ps.COLS))].hidden)
        self.assertEqual([c.value for c in ws[ps.HEADER_ROW]][4:9], ["正面", "背面", "左侧", "右侧", "俯视（上）"])
        self.assertIn("全部选填", ws["A2"].value)
        body = row_of(ws, "body")
        self.assertEqual(ws.cell(row=body, column=2).value, "不锈钢桶身（含顶盘）")
        self.assertEqual(body, row_of(ws, "example") + 2)

    def test_sizes_are_explained_by_direction(self):
        ws = load_workbook(self.xlsx)[ps.SHEET]
        self.assertIn("长＝从主体正面看过去的左右，宽＝前后，高＝上下", ws["A2"].value)
        self.assertIn("长：左右最宽处；宽：前后最深处；高：桌面到盆沿", ws["A2"].value)
        guide = row_of(ws, "guide")
        self.assertEqual(guide, ps.HEADER_ROW + 1)
        got = {label: ws.cell(row=guide, column=ps.col_of(label)).value for label in ("长", "宽", "高", "正面", "左侧", "俯视（上）")}
        self.assertEqual(got, {"长": "左右", "宽": "前后", "高": "上下", "正面": "看得到 长 × 高",
                               "左侧": "看得到 宽 × 高", "俯视（上）": "看得到 长 × 宽"})
        self.assertEqual(ws.cell(row=guide, column=ps.col_of("备注")).value, "主体正面＝有水位窗的那一面")
        upright, flat = guide + 1, guide + 2
        self.assertIn("竖的那一边写在「高」", ws.cell(row=upright, column=ps.col_of("备注")).value)
        self.assertEqual([ws.cell(row=upright, column=ps.col_of(c)).value for c in ("长", "宽", "高")], [40, 40, 120])
        self.assertIn("平放在桌上量", ws.cell(row=flat, column=ps.col_of("备注")).value)
        self.assertRaises(AssertionError, row_of, ws, "P1")
        self.assertEqual(ws.cell(row=row_of(ws, "P2"), column=3).value, "可拆件")
        row_of(ws, "new5")
        self.assertGreater(len(ws._images), 5)

    def test_never_overwrites_and_reads_an_old_form_html(self):
        self.assertRaises(ps.SheetError, ps.build, ROOT, FORM, self.xlsx)
        with open(FORM, encoding="utf-8") as fh:
            form = json.load(fh)
        del form["size"]["ratios"]
        for d in form["size"]["dims"].values():
            d.pop("unit", None)
        html = os.path.join(self.tmp, "form.html")
        with open(html, "w", encoding="utf-8") as fh:
            fh.write("<html>" + ps.pf.OPEN + json.dumps(form, ensure_ascii=False) + ps.pf.CLOSE + "</html>")
        path, parts = ps.build(ROOT, html, os.path.join(self.tmp, "from_html.xlsx"))
        self.assertEqual(parts, 8)
        meta = ps.read_meta(load_workbook(path))
        self.assertEqual(meta["size"]["ratios"], [["L", "H"], ["W", "H"]])
        self.assertEqual(meta["size"]["dims"]["L"]["unit"], "mm")


class ReadTest(Base):
    def test_untouched_sheet_agrees_with_the_draft(self):
        block, _ = self.read()
        self.assertIn("changed: 0（全部按 AI 草稿）", block)
        self.assertIn("parts: 同意 P2 P3 P4 P5 P6 P7 P8 P9\n", block)
        self.assertIn("size: 未填", block)
        self.assertIn("photos: 没有新照片", block)

    def fill(self):
        wb = load_workbook(self.xlsx)
        ws = wb[ps.SHEET]
        body = row_of(ws, "body")
        for label, value in (("长", 310), ("宽", "23cm"), ("高", 185), ("备注", "控制头高出盆沿约 55 mm")):
            ws.cell(row=body, column=ps.col_of(label), value=value)
        ws.add_image(XLImage(io.BytesIO(png("red"))), "%s%d" % (ps.col_letter(ps.col_of("背面")), body))
        p2 = row_of(ws, "P2")
        ws.cell(row=p2, column=ps.col_of("关系类型"), value="组成部件")
        for label, value in (("长", 60), ("宽", "5cm"), ("高", 210)):
            ws.cell(row=p2, column=ps.col_of(label), value=value)
        ws.add_image(XLImage(io.BytesIO(png("blue"))), "%s%d" % (ps.col_letter(ps.col_of("左侧")), row_of(ws, "P3")))
        ws.cell(row=row_of(ws, "P4"), column=ps.col_of("长"), value="约6")
        new = row_of(ws, "new1")
        for label, value in (("名称", "清洁刷"), ("关系类型", "随附配件"), ("长", 15), ("宽", 2), ("高", 2), ("单位", "cm")):
            ws.cell(row=new, column=ps.col_of(label), value=value)
        ws.delete_rows(row_of(ws, "P9"))
        wb.save(self.xlsx)
        front = "%s%d" % (ps.col_letter(ps.col_of("正面")), body)
        top = "%s%d" % (ps.col_letter(ps.col_of("俯视（上）")), body)
        patch(self.xlsx, ps.SHEET, front, '<c r="%s" t="str"><f>_xlfn.DISPIMG("ID_4F1A",1)</f>'
              '<v>=DISPIMG("ID_4F1A",1)</v></c>' % front, dict(WPS, **{"xl/media/wps_in_cell.png": png("green")}))
        patch(self.xlsx, ps.SHEET, top, '<c r="%s" vm="1" t="e"><v>#VALUE!</v></c>' % top,
              dict(RICH, **{"xl/media/excel_in_cell.png": png("white")}))

    def test_filled_sheet(self):
        self.fill()
        block, folder = self.read()
        self.assertIn("size: 长 310 mm × 宽 23 cm × 高 185 mm", block)
        self.assertIn("ratio: 长/高 1.68；宽/高 1.24", block)
        self.assertIn("geometry_prompt:\n- about 310 mm long, 23 cm deep, 185 mm tall to the rim\n"
                      "- length about 1.68 times the height; depth about 1.24 times the height", block)
        self.assertIn("  P2: 类型 可拆件 → 组成部件", block)
        self.assertIn("  P9: 不对 → 表里删掉了这一行", block)
        self.assertIn("  新增: 清洁刷 → 随附配件", block)
        self.assertIn("- P2 水泵头组件（一个整体）: 左右 60 mm × 前后 5 cm × 上下 210 mm", block)
        self.assertIn("- 新增 清洁刷: 左右 15 × 前后 2 × 上下 2 cm", block)
        self.assertIn("- P3 黑色控制头: 照片 左侧 ", block)
        self.assertIn("warnings: 黑色圆柱（上宽下窄） 的长 写的「约6」不是数字，没用", block)
        self.assertIn("不锈钢桶身（含顶盘） 备注：控制头高出盆沿约 55 mm", block)
        self.assertIn("front.png（替换）", block)
        self.assertIn("rear.png（新增）", block)
        self.assertIn("top_down.png（替换）", block)
        for name, color in (("front", "green"), ("top_down", "white"), ("rear", "red"), ("part_P3_side_left", "blue")):
            path = os.path.join(folder, name + ".png")
            self.assertTrue(os.path.isfile(path), name)
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), png(color), name)
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
        for marker in ("**参考图和尺寸表（选填）。**", "tools/photo_sheet.py build", "tools/photo_sheet.py read", "`part_sizes`"):
            self.assertIn(marker, guide)
        self.assertIn("参考图和尺寸表", self.read("grok", "grok-UTAstyle-skill.md"))
        self.assertIn("tools/photo_sheet.py", self.read("AGENTS.md"))
        self.assertIn("tools/photo_sheet.py", self.read("README.md"))


if __name__ == "__main__":
    unittest.main()
