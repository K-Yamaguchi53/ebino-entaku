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
  // Quicker since 直し31-6 (were 1100, 1100, 160): the table is there sooner.
  const CAMERA_FOR = 700, FLY_FOR = 700, FLY_GAP = 90, BACK_FOR = 700;
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
  const TEXT_PX = { place: 11, school: 12, home: 12 };
  // The seats' homes (直し33-3): 地域で働く大人 at their places on the map;
  // 県外・海外に出た人 by a way out at the map's upper right corner, GATE_COLUMNS
  // to a row, at most GATE_ROWS rows; 探究をした先輩 at the school's windows;
  // 外から来た大人・先生, and whoever the map and the school have no room for,
  // on the ground, one to a square. HOME_STEP CSS px between two side by side.
  const HOME_STEP = 16, GATE_COLUMNS = 5, GATE_ROWS = 4;
  // The school (直し25-1). Its 3D picture: at the whole map a share of the
  // drawing's width (about 86px on a PC's full screen, the size 19d drew it for),
  // nearer in as the ground grows, but never under SCHOOL_MIN_PX nor over
  // SCHOOL_MAX_PX on screen. Its name never over SCHOOL_TEXT_MAX_PX, and the
  // line mark (with no picture) never over SCHOOL_MARK_MAX_PX across.
  const SCHOOL_SHARE = 0.072, SCHOOL_MIN_PX = 56, SCHOOL_MAX_PX = 130;
  const SCHOOL_TEXT_MAX_PX = 24, SCHOOL_MARK_MAX_PX = 64;
  // The one drawing (直し33-2): the map on the left and the school with its
  // sports ground on the right (on an upright screen the map on top, the
  // school under it), both as large as the room lets them be; the room left
  // round them is the round table's and its cards' (直し33-4).
  const MAP_SHARE = 0.56;  // Landscape: the map at most this part of the room's width,
  const YARD_SHARE = 0.56;  // the yard at most this part of its height (the AI's seat under it).
  const MAP_SHARE_UP = 0.52;  // Upright: the map at most this part of the room's height,
  const AI_BAND_UP = 0.26;  // and this part at its foot left for the AI's seat (直し33-4: the room keeps its size).
  const ROOM_GAP = 16;  // CSS px between the map and the yard.
  const UPRIGHT_UNDER = 1.4;  // A room narrower than this (width to height): the yard under the map.
  const RECOMPOSE = 0.03;  // The room's shape this much off the drawing's: it is drawn again.
  // With no picture of the school (直し33-2): a plain building and its ground,
  // no name, in its own units; its windows (two rows on the building's
  // front) and its ground's corners are where seats go, as on the picture.
  const PLAIN_YARD = { width: 1400, height: 760, field: [[40, 150], [560, 150], [560, 720], [40, 720]],
    roof: [[680, 290], [1360, 290], [1360, 540], [680, 540]], wall: 110, rows: [565, 615], columns: 20 };
  // The track on the ground with no picture (直し35-1), in metres as the
  // school's model has it (build_school.py: the field 96.2 m east-west by
  // 126.5 m north-south, an oval of two straights and two half circles,
  // four lanes): drawn on the field's four corners as they are.
  const TRACK = { field: [96.2, 126.5], rOut: 42, half: 16, lanes: 4, lane: 1.25, segs: 24 };
  const WORD_PAD = 2;  // CSS px kept clear round a word drawn on the map.
  const SLIDE_MOST = 40;  // CSS px the school's name may slide off a seat's point.
  // Where a seat's 「？」 may go, by its point (x, y, which way the text runs
  // from there), in the order tried: upper right first.
  const ASK_CORNERS = [[9, -6, "start"], [-9, -6, "end"], [9, 16, "start"], [-9, 16, "end"]];

  let map = null;  // The drawing from /api/setup.
  let app = null;  // What app.js lends: state, cardEntry, renderSeats, shownQuotes.
  let svg, overlay, frame;
  let lastSeats = [];  // The seats as last drawn, to draw them again (直し33-2).
  let yardPicture = null;  // The school's large picture once it has loaded (直し33-2).
  let view = null;  // How the map's (x, y) reach the drawing (flatView, reliefView).
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
    controls();
    const go = () => {
      if (!map.relief) return build(seats, false);
      const picture = new Image();
      picture.onload = () => build(seats, true);
      picture.onerror = () => build(seats, false);
      picture.src = map.relief.image;
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
  // plain one's, in its own units.
  function yardModel() {
    if (yardPicture) return { picture: true, ...yardPicture };
    const { width, height, field, roof, rows, columns } = PLAIN_YARD;
    const [left, right] = [roof[0][0] + 24, roof[1][0] - 24];
    const windows = rows.flatMap((y) => Array.from({ length: columns },
      (_, k) => [left + (right - left) * k / (columns - 1), y]));
    return { picture: false, width, height, field, roof, windows };
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

  // Where the map (mapW x mapH, kept in its own units) and the yard ({ width,
  // height }) go in a room ({ w, h } CSS px): the drawing's size W x H (the
  // room's shape), the map's corner, the yard's corner and scale, the column
  // the yard is in. It reads nothing but what it is given.
  function compose(room, mapW, mapH, yard) {
    const upright = room.w / room.h < UPRIGHT_UNDER;
    let mw, mh;
    if (!upright) {
      mh = room.h;
      mw = mh * mapW / mapH;
      if (mw > room.w * MAP_SHARE) [mw, mh] = [room.w * MAP_SHARE, room.w * MAP_SHARE * mapH / mapW];
    } else {
      mw = room.w;
      mh = mw * mapH / mapW;
      if (mh > room.h * MAP_SHARE_UP) [mw, mh] = [room.h * MAP_SHARE_UP * mapW / mapH, room.h * MAP_SHARE_UP];
    }
    const u = mapW / mw;  // The drawing's units to a CSS px.
    const ratio = yard.height / yard.width;
    let mx, my, yx, yy, yw, column;
    if (!upright) {
      [mx, my] = [0, (room.h - mh) / 2];
      const left = mw + ROOM_GAP, free = room.w - left;
      yw = Math.min(free - ROOM_GAP, room.h * YARD_SHARE / ratio);
      [yx, yy] = [left + (free - yw) / 2, Math.max(8, room.h * 0.04)];
      column = [left, room.w];
    } else {
      [mx, my] = [(room.w - mw) / 2, 0];
      const top = mh + ROOM_GAP, free = room.h * (1 - AI_BAND_UP) - top;
      yw = Math.min(room.w * 0.94, (free - ROOM_GAP) / ratio);
      [yx, yy] = [(room.w - yw) / 2, top + (free - yw * ratio) / 2];
      column = [0, room.w];
    }
    return { W: room.w * u, H: room.h * u, upright, map: [mx * u, my * u],
      yard: { x: yx * u, y: yy * u, k: yw * u / yard.width }, column: column.map((v) => v * u) };
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

  function draw(seats, withRelief) {
    svg.replaceChildren();
    overlay.replaceChildren();
    for (const id of Object.keys(points)) delete points[id];
    tokens = [];
    schoolGroup = null;
    const base = withRelief ? reliefView(map.relief) : flatView();
    const model = yardModel();
    const laid = compose(roomSize(), base.W, base.H, model);
    const [ox, oy] = laid.map;
    view = { ...base, W: laid.W, H: laid.H, upright: laid.upright, yard: { ...laid.yard, model }, column: laid.column,
      unit: laid.W / roomSize().w,
      mapBox: [ox, oy, base.W, base.H],
      proj: (...at) => {
        const [x, y] = base.proj(...at);
        return [x + ox, y + oy];
      } };
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
      const image = layer("relief-image");
      image.append(svgEl("image", { href: map.relief.image, x: ox, y: oy, width: base.W, height: base.H }));
    }
    // The school and its ground, beside the map (直し33-2).
    drawYard(layer("yard"));
    const fill = layer("basin-fill");
    const rimLine = view.relief ? dense(map.boundary, true).map(([x, y]) => P(x, y, 1)) : map.boundary.map(([x, y]) => P(x, y));
    fill.append(svgEl("polygon", { points: rimLine.map((p) => p.join(",")).join(" ") }));

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

    splitLayer = layer("split-lines");
    // The school's picture, when it comes, under the points: no seat is hidden under it.
    const pictureLayer = layer("school-picture");
    // Each seat at its home (直し33-3), worked out from the seat table each
    // time it is drawn: 地域で働く大人 at their places, the others by the way
    // out, at the school's windows and on its ground (homesOf).
    const placed = seats.filter((seat) => seat.x !== undefined);
    const homes = homesOf(placed.map((seat) => ({ id: seat.seat_id, kind: seat.kind,
      at: seat.outer ? null : view.relief ? P(seat.x, seat.y, 1.5) : P(seat.x, seat.y) })), homePlace());
    drawGate(layer("home-gate"), homes.gate);
    const seatLayer = layer("points");
    for (const seat of placed) {
      const node = drawPoint(seat);
      const spot = homes.spots[seat.seat_id];
      points[seat.seat_id] = { node, seat, at: () => spot };
      seatLayer.append(node);
    }
    // Each home's name where it is, in the words of the seat list's headings
    // (in place of the map's four corners' boxes).
    const homeNames = layer("home-names");
    for (const { kind, at, anchor } of homes.names) {
      const words = app.state.kinds[kind];
      if (!words) continue;
      const text = svgEl("text", { class: `kind-${kind}`, x: at[0], y: at[1], "text-anchor": anchor, "data-px": TEXT_PX.home });
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
    if (model.picture) {
      building.append(svgEl("image", { href: model.image, width: model.width, height: model.height }));
      group.append(building);
      return;
    }
    group.classList.add("plain");
    const polygon = (className, spots) => svgEl("polygon", { class: className, points: spots.map((p) => p.join(",")).join(" ") });
    const [nw, ne, se, sw] = model.roof, wall = PLAIN_YARD.wall;
    group.append(polygon("yard-ground", model.field));
    const track = trackOn(model.field);
    group.append(svgEl("path", { class: "yard-track", "fill-rule": "evenodd",
      d: [track.lanes[track.lanes.length - 1], track.lanes[0]].map((ring) => `M${ring.map((p) => p.join(",")).join("L")}Z`).join("") }));
    group.append(polygon("yard-infield", track.lanes[0]));
    for (const ring of track.lanes) group.append(polygon("yard-line", ring));
    group.append(svgEl("line", { class: "yard-line", x1: track.middle[0][0], y1: track.middle[0][1],
      x2: track.middle[1][0], y2: track.middle[1][1] }));
    building.append(polygon("yard-wall", [sw, se, [se[0], se[1] + wall], [sw[0], sw[1] + wall]]), polygon("yard-roof", [nw, ne, se, sw]));
    for (const [wx, wy] of model.windows) {
      building.append(svgEl("rect", { class: "yard-window", x: wx - 9, y: wy - 14, width: 18, height: 28, rx: 2 }));
    }
    group.append(building);
  }

  // The track's lane lines (inner first) and the straight across its
  // middle, on a field given by its corners (north-west, north-east,
  // south-east, south-west): each spot in metres taken to the field's
  // corners as they are drawn. It reads nothing but what it is given.
  function trackOn([nw, ne, se, sw]) {
    const [fw, fl] = TRACK.field;
    const at = (mx, my) => {  // metres from the field's middle, east and north
      const u = 0.5 + mx / fw, v = 0.5 - my / fl;
      const top = [nw[0] + (ne[0] - nw[0]) * u, nw[1] + (ne[1] - nw[1]) * u];
      const foot = [sw[0] + (se[0] - sw[0]) * u, sw[1] + (se[1] - sw[1]) * u];
      return [top[0] + (foot[0] - top[0]) * v, top[1] + (foot[1] - top[1]) * v].map((n) => Math.round(n * 10) / 10);
    };
    const ring = (r) => {
      const spots = [];
      for (let k = 0; k <= TRACK.segs; k++) {
        const t = Math.PI * k / TRACK.segs;
        spots.push(at(r * Math.cos(t), TRACK.half + r * Math.sin(t)));
      }
      for (let k = 0; k <= TRACK.segs; k++) {
        const t = Math.PI + Math.PI * k / TRACK.segs;
        spots.push(at(r * Math.cos(t), -TRACK.half + r * Math.sin(t)));
      }
      return spots;
    };
    const rIn = TRACK.rOut - TRACK.lanes * TRACK.lane;
    const lanes = [];
    for (let k = 0; k <= TRACK.lanes; k++) lanes.push(ring(rIn + k * TRACK.lane));
    return { lanes, middle: [at(-rIn, 0), at(rIn, 0)] };
  }

  // What homesOf needs of the drawing as it is: the map's box, the yard's
  // place and model, and the drawing's units to a CSS px.
  function homePlace() {
    // A point's radius at the whole drawing (pointScale and shape()).
    return { mapBox: view.mapBox, yard: view.yard, unit: view.unit, r: Math.max(MIN_POINT_PX * view.unit, POINT_R * view.S) };
  }

  // Where each seat lives (直し33-3), in the drawing's units, from the seats
  // as given ({ id, kind, at: its spot on the map or null }) in their order:
  // 地域で働く大人 with a spot there; 県外・海外に出た人 in rows by the way out
  // (GATE_COLUMNS × GATE_ROWS); 探究をした先輩 at the school's windows, one to
  // a window (a window nearer than a point's width to one taken stays empty);
  // then 外から来た大人・先生 first and everyone else left on the
  // ground, one to a square. Returns { spots: id -> [x, y], gate, names:
  // [{ kind, at, anchor }], counts }. The same seats give the same homes. It
  // reads nothing but what it is given.
  function homesOf(seats, place) {
    const { mapBox: [mx, my, mw], yard: { x: yx, y: yy, k, model }, unit, r } = place;
    const step = Math.max(HOME_STEP * unit, 2.4 * r);
    const inYard = ([px, py]) => [yx + px * k, yy + py * k];
    const windows = [], field = model.field.map(inYard);
    for (const spot of model.windows.map(inYard)) {
      if (windows.every(([x, y]) => Math.hypot(x - spot[0], y - spot[1]) >= 2.2 * r)) windows.push(spot);
    }
    const gate = [mx + mw - step * 1.4, my + step * 2.4];
    const spots = {}, counts = { map: 0, gate: 0, windows: 0, ground: 0 }, ground = [];
    for (const seat of seats) {
      if (seat.kind === "adult" && seat.at) {
        spots[seat.id] = seat.at;
        counts.map += 1;
      } else if (seat.kind === "cross" && counts.gate < GATE_COLUMNS * GATE_ROWS) {
        const column = counts.gate % GATE_COLUMNS, row = Math.floor(counts.gate / GATE_COLUMNS);
        spots[seat.id] = [gate[0] - (column + 1.6) * step, gate[1] + (row + 0.2) * step];
        counts.gate += 1;
      } else if (seat.kind === "poster" && counts.windows < windows.length) {
        spots[seat.id] = windows[counts.windows];
        counts.windows += 1;
      } else ground.push(seat);
    }
    const first = ground.filter((seat) => seat.kind === "outsider_teacher");
    const squares = groundSquares(field, ground.length, step, 2.2 * r);
    [...first, ...ground.filter((seat) => seat.kind !== "outsider_teacher")].forEach((seat, n) => {
      spots[seat.id] = squares[n];
    });
    counts.ground = ground.length;
    const kinds = new Set(seats.map((seat) => seat.kind));
    const xs = windows.map((p) => p[0]), top = Math.min(...windows.map((p) => p[1]));
    const names = [];
    if (counts.map) names.push({ kind: "adult", at: [mx + step * 0.6, my + step * 1.3], anchor: "start" });
    if (counts.gate) names.push({ kind: "cross", at: [gate[0] + step * 0.6, gate[1] - step * 0.9], anchor: "end" });
    if (kinds.has("poster")) {
      names.push({ kind: "poster", at: [(Math.min(...xs) + Math.max(...xs)) / 2, Math.max(step, top - step * 2)], anchor: "middle" });
    }
    if (first.length || ground.length) {
      const [nw, ne] = field;
      names.push({ kind: "outsider_teacher", at: [(nw[0] + ne[0]) / 2, Math.max(step, Math.min(nw[1], ne[1]) - step * 0.5)],
        anchor: "middle" });
    }
    return { spots, gate, names, counts };
  }

  // n squares on a ground (its four corners: north-west, north-east,
  // south-east, south-west), step apart where it is large enough (closer
  // where it is not, but never under least: then the block goes past the
  // ground's edge rather than two touching), the block in its middle, row by
  // row from the north. It reads nothing but what it is given.
  function groundSquares([nw, ne, se, sw], n, step, least = 0) {
    if (!n) return [];
    const wide = Math.hypot(ne[0] - nw[0], ne[1] - nw[1]), deep = Math.hypot(sw[0] - nw[0], sw[1] - nw[1]);
    const most = Math.max(1, Math.floor(wide / Math.max(least, Math.min(step, wide / 2))) - 1);
    const columns = Math.min(most, n, Math.max(1, Math.ceil(Math.sqrt(n * wide / deep))));
    const rows = Math.ceil(n / columns);
    const across = Math.max(least, Math.min(step, wide / (columns + 1))), down = Math.max(least, Math.min(step, deep / (rows + 1)));
    const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    return Array.from({ length: n }, (_, m) => {
      const c = m % columns, r = Math.floor(m / columns);
      const u = 0.5 + (c - (columns - 1) / 2) * across / wide, v = 0.5 + (r - (rows - 1) / 2) * down / deep;
      return mix(mix(nw, ne, u), mix(sw, se, u), v);
    });
  }

  // The way out (直し33-3): a doorway at the map's upper right corner, open
  // outward, in 県外・海外に出た人's colour; no words (its name is by it).
  function drawGate(group, [x, y]) {
    const s = view.unit;
    group.setAttribute("aria-hidden", "true");
    group.classList.add("kind-cross");
    group.append(svgEl("path", { class: "door", d: `M ${x - 5 * s} ${y + 9 * s} V ${y - 8 * s} H ${x + 5 * s} V ${y + 9 * s}` }),
      svgEl("path", { class: "out", d: `M ${x - 2 * s} ${y + 3 * s} L ${x + 9 * s} ${y - 8 * s} M ${x + 3 * s} ${y - 8 * s} H ${x + 9 * s} V ${y - 2 * s}` }));
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
    draw(lastSeats, view.relief);
    for (const id of lit) if (points[id]) points[id].node.classList.add("lit");
    if (reopen) openTable(reopen.result, reopen.order, tableCenter(), () => true, true);
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

  function rescale() {
    const f = pointScale();
    const perPx = vb.w / (frame.clientWidth || 1);
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
    const reach = 9.5 * pointScale() * frameBox.width / vb.w;
    const seats = tableTop ? [] : roundSeats.map((id) => toFrame(...spotOf(id)))
      .map(([px, py]) => [px - reach, py - reach, 2 * reach, 2 * reach]);
    // While the table is open the map's words are not shown (直し33-5): nothing to keep off.
    const words = tableTop ? [] : [...svg.querySelectorAll(".place-names text, .home-names text, .school text, .school > :not(text), " +
      ".school-picture image")].map((node) => boxIn(node, frameBox));
    const cover = tableTop && tableTop.map(([x, y]) => toFrame(x, y));
    // The arrow and the four ways' names (直し25-3), once they are put.
    const around = withAround ? [...overlay.querySelectorAll(".map-compass, .map-around, .map-hint")].map((node) => boxIn(node, frameBox)) : [];
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
    placeYardColumn();
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
    // The headings first.
    put([...overlay.querySelectorAll(".split-tag")], (items) => planLabels(frameSize, items, fixed));
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
  }

  // The yard's column on screen, for what the one screen puts in it (the
  // AI's seat, under the yard: style.css --yard-left, --yard-w).
  function placeYardColumn() {
    const stage = frame.closest(".stage");
    if (!stage) return;
    const s = stage.getBoundingClientRect(), f = frame.getBoundingClientRect();
    const [x0, x1] = view.column.map((x) => f.left - s.left + x / view.W * f.width);
    stage.style.setProperty("--yard-left", `${Math.round(x0)}px`);
    stage.style.setProperty("--yard-w", `${Math.round(x1 - x0)}px`);
    // Upright: the band at the room's foot, over which the AI's seat sits.
    stage.style.setProperty("--room-foot", `${Math.round(s.bottom - f.bottom)}px`);
    stage.style.setProperty("--ai-band", `${Math.round(f.height * AI_BAND_UP)}px`);
  }

  // A 「？」 by its seat, at the first of its four corners that covers no word
  // drawn on the map (a place name, a home's name, the school's); with none
  // free, the one that covers least. Measured on screen, as the zoom is now.
  function placeAskMarks() {
    const marks = [...svg.querySelectorAll(".pt.silent .ask-mark")];
    if (!marks.length) return;
    const words = [...svg.querySelectorAll(".place-names text, .home-names text, .school text, .school-picture image")]
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

  // Where the seats gather (直し33-4): the table's middle where the map
  // meets the school (upright: between the two), and its own flat
  // projection there (the table's units, as on the basin before, to the
  // drawing's), whatever the seats' homes.
  const tableCenter = () => gatherAt({ W: view.W, H: view.H, mapBox: view.mapBox, upright: view.upright, unit: view.unit });

  // The gathering's middle and projection for a drawing ({ W, H, mapBox,
  // upright, unit }). It reads nothing but what it is given.
  function gatherAt({ W, H, mapBox: [mx, my, mw, mh], upright, unit }) {
    const [cx, cy] = upright ? [W / 2, my + mh + ROOM_GAP * unit / 2] : [mx + mw + ROOM_GAP * unit / 2, H / 2];
    const across = Math.min(W, H * 1.6) / unit * TABLE_PART;
    const s = Math.min(Math.max(across, TABLE_PX_MOST[0]), TABLE_PX_MOST[1]) * unit / TABLE_RX;
    return { x: 0, y: 0, level: 0, at: [cx, cy], scale: s,
      proj: (x, y, lift = 0) => [cx + x * s, cy + y * s * TABLE_TILT - lift * s * TABLE_TILT] };
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
  function gatherSpots(sittings, center, { W, H, unit, upright }) {
    const [cx, cy] = center.at, card = GATHER_CARD;
    const step = (card.h + card.gap) * unit, margin = 6 * unit;
    const half = (TABLE_RX + 18) * center.scale + 22 * unit;  // The table's side and a little room.
    const foot = upright ? H * (1 - AI_BAND_UP) - margin : H - margin;
    const limits = { left: foot, right: upright ? foot : H * (1 - AI_ROOM) - margin };
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
    const top = svgEl("g", { class: "table-top-group" });
    const [lx, ly] = center.proj(center.x, center.y, TABLE_LIFT, center.level);
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
      top.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 400, easing: "ease-out" });
      await wait(200);
      if (!still()) return;
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
    const spots = gatherSpots(seats.filter((sitting) => sitting.group !== "front"), center,
      { W: view.W, H: view.H, unit: view.unit, upright: view.upright });
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
      card.dataset.side = token.side;  // Its card goes this side of it first (直し33-4).
      card.dataset.rank = String(rank.indexOf(id));
      overlay.append(card, seatPress(id, token.at));
    });
    // The split's heading: under the map, over neither the table's top nor
    // its chairs; on a map narrower than TAG_ON_MAP, in the split block only.
    // It wraps after its 「：」 or between its 「…」, never inside one (app.phrased).
    if (split && overlay.clientWidth >= TAG_ON_MAP) $("map-heading").replaceChildren(app.phrased(app.shownQuotes(split.heading)));
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
    node.append(div("voice", voiceOf(quote)), div("who", whoOf(seatOf(seatId))));
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
    moveTo({ x: 0, y: 0, w: view.W, h: view.H }, BACK_FOR);
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
      await Promise.all(back);
      if (mine !== roundNo) return;
    }
    clearTable();
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
    one = { seatId, home, token, group: null, words: card ? card.querySelector(".voice").textContent : "",
      spoken: Boolean(card && card.classList.contains("spoken")) };
    const mine = one;
    frame.classList.add("one-on");
    // The AI's seat steps back too (直し34-3: it covered the person's feet and words).
    document.body.classList.add("one-open");
    $("map-back").textContent = app.state.texts.one_words.back;
    app.setNow({ one: true });
    app.askSeat(seatId);  // The box at the foot writes to this person.
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
    // Near it, the person's feet low in the frame, room for its words beside it.
    const w = view.W / ONE_ZOOM, h = w * view.H / view.W;
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
    bubble.append(voice, div("who", whoOf(seatOf(one.seatId))));
    overlay.append(bubble);
    one.bubble = bubble;
    placeOne();
    // The questions to pick from (直し34-4), asked for while it stands up.
    const mine = one;
    // The keyboard goes to the first of them (直し34-5: it was six Tabs away).
    app.oneOpen(mine.seatId).then((view) => {
      if (one !== mine) return;
      showAsks(view);
      const first = overlay.querySelector(".one-asks .one-ask");
      if (first) first.focus({ preventScroll: true });
    }, () => {});
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
    // Every item asked (直し34-5): 「聞き終えました」 and one choice,
    // 「ありがとうございました」; pressed, the seat is thanked (its mark) and
    // one to one closes.
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
    for (const { item, question } of view.questions) {
      const ask = document.createElement("button");
      ask.type = "button";
      ask.className = "one-ask";
      ask.dataset.item = item;
      ask.textContent = question;
      ask.addEventListener("click", async () => {
        if (panel.classList.contains("busy")) return;
        panel.classList.add("busy");
        try {
          const answer = await app.oneAsk(mine.seatId, item);
          if (one !== mine) return;
          says(answer.pieces, answer.source);
          showAsks(answer);
          const next = overlay.querySelector(".one-asks .one-ask");
          if (next) next.focus({ preventScroll: true });
        } catch (error) {
          panel.classList.remove("busy");
        }
      });
      panel.append(ask);
    }
    overlay.append(panel);
    one.panel = panel;
    placeOne();
  }

  // Its words in its bubble: the item's pieces, as spoken words where they
  // were let through (a small mark says so), as recorded otherwise.
  function says(pieces, source) {
    if (!one || !one.bubble) return;
    const voice = one.bubble.querySelector(".voice");
    voice.textContent = pieces.map((piece) => piece.spoken || piece.text).join("");
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

  // A question written (app.sendOne): found, its words; not, the teacher's
  // line and 「質問カードにする」, which makes it a card to the person.
  function oneAnswer(answer, question) {
    if (!one) return;
    if (answer.found) {
      says(answer.pieces, answer.source);
    } else {
      one.bubble.querySelector(".voice").textContent = app.state.texts.one_words.not_found;
      // Only who it is: no words of theirs, so no source and no spoken mark.
      one.bubble.querySelector(".who").textContent = whoOf(seatOf(one.seatId));
      one.bubble.classList.remove("spoken");
      const mark = one.bubble.querySelector(".spoken-mark");
      if (mark) mark.remove();
      one.bubble.classList.add("not-found");
      const mine = one;
      const card = document.createElement("button");
      card.type = "button";
      card.className = "one-card";
      card.textContent = app.state.texts.one_words.to_card;
      card.addEventListener("click", async () => {
        card.disabled = true;
        try {
          await app.cardFromOne(mine.seatId, question);
          card.remove();
        } catch (error) {
          card.disabled = false;
        }
      });
      for (const old of overlay.querySelectorAll(".one-card")) old.remove();
      one.bubble.append(card);
    }
    showAsks(answer);
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
    const panel = one.panel;
    if (!panel || !panel.isConnected) return;
    panel.style.maxWidth = `${Math.floor(Math.min(frameBox.width * 0.46, 24 * 16))}px`;
    const p = panel.getBoundingClientRect();
    const [, py] = toFrame(one.home[0], one.home[1] + bb.y * one.scale);
    const [, fy] = toFrame(one.home[0], one.home[1]);
    const taken = [[left, top, width, height], [lx, py, rx - lx, fy - py]];
    const clampL = (x) => Math.max(8, Math.min(x, frameBox.width - p.width - 8));
    const clampT = (y) => Math.max(8, Math.min(y, frameBox.height - p.height - 8));
    const spots = [[left, top + height + 10], [left, top - p.height - 10],
      [left + width + 10, top], [left - p.width - 10, top],
      // Beside the person, the other side from its words.
      [rx + 12, top], [rx + 12, fy - p.height], [lx - p.width - 12, top], [lx - p.width - 12, fy - p.height]]
      .map(([x, y]) => [clampL(x), clampT(y)]);
    const covered = ([x, y]) => taken.reduce((sum, [l, t, w, h]) =>
      sum + Math.max(0, Math.min(x + p.width, l + w) - Math.max(x, l)) * Math.max(0, Math.min(y + p.height, t + h) - Math.max(y, t)), 0);
    const [pLeft, pTop] = spots.reduce((best, spot) => (covered(spot) < covered(best) ? spot : best));
    panel.style.left = `${pLeft}px`;
    panel.style.top = `${pTop}px`;
  }

  // One to one's own parts gone (the table cleared, or closed).
  function endOne() {
    const { token, group, flight } = one;
    one = null;
    for (const node of overlay.querySelectorAll(".one-bubble, .one-asks")) node.remove();
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

  return { init, show, round, refresh, marked, markOf, layoutAgain, oneAnswer };
})();
