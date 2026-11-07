// 帰る前に、ひとこと (直し38): in place of the reflection sheet unless
// EBINO_REFLECT=old. The screen follows the teacher's sample: today's map,
// the listener's questions (and the ladder), the scale, what to keep, the
// light, and one sheet to print. Every word is texts/hitokoto.tsv's or the
// record's, set with textContent, never as HTML; what an AI says is in its
// own card, with its own label and colour, apart from people's words.
"use strict";

const EbinoHitokoto = (() => {
  const SVG = "http://www.w3.org/2000/svg";
  const STEPS = ["map", "talk", "light", "sheet"];
  let app = null;  // What app.js lends: call, state, setNow, sendFailed, showBackToStart, shownQuotes.
  let W = {};  // The words (texts/hitokoto.tsv).
  let view = null;  // Today's map, as the server sent it.
  let picked = null;  // { person, part } pressed on the map.
  let busy = false;

  const $ = (id) => document.getElementById(id);
  const still = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function button(cls, text, onclick) {
    const node = el("button", cls, text);
    node.type = "button";
    if (onclick) node.addEventListener("click", onclick);
    return node;
  }

  function fill(template, values) {
    return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
  }

  function show(step) {
    for (const name of STEPS) $(`hk-${name}`).hidden = name !== step;
    const at = STEPS.indexOf(step);
    for (const li of $("hk-steps").children) {
      const i = STEPS.indexOf(li.dataset.step);
      li.className = i === at ? "on" : i < at ? "done" : "";
      if (i === at) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    }
    window.scrollTo(0, 0);
  }

  // The steps that wait on the model, and the kind of wait each is (直し42,
  // texts/wait_sign.tsv); the others are quick and show no sign.
  // 直し48 段4: the sheet, 「整理中」 while it is made.
  const WAITS = { parts: "listen", choose: "listen", answer: "listen", subject_note: "subject", light: "light", sheet: "sheet" };

  async function post(step, body = {}) {
    return app.call(`/api/hitokoto/${step}`, body, { wait: WAITS[step] });
  }

  // --- 段1: today's map ---

  async function open(lent) {
    app = lent;
    W = app.state.hitokoto.words;
    $("hitokoto").hidden = false;
    $("hk-title").textContent = W.name;
    $("hk-steps").replaceChildren(...STEPS.map((step) => {
      const li = el("li", "", W[`step_${step}`]);
      li.dataset.step = step;
      return li;
    }));
    document.querySelector(".hk-heavy-talk").textContent = app.state.texts.heavy_talk_notice;
    $("hk-first-label").textContent = W.first_label;
    $("hk-map-lead").textContent = W.map_lead;
    $("hk-go").textContent = W.go;
    $("hk-omakase").textContent = W.omakase;
    $("hk-stop").textContent = W.stop;
    $("hk-stop").hidden = false;
    $("hk-now-label").textContent = W.now_label;
    $("hk-to-sheet").textContent = W.to_sheet;
    $("hk-print").textContent = W.print;
    $("hk-print-side").textContent = W.print_side;
    show("map");
    app.setNow();
    // 直し45 段5: first today's trail, and the three marks (each optional).
    const marks = await markTrail();
    try {
      view = await post("begin", { opened: app.state.opened || [], marks });
    } catch (error) {
      $("hk-first").textContent = app.sendFailed(error);
      return;
    }
    if (view.status === "ask_again") {  // A name in a line: the trail again.
      $("hk-first").textContent = view.message;
      return open(lent);
    }
    $("hk-first").textContent = view.first_question;
    renderTrail(view.trail || []);
    drawMap();
    if (!view.people.length) {  // No one to read today: the first question, then the scale.
      $("hk-map-lead").hidden = true;
      $("hk-map-buttons").hidden = true;
      $("hk-map-box").hidden = true;
      $("hk-talk").hidden = false;
      markStep("talk");
      askScale(view.question);
      return;
    }
    renderCards({});
    try {
      renderCards((await post("parts")).parts);
    } catch (error) {
      // No parts: the whole cards stay to press.
    }
  }

  // --- 直し45 段5: the trail, and the three marks ---

  // Today's trail (GET /api/trail, the same as by the map), each step with
  // the three marks to press, each optional: one mark a step and one step a
  // mark (pressed on another step, it moves there). A step marked gets a
  // line to write, empty or not. 次へ sends the marks, とばす none. No trail:
  // straight on, as before.
  async function markTrail() {
    let items = [];
    try {
      const response = await fetch("/api/trail");
      if (response.ok) items = (await response.json()).items || [];
    } catch (error) {
      items = [];
    }
    if (!items.length) return [];
    const M = app.state.hitokoto.marks, MW = app.state.hitokoto.mark_words;
    const part = $("hk-map");
    part.classList.add("marking");
    const box = el("section", "hk-marks");
    box.append(el("p", "hk-lead", MW.lead));
    const list = el("ol", "hk-mark-list");
    const chosen = {};  // mark -> n
    const rows = items.map((item) => {
      const li = el("li", `hk-mark-item hk-mark-${item.kind}`);
      li.dataset.n = String(item.n);
      li.append(...markLines(item));
      const buttons = el("div", "hk-mark-buttons");
      buttons.setAttribute("role", "group");
      for (const [key, label] of Object.entries(M)) {
        const press = button("hk-mark", label, () => {
          const was = chosen[key];
          for (const [other, n] of Object.entries(chosen)) if (n === item.n && other !== key) delete chosen[other];
          if (was === item.n) delete chosen[key];
          else chosen[key] = item.n;
          redraw();
        });
        press.dataset.mark = key;
        press.setAttribute("aria-pressed", "false");
        buttons.append(press);
      }
      const note = el("input", "hk-mark-note");
      Object.assign(note, { type: "text", maxLength: 120, placeholder: MW.note, autocomplete: "off" });
      note.setAttribute("aria-label", MW.note);
      note.hidden = true;
      li.append(buttons, note);
      list.append(li);
      return { item, li, note };
    });
    const redraw = () => {
      for (const { item, li, note } of rows) {
        const on = Object.entries(chosen).find(([, n]) => n === item.n);
        for (const press of li.querySelectorAll(".hk-mark")) {
          press.setAttribute("aria-pressed", String(Boolean(on && on[0] === press.dataset.mark)));
        }
        li.classList.toggle("marked", Boolean(on));
        note.hidden = !on;
      }
    };
    const go = button("hk-primary", MW.go);
    const skip = button("quiet", MW.skip);
    const row = el("div", "hk-row");
    row.append(go, skip);
    box.append(list, row);
    part.prepend(box);
    go.focus({ preventScroll: true });
    const marks = await new Promise((done) => {
      go.addEventListener("click", () => done(Object.entries(chosen).map(([mark, n]) => ({
        mark, n, note: rows.find((r) => r.item.n === n).note.value.trim() }))));
      skip.addEventListener("click", () => done([]));
    });
    box.remove();
    part.classList.remove("marking");
    return marks;
  }

  // A step in words: what it was (small), then the student's words or whose
  // words; an AI's question in the AI's colour with its name.
  function markLines(item) {
    const T = app.state.texts.trail_words;
    const small = (text) => el("span", "hk-mark-small", text);
    const text = (words) => el("span", "hk-mark-text", words);
    if (item.kind === "question") return [small(T.question), text(item.text)];
    if (item.kind === "opened") return [small(`${T.opened}　${item.who}`), text(item.label || item.who)];
    if (item.kind === "one_ask") return [small(`${T.one_ask}　${item.who}`), text(item.text)];
    if (item.kind === "card") return [small(T.card), text(item.text)];
    if (item.kind === "direction") return [small(T.direction), text(item.text)];
    const answer = item.declined ? T.declined : [item.choice, item.answer].filter(Boolean).join("　");
    return [el("span", "hk-mark-ai", item.ai_label), text(item.question), small(`${T.answer}　${answer}`)];
  }

  function markStep(step) {
    const at = STEPS.indexOf(step);
    for (const li of $("hk-steps").children) {
      const i = STEPS.indexOf(li.dataset.step);
      li.className = i === at ? "on" : i < at ? "done" : "";
    }
  }

  function svg(tag, attrs) {
    const node = document.createElementNS(SVG, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  }

  // The sample's small map: the basin's edge and a river (drawn, not the
  // town's map), grey points for other seats met, the people of the day lit
  // at the sample's places, a dashed line between the split's two. The
  // split's heading is over the map, never on a point or the line.
  function drawMap() {
    const box = $("hk-map-box");
    box.replaceChildren();
    if (view.split) {
      const line = el("p", "hk-split");
      // Its ”…” as 「…」, as on the other screens (直し40-0): on screen only, the record as it was.
      line.append(el("span", "hk-split-label", W.map_split), el("span", "hk-split-heading", app.shownQuotes(view.split.heading)));
      box.append(line);
    }
    const map = svg("svg", { viewBox: "0 0 600 330", "aria-hidden": "true", focusable: "false" });
    const defs = svg("defs", {});
    const glow = svg("radialGradient", { id: "hk-glow", cx: "50%", cy: "50%", r: "50%" });
    glow.append(svg("stop", { offset: "0", class: "hk-glow-in" }), svg("stop", { offset: "1", class: "hk-glow-out" }));
    defs.append(glow);
    map.append(defs,
      svg("path", { class: "hk-basin", d: "M60 170 C70 90 170 40 300 42 C440 44 540 92 548 170 C556 250 450 296 300 298 C150 300 52 252 60 170Z" }),
      svg("path", { class: "hk-river", d: "M70 210 C160 190 230 230 300 205 C380 178 450 214 540 196" }));
    for (const [x, y] of view.grey) map.append(svg("circle", { class: "hk-grey", cx: x, cy: y, r: 4 }));
    if (view.split) {
      const a = view.people[view.split.a], b = view.people[view.split.b];
      map.append(svg("line", { class: "hk-split-line", x1: a.x, y1: a.y, x2: b.x, y2: b.y }));
    }
    view.people.forEach((person, index) => {
      const g = svg("g", { class: "hk-glow" });
      g.append(svg("circle", { cx: person.x, cy: person.y, r: 24, fill: "url(#hk-glow)" }));
      map.append(g, svg("circle", { class: `hk-pt kind-${person.kind}`, id: `hk-pt-${index}`, cx: person.x, cy: person.y, r: 8 }));
      // The label over its point, or under it when the point is the split's second (as in the sample).
      const below = view.split && index === view.split.b;
      const label = svg("text", { class: "hk-pt-label", x: person.x, y: below ? person.y + 30 : person.y - 18 });
      label.textContent = person.title;
      map.append(label);
    });
    const counts = svg("text", { class: "hk-counts", x: 300, y: 320 });
    counts.textContent = fill(W.map_counts, view.counts);
    map.append(counts);
    box.append(map);
    box.setAttribute("role", "img");
    box.setAttribute("aria-label", [W.step_map, fill(W.map_counts, view.counts),
      ...view.people.map((p) => p.title), view.split ? `${W.map_split}${app.shownQuotes(view.split.heading)}` : ""].filter(Boolean).join("。"));
  }

  // 直し48 段7: today's trail beside the talk, in the order it went; a step
  // pressed opens, in place, what was heard then (whose words, as recorded).
  // Open beside the talk on a wide screen; folded above it when narrow.
  function renderTrail(items) {
    const list = $("hk-trail-list");
    list.replaceChildren();
    $("hk-trail-title").textContent = W.sheet_story;
    items.forEach((item, n) => {
      const li = el("li", `hk-trail-step kind-${item.kind}`);
      if (!item.quote) {
        li.append(el("p", "hk-trail-head", item.head));
      } else {
        const id = `hk-trail-said-${n}`;
        const head = button("hk-trail-head", null, () => {
          const open = head.getAttribute("aria-expanded") !== "true";
          head.setAttribute("aria-expanded", String(open));
          $(id).hidden = !open;
        });
        head.setAttribute("aria-expanded", "false");
        head.setAttribute("aria-controls", id);
        head.append(el("span", "hk-trail-who", [item.who, item.label].filter(Boolean).join("　")));
        if (item.kind === "one_ask") head.append(el("span", "hk-trail-asked", item.head));
        const said = el("div", "hk-trail-said");
        said.id = id;
        said.hidden = true;
        said.append(el("p", "hk-trail-quote", item.said ? `「${item.quote}」` : item.quote));
        li.append(head, said);
      }
      list.append(li);
    });
    $("hk-trail").hidden = !items.length;
    $("hk-trail-fold").open = window.matchMedia("(min-width: 769px)").matches;
  }

  // Each person's words, as recorded. Before the parts come back, or with
  // none for a card, the whole card is pressed; a part lit is pressed alone.
  function renderCards(parts) {
    const box = $("hk-cards");
    box.replaceChildren();
    view.people.forEach((person, index) => {
      const part = parts[String(index)] || "";
      const from = el("span", "hk-from", `${person.title}（${person.kind_label}）`);
      const words = person.said ? `「${person.text}」` : person.text;
      let card;
      if (!part) {
        card = button("hk-said hk-whole", null, () => pick(index, "", card));
        card.append(from, el("span", "hk-words", words));
        card.setAttribute("aria-pressed", "false");
      } else {
        // 直し48 段7 (the teacher, 11/7: 「フレーズよりも文章まるごと選択で
        // いい」): each whole sentence pressed alone (person.sentences, the
        // server's: word for word); the one the lit part is in, lit.
        card = el("div", "hk-said");
        const body = el("span", "hk-words");
        if (person.said) body.append("「");
        for (const sentence of person.sentences || [person.text]) {
          const kw = button("hk-kw hk-sentence", sentence, () => pick(index, sentence, kw));
          kw.setAttribute("aria-pressed", "false");
          kw.setAttribute("aria-label", `${person.title}の言葉「${sentence}」`);
          if (sentence.includes(part)) kw.classList.add("hk-lit-part");
          body.append(kw);
        }
        if (person.said) body.append("」");
        card.append(from, body);
      }
      if (!person.said && person.note) card.append(el("span", "hk-note", person.note));
      box.append(card);
    });
    $("hk-go").disabled = true;
    picked = null;
    // 直し45 段5: the step marked first is where the first word is looked
    // for: its person's lit part, else the whole card, already pressed.
    if (Number.isInteger(view.start) && view.people[view.start]) {
      const part = parts[String(view.start)] || "";
      const cards = box.children[view.start];
      const node = cards && (part ? cards.querySelector(".hk-kw.hk-lit-part") || cards.querySelector(".hk-kw") : cards);
      if (node) pick(view.start, node.classList.contains("hk-kw") ? node.textContent : part, node);
    }
  }

  function pick(index, part, node) {
    for (const other of document.querySelectorAll("#hk-cards [aria-pressed]")) other.setAttribute("aria-pressed", "false");
    node.setAttribute("aria-pressed", "true");
    for (const pt of document.querySelectorAll("#hk-map-box .hk-pt")) pt.classList.toggle("on", pt.id === `hk-pt-${index}`);
    picked = { person: index, part };
    $("hk-go").disabled = false;
  }

  async function choose(omakase) {
    if (busy || (!omakase && !picked)) return;
    busy = true;
    $("hk-go").disabled = true;
    $("hk-omakase").disabled = true;
    show("talk");
    $("hk-log").replaceChildren();
    if (omakase) say("ai", W.omakase_said);
    const waiting = say("ai", W.thinking, null, "waiting");
    let result;
    try {
      result = await post("choose", omakase ? { omakase: true } : picked);
    } catch (error) {
      waiting.remove();
      say("teacher", app.sendFailed(error));
      busy = false;
      return;
    }
    waiting.remove();
    busy = false;
    if (omakase) {
      for (const pt of document.querySelectorAll("#hk-map-box .hk-pt")) pt.classList.toggle("on", pt.id === `hk-pt-${result.person}`);
    }
    next(result);
  }

  // --- 段2・段3: the listener's questions, the ladder, the scale ---

  // One card in the talk: the listener (AI), the teacher's question, or the
  // student. 直し45 段5: the AI's questions as コーチ（AI） (① and ②), in the
  // AI's colour and shape. 直し46: the scale's next one (③, the teacher's
  // fixed words) is 先生の問い, as the teacher's other questions.
  function say(who, text, extra, cls = "") {
    const card = el("div", `hk-card ${who} ${cls}`.trim());
    card.append(el("span", "hk-who", { ai: app.state.hitokoto.who_coach, teacher: W.who_teacher, me: W.who_me }[who]));
    if (text) card.append(el("p", "hk-q", text));
    if (extra) card.append(extra);
    $("hk-log").append(card);
    card.scrollIntoView({ block: "nearest", behavior: still() ? "auto" : "smooth" });
    return card;
  }

  function clearInput() {
    $("hk-input").replaceChildren();
  }

  function message(text) {
    let line = $("hk-message");
    if (!line) {
      line = el("p", "message");
      line.id = "hk-message";
      line.setAttribute("role", "status");
    }
    line.textContent = text;
    $("hk-input").prepend(line);
  }

  // The server says what comes next.
  function next(result) {
    if (result.status === "ask_again") return message(result.message);
    clearInput();
    if (result.next === "ask") {
      say("ai", result.question);
      return answerBox();
    }
    if (result.next === "again") {  // 「だいじょうぶ。…」 and the same question, in one card.
      say("ai", result.note).append(el("p", "hk-q", result.question));
      return answerBox();
    }
    if (result.next === "ladder_two") return ladderTwo(result);
    if (result.next === "ladder_three") return ladderThree(result);
    if (result.next === "fill") return ladderFill(result);
    if (result.next === "scale") return askScale(result.question);
  }

  // A line to write (and 「わからない」): the answer to the listener's question.
  function answerBox() {
    const form = el("form", "hk-answer");
    const input = el("input");
    Object.assign(input, { type: "text", maxLength: 120, placeholder: W.placeholder, autocomplete: "off" });
    input.setAttribute("aria-label", W.who_me);
    const send = el("button", "hk-primary", W.send);
    send.type = "submit";
    const unsure = button("hk-pick", W.dont_know);
    form.append(input, send, unsure);
    $("hk-input").append(form);
    input.focus({ preventScroll: true });
    const go = async (body, shown) => {
      if (busy) return;
      busy = true;
      for (const node of form.querySelectorAll("input, button")) node.disabled = true;
      const waiting = body.dont_know ? null : say("ai", W.thinking, null, "waiting");
      let result;
      try {
        result = await post("answer", body);
      } catch (error) {
        if (waiting) waiting.remove();
        message(app.sendFailed(error));
        for (const node of form.querySelectorAll("input, button")) node.disabled = false;
        busy = false;
        return;
      }
      if (waiting) waiting.remove();
      busy = false;
      if (result.status === "ask_again") {
        for (const node of form.querySelectorAll("input, button")) node.disabled = false;
        input.focus();
        return message(result.message);
      }
      say("me", shown);
      next(result);
    };
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (text) go({ text }, text);
    });
    unsure.addEventListener("click", () => go({ dont_know: true }, W.dont_know));
  }

  async function ladderStep(step, body, shown, box = null) {
    if (busy) return;
    busy = true;
    let result;
    try {
      result = await post(step, body);
    } catch (error) {
      busy = false;
      if (box) unlock(box);
      return message(app.sendFailed(error));
    }
    busy = false;
    if (result.status === "ask_again") {
      if (box) unlock(box);
      return message(result.message);
    }
    if (shown) say("me", shown);
    next(result);
  }

  // Answered or picked (直し40-0): nothing more to press, but the card is not
  // faded: the people's and the student's words read as before. That it is
  // done shows in its edge (style.css .hk-done), the one picked by a small
  // mark; the buttons that went on are gone.
  function lock(box, chosen = null) {
    for (const node of box.querySelectorAll("input, button, select, textarea")) node.disabled = true;
    box.classList.add("hk-done");
    if (chosen) {
      chosen.classList.add("hk-chosen");
      chosen.setAttribute("aria-pressed", "true");
    }
  }

  // A send that failed: the box can be answered again.
  function unlock(box) {
    for (const node of box.querySelectorAll("input, button, select, textarea")) node.disabled = false;
    box.classList.remove("hk-done");
    for (const node of box.querySelectorAll(".hk-chosen")) {
      node.classList.remove("hk-chosen");
      node.removeAttribute("aria-pressed");
    }
  }

  // 2択: the split's two people's own words; no 「どっちでもない」.
  function ladderTwo(result) {
    const box = el("div", "hk-options");
    for (const option of result.options) {
      const quote = button("hk-quote", option.said ? `「${option.text}」` : option.text, () => {
        lock(box, quote);
        ladderStep("ladder", { choice: option.index }, fill(W.ladder_two_me, { who: option.title }), box);
      });
      quote.append(el("small", "", `${option.title}（${option.kind_label}）`));
      box.append(quote);
    }
    say("teacher", result.question, box);
    box.querySelector("button").focus({ preventScroll: true });
  }

  // 3択: the people on the map.
  function ladderThree(result) {
    const box = el("div", "hk-picks");
    for (const option of result.options) {
      const pick = button("hk-pick", option.title, () => {
        lock(box, pick);
        ladderStep("ladder", { choice: option.index }, option.title, box);
      });
      box.append(pick);
    }
    say("teacher", result.question, box);
    box.querySelector("button").focus({ preventScroll: true });
  }

  // The line with a blank: only the blank is written, or left empty.
  function ladderFill(result) {
    const form = el("form", "hk-fill");
    const input = el("input");
    Object.assign(input, { type: "text", maxLength: 120, autocomplete: "off" });
    input.setAttribute("aria-label", `${result.before}…${result.after}`);
    const line = el("p", "hk-fill-line");
    line.append(result.before, input, result.after);
    const ok = el("button", "hk-primary", W.fill_ok);
    ok.type = "submit";
    const empty = button("quiet", W.fill_skip);
    const row = el("div", "hk-row");
    row.append(ok, empty);
    form.append(line, row);
    say("teacher", result.question, form);
    input.focus({ preventScroll: true });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();
      lock(form);
      if (text) ladderStep("fill", { text }, `${result.before}${text}${result.after}`, form);
      else ladderStep("fill", { skip: true }, "", form);
    });
    empty.addEventListener("click", () => {
      lock(form);
      ladderStep("fill", { skip: true }, "", form);
    });
  }

  // The teacher's scale: 0 to 15, starting at 10.
  function askScale(question) {
    clearInput();
    const box = el("div", "hk-scale");
    const now = el("p", "hk-scale-now", "10");
    now.setAttribute("aria-hidden", "true");
    const range = el("input");
    Object.assign(range, { type: "range", min: "0", max: "15", value: "10", step: "1" });
    range.setAttribute("aria-label", question);
    const ticks = el("p", "hk-ticks");
    ticks.append(el("span", "", W.scale_low), el("span", "", W.scale_first), el("span", "", "15"));
    range.addEventListener("input", () => { now.textContent = range.value; });
    const ok = button("hk-primary", W.scale_ok, async () => {
      if (busy) return;
      busy = true;
      lock(box);
      let result;
      try {
        result = await post("scale", { value: Number(range.value) });
      } catch (error) {
        busy = false;
        unlock(box);
        return message(app.sendFailed(error));
      }
      busy = false;
      say("me", fill(W.scale_me, { n: range.value }));
      // 直し48 段7: at 0, no next question; on to the way to keep.
      if (result.next === "way") return askWay();
      say("teacher", result.question);
      lineBox("forward", { send: W.send, skip: W.skip }, () => askWay());
    });
    box.append(now, range, ticks, ok);
    say("teacher", question, box);
    range.focus({ preventScroll: true });
  }

  // One optional line, then on: the scale's next question, the way to keep, which lesson.
  function lineBox(step, { send, skip, placeholder = W.placeholder, label = W.who_me }, after, card = null) {
    clearInput();
    const form = el("form", "hk-answer");
    const input = el("input");
    Object.assign(input, { type: "text", maxLength: 120, placeholder, autocomplete: "off" });
    input.setAttribute("aria-label", label);
    const ok = el("button", "hk-primary", send);
    ok.type = "submit";
    const pass = button("quiet", skip);
    form.append(input, ok, pass);
    (card || $("hk-input")).append(form);
    input.focus({ preventScroll: true });
    const go = async (body) => {
      if (busy) return;
      busy = true;
      lock(form);
      let result;
      try {
        result = await post(step, body);
      } catch (error) {
        busy = false;
        unlock(form);
        return message(app.sendFailed(error));
      }
      busy = false;
      if (result.status === "ask_again") {
        unlock(form);
        input.focus();
        return message(result.message);
      }
      if (body.text) say("me", body.text);
      if (!card) form.remove();
      after(result);
    };
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();
      go(text ? { text } : { skip: true });
    });
    pass.addEventListener("click", () => go({ skip: true }));
    return form;
  }

  // --- 段4: what to keep, and the harvest card's ② and ③ ---

  function askWay() {
    const card = say("teacher", W.way_q);
    lineBox("way", { send: W.way_ok, skip: W.way_none, placeholder: W.way_example }, () => askSubject(), card);
  }

  function askSubject() {
    clearInput();
    const box = el("div", "hk-picks");
    const answers = [["yes", W.subject_yes], ["no", W.subject_no], ["unsure", W.subject_unsure]];
    for (const [key, text] of answers) {
      const pick = button("hk-pick", text, async () => {
        if (busy) return;
        busy = true;
        lock(box, pick);
        try {
          await post("subject", { answer: key });
        } catch (error) {
          busy = false;
          unlock(box);
          return message(app.sendFailed(error));
        }
        busy = false;
        say("me", text);
        if (key === "yes") {
          const which = say("teacher", W.subject_which);
          lineBox("subject_note", { send: W.send, skip: W.skip, placeholder: W.subject_example, label: W.subject_which },
            (result) => { showSubject(result.subject); askMeet(); }, which);
        } else {
          askMeet();
        }
      });
      box.append(pick);
    }
    say("teacher", W.subject_q, box);
    box.querySelector("button").focus({ preventScroll: true });
  }

  // ③ under the lesson's line: the card as the reflection sheet shows it
  // (the question held now on the left, the subject's card on the right).
  function showSubject(subject) {
    if (!subject) return;
    let box = $("hk-subject");
    if (!box) {  // Under the lesson's line and the student's answer to it.
      box = el("div", "harvest hk-harvest");
      box.id = "hk-subject";
      $("hk-log").append(box);
    }
    box.replaceChildren(el("h3", "", app.state.texts.harvest_heading), el("p", "subject-link", subject.link));
    const cards = el("div", "subject-cards");
    subject.cards.forEach((card, index) => {
      const node = el("div", "subject-card");
      node.append(el("p", "when", card.when), el("p", "subject", card.subject));
      if (card.heading) node.append(el("p", "heading", `「${card.heading}」`));
      node.append(el("p", "note", card.note));
      if (subject.choose) node.append(button("quiet", app.state.texts.harvest_subject_pick, () => subjectStep("subject_choose", { choice: index })));
      cards.append(node);
    });
    const question = el("div", "subject-question");
    question.append(el("p", "label", app.state.texts.harvest_subject_question), el("p", "words", subject.question));
    const tie = el("div", `subject-tie${subject.cards.length > 1 ? " two" : ""}`);
    const between = el("div", "subject-tie-line");
    between.setAttribute("aria-hidden", "true");
    tie.append(question, between, cards);
    box.append(tie);
    if (subject.choose) box.append(button("quiet", app.state.texts.harvest_subject_none, () => subjectStep("subject_choose", { choice: "none" })));
    if (subject.more) box.append(button("", app.state.texts.harvest_subject_more, () => subjectStep("subject_more", {})));
  }

  async function subjectStep(step, body) {
    const box = $("hk-subject");
    // Waiting only: the card is drawn again with what comes back.
    for (const node of box.querySelectorAll("button")) node.disabled = true;
    try {
      showSubject((await post(step, body)).subject);
    } catch (error) {
      box.querySelectorAll("button").forEach((node) => { node.disabled = false; });
    }
  }

  // The seat to hear more from (texts/meet_question.txt), or none; a seat: ②.
  function askMeet() {
    clearInput();
    const box = el("div", "hk-meet");
    const select = el("select");
    select.setAttribute("aria-label", app.state.texts.meet_question);
    select.append(new Option(W.meet_pick, ""));
    const met = el("optgroup");
    met.label = W.meet_met;
    const others = el("optgroup");
    others.label = W.meet_others;
    for (const seat of app.state.seats) {
      (app.state.met.has(seat.seat_id) ? met : others).append(new Option([seat.title, seat.detail].filter(Boolean).join("　"), seat.seat_id));
    }
    if (met.children.length) select.append(met);
    select.append(others);
    const row = el("div", "hk-row");
    const go = async (seat) => {
      if (busy) return;
      busy = true;
      lock(box);
      let result;
      try {
        result = await post("meet", { seat_id: seat });
      } catch (error) {
        busy = false;
        unlock(box);
        return message(app.sendFailed(error));
      }
      busy = false;
      say("me", seat ? select.selectedOptions[0].textContent : W.meet_none);
      if (result.uses.length) askUse(result.uses);
      else atEnd();
    };
    row.append(button("hk-primary", W.meet_ok, () => { if (select.value) go(select.value); }),
      button("quiet", W.meet_none, () => go("")));
    box.append(select, row);
    say("teacher", app.state.texts.meet_question, box);
    select.focus({ preventScroll: true });
  }

  function askUse(uses) {
    const box = el("div", "hk-uses");
    const go = async (use, text, chosen) => {
      if (busy) return;
      busy = true;
      lock(box, chosen);
      let result;
      try {
        result = await post("use", { use });
      } catch (error) {
        busy = false;
        unlock(box);
        return message(app.sendFailed(error));
      }
      busy = false;
      say("me", text);
      const card = el("div", "harvest hk-harvest");
      card.append(el("h3", "", app.state.texts.harvest_heading), el("p", "", result.meet));
      $("hk-log").append(card);
      atEnd();
    };
    for (const use of uses) {
      const choice = button("hk-pick", null, () => go(use.force, use.text, choice));
      choice.append(el("span", "", use.text), el("span", "hk-force", use.name));
      box.append(choice);
    }
    const none = button("hk-pick", W.meet_none, () => go("none", W.meet_none, none));
    box.append(none);
    say("teacher", app.state.texts.harvest_use_question, box);
    box.querySelector("button").focus({ preventScroll: true });
  }

  // Everything asked: the main button 「光ったところを見る」 goes on to the
  // light (直し40-0). 「ここまでにする」, the quiet way out at any time before,
  // goes: both would do the same.
  function atEnd() {
    clearInput();
    const go = button("hk-primary", W.to_light, toLight);
    go.id = "hk-to-light";
    const row = el("div", "hk-row");
    row.append(go);
    $("hk-input").append(row);
    $("hk-stop").hidden = true;
    go.focus({ preventScroll: true });
    go.scrollIntoView({ block: "nearest", behavior: still() ? "auto" : "smooth" });
  }

  // --- 段5: today's light ---

  async function toLight() {
    if (busy) return;
    busy = true;
    show("light");
    const box = $("hk-light-box");
    box.replaceChildren(el("h3", "", W.light_title), el("p", "hk-lead waiting", W.summing));
    let light;
    try {
      light = await post("light");
    } catch (error) {
      box.replaceChildren(el("p", "message", app.sendFailed(error)));
      busy = false;
      return;
    }
    busy = false;
    box.replaceChildren(el("h3", "", W.light_title));
    if (light.scale !== null) box.append(el("p", "hk-scaleline", fill(W.light_scale, { n: light.scale })));
    box.append(el("p", "hk-lead", light.source === "chosen" ? W.light_lead_chosen : W.light_lead),
      el("p", "hk-big", `「${light.quote}」`));
    if (light.source === "chosen") box.append(el("p", "hk-label", fill(W.light_chosen_who, { who: light.chosen_who })));
    box.append(el("p", "hk-why", light.why));
    if (light.deep) box.append(el("p", "hk-deep", `${light.deep}${W.light_deep_tail}`));
    if (light.next_step) {
      const step = el("div", "hk-step");
      step.append(el("p", "hk-label", W.light_step), el("p", "hk-stepq", `「${light.next_step}」`));
      box.append(step);
    }
    $("hk-now").value = light.now_question;
    $("hk-to-sheet").focus({ preventScroll: true });
  }

  // --- 段6: the sheet, and printing it ---

  // One person's sentence on the sheet (直し48 段4): their own words in 「」
  // (an article's with its note), their title after.
  function metLine(person) {
    const line = el("p", "hk-met-line");
    line.append(el("span", "hk-met-quote", person.said ? `「${person.quote}」` : person.quote),
      el("span", "hk-met-who", [person.title, person.said ? "" : person.note].filter(Boolean).join("　")));
    return line;
  }

  async function toSheet() {
    if (busy) return;
    busy = true;
    const line = $("hk-now-message");
    line.hidden = true;
    // 直し48 段4: while the sheet is made (司会（AI）のまとめ is asked), the
    // sheet's page with 「整理中」 on it, never still; after a while, the slow line.
    const box = $("hk-sheet-body");
    const signs = app.state.texts.wait_sign;
    const waitLine = el("p", "hk-making-line", signs.sheet.line);
    const dots = el("span", "hk-making-dots");
    for (let n = 0; n < 3; n++) dots.append(el("span"));
    const waiting = el("div", "hk-making");
    waiting.setAttribute("role", "status");
    waiting.append(el("p", "hk-making-word", signs.sheet.word), waitLine, dots);
    box.replaceChildren(waiting);
    const slow = setTimeout(() => { waitLine.textContent = signs.slow.line; }, 15000);
    show("sheet");
    let sheet;
    try {
      sheet = await post("sheet", { now_question: $("hk-now").value.trim() });
    } catch (error) {
      clearTimeout(slow);
      show("light");
      line.textContent = app.sendFailed(error);
      line.hidden = false;
      busy = false;
      return;
    }
    clearTimeout(slow);
    busy = false;
    if (sheet.status === "ask_again") {
      show("light");
      line.textContent = sheet.message;
      line.hidden = false;
      return;
    }
    box.replaceChildren(el("h3", "", W.sheet_title));
    const questions = el("div", "hk-qq");
    const first = el("div", "hk-qbox");
    first.append(el("p", "hk-label", W.first_label), el("p", "", sheet.first_question));
    const now = el("div", "hk-qbox");
    now.append(el("p", "hk-label", W.sheet_now), el("p", "", sheet.now_question || W.sheet_same));
    const arrow = el("p", "hk-arrow", "→");
    arrow.setAttribute("aria-hidden", "true");
    questions.append(first, arrow, now);
    box.append(questions);
    // 直し48 段4 (the teacher, 11/7: 「なるほど！となるか？」): each person met,
    // one sentence of their words as recorded with their title; the
    // student's own words in turn; 司会（AI）のまとめ (two people's sentences
    // and how they go, the split); the seat to meet. Every word is the
    // record's, the student's, or texts/.
    if (sheet.met && sheet.met.length) {
      const met = el("div", "hk-met");
      met.append(el("p", "hk-label", W.sheet_met));
      for (const person of sheet.met) met.append(metLine(person));
      box.append(met);
    }
    if (sheet.moves && sheet.moves.length > 1) {
      const moves = el("div", "hk-moves");
      moves.append(el("p", "hk-label", W.sheet_moves));
      const list = el("ol", "hk-moves-list");
      for (const text of sheet.moves) list.append(el("li", "", text));
      moves.append(list);
      box.append(moves);
    }
    if (sheet.tie || sheet.split) {
      const tie = el("div", "hk-tie");
      tie.append(el("p", "hk-label hk-ai-label", W.sheet_tie));
      if (sheet.tie) {
        tie.append(el("p", "hk-tie-line", W[`tie_${sheet.tie.kind}`]));
        const two = el("div", "hk-tie-two");
        two.append(metLine(sheet.tie.a), metLine(sheet.tie.b));
        tie.append(two);
      }
      if (sheet.split) {
        tie.append(el("p", "hk-tie-split", W.sheet_split),
          el("p", "hk-tie-heading", `${sheet.split.heading}（${sheet.split.a}・${sheet.split.b}）`));
      }
      box.append(tie);
    }
    // 直し45 段5: the steps marked on the trail, with the student's line.
    if (sheet.marks && sheet.marks.length) {
      const marked = el("div", "hk-marked");
      marked.append(el("p", "hk-label", app.state.hitokoto.mark_words.sheet));
      for (const mark of sheet.marks) {
        const line = el("p", "hk-marked-line");
        line.append(el("b", "", mark.label), "　", mark.text);
        marked.append(line);
        if (mark.note) marked.append(el("p", "hk-marked-note", `「${mark.note}」`));
      }
      box.append(marked);
    }
    box.append(el("p", "hk-label", W.sheet_story));
    const story = el("p", "hk-story");
    for (const part of sheet.story) story.append(part.strong ? el("b", "", part.text) : part.text);
    box.append(story);
    if (sheet.light) {
      const lit = el("div", "hk-litbox");
      lit.append(el("p", "hk-label", W.light_title), el("p", "hk-lit", `「${sheet.light.quote}」`), el("p", "", sheet.light.why));
      box.append(lit);
    }
    if (sheet.next_step) {
      const step = el("div", "hk-litbox");
      step.append(el("p", "hk-label", W.sheet_step), el("p", "hk-lit", `「${sheet.next_step}」`));
      box.append(step);
    }
    if (sheet.meet) {
      const meet = el("div", "hk-litbox");
      meet.append(el("p", "hk-label", W.sheet_meet), el("p", "", sheet.meet));
      box.append(meet);
    }
    box.append(el("p", "hk-print-note", W.print_note));
    show("sheet");
    // 最初にもどる, as under the reflection sheet (直し30-2).
    $("hk-back").append($("back-to-start"));
    app.showBackToStart();
    $("hk-print").focus({ preventScroll: true });
  }

  function setup() {
    $("hk-go").addEventListener("click", () => choose(false));
    $("hk-omakase").addEventListener("click", () => choose(true));
    $("hk-stop").addEventListener("click", toLight);
    $("hk-to-sheet").addEventListener("click", toSheet);
    $("hk-print").addEventListener("click", () => window.print());
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();

  return { open };
})();
