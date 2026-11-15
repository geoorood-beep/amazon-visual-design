# STYLE-APLUS-OIA-01｜oneisall A+ 页面标准

固定日期：2026-11-15  
状态：`FIXED_DEFAULT`  
代码：`STYLE-APLUS-OIA-01`  
中文名：oneisall A+ 页面  
英文名：`oneisall A+ Page`  
适用：宠物电器的 Amazon A+。喂水器、喂食器、猫砂盆在用户未指定其他 A+ 结构时默认采用。  
市场假设：Amazon US。用户未指定模块时，电脑端按 Premium A+ 的 `1464 × 600` 工作假设，手机端按独立构图的 `600 × 450`。账户没有 Premium A+ 时，改用标准 A+ `970 × 600`，并在 brief 写明原因。

本标准固定页面顺序、模块节奏和字号层级。它不授权复制 oneisall 的产品几何、商标、文案、参数、奖项或内部结构。色板与 `STYLE-WAPSI-01` 共用。Listing 副图的构图仍用 `STYLE-GALLERY-OIA-01`。

## 1. 证据与参考 ASIN

下列 ASIN 由所有者于 2026-11-15 用页面截图、按原生 1464 宽核对后批准为方法来源。本文件记录这次核对，不把截图中的句子、徽章或参数写成其他商品的规格。页面会变化；再引用在售状态、价格或评论数前须重新打开链接。

| 角色 | ASIN | 链接 | 取用的方法 |
|---|---|---|---|
| 感应喂水器，Premium A+，本标准的主要参考 | B0FN7FQ7RJ | https://www.amazon.com/dp/B0FN7FQ7RJ | 页面顺序、明暗交替、房间标签、深色剖视、英雄数字 |
| 不锈钢喂水器 | B0BN2Z5CDC | https://www.amazon.com/dp/B0BN2Z5CDC | 材质对比与水位细节如何放进宽幅场景 |
| 自动喂食器 | B0C5X2G933 | https://www.amazon.com/dp/B0C5X2G933 | 暖琥珀色板；不迁移其 A+ 文案与奖项 |
| 自动喂食器 | B0C5X4N132 | https://www.amazon.com/dp/B0C5X4N132 | 同系列的模块节奏；不迁移餐次、容量或媒体标志 |

`30 dB → 20 dB` 的曲线和 `16 in` 的标尺，只说明「一个大数字要靠参照物才看得懂」。本品没有对应证据时，不得写上这些数字。逐模块的屏幕像素记录在 `research/oneisall/VISUAL_CASE_STUDY.md`，文件索引在 `research/oneisall/README.md`。

## 2. 何时启用

```yaml
style_lock:
  id: STYLE-APLUS-OIA-01
  status: FIXED_DEFAULT
  applies_to: pet appliance Amazon A+ pages
  desktop_assumption: 1464x600 Premium A+
  desktop_fallback: 970x600 standard A+
  mobile: 600x450 independent composition
  palette: STYLE-WAPSI-01
  typesetting: layout tool after a text-free plate
  module_count: 7-9
```

- 用户说「做一套 A+」或同等含义，且商品是宠物电器时，页面结构默认用本标准。
- 每个模块仍按 `AGENTS.md` 第9.3.1节交付 1 张电脑端和 1 张手机端。9 个模块就是 18 张成品。第9.3.1节里的「6 张变 12 张」是举例，不是张数上限。
- 人物协作、教学或多人共同操作如果本身就是某个模块的沟通任务，该模块的人物关系用 `STYLE-HCEL-01`，页面顺序仍用本标准。
- 用户点名 `STYLE-NLEC-01`、`STYLE-PDMI-01` 或 `STYLE-WAPSI-01` 的某一子模式时，那个模块可以改用被点名的容器。整页顺序不因此拆掉。

## 3. 页面叙事顺序

一页按购买理解往下走，而不是把副图换成横版再排一次。

