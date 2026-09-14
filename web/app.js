const pingDot = document.getElementById("pingDot");
const pingText = document.getElementById("pingText");
const errorBox = document.getElementById("errorBox");
const loading = document.getElementById("loading");
const loadingText = document.getElementById("loadingText");
const dashboard = document.getElementById("dashboard");

const runDemo = document.getElementById("runDemo");
const runSwarm = document.getElementById("runSwarm");
const runUpload = document.getElementById("runUpload");
const userChips = Array.from(document.querySelectorAll(".user-chip"));
const weightFile = document.getElementById("weightFile");
const activityFile = document.getElementById("activityFile");

const state = {
  user: "6962181067",
  demo: null,
  compare: null,
  local: null,
};

let radarRaf = 0;

function baseUrl() {
  return "/api";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

async function checkPing() {
  try {
    const response = await fetch(`${baseUrl()}/ping`);
    if (!response.ok) throw new Error("not healthy");
    const data = await response.json();
    pingDot.className = "dot ok";
    pingText.textContent = `Live AgentCore · ${data.status || "Healthy"}`;
    clearError();
  } catch {
    pingDot.className = "dot bad";
    pingText.textContent = "AgentCore unreachable";
  }
}

async function post(payload) {
  const response = await fetch(`${baseUrl()}/invocations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status} · ${text}`);
  }
  return response.json();
}

function setLoading(text) {
  loadingText.textContent = text;
  loading.classList.remove("hidden");
  dashboard.classList.add("hidden");
}

function stopLoading() {
  loading.classList.add("hidden");
  dashboard.classList.remove("hidden");
}

function sampleFarm(farm, target = 110) {
  if (!farm || !farm.length) return "";
  const bucket = Math.max(1, Math.round(farm.length / target));
  let out = "";
  for (let i = 0; i < farm.length; i += bucket) {
    let ones = 0;
    let n = 0;
    for (let j = i; j < Math.min(i + bucket, farm.length); j += 1) {
      ones += farm[j] === "1" ? 1 : 0;
      n += 1;
    }
    out += ones >= n / 2 ? "1" : "0";
  }
  return out;
}

function lineChart(points, opts = {}) {
  const width = opts.width || 680;
  const height = opts.height || 220;
  const pad = { l: 44, r: 16, t: 18, b: 30 };
  const series = opts.series || [];
  const xFor = (i) => pad.l + (i / Math.max(1, points.length - 1)) * (width - pad.l - pad.r);
  const yFor = (v, min, max) => pad.t + (1 - (v - min) / (max - min || 1)) * (height - pad.t - pad.b);

  const values = [];
  for (const s of series) for (const p of points) values.push(p[s.key]);
  let min = opts.min ?? Math.min(...values);
  let max = opts.max ?? Math.max(...values);
  if (max - min < 0.001) { min -= 1; max += 1; }

  let grid = "";
  for (let i = 0; i <= 4; i += 1) {
    const v = min + ((max - min) * i) / 4;
    const y = yFor(v, min, max);
    grid += `<line x1="${pad.l}" y1="${y}" x2="${width - pad.r}" y2="${y}" stroke="rgba(77,144,200,0.14)" stroke-width="1"/>`;
    grid += `<text x="${pad.l - 8}" y="${y + 4}" text-anchor="end" fill="#4c637a" font-size="10">${v.toFixed(0)}</text>`;
  }

  let lines = "";
  for (const s of series) {
    const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${xFor(i).toFixed(1)},${yFor(p[s.key], min, max).toFixed(1)}`).join(" ");
    lines += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2.2}" opacity="${s.opacity ?? 1}"/>`;
  }

  let markers = "";
  if (opts.markers) {
    for (const m of opts.markers) {
      const i = m.index;
      if (i < 0 || i >= points.length) continue;
      markers += `<path d="M${xFor(i) - 5},${yFor(m.value, min, max) - 5} l10,10 M${xFor(i) + 5},${yFor(m.value, min, max) - 5} l-10,10" stroke="${m.color || "#ffd166"}" stroke-width="2.4" stroke-linecap="round"/>`;
    }
  }

  const xLabels = opts.xLabels || points.map((_, i) => i);
  let xText = `<text x="${pad.l}" y="${height - 8}" fill="#4c637a" font-size="10">${xLabels[0] ?? 0}</text>`;
  xText += `<text x="${width - pad.r}" y="${height - 8}" text-anchor="end" fill="#4c637a" font-size="10">${xLabels[xLabels.length - 1] ?? points.length - 1}</text>`;

  return `<svg class="svg-chart" viewBox="0 0 ${width} ${height}" role="img">${grid}${lines}${markers}${xText}</svg>`;
}

