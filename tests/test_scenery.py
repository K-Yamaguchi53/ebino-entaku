"""直し48 段6 (the teacher's 決定, 11/7): each time someone answers (the
town's adults at the table, or one to one) the map's scenery goes one on,
night → spring → autumn → night…; the buttons stay, and the next answer goes
on from the one pressed. It melts in slowly (at once with motion reduced).
The scenery's name sits in a corner of the map. 直し53 段8: spring's cherry
trees are in its picture (tools/render_relief.py); the dots that were drawn
over it (直し48 段6) are gone."""

import json
from pathlib import Path
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
const lookNodes = { picture: node("/relief.webp") };
const map = { relief: { looks: [{ id: "night", image: "/n" }, { id: "spring", image: "/s" },
  { id: "autumn", image: "/a" }] } };
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


def test_no_flower_dots_over_the_spring_picture():
    assert "drawFlowers" not in MAP and "flowerSpots" not in MAP and "FLOWER_" not in MAP
    assert "spring-flowers" not in MAP and "spring-flowers" not in CSS and "--sakura" not in CSS
    # The picture paints them (直し53 段8): cherry trees and rape in spring's look.
    render = (Path(__file__).resolve().parents[1] / "tools" / "render_relief.py").read_text(encoding="utf-8")
    assert '"blossom": {' in render and "def blossoms(" in render


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
