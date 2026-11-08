// The round-table screen. Every word from the server is set with textContent,
// never as HTML.
"use strict";

const state = {
  texts: {}, kinds: {}, seats: [], seatById: {},
  lastOrder: [], met: new Set(), silent: new Set(), carded: new Set(), thanked: new Set(), marks: {},
  askBoxes: {},  // Round number -> the box of 「司会が○○に聞いてみる」.
  bands: {},  // Round number -> the band of コーチ and オブザーバー below.
  // Before the reflection, one answer to コーチ or オブザーバー (直し30-1):
  // one that started the next round; or the model was out once.
  aiAnswered: false, aiUnavailable: false, needsShown: false,
  // Seat -> the card's words, when the same card was sent to it again (直し31-2).
  cardAgain: {},
  // "round:role" -> コーチ's or オブザーバー's question (直し48 段3: shown over the box answering it).
  aiAsked: {},
  // The AI's question being answered in its seat (直し53 段5): { roundNo, role }, or null.
  aiAnswer: null,
  // What 「いまやること」 is worked out from (直し31-5): a question being sent;
  // the round's seats still lighting; a lamp card's choices open; one
  // pressed this round; the round's table open with its cards; AI
  // questions to answer below.
  now: { asking: false, reading: false, choices: false, pressed: false, table: false, band: false, preparing: false },
  // Whom the one box at the foot writes to (直し32-2): everyone (a question
  // to the town's adults), one seat (a question card), or an AI's question
  // (the answer starts the next round). Each keeps its own unsent words.
  to: { kind: "all" }, drafts: {},
  // 帰る前に、ひとこと (直し38): which reflection ("hitokoto", or "old" when
  // EBINO_REFLECT=old), its words, and the bubbles opened, in that order.
  reflect: "old", hitokoto: null, opened: [],
  // The latest round has a split none of whose headings is pressed yet
  // (直し40-1): 「いまやること」 says it can be pressed.
  splitOpen: false,
  // What the one line over the box (#input-done) says: "split" after a
  // split's heading went into the box (直し40-1), so it goes when the box does.
  doneKind: "",
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

// wait (直し42): the kind of wait this is, when the model is waited for
// (texts/wait_sign.tsv); then the sign in the middle of the map, should it
// take longer than WAIT_SHOW_MS. None: no sign (a quick request).
async function call(path, body, { wait } = {}) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const waiting = wait ? waitBegin(wait) : null;
  try {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || String(response.status));
    if (afterCall.paths.has(path)) afterCall.then();  // 今日の道すじ (直し45 段2).
    return data;
  } finally {
    if (waiting) waitEnd(waiting);
  }
}

// 今日の道すじ (直し45 段2): after these sends the trail is asked for again
// (setupTrail fills them in).
const afterCall = { paths: new Set(), then: () => {} };

// --- the sign in the middle of the map (直し42) ---

// While the model is waited for, in the middle of the map's frame: a big
// short word and one small line of what is being done, from
// texts/wait_sign.tsv. Shown only when a wait passes WAIT_SHOW_MS; gone when
// it comes back or fails. After WAIT_SLOW_MS the small line says it is
// taking longer. No timer of its own ends a wait. Only where the map is
// out; the line at the top reads out what is going on, the sign does not.
// The seats flying to the round table (map.js) show 「集合中」.
const WAIT_SHOW_MS = 400, WAIT_SLOW_MS = 15000;
// Waits the student did not start and does not wait on (the AI's questions
// after a round): shown only when nothing is on the map's middle.
const WAIT_ASIDE = new Set(["coach"]);
const waits = { list: [], gather: false };
// 直し42 段2: while a question's round is waited for, the step the server
// is really at (GET /api/now_step, every WAIT_STEP_MS, not through call):
// find, moderate, speak. A step is shown only once the server is in it;
// none said, or the asking failed: the wait's own words.
const WAIT_STEP_MS = 500;
const WAIT_STEPS = new Set(["find", "moderate", "speak"]);

function waitBegin(kind) {
  const entry = { kind, shown: false, slow: false, step: "" };
  entry.timers = [setTimeout(() => { entry.shown = true; drawWait(); }, WAIT_SHOW_MS),
    setTimeout(() => { entry.slow = true; drawWait(); }, WAIT_SLOW_MS)];
  if (kind === "ask") entry.stop = askSteps(entry);
  waits.list.push(entry);
  return entry;
}

function waitEnd(entry) {
  for (const timer of entry.timers) clearTimeout(timer);
  if (entry.stop) entry.stop();
  waits.list = waits.list.filter((other) => other !== entry);
  drawWait();
}

// Asks the server's step until stopped (the answer in, a failure, the page
// left); returns the way to stop it.
function askSteps(entry) {
  let stopped = false, timer = null;
  const next = async () => {
    try {
      const response = await fetch("/api/now_step");
      const data = await response.json();
      if (!stopped && response.ok && WAIT_STEPS.has(data.step) && data.step !== entry.step) {
        entry.step = data.step;
        drawWait();
      }
    } catch (error) {
      // Not heard: the sign keeps its words, the wait goes on.
    }
    if (!stopped) timer = setTimeout(next, WAIT_STEP_MS);
  };
  timer = setTimeout(next, 0);
  return () => {
    stopped = true;
    clearTimeout(timer);
  };
}

// The page left: no step asked for after it.
if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => { for (const entry of waits.list) if (entry.stop) entry.stop(); });
}

// The seats are flying to the round table (map.js, motion on): 「集合中」.
function gathering(on) {
  waits.gather = on;
  drawWait();
}

// Something the student reads is on the map's middle: the round's seats
// lighting, the table and its cards, a bubble, one to one.
function mapBusy() {
  return state.now.reading || Boolean(document.querySelector(
    "#map-overlay .table-label, #map-overlay .map-bubble, #map-frame.one-on"));
}

// The wait on the sign now: the seats gathering first, then the newest wait
// shown, a wait aside only when nothing is on the map's middle.
function waitNow() {
  if (waits.gather) return { kind: "gather", slow: false };
  const shown = waits.list.filter((entry) => entry.shown);
  const mine = shown.filter((entry) => !WAIT_ASIDE.has(entry.kind));
  if (mine.length) return mine[mine.length - 1];
  return shown.length && !mapBusy() ? shown[shown.length - 1] : null;
}

function drawWait() {
  const sign = $("wait-sign"), words = state.texts.wait_sign;
  if (!sign || !words) return;
  const now = oneScreen() ? waitNow() : null;
  sign.hidden = !now;
  if (now) {
    const row = words[now.step] || words[now.kind] || words.ask;
    $("wait-word").textContent = row.word;
    $("wait-line").textContent = now.slow ? words.slow.line : row.line;
    sign.dataset.kind = now.kind;
  }
  // Busy for screen readers while the sign is out (the line at the top says what).
  if (now) $("map").setAttribute("aria-busy", "true");
  else $("map").removeAttribute("aria-busy");
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
    placeInside();
  }
}

// A ranking item's title, small over the item, as recorded (null when none).
function rankingTitle(piece) {
  return piece.ranking_title ? el("p", { class: "ranking-title", text: piece.ranking_title }) : null;
}

// --- start ---

// The bundled Mincho and Gothic (直し41), asked for by name before anything
// is measured: the map's labels, the school's name and the bubbles are
// placed by the width of their words. A line too slow does not hold the
// screen past FONT_WAIT_MS; the words then swap in, and the map is laid out
// again when they have (fontsDone).
const FONTS = ['400 16px "Ebino Mincho"', '700 16px "Ebino Mincho"', '400 16px "Ebino Gothic"', '700 16px "Ebino Gothic"'];
const FONT_WAIT_MS = 15000;

function fontsReady() {
  if (!document.fonts || !document.fonts.load) return Promise.resolve();
  const all = Promise.all(FONTS.map((font) => document.fonts.load(font, "あ").catch(() => null)));
  return Promise.race([all, new Promise((done) => setTimeout(done, FONT_WAIT_MS))]);
}

