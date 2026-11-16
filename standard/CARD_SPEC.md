# 图位卡规范

图位卡是写卡方（Grok）交给出图方（Codex）的唯一文件。一张卡对应一张图。卡通过 `tools/check_card.py` 校验后才能用来出图。

空白模板：`cards/_TEMPLATE.md`。可照抄的样卡：`cards/round10l/` 下的三张。

## 文件位置和格式

- 路径：`cards/<产品>/<图位>_<短名>.md`，例如 `cards/round10l/S5_clean.md`。
- 第一行和字段结束处各有一行 `---`。两条线之间每行一个 `字段: 值`，冒号用英文半角。
- `refs:` 下面四行各缩进两个空格。
- 第二条 `---` 之后可以写给人看的中文备注，不进提示词，也不校验。
- 不用的字段写 `none`，不要删掉这一行。

## 字段

| 字段 | 填什么 | 规则 |
|---|---|---|
| `card_version` | `1` | 固定 |
| `product` | 产品目录名 | `products/` 下必须有这个目录和 `PRODUCT.md` |
| `slot` | 图位 | `M1`、`S1`–`S9`、`P1`–`P8` |
| `canvas` | 画幅 | M1 填 `1:1`，S 填 `4:5`，P 填 `2.44:1` |
| `selling_point` | 事实编号 | 产品卡「已确认事实」表里的编号，例如 `F5`。一张卡只填一个。M1 可填 `none` |
| `evidence` | 画面证据 | 英文。看得见的物体或动作，不写抽象词 |
| `human_action` | 手的动作 | 英文，或 `none` |
| `pet` | 宠物 | 英文，或 `none` |
| `pet_action` | 宠物动作 | 英文，或 `none`。和 `pet` 同时填或同时为 `none` |
| `camera` | 机位 | `low_angle`、`eye_level`、`down_45`、`top_down`、`close_up`、`wide` 六选一 |
| `scene` | 场景 | 英文。地点、家具、物件 |
| `light` | 光 | 英文。写明光从哪一侧来 |
| `text_area` | 留给文字的区域 | `top`、`top_left`、`top_right`、`bottom`、`bottom_left`、`bottom_right`、`left`、`right` |
| `headline` | 主标题 | 英文，最多 6 个词 |
| `subtitle` | 副标题 | 英文，最多 10 个词 |
| `hero_number` | 强调数字 | 必须含数字，例如 `Under 20 dB`；不用写 `none` |
| `refs` | 参考图 | 见下一节 |

进提示词的字段（`evidence` 到 `light`）和文案字段必须是英文，不能出现中文。

## 参考图

四个槽位，每个槽位最多一张，一张卡最多四张图。格式是 `路径 | 取什么`，竖线后面用英文写明取什么、不取什么。

| 槽位 | 可用的索引类型 | 规则 |
|---|---|---|
| `product` | `product` | 必填。必须是本产品的参考图 |
| `anchor` | `anchor`，没有合适的再用 `scene` | 光影、人宠关系和排版的样子 |
| `expression` | `expression` | 卡里有宠物时才能填 |
| `layout` | `layout` | 只有 P 位能填，S 位和 M1 写 `none` |

路径必须是 `references/INDEX.csv` 里有的、仓库里真实存在的文件。索引里没有的图不能用。找不到合适的图就写 `none`，不凑数。

M1 只带产品参考图，其余三个槽位写 `none`。

## 文案规则

- 主标题、副标题、强调数字里出现的每一个数字，必须出现在所选事实的「画面可写」一列里。
- 不能出现 `standard/CORE.md`「禁用词」和产品卡「禁用词」里的词。
- M1 没有任何文字，三个文案字段和 `text_area` 都写 `none`。

## 校验

```
python tools/check_card.py cards/round10l/S5_clean.md
python tools/check_card.py --set cards/round10l
```

单卡校验通过时打印三段内容：要附带的图片清单、可直接使用的提示词、出图后的排版说明。不通过时打印错误清单，并且不打印提示词。

`--set` 检查一个目录下的全部卡，另外给出整套的提醒：相邻两张机位相同、平视超过一张、一个卖点用了两次、缺俯拍或低机位。这些提醒在写卡阶段修正，不拦截单张出图。
