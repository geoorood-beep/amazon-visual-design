# UTA 案例索引

每次出图前写出本图引用的案例编号、UTA 小节和借鉴点。竞品图只学画法。下表「本品事实边界」只重复 UTA §6E.2 第 6 条、§14.8、§6H.7 已经写过的话；没有写过的卖点保持待补充或禁区。

`product_reference.png` 不在本索引里，因为仓库没有这个文件。路径检查不把它算成可引用资产。

```bash
python3 - <<'EOF'
import re, os
t = open("docs/uta_style_v3/CASE_INDEX.md", encoding="utf-8").read()
miss = [p for p in re.findall(r'docs/uta_style_v3/assets/[\w\-/\.]+\.(?:jpg|png)', t) if not os.path.exists(p)]
print("missing:", miss)
EOF
```

## 卖点画法（§4.1–§4.22）

| 卖点 | 主推画法 | 参考图 | 学什么 | 不学什么 | 本品事实边界 |
|---|---|---|---|---|---|
| 静音 / dB（§4.1） | 暗场或夜景，宠物熟睡，琥珀数字 | `docs/uta_style_v3/assets/key/F_quiet_heronum_FJX69D2R.jpg` | 暗场里睡觉，数字后期排 | 别家的 20dB、50dB | 低于 25 dB（§6E.2、§14.8） |
| 容量（§4.2） | 竞品用巨型数字 | `docs/uta_style_v3/assets/key/D_20cups_C5X4N132.jpg` | 只看数字怎么占画面 | 20 Cups、7L、天数换算 | 禁区：不写容量（§6E.2） |
| App / 远程（§4.3） | 竞品用人看手机 | `docs/uta_style_v3/assets/key/D_human_phone_GFDH3WD5.jpg` | 人物放松，不学界面 | App、Wi-Fi、乱码屏幕 | 喷水器不写 App。喂食器待补充（§6A.5、§14.9） |
| 过滤（§4.4） | 滤芯分层，浅色底 | `docs/uta_style_v3/assets/key/F_filter_layers_FJX69D2R.jpg` | 层片和短标签的结构 | 实验室、除菌百分比。反例 `docs/uta_style_v3/assets/key/F_lab_D5B6RLYY.jpg` | 只写滤芯每 1–2 周更换，不写过滤功效（§6E.2） |
| 易清洗（§4.5） | 手部取出，45° 俯拍 | `docs/uta_style_v3/assets/key/F_dishwasher_FJX69D2R.jpg` | 手和零件的关系 | 洗碗机承诺、对手品牌 | 水泵和水盘可拆（§6E.2） |
| 304（§4.6） | 拉丝微距，数字后期排 | `docs/uta_style_v3/assets/key/F_steel_macro_FJX69D2R.jpg` | 高光和拉丝 | 抑菌、证书、食品级 | 304 不锈钢（§6E.2、§14.8） |
| 缺水 / 断电（§4.7） | 近景水位窗 | `docs/uta_style_v3/assets/key/F_lowwater_shutoff_D5B6RLYY.jpg` | 窗口看得见 | 自造灯色 | 缺水自动断电和防干烧（§6E.2）。§6E.3 第 10 拍写明不发明灯色 |
| 模式（§4.8） | 三种模式可做卡片 | `docs/uta_style_v3/assets/key/F_modes_3card_FJX69D2R.jpg` | 同级三项并排 | 别家的模式名和色调 | 感应、持续、定时，定时 15 分钟一档（§6E.2）。§6H.2 写「常开」，是否等同「持续」不确定 |
| 电池 / 续航（§4.9） | 竞品用巨型天数 | `docs/uta_style_v3/assets/key/F_battery30_FJWV49LP.jpg` | 不作为本品画法 | 30 days、100 days | 禁区：不写电池和续航（§6H.2、§6H.6） |
| 出粮机构（§4.10） | 喂食器爆炸图 | `docs/uta_style_v3/assets/key/D_rotor_explode_GFDCYGFM.jpg` | 只看爆炸图怎么讲结构 | 粒径、粮食品牌 | 喂食器待补充（§14.9） |
| 防臭（§4.11） | 猫砂盆剖面 | `docs/uta_style_v3/assets/key/L_neakasa_seal_DCFY8SB4.jpg` | 结构线，不画气味 | 除臭百分比 | 本品喷水器无此卖点。不写化学功效（§13） |
| 安全传感（§4.12） | 猫砂盆传感器 | `docs/uta_style_v3/assets/key/L_neakasa_sensors_DCFY8SB4.jpg` | 不搬到饮水器 | 传感器数量、夹伤场景 | 未确认。不虚构内部结构（§13） |
| 省猫砂（§4.13） | 颗粒宏观 | `docs/uta_style_v3/assets/key/L_oneisall_30pct_EaseS1.jpg` | 不作为本品事实 | 30%、省砂天数 | 未确认 |
| 尺寸（§4.14） | 正交视图加尺寸线 | `docs/uta_style_v3/assets/key/L_neakasa_measure_DCFY8SB4.jpg` | 尺寸线的画法 | 别家英寸和厘米 | P8 写包装清单与尺寸待补充（§6H.3） |
| 多宠（§4.15） | 俯拍双碗 | `docs/uta_style_v3/assets/key/D_multipet_C5X2G933.jpg` | 俯拍关系 | 16–17 in、2X | 未确认。不写容量 |
| 进食姿势（§4.16） | 平视低头 | `docs/uta_style_v3/assets/key/D_posture_2x_GFDCYGFM.jpg` | 喂食器画法 | 2X Higher | 喂食器待补充（§14.9） |
| 防打翻（§4.17） | 抓拍扒机身 | `docs/uta_style_v3/assets/key/D_lock_D4DL67CV.jpg` | 动作证明稳 | 锁的结构 | 喷水器不把扒机身写成防滑。§6H.5 S3 只表现材质 |
| 出行（§4.18） | 人与行李 | `docs/uta_style_v3/assets/key/D_travel_human_G4DX3QR8.jpg` | 人物关系 | 14 天、无线续航 | S8 只表现收纳或搬运，不写容量、电池、无线（§6H.2） |
| 适配猫砂（§4.19） | 颗粒网格 | `docs/uta_style_v3/assets/key/L_neakasa_litter_DCFY8SB4.jpg` | 网格排法 | 猫砂品牌 | 本品不写 |
| 按键（§4.20） | 手指微距 | `docs/uta_style_v3/assets/key/L_neakasa_buttons_DCFY8SB4.jpg` | 手部清晰 | 未确认的按键功能 | 只画已确认的顶部控制台，不增加按键（§6H.2 S4） |
| 宠物爱用（§4.21） | 舔嘴、眯眼 | `docs/uta_style_v3/assets/key/F_emotion_lick_DPMNQJ2N.jpg` | 表情强度 | 健康承诺 | 不写补水量（§14.8） |
| VS 对比（§4.22） | 我方清楚，对方无品牌 | `docs/uta_style_v3/assets/key/F_vs_hero_GYZQ79CY.jpg` | 左右轻重 | 对手外观和商标 | 不和竞品比（§6E.7、§13） |

