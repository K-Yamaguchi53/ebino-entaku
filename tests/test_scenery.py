"""直し48 段6 (the teacher's 決定, 11/7): each time someone answers (the
town's adults at the table, or one to one) the map's scenery goes one on,
night → spring → autumn → night…; the buttons stay, and the next answer goes
on from the one pressed. It melts in slowly (at once with motion reduced).
The scenery's name sits in a corner of the map; spring has small cherry-pink
flowers on the low land and along the river, from a fixed seed (the same
place every time), still, under the points and the bubbles."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"  function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 4]


CYCLE = """
const made = {};
const el = (id) => made[id] || (made[id] = { id, hidden: false, dataset: {}, style: {}, attrs: {},
  setAttribute(k, v) { this.attrs[k] = v; }, querySelector() { return { textContent: "" }; },
  querySelectorAll() { return []; }, getBoundingClientRect() { return { width: 0 }; } });
const $ = el;
const frame = el("map-frame");
let reducedNow = false;
const reduced = () => reducedNow;
let melted = 0;
const node = (href) => ({ attrs: { href }, setAttribute(k, v) { this.attrs[k] = v; },
  cloneNode() { const n = node(this.attrs.href); return n; }, style: {},
  after() {}, animate() { melted += 1; return {}; }, remove() {} });
const lookNodes = { picture: node("/relief.webp"), ground: node("/relief_blur.webp") };
const map = { relief: { looks: [{ id: "night", image: "/n", blur: "/nb" }, { id: "spring", image: "/s", blur: "/sb" },
  { id: "autumn", image: "/a", blur: "/ab" }] } };
const view = null, app = null;
const LOOK_FADE = 1600;
let look = map.relief.looks[0];
function looksOf() { return map.relief.looks; }
function placeLookLabel() {}
%(source)s
const seen = [look.id];
for (let n = 0; n < 4; n++) { nextLook(); seen.push(look.id); }
const meltedThen = melted;
showLook("spring");  // A button pressed: no melt, and the next answer goes on from there.
const pressed = melted === meltedThen;
nextLook();
const afterPress = look.id;
reducedNow = true;
const before = melted;
nextLook();
process.stdout.write(JSON.stringify({ seen, pressed, afterPress, reducedMelt: melted - before, look: look.id,
  href: lookNodes.picture.attrs.href, framed: frame.dataset.look }));
"""


@node
def test_each_answer_moves_the_scenery_one_on_and_a_button_is_where_it_goes_on_from():
    source = _inner("showLook") + _inner("nextLook")
    out = subprocess.run(["node", "-"], input=(CYCLE % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["seen"] == ["night", "spring", "autumn", "night", "spring"]
    assert got["pressed"] and got["afterPress"] == "autumn"
    # With motion reduced: no melting, the picture at once.
    assert got["reducedMelt"] == 0 and got["look"] == "night" and got["href"] == "/n" and got["framed"] == "night"


def test_it_goes_on_when_someone_answers_at_the_table_and_at_one_to_one():
    rnd = MAP[MAP.index("  function round(result) {"):MAP.index("  function round(result) {") + 1200]
    assert "nextLook();  // 直し48 段6: someone answered; the scenery goes one on." in rnd
    assert rnd.index("if (!order.length) return;") < rnd.index("nextLook();")
    assert "says(answer.pieces, answer.source, answer.kind_label);\n          nextLook();  // 直し48 段6." in MAP
    # The buttons stay; pressed, they show that one.
    assert 'button.addEventListener("click", () => showLook(one.id));' in MAP
    assert "const LOOK_FADE = 1600;" in MAP


FLOWERS = """
const map = { boundary: [[0, 0], [100, 0], [100, 100], [0, 100]], river: [[[0, 90], [100, 90]]] };
const view = { zAt: (x, y) => y, proj: (x, y) => [x * 2, y * 2] };
const made = [];
const svgEl = (tag, attrs) => ({ tag, attrs });
%(source)s
const one = flowerSpots(), two = flowerSpots();
const layer = { append(n) { made.push(n); } };
drawFlowers(layer);
process.stdout.write(JSON.stringify({ one, two, made: made.length, classes: [...new Set(made.map((n) => n.attrs.class))] }));
"""


@node
def test_spring_flowers_are_in_the_same_place_every_time_on_low_land_and_by_the_river():
    start = MAP.index("  const FLOWER_SEED = 48")
    source = MAP[start:MAP.index("\n  }\n", MAP.index("  function drawFlowers(")) + 4]
    out = subprocess.run(["node", "-"], input=(FLOWERS % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["one"] == got["two"] and 0 < len(got["one"]) <= 140  # The same seed, the same place; not too many.
    # Low land (here: low y) or near the river (y about 90).
    assert all(spot["z"] <= 35 or abs(spot["y"] - 90) < 6 for spot in got["one"])
    assert got["made"] == len(got["one"]) and got["classes"] == ["flower"]


def test_flowers_still_under_the_points_spring_only():
    build = MAP[MAP.index("      lookNodes = { picture, ground };"):MAP.index('    const fill = layer("basin-fill");')]
    assert 'drawFlowers(layer("spring-flowers"));' in build  # Right over the picture, before the rest is drawn.
    assert ".spring-flowers { opacity: 0; }" in CSS and '.map-frame[data-look="spring"] .spring-flowers { opacity: 1; }' in CSS
    flower = re.search(r"\.spring-flowers \.flower \{[^}]*\}", CSS).group(0)
    assert "animation" not in flower and "transition" not in flower
    assert "@media (prefers-reduced-motion: no-preference) { .spring-flowers { transition: opacity 1.6s ease-in-out; } }" in CSS


def test_the_sceneries_name_in_a_corner_its_words_in_texts():
    words = texts.screen_texts()["map_look_label"]
    assert words == {"night": "えびのの夜の風景", "spring": "えびのの春の風景", "autumn": "えびのの秋の風景", "note": "標高から描いた絵"}
    assert '<p id="map-look-label" class="map-look-label" hidden>' in HTML
    place = _inner("placeLookLabel")
    assert "if (name === ai) continue;" in place and ".table-bubble:not(.unplaced)" in place
    assert "placeLookLabel();\n  }" in MAP  # After the map's words and bubbles are laid out.
    assert ".map-look-label { position: absolute;" in CSS and "pointer-events: none;" in CSS


def test_the_label_never_wraps_and_keeps_off_the_hint_at_the_foot():
    # The screen check: with the box answering コーチ the frame narrowed and
    # the label broke inside words; at 768 it lay over 「吹き出しを押すと…」.
    assert re.search(r"\.map-look-label \{[^}]*white-space: nowrap;", CSS)
    assert '".map-hint, .map-choices"' in _inner("placeLookLabel")
    # No corner free: not shown until one is (never over them).
    assert 'label.classList.toggle("crowded", least > 0);' in _inner("placeLookLabel")
    assert ".map-look-label.crowded { visibility: hidden; }" in CSS
