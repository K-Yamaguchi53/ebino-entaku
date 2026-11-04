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
  $("lab-question").textContent = data.texts.lab_question;
  for (const [key, label] of Object.entries(data.labs)) {
    $("lab-choices").append(el("button", { type: "button", class: "lab-choice", "aria-pressed": "false",
      onclick: (event) => start(key, event.currentTarget) }, phrased(label)));
  }
  $("heavy-talk").textContent = data.texts.heavy_talk_notice;
  $("question").placeholder = "例：" + data.texts.input_example;
  $("purpose-heading").textContent = data.texts.purpose_heading;
  for (const text of data.texts.work_questions) {
    $("work-questions").append(el("button", { type: "button", text, onclick: () => fill(text) }));
  }
  renderSeats();
  // The map over the seat list (map.js). No map, or one that fails to draw:
  // the seat list alone, as before.
  // What the map may use: the round's own ways to a quote's paragraph, its
  // mark, a seat's question card and the quote's card (直し26-2).
  const lent = { state, cardEntry, renderSeats, paragraph: paragraphOf, mark: markQuote, openCard: openCardFor,
    readBelow, shownQuotes, phrased, answerForm };
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
  onMap((map) => map.show());  // Draws the rim and the river once the map is on screen.
  renderPurposes(data.purposes);
  $("question").focus();
}

// --- the opening (直し30-3) ---

// Once a Lab is picked: over the dark map a paper plane drawn in lines takes
// off from the school's mark (or the lower left), flies a loose S, nose to
// its way and leaning into its turns with a thin trail that fades at once,
// slows and lands where the round table opens; the lamp's light spreads
// once in a ring, the seats' points lighting nearest first, and the title
// comes and goes up toward the question box. Under 3 seconds; 「とばす」,
// Enter or Esc ends it at once. No flashing, the screen never shakes.
const OPENING = { fly: 1400, land: 600, title: 800 };
let openingRun = null;

