# 亚马逊美工设计

规则版本 **3.0**（2026-11-16）。这个仓库保存 Amazon 主图、副图和 A+ 的出图标准、产品事实、参考图索引和图位卡。

3.0 把出图规则从约 32 万字收成几页，并把「谁读什么、交什么」固定下来。旧规则没有删除，移到了 `archive/`，案例库留在 `docs/`。原因和取舍见 [CHANGELOG.md](CHANGELOG.md)。

## 怎么用

三方分工：你定事实和取舍，Grok 写图位卡，Codex 出图。完整流程见 [standard/WORKFLOW.md](standard/WORKFLOW.md)。

| 你要做的事 | 看哪里 |
|---|---|
| 让 Grok 写图位卡 | 把 [standard/WRITER_GUIDE.md](standard/WRITER_GUIDE.md) 的地址发给它，说明产品和要做的图位 |
| 让 Codex 出图 | 在 Codex 里打开本仓库，把图位卡粘给它。它按 [AGENTS.md](AGENTS.md) 执行 |
| 新增或修改产品事实 | 改 `products/<产品>/PRODUCT.md` |
| 补产品参考图 | 放进 `products/<产品>/ref/`，在产品卡和 [references/INDEX.csv](references/INDEX.csv) 各加一行 |
| 把认可的成图设为锚图 | 对 Codex 说「这张做锚图」 |
| 调整所有图共用的提示词段落 | 改 [standard/prompt_base.txt](standard/prompt_base.txt) |

## 目录

| 路径 | 内容 | 出图时读吗 |
|---|---|---|
| `AGENTS.md` | Codex 的执行规则 | 读 |
| `standard/CORE.md` | 核心视觉标准，不含具体产品 | 读 |
| `standard/QA.md` | 验收：三项一票否决加记录项 | 读 |
| `standard/CARD_SPEC.md` | 图位卡的字段和规则 | 写卡时读 |
| `standard/WRITER_GUIDE.md` | 给 Grok 的写卡指南 | 写卡时读 |
| `standard/WORKFLOW.md` | 三方工作流和问题定位 | 给人看 |
| `standard/prompt_base.txt` | 提示词的固定段落 | 脚本读 |
| `products/` | 每款产品一张产品卡和参考图 | 读对应的一张 |
| `references/INDEX.csv` | 全部可用参考图的索引 | 写卡时读，脚本核对 |
| `references/anchors/` | 认可过的自家成图，作风格锚 | 按卡取用 |
| `cards/` | 图位卡。`_TEMPLATE.md` 是空白模板 | 读对应的一张 |
| `tools/check_card.py` | 图位卡校验和提示词拼装 | 每张图运行一次 |
| `docs/` | 案例图库和旧版标准 | 不读 |
| `archive/` | 2.11 版规则和旧技能 | 不读 |

## 校验和测试

需要 Python 3.8 以上，只用标准库。

```sh
python tools/check_card.py cards/round10l/S5_clean.md
python tools/check_card.py --set cards/round10l
python -m unittest discover -s tools -p "test_check_card.py" -v
```

第一条校验单张卡，通过时打印要附带的图片、提示词和排版说明。第二条检查整套卡。第三条是脚本自身的测试，改过 `tools/`、`standard/`、产品卡或索引之后运行一次。

## 当前状态

- 已有产品卡：`round10l`（10L 圆款）、`clover_square`（方形四叶草款）。
- 已有锚图 5 张：v06 轮认可的清洗、换滤芯、搬运、安静四张，以及圆款清洗试样一张。
- 已有样卡 3 张：`cards/round10l/` 下的清洗、安静、材质。
- **待补：** `round10l` 只有一个角度的产品参考图。俯拍、侧面、空盆等机位出图时产品容易变形。
- **未验证：** 这套流程还没有用 Grok 和 Codex 实际跑过。建议先用 3 张样卡出图，和 `references/anchors/` 里的旧图对比后再扩展到整套。

## 其他工具

`tools/` 里另有 2.x 版留下的 `grade_check.py`、`composite_water_clarity.c`、`upscale_2x.swift`，以及 `scripts/image25.py`。它们不在 3.0 的出图流程里：明暗数值不再作为验收门槛，放大图不作为交付物。保留备用。

参考图用于理解构图和信息层级，不代表本品结构，也不附带第三方品牌素材的商业再利用授权。
