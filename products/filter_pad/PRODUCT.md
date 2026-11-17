# 产品卡：filter_pad

白色长条滤垫。可能是 round10l 饮水机配套的替换滤垫（round10l 原始整机图里摆着同样的白色滤垫），但两者的关系未确认。

来源：用户 2026-11-17 在对话里提供的 5 张大理石台面实拍（`photos/real_marble_5shots.webp`）。外形识别点是从这 5 张照片里看出来的，还没有经过用户逐条确认。本卡是出图时唯一的产品事实来源。

## 已确认事实

还没有。卖点、参数、适用机型都待用户提供。没有已确认事实之前，任何图位卡都填不了 `selling_point`。

| 编号 | 事实 | 画面可写 | 不可写成 |
|---|---|---|---|

## 未知项

尺寸、厚度、是否弯曲、材质名称、过滤功效、更换周期、适用机型、包装数量、蓝色海绵是不是这套产品的一部分，都未确认。未知保持未知：不画、不写、不暗示。

## 造型基准

状态：未做
形态：扁平

见 `UTA_STYLE.md` 1.12。形态写「立体」或「扁平」，决定出哪一套视角。状态只有三种：未做、待确认、已确认（日期）。不是「已确认」时，脚本拒绝这个产品的所有图位卡。

现有实拍拍在有花纹的大理石台面上，浅色滤垫的边缘被纹理和反光吃掉一部分。可以先用它做第一版造型基准，但侧面厚度、弯曲和长宽比会标「推定」。补拍 1.11 的三张规格照后再出一版。

## 物理边界

见 `UTA_STYLE.md` 1.11。没确认的项写「未确认」。

| 项 | 值 |
|---|---|
| 尺寸 | 未确认 |
| 比例 | 未确认 |
| 轮廓 | 未确认。实拍里有两张看着中段有弧度，另外两张接近直的，可能是拍摄角度造成的 |
| 大小参照 | 未确认。有手的那张实拍里，滤垫看着和成人的手从手腕到指尖差不多长，要用尺子量过才能填 |
| 部件清单 | 未确认。实拍里只有一片白色滤垫，没有蓝色海绵 |

## Geometry (prompt)

## Parts (prompt)

## 外形识别点

验收 V1 逐条对照。中文给人看，英文一行供提示词使用。下面是从实拍看出来的，等用户确认。

- 一整片长条形滤垫，两端圆角。
- 白色到浅灰色，致密的无纺纤维，表面有淡淡的灰色云纹、半透明感；不是蓬松的毛毡。
- 表面分成左右两块长条形的纤维区，首尾相接，每块像拉长的六边形，靠中间的一端是斜切的。
- 正中间是一段收腰：两块纤维区之间形成一个浅 V 形的压合区，两条长边在这里各向内收一点。
- 整个外轮廓有一圈窄的、压平的封边。
- 有看得见的厚度，边缘圆润，不是一张薄片。

不是：笔直的薄毛毡片、蓬松卷绒、和蓝色海绵粘在一起、两片分开的滤垫、塑料框或外壳。

## Identity (prompt)

- one long filter pad with rounded ends, a single piece
- white to light grey dense non-woven fibre with a faint grey mottled, slightly translucent texture, not fluffy felt
- two long raised fibre panels end to end, each an elongated hexagon with an angled inner end
- a pinched waist in the middle: a shallow V-shaped pressed zone between the two panels where both long edges step inward slightly
- a narrow flat pressed border around the whole outline
- visible thickness with a rounded edge, not a thin sheet
- no blue sponge, no second layer, no plastic frame or housing, no logo or print

## 产品参考图

| 文件 | 机位 | 说明 |
|---|---|---|
| `photos/real_marble_5shots.webp` | 俯拍、斜拍、有手的一张 | 用户实拍，5 张拼成一张，大理石台面。只给造型基准当实拍输入，不直接当场景图的产品参考图 |

造型基准确认后，确认的视角存成 `ref/baseline_<视角>.png`，在本表和 `ref_views.csv` 各登记一行。

## 禁用词

