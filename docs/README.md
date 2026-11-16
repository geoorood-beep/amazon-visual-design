# docs：参考区

这个目录从 3.0 起是参考区。**出图时不读这里的任何文件。** 现行规则在仓库根目录的 `AGENTS.md` 和 `standard/`，与这里冲突的一律以现行规则为准。

## 还在用的

| 路径 | 用途 |
|---|---|
| `uta_style_v3/assets/key/` | 156 张案例图。其中 151 张已收入 `references/INDEX.csv`，图位卡按索引引用 |
| `uta_style_v3/assets/sheets/` | 34 张整页拼图。未收入索引，只供人查看 |

## 只作参考的

这些文件里有价值的内容已经提炼进 3.0。需要查来源、案例拆解或历史决定时再看。

| 文件 | 里面有什么 | 提炼到了哪里 |
|---|---|---|
| `UTA_STYLE_STANDARD.md` | 卖点画法库、机位库、表情库、案例逐张拆解、v06 方案 | 五条画面规则、光、机位、文字 → `standard/CORE.md`；案例分类表 → `references/INDEX.csv`；方形款事实 → `products/clover_square/PRODUCT.md` |
| `POKPET_10L_ROUND_DESIGN_DIRECTOR.md` | 圆款的事实、几何、18 个图位设想 | 事实和几何 → `products/round10l/PRODUCT.md` |
| `APLUS_CASE_LAYOUT_RULES.md` | A+ 案例的版式拆解 | 未提炼。写 P 位图位卡时可查 |
| `POKPET_APLUS_VISUAL_STANDARD_v02.md`、`SECONDARY_STORYBOARD_v1.md`、`PET_APPLIANCE_SELLING_POINT_VISUAL_STANDARD_v1.0.md`、`FEATURE_VISUAL_EXPRESSION.md`、`STYLE_WAPSI_01.md` | 更早的风格和分镜草案 | 未提炼 |
| `HD_IMAGE_WORKFLOW.md`、`IMAGE25_SETUP.md` | 高清处理和旧 API 入口 | 不在 3.0 流程里 |
| `uta_style_v3/v06_design_notes.md`、`uta_style_v3/tests/` | v06 设计说明和 v05 测试图 | 历史记录 |
| `作图需求填写表.md` | 旧的需求表 | 由图位卡取代 |

## 已知的旧规则冲突

下面几处在旧文件里互相矛盾，3.0 已经各选了一个，记在这里方便以后查：

| 冲突 | 旧文件里的两种说法 | 3.0 的取舍 |
|---|---|---|
| 字体 | 2.11 版 `AGENTS.md` 锁定 Avenir Next；UTA 标准用 Poppins | Poppins。用户认可的 v06 成图用的是它 |
| 暗部数值 | UTA 标准第 0 节第 5 条要求 p5 ≥ 0.12；同节下方和 §6F 要求 p5 ≤ 0.12 | 取消数值门槛，改为文字描述的光影要求 |
| 出图顺序 | §6H.8 要求先出整套缩略图；圆款方案第 23 节要求逐张 | 逐张 |
| 验收 | §6H.6 的 17 项全部可以触发重做 | 3 项一票否决，其余只记录 |
| 产品外形 | §6H.6 第 1 项把方形四叶草款写进了通用验收 | 产品外形只写在各自的产品卡里 |
