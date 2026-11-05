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





  function setup() {
    $("hk-go").addEventListener("click", () => choose(false));
    $("hk-omakase").addEventListener("click", () => choose(true));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();

  return { open };
})();
