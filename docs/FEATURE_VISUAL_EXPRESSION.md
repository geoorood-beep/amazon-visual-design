# 卖点如何变成看得懂的图片

> 状态：部分有效，2026-11-15。映射写法仍可参考。文中的 5L、电池供电、仅顶盘不锈钢、Avenir / Arial，属于 2026-09-10 的概念喂水器，不是 POKPET。POKPET 的事实以 UTA §6E.2 第 6 条和 §14.8 为准；字体以 Poppins 为准。不要把本文的容量和电池写成 POKPET 卖点。

对应 AGENTS v2.1，2026-09-10。第10.4节的布局方法已由用户确认固定；本文是当前喂水器的落地示例，不代表既有图片已修改或通过新验收。

## 1. 先确定沟通任务

每张图先写一句具体目标：“看完这张图，消费者应理解 ______。”然后依次确定事实依据、收益、可见线索、工作状态、主识别入口、信息层级、必要组件和验收问题。摄影与所选图文共同解释这一目标；主参数、动作或细节已清楚时，不强制添加图标或白卡。

当前 v02 的电脑端对照图中，多数模块采用木地板、完整饮水器与猫，配标题和正文。它建立了统一风格，但感应和过滤模块缺少各自的过程或信息表达，静音模块也没有清楚表现工作状态与休息者的关系。新增图标只有在这些逻辑明确后才有效。

资料依据：`pet_fountain_fullset_20260909_v02/01_brief/copy_plan.json`、该目录的 `brief.md`、`07_qa/contact_desktop.png` 和当前用户说明。本文只评估卖点表达，不重新宣布整套产品保真或成品 QA 通过。

## 2. 当前产品事实

这是锁定概念产品参考下的设计，不等于实物商品已核验。

| 项目 | 当前依据 | 不得自行补出的信息 |
|---|---|---|
| 容量 | 用户确认 5L | 可用多少天、适用多少只宠物、实际可用水量 |
| 噪音 | 用户确认 25 dB；测试条件未知 | 0 dB、绝不打扰、睡眠改善、噪音对比或独立测试结论 |
| 材质 | 用户明确不锈钢适用于顶部饮水盘 | 全钢机身、304/316、抗菌、可放洗碗机 |
| 无线使用 | 用户确认电池供电 | 电池可充电、接口、容量、续航、无线充电 |
| 感应 | 用户确认宠物靠近后出水 | 感应技术、传感器外形/位置、范围、延时、离开后何时停水 |
| 过滤 | 用户确认滤芯过滤水质 | 滤芯真实形状、层数、材料、去除率、杀菌与健康效果 |

“充电等需要图标”提出了表达需求，当前资料尚未明确这款产品的充电方式。后续若确认可充电及真实接口/方式，再选择充电场景与图标；目前用 `Battery Powered` 电池图标说明已知事实。

## 3. 本品概念表现方向

沿用暖木、奶油色、深绿和暖中性真实光影。2026-09-10 的标题是 Avenir Next Demi Bold，正文和图标标签是 Arial；这是历史字体，POKPET 自 2026-11-15 起用 Poppins。睡眠场景按 `benefit_context` 排列人物关系，摄影底图仍需保持产品真实尺度、透视与环境光影。

| 卖点与消费者应理解的内容 | 场景或细节 | 主识别入口与按需标签 | 解释手段 | 必查逻辑 |
|---|---|---|---|---|
| 静音：运行噪音低，可放在日常休息情境中表达 | 主人在沙发休息，清醒的猫刚靠近并饮水；或一只宠物饮水，另一只在旁休息 | 短标题与 `25 dB` 分主次，数字和单位成组；静音图标可省略 | 主标题可用 `Made for Quiet Moments.`；优先直接排字，不需要白卡或虚构声压曲线 | 画面要有真实运行线索，符合感应触发；休息场景不证明任何人都不会被吵醒 |
| 感应：靠近动作触发出水 | 猫向产品靠近，在出水发生的时刻建立动作关系 | 靠近→出水的动作顺序为主；必要时用 `Pet-Activated Flow` 短标签，宠物图标可选 | 独立两步流程 `Pet Approaches → Water Starts`；必要时辅以少量无比例虚线，流程可开放排布 | 不能只画猫已经喝水便认为感应已说明；不暗示感应范围或离开停水 |
| 电池供电：使用时不用连接电源线 | 产品位于合理的宠物活动位置，无连接电源线，宠物正常使用 | 电池图标＋`Battery Powered` | 可与感应组成主次分明的模块；感应解释触发，电池解释供电 | 不用 Wi-Fi、无线充电、USB-C 或续航天数代替 |
| 不锈钢：顶部饮水接触面是什么材质 | 单独选择能清楚呈现顶盘的镜头，保留真实边缘与金属反射 | 真实顶盘细节＋`Stainless Steel Tray`，不重复放盘形徽章 | 需要定位时用一根准确指向顶盘的细引线；特写须事先记录图片任务 | 指向顶盘，不指向奶白机身；不自行拆卸未确认结构 |
| 过滤：存在滤芯过滤功能 | 产品外观与独立功能说明区组合，以抽象滤水符号作为主要信息线索 | 抽象滤水图标＋`Water Filtration` | `A filter cartridge helps filter your pet’s drinking water.`；目前不画真实内部水路 | 抽象符号不能冒充本品滤芯；清澈水面或猫喝水不是过滤效果证明 |
| 5L：明确储水容量 | 保持真实尺寸的产品展示，或真实加水动作，给容量数字清楚的信息位置 | `5L` 主参数＋简短容量说明；数字与单位紧密成组，容量图标可省略 | 优先开放排版；确需归组时才使用卡片，不同时放同等醒目的大标题和大徽章 | 不能放大产品来暗示容量，也不添加天数、宠物数量和效果承诺 |