## 表情库（§6C.1）

S1–S9 按 §6H.5 选用。同一 EXP 最多用 2 次。纯色棚拍底的 EXP 只借表情，背景仍用场景光。

| 编号 | 路径 | §6H.5 用在 | 不学什么 |
|---|---|---|---|
| EXP_007 | `docs/uta_style_v3/assets/key/EXP_007.jpg` | S3、S7 伸爪 | 黑底棚拍 |
| EXP_011 | `docs/uta_style_v3/assets/key/EXP_011.jpg` | S2、S6 回望或凑近 | 把门的身份照搬 |
| EXP_012 | `docs/uta_style_v3/assets/key/EXP_012.jpg` | S1 冲向镜头 | 草地背景 |
| EXP_013 | `docs/uta_style_v3/assets/key/EXP_013.jpg` | S8 仰头 | 未确认的喂食器情节 |
| EXP_014 | `docs/uta_style_v3/assets/key/EXP_014.jpg` | S5 熟睡 | 帽子毛衣挡住产品 |
| EXP_015 | `docs/uta_style_v3/assets/key/EXP_015.jpg` | S9 只取惊讶强度 | 尖叫 |
| EXP_016 | `docs/uta_style_v3/assets/key/EXP_016.jpg` | S4 卡片角或 P1 | 参考图上的英文 |

其余 EXP_001–006、008–010、017 的文件也在 `docs/uta_style_v3/assets/key/`。引用前先确认文件名存在。下表把它们列全，供路径检查：