function donut(protein, carb, fat) {
  const total = protein + carb + fat || 1;
  const r = 42;
  const c = 2 * Math.PI * r;
  const segments = [
    { value: protein, color: "#4cc9f0", label: "Protein" },
    { value: carb, color: "#35d07f", label: "Carbs" },
    { value: fat, color: "#ffd166", label: "Fat" },
  ];
  let offset = 0;
  let circles = "";
  for (const seg of segments) {
    const len = (seg.value / total) * c;
    circles += `<circle cx="60" cy="60" r="${r}" fill="none" stroke="${seg.color}" stroke-width="15" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 60 60)"/>`;
    offset += len;
  }
  return `<svg viewBox="0 0 120 120" style="width:120px;height:120px" role="img">${circles}<text x="60" y="56" text-anchor="middle" fill="#eaf2fb" font-size="16" font-weight="700">${Math.round(protein * 100)}%</text><text x="60" y="72" text-anchor="middle" fill="#8aa0b8" font-size="10">Protein</text></svg>`;
}

function fmtPct(v) { return `${Math.round((v || 0) * 100)}%`; }

function updateConnectome(connectome) {
  if (!connectome) return;
  document.getElementById("statKenyon").textContent = connectome.n_kenyon ?? "4064";
  document.getElementById("statDan").textContent = connectome.n_dan ?? "340";
  document.getElementById("statMbon").textContent = connectome.n_mbon ?? "97";
  document.getElementById("statRatio").textContent = `${connectome.reward_punishment_ratio ?? "2.56"}:1`;
}

