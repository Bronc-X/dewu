# Hypersuite 云算力平台训练与 PhotoRoom 替代评估

日期：2026-06-17

## 0. 结论先说

如果目标是“用这个平台来训练并逐步替代 PhotoRoom”，我的判断是：

1. **Hypersuite 可以作为训练、部署、算力调度和模型网关底座**。它覆盖 Notebook 开发、分布式训练、TensorBoard、模型微调、自定义模型、模型仓库、镜像仓库、vLLM/SGLang 推理部署、HPA 扩容、日志、账单、多租户和 API 网关。
2. **它不是开箱即用的 PhotoRoom 替代品**。PhotoRoom 的核心价值不是 GPU，而是商品图专用模型、编辑能力、质量控制、批量 API、产品工作流和多年数据闭环。
3. **平台现有能力大约满足“基础设施层”的 70% 到 80%，满足“PhotoRoom 商品图能力层”的 20% 到 35%**。能不能替代 PhotoRoom，关键不在平台按钮，而在你是否能补齐数据、标注、图像模型、质检、人工复核和业务反馈闭环。
4. **第一阶段不建议直接训练端到端大模型**。更稳的路线是：先用 PhotoRoom/成熟外部 API 跑商业闭环，同时在自研系统里沉淀原图、mask、失败原因、人工偏好和平台审核结果；再逐步替代抠图、固定背景合成、质检；最后再碰 AI 背景、重光照、阴影、虚拟模特这类高难模块。

## 1. 平台功能范围

### 1.1 Hypersuite 智算云平台可用能力

| 模块 | 你能用到的功能 | 对训练 PhotoRoom 替代能力的价值 |
|---|---|---|
| 算力资源 | GPU 主机、国产 Mars X201 GPU、共享/专属资源池、Kubernetes 管理 | 训练、批量推理、模型部署的基础算力 |
| 调度 | Volcano 大规模 GPU 调度、HAMi/sGPU 共享、任务优先级、紧凑/均衡调度 | 降低排队和碎片化，提高 GPU 利用率 |
| 开发环境 | JupyterLab/Notebook、在线终端、镜像选择、资源规格、存储挂载、日志 | 算法开发、数据处理、实验调试 |
| 分布式训练 | PyTorch 等训练任务创建/运行/停止、镜像、命令、实例数、资源规格、日志目录 | 跑 matting、质检模型、LoRA 或 diffusion 微调 |
| 训练可视化 | TensorBoard 展示 loss、accuracy、learning rate、吞吐等曲线 | 看训练是否收敛、是否过拟合、是否异常 |
| 模型微调 | LLaMA-Factory 镜像，SFT/PT/RM，LoRA 和 full fine-tuning，DeepSpeed 单机/多机 | 更偏 LLM/多模态问答微调；对图像生成模型还要自己带训练代码 |
| 数据 | PVC/并行文件存储、公共数据集、自定义数据集上传 | 存原图、mask、标注、训练集、模型 checkpoint |
| 模型资产 | 模型仓库、模型分类、模型版本、模型上传、自定义模型 | 管理训练好的模型与部署参数 |
| 镜像资产 | 公共基础镜像、自定义镜像仓库、Docker push | 适合封装 SAM/BiRefNet/SDXL/Qwen-Image-Edit 等自有运行环境 |
| 推理部署 | 模型试运行、vLLM/SGLang、单机多卡、多机多卡、API-Key、服务端点 | 把训练好的模型变成可调用 API |
| 弹性与监控 | HPA 横向扩展、GPU/CPU/内存/存储监控、容器日志 | 支撑批量处理和生产级服务稳定性 |
| 多租户与权限 | 租户、用户、用户组、RBAC、集群授权、专属节点 | 给内部团队、标注团队、外包团队做权限隔离 |
| 成本与日志 | 卡时计费、token 计费、日志查询、审计轨迹 | 统计训练成本、推理成本、失败原因 |

### 1.2 GTtoken 可用能力

GTtoken 更像“模型 API 网关 + 用量计费 + 分销系统”，不是训练平台。