// A font came in after the screen was drawn: the map's places measured
// afresh, as when the window changes, unless a bubble is open on it.
function fontsDone() {
  if (document.querySelector(".map-bubble")) return;
  mapMoved();
}

async function setup() {
  if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener("loadingdone", fontsDone);
  const [data] = await Promise.all([call("/api/setup"), fontsReady()]);
  Object.assign(state, { texts: data.texts, kinds: data.kinds, seats: data.seats, changedChoices: data.changed_choices,
    reflect: data.reflect, hitokoto: data.hitokoto });
  if (state.reflect === "hitokoto") useHitokotoName(data.texts);
  for (const seat of data.seats) state.seatById[seat.seat_id] = seat;
  for (const line of data.texts.start_notice) $("start-notice").append(el("li", { text: line }));
  $("start-purpose").textContent = data.texts.start_purpose;
  // 直し54n: the opening's words (launch.js), if it is still on.
  if (window.EbinoLaunch) EbinoLaunch.words({ line: data.texts.launch_line, skip: data.texts.opening_skip, start: data.texts.launch_start, sound: data.texts.launch_sound });
  // The host's words, a paragraph for each of its lines.
  // 直し48 段1: on the first page all but the last; the last, 「進み方は、
  // この4つです。」, heads the second page, the four steps under it.
  const about = data.texts.start_about.split("\n").filter((text) => text.trim());
  const flowTitle = about.length > 1 ? about.pop() : "";
  for (const line of about) $("start-about").append(el("p", { text: line }));
  $("first-look-flow-title").textContent = flowTitle;
  // How it goes: the band's own steps (the same words light up there later).
  for (const step of data.texts.now_steps) {
    $("start-flow").append(el("li", {}, el("span", { class: "flow-step", text: step.text }),
      el("span", { class: "flow-do", text: data.texts.start_flow[step.id] })));
  }
  for (const step of data.texts.now_steps) {
    $("now-steps").append(el("li", { "data-step": step.id, text: step.text }));
  }
  // コーチとオブザーバー (直し46): a card for each, its robot (直し47, robot.js;
  // the largest here, 「AI」 on its body) and its name as on the cards, what
  // it knows and what it does (ai_roles_intro.tsv).
  const roles = data.ai_roles || [];
  $("start-roles").hidden = !roles.length;
  $("start-roles-lead").textContent = data.texts.guide.roles_lead;
  $("start-roles-note").textContent = data.texts.guide.roles_note;
  for (const role of roles) {
    $("start-roles-list").append(el("li", { class: "role-card", "data-role": role.role },
      EbinoRobot.make(role.role, { tag: data.texts.ai_seat_mark }),
      el("div", { class: "role-text" },
        el("p", { class: "role-head" }, el("span", { class: "who", text: role.name })),
        el("p", { class: "knows", text: role.knows }),
        el("p", { class: "does", text: role.does }))));
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
  setupTrail();
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
    readBelow, shownQuotes, phrased, askSeat, answerTo, firstHelp, openParagraph, backToEveryone, oneOpen, oneAsk,
    oneCoach, oneCoachAnswer, oneThanks, bubbleOpened, trailOpened, gathering, foldAiSeat, pressSplit, splitLabel };
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
  let data, ready = false;
  // The opening over (or skipped) and the server not ready yet (直し32-5):
  // the table now, the box shut, the line saying to wait; the keyboard goes
  // to the box once it is ready.
  if (opening) opening.then(() => { if (!ready) preparing(true); });
  try {
    [data] = await Promise.all([call("/api/start", { lab }, { wait: "start" }),
      opening || new Promise((done) => setTimeout(done, still ? 0 : 320))]);
    ready = true;
  } catch (error) {
    ready = true;
    preparing(false);
    if (opening) endOpening(true);
    for (const button of buttons) {
      button.setAttribute("aria-pressed", "false");
      button.disabled = false;
    }
    throw error;
  }
  if (opening) endOpening(false);
  preparing(false);
  $("start").hidden = true;
  $("table").hidden = false;
  $("inside").hidden = !$("inside-counts").children.length;
  placeInside();
  setNow();
  onMap((map) => map.show());  // Draws the rim and the river once the map is on screen.
  renderPurposes(data.purposes);
  $("question").focus();
  await comingIn();
  firstLook();
}

// 直し52 段1 (the teacher, 11/7): the first time only, before 司会（AI）から、
// はじめに: the map not covered, the camera from a little wider than the
// whole (set as the opening's plane began) to the basin and the school, in
// APPROACH_FOR ms; then the cover and the window as before. A press or a key
// (taken, not passed on): the window at once. Motion reduced, no map, or the
// window not to come: the window at once, as before. Never longer than
// 3 seconds whatever the frames do. Kept when it is over (at once: nothing to do).
const APPROACH_FOR = 2400;

function comingIn() {
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (still || state.approached || state.firstLooked || !state.texts.guide || typeof EbinoMap === "undefined" || $("map").hidden) {
    return Promise.resolve();
  }
  state.approached = true;
  state.approaching = true;
  drawGuide();  // Its bubble away now, not at its next look.
  return new Promise((finished) => {
    let over = false, cap = null;
    const end = () => {
      if (over) return;
      over = true;
      clearTimeout(cap);
      for (const type of ["pointerdown", "keydown"]) document.removeEventListener(type, skip, true);
      onMap((map) => map.approachEnd());
      state.approaching = false;
      finished();
    };
    const skip = (event) => {
      event.preventDefault();
      event.stopPropagation();
      end();
    };
    for (const type of ["pointerdown", "keydown"]) document.addEventListener(type, skip, true);
    cap = setTimeout(end, 2.8 * 1000);
    let going = null;
    onMap((map) => { going = map.approach(APPROACH_FOR); });
    if (going) going.then(end);
    else end();
  });
}

// Waiting for /api/start with the table out (直し32-5): the box and its
// button shut, 「準備しています。…」 the line; on: off again.
function preparing(on) {
  if (!on && !state.now.preparing) return;
  if (on) {
    $("start").hidden = true;
    $("table").hidden = false;
    $("table").classList.remove("opening-on");  // The box at the foot shows, shut.
  }
  $("question").disabled = on;
  $("ask-button").disabled = on;
  setNow({ preparing: on });
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
  onMap((map) => map.wideStart());  // 直し52 段1: a little wider than the whole, to come in from after.
  const frame = $("map-frame");
  const box = frame.getBoundingClientRect();
  if (!box.width || !box.height || $("map").hidden) {
    $("table").classList.remove("opening-on");
    return false;
  }
  $("map").scrollIntoView({ block: "nearest" });
  const w = box.width, h = box.height;
  const sighted = (selector, high) => {
    const node = document.querySelector(selector);
    if (!node) return null;
    const s = node.getBoundingClientRect();
    const at = [s.left + s.width / 2 - box.left, s.top + s.height * high - box.top];
    return s.width && at[0] > 0 && at[0] < w && at[1] > 0 && at[1] < h ? at : null;
  };
  // It lands at the school beside the map (直し33-2: its picture, or the
  // plain building); with neither in sight, the middle.
  const end = sighted("#map-svg .yard-landing", 0.5) || [w / 2, h / 2];
  // From the roof of the school's 3D picture when it is on the map in sight
  // (直し30の続き-2); else from its mark; else the lower left. With no
  // picture (none given, unread, or the school said no) the same opening.
  let from = [Math.min(48, w * 0.08), h - Math.min(48, h * 0.08)];
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
// by pitch. Seen from above and from the south, as the map is (from
// elev radians over the ground, 45° unless given), the near side a little
// bigger; each face as bright as it turns to the lamp (both sides are paper).
function planeFaces(pose) {
  const { x, y, size, a, roll, pitch, elev = Math.PI / 4 } = pose;
  const ce = Math.cos(elev), se = Math.sin(elev);
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
        const [X, Y, Z] = turned[name], k = 1 / (1 - 0.3 * (Y * ce + Z * se));
        return [x + X * size * k, y + (Y * se - Z * ce) * size * k];
      }),
      depth: (p[1] + q[1] + r[1]) * ce + (p[2] + q[2] + r[2]) * se,
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

