// A seat as a person (直し34-3), drawn in lines of code, no picture: about
// seven heads tall, a head a little taller than wide, ears, a neck, a body
// narrowing from the shoulders to the waist, arms bent at the elbow with
// hands, legs with thighs, knees and shins, shoes, a light shadow down its
// right side. The teacher chose this shape from the sample (34_見本_人の形)
// and it is written here again for the app.
//
// Its colours all come from the seat's kind's colour (style.css --kind):
// the clothes and arms that colour (three shades), the face, neck, ears and
// hands it brought near white, the trousers and a cap it darkened, the hair
// and shoes darker still. Nothing else is added. No face (eyes or mouth), no
// long hair, no skirt or uniform, no name, nothing held, no photograph: the
// picture never says a sex, an age or a school.
//
// Each person differs, by a fixed working from the seat (never by chance):
// its height, width, head, shoulders, arms' spread, stance, a little lean
// and the clothes' shade from its seat ID; its clothes (four) and what is on
// its head (five) from its place among the seats of its kind in seat ID
// order, so that two next to each other never have the same pair, and with
// twenty or fewer of a kind, no two at all. While it talks, one hand up.
"use strict";

const EbinoPerson = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const TOPS = ["jacket", "tee", "coat", "hoodie"];
  const HEADS = ["none", "short", "side", "cap", "knit"];
  const POSES = ["down", "down", "down", "pocket", "behind"];
  const STEP = 7;  // Coprime to TOPS × HEADS (20): the pairs of 0..19 in order are all different.
  const HEIGHT = 178;  // Its height in its own units, its feet at 0.

  // A number from a seat ID, the same each time (FNV-1a).
  function hash(text) {
    let h = 0x811c9dc5;
    for (const ch of String(text)) {
      h ^= ch.codePointAt(0);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
  }

  // A run of numbers in [0, 1) from a seed (mulberry32), the same each time.
  function numbers(seed) {
    let s = seed | 0;
    return () => {
      s = (s + 0x6d2b79f5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Its clothes and what is on its head, from its place among its kind in
  // seat ID order (0, 1, ...). It reads nothing but what it is given.
  function pair(place) {
    const k = ((place % 20) * STEP) % 20;
    return { top: TOPS[k % TOPS.length], head: HEADS[Math.floor(k / TOPS.length)] };
  }

  // How a person looks: everything that makes it differ. It reads nothing
  // but what it is given.
  function looks(seatId, place, pose) {
    const r = numbers(hash(seatId));
    const out = {
      h: 0.9 + r() * 0.18, w: 0.9 + r() * 0.2, hs: 0.93 + r() * 0.14, sh: 18 + r() * 4, sp: r() * 6,
      stance: 6 + r() * 5, lean: (r() - 0.5) * 3, shift: (r() - 0.5) * 4, shade: Math.floor(r() * 3),
      ...pair(place),
    };
    out.pose = pose || POSES[Math.floor(r() * POSES.length)];
    out.sleeve = out.top === "tee" ? "short" : "long";
    return out;
  }

  // The colours, all from the kind's (--kind), by name for style.css.
  const CLOTHES = ["var(--kind)", "color-mix(in srgb, var(--kind) 82%, white)", "color-mix(in srgb, var(--kind) 82%, black)"];
  const SKIN = "color-mix(in srgb, var(--kind) 45%, white)";
  const DARK = "color-mix(in srgb, var(--kind) 52%, black)";
  const DARKER = "color-mix(in srgb, var(--kind) 34%, black)";
  const LINE = "color-mix(in srgb, var(--kind) 70%, black)";

  const f = (n) => (+n).toFixed(1);
  function el(tag, attrs, fill) {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (fill) node.style.fill = fill;
    return node;
  }
  function stroke(d, width, colour) {
    const node = el("path", { d, "stroke-width": width, "stroke-linecap": "round", "stroke-linejoin": "round", fill: "none" });
    node.style.stroke = colour;
    return node;
  }

  function hair(group, type, hy, rx, ry) {
    const add = (d, colour) => group.append(el("path", { d }, colour));
    if (type === "short") {
      add(`M${-rx - 1} ${hy + 2} C${-rx - 1.5} ${hy - ry - 4} ${rx + 1.5} ${hy - ry - 4} ${rx + 1} ${hy + 2} ` +
        `C${rx * 0.6} ${hy - ry * 0.35} ${-rx * 0.6} ${hy - ry * 0.35} ${-rx - 1} ${hy + 2}Z`, DARKER);
    } else if (type === "side") {
      add(`M${-rx - 1.5} ${hy + 5} C${-rx - 2.5} ${hy - ry - 4} ${rx + 2} ${hy - ry - 5} ${rx + 1.5} ${hy + 1} ` +
        `C${rx * 0.5} ${hy - ry * 0.7} ${-rx * 0.2} ${hy - ry * 0.55} ${-rx * 0.55} ${hy - ry * 0.15} ` +
        `C${-rx * 0.8} ${hy + 1} ${-rx - 1} ${hy + 3} ${-rx - 1.5} ${hy + 5}Z`, DARKER);
    } else if (type === "cap") {
      add(`M${-rx - 0.8} ${hy - 2} C${-rx - 0.5} ${hy - ry - 5} ${rx + 0.5} ${hy - ry - 5} ${rx + 0.8} ${hy - 2}Z`, DARK);
      add(`M${rx * 0.2} ${hy - 3.5} C${rx + 6} ${hy - 3.5} ${rx + 11} ${hy - 2} ${rx + 11} ${hy - 0.5} L${rx * 0.2} ${hy - 1}Z`, DARK);
    } else if (type === "knit") {
      add(`M${-rx - 1} ${hy - 2} C${-rx - 1.5} ${hy - ry - 8} ${rx + 1.5} ${hy - ry - 8} ${rx + 1} ${hy - 2}Z`, DARK);
      group.append(el("rect", { x: -rx - 1.8, y: hy - 5, width: 2 * rx + 3.6, height: 5.5, rx: 2.7 }, DARK));
    } else {
      // A round head with no hair to speak of: only a thin cap of it.
      add(`M${-rx} ${hy - 1} C${-rx - 0.5} ${hy - ry - 2.5} ${rx + 0.5} ${hy - ry - 2.5} ${rx} ${hy - 1} ` +
        `C${rx * 0.5} ${hy - ry * 0.6} ${-rx * 0.5} ${hy - ry * 0.6} ${-rx} ${hy - 1}Z`, DARKER);
    }
  }

  function arm(group, d, look, clothes) {
    const { sh, sp, pose, sleeve } = look;
    const sx = d * (sh - 1), sy = -138;
    let ex, ey, wx, wy, hand = true;
    if (pose === "pocket") [ex, ey, wx, wy, hand] = [d * (sh + 7), -110, d * 15, -92, false];
    else if (pose === "wave" && d === 1) [ex, ey, wx, wy] = [sh + 13, -128, sh + 17, -160];
    else if (pose === "behind") [ex, ey, wx, wy, hand] = [d * (sh + 3), -110, d * (sh - 3), -90, false];
    else [ex, ey, wx, wy] = [d * (sh + 3 + sp), -108, d * (sh + 4 + sp * 1.4), -82];
    if (sleeve === "short") {
      const mx = sx + (ex - sx) * 0.5, my = sy + (ey - sy) * 0.5;
      group.append(stroke(`M${f(mx)} ${f(my)} L${f(ex)} ${f(ey)} L${f(wx)} ${f(wy)}`, 7.2, SKIN),
        stroke(`M${f(sx)} ${f(sy)} L${f(mx)} ${f(my)}`, 10.5, clothes));
    } else {
      group.append(stroke(`M${f(sx)} ${f(sy)} L${f(ex)} ${f(ey)} L${f(wx)} ${f(wy)}`, 9, clothes));
    }
    if (hand) {
      const hx = wx + (wx - ex) * 0.18, hy = wy + (wy - ey) * 0.18;
      group.append(el("ellipse", { cx: f(hx), cy: f(hy), rx: 4.2, ry: 5 }, SKIN));
    }
  }

  // The person, its feet at (0, 0), HEIGHT tall: an SVG group, in the
  // kind's colours (its class kind-<kind> sets --kind).
  function figure(kind, seatId, place, pose) {
    const look = looks(seatId, place, pose);
    const { h, w, hs, sh, stance, lean, shift, top, head } = look;
    const clothes = CLOTHES[look.shade];
    const outer = el("g", { class: `person kind-${kind}`, "aria-hidden": "true" });
    const g = el("g", { transform: `rotate(${f(lean)}) scale(${f(w)} ${f(h)})` });
    outer.append(g);
    if (look.pose === "behind") for (const d of [-1, 1]) arm(g, d, look, clothes);
    if (top === "hoodie") g.append(el("ellipse", { cx: 0, cy: -151, rx: 14, ry: 6.5 }, DARK));
    for (const d of [-1, 1]) {
      const hx = d * 8.5, kx = d * (stance + 0.5) + shift * 0.5, ax = d * stance + shift;
      g.append(stroke(`M${hx} -88 L${f(kx)} -46`, 14, DARK), stroke(`M${f(kx)} -46 L${f(ax)} -9`, 11.5, DARK));
      g.append(el("path", { d: `M${f(ax - 6.5)} 0 L${f(ax - 6.5)} -5 C${f(ax - 6)} -10 ${f(ax + 6)} -10 ${f(ax + 6.5)} -6 ` +
        `C${f(ax + d * 3 + 7)} -5 ${f(ax + d * 3 + 8)} -2 ${f(ax + d * 3 + 8)} 0 Z` }, DARKER));
    }
    g.append(el("path", { d: `M-6,-152 L6,-152 C13,-151 ${f(sh)},-149 ${f(sh + 2)},-141 C${f(sh + 2)},-127 16,-112 15,-100 ` +
      `C17,-94 18,-89 18,-84 L-18,-84 C-18,-89 -17,-94 -15,-100 C-16,-112 ${f(-sh - 2)},-127 ${f(-sh - 2)},-141 ` +
      `C${f(-sh)},-149 -13,-151 -6,-152Z` }, clothes));
    if (top === "coat") {
      g.append(el("path", { d: "M-17,-100 L-20,-58 C-7,-55 7,-55 20,-58 L17,-100Z" }, clothes), stroke("M0,-148 L0,-60", 1.2, LINE));
    }
    if (top === "jacket") g.append(stroke("M0,-148 L0,-86", 1.1, LINE), stroke("M-6,-151 L0,-138 L6,-151", 1.3, LINE));
    if (top === "hoodie") g.append(el("path", { d: "M-9,-104 L9,-104 L11,-92 L-11,-92Z" }, DARK));
    // The shadow down its right side: its own colour, darker and faint.
    const shadow = el("path", { d: `M10,-150 C${f(sh)},-148 ${f(sh + 2)},-141 ${f(sh + 2)},-141 C${f(sh + 2)},-127 16,-112 15,-100 ` +
      "C17,-94 18,-89 18,-84 L12,-84 C13,-104 13,-128 10,-150Z", class: "shade" }, DARKER);
    g.append(shadow);
    if (look.pose !== "behind") for (const d of [-1, 1]) arm(g, d, look, clothes);
    const rx = 10.2 * hs, ry = 12.3 * hs, hy = -162 - ry + 4;
    g.append(el("path", { d: "M-4.5,-160 L4.5,-160 L5,-149 L-5,-149Z" }, SKIN));
    if (top === "tee") g.append(stroke("M-6,-151.5 C-3,-147 3,-147 6,-151.5", 1.4, LINE));
    g.append(el("ellipse", { cx: f(-rx + 0.3), cy: f(hy + 2), rx: 2.3, ry: 3.4 }, SKIN),
      el("ellipse", { cx: f(rx - 0.3), cy: f(hy + 2), rx: 2.3, ry: 3.4 }, SKIN));
    g.append(el("path", { d: `M${f(-rx)} ${f(hy)} C${f(-rx)} ${f(hy - ry * 1.35)} ${f(rx)} ${f(hy - ry * 1.35)} ${f(rx)} ${f(hy)} ` +
      `C${f(rx)} ${f(hy + ry * 0.75)} ${f(rx * 0.45)} ${f(hy + ry)} 0 ${f(hy + ry)} C${f(-rx * 0.45)} ${f(hy + ry)} ` +
      `${f(-rx)} ${f(hy + ry * 0.75)} ${f(-rx)} ${f(hy)}Z` }, SKIN));
    hair(g, head, hy, rx, ry);
    return outer;
  }

  return { figure, looks, pair, hash, HEIGHT, TOPS, HEADS };
})();
