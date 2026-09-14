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

  function spawn() {
    const count = Math.min(900, Math.max(260, Math.floor((width * height) / 1600)));
    flies = Array.from({ length: count }, () => {
      const homeX = Math.random() * width;
      const homeY = Math.random() * height;
      return {
        x: homeX,
        y: homeY,
        homeX,
        homeY,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.6 + 0.6,
        alpha: Math.random() * 0.5 + 0.2,
        green: Math.random() > 0.28,
      };
    });
  }

  function step() {
    ctx.clearRect(0, 0, width, height);

    for (const fly of flies) {
      fly.x += fly.vx;
      fly.y += fly.vy;

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

      fly.vx *= 0.94;
      fly.vy *= 0.94;

      if (fly.x < -20) fly.x = width + 20;
      if (fly.x > width + 20) fly.x = -20;
      if (fly.y < -20) fly.y = height + 20;
      if (fly.y > height + 20) fly.y = -20;

      const color = fly.green ? "53, 208, 127" : "76, 201, 240";
      ctx.beginPath();
      ctx.arc(fly.x, fly.y, fly.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color}, ${fly.alpha})`;
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
