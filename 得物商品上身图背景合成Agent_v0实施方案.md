# 得物商品上身图背景合成 Agent v0 实施方案

## 1. 项目目标

搭建一个本地可运行的背景合成 Agent：用户一次上传 8 张绿幕或白幕商品上身图，系统从固定背景库中自动匹配干净电商外景背景，生成 8 张结果图，并给出通过、可参考、未通过状态和精准中文原因。

v0 的核心目标不是追求一次性完美，而是建立可无人值守、可诊断、可重试、可积累数据的闭环。

## 2. 成功标准

| 指标 | v0 标准 |
|---|---|
| 单批输入 | 8 张图 |
| 背景库 | 20 张固定背景 |
| 首版成功率 | 8 张中至少 5-6 张达到通过或可参考 |
| 商品保护 | 版型、Logo、图案、鞋型、外观严格不能变化 |
| 允许变化 | 亮度、色温、整体光照可轻微调整 |
| 坐姿逻辑 | 坐姿必须保留或生成合理支撑关系 |
| 输出方式 | 本地网页在线阅览、单张下载、一键下载 zip |
| 失败处理 | 失败图也输出，但必须标明原因和建议 |
| 处理方式 | RTX 3060 Laptop 12GB 串行处理 |
| 单批耗时 | 预计 1-3 小时，无人值守 |

## 3. v0 范围

### 3.1 支持

| 类型 | 支持策略 |
|---|---|
| 站姿全身商品图 | 支持 |
| 坐姿商品图 | 支持，必须保留支撑逻辑 |
| 坐姿 + 普通椅子 | 默认保留椅子 |
| 坐姿 + 透明椅 | 支持但标记高风险 |
| 白幕图 | 支持，但白衣白鞋边缘需重点检查 |
| 绿幕图 | 支持，重点处理绿边和反光 |
| 单人图 | 支持 |
| 得物商品上身图 | v0 核心场景 |

### 3.2 暂不支持

| 暂不支持 | 原因 |
|---|---|
| 多人图 | 姿态、遮挡、商品保护复杂度高 |
| 生成背景模式 | v0 先固定背景库，降低不确定性 |
| 完全替换椅子 | 坐姿逻辑风险高 |
| 整图重绘人物 | 容易改变商品、脸和姿态 |
| GPU 并发处理 | RTX 3060 Laptop 12GB 不适合并发 |

## 4. 用户流程

1. 打开本地网页。
2. 上传 8 张绿幕或白幕商品上身图。
3. 选择背景库：默认使用“冷灰调干净电商外景库”。
4. 点击开始处理。
5. 系统逐张串行处理。
6. 结果页展示 8 张结果卡片。
7. 每张卡片显示最终图、状态、精准原因、建议、耗时、使用背景编号。
8. 用户可单张下载，也可一键下载 zip。

## 5. 系统架构

| 模块 | 职责 | 运行位置 |
|---|---|---|
| 本地网页 | 上传、进度展示、结果阅览、下载 | 本地 |
| FastAPI 后端 | 接收任务、管理状态、提供结果接口 | 本地 |
| Agent 编排器 | 串行处理 8 张图，控制重试与质检 | 本地 |
| 图像处理模块 | 抠图、合成、缩放、阴影基础处理 | 本地 |
| 背景库管理 | 保存 20 张背景及 metadata | 本地 |
| 外部视觉模型 API | 姿态判断、质检、失败原因生成 | 外部 |
| 外部图像 API | 背景库生成、困难局部修复兜底 | 外部 |
| 报告生成器 | 生成 report.json、report.html、zip | 本地 |

## 6. Agent 状态机

| 状态 | 输入 | 输出 | 失败处理 |
|---|---|---|---|
| `queued` | 上传任务 | 待处理任务 | 无 |
| `validate_input` | 原图 | 分辨率、比例、格式检查结果 | 格式错误则标记失败 |
| `analyze_subject` | 原图 | 姿态、支撑物、商品区域初判 | API 失败则走保守规则 |
| `select_background` | 姿态 + 背景 metadata | 背景编号 | 不匹配则换下一张 |
| `matte_subject` | 原图 | alpha、RGBA、主体 mask | 失败则重试一次 |
| `protect_product` | 原图 + mask | 商品保护区 | 保护区不明确则标高风险 |
| `compose_initial` | RGBA + 背景 | 初步合成图 | 落位失败则换背景 |
| `harmonize_light` | 初步合成图 | 光照匹配图 | 失败则降低处理强度 |
| `add_contact_shadow` | 光照匹配图 | 阴影修复图 | 阴影不足则标可参考或失败 |
| `quality_check` | 最终图 + 原图 | 状态、原因、建议 | 不合格则自动重试一次 |
| `export_result` | 所有中间结果 | 结果图、报告、zip | 无 |

