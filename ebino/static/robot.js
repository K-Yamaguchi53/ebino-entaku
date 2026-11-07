// コーチ（AI） and オブザーバー（AI） as small robots (直し47), in place of
// the square 「AI」 mark: so the AI is not taken for the map's people, who
// are drawn as people at their work. The teacher chose these two shapes
// (案 A, 11/7) and they are written here, once, for every place that shows
// them (the first look's two cards, the AI's seat's questions, the coach's
// board at one to one).
//
// Never a person: no nose, hair, ears, brows or skin; no name, age, manner
// or words of its own, and nothing it says. Lines only, no fill but the
// eyes, in currentColor (the place's AI blue). It never moves. It is a
// picture only (aria-hidden): the name, 「コーチ（AI）」 or 「オブザーバー（AI）」,
// is beside it, as before.
//
// コーチ: a round head, one short antenna with a dot, two small round eyes,
// a soft arc of a mouth, a rounded body, a pointer up from one hand.
// オブザーバー: a square head, two antennas, one large lens for an eye (a ring
// round a dot), no mouth, a rounded body.
// The two tell apart small, by shape: round head and pointer, square head
// and one eye.
"use strict";

const EbinoRobot = (() => {
  const NS = "http://www.w3.org/2000/svg";
  // The teacher's drawing on its 84×104 sheet, the 「AI」 tag under it left
  // out: [element, attributes]. A filled part says fill: "currentColor".
  const SHAPES = {
    coach: [
      ["line", { x1: 42, y1: 10, x2: 42, y2: 20 }],
      ["circle", { cx: 42, cy: 8, r: 3, fill: "currentColor" }],
      ["rect", { x: 18, y: 20, width: 48, height: 36, rx: 18 }],
      ["circle", { cx: 33, cy: 38, r: 3.5, fill: "currentColor" }],
      ["circle", { cx: 51, cy: 38, r: 3.5, fill: "currentColor" }],
      ["path", { d: "M35 47 Q42 51 49 47" }],
      ["rect", { x: 26, y: 60, width: 32, height: 20, rx: 6 }],
      ["line", { x1: 58, y1: 66, x2: 72, y2: 56 }],
      ["line", { x1: 72, y1: 56, x2: 76, y2: 50 }],
    ],
    observer: [
      ["line", { x1: 30, y1: 12, x2: 30, y2: 20 }],
      ["line", { x1: 54, y1: 12, x2: 54, y2: 20 }],
      ["rect", { x: 16, y: 20, width: 52, height: 36, rx: 6 }],
      ["circle", { cx: 42, cy: 38, r: 10 }],
      ["circle", { cx: 42, cy: 38, r: 4, fill: "currentColor" }],
      ["rect", { x: 26, y: 60, width: 32, height: 20, rx: 6 }],
    ],
  };
  // The part of the sheet the robot is on (its lines' width round it).
  const VIEW = "2 2 80 82";
  // The body's middle, for 「AI」 on it.
  const BODY = { x: 42, y: 70 };

  // A robot for a role ("coach" or "observer"): a span (class "robot", its
  // data-robot the role) holding the picture, aria-hidden. Its size and its
  // lines' width are the place's (style.css .robot). Given tag (the AI's
  // mark, 「AI」 from texts), it is written small on the body: for the large
  // places only (style.css shows it there, hides it elsewhere).
  function make(role, { tag = "" } = {}) {
    const shape = SHAPES[role];
    if (!shape) return null;
    const box = document.createElement("span");
    box.className = "robot";
    box.dataset.robot = role;
    box.setAttribute("aria-hidden", "true");
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", VIEW);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const lines = document.createElementNS(NS, "g");
    lines.setAttribute("class", "robot-lines");
    for (const [name, attributes] of shape) {
      const part = document.createElementNS(NS, name);
      for (const [key, value] of Object.entries(attributes)) part.setAttribute(key, String(value));
      lines.append(part);
    }
    svg.append(lines);
    if (tag) {
      const text = document.createElementNS(NS, "text");
      text.setAttribute("class", "robot-tag");
      text.setAttribute("x", String(BODY.x));
      text.setAttribute("y", String(BODY.y));
      text.textContent = tag;
      svg.append(text);
    }
    box.append(svg);
    return box;
  }

  return { make, roles: Object.keys(SHAPES) };
})();
