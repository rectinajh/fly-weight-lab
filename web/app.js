const backendInput = document.getElementById("backend");
const runLocal = document.getElementById("runLocal");
const runAgent = document.getElementById("runAgent");
const champion = document.getElementById("champion");
const decision = document.getElementById("decision");
const pingDot = document.getElementById("pingDot");
const pingText = document.getElementById("pingText");
const errorBox = document.getElementById("error");

function baseUrl() {
  return backendInput.value.replace(/\/$/, "");
}

async function checkPing() {
  try {
    const response = await fetch(`${baseUrl()}/ping`);
    if (!response.ok) throw new Error("not healthy");
    const data = await response.json();
    pingDot.className = "dot ok";
    pingText.textContent = `Healthy · ${data.status}`;
    errorBox.textContent = "";
  } catch (err) {
    pingDot.className = "dot bad";
    pingText.textContent = "Backend unreachable";
    errorBox.textContent = "Start the backend or enter a public URL.";
  }
}

async function post(payload) {
  errorBox.textContent = "";
  const response = await fetch(`${baseUrl()}/invocations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

runLocal.addEventListener("click", async () => {
  try {
    const data = await post({});
    champion.textContent = JSON.stringify(data, null, 2);
    decision.textContent = "Local mode ran the swarm without a model.";
  } catch (err) {
    errorBox.textContent = err.message;
  }
});

runAgent.addEventListener("click", async () => {
  try {
    const data = await post({
      mode: "agent",
      prompt: "Detect a plateau and surface the one decision for this user.",
    });
    decision.textContent = JSON.stringify(data, null, 2);
    champion.textContent = "Strands agent completed its tool-call loop.";
  } catch (err) {
    errorBox.textContent = err.message;
  }
});

backendInput.addEventListener("change", checkPing);
checkPing();