## 7. 单张图处理流程

```text
原图
  -> 输入检查
  -> 姿态与支撑关系分析
  -> 背景匹配
  -> 抠图与 alpha 生成
  -> 去绿边/白边
  -> 商品保护 mask 生成
  -> 初步合成
  -> 光照与色温匹配
  -> 接触阴影修复
  -> 商品不变性检查
  -> 真实感质检
  -> 输出状态、原因、建议
```

## 8. 背景库规格

### 8.1 风格定位

背景库统一为冷灰调、干净电商外景，不做强故事感大片。

| 项 | 标准 |
|---|---|
| 风格 | 干净、商业、外景、电商可用 |
| 色调 | 偏冷灰、中性、低饱和 |
| 光线 | 柔和自然光，阴天或轻晴优先 |
| 景深 | 清晰或轻微虚化，禁止强虚化 |
| 人物 | 背景中不能有人 |
| 文字 | 不能有文字、品牌、Logo、车牌、水印 |
| 构图 | 中央留空，方便放置模特 |
| 地面 | 必须有清晰接触面 |
| 遮挡 | 不要在主体落位区出现复杂遮挡 |

### 8.2 数量分配

| 编号 | 类型 | 数量 | 主要用途 |
|---|---|---:|---|
| B01-B06 | 街头水泥地 | 6 | 站姿、潮流鞋服 |
| B07-B11 | 山野石地/石板平台 | 5 | 户外、机能风 |
| B12-B15 | 街头台阶 | 4 | 坐姿、半坐姿 |
| B16-B18 | 山野石台/平台 | 3 | 坐姿户外图 |
| B19-B20 | 矮墙/长椅 | 2 | 坐姿兜底 |

### 8.3 背景 metadata

每张背景图必须配一个 metadata，供 Agent 自动匹配。

```json
{
  "id": "B01",
  "file": "B01_clean_urban_concrete.png",
  "scene_type": "street",
  "pose_fit": ["standing"],
  "sit_support": false,
  "ground_type": "concrete",
  "lighting_direction": "front_left",
  "color_temperature": "cool_neutral",
  "depth_of_field": "sharp",
  "style": ["clean_ecommerce", "urban", "streetwear"],
  "risk_notes": []
}
```

## 9. 背景匹配规则

| 输入识别 | 匹配策略 |
|---|---|
| 站姿 | 优先街头水泥地、山野石板平台 |
| 坐姿 + 椅子 | 选择有平整地面背景，默认保留椅子 |
| 坐姿 + 无明显椅子 | 优先台阶、石台、矮墙、长椅 |
| 户外/机能服 | 优先山野石地、石台 |
| 潮流鞋服 | 优先街头、城市墙面、台阶 |
| 白鞋/白袜 | 避免过亮地面，防止边缘丢失 |
| 黑鞋/深色裤 | 避免过暗地面，保证轮廓 |
| 透明椅 | 选择干净平整地面，降低复杂反射风险 |

## 10. 商品保护规则

### 10.1 严格禁止变化

| 区域 | 禁止变化 |
|---|---|
| 衣服 | 版型、图案、Logo、纹理、褶皱结构 |
| 鞋子 | 鞋型、黑白分区、Logo、鞋面细节 |
| 脸 | 五官、脸型、表情 |
| 姿势 | 坐姿、手脚关系、身体轮廓 |
| 商品外观 | 颜色分区、材质、款式识别特征 |

### 10.2 允许轻微变化

| 区域 | 允许变化 |
|---|---|
| 整体主体 | 轻微亮度匹配 |
| 皮肤 | 轻微色温统一 |
| 商品 | 轻微光照统一，但不能改变颜色分区 |
| 椅子/道具 | 光照、阴影、色温可调整 |

### 10.3 外部 API 约束

外部图像 API 不允许直接重画整张人物图。只能在 mask 约束下处理背景、边缘、阴影和局部光照。商品、Logo、人脸、衣服主体区域必须锁定。

## 11. 质检规则

### 11.1 状态定义

| 状态 | 含义 |
|---|---|
| 通过 | 商品不变、人物不漂浮、边缘干净、光照自然 |
| 可参考 | 合成方向可用，但存在轻微边缘、亮度或风格问题 |
| 未通过 | 商品被改、坐姿逻辑错误、明显漂浮、绿边严重、脸变形 |

### 11.2 检查项