1. **Hero。** 两行标题，加 3–6 个卖点芯片或 bento 卡片。芯片只放已确认的主张。不够 6 个时不要凑满。
2. **一个大差异点。** 一个巨大数字，旁边有参照曲线或标尺，例如降噪曲线、地面距离尺。参照物帮助读数，不充当新的测试结论。
3. **按房间分的场景标签。** 宠物在视线高度。每个标签是一个房间或一个使用时刻。
4. **2–3 个深潜模块。** 每个模块一个点；或者同一个主题下 3 张卡。不要在一个深潜里塞进互不相关的卖点。
5. **深色技术剖视。** X 光式的解释层。内部被简化时标注 `Illustration` 或 `Schematic`。
6. **耗材、视频或 App。** 只有该商品确认有耗材周期、可公开视频或真实 App 时才做。没有则跳过，不画虚构界面。
7. **对比表。** 规则见第 8 节。
8. **品牌收束。** 规则见第 9 节。

与 Listing 副图讲同一卖点时，A+ 用更宽的场景、过程或参照物把该卖点讲清楚。复用副图里已经使用的画面逻辑和同一个数字，重新构图，不把 4:5 副图拉成横幅，也不重复纯白主图。

## 4. 节奏与模块尺寸

- 一页 7–9 个模块。轮播可以占到大约一半。每个轮播的第一张必须单独成立：遮住后面的标签或幻灯片，第一张仍能讲完自己的主张。关键信息不得只出现在后面的幻灯片或标签里。
- 大多数模块是 `1464 × 600`。Premium 的更高英雄模块可以更高，例如视频海报加 bento 网格用 `1464 × 1175`。选用更高模块时在 brief 写明 Seller Central 模块名和覆盖原因。
- 标签轮播在 600 高里分成约 66 px 的深色标签条，加约 534 px 的图片。标签文字由排版工具绘制。
- 明暗交替。全幅场景与奶油面板交替。奶油面板上的圆角卡片，圆角 24–32 px，阴影很淡。卡片压在照片上时，底的不透明度仍为 0.90，文字和图标不透明。淡阴影只分开卡片和背景，不变成产品周围的黑圈。
- 这一套圆角比 `STYLE-WAPSI-01` 里 16–20 px 的卡片更大，是本 A+ 标准的细化，不回溯去改副图芯片。
- 母版仍按 `AGENTS.md` 第0.3节争取 2×：`1464 × 600` 的目标不低于 `2928 × 1200`，`1464 × 1175` 不低于 `2928 × 2350`，`970 × 600` 不低于 `1940 × 1200`，手机端不低于 `1200 × 900`。工具返回更小的原生文件时，保留该文件并标注 `BELOW_TARGET_DELIVER_NATIVE`。禁止把小图放大后称作原生高清母版。

### 4.1 没有 Premium A+ 时

账户只有标准 A+ 时，电脑端改为 `970 × 600`。必须按 `AGENTS.md` 第7.4.5.1节重新构图，禁止把 1464 宽的文件横向压成 970。手机端仍然单独做 `600 × 450`。标题放在 52–72 px 区间里能放下的一端；放不下就换行或删掉次要句，不把副句缩到 36 px 以下。英雄数字在 970 宽上可以小于 110 px，但必须仍明显大于标题，并保持唯一主入口。

## 5. 电脑端字体（1464 宽）

精确英文、数字、芯片、曲线、标尺、标签和表格由排版工具加在无字底图上。图像模型不生成这些文字。字体继续是 Avenir Next Bold / 700 标题与英雄数字，Avenir Next Demi Bold / 600 卡片标题，Arial Regular / 400 副句。

| 角色 | 1464 宽 | 与旧起点的关系 |
|---|---|---|
| 标题 | 52–72 px，一行里只有一个强调色关键词 | 第10.1.1节从 52 px 起步。本标准允许到 72 px。超出后换行或缩短，不横向压字 |
| 英雄数字 | 110–160 px | 细化第10.1.4节 A+ 关键数字 48 px 的起点。只给该模块唯一主入口的那一个数字 |
| 副句 | 不小于 36 px | 参考页上约 28 px 的正文在手机上太小，禁止照搬。第10.1.1节的 24 px 副标题不用于本标准的电脑端副句 |

强调色只用在关键词和这个英雄数字上。使用本项目暖琥珀色板时，强调色 `#F47A21`，深咖啡 `#25170F`，奶油 `#F1EAE0`，白字 `#FFFFFF`。面积仍约 3%–8%。钢材、水面和皮肤保持中性，不被橙色染色。

标题位置继续参考第10.2节：1464×600 上字顶 115 px、距左 120 px，允许按产品位置向内或居中。更高的 Premium 模块按同一比例关系重排，不把 600 高的坐标原样照搬。

