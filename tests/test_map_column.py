"""直し41の続き 段2: the map's column in index.html's order (no CSS order),
the keyboard's skip past the points, the three looks of what is pressed, the
box at the foot, #spoken-note shut at one to one, and the quiet glow stopped
as a question goes."""

import re

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _block(start):
    block = CSS[CSS.index(start):]
    return block[:block.index("\n}\n")]


def test_the_column_is_in_index_htmls_order_top_to_bottom():
    bar = HTML[HTML.index('<div class="map-bar map-controls">'):HTML.index("<!-- The AI's seat")]
    order = ['id="map-met-count"', 'id="map-back"', 'id="map-heading"', 'id="inside-open"', 'id="drawer-buttons"',
             'id="map-zoom-in"', 'id="map-zoom-out"', 'id="map-zoom-all"']
    at = [bar.index(part) for part in order]
    assert at == sorted(at)
    # Not moved by CSS: no order on the column or anything in it.
    for line in CSS.splitlines():
        if re.search(r"\.map-(bar|met|now|heading|drawers|zoom|back)\b|#inside\b|\.drawer-buttons", line):
            assert not re.search(r"(?<![-\w])order:", line), line


def test_the_count_alone_in_the_mincho_and_it_lights_once_when_it_grows():
    assert ".map-met-count { font-family: var(--mincho); font-size: var(--fs-num);" in CSS
    moving = _block("@media (prefers-reduced-motion: no-preference) {\n  .map-met-count.grew")
    assert "animation: met-grew 1.2s ease-out 1;" in moving and "infinite" not in moving
    assert 'count.classList.add("grew");' in MAP and "if (app.state.met.size > was) {" in MAP


def test_the_skip_is_the_maps_first_stop_seen_only_with_the_keyboard_on_it():
    frame = HTML[HTML.index('<div id="map-frame"'):HTML.index('<svg id="map-svg"')]
    assert '<button type="button" id="map-skip" class="map-skip"></button>' in frame
    assert ".map-skip:not(:focus) { width: 1px; height: 1px;" in CSS
    assert texts.screen_texts()["map_skip"] == "点をとばして右の列へ"
    skip = _top("setupMapSkip")
    assert "skip.textContent = state.texts.map_skip;" in skip
    assert '.map-bar button, .map-bar summary' in skip and "first.focus();" in skip
    # The points' own order is as before: the seniors' count goes before the svg, after the skip.
    assert "frame.insertBefore(label, svg);" in MAP


def test_every_press_sinks_and_the_rings_are_three_pixels_two_away():
    assert "--focus-w: 3px;" in CSS and "--focus-gap: 2px;" in CSS
    assert "outline: var(--focus-w) solid var(--lamp); outline-offset: var(--focus-gap);" in CSS
    moving = _block("@media (prefers-reduced-motion: no-preference) {\n  button:active:not(:disabled)")
    assert "scale: .97;" in moving
    assert "--press: .1s;" in CSS and "scale var(--press) ease-out" in CSS


def test_kiku_sends_out_one_ring_and_nothing_moves_with_motion_reduced():
    moving = _block("@media (prefers-reduced-motion: no-preference) {\n  #ask-button.rang::after")
    assert "animation: ask-rang .4s ease-out 1 both;" in moving
    assert 'button.classList.add("rang");' in APP
    reduce = CSS[CSS.index("@media (prefers-reduced-motion: reduce) {"):]
    reduce = reduce[:reduce.index("\n}\n")]
    assert "button, summary, .lab-choice, #ask-button { scale: none !important; }" in reduce
    assert "#ask-button::after, .map-met-count { animation: none !important; }" in reduce


def test_the_zoom_is_one_band_its_edge_three_to_one():
    assert ".map-zoom { display: flex; gap: 0; margin-left: auto; border: 1px solid var(--faint);" in CSS
    assert ".map-bar .map-zoom button + button { border-left: 1px solid var(--faint); }" in CSS


def test_spoken_note_is_not_said_at_one_to_one_and_its_words_are_the_teachers():
    assert "body.one-open .input-area .spoken-note { display: none; }" in CSS
    assert "spokenNote.textContent = state.texts.spoken_note;" in APP


def test_the_upright_box_grows_to_three_lines_its_words_as_large():
    upright = CSS[CSS.index("@media (orientation: portrait) {"):]
    upright = upright[:upright.index("\n}\n")]
    assert "max-height: calc(var(--rule) * 3 + 16px); overflow-y: auto;" in upright
    assert "font-size" not in upright[upright.index(".ask textarea { field-sizing: content;"):][:200]


def test_the_quiet_glow_stops_as_the_question_goes():
    ask = _top("ask")
    assert ask.index("onMap((map) => map.asked());") < ask.index('await call("/api/ask"')
    asked = MAP[MAP.index("  function asked() {"):]
    assert asked[:asked.index("\n  }\n")].strip().endswith("stopQuiet();")
