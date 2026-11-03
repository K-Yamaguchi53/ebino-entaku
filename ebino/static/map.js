// The hand-drawn map of the basin, over the seat list (SPEC 5-1, 14-65). The
// seat list stays as it is: the map adds to it. Lines are drawn with rough.js
// (bundled, MIT). Every word is set with textContent, never as HTML, and the
// map shows seat labels and quotes only, never a person's name.
"use strict";

const EbinoMap = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const LIGHT_EVERY = 400;  // ms between two seats lighting up.
  const BUBBLE_FOR = 1500;  // ms a quote's bubble stays.
  const BUBBLE_CHARS = 36;  // A longer quote is cut here, with 「…」.
  const DRAW_FOR = 1800;  // ms to draw the rim; the river follows.
  const MOUNTAINS = 16;

  let map = null;  // The drawing from /api/setup.
  let app = null;  // What app.js lends: state, cardEntry, renderSeats, shownQuotes.
  let svg, overlay, splitLayer, card;
  const points = {};  // Seat ID -> the point's <g>.
  let timers = [];
  let sticky = null;  // The seat whose label stays (the last to light up).
  let drawn = false;

  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);

  function svgEl(tag, attrs = {}) {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  }

  function div(className, text) {
    const node = document.createElement("div");
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // --- geometry (the same rule as seat_map.py's rim_point) ---

  function centroid(ring) {
    let area = 0, cx = 0, cy = 0;
    ring.forEach(([x1, y1], i) => {
      const [x2, y2] = ring[(i + 1) % ring.length];
      const cross = x1 * y2 - x2 * y1;
      area += cross; cx += (x1 + x2) * cross; cy += (y1 + y2) * cross;
    });
    return [cx / (3 * area), cy / (3 * area)];
  }

  function rimPoint([cx, cy], [dx, dy], ring) {
    let far = 0;
    ring.forEach(([x1, y1], i) => {
      const [x2, y2] = ring[(i + 1) % ring.length];
      const ex = x2 - x1, ey = y2 - y1, d = dx * ey - dy * ex;
      if (Math.abs(d) < 1e-12) return;
      const t = ((x1 - cx) * ey - (y1 - cy) * ex) / d;
      const u = ((x1 - cx) * dy - (y1 - cy) * dx) / d;
      if (t > 0 && u >= 0 && u <= 1) far = Math.max(far, t);
    });
    return [cx + far * dx, cy + far * dy];
  }

  // --- drawing ---

  function init(drawing, seats, lent) {
    map = drawing;
    app = lent;
    const [, , width, height] = map.viewbox;
    svg = $("map-svg");
    overlay = $("map-overlay");
    card = $("map-card");
    svg.setAttribute("viewBox", map.viewbox.join(" "));
    $("map-frame").style.aspectRatio = `${width} / ${height}`;
    const rc = rough.svg(svg);
    const layer = (className) => svg.appendChild(svgEl("g", { class: className }));
    // Colours come from style.css (a CSS rule beats rough's attributes). No
    // fill option: rough would hatch the inside.
    const ink = { stroke: "#000", seed: 7 };

    const fill = layer("basin-fill");
    fill.append(svgEl("polygon", { points: map.boundary.map((p) => p.join(",")).join(" ") }));

    const river = layer("river draw-later");
    for (const line of map.river) {
      river.append(rc.linearPath(line, { ...ink, strokeWidth: 3, roughness: 0.9, bowing: 0.6 }));
    }
    const rim = layer("rim draw-first");
    rim.append(rc.polygon(map.boundary, { ...ink, strokeWidth: 2.2, roughness: 1.3, bowing: 0.8 }));

    // Mountains: a decoration, not data. Small peaks just beyond the rim.
    const hills = layer("mountains");
    const middle = centroid(map.boundary);
    const seatXY = seats.filter((s) => s.x !== undefined).map((s) => [s.x, s.y]);
    for (let k = 0; k < MOUNTAINS; k++) {
      const angle = (k + 0.5) * 2 * Math.PI / MOUNTAINS;
      const dir = [Math.cos(angle), Math.sin(angle)];
      const [rx, ry] = rimPoint(middle, dir, map.boundary);
      const x = rx + 40 * dir[0], y = ry + 40 * dir[1];
      if (x < 20 || y < 20 || x > width - 20 || y > height - 20) continue;
      if (seatXY.some(([sx, sy]) => Math.hypot(sx - x, sy - y) < 22)) continue;
      hills.append(rc.linearPath([[x - 13, y + 7], [x - 4, y - 8], [x + 1, y - 1], [x + 6, y - 6], [x + 14, y + 7]],
        { ...ink, strokeWidth: 1.4, roughness: 0.8, seed: 11 + k }));
    }

    const names = layer("place-names");
    for (const place of map.places) {
      const text = svgEl("text", { x: place.x, y: place.y, "text-anchor": "middle" });
      text.textContent = place.name;
      names.append(text);
    }

    if (map.crossing) {
      const line = layer("crossing");
      line.append(rc.line(...map.crossing.from, ...map.crossing.to, { ...ink, strokeWidth: 2, roughness: 1.1 }));
      line.append(svgEl("circle", { cx: map.crossing.from[0], cy: map.crossing.from[1], r: 5 }));
    }

    splitLayer = layer("split-lines");
    const seatLayer = layer("points");
    for (const seat of seats) {
      if (seat.x === undefined) continue;
      const point = drawPoint(seat);
      points[seat.seat_id] = point;
      seatLayer.append(point);
    }
    // Over the points so its label reads; it takes no presses (not a seat).
    if (map.school) drawSchool(layer("school"), map.school);
    $("map-source").textContent = map.source;
    $("map").hidden = false;
    refresh();
  }

  function drawSchool(group, school) {
    group.setAttribute("transform", `translate(${school.x} ${school.y})`);
    group.setAttribute("role", "img");
    group.setAttribute("aria-label", school.label);
    group.append(
      svgEl("rect", { x: -9, y: -4, width: 18, height: 12 }),
      svgEl("polygon", { points: "-11,-4 0,-12 11,-4" }),
      svgEl("line", { class: "pole", x1: 9, y1: -4, x2: 9, y2: -26 }),
      svgEl("polygon", { class: "flag", points: "9,-26 20,-22 9,-18" }));
    const label = svgEl("text", { x: 0, y: 28, "text-anchor": "middle" });
    label.textContent = school.label;
    group.append(label);
  }

  // Circle, square, triangle, diamond: the kind shows in the shape as well
  // as the colour (never the colour alone).
  function shape(kind) {
    if (kind === "poster") return svgEl("rect", { class: "shape", x: -7, y: -7, width: 14, height: 14 });
    if (kind === "cross") return svgEl("polygon", { class: "shape", points: "0,-9 8.5,6.5 -8.5,6.5" });
    if (kind === "outsider_teacher") return svgEl("polygon", { class: "shape", points: "0,-9.5 9.5,0 0,9.5 -9.5,0" });
    return svgEl("circle", { class: "shape", r: 7.5 });
  }

  function drawPoint(seat) {
    const point = svgEl("g", {
      class: `pt kind-${seat.kind}`, transform: `translate(${seat.x} ${seat.y})`,
      tabindex: 0, role: "button", "data-seat": seat.seat_id,
    });
    point.append(svgEl("circle", { class: "halo", r: 14 }), shape(seat.kind),
      svgEl("circle", { class: "met-mark", cx: 8, cy: -8, r: 3.5 }));
    const ask = svgEl("text", { class: "ask-mark", x: 9, y: -6 });
    ask.textContent = "？";
    point.append(ask);
    point.addEventListener("mouseenter", () => showTip(seat.seat_id));
    point.addEventListener("focus", () => showTip(seat.seat_id));
    point.addEventListener("mouseleave", restoreTip);
    point.addEventListener("blur", restoreTip);
    point.addEventListener("click", () => press(seat.seat_id));
    point.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        press(seat.seat_id);
      }
    });
    return point;
  }

  // Draws the rim, then the river, as if by hand. Called when the map is on
  // screen (a path's length needs it laid out).
  function show() {
    if (!map || drawn) return;
    drawn = true;
    if (reduced()) return;
    for (const [selector, delay] of [[".draw-first path", 0], [".draw-later path", DRAW_FOR * 0.6]]) {
      for (const path of svg.querySelectorAll(selector)) {
        const length = path.getTotalLength();
        if (!length) continue;
        path.style.strokeDasharray = `${length} ${length}`;
        path.style.strokeDashoffset = String(length);
        path.style.transitionDelay = `${delay}ms`;
        path.style.transitionDuration = `${DRAW_FOR}ms`;
      }
    }
    svg.getBoundingClientRect();  // Lay out the start before the change.
    requestAnimationFrame(() => {
      svg.classList.add("drawing");
      for (const path of svg.querySelectorAll(".draw-first path, .draw-later path")) path.style.strokeDashoffset = "0";
    });
  }

  // --- labels and bubbles, over the map in CSS pixels ---

  function place(node, x, y, gap) {
    const [, , width, height] = map.viewbox;
    const frame = overlay.getBoundingClientRect();
    const px = x / width * frame.width, py = y / height * frame.height;
    const box = node.getBoundingClientRect();
    const left = Math.max(4, Math.min(px - box.width / 2, frame.width - box.width - 4));
    let top = py - box.height - gap;
    if (top < 4) top = py + gap;
    node.style.left = `${left}px`;
    node.style.top = `${Math.min(top, Math.max(4, frame.height - box.height - 4))}px`;
  }

  function seatOf(seatId) { return app.state.seatById[seatId]; }

  function showTip(seatId) {
    const seat = seatOf(seatId);
    if (!seat) return;
    hideTip();
    const tip = div("map-tip");
    tip.dataset.seat = seatId;
    tip.append(div("title", seat.title));
    if (seat.detail) tip.append(div("detail", seat.detail));
    if (isSilent(seatId)) tip.append(div("detail", app.state.texts.not_asked_yet));
    overlay.append(tip);
    place(tip, seat.x, seat.y, 16);
  }

  function hideTip() { for (const tip of overlay.querySelectorAll(".map-tip")) tip.remove(); }
  function restoreTip() { if (sticky) showTip(sticky); else hideTip(); }

  function bubble(seatId, quote) {
    const seat = seatOf(seatId);
    if (!seat || !quote) return;
    const chars = [...quote.text];
    const cut = chars.length > BUBBLE_CHARS ? chars.slice(0, BUBBLE_CHARS).join("") + "…" : quote.text;
    const node = div("map-bubble", quote.said ? `「${cut}」` : cut);
    overlay.append(node);
    place(node, seat.x, seat.y, 18);
    timers.push(setTimeout(() => node.remove(), BUBBLE_FOR));
  }

  // --- a round ---

  function isSilent(seatId) { return app.state.silent.has(seatId) && !app.state.met.has(seatId); }

  function clearRound() {
    for (const timer of timers) clearTimeout(timer);
    timers = [];
    sticky = null;
    hideTip();
    for (const node of overlay.querySelectorAll(".map-bubble, .split-tag")) node.remove();
    splitLayer.replaceChildren();
    for (const point of Object.values(points)) point.classList.remove("lit");
  }

  // The seats quoted light up one after another, each with its first quote
  // in a short bubble; then the splits. No seat answered: nothing lights.
  function round(result) {
    if (!map) return;
    clearRound();
    refresh();
    const first = {};
    for (const quote of result.quotes) if (!(quote.seat_id in first)) first[quote.seat_id] = quote;
    const order = result.seat_order.filter((id) => points[id]);
    if (!order.length) return;
    const last = order[order.length - 1];
    if (reduced()) {  // Everything at once: no order, no bubbles.
      for (const id of order) points[id].classList.add("lit");
      sticky = last;
      showTip(last);
      drawSplits(result);
      return;
    }
    order.forEach((id, k) => timers.push(setTimeout(() => {
      points[id].classList.add("lit");
      bubble(id, first[id]);
    }, k * LIGHT_EVERY)));
    const end = (order.length - 1) * LIGHT_EVERY;
    timers.push(setTimeout(() => drawSplits(result), end + LIGHT_EVERY));
    timers.push(setTimeout(() => { sticky = last; showTip(last); }, end + BUBBLE_FOR));
  }

  // A dashed line between the first seat of each side, its heading near it.
  function drawSplits(result) {
    const seatOfQuote = {};
    for (const quote of result.quotes) seatOfQuote[quote.utterance_id] = quote.seat_id;
    for (const split of result.splits) {
      const a = points[seatOfQuote[split.side_a[0]]] && seatOf(seatOfQuote[split.side_a[0]]);
      const b = points[seatOfQuote[split.side_b[0]]] && seatOf(seatOfQuote[split.side_b[0]]);
      if (!a || !b || a === b) continue;
      splitLayer.append(svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y }));
      const tag = div("split-tag", app.shownQuotes(split.heading));
      overlay.append(tag);
      place(tag, (a.x + b.x) / 2, (a.y + b.y) / 2, 8);
    }
  }

  // --- marks that stay: met seats, and 「？」 on seats nobody asked yet ---

  function refresh() {
    if (!map) return;
    for (const [id, point] of Object.entries(points)) {
      point.classList.toggle("met", app.state.met.has(id));
      point.classList.toggle("silent", isSilent(id));
      const seat = seatOf(id);
      const words = [seat.title, seat.detail, isSilent(id) ? app.state.texts.not_asked_yet : ""];
      point.setAttribute("aria-label", words.filter(Boolean).join("　"));
    }
    $("map-met-count").textContent = String(app.state.met.size);
  }

  // Pressing a 「？」 opens the same 「聞きたいことを書く」 as the seat list.
  // Pressing any other point keeps its label shown.
  function press(seatId) {
    if (!isSilent(seatId)) {
      sticky = seatId;
      showTip(seatId);
      return;
    }
    const seat = seatOf(seatId);
    card.replaceChildren(div("title", seat.title), div("not-asked", app.state.texts.not_asked_yet));
    const close = document.createElement("button");
    close.type = "button";
    close.className = "quiet close";
    close.textContent = "閉じる";
    close.addEventListener("click", () => { card.hidden = true; points[seatId].focus(); });
    if (app.state.carded.has(seatId)) {
      card.append(div("card-done", "質問カードにしました"));
    } else {
      const open = app.cardEntry(seatId, (form) => {
        form.replaceWith(div("card-done", "質問カードにしました"));
        app.renderSeats();
      });
      card.append(open);
      card.hidden = false;
      open.click();  // Opens the box at once, as the list's button does.
    }
    card.append(close);
    card.hidden = false;
  }

  return { init, show, round, refresh };
})();