`docs/uta_style_v3/assets/key/EXP_001.jpg`
`docs/uta_style_v3/assets/key/EXP_002.jpg`
`docs/uta_style_v3/assets/key/EXP_003.jpg`
`docs/uta_style_v3/assets/key/EXP_004.jpg`
`docs/uta_style_v3/assets/key/EXP_005.jpg`
`docs/uta_style_v3/assets/key/EXP_006.jpg`
`docs/uta_style_v3/assets/key/EXP_008.jpg`
`docs/uta_style_v3/assets/key/EXP_009.jpg`
`docs/uta_style_v3/assets/key/EXP_010.jpg`
`docs/uta_style_v3/assets/key/EXP_017.jpg`

## A+ 版式（§6D、§6D.4）

| 编号 | 路径 | 学什么 | 不学什么 |
|---|---|---|---|
| AP_001 | `docs/uta_style_v3/assets/key/AP_001.jpg` | 数字层级、巨字和产品的前后 | 认证、芯片、品牌字 |
| AP_002 | `docs/uta_style_v3/assets/key/AP_002.jpg` | 短标签和收尾大词 | 把别家产品变灰 |
| AP_003 | `docs/uta_style_v3/assets/key/AP_003.jpg` | 一格一个点 | 耳机参数 |
| AP_004 | `docs/uta_style_v3/assets/key/AP_004.jpg` | 引线和图标行 | 整页夜色舞台、认证 |
| AP_005 | `docs/uta_style_v3/assets/key/AP_005.jpg` | 人宠开场加小卡 | 标题原文和品牌 |
| AP_006 | `docs/uta_style_v3/assets/key/AP_006.jpg` | 一块深色、一块撞色 | 商标和参数 |
| AP_007 | `docs/uta_style_v3/assets/key/AP_007.jpg` | 低机位、手把零件拉出 | 线缆文案 |
| IMG_0540 | `docs/uta_style_v3/assets/key/IMG_0540.png` | 低机位斜向上，引线指向部位 | 整页截图不是首图裁切，色调数字不能复现 §6F 表 |
| IMG_0541 | `docs/uta_style_v3/assets/key/IMG_0541.png` | 产品在前，人在后 | 同上，且不抄参数 |
| IMG_0542 | `docs/uta_style_v3/assets/key/IMG_0542.png` | 人宠开场，下方等大方卡 | 同上，不抄品牌字 |

## 副图 S1–S9（§6H.5）

| 镜头 | 卖点 | 表情与机位 | 参考 | 事实边界 |
|---|---|---|---|---|
| S1 | 一米感应 | EXP_012，贴地低机位 | `docs/uta_style_v3/assets/key/EXP_012.jpg` `docs/uta_style_v3/assets/key/XHS_024.jpg` | 感应 1 m。不写无线（§6H.7） |
| S2 | 离开后再流 | EXP_011，低机位侧后 | `docs/uta_style_v3/assets/key/EXP_011.jpg` | 约 10–15 秒（§6E.2） |
| S3 | 304 | EXP_007，低位近景 | `docs/uta_style_v3/assets/key/XHS_013.jpg` | 304 不锈钢。不写防滑（§6H.5） |
| S4 | 三种模式 | EXP_016 可放卡片 | `docs/uta_style_v3/assets/key/F_modes_3card_FJX69D2R.jpg` | 感应 / 持续或常开 / 定时 15 分钟一档。本套卡片配额见 §7 |
| S5 | 低于 25 dB | EXP_014，全套唯一平视 | `docs/uta_style_v3/assets/key/XHS_020.jpg` | 低于 25 dB。不写成绝对安静 |
| S6 | 可拆 | EXP_011，45° 俯拍 | `docs/uta_style_v3/assets/key/F_dishwasher_FJX69D2R.jpg` | 水泵和水盘可拆 |
| S7 | 滤芯 | EXP_007，正俯拍 | `docs/uta_style_v3/assets/key/XHS_015.jpg` | 每 1–2 周更换。不写层名和功效 |
| S8 | 搬运 | EXP_013，贴地低机位 | `docs/uta_style_v3/assets/key/EXP_013.jpg` | 只表现收纳或搬运。不写容量、电池、无线 |
| S9 | 缺水断电 | EXP_015 只取强度，贴地低机位 | `docs/uta_style_v3/assets/key/XHS_014.jpg` | 缺水自动断电、防干烧。不尖叫，不发明灯色 |

日光场景另见 `docs/uta_style_v3/assets/key/XHS_001.jpg` 到 `docs/uta_style_v3/assets/key/XHS_029.jpg`。色调测量以 §9.1 为准，不把单张小红书的参数写成本品规格。
