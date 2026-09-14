const { invokeRuntime } = require("./_runtime");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "method not allowed" });
  }

  let payload = {};
  if (req.body && typeof req.body === "object" && !Array.isArray(req.body)) {
    payload = req.body;
  }

  try {
    const { statusCode, body } = await invokeRuntime(payload);
    return res.status(statusCode).json(body);
  } catch (error) {
    return res.status(error.statusCode || 502).json({ error: error.message });
  }
};
