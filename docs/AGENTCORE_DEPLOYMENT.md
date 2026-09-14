# AgentCore 部署说明 — Fly Weight-Lab

> 状态：真实 AgentCore Runtime 已部署到 AWS 并进入 READY，数据面调用已实测返回真实蜂群结果。

## 1. 为什么需要 AgentCore

黑客松的 Technical Implementation 会看重 agent 是否真正部署到 AWS Bedrock AgentCore Runtime，而不是只停留在本地脚本。AgentCore 提供：

- `POST /invocations` 和 `GET /ping` 标准运行时接口。
- 托管运行、鉴权、指标、追踪和会话管理。
- 与 Strands Agents SDK 的一等集成。

## 2. 本仓库已准备的内容

- `agentcore/main.py`：`BedrockAgentCoreApp` 入口，包装 `build_strands_agent()`。
- 默认 local 模式：`POST /invocations` 发 `{}` 直接跑蜂群。
- 可选 Strands 模式：`{"mode":"agent","prompt":"..."}`，默认用离线 MockModel。
- `flylab/strands_agent.py`：暴露 `get_user_context`、`detect_plateau`、`simulate_candidate`、`evolve_champion`、`surface_decision`、`record_feedback` 六个 Strands 工具。
- `requirements-strands.txt`：`strands-agents>=1.55`。
- `requirements-agentcore.txt`：`bedrock-agentcore>=1.23`。
- `Dockerfile`：linux/arm64 容器镜像。
- `scripts/deploy_agentcore.py`：ECR 构建/推送 + `create_agent_runtime`。

已本地验证：

```text
import agentcore
agentcore.app.handlers -> {'main'}
routes -> ['/invocations', '/ping', '/business-flow', '/ws']
```

本地 HTTP 烟测（无 AWS 凭据）：

```text
GET  /ping -> 200 {"status":"Healthy", ...}
POST /invocations {} -> 200 {"mode":"local","champion":{...},...}
```

默认请求不需要模型和 AWS。只有显式发送
`{"mode":"agent","prompt":"..."}` 才会走 Strands 模型驱动路径。
真实 CSV 业务流使用 `POST /business-flow`，本地也不依赖 AWS。

前端 `web/` 可部署到 Vercel；后端已开启 CORS，浏览器可以直接调用公网或本地后端地址。

## 3. 前置条件

- Python 3.10+
- AWS 账号与可用凭据（IAM / SSO / 环境变量）
- Bedrock 模型访问权限（默认 Bedrock provider）
- 可选：Docker、Finch 或 Podman（本地容器测试 / 高级部署）
- Node.js（使用官方 AgentCore CLI 时）

## 4. 方法 A：官方 AgentCore CLI（推荐快速原型）

官方文档建议用 CLI 创建、开发、部署 Strands agent。以你实际安装的 CLI 版本为准，核心流程通常是：

1. 安装官方 CLI（当前官方页以 Node 包 `@aws/agentcore` 为准；如 CLI 发布渠道变化，以 `strandsagents.com/docs/user-guide/deploy` 为准）。
2. 创建项目，选择框架为 **Strands**、语言为 **Python**。
3. 把本仓库的 `flylab/`、`agentcore/`、`data/mb_summary.json` 放进项目。
4. 将 `agentcore/main.py` 作为入口点。
5. 本地运行并测试 `/ping` 与 `/invocations`。
6. 执行 `agentcore deploy` 部署到 AWS。

也可以直接使用本仓库脚本（推荐，已实测跑通）：

```bash
export AWS_PROFILE=flyweight-agentcore
export AGENTCORE_ROLE_ARN=arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role
export AWS_REGION=us-east-1
.venv/bin/python scripts/deploy_agentcore.py
```

首次部署前需要先创建运行时执行角色：

```bash
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_agentcore_role.py
```

角色信任 `bedrock-agentcore.amazonaws.com`，内联策略包含 ECR 拉取、CloudWatch Logs、X-Ray、CloudWatch Metrics、Bedrock 模型调用与 AgentCore memory/identity 的最小权限。

