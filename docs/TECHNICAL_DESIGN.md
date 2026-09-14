# 技术方案 — Fly Weight-Lab（果蝇减脂实验室）

> 版本：v0.1 · 面向：六周黑客松交付 · 技术栈：Strands Agents SDK + AgentCore + Python

## 1. 架构总览

```
用户日志(体重/饮食/睡眠/情绪/坚持度)
        │
        ▼
┌─────────────────────┐
│  数据接入层          │  归一化、去噪、基线
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  行为数字孪生模型     │  个人化: 坚持度/体重响应/暴食风险
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  果蝇蜂群引擎         │  遗传算法: 生成→试错→繁殖→收敛
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  决策面(Agent)       │  后台重跑 + 只在真决策时冒出来
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  进化看板            │  红叉/绿勾 + 家谱可视化
└─────────────────────┘
```

## 2. 核心组件

### 2.1 数据接入层

- 输入：体重（每日/滚动）、饮食（可粗略到餐次/类别）、睡眠时长、情绪/精力、坚持度标记（是否记录、是否按方案执行）、可选生理周期与用药。
- 来源：手动、Apple Health / Fitbit 导出、食物记录 API。
- 职责：清洗、对齐时间轴、去异常值（单日体重暴涨先按水肿处理）、产出可训练特征。

### 2.2 行为数字孪生（Behavioral Twin）

**定位：不是代谢模拟器，是个人化行为反应模型。**

- 输入：历史日志特征 + 一套候选方案。
- 输出三个预测：
  - `predict_adherence(protocol)`：这个人能坚持这套方案的概率。
  - `simulate_weight(protocol, horizon)`：未来 12 周体重轨迹。
  - `predict_binge_risk(protocol)`：这套方案诱发暴食的概率。
- 实现：先用**个人历史校准的规则 + 简单回归**起步（六周内可交付），后续可换梯度提升/轻量贝叶斯模型。每周用新日志重拟合，孪生越来越像本人。
- 诚实边界：我们拟合的是「这个人会不会做、做了会怎样」，不是「他的线粒体怎么工作」。
- **真实连接组 grounding**：暴食风险里「限制→反弹」的耦合系数来自 Janelia MaleCNS 真实蘑菇体连接组——PAM（奖赏）→MBON 是 PPL（惩罚）→MBON 的约 2.56 倍。用它替换手调常数，作为习惯/奖赏动态的结构先验（不是声称人脑=果蝇脑）。

### 2.3 果蝇蜂群引擎（Genetic Swarm）

每只果蝇 = 一个候选方案。用遗传算法在方案空间里搜索「这个人最优解」。

### 2.4 决策面（Agent Orchestrator）

- 用 Strands Agents SDK 编排后台自治流程。
- 用 AgentCore 部署与调度。
- 触发打扰的三类事件：新冠军明显更优 / 风险越线（平台期、坚持度下滑、暴食预警）/ 每周例行更新。
- 每次只输出一个决策：一句话 + 证据 + 一个本周动作。

已实现核心逻辑（无需外部 API 也能跑通）：

- `flylab/agent_loop.py` 的 `WeightLossAgent` 持有当前方案、体重历史和连接组参数。
- 每周 `ingest(weight_kg)` 摄入体重，`tick(week)` 重跑蜂群。
- 通过「冠军方案指纹」判断是否真的变化；通过短窗口体重差检测平台期。
- 新检测到平台期时给行为孪生的 `metabolic_adaptation` 加 0.05，迫使下一轮搜索换新杠杆，避免重复推同一条建议。
- 只有 `new_plateau or changed` 且达到重推间隔时才调用决策面，其余周安静。
- `state_dict()` / `save_state()` / `load_state()` 把当前方案、体重历史、平台期记忆和最后重推周保存为 JSON，重启后可无缝继续。

可选 Strands 桥接：

- `flylab/strands_agent.py` 的 `build_strands_agent()` 在安装 `strands-agents` 后可用。
- 暴露 `run_swarm` 与 `is_plateau` 两个工具，让模型驱动 agent 调用本项目的蜂群与平台期检测。
- 默认 Bedrock provider 需要 AWS 凭据与模型访问权限；本地核心演示不依赖它。
- 已验证：`pip install -r requirements-strands.txt` 后，`build_strands_agent()` 返回 `strands.Agent` 实例，构造阶段无需调用 AWS。

AgentCore 部署入口：

- `agentcore/main.py` 使用 `BedrockAgentCoreApp` 包装 Strands agent。
- `@app.entrypoint` 接收 `{"prompt": "..."}`，调用 `agent.invoke_async(prompt)` 并返回可序列化结果。
- 额外支持 `{"mode":"local"}`，直接跑 `Swarm`，供无 Bedrock 凭据的部署烟测。
- AgentCore Runtime 自动提供 `POST /invocations` 与 `GET /ping`；本地已确认 routes 与 handler 注册成功。
- `Dockerfile` 构建 linux/arm64 镜像；`scripts/deploy_agentcore.py` 完成 ECR 推送与 `create_agent_runtime`。
- 完整部署步骤见 `docs/AGENTCORE_DEPLOYMENT.md`。

### 2.5 进化看板

- 展示蜂群代数、种群分布、红叉/绿勾、冠军方案家谱。
- 是 demo 的核心视觉资产。

## 3. 果蝇基因型（Genotype）

一只果蝇编码以下基因（可裁剪）：