| 模块 | 可用能力 | 对本项目的价值 |
|---|---|---|
| 统一 API 网关 | OpenAI 兼容 API、渠道管理、Vkey 虚拟密钥 | 把自研模型、外部模型、备用模型统一成一个入口 |
| 渠道路由 | 多渠道负载均衡、熔断、重试、权重分发、渠道亲和性 | 降低外部模型不稳定风险 |
| 权限与额度 | 用户组、用户、令牌、模型限制、IP 白名单、并发/次数/token 限流 | 控制不同客户、标注员、内部应用的访问范围 |
| 计费 | 按 token、按次、按时长、按分辨率，模型倍率、分组倍率 | 可以做图片生成、批量推理和客户侧成本核算 |
| 日志 | 按时间、模型、令牌查询 API 调用日志 | 追踪每次生成、失败、重试和费用 |
| 绘图设置 | 可配置绘图 Proxy 地址、API 密钥、超时和绘图计费 | 说明平台预留图像生成接入位，但不是内置 PhotoRoom 能力 |
| 模型清单 | 多模态视觉模型、OCR、embedding/reranker 等 | 可用于质检、图文审核、文本理解，不等于商品图编辑模型 |

## 2. PhotoRoom 能力拆解与平台匹配度

PhotoRoom 官方 API 已覆盖：背景移除、AI 背景、真实阴影、重光照、文字移除、扩图、uncrop、upscale、beautifier、Edit With AI、Virtual Model、Flat Lay、Ghost Mannequin、定位/缩放/边距等能力。它还把这些能力产品化成单一图像编辑 API，用于商品目录、市场平台和广告图批量生产。

### 2.1 匹配度总表

| PhotoRoom 能力 | Hypersuite 现状 | 匹配度 | 缺口 |
|---|---:|---:|---|
| 背景移除 / 抠图 | 可训练/部署 matting 模型，但没有内置 PhotoRoom 级抠图服务 | 中 | 需要 SAM/BiRefNet/MODNet 等模型、mask 标注、边缘指标、批量 API |
| Alpha matte / 发丝 / 鞋带 / 半透明边缘 | 平台提供算力，不提供专用标注和模型 | 低到中 | 需要精标 alpha、trimap、边界 F-score、人工复核 |
| 背景替换 / 固定背景合成 | 可用自研工程实现，平台负责部署 | 中高 | 需要背景库、主体落位规则、光色匹配、质检 |
| AI 背景生成 | GTtoken 有绘图 Proxy 配置，Hypersuite 可部署图像模型 | 中 | 需要 SDXL/Qwen-Image-Edit/Flux 等模型、LoRA、提示词模板、商品保护 |
| 阴影 | 平台无现成能力 | 低 | 需要接触点检测、投影方向、地面/坐姿逻辑、局部修复模型 |
| 重光照 | 平台无现成能力 | 低 | 需要光照方向/色温标注、relight 模型或规则 + 质检 |
| 定位、缩放、留白、尺寸适配 | 可纯工程实现 | 高 | 需要电商平台规格和自动 QA |
| 扩图 / uncrop / upscale | 可接外部模型或自部署模型 | 中 | 需要模型选择、稳定性评估、商品一致性检测 |
| 文字/瑕疵移除 | 可接图像编辑模型 | 中低 | 容易改商品本体，必须加人工确认 |
| Virtual Model / 上身图生成 | 平台无现成垂直能力 | 低 | 需要服装/人体/姿态/商品保真专门模型，大量授权数据 |
| Flat Lay / Ghost Mannequin | 平台无现成垂直能力 | 低 | 需要服装类目数据、版型保持、人体/衣物结构约束 |
| 自动 QA | 可用视觉模型 + 规则自研 | 中 | 需要人工标签、平台审核结果、失败原因体系 |
| 批量 API 和生产流程 | GTtoken + Hypersuite 可承接部分 API/计费/日志 | 中 | 还要自建项目、批次、复核、返修、导出、客户工作台 |
| 数据闭环 / 主动学习 | 平台有训练日志，但没有完整标注闭环 | 低到中 | 需要外部标注系统、数据版本、失败样本回流 |

### 2.2 是否能“全部满足”？

不能。它能满足“训练和部署模型所需的底座”，但不能单独满足 PhotoRoom 替代的全链路。

更准确地说：

