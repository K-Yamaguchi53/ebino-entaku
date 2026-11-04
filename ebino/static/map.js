// The map of the basin, over the seat list (SPEC 5-1, 14-65, 14-66). The seat
// list stays as it is: the map adds to it.
//
// With the picture (relief.py: the basin drawn as a model, seen from the
// south with north up, 直し31-4), the map is laid over it: every (x, y) of seat_map.py is moved onto
// the picture here, on the screen only. A round lights the seats that
// answered, the camera comes closer, a round table opens over the basin and
// the lit seats fly to it. Without the picture (none, or it does not load),
// the flat hand-drawn map; without a map, the seat list alone.
//
// Lines are drawn with rough.js (bundled, MIT). Every word is set with
// textContent, never as HTML, and the map shows seat labels and quotes only,
// never a person's name.
"use strict";

const EbinoMap = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const LIGHT_EVERY = 400;  // ms between two seats lighting up.
  const BUBBLE_FOR = 1500;  // ms a quote's bubble stays.
  const BUBBLE_CHARS = 36;  // A longer quote is cut here, with 「…」.
  // CSS px: a card further from its seat reads as another seat's (on a wide
  // frame, this part of its width, if more: a thread of light ties the two).
  const BUBBLE_NEAR = 100, BUBBLE_NEAR_PART = 0.12;
  // At the round table (直し26-1) each seat that spoke keeps its lamp card,
  // its tail pointing at its chair, the card within TABLE_REACH px of it (or
  // this part of the frame's width, if more); a card with no room that near
  // is left out, and its seat shows it when pressed.
  const TABLE_REACH = 120, TABLE_REACH_PART = 0.13;
  const TABLE_STEP = 6;  // px between two spots tried for a card at the table.
  const TAIL_CORNER = 12;  // px a tail keeps from its card's corners.
  const TAIL_LENGTH = 16;  // px: a card's tail, at the least.
  const SEAT_PRESS = 44;  // px: the square a seat with no card up takes a press over.
  const TOUCH = 6;  // px between a lamp card and its choices, against its side.
  const AI_APART = 24;  // Degrees コーチ and オブザーバー keep from every seat at the table (直し29-1).
  // A small flame in its holder: コーチ's and オブザーバー's seat, no seat's mark.
  const AI_FLAME = "M0,-11 C3.6,-6.5 5.2,-3.4 5.2,-0.8 A5.2,5.2 0 0 1 -5.2,-0.8 C-5.2,-3.4 -3.6,-6.5 0,-11 Z " +
    "M-7,5.5 H7 L5,10 H-5 Z";
  // The pictures at the table's seats (直し29-3): lines on a 12px square
  // round 0,0, one thin line in the lamp's light, no words. Drawn here,
  // nothing read from outside.
  const SEAT_ICON_PATHS = {
    medical: "M0,-5 V5 M-5,0 H5",
    care: "M0,4.8 C-6,0.5 -5.6,-4.8 -2.7,-4.8 C-1.3,-4.8 0,-3.8 0,-2.6 C0,-3.8 1.3,-4.8 2.7,-4.8 C5.6,-4.8 6,0.5 0,4.8 Z",
    child: "M-5.5,5.5 H0 V0 H-5.5 Z M0,5.5 H5.5 V0 H0 Z M-2.7,0 V-5.5 H2.7 V0",
    beauty: "M-1.4,4 A1.9,1.9 0 1 1 -5.2,4 A1.9,1.9 0 1 1 -1.4,4 Z M5.2,4 A1.9,1.9 0 1 1 1.4,4 A1.9,1.9 0 1 1 5.2,4 Z " +
      "M-2,2.4 L4.6,-5.6 M2,2.4 L-4.6,-5.6",
    town: "M-6,-2 L0,-5.8 L6,-2 Z M-4.2,-0.6 V4 M0,-0.6 V4 M4.2,-0.6 V4 M-6,5.5 H6",
    food: "M-5.5,0 H5.5 A5.5,4.6 0 0 1 -5.5,0 Z M-2,5 H2 M-1.5,-1.6 L3.5,-6 M1.2,-1.6 L6,-5",
    farm: "M0,5.5 V-0.5 M0,1 C-0.8,-3 -4.2,-4.4 -5.6,-3.6 C-4.6,-0.8 -2.2,0.6 0,1 Z " +
      "M0,-0.5 C0.8,-4.5 4.2,-5.8 5.6,-5 C4.6,-2.2 2.2,-0.8 0,-0.5 Z M-4,5.5 H4",
    forest: "M0,-6 L4,-1 H-4 Z M0,-3 L5.5,3 H-5.5 Z M0,3 V6",
    stay: "M-5.5,2 A5.5,3.4 0 0 0 5.5,2 M-2.6,0 C-4.2,-2 -1,-3.4 -2.6,-6 M0,0 C-1.6,-2 1.6,-3.4 0,-6 " +
      "M2.6,0 C1,-2 4.2,-3.4 2.6,-6",
    build: "M-6,0 L0,-5.6 L6,0 M-4.5,-1.4 V5.5 H4.5 V-1.4 M-1.4,5.5 V2 H1.4 V5.5",
    make: "M3.5,0 A3.5,3.5 0 1 1 -3.5,0 A3.5,3.5 0 1 1 3.5,0 Z M1.3,0 A1.3,1.3 0 1 1 -1.3,0 A1.3,1.3 0 1 1 1.3,0 Z " +
      "M0,-3.5 V-5.8 M0,3.5 V5.8 M-3.5,0 H-5.8 M3.5,0 H5.8 M2.5,-2.5 L4.1,-4.1 M-2.5,2.5 L-4.1,4.1 M2.5,2.5 L4.1,4.1 M-2.5,-2.5 L-4.1,-4.1",
    move: "M-6,2.6 V-3.6 H1.4 V2.6 Z M1.4,-1.6 H4 L6,1 V2.6 H1.4 M-2.2,4.2 A1.5,1.5 0 1 1 -5.2,4.2 A1.5,1.5 0 1 1 -2.2,4.2 Z " +
      "M5,4.2 A1.5,1.5 0 1 1 2,4.2 A1.5,1.5 0 1 1 5,4.2 Z",
    safety: "M0,-6 L5,-4 V0 C5,3 2.6,5 0,6 C-2.6,5 -5,3 -5,0 V-4 Z",
    culture: "M5.5,-5.5 L0.6,-0.6 M0.6,-0.6 L-0.8,0.8 C-2.8,2.4 -4.4,4.4 -5.6,5.6 C-3.6,5 -1.6,3.6 0,2 Z",
    shop: "M-6,-2.2 H6 L5,-5.6 H-5 Z M-6,-2.2 A1.5,1.5 0 0 0 -3,-2.2 A1.5,1.5 0 0 0 0,-2.2 A1.5,1.5 0 0 0 3,-2.2 " +
      "A1.5,1.5 0 0 0 6,-2.2 M-5,-0.6 V5.6 H5 V-0.6 M-1.5,5.6 V2 H1.5 V5.6",
    animal: "M-2.8,3.2 A2.8,2.3 0 1 0 2.8,3.2 A2.8,2.3 0 1 0 -2.8,3.2 Z M-3,-0.8 A1.2,1.2 0 1 0 -5.4,-0.8 A1.2,1.2 0 1 0 -3,-0.8 Z " +
      "M-0.3,-3.6 A1.2,1.2 0 1 0 -2.7,-3.6 A1.2,1.2 0 1 0 -0.3,-3.6 Z M2.7,-3.6 A1.2,1.2 0 1 0 0.3,-3.6 A1.2,1.2 0 1 0 2.7,-3.6 Z " +
      "M5.4,-0.8 A1.2,1.2 0 1 0 3,-0.8 A1.2,1.2 0 1 0 5.4,-0.8 Z",
    poster: "M2.6,-1.2 A3.8,3.8 0 1 1 -5,-1.2 A3.8,3.8 0 1 1 2.6,-1.2 Z M1.5,1.6 L5.6,5.6",
    cross: "M0,-6 C0.9,-6 1,-5 1,-4 V-1 L6,2 V3.2 L1,1.6 V4.2 L2.6,5.4 V6 L0,5.3 L-2.6,6 V5.4 L-1,4.2 V1.6 L-6,3.2 V2 " +
      "L-1,-1 V-4 C-1,-5 -0.9,-6 0,-6 Z",
  };
  // Inside each kind's mark (shape): its frame, the picture fitted in.
  const SEAT_ICON_FIT = { adult: "scale(.78)", poster: "scale(1)", cross: "translate(0 1.6) scale(.62)",
    outsider_teacher: "scale(.74)" };
  const SEAT_ROOM = 4;  // px the paragraph apart keeps from a seat's mark at the table.
  const PARAGRAPH_LINES = 5;  // The paragraph's lines seen at the least, where there is room.
  // The paragraph's lines tried, in order: all of it (0), then fewer; under PARAGRAPH_LINES only failing those.
  const PARAGRAPH_STEPS = [0, 8, PARAGRAPH_LINES, 4, 3, 2];
  const DRAW_FOR = 1800;  // ms to draw the rim; the river follows.
  const RIPPLE_FOR = 1600;  // ms of the ring a seat sends out when its voice lights.
  const FADE_FOR = 300;  // ms a card takes to go, at the end of its BUBBLE_FOR.
  // The round table (the picture only): round the basin's middle, flat at
  // the height of the ground there, in map units.
  const TABLE_RX = 150, TABLE_RY = 110, TABLE_LIFT = 7, SEAT_OUT = 48;
  const TABLE_THICK = 9;  // The top's thickness: its side shows in front (直し29-2).
  const CAMERA_FOR = 1100, FLY_FOR = 1100, FLY_GAP = 160, BACK_FOR = 700;
  const CLOSEST = 3.5;  // The nearest zoom shows this part of the whole across.
  const ZOOM_STEP = 1.4;
  const POINT_R = 7.5;  // A point's radius at scale 1 (see shape()).
  const MIN_POINT_PX = 3;  // A point is never smaller than this on screen.
  const TOKEN = 1.3;  // A seat at the table, larger than its point.
  // On a narrow map a seat's label at the table is cut here, with 「…」 (its
  // card below has the whole title).
  const NARROW = 560, LABEL_CHARS = 8;
  // A split's heading goes on the table only on a map this wide or wider (CSS
  // px); on a narrower one it is under the map only, over its cards.
  const TAG_ON_MAP = 600;
  const CHAIR_R = 13, MIN_CHAIR_PX = 13;  // An empty chair: never under 26 px across to see.
  const HIT_PX = 22;  // An empty chair takes a press over a square 44 px across or more.
  const CHAIR_GAP = HIT_PX + 6;  // CSS px between an empty chair and its label, clear of that square.
  const DRAG_FROM = 5;  // px moved before a press becomes a drag.
  // Words drawn on the picture, in CSS px (they keep their size as it zooms).
  const TEXT_PX = { place: 11, school: 12, shelf: 11 };
  // The school (直し25-1). Its 3D picture: at the whole map a share of the
  // drawing's width (about 86px on a PC's full screen, the size 19d drew it for),
  // nearer in as the ground grows, but never under SCHOOL_MIN_PX nor over
  // SCHOOL_MAX_PX on screen. Its name never over SCHOOL_TEXT_MAX_PX, and the
  // line mark (with no picture) never over SCHOOL_MARK_MAX_PX across.
  const SCHOOL_SHARE = 0.072, SCHOOL_MIN_PX = 56, SCHOOL_MAX_PX = 130;
  const SCHOOL_TEXT_MAX_PX = 24, SCHOOL_MARK_MAX_PX = 64;
  const WORD_PAD = 2;  // CSS px kept clear round a word drawn on the map.
  const SLIDE_MOST = 40;  // CSS px the school's name may slide off a seat's point.
  // Where a seat's 「？」 may go, by its point (x, y, which way the text runs
  // from there), in the order tried: upper right first.
  const ASK_CORNERS = [[9, -6, "start"], [-9, -6, "end"], [9, 16, "start"], [-9, 16, "end"]];

  let map = null;  // The drawing from /api/setup.
  let app = null;  // What app.js lends: state, cardEntry, renderSeats, shownQuotes.
  let svg, overlay, frame, card;
  let view = null;  // How the map's (x, y) reach the drawing (flatView, reliefView).
  let vb = null;  // The part of the drawing on screen.
  let splitLayer, tableLayer, schoolGroup = null;
  const points = {};  // Seat ID -> { node, seat, at() }.
  let shelves = [];  // The picture's shelves: { shelf, rect, name, seats }.
  let tokens = [];  // Seats and empty chairs at the table: { node, at, scale }.
  let timers = [], flights = [];
  let sticky = null;  // The seat whose label stays (the last to light up).
  let drawn = false, wantShow = false, pending = null;
  let camera = null, roundNo = 0, returnFocus = null;
  let tableTop = null;  // The round table's top, a ring of spots of the drawing, while it is open.
  let roundSeats = [];  // The seats this round lights, in order.
  let soon = null;
  let hovered = null;  // The seat under the mouse (the nearest of the marks it is over).
  let opened = null;  // At the table, the seat whose card was left out and is shown, pressed.
  let choices = null;  // The card of choices open at the table: { seatId, node, card }.
  let pressedOnce = false;  // A card was pressed: the line that says so goes, for good.
  let tableRoundNo = 0;  // The round the table is for.
  let band = null;  // コーチ and オブザーバー of a round (直し29-1): { round, cards }.
  let tableAt = null;  // The table open: { center, angles, split }, for the band's seats.

  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);
  const wait = (ms) => new Promise((done) => timers.push(setTimeout(done, ms)));

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

  // --- geometry (the same middle as seat_map.py's) ---

  function centroid(ring) {
    let area = 0, cx = 0, cy = 0;
    ring.forEach(([x1, y1], i) => {
      const [x2, y2] = ring[(i + 1) % ring.length];
      const cross = x1 * y2 - x2 * y1;
      area += cross; cx += (x1 + x2) * cross; cy += (y1 + y2) * cross;
    });
    return [cx / (3 * area), cy / (3 * area)];
  }

  // A line with a point every `every` map units, so that on the picture it
  // follows the ground between its corners.
  function dense(line, closed, every = 6) {
    const out = [];
    const last = closed ? line.length : line.length - 1;
    for (let k = 0; k < last; k++) {
      const [x0, y0] = line[k], [x1, y1] = line[(k + 1) % line.length];
      const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / every));
      for (let t = 0; t < n; t++) out.push([x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n]);
    }
    if (!closed) out.push(line[line.length - 1]);
    return out;
  }

  // The flat map: the drawing is the map's own viewBox.
  function flatView() {
    const [, , width, height] = map.viewbox;
    return { relief: false, W: width, H: height, S: 1, proj: (x, y) => [x, y] };
  }

  // The picture: map (x, y, height) -> its pixel, through the projection
  // tools/render_relief.py wrote. The ground's height comes from the coarse
  // grid, read between its four nearest values.
  function reliefView(relief) {
    const [W, H] = relief.res;
    const { rows, step, px, py, z } = relief;
    const heightAt = (x, y) => {
      const fx = Math.min(Math.max(x / step, 0), rows[0].length - 1.001);
      const fy = Math.min(Math.max(y / step, 0), rows.length - 1.001);
      const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j;
      return rows[j][i] * (1 - u) * (1 - v) + rows[j][i + 1] * u * (1 - v)
        + rows[j + 1][i] * (1 - u) * v + rows[j + 1][i + 1] * u * v;
    };
    const zAt = (x, y) => (heightAt(x, y) - z.base_m) / z.m_per_unit * z.exag;
    // lift: above the ground; level: a fixed height instead of the ground's.
    const proj = (x, y, lift = 0, level = null) => {
      const h = (level === null ? zAt(x, y) : level) + lift;
      return [px[0] * x + px[1] * y + px[2] * h + px[3], py[0] * x + py[1] * y + py[2] * h + py[3]];
    };
    return { relief: true, W, H, S: Math.hypot(px[0], px[1]), proj, zAt };
  }

  // --- drawing ---

  // The picture is loaded first; when it fails, the flat map is drawn.
  function init(drawing, seats, lent) {
    map = drawing;
    app = lent;
    svg = $("map-svg");
    overlay = $("map-overlay");
    frame = $("map-frame");
    card = $("map-card");
    controls();
    if (!map.relief) return build(seats, false);
    const picture = new Image();
    picture.onload = () => build(seats, true);
    picture.onerror = () => build(seats, false);
    picture.src = map.relief.image;
  }

  function build(seats, withRelief) {
    try {
      draw(seats, withRelief);
    } catch (error) {
      if (withRelief) return build(seats, false);
      $("map").hidden = true;  // The seat list alone, as before.
      return;
    }
    if (wantShow) show();
    if (pending) {
      const result = pending;
      pending = null;
      round(result);
    }
  }

  function draw(seats, withRelief) {
    svg.replaceChildren();
    overlay.replaceChildren();
    for (const id of Object.keys(points)) delete points[id];
    shelves = [];
    tokens = [];
    schoolGroup = null;
    view = withRelief ? reliefView(map.relief) : flatView();
    vb = { x: 0, y: 0, w: view.W, h: view.H };
    svg.setAttribute("viewBox", `0 0 ${view.W} ${view.H}`);
    frame.classList.toggle("relief", view.relief);
    $("map").style.setProperty("--ratio", String(view.W / view.H));
    frame.style.aspectRatio = `${view.W} / ${view.H}`;
    const rc = rough.svg(svg);
    const layer = (className) => svg.appendChild(svgEl("g", { class: className }));
    const P = view.proj, S = view.S;
    // Colours come from style.css (a CSS rule beats rough's attributes). No
    // fill option: rough would hatch the inside.
    const ink = { stroke: "#000", seed: 7 };
    drawGlows();

    if (view.relief) {
      const image = layer("relief-image");
      image.append(svgEl("image", { href: map.relief.image, width: view.W, height: view.H }));
    }
    const fill = layer("basin-fill");
    const rimLine = view.relief ? dense(map.boundary, true).map(([x, y]) => P(x, y, 1)) : map.boundary;
    fill.append(svgEl("polygon", { points: rimLine.map((p) => p.join(",")).join(" ") }));

    const river = layer("river draw-later");
    for (const line of map.river) {
      const shown = view.relief ? dense(line, false).map(([x, y]) => P(x, y, 0.5)) : line;
      river.append(rc.linearPath(shown, { ...ink, strokeWidth: 3 * S, roughness: 0.9, bowing: 0.6 }));
    }
    const rim = layer("rim draw-first");
    rim.append(rc.polygon(rimLine, { ...ink, strokeWidth: 2.2 * S, roughness: 1.3, bowing: 0.8 }));

    const mapShelves = map.shelves || [];

    // Each kind's shelf: its name, faint, the same words as the seat list's
    // heading for that kind. On the picture, the shelves sit in its corners.
    const shelfBoxes = layer("shelf-boxes");
    const shelfNames = layer("shelf-names");
    for (const shelf of mapShelves) {
      const words = app.state.kinds[shelf.kind];
      if (!words) continue;
      const text = svgEl("text", { x: shelf.label[0], y: shelf.label[1] });
      text.textContent = words;
      shelfNames.append(text);
      if (!view.relief) continue;
      const rect = svgEl("rect", { rx: 6 * S });
      shelfBoxes.append(rect);
      const onIt = seats.filter((s) => s.outer && s.kind === shelf.kind && s.x !== undefined);
      shelves.push({ shelf, rect, name: text, seats: onIt.map((s) => s.seat_id) });
    }

    if (map.crossing) {
      const line = layer("crossing");
      const [from, to] = [map.crossing.from, map.crossing.to].map(([x, y]) => P(x, y, 1));
      line.append(rc.line(...from, ...to, { ...ink, strokeWidth: 2 * S, roughness: 1.1 }));
      line.append(svgEl("circle", { cx: from[0], cy: from[1], r: 5 * S }));
    }

    splitLayer = layer("split-lines");
    // The school's picture, when it comes, under the points: no seat is hidden under it.
    const pictureLayer = layer("school-picture");
    const seatLayer = layer("points");
    for (const seat of seats) {
      if (seat.x === undefined) continue;
      const node = drawPoint(seat);
      const spot = !view.relief ? [seat.x, seat.y] : seat.outer ? null : P(seat.x, seat.y, 1.5);
      points[seat.seat_id] = { node, seat, at: spot ? () => spot : () => shelfSpot(seat.seat_id) };
      seatLayer.append(node);
    }
    // Over the points, outlined, so a point never hides a place name.
    const names = layer("place-names");
    for (const place of map.places) {
      const [x, y] = P(place.x, place.y, 2);
      const text = svgEl("text", { x, y, "text-anchor": "middle", "data-px": TEXT_PX.place });
      text.textContent = place.name;
      names.append(text);
    }
    for (const text of shelfNames.children) text.dataset.px = TEXT_PX.shelf;
    // Over the points so its label reads; it takes no presses (not a seat).
    if (map.school) drawSchool(layer("school"), map.school, pictureLayer);
    tableLayer = layer("table");
    drawAround();

    $("map-source").textContent = map.source;
    $("map-dem").textContent = view.relief ? map.relief.source : "";
    $("map-dem").hidden = !view.relief;
    $("map").hidden = false;
    watchSize();
    setView(vb);
    refresh();
  }

  // --- which way is north (直し25-3) ---

  // Which way north, east, south and west go on the drawing, as unit steps
  // on the screen, worked out from the map's own projection at its middle
  // (the map's y grows southward), so it holds for either map and for any
  // way the picture was drawn: on both, north is up (直し31-4).
  function compassWays() {
    const [x, y] = centroid(map.boundary);
    const level = view.relief ? view.zAt(x, y) : null;
    const [x0, y0] = view.proj(x, y, 0, level);
    const unit = ([x1, y1]) => {
      const dx = x1 - x0, dy = y1 - y0, n = Math.hypot(dx, dy) || 1;
      return [dx / n, dy / n];
    };
    const north = unit(view.proj(x, y - 100, 0, level)), east = unit(view.proj(x + 100, y, 0, level));
    return { north, east, south: [-north[0], -north[1]], west: [-east[0], -east[1]] };
  }

  // A small arrow with 「北」 in a corner, and by each edge what lies that way
  // (texts/map_around.tsv), on the overlay: they take no presses. They are
  // put by placeAround, off the shelves, the words and the points.
  function drawAround() {
    const words = app.state.texts && app.state.texts.map_around;
    if (!words) return;
    const ways = compassWays();
    const [nx, ny] = ways.north;
    const compass = div("map-compass");
    compass.setAttribute("role", "img");
    compass.setAttribute("aria-label", words.north.word);
    const dial = svgEl("svg", { viewBox: "-20 -20 40 40", "aria-hidden": "true", focusable: "false" });
    dial.append(svgEl("circle", { class: "dial", r: 15 }));
    const needle = dial.appendChild(svgEl("g", { transform: `rotate(${(Math.atan2(ny, nx) * 180 / Math.PI + 90).toFixed(1)})` }));
    needle.append(svgEl("polygon", { class: "north", points: "0,-13 4.2,0 -4.2,0" }),
      svgEl("polygon", { class: "tail", points: "0,13 4.2,0 -4.2,0" }));
    const letter = div("letter", words.north.word);
    letter.setAttribute("aria-hidden", "true");
    letter.style.left = `calc(50% + ${(nx * 20).toFixed(1)}px)`;
    letter.style.top = `calc(50% + ${(ny * 20).toFixed(1)}px)`;
    compass.append(dial, letter);
    overlay.append(compass);
    for (const way of ["north", "east", "south", "west"]) {
      const [ux, uy] = ways[way];
      const note = div("map-around", words[way].place);
      note.dataset.way = way;
      note.setAttribute("aria-label", `${words[way].word}　${words[way].place}`);
      note.style.setProperty("--turn", `${(Math.atan2(uy, ux) + Math.PI / 4).toFixed(3)}rad`);
      overlay.append(note);
    }
  }

  // The arrow first, then the four names, each kept off the shelves, the
  // words drawn on the map, the points and what was put before it.
  function placeAround() {
    const compass = overlay.querySelector(".map-compass");
    if (!compass) return;
    const frameBox = overlay.getBoundingClientRect();
    const frameWH = { w: frameBox.width, h: frameBox.height };
    const avoid = [...fixedBoxes(frameBox, false),
      ...[...svg.querySelectorAll(".points .pt .shape")].map((node) => boxIn(node, frameBox))];
    const ways = compassWays();
    const put = (node, [left, top]) => {
      node.style.left = `${left}px`;
      node.style.top = `${top}px`;
      avoid.push(boxIn(node, frameBox));
    };
    put(compass, compassSpot(frameWH, { w: compass.offsetWidth, h: compass.offsetHeight }, avoid));
    for (const note of overlay.querySelectorAll(".map-around")) {
      put(note, aroundSpot(frameWH, { w: note.offsetWidth, h: note.offsetHeight }, ways[note.dataset.way], avoid));
    }
    // The line that says a lamp card can be pressed: by the lower edge, off
    // the arrow, the edge names, the table and its seats (the dimmed map's
    // points under it do not count).
    const clear = [...fixedBoxes(frameBox, false, false),
      ...[...overlay.querySelectorAll(".map-compass, .map-around")].map((node) => boxIn(node, frameBox))];
    // With no room along the edge itself, a line higher up, then another.
    for (const hint of overlay.querySelectorAll(".map-hint")) {
      const box = { w: hint.offsetWidth, h: hint.offsetHeight };
      let spot = null;
      for (let up = 0; up < 3 && !(spot && coverOf(spot, box, clear) === 0); up++) {
        const found = aroundSpot({ w: frameWH.w, h: frameWH.h - up * (box.h + 6) }, box, [0, 1], clear);
        if (!spot || coverOf(found, box, clear) < coverOf(spot, box, clear)) spot = found;
      }
      put(hint, spot);
    }
  }

  // How much of a box [left, top] { w, h } the boxes [left, top, w, h] cover.
  function coverOf([left, top], { w, h }, others) {
    let sum = 0;
    for (const [x, y, ow, oh] of others) {
      const dx = Math.min(left + w, x + ow) - Math.max(left, x), dy = Math.min(top + h, y + oh) - Math.max(top, y);
      if (dx > 0 && dy > 0) sum += dx * dy;
    }
    return sum;
  }

  // Where a way's name goes in a frame { w, h }: by the edge its way [ux, uy]
  // leaves the frame's middle through, where that way meets it, then slid
  // along that edge to the first spot that covers nothing in avoid (with
  // none free, the one that covers least). Inside the frame by margin.
  function aroundSpot(frame, box, [ux, uy], avoid, margin = 8) {
    const { w: W, h: H } = frame;
    const across = Math.abs(uy) * W >= Math.abs(ux) * H;  // The top or the bottom edge.
    const clampX = (left) => Math.min(Math.max(left, margin), W - box.w - margin);
    const clampY = (top) => Math.min(Math.max(top, margin), H - box.h - margin);
    const base = across
      ? [clampX(W / 2 + ux * (H / 2) / Math.abs(uy) - box.w / 2), uy > 0 ? H - box.h - margin : margin]
      : [ux > 0 ? W - box.w - margin : margin, clampY(H / 2 + uy * (W / 2) / Math.abs(ux) - box.h / 2)];
    let best = base, least = Infinity;
    for (let step = 0; step <= (across ? W : H) / 2; step += 12) {
      for (const sign of step ? [1, -1] : [1]) {
        const spot = across ? [clampX(base[0] + sign * step), base[1]] : [base[0], clampY(base[1] + sign * step)];
        const cover = coverOf(spot, box, avoid);
        if (cover === 0) return spot;
        if (cover < least) [best, least] = [spot, cover];
      }
    }
    return best;
  }

  // Where the arrow goes: the first corner (bottom right, bottom left, top
  // right, top left), slid along either of its edges, that covers nothing in
  // avoid; with none free, the spot that covers least.
  function compassSpot(frame, box, avoid, margin = 8) {
    const { w: W, h: H } = frame;
    const right = W - box.w - margin, bottom = H - box.h - margin;
    const corners = [[right, bottom, -1, -1], [margin, bottom, 1, -1], [right, margin, -1, 1], [margin, margin, 1, 1]];
    let best = [right, bottom], least = Infinity;
    for (const [x, y, sx, sy] of corners) {
      for (let step = 0; step <= Math.min(W, H) / 2; step += 12) {
        for (const spot of step ? [[x + sx * step, y], [x, y + sy * step]] : [[x, y]]) {
          const cover = coverOf(spot, box, avoid);
          if (cover === 0) return spot;
          if (cover < least) [best, least] = [spot, cover];
        }
      }
    }
    return best;
  }

  // The soft lights the drawing is lit with: round glows that fade to
  // nothing (their colours are style.css's, by name).
  function drawGlows() {
    const defs = svg.appendChild(svgEl("defs"));
    for (const [id, stops] of [["lamp-glow", ["glow-in", "glow-out"]], ["paper-glow", ["paper-in", "paper-out"]],
      ["table-light", ["top-in", "top-mid", "top-out"]]]) {
      const glow = svgEl("radialGradient", { id });
      stops.forEach((className, k) => glow.append(svgEl("stop", { class: className, offset: k / (stops.length - 1) })));
      defs.append(glow);
    }
  }

  // The school as its building is, seen from above, north up: the wing that
  // rings its north half, the wing across its diameter, the round roof in the
  // middle, and the glass at the roof's top lit like a lamp (it does not
  // move). The southern wing, the corridors, the gate and the grounds are
  // left out: a mark this small would blur them.
  function drawSchool(group, school, pictureLayer) {
    const [x, y] = view.proj(school.x, school.y, 1);
    schoolGroup = { node: group, x, y, picture: null };
    group.setAttribute("role", "img");
    group.setAttribute("aria-label", school.label);
    group.append(
      svgEl("path", { class: "wing", d: "M -13 0 A 13 13 0 0 1 13 0 L 8.3 0 A 8.3 8.3 0 0 0 -8.3 0 Z" }),
      svgEl("rect", { class: "wing", x: -13.5, y: 0, width: 27, height: 4.8 }),
      svgEl("path", { class: "dome", d: "M -4.8 0 A 4.8 4.8 0 0 1 4.8 0 Z" }),
      svgEl("circle", { class: "glass-glow", r: 5.5 }),
      svgEl("circle", { class: "glass", r: 1.6 }));
    const label = svgEl("text", { x: 0, y: 25, "text-anchor": "middle" });
    label.textContent = school.label;
    group.append(label);
    const picture = map.school_picture && map.school_picture[view.relief ? "relief" : "flat"];
    if (picture) loadSchoolPicture(picture, pictureLayer);
  }

  // The school as a 3D picture (from outside the repo, school_picture.py),
  // in place of its line mark once it has loaded; until then, or if it never
  // does, the line mark stays. Like the mark it takes no presses.
  function loadSchoolPicture(picture, pictureLayer) {
    const owner = schoolGroup;
    const image = new Image();
    image.onload = () => {
      if (schoolGroup !== owner) return;  // The map was drawn again meanwhile.
      const node = svgEl("image", { href: picture.image, width: picture.width, height: picture.height });
      pictureLayer.append(node);
      owner.picture = { ...picture, node };
      owner.node.classList.add("pictured");
      rescale();
      relayout();
    };
    image.src = picture.image;
  }

  // The school's mark or picture at the zoom as it is (perPx: the drawing's
  // units to a CSS pixel), and its name just under it, at most so large.
  function placeSchool(perPx) {
    const { node, x, y, picture } = schoolGroup;
    const grown = view.relief ? Math.max(view.S, TEXT_PX.school * perPx / 20) : 1;
    const k = Math.min(grown, SCHOOL_MARK_MAX_PX * perPx / 27);
    node.setAttribute("transform", `translate(${x} ${y}) scale(${k})`);
    let bottom = 4.8 * k / perPx;  // How far under the point the mark ends, on screen.
    if (picture) {
      const width = Math.min(Math.max(SCHOOL_SHARE * view.W, SCHOOL_MIN_PX * perPx), SCHOOL_MAX_PX * perPx);
      const s = width / picture.width;
      picture.node.setAttribute("transform",
        `translate(${x - picture.point[0] * s} ${y - picture.point[1] * s}) scale(${s})`);
      bottom = (picture.height - picture.point[1]) * s / perPx + 2;
    }
    const label = node.querySelector("text");
    const fontPx = Math.min(20 * grown / perPx, SCHOOL_TEXT_MAX_PX);
    label.style.fontSize = `${fontPx * perPx / k}px`;
    label.setAttribute("y", (bottom + fontPx * 1.01) * perPx / k);
  }

  // Circle, square, triangle, diamond: the kind shows in the shape as well
  // as the colour (never the colour alone).
  function shape(kind) {
    if (kind === "poster") return svgEl("rect", { class: "shape", x: -7, y: -7, width: 14, height: 14 });
    if (kind === "cross") return svgEl("polygon", { class: "shape", points: "0,-9 8.5,6.5 -8.5,6.5" });
    if (kind === "outsider_teacher") return svgEl("polygon", { class: "shape", points: "0,-9.5 9.5,0 0,9.5 -9.5,0" });
    return svgEl("circle", { class: "shape", r: POINT_R });
  }

  function drawPoint(seat) {
    const point = svgEl("g", { class: `pt kind-${seat.kind}`, tabindex: 0, role: "button", "data-seat": seat.seat_id });
    point.append(svgEl("circle", { class: "halo", r: 20 }), shape(seat.kind),
      svgEl("circle", { class: "met-mark", cx: 8, cy: -8, r: 3.5 }));
    const ask = svgEl("text", { class: "ask-mark", x: 9, y: -6 });
    ask.textContent = "？";
    point.append(ask);
    // The mouse is followed over the whole layer (hoverAt); the keyboard here.
    point.addEventListener("focus", () => showTip(seat.seat_id));
    point.addEventListener("blur", restoreTip);
    // A mouse's press goes to the seat whose name it shows; a touch, as before.
    pressable(point, (event) => {
      if (svg.classList.contains("dim")) return;  // Not while the table is open (直し27-4).
      const id = event && event.pointerType === "mouse" && hovered ? hovered : seat.seat_id;
      press(id, points[id].node);
    });
    return point;
  }

  // Which seat the mouse is on: of the points it is over, the one whose mark
  // is nearest (where seats are close their soft rings overlap, and the ring
  // on top is not always the seat under the pointer). Its name card shows
  // while the mouse is there and goes when it leaves. A touch is left as it was.
  function hoverAt(event) {
    if (event.pointerType !== "mouse" || event.buttons) return;
    if (svg.classList.contains("dim")) return;  // The table is open: the points behind keep still (直し27-4).
    const id = nearestPoint(event.clientX, event.clientY);
    if (id === hovered) return;
    if (hovered && points[hovered]) points[hovered].node.classList.remove("hover");
    hovered = id;
    if (!id) return restoreTip();
    points[id].node.classList.add("hover");
    showTip(id);
  }

  function nearestPoint(x, y) {
    let best = null, far = Infinity;
    for (const node of document.elementsFromPoint(x, y)) {
      const point = node.closest && node.closest(".points .pt");
      if (!point || !points[point.dataset.seat]) continue;
      const r = point.querySelector(".shape").getBoundingClientRect();
      const d = Math.hypot(r.left + r.width / 2 - x, r.top + r.height / 2 - y);
      if (d < far) { best = point.dataset.seat; far = d; }
    }
    return best;
  }

  function pressable(node, action) {
    node.addEventListener("click", action);
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        action(event);
      }
    });
  }

  // --- sizes that follow the zoom: points, words on the picture, shelves ---

  // A point's scale: its size on the drawing, never under MIN_POINT_PX on screen.
  function pointScale() {
    const across = frame.clientWidth || 1;
    return Math.max(view.S, MIN_POINT_PX * (vb.w / across) / POINT_R);
  }

  // The picture's shelves, one per corner (nothing is over the corners: the
  // buttons are under the map), spaced so their points never touch at any width.
  function layoutShelves(f) {
    const margin = 14 * f;
    const corners = [[0, 0], [1, 0], [0, 1], [1, 1]];
    shelves.forEach((entry, k) => {
      const [x0, y0, x1, y1] = entry.shelf.box;
      const w = (x1 - x0) * f, h = (y1 - y0) * f;
      const [cx, cy] = corners[k % corners.length];
      const left = cx ? view.W - w - margin : margin, top = cy ? view.H - h - margin : margin;
      entry.origin = [left, top];
      entry.scale = f;
      Object.entries({ x: left, y: top, width: w, height: h }).forEach(([key, value]) => entry.rect.setAttribute(key, value));
      entry.name.setAttribute("x", left + (entry.shelf.label[0] - x0) * f);
      entry.name.setAttribute("y", top + (entry.shelf.label[1] - y0) * f);
    });
  }

  function shelfSpot(seatId) {
    const seat = points[seatId].seat;
    const entry = shelves.find((s) => s.seats.includes(seatId));
    if (!entry || !entry.origin) return [seat.x * view.S, seat.y * view.S];
    const [x0, y0] = entry.shelf.box;
    return [entry.origin[0] + (seat.x - x0) * entry.scale, entry.origin[1] + (seat.y - y0) * entry.scale];
  }

  function rescale() {
    const f = pointScale();
    const perPx = vb.w / (frame.clientWidth || 1);
    if (view.relief) layoutShelves(f);
    for (const { node, at } of Object.values(points)) {
      const [x, y] = at();
      node.setAttribute("transform", `translate(${x} ${y}) scale(${f})`);
    }
    for (const token of tokens) {
      const k = token.chair ? Math.max(f * token.scale, MIN_CHAIR_PX * perPx / CHAIR_R) : f * token.scale;
      token.node.setAttribute("transform", `translate(${token.at[0]} ${token.at[1]}) scale(${k})`);
      if (!token.chair) continue;
      // The square that takes the press: HIT_PX each way on screen, at any zoom.
      const half = Math.max(CHAIR_R, HIT_PX * perPx / k);
      const hit = token.node.querySelector(".hit");
      Object.entries({ x: -half, y: -half, width: 2 * half, height: 2 * half, rx: half * 0.28 })
        .forEach(([key, value]) => hit.setAttribute(key, value));
    }
    if (schoolGroup) placeSchool(perPx);
    if (!view.relief) return;  // The flat map keeps its words' sizes from style.css.
    for (const text of svg.querySelectorAll("text[data-px]")) {
      text.style.fontSize = `${Number(text.dataset.px) * perPx}px`;
      text.style.strokeWidth = `${2 * perPx}px`;  // A thin halo, not an outline.
    }
  }

  // --- the camera: the part of the drawing on screen ---

  function clampView(v) {
    const w = Math.min(view.W, Math.max(view.W / CLOSEST, v.w)), h = w * view.H / view.W;
    return { x: Math.min(view.W - w, Math.max(0, v.x)), y: Math.min(view.H - h, Math.max(0, v.y)), w, h };
  }

  function setView(v, settle = true) {
    vb = clampView(v);
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    frame.classList.toggle("zoomed", vb.w < view.W - 0.5);
    rescale();
    if (settle) relayout();
  }

  function stopCamera() {
    if (camera) cancelAnimationFrame(camera);
    camera = null;
    frame.classList.remove("moving");
  }

  // Moves the camera there; at once when motion is reduced.
  function moveTo(target, ms) {
    stopCamera();
    target = clampView(target);
    if (reduced() || !ms) {
      setView(target);
      return Promise.resolve();
    }
    const from = { ...vb }, start = performance.now();
    frame.classList.add("moving");
    return new Promise((done) => {
      const step = (now) => {
        const t = Math.min(1, (now - start) / ms), e = 1 - Math.pow(1 - t, 3);
        const mix = (key) => from[key] + (target[key] - from[key]) * e;
        setView({ x: mix("x"), y: mix("y"), w: mix("w"), h: mix("h") }, false);
        if (t < 1) {
          camera = requestAnimationFrame(step);
          return;
        }
        camera = null;
        frame.classList.remove("moving");
        relayout();
        done();
      };
      camera = requestAnimationFrame(step);
    });
  }

  function zoomAround(factor, x = vb.x + vb.w / 2, y = vb.y + vb.h / 2) {
    return { x: x - (x - vb.x) / factor, y: y - (y - vb.y) / factor, w: vb.w / factor, h: vb.h / factor };
  }

  function fromScreen(clientX, clientY) {
    const r = svg.getBoundingClientRect();
    return [vb.x + (clientX - r.left) / r.width * vb.w, vb.y + (clientY - r.top) / r.height * vb.h];
  }

  // Labels move once a drag or a wheel stops, not on every step.
  function settleSoon() {
    clearTimeout(soon);
    for (const node of overlay.querySelectorAll(".map-bubble")) node.remove();
    frame.classList.add("moving");
    soon = setTimeout(() => { frame.classList.remove("moving"); relayout(); }, 140);
  }

  // The buttons, the wheel, a drag and a two-finger pinch.
  function controls() {
    const words = app.state.texts.map_buttons;
    for (const [id, key] of [["map-back", "back"], ["map-zoom-in", "zoom_in"], ["map-zoom-out", "zoom_out"],
      ["map-zoom-all", "zoom_all"]]) {
      $(id).textContent = words[key].text;
      if (words[key].label !== words[key].text) $(id).setAttribute("aria-label", words[key].label);
    }
    $("map-zoom-in").addEventListener("click", () => moveTo(zoomAround(ZOOM_STEP), 300));
    $("map-zoom-out").addEventListener("click", () => moveTo(zoomAround(1 / ZOOM_STEP), 300));
    $("map-zoom-all").addEventListener("click", () => moveTo({ x: 0, y: 0, w: view.W, h: view.H }, 500));
    $("map-back").addEventListener("click", closeTable);

    svg.addEventListener("wheel", (event) => {
      if (!view) return;
      event.preventDefault();
      stopCamera();
      const [x, y] = fromScreen(event.clientX, event.clientY);
      setView(zoomAround(event.deltaY < 0 ? 1.18 : 1 / 1.18, x, y), false);
      settleSoon();
    }, { passive: false });

    const down = new Map();
    let dragged = false, pinch = null;
    svg.addEventListener("pointerdown", (event) => {
      down.set(event.pointerId, { x: event.clientX, y: event.clientY, start: [event.clientX, event.clientY] });
      dragged = false;
      pinch = null;
    });
    svg.addEventListener("pointermove", (event) => {
      const before = down.get(event.pointerId);
      if (!before || !view) return;
      const r = svg.getBoundingClientRect();
      if (!dragged && Math.hypot(event.clientX - before.start[0], event.clientY - before.start[1]) < DRAG_FROM) return;
      if (!dragged) {
        dragged = true;
        stopCamera();
        svg.setPointerCapture(event.pointerId);
        svg.classList.add("dragging");
      }
      if (down.size === 1) {
        const dx = (event.clientX - before.x) / r.width * vb.w, dy = (event.clientY - before.y) / r.height * vb.h;
        setView({ ...vb, x: vb.x - dx, y: vb.y - dy }, false);
      } else if (down.size === 2) {
        const [a, b] = [...down.values()].map((p) => (p === before ? { x: event.clientX, y: event.clientY } : p));
        const apart = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) {
          const [x, y] = fromScreen((a.x + b.x) / 2, (a.y + b.y) / 2);
          setView(zoomAround(apart / pinch, x, y), false);
        }
        pinch = apart;
      }
      before.x = event.clientX;
      before.y = event.clientY;
      settleSoon();
    });
    const up = (event) => {
      down.delete(event.pointerId);
      pinch = null;
      if (down.size) return;
      svg.classList.remove("dragging");
      // The click that follows this drag (if any) comes first; then presses count again.
      if (dragged) setTimeout(() => { dragged = false; }, 0);
    };
    svg.addEventListener("pointermove", hoverAt);
    svg.addEventListener("pointerleave", (event) => hoverAt({ pointerType: event.pointerType, buttons: 0, clientX: -1, clientY: -1 }));
    svg.addEventListener("pointerup", up);
    svg.addEventListener("pointercancel", up);
    // A drag is not a press on the point it started on.
    svg.addEventListener("click", (event) => {
      if (!dragged) return;
      dragged = false;
      event.stopPropagation();
      event.preventDefault();
    }, true);
    // A press on the map, not a drag: the choices close. Esc too, wherever
    // the keyboard is.
    svg.addEventListener("click", () => closeChoices(false));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && choices) closeChoices(true);
    });
  }

  // When the frame's width changes, the sizes and every label follow.
  function watchSize() {
    if (watchSize.on) return;
    watchSize.on = true;
    let width = frame.clientWidth;
    const changed = () => {
      if (!view || frame.clientWidth === width) return;
      width = frame.clientWidth;
      rescale();
      relayout();
    };
    if (window.ResizeObserver) new ResizeObserver(changed).observe(frame);
    window.addEventListener("resize", changed);
    // The screen's keyboard takes the lower part of the screen: the card
    // being written in stays in sight.
    if (window.visualViewport) window.visualViewport.addEventListener("resize", keepCardInSight);
    window.addEventListener("resize", keepCardInSight);
  }

  // The card of an empty chair, whole on screen when it opens and while one
  // writes in it.
  function keepCardInSight() {
    if (card && !card.hidden && card.contains(document.activeElement)) card.scrollIntoView({ block: "nearest" });
  }

  // Draws the rim, then the river, as if by hand. Called when the map is on
  // screen (a path's length needs it laid out).
  function show() {
    if (!view) { wantShow = true; return; }
    rescale();
    relayout();
    if (drawn) return;
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

  // Where a spot of the drawing is in the frame, in CSS pixels.
  function toFrame(x, y) {
    return [(x - vb.x) / vb.w * overlay.clientWidth, (y - vb.y) / vb.h * overlay.clientHeight];
  }

  function inView(x, y) {
    return x >= vb.x && x <= vb.x + vb.w && y >= vb.y && y <= vb.y + vb.h;
  }

  // Where one box ({ w, h } by its spot px, py, gap apart) goes in a frame
  // ({ w, h }), always inside it: above the spot, below it, right or left,
  // the first side that covers none of the others ([left, top, width,
  // height] in the frame); failing that, the nearest spot in the frame that
  // covers none. Returns [[left, top], area covered]: with no free spot, the
  // side that covers least. It reads nothing but what it is given.
  function chooseSpot(frame, box, others) {
    const { w, h, px, py, gap } = box;
    const clampX = (left) => Math.max(4, Math.min(left, frame.w - w - 4));
    const clampY = (top) => Math.max(4, Math.min(top, frame.h - h - 4));
    const sides = [
      [px - w / 2, py - h - gap], [px - w / 2, py + gap],
      [px + gap, py - h / 2], [px - w - gap, py - h / 2],
    ].map(([left, top]) => [clampX(left), clampY(top)]);
    const covered = ([left, top]) => others.reduce((sum, [ol, ot, ow, oh]) =>
      sum + Math.max(0, Math.min(left + w, ol + ow) - Math.max(left, ol)) *
        Math.max(0, Math.min(top + h, ot + oh) - Math.max(top, ot)), 0);
    let best = sides[0], least = Infinity;
    for (const side of sides) {
      const area = covered(side);
      if (area < least) { best = side; least = area; }
      if (!area) return [side, 0];
    }
    const away = ([left, top]) => Math.hypot(left + w / 2 - px, top + h / 2 - py);
    let free = null, far = Infinity;
    for (let top = 4; top <= frame.h - h - 4; top += 6) {
      for (let left = 4; left <= frame.w - w - 4; left += 6) {
        const spot = [left, top], d = away(spot);
        if (d < far && !covered(spot)) { free = spot; far = d; }
      }
    }
    return free ? [free, 0] : [best, least];
  }

  // Where every heading and label goes, in order, from the frame as it is
  // now and nothing before: the same width gives the same places, however
  // the window came to it. Each box keeps clear of the fixed ones (the
  // buttons, the seats and chairs at the table) and of the boxes put before
  // it. null leaves a box out: its spot is off screen; it is the heading at
  // the table on a map narrower than TAG_ON_MAP; or it is a label or heading
  // at the table with no free spot.
  function planLabels(frame, items, fixed) {
    const taken = [...fixed];
    return items.map((item) => {
      if (!item.inView || (item.heading && item.atTable && frame.w < TAG_ON_MAP)) return null;
      const [spot, least] = chooseSpot(frame, item, taken);
      if (least && item.atTable) return null;
      taken.push([spot[0], spot[1], item.w, item.h]);
      return spot;
    });
  }

  // A box's size as it will be put. It is measured from the frame's corner,
  // not where it was (a box left further right wraps narrower and grows
  // taller), and its width is then fixed, so it keeps that size wherever it
  // goes.
  function measure(node, frameBox) {
    node.classList.remove("unplaced");
    node.style.left = "0px";
    node.style.top = "0px";
    node.style.width = "";
    // A voice's card: its lines about twenty characters (style.css), never
    // more than half the frame across.
    const voice = node.classList.contains("map-bubble") || node.classList.contains("table-bubble");
    const most = voice ? frameBox.width * 0.5 : Math.min(frameBox.width * 0.7, 18 * 16);
    node.style.maxWidth = `${Math.floor(Math.min(most, frameBox.width - 8))}px`;
    node.style.width = `${Math.ceil(node.getBoundingClientRect().width)}px`;
    const { width, height } = node.getBoundingClientRect();
    return { w: width, h: height };
  }

  function boxIn(node, frameBox) {
    const r = node.getBoundingClientRect();
    return [r.left - frameBox.left, r.top - frameBox.top, r.width, r.height];
  }

  // Whether a spot is inside a closed ring of spots.
  function within(ring, [x, y]) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // The words drawn on the map ([left, top, width, height] in a frame
  // { w, h }) that a box keeps off, each with a little room round it: those
  // in the frame and not wholly under the round table's top, which hides
  // them (cover: the top's ring in the frame, or null). It reads nothing but
  // what it is given.
  function seenWords(frame, words, cover) {
    const under = ([left, top, w, h]) => cover &&
      [[left, top], [left + w, top], [left, top + h], [left + w, top + h]].every((p) => within(cover, p));
    return words
      .filter((word) => word[2] && word[0] < frame.w && word[1] < frame.h && word[0] + word[2] > 0 &&
        word[1] + word[3] > 0 && !under(word))
      .map(([left, top, w, h]) => [left - WORD_PAD, top - WORD_PAD, w + 2 * WORD_PAD, h + 2 * WORD_PAD]);
  }

  // What a label, bubble or heading never covers (the buttons are under the
  // map, not over it): the seats this round lights, on the map (all of them
  // from the start, so a seat lit later is not under an earlier bubble), or,
  // while the table is open, its seats and empty chairs with the square that
  // takes a press; the shelves with their rows of points; and what is drawn
  // on the map in words: the place names, the shelves' names, the school's
  // name and its mark.
  function fixedBoxes(frameBox, withAround = true, withWords = true, withBacks = true) {
    // The chairs' backs and the table's leg and foot too (直し29-2): cards and names keep off them.
    // コーチ and オブザーバー's seats with their light round them (直し31-4: at
    // 768 a card came over the coach's flame's foot).
    const nodes = [...tableLayer.querySelectorAll(".token .shape, .token.ai-seat .halo, .chair circle, .chair .hit" +
      (withBacks ? ", .token .chair-back, .chair .back, .table-foot .leg, .table-foot .base" : ""))];
    // A seat of the round at the size it has once lit (not met yet, it is drawn smaller).
    const reach = 9.5 * pointScale() * frameBox.width / vb.w;
    const seats = tableTop ? [] : roundSeats.map((id) => toFrame(...spotOf(id)))
      .map(([px, py]) => [px - reach, py - reach, 2 * reach, 2 * reach]);
    const words = [...svg.querySelectorAll(".place-names text, .shelf-names text, .school text, .school > :not(text), " +
      ".school-picture image")].map((node) => boxIn(node, frameBox));
    const cover = tableTop && tableTop.map(([x, y]) => toFrame(x, y));
    const shelfBoxes = shelfAreas().map(([x0, y0, x1, y1]) => {
      const [left, top] = toFrame(x0, y0), [right, bottom] = toFrame(x1, y1);
      return [left, top, right - left, bottom - top];
    });
    // The arrow and the four ways' names (直し25-3), once they are put.
    const around = withAround ? [...overlay.querySelectorAll(".map-compass, .map-around, .map-hint")].map((node) => boxIn(node, frameBox)) : [];
    return [...nodes.map((node) => boxIn(node, frameBox)), ...seats, ...(cover ? topStrips(cover) : []),
      ...shelfBoxes, ...(withWords ? seenWords({ w: frameBox.width, h: frameBox.height }, words, cover) : []), ...around];
  }

  // The shelves, each a box of the drawing [x0, y0, x1, y1] with its name and
  // its row of points: on the picture where layoutShelves put it (a corner),
  // on the flat map where the map has it.
  function shelfAreas() {
    if (view.relief) {
      return shelves.filter((entry) => entry.origin).map(({ shelf: { box: [x0, y0, x1, y1] }, origin: [left, top], scale }) =>
        [left, top, left + (x1 - x0) * scale, top + (y1 - y0) * scale]);
    }
    return (map.shelves || []).filter((shelf) => app.state.kinds[shelf.kind]).map((shelf) => shelf.box);
  }

  // The round table's top (a ring of spots in a frame) as a few boxes, band
  // by band, so a label by a chair stays off the top and its rim of light.
  // It reads nothing but what it is given.
  function topStrips(ring, bands = 8) {
    const ys = ring.map((p) => p[1]), top = Math.min(...ys), step = (Math.max(...ys) - top) / bands;
    const strips = [];
    for (let k = 0; k < bands; k++) {
      const y0 = top + k * step, y1 = y0 + step;
      const xs = ring.filter(([, y]) => y >= y0 - step / 2 && y <= y1 + step / 2).map((p) => p[0]);
      if (xs.length) strips.push([Math.min(...xs), y0, Math.max(...xs) - Math.min(...xs), step]);
    }
    return strips;
  }

  // Where a bubble (or a seat's label) goes, a box { w, h, px, py, gap } in a
  // frame { w, h }: clear of the fixed boxes, the headings and labels (kept)
  // and the bubbles still up, by its spot or, with no side free, at the
  // nearest free spot (chooseSpot). When that spot is further than near
  // (BUBBLE_NEAR, or BUBBLE_NEAR_PART of the frame's width) from its own spot, the earlier bubbles in the way go instead, if that
  // frees a spot near it (they are short-lived); failing that, the free spot
  // further away; with none free, the one that covers least. Returns
  // [[left, top], area covered, whether the bubbles in the way go]. It reads
  // nothing but what it is given.
  function planBubble(frame, box, fixed, kept, bubbles) {
    const away = ([left, top]) => Math.hypot(Math.max(left - box.px, 0, box.px - left - box.w),
      Math.max(top - box.py, 0, box.py - top - box.h));
    const near = Math.max(BUBBLE_NEAR, frame.w * BUBBLE_NEAR_PART);
    const [best, least] = chooseSpot(frame, box, [...fixed, ...kept, ...bubbles]);
    if (!bubbles.length || (!least && away(best) <= near)) return [best, least, false];
    const [spot, rest] = chooseSpot(frame, box, [...fixed, ...kept]);
    if (!rest && (least || away(spot) <= near)) return [spot, 0, true];
    return [best, least, false];
  }

  function boxesMeet(a, b) {
    return a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
  }

  // Whether the line from a to b passes through a box [left, top, width,
  // height]. It reads nothing but what it is given.
  function crosses([ax, ay], [bx, by], [left, top, w, h]) {
    let t0 = 0, t1 = 1;
    const dx = bx - ax, dy = by - ay;
    for (const [p, q] of [[-dx, ax - left], [dx, left + w - ax], [-dy, ay - top], [dy, top + h - ay]]) {
      if (p === 0) {
        if (q < 0) return false;
        continue;
      }
      const t = q / p;
      if (p < 0) {
        if (t > t1) return false;
        t0 = Math.max(t0, t);
      } else {
        if (t < t0) return false;
        t1 = Math.min(t1, t);
      }
    }
    return t0 < t1;
  }

  // A card's tail ([left, top, width, height] in the frame): from r short of
  // its seat's spot (px, py) to the side of the card that faces it, TAIL_CORNER
  // from its corners where the side is long enough. [[from], [to]], or null
  // when the card is that close. It reads nothing but what it is given.
  function tailEnds([left, top, w, h], px, py, r) {
    const along = (v, lo, hi) => (hi - lo > 2 * TAIL_CORNER ? Math.min(Math.max(v, lo + TAIL_CORNER), hi - TAIL_CORNER) : (lo + hi) / 2);
    const outX = Math.max(left - px, 0, px - left - w), outY = Math.max(top - py, 0, py - top - h);
    if (!outX && !outY) return null;
    const [qx, qy] = outX >= outY
      ? [px < left ? left : left + w, along(py, top, top + h)]
      : [along(px, left, left + w), py < top ? top : top + h];
    const length = Math.hypot(qx - px, qy - py);
    if (length <= r + 4) return null;
    return [[px + (qx - px) * r / length, py + (qy - py) * r / length], [qx, qy]];
  }

  // Where each card at the table goes (直し26-1), in the order given (the
  // round's seat_order), each a box { w, h, px, py, gap, r, inView } in a
  // frame { w, h }: inside the frame, within reach of its seat, covering none
  // of the fixed boxes nor a card put before it, no tail crossing a card, and
  // its own tail crossing none of block (the seats, the chairs, the table's
  // top). null leaves a card out: off screen, or no such spot. The same frame
  // gives the same places. It reads nothing but what it is given.
  function planTableBubbles(frame, items, fixed, block, reach) {
    const taken = [...fixed], cards = [], tails = [];
    return items.map((item) => {
      if (!item.inView) return null;
      const found = tableBubbleSpot(frame, item, taken, [...block, ...cards], tails, reach);
      if (!found) return null;
      const [spot, tail] = found;
      const box = [spot[0], spot[1], item.w, item.h];
      taken.push(box);
      cards.push(box);
      if (tail) tails.push(tail);
      return spot;
    });
  }

  // One card's spot: first the eight round its seat (above first), then the
  // nearest free one within reach. [spot, its tail] or null.
  function tableBubbleSpot(frame, item, taken, block, tails, reach) {
    const { w, h, px, py, gap, r } = item, m = 4;
    if (w > frame.w - 2 * m || h > frame.h - 2 * m) return null;
    const clamp = ([left, top]) => [Math.max(m, Math.min(left, frame.w - w - m)), Math.max(m, Math.min(top, frame.h - h - m))];
    const away = ([left, top]) => Math.hypot(Math.max(left - px, 0, px - left - w), Math.max(top - py, 0, py - top - h));
    const d = gap * 0.7;
    const round = [[px - w / 2, py - h - gap], [px - w / 2, py + gap], [px + gap, py - h / 2], [px - w - gap, py - h / 2],
      [px + d, py - h - d], [px - w - d, py - h - d], [px + d, py + d], [px - w - d, py + d]].map(clamp);
    const grid = [];
    for (let top = py - reach - h; top <= py + reach; top += TABLE_STEP) {
      for (let left = px - reach - w; left <= px + reach; left += TABLE_STEP) {
        const spot = clamp([left, top]);
        grid.push([away(spot), spot]);
      }
    }
    grid.sort((a, b) => a[0] - b[0]);
    for (const spot of [...round, ...grid.map(([, spot]) => spot)]) {
      const far = away(spot);
      if (far > reach || far < gap * 0.9) continue;  // Near its seat, its tail long enough to see.
      const box = [spot[0], spot[1], w, h];
      if (taken.some((other) => boxesMeet(box, other))) continue;
      if (tails.some(([a, b]) => crosses(a, b, box))) continue;
      const tail = tailEnds(box, px, py, r);
      if (tail && block.some((other) => crosses(tail[0], tail[1], other))) continue;
      return [spot, tail];
    }
    return null;
  }

  // Puts one label, bubble or heading by a spot of the drawing, clear of the
  // fixed boxes and of every other box on the map (planBubble). Returns
  // false when there is no free spot even with the bubbles gone (it then
  // takes the side that covers least). The spot is kept on the node, so it
  // can be put again when the frame or the camera changes.
  function place(node, x, y, gap) {
    Object.assign(node.dataset, { x, y, gap });
    const frameBox = overlay.getBoundingClientRect();
    const [px, py] = toFrame(x, y);
    const box = { ...measure(node, frameBox), px, py, gap };
    const others = [...overlay.children].filter((other) => other !== node && !other.classList.contains("unplaced"));
    const isBubble = (other) => other.classList.contains("map-bubble");
    const boxes = (nodes) => nodes.map((other) => boxIn(other, frameBox));
    const [best, least, dropBubbles] = planBubble({ w: frameBox.width, h: frameBox.height }, box,
      fixedBoxes(frameBox), boxes(others.filter((other) => !isBubble(other))), boxes(others.filter(isBubble)));
    node.style.left = `${best[0]}px`;
    node.style.top = `${best[1]}px`;
    if (dropBubbles) {
      for (const other of overlay.querySelectorAll(".map-bubble")) if (other !== node && overlaps(node, other)) other.remove();
    }
    return least === 0;
  }

  // Every heading and label put again, in that order (headings first), after
  // the frame's width or the camera changed: each measured afresh, then all
  // placed by planLabels. Bubbles go.
  function relayout() {
    if (!view) return;
    clearSchoolName();
    for (const node of overlay.querySelectorAll(".map-bubble")) node.remove();
    placeAround();
    const frameBox = overlay.getBoundingClientRect();
    const frameSize = { w: frameBox.width, h: frameBox.height };
    const narrow = frameBox.width < NARROW;
    const itemOf = (node) => {
      const x = Number(node.dataset.x), y = Number(node.dataset.y);
      if (node.classList.contains("table-label")) node.textContent = narrow ? node.dataset.short : node.dataset.full;
      node.classList.toggle("narrow", narrow);
      const [px, py] = toFrame(x, y);
      return { ...measure(node, frameBox), px, py, gap: Number(node.dataset.gap), inView: inView(x, y),
        heading: node.classList.contains("split-tag"),
        atTable: node.classList.contains("table-label") || node.classList.contains("on-table") };
    };
    const fixed = fixedBoxes(frameBox);
    const taken = [];  // What is put, in order: the next ones keep off it.
    const put = (nodes, plan) => {
      const items = nodes.map(itemOf);
      const spots = plan(items);
      nodes.forEach((node, k) => {
        if (!spots[k]) {
          node.classList.add("unplaced");
          return;
        }
        node.style.left = `${spots[k][0]}px`;
        node.style.top = `${spots[k][1]}px`;
        taken.push([spots[k][0], spots[k][1], items[k].w, items[k].h]);
      });
    };
    // The headings, then the empty chairs' labels.
    put([...overlay.querySelectorAll(".split-tag"), ...overlay.querySelectorAll(".table-label.empty")],
      (items) => planLabels(frameSize, items, fixed));
    // At the table, the cards of the seats that spoke, in seat_order (直し26-1).
    const { named, planned } = placeTableBubbles(frameBox, frameSize, taken);
    // The names of the other seats there (a seat whose card is up has none:
    // the card says who), then a seat's name card.
    const labels = [...overlay.querySelectorAll(".table-label:not(.empty)")];
    for (const label of labels) if (named.has(label.dataset.seat)) label.classList.add("unplaced");
    put([...labels.filter((label) => !named.has(label.dataset.seat)), ...overlay.querySelectorAll(".map-tip")],
      (items) => planLabels(frameSize, items, [...fixed, ...taken]));
    placeSeatPresses(planned);
    putChoices();
    placeAskMarks();
  }

  // A 「？」 by its seat, at the first of its four corners that covers no word
  // drawn on the map (a place name, a shelf's name, the school's); with none
  // free, the one that covers least. Measured on screen, as the zoom is now.
  function placeAskMarks() {
    const marks = [...svg.querySelectorAll(".pt.silent .ask-mark")];
    if (!marks.length) return;
    const words = [...svg.querySelectorAll(".place-names text, .shelf-names text, .school text, .school-picture image")]
      .map((node) => node.getBoundingClientRect()).filter((r) => r.width)
      .map((r) => [r.left - WORD_PAD, r.top - WORD_PAD, r.width + 2 * WORD_PAD, r.height + 2 * WORD_PAD]);
    for (const mark of marks) {
      const boxes = ASK_CORNERS.map(([x, y, anchor]) => {
        Object.entries({ x, y, "text-anchor": anchor }).forEach(([key, value]) => mark.setAttribute(key, value));
        const r = mark.getBoundingClientRect();
        return [r.left, r.top, r.width, r.height];
      });
      const [x, y, anchor] = ASK_CORNERS[leastCovered(boxes, words)];
      Object.entries({ x, y, "text-anchor": anchor }).forEach(([key, value]) => mark.setAttribute(key, value));
    }
  }

  // The school's name stays under its mark, slid left or right off the
  // seats' points by as little as it takes (直し26-4); a place name in its
  // way (or in the way of the school's picture) moves up or down (whichever
  // is nearer its own side), just clear of both, as the zoom is now.
  function clearSchoolName() {
    const label = svg.querySelector(".school text");
    const names = [...svg.querySelectorAll(".place-names text")];
    for (const name of names) name.removeAttribute("dy");
    if (label) label.removeAttribute("dx");
    let school = label && label.getBoundingClientRect();
    if (!school || !school.width) return;
    const dots = [...svg.querySelectorAll(".points .pt .shape")].map((node) => node.getBoundingClientRect()).filter((r) => r.width)
      .map((r) => [r.left - WORD_PAD, r.top - WORD_PAD, r.width + 2 * WORD_PAD, r.height + 2 * WORD_PAD]);
    const slide = nameSlide([school.left, school.top, school.width, school.height], dots);
    if (slide) {
      label.setAttribute("dx", slide * label.getBBox().width / school.width);
      school = label.getBoundingClientRect();
    }
    const picture = svg.querySelector(".school-picture image");
    if (picture) {
      const p = picture.getBoundingClientRect();
      school = { left: Math.min(school.left, p.left), right: Math.max(school.right, p.right),
        top: Math.min(school.top, p.top), bottom: Math.max(school.bottom, p.bottom) };
    }
    const perPx = vb.h / (overlay.clientHeight || 1);
    for (const name of names) {
      const r = name.getBoundingClientRect();
      if (!(r.left < school.right + WORD_PAD && school.left - WORD_PAD < r.right &&
        r.top < school.bottom + WORD_PAD && school.top - WORD_PAD < r.bottom)) continue;
      const below = r.top + r.bottom >= school.top + school.bottom;
      const shift = below ? school.bottom + WORD_PAD - r.top : school.top - WORD_PAD - r.bottom;
      name.setAttribute("dy", shift * perPx);
    }
  }

  // How far a name ([left, top, width, height]) slides left (less than 0) or
  // right to cover none of the boxes given: 0 when it covers none already;
  // the smaller slide, up to SLIDE_MOST px, the left first when they are the
  // same; 0 when no slide that small frees it. It reads nothing but what it
  // is given.
  function nameSlide([left, top, w, h], boxes) {
    const free = (dx) => !boxes.some((b) => boxesMeet([left + dx, top, w, h], b));
    if (free(0)) return 0;
    for (let d = 1; d <= SLIDE_MOST; d++) {
      if (free(-d)) return -d;
      if (free(d)) return d;
    }
    return 0;
  }

  // Of a few boxes, the first that covers none of the others given, or the
  // one that covers least ([left, top, width, height]). It reads nothing but
  // what it is given.
  function leastCovered(boxes, others) {
    let best = 0, least = Infinity;
    boxes.forEach(([left, top, w, h], k) => {
      const area = others.reduce((sum, [ol, ot, ow, oh]) => sum + Math.max(0, Math.min(left + w, ol + ow) - Math.max(left, ol)) *
        Math.max(0, Math.min(top + h, ot + oh) - Math.max(top, ot)), 0);
      if (area < least) { best = k; least = area; }
    });
    return best;
  }

  function overlaps(a, b) {
    const r = a.getBoundingClientRect(), q = b.getBoundingClientRect();
    return r.left < q.right && q.left < r.right && r.top < q.bottom && q.top < r.bottom;
  }

  function seatOf(seatId) { return app.state.seatById[seatId]; }
  function spotOf(seatId) { return points[seatId].at(); }

  // A seat's name card: one at a time, by its mark, in the words the seat
  // list shows (its title, and on the in-school screen its company and name;
  // seat_label.py), set on the screen only. It covers no lamp card, heading
  // or label on the map and keeps inside the frame; it moves none of them.
  function showTip(seatId) {
    const seat = seatOf(seatId);
    if (!seat || !points[seatId]) return;
    hideTip();
    const tip = div("map-tip");
    tip.dataset.seat = seatId;
    tip.append(div("title", seat.title));
    if (seat.detail) tip.append(div("detail", seat.detail));
    if (isSilent(seatId)) tip.append(div("detail", app.state.texts.not_asked_yet));
    overlay.append(tip);
    const [x, y] = spotOf(seatId);
    Object.assign(tip.dataset, { x, y, gap: 14 });
    if (!inView(x, y)) { tip.classList.add("unplaced"); return; }
    const frameBox = overlay.getBoundingClientRect();
    const [px, py] = toFrame(x, y);
    const others = [...overlay.children].filter((other) => other !== tip && !other.classList.contains("unplaced"))
      .map((other) => boxIn(other, frameBox));
    const own = boxIn(points[seatId].node.querySelector(".shape"), frameBox);
    const [left, top] = tipSpot({ w: frameBox.width, h: frameBox.height }, { ...measure(tip, frameBox), px, py, gap: 14 },
      [...others, own], fixedBoxes(frameBox));
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  }

  // Where a seat's name card goes ({ w, h } by its mark at px, py, gap away)
  // in a frame { w, h }: of the eight places round the mark (above first),
  // the first that covers nothing; failing that, the one that covers least,
  // what it must not cover (avoid: the cards, headings and labels on the map
  // and the mark itself) counting far more than the map's words and seats
  // (fixed). Always inside the frame. It reads nothing but what it is given.
  function tipSpot(frame, box, avoid, fixed) {
    const { w, h, px, py, gap } = box, d = gap * 0.7;
    const clampX = (left) => Math.max(4, Math.min(left, frame.w - w - 4));
    const clampY = (top) => Math.max(4, Math.min(top, frame.h - h - 4));
    const spots = [[px - w / 2, py - h - gap], [px + gap, py - h / 2], [px - w / 2, py + gap], [px - w - gap, py - h / 2],
      [px + d, py - h - d], [px - w - d, py - h - d], [px + d, py + d], [px - w - d, py + d]]
      .map(([left, top]) => [clampX(left), clampY(top)]);
    const area = ([left, top], boxes) => boxes.reduce((sum, [ol, ot, ow, oh]) =>
      sum + Math.max(0, Math.min(left + w, ol + ow) - Math.max(left, ol)) *
        Math.max(0, Math.min(top + h, ot + oh) - Math.max(top, ot)), 0);
    let best = spots[0], least = Infinity;
    for (const spot of spots) {
      const cost = area(spot, avoid) * 1000 + area(spot, fixed);
      if (cost < least) { best = spot; least = cost; }
      if (!cost) break;
    }
    return best;
  }

  function hideTip() { for (const tip of overlay.querySelectorAll(".map-tip")) tip.remove(); }
  function restoreTip() { if (sticky) showTip(sticky); else hideTip(); }

  // 灯り札: a seat's first quote on paper by its seat, in large Mincho, and
  // under it which seat, in the words the seat's label already shows. A
  // thread of light runs from the seat to the card's nearest edge.
  function bubble(seatId, quote) {
    const seat = seatOf(seatId);
    if (!seat || !quote) return;
    const [x, y] = spotOf(seatId);
    if (!inView(x, y)) return;
    const node = div("map-bubble");
    node.append(div("voice", voiceOf(quote)), div("who", whoOf(seat)));
    overlay.append(node);
    place(node, x, y, 18);
    thread(node, ...toFrame(x, y));
    timers.push(setTimeout(() => node.classList.add("fading"), BUBBLE_FOR - FADE_FOR));
    timers.push(setTimeout(() => node.remove(), BUBBLE_FOR));
  }

  // A lamp card's words: the quote cut at BUBBLE_CHARS with 「…」, and which
  // seat, in the words the seat's label already shows.
  function voiceOf(quote) {
    const chars = [...quote.text];
    const cut = chars.length > BUBBLE_CHARS ? chars.slice(0, BUBBLE_CHARS).join("") + "…" : quote.text;
    return quote.said ? `「${cut}」` : cut;
  }

  function whoOf(seat) { return [seat.title, seat.detail].filter(Boolean).join("　"); }

  // The thread of light from a seat's spot (px, py in the frame) to the
  // nearest edge of its card. Inside the card, so it goes with it.
  function thread(node, px, py) {
    const left = parseFloat(node.style.left), top = parseFloat(node.style.top);
    const { width, height } = node.getBoundingClientRect();
    const qx = Math.min(Math.max(px, left), left + width), qy = Math.min(Math.max(py, top), top + height);
    const length = Math.hypot(qx - px, qy - py);
    if (length < 4) return;
    const line = document.createElement("span");
    line.className = "thread";
    Object.assign(line.style, { left: `${px - left}px`, top: `${py - top}px`, width: `${length}px` });
    line.style.setProperty("--a", `${Math.atan2(qy - py, qx - px)}rad`);
    node.append(line);
  }

  // A seat lights: bright, and (unless motion is reduced) one soft ring of
  // light goes out from it, once.
  function light(seatId) {
    const node = points[seatId].node;
    node.classList.add("lit");
    if (reduced() || !node.animate) return;
    const ring = svgEl("circle", { class: "ripple", r: 10 });
    node.append(ring);
    const wave = ring.animate([{ transform: "scale(1)", opacity: 0.9 }, { transform: "scale(4.2)", opacity: 0 }],
      { duration: RIPPLE_FOR, easing: "cubic-bezier(.2,.6,.3,1)" });
    wave.finished.then(() => ring.remove(), () => ring.remove());
  }

  // --- a round ---

  function isSilent(seatId) { return app.state.silent.has(seatId) && !app.state.met.has(seatId); }

  function clearRound() {
    roundNo += 1;
    for (const timer of timers) clearTimeout(timer);
    timers = [];
    for (const flight of flights) flight.cancel();
    flights = [];
    sticky = null;
    roundSeats = [];
    hideTip();
    for (const node of overlay.querySelectorAll(".map-bubble, .split-tag, .table-label, .table-bubble, .seat-press, .map-hint")) node.remove();
    splitLayer.replaceChildren();
    clearTable();
    for (const { node } of Object.values(points)) node.classList.remove("lit");
  }

  // The seats quoted light up one after another, each with its first quote
  // in a short bubble. On the picture the round table follows; on the flat
  // map, the splits. No seat answered: nothing lights.
  function round(result) {
    if (!map) return;
    if (!view) { pending = result; return; }
    clearRound();
    refresh();
    const first = {};
    for (const quote of result.quotes) if (!(quote.seat_id in first)) first[quote.seat_id] = quote;
    const order = result.seat_order.filter((id) => points[id]);
    if (!order.length) return;
    roundSeats = order;
    // 「いまやること」 (直し31-5): the seats are lighting until the table's
    // cards (or, on the flat map, the last bubble) are out.
    app.setNow({ reading: true });
    // The whole map and its sources on screen while the round plays (on a
    // low screen it starts under the question). At once, as the round starts.
    $("map").scrollIntoView({ block: "nearest" });
    if (view.relief) return tableRound(result, order, first, roundNo);
    const last = order[order.length - 1];
    if (reduced()) {  // Everything at once: no order, no bubbles.
      for (const id of order) points[id].node.classList.add("lit");
      sticky = last;
      showTip(last);
      drawSplits(result);
      app.setNow({ reading: false });
      return;
    }
    order.forEach((id, k) => timers.push(setTimeout(() => {
      light(id);
      bubble(id, first[id]);
    }, k * LIGHT_EVERY)));
    const end = (order.length - 1) * LIGHT_EVERY;
    timers.push(setTimeout(() => { drawSplits(result); app.setNow({ reading: false }); }, end + LIGHT_EVERY));
    timers.push(setTimeout(() => { sticky = last; showTip(last); }, end + BUBBLE_FOR));
  }

  // A dashed line between the first seat of each side, its heading near it.
  function drawSplits(result) {
    const seatOfQuote = {};
    for (const quote of result.quotes) seatOfQuote[quote.utterance_id] = quote.seat_id;
    for (const split of result.splits) {
      const a = seatOfQuote[split.side_a[0]], b = seatOfQuote[split.side_b[0]];
      if (!points[a] || !points[b] || a === b) continue;
      const [ax, ay] = spotOf(a), [bx, by] = spotOf(b);
      splitLayer.append(svgEl("line", { x1: ax, y1: ay, x2: bx, y2: by }));
      // It wraps after its 「：」 or between its 「…」, never inside one (app.phrased).
      const tag = div("split-tag");
      tag.append(app.phrased(app.shownQuotes(split.heading)));
      tag.classList.toggle("narrow", overlay.clientWidth < NARROW);
      overlay.append(tag);
      place(tag, (ax + bx) / 2, (ay + by) / 2, 8);
    }
  }

  // --- the round table (the picture only) ---

  const tableCenter = () => {
    const [x, y] = centroid(map.boundary);
    return { x, y, level: view.zAt(x, y) };
  };

  function onTable(center, angle, out, lift = TABLE_LIFT) {
    const a = angle * Math.PI / 180;
    return view.proj(center.x + (TABLE_RX + out) * Math.cos(a), center.y + (TABLE_RY + out) * Math.sin(a),
      lift, center.level);
  }

  function ring(center, out, lift) {
    return Array.from({ length: 72 }, (_, k) => onTable(center, k * 5, out, lift));
  }

  // The side of the table towards the camera, in degrees round it (0° the
  // map's east, 90° its south): where its rim is lowest on the picture,
  // worked out from the projection, so it holds whichever way the picture
  // looks (直し31-4: now south, 90°).
  function frontAngle(center) {
    let best = 0, low = -Infinity;
    for (let k = 0; k < 72; k++) {
      const y = onTable(center, k * 5, 0)[1];
      if (y > low) [best, low] = [k * 5, y];
    }
    return best;
  }

  // Who sits where, round from the side in front (front, in degrees): the
  // two sides of the first split face each other across the dashed line
  // (left and right), the other seats sit at the back, and the empty chairs
  // in front.
  function seating(result, order, front = 270) {
    const seatOfQuote = {};
    for (const quote of result.quotes) seatOfQuote[quote.utterance_id] = quote.seat_id;
    const sideOf = (ids) => new Set(ids.map((id) => seatOfQuote[id]).filter((id) => order.includes(id)));
    const split = result.splits.map((s) => ({ split: s, a: sideOf(s.side_a), b: sideOf(s.side_b) }))
      .find(({ a, b }) => a.size && b.size && [...a].some((id) => !b.has(id)));
    const groups = { a: [], b: [], back: [], front: [] };
    for (const id of order) {
      if (split && split.a.has(id)) groups.a.push(id);
      else if (split && split.b.has(id)) groups.b.push(id);
      else groups.back.push(id);
    }
    groups.front = result.silent_seats.filter((id) => points[id] && isSilent(id));
    const turn = (a) => ((a % 360) + 360) % 360;
    const arcs = { a: [turn(front + 90), 80], b: [turn(front - 90), 80], back: [turn(front + 180), split ? 70 : 170],
      front: [front, 90] };
    const seats = [];
    for (const [name, ids] of Object.entries(groups)) {
      const [middle, arc] = arcs[name];
      const gap = ids.length > 1 ? Math.min(26, arc / (ids.length - 1)) : 0;
      ids.forEach((id, k) => seats.push({ id, group: name, angle: middle + (k - (ids.length - 1) / 2) * gap }));
    }
    return { split: split && split.split, sides: split ? [split.a, split.b] : null, seats };
  }

  // The order the cards at the table are put in, so the first that find
  // room are these (直し27-2): with a split, one from each side by turns
  // (side_a first), each side in seat_order; when one side has no one
  // left, the other's; then the seats on neither side, in seat_order.
  // Without a split, seat_order. It reads nothing but what it is given.
  function cardOrder(order, sides) {
    if (!sides) return [...order];
    const [a, b] = sides;
    const sideA = order.filter((id) => a.has(id)), sideB = order.filter((id) => b.has(id) && !a.has(id));
    const out = [];
    for (let k = 0; k < Math.max(sideA.length, sideB.length); k++) {
      if (k < sideA.length) out.push(sideA[k]);
      if (k < sideB.length) out.push(sideB[k]);
    }
    return out.concat(order.filter((id) => !out.includes(id)));
  }

  function tableView(center) {
    const spots = ring(center, SEAT_OUT + 70, TABLE_LIFT);
    const xs = spots.map((p) => p[0]), ys = spots.map((p) => p[1]);
    let w = (Math.max(...xs) - Math.min(...xs)) * 1.2, h = (Math.max(...ys) - Math.min(...ys)) * 1.3;
    if (w / h < view.W / view.H) w = h * view.W / view.H; else h = w * view.H / view.W;
    return { x: (Math.max(...xs) + Math.min(...xs)) / 2 - w / 2, y: (Math.max(...ys) + Math.min(...ys)) / 2 - h / 2, w, h };
  }

  async function tableRound(result, order, first, mine) {
    const still = () => mine === roundNo;
    // From the whole map, so every seat that lights can be seen.
    if (vb.w < view.W - 0.5) await moveTo({ x: 0, y: 0, w: view.W, h: view.H }, reduced() ? 0 : 500);
    if (!still()) return;
    if (reduced()) {
      for (const id of order) points[id].node.classList.add("lit");
    } else {
      for (const id of order) {
        light(id);
        bubble(id, first[id]);
        await wait(LIGHT_EVERY);
        if (!still()) return;
      }
      await wait(300);
      if (!still()) return;
    }
    const center = tableCenter();
    // Motion reduced: the camera is at the table at once, nothing flies.
    await moveTo(tableView(center), CAMERA_FOR);
    if (!still()) return;
    openTable(result, order, center, still);
  }

  async function openTable(result, order, center, still) {
    const motion = !reduced();
    const front = frontAngle(center);
    const { split, sides, seats } = seating(result, order, front);
    tableAt = { center, angles: seats.map((sitting) => sitting.angle), split: Boolean(split), front };
    svg.classList.add("dim");
    // While the table is open the map's points behind take no mouse, press
    // or touch (style.css; 直し27-4): the name card the mouse showed goes.
    if (hovered && points[hovered]) points[hovered].node.classList.remove("hover");
    hovered = null;
    hideTip();
    // The map's points step back from the keyboard too: Tab goes to the chairs.
    for (const { node } of Object.values(points)) node.setAttribute("tabindex", "-1");
    $("map-back").hidden = false;
    const rc = rough.svg(svg);
    const S = view.S;
    const polygon = (className, spots) => svgEl("polygon", { class: className, points: spots.map((p) => p.join(",")).join(" ") });
    tableTop = ring(center, 0, TABLE_LIFT);
    // The lamp's light on the ground round the table, its shadow, the top's
    // edge (so it reads as a top, not a ring), the top lit from its middle,
    // its rim of light, and the lamp.
    const top = svgEl("g", { class: "table-top-group" });
    const [lx, ly] = view.proj(center.x, center.y, TABLE_LIFT, center.level);
    const lamp = svgEl("g", { class: "table-lamp" });
    lamp.append(svgEl("circle", { class: "light", cx: lx, cy: ly, r: 70 * S }),
      svgEl("circle", { class: "core", cx: lx, cy: ly, r: 4.5 * S }));
    // A round table of wood (直し29-2): its side in front, under the top;
    // the top's grain; the lamp's light on its near rim; its one leg and
    // foot, a little seen under the front. Its size and the seats' spots
    // are as before.
    const under = ring(center, 0, TABLE_LIFT - TABLE_THICK);
    // The side towards the camera: 80° each way from the front.
    const near = tableTop.filter((_, k) => Math.min(Math.abs(k * 5 - front), 360 - Math.abs(k * 5 - front)) <= 80);
    const rimLight = svgEl("polyline", { class: "table-rim-light", points: near.map((p) => p.join(",")).join(" ") });
    top.append(polygon("table-edge", under), polygon("table-top", tableTop),
      polygon("table-grain", ring(center, -46, TABLE_LIFT)), polygon("table-grain", ring(center, -86, TABLE_LIFT)),
      polygon("table-inner", ring(center, -16, TABLE_LIFT)), polygon("table-rim-glow", tableTop), rimLight, lamp);
    const low = under.reduce((a, b) => (b[1] > a[1] ? b : a));
    const foot = svgEl("g", { class: "table-foot" });
    foot.append(svgEl("ellipse", { class: "base", cx: lx, cy: low[1] + 15 * S, rx: 36 * S, ry: 7 * S }),
      svgEl("rect", { class: "leg", x: lx - 11 * S, y: low[1] - 8 * S, width: 22 * S, height: 23 * S, rx: 3 * S }));
    tableLayer.append(polygon("table-glow", ring(center, SEAT_OUT + 40, 0)),
      polygon("table-shadow", ring(center, 4, 0)), foot, top);
    if (motion) {
      top.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, easing: "ease-out" });
      await wait(350);
      if (!still()) return;
    }
    // The split: a dashed line down the table's middle, between the sides.
    if (split) {
      const [n0, n1] = [view.proj(center.x, center.y - TABLE_RY + 6, TABLE_LIFT, center.level),
        view.proj(center.x, center.y + TABLE_RY - 6, TABLE_LIFT, center.level)];
      const line = rc.line(n0[0], n0[1], n1[0], n1[1], { stroke: "#000", strokeWidth: 1.8 * S, roughness: 0.9,
        seed: 5 });
      line.classList.add("table-split");
      tableLayer.append(line);
    }
    const landed = [];
    seats.forEach((sitting, k) => {
      const at = onTable(center, sitting.angle, SEAT_OUT);
      if (sitting.group === "front") return landed.push(chair(sitting.id, at, [lx, ly]));
      const kind = points[sitting.id].seat.kind;
      const node = svgEl("g", { class: `token pt lit kind-${kind}`, "aria-hidden": "true" });
      // Its chair, lit, its back to the outside (直し29-2); the seat's own mark sits on it.
      node.append(svgEl("circle", { class: "halo", r: 20 }), chairBack(at, [lx, ly], 15, "chair-back"),
        svgEl("ellipse", { class: "cushion", rx: 15, ry: 10, cy: 3 }), shape(kind));
      // Its work in a picture, its mark the picture's frame (直し29-3); none fits, its mark as before.
      const icon = seatIcon(kind, seatOf(sitting.id).title, app.state.texts.seat_icons || []);
      if (icon) {
        node.classList.add("has-icon");
        node.append(svgEl("path", { class: "icon", d: SEAT_ICON_PATHS[icon], transform: SEAT_ICON_FIT[kind] || "" }));
      }
      tableLayer.append(node);
      const token = { node, at, scale: TOKEN, id: sitting.id };
      tokens.push(token);
      if (!motion) return landed.push(Promise.resolve(token));
      const f = pointScale();
      const [x0, y0] = spotOf(sitting.id);
      const mx = (x0 + at[0]) / 2, my = Math.max(vb.y + 30 * S, Math.min(y0, at[1]) - 70 * S);
      const flight = node.animate([
        { transform: `translate(${x0}px, ${y0}px) scale(${f * 0.8})` },
        { transform: `translate(${mx}px, ${my}px) scale(${f * TOKEN * 1.25})`, offset: 0.5 },
        { transform: `translate(${at[0]}px, ${at[1]}px) scale(${f * TOKEN})` },
      ], { duration: FLY_FOR, delay: k * FLY_GAP, easing: "cubic-bezier(.3,.7,.2,1)", fill: "both" });
      flights.push(flight);
      landed.push(flight.finished.then(() => token, () => token));
    });
    rescale();
    const done = await Promise.all(landed);
    if (!still()) return;
    for (const flight of flights) flight.cancel();  // The transform attribute holds the spot now.
    flights = [];
    rescale();
    for (const item of done) {
      if (!item || !item.id) continue;
      const title = seatOf(item.id).title, chars = [...title];
      const label = div("table-label", title);
      if (item.chair) label.classList.add("empty");
      overlay.append(label);
      Object.assign(label.dataset, { seat: item.id, x: item.at[0], y: item.at[1], gap: item.chair ? CHAIR_GAP : 16,
        full: title, short: chars.length > LABEL_CHARS ? chars.slice(0, LABEL_CHARS).join("") + "…" : title });
    }
    // Each seat that spoke: its lamp card by its chair, in seat_order (as
    // Tab goes), and the part that takes a press when the card has no room
    // (直し26-1). They find room in cardOrder: both sides of a split first.
    const first = {};
    for (const quote of result.quotes) if (!(quote.seat_id in first)) first[quote.seat_id] = quote;
    const rank = cardOrder(order, sides);
    order.forEach((id, k) => {
      const token = tokens.find((t) => t.id === id && !t.chair);
      if (!token || !first[id]) return;
      const card = tableBubble(id, first[id], token.at, k);
      card.dataset.rank = String(rank.indexOf(id));
      overlay.append(card, seatPress(id, token.at));
    });
    // The split's heading: under the map, over neither the table's top nor
    // its chairs; on a map narrower than TAG_ON_MAP, in the split block only.
    // It wraps after its 「：」 or between its 「…」, never inside one (app.phrased).
    if (split && overlay.clientWidth >= TAG_ON_MAP) $("map-heading").replaceChildren(app.phrased(app.shownQuotes(split.heading)));
    for (const chairNode of tableLayer.querySelectorAll(".chair")) chairNode.classList.add("ready");
    tableRoundNo = result.round;
    if (band && band.round === result.round) seatBand();
    if (!pressedOnce) overlay.append(div("map-hint", app.state.texts.bubble_hint));
    relayout();
    marked();
    app.setNow({ reading: false, table: true });
  }

  // A seat's lamp card at the table: the same words as on the map, kept.
  // Pressed (or Enter or Space on it), it opens its choices (直し26-2).
  function tableBubble(seatId, quote, at, k) {
    const node = div("table-bubble unplaced");
    node.append(div("voice", voiceOf(quote)), div("who", whoOf(seatOf(seatId))));
    Object.assign(node.dataset, { seat: seatId, utterance: quote.utterance_id, x: at[0], y: at[1] });
    node.style.setProperty("--k", String(k));
    node.tabIndex = 0;
    node.setAttribute("role", "button");
    node.setAttribute("aria-expanded", "false");
    pressable(node, () => toggleChoices(seatId));
    return node;
  }

  // コーチ and オブザーバー (直し29-1), from the band app.js got with its one
  // call to /api/coach: kept for the round's table, seated at once if it is
  // open. A band with no cards, or answered, is not sent.
  function setBand(roundNo, cards) {
    band = { round: roundNo, cards };
    if (tableTop && tableAt && tableRoundNo === roundNo && !tokens.some((token) => token.ai)) {
      seatBand();
      relayout();
    }
  }

  // Their two seats: off the seats and chairs (aiAngles), a small flame in
  // moonlight each, no seat's mark; their names as on the cards below; their
  // questions in moonlit cards that find room before the seats' (rank).
  function seatBand() {
    const { center, angles, split, front } = tableAt;
    const spots = aiAngles(angles, split, band.cards.length, front);
    band.cards.forEach((card, k) => {
      const id = `ai-${card.role}`, at = onTable(center, spots[k], SEAT_OUT);
      const node = svgEl("g", { class: "token ai-seat lit", "aria-hidden": "true" });
      node.append(svgEl("circle", { class: "halo", r: 20 }), svgEl("path", { class: "shape", d: AI_FLAME }));
      tableLayer.append(node);
      tokens.push({ node, at, scale: TOKEN, id, ai: card });
      const label = div("table-label ai", card.label);
      Object.assign(label.dataset, { seat: id, x: at[0], y: at[1], gap: 16, full: card.label, short: card.label });
      const bubble = aiBubble(id, card, at);
      bubble.dataset.rank = String(k - band.cards.length);
      overlay.append(label, bubble, seatPress(id, at));
    });
    rescale();
  }

  // Where コーチ and オブザーバー sit (直し29-1), in degrees round the table:
  // with a split, at the ends of its dashed line (the front and the back:
  // on neither side) where no seat is near; else between the groups,
  // the front's two first; the first tried
  // that is AI_APART from every seat (taken) and from each other, or failing
  // that the furthest. It reads nothing but what it is given.
  function aiAngles(taken, split, count = 2, front = 270) {
    const turn = (a) => ((a % 360) + 360) % 360;
    const tried = [...(split ? [front, turn(front + 180)] : []), ...[-45, 45, -135, 135].map((d) => turn(front + d)),
      ...Array.from({ length: 72 }, (_, k) => k * 5)];
    const apart = (a, b) => { const d = (((a - b) % 360) + 360) % 360; return Math.min(d, 360 - d); };
    const out = [];
    for (let k = 0; k < count; k++) {
      const near = (angle) => Math.min(360, ...[...taken, ...out].map((other) => apart(angle, other)));
      const free = tried.find((angle) => near(angle) >= AI_APART);
      out.push(free !== undefined ? free : tried.reduce((best, angle) => (near(angle) > near(best) ? angle : best)));
    }
    return out;
  }

  // An AI question's card at the table: in moonlight, not the seats' paper,
  // so a recorded voice and an AI's question are told apart at a glance.
  // Pressed, its choices: 「答える」 and 「閉じる」.
  function aiBubble(id, card, at) {
    const node = div("table-bubble ai unplaced");
    node.append(div("badge", card.badge), div("voice", card.question), div("who", card.label));
    Object.assign(node.dataset, { seat: id, utterance: "", x: at[0], y: at[1] });
    node.style.setProperty("--k", "0");
    node.tabIndex = 0;
    node.setAttribute("role", "button");
    node.setAttribute("aria-expanded", "false");
    pressable(node, () => toggleChoices(id));
    return node;
  }

  // Whose a seat at the table is, in words: a seat's title and detail, or
  // コーチ's or オブザーバー's label.
  function nameAt(seatId) {
    const token = tokens.find((t) => t.id === seatId && t.ai);
    return token ? token.ai.label : whoOf(seatOf(seatId));
  }

  // Over a seat at the table whose card has no room: pressing it (or Enter
  // or Space on it) shows that card.
  function seatPress(seatId, at) {
    const node = div("seat-press unplaced");
    Object.assign(node.dataset, { seat: seatId, x: at[0], y: at[1] });
    node.tabIndex = 0;
    node.setAttribute("role", "button");
    node.setAttribute("aria-label", nameAt(seatId));
    pressable(node, () => {
      opened = seatId;
      relayout();
      toggleChoices(seatId);
    });
    return node;
  }

  // The cards at the table (直し26-1), each by its seat in seat_order (the
  // order they were added in), clear of what a label keeps off but the map's
  // words (the map is dimmed under the table), of the labels put before
  // (taken) and of one another, near its seat, its tail crossing no seat,
  // chair or the table's top (planTableBubbles). A card with no room is left
  // out; the one pressed (opened) is then shown all the same, by its seat
  // clear of the fixed boxes and its tail clear of the other seats, the
  // cards and chairs' labels it covers stepping behind. Returns
  // the seats whose card is up (named) and those put by the plan (planned);
  // taken gets their boxes.
  function placeTableBubbles(frameBox, frameSize, taken) {
    const named = new Set(), planned = new Set();
    for (const node of overlay.querySelectorAll(".behind")) node.classList.remove("behind");
    // In cardOrder (直し27-2), not as they stand in the page.
    const cards = [...overlay.querySelectorAll(".table-bubble")].sort((x, y) => Number(x.dataset.rank) - Number(y.dataset.rank));
    if (!cards.length) return { named, planned };
    const before = [...taken];
    const fixed = fixedBoxes(frameBox, true, false);
    // A tail crosses no seat, chair, the table's top, nor a label put before.
    const block = [...tableLayer.querySelectorAll(".token .shape, .chair circle")].map((node) => boxIn(node, frameBox))
      .concat(tableTop ? topStrips(tableTop.map(([x, y]) => toFrame(x, y))) : [], before);
    const items = cards.map((card) => {
      const { px, py, r } = seatAtTable(card);
      // Its tail TAIL_LENGTH long at least, so it shows which seat it is.
      return { ...measure(card, frameBox), px, py, gap: r + TAIL_LENGTH, r,
        inView: inView(Number(card.dataset.x), Number(card.dataset.y)) };
    });
    const reach = Math.max(TABLE_REACH, frameSize.w * TABLE_REACH_PART);
    const spots = planTableBubbles(frameSize, items, [...fixed, ...before], block, reach);
    const show = (card, item, spot) => {
      card.style.left = `${spot[0]}px`;
      card.style.top = `${spot[1]}px`;
      const box = [spot[0], spot[1], item.w, item.h];
      const ends = drawTail(card, box, item);
      // The labels put after keep off the card and its tail.
      taken.push(box, ...(ends ? alongTail(ends) : []));
      named.add(card.dataset.seat);
    };
    cards.forEach((card, k) => {
      if (!spots[k]) return card.classList.add("unplaced");
      show(card, items[k], spots[k]);
      planned.add(card.dataset.seat);
    });
    const k = cards.findIndex((card) => card.dataset.seat === opened);
    if (k >= 0 && !spots[k] && items[k].inView) {
      cards[k].classList.remove("unplaced");
      cards[k].style.setProperty("--k", "0");  // Pressed: it comes at once (直し27-1).
      // Its tail crossing no other seat if it can be: a little further off,
      // or over the chairs' labels, if it must.
      const found = tableBubbleSpot(frameSize, items[k], [...fixed, ...before], block, [], 2 * reach) ||
        tableBubbleSpot(frameSize, items[k], fixed, block, [], 2 * reach);
      show(cards[k], items[k], found ? found[0] : chooseSpot(frameSize, items[k], [...fixed, ...before])[0]);
      for (const other of [...cards, ...overlay.querySelectorAll(".table-label.empty:not(.unplaced)")]) {
        if (other !== cards[k] && !other.classList.contains("unplaced") && overlaps(cards[k], other)) other.classList.add("behind");
      }
    }
    return { named, planned };
  }

  // The room the paragraph apart keeps round the seats at the table
  // (直し27-3): each seat's mark and SEAT_ROOM more, for its light.
  function seatRoom(frameBox) {
    return tokens.filter((t) => !t.chair).map(({ node }) => {
      const [l, t, w, h] = boxIn(node.querySelector(".shape"), frameBox);
      return [l - SEAT_ROOM, t - SEAT_ROOM, w + 2 * SEAT_ROOM, h + 2 * SEAT_ROOM];
    });
  }

  // Where a card's seat is at the table, in the frame (px, py), and how far
  // short of it a tail stops (r, clear of its mark).
  function seatAtTable(card) {
    const [px, py] = toFrame(Number(card.dataset.x), Number(card.dataset.y));
    const token = tokens.find((t) => t.id === card.dataset.seat && !t.chair);
    const shape = token && token.node.querySelector(".shape").getBoundingClientRect();
    return { px, py, r: shape ? Math.hypot(shape.width, shape.height) / 2 + 3 : 12, token };
  }

  // A card's tail: paper, from its side to just short of its seat, inside
  // the card so it goes with it.
  function drawTail(card, box, { px, py, r }) {
    for (const old of card.querySelectorAll(".tail")) old.remove();
    const ends = tailEnds(box, px, py, r);
    if (!ends) return null;
    const [[fx, fy], [qx, qy]] = ends;
    const tail = document.createElement("span");
    tail.className = "tail";
    // A little into the card, so the two are one piece of paper.
    Object.assign(tail.style, { left: `${fx - box[0]}px`, top: `${fy - box[1]}px`, width: `${Math.hypot(qx - fx, qy - fy) + 6}px` });
    tail.style.setProperty("--a", `${Math.atan2(qy - fy, qx - fx)}rad`);
    card.append(tail);
    return ends;
  }

  // A tail as a row of small boxes along it, for the labels to keep off. It
  // reads nothing but what it is given.
  function alongTail([[fx, fy], [qx, qy]], size = 10) {
    const steps = Math.max(1, Math.ceil(Math.hypot(qx - fx, qy - fy) / (size / 2)));
    return Array.from({ length: steps + 1 }, (_, k) => {
      const x = fx + (qx - fx) * k / steps, y = fy + (qy - fy) * k / steps;
      return [x - size / 2, y - size / 2, size, size];
    });
  }

  // The part that takes a press, over each seat at the table whose card the
  // plan left out.
  function placeSeatPresses(planned) {
    for (const node of overlay.querySelectorAll(".seat-press")) {
      const x = Number(node.dataset.x), y = Number(node.dataset.y);
      const out = planned.has(node.dataset.seat) || !inView(x, y);
      node.classList.toggle("unplaced", out);
      if (out) continue;
      const [px, py] = toFrame(x, y);
      node.style.left = `${px - SEAT_PRESS / 2}px`;
      node.style.top = `${py - SEAT_PRESS / 2}px`;
    }
  }

  // --- the choices a lamp card at the table opens (直し26-2) ---

  // One card of choices at a time: pressing another lamp card closes the
  // one open; pressing the same one again closes it.
  function toggleChoices(seatId) {
    if (choices && choices.seatId === seatId) return closeChoices(true);
    openChoices(seatId);
  }

  // By the lamp card, what can be done next with its words: each the same
  // as the round's own cards below the map do, in the teacher's words.
  function openChoices(seatId) {
    closeChoices(false);
    const card = [...overlay.querySelectorAll(".table-bubble")].find((node) => node.dataset.seat === seatId);
    if (!card || card.classList.contains("unplaced")) return;
    dropHint();
    const ai = tokens.find((t) => t.id === seatId && t.ai);
    if (ai) return openAnswer(seatId, card, ai.ai);
    app.setNow({ choices: true, pressed: true });
    const words = app.state.texts.bubble_choices, utteranceId = card.dataset.utterance;
    const node = div("map-choices");
    node.setAttribute("role", "group");
    node.setAttribute("aria-label", whoOf(seatOf(seatId)));
    // At the top, whose card it is (as on the lamp card), and 「閉じる」 (直し27-1).
    const head = div("head");
    const close = document.createElement("button");
    close.type = "button";
    close.className = "close";
    close.textContent = app.state.texts.bubble_close;
    close.addEventListener("click", () => closeChoices(true));
    head.append(div("who", whoOf(seatOf(seatId))), close);
    const button = (key, action) => {
      const item = document.createElement("button");
      item.type = "button";
      item.textContent = words[key];
      item.dataset.choice = key;
      item.addEventListener("click", action);
      return item;
    };
    const paragraph = div("paragraph");
    paragraph.hidden = true;
    // At its head, whose paragraph it is: the name only (直し27-3).
    const text = div("text");
    paragraph.append(div("whose", seatOf(seatId).title), text);
    // While a choice waits on the server it stays where it is (a disabled
    // button would drop the keyboard's focus): a second press then does nothing.
    let busy = false;
    const read = button("paragraph", async () => {
      if (busy) return;
      if (!text.textContent) {
        busy = true;
        try {
          text.textContent = await app.paragraph(utteranceId);
        } catch (error) {
          return;
        } finally {
          busy = false;
        }
      }
      paragraph.hidden = !paragraph.hidden;
      read.setAttribute("aria-expanded", String(!paragraph.hidden));
      putChoices();
    });
    read.setAttribute("aria-expanded", "false");
    const mark = button("mark", async () => {
      if (busy) return;
      busy = true;
      try {
        await app.mark(tableRoundNo, utteranceId);
      } catch (error) {
        // As below the map: nothing changes.
      } finally {
        busy = false;
      }
    });
    const write = app.state.carded.has(seatId) ? div("done", "質問カードにしました")
      : button("card", () => { closeChoices(false); app.openCard(seatId); });
    const below = button("read", () => { closeChoices(false); app.readBelow(tableRoundNo, utteranceId); });
    node.append(head, read, paragraph, mark, write, below);
    node.addEventListener("keydown", (event) => moveInChoices(event, node));
    card.after(node);  // Tab goes on from the lamp card into its choices.
    card.setAttribute("aria-expanded", "true");
    // Its seat at the table, a ring brighter, while they are open.
    const { token } = seatAtTable(card);
    if (token) token.node.classList.add("chosen");
    choices = { seatId, node, card, moved: false };
    marked();
    putChoices();
    read.focus({ preventScroll: true });
  }

  // The choices of コーチ's or オブザーバー's card (直し29-1): 「答える」, the
  // same one-line box as below the map (app.answerForm; sent, the next round
  // starts), and 「閉じる」. Not answering is fine: nothing waits on it.
  function openAnswer(seatId, card, ai) {
    const node = div("map-choices ai");
    node.setAttribute("role", "group");
    node.setAttribute("aria-label", ai.label);
    const head = div("head");
    const close = document.createElement("button");
    close.type = "button";
    close.className = "close";
    close.textContent = app.state.texts.bubble_close;
    close.addEventListener("click", () => closeChoices(true));
    head.append(div("who", ai.label), close);
    const answer = document.createElement("button");
    answer.type = "button";
    answer.textContent = app.state.texts.bubble_answer;
    answer.dataset.choice = "answer";
    const roundNo = tableRoundNo;
    answer.addEventListener("click", () => {
      const form = app.answerForm(roundNo, ai.role);
      answer.replaceWith(form);
      putChoices();
      form.querySelector("input").focus({ preventScroll: true });
    });
    // No paragraph here; putChoices lays out one, kept hidden.
    const paragraph = div("paragraph");
    paragraph.hidden = true;
    paragraph.append(div("text"));
    node.append(head, answer, paragraph);
    node.addEventListener("keydown", (event) => moveInChoices(event, node));
    card.after(node);
    card.setAttribute("aria-expanded", "true");
    const { token } = seatAtTable(card);
    if (token) token.node.classList.add("chosen");
    choices = { seatId, node, card, moved: false };
    putChoices();
    answer.focus({ preventScroll: true });
  }

  // Esc closes the choices, back to their lamp card; the arrows go from
  // one choice to the next (Tab too).
  function moveInChoices(event, node) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      return closeChoices(true);
    }
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const items = [...node.querySelectorAll("button")];
    const at = items.indexOf(document.activeElement);
    if (at < 0) return;
    event.preventDefault();
    items[(at + step + items.length) % items.length].focus();
  }

  // A card the plan left out, shown by pressing its seat, goes again with
  // its choices: the cards it covered come back, and the keyboard goes back
  // to the seat. (laying: called while the map is being laid out.)
  function closeChoices(back, laying = false) {
    if (!choices) return;
    const { node, card, seatId, moved } = choices;
    choices = null;
    node.remove();
    app.setNow({ choices: false });
    for (const other of overlay.querySelectorAll(".under-choices")) other.classList.remove("under-choices");
    for (const token of tableLayer.querySelectorAll(".token.chosen")) token.classList.remove("chosen");
    card.setAttribute("aria-expanded", "false");
    // Its card goes back to its own spot (a card moved for them), or goes
    // (one shown only by pressing its seat).
    const shownByPress = seatId === opened;
    if (shownByPress) opened = null;
    if ((shownByPress || moved) && !laying) relayout();
    if (!back) return;
    if (card.isConnected && !card.classList.contains("unplaced")) return card.focus({ preventScroll: true });
    const press = [...overlay.querySelectorAll(".seat-press")].find((other) => other.dataset.seat === seatId);
    if (press && !press.classList.contains("unplaced")) press.focus({ preventScroll: true });
  }

  // The choices by their lamp card (直し27-1): against its side, below,
  // above, right or left, its own card in sight, their tail to its seat;
  // inside the frame, clear of the table's top, its seats and chairs
  // (choicesPlan). Its card moves, while they are open, if that is what
  // keeps the others in sight. Closed when their card is no longer up.
  function putChoices(withBacks = true) {
    if (!choices) return;
    const { node, card } = choices;
    if (!card.isConnected || card.classList.contains("unplaced")) return closeChoices(false, true);
    for (const other of overlay.querySelectorAll(".under-choices, .behind")) other.classList.remove("under-choices", "behind");
    const frameBox = overlay.getBoundingClientRect();
    const frameWH = { w: frameBox.width, h: frameBox.height };
    // It keeps off the table, its seats and chairs (hard); it would rather
    // not cover the other cards, the labels, the arrow, the edge names and
    // the line by the edge (soft), which step behind it if it must.
    const shown = [...overlay.querySelectorAll(".table-bubble:not(.unplaced), .table-label:not(.unplaced), " +
      ".map-compass, .map-around, .map-hint")].filter((other) => other !== card && getComputedStyle(other).visibility !== "hidden");
    const others = shown.map((other) => boxIn(other, frameBox));
    const seat = seatAtTable(card);
    const own = boxIn(card, frameBox), hard = fixedBoxes(frameBox, false, false, withBacks);
    // A tail never crosses the table's top (top); it crosses no seat or chair either (block) but as a last resort.
    const top = tableTop ? topStrips(tableTop.map(([x, y]) => toFrame(x, y))) : [];
    const block = [...tableLayer.querySelectorAll(".token .shape, .chair circle")].map((other) => boxIn(other, frameBox)).concat(top);
    // ring: how far the seat's ring of light reaches, which choices with no tail keep off.
    const halo = seat.token && seat.token.node.querySelector(".halo").getBoundingClientRect();
    const item = { w: own[2], h: own[3], px: seat.px, py: seat.py, r: seat.r, gap: seat.r + TAIL_LENGTH,
      ring: halo ? halo.width / 2 + 2 : seat.r };
    const reach = 2 * Math.max(TABLE_REACH, frameWH.w * TABLE_REACH_PART);
    node.style.left = "0px";
    node.style.top = "0px";
    for (const old of node.querySelectorAll(".tail")) old.remove();
    // Two choices to a line; or, where the map has room only so (直し27-1),
    // smaller and three to a line (low), or one to a line (narrow). The
    // paragraph, when open (直し27-3): all of it if that finds room, else
    // PARAGRAPH_LINES lines or more, and only failing that fewer (it
    // scrolls); beside the choices or under them, the card as it is or
    // wider. The first way that covers nothing of soft; with none, the
    // one that covers least.
    const paragraph = node.querySelector(".paragraph"), text = paragraph.querySelector(".text");
    const widths = [0, 420, 540].filter((w) => w < frameWH.w - 16);
    const closed = [["", false, 0, 0], ["low", false, 0, 0], ["column", false, 0, 0]];
    const ways = paragraph.hidden ? closed
      : PARAGRAPH_STEPS.flatMap((lines) => [["", true, lines, 0],
        ...widths.map((w) => ["", false, lines, w]), ["low", false, lines, 0]]);
    const lineHeight = parseFloat(getComputedStyle(text).lineHeight) || 24;
    const lay = ([shape, beside, lines, width]) => {
      node.classList.toggle("low", shape === "low");
      node.classList.toggle("column", shape === "column");
      node.classList.toggle("beside", beside);
      text.style.maxHeight = lines ? `${Math.ceil(lines * lineHeight) + 1}px` : "";
      node.style.width = width ? `${width}px` : "";
    };
    // By its own card, the first way that covers nothing of soft; with
    // none, the one that covers least.
    // Failing all, the choices' tail may cross the other seats (never the
    // table's top); failing that, right by the seat they need none (the
    // seat's ring says whose they are), off its ring, then by it; and only
    // failing that may the moved card's tail cross a seat: the choices are
    // always against their card.
    const search = (tried) => {
      let planned = null;
      // needTail: true, or false (none, off the seat's ring), or "near" (none, by the ring).
      for (const [cardCrossed, crossed, needTail] of [[block, block, true], [block, top, true], [block, top, false],
        [block, top, "near"], [top, top, true], [top, top, false], [top, top, "near"]]) {
        const spots = cardSpots(frameWH, item, own, hard, cardCrossed, reach);
        for (const way of tried) {
          lay(way);
          const { width, height } = node.getBoundingClientRect();
          const plan = choicesPlan(frameWH, item, own, { w: width, h: height }, hard, crossed, others, spots, needTail);
          if (plan && (!planned || plan.covered < planned.plan.covered)) planned = { way, plan };
          if (plan && !plan.covered) break;
        }
        if (planned) return planned;
      }
      return null;
    };
    const setApart = (on) => {
      paragraph.classList.toggle("apart", on);
      if (!on) Object.assign(paragraph.style, { left: "", top: "", width: "" });
    };
    const put = ({ way, plan }) => {
      lay(way);
      card.style.left = `${plan.at[0]}px`;
      card.style.top = `${plan.at[1]}px`;
      drawTail(card, [...plan.at, own[2], own[3]], item);
      if (plan.at[0] !== own[0] || plan.at[1] !== own[1]) choices.moved = true;
      for (const old of node.querySelectorAll(".tail")) old.remove();
      node.style.left = `${plan.spot[0]}px`;
      node.style.top = `${plan.spot[1]}px`;
      const { width, height } = node.getBoundingClientRect();
      if (plan.tail) drawTail(node, [...plan.spot, width, height], item);
    };
    // How many of the paragraph's lines show (0: all of it), as a number to compare.
    const seen = (lines) => (lines === 0 ? Infinity : lines);
    setApart(false);
    let planned = search(ways), apart = false;
    // The paragraph in the card where that covers nothing and shows all of
    // it or PARAGRAPH_LINES lines or more; else the choices as they are
    // closed, and the paragraph apart (直し27-3), whichever shows more.
    const inCard = planned && !planned.plan.covered ? seen(planned.way[2]) : -1;
    if (!paragraph.hidden && inCard < PARAGRAPH_LINES) {
      setApart(true);
      const closedPlan = search(closed);
      if (closedPlan) {
        put(closedPlan);
        const lines = putParagraphApart(paragraph, text, lineHeight, frameBox, [...hard, ...seatRoom(frameBox), boxIn(card, frameBox)], others);
        if (lines !== null && seen(lines) > inCard) {
          planned = closedPlan;
          apart = true;
        }
      }
      if (!apart) setApart(false);
    }
    if (planned) {
      if (!apart) put(planned);
      // What they, their paragraph or the moved card cover steps behind while they are open.
      for (const other of shown) {
        if (overlaps(node, other) || overlaps(card, other) || (apart && overlaps(paragraph, other))) other.classList.add("under-choices");
      }
      return;
    }
    // No such spot: the chairs' backs given up (直し29-2; the seats, chairs
    // and the table never), then as before, by the card, over it rather than the table.
    if (withBacks) return putChoices(false);
    setApart(false);
    // No such spot: as before, by the card, over it rather than the table.
    const byOwn = (tried) => {
      let chosen = null;
      for (const overOwn of [false, true]) {
        for (const way of tried) {
          lay(way);
          const { width, height } = node.getBoundingClientRect();
          const [found, clear] = choiceSpot(frameWH, { w: width, h: height }, own, hard, others, overOwn);
          if (!chosen || (clear && !chosen.clear)) chosen = { way, found, clear };
          if (clear) return chosen;
        }
      }
      return chosen;
    };
    const place = ({ way, found }) => {
      lay(way);
      node.style.left = `${found[0]}px`;
      node.style.top = `${found[1]}px`;
    };
    let chosen = byOwn(ways);
    // The paragraph stays in the choices only where that covers none of
    // the table, its seats and chairs, and shows all of it or
    // PARAGRAPH_LINES lines or more; else the choices as they are closed,
    // and the paragraph on paper of its own (直し27-3), whichever shows more.
    const inOwn = chosen.clear ? seen(chosen.way[2]) : -1;
    if (!paragraph.hidden && inOwn < PARAGRAPH_LINES) {
      setApart(true);
      const closedChosen = byOwn(closed);
      place(closedChosen);
      const lines = putParagraphApart(paragraph, text, lineHeight, frameBox, [...hard, ...seatRoom(frameBox), boxIn(card, frameBox)], others);
      if (lines !== null && seen(lines) > inOwn) apart = true;
      else setApart(false);
    }
    // Laid again only when the paragraph is in them (laying sets its lines).
    if (!apart) place(chosen);
    // What it covers steps behind it while it is open (its own card too,
    // when there was no room but over it), and what its paragraph covers.
    for (const other of [...shown, card]) if (overlaps(node, other)) other.classList.add("under-choices");
    if (apart) for (const other of shown) if (overlaps(paragraph, other)) other.classList.add("under-choices");
  }

  // The paragraph apart from its choices (直し27-3), where the map has no
  // room for it in them: on paper of its own, its name at its head, the
  // nearest spot to the choices that covers none of hard (the table, its
  // seats and chairs, the lamp card) nor the choices, and none of soft if
  // it can; all of it, or PARAGRAPH_LINES lines or more, and only failing
  // that fewer (it scrolls), as wide as that takes. Returns the lines it
  // shows (0: all of it), or null when it covers hard wherever it goes.
  function putParagraphApart(paragraph, text, lineHeight, frameBox, hard, soft) {
    const frameWH = { w: frameBox.width, h: frameBox.height }, from = boxIn(paragraph.parentElement, frameBox);
    const covered = ([left, top], { w, h }) => soft.some((b) => boxesMeet([left, top, w, h], b));
    let best = null;
    for (const lines of PARAGRAPH_STEPS) {
      for (const width of [560, 420, 300].filter((w) => w <= frameWH.w - 8)) {
        paragraph.style.width = `${width}px`;
        text.style.maxHeight = lines ? `${Math.ceil(lines * lineHeight) + 1}px` : "";
        const { width: w, height: h } = paragraph.getBoundingClientRect();
        const [spot, clear] = choiceSpot(frameWH, { w, h }, from, hard, soft);
        const way = { lines, width, spot };
        if (clear && !covered(spot, { w, h })) { best = way; break; }
        if (clear && (!best || !best.clear)) best = { ...way, clear };
      }
      if (best && best.clear === undefined) break;
    }
    if (!best) return null;
    paragraph.style.width = `${best.width}px`;
    text.style.maxHeight = best.lines ? `${Math.ceil(best.lines * lineHeight) + 1}px` : "";
    // Inside the choices' border: their box is where it is measured from.
    paragraph.style.left = `${best.spot[0] - from[0] - 1}px`;
    paragraph.style.top = `${best.spot[1] - from[1] - 1}px`;
    return best.lines;
  }

  // Where a lamp card may go while its choices are open (直し27-1), a box
  // { w, h, px, py, gap, r } (its seat's spot px, py) in a frame { w, h }:
  // inside the frame, within reach of its seat and gap from it at the least,
  // covering none of hard, its tail crossing none of block. The spots
  // [left, top, w, h], nearest its own spot (own) first. It reads nothing
  // but what it is given.
  function cardSpots(frame, item, own, hard, block, reach) {
    const { w, h, px, py, gap, r } = item, m = 4, spots = [];
    const away = ([left, top]) => Math.hypot(Math.max(left - px, 0, px - left - w), Math.max(top - py, 0, py - top - h));
    for (let top = py - reach - h; top <= py + reach; top += TABLE_STEP) {
      for (let left = px - reach - w; left <= px + reach; left += TABLE_STEP) {
        const box = [left, top, w, h], far = away(box);
        if (left < m || top < m || left + w > frame.w - m || top + h > frame.h - m) continue;
        if (far > reach || far < gap * 0.9 || hard.some((other) => boxesMeet(box, other))) continue;
        const tail = tailEnds(box, px, py, r);
        if (tail && block.some((other) => crosses(tail[0], tail[1], other))) continue;
        spots.push([Math.hypot(left - own[0], top - own[1]), box]);
      }
    }
    return spots.sort((a, b) => a[0] - b[0]).map(([, box]) => box);
  }

  // Where the choices ({ w, h }) go by their lamp card (直し27-1): against
  // its side (below, above, right or left, TOUCH apart), inside the frame
  // { w, h }, covering none of hard, their tail to the seat (card's px, py,
  // r) crossing neither the card nor block, and the card's own tail not
  // crossing them. The card stays where it is (own) if that covers nothing
  // of soft; else it goes to the nearest of spots (cardSpots) that does;
  // failing that, the one that covers least (a little more for each px it
  // moves). Returns { at, spot, tail, covered, cost } or null when there is none.
  // It reads nothing but what it is given.
  function choicesPlan(frame, card, own, box, hard, block, soft, spots, needTail = true) {
    const { w, h } = box, m = 4;
    const area = (b) => soft.reduce((sum, o) => sum + Math.max(0, Math.min(b[0] + b[2], o[0] + o[2]) - Math.max(b[0], o[0])) *
      Math.max(0, Math.min(b[1] + b[3], o[1] + o[3]) - Math.max(b[1], o[1])), 0);
    const by = (c) => {
      const [l, t, cw, ch] = c, cardTail = tailEnds(c, card.px, card.py, card.r);
      let pick = null;
      for (const [left, top] of [[l, t + ch + TOUCH], [l + cw - w, t + ch + TOUCH], [l, t - h - TOUCH], [l + cw - w, t - h - TOUCH],
        [l + cw + TOUCH, t], [l + cw + TOUCH, t + ch - h], [l - w - TOUCH, t], [l - w - TOUCH, t + ch - h]]) {
        const spot = [left, top, w, h];
        if (left < m || top < m || left + w > frame.w - m || top + h > frame.h - m) continue;
        if (hard.some((other) => boxesMeet(spot, other))) continue;
        // Their tail long enough to see which seat it is (unless needTail
        // is false: then right by the seat will do, with no tail).
        const tail = tailEnds(spot, card.px, card.py, card.r);
        const seen = tail && Math.hypot(tail[1][0] - tail[0][0], tail[1][1] - tail[0][1]) >= TAIL_LENGTH * 0.6;
        if (needTail === true && !seen) continue;
        // With no tail, against the seat's ring but not over it (unless "near").
        if (!seen && needTail !== "near" && Math.hypot(Math.max(left - card.px, 0, card.px - left - w), Math.max(top - card.py, 0, card.py - top - h)) < (card.ring || card.r)) continue;
        if (seen && (crosses(tail[0], tail[1], c) || block.some((other) => crosses(tail[0], tail[1], other)))) continue;
        if (cardTail && crosses(cardTail[0], cardTail[1], spot)) continue;
        const covered = area(spot) + area(c), cost = covered + Math.hypot(l - own[0], t - own[1]) * 10;
        if (!pick || cost < pick.cost) pick = { at: [l, t], spot: [left, top], tail: seen ? tail : null, covered, cost };
      }
      return pick;
    };
    const stay = by(own);
    if (stay && !stay.covered) return stay;
    let least = stay;
    for (const c of spots) {
      const pick = by(c);
      if (!pick) continue;
      if (!pick.covered) return pick;
      if (!least || pick.cost < least.cost) least = pick;
    }
    return least;
  }

  // Where the choices ({ w, h }) go in a frame { w, h }: beside their lamp
  // card (own, [left, top, width, height]) on the right, the left, below or
  // above, the first that covers neither the card (unless overOwn) nor any
  // of hard, and covers least of soft (the other cards and labels); failing that, the
  // free spot nearest the card; with none, the side that covers least.
  // Always inside the frame. Returns [[left, top], whether it covers
  // nothing of the card and hard]. It reads nothing but what it is given.
  function choiceSpot(frame, box, own, hard, soft, overOwn = false, margin = 4) {
    const { w, h } = box, [l, t, ow, oh] = own, gap = 8;
    const clampX = (left) => Math.max(margin, Math.min(left, frame.w - w - margin));
    const clampY = (top) => Math.max(margin, Math.min(top, frame.h - h - margin));
    const area = ([left, top], boxes) => boxes.reduce((sum, [bl, bt, bw, bh]) =>
      sum + Math.max(0, Math.min(left + w, bl + bw) - Math.max(left, bl)) * Math.max(0, Math.min(top + h, bt + bh) - Math.max(top, bt)), 0);
    const must = overOwn ? hard : [own, ...hard];
    const sides = [[l + ow + gap, t], [l - w - gap, t], [l, t + oh + gap], [l, t - h - gap],
      [l + ow + gap, t + oh - h], [l - w - gap, t + oh - h], [l + ow - w, t + oh + gap], [l + ow - w, t - h - gap]]
      .map(([left, top]) => [clampX(left), clampY(top)]);
    let best = sides[0], least = Infinity, clear = null, fewest = Infinity;
    for (const side of sides) {
      const hit = area(side, must), cost = hit * 1000 + area(side, soft);
      if (cost < least) { best = side; least = cost; }
      if (!hit && area(side, soft) < fewest) { clear = side; fewest = area(side, soft); }
    }
    if (clear) return [clear, true];
    const away = ([left, top]) => Math.hypot(Math.max(l - left - w, 0, left - l - ow), Math.max(t - top - h, 0, top - t - oh));
    let free = null, far = Infinity;
    for (let top = margin; top <= frame.h - h - margin; top += 8) {
      for (let left = margin; left <= frame.w - w - margin; left += 8) {
        const spot = [left, top];
        if (area(spot, must)) continue;
        const d = away(spot) + area(spot, soft) / 100;
        if (d < far) { free = spot; far = d; }
      }
    }
    return free ? [free, true] : [best, false];
  }

  // Which lamp cards are marked (app.js keeps the marks), and the choice
  // that says so. Called whenever a mark changes, from here or below.
  function marked() {
    if (!overlay) return;
    const marks = app.state.marks;
    for (const card of overlay.querySelectorAll(".table-bubble")) {
      card.classList.toggle("marked", marks[card.dataset.seat] === card.dataset.utterance);
    }
    if (!choices) return;
    const mark = choices.node.querySelector('[data-choice="mark"]');
    if (mark) mark.setAttribute("aria-pressed", String(marks[choices.seatId] === choices.card.dataset.utterance));
  }

  // The line by the map's lower edge once the table is open, until a lamp
  // card is first pressed (the teacher's words: texts/bubble_hint.txt).
  function dropHint() {
    pressedOnce = true;
    for (const node of overlay.querySelectorAll(".map-hint")) node.remove();
  }

  // A seat's picture at the table (直し29-3): 探究をした先輩 a magnifier, 県外・
  // 海外に出た人 an aeroplane; 地域で働く大人 and 外から来た大人・先生 by their
  // title, the first row of texts/seat_icons.tsv (table: [[言葉, 絵], ...])
  // whose word is in it; none, null. It reads nothing but what it is given.
  function seatIcon(kind, title, table) {
    if (kind === "poster") return "poster";
    if (kind === "cross") return "cross";
    if (kind !== "adult" && kind !== "outsider_teacher") return null;
    const row = table.find(([word]) => word && (title || "").includes(word));
    return row && SEAT_ICON_PATHS[row[1]] ? row[1] : null;
  }

  // A chair's back (直し29-2), round a seat's spot at (at): on the side away
  // from the table's middle, across that way, r from the spot.
  function chairBack(at, middle, r, className) {
    const a = Math.atan2(at[1] - middle[1], at[0] - middle[0]) * 180 / Math.PI;
    return svgEl("rect", { class: className, x: -r * 0.85, y: -r - 9, width: r * 1.7, height: 7, rx: 3.5,
      transform: `rotate(${a + 90})` });
  }

  // An empty chair 「？」: a seat nobody asked yet, the same chair in a dotted
  // line (直し29-2). Pressing it (or Enter or Space on it) opens the same
  // 「聞きたいことを書く」 as the seat list.
  function chair(seatId, at, middle) {
    const seat = seatOf(seatId);
    const node = svgEl("g", { class: "chair", tabindex: 0, role: "button",
      "aria-label": [seat.title, app.state.texts.not_asked_yet].join("　") });
    node.append(svgEl("rect", { class: "hit" }), chairBack(at, middle, CHAIR_R, "back"), svgEl("circle", { r: CHAIR_R }));
    const mark = svgEl("text", { y: 5.5, "text-anchor": "middle" });
    mark.textContent = "？";
    node.append(mark);
    pressable(node, () => press(seatId, node));
    tableLayer.append(node);
    const token = { node, at, scale: 1.2, id: seatId, chair: true };
    tokens.push(token);
    return Promise.resolve(token);
  }

  function clearTable() {
    tokens = [];
    tableTop = null;
    tableAt = null;
    opened = null;
    closeChoices(false);
    if ($("map-heading")) $("map-heading").replaceChildren();
    if (tableLayer) tableLayer.replaceChildren();
    if (svg) svg.classList.remove("dim");
    for (const { node } of Object.values(points)) node.setAttribute("tabindex", "0");
    if ($("map-back")) $("map-back").hidden = true;
  }

  // 「地図にもどす」: the table goes, the camera goes back to the whole map
  // (at once when motion is reduced). The lit seats and the marks stay.
  function closeTable() {
    roundNo += 1;
    for (const flight of flights) flight.cancel();
    flights = [];
    for (const node of overlay.querySelectorAll(".split-tag, .table-label, .map-bubble, .table-bubble, .seat-press, .map-hint")) node.remove();
    clearTable();
    $("map-zoom-all").focus();
    moveTo({ x: 0, y: 0, w: view.W, h: view.H }, BACK_FOR);
  }

  // --- marks that stay: met seats, and 「？」 on seats nobody asked yet ---

  function refresh() {
    if (!map || !view) return;
    for (const [id, { node }] of Object.entries(points)) {
      node.classList.toggle("met", app.state.met.has(id));
      node.classList.toggle("silent", isSilent(id));
      const seat = seatOf(id);
      const words = [seat.title, seat.detail, isSilent(id) ? app.state.texts.not_asked_yet : ""];
      node.setAttribute("aria-label", words.filter(Boolean).join("　"));
    }
    $("map-met-count").textContent = String(app.state.met.size);
    placeAskMarks();
  }

  // Pressing a 「？」 opens the same 「聞きたいことを書く」 as the seat list.
  // Pressing any other point keeps its label shown.
  function press(seatId, from) {
    if (!isSilent(seatId)) {
      sticky = seatId;
      showTip(seatId);
      return;
    }
    returnFocus = from;
    const seat = seatOf(seatId);
    card.replaceChildren(div("title", seat.title), div("not-asked", app.state.texts.not_asked_yet));
    const close = document.createElement("button");
    close.type = "button";
    close.className = "quiet close";
    close.textContent = "閉じる";
    close.addEventListener("click", () => {
      card.hidden = true;
      if (returnFocus && returnFocus.isConnected) returnFocus.focus();
    });
    if (app.state.carded.has(seatId)) {
      card.append(app.cardDone(seatId));
    } else {
      const open = app.cardEntry(seatId, (form) => {
        form.replaceWith(app.cardDone(seatId));
        app.renderSeats();
      });
      card.append(open);
      card.hidden = false;
      open.click();  // Opens the box at once, as the list's button does.
    }
    card.append(close);
    card.hidden = false;
    card.scrollIntoView({ block: "nearest" });
  }

  // A seat kind's mark as on the map, small, for the counts over the
  // question box (直し31-5): the same shape and colour as its points.
  function markOf(kind) {
    const mark = document.createElementNS(NS, "svg");
    mark.setAttribute("viewBox", "-11 -11 22 22");
    mark.setAttribute("class", `pt-mark kind-${kind}`);
    mark.setAttribute("aria-hidden", "true");
    mark.setAttribute("focusable", "false");
    mark.append(shape(kind));
    return mark;
  }

  return { init, show, round, refresh, marked, band: setBand, markOf };
})();
