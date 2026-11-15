# oneisall A+ 页面研究（From the brand / Product description）× POKPET 10L A+ 方案

日期：2026-11-15 · 研究对象：B0BN2Z5CDC（2L 不锈钢圆形饮水机）、B0FN7FQ7RJ（2.2L 无线饮水机，Premium A+）、B0C5X2G933（双猫定时喂食器）、B0C5X4N132（5G WiFi 双猫喂食器）

## 0. 素材来源（如实记录）
- **原图抓取失败**：2026-11-15 用 curl 请求 `https://www.amazon.com/dp/<ASIN>`，带桌面 Chrome UA 和 `Accept-Language: en-US`。4 个 ASIN 都返回 3,781 字节的验证码页（"Captcha" / "automated access"），没有任何 `aplus-media` URL。没有尝试绕过，HTML 存档在 `aplus_hd/html/`。
- **改用页面截图**：`/workspace/oneisall_refs/<ASIN>/aplus_*.png`，1920×1071，每张向下滚动 720 px。经过像素比对，两张截图之间的重叠完全一致（差值 0.0）。
  - A+ 内容列在截图中的 x 范围是 220–1684，宽 1464 px，所以裁出来的模块就是 1464 宽的原始像素，高度可以直接量。
- **懒加载导致的缺口**：B0BN2Z5CDC、B0C5X2G933、B0C5X4N132 的第 1 张截图拍摄时首图还没加载。所以拼接从 aplus_02 开始，这 3 个页面的首图顶部被截掉，文件名标 `TOPCUT`，高度未知。
- **轮播只拍到当前页**：其他页没有拍到，tab 名称记录在下表。截图是 JPEG/PNG 屏幕像素，不是原始上传文件，画质略软。
- 模块裁切：`aplus_hd/<ASIN>/NN_*.png`。整页拼接：`aplus_hd/<ASIN>/_full_strip.jpg`。脚本：`aplus_hd/stitch.py`、`cut.py`。

## 1. 逐 ASIN 模块清单（页面顺序）
尺寸为 1464 宽下的实测像素。"dark" 或 "light" 指模块的主色调。

### B0BN2Z5CDC — 2L 不锈钢饮水机（标准轮播型）
| # | 模块类型 | 尺寸 | 标题 / 文案 | 版式 | 光线 / 角度 | 数字 / 图标 | 叙事角色 |
|---|---|---|---|---|---|---|---|
|01| 全宽 hero 横幅（light，橙色色块） | 1464×≥371（顶部截掉） | "Stainless Steel Cat Water Fountain" / "Make your cat healthier"（健康暗示，不可学） | 左 55% 是橙底白字加 4 个圆形图标（Visible Window、LED Light、2L Capacity、3 Packs Filter），右 45% 是猫在喝水 | 暖色室内，平视偏高 | 黄色圆形图标配两行短标签 | Hook：品类加 4 个卖点速览 |
|02| 全宽轮播加热点 tab（dark） | 1464×600 | "Ultra Quiet Fountain"；tab "1 <30dB Quiet" / "2 304 Stainless Steel" | 标题在左上，中间是一条声波曲线：60dB 冰箱图标 → **30dB** 产品 → 70dB 摩托图标；右侧是白色胶囊 tab | 夜景，暖色台灯，猫睡觉，产品在近景 | 大号数字 30dB 嵌在曲线里，对比参照物用小图标 | 关键差异点：安静 |
|03| 全宽单图（mid-dark） | 1464×600 | "Easy to Clean" / "BPA Free & Dishwasher Safe" | 白字在左下，产品放在洗碗机碗篮里 | 冷暖混合，俯视 30° | 无 | 功能深挖：清洁 |
|04| 文字标题（Amazon 原生 heading） | 1464×118 | "Faucet Design Attracting Cats to Drink More Water" | 黑字左对齐 | — | — | 段落标题（SEO 文本） |
|05| 轮播（2 页，light 驼色） | 1464×600 | "Faucet Design" / "Attracting pets to drink water"，手写体 "Mom, I want to drink water" | 左上标题；中间三张圆角卡片（两张猫舔水龙头加产品）；右侧大猫头舔嘴 | 暖棚拍 | 星形闪光装饰 | 情绪、生活方式 |
|06| 轮播（3 页，light） | 1464×600 | "Clearly see the remaining water level"（棕橙色） | 文字左上占 40%，产品特写占右 60% 并出血 | 暖侧光，低角度近景 | MAX/MIN 窗口本身就是视觉 | 功能深挖：水位窗 |
|07| 视频轮播（Amazon 原生视频加文字） | 1464×≈522 | "How to Assemble?" | 左 55% 视频，右侧白底文字 | 开箱，白手套 | — | 使用和信任 |
|08| 轮播（3 页，light）加半透明文字框加 CTA | 1464×598 | "Muti-layer filtration system"（原文拼错）/ "buy additional 8 filters…" / [Learn More] | 左侧深灰半透明圆角文字框，右侧产品加猫加 "8 Pack" 橙色滤芯卡 | 窗光暖，木地板 | 漂浮气泡加叶子（暗示净化，不可学） | 耗材复购导流 |
|09| From the brand（品牌故事轮播） | 1464×625 | "oneisall \| Transform How You Pet"，"5,882,669+ Units Sold Globally / 1,000+ Top Media Highlights / 89 Invention Patents"，Awards，"We're Here to Help"：2-Year Guarantee / 24/7 Support / Free Shipping | 左侧人宠合照，右侧横向滑动白卡 | 暖橙黄 | 大号数字统计加奖项 logo | 品牌信任 |