| 层级 | 平台满足度 | 说明 |
|---|---:|---|
| GPU/容器/存储/调度 | 高 | 这正是 Hypersuite 的强项 |
| 训练运行环境 | 中高 | PyTorch/分布式训练/TensorBoard 可用，但图像模型训练脚本和依赖要自己带 |
| 推理部署 | 中高 | vLLM/SGLang 偏 LLM，多数图像编辑模型可能要用自定义镜像/通用部署 |
| API 网关/计费 | 中高 | GTtoken 对 token/API 管理强，但图像按张、按分辨率、按时长还要适配业务 |
| 数据标注 | 低 | 手册没有看到完整图片标注平台、标注任务分发、质检抽检、返工队列 |
| 商品图专用模型 | 低 | 需要你自研、接外部模型或购买模型能力 |
| PhotoRoom 式产品工作流 | 低 | 需要自建上传、预览、画布编辑、人工复核、批量导出、审核反馈 |
| 商业可用质量闭环 | 低到中 | 必须依赖真实商家图、人工反馈、平台审核结果和返修数据 |

## 3. 还需要的外部资源

### 3.1 必须补齐

| 外部资源 | 为什么需要 |
|---|---|
| 授权图片数据 | 没有真实商品上身图、人工成品图、失败图，就无法训练出垂直效果 |
| 标注平台 | Hypersuite 手册没有完整图片标注工作台；建议接 CVAT、Label Studio、SageMaker Ground Truth 或标注外包系统 |
| 标注/修图团队 | mask、边缘、失败原因、偏好排序都需要人工判断 |
| 图像算法工程师 | 负责 matting、合成、diffusion/LoRA、质检模型和评估 |
| 后端/工作流工程 | 负责批量任务、队列、回调、重试、导出、权限、成本记录 |
| 前端/复核工作台 | 负责上传、对比、mask 修补、局部重跑、pass/review/fail |
| 对象存储/数据版本管理 | 训练集、验证集、mask、结果图、模型文件都要可追溯 |
| 评估体系 | mIoU、Boundary F-score、DINO/CLIP 商品一致性、人工偏好、平台审核通过率 |
| 合规与授权记录 | 商品图、模特图、品牌 Logo、AI 生成内容标识都要留证 |

### 3.2 建议接入的模型/工具

| 模块 | 可选工具 |
|---|---|
| 抠图/matting | BiRefNet、SAM 2、MODNet、RMBG、商业 API |
| 商品保护 | DINOv2、SigLIP/OpenCLIP、局部 OCR/logo 检测 |
| 背景生成 | SDXL、Flux、Qwen-Image-Edit、商用图像 API |
| 局部编辑 | ControlNet、IP-Adapter、inpainting 模型 |
| 质检 | Qwen-VL 类视觉模型 + 规则引擎 + 人工标签校准 |
| 标注 | CVAT、Label Studio、SageMaker Ground Truth、外包标注团队 |
| 实验管理 | MLflow、Weights & Biases、DVC/LakeFS |
| 队列与批处理 | Celery/RQ/Temporal/Argo Workflows |

## 4. 标注全流程设计

### 4.1 标注目标

不要一上来只标“好/不好”。PhotoRoom 替代需要四类数据：

1. **分割数据**：训练抠图、alpha matte、边缘修复。
2. **合成数据**：训练背景匹配、主体落位、阴影、光照。
3. **质检数据**：训练自动判定 pass/review/fail 和失败原因。
4. **偏好数据**：训练排序器，让系统知道多张候选图哪张更像“可上架商品图”。

### 4.2 标注对象与字段

| 数据对象 | 具体标注内容 | 用途 |
|---|---|---|
| 原始图片 | SKU、类目、品牌/Logo 是否明显、拍摄背景、姿势、站姿/坐姿、光照方向、清晰度 | 数据分层和测试集隔离 |
| 主体 mask | 人、商品、鞋、衣服、配饰、椅子/支撑物分层 mask | 抠图和合成 |
| Alpha/trimap | 前景、背景、不确定边界区；发丝、鞋带、透明/反光区域精修 | 高质量 matting |
| 商品关键区域 | Logo、鞋型、鞋面纹理、服装图案、吊牌、瑕疵不可改区域 | 商品一致性保护 |
| 接触点 | 鞋底接地点、坐姿支撑点、手持/背包接触点 | 阴影和物理合理性 |
| 背景标签 | 场景类别、地面材质、景深、光照方向、色温、适合站姿/坐姿 | 背景匹配和生成 |
| 合成结果 | pass/review/fail、失败原因、是否可返修、返修建议 | 自动 QA 和复核队列 |
| 多候选偏好 | A/B/C 候选排序，最佳图，不能用图 | 排序模型和生成策略优化 |
| 平台审核 | 通过/退回/人工复审、退回原因、适用主图/详情/种草 | 商业可用性闭环 |

