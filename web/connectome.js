(() => {
  const canvas = document.getElementById("connectome-canvas");
  const ctx = canvas.getContext("2d");

  let width = 0;
  let height = 0;
  let nodes = { kenyon: [], dan: [], mbon: [] };
  let particles = [];
  let links = [];
  let raf = 0;

  const colors = {
    kenyon: "76, 201, 240",
    reward: "255, 209, 102",
    punish: "255, 92, 122",
    mbon: "53, 208, 127",
  };

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
  }

  function gridPoints(x0, x1, y0, y1, cols, rows) {
    const points = [];
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const x = x0 + ((x1 - x0) * c) / Math.max(1, cols - 1);
        const y = y0 + ((y1 - y0) * r) / Math.max(1, rows - 1);
        points.push({ x, y });
      }
    }
    return points;
  }

  function build() {
    const top = height * 0.16;
    const bottom = height * 0.72;
    nodes.kenyon = gridPoints(width * 0.05, width * 0.27, top, bottom, 8, 11);
    nodes.dan = gridPoints(width * 0.43, width * 0.56, top + 6, bottom - 6, 3, 5);
    nodes.mbon = gridPoints(width * 0.73, width * 0.94, top + 20, bottom - 20, 2, 3);

    links = [];
    for (const kc of nodes.kenyon) {
      const target = nodes.mbon[Math.floor(Math.random() * nodes.mbon.length)];
      links.push({
        x0: kc.x,
        y0: kc.y,
        x1: target.x,
        y1: target.y,
        alpha: Math.random() * 0.16 + 0.05,
        color: Math.random() > 0.24 ? colors.reward : colors.punish,
      });
    }

    particles = Array.from({ length: 54 }, () => spawnParticle());
  }

  function spawnParticle() {
    const kc = nodes.kenyon[Math.floor(Math.random() * nodes.kenyon.length)];
    const mb = nodes.mbon[Math.floor(Math.random() * nodes.mbon.length)];
    return {
      x0: kc.x,
      y0: kc.y,
      x1: mb.x,
      y1: mb.y,
      x: kc.x,
      y: kc.y,
      prevX: kc.x,
      prevY: kc.y,
      t: 0,
      speed: Math.random() * 0.008 + 0.006,
      color: Math.random() > 0.24 ? colors.reward : colors.punish,
    };
  }

  function drawNodes() {
    for (const kc of nodes.kenyon) {
      ctx.beginPath();
      ctx.arc(kc.x, kc.y, 1.4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${colors.kenyon}, 0.55)`;
      ctx.fill();
    }
    for (const dan of nodes.dan) {
      ctx.beginPath();
      ctx.arc(dan.x, dan.y, 2.4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${colors.reward}, 0.8)`;
      ctx.fill();
    }
    for (const mb of nodes.mbon) {
      ctx.beginPath();
      ctx.arc(mb.x, mb.y, 3.6, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${colors.mbon}, 0.9)`;
      ctx.shadowColor = "rgba(53, 208, 127, 0.8)";
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  function step() {
    ctx.clearRect(0, 0, width, height);

    for (const link of links) {
      ctx.beginPath();
      ctx.moveTo(link.x0, link.y0);
      ctx.lineTo(link.x1, link.y1);
      ctx.strokeStyle = `rgba(${link.color}, ${link.alpha})`;
      ctx.lineWidth = 0.7;
      ctx.stroke();
    }

    drawNodes();

    for (const p of particles) {
      p.prevX = p.x;
      p.prevY = p.y;
      p.t += p.speed;
      if (p.t >= 1) {
        Object.assign(p, spawnParticle());
        continue;
      }
      const t = p.t;
      p.x = p.x0 + (p.x1 - p.x0) * t;
      p.y = p.y0 + (p.y1 - p.y0) * t - Math.sin(t * Math.PI) * 14;

      const grad = ctx.createLinearGradient(p.prevX, p.prevY, p.x, p.y);
      grad.addColorStop(0, `rgba(${p.color}, 0)`);
      grad.addColorStop(1, `rgba(${p.color}, 0.95)`);
      ctx.beginPath();
      ctx.moveTo(p.prevX, p.prevY);
      ctx.lineTo(p.x, p.y);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.4;
      ctx.lineCap = "round";
      ctx.stroke();
    }

    raf = requestAnimationFrame(step);
  }

  function start() {
    resize();
    cancelAnimationFrame(raf);
    step();
  }

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(start, 120);
  });

  start();
})();
