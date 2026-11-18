---
card_version: 1
product: <产品目录名，例如 round10l>
slot: <M1 | S1-S9 | P1-P8>
canvas: <M1 填 1:1 | S 填 4:5 | P 填 2.44:1>
selling_point: <产品卡里的事实编号，例如 F5>
evidence: <English. 画面里哪个看得见的东西证明这个卖点>
human_action: <English. 手在做什么；没有人就写 none>
pet: <English. 什么宠物；没有就写 none>
pet_action: <English. 宠物对同一个证据做什么；没有就写 none>
camera: <low_angle | eye_level | down_45 | top_down | close_up | wide>
scene: <English. 在哪里，有哪些家具和物件>
light: <English. 光从哪边来，影子落在哪>
text_area: <top | top_left | top_right | bottom | bottom_left | bottom_right | left | right>
headline: <English. 最多 6 个词>
subtitle: <English. 最多 10 个词>
hero_number: <一个带数字的短语，例如 Under 20 dB；不用就写 none>
caption: <可见说明，最多 12 个英文词；不用就写 none。排版加字，不进 story>
comparison: <只有 pw002_s 的 S6 可写 risk_scenario；其他卡写 none>
refs:
  product: <INDEX.csv 里 type=product 的路径> | <English. 只取什么>
  anchor: <type=anchor 或 scene 的路径> | <English. 取什么，不取什么>
  expression: <type=expression 的路径，或 none> | <English. 取什么，不取什么>
  layout: <type=layout 的路径，仅 P 位；S 位写 none> | <English. 取什么，不取什么>
---

（这条线下面可以写给人看的中文备注，不进提示词。）

这是 M1、副图和 A+ 单场景用的模板。A+ 单场景在 `canvas` 下面加一行 `module: scene`。
A+ 组合模块的模块卡和小格卡字段不同，照抄 `cards/round10l/P6_daily_use.md` 和 `cards/round10l/P6a_steel.md`，规则见 `UTA_STYLE.md` 2.4。