### 5.1 四款 A+ 的实测配方（v2.9）

2026-11-15 裁切文件的高度：常规模块 1464×600；B0FN7FQ7RJ Hero 为 1464×1175；对比表 701–710；品牌故事 624–626。带顶栏的轮播，黑条约占 66 px，下面约 534 px 是照片。

```yaml
layout_grid_1464:
  text_column: 35%-45% when split
  image_column: remaining, may bleed
  tab_bar_height: 66 px
  card_radius: 24-32 px
  card_gap: about 16-24 px
  card_shadow: faint, not a product vignette
  three_cards: equal width, title inside at top left
  first_carousel_slide: must stand alone
lighting_recipe:
  scene: same window key as the gallery standard
  dark_module: night interior or deep blue field
  schematic_blue: inside the illustration only
  alternation: light module then dark module
  steel_and_skin: neutral, accent orange stays on type
type_scale_1464:
  headline: 52-72 px
  hero_number: 110-160 px
  subline_minimum: 36 px
  accent: one word or the hero number, "#F47A21"
  font: Avenir Next Bold / Demi Bold, Arial for the subline
camera_presets:
  scene_module: pet eye level, product and pet together
  spacing_claim: top-down only when the claim is a measured distance
  cutaway: orthographic section, labelled Illustration
do_not:
  - cyan-lime gradient as a second brand color
  - health lines, TOP 1, patent seals, BPA seals
  - SilentFlow or any competitor trademark
  - sales counts, award logos, media logos
  - body copy under 36 px on the 1464 canvas
```

左文右图时，文字不压住宠物的头和出水口。三张卡只服务同一个主题。深色模块的冷蓝留在剖视里，场景本身仍用暖灯。同一数字若已在图库出现，A+ 放大它，不改成另一个数。

## 6. 手机端

Amazon 会把电脑端缩到大约 390 pt 宽。因此电脑端副句不得小于 36 px，而且每个模块仍要单独做 `600 × 450`，不能靠平台缩放代替。

手机端只保留：标题、一个数字或一个视觉主体、最多一行副句。芯片条、多卡和表格的其余行删掉或改成这一行能说完的那一个事实。字顶 45 px、距左 80 px，按第10.2节。构图按 4:3 重排，满版，不留白边，不把电脑端缩小后贴上。

## 7. 技术层、耗材与 App

- 剖视保持部件数量和连接关系与已确认结构一致。简化的水路、滤层或泵用 `Illustration` 或 `Schematic` 标出。解释层不是真实的透明外壳。
- 感应距离若已确认，用标尺或地面刻度表示这个数字。不用发光锥、激光或看起来像实测雷达范围的弧线。未确认的停止条件不补写。
- 耗材模块只写已确认的更换对象和周期。视频模块只放已有的可公开视频封面。App 模块只复现已确认存在的界面字段，不增加健康监测或虚构通知。

## 8. 对比

两种对比不要混在一张图里。

- **图片对比。** 只做事实层面的「相对普通塑料」或同等的无名器物。本品一侧暖色受光，对侧去饱和。不出现任何品牌名、商标或可识别的竞品外形。标签写明比较的是哪个部位。
- **内置对比表。** 只放自有品牌的型号，当前产品排在第一列。行序为评论、价格、关键规格，单元格用 ✔ 或 /。评论数和价格必须是当时可核对的数据；没有核对就删掉该行，不填估计值。规格行只放两侧都有来源的项目。不把竞品列进这张表。

## 9. 品牌收束

事实已经核实时，可以用人物与宠物的照片，加上统计、奖项、服务和店铺入口卡片。每一项都要有来源。未核实时，只保留品牌一句、产品一句，以及 Amazon Store 的店铺入口。不写数字、不放奖杯、不放媒体标志、不放销量。

店铺入口指 Seller Central 提供的 Amazon Store 模块。不写站外网址、邮箱、社交账号或二维码。这与 `AGENTS.md` 第9.3节禁止站外联系方式是同一条规则。

## 10. 禁止照搬

- 健康用语：`healthier`、`hygienic`、`safe for pets`、`purifying`，以及肾脏、杀菌、疗效。
- 无法核实的徽章：`TOP 1`、`#1`、专利、销量、奖项、媒体标志、保证书。
- 资料里没有的功能、天数、体重、续航和传感器型号。
- 竞品资产和商标。专有名称例如 `SilentFlow™` 不得出现，也不得改写成一个新的仿名。
- 纯白主图的重复使用。A+ 不从主图裁一块出来当模块。

