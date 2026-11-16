# 归档

这里是 3.0 之前的规则文件。内容原样保留，只是不再参与出图。与 `AGENTS.md`、`standard/` 冲突的一律以后者为准。

| 路径 | 原位置 | 说明 |
|---|---|---|
| `AGENTS_v2.11.md` | `AGENTS.md` | 2.11 版规则全文 |
| `skills_old/skills/` | `skills/` | `amazon-visual-skill` 和 `amazon-visual-chief-designer-workflow` 两个技能 |
| `skills_old/pokpet-v06-design-director/` | `.cursor/skills/pokpet-v06-design-director/` | 圆款总设计师技能 |

技能被移出原目录，是为了不让 Cursor 或 Codex 自动加载它们。需要恢复时用 `git mv` 移回原位置。

`docs/` 里的旧版标准和方案没有移动，因为案例图的相对路径依赖那个目录。它们的状态见 `docs/README.md`。