### B0FN7FQ7RJ — 2.2L 无线饮水机（Premium A+，最值得学）
| # | 模块类型 | 尺寸 | 标题 / 文案 | 版式 | 光线 / 角度 | 数字 / 图标 | 叙事角色 |
|---|---|---|---|---|---|---|---|
|01| Premium hero（视频加 bento 网格，一张长图） | 1464×1175 | 角标 "TOP 1 The Leading Brand in Smart Pet Products"（不可学）；logo；"Hygienic, Wireless / Flexible Placement" / "The Quietest and Easiest to Clean" | 上半部分是视频封面（标题在左，猫在右侧大理石台面喝水）；下半部分是 6 格 bento 圆角卡片：45-day Runtime 剖面、Three water output modes（Timer / Motion Sensor / Constant 三个图标）、30dB Others → **20dB**、Track Water Level、Easy to Maintain 爆炸图、Smart Indicator | 暖色厨房，平视略高 | 每张卡片只讲一个点：卡片标题加一张图或一个大数字 | Hook 加全卖点地图（相当于目录） |
|02| 场景 tab 轮播（顶部黑色 tab 条） | 1464×600（tab 66 加图 534） | tab：On the Windowsill / In Kitty's Playroom / In the Kitchen / In the Living Room / In the Bedroom；"Sip Where Cats **Relax**"（Relax 用强调色）/ "Cord-free for flexible placement…" | 左 60% 是猫加产品，右 40% 文字 | 窗边自然暖光，猫眼高度 | 无 | 生活方式和场景 |
|03| 技术轮播（dark 深蓝）加热点 tab | 1464×600 | "Latest SilentFlow™ Pump"；3 个圆形图标（Ultra Quiet、Easy to Clean、Safe for Pets）；tab "1 Recharge 30d Battery / 2 Triple Water Modes"；"PATENTED US PROTECTED" 徽章 | 左 45% 标题加图标，右 55% 是透明 X 光剖面 | 冷蓝科技光 | 渐变青绿圆形图标 | Proof / 技术 |
|04| tab 轮播（dark） | 1464×600 | tab：20dB Quietness / 5-layer Filtration / Portable & Wireless / Effortless to Clean；"So Quiet, You'll Hear Nothing At All" / "Advanced fluidics effectively reduce noise" | 左侧标题加 30dB Others → **20dB** 曲线，右侧夜景猫加产品 | 暗室，暖色点光 | 大号数字加对比曲线（同一套视觉在 hero 里出现过） | 关键差异点深挖 |
|05| 轮播（3 页，light）加 CTA 按钮 | 1464×600 | 滤芯分层爆炸圆角卡，加 "Get Filters" 购物车按钮 | 左侧猫趴在桌上看滤芯，右侧卡片加按钮 | 暖客厅 | 箭头示意水流 | 耗材复购 |
|06| 对比表（Amazon 原生 comparison chart） | 1464×≈702 | "Explore More From oneisall"；行：Customer Reviews / Price / Capacity / Material / Three Water Modes / Filter per pack / Filter System / Quiet Design / Cordless/Cord | 白底产品图（节日装饰）加 Add to Cart | — | ✔ 和 / 表示有无 | 只和自家产品横向对比，导流 |
|07| From the brand | 1464×625 | 同 B0BN2Z5CDC，第二张卡是媒体背书（Yahoo、People、NBC…） | — | — | 统计数字 | 品牌信任 |

