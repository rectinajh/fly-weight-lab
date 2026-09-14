# Demo 分镜 — Fly Weight-Lab

> 目标：5 分钟黑客松演示视频 / live demo 脚本。核心叙事只有一句：**你的身体只跑 1 个冠军方案，果蝇替你跑 1 万个失败实验。**

## 演示原则

1. 每个镜头必须服务于同一句话：后台安静，只在真决策时冒出来。
2. 强调「真实连接组」不是贴图，是承重墙：它改变了暴食风险，也改变了最终建议。
3. 不用「代谢模拟」的说法，统一叫「行为数字孪生」。
4. 镜头之间用真实命令产出结果，不让观众以为只是 PPT 概念图。

## 镜头 1：开场钩子（15 秒）

**画面**：一张只有标题和一句话的卡片。

> 减脂最大的问题不是你不知道少吃多动，而是你只有一副身体，没法同时跑一万种方案。

**口播**：

「MyFitnessPal 记录你吃了什么，Noom 提醒你坚持。但真正决定成败的问题是：哪套方案，这个具体的人能撑住，身体又会怎么反应？」

**转场**：屏幕上飞入一群果蝇。

## 镜头 2：果蝇蜂群进化（60 秒）

**运行**：`python examples/demo_plateau_breaker.py`

**画面**：

- 展示 `Evolution history` 表格和红/绿种群条：红叉死亡，绿勾存活。
- 展示一个激进方案（1500 kcal + 8 小时窗口 + 无深夜加餐）如何被淘汰。
- 展示冠军方案：热量上调、保留深夜加餐或 refeed。

**口播**：

「每只果蝇是一套候选方案。我们用你的行为孪生跑几千次模拟未来，弱方案变红死掉，强方案繁殖、交叉、变异，最后只活下一个冠军。注意：同样是减脂，两个用户会进化出完全相反的方案。」

**关键镜头**：`TWO USERS, SAME GOAL, OPPOSITE PLANS` 输出并列显示。

## 镜头 3：真实果蝇连接组（60 秒）

**运行**：`python examples/demo_connectome.py`

**画面**：

```
REAL MUSHROOM BODY — Janelia MaleCNS v1.0
Kenyon cells (context):            4064
Dopaminergic neurons (reward):      340
MBONs (decision):                    97
KC -> MBON convergence:             631 KCs per MBON
Reward (PAM) : Punishment (PPL):    2.56 : 1
```

然后并列显示：

```
Aggressive protocol binge risk, un-grounded: 0.74
Aggressive protocol binge risk, grounded:     0.90
```

**口播**：

「这不是装饰。我们接了 Janelia 的真实雄性果蝇蘑菇体连接组：4064 个 Kenyon cell、340 个奖赏/惩罚神经元、97 个决策神经元。真实线路里，奖赏对惩罚的比例是 2.56 比 1。节食靠的是惩罚和限制，所以真实线路预测：限制会被更强烈的渴望压力反扑。这就是为什么激进节食的暴食风险从 0.74 升到 0.90。」

**关键结论**：接连接组后，建议从「继续压热量」变成「上调热量 + 保留深夜加餐」。

## 镜头 4：后台 agent 安静运行（90 秒）

**运行**：`python examples/demo_agent.py`

**画面**：12 周时间轴。

```
week  1: SURFACED -> 把每日热量目标从 1500 上调到 1648 kcal；允许一份固定的睡前加餐
week  2: (quiet)
week  3: (quiet)
week  4: (quiet)
week  5: (quiet)
week  6: SURFACED -> 把每日热量目标从 1648 上调到 1691 kcal；先把睡眠补到 8.8 小时
week  7: (quiet)
week  8: (quiet)
week  9: (quiet)
week 10: SURFACED -> 锁定这套方案：...
week 11: (quiet)
week 12: (quiet)
```

**口播**：

「这是我们要给评委看的核心：12 周里 agent 只冒出来 3 次，其余 9 周完全安静。它每周都在后台重跑蜂群，但不打扰你。只有平台期新出现，或冠军方案真的变了，它才给一个决策。这就是 Agents for Humans 的定义：autonomous，但只在有 real decision 时 surface。」

**补一句**：状态已持久化，重启后不会丢当前方案和体重历史。

## 镜头 5：技术可信度 + 边界（45 秒）

**画面**：三行卡片。

- Behavioral twin，不是 metabolic simulator。
- Real Drosophila connectome as structural prior。
- Safety floor + 医疗边界：只提示，不诊断，不处方。

**口播**：

「我们刻意不假装模拟人体代谢，因为那不诚实也不必要。我们拟合的是：这个人会不会做、做了会怎样。真实连接组只作为习惯和奖赏动态的结构先验。安全上，热量有下限，危险方案硬过滤，慢性病用户只得到『去问医生』。」

## 镜头 6：一句话收尾（15 秒）

> Your body runs one experiment. The flies ran ten thousand.

**口播**：

「Fly Weight-Lab：让一万只赛博果蝇替你失败，你只跑那一个被证明能赢的方案。」

## Demo 检查清单

- [ ] 三个命令都能从仓库根目录直接运行，无外部 API 依赖。
- [ ] 测试通过：`python tests/test_evolution.py -v`
- [ ] README 的 Real Connectome Grounding 数据与 `examples/demo_connectome.py` 一致。
- [ ] 视频里任何「代谢」字样都替换为「行为响应」。
- [ ] 提交页面放仓库链接、Demo 视频、PRD、技术方案、Demo 分镜。
