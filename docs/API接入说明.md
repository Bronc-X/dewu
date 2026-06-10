# API 接入说明

本项目后端已经按“真实工具接入”方式预留接口。原则是：

- 选择第三方 provider 时必须配置真实 key。
- 未配置 key 时返回明确的 `ProviderNotConfiguredError`，不会生成硬编码图片，也不会伪造成功结果。
- 本地算法只代表自研处理链路，例如主体识别、局部合成、光影处理、质检，不冒充 PhotoRoom、Adobe 或 Photoshop。

## 1. Provider 配置

`.env` 中可配置三类 provider：

```env
MATTING_PROVIDER=local
COMPOSITING_PROVIDER=local
BACKGROUND_PROVIDER=local
```

当前支持值：

| 配置项 | 可选值 | 说明 |
|---|---|---|
| `MATTING_PROVIDER` | `local` / `photoroom` | 抠图来源。`photoroom` 会真实调用 PhotoRoom Remove Background API。 |
| `COMPOSITING_PROVIDER` | `local` / `photoroom` | 前后景合成来源。`photoroom` 会真实调用 PhotoRoom Image Editing API。 |
| `BACKGROUND_PROVIDER` | `local` / `openai_compatible` / `adobe_firefly` | 背景生成来源。当前脚本默认用 OpenAI-compatible；Adobe Firefly 已预留真实接口。 |

## 2. PhotoRoom

环境变量：

```env
PHOTOROOM_API_KEY=
PHOTOROOM_SEGMENT_URL=https://sdk.photoroom.com/v1/segment
PHOTOROOM_EDIT_URL=https://image-api.photoroom.com/v2/edit
PHOTOROOM_AI_BACKGROUND_MODEL=
```

已接入能力：

- `remove_background`：调用 `POST /v1/segment`，用于高质量抠图，并从 RGBA 结果中提取 alpha mask。
- `edit_image`：调用 `POST /v2/edit`，支持 `background.imageFile`、`background.prompt`、`background.guidance.*`、`lighting.mode`、`shadow.mode`、`removeBackground` 等参数。

后端路由：

```text
GET  /api/providers/status
POST /api/tools/photoroom/remove-background
POST /api/tools/photoroom/edit
```

示例请求：

```json
{
  "image_path": "data/projects/proj_x/assets/input_01.png",
  "background_image_path": "assets/backgrounds/B01_street.png",
  "lighting_mode": "ai.auto",
  "shadow_mode": "ai.soft",
  "remove_background": true
}
```

## 3. Adobe Firefly

环境变量：

```env
ADOBE_CLIENT_ID=
ADOBE_CLIENT_SECRET=
ADOBE_SCOPE=openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis
ADOBE_TOKEN_URL=https://ims-na1.adobelogin.com/ims/token/v3
ADOBE_FIREFLY_BASE_URL=https://firefly-api.adobe.io
ADOBE_JOB_POLL_ATTEMPTS=40
ADOBE_JOB_POLL_INTERVAL_SECONDS=3
```

已预留真实接口：

```text
POST /api/tools/adobe/firefly/generate-background
```

该接口会先通过 Adobe IMS 获取 access token，再调用 Firefly 异步生图接口，并轮询任务状态。没有 Adobe 凭证时不会 fallback 到本地假图。

示例请求：

```json
{
  "prompt": "photorealistic outdoor mountain stone platform, soft overcast daylight, empty center for fashion model",
  "output_path": "data/provider_outputs/firefly_bg_01.png",
  "content_class": "photo"
}
```

## 4. Adobe Photoshop API

环境变量复用 Adobe 凭证：

```env
ADOBE_CLIENT_ID=
ADOBE_CLIENT_SECRET=
ADOBE_PHOTOSHOP_BASE_URL=https://image.adobe.io
```

已预留真实接口：

```text
POST /api/tools/adobe/photoshop/remove-background
```

注意：Photoshop API 的远程工作流通常要求源图是外部可访问的签名 URL。当前路由接收 `source_url`，不直接上传本地文件。未来如果要自动化完整 Photoshop 工作流，需要接对象存储并生成 signed URL。

示例请求：

```json
{
  "source_url": "https://example-cdn.com/signed/input.png",
  "mode": "cutout",
  "media_type": "image/png"
}
```

## 5. 项目制 API

为了给未来 React/Tailwind 前端使用，后端已预留项目维度接口：

```text
GET   /api/projects
POST  /api/projects
GET   /api/projects/{project_id}
PATCH /api/projects/{project_id}
POST  /api/projects/{project_id}/assets
GET   /api/projects/{project_id}/assets
POST  /api/projects/{project_id}/batches/{batch_id}
GET   /api/projects/{project_id}/batches
```

项目类型：

```text
new_listing
style_reuse
campaign
buyer_preview
```

这对应前端的四类项目入口：商品上新、款式复用、活动投放、买家预览。

## 6. 现有批次 API

原有批量处理接口仍保留：

```text
POST /batches
GET  /batches/{batch_id}
GET  /batches/{batch_id}/report.json
GET  /batches/{batch_id}/report.html
GET  /batches/{batch_id}/zip
GET  /batches/{batch_id}/file
POST /batches/{batch_id}/open-folder
POST /batches/{batch_id}/open-file
```

`POST /batches` 支持上传 1 到 `MAX_IMAGES_PER_BATCH` 张图片，默认上限为 8 张；不再要求一次必须上传满 8 张。

## 7. 前端接入建议

前端不要直接保存任何第三方 API key。推荐链路：

```text
React/Tailwind 前端
  -> 本项目 FastAPI 后端
  -> PhotoRoom / Adobe / Photoshop / OpenAI-compatible provider
  -> 后端保存结果和 report
  -> 前端展示项目、批次、质检、下载
```

前端可先调用 `GET /api/providers/status` 判断哪些工具已经配置，再决定是否显示对应功能入口。
