# 产品卡：round10l

POKPET 10L 不锈钢宠物饮水机。项目名「圆款 / ROUND」只是项目名，机身不是圆柱。

来源：`docs/POKPET_10L_ROUND_DESIGN_DIRECTOR.md` 第 6、7 节（2026-11-15 用户确认）。本卡是出图时唯一的产品事实来源。

## 已确认事实

图位卡的 `selling_point` 只能填下表的编号。主标题、副标题、强调数字里的数字，只能用「画面可写」一列里出现过的。

| 编号 | 事实 | 画面可写 | 不可写成 |
|---|---|---|---|
| F1 | 容量 10 升 | 10 L | 可用天数、适合几只宠物、类目最大、加仑换算 |
| F2 | 304 不锈钢 | 304、stainless steel、brushed | 认证徽章、医用级、其他牌号 |
| F3 | 运行声音低于 20 分贝 | Under 20 dB | 25 dB、0 dB、实验室已测、绝对静音、保证不吵醒 |
| F4 | 猫和狗都能用，多宠家庭 | Cats and dogs | 指定只数、指定品种 |
| F5 | 易清洗 | Easy to clean、rinse、wipe | 洗碗机、免工具拆解、零件数量 |
| F6 | 透明水位窗可看水位 | Water window、see the water level | 缺水报警、自动断电、传感器 |

品牌名 POKPET 可以出现在排版文字里，不印在产品钢面上。

## 证据方案

每个事实有哪几种证明画面，见同目录的 `evidence_options.csv`（列的含义见 `UTA_STYLE.md` 1.10）。`F5-B`（整机在水槽里用龙头冲）碰到下面的未知项「是否防水、哪些零件可拆」，状态是 `needs_confirmation`：写卡方在第二轮的选择卡里问你一次，你答「是」这一轮才能选。想让它长期可选，把答案写进上面的已确认事实，再把这一行的状态改成 `ok`。`F6-B`（人低头查看水位）只在用户点名时给：成图里这个动作容易被画成用手指着水窗。

## 未知项

供电方式、包装清单、外形尺寸、内部水泵、滤芯结构、哪些零件可拆、是否防水、能否户外使用，都未确认。未知保持未知：不画、不写、不暗示。

`ref/source_with_filter_pads.png` 右侧的白色滤垫和蓝色海绵只是参考图里的摆放，不是包装清单，不入画。

## 外形识别点

验收 V1 逐条对照。中文给人看，英文一行供提示词使用。

- 宽的圆角矩形深盆，拉丝不锈钢，盆口有一圈外翻的卷边。
- 正面正中是一条竖直的细长胶囊形透明水位窗，里面是蓝色水柱，有 MAX 和 MIN 刻度。
- 盆内靠后正中是黑色圆角方形龙头座。
- 龙头座上是一根弯成鹅颈形的银色龙头，水从龙头落向盆中央。
- 盆内靠前沿有一条黑色细长槽。只照样画出来，不给它起功能名。
- 盆内水面下有一层带波浪形台阶的内胆。

不是：四叶草水窗、顶部带按键的控制台、方箱机身、圆柱机身。

## Identity (prompt)

- wide rounded-rectangle deep basin in brushed stainless steel with a rolled outer rim
- one slim vertical pill-shaped transparent water window centred on the front face, blue water column inside, MAX and MIN marks
- black rounded-square spout base at the rear centre inside the basin
- curved silver gooseneck spout rising from the black base, its outlet pointing down at the centre of the basin
- one slim black slot along the front inner edge of the basin
- inner tray with a wavy step visible under the water surface
- no clover window, no top control console, no buttons, no screen, no logo on the steel

## 产品参考图

| 文件 | 机位 | 说明 |
|---|---|---|
| `ref/front_high.png` | 正面偏高 3/4 | 目前唯一可用的结构参考，从用户提供的整机图裁出 |
| `ref/source_with_filter_pads.png` | 同上 | 原始整机图，带滤垫。只留档，不作为生图参考 |

**缺口：** 目前只有一个角度。正俯拍、45° 俯拍、侧面、背面、空盆、拆开状态都没有参考图。这些机位出图时产品容易变形，V1 的通过率会低。补图后在本表和 `references/INDEX.csv` 各加一行。

## 禁用词

本产品的主标题、副标题、强调数字、卡片标签里不得出现：

- 1 m
- sensing
- sensor
- 10-15 s
- three modes
- timer
- 25 dB
- clover
- dishwasher
- auto shut-off
- low-water alert
- days
- gallon
- lab tested
- silent
