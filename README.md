# 亚马逊美工设计

规则版本 **3.47**（2026-11-20）。这个仓库保存 Amazon 主图、副图和 A+ 的出图指引、产品事实、参考图索引和图位卡。

出图只有一份指引：**[UTA_STYLE.md](UTA_STYLE.md)**。写任务的 Grok 和出图的 Codex 读的是同一份。

## 怎么用

**准备一次：给 Grok 装上启动指令。** 把 [grok/BOOTSTRAP.md](grok/BOOTSTRAP.md) 方框里的一小段放进 Geo / Grok 的项目指令或 skill。它每次开新对话都会去仓库读最新的 [grok/grok-UTAstyle-skill.md](grok/grok-UTAstyle-skill.md)，以后 skill 更新了不用再重新粘贴。不方便放的话，每次开新对话时发这一句：

```
请读取 https://raw.githubusercontent.com/geoorood-beep/amazon-visual-design/main/grok/grok-UTAstyle-skill.md 并按它执行。
```

**第一步：让 Grok 写任务单。** 对它说产品名就可以开始，例如「产品：round10l，开始」。它的第一条回复会先报出读到的版本号、事实编号和参考图数量，对不上说明它没读到文件。

新产品先把多视角素材（实拍、五视图都行）发给 Grok：它马上判断每张是哪个角度、起草产品卡、出造型基准总览图，你只确认一次「产品样子和资料对不对」。造型基准确认之前不出场景图。

Grok 只用五张卡问你：做哪些图、卖点怎么分配、整套故事怎么讲、情绪基调、风格。一类一张卡管整套，不按图一张张问；文字放哪、A+ 版本、景别机位光、场景宠物这些它自己定，写在确认单「我替你定的」一栏，你想改就在确认单上说一句。正常情况下你只点两次：第一条消息的卡，和确认单上的「确认」。没回答的卡它按推荐往下做，不会停住等。

**第二步：把 Grok 输出的任务单交给 Codex。** 在 Codex 里打开本仓库，发：

把 Grok 输出的整个代码块原样粘贴过去。代码块第一行已经写好「按 UTA style 执行下面这份任务单。」，不需要你再加话。

Codex 会校验、逐张出图、排版、拼版、验收，最后给一份回报。

Codex 最后还会生成一张验收表单（一图一格，成图和这张卡要拍的内容对照，图片嵌在网页里）。满意的图不用动，不满意的写一句建议，点「生成验收结果」，把结果发给 Grok，它会自动把这几张改进卡里交给 Codex 返工。

**第三步：把 Codex 的回报原样转给 Grok。** Grok 自己修掉校验没过的卡并重新出任务单；只有需要你拿主意的（比如某张图重做两次仍不理想）才用选择题问你；全部通过后给你一张汇总表。

**想直接出仓库里已有的卡**，不需要 Grok：

```
按 UTA style 出 cards/round10l/S5_clean.md
```

## 你可能要改的地方

| 你要做的事 | 改哪里 |
|---|---|
| 新增或修改产品事实 | `products/<产品>/PRODUCT.md` |
| 给某个卖点增加或修改证明画面 | `products/<产品>/evidence_options.csv`（列的含义见 `UTA_STYLE.md` 1.10） |
| 补产品参考图 | 放进 `products/<产品>/ref/`，在产品卡和 [references/INDEX.csv](references/INDEX.csv) 各加一行 |
| 补尺寸、规格照、部件关系 | 打开产品资料表（选填）填好，把生成的 `UTA-PRODUCT` 发给 Grok；或对 Codex 说「打开 <产品> 的产品资料表」 |
| 拿着实物拍照、量尺寸 | 对 Codex 说「出 <产品> 的参考图和尺寸表」，拿到一张 Excel 表：主体和配件各一行，贴前后左右上五面照片、写长宽高（全部选填），发回给 Grok 或 Codex |
| 改某个产品的结构核对题 | `products/<产品>/checks.csv`（列的含义见 `UTA_STYLE.md` 4.7），改完运行 `python tools/blind_check.py check` |
| 加一个新品类 | 在 [references/categories/](references/categories/README.md) 加一份品类文件，运行 `python tools/product_form.py check` |
| 把认可的成图设为锚图 | 对 Codex 说「这张做锚图」 |
| 多张图有同一个毛病 | 改 [tools/prompt_base.txt](tools/prompt_base.txt) 里的固定提示词段落 |
| 调整画面规则、文字规则、验收 | 改 [UTA_STYLE.md](UTA_STYLE.md) |

效果不对时先查哪一层，见 `UTA_STYLE.md` 第 5 节。

## 目录