## 11. 与既有 A+ 规则的关系

| 既有规则 | 本标准如何配合 |
|---|---|
| 第9.3.1节 1464×600 与独立的 600×450 | 默认模块仍是这一对。更高的 Premium 模块和 970×600 回退都要在 brief 标明，并各自重新构图。手机端内容减到标题、一个数字或一个视觉、最多一行 |
| `STYLE-WAPSI-01` 色板 | 共用 `#F47A21`、`#25170F`、`#F1EAE0`。WAPSI 的三种子模式可以放进单个模块，整页顺序以本标准为准 |
| 排版工具出字 | 无字底图先完成。曲线、标尺、表格和芯片都是后期排版 |
| 不编造声明 | 参考页上的曲线数值、奖项和 App 不能迁移。第10节的禁用词即使参考页上有，也不写 |
| 第0.3–0.5节原生与放大 | 2× 是质量目标，不是开工门槛。实际像素、重采样次数如实记录 |
| 第7.10节宠物四项 | 场景模块仍记录表情、焦点、家具色板和光层次。标签页里的宠物在视线高度，饮水时脸可见，安静场景的睡眠宠物在产品之后 |
| 副图标准 | 同一主张复用 `STYLE-GALLERY-OIA-01` 的动作和同一个数字，改成宽幅。副图的三枚底栏芯片不原样铺满 A+；Hero 可以有 3–6 个已确认芯片 |

## 12. 案例卡

案例名：oneisall Premium A+ 页面（方法案例）  
适合目标：宠物电器 A+ 的整页叙事  
画面结构：Hero 与芯片、一个带参照的大数字、房间标签、少量深潜、深色剖视、条件式耗材模块、自有型号表、品牌收束  
背景/色板：奶油面板与深色技术模块交替；强调色只给关键词和数字  
光线与镜头：宽幅场景沿用副图的窗光和宠物视线高度；剖视模块用深色底和局部暖色说明  
卖点表达：每一模块一个主入口；轮播第一张独立成立  
可借鉴：明暗节奏、标尺或曲线帮助读数、第一张幻灯片能单独使用  
不可照搬：商标、健康承诺、TOP 1 与媒体标志、竞品专有名、28 px 正文  
本品转化方式：先锁 Product DNA 和账户是否有 Premium A+，再按第3节跳过没有证据的模块  
风险：把参考曲线的数字写成本品数据；手机端只缩小电脑端；对比表列进竞品  

来源：第1节，所有者 2026-11-15 按 1464 原生宽度截图核对。B0FN7FQ7RJ 是主要参考。

## 13. POKPET 10L A+ 计划示例

本计划是所有者在 2026-11-15 后续批准里指定的 POKPET 10L 示例，不是实验室报告，也不是 `docs/FEATURE_VISUAL_EXPRESSION.md` 那套 5L 概念喂水器。概念文档里的 5L、顶盘限定和电池供电仍然不得套过来。本示例里的数字只在这套成套计划中使用；副图若讲同一主张，复用同一个数字和同一句英文，不另造一套。

有线与无线仍是两个变体。开做前锁定其中一个。历史四宠图上的蓝色电池光波，若是示意图层，不得画成真实发光硬件。

没有第二个自有型号时不做 A9，整页为 9 个模块，落在 7–9 的区间里。有第二个自有型号时保留 A9，并在 brief 写明本页为 10 个模块的原因。本示例不单设 App 或视频模块。

明暗顺序：浅、中、浅、深、浅、深、浅、浅、表、品牌。

证据等级一律写 `owner-specified worked example, 2026-11-15`。不得据此添加检测机构、媒体标志或健康承诺。三个模式的具体名称此笔记未给出，排版前必须先锁定名称；不得用参考喂食器的 2/4/6/8 小时或自拟模式名填空。