// How far into its landing the plane is: 0 until LANDING_FROM of the way,
// then smoothly to 1 at the end.
const LANDING_FROM = 0.8;
const LANDING_ELEV = 0.22;  // Radians over the ground at the end: nearly from the side.
function landing(fly) {
  const k = Math.max(0, Math.min(1, (fly - LANDING_FROM) / (1 - LANDING_FROM)));
  return k * k * (3 - 2 * k);
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
  // Landing (直し32-5): from straight above its folds read as an umbrella,
  // so for the last of the way it is seen more from the side (the camera
  // low, its nose turned across the screen), its wings' thickness and its
  // nose's way plain. The time it takes is as before.
  const side = landing(fly);
  const across = Math.cos(p.a) >= 0 ? 0 : Math.PI;
  const turn = Math.atan2(Math.sin(across - p.a), Math.cos(across - p.a));
  const faces = planeFaces({ x: p.x, y: p.y, size, a: p.a + turn * side * 0.75, roll: -run.lean * (1 - side), pitch,
    elev: Math.PI / 4 - (Math.PI / 4 - LANDING_ELEV) * side });
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
  if (!$("reflect").hidden || !$("hitokoto").hidden) return "reflect";
  if (now.preparing) return "preparing";
  if (now.asking) return "asking";
  if (!state.firstQuestion) return "write";
  if (now.reading) return "reading";
  if (now.one) return "one";  // One to one (直し34-3).
  if (cardOpen()) return "card";
  if (state.aiAnswer) return "answer_ai";  // Writing in the AI's seat (直し53 段5).
  if (now.choices) return "pressed";
  if (now.table && !now.pressed) return "table";
  if (!state.aiAnswered && now.band) return "answer_ai";
  // The latest round split and none of it pressed yet (直し40-1).
  if (state.splitOpen) return "split";
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
  const nowLine = $("now-line");
  if (nowLine.textContent !== line.text) {
    nowLine.textContent = line.text;
    // Something new to do: lit once so the eye goes to it (11/6). The CSS
    // keeps it still with motion reduced.
    nowLine.classList.remove("fresh");
    void nowLine.offsetWidth;
    nowLine.classList.add("fresh");
  }
  keepUnderNow();
  drawWait();  // The sign in the middle may step back or come out now (直し42).
  drawGuide();
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

// Whose words are in (直し33-1): shut, its button alone over the map; open
// over the map at once when pressed (the map does not move for it). Pressed
// again, Esc, or a press outside it shuts it, the keyboard back on its
// button. Before the first question the button is lit once (style.css:
// .beckon; with motion reduced, lit and still).
function setupInside() {
  const fold = $("inside-fold"), button = $("inside-open");
  // Lit once: the first time it opens, the light goes for good.
  fold.addEventListener("toggle", () => { if (fold.open) $("inside").classList.remove("beckon"); });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !fold.open) return;
    event.preventDefault();
    event.stopPropagation();
    fold.open = false;
    button.focus({ preventScroll: true });
  });
  document.addEventListener("click", (event) => {
    if (fold.open && !$("inside").contains(event.target)) fold.open = false;
  });
  $("inside").classList.add("beckon");
}

// The first look (the teacher, 11/6: the students did not open it by
// themselves, and should know what the app is right before): once the
// table is out, one window in the middle of the screen, over everything, by
// itself, two pages: what the app is and how it goes, then (次へ) whose words
// are in. Once only (the next student starts from the page read afresh).
// Its last button, Esc, or a question example pressed puts whose words are
// in back in the map's column, and the keyboard goes to the box.
// The pages there are, in turn (直し48 段1): the host's hello and how it goes
// always; コーチ and オブザーバー with any; whose words are in and the
// examples of questions with any words in. Each page's heading names it.
function firstLookPages(withRoles, withInside) {
  return [["first-look-about", "first-look-about-title"], ["first-look-flow", "first-look-flow-title"],
    withRoles && ["first-look-roles", "start-roles-lead"], withInside && ["first-look-inside", "first-look-title"],
    withInside && ["first-look-examples", "examples-lead"]].filter(Boolean);
}

function firstLook() {
  const look = $("first-look"), words = state.texts.guide;
  if (state.firstLooked || !words || typeof look.showModal !== "function") return;
  state.firstLooked = true;
  // Whose words are in, when there are any: its two parts, each a page of
  // its own here, moved (not copied) and put back after.
  const body = $("inside").hidden ? null : document.querySelector("#inside-fold .inside-body");
  const counts = body && body.querySelector(".inside-counts-part");
  const examples = body && body.querySelector(".inside-examples");
  // 司会（AI）'s robot (直し48 段2, robot.js) by its name.
  $("host-mark").replaceChildren(EbinoRobot.make("host"));
  $("host-name").textContent = words.about_title;
  $("first-look-title").textContent = words.first_look_title;
  $("first-look-back").textContent = words.back;
  $("inside-fold").open = false;
  if (counts) $("first-look-body").append(counts);
  if (examples) $("first-look-examples-body").append(examples);
  const pages = firstLookPages(!$("start-roles").hidden, Boolean(counts && examples));
  const dots = $("first-look-dots");
  dots.replaceChildren(...pages.map(() => el("li")));
  let at = 0;
  // One page at a time: its heading names the window; 次へ on the last is
  // 「見た。聞きたいことを書く」. The keyboard stays on 次へ (Enter, Enter, …).
  const turn = (to) => {
    at = Math.max(0, Math.min(pages.length - 1, to));
    pages.forEach(([id], n) => { $(id).hidden = n !== at; });
    [...dots.children].forEach((dot, n) => dot.classList.toggle("here", n === at));
    look.setAttribute("aria-labelledby", pages[at][1]);
    $("first-look-back").disabled = at === 0;
    $("first-look-next").textContent = at === pages.length - 1 ? words.first_look_go : words.next;
    look.querySelector(".first-look-pages").scrollTop = 0;
  };
  turn(0);
  $("first-look-next").onclick = () => {
    if (at === pages.length - 1) return done();
    turn(at + 1);
    $("first-look-next").focus();
  };
  $("first-look-back").onclick = () => {
    turn(at - 1);
    ($("first-look-back").disabled ? $("first-look-next") : $("first-look-back")).focus();
  };
  // Every way out comes here, once (the browser's own close event does not
  // always come: Esc closes it here, not by the browser).
  let over = false;
  const done = () => {
    if (over) return;
    over = true;
    if (look.open) look.close();
    if (counts) body.append(counts);
    if (examples) body.append(examples);
    $("inside").classList.remove("beckon");  // Seen: the light goes for good.
    $("question").focus({ preventScroll: true });
    drawGuide();
  };
  look.addEventListener("cancel", (event) => { event.preventDefault(); done(); });
  look.addEventListener("close", done);
  // An example pressed fills the box (fill); then the box is what is next.
  look.addEventListener("click", (event) => {
    if (event.target.closest("#work-questions button")) done();
  });
  look.showModal();
  look.scrollTop = 0;  // From its heading, the button focused or not.
  drawGuide();
}

// --- the guide (the teacher, 11/6) ---