### B0C5X2G933 — 双猫定时喂食器（tab 轮播型）
| # | 模块 | 尺寸 | 标题 / 文案 | 版式 | 光线 | 数字 / 图标 | 角色 |
|---|---|---|---|---|---|---|---|
|01| 全宽 hero（dark 暖） | 1464×≥364（顶部截掉） | 看不到标题 | 两只猫对称吃饭，产品居中 | 暖色木地板，猫眼高度 | — | Hook |
|02| tab 轮播（tab：Peaceful Eating / 100% Balance），light 米色 | 1464×600 | "Perfect Spacing for Comfy Meals" / "Helps Prevent Cats from Fighting Over Food" | 左 35% 文字，右 65% 圆角俯拍图配 "16 in" 标尺 | 柔和俯拍 | 白色大号数字嵌在地面上 | 差异点 1 |
|03| tab 轮播（tab：20 Cups Capacity / Easy Setup / Kibble ≤0.5 inch / Tips for Feeding），dark | 1464×600 | "Up to **10-Day** Tank Capacity"（数字加粗） | 标题居中在顶部，产品居中，两只猫在两侧 | 金色逆光，平视 | "20 CUPS" 橙色字直接印在料仓上 | 差异点 2 |
|04| tab 轮播（tab：Lock-in Freshness / Cat-Proof / Outage Schedule Storage），light | 1464×600 | "**Freshness** in Every Bite"；3 卡：360° Reinforced Top Lid / Protects Against Moisture / Auto-Lock Keeps Pests Out | 标题居中，下方 3 张等宽圆角卡，卡片标题写在图内左上 | 暖棕棚拍 | 局部蓝色高亮表示结构 | 功能深挖（3 栏卡片） |
|05| 对比表 | 1464×≈710 | "Choose oneisall Related Item Based on Your Needs"；行：Reviews / Price / Feature / For Cats / Wi-Fi / Power Source / Capacity / Meals/Day / Max Kibble Size | — | — | 规格对比 | 自家导流 |
|06| 品牌信任轮播（2 页） | 1464×600 | "Trusted by / 5,882,669+ Pet Families."，加 5 个奖项 logo | 文字在左下，人、猫、狗在沙发上 | 暖逆光 | 超大数字 | 信任 |
|07| From the brand | 1464×625 | 同上，第二、三卡是 "More Feeder Options / Visit the Store" | — | — | — | 品牌和店铺导流 |

