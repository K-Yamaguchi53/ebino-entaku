// The round-table screen. Every word from the server is set with textContent,
// never as HTML.
"use strict";

const state = {
  texts: {}, kinds: {}, seats: [], seatById: {},
  lastOrder: [], met: new Set(), silent: new Set(), carded: new Set(), marks: {},
  askBoxes: {},  // Round number -> the box of 「司会が○○に聞いてみる」.
  bands: {},  // Round number -> the band of コーチ and オブザーバー below.
  // Before the reflection, one answer to コーチ or オブザーバー (直し30-1):
  // one that started the next round; or the model was out once.
  aiAnswered: false, aiUnavailable: false, needsShown: false,
  // Seat -> the card's words, when the same card was sent to it again (直し31-2).
  cardAgain: {},
  // What 「いまやること」 is worked out from (直し31-5): a question being sent;
  // the round's seats still lighting; a lamp card's choices open; one
  // pressed this round; the round's table open with its cards; AI
  // questions to answer below.
  now: { asking: false, reading: false, choices: false, pressed: false, table: false, band: false },
  // Whom the one box at the foot writes to (直し32-2): everyone (a question
  // to the town's adults), one seat (a question card), or an AI's question
  // (the answer starts the next round). Each keeps its own unsent words.
  to: { kind: "all" }, drafts: {},
};

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

async function call(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || String(response.status));
  return data;
}

function sourceLine(source) {
  return [source.title, source.detail, source.note].filter(Boolean).join("　");
}

// The map (map.js) is an extra over the seat list: when it is missing or
// fails, the seat list and the round go on as before.
function onMap(action) {
  if (typeof EbinoMap === "undefined") return;
  try {
    action(EbinoMap);
  } catch (error) {
    $("map").hidden = true;
  }
}

// A ranking item's title, small over the item, as recorded (null when none).
function rankingTitle(piece) {
  return piece.ranking_title ? el("p", { class: "ranking-title", text: piece.ranking_title }) : null;
}

// --- start ---

async function setup() {
  const data = await call("/api/setup");
  Object.assign(state, { texts: data.texts, kinds: data.kinds, seats: data.seats, changedChoices: data.changed_choices });
  for (const seat of data.seats) state.seatById[seat.seat_id] = seat;
  for (const line of data.texts.start_notice) $("start-notice").append(el("li", { text: line }));
  $("start-purpose").textContent = data.texts.start_purpose;
  for (const step of data.texts.now_steps) {
    $("now-steps").append(el("li", { "data-step": step.id, text: step.text }));
  }
  renderInside(data.inside || []);
  setNow();
  $("lab-question").textContent = data.texts.lab_question;
  for (const [key, label] of Object.entries(data.labs)) {
    $("lab-choices").append(el("button", { type: "button", class: "lab-choice", "aria-pressed": "false",
      onclick: (event) => start(key, event.currentTarget) }, phrased(label)));
  }
  $("heavy-talk").textContent = data.texts.heavy_talk_notice;
  setupDrawer();
  setTo({ kind: "all" }, { focus: false });
  $("purpose-heading").textContent = data.texts.purpose_heading;
  for (const text of data.texts.work_questions) {
    $("work-questions").append(el("button", { type: "button", text, onclick: () => fill(text) }));
  }
  renderSeats();
  // The map over the seat list (map.js). No map, or one that fails to draw:
  // the seat list alone, as before.
  // What the map may use: the round's own ways to a quote's paragraph, its
  // mark, a seat's question card and the quote's card (直し26-2).
  const lent = { state, cardEntry, cardDone, setNow, renderSeats, paragraph: paragraphOf, mark: markQuote, openCard: openCardFor,
    readBelow, shownQuotes, phrased, askSeat, answerTo, firstHelp, openParagraph };
  if (data.map && window.rough) onMap((map) => map.init(data.map, data.seats, lent));
}

// The Lab pressed lights up, the others step back, and the table opens a
// moment after (at once when motion is reduced), so the choice is seen.
async function start(lab, chosen) {
  const buttons = [...$("lab-choices").querySelectorAll("button")];
  for (const button of buttons) {
    button.setAttribute("aria-pressed", String(button === chosen));
    button.disabled = true;
  }
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // The opening over the map while /api/start is waited for (直し30-3);
  // none with motion reduced or no map: the table at once, as before.
  const opening = still ? null : playOpening();
  let data;
  try {
    [data] = await Promise.all([call("/api/start", { lab }),
      opening || new Promise((done) => setTimeout(done, still ? 0 : 320))]);
  } catch (error) {
    if (opening) endOpening(true);
    for (const button of buttons) {
      button.setAttribute("aria-pressed", "false");
      button.disabled = false;
    }
    throw error;
  }
  if (opening) endOpening(false);
  $("start").hidden = true;
  $("table").hidden = false;
  $("inside").hidden = !$("inside-counts").children.length;
  setNow();
  onMap((map) => map.show());  // Draws the rim and the river once the map is on screen.
  renderPurposes(data.purposes);
  $("question").focus();
}

// --- the opening (直し30-3) ---

// Once a Lab is picked: over the dark map a paper plane of folded paper in
// 3D takes off from the school (the roof of its 3D picture, else its mark,
// else the lower left), coming near from far, flies a loose S over the
// town of Ebino, nose to its way, banking into its turns and its nose up a
// little before it lands, with a thin trail that fades at once; the seats'
// points under it light as it passes (going to meet the town's people).
// It slows and lands where the round table opens; the lamp's light spreads
// once in a ring, the points not yet lit lighting nearest first, and the title
// comes and goes up toward the question box. Under 3 seconds; 「とばす」,
// Enter or Esc ends it at once. No flashing, the screen never shakes.
const OPENING = { fly: 1400, land: 600, title: 800 };
// Before it (直し30の続き-3): the Lab's board becomes one sheet of paper, the
// words fading; the sheet folds into the plane (in half down the middle,
// the two top corners to the middle, the wings opened); the map comes up
// behind and the plane goes off far, small, to the school, turns there and
// flies the opening as above. In all 4.5 seconds at most.
const FOLD = { paper: 300, fold: 900, away: 500 };
let openingRun = null;

// Starts it and returns a promise kept when it has ended (or at once, with
// no map on screen to fly over: then null).
function playOpening() {
  if (typeof EbinoMap === "undefined" || $("map").hidden) return null;
  const run = { trail: [], last: null, lean: 0, frame: 0, points: [], sheet: foldSheet($("start").getBoundingClientRect()) };
  if (run.sheet) {
    $("fold-skip").textContent = state.texts.opening_skip;
    $("fold").hidden = false;
  } else if (!mapStage(run)) return null;
  openingRun = run;
  return new Promise((done) => {
    run.done = done;
    const began = performance.now();
    const step = (now) => {
      if (openingRun !== run) return;
      let t = now - began;
      if (run.sheet) {
        if (t < FOLD.paper + FOLD.fold) {
          // The window turned or resized while folding: the board measured again.
          if (run.sheet.vw !== window.innerWidth || run.sheet.vh !== window.innerHeight) {
            run.sheet = foldSheet($("start").getBoundingClientRect()) || run.sheet;
          }
          drawFold(run, t);
          run.frame = requestAnimationFrame(step);
          return;
        }
        if (!run.w && !mapStage(run)) return finishOpening(run);
        t -= FOLD.paper + FOLD.fold;
      }
      drawOpening(run, t);
      if (t >= (run.away ? FOLD.away : 0) + OPENING.fly + OPENING.land + OPENING.title) return finishOpening(run);
      run.frame = requestAnimationFrame(step);
    };
    run.keys = (event) => {
      if (event.key === "Enter" || event.key === "Escape") {
        event.preventDefault();
        finishOpening(run);
      }
    };
    document.addEventListener("keydown", run.keys);
    $("opening-skip").onclick = () => finishOpening(run);
    $("fold-skip").onclick = () => finishOpening(run);
    $(run.sheet ? "fold-skip" : "opening-skip").focus();
    run.frame = requestAnimationFrame(step);
  });
}

