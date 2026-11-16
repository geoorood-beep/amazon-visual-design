# 亚马逊美工设计

规则版本 **3.1**（2026-11-16）。这个仓库保存 Amazon 主图、副图和 A+ 的出图指引、产品事实、参考图索引和图位卡。

出图只有一份指引：**[UTA_STYLE.md](UTA_STYLE.md)**。写任务的 Grok 和出图的 Codex 读的是同一份。

## 怎么用

**第一步：让 Grok 写任务单。** 把下面这段发给它，填上产品：

```
请读取 https://raw.githubusercontent.com/geoorood-beep/amazon-visual-design/main/UTA_STYLE.md
你是写任务单的一方，按第 2 节执行。
产品：round10l
```

Grok 会用选择题和你确认：做哪几个卖点，每张图的呈现形式、场景、宠物和标题。你用编号回答，最后回复「确认」，它一次输出整份任务单。

**第二步：把 Grok 输出的任务单交给 Codex。** 在 Codex 里打开本仓库，发：

```
按 UTA style 执行这份任务单：
（粘贴 Grok 输出的整个代码块，不改动）
```

Codex 会校验、逐张出图、排版、验收，最后给一份回报。

**想直接出仓库里已有的卡**，不需要 Grok：

```
按 UTA style 出 cards/round10l/S5_clean.md
```

## 你可能要改的地方

| 你要做的事 | 改哪里 |
|---|---|
| 新增或修改产品事实 | `products/<产品>/PRODUCT.md` |
| 补产品参考图 | 放进 `products/<产品>/ref/`，在产品卡和 [references/INDEX.csv](references/INDEX.csv) 各加一行 |
| 把认可的成图设为锚图 | 对 Codex 说「这张做锚图」 |
| 多张图有同一个毛病 | 改 [tools/prompt_base.txt](tools/prompt_base.txt) 里的固定提示词段落 |
| 调整画面规则、文字规则、验收 | 改 [UTA_STYLE.md](UTA_STYLE.md) |

效果不对时先查哪一层，见 `UTA_STYLE.md` 第 5 节。

## 目录

| 路径 | 内容 | 性质 |
|---|---|---|
| `UTA_STYLE.md` | 唯一的出图指引：标准、写任务单、出图、验收、校准 | 规则 |
| `AGENTS.md` | 只有一句话：读 `UTA_STYLE.md` | 入口 |
| `products/` | 每款产品一张产品卡和参考图 | 数据 |
| `references/INDEX.csv` | 全部可用参考图的索引 | 数据 |
| `references/anchors/` | 认可过的自家成图，作风格锚 | 数据 |
| `cards/` | 图位卡。`_TEMPLATE.md` 是空白模板 | 数据 |
| `tools/check_card.py` | 校验任务单和图位卡，拼出提示词 | 机制 |
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
```

第一条接收 Grok 的任务单：拆成图位卡并逐张校验。第二条校验单张卡，通过时打印要附带的图片、提示词和排版说明。第三条检查一个目录下的整套卡。第四条是脚本自身的测试，改过 `tools/`、`UTA_STYLE.md`、产品卡或索引之后运行一次。

## 当前状态

- 已有产品卡：`round10l`（10L 圆款）、`clover_square`（方形四叶草款）。
- 已有锚图 5 张：v06 轮认可的清洗、换滤芯、搬运、安静四张，以及圆款清洗试样一张。
- 已有样卡 3 张：`cards/round10l/` 下的清洗、安静、材质。
- **待补：** `round10l` 只有一个角度的产品参考图。俯拍、侧面、空盆等机位出图时产品容易变形。
- **未验证：** 这套流程还没有用 Grok 和 Codex 实际跑过。建议先用 3 张样卡出图，和 `references/anchors/` 里的旧图对比后再扩展到整套。
- Grok 不能直接调用 Codex，任务单需要你原样转交一次。

## 其他工具

`tools/` 里另有 2.x 版留下的 `grade_check.py`、`composite_water_clarity.c`、`upscale_2x.swift`，以及 `scripts/image25.py`。它们不在现在的出图流程里：明暗数值不再作为验收门槛，放大图不作为交付物。保留备用。

参考图用于理解构图和信息层级，不代表本品结构，也不附带第三方品牌素材的商业再利用授权。版本变化见 [CHANGELOG.md](CHANGELOG.md)。