// For each state with one thing to press: where it is (null: not on screen
// now), whose words the bubble says, or lit: the thing itself lit instead
// (the bubble's choices, so no bubble covers the card being read).
// 直し53 段7 (52_scene_autumn_start: 「ここに書いて『聞く』を押そう」 hid the
// ways out's tags 霧島山・鹿児島県 and 県外・海外に出た人): over the box, slid
// along it, clear of the map's words (its point still on the box).
const GUIDE = {
  write: { at: () => $("question"), voices: () => [], sides: ["above", "below"],
    clear: () => [...document.querySelectorAll("#map-frame .map-around, #map-frame .home-names text, "
      + "#map-frame .place-names text, #map-frame .school-count, #map-look-label")] },
  card: { at: () => $("question"), words: "write", voices: () => [], sides: ["above", "below"],
    clear: () => GUIDE.write.clear() },
  // 直し45 段3: no box at one to one; the questions to pick, lit.
  one: { at: () => document.querySelector(".one-asks .one-ask:not(.one-finish)"), lit: true },
  // 直し48 (the screen check): never over the AI's questions (their robots, names, bubbles).
  // 直し50 段2: never over the people's words either (voices).
  // 直し52 段3 (ヒビキ, 1366×650: its left end over the AI's seat's blue frame): the frame kept clear too.
  // 直し53 段5 (ヒビキ, 52_ai_seat_1366x650: it hid the farmer's seat's mark):
  // the gathered seats' marks and the empty chairs kept clear too.
  table: { at: () => document.querySelector("#map-overlay .table-bubble:not(.unplaced)"), voices: peopleVoices,
    clear: () => [...document.querySelectorAll("#ai-seat-cards .ai-question"), $("now-line"), $("ai-seat"),
      ...document.querySelectorAll("#map-svg .token, #map-svg .chair")],
    sides: ["above", "below", "right", "left"] },
  pressed: { at: () => document.querySelector('.map-choices button[data-choice="card"]'), lit: true },
  // 直し46: never over the AI's seat's heading (「AI（町の人ではありません）」)
  // nor its note (「この問いは、AI が作りました。…」), nor over the AI's
  // questions (the other card's words): over the card when there is room
  // clear of them, else beside it, else under it; slid along the card, and
  // over as little of the people's bubbles as it can (the one pressed, the
  // one being read, least of all); narrower when nothing else is clear.
  answer_ai: { at: () => shown(document.querySelector("#ai-seat-cards .ai-question:not(:disabled)")) || shown($("ai-seat-open")),
    // 直し48 段2: the heading and the note are gone; each question (its
    // robot, its name and its bubble) kept clear; and (the screen check's
    // 差し戻し) the line at the top and the map's column, which the room
    // over the card now reaches.
    clear: () => [...document.querySelectorAll("#ai-seat-cards .ai-question"), $("now-line"),
      document.querySelector(".map-controls")],
    spare: () => [...document.querySelectorAll("#map-overlay .table-bubble:not(.unplaced):not(.ai)")],
    voices: peopleVoices,
    sides: ["above", "right", "left", "below"] },
  // 直し48 段3 (the teacher, 11/7: it went unseen): large, in two lines,
  // the second saying going on is fine too (「もっと話を聞きたい人は、…」), so
  // it is not taken for the one right next step; the button lit (once).
  after: { at: () => $("to-reflect"), more: "after_more", big: true },
};

// 直し50 段2 (ヒビキ: the sign hid a farmer's words): the people's words in
// their bubbles (the quotes' text) are never under 「吹き出しを1つ押してみよう」
// nor 「コーチとオブザーバーの問いはここ」. A place by the card first, else
// a free place by the map's edges or under the table, its point short; with
// none such, no sign rather than words hidden.
function peopleVoices() {
  return [...document.querySelectorAll("#map-overlay .table-bubble:not(.unplaced):not(.ai) .voice, #map-overlay .map-bubble .voice")];
}

// node if it is on screen (a box of its own), else null.
function shown(node) {
  if (!node) return null;
  const box = node.getBoundingClientRect();
  return box.width && box.height ? node : null;
}

function guideState() {
  // 直し53 段5: none while an answer is being written in the AI's seat (it
  // would lie over the box; what to do there is plain).
  if (state.aiAnswer) return "";
  return state.texts && state.texts.now_line ? nowState() : "";
}

// The bubble by what to press now, pointing at it: over it, or under it
// when there is no room over it. Hidden while nothing is to be pressed,
// while the first look is up, or with no words for it. Never pressed
// (pointer-events: none); lit once each time it says something new (not
// with motion reduced).
function drawGuide() {
  const guide = $("guide"), words = state.texts && state.texts.guide;
  const now = guideState();
  const spec = GUIDE[now];
  guideReach().hidden = true;  // 直し52 段3: drawn again below when the bubble is away from what it points at.
  // 直し52 段1: nothing while the camera comes in before the first look.
  const target = spec && !state.approaching && shown(spec.at());
  const lit = spec && spec.lit ? target : null;
  for (const node of document.querySelectorAll(".guide-here")) if (node !== lit) node.classList.remove("guide-here");
  if (lit) lit.classList.add("guide-here");
  // 「帰る前に、ひとこと」 lit while the sign points at it (直し48 段3).
  const glow = spec && spec.big ? target : null;
  for (const node of document.querySelectorAll(".guide-glow")) if (node !== glow) node.classList.remove("guide-glow");
  if (glow && !$("first-look").open) glow.classList.add("guide-glow");
  if (!words || !target || lit || $("first-look").open) {
    guide.hidden = true;
    guide.dataset.state = "";
    return;
  }
  if (guide.dataset.state !== now) {
    // Broken between phrases where it may be made narrower (直し46).
    if (spec.clear) $("guide-text").replaceChildren(phrased(words[spec.words || now]));
    else if (spec.more && words[spec.more]) {
      $("guide-text").replaceChildren(el("span", { class: "guide-main", text: words[spec.words || now] }),
        el("span", { class: "guide-more", text: words[spec.more] }));
    } else $("guide-text").textContent = words[spec.words || now];
    if (spec.big) guide.classList.add("big");
    else guide.classList.remove("big");
    guide.dataset.state = now;
    guide.classList.remove("fresh");
    void guide.offsetWidth;
    guide.classList.add("fresh");
  }
  guide.hidden = false;
  const box = target.getBoundingClientRect();
  const gap = 14, edge = 8, vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  // Over it when there is room, else under it; a state that keeps things
  // clear (直し46) has its bubble placed by guideSpot.
  guide.classList.remove("narrow");
  const wide = spec.clear && guideSpot(spec, box, true);
  const narrow = spec.clear && (!wide || wide.cost > 0) && guideSpot(spec, box, false);
  const spot = narrow && (!wide || narrow.cost < wide.cost) ? narrow : wide;
  if (spot === narrow && narrow) guide.classList.add("narrow");
  else guide.classList.remove("narrow");
  guide.classList.remove("far");
  // 直し50 段2: no place by it clear of the people's words: a free place
  // away from it (its point short), else no sign (never over their words).
  // Hidden so, it comes back unlit (no blink as it comes and goes).
  if (!spot && spec.voices) {
    const room = guideRoom(spec, box);
    if (!room) {
      guide.hidden = true;
      guide.classList.remove("fresh");
      return;
    }
    guide.classList.add("narrow", "far");
    pointGuide(guide, room, box);
    // 直し52 段3: its point reaches what it points at (the AI's seat: its frame).
    const frame = target.closest && target.closest("#ai-seat");
    return reachGuide(room, frame ? frame.getBoundingClientRect() : box);
  }
  const place = spot || (() => {
    guide.classList.remove("narrow");
    const w = guide.offsetWidth, h = guide.offsetHeight;
    const side = box.top - gap - h >= edge ? "above" : "below";
    return { side, w, h, top: side === "above" ? box.top - gap - h : Math.min(box.bottom + gap, vh - h - edge),
      left: clamp(box.left + box.width / 2 - w / 2, edge, vw - w - edge) };
  })();
  pointGuide(guide, place, box);
}

// 直し52 段3 (ヒビキ, 1366×650: 「コーチとオブザーバーの問いはここ」 far from
// the frame, its point short, and which it meant hard to tell): the bubble
// away from what it points at, a line of its colour from its edge to the
// nearest of what it points at, a dot there. Never pressed, never read out.
function guideReach() {
  let reach = $("guide-reach");
  if (!reach) {
    reach = el("div", { id: "guide-reach", class: "guide-reach", "aria-hidden": "true" });
    reach.hidden = true;
    document.body.append(reach);
  }
  return reach;
}