// Starts it and returns a promise kept when it has ended (or at once, with
// no map on screen to fly over: then null).
function playOpening() {
  if (typeof EbinoMap === "undefined" || $("map").hidden) return null;
  $("start").hidden = true;
  $("table").hidden = false;
  $("table").classList.add("opening-on");
  onMap((map) => map.show());
  const frame = $("map-frame");
  const box = frame.getBoundingClientRect();
  if (!box.width || !box.height || $("map").hidden) {
    $("table").classList.remove("opening-on");
    return null;
  }
  $("map").scrollIntoView({ block: "nearest" });
  const w = box.width, h = box.height;
  const end = [w / 2, h / 2];
  // From the school's mark when it is on the map in sight; else the lower left.
  let from = [Math.min(48, w * 0.08), h - Math.min(48, h * 0.08)];
  const school = document.querySelector("#map-svg .school > :not(text)");
  if (school) {
    const s = school.getBoundingClientRect();
    const at = [s.left + s.width / 2 - box.left, s.top + s.height / 2 - box.top];
    if (s.width && at[0] > 0 && at[0] < w && at[1] > 0 && at[1] < h) from = at;
  }
  const points = [...document.querySelectorAll("#map-svg .pt")].map((node) => {
    const p = node.getBoundingClientRect();
    return { node, d: Math.hypot(p.left + p.width / 2 - box.left - end[0], p.top + p.height / 2 - box.top - end[1]) };
  });
  const far = Math.max(1, ...points.map((p) => p.d));
  for (const p of points) p.node.style.opacity = ".2";
  $("opening-title").textContent = document.querySelector(".masthead h1").textContent;
  $("opening-skip").textContent = state.texts.opening_skip;
  $("opening").hidden = false;
  $("opening-bar").hidden = false;
  $("map-frame").inert = true;  // The keyboard goes to 「とばす」, not the points behind.
  const run = { from, end, w, h, points, far, ring: Math.hypot(w, h) * 0.42, trail: [], last: null, lean: 0, frame: 0 };
  openingRun = run;
  return new Promise((done) => {
    run.done = done;
    const began = performance.now();
    const step = (now) => {
      if (openingRun !== run) return;
      const t = now - began;
      drawOpening(run, t);
      if (t >= OPENING.fly + OPENING.land + OPENING.title) return finishOpening(run);
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
    $("opening-skip").focus();
    run.frame = requestAnimationFrame(step);
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
  const keep = (x, y) => (run.w ? [Math.max(24, Math.min(run.w - 24, x)), Math.max(24, Math.min(run.h - 24, y))] : [x, y]);
  const c1 = keep(x0 + dx / 3 + nx, y0 + dy / 3 + ny), c2 = keep(x0 + dx * 2 / 3 - nx, y0 + dy * 2 / 3 - ny);
  const v = 1 - u;
  const at = (a, b, c, d) => v * v * v * a + 3 * v * v * u * b + 3 * v * u * u * c + u * u * u * d;
  const slope = (a, b, c, d) => 3 * v * v * (b - a) + 6 * v * u * (c - b) + 3 * u * u * (d - c);
  return { x: at(x0, c1[0], c2[0], x3), y: at(y0, c1[1], c2[1], y3),
    a: Math.atan2(slope(y0, c1[1], c2[1], y3), slope(x0, c1[0], c2[0], x3)) };
}

// The opening as it is t ms in.
function drawOpening(run, t) {
  const plane = $("opening-plane"), trail = $("opening-trail"), ring = $("opening-ring"), title = $("opening-title");
  const fly = Math.min(1, t / OPENING.fly);
  // Slowing down to land: fast at first, the last stretch gently.
  const u = 1 - Math.pow(1 - fly, 2.2);
  const p = planeAt(run, u);
  if (run.last !== null) {
    let turn = p.a - run.last;
    turn = Math.atan2(Math.sin(turn), Math.cos(turn));
    run.lean += (Math.min(0.45, Math.abs(turn) * 14) - run.lean) * 0.25;
  }
  run.last = p.a;
  const deg = p.a * 180 / Math.PI;
  plane.setAttribute("transform", `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) rotate(${deg.toFixed(1)}) scale(1 ${(1 - run.lean).toFixed(3)})`);
  plane.style.opacity = t < OPENING.fly + OPENING.land ? "1"
    : String(Math.max(0, 1 - (t - OPENING.fly - OPENING.land) / (OPENING.title * 0.5)));
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
    for (const point of run.points) if (point.d / run.far <= k) point.node.style.opacity = "";
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

// --- asking ---

async function ask(event) {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;
  const button = $("ask-button");
  button.disabled = true;
  showMessage(state.texts.waiting_ask);
  try {
    const round = await call("/api/ask", { question });
    hideMessage();
    if (round.status === "ask_again" || round.status === "unavailable") {
      showMessage(round.message);  // The question stays in the box to be changed.
      return;
    }
    $("question").value = "";
    renderRound(round);
  } catch (error) {
    showMessage(sendFailed(error));
  } finally {
    button.disabled = false;
  }
}

function sendFailed(error) { return state.texts.send_failed.replace("{error}", error.message); }
function showMessage(text) { $("ask-message").textContent = text; $("ask-message").hidden = false; }
function hideMessage() { $("ask-message").hidden = true; }

function renderRound(round) {
  if (!state.firstQuestion) state.firstQuestion = round.question;
  $("to-reflect").hidden = false;
  state.lastOrder = round.seat_order;
  for (const id of round.met_seats) state.met.add(id);
  for (const id of round.silent_seats) state.silent.add(id);

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
  asked.focus({ preventScroll: true });
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
  // One line just over the two cards, until one AI question is answered in
  // this session (直し30の続き-0).
  if (!state.aiAnswered && !band.answered) part.append(el("p", { class: "ai-hint", text: state.texts.ai_answer_hint }));
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
  // The same two sit at the round table (直し29-1), from this one call.
  if (!band.answered) onMap((map) => map.band(roundNo, band.cards));
}

function answerEntry(roundNo, role) {
  const open = el("button", { type: "button", class: "quiet", text: state.texts.bubble_answer });
  open.addEventListener("click", () => {
    const form = answerForm(roundNo, role);
    open.replaceWith(form);
    form.querySelector("input").focus();
  });
  return open;
}

// The one-line box an answer to コーチ or オブザーバー goes in, empty: below
// the map and in the round table's choices alike (直し29-1). Sent, the next
// round starts.
function answerForm(roundNo, role) {
  const input = el("input", { type: "text", maxlength: "120", autocomplete: "off" });
  const form = el("form", { class: "ai-answer" }, input, el("button", { type: "submit", text: "送る" }));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const answer = input.value.trim();
    if (!answer) return;
    for (const node of form.querySelectorAll("input, button")) node.disabled = true;
    showMessage(state.texts.waiting_ask);
    try {
      const round = await call("/api/coach_answer", { round: roundNo, role, answer, after_notice: state.needsShown });
      if (round.status === "unavailable") state.aiUnavailable = true;
      if (round.status === "ask_again" || round.status === "unavailable") {
        showMessage(round.message);
        for (const node of form.querySelectorAll("input, button")) node.disabled = false;
        return;
      }
      hideMessage();
      state.aiAnswered = true;
      $("reflect-needs-answer").hidden = true;
      for (const node of document.querySelectorAll(".ai-card.needs-answer")) node.classList.remove("needs-answer");
      for (const node of document.querySelectorAll(".ai-hint")) node.remove();
      bandAnswered(roundNo, role);
      renderRound(round);
    } catch (error) {
      showMessage(sendFailed(error));
      for (const node of form.querySelectorAll("input, button")) node.disabled = false;
    }
  });
  return form;
}

// One answer per band: the other card's 「答える」 goes away and the card
// answered is marked, wherever the answer was written.
function bandAnswered(roundNo, role) {
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
    const done = () => el("p", { class: "card-done", text: "質問カードにしました" });
    if (asked.carded || state.carded.has(asked.seat_id)) node.append(done());
    else node.append(cardEntry(asked.seat_id, (form) => form.replaceWith(done())));
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
  const words = quote.said ? `「${quote.text}」` : quote.text;
  const node = el("div", { class: "quote", "data-utterance": quote.utterance_id });
  if (state.marks[quote.seat_id] === quote.utterance_id) node.classList.add("marked");
  const paragraph = el("p", { class: "paragraph", hidden: "" });
  const back = el("button", { type: "button", text: "元の段落", onclick: async () => {
    if (paragraph.hidden && !paragraph.textContent) paragraph.textContent = await paragraphOf(quote.utterance_id);
    paragraph.hidden = !paragraph.hidden;
  } });
  const mark = el("button", { type: "button", text: "印をつける", onclick: () => markQuote(roundNo, quote.utterance_id) });
  node.dataset.seat = quote.seat_id;
  node.append(
    el("p", { class: "words", text: words }),
    el("span", { class: "source", text: sourceLine(quote.source) }),
    el("div", { class: "actions" }, back, mark),
    paragraph);
  return node;
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
function readBelow(roundNo, utteranceId) {
  const quote = [...document.querySelectorAll(`#rounds .round[data-round="${roundNo}"] .quote`)]
    .find((node) => node.dataset.utterance === utteranceId);
  if (!quote) return;
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
  // A card being written in stays open, its words as they were, when the
  // list is drawn again (直し26-3).
  const draft = keptDraft(list);
  list.replaceChildren();
  for (const [kind, label] of Object.entries(state.kinds)) {
    const seats = state.seats.filter((seat) => seat.kind === kind);
    if (!seats.length) continue;
    const row = el("div", { class: "seat-row" });
    for (const seat of seats) row.append(renderSeat(seat));
    list.append(el("section", { class: `kind-group kind-${kind}` }, el("h3", { text: label }), row));
  }
  $("met-count").textContent = String(state.met.size);
  putBackDraft(draft);
  onMap((map) => map.refresh());  // The same count and marks on the map.
}

// The seat list's open card, if any: whose seat, the student's words in it
// so far, and whether the keyboard was in it (and where).
function keptDraft(list) {
  const form = list.querySelector(".card-form");
  if (!form || !form.dataset.seat) return null;
  const box = form.querySelector("textarea");
  return { seatId: form.dataset.seat, text: box.value, focused: document.activeElement === box,
    start: box.selectionStart, end: box.selectionEnd };
}

// The card open again under its seat's line, with the student's own words
// put back (the box is never filled with anything else); the page does not
// move, and the keyboard stays where it is unless it was in the card.
// A card already sent is not opened again.
function putBackDraft(draft) {
  if (!draft || state.carded.has(draft.seatId)) return;
  const form = openCardFor(draft.seatId, { quiet: true });
  if (!form) return;
  const box = form.querySelector("textarea");
  box.value = draft.text;
  if (!draft.focused) return;
  box.focus({ preventScroll: true });
  box.setSelectionRange(draft.start, draft.end);
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
    box.append(el("div", { class: "card-done", text: "質問カードにしました" }));
    return box;
  }
  box.append(cardEntry(seat.seat_id, renderSeats, (form, open) => putUnderLine(seat, form, open)));
  return box;
}

// In the seat list an open card goes right under its seat's line of seats,
// the list's full width, so the seat keeps its size (直し25-4). It says
// whose seat it is for, in the seat list's own words. One open at a time:
// another one closes, its button back.
function putUnderLine(seat, form, open) {
  for (const other of document.querySelectorAll("#seat-list .card-form")) other.closeCard();
  const node = open.closest(".seat");
  let last = node;
  for (const next of node.parentElement.children) {
    if (next.classList.contains("seat") && next.offsetTop === node.offsetTop) last = next;
  }
  form.prepend(el("p", { class: "card-for", text: [seat.title, seat.detail].filter(Boolean).join("　") }));
  form.closeCard = () => {
    form.remove();
    if (open.dataset.quiet) open.remove();  // Opened from the map: no button of its own here.
    else open.hidden = false;
    node.classList.remove("writing");
  };
  open.hidden = true;
  node.classList.add("writing");
  last.after(form);
  // As wide as the seats' columns, not the whole list (直し26-4), again
  // when the window's width changes.
  form.fit = () => fitToSeats(node, form);
  form.fit();
}

// The width the seats of a row take: from the left of the leftmost to the
// right of the rightmost, whichever line they are on.
function fitToSeats(node, form) {
  const seats = [...node.parentElement.children].filter((next) => next.classList.contains("seat"));
  const left = Math.min(...seats.map((seat) => seat.offsetLeft));
  const right = Math.max(...seats.map((seat) => seat.offsetLeft + seat.offsetWidth));
  form.style.setProperty("--line", `${right - left}px`);
}

// The seat list's question card for any seat, opened from its lamp card at
// the table (直し26-2): the same card as 「聞きたいことを書く」, under its
// seat's line, its box empty. A seat that spoke has no button for it in the
// list: one is made for the card to go by, and goes with it.
function openCardFor(seatId, { quiet = false } = {}) {
  const seat = state.seatById[seatId];
  const node = [...$("seat-list").querySelectorAll(".seat")].find((item) => item.dataset.seat === seatId);
  if (!seat || !node) return null;
  let open = node.querySelector(".not-asked > button");
  if (!open) {
    open = cardEntry(seatId, renderSeats, (form, button) => putUnderLine(seat, form, button));
    open.dataset.quiet = "1";
    open.hidden = true;
    node.append(open);
  }
  // Quiet (put back after the list is drawn again): no focus, no scroll.
  open.dataset.still = quiet ? "1" : "";
  open.click();
  delete open.dataset.still;
  const form = node.parentElement.querySelector(".card-form");
  if (form && !quiet) form.scrollIntoView({ block: "center" });
  return form;
}

// 「聞きたいことを書く」: opens an empty box; the card holds the student's
// words only (SPEC 2-2). put: where the open card goes (in the button's place).
function cardEntry(seatId, done, put = (form, open) => open.replaceWith(form)) {
  const open = el("button", { type: "button", class: "quiet", text: "聞きたいことを書く" });
  open.addEventListener("click", () => {
    const form = $("card-form-template").content.firstElementChild.cloneNode(true);
    form.dataset.seat = seatId;  // Whose card it is, so it can be opened again (直し26-3).
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = form.querySelector("textarea").value.trim();
      if (!text) return;
      await call("/api/card", { seat_id: seatId, text });
      state.carded.add(seatId);
      done(form);
    });
    put(form, open);
    if (!open.dataset.still) form.querySelector("textarea").focus();
  });
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
  const card = entry.closest(".ai-card");
  for (const node of document.querySelectorAll(".ai-card.needs-answer")) node.classList.remove("needs-answer");
  card.classList.add("needs-answer");
  card.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "center" });
  entry.focus({ preventScroll: true });
}

