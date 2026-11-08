// えびの円卓を開いた時の演出 (直し54n, the teacher, 11/8). Made after the
// teacher's own opening for their class newsletter: a paper plane flown in
// 3D, a cut on the beat to a flat plane on one colour, then the title one
// character a beat. Here: the plane flies over Ebino's own relief (the
// pictures the map already has), the seasons going round under it (spring,
// autumn, then night, when the town's lights come on), and lands in the
// lamp's light; on the beat the night's indigo and a flat paper plane, which
// flies off to the title's upper right; 「え」「び」「の」「円」「卓」 one a
// beat; the lamp's rule and one line (texts/launch_line.txt); then the title
// goes to its place at the top of the first screen and the screen is there.
//
// About 8 seconds. A click on it, Enter, Esc or the space bar ends it (to
// the title going to its place). Nothing is sent, kept or asked of the
// server: it reads only the pictures the map uses and the title on the page.
// No sound (a page that has not been touched may not play one). With motion
// reduced: none at all, the first screen as before. A picture that cannot be
// read: the flight is left out and it starts at the cut.
//
// render(T) draws the moment T seconds in, nothing else (as the newsletter's
// opening was made), so a skip is only a jump in T.
(function () {
  "use strict";
  const root = document.documentElement;
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (still) return;
  root.classList.add("launch-on");  // Before the first paint: the start screen is never seen first.

  const B = 0.46, CUT = 3.5, beat = (k) => CUT + (k - 1) * B;  // Beat 1 = the cut.
  const END = beat(9) + 0.7, OUT = 0.8, SKIP_OUT = 0.55;
  const LOAD_MS = 4000;  // The pictures not read by then (counted while the page is seen): no flight.
  const IMG = [4800, 3646];
  const SPOT = [0.43, 0.50];  // Where the lamp is: the middle of the basin.
  const SKY = [[38, 62, 84], [58, 34, 24], [6, 11, 24]];  // Spring morning, autumn evening, night.
  const NS = "http://www.w3.org/2000/svg";
  const cl = (x) => x < 0 ? 0 : x > 1 ? 1 : x, p = (T, t0, d) => cl((T - t0) / d);
  const L = (a, b, t) => a + (b - a) * t;
  const oQ = (x) => 1 - Math.pow(1 - x, 4), ioC = (x) => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  const oB = (x) => { const c = 1.4; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const ioS = (x) => x * x * (3 - 2 * x);

  let box, words = null, flight = true, W = 0, H = 0, G = 0, GH = 0, fs = 0;
  const parts = {}, towns = [], faces = [], icons = [];

  // --- the paper plane in 3D (its nose -z, its wings x, up y) ---
  const PLANE = { N: [0, 0, -0.62], Lw: [-0.36, 0.05, 0.27], Rw: [0.36, 0.05, 0.27], T: [0, 0, 0.27], K: [0, -0.11, 0.25] };
  const FACES = [["N", "Lw", "T"], ["N", "T", "Rw"], ["N", "T", "K"]];
  const LANDED = { x: 0, y: -0.06, z: -2.0, bank: 0, pitch: 1.2, yaw: 0, spin: -0.55, warm: 1 };
  const rotX = (v, a) => [v[0], v[1] * Math.cos(a) - v[2] * Math.sin(a), v[1] * Math.sin(a) + v[2] * Math.cos(a)];
  const rotY = (v, a) => [v[0] * Math.cos(a) + v[2] * Math.sin(a), v[1], -v[0] * Math.sin(a) + v[2] * Math.cos(a)];
  const rotZ = (v, a) => [v[0] * Math.cos(a) - v[1] * Math.sin(a), v[0] * Math.sin(a) + v[1] * Math.cos(a), v[2]];
  const sub3 = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  const LIGHT = unit([-0.4, 0.8, 0.45]);
  // --- the flat plane, seen from above, its centre of mass at 0 (nose up) ---
  const FLAT = [[[0, -1.187], [-0.62, 0.593], [0, 0.233]], [[0, -1.187], [0, 0.233], [0.62, 0.593]]];
  const GHOSTS = 6;

  function make(tag, cls, parent, ns) {
    const node = ns ? document.createElementNS(NS, tag) : document.createElement(tag);
    if (cls) node.setAttribute("class", cls);
    parent.append(node);
    return node;
  }

  function build() {
    box = document.getElementById("launch");
    parts.world = make("div", "launch-world", box);
    parts.ground = make("div", "launch-ground", parts.world);
    for (const [id, src] of [["spring", "/relief_spring.webp"], ["autumn", "/relief_autumn.webp"], ["night", "/relief.webp"]]) {
      parts[id] = make("img", "launch-picture", parts.ground);
      parts[id].alt = "";
      parts[id].decoding = "async";
      parts[id].src = src;
    }
    parts.glow = make("div", "launch-glow", parts.ground);
    let seed = 7;  // The town's lights round the lamp, the same each time.
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 16; i++) {
      const a = rnd() * Math.PI * 2, r = 0.012 + rnd() * 0.07;
      towns.push({ u: SPOT[0] + Math.cos(a) * r * 1.2, v: SPOT[1] + Math.sin(a) * r, node: make("div", "launch-town", parts.ground) });
    }
    parts.fog = make("div", "launch-fog", box);
    parts.plane = make("svg", "launch-plane", box, true);
    for (let i = 0; i < FACES.length; i++) faces.push(make("polygon", "", parts.plane, true));
    parts.flat = make("div", "launch-flat", box);
    parts.ring = make("div", "launch-ring", box);
    parts.icons = make("svg", "launch-icons", box, true);
    for (let i = 0; i <= GHOSTS; i++) {
      const g = make("g", "", parts.icons, true);
      FLAT.forEach((points, side) => {
        const face = make("polygon", side ? "launch-paper-shade" : "launch-paper", g, true);
        face.setAttribute("points", points.map((q) => q.join(",")).join(" "));
      });
      icons.push(g);
    }
    parts.title = make("div", "launch-title", box);
    const h1 = document.querySelector(".masthead h1");
    for (const ch of (h1 ? h1.textContent.trim() : "")) make("span", "", parts.title).textContent = ch;
    parts.rule = make("div", "launch-rule", box);
    parts.line = make("div", "launch-line", box);
    parts.skip = make("div", "launch-skip", box);
    window.EbinoLaunch.words(words);  // Words already in: shown.
  }

  function layout() {
    W = window.innerWidth; H = window.innerHeight;
    G = 2.3 * Math.max(W, H * 1.4); GH = G * IMG[1] / IMG[0];
    Object.assign(parts.ground.style, { width: G + "px", height: GH + "px", left: (W - G) / 2 + "px", top: (H - GH) / 2 + "px" });
    parts.world.style.perspective = H * 1.05 + "px";
    for (const t of towns) Object.assign(t.node.style, { left: t.u * G + "px", top: t.v * GH + "px" });
    Object.assign(parts.glow.style, { width: G * .34 + "px", height: G * .34 + "px", left: SPOT[0] * G - G * .17 + "px", top: SPOT[1] * GH - G * .17 + "px" });
    fs = Math.min(W * .15, H * .23);
    Object.assign(parts.title.style, { fontSize: fs + "px", top: H * .47 - fs * .55 + "px" });
    Object.assign(parts.rule.style, { width: fs * 2 + "px", left: W / 2 - fs + "px", top: H * .47 + fs * .62 + "px" });
    Object.assign(parts.line.style, { fontSize: Math.max(16, fs * .14) + "px", top: H * .47 + fs * .78 + "px" });
  }

  function project(pose) {
    const f = H * 0.95, cx = W / 2, cy = H / 2, pts = {};
    for (const [k, v0] of Object.entries(PLANE)) {
      let v = rotZ(v0, pose.bank); v = rotX(v, pose.pitch); v = rotY(v, pose.yaw); v = rotZ(v, pose.spin);
      v = [v[0] + pose.x, v[1] + pose.y, v[2] + pose.z];
      pts[k] = { w: v, s: [cx + f * v[0] / -v[2], cy - f * v[1] / -v[2]] };
    }
    return pts;
  }

  function drawPlane(pose) {
    const pts = project(pose);
    // Far faces first; each lit by how it turns to the light, warmer in the lamp's.
    FACES.map((F, i) => ({ i, z: F.reduce((t, k) => t + pts[k].w[2], 0) })).sort((a, b) => a.z - b.z).forEach(({ i }) => {
      const F = FACES[i], node = faces[i];
      const n = unit(cross(sub3(pts[F[1]].w, pts[F[0]].w), sub3(pts[F[2]].w, pts[F[0]].w)));
      const lit = 0.55 + 0.45 * Math.abs(n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]);
      const c = [L(150, 251, lit) + pose.warm * 4, L(162, 246, lit), L(190, 234, lit) - pose.warm * 30].map((x) => Math.round(Math.min(255, x)));
      node.setAttribute("points", F.map((k) => pts[k].s.join(",")).join(" "));
      node.setAttribute("fill", `rgb(${c})`);
      parts.plane.append(node);
    });
  }

  function render(T, out) {
    // 1. Over Ebino, the seasons going round (0 to the cut).
    const fl = ioS(p(T, 0, CUT - 0.75)), ld = ioC(p(T, CUT - 0.95, 0.95));
    const u = L(0.37, SPOT[0], fl), v = L(0.80, SPOT[1] + 0.03, fl) - ld * 0.03;
    const tilt = 66 - ld * 30, z = L(-H * 0.18, -H * 0.05, fl) + ld * H * 0.32;
    const yaw = L(-12, 0, fl) + Math.sin(T * 1.3) * 2 * (1 - ld);
    parts.ground.style.transform = `translateY(${H * 0.16 * (1 - ld * .6)}px) translateZ(${z}px) rotateX(${tilt}deg) rotateZ(${yaw}deg) translate(${(0.5 - u) * G}px, ${(0.5 - v) * GH}px)`;
    const aut = ioS(p(T, 0.9, 0.7)), nig = ioS(p(T, 1.85, 0.7));
    parts.autumn.style.opacity = aut;
    parts.night.style.opacity = nig;
    const dawn = oQ(p(T, 0, 0.4));  // From the night's colour it was waiting in.
    const sky = SKY[0].map((c, i) => Math.round(L(SKY[2][i], L(L(c, SKY[1][i], aut), SKY[2][i], nig), dawn)));
    root.style.setProperty("--launch-sky", sky.join(","));
    parts.glow.style.opacity = nig * (L(0.35, 1, fl) + ld * 0.3);
    for (const t of towns) t.node.style.opacity = nig * oQ(cl((0.27 - (v - t.v)) / 0.07));
    const sway = Math.sin(T * 1.9);
    drawPlane({ x: L(sway * 0.09, 0, ld), y: L(-0.33 + Math.sin(T * 2.6) * 0.025, LANDED.y, ld), z: L(-2.25, LANDED.z, ld),
      bank: L(-sway * 0.45, 0, ld), pitch: L(0.22, LANDED.pitch, ld), yaw: L(sway * 0.12, 0, ld), spin: L(0, LANDED.spin, ld), warm: ld });
    const cut = T >= CUT || !flight;
    for (const part of [parts.world, parts.fog, parts.plane]) part.style.opacity = cut ? 0 : dawn;
    // 2. Beat 1, the cut: the night's indigo, and the plane flat where it landed, the same way and size.
    parts.flat.style.opacity = cut ? 1 : 0;
    const lp = project(LANDED), nose = lp.N.s, back = lp.T.s;
    const PX = (nose[0] + lp.Lw.s[0] + lp.Rw.s[0]) / 3, PY = (nose[1] + lp.Lw.s[1] + lp.Rw.s[1]) / 3;
    const rot0 = Math.atan2(nose[0] - back[0], back[1] - nose[1]) * 180 / Math.PI;
    const len0 = Math.hypot(nose[0] - back[0], nose[1] - back[1]) / 1.42;
    const r = p(T, CUT, 0.7);
    Object.assign(parts.ring.style, { left: PX + "px", top: PY + "px", transform: `scale(${1 + oQ(r) * 7})`, opacity: cut && r < 1 ? 0.55 * (1 - r) : 0 });
    // Beat 2: off to the title's upper right, its trail behind it (faster, longer).
    const to = [W / 2 + fs * 2.95, H * 0.47 - fs * 0.95], mid = [W / 2 + fs * 0.6, H * 0.47 - fs * 1.7];
    const at = (k) => { const q = 1 - k; return [q * q * PX + 2 * q * k * mid[0] + k * k * to[0], q * q * PY + 2 * q * k * mid[1] + k * k * to[1]]; };
    icons.forEach((g, i) => {
      const q = ioC(p(T - i * 0.016, beat(2), 0.8)), [x, y] = at(q);
      g.setAttribute("transform", `translate(${x},${y}) rotate(${L(rot0, 40, q)}) scale(${L(len0, fs * 0.32, q)})`);
      g.style.opacity = !cut ? 0 : i === 0 ? 1 : q > 0 && q < 1 ? 0.22 * (1 - i / (GHOSTS + 1)) : 0;
    });
    // Beats 3 to 7: the title, a character a beat.
    [...parts.title.children].forEach((s, i) => {
      const t0 = beat(3 + i), e = oQ(p(T, t0, 0.3)), g = oB(p(T, t0, 0.5));
      s.style.opacity = e;
      s.style.transform = `translateY(${(1 - g) * -0.3}em) scale(${L(1.22, 1, oQ(p(T, t0, 0.42)))})`;
      s.style.filter = e < 1 ? `blur(${((1 - e) * 10).toFixed(1)}px)` : "none";
    });
    // Beat 8: the lamp's rule and the line.
    parts.rule.style.transform = `scaleX(${oQ(p(T, beat(8), 0.6))})`;
    const sb = oQ(p(T, beat(8) + 0.1, 0.7));
    parts.line.style.opacity = sb;
    parts.line.style.letterSpacing = L(0.7, 0.3, sb) + "em";
    parts.skip.style.opacity = words && words.skip ? 0.8 : 0;
    // The end: the title to its place on the first screen, all else away.
    const k = out ? ioC(cl(out)) : 0;
    box.style.backgroundColor = `rgba(${sky.join(",")},${1 - k})`;
    for (const part of [parts.flat, parts.icons, parts.rule, parts.line, parts.skip]) part.style.visibility = k >= 1 ? "hidden" : "";
    parts.flat.style.opacity = cut ? 1 - k : 0;
    for (const part of [parts.icons, parts.rule, parts.line]) part.style.opacity = (part === parts.line ? sb : 1) * (1 - k);
    parts.title.style.transform = home ? `translate(${home.dx * k}px, ${home.dy * k}px) scale(${L(1, home.scale, k)})` : "";
    parts.title.style.opacity = home && !home.fade ? 1 : 1 - k;
  }

  // Where the title goes: the first screen's own title, measured at the end.
  let home = null;
  function measureHome() {
    const h1 = document.querySelector(".masthead h1");
    const size = h1 ? parseFloat(getComputedStyle(h1).fontSize) : 0;
    // Each title by its characters' own box (the page's starts at its left, the launch's is centred).
    const own = (node) => { const range = document.createRange(); range.selectNodeContents(node); return range.getBoundingClientRect(); };
    if (!size || !fs) return null;
    const to = own(h1), from = own(parts.title), div = parts.title.getBoundingClientRect();
    if (!to.width || !from.width) return null;
    const cx = from.left + from.width / 2, cy = from.top + from.height / 2;
    parts.title.style.transformOrigin = `${cx - div.left}px ${cy - div.top}px`;
    return { scale: size / fs, dx: to.left + to.width / 2 - cx, dy: to.top + to.height / 2 - cy };
  }

  let began = null, ending = null, frame = 0, over = false;
  function finish() {
    over = true;
    cancelAnimationFrame(frame);
    window.removeEventListener("resize", onResize);
    document.removeEventListener("keydown", onKey, true);
    root.classList.remove("launch-on");
    root.style.removeProperty("--launch-sky");
    if (box) box.remove();
  }
  function step(now) {
    if (over) return;
    if (began === null) began = now;
    const T = (now - began) / 1000;
    if (!ending && T >= END) ending = { from: now, length: OUT, at: END };
    if (ending) {
      if (!home) home = measureHome() || { scale: 1, dx: 0, dy: 0, fade: true };
      const k = (now - ending.from) / 1000 / ending.length;
      render(ending.at, Math.min(1, k));
      if (k >= 1) return finish();
    } else render(T, 0);
    frame = requestAnimationFrame(step);
  }
  function skip() {
    if (over || ending) return;
    ending = { from: performance.now(), length: SKIP_OUT, at: END };
  }
  function onKey(event) {
    if (event.key === "Enter" || event.key === "Escape" || event.key === " ") {
      event.preventDefault();
      event.stopPropagation();
      skip();
    }
  }
  function onResize() { layout(); home = null; }

  function ready(src) {
    return new Promise((done) => {
      const picture = parts[src];
      picture.decode ? picture.decode().then(() => done(true), () => done(false)) : (picture.onload = () => done(true));
    });
  }

  function go() {
    build();
    layout();
    box.addEventListener("click", skip);
    document.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", onResize);
    const fonts = document.fonts && document.fonts.load ? document.fonts.load('800 100px "Ebino Title"', parts.title.textContent || "あ").catch(() => null) : null;
    const pictures = Promise.all(["spring", "autumn", "night"].map(ready)).then((read) => read.every(Boolean));
    // Counted only while the page is seen: a page opened behind waits, its opening whole.
    const late = new Promise((done) => {
      const count = () => { if (!document.hidden) { document.removeEventListener("visibilitychange", count); setTimeout(() => done(false), LOAD_MS); } };
      document.addEventListener("visibilitychange", count);
      count();
    });
    Promise.all([Promise.race([pictures, late]), fonts]).then(([read]) => {
      if (over) return;
      flight = read;
      if (!flight) began = performance.now() - CUT * 1000;  // No pictures: from the cut.
      box.classList.add("launch-going");
      frame = requestAnimationFrame(step);
    });
  }

  // The app gives the words once /api/setup is in (texts/launch_line.txt, opening_skip.txt).
  window.EbinoLaunch = {
    words(given) {
      words = given || null;
      if (!parts.line) return;
      parts.line.textContent = (words && words.line) || "";
      parts.skip.textContent = (words && words.skip) || "";
    },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
  else go();
})();