| 模块 | 调性 | 沟通任务 | 电脑端 1464×600 | 手机端 600×450 | 英文 |
|---|---|---|---|---|---|
| A1 Hero | 浅 | 靠近出水，并扫读四项已指定主张 | 两行标题。四枚芯片，不凑到六枚。产品在暖色室内，宠物正走向它 | 只留标题和行走中的宠物与产品。四枚芯片不进手机端 | `Pet Approaches. Water Starts.` 芯片：`304 Stainless Steel` / `1 m Motion Sensing` / `Under 25 dB` / `3 Flow Modes`。强调词 `Water` |
| A2 感应 | 中 | 1 m 的感应距离，以及约 10–15 秒的后续水流 | 英雄数字 `1 m`，110–160 px。旁边地面标尺，标注约 `3.3 ft`。副句说明后续水流。标尺不是发光探测锥 | 只留 `1 m` 和一行 `About 3.3 ft` | `1 m`。副句 `About 3.3 ft. Flow continues for about 10–15 s.` |
| A3 模式 | 浅 | 三种水流模式是同一主题 | 奶油面板上三张圆角卡。名称锁定后再排字。当前项可以更强调，但不发明第四种 | 只留标题和一种模式，或一行「3 Flow Modes」 | 标题 `Three Ways the Water Flows.` 卡片标题等待锁定 |
| A4 安静 | 深 | 夜间运行噪音 | 海军蓝或梅子色环境，暖灯打在产品上，宠物在后方睡觉。机身上 `<25 dB` | 只留 `<25 dB` 和短标题 | `<25 dB`。标题 `Quiet after Dark.` |
| A5 过滤与拆洗 | 浅 | 滤芯周期，以及泵和饮水盘可拆 | 一个主题。主数字或主句是 `1–2 weeks`。剖视标注 `Illustration`。泵与盘可拆作为同一主题的副句，不另开卖点 | 只留 `1–2 weeks` 和一行可拆说明 | `Every 1–2 Weeks.` 副句 `The pump and tray come out to clean.` 旁注 `Illustration` |
| A6 保护 | 深 | 低水位关机、防干烧、水位窗 | 深色底上同一主题的信息，加一个对准真实水位窗的放大镜。不写绝对安全 | 只留水位窗，或一行 `Low-Water Auto Off` | `Low-Water Auto Off` / `Dry-Run Protection`。手机端二选一 |
| A7 材质 | 浅 | 304 相对普通塑料 | 图片对比。本品暖色，对侧去饱和的无名塑料件。不出现竞品商标 | 只留标题和钢件局部 | `304 Stainless Steel`。对侧 `Ordinary Plastic` |
| A8 生活 | 浅 | 宠物愿意喝 | 宽幅场景，复用副图的饮水动作和真实尺度，脸可见，产品最清晰。不贴白底主图 | 脸和产品仍完整，一行标题 | `The Bowl They Actually Use.` |
| A9 对比表 | 表 | 只在有第二个自有型号时比较 | 当前产品在第一列。行序为评论、价格、关键规格，用 ✔ 或 /。评论和价格未核对就删行 | 手机端不做缩小的整表。只留当前产品名和一行最关键规格 | 表头用两个自有型号名 |
| A10 品牌 | 品牌 | 品牌一句和产品一句 | 无统计、无奖项、无销量。有核实的人物与宠物照片才使用照片；否则用产品与暖色空间。店铺入口只用 Amazon Store | 品牌一句加产品一句 | 品牌句与产品句待品牌规范锁定。不写数字 |

A2 的 `3.3 ft` 是所有者给出的 1 m 约数，不是第二次测量。A5 的剖视在内部结构未逐件核对前保持示意标注。A6 的关机与防干烧按本示例的指定功能表达，不升级成「绝不干烧」或医疗安全。

## 14. 执行记录

每个模块、每一端单独记录：

```yaml
style_lock_id: STYLE-APLUS-OIA-01
module_id: A1
desktop_canvas: 1464x600
mobile_canvas: 600x450
premium_override: NONE
tone: light | mid | dark | chart | brand
primary_entry: UNKNOWN
hero_number_and_source: NONE
carousel_first_slide_stands_alone: NOT_APPLICABLE
mobile_content: headline + one number or visual + at most one line
typesetting: layout tool on text-free plate
native_resolution_gate: MET_TARGET | BELOW_TARGET_DELIVER_NATIVE
```

负向提示词在副图基线之外增加：white main image repeated、competitor trademark、SilentFlow、healthier、hygienic、safe for pets、purifying、TOP 1 badge、media logos、award badges、generated text、desktop layout scaled down for mobile、letterbox bars、invented app UI。
