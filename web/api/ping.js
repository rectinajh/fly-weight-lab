const {
  BedrockAgentCoreControlClient,
  GetAgentRuntimeCommand,
} = require("@aws-sdk/client-bedrock-agentcore-control");

const REGION = process.env.AWS_REGION || "us-east-1";
const RUNTIME_ID = process.env.AGENTCORE_RUNTIME_ID;

module.exports = async function handler(_req, res) {
  if (!RUNTIME_ID) {
    return res.status(500).json({ status: "Unconfigured" });
  }

  try {
    const client = new BedrockAgentCoreControlClient({ region: REGION });
    const output = await client.send(
      new GetAgentRuntimeCommand({ agentRuntimeId: RUNTIME_ID }),
    );
    const healthy = output.status === "READY";
    return res.status(healthy ? 200 : 503).json({
      status: healthy ? "Healthy" : output.status,
    });
  } catch (error) {
    return res.status(502).json({ status: "Unreachable", error: error.message });
  }
};
