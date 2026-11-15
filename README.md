# 亚马逊美工设计

当前规则版本：**v2.10**。本仓库保存 Amazon 主图、副图与 A+ 的作图规则、配套技能、卖点可视化方法和局部图片处理工具。

## 从这里开始

1. 在 Codex 中打开本仓库，先读取 [AGENTS.md](AGENTS.md)。这是项目规则的主入口。
2. 新建视觉任务时，参考 [作图需求填写表](docs/作图需求填写表.md)，提供产品参考图、规格、图片用途和明确尺寸。
3. 规划、提示词与视觉验收需要配套流程时，读取 [amazon-visual-skill](skills/amazon-visual-skill/SKILL.md)。技能随仓库保存，不依赖原电脑的全局技能目录；这里没有自动安装或覆盖全局技能的脚本。
4. 处理清晰度、反复重绘或指定像素问题时，读取 [高清图片工作流](docs/HD_IMAGE_WORKFLOW.md)。

## 本次同步内容

| 内容 | 入口 |
|---|---|
| 产品保真、主副图/A+架构、双端构图、生成与QA规则 | [AGENTS.md](AGENTS.md) |
| 高清处理与防磨皮流程 | [HD_IMAGE_WORKFLOW.md](docs/HD_IMAGE_WORKFLOW.md) |
| 已确认事实到可见动作/结构的卖点映射 | [FEATURE_VISUAL_EXPRESSION.md](docs/FEATURE_VISUAL_EXPRESSION.md) |
| 宠物用品卖点可视化标准 | [PET_APPLIANCE_SELLING_POINT_VISUAL_STANDARD_v1.0.md](docs/PET_APPLIANCE_SELLING_POINT_VISUAL_STANDARD_v1.0.md) |
| 固定风格说明与三张参考图 | [STYLE_WAPSI_01.md](docs/STYLE_WAPSI_01.md)、[style_references](docs/style_references/) |
| 宠物电器 Listing 副图图库构图（STYLE-GALLERY-OIA-01） | [LISTING_GALLERY_STANDARD_ONEISALL.md](docs/LISTING_GALLERY_STANDARD_ONEISALL.md) |
| 宠物电器 A+ 页面（STYLE-APLUS-OIA-01） | [APLUS_STANDARD_ONEISALL.md](docs/APLUS_STANDARD_ONEISALL.md) |
| oneisall 研究截图、索引和视觉尺寸案例 | [research/oneisall](research/oneisall/README.md)、[VISUAL_CASE_STUDY.md](research/oneisall/VISUAL_CASE_STUDY.md)、[STRUCTURE.md](research/oneisall/STRUCTURE.md) |
| 小红书第三方参考（内部研究） | [research/references/xiaohongshu](research/references/xiaohongshu/README.md) |
| 规划、模板、提示词和验收技能 | [skills/amazon-visual-skill](skills/amazon-visual-skill/) |
| 水体局部合成及实际改动计数 | [composite_water_clarity.c](tools/composite_water_clarity.c) |
| 2×尺寸导出示例 | [upscale_2x.swift](tools/upscale_2x.swift) |
| 历史可选API入口及模拟测试 | [IMAGE25_SETUP.md](docs/IMAGE25_SETUP.md)、[image25.py](scripts/image25.py) |

参考图用于理解构图和信息层级，不代表本品结构，也不附带第三方品牌素材的商业再利用授权。

## 运行与迁移边界

- 默认直接使用当前可用的内置图像工具。历史API脚本并非默认通道；其中固定模型名称、接口能力及历史认证状态未在本次GitHub同步中重新验证。
- `AGENTS.md`第14.1节及部分历史说明中的`/Users/leo/...`路径是原项目的本机落点，不是其他电脑的有效路径。迁移时由使用者指定新的输入、输出目录；不会自动修改或访问原电脑目录。
- 高清工作流中的历史交付路径是审计证据引用。对应生成大图未上传，不能在本仓库内直接打开这些历史图片。
- 两个`tools/`示例依赖macOS系统图像框架。水体合成工具的遮罩坐标针对旧V02构图，使用前需按当前产品图重新核对；它不是适用于任意图片的一键修复器。
- `upscale_2x.swift`是传统Lanczos缩放与轻度亮度锐化，不是AI超分，也不会恢复原图缺失的真实细节。交付时如实注明来源和尺寸处理。
- 模型、账号权限、字体及运行系统需要在使用环境单独确认。同步规则不保证不同环境生成相同像素结果。

## 本地检查

在仓库根目录执行：

```sh
python3 -m unittest discover -s scripts -p 'test_image25.py' -v
clang -fsyntax-only -Wall tools/composite_water_clarity.c
```

Python测试使用模拟响应，不调用真实图像API、不消费生成额度。C语法检查需要macOS与相应开发工具。两项检查均不能代替图片视觉验收。

## 同步范围

仅包含项目规则、必要文档、配套技能、三个风格参考图及选定工具源码。不包含API密钥、账号会话、`.env`、客户数据、缓存、历史生成大图、视频和打包备份。

后续提交请显式列出要同步的文件，不对本地制作目录执行无差别`git add .`。版本变化见 [CHANGELOG.md](CHANGELOG.md)。