### B0C5X4N132 — 5G WiFi 喂食器
| # | 模块 | 尺寸 | 标题 / 文案 | 版式 | 光线 | 数字 / 图标 | 角色 |
|---|---|---|---|---|---|---|---|
|01| 长 hero（暖棕）加深色信息卡 | 1464×≥964（顶部截掉，左上角有 "...on Amazon." 橙色缎带角标） | 4 行图标清单：5G/2.4G WiFi、5L Capacity、16-inch Comfy Space、Scheduled Feeding | 上半部分是两只猫加产品场景；下半部分是深色圆角大卡，左侧女性看手机，右侧 4 个橙色圆形图标加白字 | 暖室内，平视 | 橙圆白线图标 | Hook 加卖点速览 |
|02| tab 轮播（tab：Slow Feeding / Feeding Logs / Device Sharing），dark 暖 | 1464×600 | "Slow Feed for Healthy Tummy"（健康暗示）/ "10-second portions prevent cats from gulping" | 标题在左上，App 截图浮层（Slow Feed 开关）叠在场景上 | 暖低角度 | UI 浮层代替图标 | 差异点 |
|03| tab 轮播（tab：Opposing Bowls / Recommended Kibble Size / Stay Fresh / Daily Intake） | 1464×600 | "Peaceful Mealtime Spacing"；"16 inch" 标尺胶囊 | 标题居中，俯拍，标尺横穿画面 | 俯拍暖光 | 数字放在黑色胶囊里 | 功能深挖 |
|04| App 下载（light 米色） | 1464×600 | "Download the App to Control Oneisall 5 GHz Smart Pet Feeder"；App Store / Google Play 徽章、二维码 | 标题居中，左侧手机，右侧徽章加二维码 | 棚拍 | — | 使用指引 |
|05| 对比表 | 1464×≈701 | 同 X2G933 | — | — | — | 导流 |
|06| 品牌信任轮播 | 1464×600 | "Trusted by 5,882,669+ Pet Families." | 同上 | — | — | 信任 |
|07| From the brand | 1464×624 | 同上 | — | — | — | 品牌 |

## 2. 综合出的 A+ 标准

### 2.1 页面叙事顺序（4 个页面共同的骨架）
1. **Hook（hero）**：一张场景大图，加品牌 logo、一句双行大标题和 3–6 个卖点速览（图标或 bento 卡）。Premium 版用 1464×≈1000–1200 的长图，把卖点地图一次讲完。
2. **关键差异点**：做成一个全幅 600 高的模块，配一个超大数字（20dB / 30dB / 16 in / 10-Day）和参照物曲线或标尺。
3. **场景和情绪**：tab 轮播展示不同房间、不同时段，宠物在猫眼高度享受产品。
4. **功能深挖** ×2–3：每个模块只讲一个点，或者用 3 栏卡片讲同一主题下的 3 个子点（Freshness → 3 卡）。
5. **Proof / 技术**：深色科技风剖面或 X 光透视，加 2–3 个图标。
6. **耗材 / 配件 / 使用**：滤芯复购、组装视频、App 下载。
7. **对比表**：只放自家型号的规格横向对比，用于导流。
8. **品牌信任**：品牌故事轮播，包含统计、奖项、服务承诺、店铺入口。

### 2.2 模块节奏
- 高度统一为 **1464×600**，hero 例外，可以更高。tab 轮播 = 66 px 黑色 tab 条加 534 px 图。
- **明暗交替**：light hero → dark 差异点 → light 功能 → dark 技术 → light 耗材 → 白色对比表 → 暖橙品牌，基本不会出现两个同色调模块相邻。
- **出血与卡片交替**：全幅出血的场景图和"米色底加圆角卡片"的信息模块交替出现。卡片圆角约 24–32 px（1464 宽下），阴影很弱。
- 每页大约 7–9 个模块，其中 4–6 个是轮播。轮播首页必须单独成立，因为大多数人只看首页。

### 2.3 字号（以 1464 宽为基准）
| 元素 | 1464 桌面 | 换算到手机（约 0.27×，1464→≈390 pt） | 建议最小值 |
|---|---|---|---|
| Hero 标题（Poppins / Mulish 类几何无衬线，800） | 60–72 px | ≈17–19 pt | 56 px |
| 模块标题 | 52–64 px | ≈15–17 pt | 48 px |
| 超大数字 | 110–160 px | ≈30–43 pt | — |
| 副标题 | 30–36 px | ≈8–10 pt | **36 px**（oneisall 的 28 px 正文在手机上偏小，不要学） |
| 图标标签 | 26–30 px | ≈7–8 pt | 30 px，或者在手机版去掉 |
- 标题以白字或咖啡色为主，**一个关键词用强调色**（Relax、10-Day、Freshness），并且加粗。