### 4.3 标注步骤

1. **数据入库**
   - 每张图生成唯一 ID，绑定 SKU、类目、来源、授权状态、拍摄批次。
   - 原图、人工成品图、PhotoRoom 结果、自研结果都保存。
   - 训练/验证/测试按 SKU 和商家切分，避免同一商品泄漏到测试集。

2. **自动预标**
   - 先用 SAM/BiRefNet/PhotoRoom 生成初始 mask。
   - 自动生成主体 bbox、粗 mask、边缘不确定区、商品区域候选。
   - 把低置信度、复杂边缘、坐姿、白鞋、透明/反光材质送人工精修。

3. **人工精标**
   - 用画笔/多边形/橡皮工具修正 mask。
   - 发丝、鞋带、衣服边缘、椅子边缘、透明材质必须放大到 200% 到 400% 检查。
   - 标出“不可改变商品区域”：Logo、鞋型、图案、颜色、纹理。
   - 标出接地点和阴影方向，尤其是鞋底、坐姿、包带、手持商品。

4. **结果质检标注**
   - 对每张生成图打 `pass / review / fail`。
   - 失败原因建议固定枚举：抠图残留、边缘硬、边缘缺失、商品变形、Logo 改变、颜色偏差、背景假、光影不一致、阴影缺失、坐姿无支撑、比例错误、平台审核风险。
   - 每个失败样本必须写一句“返修建议”，例如“保留椅子重新合成”“换成有台阶支撑的背景”“降低背景虚化”。

5. **偏好排序**
   - 同一原图生成 3 到 6 张候选。
   - 标注员选择最佳图，并按“商品真实度、背景自然度、平台可用性、商业美观度”打分。
   - 如果没有可用图，标 `none_usable`，并记录主因。

6. **二次审核**
   - 抽检 10% 到 20% 样本。
   - 对高价值类目、Logo 明显、AI 改商品风险高的样本做双人审核。
   - 分歧样本进入仲裁队列，形成标注规范补充。

7. **数据集打包**
   - 建议目录结构：

```text
dataset/
  images/original/
  images/photoroom_baseline/
  images/generated/
  masks/foreground_alpha/
  masks/trimap/
  masks/product_protected/
  metadata/images.jsonl
  metadata/qc_labels.jsonl
  metadata/preferences.jsonl
  splits/train.txt
  splits/val.txt
  splits/test.txt
```

8. **上传 Hypersuite**
   - 上传到租户 PVC 或并行文件存储。
   - 在分布式训练任务里挂载数据目录。
   - 如果走 LLaMA-Factory 只适合 SFT/RM 类数据；图像模型训练要用自定义镜像和自定义训练脚本。

9. **训练与验证**
   - 第一批训练优先级：抠图/边缘模型 > 自动质检模型 > 背景匹配/排序模型 > AI 背景 LoRA > 阴影/重光照。
   - 每轮训练固定测试集，不要只看主观样张。

10. **主动学习回流**
   - 上线后把 `review/fail`、人工返修、平台退回、客户不满意样本自动回流。
   - 每周整理高频失败原因，补标，再训练。

### 4.4 反馈信号如何显示

| 阶段 | 信号 | 在哪里看 |
|---|---|---|
| 标注进度 | 已标数量、待标数量、返工率、抽检通过率、类目覆盖 | 外部标注平台或自建复核台 |
| 训练收敛 | train/val loss、mIoU、Boundary F-score、alpha 误差、QA F1、偏好准确率 | Hypersuite 分布式训练 + TensorBoard |
| 训练异常 | loss 不降、验证集变差、显存 OOM、节点失败、数据加载慢 | Hypersuite 训练日志、容器日志、节点资源监控 |
| 推理效果 | 单图耗时、失败率、GPU 利用率、HPA 扩容、API 错误 | Hypersuite 推理服务、日志查询、集群监控 |
| API 成本 | 卡时成本、token/按次/按分辨率费用、单张成本 | Hypersuite 账单 + GTtoken 日志/计费 |
| 业务质量 | pass/review/fail 比例、人工返修率、平台审核通过率、客户采纳率 | 自建项目/批次/复核系统 |
| 主动学习 | 高损失样本、高争议样本、高频失败原因 | 自建数据闭环看板 |