| 检查项 | 失败条件 | 回退动作 |
|---|---|---|
| 商品不变性 | 鞋型、Logo、图案、版型变化 | 判未通过，不强行输出通过 |
| 人脸不变性 | 五官、脸型、表情变化 | 判未通过 |
| 边缘质量 | 明显绿边、白边、锯齿、羽化过度 | 重试去边 |
| 接触关系 | 鞋底、椅脚、腿部悬空 | 重试阴影或换背景 |
| 坐姿逻辑 | 坐姿支撑物消失 | 判未通过或换可坐背景 |
| 光照一致性 | 前景棚拍感明显，背景外景光不匹配 | 重试光照匹配 |
| 背景虚化 | 背景过度虚化导致贴图感 | 换背景或降低虚化 |
| 透明道具 | 透明椅反光不自然 | 标可参考或未通过 |

## 12. 中文原因生成规范

原因必须自然、精准、可行动，避免只给技术标签。

| 问题 | 文案示例 |
|---|---|
| 绿边 | 头发左侧和手臂边缘残留绿色反光，近看仍有棚拍痕迹。 |
| 漂浮 | 左脚鞋底与地面没有形成足够接触阴影，人物有轻微漂浮感。 |
| 商品变化 | 鞋面黑白分区疑似被模型轻微改写，不建议作为正式商品图。 |
| 椅子逻辑 | 模特为坐姿，但当前背景中没有合理支撑物，画面逻辑不成立。 |
| 背景过虚 | 背景虚化强度偏高，人物像贴在背景前，真实感不足。 |
| 光照不合 | 人物是偏暖棚拍光，背景是冷调外景光，脸部和腿部亮度不匹配。 |
| 透明椅风险 | 透明椅边缘反光仍保留棚拍质感，与街头背景融合不够自然。 |

每张图还需要给出一句建议：

| 问题 | 建议示例 |
|---|---|
| 坐姿支撑不自然 | 建议换用台阶、矮墙或长椅背景重跑。 |
| 绿边明显 | 建议降低背景复杂度，并提高边缘去色溢强度。 |
| 光照不匹配 | 建议换用冷灰调阴天背景，或重跑光照匹配。 |
| 商品疑似变化 | 建议使用更严格的商品保护 mask 后重跑。 |

## 13. 输出结构

### 13.1 页面展示

结果页以 8 张卡片展示：

| 字段 | 内容 |
|---|---|
| 结果图 | 最终图预览 |
| 状态 | 通过 / 可参考 / 未通过 |
| 原因 | 中文自然语言 |
| 建议 | 下一步修复建议 |
| 背景 | 背景编号、场景类型 |
| 耗时 | 单张处理耗时 |
| 中间结果 | 抠图、初步合成、最终处理图 |
| 下载 | 单张下载 |

### 13.2 zip 目录

```text
batch_YYYYMMDD_HHMMSS.zip
  final_pass/
  final_review/
  final_fail/
  debug_matte/
  debug_composite/
  debug_final/
  background_used/
  report.html
  report.json
```

### 13.3 report.json 结构

```json
{
  "batch_id": "20260605_153000",
  "status": "completed",
  "total": 8,
  "pass": 5,
  "review": 2,
  "fail": 1,
  "items": [
    {
      "input": "input_01.png",
      "final": "final_pass/input_01_final.png",
      "status": "pass",
      "background_id": "B03",
      "reason": "主体和背景亮度自然，鞋型和衣服图案未发现明显变化。",
      "suggestion": "可作为正式图使用。",
      "elapsed_seconds": 612,
      "risk_tags": []
    }
  ]
}
```

## 14. 本地目录结构

```text
dewu-bg-agent/
  app/
    main.py
    agent/
      pipeline.py
      state.py
      quality_check.py
      background_matcher.py
      product_protection.py
    image_ops/
      matting.py
      despill.py
      compose.py
      relight.py
      shadow.py
    api_clients/
      vision_api.py
      image_api.py
    web/
      templates/
      static/
  assets/
    backgrounds/
      B01_clean_urban_concrete.png
      backgrounds.json
  data/
    batches/
  docs/
  README.md
```

## 15. 外部 API 使用边界

| 用途 | 是否允许 | 说明 |
|---|---|---|
| 生成 20 张背景库 | 允许 | 背景不含用户商品图，风险低 |
| 姿态与支撑关系判断 | 允许 | 可上传原图 |
| 结果质检 | 允许 | 可上传原图与结果图 |
| 中文原因生成 | 允许 | 基于质检结果生成 |
| 局部阴影/边缘修复 | 允许 | 必须使用 mask 约束 |
| 整图重绘人物 | 禁止 | 容易改变商品 |
| 自由修改商品区域 | 禁止 | 违反商品保护原则 |

所有外部调用必须写入 report，包括调用目的、输入文件、输出文件、是否影响主体区域。

## 16. 背景库生成提示词模板

### 16.1 街头站姿背景

```text
Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background.
Empty urban concrete floor with a neutral cool gray wall, soft overcast daylight, central negative space for a full-body fashion model.
No people, no products, no text, no logos, no signs, no vehicles near the center, no watermark.
Sharp or mild depth of field only, not overly blurred.
The foreground floor must be clear, flat, and suitable for realistic shoe contact shadows.
Cool gray low-saturation palette, clean streetwear ecommerce look.
```