### 2.4 手机端
- Amazon 手机端会把 1464 宽的图等比缩小，小字基本看不清。oneisall 的做法是标题足够大，并且把卖点放进图标和大数字里。
- 我们的规范：每个 Premium 模块另外做一张手机图（600×450，按项目 v2.7 规格，上传前在 Seller Central 核对）。手机图只保留标题、一个数字或一个视觉、最多一行副标题，文字放在图片上方 1/3。
- 不要依赖 tab 文字和轮播第 2、3 页传达关键信息。

### 2.5 对比表规范
- oneisall 的对比表**只放自家型号**，用 Amazon 原生 comparison chart，第一列是当前商品。
- 行顺序：评价 → 价格 → 核心规格（容量 / 材质 / 模式 / 滤芯 / 噪音 / 供电）。用 ✔ 或 / 表示有无。
- 不点名竞品，也不放竞品图。图片版"vs 普通塑料"只做材质和功能的事实对比。

### 2.6 品牌故事模块
- 左侧是人宠合照（品牌情绪），右侧是横滑白卡：统计数字、媒体和奖项、服务承诺、品牌介绍、店铺入口。
- POKPET 现在**没有**已确认的销量、奖项、专利、质保或服务承诺，所以只能做品牌理念、产品线和店铺入口这类卡片，不写任何数字。

### 2.7 与主图 / 副图的重复度
- oneisall 的 A+ 大量复用副图视觉（20dB 曲线、模式图标、剖面、水位窗），但改成横版构图，并补充场景、tab 和导流。
- 结论：**同一个视觉语言、同一套数字，但用不同的构图和场景**。A+ 不再重复主图的白底图。

### 2.8 不要照搬
- 健康和功效暗示："Make your cat healthier"、"Healthy Tummy"、"Hygienic"、"Safe for Pets"、净化气泡和叶子、"Drink More Water"。
- 无法核实的徽章和数据："TOP 1 The Leading Brand"、"#1 on Amazon"、"PATENTED"、"5,882,669+"、奖项 logo、媒体 logo、"2-Year Guarantee"、"24/7 Support"。
- 我们没确认的功能："BPA Free"、"Dishwasher Safe"、无线 / 电池、容量天数、MAX/MIN、"Quietest"。
- 竞品资产：任何 oneisall 的图片、logo、文字原句、™ 名称（SilentFlow™），以及 Poppins 加橙色的整套品牌皮肤（我们用 Mulish 800 加咖啡和琥珀色，强调色 #F47A21 只用于关键词）。
- 原文中的拼写错误（"Muti-layer"），以及 "Mom, I want to drink water" 这类手写体口语。

## 3. POKPET 10L A+ 模块方案（只用 copy.md v03 已确认事实）
规格：Premium A+ 桌面 1464×600（hero 可以做 1464×600 或更高的长图，视账号权限而定），每个模块配一张 600×450 手机图。如果账号没有 Premium，退回标准 A+ 970×600 / 970×300。
- 视觉统一：基于 v02 的 `raw/main_v02_base.png`（四叶草窗、方块控制头在后右、不做镜像），光线为暖色电影感，宠物在猫眼高度。
- 所有文字用 PIL 排版。色板：米色 #F1EAE0、咖啡 #25170F、琥珀 #9A6638、强调 #F47A21、灰褐 #6F6255。

