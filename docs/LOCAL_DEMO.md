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

## 3. 打开前端

直接在浏览器打开 `web/index.html`，后端地址填 `http://localhost:8080`。

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
