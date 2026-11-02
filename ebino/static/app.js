// The round-table screen. Every word from the server is set with textContent,
// never as HTML.
"use strict";

const state = {
  texts: {}, kinds: {}, seats: [], seatById: {},
  lastOrder: [], met: new Set(), silent: new Set(), carded: new Set(), marks: {},
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

// --- start ---

async function setup() {
  const data = await call("/api/setup");
  Object.assign(state, { texts: data.texts, kinds: data.kinds, seats: data.seats, changedChoices: data.changed_choices });
  for (const seat of data.seats) state.seatById[seat.seat_id] = seat;
  for (const line of data.texts.start_notice) $("start-notice").append(el("li", { text: line }));
  $("lab-question").textContent = data.texts.lab_question;
  for (const [key, label] of Object.entries(data.labs)) {
    $("lab-choices").append(el("button", { type: "button", text: label, onclick: () => start(key) }));
  }
  $("heavy-talk").textContent = data.texts.heavy_talk_notice;
  $("question").placeholder = "例：" + data.texts.input_example;
  $("purpose-heading").textContent = data.texts.purpose_heading;
  for (const text of data.texts.work_questions) {
    $("work-questions").append(el("button", { type: "button", text, onclick: () => fill(text) }));
  }
  renderSeats();
}

async function start(lab) {
  const data = await call("/api/start", { lab });
  $("start").hidden = true;
  $("table").hidden = false;
  renderPurposes(data.purposes);
  $("question").focus();
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
    list.append(el("li", {},
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
  showMessage("席の言葉を探しています…");
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
    showMessage("うまく送れませんでした（" + error.message + "）");
  } finally {
    button.disabled = false;
  }
}

function showMessage(text) { $("ask-message").textContent = text; $("ask-message").hidden = false; }
function hideMessage() { $("ask-message").hidden = true; }

function renderRound(round) {
  if (!state.firstQuestion) state.firstQuestion = round.question;
  $("to-reflect").hidden = false;
  state.lastOrder = round.seat_order;
  for (const id of round.met_seats) state.met.add(id);
  for (const id of round.silent_seats) state.silent.add(id);

  const box = el("article", { class: "round" });
  box.append(el("p", { class: "round-question", text: round.question }));
  box.append(el("p", { class: "steps",
    text: `司書が見つけた片：${round.steps.found}　番人が通した引用：${round.steps.passed}　止めた引用：${round.steps.stopped}` }));
  box.append(el("p", { class: "count", text: state.texts.answered_count.replace("{n}", round.answered_seats) }));

  const byId = {};
  round.quotes.forEach((quote, index) => {
    const node = renderQuote(round.round, quote);
    byId[quote.utterance_id] = quote;
    box.append(node);
    if (index === 0) for (const text of round.planted_stopped) box.append(renderPlanted(text));
  });

  for (const split of round.splits) box.append(renderSplit(round.round, split, byId));
  if (round.card) box.append(el("p", { class: "card-done", text: "この問いを質問カードにしました" }));
  $("rounds").prepend(box);
  renderSeats();
}

function renderQuote(roundNo, quote) {
  const words = quote.said ? `「${quote.text}」` : quote.text;
  const node = el("div", { class: "quote", "data-utterance": quote.utterance_id });
  if (state.marks[quote.seat_id] === quote.utterance_id) node.classList.add("marked");
  const paragraph = el("p", { class: "paragraph", hidden: "" });
  const back = el("button", { type: "button", text: "元の段落", onclick: async () => {
    if (paragraph.hidden && !paragraph.textContent) {
      paragraph.textContent = (await call("/api/paragraph", { utterance_id: quote.utterance_id })).paragraph;
    }
    paragraph.hidden = !paragraph.hidden;
  } });
  const mark = el("button", { type: "button", text: "印をつける", onclick: async () => {
    state.marks = (await call("/api/mark", { round: roundNo, utterance_id: quote.utterance_id })).marks;
    for (const other of document.querySelectorAll(".quote")) {
      const seatId = other.dataset.seat;
      other.classList.toggle("marked", state.marks[seatId] === other.dataset.utterance);
    }
  } });
  node.dataset.seat = quote.seat_id;
  node.append(
    el("p", { class: "words", text: words }),
    el("span", { class: "source", text: sourceLine(quote.source) }),
    el("div", { class: "actions" }, back, mark),
    paragraph);
  return node;
}

function renderPlanted(text) {
  const line = el("p", { class: "planted" });
  line.append("番人が止めた（原文にない）：", el("s", { text }));
  return line;
}

function renderSplit(roundNo, split, byId) {
  const titles = (ids) => [...new Set(ids.map((id) => state.seatById[byId[id].seat_id].title))].join("・");
  return el("div", { class: "split" },
    el("p", { class: "notice", text: state.texts.split_notice }),
    el("p", { class: "heading", text: split.heading }),
    el("p", { class: "sides", text: `${titles(split.side_a)}　／　${titles(split.side_b)}` }),
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
}

function renderSeat(seat) {
  const node = el("div", { class: `seat kind-${seat.kind}` });
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
  const open = el("button", { type: "button", class: "quiet", text: "聞きたいことを書く" });
  open.addEventListener("click", () => {
    const form = $("card-form-template").content.firstElementChild.cloneNode(true);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = form.querySelector("textarea").value.trim();
      if (!text) return;
      await call("/api/card", { seat_id: seat.seat_id, text });
      state.carded.add(seat.seat_id);
      renderSeats();
    });
    open.replaceWith(form);
    form.querySelector("textarea").focus();
  });
  box.append(open);
  return box;
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

function openReflection() {
  $("table").hidden = true;
  $("reflect").hidden = false;
  document.querySelector(".reflect-heavy-talk").textContent = state.texts.heavy_talk_notice;
  $("first-question").textContent = state.firstQuestion;
  radios($("changed-choices"), "changed", Object.entries(state.changedChoices));
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
  const result = await call("/api/reflect/begin", { changed, now_question: nowQuestion });
  if (result.status === "ask_again") {
    $("reflect-message").textContent = result.message;
    $("reflect-message").hidden = false;
    return;
  }
  for (const node of $("reflect-first").querySelectorAll("input, textarea, button")) node.disabled = true;
  $("reflect-message").hidden = true;
  $("ask-back").textContent = result.ask_back;
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
  const meetSeat = $("meet-seat").value;
  if (!chosen || !meetSeat) return;
  if (chosen === "own" && !$("own-move").value.trim()) return;
  const sheet = await call("/api/reflect/finish", {
    chosen, own_move: $("own-move").value, rewrite: $("rewrite").value,
    meet_seat: meetSeat, meet_reason: $("meet-reason").value,
  });
  for (const id of ["reflect-first", "reflect-answer", "reflect-finish"]) $(id).hidden = true;
  renderSheet(sheet);
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
  row("出会った生き方", ...sheet.met_lives.map((life) => el("div", {},
    el("div", { text: life.said ? `「${life.text}」` : life.text }),
    el("div", { class: "source", text: sourceLine(life.source) }))));
  row("割れたところ", ...sheet.splits.map((split) =>
    el("div", { class: split.pressed ? "" : "left", text: (split.pressed ? "" : "置いてきた：") + split.heading })));
  row("残した質問カード", ...sheet.cards);
  row("最初の問いは変わった？", sheet.changed);
  row("いまの問い（1回目）", sheet.now_question);
  row("問い返し", sheet.ask_back, sheet.declined ? "答えない" : sheet.answer);
  const move = sheet.chosen === "none" ? "選ばない"
    : sheet.chosen === "own" ? `自分で書いた一手：${sheet.own_move}`
    : sheet.move ? `${sheet.move.label}：${sheet.move.text}` : "";
  row("次の一手", move);
  if (sheet.rewrite) row("いまの問い（書き直し）", sheet.rewrite);
  if (sheet.meet) row("会いに行きたい1人", sourceLine(sheet.meet), sheet.meet.reason);
  box.hidden = false;
}

$("ask-form").addEventListener("submit", ask);
$("to-reflect").addEventListener("click", openReflection);
$("reflect-first").addEventListener("submit", reflectFirst);
$("reflect-answer").addEventListener("submit", (event) => { event.preventDefault(); reflectAnswer(false); });
$("decline").addEventListener("click", () => reflectAnswer(true));
$("reflect-finish").addEventListener("submit", reflectFinish);
$("more-purposes").addEventListener("click", async () => renderPurposes((await call("/api/purposes", {})).purposes));
setup();
