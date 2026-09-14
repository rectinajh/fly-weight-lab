(() => {
  const canvas = document.getElementById("swarm-bg");
  const ctx = canvas.getContext("2d");

  let width = 0;
  let height = 0;
  let flies = [];
  let raf = 0;
  const pointer = { x: -9999, y: -9999, active: false };

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function makeFly() {
    return {
      x: Math.random() * width,
      y: Math.random() * height,
      homeX: Math.random() * width,
      homeY: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: Math.random() * 1.6 + 0.6,
      alpha: Math.random() * 0.5 + 0.22,
      green: Math.random() > 0.28,
      diving: false,
      diveT: 0,
      diveCooldown: 80 + Math.random() * 320,
      prevX: 0,
      prevY: 0,
    };
  }

  function spawn() {
    const count = Math.min(760, Math.max(240, Math.floor((width * height) / 1900)));
    flies = Array.from({ length: count }, makeFly);
  }

  function step() {
    ctx.clearRect(0, 0, width, height);

    for (const fly of flies) {
      fly.prevX = fly.x;
      fly.prevY = fly.y;

      if (fly.diving) {
        fly.diveT -= 1;
        fly.vx += (fly.diveVX - fly.vx) * 0.35;
        fly.vy += (fly.diveVY - fly.vy) * 0.2;
        if (fly.diveT <= 0) {
          fly.diving = false;
          fly.diveCooldown = 180 + Math.random() * 420;
        }
      } else {
        const dxHome = fly.homeX - fly.x;
        const dyHome = fly.homeY - fly.y;
        fly.vx += dxHome * 0.0005;
        fly.vy += dyHome * 0.0005;

        if (pointer.active) {
          const dx = fly.x - pointer.x;
          const dy = fly.y - pointer.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 16000) {
            const d = Math.sqrt(d2) || 1;
            const force = (16000 - d2) / 16000;
            fly.vx += (dx / d) * force * 0.6;
            fly.vy += (dy / d) * force * 0.6;
          }
        }

        fly.diveCooldown -= 1;
        if (fly.diveCooldown <= 0 && Math.random() < 0.012) {
          fly.diving = true;
          fly.diveT = 20 + Math.floor(Math.random() * 18);
          fly.diveVX = (Math.random() - 0.5) * 7;
          fly.diveVY = 7 + Math.random() * 12;
        }
      }

      fly.vx *= 0.94;
      fly.vy *= 0.94;
      fly.x += fly.vx;
      fly.y += fly.vy;

      if (fly.x < -24) fly.x = width + 24;
      if (fly.x > width + 24) fly.x = -24;
      if (fly.y < -24) fly.y = height + 24;
      if (fly.y > height + 24) fly.y = -24;

      const color = fly.green ? "53, 208, 127" : "76, 201, 240";
      if (fly.diving) {
        const grad = ctx.createLinearGradient(fly.prevX, fly.prevY, fly.x, fly.y);
        grad.addColorStop(0, `rgba(${color}, 0)`);
        grad.addColorStop(1, `rgba(${color}, ${Math.min(1, fly.alpha + 0.45)})`);
        ctx.beginPath();
        ctx.moveTo(fly.prevX, fly.prevY);
        ctx.lineTo(fly.x, fly.y);
        ctx.strokeStyle = grad;
        ctx.lineWidth = fly.r * 1.7;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.arc(fly.x, fly.y, fly.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color}, ${fly.diving ? Math.min(1, fly.alpha + 0.5) : fly.alpha})`;
      ctx.fill();
    }

    raf = requestAnimationFrame(step);
  }

  function onPointerMove(e) {
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.active = true;
  }

  function onPointerLeave() {
    pointer.active = false;
    pointer.x = -9999;
    pointer.y = -9999;
  }

  function start() {
    resize();
    spawn();
    cancelAnimationFrame(raf);
    step();
  }

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(start, 120);
  });
  window.addEventListener("pointermove", onPointerMove, { passive: true });
  window.addEventListener("pointerleave", onPointerLeave);

  start();
})();
