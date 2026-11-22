"""Asked choices list every current legal option; a star only marks the recommendation (v3.55).

    python -m unittest discover -s tools -p "test_choice_listing.py" -v
"""
import csv
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Old instructions that hid legal options by keeping only a few recommendations.
# Negations such as "不收成 2–3 个方案" are allowed and checked separately.
FORBIDDEN = (
    "风格池里 2–3",
    "风格池里 2-3",
    "2–3 个整套分配",
    "卖点分配卡的 2–3",
    "每张卡给 2–3",
    "两到三个完整方案",
    "每项 2–4 个选项",
    "每项给 2–4",
    "4 个故事选项",
    "4 个故事",
    "2–3 个故事",
    "2–3 组主标题",
    "2–3 组选项",
    "2–3 只",
    "2–3 种组合",
    "多一些户外和阳台",
    "全部在厨房和客厅",
    "给 2–3 个选项",
    "给用户 2–3 个选项",
)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def rows(name):
    with open(os.path.join(ROOT, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def between(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


class ChoiceListingTest(unittest.TestCase):
    def setUp(self):
        self.guide = read("UTA_STYLE.md")
        self.skill = read("grok", "grok-UTAstyle-skill.md")
        self.asking = between(self.guide, "### 2.2 先让用户选", "### 2.3 每张卡怎么写")

    def test_version_is_recorded(self):
        import check_set
        self.assertIn("版本 3.55（2026-11-22）", self.guide)
        self.assertIn("**3.55**", read("README.md"))
        self.assertIn("## v3.55", read("CHANGELOG.md"))
        self.assertEqual(check_set.VERSION, "3.55")

    def test_old_top_n_caps_are_gone(self):
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, self.guide, phrase)
            self.assertNotIn(phrase, self.skill, phrase)
        self.assertIn("不收成 2–3 个方案", self.guide)
        self.assertIn("也不收成两到三个方案", self.skill)

    def test_style_groups_list_every_pool_row(self):
        styles = rows("pools/styles.csv")
        block = between(self.asking, "风格分组（与 pools/styles.csv 逐行对应）：", "推荐哪一种风格")
        groups = [line for line in block.splitlines() if line.startswith("- ")]
        self.assertEqual(
            [line.split("：", 1)[0][2:] for line in groups],
            ["纪实", "家居", "海报", "生活"],
        )
        found = []
        by_group = {}
        for line in groups:
            name, rest = line.split("：", 1)
            ids = re.findall(r"ST\d+", rest)
            by_group[name[2:]] = ids
            found.extend(ids)
        self.assertEqual(by_group, {
            "纪实": ["ST01", "ST08"],
            "家居": ["ST02", "ST03", "ST05"],
            "海报": ["ST04"],
            "生活": ["ST06", "ST07"],
        })
        self.assertEqual(sorted(found), [row["id"] for row in styles])
        self.assertEqual(len(found), len(set(found)))
        for row in styles:
            self.assertIn(row["id"] + " " + row["name"], block)
        self.assertIn("ST08 暖调家庭纪实胶片风（限制：", block)
        self.assertIn("风格池每一行都列出", self.skill)
        self.assertIn("按纪实、家居、海报、生活分组", self.skill)

    def test_storylines_list_every_row(self):
        lines = rows("references/storylines.csv")
        sentence = between(self.asking, "故事主线以", "推荐哪条")
        self.assertIn("全部行为准，一条不漏", sentence)
        for row in lines:
            self.assertIn(row["id"] + " " + row["name"], sentence)
        for row in lines:
            self.assertIn(row["name"], self.skill)
        self.assertIn("不要只给其中四条", self.skill)

    def test_scope_lists_every_nonempty_combination(self):
        for text in (self.asking, self.skill):
            for label in ("主图 + 副图 + A+", "主图 + A+", "只做主图", "只做副图", "只做 A+"):
                self.assertIn(label, text)
            self.assertRegex(text, r"主图 \+ 副图(?! \+)")
            self.assertIn("三部分都不做，不是选项" if text is self.asking else "三部分都不做不是选项", text)
        self.assertIn("1 到 9", self.asking)
        self.assertIn("1 到 8", self.asking)
        self.assertIn("不把「副图几张 × A+ 几屏」逐对写成方案", self.asking)
        self.assertIn("不把张数和屏数逐对展开", self.skill)

    def test_emotion_closed_set_is_shown_in_full(self):
        for text in (self.asking, self.skill):
            self.assertIn("只有这三项", text)
            for name in ("温暖日常", "惊喜活泼", "安静治愈"):
                self.assertIn(name, text)
            self.assertIn("不临时加第四项" if text is self.asking else "不另编第四项", text)

    def test_other_pools_are_listed_in_full_when_asked(self):
        for phrase in (
            "场景池的每一行",
            "宠物池的每一行",
            "人物池的每一行",
            "`pools/moods.csv` 每一行都列出",
            "表情池的每一行",
            "1.17 的每个取值",
            "用得上的标题手法每条一组",
        ):
            self.assertIn(phrase, self.asking)
        self.assertIn("该池的每一行都出现", self.skill)
        self.assertIn("适用的展现路线在目录里列全", self.skill)
        self.assertGreater(len(rows("pools/scenes.csv")), 4)
        self.assertGreater(len(rows("pools/expressions.csv")), 4)

    def test_groups_do_not_hide_a_member_or_promise_a_cartesian_product(self):
        for phrase in (
            "分组不能用来少列某一组里的合法项",
            "不枚举「每个图位 × 每个事实」",
            "不把「路线 × 镜头 × 景别 × 机位」",
            "不把「每个人 × 每种情绪」逐对展开",
            "每一个已确认事实一行",
        ):
            self.assertIn(phrase, self.asking)
        self.assertIn("不是用来少列某一组里的合法项", self.skill)

    def test_ineligible_options_stay_visible_and_stay_closed(self):
        for text in (self.asking, self.skill):
            self.assertIn("标不可选", text)
            self.assertIn("不删掉", text)
        self.assertIn("也不改成可选", self.asking)
        self.assertIn("不新开上面没有的类别", self.asking)

    def test_card_capacity_does_not_truncate_the_class(self):
        self.assertIn("一张提问卡最多四个选项加一个「自己输入」", self.asking)
        self.assertIn("这是卡片容量，不是一类最多四个", self.asking)
        self.assertIn("四个是这张卡的容量，不是一类的上限", self.skill)
        self.assertIn("一条消息最多八张卡", self.asking)
        self.assertIn("这个上限不拿来删选项", self.asking)
        self.assertIn("不用这个上限删选项", self.skill)
        self.assertIn("看得到的目录", self.asking)
        self.assertIn("不展示的文件或后台里，不算列出", self.asking)
        self.assertIn("也不只放在后台", self.skill)
        self.assertIn("紧接着连发，中间不等回复", self.skill)

    def test_recommend_all_states_what_it_adopts(self):
        scope = between(self.asking, "**全部按推荐的采纳范围。**", "故事这一类选的是整套主线")
        for item in ("范围", "卖点分配", "故事主线", "情绪基调", "风格", "主推表达"):
            self.assertIn(item, scope)
        self.assertIn("主图 1 张、副图 8 张、A+ 7 屏", scope)
        self.assertIn("采纳范围不包括：判断题", scope)
        self.assertIn("产品样子和资料对不对", scope)
        self.assertIn("我替你定的", scope)
        self.assertIn("采纳范围：", self.skill)
        self.assertIn("判断题和造型基准不在这个采纳范围里", self.skill)
        self.assertIn("正常情况下用户只点两次", self.skill)

    def test_fast_path_still_keeps_every_class(self):
        for text in (self.guide, self.skill):
            self.assertIn("一张都不能少", text)
            self.assertIn("判断题最多再发两张", text)
            self.assertIn("一类一张卡", text)
        self.assertIn("**选择项列全。**", self.asking)
        self.assertIn("选择项列全", self.skill)


if __name__ == "__main__":
    unittest.main()