| 路径 | 内容 | 性质 |
|---|---|---|
| `UTA_STYLE.md` | 唯一的出图指引：标准、写任务单、出图、验收、校准 | 规则 |
| `AGENTS.md` | 只有一句话：读 `UTA_STYLE.md` | Codex 的入口 |
| `grok/grok-UTAstyle-skill.md` | grok-UTAstyle skill 3.1：Grok 的操作步骤：每一步发什么消息、什么格式 | Grok 的入口 |
| `products/` | 每款产品一张产品卡和参考图 | 数据 |
| `references/INDEX.csv` | 全部可用参考图的索引 | 数据 |
| `references/anchors/` | 认可过的自家成图，作风格锚 | 数据 |
| `cards/` | 图位卡。`_TEMPLATE.md` 是空白模板 | 数据 |
| `tools/check_card.py` | 校验任务单和图位卡，拼出提示词 | 机制 |
| `tools/review_form.py` | 出图之后生成验收表单 `outputs/<产品>/review_vNN.html`（4.5） | 机制 |
| `tools/blind_check.py` | 独立核对：另一个没看过卡片的模型只看图答结构题，脚本对照产品卡打分（4.7） | 机制 |
| `grok/product_template.html` 和 `grok/product_form.css`、`grok/product_form.js` | 产品资料表：Grok 只抄很短的外壳，样式和脚本从仓库加载；`product_form.py build` 生成的文件把它们嵌进页面 | 机制 |
| `tools/product_form.py` | 选填的产品资料表：定品类、出草稿、生成 `outputs/<产品>/product_form_vNN.html`（1.15、3.9） | 机制 |
| `tools/photo_sheet.py` | 选填的参考图和尺寸表：`build` 把产品资料表做成一张 Excel（主体和每个配件一行，五面照片加长宽高）；`read` 读回填好的表，取出照片、打出 `UTA-PRODUCT v1`（1.15、3.9） | 机制 |
| `references/aplus_recipes.csv` | A+ 页面套路：痛点解决、功能清单、质感叙事、场景旅程、自由组合，各自学自哪个详情页、骨架和例子（1.9） | 数据 |
| `references/storylines.csv` | 整套主线：一天里的几个瞬间、一个家的几个角落、先乱后静、一家人各有各的需要、各讲各的（1.14） | 数据 |
| `references/categories/` | 品类库：每个品类通常有哪些部件和关系、产品有几种样子、要问什么、要补哪些照片（1.15） | 数据 |
| `tools/prompt_base.txt` | 提示词的固定段落 | 机制 |
| `docs/` | 案例图库和旧版标准 | 出图时不读 |
| `archive/` | 2.11 版规则和旧技能 | 出图时不读 |

## 校验和测试

需要 Python 3.8 以上，只用标准库。

```sh
python tools/check_card.py --task outputs/task.md
python tools/check_card.py cards/round10l/S5_clean.md
python tools/check_card.py --set cards/round10l
python -m unittest discover -s tools -p "test_check_card.py" -v
python tools/product_form.py check
python tools/blind_check.py check
python -m unittest discover -s tools -p "test_*.py"
```

第一条接收 Grok 的任务单：拆成图位卡并逐张校验。第二条校验单张卡，通过时打印要附带的图片、提示词和排版说明。第三条检查一个目录下的整套卡。第四条是脚本自身的测试，改过 `tools/`、`UTA_STYLE.md`、产品卡或索引之后运行一次。第五条校验品类库，第六条校验结构核对题，第七条跑全部测试。

## 当前状态

- 已有产品卡：`round10l`（10L 圆款）、`clover_square`（方形四叶草款）。
- 已有锚图 5 张：v06 轮认可的清洗、换滤芯、搬运、安静四张，以及圆款清洗试样一张。
- 已有样卡 24 张。`cards/round10l/` 14 张：主图 1 张；副图 3 张（清洗、安静、材质）；标准版 A+ 四屏共 10 张卡（P1 单场景、P6 三格宫格、P7 两步流程、P8 参数收尾）。`cards/examples_premium/` 10 张：高级版 A+ 四屏（P1 单场景、P2 大数字加场景、P3 深色三格拼盘、P4 前后对照）。
- 主图、副图、A+ 都在同一份指引里。A+ 每一屏交电脑端 1464×600 和手机端 600×450 两个文件，共用同一批底图。
- A+ 有两个版本，由你在 Grok 的选择题里选：**标准版**是浅色纯底、等大格子；**高级版**按你的精选案例（AP_005、AP_006、AP_007）来：拼盘、字压在图里、巨型数字屏、前后对照屏、一到两屏深色。
- A+ 高级版有 12 种屏型和 4 个页面套路（`references/aplus_recipes.csv`），按卖点挑版式，开场可以和下一屏无缝拼接。所有屏都是静态图，动态效果用 Amazon 自带模块。
- **A+ 还没有的：** 点名别家的对比屏（麻烦格可以放无牌的同类产品）、爆炸图；认证和质保收尾要等产品卡登记了这些事实再用。
- **A+ 的拼版由 Codex 按指引 1.9 的坐标排。** 目前没有拼版脚本，不同次排出来的细节可能略有出入。
- **待补：** `round10l` 只有一个角度的产品参考图。俯拍、侧面、空盆等机位出图时产品容易变形。
- **未验证：** 这套流程还没有用 Grok 和 Codex 实际跑过。建议先用 3 张样卡出图，和 `references/anchors/` 里的旧图对比后再扩展到整套。
- Grok 不能直接调用 Codex，任务单需要你原样转交一次。

## 其他工具

`tools/` 里另有 2.x 版留下的 `grade_check.py`、`composite_water_clarity.c`、`upscale_2x.swift`，以及 `scripts/image25.py`。它们不在现在的出图流程里：明暗数值不再作为验收门槛，放大图不作为交付物。保留备用。

参考图用于理解构图和信息层级，不代表本品结构，也不附带第三方品牌素材的商业再利用授权。版本变化见 [CHANGELOG.md](CHANGELOG.md)。
