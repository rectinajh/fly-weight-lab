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
    pingText.textContent = `已连接真实 AgentCore · ${data.status || "Healthy"}`;
    clearError();
  } catch {
    pingDot.className = "dot bad";
    pingText.textContent = "AgentCore 不可达";
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

function sampleFarm(farm, target = 120) {
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
  const width = opts.width || 720;
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
  let xText = "";
  xText += `<text x="${pad.l}" y="${height - 8}" fill="#4c637a" font-size="10">${xLabels[0] ?? 0}</text>`;
  xText += `<text x="${width - pad.r}" y="${height - 8}" text-anchor="end" fill="#4c637a" font-size="10">${xLabels[xLabels.length - 1] ?? points.length - 1}</text>`;

  return `<svg class="svg-chart" viewBox="0 0 ${width} ${height}" role="img">${grid}${lines}${markers}${xText}</svg>`;
}

function donut(protein, carb, fat) {
  const total = protein + carb + fat || 1;
  const r = 42;
  const c = 2 * Math.PI * r;
  const segments = [
    { value: protein, color: "#4cc9f0", label: "蛋白" },
    { value: carb, color: "#35d07f", label: "碳水" },
    { value: fat, color: "#ffd166", label: "脂肪" },
  ];
  let offset = 0;
  let circles = "";
  for (const seg of segments) {
    const len = (seg.value / total) * c;
    circles += `<circle cx="60" cy="60" r="${r}" fill="none" stroke="${seg.color}" stroke-width="15" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 60 60)"/>`;
    offset += len;
  }
  return `<svg viewBox="0 0 120 120" style="width:120px;height:120px" role="img">${circles}<text x="60" y="56" text-anchor="middle" fill="#eaf2fb" font-size="16" font-weight="700">${Math.round(protein * 100)}%</text><text x="60" y="72" text-anchor="middle" fill="#8aa0b8" font-size="10">蛋白质</text></svg>`;
}

function fmtPct(v) { return `${Math.round((v || 0) * 100)}%`; }
function fmtKg(v) { return `${Number(v || 0).toFixed(1)} kg`; }

function updateConnectome(connectome) {
  if (!connectome) return;
  document.getElementById("statKenyon").textContent = connectome.n_kenyon ?? "4064";
  document.getElementById("statDan").textContent = connectome.n_dan ?? "340";
  document.getElementById("statMbon").textContent = connectome.n_mbon ?? "97";
  document.getElementById("statRatio").textContent = `${connectome.reward_punishment_ratio ?? "2.56"}:1`;
}

function evolutionCard(evolution, title, subtitle) {
  const gens = evolution?.generations || [];
  if (!gens.length) return "";
  const points = gens.map((g) => ({ best: g.best, mean: g.mean }));
  const series = [
    { key: "best", color: "#35d07f", width: 2.6 },
    { key: "mean", color: "#4cc9f0", width: 1.6, opacity: 0.85 },
  ];
  const chart = lineChart(points, {
    width: 720,
    height: 220,
    series,
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
        <div><p class="kicker">Genetic swarm</p><h2>${title}</h2><p class="note">${subtitle}</p></div>
        <div class="legend"><span class="q">存活</span><span class="s">淘汰</span></div>
      </div>
      ${chart}
      <div class="farm">${farmRows}</div>
      <p class="note">每一行是一代果蝇：绿色存活进入下一代，红色被淘汰。best（绿线）一路收敛，mean（青线）说明整个蜂群越来越像冠军。</p>
    </article>`;
}

function weightCard(report) {
  const ws = report.real_weight_summary;
  const checkpoints = ws?.weekly_checkpoints || [];
  if (checkpoints.length < 2) {
    return `<article class="card"><div class="card-head"><div><p class="kicker">Real data</p><h2>真实体重轨迹</h2></div></div><p class="note">数据点不足以绘制轨迹。</p></article>`;
  }
  const points = checkpoints.map((c) => ({ value: c.weight_kg }));
  const markers = (report.surfaced_weeks || []).map((w) => ({ index: w - 1, value: checkpoints[w - 1]?.weight_kg }));
  const chart = lineChart(points, {
    width: 620,
    height: 220,
    series: [{ key: "value", color: "#4cc9f0", width: 2.4 }],
    markers: markers.filter((m) => m.index >= 0 && m.value != null),
    xLabels: checkpoints.map((_, i) => `W${i + 1}`),
  });
  return `
    <article class="card">
      <div class="card-head">
        <div><p class="kicker">Real Fitbit data</p><h2>真实体重轨迹</h2><p class="note">${ws.n_records} 条真实体重记录 · ${ws.start_weight_kg} kg → ${ws.end_weight_kg} kg（${ws.observed_weight_change_kg > 0 ? "−" : "+"}${Math.abs(ws.observed_weight_change_kg).toFixed(1)} kg）</p></div>
      </div>
      ${chart}
      <p class="note">黄色 × 是 agent 冒出来给决定的周。其余周保持安静。</p>
    </article>`;
}

function timelineCard(report) {
  const flow = report.flow || [];
  const ticks = flow
    .map((f) => {
      const cls = f.decision ? "surfaced" : "quiet";
      const symbol = f.decision ? "★" : "·";
      return `<div class="tick ${cls}" title="week ${f.week}">${symbol}</div>`;
    })
    .join("");
  const surfaced = flow.filter((f) => f.decision).length;
  const quiet = flow.length - surfaced;
  return `
    <article class="card">
      <div class="card-head">
        <div><p class="kicker">Background agent</p><h2>后台 agent 时间线</h2><p class="note">${flow.length} 周里只冒出来 ${surfaced} 次，其余 ${quiet} 周安静。</p></div>
      </div>
      <div class="timeline">${ticks}</div>
      <div class="legend"><span class="q">安静</span><span class="s">只给一个决定</span></div>
      <p class="note">它不是推送提醒，而是在后台消化体重噪音，只在平台期或冠军方案真正改变时打扰你。</p>
    </article>`;
}

function championCard(champion, title = "冠军方案") {
  if (!champion) return "";
  const fat = Math.max(0, 1 - (champion.protein_pct || 0) - (champion.carb_pct || 0));
  const workout = `${champion.workout_freq}× ${champion.workout_type}`;
  const cells = [
    { value: `${champion.meal_window}h`, label: "进食窗口" },
    { value: `${champion.meal_count} 餐`, label: "每日餐次" },
    { value: `${champion.sleep_target}h`, label: "睡眠目标" },
    { value: `${champion.step_target}`, label: "每日步数" },
    { value: workout, label: "训练节奏" },
    { value: champion.refeed_schedule === "none" ? "无" : champion.refeed_schedule, label: "计划 refeed" },
    { value: champion.late_night_rule ? "保留" : "不保留", label: "固定睡前加餐" },
    { value: champion.calorie_target, label: "每日热量" },
    { value: `${fmtPct(champion.carb_pct)}`, label: "碳水占比" },
  ];
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">Evolved champion</p><h2>${title}</h2></div></div>
      <div class="big-number">${champion.calorie_target}<small> kcal/天</small></div>
      <div class="donut-wrap" style="margin:16px 0">
        ${donut(champion.protein_pct, champion.carb_pct, fat)}
        <div class="macro-list">
          <div class="macro"><span class="swatch" style="background:#4cc9f0"></span>蛋白 <b>${fmtPct(champion.protein_pct)}</b></div>
          <div class="macro"><span class="swatch" style="background:#35d07f"></span>碳水 <b>${fmtPct(champion.carb_pct)}</b></div>
          <div class="macro"><span class="swatch" style="background:#ffd166"></span>脂肪 <b>${fmtPct(fat)}</b></div>
        </div>
      </div>
      <div class="champion-grid">${cells.map((c) => `<div class="champ-cell"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`).join("")}</div>
    </article>`;
}

function decisionCard(report) {
  const decision = report.decision;
  if (!decision) {
    return `<article class="card"><div class="card-head"><div><p class="kicker">One decision</p><h2>唯一决定</h2></div></div><p class="note">这几周没有需要打扰你的事。</p></article>`;
  }
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">One decision at a time</p><h2>唯一决定</h2></div></div>
      <div class="decision-box">
        <p class="headline">${decision.headline}</p>
        <p class="action">${decision.action}</p>
        <p class="reason">${decision.reason}</p>
      </div>
      <p class="note">不是五页建议清单，而是一个你现在就能执行的下一步。</p>
    </article>`;
}

function safetyCalibrationCard(report) {
  const safety = report.safety || {};
  const cal = report.calibration?.profile || {};
  const binge = cal.binge_sensitivity ?? 0;
  const adaptation = cal.metabolic_adaptation ?? 0;
  const adherence = cal.adherence_base ?? 0;
  const warnings = (safety.warnings || []).length
    ? safety.warnings.join("；")
    : "无风险警告";
  const gauges = [
    { label: "暴食敏感度", value: binge, display: binge.toFixed(2) },
    { label: "代谢适应", value: adaptation, display: adaptation.toFixed(2) },
    { label: "坚持度先验", value: adherence, display: adherence.toFixed(2) },
  ];
  return `
    <article class="card">
      <div class="card-head"><div><p class="kicker">Calibration · Safety</p><h2>从真实数据拟合</h2></div></div>
      <div class="gauge-row">
        ${gauges.map((g) => `<div class="gauge"><div class="gauge-top"><span>${g.label}</span><b>${g.display}</b></div><div class="bar"><div class="fill" style="width:${Math.round(g.value * 100)}%"></div></div></div>`).join("")}
      </div>
      <div style="margin-top:16px;font-size:13px">
        <p style="margin:0 0 6px;color:var(--muted)">安全边界：<b style="color:${safety.red_flags ? "var(--red)" : "var(--green)"}">${safety.red_flags ? "已触发升级" : "通过"}</b></p>
        <p class="note">${warnings}。这个 agent 只做行为哨兵，不诊断、不处方。</p>
      </div>
    </article>`;
}

function compareCard(a, b) {
  if (!a || !b) return "";
  const rows = (side, other) => [
    { label: "每日热量", value: `${side.champion.calorie_target} kcal`, diff: side.champion.calorie_target !== other.champion.calorie_target },
    { label: "睡前加餐", value: side.champion.late_night_rule ? "保留" : "不保留", diff: side.champion.late_night_rule !== other.champion.late_night_rule },
    { label: "计划 refeed", value: side.champion.refeed_schedule === "none" ? "无" : side.champion.refeed_schedule, diff: side.champion.refeed_schedule !== other.champion.refeed_schedule },
    { label: "睡眠目标", value: `${side.champion.sleep_target}h`, diff: side.champion.sleep_target !== other.champion.sleep_target },
    { label: "暴食敏感度", value: side.calibration.profile.binge_sensitivity.toFixed(2), diff: Math.abs(side.calibration.profile.binge_sensitivity - other.calibration.profile.binge_sensitivity) > 0.05 },
  ];
  const sideHtml = (side, other, name) => `
    <div class="side">
      <h3>${name}</h3>
      ${rows(side, other).map((r) => `<div class="row"><span>${r.label}</span><b class="${r.diff ? "diff" : ""}">${r.value}</b></div>`).join("")}
    </div>`;
  return `
    <article class="card wide">
      <div class="card-head">
        <div><p class="kicker">Personalization proof</p><h2>两个真实用户 · 同样目标 · 相反方案</h2><p class="note">同一个蜂群引擎，面对不同的行为数据，进化出不同的冠军。这才是“个性化”，不是套模板。</p></div>
      </div>
      <div class="compare">
        ${sideHtml(a, b, `用户 A · ${a.user_id}`)}
        ${sideHtml(b, a, `用户 B · ${b.user_id}`)}
      </div>
    </article>`;
}

function renderDemo(report, compare) {
  updateConnectome(report.connectome);
  const source = report.data_source
    ? `${report.data_source.path} · Zenodo ${report.data_source.zenodo} (${report.data_source.license})`
    : "用户上传数据";

  const html = `
    <article class="card wide">
      <div class="card-head">
        <div><p class="kicker">Real business flow</p><h2>用户 ${report.user_id}</h2><p class="note">${report.real_weight_summary.n_records} 条真实体重记录 → 校准行为孪生 → 后台周 tick → 只冒出一个决定 → 记录真实反馈。</p></div>
        <div class="runtime-tag">${source}</div>
      </div>
    </article>
    ${evolutionCard(report.evolution, "蜂群进化", "赛博果蝇在数字孪生里跑了一万次实验，弱方案被淘汰。")}
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
  stopLoading();
}

function renderLocal(report) {
  updateConnectome(report.connectome);
  const html = `
    ${evolutionCard(report.evolution, "蜂群进化 · 快速演示", "直接跑蜂群，看冠军如何从一万次实验中收敛。")}
    <div class="grid-2">
      ${championCard(report.champion)}
      <article class="card">
        <div class="card-head"><div><p class="kicker">Real connectome</p><h2>真实果蝇大脑先验</h2></div></div>
        <div class="gauge-row">
          <div class="gauge"><div class="gauge-top"><span>奖赏 : 惩罚</span><b>${report.connectome.reward_punishment_ratio} : 1</b></div><div class="bar"><div class="fill" style="width:72%"></div></div></div>
          <p class="note">${report.connectome.n_kenyon} 个 Kenyon cell 压缩到 ${report.connectome.n_mbon} 个决策单元；真实线路里奖赏远强于惩罚，所以激进节食会触发更强的反弹压力。</p>
        </div>
        <div class="champion-grid" style="margin-top:14px">
          <div class="champ-cell"><div class="value">${report.connectome.kc_mbon_convergence}</div><div class="label">KC / MBON 收敛</div></div>
          <div class="champ-cell"><div class="value">${report.adherence}</div><div class="label">冠军坚持度</div></div>
          <div class="champ-cell"><div class="value">${report.binge_risk}</div><div class="label">暴食风险</div></div>
        </div>
      </article>
    </div>
  `;
  dashboard.innerHTML = html;
  stopLoading();
}

async function runDemoFlow() {
  clearError();
  const userA = state.user;
  const userB = userA === "6962181067" ? "8877689391" : "6962181067";
  const payloadA = { mode: "demo", user_id: userA, population_size: 250, generations: 25, seed: 7 };
  const payloadB = { mode: "demo", user_id: userB, population_size: 250, generations: 25, seed: 7 };
  setLoading(`正在用真实 Fitbit 数据进化 ${userA} 与 ${userB} 的蜂群…`);
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
  setLoading("果蝇正在后台跑一万次实验…");
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
    showError("请先选择体重 CSV（或直接用上面的真实用户数据）。");
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
    showError("体重 CSV 里没有 date / weight_kg 行。");
    return;
  }
  setLoading("正在校准你的行为孪生并进化蜂群…");
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
