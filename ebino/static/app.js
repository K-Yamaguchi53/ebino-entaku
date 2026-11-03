// The round-table screen. Every word from the server is set with textContent,
// never as HTML.
"use strict";

const state = {
  texts: {}, kinds: {}, seats: [], seatById: {},
  lastOrder: [], met: new Set(), silent: new Set(), carded: new Set(), marks: {},
  askBoxes: {},  // Round number -> the box of 「司会が○○に聞いてみる」.
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

  const box = el("article", { class: "round" });
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
  for (const card of band.cards) {
    const node = el("div", { class: "ai-card" },
      el("p", { class: "label", text: card.label }),
      el("p", { class: "badge", text: card.badge }),
      el("p", { class: "words", text: card.question }));
    if (!band.answered) node.append(answerEntry(roundNo, card.role, part));
    else if (band.answered === card.role) node.classList.add("answered");
    part.append(node);
  }
  box.append(part);
}

function answerEntry(roundNo, role, part) {
  const open = el("button", { type: "button", class: "quiet", text: "答える" });
  open.addEventListener("click", () => {
    const input = el("input", { type: "text", maxlength: "120", autocomplete: "off" });
    const form = el("form", { class: "ai-answer" }, input, el("button", { type: "submit", text: "送る" }));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const answer = input.value.trim();
      if (!answer) return;
      for (const node of form.querySelectorAll("input, button")) node.disabled = true;
      showMessage(state.texts.waiting_ask);
      try {
        const round = await call("/api/coach_answer", { round: roundNo, role, answer });
        if (round.status === "ask_again" || round.status === "unavailable") {
          showMessage(round.message);
          for (const node of form.querySelectorAll("input, button")) node.disabled = false;
          return;
        }
        hideMessage();
        // One answer per band: the other card's button goes away.
        for (const button of part.querySelectorAll(".ai-card > button")) button.remove();
        form.closest(".ai-card").classList.add("answered");
        renderRound(round);
      } catch (error) {
        showMessage(sendFailed(error));
        for (const node of form.querySelectorAll("input, button")) node.disabled = false;
      }
    });
    open.replaceWith(form);
    input.focus();
  });
  return open;
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
    // A mark can change the card of 「司会が○○に聞いてみる」 until it is pressed.
    const askBox = state.askBoxes[roundNo];
    if (askBox && !askBox.dataset.asked) loadAskCard(roundNo, askBox);
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

// A split heading's "…" or ”…” shown as 「…」: on the screen only. The record
// and what the models are sent keep the heading as it was written.
function shownQuotes(text) {
  return text.replace(/["“”]([^"“”\n]*)["“”]/g, "「$1」");
}

function renderSplit(roundNo, split, byId) {
  const titles = (ids) => [...new Set(ids.map((id) => state.seatById[byId[id].seat_id].title))].join("・");
  return el("div", { class: "split" },
    el("p", { class: "notice", text: state.texts.split_notice }),
    el("p", { class: "heading", text: shownQuotes(split.heading) }),
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
  box.append(cardEntry(seat.seat_id, renderSeats));
  return box;
}

// 「聞きたいことを書く」: opens an empty box; the card holds the student's
// words only (SPEC 2-2).
function cardEntry(seatId, done) {
  const open = el("button", { type: "button", class: "quiet", text: "聞きたいことを書く" });
  open.addEventListener("click", () => {
    const form = $("card-form-template").content.firstElementChild.cloneNode(true);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = form.querySelector("textarea").value.trim();
      if (!text) return;
      await call("/api/card", { seat_id: seatId, text });
      state.carded.add(seatId);
      done(form);
    });
    open.replaceWith(form);
    form.querySelector("textarea").focus();
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
}

$("ask-form").addEventListener("submit", ask);
$("to-reflect").addEventListener("click", openReflection);
$("reflect-first").addEventListener("submit", reflectFirst);
$("reflect-answer").addEventListener("submit", (event) => { event.preventDefault(); reflectAnswer(false); });
$("decline").addEventListener("click", () => reflectAnswer(true));
$("reflect-finish").addEventListener("submit", reflectFinish);
$("harvest-subject-more").addEventListener("click", moreSubject);
$("more-purposes").addEventListener("click", async () => renderPurposes((await call("/api/purposes", {})).purposes));
setup();
