# 参考图

`INDEX.csv` 是全部可用参考图的唯一清单。图位卡只能引用这里列出的图，校验脚本会逐张核对。

## 索引的四列

| 列 | 含义 |
|---|---|
| `path` | 从仓库根目录起的路径 |
| `type` | 类型，决定它能填进图位卡的哪个槽位 |
| `key` | 检索键，写卡时按它查 |
| `note` | 这张图可以取什么、不可以取什么 |

## 五种类型

| `type` | 是什么 | 能填的槽位 | `key` 的写法 |
|---|---|---|---|
| `product` | 产品结构参考图 | `product` | `产品名/机位`，例如 `round10l/front_high` |
| `anchor` | 认可过的自家成图 | `anchor` | `场景/机位/内容`，例如 `kitchen_sink/down_45/清洗` |
| `scene` | 第三方的场景、光影、材质案例 | `anchor`（没有自家锚图时） | 案例类别 |
| `expression` | 宠物表情案例 | `expression` | 案例类别 |
| `layout` | A+ 模块和版式案例 | `layout`（只有 P 位） | 案例类别 |

第三方案例共 151 张，来自 `docs/UTA_STYLE_STANDARD.md` 第 14.10 节的分类表，图片在 `docs/uta_style_v3/assets/key/`。认证检测类 2 张和过程稿总览 1 张没有收入索引。

## 锚图

`anchors/` 里是用户认可过的成图。它们是「标准落地后的样子」，比第三方案例更贴近要的效果，所以 `anchor` 槽位优先用它们。

| 文件 | 来源 | 取什么 |
|---|---|---|
| `v06_S6_clean_sink.png` | v06 轮 S6，用户点名认可 | 侧窗硬光、手和猫围绕同一部件 |
| `v06_S7_filter_topdown.png` | v06 轮 S7，用户点名认可 | 正俯拍、长投影、手和猫爪伸向同一零件 |
| `v06_S8_move_entry.png` | v06 轮 S8，用户点名认可 | 低机位、门口逆光、猫抬头扒包 |
| `v06_S5_quiet_dusk.png` | v06 轮 S5，用户确认通过 | 黄昏暖光、猫贴着机器熟睡 |
| `round_S5_clean_sink.png` | 圆款清洗试样，用户评价「视觉是对的，产品有点变形」 | 光影和人宠关系；不取产品 |

前四张里的产品是方形四叶草款。用在别的产品上时，图位卡里必须写 `not the product`。

## 新增一张图

1. 把文件放进对应目录：锚图放 `anchors/`，产品参考图放 `products/<产品>/ref/`。
2. 在 `INDEX.csv` 末尾加一行，四列都填。
3. 运行 `python -m unittest discover -s tools -p "test_check_card.py"`。
