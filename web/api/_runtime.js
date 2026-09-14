const {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand,
} = require("@aws-sdk/client-bedrock-agentcore");
const {
  awsCredentialsProvider,
} = require("@vercel/oidc-aws-credentials-provider");

const REGION = process.env.AWS_REGION || "us-east-1";
const RUNTIME_ARN = process.env.AGENTCORE_RUNTIME_ARN;

function httpError(message, statusCode = 502) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

async function readResponseBody(response) {
  if (typeof response === "string") return response;
  if (response instanceof Uint8Array) {
    return Buffer.from(response).toString("utf8");
  }
  if (response && typeof response.transformToString === "function") {
    return response.transformToString();
  }
  if (response && typeof response[Symbol.asyncIterator] === "function") {
    const chunks = [];
    for await (const chunk of response) {
      chunks.push(Buffer.from(chunk));
    }
    return Buffer.concat(chunks).toString("utf8");
  }
  return String(response || "");
}

async function invokeRuntime(payload) {
  if (!RUNTIME_ARN) {
    throw httpError("AGENTCORE_RUNTIME_ARN is not configured", 500);
  }
  if (!process.env.AWS_ROLE_ARN) {
    throw httpError("AWS_ROLE_ARN is not configured", 500);
  }

  const client = new BedrockAgentCoreClient({
    region: REGION,
    credentials: awsCredentialsProvider({
      roleArn: process.env.AWS_ROLE_ARN,
    }),
  });
  const output = await client.send(
    new InvokeAgentRuntimeCommand({
      agentRuntimeArn: RUNTIME_ARN,
      contentType: "application/json",
      accept: "application/json",
      payload: new TextEncoder().encode(JSON.stringify(payload)),
    }),
  );

  const statusCode = output.statusCode || 200;
  const text = await readResponseBody(output.response);
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }
  return { statusCode, body };
}

module.exports = { invokeRuntime, REGION, RUNTIME_ARN };