// The line never over the people's words nor the AI's questions (the
// screen check, 768×1024: it ran through two cards' quotes): from the
// nearest point of the frame's edge outward, the first way that crosses
// none of them; none such: no line (the bubble's short point, as before).
function reachGuide(place, to) {
  const reach = guideReach();
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const keep = [...peopleVoices(), ...document.querySelectorAll("#ai-seat-cards .ai-question")].map(shown).filter(Boolean)
    .map((n) => n.getBoundingClientRect());
  const crosses = (sx, sy, ex, ey) => {
    const steps = Math.ceil(Math.hypot(ex - sx, ey - sy) / 3);
    for (let k = 0; k <= steps; k++) {
      const x = sx + (ex - sx) * k / steps, y = sy + (ey - sy) * k / steps;
      if (keep.some((r) => x > r.left - 4 && x < r.right + 4 && y > r.top - 4 && y < r.bottom + 4)) return true;
    }
    return false;
  };
  const mx = place.left + place.w / 2, my = place.top + place.h / 2;
  const near = clamp(mx, to.left + 12, to.right - 12);
  const tries = [near];
  for (let d = 16; d < to.right - to.left; d += 16) tries.push(near - d, near + d);
  for (const tx of tries) {
    if (tx < to.left + 12 || tx > to.right - 12) continue;
    const ex = tx, ey = clamp(my, to.top, to.bottom);
    const sx = clamp(ex, place.left + 12, place.left + place.w - 12), sy = clamp(ey, place.top, place.top + place.h);
    const length = Math.hypot(ex - sx, ey - sy);
    if (length < 24) return;
    if (crosses(sx, sy, ex, ey)) continue;
    Object.assign(reach.style, { left: `${Math.round(sx)}px`, top: `${Math.round(sy) - 2}px`, width: `${Math.round(length)}px`,
      transform: `rotate(${Math.atan2(ey - sy, ex - sx)}rad)` });
    reach.hidden = false;
    return;
  }
}

// The bubble at place { side, left, top, w, h }, its point at box.
function pointGuide(guide, place, box) {
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  guide.dataset.side = place.side;
  guide.style.left = `${Math.round(place.left)}px`;
  guide.style.top = `${Math.round(place.top)}px`;
  // The bubble's point at what it points at, even when the bubble is kept
  // inside the window: along its foot or head, or its side.
  guide.style.setProperty("--point", place.side === "above" || place.side === "below"
    ? `${Math.round(clamp(box.left + box.width / 2 - place.left, 16, place.w - 16))}px`
    : `${Math.round(clamp(box.top + box.height / 2 - place.top, 16, place.h - 16))}px`);
}

// 直し50 段2: a free place for the bubble (narrow) away from what it points
// at, inside the map's frame and the window: over none of what is kept clear,
// the people's words, nor what it points at; first clear of the bubbles and
// the split's heading too, else of their words only. Of those, the one over
// least of the names on the map, the seats' titles and marks and the
// scenery's label (a small matter), then the nearest. Its side faces what it
// points at.
// None such: null.
function guideRoom(spec, box) {
  const guide = $("guide");
  guide.classList.add("narrow");
  const w = guide.offsetWidth, h = guide.offsetHeight;
  const edge = 8, step = 12, vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const frameNode = shown(document.querySelector("#map-overlay"));
  const frame = frameNode ? frameNode.getBoundingClientRect() : { left: 0, top: 0, right: vw, bottom: vh };
  const area = { left: Math.max(edge, frame.left), top: Math.max(edge, frame.top),
    right: Math.min(vw - edge, frame.right), bottom: Math.min(vh - edge, frame.bottom) };
  const rects = (nodes) => (nodes || []).map(shown).filter(Boolean).map((n) => n.getBoundingClientRect());
  const over = (left, top, k) => Math.max(0, Math.min(left + w, k.right) - Math.max(left, k.left))
    * Math.max(0, Math.min(top + h, k.bottom) - Math.max(top, k.top));
  // The people's words with a margin for the bubble's point.
  const grow = (k, by) => ({ left: k.left - by, top: k.top - by, right: k.right + by, bottom: k.bottom + by });
  const hard = [...rects(spec.clear()), ...rects(spec.voices()).map((k) => grow(k, 6)), box];
  const bubbles = rects([...document.querySelectorAll("#map-overlay .table-bubble:not(.unplaced), #map-overlay .map-bubble, #map-overlay .split-tag, #map-overlay .map-choices")]);
  const small = rects([...document.querySelectorAll("#map-overlay .map-around, #map-overlay .table-label:not(.unplaced), #map-overlay .map-look-label, #map-overlay .map-compass, #map-overlay .seat-press, #map .points .pt .shape")]);
  const cx = box.left + box.width / 2, cy = box.top + box.height / 2;
  for (const avoid of [[...hard, ...bubbles], hard]) {
    let best = null;
    for (let top = area.top; top + h <= area.bottom; top += step) {
      for (let left = area.left; left + w <= area.right; left += step) {
        if (avoid.some((k) => over(left, top, k) > 0)) continue;
        const cost = small.reduce((sum, k) => sum + over(left, top, k), 0);
        const far = Math.hypot(left + w / 2 - cx, top + h / 2 - cy);
        if (!best || cost < best.cost || (cost === best.cost && far < best.far)) best = { left, top, cost, far };
      }
    }
    if (best) {
      const { left, top } = best;
      // Beside it when clear of it across (its point then reaches it along the
      // row it is in), else over or under it.
      const side = left >= box.right ? "right" : left + w <= box.left ? "left" : top + h <= box.top ? "above" : "below";
      return { side, left, top, w, h };
    }
  }
  return null;
}

// 直し46: where the bubble goes for a state that keeps things clear. Each of
// the state's sides in turn, at the middle of what it points at and then
// slid along it (its point still on it), inside the window and over none
// of what is kept clear; of those, the first over none of the spared (the
// people's bubbles), else the one over least of them (the one marked, or
// pressed and still holding the keyboard, counts four times), with how
// much it is over (cost). None such: null. drawGuide tries it narrower too
// when wide it is over some, or nowhere is clear, and keeps the one over less.
function guideSpot(spec, box, wide) {
  const guide = $("guide");
  guide.classList.toggle("narrow", !wide);
  const w = guide.offsetWidth, h = guide.offsetHeight;
  const gap = 14, edge = 8, step = 8, vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const boxes = (nodes) => (nodes || []).map(shown).filter(Boolean)
    .map((n) => ({ rect: n.getBoundingClientRect(),
      weight: n.classList && (n.classList.contains("marked") || n === document.activeElement) ? 4 : 1 }));
  // 直し50 段2: the people's words kept clear as the rest is.
  const keep = boxes([...spec.clear(), ...(spec.voices ? spec.voices() : [])]), spare = boxes(spec.spare && spec.spare());
  const over = (p, k) => Math.max(0, Math.min(p.left + w, k.right) - Math.max(p.left, k.left))
    * Math.max(0, Math.min(p.top + h, k.bottom) - Math.max(p.top, k.top));
  const spots = [];
  for (const side of spec.sides || ["above", "below"]) {
    const across = side === "above" || side === "below";
    const mid = across ? clamp(box.left + box.width / 2 - w / 2, edge, vw - w - edge)
      : clamp(box.top + box.height / 2 - h / 2, edge, vh - h - edge);
    const [lo, hi] = across ? [box.left + 12 - (w - 16), box.right - 28] : [box.top + 12 - (h - 16), box.bottom - 28];
    const slides = [mid];
    for (let v = Math.ceil(lo); v <= hi; v += step) slides.push(v);
    for (const v of slides) {
      spots.push(across ? { side, w, h, left: v, top: side === "above" ? box.top - gap - h : box.bottom + gap }
        : { side, w, h, top: v, left: side === "right" ? box.right + gap : box.left - gap - w });
    }
  }
  let best = null, least = Infinity;
  for (const p of spots) {
    if (p.top < edge || p.top + h > vh - edge || p.left < edge || p.left + w > vw - edge) continue;
    if (keep.some((k) => over(p, k.rect) > 0)) continue;
    const cost = spare.reduce((sum, k) => sum + over(p, k.rect) * k.weight, 0);
    if (cost === 0) return { ...p, cost };
    if (cost < least) [best, least] = [{ ...p, cost }, cost];
  }
  return best;
}
// What it points at moves with the window, the map and its bubbles: kept by it.
window.addEventListener("resize", drawGuide);
setInterval(() => { if (!$("guide").hidden || GUIDE[guideState()]) drawGuide(); }, 400);

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
  setupInside();
  setupMapSkip();
  $("drawer").addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !drawerOpen()) return;
    event.preventDefault();
    event.stopPropagation();
    closeDrawer();
  });
}