脚本会自动从 AWS STS 推导账号 ID，从当前 boto3 session 推导区域；也可以显式设置 `AWS_REGION` 和 `AWS_ACCOUNT_ID`。
如果本机没有 `docker buildx`，脚本会回退到 `docker build --platform linux/arm64`。

## 4a. 已部署的真实 Runtime

当前生产运行时：

- Runtime ARN：`arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2`
- Runtime ID：`flyweight_lab-k3JItG63s2`
- 状态：`READY`
- 镜像：`032529260721.dkr.ecr.us-east-1.amazonaws.com/fly-weight-lab-agent:latest`
- 协议：`HTTP`
- 网络：`PUBLIC`
- 执行角色：`arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role`

已通过 Bedrock AgentCore 数据面实测：

```text
POST /invocations (payload {})
-> 200 {"mode":"local","champion":{...},"fitness":...,"adherence":...,"safety":{...}}
```

说明容器内的 `/invocations`、`/ping` 入口和真实蜂群计算都在云端托管运行时中工作，而不是本地 mock。

> 浏览器直连已通过 Vercel Serverless 代理打通：`web/api/invocations.js` 把浏览器的 `/api/invocations` 转发到 `invoke_agent_runtime`，`web/api/ping.js` 用控制面 `GetAgentRuntime` 做健康检查。前端默认后端地址为 `/api`，线上演示无需本地后端。

线上演示：https://fly-weight-lab-demo.vercel.app

代理使用 Vercel ↔ AWS OIDC 联合身份，不再使用长期 access key。浏览器函数通过 `@vercel/oidc-aws-credentials-provider` 换取短期 `sts:AssumeRoleWithWebIdentity` 凭据。

需要的 Vercel Production 环境变量（值已写入 Vercel，不在仓库中）：

- `AWS_ROLE_ARN=arn:aws:iam::032529260721:role/flyweight-vercel-oidc-role`
- `AWS_REGION=us-east-1`
- `AGENTCORE_RUNTIME_ARN`
- `AGENTCORE_RUNTIME_ID`

OIDC 侧由 [scripts/setup_vercel_oidc_role.py](../scripts/setup_vercel_oidc_role.py) 创建：

- IAM OIDC provider：`oidc.vercel.com/rectinajhs-projects`
- Audience：`https://vercel.com/rectinajhs-projects`
- Trust 限定：`owner:rectinajhs-projects:project:web:environment:production`
- 权限仅 `bedrock-agentcore:InvokeAgentRuntime` 和 `bedrock-agentcore:GetAgentRuntime`，资源限定到当前 runtime ARN 及其 `runtime-endpoint/*` 子资源。

## 5. 方法 B：手动部署到 ECR + CreateAgentRuntime

AgentCore Runtime 要求：

- 平台：`linux/arm64`
- 端口：`8080`
- 必需接口：`POST /invocations`、`GET /ping`
- 镜像推送到 ECR

`BedrockAgentCoreApp` 已经自动提供两个接口。剩余步骤是打包、推送、创建 runtime，官方 Python 部署文档有完整示例。部署成功后用 Bedrock AgentCore 的调用接口发送：

```json
{
  "prompt": "Detect a plateau and surface the one decision for this user."
}
```

## 6. 鉴权与安全

- 使用最小权限 IAM role：只授予 `bedrock:InvokeModel` 和 AgentCore 所需权限。
- 不把 AWS 凭据写进代码或提交到仓库。
- 健康建议仍在应用层加安全下限和医疗边界，不等同于诊断或处方。
- 本地 `.env` 已被 `.gitignore` 忽略。

## 7. 本地验证入口（无需调用 AWS）

```bash
.venv/bin/python -c "import agentcore; print(agentcore.app.handlers)"
```

真正调用模型会触发 Bedrock 请求，因此需要先配置凭据与模型访问权限。
