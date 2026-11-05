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
  let app = null;  // What app.js lends: call, el, state, setNow, sendFailed, showBackToStart.
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

  async function post(step, body = {}) {
    return app.call(`/api/hitokoto/${step}`, body);
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
    $("hk-now-label").textContent = W.now_label;
    $("hk-to-sheet").textContent = W.to_sheet;
    $("hk-print").textContent = W.print;
    $("hk-print-side").textContent = W.print_side;
    show("map");
    app.setNow();
    try {
      view = await post("begin", { opened: app.state.opened || [] });
    } catch (error) {
      $("hk-first").textContent = app.sendFailed(error);
      return;
    }
    $("hk-first").textContent = view.first_question;
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
      line.append(el("span", "hk-split-label", W.map_split), el("span", "hk-split-heading", view.split.heading));
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
      ...view.people.map((p) => p.title), view.split ? `${W.map_split}${view.split.heading}` : ""].filter(Boolean).join("。"));
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
        card = el("div", "hk-said");
        const body = el("span", "hk-words");
        const at = words.indexOf(part);  // The first place only: one place to press.
        const kw = button("hk-kw", part, () => pick(index, part, kw));
        kw.setAttribute("aria-pressed", "false");
        kw.setAttribute("aria-label", `${person.title}の言葉「${part}」`);
        body.append(words.slice(0, at), kw, words.slice(at + part.length));
        card.append(from, body);
      }
      if (!person.said && person.note) card.append(el("span", "hk-note", person.note));
      box.append(card);
    });
    $("hk-go").disabled = true;
    picked = null;
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

  // One card in the talk: the listener (AI), the teacher's question, or the student.
  function say(who, text, extra, cls = "") {
    const card = el("div", `hk-card ${who} ${cls}`.trim());
    card.append(el("span", "hk-who", { ai: W.who_ai, teacher: W.who_teacher, me: W.who_me }[who]));
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

  async function ladderStep(step, body, shown) {
    if (busy) return;
    busy = true;
    let result;
    try {
      result = await post(step, body);
    } catch (error) {
      busy = false;
      return message(app.sendFailed(error));
    }
    busy = false;
    if (result.status === "ask_again") return message(result.message);
    if (shown) say("me", shown);
    next(result);
  }

  function lock(box) {
    for (const node of box.querySelectorAll("input, button, select, textarea")) node.disabled = true;
  }

  // 2択: the split's two people's own words; no 「どっちでもない」.
  function ladderTwo(result) {
    const box = el("div", "hk-options");
    for (const option of result.options) {
      const quote = button("hk-quote", option.said ? `「${option.text}」` : option.text, () => {
        lock(box);
        ladderStep("ladder", { choice: option.index }, fill(W.ladder_two_me, { who: option.title }));
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
      box.append(button("hk-pick", option.title, () => {
        lock(box);
        ladderStep("ladder", { choice: option.index }, option.title);
      }));
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
      if (text) ladderStep("fill", { text }, `${result.before}${text}${result.after}`);
      else ladderStep("fill", { skip: true }, "");
    });
    empty.addEventListener("click", () => {
      lock(form);
      ladderStep("fill", { skip: true }, "");
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
        box.querySelectorAll("input, button").forEach((node) => { node.disabled = false; });
        return message(app.sendFailed(error));
      }
      busy = false;
      say("me", fill(W.scale_me, { n: range.value }));
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
        form.querySelectorAll("input, button").forEach((node) => { node.disabled = false; });
        return message(app.sendFailed(error));
      }
      busy = false;
      if (result.status === "ask_again") {
        form.querySelectorAll("input, button").forEach((node) => { node.disabled = false; });
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
      box.append(button("hk-pick", text, async () => {
        if (busy) return;
        busy = true;
        lock(box);
        try {
          await post("subject", { answer: key });
        } catch (error) {
          busy = false;
          box.querySelectorAll("button").forEach((node) => { node.disabled = false; });
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
      }));
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
    lock(box);
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
        box.querySelectorAll("select, button").forEach((node) => { node.disabled = false; });
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
    const go = async (use, text) => {
      if (busy) return;
      busy = true;
      lock(box);
      let result;
      try {
        result = await post("use", { use });
      } catch (error) {
        busy = false;
        box.querySelectorAll("button").forEach((node) => { node.disabled = false; });
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
      const choice = button("hk-pick", null, () => go(use.force, use.text));
      choice.append(el("span", "", use.text), el("span", "hk-force", use.name));
      box.append(choice);
    }
    box.append(button("hk-pick", W.meet_none, () => go("none", W.meet_none)));
    say("teacher", app.state.texts.harvest_use_question, box);
    box.querySelector("button").focus({ preventScroll: true });
  }

  // Everything asked: 「ここまでにする」 goes on to the light.
  function atEnd() {
    clearInput();
    $("hk-stop").classList.add("hk-primary");
    $("hk-stop").classList.remove("quiet");
    $("hk-stop").focus({ preventScroll: true });
    $("hk-stop").scrollIntoView({ block: "nearest", behavior: still() ? "auto" : "smooth" });
  }



  function setup() {
    $("hk-go").addEventListener("click", () => choose(false));
    $("hk-omakase").addEventListener("click", () => choose(true));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();

  return { open };
})();