// The map's part: the table screen up with the map alone, the way worked out
// on the spot (false: no map on screen after all).
function mapStage(run) {
  $("start").hidden = true;
  $("table").hidden = false;
  $("table").classList.add("opening-on");
  onMap((map) => map.show());
  const frame = $("map-frame");
  const box = frame.getBoundingClientRect();
  if (!box.width || !box.height || $("map").hidden) {
    $("table").classList.remove("opening-on");
    return false;
  }
  $("map").scrollIntoView({ block: "nearest" });
  const w = box.width, h = box.height;
  const end = [w / 2, h / 2];
  // From the roof of the school's 3D picture when it is on the map in sight
  // (直し30の続き-2); else from its mark; else the lower left. With no
  // picture (none given, unread, or the school said no) the same opening.
  let from = [Math.min(48, w * 0.08), h - Math.min(48, h * 0.08)];
  const sighted = (selector, high) => {
    const node = document.querySelector(selector);
    if (!node) return null;
    const s = node.getBoundingClientRect();
    const at = [s.left + s.width / 2 - box.left, s.top + s.height * high - box.top];
    return s.width && at[0] > 0 && at[0] < w && at[1] > 0 && at[1] < h ? at : null;
  };
  from = sighted("#map-svg .school-picture image", 0.3) || sighted("#map-svg .school > :not(text)", 0.5) || from;
  const points = [...document.querySelectorAll("#map-svg .pt")].map((node) => {
    const p = node.getBoundingClientRect();
    const x = p.left + p.width / 2 - box.left, y = p.top + p.height / 2 - box.top;
    return { node, x, y, d: Math.hypot(x - end[0], y - end[1]), lit: false };
  });
  const far = Math.max(1, ...points.map((p) => p.d));
  for (const p of points) p.node.style.opacity = ".2";
  $("opening-title").textContent = document.querySelector(".masthead h1").textContent;
  $("opening-skip").textContent = state.texts.opening_skip;
  $("opening").hidden = false;
  $("opening-bar").hidden = false;
  $("map-frame").inert = true;  // The keyboard goes to 「とばす」, not the points behind.
  // At its nearest it is 10% of the map's width (64px at least): 8% or more.
  Object.assign(run, { from, end, w, h, points, far, ring: Math.hypot(w, h) * 0.42,
    size: Math.max(64, w * 0.1), reach: Math.max(28, Math.min(w, h) * 0.07) });
  // The town: where the seats' points are, the middle of them.
  if (points.length) run.town = [points.reduce((t, p) => t + p.x, 0) / points.length, points.reduce((t, p) => t + p.y, 0) / points.length];
  if (run.sheet) {
    // The folded plane, where it is on the screen, goes on over the map.
    const m = run.size * 0.7, [x, y] = run.sheet.plane;
    run.away = { x: Math.max(m, Math.min(w - m, x - box.left)), y: Math.max(m, Math.min(h - m, y - box.top)), size: run.sheet.size };
    $("fold").hidden = true;
    if (document.activeElement === $("fold-skip")) $("opening-skip").focus();
  }
  return true;
}

// The Lab's board as one sheet on the screen (null: not on screen to fold).
function foldSheet(board) {
  const T = Math.max(0, board.top), B = Math.min(window.innerHeight, board.bottom);
  if (board.width < 80 || B - T < 80) return null;
  const L = board.left, R = board.right, cx = (L + R) / 2;
  const size = Math.min(B - T, R - L) * 0.5;
  return { L, R, T, B, cx, size, plane: [cx, (T + B) / 2], vw: window.innerWidth, vh: window.innerHeight };
}

// The fold as it is t ms in: the words fading over the cream sheet; folded
// in half and opened again (a crease down the middle); the two top corners
// to the middle (a long triangle); the triangle's six faces taking the
// plane's shape, the wings coming in to the middle and opening.
function drawFold(run, t) {
  const { L, R, T, B, cx, size, plane } = run.sheet;
  const clamp = (x) => Math.max(0, Math.min(1, x)), ease = (x) => x * x * (3 - 2 * x);
  const paper = clamp(t / FOLD.paper), k = clamp((t - FOLD.paper) / FOLD.fold);
  const half = ease(clamp(k / 0.3)), corner = ease(clamp((k - 0.3) / 0.3)), wing = ease(clamp((k - 0.6) / 0.4));
  $("start").style.opacity = String(1 - paper);
  const sheet = $("fold-sheet"), faces = [...$("fold-plane").children];
  const line = (pts) => pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const mix = (a, b, u) => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
  if (k < 0.6) {
    const over = Math.sin(Math.PI * half) * 0.92;  // The left half laid over the right, and back.
    const l = L + (cx - L) * over, nose = [cx, T];
    const tl = mix([l, T], mix(nose, [l, B], 0.35), corner), tr = mix([R, T], mix(nose, [R, B], 0.35), corner);
    sheet.setAttribute("points", line([tl, nose, tr, [R, B], [l, B]]));
    sheet.style.fillOpacity = String(paper);
    sheet.style.strokeOpacity = String(paper);
    for (const node of faces) node.setAttribute("points", "");
    return;
  }
  sheet.setAttribute("points", "");
  const flat = { nose: [cx, T], keel: [cx, B], tl: [cx - 1, B], tr: [cx + 1, B], ml: [(L + cx) / 2, B], mr: [(R + cx) / 2, B],
    wl: [L, B], wr: [R, B] };
  const shaped = planeFaces({ x: plane[0], y: plane[1], size, a: -Math.PI / 2, roll: 0, pitch: 0 });
  const at = {};
  for (const face of shaped) face.names.forEach((name, i) => { at[name] = face.points[i]; });
  const pull = Math.sin(Math.PI * wing) * 0.6;  // The wings in to the middle on the way, then opened.
  const middle = plane[0] + (cx - plane[0]) * (1 - wing);
  shaped.forEach((face, i) => {
    faces[i].setAttribute("points", line(face.names.map((name) => {
      const [x, y] = mix(flat[name], at[name], wing);
      return [x - (x - middle) * pull, y];
    })));
    faces[i].style.filter = `brightness(${(1 + (face.light - 1) * wing).toFixed(3)})`;
  });
}