function initRadar(canvas, evolution) {
  cancelAnimationFrame(radarRaf);
  if (!canvas || !evolution?.generations?.length) return;

  const size = 240;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = `${size}px`;
  canvas.style.height = `${size}px`;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const cx = size / 2;
  const cy = size / 2;
  const R_outer = 104;
  const R_inner = 20;
  const gens = evolution.generations;
  const bests = gens.map((g) => g.best);
  const min = Math.min(...bests);
  const max = Math.max(...bests);
  const range = max - min || 1;
  const totalAngle = Math.PI * 3.1;

  const pts = gens.map((g, i) => {
    const ang = -Math.PI / 2 + (i / Math.max(1, gens.length - 1)) * totalAngle;
    const r = R_inner + (1 - (g.best - min) / range) * (R_outer - R_inner);
    return { x: cx + Math.cos(ang) * r, y: cy + Math.sin(ang) * r, t: i / Math.max(1, gens.length - 1) };
  });

  let sweep = 0;
  function draw() {
    ctx.clearRect(0, 0, size, size);

    for (let i = 1; i <= 4; i += 1) {
      const r = (R_outer / 4) * i;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(77,144,200,0.18)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.moveTo(cx - R_outer, cy);
    ctx.lineTo(cx + R_outer, cy);
    ctx.moveTo(cx, cy - R_outer);
    ctx.lineTo(cx, cy + R_outer);
    ctx.strokeStyle = "rgba(77,144,200,0.18)";
    ctx.stroke();

    if (pts.length > 1) {
      ctx.beginPath();
      pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
      ctx.strokeStyle = "rgba(76,201,240,0.45)";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    for (const p of pts) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(53, 208, 127, ${0.25 + 0.75 * p.t})`;
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(cx, cy, 6 + Math.sin(sweep * 0.35) * 2, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(53,208,127,0.9)";
    ctx.shadowColor = "rgba(53,208,127,0.85)";
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.shadowBlur = 0;

    const sx = cx + Math.cos(sweep) * R_outer;
    const sy = cy + Math.sin(sweep) * R_outer;
    const grad = ctx.createLinearGradient(cx, cy, sx, sy);
    grad.addColorStop(0, "rgba(53,208,127,0.95)");
    grad.addColorStop(1, "rgba(53,208,127,0)");
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(sx, sy);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 2;
    ctx.stroke();

    sweep += 0.035;
    radarRaf = requestAnimationFrame(draw);
  }
  draw();
}

function evolutionCard(evolution, title, subtitle) {
  const gens = evolution?.generations || [];
  if (!gens.length) return "";
  const points = gens.map((g) => ({ best: g.best, mean: g.mean }));
  const chart = lineChart(points, {
    width: 640,
    height: 220,
    series: [
      { key: "best", color: "#35d07f", width: 2.6 },
      { key: "mean", color: "#4cc9f0", width: 1.6, opacity: 0.85 },
    ],
    xLabels: gens.map((g) => g.generation),
  });

  const farmRows = gens
    .map((g) => {
      const cells = sampleFarm(g.farm, 110);
      const html = cells
        .split("")
        .map((c) => `<span class="farm-cell ${c === "1" ? "alive" : "dead"}"></span>`)
        .join("");
      return `<div class="farm-row"><span class="farm-label">G${g.generation}</span><div class="farm-cells">${html}</div></div>`;
    })
    .join("");

  return `
    <article class="card wide">
      <div class="card-head">
        <div><p class="kicker">Genetic swarm · convergence radar</p><h2>${title}</h2><p class="note">${subtitle}</p></div>
        <div class="legend"><span class="q">survives</span><span class="s">culled</span></div>
      </div>
      <div class="evo-grid">
        <div class="radar-wrap"><canvas id="radarCanvas"></canvas></div>
        <div class="evo-line">${chart}</div>
      </div>
      <div class="farm">${farmRows}</div>
      <p class="note">The radar sweeps generation by generation. Best fitness (green line) spirals inward toward the champion while the population mean (cyan line) rises to meet it.</p>
    </article>`;
}

function weightCard(report) {
  const ws = report.real_weight_summary;
  const checkpoints = ws?.weekly_checkpoints || [];
  if (checkpoints.length < 2) {
    return `<article class="card"><div class="card-head"><div><p class="kicker">Real data</p><h2>Real weight trajectory</h2></div></div><p class="note">Not enough checkpoints to plot.</p></article>`;
  }
  const points = checkpoints.map((c) => ({ value: c.weight_kg }));
  const markers = (report.surfaced_weeks || [])
    .map((w) => ({ index: w - 1, value: checkpoints[w - 1]?.weight_kg }))
    .filter((m) => m.index >= 0 && m.value != null);
  const chart = lineChart(points, {
    width: 620,
    height: 220,
    series: [{ key: "value", color: "#4cc9f0", width: 2.4 }],
    markers,
    xLabels: checkpoints.map((_, i) => `W${i + 1}`),
  });
  const change = ws.observed_weight_change_kg;
  const sign = change > 0 ? "−" : "+";
  return `
    <article class="card">
      <div class="card-head">
        <div><p class="kicker">Real Fitbit data</p><h2>Real weight trajectory</h2><p class="note">${ws.n_records} real weight records · ${ws.start_weight_kg} kg → ${ws.end_weight_kg} kg (${sign}${Math.abs(change).toFixed(1)} kg)</p></div>
      </div>
      ${chart}
      <p class="note">Yellow × marks the weeks the agent surfaced a decision. Every other week stays quiet.</p>
    </article>`;
}

function timelineCard(report) {
  const flow = report.flow || [];
  const ticks = flow
    .map((f) => `<div class="tick ${f.decision ? "surfaced" : "quiet"}" title="week ${f.week}">${f.decision ? "★" : "·"}</div>`)
    .join("");
  const surfaced = flow.filter((f) => f.decision).length;
  const quiet = flow.length - surfaced;
  return `
    <article class="card">
      <div class="card-head">
        <div><p class="kicker">Background agent</p><h2>Background agent timeline</h2><p class="note">${flow.length} weeks · surfaced ${surfaced}× · quiet ${quiet}×</p></div>
      </div>
      <div class="timeline">${ticks}</div>
      <div class="legend"><span class="q">quiet</span><span class="s">one decision</span></div>
      <p class="note">It is not a notification feed. It absorbs noisy weekly weight in the background and surfaces only on a real plateau or protocol change.</p>
    </article>`;
}

function championCard(champion, title = "Champion protocol") {
  if (!champion) return "";
  const fat = Math.max(0, 1 - (champion.protein_pct || 0) - (champion.carb_pct || 0));
  const workout = `${champion.workout_freq}× ${champion.workout_type}`;
  const cells = [
    { value: `${champion.meal_window}h`, label: "Eating window" },
    { value: `${champion.meal_count} meals`, label: "Meals / day" },
    { value: `${champion.sleep_target}h`, label: "Sleep target" },
    { value: `${champion.step_target}`, label: "Steps / day" },
    { value: workout, label: "Training" },
    { value: champion.refeed_schedule === "none" ? "none" : champion.refeed_schedule, label: "Planned refeed" },
    { value: champion.late_night_rule ? "kept" : "removed", label: "Late-night snack" },
    { value: `${champion.calorie_target}`, label: "Daily kcal" },
    { value: fmtPct(champion.carb_pct), label: "Carb share" },
  ];
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">Evolved champion</p><h2>${title}</h2></div></div>
      <div class="big-number">${champion.calorie_target}<small> kcal/day</small></div>
      <div class="donut-wrap" style="margin:16px 0">
        ${donut(champion.protein_pct, champion.carb_pct, fat)}
        <div class="macro-list">
          <div class="macro"><span class="swatch" style="background:#4cc9f0"></span>Protein <b>${fmtPct(champion.protein_pct)}</b></div>
          <div class="macro"><span class="swatch" style="background:#35d07f"></span>Carbs <b>${fmtPct(champion.carb_pct)}</b></div>
          <div class="macro"><span class="swatch" style="background:#ffd166"></span>Fat <b>${fmtPct(fat)}</b></div>
        </div>
      </div>
      <div class="champion-grid">${cells.map((c) => `<div class="champ-cell"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`).join("")}</div>
    </article>`;
}

function decisionCard(report) {
  const decision = report.decision;
  if (!decision) {
    return `<article class="card"><div class="card-head"><div><p class="kicker">One decision</p><h2>One decision</h2></div></div><p class="note">Nothing worth interrupting you this period.</p></article>`;
  }
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">One decision at a time</p><h2>One decision</h2></div></div>
      <div class="decision-box">
        <p class="headline">${decision.headline}</p>
        <p class="action">${decision.action}</p>
        <p class="reason">${decision.reason}</p>
      </div>
      <p class="note">Not five pages of suggestions — one next step you can actually take.</p>
    </article>`;
}

function safetyCalibrationCard(report) {
  const safety = report.safety || {};
  const cal = report.calibration?.profile || {};
  const binge = cal.binge_sensitivity ?? 0;
  const adaptation = cal.metabolic_adaptation ?? 0;
  const adherence = cal.adherence_base ?? 0;
  const warnings = (safety.warnings || []).length ? safety.warnings.join("; ") : "No risk warnings";
  const gauges = [
    { label: "Binge sensitivity", value: binge, display: binge.toFixed(2) },
    { label: "Metabolic adaptation", value: adaptation, display: adaptation.toFixed(2) },
    { label: "Adherence prior", value: adherence, display: adherence.toFixed(2) },
  ];
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">Calibration · Safety</p><h2>Fitted from real data</h2></div></div>
      <div class="gauge-row">
        ${gauges.map((g) => `<div class="gauge"><div class="gauge-top"><span>${g.label}</span><b>${g.display}</b></div><div class="bar"><div class="fill" style="width:${Math.round(g.value * 100)}%"></div></div></div>`).join("")}
      </div>
      <div style="margin-top:16px;font-size:13px">
        <p style="margin:0 0 6px;color:var(--muted)">Safety boundary: <b style="color:${safety.red_flags ? "var(--red)" : "var(--green)"}">${safety.red_flags ? "Escalation triggered" : "Passed"}</b></p>
        <p class="note">${warnings}. This agent is a behavioral sentinel — not a diagnosis, not a prescription.</p>
      </div>
    </article>`;
}

function compareCard(a, b) {
  if (!a || !b) return "";
  const rows = (side, other) => [
    { label: "Daily kcal", value: `${side.champion.calorie_target}`, diff: side.champion.calorie_target !== other.champion.calorie_target },
    { label: "Late-night snack", value: side.champion.late_night_rule ? "kept" : "removed", diff: side.champion.late_night_rule !== other.champion.late_night_rule },
    { label: "Planned refeed", value: side.champion.refeed_schedule === "none" ? "none" : side.champion.refeed_schedule, diff: side.champion.refeed_schedule !== other.champion.refeed_schedule },
    { label: "Sleep target", value: `${side.champion.sleep_target}h`, diff: side.champion.sleep_target !== other.champion.sleep_target },
    { label: "Binge sensitivity", value: side.calibration.profile.binge_sensitivity.toFixed(2), diff: Math.abs(side.calibration.profile.binge_sensitivity - other.calibration.profile.binge_sensitivity) > 0.05 },
  ];
  const sideHtml = (side, other, name) => `
    <div class="side">
      <h3>${name}</h3>
      ${rows(side, other).map((r) => `<div class="row"><span>${r.label}</span><b class="${r.diff ? "diff" : ""}">${r.value}</b></div>`).join("")}
    </div>`;
  return `
    <article class="card wide">
      <div class="card-head">
        <div><p class="kicker">Personalization proof</p><h2>Two real users · same goal · opposite protocols</h2><p class="note">The same swarm engine, different real behavioral data, different champions. That is personalization, not a template.</p></div>
      </div>
      <div class="compare">
        ${sideHtml(a, b, `User A · ${a.user_id}`)}
        ${sideHtml(b, a, `User B · ${b.user_id}`)}
      </div>
    </article>`;
}

function renderDemo(report, compare) {
  updateConnectome(report.connectome);
  const source = report.data_source
    ? `${report.data_source.path} · Zenodo ${report.data_source.zenodo} (${report.data_source.license})`
    : "uploaded data";

  const html = `
    <article class="card wide">
      <div class="card-head">
        <div><p class="kicker">Real business flow</p><h2>User ${report.user_id}</h2><p class="note">${report.real_weight_summary.n_records} real weight records → calibrate the twin → weekly background ticks → one surfaced decision → durable feedback.</p></div>
        <div class="runtime-tag">${source}</div>
      </div>
    </article>
    ${evolutionCard(report.evolution, "Swarm evolution", "Cyber flies ran ten thousand experiments on your digital twin. Weak protocols were culled.")}
    <div class="grid-2">
      ${weightCard(report)}
      ${timelineCard(report)}
    </div>
    <div class="grid-3">
      ${championCard(report.champion)}
      ${decisionCard(report)}
      ${safetyCalibrationCard(report)}
    </div>
    ${compareCard(report, compare)}
  `;
  dashboard.innerHTML = html;
  initRadar(document.getElementById("radarCanvas"), report.evolution);
  stopLoading();
}

function renderLocal(report) {
  updateConnectome(report.connectome);
  const html = `
    ${evolutionCard(report.evolution, "Swarm evolution · quick run", "Watch the champion converge out of ten thousand experiments.")}
    <div class="grid-2">
      ${championCard(report.champion)}
      <article class="card">
        <div class="card-head"><div><p class="kicker">Real connectome</p><h2>Real fly-brain prior</h2></div></div>
        <div class="gauge-row">
          <div class="gauge"><div class="gauge-top"><span>Reward : punishment</span><b>${report.connectome.reward_punishment_ratio} : 1</b></div><div class="bar"><div class="fill" style="width:72%"></div></div></div>
          <p class="note">${report.connectome.n_kenyon} Kenyon cells compress into ${report.connectome.n_mbon} decision units; reward strongly outranks punishment, so aggressive restriction triggers disproportionate craving pressure.</p>
        </div>
        <div class="champion-grid" style="margin-top:14px">
          <div class="champ-cell"><div class="value">${report.connectome.kc_mbon_convergence}</div><div class="label">KC / MBON convergence</div></div>
          <div class="champ-cell"><div class="value">${report.adherence}</div><div class="label">Champion adherence</div></div>
          <div class="champ-cell"><div class="value">${report.binge_risk}</div><div class="label">Binge risk</div></div>
        </div>
      </article>
    </div>
  `;
  dashboard.innerHTML = html;
  initRadar(document.getElementById("radarCanvas"), report.evolution);
  stopLoading();
}

async function runDemoFlow() {
  clearError();
  const userA = state.user;
  const userB = userA === "6962181067" ? "8877689391" : "6962181067";
  const payloadA = { mode: "demo", user_id: userA, population_size: 250, generations: 25, seed: 7 };
  const payloadB = { mode: "demo", user_id: userB, population_size: 250, generations: 25, seed: 7 };
  setLoading(`Evolving the ${userA} and ${userB} swarms on real Fitbit data…`);
  try {
    const [a, b] = await Promise.all([post(payloadA), post(payloadB)]);
    state.demo = a;
    state.compare = b;
    renderDemo(a, b);
  } catch (err) {
    stopLoading();
    showError(err.message);
  }
}

async function runSwarmFlow() {
  clearError();
  setLoading("The flies are running ten thousand experiments…");
  try {
    const report = await post({});
    state.local = report;
    renderLocal(report);
  } catch (err) {
    stopLoading();
    showError(err.message);
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 1; }
        else quoted = false;
      } else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(cell);
      if (row.some((v) => v.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  row.push(cell);
  if (row.some((v) => v.trim() !== "")) rows.push(row);
  return rows;
}

function rowsToObjects(rows) {
  if (rows.length < 2) return [];
  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((row) => Object.fromEntries(headers.map((h, i) => [h, (row[i] || "").trim()])));
}

async function readFile(file) {
  if (!file) return [];
  const text = await file.text();
  return rowsToObjects(parseCsv(text));
}

async function runUploadFlow() {
  clearError();
  if (!weightFile.files[0]) {
    showError("Choose a weight CSV first — or just use the preloaded real users above.");
    return;
  }
  const weightRows = await readFile(weightFile.files[0]);
  const activityRows = await readFile(activityFile.files[0]);
  const weight_records = weightRows
    .filter((r) => r.date && r.weight_kg)
    .map((r) => ({ date: r.date, weight_kg: parseFloat(r.weight_kg), adherence: r.adherence ? parseFloat(r.adherence) : undefined }))
    .sort((a, b) => a.date.localeCompare(b.date));
  const activity_records = activityRows
    .filter((r) => r.date)
    .map((r) => ({ date: r.date, total_steps: parseInt(r.total_steps || "0", 10), active_minutes: parseInt(r.active_minutes || "0", 10), calories: parseInt(r.calories || "0", 10) }))
    .sort((a, b) => a.date.localeCompare(b.date));
  if (!weight_records.length) {
    showError("No date / weight_kg rows found in the weight CSV.");
    return;
  }
  setLoading("Calibrating your behavioral twin and evolving the swarm…");
  try {
    const report = await post({
      mode: "demo",
      user_id: "uploaded_user",
      weight_records,
      activity_records,
      population_size: 250,
      generations: 25,
      seed: 7,
    });
    state.demo = report;
    state.compare = null;
    renderDemo(report, null);
  } catch (err) {
    stopLoading();
    showError(err.message);
  }
}

userChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    userChips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.user = chip.dataset.user;
  });
});

runDemo.addEventListener("click", runDemoFlow);
runSwarm.addEventListener("click", runSwarmFlow);
runUpload.addEventListener("click", runUploadFlow);

checkPing();
