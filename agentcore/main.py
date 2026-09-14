"""AgentCore Runtime entrypoint for Fly Weight-Lab.

Wraps the Strands agent from ``flylab.strands_agent`` in a Bedrock AgentCore
app. The runtime exposes ``POST /invocations`` and ``GET /ping`` automatically.

Expected invocation payload:
    {"prompt": "Detect a plateau and surface the one decision for this user."}
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp

from flylab.strands_agent import build_strands_agent

app = BedrockAgentCoreApp()
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_strands_agent()
    return _agent


@app.entrypoint
async def main(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the fruit-fly agent and return a serializable result."""
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "payload.prompt must be a non-empty string"}

    result = await _get_agent().invoke_async(prompt)
    if hasattr(result, "to_dict"):
        return {"result": result.to_dict()}
    return {"result": str(result)}