// From where it was folded, off far (smaller) to the school, turning there.
function drawAway(run, t) {
  const u = Math.min(1, t / FOLD.away), e = u * u * (3 - 2 * u);
  const a = [run.away.x, run.away.y], b = run.from;
  const c = [(a[0] + b[0]) / 2, Math.max(run.size * 0.7, Math.min(a[1], b[1]) - run.h * 0.12)];
  const v = 1 - e;
  const x = v * v * a[0] + 2 * v * e * c[0] + e * e * b[0], y = v * v * a[1] + 2 * v * e * c[1] + e * e * b[1];
  const dir = Math.atan2(2 * v * (c[1] - a[1]) + 2 * e * (b[1] - c[1]), 2 * v * (c[0] - a[0]) + 2 * e * (b[0] - c[0]));
  const size = run.away.size + (run.size * 0.32 - run.away.size) * e;
  const faces = planeFaces({ x, y, size, a: dir, roll: 0, pitch: 0 });
  [...$("opening-plane").children].forEach((node, i) => {
    node.setAttribute("points", faces[i].points.map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`).join(" "));
    node.style.filter = `brightness(${faces[i].light.toFixed(3)})`;
  });
}

// Where the plane is at u (0 to 1) of its flight: a cubic curve bent one
// way then the other, a loose S from (from) to (end).
function planeAt(run, u) {
  const [x0, y0] = run.from, [x3, y3] = run.end;
  const dx = x3 - x0, dy = y3 - y0, len = Math.hypot(dx, dy) || 1;
  // The swing is wide even when the school is near the middle; the bends
  // stay in the frame (the curve keeps inside its four points).
  const swing = Math.max(len * 0.28, Math.min(run.w || 0, run.h || 0) * 0.22);
  const nx = -dy / len * swing, ny = dx / len * swing;
  // Kept off the frame's edge by the plane's own reach, so no wing goes out.
  const m = Math.max(24, (run.size || 0) * 0.7);
  const keep = (x, y) => (run.w ? [Math.max(m, Math.min(run.w - m, x)), Math.max(m, Math.min(run.h - m, y))] : [x, y]);
  let c1 = keep(x0 + dx / 3 + nx, y0 + dy / 3 + ny), c2 = keep(x0 + dx * 2 / 3 - nx, y0 + dy * 2 / 3 - ny);
  // Over the town (直し30の続き-2): out past the middle of the seats' points
  // and back over them, bending one way then the other, to the table's spot.
  if (run.town) {
    const [tx, ty] = run.town, ox = tx - x3, oy = ty - y3, out = Math.hypot(ox, oy);
    const far = Math.max(swing * 2.4, out * 2.6), ux = out > 1 ? ox / out : dy / len, uy = out > 1 ? oy / out : -dx / len;
    c1 = keep(x3 + ux * far + uy * swing * 0.8, y3 + uy * far - ux * swing * 0.8);
    c2 = keep(x3 + ux * far * 0.3 - uy * swing * 1.5, y3 + uy * far * 0.3 + ux * swing * 1.5);
  }
  const v = 1 - u;
  const at = (a, b, c, d) => v * v * v * a + 3 * v * v * u * b + 3 * v * u * u * c + u * u * u * d;
  const slope = (a, b, c, d) => 3 * v * v * (b - a) + 6 * v * u * (c - b) + 3 * u * u * (d - c);
  return { x: at(x0, c1[0], c2[0], x3), y: at(y0, c1[1], c2[1], y3),
    a: Math.atan2(slope(y0, c1[1], c2[1], y3), slope(x0, c1[0], c2[0], x3)) };
}

// The paper plane (直し30の続き-1): a sheet folded in half down the middle,
// its two sides folded down into wings, opened. x to the nose, y to the
// right wing, z up; its length is 1. Six triangles: the keel's two sides,
// and each wing in two, so every fold shows.
const PLANE = {
  points: { nose: [0.62, 0, 0], tl: [-0.38, -0.03, 0], tr: [-0.38, 0.03, 0], keel: [-0.38, 0, -0.2],
    ml: [-0.38, -0.16, 0.025], mr: [-0.38, 0.16, 0.025], wl: [-0.38, -0.32, 0.1], wr: [-0.38, 0.32, 0.1] },
  faces: [["nose", "tl", "keel"], ["nose", "tr", "keel"], ["nose", "tl", "ml"], ["nose", "tr", "mr"],
    ["nose", "ml", "wl"], ["nose", "mr", "wr"]],
};
// The lamp's light, from the upper left and in front.
const PLANE_LIGHT = [-0.36, -0.5, 0.79];

// The plane's six faces on the screen, far ones first: at (x, y), size px
// long, nose to a (radians, on the screen), banked by roll and its nose up
// by pitch. Seen from above and from the south, as the map is, the near
// side a little bigger; each face as bright as it turns to the lamp (both
// sides are paper).
function planeFaces(pose) {
  const { x, y, size, a, roll, pitch } = pose;
  const cp = Math.cos(pitch), sp = Math.sin(pitch), cr = Math.cos(roll), sr = Math.sin(roll);
  const ca = Math.cos(a), sa = Math.sin(a);
  const turned = {};
  for (const [name, [px, py, pz]] of Object.entries(PLANE.points)) {
    const x1 = px * cp - pz * sp, z1 = px * sp + pz * cp;
    const y2 = py * cr - z1 * sr, z2 = py * sr + z1 * cr;
    turned[name] = [x1 * ca - y2 * sa, x1 * sa + y2 * ca, z2];
  }
  const faces = PLANE.faces.map((names) => {
    const [p, q, r] = names.map((name) => turned[name]);
    const u = [q[0] - p[0], q[1] - p[1], q[2] - p[2]], v = [r[0] - p[0], r[1] - p[1], r[2] - p[2]];
    const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const cos = Math.abs(n[0] * PLANE_LIGHT[0] + n[1] * PLANE_LIGHT[1] + n[2] * PLANE_LIGHT[2]) / (Math.hypot(...n) || 1);
    return {
      names,
      points: names.map((name) => {
        const [X, Y, Z] = turned[name], k = 1 / (1 - 0.3 * (Y * 0.7 + Z * 0.7));
        return [x + X * size * k, y + (Y * 0.7 - Z * 0.7) * size * k];
      }),
      depth: (p[1] + q[1] + r[1]) * 0.7 + (p[2] + q[2] + r[2]) * 0.7,
      light: 0.42 + 0.58 * cos,
    };
  });
  return faces.sort((f, g) => f.depth - g.depth);
}

// The seats' points the plane is passing over light, once each.
function lightNear(run, x, y) {
  for (const point of run.points) {
    if (!point.lit && Math.hypot(point.x - x, point.y - y) <= run.reach) {
      point.lit = true;
      point.node.style.opacity = "";
    }
  }
}

// The opening as it is t ms in (after the fold, its way to the school first).
function drawOpening(run, t) {
  if (run.away) {
    if (t < FOLD.away) return drawAway(run, t);
    t -= FOLD.away;
  }
  const plane = $("opening-plane"), trail = $("opening-trail"), ring = $("opening-ring"), title = $("opening-title");
  const fly = Math.min(1, t / OPENING.fly);
  // Slowing down to land: fast at first, the last stretch gently.
  const u = 1 - Math.pow(1 - fly, 2.2);
  const p = planeAt(run, u);
  if (run.last !== null) {
    let turn = p.a - run.last;
    turn = Math.atan2(Math.sin(turn), Math.cos(turn));
    run.lean += (Math.max(-0.6, Math.min(0.6, turn * 14)) - run.lean) * 0.25;
  }
  run.last = p.a;
  // From far to near (small to its full size), settled before it lands;
  // banked into the turn (the inner wing down); the nose up a little at the end.
  const near = Math.min(1, fly / 0.8);
  const size = run.size * (0.32 + 0.68 * (1 - Math.pow(1 - near, 2)));
  const pitch = 0.32 * Math.max(0, Math.min(1, (fly - 0.78) / 0.22));
  const faces = planeFaces({ x: p.x, y: p.y, size, a: p.a, roll: -run.lean, pitch });
  [...plane.children].forEach((node, i) => {
    node.setAttribute("points", faces[i].points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "));
    node.style.filter = `brightness(${faces[i].light.toFixed(3)})`;
  });
  if (fly < 1) lightNear(run, p.x, p.y);
  // Gone before the title comes, so it never lies over it.
  plane.style.opacity = String(Math.max(0, Math.min(1, (OPENING.fly + OPENING.land - t) / (OPENING.land * 0.5))));
  // The trail: the last quarter second of the way only, so it fades at once.
  run.trail.push([t, p.x, p.y]);
  while (run.trail.length && t - run.trail[0][0] > 240) run.trail.shift();
  trail.setAttribute("points", fly < 1 ? run.trail.map(([, x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ") : "");
  // Landed: the lamp's light spreads once in a ring; the points light from the nearest.
  const lit = (t - OPENING.fly) / OPENING.land;
  if (lit > 0) {
    const k = Math.min(1, lit);
    ring.setAttribute("cx", run.end[0].toFixed(1));
    ring.setAttribute("cy", run.end[1].toFixed(1));
    ring.setAttribute("r", (8 + (run.ring - 8) * (1 - Math.pow(1 - k, 2))).toFixed(1));
    ring.style.opacity = String(0.85 * (1 - k));
    for (const point of run.points) {
      if (!point.lit && point.d / run.far <= k) {
        point.lit = true;
        point.node.style.opacity = "";
      }
    }
  }
  // The title: comes, stays a moment, and goes up toward the question box.
  const shown = (t - OPENING.fly - OPENING.land) / OPENING.title;
  if (shown > 0) {
    const come = Math.min(1, shown / 0.3), go = Math.max(0, (shown - 0.6) / 0.4);
    title.style.opacity = String(Math.min(come, 1 - go));
    title.style.transform = `translate(-50%, calc(-50% - ${(go * 48).toFixed(1)}px))`;
  }
}

function finishOpening(run) {
  if (openingRun !== run || run.ended) return;
  run.ended = true;
  cancelAnimationFrame(run.frame);
  document.removeEventListener("keydown", run.keys);
  // Its last form: the map as the table screen shows it, until /api/start is in.
  for (const point of run.points) point.node.style.opacity = "";
  for (const id of ["opening-svg", "opening-title"]) $(id).style.visibility = "hidden";
  $("opening-bar").hidden = true;
  $("fold").hidden = true;
  $("start").style.opacity = "";
  run.done();
}

// Taken away once /api/start is in (back: it failed, the Lab buttons again).
function endOpening(back) {
  const run = openingRun;
  if (run) finishOpening(run);
  openingRun = null;
  $("opening").hidden = true;
  for (const id of ["opening-svg", "opening-title"]) $(id).style.visibility = "";
  $("opening-bar").hidden = true;
  $("opening-trail").setAttribute("points", "");
  $("opening-ring").setAttribute("r", "0");
  $("opening-title").style.opacity = "0";
  $("table").classList.remove("opening-on");
  $("map-frame").inert = false;
  if (back) {
    $("table").hidden = true;
    $("start").hidden = false;
  }
}

// Buttons only put words in the box; the student sends them (SPEC 14-11).
function fill(text) {
  $("question").value = text;
  $("question").focus();
}

// --- 「いまやること」 (直し31-5) ---

// The one state the screen is in, from the first that holds.
function nowState() {
  const now = state.now;
  if (!$("start").hidden) return "start";
  if (!$("reflect").hidden) return "reflect";
  if (now.asking) return "asking";
  if (!state.firstQuestion) return "write";
  if (now.reading) return "reading";
  if (cardOpen()) return "card";
  if (state.to.kind === "ai") return "answer_ai";
  if (now.choices) return "pressed";
  if (now.table && !now.pressed) return "table";
  if (!state.aiAnswered && now.band) return "answer_ai";
  return "after";
}

// The box writes to one seat (直し31続き-3; the one box, 直し32-2).
function cardOpen() {
  return state.to.kind === "seat";
}

// The band's step for this state lit (by its words and a mark, not its
// colour alone), and the one line under it. changes: flags to set first.
function setNow(changes = {}) {
  Object.assign(state.now, changes);
  const lines = state.texts.now_line;
  if (!lines) return;
  const line = lines[nowState()];
  for (const step of $("now-steps").children) {
    const lit = step.dataset.step === line.step;
    step.classList.toggle("lit", lit);
    if (lit) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
  }
  if ($("now-line").textContent !== line.text) $("now-line").textContent = line.text;
  keepUnderNow();
}

// Whatever the page scrolls to stops under the band, not behind it.
function keepUnderNow() {
  document.documentElement.style.setProperty("--now-h", `${Math.ceil($("now").getBoundingClientRect().height) + 8}px`);
}

// Over the first question box: whose words are in the app, as counts from
// the seat table, each with the mark its seats have on the map; then
// examples of questions, to read only (the box is never filled from them).
function renderInside(rows) {
  $("inside-open").textContent = state.texts.inside_open;
  $("inside-heading").textContent = state.texts.inside_heading;
  for (const row of rows) {
    const mark = typeof EbinoMap !== "undefined" ? EbinoMap.markOf(row.kind) : null;
    $("inside-counts").append(el("li", { class: `kind-${row.kind}` },
      el("span", { class: "mark", "aria-hidden": "true" }, mark),
      el("span", { class: "label", text: row.before }),
      el("span", { class: "count" }, el("span", { class: "number", text: String(row.number) }),
        el("span", { class: "unit", text: row.after }))));
  }
  $("inside-end").textContent = state.texts.inside_end;
  $("examples-lead").textContent = state.texts.question_examples_lead;
  for (const text of state.texts.question_examples) $("examples").append(el("li", { text }));
  $("examples-end").textContent = state.texts.question_examples_end;
}

// --- the drawer (直し32-1) ---

// On the right of the one screen, only when opened: one part at a time (the
// paragraph, the rounds so far, the seat list, the seniors' questions).
// 閉じる or Esc closes it, and the keyboard goes back where it came from.
// With no map the parts are the page's, one under the other, as before.
const drawer = { from: null };

function setupDrawer() {
  const parts = state.texts.drawer_parts;
  $("drawer-close").textContent = state.texts.bubble_close;
  for (const part of ["rounds", "seats", "purposes"]) {
    $("drawer-buttons").append(el("button", { type: "button", class: "drawer-button", "data-part": part,
      "aria-expanded": "false", "aria-controls": "drawer", text: parts[part],
      onclick: (event) => toggleDrawer(part, event.currentTarget) }));
  }
  $("drawer-close").addEventListener("click", () => closeDrawer());
  // The card of whose words are in, opened or folded, moves the map too.
  $("inside-fold").addEventListener("toggle", mapMoved);
  $("drawer").addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !drawerOpen()) return;
    event.preventDefault();
    event.stopPropagation();
    closeDrawer();
  });
}

// The one screen is on: the table is out and the map with it.
function oneScreen() {
  return !$("table").hidden && !$("map").hidden;
}

// The map stands somewhere else now: its cards are laid out again, once the
// page has its new shape.
function mapMoved() {
  requestAnimationFrame(() => onMap((map) => map.layoutAgain()));
}

function drawerOpen() {
  return $("drawer").classList.contains("open");
}

// Opens the drawer at a part (the same part again: closes it). from: what
// the keyboard goes back to when it closes.
function toggleDrawer(part, from) {
  if (drawerOpen() && $("drawer").dataset.part === part) return closeDrawer();
  openDrawer(part, from);
}

// focus: the keyboard goes into the drawer, to its title (so Esc closes it
// from there); false when the caller puts it on something inside.
function openDrawer(part, from = document.activeElement, { focus = true } = {}) {
  if (!oneScreen()) return;
  const box = $("drawer");
  if (!drawerOpen()) drawer.from = from;
  box.dataset.part = part;
  box.classList.add("open");
  $("drawer-title").textContent = state.texts.drawer_parts[part];
  for (const button of $("drawer-buttons").children) {
    button.setAttribute("aria-expanded", String(button.dataset.part === part));
  }
  box.querySelector(".drawer-body").scrollTop = 0;
  mapMoved();
  if (focus) $("drawer-title").focus({ preventScroll: true });
}

function closeDrawer() {
  const box = $("drawer");
  if (!drawerOpen()) return;
  box.classList.remove("open");
  for (const button of $("drawer-buttons").children) button.setAttribute("aria-expanded", "false");
  mapMoved();
  const back = drawer.from;
  drawer.from = null;
  const inside = box.contains(document.activeElement);
  // Back where it came from; that gone (or never kept) while the keyboard
  // was in the drawer, to the box at the foot rather than to nowhere.
  if (back && back.isConnected && back.offsetParent !== null) back.focus({ preventScroll: true });
  else if (inside || document.activeElement === document.body) $("question").focus({ preventScroll: true });
}

// --- purposes ---

function renderPurposes(purposes) {
  const list = $("purpose-list");
  list.replaceChildren();
  for (const sample of purposes) {
    // A long sample is shown as its summary, marked so it never reads as
    // the senior's own words.
    list.append(el("li", {},
      sample.summarized ? el("span", { class: "summarized", text: state.texts.sample_summarized }) : null,
      el("p", { class: "words", text: sample.texts.join("") }),
      el("span", { class: "source", text: sourceLine(sample.source) })));
  }
  $("purposes").hidden = purposes.length === 0;
}

// --- the one box at the foot (直し32-2) ---

// Whom it writes to, in words: the label on its left, its button's word,
// how long it may be, and the example only when it is everyone.
function seatName(seatId) {
  const seat = state.seatById[seatId];
  return seat ? [seat.title, seat.detail].filter(Boolean).join("　") : "";
}

function draftKey(to) {
  return to.kind === "seat" ? `seat:${to.seatId}` : to.kind === "ai" ? `ai:${to.roundNo}:${to.role}` : "all";
}

function setTo(next, { focus = true } = {}) {
  const box = $("question");
  if (state.to) state.drafts[draftKey(state.to)] = box.value;
  state.to = next;
  const words = state.texts.input_to;
  const label = next.kind === "seat" ? words.seat.replace("{seat}", seatName(next.seatId)) : words[next.kind];
  $("input-to-label").textContent = label;
  $("question-label").textContent = label;
  const clear = $("input-to-clear");
  clear.hidden = next.kind === "all";
  clear.setAttribute("aria-label", words.clear);
  clear.title = words.clear;
  $("ask-button").textContent = state.texts.input_send[next.kind];
  $("ask-form").dataset.to = next.kind;
  box.maxLength = next.kind === "ai" ? 120 : 200;
  box.placeholder = next.kind === "all" ? "例：" + state.texts.input_example : "";
  box.value = state.drafts[draftKey(next)] || "";
  if (next.kind !== "ai") for (const button of document.querySelectorAll(".ai-question.chosen")) button.classList.remove("chosen");
  setNow();
  if (focus) box.focus({ preventScroll: true });
}

// 「この人に聞きたいことを書く」, a 「？」, the seat list: the box writes to
// that seat, the keyboard in it at once.
// While a send is out the box keeps whom it writes to: what comes back
// clears the words that went, never another's.
function sending() {
  return $("ask-button").disabled;
}

function askSeat(seatId) {
  if (sending()) return;
  hideDone();
  setTo({ kind: "seat", seatId });
}

// 「答える」 on an AI's question: the box answers it.
function answerTo(roundNo, role) {
  if (sending()) return;
  hideDone();
  setTo({ kind: "ai", roundNo, role });
}

function backToEveryone() {
  if (!sending() && state.to.kind !== "all") setTo({ kind: "all" });
}

function showDone(text) { $("input-done").textContent = text; $("input-done").hidden = false; }
function hideDone() { $("input-done").hidden = true; }

// One press sends once: the button waits while it is sent (直し31-2).
async function send(event) {
  event.preventDefault();
  const button = $("ask-button");
  if (button.disabled || !$("question").value.trim()) return;
  hideDone();
  if (state.to.kind === "seat") return sendCard(state.to.seatId);
  if (state.to.kind === "ai") return sendAnswer(state.to.roundNo, state.to.role);
  return ask();
}

// To one seat: a question card (/api/card), the student's words only. The
// same words to the same seat again: the card there is (直し31-2).
async function sendCard(seatId) {
  const button = $("ask-button");
  const text = $("question").value.trim();
  button.disabled = true;
  hideMessage();
  let card;
  try {
    card = await call("/api/card", { seat_id: seatId, text });
  } catch (error) {
    showMessage(sendFailed(error));
    return;
  } finally {
    button.disabled = false;
  }
  state.carded.add(seatId);
  if (card.again) state.cardAgain[seatId] = card.text;
  $("question").value = "";
  delete state.drafts[`seat:${seatId}`];
  // Every 「聞きたいことを書く」 of that seat says its card is made.
  for (const open of document.querySelectorAll("button[data-card-seat]")) {
    if (open.dataset.cardSeat === seatId) open.replaceWith(cardDone(seatId, open.dataset.doneTag || "div"));
  }
  setTo({ kind: "all" });
  showDone(card.again ? state.texts.card_already.replace("{card}", card.text)
    : state.texts.input_done.seat.replace("{seat}", seatName(seatId)));
  renderSeats();  // The seat marked on the map too (map.refresh).
}

// To an AI's question: the answer starts the next round (直し29-1).
async function sendAnswer(roundNo, role) {
  const button = $("ask-button");
  const answer = $("question").value.trim();
  button.disabled = true;
  hideMessage();
  setNow({ asking: true });
  try {
    const round = await call("/api/coach_answer", { round: roundNo, role, answer, after_notice: state.needsShown });
    setNow({ asking: false });
    if (round.status === "unavailable") state.aiUnavailable = true;
    if (round.status === "ask_again" || round.status === "unavailable") {
      showMessage(round.message);  // The answer stays in the box to be changed.
      return;
    }
    hideMessage();
    state.aiAnswered = true;
    $("reflect-needs-answer").hidden = true;
    for (const node of document.querySelectorAll(".needs-answer")) node.classList.remove("needs-answer");
    bandAnswered(roundNo, role);
    $("question").value = "";
    delete state.drafts[`ai:${roundNo}:${role}`];
    setTo({ kind: "all" });
    showDone(state.texts.input_done.ai);
    renderRound(round);
  } catch (error) {
    setNow({ asking: false });
    showMessage(sendFailed(error));
  } finally {
    button.disabled = false;
  }
}

// --- asking ---

async function ask() {
  const question = $("question").value.trim();
  if (!question) return;
  const button = $("ask-button");
  button.disabled = true;
  // The waiting line is the one at the top now (直し31-5).
  hideMessage();
  setNow({ asking: true });
  try {
    const round = await call("/api/ask", { question });
    setNow({ asking: false });
    // The counts and examples fold once a question is sent; they open again.
    $("inside-fold").open = false;
    if (round.status === "ask_again" || round.status === "unavailable") {
      showMessage(round.message);  // The question stays in the box to be changed.
      return;
    }
    $("question").value = "";
    delete state.drafts.all;
    renderRound(round);
  } catch (error) {
    showMessage(sendFailed(error));
  } finally {
    button.disabled = false;
    setNow({ asking: false });
  }
}

function sendFailed(error) { return state.texts.send_failed.replace("{error}", error.message); }
function showMessage(text) { $("ask-message").textContent = text; $("ask-message").hidden = false; }
function hideMessage() { $("ask-message").hidden = true; }

function renderRound(round) {
  if (!state.firstQuestion) state.firstQuestion = round.question;
  // A new round: its seats light (map.js says when they are done).
  setNow({ reading: false, choices: false, pressed: false, table: false, band: false });
  $("to-reflect").hidden = false;
  state.lastOrder = round.seat_order;
  for (const id of round.met_seats) state.met.add(id);
  for (const id of round.silent_seats) state.silent.add(id);

  state.lastRound = round.round;
  // The AI's seat keeps the questions it has (the one answered marked) until
  // this round's come (renderAiSeat): it never goes blank meanwhile.
  // The first round with spoken words says once what they are (直し31-7).
  const spokenNote = $("spoken-note");
  if (round.quotes.some((quote) => quote.spoken) && !state.spokenNoted) {
    state.spokenNoted = round.round;
    spokenNote.textContent = state.texts.spoken_note;
    spokenNote.hidden = false;
  } else if (state.spokenNoted && state.spokenNoted !== round.round) {
    spokenNote.hidden = true;
  }
  const box = el("article", { class: "round", "data-round": round.round });
  // A round that answers an AI's question shows that question over the answer.
  if (round.ai_question) {
    box.append(el("p", { class: "ai-asked" },
      el("span", { class: "label", text: round.ai_question.label }),
      el("span", { text: round.ai_question.text })));
  }
  box.append(el("p", { class: "round-question", text: round.question }));
  box.append(el("p", { class: "steps",
    text: `司書が見つけた片：${round.steps.found}　番人が通した引用：${round.steps.passed}　止めた引用：${round.steps.stopped}` }));
  box.append(el("p", { class: "count", text: state.texts.answered_count.replace("{n}", round.answered_seats) }));

  const byId = {};
  for (const quote of round.quotes) byId[quote.utterance_id] = quote;
  // A split's two sides stand side by side, each its seats' titles over its
  // quotes as paper cards (one under the other on a narrow screen). A quote
  // goes under the first split that holds it; the others stand apart above.
  const placed = new Set();
  const take = (ids) => ids.filter((id) => byId[id] && !placed.has(id) && placed.add(id)).map((id) => byId[id]);
  const sides = round.splits.map((split) => [take(split.side_a), take(split.side_b)]);
  const loose = el("div", { class: "cards" });
  const planted = round.planted_stopped.map(renderPlanted);
  round.quotes.filter((quote) => !placed.has(quote.utterance_id)).forEach((quote, index) => {
    loose.append(renderQuote(round.round, quote));
    if (index === 0) loose.append(...planted.splice(0));
  });
  box.append(...planted, loose);
  round.splits.forEach((split, index) => box.append(renderSplit(round.round, split, byId, sides[index])));
  if (round.card) box.append(el("p", { class: "card-done", text: "この問いを質問カードにしました" }));
  $("rounds").prepend(box);
  // The keyboard goes on from the new round's question, not through the
  // map's points before it (直し25-5); the page does not jump for it.
  const asked = box.querySelector(".round-question");
  asked.tabIndex = -1;
  if (!oneScreen()) asked.focus({ preventScroll: true });
  renderSeats();
  onMap((map) => map.round(round));  // The quoted seats light up on the map, in order.
  if (round.status === "answered") {
    // 「司会が○○に聞いてみる」 comes before the last word (SPEC 14-53 B).
    const askBox = el("div", { class: "ask-seat-box" });
    const closingBox = el("div");
    box.append(askBox, closingBox);
    state.askBoxes[round.round] = askBox;
    loadAskCard(round.round, askBox);
    closeRound(round.round, closingBox);
  }
  if (round.status === "answered" || round.status === "silent") {
    // コーチとオブザーバー: last in the round, apart from the seats' words.
    const bandBox = el("div");
    box.append(bandBox);
    loadBand(round.round, bandBox);
  }
}

// コーチとオブザーバー (SPEC 5-1): two AI questions in a fixed order, the same
// size. Pressing one opens an empty one-line box; the answer starts the next
// round. Not answering is fine: nothing waits on it.
async function loadBand(roundNo, box) {
  let band;
  try {
    band = await call("/api/coach", { round: roundNo });
  } catch (error) {
    return;  // An extra at the round's end.
  }
  if (!band.cards.length) return;
  const part = el("section", { class: "ai-band" });
  // The line asking for one answer is the one at the top (直し31-5), not
  // over the cards as well (直し30の続き-0): said once, in one place.
  if (!band.answered && roundNo === state.lastRound) setNow({ band: true });
  for (const card of band.cards) {
    const node = el("div", { class: "ai-card" },
      el("p", { class: "label", text: card.label }),
      el("p", { class: "badge", text: card.badge }),
      el("p", { class: "words", text: card.question }));
    node.dataset.role = card.role;
    if (!band.answered) node.append(answerEntry(roundNo, card.role));
    else if (band.answered === card.role) node.classList.add("answered");
    part.append(node);
  }
  box.append(part);
  state.bands[roundNo] = part;
  // The newest round's questions at the AI's seat (直し32-3), not at the table.
  if (roundNo === state.lastRound) renderAiSeat(roundNo, band);
}

// --- the AI's seat (直し32-3) ---

// コーチ and オブザーバー, out of the round table's ring: a rounded square in
// the AI's blue with 「AI」 on it, its name, and the newest round's two
// questions. Pressed, the box at the foot answers that one. The first time
// there are questions, one line says they are the AI's, not the map's
// people's; after that the name only.
function renderAiSeat(roundNo, band) {
  const seat = $("ai-seat");
  $("ai-seat-mark").textContent = state.texts.ai_seat_mark;
  $("ai-seat-label").textContent = state.texts.ai_seat_label;
  const note = $("ai-seat-note");
  if (!state.aiNoted) {
    state.aiNoted = roundNo;
    note.textContent = state.texts.ai_seat_note;
  }
  note.hidden = state.aiNoted !== roundNo;
  const cards = $("ai-seat-cards");
  cards.replaceChildren();
  for (const card of band.cards) {
    const button = el("button", { type: "button", class: "ai-question", "data-role": card.role, "data-round": roundNo },
      el("span", { class: "who", text: card.label }), el("span", { class: "words", text: card.question }));
    button.addEventListener("click", () => {
      answerTo(roundNo, card.role);
      markAiChosen(card.role);
    });
    if (band.answered) {
      button.disabled = true;
      if (band.answered === card.role) button.classList.add("answered");
    }
    cards.append(button);
  }
  seat.hidden = false;
  mapMoved();  // The map's cards keep off it.
}

// The question the box at the foot answers, lit; the box back to everyone, none.
function markAiChosen(role) {
  for (const button of $("ai-seat-cards").children) {
    button.classList.toggle("chosen", state.to.kind === "ai" && button.dataset.role === role);
  }
}

function answerEntry(roundNo, role) {
  return el("button", { type: "button", class: "quiet", text: state.texts.bubble_answer,
    onclick: () => answerTo(roundNo, role) });
}

// One answer per band: the other card's 「答える」 goes away and the card
// answered is marked, wherever the answer was written.
function bandAnswered(roundNo, role) {
  for (const button of document.querySelectorAll(`#ai-seat-cards .ai-question[data-round="${roundNo}"]`)) {
    button.disabled = true;
    button.classList.toggle("answered", button.dataset.role === role);
  }
  const part = state.bands[roundNo];
  if (!part) return;
  for (const card of part.querySelectorAll(".ai-card")) {
    for (const button of card.querySelectorAll(":scope > button")) button.remove();
    if (card.dataset.role === role) card.classList.add("answered");
    else for (const form of card.querySelectorAll(":scope > form")) form.remove();
  }
}

// 「司会が○○に聞いてみる」 (SPEC 14-53 B): a card with one question to one
// seat. Nothing is asked until the student presses it; once per round.
async function loadAskCard(roundNo, box) {
  let data;
  try {
    data = await call("/api/ask_card", { round: roundNo });
  } catch (error) {
    return;
  }
  if (data.asked) { renderAsked(roundNo, box, data.asked); return; }
  box.replaceChildren();
  if (!data.card) return;
  const button = el("button", { type: "button", class: "quiet", text: "聞いてみる" });
  button.onclick = async () => {
    button.disabled = true;
    try {
      renderAsked(roundNo, box, await call("/api/ask_seat", { round: roundNo }));
    } catch (error) {
      button.disabled = false;
    }
  };
  box.append(el("div", { class: "ask-seat" },
    el("p", { class: "label", text: data.card.header }),
    el("p", { class: "words", text: data.card.question }),
    button));
}

function renderAsked(roundNo, box, asked) {
  box.dataset.asked = "1";
  const node = el("div", { class: "ask-seat" },
    el("p", { class: "label", text: asked.header }),
    el("p", { class: "words", text: asked.question }));
  if (asked.piece) {
    const answer = el("div", { class: "closing-word" },
      el("p", { class: "label", text: asked.label }),
      rankingTitle(asked.piece),
      el("p", { class: "words", text: asked.piece.said ? `「${asked.piece.text}」` : asked.piece.text }),
      el("span", { class: "source", text: sourceLine(asked.piece.source) }));
    answer.append(moreButton(asked.piece.utterance_id, answer));
    node.append(answer);
  } else if (asked.not_answered) {
    // Shown only, never a button: the question is the app's sentence, not
    // the student's. Under it, the seat's 「聞きたいことを書く」, box empty.
    node.append(el("p", { class: "not-answered", text: asked.not_answered }));
    if (asked.carded || state.carded.has(asked.seat_id)) node.append(cardDone(asked.seat_id, "p"));
    else node.append(cardEntry(asked.seat_id, "p"));
  } else if (asked.message) {
    node.append(el("p", { class: "message", text: asked.message }));
  }
  box.replaceChildren(node);
}

// 「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A): asked after the
// round is on screen. Shown apart from the quotes, never as an answer to the
// question; when no seat's words passed, nothing is shown at all. Each piece
// has the line of its kind of talk over it, and its source by its voice.
async function closeRound(roundNo, box) {
  let closing;
  try {
    closing = await call("/api/closing", { round: roundNo });
  } catch (error) {
    return;  // An extra at the round's end: the round itself is already shown.
  }
  if (!closing.words.length) return;
  const part = el("section", { class: "closing" }, el("p", { class: "closing-question", text: closing.question }));
  for (const word of closing.words) {
    const node = el("div", { class: "closing-word" },
      el("p", { class: "label", text: word.label }),
      rankingTitle(word),
      el("p", { class: "words", text: word.said ? `「${word.text}」` : word.text }),
      el("span", { class: "source", text: sourceLine(word.source) }));
    node.append(moreButton(word.utterance_id, node));
    part.append(node);
  }
  box.append(part);
}

// One press of 「もっと聞く」 as one passage: the pieces in reading order, the
// person's own words in 「」 inside the sentence, a ranking item's title
// small before the item, each ranking item on its own line, and one source
// line at the end (heard.source).
function morePassage(heard) {
  const blocks = [];
  for (const piece of heard.pieces) {
    if (piece.ranking_title) blocks.push({ title: piece.ranking_title });
    const words = piece.said ? `「${piece.text}」` : piece.text;
    const last = blocks[blocks.length - 1];
    if (last && "words" in last && !piece.ranking_item) last.words += words;
    else blocks.push({ words });
  }
  return { blocks, source: sourceLine(heard.source) };
}

// 「もっと聞く」: the next piece of the same seat and section, as recorded,
// at most twice from one piece. When the section runs out, 「ここから先は、
// まだ聞いていない」; pressing it makes a question card to that seat (SPEC 2-2).
function moreButton(utteranceId, node) {
  const button = el("button", { type: "button", class: "quiet more", text: "もっと聞く" });
  button.onclick = async () => {
    button.disabled = true;
    let heard;
    try {
      heard = await call("/api/more", { utterance_id: utteranceId });
    } catch (error) {
      button.disabled = false;
      return;
    }
    // One press reads to the end of the sentence: its pieces in one box.
    if (heard.pieces.length) {
      const passage = morePassage(heard);
      node.insertBefore(el("div", { class: "more-piece" },
        ...passage.blocks.map((block) => "title" in block
          ? el("p", { class: "ranking-title", text: block.title })
          : el("p", { class: "words", text: block.words })),
        el("span", { class: "source", text: passage.source })), button);
    }
    if (heard.ended) {
      const end = el("button", { type: "button", class: "quiet not-heard", text: state.texts.more_end });
      end.onclick = async () => {
        end.disabled = true;
        try {
          await call("/api/more_card", { utterance_id: utteranceId });
          end.replaceWith(el("p", { class: "card-done", text: state.texts.more_card_done }));
        } catch (error) {
          end.disabled = false;
        }
      };
      button.replaceWith(end);
    } else if (!heard.can_press) {
      button.remove();
    } else {
      button.disabled = false;
    }
  };
  return button;
}

function renderQuote(roundNo, quote) {
  // As spoken words (直し31-7): marked small, the source's note with the
  // original paragraph rather than the spoken words.
  const words = quote.spoken || (quote.said ? `「${quote.text}」` : quote.text);
  const node = el("div", { class: "quote", "data-utterance": quote.utterance_id });
  if (quote.spoken) node.classList.add("spoken");
  if (state.marks[quote.seat_id] === quote.utterance_id) node.classList.add("marked");
  const paragraph = el("p", { class: "paragraph", hidden: "" });
  const back = el("button", { type: "button", text: state.texts.bubble_choices.paragraph, onclick: async () => {
    if (paragraph.hidden && !paragraph.textContent) {
      paragraph.append(el("span", { text: await paragraphOf(quote.utterance_id) }));
      if (quote.spoken && quote.source.note) paragraph.append(el("span", { class: "source", text: quote.source.note }));
    }
    paragraph.hidden = !paragraph.hidden;
  } });
  const mark = el("button", { type: "button", text: "印をつける", onclick: () => markQuote(roundNo, quote.utterance_id) });
  node.dataset.seat = quote.seat_id;
  // node.append writes a null as the word "null": only what is there goes in.
  if (quote.spoken) node.append(el("span", { class: "spoken-mark", text: state.texts.spoken_mark }));
  node.append(
    el("p", { class: "words", text: words }),
    el("span", { class: "source", text: sourceLine(quote.spoken ? { ...quote.source, note: "" } : quote.source) }),
    el("div", { class: "actions" }, back, mark),
    paragraph);
  return node;
}

// The help under the bubble's buttons (直し32-4): the first time this
// student presses a bubble, and not again. 「最初にもどる」 reads the page
// afresh, so the next student has it again.
function firstHelp() {
  if (state.helpShown) return null;
  state.helpShown = true;
  return state.texts.bubble_choices_help;
}

// 「元の段落を読む」 at the table (直し32-4): the paragraph as recorded and
// whose it is (with its source's note) in the drawer, not by the map. 閉じる
// or Esc closes it, the keyboard back on the button pressed.
async function openParagraph(utteranceId, whose, from) {
  const text = await paragraphOf(utteranceId);
  $("drawer-paragraph").replaceChildren(el("p", { class: "whose", text: whose }),
    el("p", { class: "paragraph-text", text }));
  openDrawer("paragraph", from);
}

// A quote's paragraph, as recorded (/api/paragraph).
async function paragraphOf(utteranceId) {
  return (await call("/api/paragraph", { utterance_id: utteranceId })).paragraph;
}

// 「印をつける」, from a quote's card or from its lamp card at the table
// (直し26-2): the marks are kept in one place, state.marks, and every card
// that shows them follows.
async function markQuote(roundNo, utteranceId) {
  state.marks = (await call("/api/mark", { round: roundNo, utterance_id: utteranceId })).marks;
  for (const other of document.querySelectorAll(".quote")) {
    const seatId = other.dataset.seat;
    other.classList.toggle("marked", state.marks[seatId] === other.dataset.utterance);
  }
  // A mark can change the card of 「司会が○○に聞いてみる」 until it is pressed.
  const askBox = state.askBoxes[roundNo];
  if (askBox && !askBox.dataset.asked) loadAskCard(roundNo, askBox);
  onMap((map) => map.marked());
}

// 「下のやりとりで読む」 (直し26-2): the page goes to that quote's card in its
// round, and the keyboard's focus with it.
function readBelow(roundNo, utteranceId, from) {
  const quote = [...document.querySelectorAll(`#rounds .round[data-round="${roundNo}"] .quote`)]
    .find((node) => node.dataset.utterance === utteranceId);
  if (!quote) return;
  // On the one screen, in the drawer's rounds (直し32-1).
  openDrawer("rounds", from, { focus: false });
  quote.tabIndex = -1;
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  quote.scrollIntoView({ block: "center", behavior: still ? "auto" : "smooth" });
  quote.focus({ preventScroll: true });
}

function renderPlanted(text) {
  const line = el("p", { class: "planted" });
  line.append("番人が止めた（原文にない）：", el("s", { text }));
  return line;
}

// A split heading's "…" or ”…” shown as 「…」: on the screen only. The record
// and what the models are sent keep the heading as it was written.
function shownQuotes(text) {
  return text.replace(/["“”]([^"“”\n]*)["“”]/g, "「$1」");
}

// Words that wrap only between their pieces: after a 「：」, between two
// 「…」 (休みを「決めて取る」か｜「空いたら取る」か), and before a 「（」; never
// inside a 「…」 or a （…）. A piece wider than its line wraps inside itself
// only then. The same words, on screen only.
function phrases(text) {
  const pieces = [];
  let piece = "", depth = 0, quoted = false;
  const cut = () => { if (piece) pieces.push(piece); piece = ""; quoted = false; };
  for (const char of text) {
    if (!depth && ((char === "「" && quoted) || char === "（")) cut();
    piece += char;
    if (char === "「" || char === "（") depth += 1;
    else if ((char === "」" || char === "）") && depth) { depth -= 1; if (!depth && char === "」") quoted = true; }
    else if (!depth && char === "：") cut();
  }
  cut();
  return pieces;
}

function phrased(text) {
  return el("span", { class: "phrased" }, ...phrases(text).map((piece) => el("span", { class: "phrase", text: piece })));
}

function renderSplit(roundNo, split, byId, [quotesA, quotesB]) {
  const titles = (ids) => [...new Set(ids.map((id) => state.seatById[byId[id].seat_id].title))].join("・");
  const side = (ids, quotes) => el("div", { class: "side" },
    el("p", { class: "side-head", text: titles(ids) }),
    ...quotes.map((quote) => renderQuote(roundNo, quote)));
  return el("div", { class: "split" },
    el("p", { class: "notice", text: state.texts.split_notice }),
    el("p", { class: "heading" }, phrased(shownQuotes(split.heading))),
    el("div", { class: "sides" }, side(split.side_a, quotesA), side(split.side_b, quotesB)),
    el("button", { type: "button", class: "quiet", text: "この割れ目を次の問いにする", onclick: async () => {
      fill((await call("/api/split", { round: roundNo, index: split.index })).heading);
    } }));
}

// --- seats ---

function renderSeats() {
  const list = $("seat-list");
  list.replaceChildren();
  for (const [kind, label] of Object.entries(state.kinds)) {
    const seats = state.seats.filter((seat) => seat.kind === kind);
    if (!seats.length) continue;
    const row = el("div", { class: "seat-row" });
    for (const seat of seats) row.append(renderSeat(seat));
    list.append(el("section", { class: `kind-group kind-${kind}` }, el("h3", { text: label }), row));
  }
  $("met-count").textContent = String(state.met.size);
  onMap((map) => map.refresh());  // The same count and marks on the map.
}

function renderSeat(seat) {
  const node = el("div", { class: `seat kind-${seat.kind}`, "data-seat": seat.seat_id });
  const order = state.lastOrder.indexOf(seat.seat_id);
  const title = el("div", { class: "title" });
  if (order >= 0) {
    node.classList.add("lit");
    title.append(el("span", { class: "order", text: String(order + 1) }));
  }
  title.append(seat.title);
  node.append(title);
  if (seat.detail) node.append(el("div", { class: "detail", text: seat.detail }));
  if (state.met.has(seat.seat_id)) node.classList.add("met");
  if (state.silent.has(seat.seat_id) && !state.met.has(seat.seat_id)) node.append(renderNotAsked(seat));
  return node;
}

function renderNotAsked(seat) {
  const box = el("div", { class: "not-asked" }, el("div", { text: state.texts.not_asked_yet }));
  if (state.carded.has(seat.seat_id)) {
    box.append(cardDone(seat.seat_id));
    return box;
  }
  box.append(cardEntry(seat.seat_id));
  return box;
}

// A seat's question card, from its lamp card at the table (直し26-2): the
// one box at the foot writes to that seat (直し32-2).
function openCardFor(seatId) {
  askSeat(seatId);
}

// Where a seat's card was made: 「質問カードにしました」, or when the same
// words were sent to it again, the card there is (直し31-2).
function cardDone(seatId, tag = "div") {
  const again = state.cardAgain[seatId];
  return el(tag, { class: "card-done", text: again ? state.texts.card_already.replace("{card}", again) : "質問カードにしました" });
}

// 「聞きたいことを書く」: the one box at the foot writes to that seat, empty
// for it (SPEC 2-2: the card holds the student's words only). Once its card
// is made, the button says so (sendCard). tag: what the line it becomes is.
function cardEntry(seatId, tag = "div") {
  const open = el("button", { type: "button", class: "quiet", text: "聞きたいことを書く",
    onclick: () => askSeat(seatId) });
  open.dataset.cardSeat = seatId;
  open.dataset.doneTag = tag;
  return open;
}

// --- the reflection sheet (SPEC 5-2) ---

function radios(container, name, options) {
  container.replaceChildren();
  for (const [value, label] of options) {
    const input = el("input", { type: "radio", name, value });
    container.append(el("label", { class: "choice" }, input, label));
  }
}

function picked(name) {
  const input = document.querySelector(`input[name="${name}"]:checked`);
  return input ? input.value : "";
}

// 「ふりかえりへ」 (直し30-1): once, in any round, an answer to コーチ or
// オブザーバー first. Not yet: a line by the button, and the newest card
// that can still be answered brought into view, its 「答える」 focused. The
// button itself is never taken away. Nothing to answer anywhere, or the
// model was out once: on to the reflection, so no student is ever held.
function toReflection() {
  const entry = state.aiAnswered || state.aiUnavailable ? null : answerable();
  const line = $("reflect-needs-answer");
  if (!entry) {
    line.hidden = true;
    openReflection();
    return;
  }
  line.textContent = state.texts.reflect_needs_answer;
  line.hidden = false;
  state.needsShown = true;
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const card = entry.closest(".ai-card, .ai-question");
  if (!card.classList.contains("ai-question")) openDrawer("rounds", document.activeElement, { focus: false });
  for (const node of document.querySelectorAll(".needs-answer")) node.classList.remove("needs-answer");
  card.classList.add("needs-answer");
  card.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "center" });
  entry.focus({ preventScroll: true });
}

// The newest round's card that can still be answered: its 「答える」, or the
// box already open under it. None: null.
function answerable() {
  const seat = $("ai-seat");
  const there = seat.hidden ? null : seat.querySelector(".ai-question:not(:disabled)");
  if (there) return there;
  const rounds = Object.keys(state.bands).map(Number).sort((a, b) => b - a);
  for (const roundNo of rounds) {
    const entry = state.bands[roundNo].querySelector(".ai-card > button, .ai-card > form input:not(:disabled)");
    if (entry) return entry;
  }
  return null;
}

function openReflection() {
  closeDrawer();
  $("table").hidden = true;
  $("reflect").hidden = false;
  setNow();
  document.querySelector(".reflect-heavy-talk").textContent = state.texts.heavy_talk_notice;
  $("first-question").textContent = state.firstQuestion;
  radios($("changed-choices"), "changed", Object.entries(state.changedChoices));
  $("meet-question").textContent = state.texts.meet_question;
  const select = $("meet-seat");
  select.replaceChildren(el("option", { value: "", text: "席を選ぶ" }));
  const label = (seat) => [seat.title, seat.detail].filter(Boolean).join("　");
  const met = el("optgroup", { label: "会った席" });
  const others = el("optgroup", { label: "ほかの席" });
  for (const seat of state.seats) {
    (state.met.has(seat.seat_id) ? met : others).append(el("option", { value: seat.seat_id, text: label(seat) }));
  }
  if (met.children.length) select.append(met);
  select.append(others);
  window.scrollTo(0, 0);
}

async function reflectFirst(event) {
  event.preventDefault();
  const changed = picked("changed");
  const nowQuestion = $("now-question").value.trim();
  if (!changed || !nowQuestion) return;
  const message = $("reflect-message");
  const button = $("reflect-first").querySelector("button[type=submit]");
  button.disabled = true;
  message.textContent = state.texts.waiting_reflection;
  message.hidden = false;
  let result;
  try {
    result = await call("/api/reflect/begin", { changed, now_question: nowQuestion });
  } catch (error) {
    message.textContent = sendFailed(error);
    button.disabled = false;
    return;
  }
  if (result.status === "ask_again") {
    message.textContent = result.message;
    button.disabled = false;
    return;
  }
  for (const node of $("reflect-first").querySelectorAll("input, textarea, button")) node.disabled = true;
  message.hidden = true;
  // The split headings in it shown in 「」 too; on screen only (SPEC 5-2).
  $("ask-back").textContent = shownQuotes(result.ask_back);
  $("reflect-answer").hidden = false;
  $("answer").focus();
}

async function reflectAnswer(declined) {
  const answer = $("answer").value.trim();
  if (!declined && !answer) return;
  const result = await call("/api/reflect/answer", { answer, declined });
  for (const node of $("reflect-answer").querySelectorAll("input, button")) node.disabled = true;
  // The moves come in the fixed order of their directions; none and own
  // stand beside them at the same size.
  const options = result.moves.map((move) => [move.direction, `${move.label}：${move.text}`]);
  options.push(["none", "どれも選ばない"], ["own", "自分で書く"]);
  radios($("moves"), "move", options);
  for (const input of $("moves").querySelectorAll("input")) {
    input.addEventListener("change", () => { $("own-move").hidden = picked("move") !== "own"; });
  }
  $("reflect-finish").hidden = false;
}

async function reflectFinish(event) {
  event.preventDefault();
  const chosen = picked("move");
  // The seat to hear more from is optional.
  if (!chosen) return;
  if (chosen === "own" && !$("own-move").value.trim()) return;
  const sheet = await call("/api/reflect/finish", {
    chosen, own_move: $("own-move").value, rewrite: $("rewrite").value,
    meet_seat: $("meet-seat").value, meet_reason: $("meet-reason").value,
  });
  for (const id of ["reflect-first", "reflect-answer", "reflect-finish"]) $(id).hidden = true;
  state.sheet = sheet;
  if (sheet.uses.length) {
    renderUses(sheet.uses);
    return;
  }
  // No seat picked: no ②; the card (if any move) and the sheet at once.
  if (sheet.harvest) showHarvest(sheet.harvest);
  renderSheet(sheet);
  loadSubject();
}

// --- today's harvest card (SPEC 5-3) ---

// Either line may be empty: no move, or no seat picked. Then it is left out.
function showHarvest(card) {
  $("harvest-heading").textContent = state.texts.harvest_heading;
  for (const [id, text] of [["harvest-moves", card.moves], ["harvest-meet", card.meet]]) {
    $(id).textContent = text;
    $(id).hidden = !text;
  }
  $("harvest").hidden = false;
}

// ②: the uses the record fits, and 「選ばない」, all the same size.
function renderUses(uses) {
  $("harvest-use-question").textContent = state.texts.harvest_use_question;
  const box = $("uses");
  box.replaceChildren();
  for (const use of uses) {
    box.append(el("button", { type: "button", onclick: () => pickUse(use.force) },
      el("span", { text: use.text }), el("span", { class: "force", text: use.name })));
  }
  box.append(el("button", { type: "button", text: "選ばない", onclick: () => pickUse("none") }));
  $("harvest-use").hidden = false;
}

async function pickUse(use) {
  const buttons = [...$("uses").querySelectorAll("button")];
  for (const button of buttons) button.disabled = true;
  const message = $("harvest-message");
  try {
    const card = await call("/api/harvest", { use });
    $("harvest-use").hidden = true;
    showHarvest(card);
    renderSheet(state.sheet);
  } catch (error) {
    message.textContent = sendFailed(error);
    message.hidden = false;
    for (const button of buttons) button.disabled = false;
    return;
  }
  loadSubject();
}

// ③: asked for once ① and ② are on screen, so they never wait on the model.
// No ③ (or a failure): nothing is added.
async function loadSubject() {
  try {
    showSubject((await call("/api/subject", {})).subject);
  } catch (error) {
    // ③ is left out; ① and ② stay as they are.
  }
}

// ③ as a card (直し31-3): the student's question as they hold it now on the
// left, the subject's card on the right (いつ・科目・見出し・ひとこと), a line
// between, so the tie is seen at a glance. Nothing else fit: two cards, and
// the student picks the one they think nearer, or neither.
function showSubject(subject) {
  if (!subject) return;
  $("harvest-heading").textContent = state.texts.harvest_heading;
  $("harvest-subject-link").textContent = subject.link;
  const cards = el("div", { class: "subject-cards" });
  subject.cards.forEach((card, index) => {
    const node = el("div", { class: "subject-card" },
      el("p", { class: "when", text: card.when }),
      el("p", { class: "subject", text: card.subject }),
      card.heading ? el("p", { class: "heading", text: `「${card.heading}」` }) : null,
      el("p", { class: "note", text: card.note }));
    if (subject.choose) {
      node.append(el("button", { type: "button", class: "quiet", text: state.texts.harvest_subject_pick,
        onclick: () => chooseSubject(index) }));
    }
    cards.append(node);
  });
  const tie = $("harvest-subject-tie");
  tie.classList.toggle("two", subject.cards.length > 1);
  tie.replaceChildren(
    el("div", { class: "subject-question" },
      el("p", { class: "label", text: state.texts.harvest_subject_question }),
      el("p", { class: "words", text: subject.question })),
    el("div", { class: "subject-tie-line", "aria-hidden": "true" }),
    cards);
  const none = $("harvest-subject-none");
  none.textContent = state.texts.harvest_subject_none;
  none.hidden = !subject.choose;
  none.disabled = false;
  const more = $("harvest-subject-more");
  more.textContent = state.texts.harvest_subject_more;
  more.hidden = !subject.more;
  more.disabled = false;
  $("harvest-subject").hidden = false;
  $("harvest").hidden = false;
}

async function chooseSubject(choice) {
  const buttons = [$("harvest-subject-none"), ...$("harvest-subject-tie").querySelectorAll("button")];
  for (const button of buttons) button.disabled = true;
  try {
    showSubject((await call("/api/subject_choose", { choice })).subject);
  } catch (error) {
    for (const button of buttons) button.disabled = false;
  }
}

async function moreSubject() {
  const more = $("harvest-subject-more");
  more.disabled = true;
  try {
    showSubject((await call("/api/subject_more", {})).subject);
  } catch (error) {
    more.disabled = false;
  }
}

function renderSheet(sheet) {
  const box = $("sheet");
  box.replaceChildren();
  const row = (label, ...values) => {
    const cell = el("dd");
    for (const value of values) if (value) cell.append(typeof value === "string" ? el("div", { text: value }) : value);
    box.append(el("dt", { text: label }), cell);
  };
  row("最初の問い", sheet.first_question);
  const lives = sheet.met_lives.map((life) => el("div", {},
    el("div", { text: life.said ? `「${life.text}」` : life.text }),
    el("div", { class: "source", text: sourceLine(life.source) })));
  // No words marked: one line from texts/ instead of an empty row.
  row("出会った生き方", ...(lives.length ? lives : [el("div", { class: "left", text: state.texts.met_lives_empty })]));
  row("割れたところ", ...sheet.splits.map((split) =>
    el("div", { class: split.pressed ? "" : "left", text: (split.pressed ? "" : "置いてきた：") + shownQuotes(split.heading) })));
  // No card left: the row is not shown at all.
  if (sheet.cards.length) row("残した質問カード", ...sheet.cards);
  row("最初の問いは変わった？", sheet.changed);
  row("いまの問い（1回目）", sheet.now_question);
  row("問い返し", shownQuotes(sheet.ask_back), sheet.declined ? "答えない" : sheet.answer);
  const move = sheet.chosen === "none" ? "選ばない"
    : sheet.chosen === "own" ? `自分で書いた一手：${sheet.own_move}`
    : sheet.move ? `${sheet.move.label}：${sheet.move.text}` : "";
  row("次の一手", move);
  if (sheet.rewrite) row("いまの問い（書き直し）", sheet.rewrite);
  // The row's label is the card's line head without its colon.
  const meetLabel = state.texts.harvest_meet_prefix.replace(/[：:]$/, "");
  if (sheet.meet) row(meetLabel, sourceLine(sheet.meet), sheet.meet.reason);
  else if (sheet.meet_reason) row(meetLabel, sheet.meet_reason);
  box.hidden = false;
  showBackToStart();
}

// --- back to the first screen (直し30-2) ---

// Under the sheet (after the harvest card where ② is asked): 最初にもどる.
function showBackToStart() {
  $("back-start").textContent = state.texts.back_to_start;
  $("back-confirm-line").textContent = state.texts.back_to_start_confirm;
  $("back-yes").textContent = state.texts.back_to_start_yes;
  $("back-no").textContent = state.texts.back_to_start_no;
  $("back-confirm").hidden = true;
  $("back-start").hidden = false;
  $("back-to-start").hidden = false;
}

// Pressed: not yet; the line and もどる・やめる in its place.
function askBackToStart() {
  $("back-start").hidden = true;
  $("back-confirm").hidden = false;
  $("back-no").focus();
}

function stayHere() {
  $("back-confirm").hidden = true;
  $("back-start").hidden = false;
  $("back-start").focus();
}

// The next student starts from the page read afresh, so nothing of this
// one's words is left on screen or in the page. The sitting's record is on
// the server already, kept after every step; the next Lab starts a new one.
function backToStart() {
  for (const node of document.querySelectorAll("input, textarea")) {
    node.value = "";
    node.checked = false;
  }
  window.location.replace(window.location.pathname);
}

$("ask-form").addEventListener("submit", send);
$("input-to-clear").addEventListener("click", backToEveryone);
$("question").addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.to.kind !== "all") {
    event.preventDefault();
    backToEveryone();
  }
});
$("to-reflect").addEventListener("click", toReflection);
$("reflect-first").addEventListener("submit", reflectFirst);
$("reflect-answer").addEventListener("submit", (event) => { event.preventDefault(); reflectAnswer(false); });
$("decline").addEventListener("click", () => reflectAnswer(true));
$("reflect-finish").addEventListener("submit", reflectFinish);
$("harvest-subject-more").addEventListener("click", moreSubject);
$("harvest-subject-none").addEventListener("click", () => chooseSubject("none"));
$("back-start").addEventListener("click", askBackToStart);
$("back-yes").addEventListener("click", backToStart);
$("back-no").addEventListener("click", stayHere);
$("back-confirm").addEventListener("keydown", (event) => { if (event.key === "Escape") stayHere(); });
$("more-purposes").addEventListener("click", async () => renderPurposes((await call("/api/purposes", {})).purposes));
window.addEventListener("resize", keepUnderNow);
setup();
