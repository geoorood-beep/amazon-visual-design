# 本项目 Image 2.5 配置

> 2026-09-09 策略更新：本入口现为可选。用户已取消强制模型限制，日常任务按 AGENTS 使用当前可用的内置图像工具；无需先配置此 API。以下为重新选择固定 API 时的说明。

固定模型：`gpt-image-2.5-sunburst-2026-09-08`。官方端点固定为 `https://api.openai.com/v1`，不受 `OPENAI_BASE_URL` 影响。仅需 Python 3 标准库，不安装第三方运行依赖。

## 当前状态

2026-09-09：调用入口及 AGENTS 已配置。现有环境凭据访问官方模型接口返回 HTTP 401。真实生图和改图尚未验证；不能称为已接通。配置不会改变 Codex 内置图像工具的底层模型。

## 一次性配置

在 Mac 的“终端”粘贴下面一条命令，然后输入你自己的 OpenAI 官方 API Key（输入不回显）：

```sh
python3 '/Users/leo/Documents/ChatGPT/美工设计/scripts/image25.py' configure
```

密钥保存于 `~/.config/amazon-visual/openai_api_key`，普通本地文件，权限 600，目录创建权限 700；不是加密保险库。此文件在项目外，不能放进项目交付包。专用文件优先于环境变量，避免旧环境变量覆盖新密钥。没有专用文件才读取 `OPENAI_API_KEY`。不会修改全局环境或其他项目密钥。

不要把密钥发给助手或写入 AGENTS。可从 [OpenAI 开发者平台](https://platform.openai.com/) 管理 API 凭据和额度。

完成后检查：

```sh
python3 '/Users/leo/Documents/ChatGPT/美工设计/scripts/image25.py' check
```

`MODEL_ACCESS_OK` 只代表模型读取成功，生成权限、计费及实际出图仍需验证。401 为认证失败；403 为权限/访问受限；404 为固定模型或接口不可用；429 为额度或速率限制，需查看开发者平台。脚本不会打印可能回显密钥的服务端错误原文。

## Codex 的日常调用

以下命令在项目根目录执行。先完成 Product DNA、案例及英文提示词，提示词应包含正向要求和负向约束。输入文件必须实际存在。

```sh
python3 scripts/image25.py generate --prompt-file 05_prompts/main.txt --output-dir 06_outputs/main_v01 --size 2000x2000
python3 scripts/image25.py edit --prompt-file 05_prompts/edit.txt --image /absolute/path/product.png --output-dir 06_outputs/edit_v01 --size 1600x2000
```

参考图驱动的场景生成也使用 `edit`；多张图重复 `--image`。不会自动上传目录内其他文件。输出目录必须是新目录，避免覆盖。每次生成1张，默认 `high`，可用 `--quality low` 做小规模连通性测试。

每次保存 `prompt.txt`、`manifest.json`、成功返回的 `candidate.png`。日志记录请求模型、响应模型（未提供为 UNKNOWN）、请求 ID、输入和输出 SHA-256、像素和用量（若返回）。只检查 PNG 头和像素，不替代完整解码或人工视觉验收。出图后必须打开检查；未验收为候选。

网络超时/服务端错误可能已执行请求，不自动重试，避免重复计费。没有自动降级模型或自动换地址。失败目录和日志保留用于排查。

## 尺寸

原生尺寸两边为16倍数、最大3840、长短边不超过3倍，总像素655360至8294400。2000×2000和1600×2000可直接请求。

A+ 桌面端独立生成1952×800，再等比缩小到1464×600；手机端独立生成1280×960，再等比缩小到600×450。此脚本只保存原始输出，不进行重构、拉伸或补白；后续排版与导出需单独验收。大于2560×1440像素面积的输出在官方指南中标为实验性，正式交付须检查。

## 接通验收

有效凭据配置后：check → 一次低质量测试生图 → 查看图片 → 用该图测试编辑 → 查看编辑结果。两次真实请求及逐张检查前，不得报告“生图和改图已通过”。测试素材单独存入 checks，不当作真实商品图。

本地测试：`python3 -m unittest discover -s scripts -p 'test_image25.py' -v`，均为模拟响应，不消费额度。

来源（2026-09-09 核对）：[官方模型](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)、[官方图像指南](https://developers.openai.com/api/docs/guides/image-generation)。