| # | 模块（色调） | 桌面版式 | 文案（英文） | 手机 600×450 | 叙事角色 |
|---|---|---|---|---|---|
|A1| Hero 全幅（light 暖） | 左 40% 是标题和 4 个圆角图标 chip，右 60% 是厨房地板上虎斑猫走近产品 | "POKPET"（logo 待提供，暂用排版文字）/ "Pet Approaches. **Water Starts.**" / chips: 304 Stainless Steel · 1 m Motion Sensing · Under 25 dB · 3 Flow Modes | 标题加产品，chips 改为 2×2 | Hook 加卖点地图 |
|A2| 感应差异点（mid，地面光环） | 左侧标题和超大 "**1 m**"，右侧猫走进地面上的同心光环 | "Senses Your Pet Within **1 m**" / "(~3.3 ft) · keeps flowing ~10–15 s after your pet leaves" / footnote "Sensing range illustrative." | "1 m" 加一行副标题 | 关键差异点 |
|A3| 三模式（light 米色，3 栏卡片） | 标题居中，下方 3 张圆角卡 | "3 Modes, **Your Routine**" / NORMAL – Always-on flow [待确认] · INDUCTION – Flows when your pet is within 1 m · TIMER – Runs in 15-minute intervals | 3 张卡竖向排列，只留模式名加 4 个字以内说明 | 功能深挖 |
|A4| 安静（dark 夜景） | 左侧标题加超大 "**<25 dB**"，右侧暗卧室里猫在睡觉、产品在近景 | "Quiet Flow, **Sound Sleep**" / "Pump and water noise under 25 dB" | "<25 dB" 加标题 | 第二差异点（明暗交替） |
|A5| 过滤加清洁（light，2 卡） | 左卡：剖面示意加 "Replace about every 1–2 weeks"，标注 "Illustrative cutaway"；右卡：泵和水盘提起 | "**Filtered** Flow, Easy Care" / Filter – Replace about every 1–2 weeks · Pump & water tray – Lift out for washing | 两卡上下排列 | 功能深挖和维护 |
|A6| 安全保护（dark 科技，深咖色） | 左侧标题加 2 个图标，右侧四叶草水位窗放大镜 | "Smart Protection, **Built In**" / Low-water auto power-off · Pump dry-run protection · See the water level through the clover window | 放大镜加 2 个 chip | Proof / 技术 |
|A7| 304 vs 普通塑料（light，事实对比） | 左右两个圆角面板加 VS，下方 3 行 ✓ / • | "304 Stainless Steel **vs Ordinary Plastic**" / ✓ 304 stainless steel · ✓ Flowing, filtered water · ✓ Motion-sensing INDUCTION mode vs • Plastic · • Still water · • No filter / footnote "Material and feature comparison only." | 只保留面板和 3 行 | 对比（不点名竞品） |
|A8| 生活方式场景（light 暖，可做 tab 轮播：Kitchen / Living Room / Bedroom） | 全幅出血，文字在右 35% | "Fresh, **Flowing Water**" / "Filtered and quiet, right where your pet drinks" | 场景加标题 | 情绪收尾 |
|A9| 原生对比表（只在 POKPET 有第二个 SKU 时才用） | — | 行：Material（304 stainless steel）/ Modes（NORMAL · INDUCTION · TIMER）/ Sensing（1 m）/ Noise（Under 25 dB）/ Filter（Replace every 1–2 weeks）/ Capacity（TBC） | — | 导流（目前没有 SKU，可以先不做） |
|A10| From the brand（品牌故事） | 左侧人宠合照，右侧卡片：品牌理念 / 产品线 / Visit the Store | "POKPET" / 品牌一句话（待用户提供）；**不写**销量、奖项、质保 | — | 品牌信任 |

- 节奏：light → mid → light → **dark** → light → **dark** → light → light（场景）→（表）→ 品牌。
- 每个模块只放一个大数字。全部数字只来自已确认事实：1 m、~3.3 ft、10–15 s、15-minute、25 dB、1–2 weeks、304。
- 还需要用户提供：logo 文件、品牌一句话、NORMAL 措辞、容量和尺寸（如果要做规格模块）、是否有 Premium A+ 权限、是否有第二个 SKU（对比表）。

## 4. 文件
- 模块裁切：`aplus_hd/<ASIN>/NN_*.png`（1464 宽，截图像素）。
- 联系表：`sheets/<ASIN>_aplus_hd_1.jpg`、`_2.jpg`（每页都偏长，所以都分成两张）。
