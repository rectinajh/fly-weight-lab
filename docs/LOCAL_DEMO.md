# Local Demo — Fly Weight-Lab

## 1. 启动后端

```bash
.venv/bin/python -m uvicorn agentcore.main:app --host 0.0.0.0 --port 8080
```

后端默认 local 模式，不需要模型、AWS 凭据或外部 API。

## 2. 验证接口

```bash
curl http://127.0.0.1:8080/ping
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{}'
```

默认 `{}` 会返回：

- 进化出的冠军方案
- fitness
- 坚持度
- 暴食风险
- 安全报告

真实业务流接口：

```bash
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067
```

更细的 HTTP 接口是 `POST /business-flow`，请求体包含真实 CSV 解析后的
`weight_records` 和可选的 `activity_records`；前端上传 CSV 时走的就是这条路径。
该接口会跑完上传 → 校准 → 周循环 → 只冒出一个决策 → 记录下一周真实体重结果
→ 持久化反馈的完整流程，不依赖 mock/sample 日志。

## 3. 打开前端

直接在浏览器打开 `web/index.html`，后端地址填 `http://localhost:8080`。
前端支持上传真实 Fitbit `weightLogInfo` 规范化 CSV，可选再传 activity CSV，
然后点击 **Run real CSV flow**。

部署到 Vercel 时，使用 `web/` 目录作为项目根目录，`web/vercel.json` 已配置为静态站点。
浏览器访问的是公网后端地址，因此需要把本地后端通过 ngrok/cloudflared 暴露，或部署到任意 Python 托管平台。

当前公开前端：

[https://fly-weight-lab-demo.vercel.app](https://fly-weight-lab-demo.vercel.app)

## 4. 使用真实本地模型

如果本机装了 Ollama：

```bash
export STRANDS_MODEL_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3.2
```

然后重启后端，`{"mode":"agent","prompt":"..."}` 会走真实模型。

不设置这些变量时，Strands 使用确定性的 MockModel，仍然会完成完整 tool-call 循环。

## 5. 生成真实数据

```bash
.venv/bin/python scripts/ingest_fitbit_data.py
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067
```

生成的数据保存在 `data/real_users/`，运行报告和持久化状态保存在 `runs/`。
