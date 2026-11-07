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
  const LIGHT_EVERY = 250;  // ms between two seats lighting up (直し31-6: was 400).
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
  // 直し41: before the first question, now and then one point (two at most)
  // glows softly and goes back, QUIET_FOR ms each, QUIET_GAP ms apart at
  // random: people in the basin, not a call to press. Never with motion reduced.
  const QUIET_FOR = 2 * 1000, QUIET_GAP = [1400, 3800], QUIET_MAX = 2;
  const PRESS_RING_FOR = 400;  // ms of the small ring a point sends out when pressed.
  const FADE_FOR = 300;  // ms a card takes to go, at the end of its BUBBLE_FOR.
  // The round table (the picture only): round the basin's middle, flat at
  // the height of the ground there, in map units.
  const TABLE_RX = 150, TABLE_RY = 110, TABLE_LIFT = 7, SEAT_OUT = 48;
  const TABLE_THICK = 9;  // The top's thickness: its side shows in front (直し29-2).
  // The gathering (直し33-4): the table is no longer on the basin. Its middle
  // is where the map meets the school (upright: between the two), flat, seen
  // a little from above (TABLE_TILT); its top TABLE_PX CSS px from its middle
  // to its side (this part of the room, within TABLE_PX_MOST), so the seats
  // that spoke gather round it wherever they live and their cards have the
  // room round it.
  const TABLE_TILT = 0.55, TABLE_PART = 0.075, TABLE_PX_MOST = [54, 96];
  // The seats that spoke sit where their cards have room (直し33-4): in two
  // columns, left and right of the table, a card's height apart, each at
  // the inner edge of where its card goes. GATHER_CARD: the CSS px a card
  // takes at the table (style.css: two lines of words, whose under them),
  // and the gap between two. On a wide screen the right column stays over
  // the room the AI's seat takes under the school (AI_ROOM of the height).
  const GATHER_CARD = { w: 236, h: 112, gap: 10 }, AI_ROOM = 0.45;
  // The meeting (直し35-3): the school rises from its place on the map to the
  // middle, its picture RISE_PART of the map's height (upright: RISE_PART_UP
  // of the width) at the least, in RISE_FOR ms; the seats sit round its ring
  // (RING_R_M metres across its half, the picture's north-south at
  // PICTURE_TILT of its east-west).
  const RISE_PART = 0.62, RISE_PART_UP = 0.82, RISE_FOR = 700, RING_R_M = 40.35, PICTURE_TILT = 0.788;
  // Quicker since 直し31-6 (were 1100, 1100, 160): the table is there sooner.
  const CAMERA_FOR = 700, FLY_FOR = 700, FLY_GAP = 90, BACK_FOR = 700;
  const CLOSEST = 3.5;  // The nearest zoom shows this part of the whole across.
  const ZOOM_STEP = 1.4;
  const POINT_R = 7.5;  // A point's radius at scale 1 (see shape()).
  const MIN_POINT_PX = 3;  // A point is never smaller than this on screen.
  // 直し41: a point is drawn at least this big (its radius, CSS px), so the
  // whole map shows people, not grains. Drawn only: where the points go
  // (homePlace), what takes a press (HIT_PX) and the seniors are as before.
  const MIN_DRAWN_PX = 6.5;
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
  const TEXT_PX = { place: 11, school: 12, home: 12 };
  // The seats' homes (直し35-2): 地域で働く大人 at their places on the map
  // (those with no place, together where the map is free); 県外・海外に出た人
  // at a way out on the map's edge, to 県外 by the north side, to
  // 海外 by the south, beside the arrow going out, GATE_COLUMNS to a row;
  // 外から来た大人・先生 at the way to 県外, beside the arrow coming in;
  // 探究をした先輩 at the school's windows, more than those on rows past them.
  // HOME_STEP CSS px between two side by side at the whole map.
  const HOME_STEP = 16, GATE_COLUMNS = 5;
  // The school's name never over SCHOOL_TEXT_MAX_PX on screen.
  const SCHOOL_TEXT_MAX_PX = 24;
  // The one drawing (直し35-2): the map alone, as large as the room lets it
  // be, in its middle (the school is on it, put larger: SCHOOL_SCALE).
  const AI_BAND_UP = 0.3;  // Upright: the AI's seat this part of the room's height, under the map.
  const UPRIGHT_UNDER = 1.4;  // A room narrower than this (width to height) is upright.
  // The school put larger on the map (直し37-1: 大きめに置いた校舎, SCHOOL_SCALE
  // times its real size; at its real size, 直し35-2, it was a few pixels
  // across at the whole map, and its seniors came out only 110 to 220 times
  // nearer, where the relief is a grey blur). The one scale for the picture,
  // its windows and the rows past them, the school rising
  // at the meeting and one to one at its windows. 22: at the whole map the
  // picture (with its ground, before 直し39) is about 0.18 of the map's shorter side (at most 0.2), and its
  // seniors come out within 4 to 8 times (at most 10), 4 to 6 presses of ＋
  // (3 to 6 asked), at the five sizes. The map's metres to a unit (the relief's
  // own, else this), the plain school's units to a metre (the ground it had
  // was the model's 96.2 m across in 520) and the ring's middle on it.
  const SCHOOL_SCALE = 22;
  const M_PER_UNIT = 33.4225;
  const PLAIN_PX_PER_M = 520 / 96.2, PLAIN_RING = [380, 60];
  // The school without its sports ground (直し39, 先生「円卓として校舎が出て
  // くるときに、グラウンドは不要」): the picture shown from CUT_GAP_M metres
  // east of its ground's east side (field_px's two east corners) on, the
  // ground, track, lanes and lines west of that left out; the plain one has
  // none. Past the windows the seniors go on rows outward (seniorRows), kept
  // RING_MARGIN window steps inside the part shown.
  const CUT_GAP_M = 3, RING_MARGIN = 2;
  // A seat at the school (a window, the track) never more than SCHOOL_R_PX
  // across its half on screen; the seniors show at their windows once the
  // windows are that far apart on screen (twice it), and the nearest zoom is
  // CLOSEST_MORE times nearer than that. Points never over MAX_POINT_PX.
  const SCHOOL_R_PX = 5, CLOSEST_MORE = 1.6, MAX_POINT_PX = 10;
  // A window or spot this many window steps from an adult's point is passed
  // over (直し37-1), so no senior sits on it; and (直し40-0) edge to edge
  // they are EDGE_GAP_PX apart on screen or more: a lit point reaches
  // POINT_REACH_PX from its middle (its circle, 10px at most, and stroke), a
  // senior SENIOR_REACH_PX, and the windows are 2 * SCHOOL_R_PX apart when
  // the seniors come out (nearer, further). (11.2 + 5.3 + 4) / 10 = 2.05.
  const EDGE_GAP_PX = 4, POINT_REACH_PX = 11.2, SENIOR_REACH_PX = 5.3;
  const SCHOOL_CLEAR = 2.05;
  // The AI's seat in a corner of the map (直し35-2), tried in this order.
  const AI_CORNERS = ["bottom-right", "bottom-left", "top-left"];
  const RECOMPOSE = 0.03;  // The room's shape this much off the drawing's: it is drawn again.
  // With no picture of the school (直し33-2): a plain building (no site, 直し44),
  // no name, in its own units; its windows (two rows on the building's
  // front, the lower first as the picture's inner row: rows past them go up
  // over the roof) are where seats go, as on the picture. No ground, no
  // track (直し39); rise: its size as it was with them, for the meeting.
  const PLAIN_YARD = { width: 760, height: 480, roof: [[40, 60], [720, 60], [720, 310], [40, 310]], wall: 110,
    rows: [385, 335], columns: 20, rise: [1400, 760] };
  const WORD_PAD = 2;  // CSS px kept clear round a word drawn on the map.
  const SLIDE_MOST = 40;  // CSS px the school's name may slide off a seat's point.
  const NAME_MOVE_MOST = 36;  // CSS px a place name may move off the seats' points (直し41の続き).
  // 直し41の続き 段4: under the picture, the same picture mirrored, blurred
  // and darkened (tools/make_relief_blur.py), three times as wide and as
  // tall, the picture in its middle: no empty black in the frame.
  const BLUR_IMAGE = "/relief_blur.webp";
  // The map's seasons (the teacher, 11/6): which one opens by the month
  // (3-5 spring, 9-11 autumn, else the night), when its picture is there.
  const SEASON_MONTHS = { spring: [3, 4, 5], autumn: [9, 10, 11] };
  const LOOK_FADE = 1600;  // ms for the next scenery to melt in (直し48 段6).
  // Where the picture melts into it ([where, shown]): its see-through or
  // black margin hidden, the land shown a little further in.
  const RELIEF_FADE_X = [[0, 0], [0.016, 0], [0.04, 1], [0.96, 1], [0.984, 0], [1, 0]];
  const RELIEF_FADE_Y = [[0, 0], [0.05, 0], [0.085, 1], [0.9, 1], [0.935, 0], [1, 0]];
  // The whole map (「全体」, the first screen): the basin's rim this much of
  // the frame's height, every seat's home (the ways out's triangles among
  // them) kept inside by WHOLE_EDGE of the height, which comes first.
  const RIM_SHARE = 0.85;
  const WHOLE_EDGE = 0.015;  // Of the frame's height, between the frame's edge and a home or its name.
  // Where a seat's 「？」 may go, by its point (x, y, which way the text runs
  // from there), in the order tried: upper right first.
  const ASK_CORNERS = [[9, -6, "start"], [-9, -6, "end"], [9, 16, "start"], [-9, 16, "end"]];

  let map = null;  // The drawing from /api/setup.
  let app = null;  // What app.js lends: state, cardEntry, renderSeats, shownQuotes.
  let svg, overlay, frame;
  let lastSeats = [];  // The seats as last drawn, to draw them again (直し33-2).
  let yardPicture = null;  // The school's large picture once it has loaded (直し33-2).
  let view = null;  // How the map's (x, y) reach the drawing (flatView, reliefView).
  let look = null;  // The picture shown, night or a season: { id, image, blur }.
  let lookNodes = null;  // The picture's and the ground's <image>, to switch them.
  let vb = null;  // The part of the drawing on screen.
  let splitLayer, tableLayer, schoolGroup = null;
  const points = {};  // Seat ID -> { node, seat, at() }.
  let tokens = [];  // Seats and empty chairs at the table: { node, at, scale }.
  let timers = [], flights = [];
  let sticky = null;  // The seat whose label stays (the last to light up).
  let drawn = false, wantShow = false, pending = null;
  let camera = null, roundNo = 0, returnFocus = null;
  let tableTop = null;  // The round table's top, a ring of spots of the drawing, while it is open.
  let roundSeats = [];  // The seats this round lights, in order.
  let splitsDrawn = null;  // The round whose splits are on the flat map (直し40-1: drawn again with the map).
  let soon = null;
  let hovered = null;  // The seat under the mouse (the nearest of the marks it is over).
  let opened = null;  // At the table, the seat whose card was left out and is shown, pressed.
  let choices = null;  // The card of choices open at the table: { seatId, node, card }.
  let pressedOnce = false;  // A card was pressed: the line that says so goes, for good.
  let tableRoundNo = 0;  // The round the table is for.
  let tableAt = null;  // The table open: { center, angles, split }, for the band's seats.
  let tableOf = null;  // The round the table is open for, to open it again laid out afresh (直し33-4).
  let playing = false;  // A round's seats lighting or gathering: not drawn again meanwhile.

  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);
  const wait = (ms) => new Promise((done) => timers.push(setTimeout(done, ms)));

  // The quiet glow (直し41). pick() gives the points that may glow now. rng,
  // later and cancel can be given (the tests do). Motion reduced: no timer at
  // all. Returns what stops it, the glow on any point taken off.
  function quietGlow(pick, { rng = Math.random, later = setTimeout, cancel = clearTimeout, reduce = reduced } = {}) {
    if (reduce()) return () => {};
    let timer = null, on = true;
    const glowing = new Set();
    const wait = () => QUIET_GAP[0] + rng() * (QUIET_GAP[1] - QUIET_GAP[0]);
    const step = () => {
      if (!on) return;
      const free = pick().filter((node) => !glowing.has(node));
      if (free.length && glowing.size < QUIET_MAX) {
        const node = free[Math.min(free.length - 1, Math.floor(rng() * free.length))];
        glowing.add(node);
        node.classList.add("quiet-glow");
        later(() => { node.classList.remove("quiet-glow"); glowing.delete(node); }, QUIET_FOR);
      }
      timer = later(step, wait());
    };
    timer = later(step, wait());
    return () => {
      on = false;
      cancel(timer);
      for (const node of glowing) node.classList.remove("quiet-glow");
      glowing.clear();
    };
  }

  // A point pressed (直し41): one small ring goes out and is gone. Not with motion reduced.
  function pressRing(node) {
    if (reduced() || !node || !node.animate) return;
    const ring = svgEl("circle", { class: "ripple press-ring", r: 10 });
    node.append(ring);
    const wave = ring.animate([{ transform: "scale(1)", opacity: 0.85 }, { transform: "scale(2.2)", opacity: 0 }],
      { duration: PRESS_RING_FOR, easing: "ease-out" });
    wave.finished.then(() => ring.remove(), () => ring.remove());
  }

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
    look = map.relief ? startLook() : null;
    controls();
    const go = () => {
      if (!map.relief) return build(seats, false);
      // A season's picture that will not load: the night's; the night's
      // that will not: the flat map.
      const night = looksOf()[0];
      const tryLook = (one) => {
        const picture = new Image();
        picture.onload = () => { showLook(one.id); build(seats, true); };
        picture.onerror = () => (one === night ? build(seats, false) : tryLook(night));
        picture.src = one.image;
      };
      tryLook(look);
    };
    // The school's large picture first (直し33-2): the seats on it are put
    // from it. Not loaded (none, or it fails): the plain yard.
    const yard = map.school_picture && map.school_picture.yard;
    if (!yard) return go();
    const image = new Image();
    image.onload = () => { yardPicture = yard; go(); };
    image.onerror = go;
    image.src = yard.image;
  }

  // The yard as drawn: the picture's size and where its seats go, or the
  // plain one's, in its own units; board: the part shown, its corners
  // (north-west, north-east, south-east, south-west).
  function yardModel() {
    if (yardPicture) return cutYard(yardPicture);
    const { width, height, roof, wall, rows, columns, rise } = PLAIN_YARD;
    const [left, right] = [roof[0][0] + 24, roof[1][0] - 24];
    const windows = rows.flatMap((y) => Array.from({ length: columns },
      (_, k) => [left + (right - left) * k / (columns - 1), y]));
    const [[x0, y0], , [x1, y1]] = roof;
    const board = [[x0 - 24, y0 - 24], [x1 + 24, y0 - 24], [x1 + 24, y1 + wall + 24], [x0 - 24, y1 + wall + 24]];
    return { picture: false, width, height, roof, windows, board, ring: PLAIN_RING, pxPerM: PLAIN_PX_PER_M, rise };
  }

  // The picture without its ground (直し39): its ground's east side (field:
  // north-west, north-east, south-east, south-west) CUT_GAP_M metres east,
  // run to the picture's top and foot, and only what is east of that shown.
  // In the part shown's own px, its left at 0: the picture at imageX, the
  // part shown (board), the windows and the ring's middle; rise: the
  // picture's whole size, for the meeting. Never over a
  // window or the ring's middle (the cut kept gap west of them). The file is
  // as it was. It reads nothing but what it is given.
  function cutYard(p) {
    const [, ne, se] = p.field, gap = CUT_GAP_M * p.px_per_m;
    const most = Math.min(...p.windows.map((w) => w[0]), p.ring[0]) - gap;
    const xAt = (y) => Math.max(0, Math.min(ne[0] + (se[0] - ne[0]) * (y - ne[1]) / ((se[1] - ne[1]) || 1) + gap, most));
    const top = xAt(0), foot = xAt(p.height), left = Math.min(top, foot);
    const shift = ([x, y]) => [Math.round((x - left) * 100) / 100, y];
    const board = [[top, 0], [p.width, 0], [p.width, p.height], [foot, p.height]].map(shift);
    return { picture: true, image: p.image, imageX: -left, imageW: p.width, width: p.width - left, height: p.height,
      board, windows: p.windows.map(shift), ring: shift(p.ring), pxPerM: p.px_per_m, rise: [p.width, p.height] };
  }

  // The room the drawing has on screen (the map's room), or a guess from
  // the window before it is on screen.
  function roomSize() {
    const room = frame.parentElement;
    if (room && room.clientWidth > 80 && room.clientHeight > 80) return { w: room.clientWidth, h: room.clientHeight };
    const upright = window.innerHeight > window.innerWidth * 0.9;
    return upright ? { w: window.innerWidth - 32, h: Math.max(300, window.innerHeight - 380) }
      : { w: Math.max(400, window.innerWidth - 260), h: Math.max(240, window.innerHeight - 220) };
  }

  // Where the map (mapW x mapH, kept in its own units) goes in a room ({ w,
  // h } CSS px), 直し35-2: as large as the room lets it be, in its middle;
  // upright, at the top, the room's foot (AI_BAND_UP of it) left for the
  // AI's seat. The drawing's size W x H (the room's shape) and the map's
  // corner. It reads nothing but what it is given.
  function compose(room, mapW, mapH) {
    const upright = room.w / room.h < UPRIGHT_UNDER;
    const tall = upright ? room.h * (1 - AI_BAND_UP) : room.h;
    const u = Math.max(mapW / room.w, mapH / tall);  // The drawing's units to a CSS px.
    const W = room.w * u, H = room.h * u;
    return { W, H, upright, map: [(W - mapW) / 2, upright ? 0 : (H - mapH) / 2] };
  }

  // The school put larger on the map (直し37-1, 大きめに置いた校舎、倍率
  // SCHOOL_SCALE): its picture's (or the plain one's) ring's middle on the
  // school's point, its metres SCHOOL_SCALE times the map's (unitsPerM: the
  // drawing's units to a metre across). Returns the picture's corner and its
  // scale. It reads nothing but what it is given.
  function schoolOnMap([px, py], model, unitsPerM) {
    const k = SCHOOL_SCALE * unitsPerM / model.pxPerM;
    return { x: px - model.ring[0] * k, y: py - model.ring[1] * k, k };
  }

  // How far apart the school's windows are, at the least (the drawing's units).
  function windowStep(windows) {
    let least = Infinity;
    windows.forEach(([x, y], i) => windows.slice(i + 1).forEach(([u, v]) => { least = Math.min(least, Math.hypot(u - x, v - y)); }));
    return least;
  }

  function build(seats, withRelief) {
    lastSeats = seats;
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

  // whole: the camera at the whole map after (else at the whole drawing, as
  // a meeting drawn again wants it).
  function draw(seats, withRelief, whole = true) {
    svg.replaceChildren();
    overlay.replaceChildren();
    for (const old of frame.querySelectorAll(".school-count")) old.remove();
    for (const id of Object.keys(points)) delete points[id];
    tokens = [];
    schoolGroup = null;
    const base = withRelief ? reliefView(map.relief) : flatView();
    const model = yardModel();
    const room = roomSize();
    const laid = compose(room, base.W, base.H);
    const [ox, oy] = laid.map;
    const proj = (...at) => {
      const [x, y] = base.proj(...at);
      return [x + ox, y + oy];
    };
    // The school put larger where it is on the map (直し37-1, SCHOOL_SCALE).
    const mPerUnit = (map.relief && map.relief.z && map.relief.z.m_per_unit) || M_PER_UNIT;
    const schoolAt = map.school ? proj(map.school.x, map.school.y, 0) : [ox + base.W / 2, oy + base.H / 2];
    const yard = { ...schoolOnMap(schoolAt, model, base.S / mPerUnit), model };
    const unit = laid.W / room.w;
    // The seniors come out at their windows from this zoom on; the nearest
    // zoom a little nearer than that, never less near than CLOSEST.
    const seniorStep = windowStep(model.windows) * yard.k;
    const seniorZoom = unit * 2 * SCHOOL_R_PX / seniorStep;
    view = { ...base, W: laid.W, H: laid.H, upright: laid.upright, yard, unit, proj,
      mapBox: [ox, oy, base.W, base.H], mPerUnit, seniorStep, seniorZoom,
      closest: Math.max(CLOSEST, seniorZoom * CLOSEST_MORE) };
    vb = { x: 0, y: 0, w: view.W, h: view.H };
    svg.setAttribute("viewBox", `0 0 ${view.W} ${view.H}`);
    frame.classList.toggle("relief", view.relief);
    $("map").style.setProperty("--ratio", String(view.W / view.H));
    // The map's shape for what sits beside it on the one screen (直し32-1).
    document.documentElement.style.setProperty("--map-ratio", String(view.W / view.H));
    frame.style.aspectRatio = `${view.W} / ${view.H}`;
    const rc = rough.svg(svg);
    const layer = (className) => svg.appendChild(svgEl("g", { class: className }));
    const P = view.proj, S = view.S;
    // Colours come from style.css (a CSS rule beats rough's attributes). No
    // fill option: rough would hatch the inside.
    const ink = { stroke: "#000", seed: 7 };
    drawGlows();

    if (view.relief) {
      const blur = layer("relief-blur");
      const ground = svgEl("image", { href: look.blur, x: ox - base.W, y: oy - base.H, width: 3 * base.W, height: 3 * base.H,
        preserveAspectRatio: "none" });
      blur.append(ground);
      const image = layer("relief-image");
      // Its edges (the render's margin, see-through or black) melt into the
      // ground under it: two still masks, across and down (no blur here).
      const defs = svgEl("defs", {});
      const fade = (id, across, stops) => {
        const ramp = svgEl("linearGradient", { id: `${id}-ramp`, x1: 0, y1: 0, x2: across ? 1 : 0, y2: across ? 0 : 1 });
        for (const [at, on] of stops) ramp.append(svgEl("stop", { offset: at, "stop-color": on ? "#fff" : "#000" }));
        const mask = svgEl("mask", { id, maskContentUnits: "objectBoundingBox" });
        mask.append(svgEl("rect", { width: 1, height: 1, fill: `url(#${id}-ramp)` }));
        defs.append(ramp, mask);
      };
      fade("relief-fade-x", true, RELIEF_FADE_X);
      fade("relief-fade-y", false, RELIEF_FADE_Y);
      image.append(defs);
      const faded = svgEl("g", { mask: "url(#relief-fade-y)" });
      const picture = svgEl("image", { href: look.image, x: ox, y: oy, width: base.W, height: base.H, mask: "url(#relief-fade-x)" });
      faded.append(picture);
      image.append(faded);
      lookNodes = { picture, ground };
      // 直し48 段6: spring's flowers, over the picture, under everything else.
      drawFlowers(layer("spring-flowers"));
    }
    $("map-season").hidden = !view.relief || looksOf().length < 2;
    const fill = layer("basin-fill");
    const rimLine = view.relief ? dense(map.boundary, true).map(([x, y]) => P(x, y, 1)) : map.boundary.map(([x, y]) => P(x, y));
    fill.append(svgEl("polygon", { points: rimLine.map((p) => p.join(",")).join(" ") }));
    view.rimBox = [Math.min(...rimLine.map((p) => p[0])), Math.min(...rimLine.map((p) => p[1])),
      Math.max(...rimLine.map((p) => p[0])), Math.max(...rimLine.map((p) => p[1]))];

    const river = layer("river draw-later");
    for (const line of map.river) {
      const shown = view.relief ? dense(line, false).map(([x, y]) => P(x, y, 0.5)) : line.map(([x, y]) => P(x, y));
      river.append(rc.linearPath(shown, { ...ink, strokeWidth: 3 * S, roughness: 0.9, bowing: 0.6 }));
    }
    const rim = layer("rim draw-first");
    rim.append(rc.polygon(rimLine, { ...ink, strokeWidth: 2.2 * S, roughness: 1.3, bowing: 0.8 }));

    if (map.crossing) {
      const line = layer("crossing");
      const [from, to] = [map.crossing.from, map.crossing.to].map(([x, y]) => P(x, y, 1));
      line.append(rc.line(...from, ...to, { ...ink, strokeWidth: 2 * S, roughness: 1.1 }));
      line.append(svgEl("circle", { cx: from[0], cy: from[1], r: 5 * S }));
    }

    // The school and its ground on the map, put larger (直し37-1, SCHOOL_SCALE),
    // under the seats' points and the place names.
    drawYard(layer("yard"));
    splitLayer = layer("split-lines");
    // Each seat at its home (直し33-3), worked out from the seat table each
    // time it is drawn: 地域で働く大人 at their places, the others by the way
    // out, at the school's windows and on its ground (homesOf).
    const placed = seats.filter((seat) => seat.x !== undefined);
    const homes = homesOf(placed.map((seat) => ({ id: seat.seat_id, kind: seat.kind, abroad: Boolean(seat.abroad),
      at: seat.outer ? null : view.relief ? P(seat.x, seat.y, 1.5) : P(seat.x, seat.y) })), homePlace());
    view.homes = homes;
    drawGates(layer("home-gate"), homes.gates, homes.used);
    const seatLayer = layer("points");
    for (const seat of placed) {
      const node = drawPoint(seat);
      const spot = homes.spots[seat.seat_id];
      // At the school: small, and folded into its count until there is room (直し35-2).
      if (homes.school.has(seat.seat_id)) node.classList.add("school-home");
      // A seat with no place on the map: its point's line dotted.
      if (homes.noPlace.has(seat.seat_id)) node.classList.add("no-place");
      points[seat.seat_id] = { node, seat, at: () => spot };
      seatLayer.append(node);
    }
    // Each home's name where it is, in the words of the seat list's headings
    // (in place of the map's four corners' boxes).
    const homeNames = layer("home-names");
    for (const { kind, at, anchor, school } of homes.names) {
      const words = app.state.kinds[kind];
      if (!words) continue;
      const text = svgEl("text", { class: `kind-${kind}${school ? " at-school" : ""}`, x: at[0], y: at[1], "text-anchor": anchor,
        "data-px": TEXT_PX.home });
      text.textContent = words;
      homeNames.append(text);
    }
    // Over the points, outlined, so a point never hides a place name.
    const names = layer("place-names");
    for (const place of map.places) {
      const [x, y] = P(place.x, place.y, 2);
      const text = svgEl("text", { x, y, "text-anchor": "middle", "data-px": TEXT_PX.place });
      text.textContent = place.name;
      names.append(text);
    }
    // Over the points so its label reads; it takes no presses (not a seat).
    if (map.school) drawSchool(layer("school"), map.school);
    tableLayer = layer("table");
    drawAround();
    drawSchoolCount(homes);

    $("map-source").textContent = map.source;
    $("map-dem").textContent = view.relief ? map.relief.source : "";
    $("map-dem").hidden = !view.relief;
    $("map").hidden = false;
    watchSize();
    // Twice: the names' size on screen is set by the camera, so the whole
    // map is found again once the camera is there.
    const full = { ...vb };
    view.whole = wholeView();
    setView(view.whole, false);
    view.whole = wholeView();
    setView(whole ? view.whole : full);
    refresh();
  }

  // The whole map (直し41の続き 段4): the basin's rim RIM_SHARE of the
  // frame's height, round its middle; every seat's home (the triangles of
  // the ways out, the people from outside) kept inside, WHOLE_EDGE of the
  // height from the frame's edges, before the rim's share. Never past the
  // drawing (the blurred ground). It reads view and the points.
  function wholeView() {
    const rim = view.rimBox;
    if (!rim) return { x: 0, y: 0, w: view.W, h: view.H };
    const keep = [...rim];
    const r = drawnScale() * POINT_R * 1.3;  // A point as large as it is drawn, its ring too.
    for (const { at, node } of Object.values(points)) {
      if (node.classList.contains("school-home")) continue;  // At the school: seen only near it.
      const [x, y] = at();
      keep[0] = Math.min(keep[0], x - r);
      keep[1] = Math.min(keep[1], y - r);
      keep[2] = Math.max(keep[2], x + r);
      keep[3] = Math.max(keep[3], y + r);
    }
    // The homes' names by them (県外・海外に出た人 and the others), as large as
    // they are drawn now.
    for (const text of svg.querySelectorAll(".home-names text:not(.at-school)")) {
      const b = text.getBBox();
      if (!b.width) continue;
      keep[0] = Math.min(keep[0], b.x);
      keep[1] = Math.min(keep[1], b.y);
      keep[2] = Math.max(keep[2], b.x + b.width);
      keep[3] = Math.max(keep[3], b.y + b.height);
    }
    const ratio = view.W / view.H, room = 1 - 2 * WHOLE_EDGE;
    const h = Math.min(view.H, Math.max((rim[3] - rim[1]) / RIM_SHARE, (keep[3] - keep[1]) / room,
      (keep[2] - keep[0]) / (room * ratio)));
    const w = h * ratio, edge = WHOLE_EDGE * h;
    const fit = (lo, hi, size, total) => {
      const at = Math.min(Math.max((lo + hi) / 2 - size / 2, hi + edge - size), lo - edge);
      return Math.min(Math.max(0, at), total - size);
    };
    return { x: fit(keep[0], keep[2], w, view.W), y: fit(keep[1], keep[3], h, view.H), w, h };
  }

  // The school and its ground (直し33-2), in the yard's own units scaled to
  // its place: the picture (from outside the repo), or with none a plain
  // building and a ground with no name. They take no presses.
  function drawYard(group) {
    const { x, y, k, model } = view.yard;
    group.setAttribute("transform", `translate(${x} ${y}) scale(${k})`);
    group.setAttribute("aria-hidden", "true");
    const building = svgEl("g", { class: "yard-building" });
    // Where the paper plane lands (直し33-2): the middle of the school's
    // windows, on the building, not the ground beside it.
    const xs = model.windows.map((p) => p[0]), ys = model.windows.map((p) => p[1]);
    group.append(svgEl("circle", { class: "yard-landing", r: 1,
      cx: (Math.min(...xs) + Math.max(...xs)) / 2, cy: (Math.min(...ys) + Math.max(...ys)) / 2 }));
    const polygon = (className, spots) => svgEl("polygon", { class: className, points: spots.map((p) => p.join(",")).join(" ") });
    if (model.picture) {
      // Only the part east of the cut (直し39): the picture fills the part
      // shown, so the building's box is that part, not the whole picture.
      const fill = svgEl("pattern", { id: "yard-picture", patternUnits: "userSpaceOnUse", x: model.imageX, y: 0,
        width: model.imageW, height: model.height });
      fill.append(svgEl("image", { href: model.image, width: model.imageW, height: model.height }));
      svg.querySelector("defs").append(fill);
      const shown = polygon("yard-picture", model.board);
      shown.setAttribute("fill", "url(#yard-picture)");
      building.append(shown);
      group.append(building);
      return;
    }
    group.classList.add("plain");
    const [nw, ne, se, sw] = model.roof, wall = PLAIN_YARD.wall;
    // No site under the building (直し44), as on the picture: the building
    // stands on the map, not on a board; no ground (直し39).
    building.append(polygon("yard-wall", [sw, se, [se[0], se[1] + wall], [sw[0], sw[1] + wall]]), polygon("yard-roof", [nw, ne, se, sw]));
    for (const [wx, wy] of model.windows) {
      building.append(svgEl("rect", { class: "yard-window", x: wx - 9, y: wy - 14, width: 18, height: 28, rx: 2 }));
    }
    group.append(building);
  }

  // What homesOf needs of the drawing as it is: the map's box, the school's
  // place and model, the drawing's units to a CSS px, a point's radius at
  // the whole map, and the spots no seat with no place may cover (the place
  // names, the school) with the map's middle they gather nearest.
  function homePlace() {
    const r = Math.min(Math.max(MIN_POINT_PX * view.unit, POINT_R * view.S), MAX_POINT_PX * view.unit);
    const avoid = map.places.map((place) => view.proj(place.x, place.y, 2));
    const { x, y, k, model } = view.yard;
    avoid.push([x + model.ring[0] * k, y + model.ring[1] * k]);
    const [mx, my, mw, mh] = view.mapBox;
    const middle = map.boundary.length ? view.proj(...centroid(map.boundary), 0) : [mx + mw / 2, my + mh / 2];
    return { mapBox: view.mapBox, yard: view.yard, unit: view.unit, r, avoid, middle };
  }

  // Where each seat lives (直し35-2), in the drawing's units, from the seats
  // as given ({ id, kind, at: its spot on the map or null, abroad }) in their
  // order:
  //   地域で働く大人 with a place: there; with none: together, GATE_COLUMNS
  //     to a row, where the map is free (no place name, point, way out or
  //     school near), nearest its middle;
  //   県外・海外に出た人: at the way out to 海外 (south) if they went abroad,
  //     else to 県外 (north), beside the arrow going out, rows inward;
  //   外から来た大人・先生: at the way to 県外, beside the arrow coming in;
  //   探究をした先輩: one to each of the school's windows, then on the rows
  //     past them (seniorRows, 直し39: the ground is gone), the windows'
  //     step apart or more.
  // Returns { spots: id -> [x, y], gates, used, names: [{ kind, at, anchor,
  // school }], counts, school: the ids at the school, noPlace: the ids with
  // no place, seniorStep: the windows' step, room: { windows, rows }: how
  // many fit at the windows and on the rows on the school }. The same seats
  // give the same homes. It reads nothing but what it is given.
  function homesOf(seats, place) {
    const { mapBox: [mx, my, mw, mh], yard: { x: yx, y: yy, k, model }, unit, r, avoid = [], middle } = place;
    const step = Math.max(HOME_STEP * unit, 2.4 * r);
    const inYard = ([px, py]) => [yx + px * k, yy + py * k];
    const windows = model.windows.map(inYard), board = model.board.map(inYard);
    const seniorStep = windowStep(windows);
    const gates = { out: [mx + mw / 2 + 6 * step, my + 3 * step], abroad: [mx + mw / 2 + 6 * step, my + mh - 3 * step] };
    const spots = {}, counts = { map: 0, noPlace: 0, out: 0, abroad: 0, in: 0, windows: 0, rows: 0, past: 0 };
    const lines = { out: [], abroad: [], in: [] }, noPlace = [], seniors = [];
    for (const seat of seats) {
      if (seat.kind === "adult" && seat.at) {
        spots[seat.id] = seat.at;
        counts.map += 1;
      } else if (seat.kind === "adult") noPlace.push(seat);
      else if (seat.kind === "cross") lines[seat.abroad ? "abroad" : "out"].push(seat);
      else if (seat.kind === "poster") seniors.push(seat);
      else lines.in.push(seat);
    }
    // At the ways out, rows of GATE_COLUMNS beside the door, inward.
    const row = (gate, list, side, inward, key) => list.forEach((seat, n) => {
      const c = n % GATE_COLUMNS, down = Math.floor(n / GATE_COLUMNS);
      spots[seat.id] = [gate[0] + side * (c + 1.6) * step, gate[1] + inward * down * step];
      counts[key] += 1;
    });
    row(gates.out, lines.out, 1, 1, "out");
    row(gates.out, lines.in, -1, 1, "in");
    row(gates.abroad, lines.abroad, 1, -1, "abroad");
    // The seniors: the windows, then the rows past them (直し39).
    // The school put larger (直し37-1) can lie under an adult's place: that
    // point stays where it is, and a window or spot under it is passed
    // over, so no senior sits on it once they come out.
    const places = seats.filter((seat) => seat.kind === "adult" && seat.at).map((seat) => seat.at);
    const free = (p) => places.every(([ax, ay]) => Math.hypot(ax - p[0], ay - p[1]) >= seniorStep * SCHOOL_CLEAR);
    const openWindows = windows.filter(free);
    const rows = seniorRows(windows, board, seniorStep * RING_MARGIN, Math.max(0, seniors.length - openWindows.length), free);
    const school = new Set();
    seniors.forEach((seat, n) => {
      const row = n < openWindows.length ? null : rows.spots[n - openWindows.length];
      const spot = row ? row.p : openWindows[n];
      if (!spot) return;
      spots[seat.id] = spot;
      school.add(seat.id);
      counts[!row ? "windows" : row.shown ? "rows" : "past"] += 1;
    });
    // Those with no place, where the map is free.
    if (noPlace.length) {
      // Clear of the ways out and the rows by them, so they are not taken for theirs.
      const round = (gate) => Array.from({ length: 17 * 9 }, (_, n) => [gate[0] + (n % 17 - 8) * step, gate[1] + (Math.floor(n / 17) - 4) * step]);
      const taken = [...avoid, ...Object.values(spots), ...round(gates.out), ...round(gates.abroad)];
      const corner = freeBlock([mx, my, mw, mh], noPlace.length, step, taken, middle || [mx + mw / 2, my + mh / 2]);
      noPlace.forEach((seat, n) => {
        spots[seat.id] = [corner[0] + (n % GATE_COLUMNS) * step, corner[1] + Math.floor(n / GATE_COLUMNS) * step];
      });
      counts.noPlace = noPlace.length;
    }
    const names = [];
    if (counts.map) names.push({ kind: "adult", at: [mx + step * 0.6, my + step * 1.3], anchor: "start" });
    if (counts.out) names.push({ kind: "cross", at: [gates.out[0] + step * 1.1, gates.out[1] - step * 1.1], anchor: "start" });
    if (counts.in) names.push({ kind: "outsider_teacher", at: [gates.out[0] - step * 1.1, gates.out[1] - step * 1.1], anchor: "end" });
    if (counts.abroad) names.push({ kind: "cross", at: [gates.abroad[0] + step * 1.1, gates.abroad[1] + step * 1.6], anchor: "start" });
    if (seniors.length) {
      // Over the windows and the rows in use.
      const xs = windows.map((p) => p[0]), top = Math.min(...[...windows, ...[...school].map((id) => spots[id])].map((p) => p[1]));
      names.push({ kind: "poster", at: [(Math.min(...xs) + Math.max(...xs)) / 2, top - seniorStep * 1.5], anchor: "middle", school: true });
    }
    return { spots, gates, used: { out: counts.out > 0, in: counts.in > 0, abroad: counts.abroad > 0 }, names, counts,
      school, noPlace: new Set(noPlace.map((seat) => seat.id)), seniorStep,
      room: { windows: openWindows.length, rows: rows.room } };
  }

  // Spots for seats at the school past its windows (直し39: the ground they
  // went on is gone). The windows are two rows, as the sprite has them (the
  // first half the inner row, the second the outer, in the same order):
  // row n past the outer one has each window's spot n times as far again
  // past the outer row as the outer is past the inner (the same step
  // between rows), outward round the ring; each row from its middle out.
  // Kept where `free` says and at least `margin` inside the part shown
  // (board, its corners north-west, north-east, south-east, south-west);
  // with no room left there, rows go on outward past it, never west of its
  // west side (the cut), so every one has a spot. Returns { spots: [{ p,
  // shown: on the part shown }] (need of them, or as many as there are),
  // room: how many fit on the part shown }. It reads nothing but what it is
  // given.
  function seniorRows(windows, board, margin, need, free = () => true) {
    const half = Math.floor(windows.length / 2), mid = (half - 1) / 2;
    const order = Array.from({ length: half }, (_, k) => k).sort((a, b) => Math.abs(a - mid) - Math.abs(b - mid));
    const row = (n) => order.map((k) => {
      const [ix, iy] = windows[k], [ox, oy] = windows[k + half];
      return [ox + n * (ox - ix), oy + n * (oy - iy)];
    });
    const onBoard = (p) => within(board, p) && clearOf(board, p, margin);
    const [[wx0, wy0], , , [wx1, wy1]] = board;
    const eastOfCut = ([x, y]) => x >= wx0 + (wx1 - wx0) * (y - wy0) / ((wy1 - wy0) || 1) + margin;
    const shown = [];
    let n = 1;
    for (; half && n <= 200; n++) {
      const on = row(n).filter(onBoard);
      if (!on.length) break;
      shown.push(...on.filter(free));
    }
    const spots = shown.map((p) => ({ p, shown: true }));
    for (; half && spots.length < need && n <= 1000; n++) {
      for (const p of row(n)) if (eastOfCut(p) && free(p) && !onBoard(p)) spots.push({ p, shown: false });
    }
    return { spots: spots.slice(0, Math.max(need, 0)), room: shown.length };
  }

  // Whether a spot is at least d from every side of a ring of spots.
  function clearOf(ring, [x, y], d) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j], [bx, by] = ring[i];
      const dx = bx - ax, dy = by - ay, t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
      if (Math.hypot(x - ax - t * dx, y - ay - t * dy) < d) return false;
    }
    return true;
  }

  // The corner of a block of n spots (GATE_COLUMNS to a row, step apart) in
  // the map's box, with every taken spot at least two steps off it, nearest
  // the given middle; with none so free, the map's upper left. It reads
  // nothing but what it is given.
  function freeBlock([mx, my, mw, mh], n, step, taken, [cx, cy]) {
    const columns = Math.min(n, GATE_COLUMNS), rows = Math.ceil(n / columns);
    const bw = (columns - 1) * step, bh = (rows - 1) * step, room = 2 * step;
    let best = null, least = Infinity;
    for (let y = my + room; y + bh <= my + mh - room; y += step) {
      for (let x = mx + room; x + bw <= mx + mw - room; x += step) {
        const free = taken.every(([tx, ty]) => tx < x - room || tx > x + bw + room || ty < y - room || ty > y + bh + room);
        const d = Math.hypot(x + bw / 2 - cx, y + bh / 2 - cy);
        if (free && d < least) [best, least] = [[x, y], d];
      }
    }
    return best || [mx + room, my + room * 2];
  }

  // The ways out (直し35-2): a doorway on the map's north edge (to 県外) and,
  // when someone went abroad, one on its south edge (to 海外); beside each,
  // an arrow going out in 県外・海外に出た人's colour, and at the way to 県外,
  // when someone came from outside, an arrow coming in in their colour. No
  // words (each group's name is by it).
  function drawGates(group, gates, used) {
    const s = view.unit;
    group.setAttribute("aria-hidden", "true");
    const door = ([x, y], down) => svgEl("path", { class: "door kind-cross", d: down
      ? `M ${x - 5 * s} ${y - 9 * s} V ${y + 8 * s} H ${x + 5 * s} V ${y - 9 * s}`
      : `M ${x - 5 * s} ${y + 9 * s} V ${y - 8 * s} H ${x + 5 * s} V ${y + 9 * s}` });
    if (used.out || used.in) {
      const [x, y] = gates.out;
      group.append(door(gates.out, false));
      group.append(svgEl("path", { class: "out kind-cross",
        d: `M ${x + 2 * s} ${y - 1 * s} L ${x + 11 * s} ${y - 10 * s} M ${x + 5 * s} ${y - 10 * s} H ${x + 11 * s} V ${y - 4 * s}` }));
      if (used.in) {
        group.append(svgEl("path", { class: "in kind-outsider_teacher",
          d: `M ${x - 13 * s} ${y - 12 * s} L ${x - 4 * s} ${y - 3 * s} M ${x - 4 * s} ${y - 9 * s} V ${y - 3 * s} H ${x - 10 * s}` }));
      }
    }
    if (used.abroad) {
      const [x, y] = gates.abroad;
      group.append(door(gates.abroad, true));
      group.append(svgEl("path", { class: "out kind-cross",
        d: `M ${x + 2 * s} ${y + 1 * s} L ${x + 11 * s} ${y + 10 * s} M ${x + 5 * s} ${y + 10 * s} H ${x + 11 * s} V ${y + 4 * s}` }));
    }
    for (const path of group.querySelectorAll("path")) path.style.strokeWidth = `${1.6 * s}px`;
  }

  // Drawn again for the room's shape as it is now, when that is not the
  // drawing's (the window turned or was resized) and no round is playing or
  // its table open: true when it was. The lit seats stay lit.
  // With the table open (直し33-4), it is opened again for the same round,
  // at once, its seats where the new shape gives them room.
  function recompose() {
    if (!view || camera || playing || flights.length || one) return false;
    const room = roomSize(), want = room.w / room.h, have = view.W / view.H;
    if (Math.abs(want - have) <= RECOMPOSE * have) return false;
    const lit = Object.keys(points).filter((id) => points[id].node.classList.contains("lit"));
    const reopen = tableAt && tableOf;
    if (reopen) clearTable();
    const splits = splitsDrawn;
    draw(lastSeats, view.relief, !reopen);
    for (const id of lit) if (points[id]) points[id].node.classList.add("lit");
    if (reopen) openTable(reopen.result, reopen.order, tableCenter(), () => true, true);
    // The flat map's splits drawn again with it (直し40-1: they went with the
    // old drawing, and their heading with them).
    if (splits && !reopen) {
      drawSplits(splits);
      relayout();
    }
    return true;
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
    // The arrow and the ways' names by the map's own edges (直し33-2), inside the frame.
    const [mx, my, mw, mh] = view.mapBox;
    const [left0, top0] = toFrame(mx, my), [right0, bottom0] = toFrame(mx + mw, my + mh);
    const [left, top] = [Math.max(0, left0), Math.max(0, top0)];
    const room = { w: Math.min(frameWH.w, right0) - left, h: Math.min(frameWH.h, bottom0) - top };
    const back = ([x, y]) => [x + left, y + top];
    const shifted = () => avoid.map(([x, y, w, h]) => [x - left, y - top, w, h]);
    put(compass, back(compassSpot(room, { w: compass.offsetWidth, h: compass.offsetHeight }, shifted())));
    for (const note of overlay.querySelectorAll(".map-around")) {
      put(note, back(aroundSpot(room, { w: note.offsetWidth, h: note.offsetHeight }, ways[note.dataset.way], shifted())));
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
  // The school's name (texts/school_label.txt) under the school, which is
  // drawn on the map put larger (直し37-1, SCHOOL_SCALE; 直し35-2: one
  // school, no mark beside it). It takes no presses.
  function drawSchool(group, school) {
    const { x, y, k, model } = view.yard;
    schoolGroup = { node: group, x: x + model.ring[0] * k, y: y + model.height * k };
    group.setAttribute("role", "img");
    group.setAttribute("aria-label", school.label);
    const label = svgEl("text", { x: 0, y: 0, "text-anchor": "middle" });
    label.textContent = school.label;
    group.append(label);
  }

  // The school's name just under the school at the zoom as it is (perPx:
  // the drawing's units to a CSS pixel), at most so large.
  function placeSchool(perPx) {
    const { node, x, y } = schoolGroup;
    node.setAttribute("transform", `translate(${x} ${y}) scale(${perPx})`);
    const label = node.querySelector("text");
    const fontPx = Math.min(TEXT_PX.school * 1.4, SCHOOL_TEXT_MAX_PX);
    label.style.fontSize = `${fontPx}px`;
    label.setAttribute("y", fontPx * 1.1);
  }

  // 「探究をした先輩 45」 on the school (直し35-2) while its windows are
  // closer on screen than a senior's point is wide; pressed, the camera goes
  // to the school until they come out. In the words of the seat list's
  // heading and the count of the seat table.
  function drawSchoolCount(homes) {
    if (!homes.school.size) return;
    const label = document.createElement("button");
    label.type = "button";
    label.className = "school-count kind-poster";
    label.textContent = `${app.state.kinds.poster} ${homes.school.size}`;
    label.addEventListener("click", async () => {
      await toSchool();
      const first = svg.querySelector(".pt.school-home");
      if (first) first.focus({ preventScroll: true });
    });
    // Before the map's points in the keyboard's order (直し35-2: it was over a hundred Tabs away).
    frame.insertBefore(label, svg);
  }

  // Whether the seniors are out at their windows: the one boundary, the
  // windows a senior's width apart on screen (perPx: as the zoom is now).
  function seniorsOut(perPx = vb.w / (frame.clientWidth || 1)) {
    return view.seniorStep / perPx >= 2 * SCHOOL_R_PX;
  }

  // To the school, near enough for its seniors to come out.
  function toSchool() {
    const { x, y, k, model } = view.yard;
    const w = (frame.clientWidth || 1) * view.seniorStep / (2 * SCHOOL_R_PX) / 1.15, h = w * view.H / view.W;
    const cx = x + model.width * k / 2, cy = y + model.height * k / 2;
    return moveTo({ x: cx - w / 2, y: cy - h / 2, w, h }, reduced() ? 0 : CAMERA_FOR);
  }

  // The count over the school, or the seniors at their windows: never both,
  // never neither.
  function foldSchool(perPx) {
    const out = seniorsOut(perPx);
    frame.classList.toggle("seniors-out", out);
    const label = frame.querySelector(".school-count");
    if (label) label.hidden = out;
  }

  // The count by the school, on the first side that covers no word drawn on
  // the map, no seat and nothing laid over the map (chooseSpot).
  function placeSchoolCount(frameBox) {
    const label = frame.querySelector(".school-count");
    if (!label || label.hidden) return;
    const { x, y, k, model } = view.yard;
    const [px, py] = toFrame(x + model.ring[0] * k, y + model.ring[1] * k);
    label.style.left = "0px";
    label.style.top = "0px";
    const { width: w, height: h } = label.getBoundingClientRect();
    const points = [...svg.querySelectorAll(".pt:not(.school-home) .shape")].map((node) => boxIn(node, frameBox));
    const [[left, top]] = chooseSpot({ w: frameBox.width, h: frameBox.height }, { w, h, px, py, gap: 12 },
      [...fixedBoxes(frameBox, true, true, false), ...points]);
    label.style.left = `${Math.round(left)}px`;
    label.style.top = `${Math.round(top)}px`;
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
    // 直し41の続き: behind the shape, the same shape a little larger in the
    // map's ground with a small shadow under it (style.css .edge), so the
    // points over each other are told apart. It takes no press.
    const edge = shape(seat.kind);
    edge.setAttribute("class", "edge");
    point.append(svgEl("circle", { class: "halo", r: 20 }), edge, shape(seat.kind),
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
    return Math.min(Math.max(view.S, MIN_POINT_PX * (vb.w / across) / POINT_R), MAX_POINT_PX * (vb.w / across) / POINT_R);
  }

  // A point's drawn scale (直し41): never under MIN_DRAWN_PX, never over MAX_POINT_PX.
  function drawnScale() {
    const perPx = vb.w / (frame.clientWidth || 1);
    return Math.min(Math.max(pointScale(), MIN_DRAWN_PX * perPx / POINT_R), MAX_POINT_PX * perPx / POINT_R);
  }

  function rescale() {
    const f = pointScale();
    const drawn = drawnScale();
    const perPx = vb.w / (frame.clientWidth || 1);
    const atSchool = Math.min(f, SCHOOL_R_PX * perPx / POINT_R);
    for (const { node, at } of Object.values(points)) {
      const [x, y] = at();
      node.setAttribute("transform", `translate(${x} ${y}) scale(${node.classList.contains("school-home") ? atSchool : drawn})`);
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
    foldSchool(perPx);
    if (!view.relief) return;  // The flat map keeps its words' sizes from style.css.
    for (const text of svg.querySelectorAll("text[data-px]")) {
      text.style.fontSize = `${Number(text.dataset.px) * perPx}px`;
      text.style.strokeWidth = `${2 * perPx}px`;  // A thin halo, not an outline.
    }
  }

  // --- the camera: the part of the drawing on screen ---

  function clampView(v) {
    const w = Math.min(view.W, Math.max(view.W / view.closest, v.w)), h = w * view.H / view.W;
    // At one to one the camera may go past the drawing's edge (直し34-3: a
    // home at the top, the way out or a window, had the person's head cut
    // off), keeping the drawing's edge no further in than half the frame.
    if (one) return { x: Math.min(view.W - w / 2, Math.max(-w / 2, v.x)), y: Math.min(view.H - h / 2, Math.max(-h / 2, v.y)), w, h };
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

  // The pictures there are: the night, then each season's (relief.py).
  function looksOf() {
    return (map.relief && map.relief.looks) || [{ id: "night", image: map.relief.image, blur: BLUR_IMAGE }];
  }

  // The season by today's month when its picture is there; else the night.
  function startLook() {
    const month = new Date().getMonth() + 1;
    const all = looksOf();
    const season = Object.keys(SEASON_MONTHS).find((id) => SEASON_MONTHS[id].includes(month));
    return all.find((one) => one.id === season) || all[0];
  }

  // 夜・春・秋 (the teacher, 11/6): only the picture and its ground change,
  // where they are; the points, the words and the view stay as they were.
  function seasonButtons() {
    const words = app.state.texts.map_buttons;
    const band = $("map-season");
    band.setAttribute("aria-label", words.seasons.label);
    for (const one of looksOf()) {
      const key = `season_${one.id}`;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.look = one.id;
      button.textContent = words[key].text;
      if (words[key].label !== words[key].text) button.setAttribute("aria-label", words[key].label);
      button.addEventListener("click", () => showLook(one.id));
      band.append(button);
    }
    showLook(look.id);
  }

  // 直し48 段6 (the teacher's 決定, 11/7): with fade, the new picture melts
  // in over the old one (LOOK_FADE; at once with motion reduced).
  function showLook(id, { fade = false } = {}) {
    const was = look;
    look = looksOf().find((one) => one.id === id) || look;
    frame.dataset.look = look.id;  // The place names' halo, the spring's flowers (style.css).
    if (lookNodes) {
      const melt = fade && was && was.id !== look.id && !reduced();
      for (const [node, href] of [[lookNodes.picture, look.image], [lookNodes.ground, look.blur]]) {
        if (!melt) {
          node.setAttribute("href", href);
          continue;
        }
        const over = node.cloneNode();
        over.setAttribute("href", href);
        over.style.opacity = "0";
        node.after(over);
        const run = over.animate([{ opacity: 0 }, { opacity: 1 }], { duration: LOOK_FADE, easing: "ease-in-out", fill: "forwards" });
        run.onfinish = () => { node.setAttribute("href", href); over.remove(); };
      }
    }
    for (const button of $("map-season").querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(button.dataset.look === look.id));
    }
    const label = $("map-look-label");
    const words = app && app.state.texts.map_look_label;
    if (label && words) {
      label.querySelector(".look-name").textContent = words[look.id] || "";
      label.querySelector(".look-note").textContent = words.note;
      label.hidden = !words[look.id];
      placeLookLabel();
    }
  }

  // 直し48 段6: each time someone answers (the town's adults at the table,
  // or one to one), the scenery goes one on: night, spring, autumn, night…
  // From the one shown (a button pressed is where it goes on from).
  function nextLook() {
    const all = looksOf();
    if (!map || !map.relief || all.length < 2 || !look) return;
    const at = all.findIndex((one) => one.id === look.id);
    showLook(all[(at + 1) % all.length].id, { fade: true });
  }

  // The scenery's name in a corner of the frame (直し48 段6): the first of
  // the corners (the AI's seat's not among them) over the fewest of the
  // map's words, bubbles and marks.
  function placeLookLabel() {
    const label = $("map-look-label");
    if (!label || label.hidden || !frame) return;
    const f = frame.getBoundingClientRect(), l = label.getBoundingClientRect();
    if (!f.width || !l.width) return;
    const m = 8;
    const corners = { "top-right": [f.width - l.width - m, m], "bottom-left": [m, f.height - l.height - m],
      "bottom-right": [f.width - l.width - m, f.height - l.height - m], "top-left": [m, m] };
    const ai = view && view.aiCorner && !$("ai-seat").hidden ? view.aiCorner : "";
    const busy = [...frame.querySelectorAll(".table-bubble:not(.unplaced), .table-label:not(.unplaced), .map-around, "
      + ".map-compass, .split-tag, .school-count, .home-names text, .place-names text, .pt .shape, .one-bubble, .one-asks, .one-coach, "
      + ".map-hint, .map-choices")]
      .filter((n) => n.getClientRects().length).map((n) => n.getBoundingClientRect());
    const seat = $("ai-seat");
    if (seat && !seat.hidden) busy.push(seat.getBoundingClientRect());
    let best = null, least = Infinity;
    for (const [name, [x, y]] of Object.entries(corners)) {
      if (name === ai) continue;
      const box = { left: f.left + x, top: f.top + y, right: f.left + x + l.width, bottom: f.top + y + l.height };
      const n = busy.filter((b) => b.left < box.right && box.left < b.right && b.top < box.bottom && box.top < b.bottom).length;
      if (n < least) [best, least] = [[x, y], n];
      if (!n) break;
    }
    label.style.left = `${Math.round(best[0])}px`;
    label.style.top = `${Math.round(best[1])}px`;
    // No corner free (the screen check, 768: the hint at the foot, a bubble,
    // the ways out and the AI's seat): not shown until one is.
    label.classList.toggle("crowded", least > 0);
  }

  // Spring's flowers (直し48 段6): small cherry-pink dots on the low land
  // and along the river, from a fixed seed (the same place every time),
  // still, under the points and the bubbles; shown on the spring picture only.
  const FLOWER_SEED = 48, FLOWER_MOST = 140, FLOWER_LOW = 0.3;
  function flowerSpots() {
    let s = FLOWER_SEED;
    const rand = () => { s = (s + 0x6d2b79f5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const rim = map.boundary;
    const xs = rim.map((p) => p[0]), ys = rim.map((p) => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const inside = (x, y) => {
      let hit = false;
      for (let i = 0, j = rim.length - 1; i < rim.length; j = i++) {
        const [xi, yi] = rim[i], [xj, yj] = rim[j];
        if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit;
      }
      return hit;
    };
    const tries = [];
    for (let n = 0; n < 3000; n++) {
      const x = x0 + rand() * (x1 - x0), y = y0 + rand() * (y1 - y0), r = rand();
      if (inside(x, y)) tries.push({ x, y, r, z: view.zAt(x, y) });
    }
    if (!tries.length) return [];
    const low = [...tries].map((t) => t.z).sort((a, b) => a - b)[Math.floor(tries.length * FLOWER_LOW)];
    // Along the river: within a few units of its lines.
    const near = (x, y) => (map.river || []).some((line) => line.some(([rx, ry]) => Math.abs(rx - x) + Math.abs(ry - y) < 6));
    return tries.filter((t) => t.z <= low || near(t.x, t.y)).slice(0, FLOWER_MOST);
  }

  function drawFlowers(layer) {
    for (const spot of flowerSpots()) {
      const [px, py] = view.proj(spot.x, spot.y, 0.5);
      layer.append(svgEl("circle", { class: "flower", cx: px.toFixed(1), cy: py.toFixed(1), r: (2.6 + spot.r * 2.4).toFixed(1) }));
    }
  }

  // The buttons, the wheel, a drag and a two-finger pinch.
  function controls() {
    if (map.relief) seasonButtons();
    const words = app.state.texts.map_buttons;
    for (const [id, key] of [["map-back", "back"], ["map-zoom-in", "zoom_in"], ["map-zoom-out", "zoom_out"],
      ["map-zoom-all", "zoom_all"]]) {
      $(id).textContent = words[key].text;
      if (words[key].label !== words[key].text) $(id).setAttribute("aria-label", words[key].label);
    }
    // ＋ and － keep the school where it is on screen while it is in view
    // (直し35-2: so pressing ＋ comes to its windows); else round the middle.
    const round = (factor) => {
      const { x, y, k, model } = view.yard;
      const sx = x + model.ring[0] * k, sy = y + model.ring[1] * k;
      return inView(sx, sy) ? zoomAround(factor, sx, sy) : zoomAround(factor);
    };
    $("map-zoom-in").addEventListener("click", () => moveTo(round(ZOOM_STEP), 300));
    $("map-zoom-out").addEventListener("click", () => moveTo(round(1 / ZOOM_STEP), 300));
    $("map-zoom-all").addEventListener("click", () => moveTo(view.whole, 500));
    $("map-back").addEventListener("click", () => (one ? closeOne() : closeTable()));

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
      const pressed = event.target.closest && event.target.closest(".points .pt");
      if (pressed) pressRing(pressed);
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
      // Esc at one to one: back to the table, as 「円卓にもどす」 (直し34-3).
      else if (event.key === "Escape" && one && !event.defaultPrevented && !$("drawer").contains(document.activeElement)) closeOne();
    });
  }

  // When the frame's width changes, the sizes and every label follow.
  function watchSize() {
    if (watchSize.on) return;
    watchSize.on = true;
    let width = frame.clientWidth;
    let room = "";
    const changed = () => {
      // The table hidden (the reflection, 直し38): no size to lay the map out in.
      if (!frame.clientWidth || !frame.clientHeight) return;
      const now = roomSize(), key = `${now.w}x${now.h}`;
      if (!view || (frame.clientWidth === width && key === room)) return;
      width = frame.clientWidth;
      room = key;
      if (recompose()) return;
      rescale();
      relayout();
    };
    if (window.ResizeObserver) {
      const watch = new ResizeObserver(changed);
      watch.observe(frame);
      if (frame.parentElement) watch.observe(frame.parentElement);
    }
    window.addEventListener("resize", changed);
  }

  // Draws the rim, then the river, as if by hand. Called when the map is on
  // screen (a path's length needs it laid out).
  function show() {
    if (!view) { wantShow = true; return; }
    recompose();
    rescale();
    relayout();
    startQuiet();
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
    const nodes = [...tableLayer.querySelectorAll(".token .shape, .chair circle, .chair .hit" +
      (withBacks ? ", .token .chair-back, .chair .back, .table-foot .leg, .table-foot .base" : ""))];
    // A seat of the round at the size it has once lit (not met yet, it is drawn smaller).
    const reach = 9.5 * drawnScale() * frameBox.width / vb.w;
    const seats = tableTop ? [] : roundSeats.map((id) => toFrame(...spotOf(id)))
      .map(([px, py]) => [px - reach, py - reach, 2 * reach, 2 * reach]);
    // While the table is open the map's words are not shown (直し33-5): nothing to keep off.
    const words = tableTop ? [] : [...svg.querySelectorAll(".place-names text, .home-names text, .school text, .school > :not(text), " +
      ".yard-building")].map((node) => boxIn(node, frameBox));
    const cover = tableTop && tableTop.map(([x, y]) => toFrame(x, y));
    // The arrow and the four ways' names (直し25-3), once they are put.
    // At the meeting (直し35-3) the map's ways and its arrow step back with the map: only the hint stays.
    const around = withAround ? [...overlay.querySelectorAll(tableTop ? ".map-hint" : ".map-compass, .map-around, .map-hint")]
      .map((node) => boxIn(node, frameBox)) : [];
    // What the one screen lays over the map's side (直し32-1): the card of
    // whose words are in, and the AI's seat (直し32-3).
    for (const node of document.querySelectorAll("#inside:not([hidden]), #ai-seat:not([hidden])")) {
      around.push(boxIn(node, frameBox));
    }
    return [...nodes.map((node) => boxIn(node, frameBox)), ...seats, ...(cover ? topStrips(cover) : []),
      ...(withWords ? seenWords({ w: frameBox.width, h: frameBox.height }, words, cover) : []), ...around];
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
    const { w, h, px, py, gap, r, side } = item, m = 4;
    if (w > frame.w - 2 * m || h > frame.h - 2 * m) return null;
    const clamp = ([left, top]) => [Math.max(m, Math.min(left, frame.w - w - m)), Math.max(m, Math.min(top, frame.h - h - m))];
    const away = ([left, top]) => Math.hypot(Math.max(left - px, 0, px - left - w), Math.max(top - py, 0, py - top - h));
    const d = gap * 0.7;
    // A seat gathered by the table (直し33-4): its card on its own side first.
    const first = side === "left" ? [[px - w - gap, py - h / 2]] : side === "right" ? [[px + gap, py - h / 2]] : [];
    const round = [...first, [px - w / 2, py - h - gap], [px - w / 2, py + gap], [px + gap, py - h / 2], [px - w - gap, py - h / 2],
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
    clearPlaceNames();
    placeAiCorner();
    foldSchool();
    placeSchoolCount(overlay.getBoundingClientRect());
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
    // The seniors' count, put just before: the headings and labels keep off
    // it too (直し40-1: on the flat map the split's tag went under it).
    const count = frame.querySelector(".school-count:not([hidden])");
    if (count && count.getClientRects().length) fixed.push(boxIn(count, frameBox));
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
    // The headings first; a split's tag, pressed now, off every seat's point
    // seen too (直し40-1: it came over points to press).
    put([...overlay.querySelectorAll(".split-tag")], (items) => planLabels(frameSize, items, [...fixed, ...seenPoints(frameBox)]));
    // At the table, the cards of the seats that spoke, in seat_order (直し26-1),
    // before the empty chairs' labels (直し33-5: a long one in a card's column
    // left that card out); the labels then where the cards leave room.
    const { named, planned } = placeTableBubbles(frameBox, frameSize, taken);
    put([...overlay.querySelectorAll(".table-label.empty")], (items) => planLabels(frameSize, items, [...fixed, ...taken]));
    // The names of the other seats there (a seat whose card is up has none:
    // the card says who), then a seat's name card.
    const labels = [...overlay.querySelectorAll(".table-label:not(.empty)")];
    for (const label of labels) if (named.has(label.dataset.seat)) label.classList.add("unplaced");
    put([...labels.filter((label) => !named.has(label.dataset.seat)), ...overlay.querySelectorAll(".map-tip")],
      (items) => planLabels(frameSize, items, [...fixed, ...taken]));
    placeSeatPresses(planned);
    if (one) placeOne();
    putChoices();
    placeAskMarks();
    placeLookLabel();
  }

  // The AI's seat over a corner of the map (直し35-2): the first of
  // AI_CORNERS where, at the whole map, it covers no seat's point, way out,
  // place name, home's name, the school or its count; with none free, the
  // one that covers least. Chosen once for each drawing, so it stays where it
  // is through a round (style.css --ai-left, --ai-top, --ai-w, --ai-h).
  function placeAiCorner() {
    const stage = frame.closest(".stage");
    if (!stage) return;
    const s = stage.getBoundingClientRect(), f = frame.getBoundingClientRect();
    const w = Math.round(view.upright ? f.width * 0.56 : Math.min(Math.max(f.width * 0.36, 300), 460));
    // Upright: the band under the map, as tall as it is.
    const free = f.height * (1 - (view.mapBox[1] + view.mapBox[3]) / view.H) - 16;
    const h = Math.round(view.upright ? Math.max(f.height * AI_BAND_UP, free) : f.height * AI_ROOM);
    // Its height is fixed (style.css), so the corner is chosen once for the drawing and stays.
    const tall = h;
    const key = `${Math.round(f.width)}x${Math.round(f.height)}`;
    if (view.aiCorner === undefined || view.aiFor !== key) {
      // What it keeps off, as drawn now at the whole map (the words whole, not their first letter).
      const boxes = seatKeepsOff(f);
      const pad = 6;
      const boxOf = (corner) => [corner.endsWith("left") ? 8 : f.width - w - 8, corner.startsWith("top") ? 8 : f.height - tall - 8];
      const covered = (corner) => {
        const [left, top] = boxOf(corner);
        return boxes.filter(([x, y, bw, bh]) => x < left + w + pad && x + bw > left - pad && y < top + tall + pad && y + bh > top - pad).length;
      };
      let best = AI_CORNERS[0], least = Infinity;
      for (const corner of AI_CORNERS) {
        const n = covered(corner);
        if (n < least) [best, least] = [corner, n];
        if (!n) break;
      }
      view.aiCorner = best;
      view.aiFor = key;
    }
    const left = view.aiCorner.endsWith("left") ? 8 : f.width - w - 8, top = view.aiCorner.startsWith("top") ? 8 : f.height - h - 8;
    stage.style.setProperty("--ai-left", `${Math.round(f.left - s.left + left)}px`);
    // At a bottom corner it sits on the map's foot whatever its height (直し35-3: the cards over it keep their room).
    const bottom = view.aiCorner.startsWith("bottom");
    stage.style.setProperty("--ai-top", bottom ? "auto" : `${Math.round(f.top - s.top + top)}px`);
    stage.style.setProperty("--ai-bottom", bottom ? `${Math.round(s.bottom - f.bottom + 8)}px` : "auto");
    stage.style.setProperty("--ai-w", `${w}px`);
    // Folded (直し37-2) it keeps to its corner's side.
    stage.style.setProperty("--ai-right", `${Math.round(s.right - f.right + 8)}px`);
    stage.style.setProperty("--ai-h", `${h}px`);
    stage.dataset.aiCorner = view.aiCorner;
    placeFoldedSeat();
  }

  // What the AI's seat keeps off on the map, as drawn now: the seats'
  // points, the ways out, the homes' and places' names, the school and its
  // count (boxes in the frame's own px).
  function seatKeepsOff(f) {
    return [...svg.querySelectorAll(".pt .shape, .home-gate path, .home-names text, .place-names text, .school text, .yard-building"),
      ...frame.querySelectorAll(".school-count")]
      .filter((node) => node.getClientRects().length).map((node) => boxIn(node, f));
  }

  // Folded (直し37-2), the AI's seat is its heading only. Within the room its
  // opened seat takes at its corner, it sits where it covers least of what
  // the map shows (the corner's edge first, then a step at a time inward):
  // 直し37-3, at 1180 the corner's edge covered a way out's name.
  function placeFoldedSeat() {
    const stage = frame.closest(".stage"), seat = $("ai-seat");
    if (!stage || !seat || seat.hidden || !seat.classList.contains("folded") || !view.aiCorner) return;
    stage.style.setProperty("--ai-fold-shift", "0px");
    const f = frame.getBoundingClientRect(), s = seat.getBoundingClientRect();
    const boxes = seatKeepsOff(f);
    const room = parseFloat(stage.style.getPropertyValue("--ai-h")) || s.height;
    const left = s.left - f.left, bottom = view.aiCorner.startsWith("bottom");
    let best = 0, least = Infinity;
    for (let shift = 0; shift <= Math.max(0, room - s.height); shift += 8) {
      const top = (s.top - f.top) + (bottom ? -shift : shift);
      const n = boxes.filter(([x, y, bw, bh]) => x < left + s.width + 6 && x + bw > left - 6 && y < top + s.height + 6 && y + bh > top - 6).length;
      if (n < least) [best, least] = [shift, n];
      if (!n) break;
    }
    stage.style.setProperty("--ai-fold-shift", `${best}px`);
  }

  // A 「？」 by its seat, at the first of its four corners that covers no word
  // drawn on the map (a place name, a home's name, the school's); with none
  // free, the one that covers least. Measured on screen, as the zoom is now.
  function placeAskMarks() {
    const marks = [...svg.querySelectorAll(".pt.silent .ask-mark")];
    if (!marks.length) return;
    const words = [...svg.querySelectorAll(".place-names text, .home-names text, .school text, .yard-building")]
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
    const picture = svg.querySelector(".yard-building");
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

  // A place name over a seat's point (直し41の続き): the name, not the
  // point, moves, a little left or right or up or down (NAME_MOVE_MOST px at
  // most), to where it covers no point and no other word; where every such
  // place covers some, the one that covers least. The points' places and
  // what takes their presses do not change.
  function clearPlaceNames() {
    const names = [...svg.querySelectorAll(".place-names text")];
    for (const name of names) name.removeAttribute("dx");
    if (!names.length || !names[0].getClientRects().length) return;
    const perPx = vb.w / (overlay.clientWidth || 1);
    const dots = [...svg.querySelectorAll(".points .pt .shape")].map((node) => node.getBoundingClientRect()).filter((r) => r.width)
      .map((r) => [r.left - WORD_PAD, r.top - WORD_PAD, r.width + 2 * WORD_PAD, r.height + 2 * WORD_PAD]);
    const words = [...svg.querySelectorAll(".school text, .yard-building, .home-names text")]
      .map((node) => node.getBoundingClientRect()).filter((r) => r.width).map((r) => [r.left, r.top, r.width, r.height]);
    const placed = [];
    for (const name of names) {
      const r = name.getBoundingClientRect();
      const here = [r.left, r.top, r.width, r.height];
      const others = [...dots, ...words, ...placed];
      if (!others.some((b) => boxesMeet(here, b))) { placed.push(here); continue; }
      const moves = nameMoves(r.height);
      const best = leastCovered(moves.map(([dx, dy]) => [r.left + dx, r.top + dy, r.width, r.height]), others);
      const [dx, dy] = moves[best];
      if (dx) name.setAttribute("dx", dx * perPx);
      if (dy) name.setAttribute("dy", Number(name.getAttribute("dy") || 0) + dy * perPx);
      placed.push([r.left + dx, r.top + dy, r.width, r.height]);
    }
  }

  // Where a name of this height may go, nearest first: where it is, then a
  // step at a time left, right, up and down, up to NAME_MOVE_MOST px.
  function nameMoves(height) {
    const moves = [[0, 0]];
    const step = Math.max(4, Math.round(height / 3));
    for (let d = step; d <= NAME_MOVE_MOST; d += step) {
      moves.push([-d, 0], [d, 0], [0, -d], [0, d], [-d, -d], [d, -d], [-d, d], [d, d]);
    }
    return moves;
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
    node.append(...kindOf(quote), div("voice", voiceOf(quote)), div("who", whoOf(seat)));
    spokenMark(node, quote);
    overlay.append(node);
    place(node, x, y, 18);
    thread(node, ...toFrame(x, y));
    timers.push(setTimeout(() => node.classList.add("fading"), BUBBLE_FOR - FADE_FOR));
    timers.push(setTimeout(() => node.remove(), BUBBLE_FOR));
  }

  // A lamp card's words: the quote cut at BUBBLE_CHARS with 「…」, and which
  // seat, in the words the seat's label already shows.
  // As spoken words (直し31-7) when code let them through: no 「」, a small mark.
  function voiceOf(quote) {
    const text = quote.spoken || quote.text;
    const chars = [...text];
    const cut = chars.length > BUBBLE_CHARS ? chars.slice(0, BUBBLE_CHARS).join("") + "…" : text;
    return quote.said && !quote.spoken ? `「${cut}」` : cut;
  }

  // The small line over a bubble (直し45 段1): the kind of talk of its
  // piece, from the teacher's table (closing_kind_labels.tsv); none for
  // 「なし」. First in the bubble, so it is read out before the words.
  function kindOf(quote) {
    return quote && quote.kind_label ? [div("kind", quote.kind_label)] : [];
  }

  function spokenMark(node, quote) {
    if (!quote.spoken) return;
    node.classList.add("spoken");
    node.prepend(div("spoken-mark", app.state.texts.spoken_mark));
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
    playing = false;
    for (const timer of timers) clearTimeout(timer);
    timers = [];
    for (const flight of flights) flight.cancel();
    flights = [];
    if (app && app.gathering) app.gathering(false);  // No 「集合中」 left over (直し42).
    sticky = null;
    roundSeats = [];
    splitsDrawn = null;
    hideTip();
    for (const node of overlay.querySelectorAll(".map-bubble, .split-tag, .table-label, .table-bubble, .seat-press, .map-hint")) node.remove();
    splitLayer.replaceChildren();
    clearTable();
    for (const { node } of Object.values(points)) node.classList.remove("lit");
  }

  // The seats quoted light up one after another, each with its first quote
  // in a short bubble. On the picture the round table follows; on the flat
  // map, the splits. No seat answered: nothing lights.
  // The quiet glow runs on the first map only: once a round comes, never again.
  let quiet = null, quietOver = false;
  function startQuiet() {
    if (quiet || quietOver) return;
    quiet = quietGlow(() => [...svg.querySelectorAll(".points .pt:not(.met):not(.lit):not(.away):not(.school-home)")]
      .filter((node) => node.getClientRects().length));
  }
  function stopQuiet() {
    quietOver = true;
    if (quiet) quiet();
    quiet = null;
  }
  // A question sent (直し41の続き): the glow stops then, not when its round
  // comes; nothing glows while the answer is waited for.
  function asked() {
    stopQuiet();
  }

  function round(result) {
    stopQuiet();
    if (!map) return;
    if (!view) { pending = result; return; }
    clearRound();
    refresh();
    const first = {};
    for (const quote of result.quotes) if (!(quote.seat_id in first)) first[quote.seat_id] = quote;
    const order = result.seat_order.filter((id) => points[id]);
    if (!order.length) return;
    roundSeats = order;
    nextLook();  // 直し48 段6: someone answered; the scenery goes one on.
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
  // The heading is a button (直し40-1): pressed, it goes into the question
  // box (app.pressSplit), as the drawer's button does; it looks as it did.
  function drawSplits(result) {
    splitsDrawn = result;
    const seatOfQuote = {};
    for (const quote of result.quotes) seatOfQuote[quote.utterance_id] = quote.seat_id;
    for (const split of result.splits) {
      const a = seatOfQuote[split.side_a[0]], b = seatOfQuote[split.side_b[0]];
      if (!points[a] || !points[b] || a === b) continue;
      const [ax, ay] = spotOf(a), [bx, by] = spotOf(b);
      splitLayer.append(svgEl("line", { x1: ax, y1: ay, x2: bx, y2: by }));
      // It wraps after its 「：」 or between its 「…」, never inside one (app.phrased).
      const tag = splitButton(result.round, split, "split-tag");
      tag.classList.toggle("narrow", overlay.clientWidth < NARROW);
      overlay.append(tag);
      place(tag, (ax + bx) / 2, (ay + by) / 2, 8);
    }
    placeSplitTags();
  }

  // Every seat's point on screen, as boxes in the frame (直し40-1).
  function seenPoints(frameBox) {
    return [...svg.querySelectorAll(".points .pt .shape")].map((node) => boxIn(node, frameBox))
      .filter(([x, y, w, h]) => w && x + w > 0 && y + h > 0 && x < frameBox.width && y < frameBox.height);
  }

  // The splits' tags put again as soon as they are drawn, as relayout puts
  // them: off the fixed boxes, the seniors' count, what is over the map now
  // (the last bubble, the name card) and every seat's point, since pressed
  // they would cover it (直し40-1).
  function placeSplitTags() {
    const frameBox = overlay.getBoundingClientRect();
    const tags = [...overlay.querySelectorAll(".split-tag")];
    const others = [...overlay.children].filter((node) => !node.classList.contains("split-tag") && !node.classList.contains("unplaced"))
      .map((node) => boxIn(node, frameBox));
    const count = frame.querySelector(".school-count:not([hidden])");
    const counted = count && count.getClientRects().length ? [boxIn(count, frameBox)] : [];
    const items = tags.map((node) => {
      const x = Number(node.dataset.x), y = Number(node.dataset.y);
      const [px, py] = toFrame(x, y);
      return { ...measure(node, frameBox), px, py, gap: Number(node.dataset.gap), inView: inView(x, y), heading: true, atTable: false };
    });
    const spots = planLabels({ w: frameBox.width, h: frameBox.height }, items,
      [...fixedBoxes(frameBox), ...counted, ...others, ...seenPoints(frameBox)]);
    tags.forEach((node, k) => {
      node.classList.toggle("unplaced", !spots[k]);
      if (!spots[k]) return;
      node.style.left = `${spots[k][0]}px`;
      node.style.top = `${spots[k][1]}px`;
    });
  }

  // A split's heading as a button: its words as they are shown, read aloud
  // as 「この割れ目を次の問いにする：」 and the heading (直し40-1).
  function splitButton(roundNo, split, className) {
    const press = document.createElement("button");
    press.type = "button";
    press.className = className;
    press.append(app.phrased(app.shownQuotes(split.heading)));
    press.setAttribute("aria-label", app.splitLabel(split.heading));
    press.addEventListener("click", () => app.pressSplit(roundNo, split.index));
    return press;
  }

  // --- the round table (the picture only) ---

  // Where the seats gather (直し33-4): the table's middle where the map
  // meets the school (upright: between the two), and its own flat
  // projection there (the table's units, as on the basin before, to the
  // drawing's), whatever the seats' homes.
  const tableCenter = () => riseAt({ W: view.W, H: view.H, mapBox: view.mapBox, upright: view.upright, model: view.yard.model });

  // The gathering's middle and projection for a drawing ({ W, H, mapBox,
  // upright, unit }). It reads nothing but what it is given.
  // Where the school rises to (直し35-3), in a drawing ({ W, H, mapBox,
  // upright, model: the school's picture or the plain one}): its picture at
  // least RISE_PART of the map's height (upright: RISE_PART_UP of its width),
  // its ring's middle a little under the map's middle and the picture whole
  // in the drawing. Returns the meeting's middle as the table's was ({ x, y,
  // level, at, scale, proj }: its ring the table's top) with the picture's
  // corner and scale (pic). Its scale from the yard's size as it was with its
  // ground (model.rise, 直し39), so the table and the seats round it are as
  // they were (直し37). It reads nothing but what it is given.
  function riseAt({ W, H, mapBox: [mx, my, mw, mh], upright, model }) {
    const [across, tall] = model.rise || [model.width, model.height];
    const k = upright ? RISE_PART_UP * W / across : Math.min(RISE_PART * mh / tall, 0.94 * W / across);
    const room = upright ? H * (1 - AI_BAND_UP) : my + mh;
    const top = upright ? 0 : my;
    let cx = mx + mw / 2;
    const cy = Math.min(top + (room - top) * 0.58, room - (model.height - model.ring[1]) * k - 4);
    cx = Math.min(Math.max(cx, model.ring[0] * k + 4), W - (model.width - model.ring[0]) * k - 4);
    const s = RING_R_M * model.pxPerM * k / TABLE_RX, tilt = PICTURE_TILT * TABLE_RX / TABLE_RY;
    return { x: 0, y: 0, level: 0, at: [cx, cy], scale: s, pic: { x: cx - model.ring[0] * k, y: cy - model.ring[1] * k, k },
      proj: (x, y, lift = 0) => [cx + x * s, cy + y * s * tilt - lift * s * tilt] };
  }

  // The seats' spots bent onto an arc round the ring (直し35-3): each at its
  // height, nearer the ring's middle the further up or down it is, never
  // into the ring. It reads nothing but what it is given.
  function onArc(spots, [cx, cy]) {
    const far = Math.max(1, ...Object.values(spots).map(({ at }) => Math.abs(at[1] - cy))) * 1.35;
    for (const spot of Object.values(spots)) {
      const [x, y] = spot.at, t = (y - cy) / far;
      spot.at = [cx + (x - cx) * Math.sqrt(Math.max(0.5, 1 - t * t)), y];
    }
    return spots;
  }

  // The school lifted from the map (直し35-3): the same drawing (its
  // picture, or the plain building and ground), from its place and size on
  // the map to the meeting's (center.pic), a faint shadow under it; the one
  // on the map unseen meanwhile. Motion reduced: there at once.
  function riseSchool(center, motion) {
    const { x, y, k, model } = view.yard, pic = center.pic;
    const from = svg.querySelector(".yard");
    const group = svgEl("g", { class: "risen-school", "aria-hidden": "true" });
    for (const node of from.children) if (!node.classList.contains("yard-landing")) group.append(node.cloneNode(true));
    group.setAttribute("transform", `translate(${pic.x} ${pic.y}) scale(${pic.k})`);
    const shadow = svgEl("ellipse", { class: "risen-shadow", cx: pic.x + model.width * pic.k / 2, cy: pic.y + model.height * pic.k * 0.97,
      rx: model.width * pic.k * 0.5, ry: model.height * pic.k * 0.09 });
    from.classList.add("lifted");
    let done = Promise.resolve();
    if (motion) {
      const lift = model.height * pic.k * 0.04;
      done = group.animate([
        { transform: `translate(${x}px, ${y}px) scale(${k})`, opacity: 0.85 },
        { transform: `translate(${pic.x}px, ${pic.y - lift}px) scale(${pic.k * 1.02})`, opacity: 1, offset: 0.8 },
        { transform: `translate(${pic.x}px, ${pic.y}px) scale(${pic.k})`, opacity: 1 },
      ], { duration: RISE_FOR, easing: "cubic-bezier(.3,.7,.2,1)" }).finished.catch(() => {});
      shadow.animate([{ opacity: 0 }, { opacity: 1 }], { duration: RISE_FOR, easing: "ease-in" });
    }
    return { group, shadow, done };
  }

  // The school back down to its place on the map (「地図にもどす」, the next question).
  function sinkSchool() {
    const group = tableLayer && tableLayer.querySelector(".risen-school");
    if (!group || reduced()) return Promise.resolve();
    const { x, y, k } = view.yard;
    const shadow = tableLayer.querySelector(".risen-shadow");
    if (shadow) shadow.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FLY_FOR * 0.6, fill: "forwards" });
    return group.animate([{ transform: group.getAttribute("transform").replace(/translate\(([^ ]+) ([^)]+)\) scale\(([^)]+)\)/, "translate($1px, $2px) scale($3)") },
      { transform: `translate(${x}px, ${y}px) scale(${k})` }], { duration: FLY_FOR * 0.7, easing: "cubic-bezier(.4,0,.6,1)", fill: "forwards" })
      .finished.catch(() => {});
  }

  function onTable(center, angle, out, lift = TABLE_LIFT) {
    const a = angle * Math.PI / 180;
    return (center.proj || view.proj)(center.x + (TABLE_RX + out) * Math.cos(a), center.y + (TABLE_RY + out) * Math.sin(a),
      lift, center.level);
  }

  function ring(center, out, lift) {
    return Array.from({ length: 72 }, (_, k) => onTable(center, k * 5, out, lift));
  }

  // Where each seat that spoke sits (直し33-4), from the seating's groups
  // (a: one side of the split, b: the other, back: neither) and the
  // gathering's middle, in a drawing ({ W, H, unit, upright }): side a in
  // the left column, side b in the right, the others where there is room,
  // each column as many rows as fit (on a wide screen the right one over
  // the AI's room), centred on the table. Returns id -> { at, side }; a seat
  // with no room has none (it sits round the table and its seat shows its
  // card when pressed). It reads nothing but what it is given.
  function gatherSpots(sittings, center, { W, H, unit, upright, ai = "bottom-right" }) {
    const [cx, cy] = center.at, card = GATHER_CARD;
    const step = (card.h + card.gap) * unit, margin = 6 * unit;
    const half = (TABLE_RX + 18) * center.scale + 22 * unit;  // The table's side and a little room.
    const foot = upright ? H * (1 - AI_BAND_UP) - margin : H - margin;
    // The AI's seat's corner (直し35-2): its side's column stops over it.
    const under = upright ? foot : H * (1 - AI_ROOM) - margin;
    const limits = { left: ai === "bottom-left" ? under : foot, right: ai === "bottom-right" ? under : foot };
    const fits = (limit) => Math.max(0, Math.floor((limit - margin + card.gap * unit) / step));
    const room = { left: fits(limits.left), right: fits(limits.right) };
    const columns = { left: [], right: [] };
    const put = (id, side) => {
      const other = side === "left" ? "right" : "left";
      if (columns[side].length < room[side]) columns[side].push(id);
      else if (columns[other].length < room[other]) columns[other].push(id);
    };
    for (const { id, group } of sittings) if (group === "a") put(id, "left"); else if (group === "b") put(id, "right");
    for (const { id, group } of sittings) {
      if (group === "a" || group === "b") continue;
      put(id, columns.left.length - room.left <= columns.right.length - room.right ? "left" : "right");
    }
    const out = {};
    for (const side of ["left", "right"]) {
      const ids = columns[side];
      if (!ids.length) continue;
      // Centred on the table, moved up or down as little as keeps it in the room.
      const tall = ids.length * step - card.gap * unit;
      const top = Math.min(Math.max(cy - tall / 2, margin), limits[side] - tall);
      const x = side === "left" ? cx - half : cx + half;
      ids.forEach((id, k) => { out[id] = { at: [x, top + k * step + card.h * unit / 2], side }; });
    }
    return out;
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

  async function tableRound(result, order, first, mine) {
    const still = () => mine === roundNo;
    // The room may have changed with the question sent (直し35-3: the meeting
    // was laid out for the room before it): drawn again first if so.
    recompose();
    playing = true;
    // From the whole map, so every seat that lights can be seen.
    if (vb.w < view.W - 0.5) await moveTo({ x: 0, y: 0, w: view.W, h: view.H }, reduced() ? 0 : 500);
    if (!still()) return;
    if (reduced()) {
      for (const id of order) points[id].node.classList.add("lit");
    } else {
      // Each lights at its home, no card there (直し33-4: the cards come
      // from the seats gathered at the table, no line from their homes).
      for (const id of order) {
        light(id);
        await wait(LIGHT_EVERY);
        if (!still()) return;
      }
      await wait(150);
      if (!still()) return;
    }
    // The seats gather where their cards have room (直し33-4): the camera
    // stays on the whole drawing; they fly there from their homes (motion
    // reduced: they are there at once).
    openTable(result, order, tableCenter(), still);
  }

  // again: the same round's table opened again for the room's new shape
  // (recompose): at once, nothing flies.
  async function openTable(result, order, center, still, again = false) {
    const motion = !reduced() && !again;
    tableOf = { result, order };
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
    const S = center.scale || view.S;
    const polygon = (className, spots) => svgEl("polygon", { class: className, points: spots.map((p) => p.join(",")).join(" ") });
    tableTop = ring(center, 0, TABLE_LIFT);
    // The lamp's light on the ground round the table, its shadow, the top's
    // edge (so it reads as a top, not a ring), the top lit from its middle,
    // its rim of light, and the lamp.
    // The school rises from the map (直し35-3): its ring is the round table,
    // the lamp the light in its glass roof; the seats gather round the ring.
    const [lx, ly] = center.proj(center.x, center.y, TABLE_LIFT, center.level);
    const top = svgEl("g", { class: "table-top-group" });
    const lamp = svgEl("g", { class: "table-lamp" });
    lamp.append(svgEl("circle", { class: "light", cx: lx, cy: ly, r: 70 * S }),
      svgEl("circle", { class: "core", cx: lx, cy: ly, r: 4.5 * S }));
    const risen = riseSchool(center, motion);
    top.append(risen.group, polygon("table-rim-glow", tableTop), lamp);
    tableLayer.append(risen.shadow, top);
    if (motion) {
      await risen.done;
      if (!still()) return;
      // The school is up: until the seats have landed, 「集合中」 in the
      // middle (直し42; not while they light at home, nor with motion off).
      if (app.gathering) app.gathering(true);
    }
    // The split: a dashed line down the table's middle, between the sides.
    if (split) {
      const [n0, n1] = [center.proj(center.x, center.y - TABLE_RY + 6, TABLE_LIFT, center.level),
        center.proj(center.x, center.y + TABLE_RY - 6, TABLE_LIFT, center.level)];
      const line = rc.line(n0[0], n0[1], n1[0], n1[1], { stroke: "#000", strokeWidth: 1.8 * S, roughness: 0.9,
        seed: 5 });
      line.classList.add("table-split");
      tableLayer.append(line);
    }
    const landed = [];
    const spots = onArc(gatherSpots(seats.filter((sitting) => sitting.group !== "front"), center,
      { W: view.W, H: view.H, unit: view.unit, upright: view.upright, ai: view.aiCorner }), center.at);
    seats.forEach((sitting, k) => {
      const spot = spots[sitting.id];
      const at = spot ? spot.at : onTable(center, sitting.angle, SEAT_OUT);
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
      const token = { node, at, scale: TOKEN, id: sitting.id, side: spot ? spot.side : "" };
      tokens.push(token);
      // It has left its home for the table (直し33-4): its home stays empty until it goes back.
      points[sitting.id].node.classList.add("away");
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
    const done = await Promise.all(landed).finally(() => { if (motion && app.gathering) app.gathering(false); });
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
      card.dataset.side = token.side;  // Its card goes this side of it first (直し33-4).
      card.dataset.rank = String(rank.indexOf(id));
      overlay.append(card, seatPress(id, token.at));
    });
    // The split's heading: under the map, over neither the table's top nor
    // its chairs; on a map narrower than TAG_ON_MAP, in the split block only.
    // It wraps after its 「：」 or between its 「…」, never inside one (app.phrased).
    // Pressed, it goes into the question box (直し40-1).
    if (split && overlay.clientWidth >= TAG_ON_MAP) $("map-heading").replaceChildren(splitButton(result.round, split, "map-heading-press"));
    for (const chairNode of tableLayer.querySelectorAll(".chair")) chairNode.classList.add("ready");
    tableRoundNo = result.round;
    if (!pressedOnce) overlay.append(div("map-hint", app.state.texts.bubble_hint));
    playing = false;
    relayout();
    marked();
    app.setNow({ reading: false, table: true });
    // Nothing has the keyboard (the box sent the question): the first card has it (直し32-1).
    if (document.activeElement === document.body || !document.activeElement) {
      const firstCard = overlay.querySelector(".table-bubble:not(.unplaced)");
      if (firstCard) firstCard.focus({ preventScroll: true });
    }
  }

  // A seat's lamp card at the table: the same words as on the map, kept.
  // Pressed (or Enter or Space on it), it opens its choices (直し26-2).
  function tableBubble(seatId, quote, at, k) {
    const node = div("table-bubble unplaced");
    node.append(...kindOf(quote), div("voice", voiceOf(quote)), div("who", whoOf(seatOf(seatId))));
    spokenMark(node, quote);
    if (quote.spoken) node.dataset.note = (quote.source && quote.source.note) || "";
    Object.assign(node.dataset, { seat: seatId, utterance: quote.utterance_id, x: at[0], y: at[1] });
    node.style.setProperty("--k", String(k));
    node.tabIndex = 0;
    node.setAttribute("role", "button");
    node.setAttribute("aria-expanded", "false");
    pressable(node, () => toggleChoices(seatId));
    return node;
  }

  // Whose a seat at the table is, in words: its title and detail. (コーチ
  // and オブザーバー sit at the AI's seat, off the table: 直し32-3.)
  function nameAt(seatId) {
    return whoOf(seatOf(seatId));
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
      return { ...measure(card, frameBox), px, py, gap: r + TAIL_LENGTH, r, side: card.dataset.side,
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
    // Never broken inside a word nor its （…） (直し33-5: 「架空の川／1」).
    const who = div("who");
    who.append(app.phrased(whoOf(seatOf(seatId))));
    head.append(who, close);
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
    // A bubble shown as spoken words: its source's note goes with the original (直し31-7).
    paragraph.append(div("whose", [seatOf(seatId).title, card.dataset.note].filter(Boolean).join("　")), text);
    // While a choice waits on the server it stays where it is (a disabled
    // button would drop the keyboard's focus): a second press then does nothing.
    let busy = false;
    // In the drawer, not here (直し32-4): the paragraph and whose it is.
    const read = button("paragraph", async () => {
      if (busy) return;
      busy = true;
      try {
        await app.openParagraph(utteranceId, paragraph.querySelector(".whose").textContent, read);
      } catch (error) {
        // As below the map: nothing changes.
      } finally {
        busy = false;
      }
    });
    read.setAttribute("aria-controls", "drawer");
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
    // One to one with this seat (直し34-3), its card made or not.
    const write = button("card", () => openOne(seatId, card));
    const below = button("read", () => { closeChoices(false); app.readBelow(tableRoundNo, utteranceId, card); });
    node.append(head, read, paragraph, mark, write, below);
    if (app.bubbleOpened) app.bubbleOpened(utteranceId);  // For today's map (直し38).
    if (app.trailOpened) app.trailOpened(tableRoundNo, utteranceId);  // 今日の道すじ (直し45 段2).
    // The first time a bubble is pressed, a line under each button says what
    // it does (直し32-4); after that the buttons alone.
    const help = app.firstHelp();
    if (help) {
      node.classList.add("with-help");
      for (const item of [read, mark, write, below]) {
        const key = item.dataset.choice;
        if (!key || !help[key]) continue;
        const line = div("help", help[key]);
        line.id = `choice-help-${key}`;
        item.setAttribute("aria-describedby", line.id);
        item.after(line);
      }
    }
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
    // And the words on the map and the homes' names (直し33-5: pressed a
    // second time, the choices came over a place name and a seat's label).
    const words = [...svg.querySelectorAll(".place-names text, .home-names text, .school text")].map((other) => boxIn(other, frameBox));
    const others = [...shown.map((other) => boxIn(other, frameBox)),
      ...seenWords(frameWH, words, tableTop && tableTop.map(([x, y]) => toFrame(x, y)))];
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
    if (one) endOne();
    tableOf = null;
    tokens = [];
    tableTop = null;
    tableAt = null;
    opened = null;
    closeChoices(false);
    if ($("map-heading")) $("map-heading").replaceChildren();
    if (tableLayer) tableLayer.replaceChildren();
    if (svg) svg.classList.remove("dim");
    if (svg && svg.querySelector(".yard")) svg.querySelector(".yard").classList.remove("lifted");  // The school on the map again.
    for (const { node } of Object.values(points)) {
      node.setAttribute("tabindex", "0");
      node.classList.remove("away");
    }
    if ($("map-back")) $("map-back").hidden = true;
  }

  // 「地図にもどす」: the table goes, the camera goes back to the whole map
  // (at once when motion is reduced). The lit seats and the marks stay.
  async function closeTable() {
    roundNo += 1;
    playing = false;
    const mine = roundNo;
    for (const flight of flights) flight.cancel();
    flights = [];
    for (const node of overlay.querySelectorAll(".split-tag, .table-label, .map-bubble, .table-bubble, .seat-press, .map-hint")) node.remove();
    $("map-zoom-all").focus();
    moveTo(view.whole, BACK_FOR);
    // Each seat flies back to its home (直し33-4; motion reduced: at once).
    if (!reduced()) {
      closeChoices(false);
      const f = pointScale();
      const back = tokens.filter((t) => !t.chair && points[t.id]).map((t) => {
        const [x, y] = spotOf(t.id);
        const flight = t.node.animate([
          { transform: `translate(${t.at[0]}px, ${t.at[1]}px) scale(${f * TOKEN})` },
          { transform: `translate(${x}px, ${y}px) scale(${f})` },
        ], { duration: FLY_FOR * 0.7, easing: "cubic-bezier(.3,.7,.2,1)", fill: "forwards" });
        return flight.finished.catch(() => {});
      });
      await Promise.all([...back, sinkSchool()]);
      if (mine !== roundNo) return;
    }
    clearTable();
    app.foldAiSeat(true);  // Back at the map: the AI's seat folded (直し37-2).
    requestAnimationFrame(placeFoldedSeat);
  }

  // --- marks that stay: met seats, and 「？」 on seats nobody asked yet ---

  function refresh() {
    if (!map || !view) return;
    for (const [id, { node }] of Object.entries(points)) {
      node.classList.toggle("met", app.state.met.has(id));
      node.classList.toggle("silent", isSilent(id));
      node.classList.toggle("carded", app.state.carded.has(id));
      node.classList.toggle("thanked", app.state.thanked.has(id));  // 直し34-5
      const seat = seatOf(id);
      const words = [seat.title, seat.detail, isSilent(id) ? app.state.texts.not_asked_yet : ""];
      node.setAttribute("aria-label", words.filter(Boolean).join("　"));
    }
    // The seats met: when the number grows it lights once, softly (直し41の続き;
    // the light is CSS, with motion not reduced only).
    const count = $("map-met-count"), was = Number(count.textContent) || 0;
    count.textContent = String(app.state.met.size);
    if (app.state.met.size > was) {
      count.classList.remove("grew");
      void count.offsetWidth;  // The light again from its start.
      count.classList.add("grew");
    }
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
    // The one box at the foot writes to it (直し32-2), the keyboard in it.
    app.askSeat(seatId);
  }

  // --- one to one (直し34-3) ---
  // 「この人に聞きたいことを書く」 on a card at the table: the seat goes back
  // to its home, the camera comes near it there, the seat stands up as a
  // person (person.js), one hand up, and talks from there; the other seats
  // and cards step back. 「円卓にもどす」 or Esc: the person is a seat again,
  // the camera goes back and the table is as it was. Motion reduced: the
  // near view with the person standing, at once. The AI's seat never stands
  // up (it is not one of the town's people): it has no card at the table.
  const ONE_ZOOM = 2.4;  // The camera this much nearer.
  const PERSON_PART = 0.5;  // The person this part of the frame's height.
  const STAND_FOR = 450;  // ms the seat takes to stand up.
  let one = null;  // { seatId, home, token, group, scale, flight }

  // A seat's place among the seats of its kind in seat ID order (person.js).
  function placeAmong(seatId) {
    const kind = seatOf(seatId).kind;
    const ids = app.state.seats.filter((seat) => seat.kind === kind).map((seat) => seat.seat_id).sort();
    return Math.max(0, ids.indexOf(seatId));
  }

  async function openOne(seatId, card) {
    if (!tableAt || !points[seatId] || one) return;
    closeChoices(false);
    const motion = !reduced();
    const token = tokens.find((t) => t.id === seatId && !t.chair) || null;
    const home = spotOf(seatId);
    const kindLine = card && card.querySelector(".kind");
    one = { seatId, home, token, group: null, words: card ? card.querySelector(".voice").textContent : "",
      kind: kindLine ? kindLine.textContent : "",
      spoken: Boolean(card && card.classList.contains("spoken")) };
    const mine = one;
    // The questions, put to this person, asked for while the camera flies
    // (直し36-3; 直し39: at most eight seconds; the teacher's questions past that).
    mine.asks = app.oneOpen(seatId).catch(() => null);
    mine.asks.then(() => { mine.back = true; });
    frame.classList.add("one-on");
    // The AI's seat steps back too (直し34-3: it covered the person's feet and words).
    document.body.classList.add("one-open");
    $("map-back").textContent = app.state.texts.one_words.back;
    app.setNow({ one: true });
    // 直し45 段3: no box to write in at one to one; the questions to pick only.
    if (token) token.node.classList.add("one-self");
    // Back home first.
    if (token && motion) {
      const f = pointScale();
      mine.flight = token.node.animate([
        { transform: `translate(${token.at[0]}px, ${token.at[1]}px) scale(${f * TOKEN})` },
        { transform: `translate(${home[0]}px, ${home[1]}px) scale(${f})` },
      ], { duration: FLY_FOR * 0.7, easing: "cubic-bezier(.3,.7,.2,1)", fill: "forwards" });
      await mine.flight.finished.catch(() => {});
      if (one !== mine) return;
    }
    // Near it, the person's feet low in the frame, room for its words beside
    // it; a seat at the school (its window, its track) as near as the
    // nearest zoom, where the school is large and its seniors out (直し35-4).
    const w = view.W / (view.homes.school.has(seatId) ? view.closest : ONE_ZOOM), h = w * view.H / view.W;
    await moveTo({ x: home[0] - w * 0.36, y: home[1] - h * 0.86, w, h }, motion ? CAMERA_FOR : 0);
    if (one !== mine) return;
    standUp(motion);
  }

  // The seat stands up as a person: in its kind's colour, stretched up from
  // the seat, its head and legs coming out.
  function standUp(motion) {
    const [x, y] = one.home;
    const s = PERSON_PART * vb.h / EbinoPerson.HEIGHT;
    const group = svgEl("g", { class: "one-person" });
    group.append(EbinoPerson.figure(seatOf(one.seatId).kind, one.seatId, placeAmong(one.seatId), "wave"));
    group.setAttribute("transform", `translate(${x} ${y}) scale(${s})`);
    tableLayer.append(group);
    Object.assign(one, { group, scale: s });
    if (one.token) one.token.node.classList.add("stood");
    if (motion && group.animate) {
      group.animate([
        { transform: `translate(${x}px, ${y}px) scale(${s * 0.3}, ${s * 0.1})`, opacity: 0.8 },
        { transform: `translate(${x}px, ${y}px) scale(${s * 0.55}, ${s * 0.75})`, opacity: 1, offset: 0.5 },
        { transform: `translate(${x}px, ${y}px) scale(${s})`, opacity: 1 },
      ], { duration: STAND_FOR, easing: "cubic-bezier(.3,.7,.2,1)" });
    }
    const bubble = div("one-bubble");
    bubble.setAttribute("role", "status");
    if (one.spoken) bubble.append(div("spoken-mark", app.state.texts.spoken_mark));
    const voice = div("voice");
    voice.textContent = one.words;
    bubble.append(...kindOf({ kind_label: one.kind }), voice, div("who", whoOf(seatOf(one.seatId))));
    overlay.append(bubble);
    one.bubble = bubble;
    placeOne();
    // The questions to pick from (直し34-4), asked for while it stands up.
    const mine = one;
    // Stood up and not back yet (直し40-0): three dots where they go, until
    // they come (past the wait, the teacher's) or nothing does.
    new Promise((done) => setTimeout(done, motion ? STAND_FOR : 0)).then(() => {
      if (one === mine && !mine.back) showWait();
    });
    // The keyboard goes to the first of them (直し34-5: it was six Tabs away).
    mine.asks.then((view) => {
      if (one !== mine) return;
      if (!view) {
        for (const old of overlay.querySelectorAll(".one-wait")) old.remove();
        return;
      }
      showAsks(view);
      const first = overlay.querySelector(".one-asks .one-ask");
      if (first) first.focus({ preventScroll: true });
    }, () => {});
  }

  // Where the questions go, while they are asked for: three dots, no words
  // (直し40-0); busy for screen readers. The questions take its place.
  function showWait() {
    for (const old of overlay.querySelectorAll(".one-asks")) old.remove();
    const wait = div("one-asks one-wait");
    wait.setAttribute("aria-busy", "true");
    for (let n = 0; n < 3; n++) wait.append(document.createElement("span"));
    overlay.append(wait);
    one.panel = wait;
    placeOne();
  }

  // Up to three questions under its words, each a button; pressed, that
  // item's words in its bubble and the questions after it.
  function showAsks(view) {
    if (!one) return;
    for (const old of overlay.querySelectorAll(".one-asks")) old.remove();
    const panel = div("one-asks");
    panel.setAttribute("role", "group");
    panel.setAttribute("aria-label", whoOf(seatOf(one.seatId)));
    const mine = one;
    // Every item asked (直し34-5), or 「聞き終えました」 pressed (直し45 段3: at
    // any time): 「聞き終えました」 and one choice, 「ありがとうございました」;
    // pressed, the seat is thanked (its mark) and one to one closes.
    if (view.done) {
      panel.append(div("one-done", app.state.texts.one_words.done));
      const thanks = document.createElement("button");
      thanks.type = "button";
      thanks.className = "one-ask one-thanks";
      thanks.textContent = app.state.texts.one_words.thanks;
      thanks.addEventListener("click", async () => {
        thanks.disabled = true;
        try {
          await app.oneThanks(mine.seatId);
          if (one !== mine) return;
          refresh();
          closeOne();
        } catch (error) {
          thanks.disabled = false;
        }
      });
      panel.append(thanks);
    }
    const left = view.done ? [] : view.questions;
    for (const { item, question, rephrased } of left) {
      const ask = document.createElement("button");
      ask.type = "button";
      ask.className = "one-ask";
      ask.dataset.item = item;
      if (rephrased) ask.dataset.rephrased = "1";  // Put to this person (直し36-3).
      ask.textContent = question;
      ask.addEventListener("click", async () => {
        if (panel.classList.contains("busy")) return;
        panel.classList.add("busy");
        dropCoach(mine);  // Picked first: the coach's question for the last words is not shown.
        try {
          const answer = await app.oneAsk(mine.seatId, item);
          if (one !== mine) return;
          says(answer.pieces, answer.source, answer.kind_label);
          nextLook();  // 直し48 段6.
          // The next questions at once; the coach's question after, if it comes.
          if (answer.coach) askCoach(mine, answer.coach.ask_no);
          showAsks(answer);
          const next = overlay.querySelector(".one-asks .one-ask:not(.one-finish)");
          if (next) next.focus({ preventScroll: true });
        } catch (error) {
          panel.classList.remove("busy");
        }
      });
      panel.append(ask);
    }
    // 「聞き終えました」 at any time (直し45 段3): then 「ありがとうございました」.
    if (!view.done) {
      const finish = document.createElement("button");
      finish.type = "button";
      finish.className = "one-ask one-finish";
      finish.textContent = app.state.texts.one_words.done;
      finish.addEventListener("click", () => {
        dropCoach(mine);
        showAsks({ ...view, done: true, questions: [] });
        const thanks = overlay.querySelector(".one-asks .one-thanks");
        if (thanks) thanks.focus({ preventScroll: true });
      });
      panel.append(finish);
    }
    overlay.append(panel);
    one.panel = panel;
    placeOne();
  }

  // コーチ（AI） at one to one (直し45 段3): asked for after the person's
  // words came (never waited for: the next questions are already there); on
  // its own small board in the AI's colour and shape with its name, never
  // from the person or its bubble. Three dots while it comes; nothing when
  // it does not. Answered with the teacher's choices (and a line, or not),
  // or 答えない; then on as before.
  // 直し48 段2 (the teacher, 11/7: the band at the foot went unseen): over
  // the map by the person (placeOne: above its words, else beside it), the
  // question in a bubble from コーチ's robot, the choices and the line right
  // under the bubble.
  async function askCoach(mine, askNo) {
    const words = app.state.texts.one_coach_words;
    const board = div("one-coach waiting");
    board.setAttribute("aria-busy", "true");
    const dots = div("one-coach-dots");
    for (let n = 0; n < 3; n++) dots.append(document.createElement("span"));
    board.append(EbinoRobot.make("coach"), div("one-coach-question", ""));
    board.lastChild.append(dots);
    mine.coach = { askNo, node: board };
    for (const old of overlay.querySelectorAll(".one-coach")) old.remove();
    overlay.append(board);
    placeOne();
    let view = null;
    try {
      view = await app.oneCoach(mine.seatId, askNo);
    } catch (error) {
      view = null;
    }
    if (one !== mine || !mine.coach || mine.coach.askNo !== askNo) return;  // Moved on.
    if (!view || !view.question) return dropCoach(mine);
    board.classList.remove("waiting");
    board.removeAttribute("aria-busy");
    board.setAttribute("role", "group");
    const head = div("one-coach-head");
    // The coach's robot (直し47, robot.js; a picture only) beside its name.
    head.append(EbinoRobot.make("coach"), div("one-coach-name", view.label));
    const question = div("one-coach-question", view.question);
    question.id = `one-coach-q-${askNo}`;
    board.setAttribute("aria-labelledby", question.id);
    const note = document.createElement("input");
    note.type = "text";
    note.maxLength = 120;
    note.autocomplete = "off";
    note.placeholder = words.note;
    note.setAttribute("aria-label", words.note);
    const said = div("one-coach-message");
    said.hidden = true;
    const choices = div("one-coach-choices");
    const send = async (body) => {
      if (board.classList.contains("busy")) return;
      board.classList.add("busy");
      try {
        const done = await app.oneCoachAnswer(mine.seatId, askNo, body);
        if (done.status === "ask_again") {
          said.textContent = done.message;
          said.hidden = false;
          return;
        }
        dropCoach(mine);
        const next = overlay.querySelector(".one-asks .one-ask");
        if (next) next.focus({ preventScroll: true });
      } catch (error) {
        // As it was: it may be pressed again.
      } finally {
        board.classList.remove("busy");
      }
    };
    for (const { id, text } of view.choices) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "one-coach-choice";
      button.dataset.choice = id;
      button.textContent = text;
      button.addEventListener("click", () => send({ choice: id, note: note.value }));
      choices.append(button);
    }
    const decline = document.createElement("button");
    decline.type = "button";
    decline.className = "one-coach-decline";
    decline.textContent = words.decline;
    decline.addEventListener("click", () => send({ declined: true }));
    choices.append(decline);
    // 直し48 段3: a question asking for an answer, not a choice (one_choices:
    // まだわからない only): the line to write in first, with its own 「答える」
    // (on once something is written); then まだわからない and 答えない.
    if (view.choices.length <= 1) {
      board.classList.add("open-form");
      const answer = document.createElement("button");
      answer.type = "button";
      answer.className = "one-coach-send";
      answer.textContent = words.send;
      answer.disabled = true;
      note.addEventListener("input", () => { answer.disabled = !note.value.trim(); });
      answer.addEventListener("click", () => { if (note.value.trim()) send({ choice: "", note: note.value }); });
      board.replaceChildren(head, question, div("one-coach-write"), choices, said);
      board.querySelector(".one-coach-write").append(note, answer);
    } else board.replaceChildren(head, question, choices, note, said);
    placeOne();
  }

  // The coach's board gone (answered, not come, or another question picked).
  function dropCoach(mine) {
    if (!mine || !mine.coach) return;
    if (mine.coach.node) mine.coach.node.remove();
    mine.coach = null;
    if (one === mine) placeOne();
  }

  // 直し48 段5 (the teacher, 11/7: one question's answer can be longer than
  // the screen): past about four lines (FOLD_CHARS) the words stop at the end
  // of a sentence (。！？) and 「続きを読む」 opens the rest in place (pressed
  // again, it shuts). The words are never changed nor cut short: what shows
  // and what is folded are, together, the words as they came.
  const FOLD_CHARS = 120, FOLD_SPARE = 20;

  // Where the words stop: the last sentence end at or before FOLD_CHARS (not
  // before half of it), else the first after it; null when they are short
  // enough, or the rest would be only a little.
  function foldAt(text, limit = FOLD_CHARS) {
    const chars = [...text];
    if (chars.length <= limit + FOLD_SPARE) return null;
    const ends = [];
    chars.forEach((c, n) => { if ("。！？!?".includes(c)) ends.push(n + 1); });
    const before = ends.filter((n) => n <= limit && n >= limit / 2);
    const at = before.length ? before[before.length - 1] : ends.find((n) => n > limit);
    return at && chars.length - at >= FOLD_SPARE ? at : null;
  }

  // The pieces (each a line of its own), folded where foldAt says: the piece
  // the fold is in split there, the rest hidden, and the button after them.
  // limit: about four lines of the bubble as wide as it may be (the screen
  // check: on a narrow map 120 characters were six lines).
  function foldPieces(texts, bubble, limit = FOLD_CHARS) {
    const at = foldAt(texts.join(""), limit);
    if (at === null) return texts.map((text) => div("one-piece", text));
    const words = app.state.texts.one_words;
    const nodes = [], rest = [];
    let seen = 0;
    for (const text of texts) {
      const chars = [...text];
      if (seen >= at) {
        const node = div("one-piece one-rest", text);
        rest.push(node);
        nodes.push(node);
      } else if (seen + chars.length <= at) {
        nodes.push(div("one-piece", text));
      } else {
        const node = div("one-piece", chars.slice(0, at - seen).join(""));
        const more = document.createElement("span");
        more.className = "one-rest";
        more.textContent = chars.slice(at - seen).join("");
        node.append(more);
        rest.push(more);
        nodes.push(node);
      }
      seen += chars.length;
    }
    const id = `one-rest-${++foldCount}`;
    rest.forEach((node, n) => { node.hidden = true; node.id = `${id}-${n}`; });
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "one-more";
    toggle.textContent = words.read_more;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", rest.map((node) => node.id).join(" "));
    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") !== "true";
      for (const node of rest) node.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      toggle.textContent = open ? words.read_less : words.read_more;
      bubble.classList.toggle("unfolded", open);
      placeOne();
    });
    nodes.push(toggle);
    return nodes;
  }
  let foldCount = 0;

  // Its words in its bubble: the item's pieces, as spoken words where they
  // were let through (a small mark says so), as recorded otherwise (a
  // slide's page tidied, 直し43). Each piece on a line of its own: they part
  // where a sentence ends, never run into one another.
  function says(pieces, source, kindLabel = "") {
    if (!one || !one.bubble) return;
    const voice = one.bubble.querySelector(".voice");
    // Its kind's small line over the words (直し45 段1), or none.
    for (const old of one.bubble.querySelectorAll(".kind")) old.remove();
    voice.before(...kindOf({ kind_label: kindLabel }));
    // About four lines of the widest the bubble may be (placeOne's 「most」, 18px a character).
    const most = Math.min(overlay.getBoundingClientRect().width * 0.5, 28 * 18);
    const limit = Math.min(FOLD_CHARS, 4 * Math.max(10, Math.floor((most - 32) / 18)));
    voice.replaceChildren(...foldPieces(pieces.map((piece) => piece.spoken || piece.text), one.bubble, limit));
    const spoken = pieces.some((piece) => piece.spoken);
    one.bubble.classList.toggle("spoken", spoken);
    const mark = one.bubble.querySelector(".spoken-mark");
    if (spoken && !mark) one.bubble.prepend(div("spoken-mark", app.state.texts.spoken_mark));
    if (!spoken && mark) mark.remove();
    one.bubble.querySelector(".who").textContent = [whoOf(seatOf(one.seatId)), source && source.note].filter(Boolean).join("　");
    one.bubble.classList.remove("not-found");
    for (const old of overlay.querySelectorAll(".one-card")) old.remove();  // Its words now, no card to make.
    placeOne();
  }

  // The person's words by its head, on the side with room (right first),
  // inside the frame; what one to one adds under them (直し34-4) below.
  function placeOne() {
    if (!one || !one.bubble) return;
    const frameBox = overlay.getBoundingClientRect();
    const [hx, hy] = toFrame(one.home[0], one.home[1] - EbinoPerson.HEIGHT * 0.9 * one.scale);
    // The person's own outline as it stands (its hand up included), not as
    // it is while standing up: the bubble keeps clear of it.
    const bb = one.group.firstElementChild.getBBox();
    const [rx] = toFrame(one.home[0] + (bb.x + bb.width) * one.scale, one.home[1]);
    const [lx] = toFrame(one.home[0] + bb.x * one.scale, one.home[1]);
    const bubble = one.bubble;
    // Right of the person where its words fit, else left; with room on
    // neither side as wide as they would be, narrower on the wider side.
    const most = Math.min(frameBox.width * 0.5, 28 * 18);
    const roomRight = frameBox.width - 8 - (rx + 12), roomLeft = lx - 12 - 8;
    bubble.style.maxWidth = `${Math.floor(most)}px`;
    let { width } = bubble.getBoundingClientRect();
    const right = width <= roomRight || (width > roomLeft && roomRight >= roomLeft);
    if (width > (right ? roomRight : roomLeft)) {
      bubble.style.maxWidth = `${Math.floor(Math.max(120, right ? roomRight : roomLeft))}px`;
      width = bubble.getBoundingClientRect().width;
    }
    const { height } = bubble.getBoundingClientRect();
    const left = right ? Math.min(rx + 12, frameBox.width - 8 - width) : Math.max(8, lx - 12 - width);
    const top = Math.min(Math.max(8, hy - 12), frameBox.height - height - 8);
    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;
    bubble.classList.toggle("left", left < hx);
    // The questions under the words; with no room there, above them, then
    // beside them: the first spot inside the frame that covers neither the
    // words nor the person (else the one that covers least).
    const [, py] = toFrame(one.home[0], one.home[1] + bb.y * one.scale);
    const [, fy] = toFrame(one.home[0], one.home[1]);
    // What is kept clear, each with its weight: the person's words most,
    // then the questions to pick, then the person.
    const taken = [[left, top, width, height, 3], [lx, py, rx - lx, fy - py, 1]];
    // node at the first of spots (made from its size) inside the frame that
    // covers none of taken, else at the one that covers least; then taken too.
    const spot = (node, spotsFor) => {
      const p = node.getBoundingClientRect();
      const clampL = (x) => Math.max(8, Math.min(x, frameBox.width - p.width - 8));
      const clampT = (y) => Math.max(8, Math.min(y, frameBox.height - p.height - 8));
      const covered = ([x, y]) => taken.reduce((sum, [l, t, w, h, k]) =>
        sum + k * Math.max(0, Math.min(x + p.width, l + w) - Math.max(x, l)) * Math.max(0, Math.min(y + p.height, t + h) - Math.max(y, t)), 0);
      const spots = spotsFor(p).map(([x, y]) => [clampL(x), clampT(y)]);
      const [x, y] = spots.reduce((best, at) => (covered(at) < covered(best) ? at : best));
      return { x, y, w: p.width, h: p.height, cost: covered([x, y]) };
    };
    const put = (node, at) => {
      node.style.left = `${at.x}px`;
      node.style.top = `${at.y}px`;
      taken.push([at.x, at.y, at.w, at.h, 2]);
    };
    const panel = one.panel;
    if (panel && panel.isConnected) {
      panel.style.maxWidth = `${Math.floor(Math.min(frameBox.width * 0.46, 24 * 16))}px`;
      put(panel, spot(panel, (p) => [[left, top + height + 10], [left, top - p.height - 10],
        [left + width + 10, top], [left - p.width - 10, top],
        // Beside the person, the other side from its words.
        [rx + 12, top], [rx + 12, fy - p.height], [lx - p.width - 12, top], [lx - p.width - 12, fy - p.height]]));
    }
    // コーチ（AI）'s board (直し48 段2: no more in the band at the foot, where
    // it went unseen): by the person, where the eye is: above its words,
    // else beside the person, else the frame's top corners; over none of the
    // words, the person or the questions when it can.
    const board = one.coach && one.coach.node;
    if (board && board.isConnected) {
      // As wide as 30em where that covers nothing, else narrower (taller) if that does.
      let best = null;
      for (const em of [30, 24, 20]) {
        board.style.maxWidth = `${Math.floor(Math.min(frameBox.width - 16, em * 16))}px`;
        const at = spot(board, (c) => [[left, top - c.height - 12], [lx - c.width - 12, top], [rx + 12, top],
          [left + width - c.width, top - c.height - 12], [left + width + 12, top], [left - c.width - 12, top],
          [8, 8], [frameBox.width - c.width - 8, 8], [8, frameBox.height - c.height - 8],
          [frameBox.width - c.width - 8, frameBox.height - c.height - 8]]);
        if (!best || at.cost < best.at.cost) best = { at, em };
        if (!at.cost) break;
      }
      board.style.maxWidth = `${Math.floor(Math.min(frameBox.width - 16, best.em * 16))}px`;
      put(board, best.at);
    }
  }

  // One to one's own parts gone (the table cleared, or closed).
  function endOne() {
    const { token, group, flight } = one;
    one = null;
    for (const node of overlay.querySelectorAll(".one-bubble, .one-asks")) node.remove();
    for (const node of overlay.querySelectorAll(".one-coach")) node.remove();
    if (group) group.remove();
    if (flight) flight.cancel();
    if (token) token.node.classList.remove("one-self", "stood");
    frame.classList.remove("one-on");
    document.body.classList.remove("one-open");
    $("map-back").textContent = app.state.texts.map_buttons.back.text;
    app.setNow({ one: false });
  }

  // 「円卓にもどす」 or Esc: the person a seat again, the camera back, the table as it was.
  async function closeOne() {
    if (!one) return;
    const seatId = one.seatId;
    endOne();
    app.backToEveryone();
    await moveTo({ x: 0, y: 0, w: view.W, h: view.H }, reduced() ? 0 : BACK_FOR);
    relayout();
    const card = overlay.querySelector(`.table-bubble[data-seat="${seatId}"]:not(.unplaced)`);
    if (card) card.focus({ preventScroll: true });
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

  // Laid out again where the map now stands (直し32-1): the drawer or the
  // card of whose words are in moved it, or came over its side.
  function layoutAgain() {
    if (!view) return;
    rescale();
    relayout();
  }

  return { init, show, round, refresh, marked, markOf, layoutAgain, asked };
})();
