# 得物商品上身图背景合成 Agent

本项目是一个本地运行的商品上身图背景合成 Agent。用户一次上传 8 张绿幕或白幕图片，系统从固定背景库中自动匹配干净电商外景背景，串行生成结果图，保留中间过程，并输出中文质检报告与 zip 包。

## 功能

- 本地网页上传批量图片
- 固定背景库自动匹配
- 串行任务处理，适合 RTX 3060 Laptop 12GB
- 保留抠图、初步合成、最终图等中间结果
- 生成 `通过 / 可参考 / 未通过` 结果
- 中文自然语言原因和修复建议
- 单张下载和批量 zip 下载
- 固定 8 图回归集，便于每次调参后做可重复检查
- 商品主体保护分数与自动回退边界，避免修边误伤鞋型、Logo、服装纹理
- 报告中展示原图、抠图、初合成、最终图，便于逐张对比
- 外部模型 API 配置位预留，填好 key 后可接入真实视觉/图像模型

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts\create_placeholder_backgrounds.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

批量生成时不要使用 `--reload`。处理过程中会持续写入 `data/batches/`，热重载可能重启服务并中断后台任务。

打开：

```text
http://127.0.0.1:8000
```

## 外部 API

复制 `.env.example` 为 `.env` 后填写 API 配置。未填写时，系统会使用本地占位逻辑跑完整闭环，方便验证页面、文件结构、报告和 zip。

```env
OPENAI_API_KEY=
VISION_API_BASE_URL=
VISION_API_KEY=
VISION_MODEL=gpt-5.4-mini
IMAGE_API_KEY=
```

NewAPI / OpenAI-compatible 通道需要把 `VISION_API_BASE_URL` 写成带 `/v1` 的地址，例如 `https://aicanapi.com/v1`。

生成真实 20 张背景库：

```powershell
python scripts\generate_background_library.py
```

如果没有 API key，可以先使用占位背景库：

```powershell
python scripts\create_placeholder_backgrounds.py
```

## 回归验证

默认回归集位于：

```text
data/regression_cases/default/
```

该目录必须正好放 8 张真实商品图。当前仓库里可以先用已验证 smoke 输入图跑通流程；明天替换为真实得物图后，继续使用同一条命令：

```powershell
python scripts\run_regression_batch.py
```

每次修改抠图、羽化、亮度、背景匹配或模型修边策略后，都先跑这套固定样本。报告会记录商品变化分和保护选择：如果后续模型修边导致商品主体变化超过阈值，系统会回退到修边前版本。

## 输出结构

```text
data/batches/<batch_id>/
  input/
  final_pass/
  final_review/
  final_fail/
  debug_matte/
  debug_composite/
  debug_final/
  background_used/
  report.html
  report.json
  batch_<batch_id>.zip
```