以上英文为规划候选。最终文案仍需和画面、字数及实际模块一起检查。过滤结构仍未知：此时用抽象滤水符号与准确短句；后续有真实滤芯参考后，才可采用滤芯特写或有依据的结构引线。图标不是认证标志；25 dB 的来源和未知测试条件保留在 brief/QA，不能为它编造脚注、比较对象或测试机构。

## 4. 感应图片的完整映射示例

```yaml
feature_visual_map:
  slot_id: APLUS04
  communication_task: Explain pet-triggered flow and distinguish it from battery power.
  fact_and_source: User confirmed battery power and water activation when a pet approaches.
  evidence_status: User confirmed; sensor details unknown.
  benefit_and_basis: Flow starts in response to the pet approaching; no claim about timing or energy savings.
  scene_or_detail: A cat approaches the locked fountain in a warm, believable home setting.
  action_and_operating_state: Show the activation moment with the cat close by and water beginning to flow.
  visible_cue: Approaching posture plus a separate two-step explanation.
  primary_entry: The pet-approach to water-start sequence, with a short headline.
  layout_structure_and_reason: Integrated scene plus open two-step layout to explain cause and result.
  information_hierarchy: Headline and activation sequence first; battery-power label secondary.
  headline_en: Come closer. Water flows.
  supporting_copy_en: Water flow starts when your pet approaches.
  icon_meaning_and_label_en:
    - battery power / Battery Powered
  card_grouping_reason: NONE; open step grouping is sufficient unless legibility requires a container.
  explanatory_overlay:
    type: Separate open process group; optional minimal dashed approach cue.
    text: Pet Approaches → Water Starts
    anchor: No attachment to an unverified sensor window or point on the shell.
    interpretation: Conceptual sequence, not measured range or visible light emission.
  forbidden_inferences:
    - No claim of rechargeable battery, charging port, battery capacity or runtime.
    - No invented sensor hardware, technology, range, angle or delay.
    - No claim about what happens immediately after the pet leaves.
  desktop_and_mobile_layout:
    desktop: Separate text/process area and integrated scene; maintain clear hierarchy.
    mobile: Recompose the scene and arrange steps vertically if needed; keep both steps readable.
  qa_question: Can the viewer distinguish what triggers flow from what powers the fountain?
```

这一示例指导后续提示词与排版，不要求把 YAML 内容全部画进图。所选图标和流程先规划位置，再在摄影底图完成后由原生排版工具绘制。卡片只在确有归组或阅读需要时使用，不为它增加模式或 App 等未确认能力。

## 5. 执行和复检

1. 为本次需要修改的每个图片位建立映射，再选择场景；不沿用与新任务冲突的旧描述。例如“无虚构感应箭头”应具体区分虚构硬件/参数与允许的解释箭头。
2. 代表样张优先选静音或感应，覆盖工作状态与图文解释的难点；先完成其完整图文版并自检，再扩展同类设计。
3. 先生成产品与场景光影统一的底图，再添加文字以及选用的参数、图标和流程示意；保存可编辑排版源。不能把统一图标规范误解为统一商品像素大小。
4. 逐张、双端分别打开，检查真实尺度与部件、工作状态、场景对应、主次层级、所选组件的语义与阅读顺序。移动端空间不足先减次要信息或重排，不机械缩小电脑端整图；不因缺少图标或卡片判失败。
5. 整套并排检查：静音是否讲休息情境，感应是否讲触发过程，供电是否讲电池，材质是否准确指向顶盘，过滤是否只表达已知功能，容量是否清楚给出 5L。
6. 错误场景重新构图；模糊图文重新排版；未知结构不猜画。分别记录产品一致性结论和卖点表达结论，任何一项不通过都不能宣布该图完成。

本规则设计的检查结果：六项卖点均能给出对应表现手段；可充电、感应细节和真实滤芯结构仍属于待确认资料；睡眠场景无需违反共同视线规则；白底主图继续无添加图文。尚未执行按新规则生成的图片 QA。

布局采纳依据见 [9款 Amazon 案例对照](../icon_typography_study_20260910/amazon_brands/index.html)。借鉴简洁层级、具体场景和结构说明。2026-09-10 写的是保持 Avenir/Arial；该句自 2026-11-15 起只作历史。POKPET 用 Poppins，A+ 标题起点仍不新增未经测量的竞品字号、手机行为或功能事实。