建议把“收敛”拆成两层：

1. **模型收敛**：TensorBoard 上 loss、mIoU、Boundary F-score、QA F1 稳定提升。
2. **业务收敛**：同一类目下人工返修率下降、平台审核通过率上升、单张成本下降。

只看到模型 loss 下降，不等于能替代 PhotoRoom；必须看业务收敛。

## 5. 平台竞争力评估

### 5.1 纵向排名判断

如果按“云算力 + MLOps 平台”纵向比较：

| 梯队 | 平台类型 | Hypersuite 所处位置 |
|---|---|---|
| 第一梯队 | AWS SageMaker、Google Vertex AI/Gemini Enterprise Agent Platform、Azure ML、部分成熟国内云 AI 平台 | 不属于 |
| 第二梯队 | 有完整 GPU/K8s/Notebook/训练/部署/模型仓库/网关/计费能力的企业级 AI 平台 | **Hypersuite 更接近这里** |
| 第三梯队 | 主要卖 GPU 实例、Notebook 或简单容器服务的平台 | Hypersuite 明显强于这类 |
| 垂直应用平台 | PhotoRoom、remove.bg、Claid、Bria、Photoroom API 这类商品图/图像编辑产品 | Hypersuite 不是同一类；它是底座，不是图像编辑成品服务 |

我的排序判断：**在“算力底座/私有化/国产化/网关计费”维度是中游偏上；在“端到端 MLOps 和数据标注”维度是中游；在“PhotoRoom 式商品图产品能力”维度是早期底座，不是成熟竞品。**

### 5.2 比平均水平好的地方

| 优势 | 事实依据 |
|---|---|
| 不只是裸 GPU 租赁 | 手册明确包含 Notebook、分布式训练、模型试运行、模型微调、自定义模型、模型仓库、镜像仓库、推理部署、日志和账单 |
| Kubernetes 和 GPU 调度较完整 | 支持 Volcano GPU 调度、HAMi/sGPU、专属节点、资源组、共享/专属资源池 |
| 推理部署不是空白 | 支持 vLLM、SGLang、单机多卡、多机多卡、HPA、API-Key 和服务端点 |
| 多租户和企业权限体系完整度较好 | 租户、用户、用户组、RBAC、集群授权、专属节点和审计日志都在手册中出现 |
| GTtoken 的商业化网关能力较强 | 支持渠道、Vkey、额度、模型限制、IP 白名单、限流、倍率计费、使用日志、渠道自动检测和失败切换 |
| 对国产算力/私有化场景友好 | 手册定位强调国产算力供给、X201 GPU、深度国产化适配、专属资源池 |

### 5.3 与头部平台相比的差距

| 差距 | 事实依据 |
|---|---|
| 缺少成熟托管标注体系 | AWS SageMaker Ground Truth 官方提供人工标注、私有/供应商/Mechanical Turk workforce 和自定义标注工作流；Hypersuite 手册只看到训练数据上传和少量“标注数据”描述，没有完整图片标注任务系统 |
| 数据集治理弱 | Vertex AI 官方强调 managed datasets、AutoML/custom training、模型管理；Hypersuite 主要是 PVC/公共数据集/自定义目录，缺少数据版本、数据漂移、主动学习闭环 |
| MLOps 自动化弱 | SageMaker/Azure/Vertex 都有更成熟的 pipeline、registry、endpoint、monitoring、CI/CD/MLOps 生态；Hypersuite 手册更多是手动创建任务和部署服务 |
| 生态与模型市场弱 | 头部平台有大量官方集成、预训练模型、市场、监控和安全生态；Hypersuite 模型分类虽有“图像生成与处理”等类别，但不等于有现成 PhotoRoom 级模型 |
| 图像垂直能力不足 | PhotoRoom 官方 API 已经把去背、阴影、重光照、AI 背景、虚拟模特、Flat Lay、Ghost Mannequin、自动 QA 等做成商品图 API；Hypersuite 只是能训练/部署相关模型 |
| 生产级评估与 A/B 不足 | Hypersuite 有日志和 TensorBoard，但没有看到内置商品图质量评估、人工偏好、审核通过率、A/B 测试、模型监控自动回滚 |
| 国际高端 GPU/加速生态不确定 | 手册重点是国产 X201 GPU；如果训练 diffusion、SAM2、Qwen-Image-Edit 等，需要先验证算子、框架版本、显存、吞吐和兼容性 |

