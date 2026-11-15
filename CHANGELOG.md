# 版本记录

## v2.12 — 2026-11-15 UTA 与 AGENTS 对齐

- `AGENTS.md` 文首指向 `docs/UTA_STYLE_STANDARD.md`。POKPET 的风格、字体、机位、色调、表情、分镜和案例以 UTA 为准；合规、尺寸、母版、产品保真和 QA 门槛仍以 AGENTS 为准。
- 确认 D1：全套 Poppins。字体文件和 SIL OFL 1.1 放在 `fonts/poppins/`。历史 Avenir / Arial 条款保留并标明已被取代。
- 确认 D2：1600×2000 标题保持 92px。不把 UTA 里冲突的 96–128px、52–58px 换算成新的绝对像素。
- 确认 D3：生活场景暗部 p5 ≤ 0.12。`tools/grade_check.py` 增加 `--contrast`、`--slot`、`--json` 和非 0 退出码。`--dark` 与 `--outdoor` 的原阈值保留。
- D4 保持 `TODO(D4)`。不决定 Amazon 图位上限，不删除、不合并 S1–S9。
- 确认 D5：POKPET 卡片按 UTA §7。AGENTS 旧卡片条款标明适用范围。
- 确认 D6：STYLE-HCEL-01、NLEC-01、PDMI-01、WAPSI-01 降级为非 POKPET 或用户指定时可选，正文保留。
- 新增 `docs/UTA_QUICKSTART.md`、`docs/uta_style_v3/CASE_INDEX.md`、`tools/layout_render.py`、`tools/facts.json`。
- 旧分镜、卖点示例和 WAPSI 说明在文件头标明状态。`product_reference.png` 仍缺失，外形对照阻塞。
- 不改 GitHub 仓库简介，也不改可见性。简介里的 v2.7 因此没有同步。

## v2.11 — 2026-11-15 POKPET A+ 视觉标准 v02 配图

- 新增 `docs/POKPET_APLUS_VISUAL_STANDARD_v02.md`。正文规则与 235 行草案相同，只加入图片标题和说明。
- 8 个模块示例和整页预览压缩为约 1200 px 宽的 JPG，放在 `docs/assets/visual_standard_v02/modules/`。标注为 v02 案例：原生约 1280×720，1464×600 为放大裁切。
- 文中点名的 22 张 oneisall 参考图链接到 `research/oneisall/` 中的对应文件。

## v2.7 — 2026-11-15 GitHub首次同步

本次发布现有v2.7规则快照，不将同步日期冒充规则首次制定日期。

### 已有规则与工具修订（2026-09-29）

- 恢复内置工具正常出图，输出像素低于目标不自动造成整个任务停工。
- 将明确尺寸要求、实际视觉清晰度和原生/合成/放大来源分开记录。
- 先复用同项目已验证的方法；失败结论限定于有证据的工具与参数。
- 优先局部重做，保护清晰产品区域、宠物毛发、已批准的搞怪表情与配饰。
- 增加高清处理工作流说明；不把原生小图误称为指定尺寸已完成。
- 修复水体合成脚本改动计数：在合成和边缘处理后逐像素比较，分别报告水体遮罩外及全部许可区域外的实际改动。

### 本次仓库整理

- 保存现有AGENTS、配套文档、技能目录和必要工具；未改写作图规则。
- 添加仓库入口说明和版本记录，说明本机路径、历史证据与macOS工具的迁移边界。
- 排除账号凭据、历史成品大图、视频、缓存及备份包。
