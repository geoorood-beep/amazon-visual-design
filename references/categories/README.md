# 品类库

每个品类一份 JSON：这类产品通常有哪些部件、部件之间什么关系、产品有哪几种样子、哪些地方要问卖家、要补哪些照片、尺寸怎么量、画图常错在哪、哪些话不能写。AI 拿它当起点，对照这款产品的照片改成这款产品自己的产品资料表（`grok/product_template.html`）。

**这是品类常识，不是产品事实。** 文件里的东西全部按「推定」用：可以帮 AI 想到该看什么、该问什么，不能直接写进产品卡的「已确认事实」，也不能写进文案。每份文件的 `basis` 写了它是怎么来的（大多来自 2026-11-19 联网整理，很多页面只看到搜索摘要）。

**产品资料表不是闸门。** 用户不打开它，流程照样往下走：AI 草稿按「推定」用。用户改了，以用户为准。谁说了算：用户改过、填过的 ＞ 用户看过没改的 ＞ AI 推定。

## 现有品类

| 文件 | 品类 | 形态 |
|---|---|---|
| `pet_fountain.json` | 宠物饮水机 | 立体 |
| `smart_feeder.json` | 智能宠物喂食器 | 立体 |
| `smart_litter_box.json` | 智能猫砂盆 | 立体 |
| `dog_leash.json` | 狗牵引绳 | 扁平（伸缩款按立体） |
| `pet_grooming_vacuum.json` | 宠物真空美容套装 | 立体 |
| `generic.json` | 没对上任何品类时用 | 立体 |

## 部件的关系类型

画面怎么处理一个部件，看它是哪一类，而不是看它叫什么。

| 类型 | 意思 | 画面规则 |
|---|---|---|
| 组成部件 | 长在产品上 | 跟着产品状态走：装好时在原位，拆开时跟着拿出来 |
| 可拆件 | 用户会拆下来洗、加东西 | 只在拆洗、加注的画面里出现在外面 |
| 耗材 | 定期更换 | 只在换耗材的画面出现；主图不入画 |
| 随附配件 | 包装里另附 | 只在用到它的画面或开箱图出现；没附带的不画 |
| 宿主产品 | 卖的是配件时，它要装上去的那台产品（例如牵引绳扣上的项圈） | 当背景出现，不当主角，不能画成别家的产品 |
| 外部物品 | 水、粮、猫砂、宠物、人手 | 场景道具，不算部件 |

## 新产品怎么走

```
用户发产品图和需求
  → detect：从产品名、需求原话、照片文件名猜品类，列出每个候选品类的外观特征
  → AI 看照片对照外观特征，定品类和款式（--variant）；对不上任何品类就用 generic
  → skeleton：品类模板 + 产品卡事实 + ref_views.csv + 照片 → 草稿 JSON（部件全部「推定」）
  → AI 按草稿里的 ai_todo 对照照片改：看得见的改「确定」并写依据，没有的删，模板没有的加；问题只留 3 个
  → build：生成 outputs/<产品>/product_form_vNN.html（图片压缩嵌入，单独发出去也能看，不覆盖旧版）
  → 和第一批选择卡放在同一条回复里给用户；用户可以不打开
  → 用户填了，发回一段 UTA-PRODUCT v1，按它写进产品卡（写入步骤待接进规范）
  → 产品确认后，AI 提议把这款学到的关系写进品类文件的 learned（只记关系规律，不记产品事实），用户同意再写
```

命令：

```
python tools/product_form.py detect   --product <产品> --text "用户需求原话"
python tools/product_form.py skeleton --product <产品> --category <品类> --variant <款式>,<款式>
python tools/product_form.py build    --sheet outputs/<产品>/product_form_draft.json
python tools/product_form.py check
```

两种品类合在一起的产品（例如喂食喂水一体机），`detect` 会提示 `COMBO?`，`--category` 写两个，用逗号隔开。

## 文件里有什么

| 字段 | 写什么 |
|---|---|
| `aliases` | 中英文关键词，`detect` 用它从产品名和需求里认品类。英文按整词匹配 |
| `cues` | 看照片时认出这个品类的外观特征，AI 用它确认 |
| `form` | 立体或扁平，决定照片区的标准视角；款式可以用 `form` 改 |
| `variants` | 款式（带摄像头、伸缩款……）；`adds` 是这个款式才有的部件 |
| `parts` | 部件：`key`、`name`、`en`、`type`（上面六类之一）、`parent`（装在哪个部件上）、`where`、`visible`、`detach`、`variant`（只属于某个款式时写）、`pitfall`、`refs`（`ref_views.csv` 里哪些部位词能当它的参考图） |
| `states` | 产品有几种样子；`keywords` 用来把产品卡的事实对到状态上；`show`、`hide`、`never` |
| `questions` | 会影响画面的问题；最后一个选项是安全的「不确定，……先不拍」；`rec` 是没人回答时按哪个 |
| `photo_slots` | 这个品类特别要补的照片，排在标准视角和规格照后面 |
| `size` | 三个尺寸怎么量（每个带单位）、`ratios` 算哪几个比例、品类特有的尺寸或容量 |
| `pitfalls` | 图像模型在这个品类常犯的错 |
| `forbidden` | 没有证据不能写的话 |
| `selling_visuals` | 常见卖点和画面里用什么证明 |
| `learned` | 做过的产品沉淀下来的关系规律，`status` 写已确认或待确认 |
| `sources` | 来源；`opened: false` 表示只看到搜索摘要 |

## 加一个新品类

两种办法：

- 复制 `generic.json`，改成新品类，填 `aliases`、`cues`、`parts`、`states`、`questions`、`photo_slots`、`size`，运行 `python tools/product_form.py check`。
- 新品类的第一款产品先用 `generic` 走完；用户确认产品资料后，让 AI 按这款产品起草一份新品类文件，用户同意再加。

改了任何品类文件都运行一次 `check`；测试是 `python -m unittest discover -s tools -p "test_product_form.py"`。
