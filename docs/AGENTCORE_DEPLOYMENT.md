# AgentCore 部署说明 — Fly Weight-Lab

> 状态：入口代码已验证可导入；真实云端部署需要 AWS 账号、Bedrock 模型访问权限和 AgentCore 项目。

## 1. 为什么需要 AgentCore

黑客松的 Technical Implementation 会看重 agent 是否真正部署到 AWS Bedrock AgentCore Runtime，而不是只停留在本地脚本。AgentCore 提供：

- `POST /invocations` 和 `GET /ping` 标准运行时接口。
- 托管运行、鉴权、指标、追踪和会话管理。
- 与 Strands Agents SDK 的一等集成。

## 2. 本仓库已准备的内容

- `agentcore/main.py`：`BedrockAgentCoreApp` 入口，包装 `build_strands_agent()`。
- `flylab/strands_agent.py`：暴露 `run_swarm` 与 `is_plateau` 两个 Strands 工具。
- `requirements-strands.txt`：`strands-agents>=1.55`。
- `requirements-agentcore.txt`：`bedrock-agentcore>=1.23`。

已本地验证：

```text
import agentcore
agentcore.app.handlers -> {'main'}
routes -> ['/invocations', '/ping', '/ws']
```

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