// The map's first stop for the keyboard (直し41 段2): seen only when it is
// there; pressed, the keyboard goes past the points to the first thing that
// can be pressed in the map's column. The points' own order is as before.
function setupMapSkip() {
  const skip = $("map-skip");
  skip.textContent = state.texts.map_skip;
  skip.addEventListener("click", () => {
    const first = [...document.querySelectorAll(".map-bar button, .map-bar summary")]
      .find((node) => !node.disabled && node.offsetParent !== null && !node.closest("[hidden]"));
    if (first) first.focus();
  });
}

// With no map, whose words are in stands in the page, before the AI's seat,
// as it did before it went into the map's column (直し41 段2).
function placeInside() {
  if ($("map").hidden && $("inside").closest("#map")) $("ai-seat").before($("inside"));
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
  if (state.doneKind === "split") hideDone();  // Whom it writes to changed: the split's line goes (直し40-1).
  if (state.to) state.drafts[draftKey(state.to)] = box.value;
  state.to = next;
  const words = state.texts.input_to;
  // 直し48 段3: which AI's question it answers, by its name (「コーチの問いに
  // 答える」), and that question right over the box.
  const roleWord = next.kind === "ai" && words[`ai_${next.role}`];
  const label = next.kind === "seat" ? words.seat.replace("{seat}", seatName(next.seatId)) : roleWord || words[next.kind];
  const asked = next.kind === "ai" && (state.aiAsked || {})[`${next.roundNo}:${next.role}`];
  $("input-to-asked").textContent = asked && words[`asked_${next.role}`] ? words[`asked_${next.role}`] + asked : "";
  $("input-to-asked").hidden = !$("input-to-asked").textContent;
  // Never broken inside a word nor its （…） (直し33-5: 「架空の川／1」).
  $("input-to-label").replaceChildren(phrased(label));
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
// clears the words that went, never another's. The AI's seat's 送る too
// (直し53 段5): one send at a time.
function sending() {
  return $("ask-button").disabled || $("ai-answer-send").disabled;
}

function askSeat(seatId) {
  if (sending()) return;
  hideDone();
  setTo({ kind: "seat", seatId });
}

// 「答える」 on an AI's question: its answer is written in the AI's seat,
// right under the questions (直し53 段5, the teacher, 11/7: the box at the
// foot was far from the frame). The box at the foot stays the town's.
function answerTo(roundNo, role) {
  if (sending()) return;
  foldAiSeat(false);  // Answering it: open (直し37-2).
  hideDone();
  keepAiDraft();
  state.aiAnswer = { roundNo, role };
  markAiChosen(role);
  const text = $("ai-answer-text");
  text.value = state.drafts[draftKey({ kind: "ai", roundNo, role })] || "";
  // Read out as whose question it answers (input_to: 「コーチの問いに答える」).
  text.setAttribute("aria-label", state.texts.input_to[`ai_${role}`] || state.texts.input_to.ai);
  // Right under the question picked (the room under it), inside the frame.
  const form = $("ai-answer"), picked = document.querySelector(`#ai-seat-cards .ai-question[data-role="${role}"]`);
  if (picked) picked.after(form);
  form.hidden = false;
  $("ai-seat-pick").hidden = true;
  setNow();
  // In the seat's own scroll, never the page's: the box and its buttons in
  // view, the question over it as far as there is room.
  const seat = $("ai-seat");
  if (seat.scrollHeight > seat.clientHeight) seat.scrollTop = Math.max(0, form.offsetTop + form.offsetHeight - seat.clientHeight + 8);
  text.focus({ preventScroll: true });
}

// What was written to the open question kept for when it is picked again.
function keepAiDraft() {
  if (state.aiAnswer) state.drafts[draftKey({ kind: "ai", ...state.aiAnswer })] = $("ai-answer-text").value;
}

// やめる (or Esc in it): the box goes, its words kept; the question picked no more.
function closeAiAnswer({ focus = true } = {}) {
  if (!state.aiAnswer) return;
  const role = state.aiAnswer.role;
  keepAiDraft();
  state.aiAnswer = null;
  $("ai-answer").hidden = true;
  markAiChosen(null);
  showAiPick();
  setNow();
  const back = document.querySelector(`#ai-seat-cards .ai-question[data-role="${role}"]`);
  if (focus && back) back.focus({ preventScroll: true });
}

// The quiet line under the questions, while one is still to be picked.
function showAiPick() {
  const open = [...document.querySelectorAll("#ai-seat-cards .ai-question")].some((button) => !button.disabled);
  const words = state.texts.ai_answer_words;
  $("ai-seat-pick").textContent = words.pick;
  $("ai-answer-send").textContent = words.send;
  $("ai-answer-cancel").textContent = words.cancel;
  $("ai-seat-pick").hidden = !open || Boolean(state.aiAnswer);
}

function backToEveryone() {
  if (!sending() && state.to.kind !== "all") setTo({ kind: "all" });
}

function showDone(text, kind = "") {
  $("input-done").textContent = text;
  $("input-done").hidden = false;
  state.doneKind = kind;
}
function hideDone() {
  $("input-done").hidden = true;
  state.doneKind = "";
}

// One press sends once: the button waits while it is sent (直し31-2).
async function send(event) {
  event.preventDefault();
  const button = $("ask-button");
  if (button.disabled || !$("question").value.trim()) return;
  hideDone();
  // At one to one there is no box (直し45 段3): the questions to pick only.
  if (state.now.one) return;
  if (state.to.kind === "seat") return sendCard(state.to.seatId);
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

const oneOpen = (seatId) => call("/api/one/open", { seat_id: seatId });
const oneAsk = (seatId, item) => call("/api/one/ask", { seat_id: seatId, item });
// コーチ（AI） at one to one (直し45 段3): no sign in the middle (the
// questions can be picked meanwhile); its board has three dots.
const oneCoach = (seatId, askNo) => call("/api/one/coach", { seat_id: seatId, ask_no: askNo });
const oneCoachAnswer = (seatId, askNo, body) => call("/api/one/coach_answer", { seat_id: seatId, ask_no: askNo, ...body });

// 「ありがとうございました」 (直し34-5): the seat kept as thanked, its mark on the map.
async function oneThanks(seatId) {
  const done = await call("/api/one/thanks", { seat_id: seatId });
  for (const id of done.thanked) state.thanked.add(id);
  return done;
}

// To an AI's question: the answer starts the next round (直し29-1), sent
// from the AI's seat (直し53 段5) as it was from the box at the foot.
async function sendAnswer(roundNo, role) {
  const button = $("ai-answer-send");
  const answer = $("ai-answer-text").value.trim();
  if (button.disabled || !answer) return;
  button.disabled = true;
  hideMessage();
  setNow({ asking: true });
  try {
    const round = await call("/api/coach_answer", { round: roundNo, role, answer, after_notice: state.needsShown },
      { wait: "ask" });
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
    $("ai-answer-text").value = "";
    delete state.drafts[`ai:${roundNo}:${role}`];
    state.aiAnswer = null;
    $("ai-answer").hidden = true;
    $("ai-seat-pick").hidden = true;
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
  // The map's quiet glow stops as the question goes (直し41の続き).
  onMap((map) => map.asked());
  // The waiting line is the one at the top now (直し31-5).
  hideMessage();
  setNow({ asking: true });
  try {
    const round = await call("/api/ask", { question }, { wait: "ask" });
    setNow({ asking: false });
    // The counts and examples shut once a question is sent; they open again.
    $("inside-fold").open = false;
    $("inside").classList.remove("beckon");
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

// 行き止まりの道案内 (直し45 段4): under a question no seat answered, the
// card made and the ways on (by kind of talk, picked by code). A way pressed:
// up to three seats' words of that kind at the table, as a round of its own.
function showWays(round) {
  const box = $("ways");
  const ways = round.ways || [];
  box.hidden = !round.ways_notice;
  if (box.hidden) return;
  $("ways-notice").textContent = round.ways_notice;
  $("ways-buttons").replaceChildren(...ways.map((way) => {
    const press = el("button", { type: "button", class: "way", text: way.text });
    press.dataset.kind = way.kind;
    press.addEventListener("click", () => takeWay(round.round, way.kind, press));
    return press;
  }));
}

async function takeWay(roundNo, kind, press) {
  if (press.disabled) return;
  for (const other of $("ways-buttons").children) other.disabled = true;
  try {
    const round = await call("/api/direction", { round: roundNo, kind });
    press.remove();
    renderRound(round);
  } catch (error) {
    showMessage(sendFailed(error));
  } finally {
    for (const other of $("ways-buttons").children) other.disabled = false;
    if (!$("ways-buttons").children.length) $("ways").hidden = true;
  }
}

function sendFailed(error) { return state.texts.send_failed.replace("{error}", error.message); }
function showMessage(text) { $("ask-message").textContent = text; $("ask-message").hidden = false; }
function hideMessage() { $("ask-message").hidden = true; }

function renderRound(round) {
  if (!state.firstQuestion) state.firstQuestion = round.question;
  // A new round: its seats light (map.js says when they are done). Its
  // splits not pressed yet (直し40-1).
  state.splitOpen = round.splits.length > 0;
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
  box.append(el("p", { class: "round-question", text: round.question || round.way || "" }));
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
  if (!round.way) showWays(round);  // 行き止まりの道案内 (直し45 段4).
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
    band = await call("/api/coach", { round: roundNo }, { wait: "coach" });
  } catch (error) {
    return;  // An extra at the round's end.
  }
  if (!band.cards.length) return;
  const part = el("section", { class: "ai-band" });
  // The line asking for one answer is the one at the top (直し31-5), not
  // over the cards as well (直し30の続き-0): said once, in one place.
  if (!band.answered && roundNo === state.lastRound) setNow({ band: true });
  for (const card of band.cards) {
    (state.aiAsked ||= {})[`${roundNo}:${card.role}`] = card.question;
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

// コーチ and オブザーバー, out of the round table's ring, with the newest
// round's two questions. Pressed, the box at the foot answers that one.
// 直し48 段2 (the teacher, 11/7): no heading 「AI（町の人ではありません）」
// nor the note 「この問いは、AI が作りました。…」 (the first look says both
// are AI); each question in a bubble from its robot, its name with （AI）
// right by the robot (style.css: コーチ top left, オブザーバー bottom right).
// Folded, the head is their robots; the seat is named by their names.
function renderAiSeat(roundNo, band) {
  const seat = $("ai-seat");
  $("ai-seat-label").textContent = band.cards.map((card) => card.label).join("・");
  $("ai-seat-faces").replaceChildren(...band.cards.map((card) => EbinoRobot.make(card.role)));
  const cards = $("ai-seat-cards");
  $("ai-seat-pick").after($("ai-answer"));  // Out of the cards before they go (直し53 段5).
  cards.replaceChildren();
  for (const card of band.cards) {
    // Its role's robot (直し47, robot.js) just before its name; its words in a bubble from it (直し48).
    const button = el("button", { type: "button", class: "ai-question", "data-role": card.role, "data-round": roundNo },
      el("span", { class: "who" }, EbinoRobot.make(card.role), el("span", { class: "who-name", text: card.label })),
      el("span", { class: "words", text: card.question }));
    button.addEventListener("click", () => answerTo(roundNo, card.role));
    if (band.answered) {
      button.disabled = true;
      if (band.answered === card.role) button.classList.add("answered");
    }
    cards.append(button);
  }
  // A new round's questions: no box open, the line asking to pick one.
  state.aiAnswer = null;
  $("ai-answer").hidden = true;
  showAiPick();
  seat.hidden = false;
  $("ai-seat-open").onclick = openAiSeat;
  foldAiSeat(false);  // A round's questions: open while the meeting is out (直し37-2).
  mapMoved();  // The map's cards keep off it.
}

// Back at the map the AI's seat is folded (直し37-2): its heading and the
// button that opens it, at the same corner; its place on the map and the
// upright screen's band under the map stay as they were, so the meeting's
// bubbles and the map do not move when it comes out again. The button
// (named by the heading) opens it, the keyboard to its first question.
function foldAiSeat(fold) {
  const seat = $("ai-seat"), open = $("ai-seat-open");
  if (!seat || !open) return;
  seat.classList.toggle("folded", fold);
  open.hidden = !fold;
  open.setAttribute("aria-expanded", String(!fold));
}

function openAiSeat() {
  foldAiSeat(false);
  const first = document.querySelector("#ai-seat-cards .ai-question:not(:disabled)") || document.querySelector("#ai-seat-cards .ai-question");
  if (first) first.focus({ preventScroll: true });
}

// The question being answered in the AI's seat, lit (aria-pressed too); none, none.
function markAiChosen(role) {
  for (const button of $("ai-seat-cards").querySelectorAll(".ai-question")) {
    const chosen = Boolean(state.aiAnswer) && button.dataset.role === role;
    button.classList.toggle("chosen", chosen);
    button.setAttribute("aria-pressed", String(chosen));
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
      renderAsked(roundNo, box, await call("/api/ask_seat", { round: roundNo }, { wait: "ask_seat" }));
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
  bubbleOpened(utteranceId);
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
    el("button", { type: "button", class: "quiet", text: SPLIT_PRESS, onclick: () => pressSplit(roundNo, split.index) }));
}

// A split's heading, pressed where it is seen (直し40-1: the tag on the flat
// map, the heading under the round table) or in the drawer: the box goes
// back to writing to everyone (whatever was being written to a seat or an
// AI's question stays in state.drafts), then, as before, the heading goes
// into the box as it is (SPEC 5-1) and the keyboard with it; one line over
// the box says it may be put in one's own words.
const SPLIT_PRESS = "この割れ目を次の問いにする";

function splitLabel(heading) {
  return `${SPLIT_PRESS}：${shownQuotes(heading)}`;
}

async function pressSplit(roundNo, index) {
  if (sending()) return;
  if (state.to.kind !== "all") setTo({ kind: "all" }, { focus: false });
  let heading;
  try {
    ({ heading } = await call("/api/split", { round: roundNo, index }));
  } catch (error) {
    showMessage(sendFailed(error));
    return;
  }
  if (roundNo === state.lastRound) state.splitOpen = false;
  fill(heading);
  showDone(state.texts.input_done.split, "split");
  setNow();
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

// --- 帰る前に、ひとこと (直し38) ---

// The step at the top and the button to it say 帰る前に、ひとこと; the line
// under the steps after a round says the same button's name; on its own
// screen, no line (its own steps are there).
function useHitokotoName(texts) {
  const words = state.hitokoto.words;
  // The step keeps its mark (④) from texts/now_steps.tsv; its name is the new one.
  for (const step of texts.now_steps) if (step.id === "reflect") step.text = step.text.replace(/^(\S+\s+)?.*$/, `$1${words.name}`);
  texts.now_line.after = { ...texts.now_line.after, text: words.now_after };
  texts.now_line.reflect = { ...texts.now_line.reflect, text: "" };
  $("to-reflect").textContent = words.name;
}

// A bubble opened (its choices, or its paragraph): the people on today's
// map come from these too, the one opened last first.
// --- 今日の道すじ (直し45 段2) ---

// After these the trail is asked for again (GET /api/trail: the record's
// steps, in turn; no model). Only what the student wrote or chose is on it.
const TRAIL_AFTER = new Set(["/api/ask", "/api/coach_answer", "/api/one/ask", "/api/one/coach_answer", "/api/card",
  "/api/more_card", "/api/direction", "/api/trail/opened"]);
const trailView = { items: [], open: false };
// Shut at first where the column has no room (1366×650) and upright.
const TRAIL_SHUT_AT_FIRST = "(max-height: 700px), (orientation: portrait)";

function setupTrail() {
  const words = state.texts.trail_words;
  if (!words) return;
  $("trail-open").textContent = words.open;
  Object.assign(afterCall, { paths: TRAIL_AFTER, then: refreshTrail });
  setTrailOpen(!(window.matchMedia && window.matchMedia("(max-height: 700px), (orientation: portrait)").matches));
  $("trail-open").addEventListener("click", () => setTrailOpen(!trailView.open));
  window.addEventListener("resize", placeTrail);
  $("trail").addEventListener("keydown", (event) => {
    if (event.key === "Escape" && trailView.open && window.matchMedia(TRAIL_SHUT_AT_FIRST).matches) {
      event.stopPropagation();
      setTrailOpen(false);
      $("trail-open").focus();
    }
  });
}

function setTrailOpen(open) {
  trailView.open = open;
  $("trail-open").setAttribute("aria-expanded", String(open));
  $("trail-list").hidden = !open;
  placeTrail();
  if (open) $("trail-list").scrollTop = $("trail-list").scrollHeight;  // The newest at the foot.
}

// Shut at first (1366×650, upright), opened it stands by its button: beside
// it over the map's right edge, its foot level with the button's; upright,
// over the button. Never over the top line or the box at the foot.
function placeTrail() {
  const list = $("trail-list");
  const folded = window.matchMedia && window.matchMedia(TRAIL_SHUT_AT_FIRST).matches;
  if (!folded || list.hidden) {
    for (const key of ["top", "bottom", "right", "maxHeight"]) list.style[key] = "";
    return;
  }
  const at = $("trail-open").getBoundingClientRect();
  const top = $("now-line").getBoundingClientRect().bottom + 8;
  const upright = window.matchMedia("(orientation: portrait)").matches;
  const foot = upright ? at.top - 6 : at.bottom;
  Object.assign(list.style, { top: "auto", bottom: `${Math.round(window.innerHeight - foot)}px`,
    right: `${Math.round(upright ? window.innerWidth - at.right : window.innerWidth - at.left + 10)}px`,
    maxHeight: `${Math.max(140, Math.round(foot - top))}px` });
}

async function refreshTrail() {
  try {
    const response = await fetch("/api/trail");
    if (!response.ok) return;
    trailView.items = (await response.json()).items || [];
  } catch (error) {
    return;  // As it was.
  }
  renderTrail();
}

// A bubble pressed: one step on the trail (a light request, no model).
function trailOpened(roundNo, utteranceId) {
  call("/api/trail/opened", { round: roundNo, utterance_id: utteranceId }).catch(() => {});
}

// One item: its small line (what it was), then the words. A question that
// changed has 「ここで問いが変わった」 over it, and a line in the lamp's colour
// goes back to the nearest thing heard before it. The AI's questions in the
// AI's colour and shape with its name, never as a person's.
function trailItem(item, words) {
  const li = el("li", { class: `trail-item trail-${item.kind}`, "data-n": String(item.n) });
  // A seat's title is never broken inside its （…） (as everywhere, 直し33-5).
  const small = (text) => el("span", { class: "trail-small" }, phrased(text));
  if (item.kind === "question") {
    if (item.changed) li.append(el("span", { class: "trail-turn", text: words.changed }));
    li.append(small(words.question), el("span", { class: "trail-text", text: item.text }));
    li.append(small(item.silent ? words.silent : item.lit.join("・")));
  } else if (item.kind === "opened") {
    const press = el("button", { type: "button", class: "trail-press" },
      small(`${words.opened}　${item.who}`), item.label ? el("span", { class: "trail-label", text: item.label }) : null);
    press.addEventListener("click", () => openParagraph(item.utterance_id, item.who, press).catch(() => {}));
    li.append(press);
  } else if (item.kind === "one_ask") {
    li.append(small(`${words.one_ask}　${item.who}`), el("span", { class: "trail-text", text: item.text }));
    if (item.label) li.append(el("span", { class: "trail-label", text: item.label }));
  } else if (item.kind === "ai_answer" || item.kind === "one_coach") {
    li.classList.add("trail-ai");
    const answer = item.declined ? words.declined : [item.choice, item.answer].filter(Boolean).join("　");
    li.append(el("span", { class: "trail-ai-name", text: item.ai_label }), el("span", { class: "trail-text", text: item.question }));
    if (item.answered !== false) li.append(el("span", { class: "trail-answer" }, small(words.answer), el("span", { text: answer })));
  } else if (item.kind === "card") {
    li.append(small([words.card, item.who].filter(Boolean).join("　")), el("span", { class: "trail-text", text: item.text }));
  } else if (item.kind === "direction") {
    li.append(small(words.direction), el("span", { class: "trail-text", text: item.text }));
  }
  return li;
}

function renderTrail() {
  const words = state.texts.trail_words, items = trailView.items;
  if (!words) return;
  $("trail").hidden = !items.length;
  // Where the question changed: from the step heard to the new question.
  const spans = items.filter((item) => item.changed && item.came_from != null).map((item) => [item.came_from, item.n]);
  const list = $("trail-list");
  list.replaceChildren(...items.map((item) => {
    const li = trailItem(item, words);
    if (spans.some(([from, to]) => item.n >= from && item.n <= to)) li.classList.add("on-turn");
    if (spans.some(([from]) => item.n === from)) li.classList.add("turn-from");
    if (item.changed) li.classList.add("turn-to");
    return li;
  }));
  list.scrollTop = list.scrollHeight;
}

function bubbleOpened(utteranceId) {
  state.opened = state.opened.filter((id) => id !== utteranceId);
  state.opened.push(utteranceId);
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
  if (state.reflect === "hitokoto") {
    EbinoHitokoto.open({ call, state, setNow, sendFailed, showBackToStart, shownQuotes });
    return;
  }
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
    result = await call("/api/reflect/begin", { changed, now_question: nowQuestion }, { wait: "reflect" });
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
    showSubject((await call("/api/subject", {}, { wait: "subject" })).subject);
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
  const go = () => window.location.replace(window.location.pathname);
  // 直し54w (the teacher, 11/8): back to the first screen with a little
  // ending: the night closes over the page and the title comes up in the
  // lamp's light (style.css .back-curtain), then the page is read afresh.
  // Motion reduced: straight back, as before.
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return go();
  const curtain = document.createElement("div");
  curtain.className = "back-curtain";
  curtain.setAttribute("aria-hidden", "true");
  const title = document.createElement("p");
  title.className = "back-curtain-title";
  title.textContent = document.querySelector(".masthead h1")?.textContent || "";
  curtain.append(title);
  document.body.append(curtain);
  setTimeout(go, 1600);
}

$("ask-form").addEventListener("submit", send);
// 「聞く」 pressed (直し41の続き): one small ring goes out from it and is gone
// (CSS, with motion not reduced only; no bounce).
$("ask-button").addEventListener("click", (event) => {
  const button = event.currentTarget;
  button.classList.remove("rang");
  void button.offsetWidth;
  button.classList.add("rang");
});
$("ask-button").addEventListener("animationend", (event) => event.currentTarget.classList.remove("rang"));
$("input-to-clear").addEventListener("click", backToEveryone);
// 直し53 段5: the AI's question answered in its seat.
$("ai-answer").addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.aiAnswer) sendAnswer(state.aiAnswer.roundNo, state.aiAnswer.role);
});
$("ai-answer-cancel").addEventListener("click", () => closeAiAnswer());
$("ai-answer-text").addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    closeAiAnswer();
  }
});
// The box emptied: the split's line goes with what it was about (直し40-1).
$("question").addEventListener("input", () => {
  if (state.doneKind === "split" && !$("question").value.trim()) hideDone();
});
$("question").addEventListener("keydown", (event) => {
  // At one to one, Esc goes back to the table (map.js), the box with it (直し34-3).
  if (event.key === "Escape" && state.to.kind !== "all" && !state.now.one) {
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
