"""直し52 段1 (the teacher, 11/7): the first time only, before 司会（AI）から、
はじめに, the map is not covered: the camera comes from a little wider than the
whole to the basin and the school (2.4 s, slowing as moveTo does), then the
cover and the window as before. In 3 seconds at most; a press or a key: the
window at once (the press taken, not passed on to the box or a button);
motion reduced: the window at once, as before; the second time (the window
shut, back to the start): no camera. (The screen check measures it in a
browser: the window at 0 s with motion reduced, at 2.4 s with motion, 80 ms
after a press or a key, the camera still after it shut.)"""

from ebino import app as app_module

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
COMING = APP[APP.index("function comingIn() {"):APP.index("// Waiting for /api/start with the table out")]
START = APP[APP.index("async function start(lab, chosen) {"):APP.index("const APPROACH_FOR")]


def test_before_the_window_once_and_not_with_motion_reduced():
    assert '$("question").focus();\n  await comingIn();\n  firstLook();\n}' in START
    guard = 'if (still || state.approached || state.firstLooked || !state.texts.guide || typeof EbinoMap === "undefined" || $("map").hidden) {'
    assert guard in COMING
    assert COMING.index("return Promise.resolve();") < COMING.index("state.approached = true;")
    # firstLook itself still shows the window once, as before.
    assert "if (state.firstLooked || !words || typeof look.showModal !== \"function\") return;" in APP


def test_within_three_seconds_and_a_press_or_key_ends_it():
    assert "const APPROACH_FOR = 2400;" in APP
    assert "cap = setTimeout(end, 2.8 * 1000);" in COMING
    assert 'for (const type of ["pointerdown", "keydown"]) document.addEventListener(type, skip, true);' in COMING
    assert "event.preventDefault();\n      event.stopPropagation();\n      end();" in COMING
    assert "onMap((map) => map.approachEnd());" in COMING
    assert "if (over) return;" in COMING  # The window once, whichever way it ends.


def test_the_map_not_covered_and_no_guide_while_it_comes_in():
    assert "const target = spec && !state.approaching && shown(spec.at());" in APP
    assert ".coming-in .school-count { visibility: hidden; }" in CSS


def test_the_camera_wider_then_to_the_school_never_where_the_seniors_come_out():
    assert "onMap((map) => map.wideStart());" in APP
    assert "const APPROACH_WIDE = 1.12, APPROACH_NEAR = 1.6;" in MAP
    approach = MAP[MAP.index("  function approach(ms) {"):MAP.index("  function approachEnd() {")]
    assert "view.seniorStep / (2 * SCHOOL_R_PX) * (frame.clientWidth || 1) * 1.25" in approach
    assert "return moveTo(approachTo, reduced() ? 0 : ms);" in approach
    assert "wideStart, approach, approachEnd };" in MAP
    # Under the cover, the camera back at the whole: after the first look, all as before.
    assert "if (approachTo && view && view.whole) moveTo(view.whole, 0);" in MAP