## 6. 推荐落地路线

### P0：验证平台能跑你的模型

目标：证明 X201 + 容器 + 存储 + 训练任务能跑通。

1. 上传 100 到 200 张授权商品图。
2. 跑一个 BiRefNet/SAM 类抠图批处理。
3. 跑一个 Qwen-VL/视觉质检 prompt 或轻量分类器。
4. 部署成 API，记录单图耗时、失败率、GPU 占用和单张成本。

### P1：先替代固定背景合成和质检

目标：不承诺全替代 PhotoRoom，只替代可控环节。

1. 标注 300 到 800 张高质量 mask。
2. 建立 pass/review/fail 质检标签。
3. 背景库 + 规则合成 + 商品保护分数。
4. 人工复核台记录失败原因。

### P2：训练垂直抠图和自动 QA

目标：降低 PhotoRoom 调用量和人工返修率。

1. 1,000 到 3,000 张原图。
2. 1,000+ mask/trimap，其中 300+ 精标边缘样本。
3. 5,000 到 20,000 条生成结果质检标签。
4. 验收：自动质检与人工一致率达到 75% 以上，固定测试集优于上一版本。

### P3：AI 背景、阴影、重光照

目标：谨慎替代 PhotoRoom 高难功能。

1. 做 LoRA 或图像编辑模型微调。
2. 引入候选图排序和商品一致性检测。
3. 对高风险功能保留人工确认。
4. 上线时只对低风险类目开放。

## 7. 最重要的采购/合作追问

在投入训练前，建议向 Hypersuite/供应商确认这些问题：

1. X201 GPU 对 PyTorch、CUDA 兼容层、diffusion、SAM2、BiRefNet、Qwen-Image-Edit 的实际支持情况。
2. 是否已有可商用的图像生成/抠图/图像编辑模型镜像，不只是模型分类。
3. 是否支持图片标注任务管理，若不支持，推荐外接哪个标注系统。
4. PVC/并行文件存储对海量小图片读取的吞吐基准。
5. 单机/多机训练的真实可用显存、网络带宽、故障恢复方式。
6. 自定义图像模型部署是否必须走 vLLM/SGLang，还是支持 Triton/TorchServe/FastAPI/ComfyUI 等自定义服务。
7. GTtoken 的绘图 Proxy 是否已有可用图像生成后端，是否支持按张、按分辨率、按失败重试计费。
8. 日志和账单能否按项目、批次、SKU、客户维度导出。
9. 是否支持模型灰度、A/B、回滚和线上监控告警。
10. 数据安全、图片授权、生成内容标识、客户数据隔离如何落地。

## 8. 来源

本报告使用了以下材料：

- 本地手册：`C:/Users/Administrator/Documents/xwechat_files/broncin_80df/msg/file/2026-06/Hypersuite智算云产品用户手册-v1.3-20260507(1).pdf`
- 本地手册：`C:/Users/Administrator/Documents/xwechat_files/broncin_80df/msg/file/2026-06/GTtoken产品手册-v1.0.(1).pdf`
- [PhotoRoom API Documentation: Introduction](https://docs.photoroom.com/)
- [PhotoRoom API Reference](https://docs.photoroom.com/getting-started/api-reference-openapi)
- [PhotoRoom API product page](https://www.photoroom.com/api)
- [PhotoRoom API pricing](https://www.photoroom.com/api/pricing)
- [Amazon SageMaker Ground Truth documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/sms.html)
- [Amazon SageMaker training documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/train-model.html)
- [Amazon SageMaker deployment documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)
- [Google Cloud machine learning on Gemini Enterprise Agent Platform / Vertex AI](https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning)
- [Microsoft Azure Machine Learning](https://azure.microsoft.com/en-us/products/machine-learning)
- [Huawei Cloud ModelArts](https://www.huaweicloud.com/intl/en-us/product/modelarts.html)
