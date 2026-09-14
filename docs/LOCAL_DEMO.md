# Local Demo — Fly Weight-Lab

The live demo is hosted and talks to a real Bedrock AgentCore Runtime. This page
is for running the same thing locally, either as a Python backend or as the
Vercel frontend.

## Public demo

https://fly-weight-lab-demo.vercel.app

Two real Fitbit users are preloaded inside the runtime, so the demo needs no CSV
upload and no local backend.

## 1. Start the backend

```bash
.venv/bin/python -m uvicorn agentcore.main:app --host 0.0.0.0 --port 8080
```

The backend defaults to local mode and needs no model, AWS credentials, or
external API.

## 2. Exercise the endpoints

```bash
curl http://127.0.0.1:8080/ping
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{}'
```

`{}` returns the evolved champion protocol, fitness, adherence, binge risk, the
connectome parameters, and a compact evolution history.

Run the real-data product loop without any cloud dependency:

```bash
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067
```

The same flow is reachable over HTTP in three ways:

| Route | Payload | Purpose |
|---|---|---|
| `POST /invocations` | `{}` | quick swarm run |
| `POST /invocations` | `{"mode":"demo","user_id":"6962181067"}` | real-data loop using the preloaded users |
| `POST /business-flow` | `{"weight_records":[...],"activity_records":[...]}` | direct container route for uploaded data |

The business flow runs ingest → calibrate the twin → weekly background ticks →
exactly one surfaced decision → record the real next-week outcome → persist
feedback. It never falls back to mock or sample rows.

## 3. Open the frontend locally

Serve the `web/` directory as a static site and open it in a browser.

```bash
python -m http.server 5173 --directory web
```

The page calls `/api/ping` and `/api/invocations` on the same origin. To point it
at a local Python backend instead of the Vercel proxy, edit `baseUrl()` in
`web/app.js` to return `http://localhost:8080`.

The frontend has three buttons:

- **Launch background agent** — runs the full real-data flow for the selected
  user and renders the dashboard.
- **Swarm evolution only** — runs the swarm directly for a fast look at the
  convergence visuals.
- **Import my own Fitbit export** — optional advanced path for bringing your own
  normalized CSV.

## 4. Deploying the frontend

The Vercel project builds `web/` as the project root. `web/vercel.json` defines
the static output and the serverless functions.

```json
{
  "buildCommand": "",
  "outputDirectory": ".",
  "functions": { "api/*.js": { "maxDuration": 60 } }
}
```

The functions need four production environment variables to reach AWS:
`AWS_ROLE_ARN`, `AWS_REGION`, `AGENTCORE_RUNTIME_ARN`, `AGENTCORE_RUNTIME_ID`.

Authentication is Vercel ↔ AWS OIDC federation, so there are no long-lived AWS
access keys in Vercel. See
[AGENTCORE_DEPLOYMENT.md](./AGENTCORE_DEPLOYMENT.md) for the full setup,
including the GitHub-triggered deploy configuration.

## 5. Using a real local model

With Ollama installed:

```bash
export STRANDS_MODEL_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3.2
```

Restart the backend and `{"mode":"agent","prompt":"..."}` runs a real model
through the same tools. Without these variables the live demo uses the
deterministic FlowModel and still completes the full tool-call loop.

## 6. Regenerating the real data

```bash
.venv/bin/python scripts/ingest_fitbit_data.py
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067
```

Normalized inputs land in `data/real_users/`; run reports and persisted agent
state land in `runs/`.