| 基因 | 含义 | 示例范围 |
|---|---|---|
| calorie_target | 每日热量目标 | 维持热量 - 200~500（设安全下限） |
| protein_pct | 蛋白占比 | 25% ~ 45% |
| carb_pct | 碳水占比 | 20% ~ 50% |
| fat_pct | 脂肪占比 | 由剩余推导 |
| meal_window | 进食窗口（小时） | 8 = 16:8；12 = 不断食 |
| meal_count | 每日餐次 | 2 ~ 5 |
| late_night_rule | 是否允许深夜加餐 | bool（某些人保留可防暴食） |
| habit_trigger | 锚点小习惯 | 枚举（早餐先吃蛋白 / 午饭后走 10 分钟等） |
| workout_freq | 每周训练次数 | 0 ~ 6 |
| workout_type | 训练类型 | 有氧/抗阻/混合 |
| sleep_target | 睡眠目标 | 7 ~ 9 小时 |
| refeed_schedule | 高热量日节奏 | none / weekly / biweekly |
| step_target | 每日步数（NEAT） | 4000 ~ 12000 |

## 4. 适应度函数（Fitness）

对每只果蝇 `p`，用孪生模型评估：

```
adherence  = twin.predict_adherence(p)
weight_curve = twin.simulate_weight(p, 12周)
total_loss = 起始体重 - 期末体重
plateau_risk = 检测轨迹平台期
binge_risk = twin.predict_binge_risk(p)
dropout_risk = 1 - adherence

fitness = w1*total_loss + w2*adherence
        - w3*plateau_risk - w4*binge_risk - w5*dropout_risk
```

要点：**适应度优先「能不能坚持」，其次才是「减多少」。** 反完美主义写进函数里。

## 5. 遗传算法细节

- 种群规模：`N = 500 ~ 2000`。
- 初始化：随机 + 常识种子（普通热量缺口方案等）。
- 选择：锦标赛选择（`k=3~5`）。
- 交叉：基因向量均匀交叉。
- 变异：每个基因以概率扰动（连续基因高斯扰动，离散基因翻转/重采样）。
- 精英保留：每代保留 top-K。
- 停止条件：适应度收敛或达到代数上限。
- 安全约束：热量目标不得低于安全下限；不产出危险节食方案。

## 6. 数据流

1. 新日志进入 → 触发孪生重拟合（每日增量）。
2. 每周或越线时 → 触发完整蜂群进化。
3. 进化收敛 → 冠军方案交给决策面。
4. 决策面判断是否值得打扰 → 推一条决策给用户。
5. 用户反馈（坚持/放弃/记录）回流，成为下一代果蝇的适应度证据。

## 7. 技术栈

- **Agent 编排**：Strands Agents SDK。
- **部署/调度**：AgentCore（同时强化 Technical Implementation 评分）。
- **算法/模型**：Python 3.x + numpy/pandas + scikit-learn。
- **存储**：用户日志、方案史、蜂群状态 → DynamoDB 或 Postgres。
- **自然语言**：Strands/Bedrock LLM 生成习惯建议与解释文案（可选）。
- **前端**：React/Next.js 进化看板。

## 8. MVP 切片：平台期破解器

先交付最窄、最能 demo 的原子：

1. 一只果蝇 = 一个未来情景，跑 1 万次 Monte Carlo。
2. 红叉（断粮/爆掉）与绿勾（存活）可视化。
3. 只在检测到平台期或坚持度下滑时，推一个破局杠杆。

这一片能独立成片、独立演示，后续再扩成完整实验室。

## 8.1 已落地代码清单

| 模块 | 职责 |
|---|---|
| `flylab/genotype.py` | 一只果蝇 = 一套减脂方案基因型 |
| `flylab/twin.py` | 行为数字孪生：坚持度、体重轨迹、暴食风险 |
| `flylab/fitness.py` | 适应度函数，坚持度权重最高 |
| `flylab/evolution.py` | 锦标赛选择、交叉、变异、精英保留 |
| `flylab/plateau.py` | 平台期检测 |
| `flylab/connectome.py` | Janelia MaleCNS 蘑菇体参数加载与连接组构建 |
| `flylab/agent.py` | 冠军方案翻译成一个决策 + 一句理由 |
| `flylab/agent_loop.py` | 后台 agent 循环 + 状态保存/恢复（JSON 持久化） |
| `flylab/strands_agent.py` | 可选 Strands Agents SDK 桥接 |
| `agentcore/main.py` | Bedrock AgentCore Runtime 部署入口 |
| `scripts/make_dashboard.py` | 用真实运行结果生成 2880x1600 进化看板 |
| `scripts/deploy_agentcore.py` | ECR 构建推送 + AgentCore runtime 创建 |
| `examples/demo_agent.py` | 12 周后台 agent 演示 |
| `tests/test_evolution.py` | 自动验证：基因型、蜂群、连接组、后台循环安静性 |

## 9. 六周落地计划

- 第 1 周：数据接入 + 平台期破解器 MVP + 进化可视化。
- 第 2–3 周：Strands Agents SDK 编排 + AgentCore 部署 + 后台定时重跑。
- 第 4–5 周：完整遗传进化（繁殖/交叉/变异/收敛）+ 行为孪生重拟合闭环。
- 第 6 周：demo 视频、README、架构图、提交材料。

## 10. 风险与缓解

- **孪生可信度**：坚持「行为孪生」的诚实表述；用真实数据拟合，不编代谢。
- **数据稀疏**：冷启动用常识种子 + 快速校准；2 周基线后开始真正个性化。
- **健康安全**：安全热量下限、危险方案硬过滤、医疗边界提示。
- **范围失控**：MVP 钉死「平台期破解器」，再按切片外扩。
