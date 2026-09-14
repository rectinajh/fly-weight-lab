const backendInput = document.getElementById("backend");
const runLocal = document.getElementById("runLocal");
const runAgent = document.getElementById("runAgent");
const runBusiness = document.getElementById("runBusiness");
const champion = document.getElementById("champion");
const decision = document.getElementById("decision");
const business = document.getElementById("business");
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

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }
  row.push(cell);
  if (row.some((value) => value.trim() !== "")) rows.push(row);
  return rows;
}

function rowsToObjects(rows) {
  if (rows.length < 2) return [];
  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((row) =>
    Object.fromEntries(headers.map((h, i) => [h, (row[i] || "").trim()]))
  );
}

function normalizeWeightRows(rows) {
  return rows
    .filter((row) => row.date && row.weight_kg)
    .map((row) => ({
      date: row.date,
      weight_kg: parseFloat(row.weight_kg),
      adherence: row.adherence ? parseFloat(row.adherence) : undefined,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function normalizeActivityRows(rows) {
  return rows
    .filter((row) => row.date)
    .map((row) => ({
      date: row.date,
      total_steps: parseInt(row.total_steps || "0", 10),
      active_minutes: parseInt(row.active_minutes || "0", 10),
      calories: parseInt(row.calories || "0", 10),
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

async function readFile(file) {
  if (!file) return [];
  const text = await file.text();
  return rowsToObjects(parseCsv(text));
}

runBusiness.addEventListener("click", async () => {
  try {
    const weightFile = document.getElementById("weightFile").files[0];
    const activityFile = document.getElementById("activityFile").files[0];
    if (!weightFile) throw new Error("Choose a real Fitbit weight CSV first.");

    const weightRows = await readFile(weightFile);
    const activityRows = await readFile(activityFile);
    const weight_records = normalizeWeightRows(weightRows);
    const activity_records = normalizeActivityRows(activityRows);
    if (!weight_records.length) {
      throw new Error("No date/weight_kg rows found in the uploaded CSV.");
    }

    const payload = {
      mode: "business_flow",
      user_id: "uploaded_user",
      weight_records,
      activity_records,
      population_size: 250,
      generations: 25,
      seed: 7,
    };
    const response = await fetch(`${baseUrl()}/business-flow`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`HTTP ${response.status}: ${text}`);
    }
    const data = await response.json();
    business.textContent = JSON.stringify(data, null, 2);
    champion.textContent = "Business flow used the uploaded real CSV.";
    decision.textContent = "Background agent surfaced only the real decisions.";
  } catch (err) {
    errorBox.textContent = err.message;
  }
});

backendInput.addEventListener("change", checkPing);
checkPing();