### 16.2 山野站姿背景

```text
Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background.
Empty stone platform or flat rock ground in a low-saturation mountain outdoor setting, soft overcast daylight, cool gray tone.
Leave central negative space for a full-body fashion model.
No people, no products, no text, no logos, no watermark.
The foreground must have a clear flat contact area for shoes, with mild background depth only.
Avoid dramatic landscape, strong fog, strong backlight, or fantasy mood.
```

### 16.3 台阶坐姿背景

```text
Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background.
Modern outdoor concrete steps or stone steps, cool gray tone, soft natural daylight.
The center must have a clear sitting surface and clean floor/contact area for compositing a seated fashion model.
No people, no products, no text, no logos, no watermark.
No clutter, no strong shadows, no dramatic perspective.
Commercial fashion ecommerce style, clean and realistic.
```

### 16.4 矮墙/长椅坐姿背景

```text
Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background.
Minimal outdoor low wall or simple bench with a clear sitting surface, cool gray low-saturation palette, soft overcast daylight.
Leave central space for a seated fashion model.
No people, no products, no text, no logos, no watermark.
The ground must be clean and suitable for contact shadows.
Avoid ornate furniture, strong branding, busy streets, or heavy blur.
```

## 17. 技术实现建议

| 模块 | 推荐技术 |
|---|---|
| Web 后端 | Python FastAPI |
| 前端 | 简单 HTML/CSS/JS 或轻量 React |
| 图像处理 | OpenCV、Pillow、PyTorch |
| 任务队列 | v0 可先用本地串行队列，后续再接 Redis |
| 抠图 | 本地 matting 模型优先，外部兜底 |
| 光照匹配 | 本地轻处理 + 外部局部修复 |
| 质检 | 外部视觉模型 + 本地规则 |
| 打包下载 | Python zipfile |
| 结果页 | report.html 静态生成 + Web 预览 |

## 18. 开发里程碑

### M1：背景库

| 任务 | 验收 |
|---|---|
| 生成 20 张背景 | 每张 2:3、无人、无字、无品牌 |
| 编写 backgrounds.json | 每张都有 metadata |
| 人工初筛 | 删除不适合落位的背景 |

### M2：最小网页

| 任务 | 验收 |
|---|---|
| 上传 8 张图 | 能创建 batch |
| 展示进度 | 能看到逐张处理状态 |
| 结果页 | 能展示 8 张结果卡片 |
| 下载 | 支持单张和 zip 下载 |

### M3：本地基础合成

| 任务 | 验收 |
|---|---|
| 抠图 | 输出 debug_matte |
| 背景匹配 | 站姿/坐姿选择合理背景 |
| 初步合成 | 输出 debug_composite |
| 中间结果保留 | 每张图有可追踪过程 |

### M4：质检与报告

| 任务 | 验收 |
|---|---|
| 状态判断 | 通过/可参考/未通过 |
| 中文原因 | 自然语言精准说明 |
| 建议 | 每张图有修复建议 |
| report.json/html | 内容完整 |

### M5：自动重试

| 任务 | 验收 |
|---|---|
| 每张最多重试 1 次 | 不无限循环 |
| 重试策略 | 按失败原因换背景或调整处理强度 |
| 最终输出 | 失败图也输出并标明原因 |

## 19. 风险与对策

| 风险 | 影响 | v0 对策 |
|---|---|---|
| RTX 3060 Laptop 速度慢 | 单批耗时长 | 串行无人值守，避免并发 |
| 透明椅难处理 | 反光和边缘假 | 标高风险，保留中间图 |
| 商品被外部模型改写 | 电商不可用 | 严格 mask，不允许整图重绘 |
| 坐姿去掉支撑物 | 图像逻辑错误 | 默认保留支撑物 |
| 背景风格不匹配 | 审美一般 | 可输出为可参考，不判失败 |
| 质检误判 | 差图进入通过 | 宁可降级为可参考或未通过 |
| 背景库太少 | 重复感强 | v0 接受，后续扩展到 100 张 |

## 20. v1 方向

| 方向 | 说明 |
|---|---|
| 背景库扩展 | 从 20 张扩到 100-300 张 |
| 背景自动生成 | 根据商品风格生成背景 |
| 专用 matting 微调 | 针对得物绿幕/白幕样本优化头发和透明道具 |
| 商品保护评估器 | 专门检测 Logo、鞋型、图案是否变化 |
| 批量队列 | 支持多批次排队 |
| 云 GPU worker | 将重模型处理放到云端 |
| 运营工作台 | 支持历史任务、筛选、重跑、收藏背景 |