// The newest round's card that can still be answered: its 「答える」, or the
// box already open under it. None: null.
function answerable() {
  const rounds = Object.keys(state.bands).map(Number).sort((a, b) => b - a);
  for (const roundNo of rounds) {
    const entry = state.bands[roundNo].querySelector(".ai-card > button, .ai-card > form input:not(:disabled)");
    if (entry) return entry;
  }
  return null;
}

function openReflection() {
  $("table").hidden = true;
  $("reflect").hidden = false;
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

function showSubject(subject) {
  if (!subject) return;
  $("harvest-heading").textContent = state.texts.harvest_heading;
  $("harvest-subject-line").textContent = subject.line;
  $("harvest-subject-note").textContent = subject.note;
  const more = $("harvest-subject-more");
  more.textContent = state.texts.harvest_subject_more;
  more.hidden = !subject.more;
  more.disabled = false;
  $("harvest-subject").hidden = false;
  $("harvest").hidden = false;
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

$("ask-form").addEventListener("submit", ask);
$("to-reflect").addEventListener("click", toReflection);
$("reflect-first").addEventListener("submit", reflectFirst);
$("reflect-answer").addEventListener("submit", (event) => { event.preventDefault(); reflectAnswer(false); });
$("decline").addEventListener("click", () => reflectAnswer(true));
$("reflect-finish").addEventListener("submit", reflectFinish);
$("harvest-subject-more").addEventListener("click", moreSubject);
$("back-start").addEventListener("click", askBackToStart);
$("back-yes").addEventListener("click", backToStart);
$("back-no").addEventListener("click", stayHere);
$("back-confirm").addEventListener("keydown", (event) => { if (event.key === "Escape") stayHere(); });
$("more-purposes").addEventListener("click", async () => renderPurposes((await call("/api/purposes", {})).purposes));
window.addEventListener("resize", () => {
  for (const form of document.querySelectorAll("#seat-list .card-form")) if (form.fit) form.fit();
});
setup();
