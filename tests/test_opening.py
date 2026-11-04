"""The opening after a Lab is picked (直し30-3): over the dark map, a paper
plane in lines flies a loose S from the school's mark (or the lower left)
to where the round table opens, lands, the lamp's light spreads once and the
title comes and goes. Under 3 seconds; 「とばす」, Enter or Esc ends it.
/api/start is waited for all the while: the question box never comes
before it, and a failure brings the Lab buttons back. With motion reduced,
or no map, none: the table at once, as before."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_the_skip_button_is_the_teachers_word():
    assert texts.screen_texts()["opening_skip"] == "とばす"
    assert '"とばす"' not in APP and ">とばす<" not in HTML
    assert '$("opening-skip").textContent = state.texts.opening_skip;' in (_top("playOpening") + _top("mapStage"))


def test_it_plays_while_start_is_waited_for_and_never_shows_the_box_before_it():
    start = _top("start")
    assert "const opening = still ? null : playOpening();" in start
    assert 'Promise.all([call("/api/start", { lab }),\n      opening ||' in start
    # A failure: the opening away and the Lab buttons back, as before.
    failed = start[start.index("} catch (error) {"):start.index("throw error;")]
    assert failed.index("if (opening) endOpening(true);") < failed.index("button.disabled = false;")
    assert "$(\"table\").hidden = true;" in _top("endOpening") and "$(\"start\").hidden = false;" in _top("endOpening")
    # Only once /api/start is in: the opening away, the purposes, the box focused.
    after = start[start.index("throw error;"):]
    assert after.index("if (opening) endOpening(false);") < after.index("renderPurposes(data.purposes);") \
        < after.index('$("question").focus();')


def test_no_map_or_motion_reduced_means_no_opening():
    play = (_top("playOpening") + _top("mapStage"))
    assert play.index('if (typeof EbinoMap === "undefined" || $("map").hidden) return null;') \
        < play.index('$("table").classList.add("opening-on");')
    assert "if (!box.width || !box.height" in play
    # It uses the map's own drawing of the rim and the river.
    assert "onMap((map) => map.show());" in play
    assert "opening" not in MAP


def test_it_is_under_three_seconds_and_skipped_at_once():
    times = re.search(r"const OPENING = \{ fly: (\d+), land: (\d+), title: (\d+) \};", APP)
    assert sum(int(n) for n in times.groups()) <= 3000
    play = (_top("playOpening") + _top("mapStage"))
    assert 'event.key === "Enter" || event.key === "Escape"' in play
    assert '$("opening-skip").onclick = () => finishOpening(run);' in play and '$(run.sheet ? "fold-skip" : "opening-skip").focus();' in play
    finish = _top("finishOpening")
    assert "cancelAnimationFrame(run.frame);" in finish and 'document.removeEventListener("keydown", run.keys);' in finish
    assert "run.done();" in finish
    # The keyboard goes to 「とばす」 (the map behind kept out), its ring shown.
    assert '$("map-frame").inert = true;' in play and '$("map-frame").inert = false;' in _top("endOpening")
    assert ".opening-bar button:focus { outline: 2px solid var(--lamp);" in CSS


def test_the_plane_is_folded_paper_in_the_code_and_nothing_flashes():
    group = HTML[HTML.index('<g id="opening-plane" class="opening-plane">'):]
    group = group[:group.index("</g>")]
    assert group.count("<polygon></polygon>") == 6 and "href" not in group  # Six triangles, no picture.
    # The cream of the people's words' paper, its folds in the lamp's colour.
    assert ".opening-plane polygon { fill: var(--paper); stroke: var(--lamp);" in CSS
    rules = CSS[CSS.index("/* The opening (直し30-3)"):CSS.index("/* 最初にもどる under the sheet")]
    assert "animation" not in rules and "#" not in rules.replace("#table", "").replace("#map", "")
    assert "http" not in rules and "url(" not in rules
    # The aeroplane of 県外・海外 at the table is another shape.
    assert "cross: \"M0,-6 C0.9,-6" in MAP and "planeFaces" not in MAP


_PLANE = """
%(source)s
const run = { from: [40, 560], end: [500, 300] };
const at = (u) => planeAt(run, u);
const side = (p) => Math.sign((500 - 40) * (p.y - 560) - (300 - 560) * (p.x - 40));
process.stdout.write(JSON.stringify({ start: at(0), end: at(1), sides: [side(at(0.25)), side(at(0.75))] }));
"""


@node
def test_the_plane_flies_a_loose_s_from_its_start_to_the_tables_spot():
    program = _PLANE % {"source": _top("planeAt")}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert (round(got["start"]["x"]), round(got["start"]["y"])) == (40, 560)
    assert (round(got["end"]["x"]), round(got["end"]["y"])) == (500, 300)
    # One side of the straight way, then the other: an S.
    assert got["sides"][0] == -got["sides"][1] != 0


_FACES = """
%(source)s
const pose = (o) => Object.assign({ x: 500, y: 300, size: 100, a: 0, roll: 0, pitch: 0 }, o);
const box = (faces) => { const xs = faces.flatMap((f) => f.points.map((p) => p[0])), ys = faces.flatMap((f) => f.points.map((p) => p[1]));
  return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]; };
const level = planeFaces(pose({})), right = planeFaces(pose({ a: Math.PI / 2 })),
  banked = planeFaces(pose({ roll: 0.5 })), up = planeFaces(pose({ pitch: 0.3 }));
process.stdout.write(JSON.stringify({ n: level.length, lights: [...new Set(level.map((f) => f.light.toFixed(2)))].length,
  level: box(level), right: box(right), banked: box(banked), up: box(up),
  sorted: level.every((f, i) => !i || level[i - 1].depth <= f.depth),
  size: (_size) }));
"""


@node
def test_the_plane_is_six_faces_lit_apart_turned_to_its_way_and_big_enough():
    program = _FACES.replace("(_size)", "Math.max(64, 1180 * 0.1)") % {"source": APP[APP.index("const PLANE = {"):APP.index("// The opening as it is t ms in")]}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["n"] == 6 and got["lights"] >= 3 and got["sorted"]  # The folds show by their light.
    x0, x1, y0, y1 = got["level"]
    assert 92 <= x1 - x0 <= 112 and x1 > 500 + 55  # Nose to the right, about 100px long.
    x0, x1, y0, y1 = got["right"]
    assert y1 > 300 + 45 and round(x1 - x0) < 70  # Turned to fly down the screen.
    assert got["banked"] != got["level"] and got["up"] != got["level"]
    # At its nearest, 8% of the map's width or more and 64px at least.
    assert "size: Math.max(64, w * 0.1)" in (_top("playOpening") + _top("mapStage")) and got["size"] >= 64


def test_it_takes_off_from_the_schools_picture_else_its_mark_else_the_lower_left():
    play = (_top("playOpening") + _top("mapStage"))
    picture = play.index('sighted("#map-svg .school-picture image", 0.3)')
    mark = play.index('sighted("#map-svg .school > :not(text)", 0.5)')
    assert play.index("let from = [Math.min(48, w * 0.08), h - Math.min(48, h * 0.08)];") < picture < mark
    # The plane is drawn over the map and the school's picture alike.
    assert ".opening { position: absolute; inset: 0; z-index: 6;" in CSS
    # The wings kept off the frame's edge by the plane's own reach.
    assert "const m = Math.max(24, (run.size || 0) * 0.7);" in _top("planeAt")


_NEAR = """
%(source)s
const node = () => ({ style: { opacity: ".2" } });
const run = { reach: 40, points: [{ node: node(), x: 100, y: 100, lit: false }, { node: node(), x: 300, y: 100, lit: false }] };
lightNear(run, 120, 110);
const first = run.points.map((p) => p.lit);
run.points[0].node.style.opacity = "x";
lightNear(run, 110, 100);
process.stdout.write(JSON.stringify({ first, again: run.points[0].node.style.opacity, shown: run.points[0].node.style.opacity }));
"""


@node
def test_the_seats_it_passes_over_light_once_each_and_the_ring_lights_the_rest():
    program = _NEAR % {"source": _top("lightNear")}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["first"] == [True, False] and got["again"] == "x"  # Lit once, not again.
    draw = _top("drawOpening")
    assert draw.index("if (fly < 1) lightNear(run, p.x, p.y);") < draw.index("if (!point.lit && point.d / run.far <= k) {")


def test_no_school_picture_is_needed():
    # The tests run with no picture; the opening asks for none of its own.
    assert "school_picture" not in (_top("playOpening") + _top("mapStage")) and "EBINO_SCHOOL_DIR" not in APP


def test_the_lab_board_folds_into_the_plane_first_all_in_four_and_a_half_seconds():
    times = re.search(r"const FOLD = \{ paper: (\d+), fold: (\d+), away: (\d+) \};", APP)
    opening = re.search(r"const OPENING = \{ fly: (\d+), land: (\d+), title: (\d+) \};", APP)
    assert sum(int(n) for n in times.groups()) + sum(int(n) for n in opening.groups()) <= 4500
    play = _top("playOpening")
    # No map or motion reduced: none, the fold too (start() asks for none).
    assert play.index('if (typeof EbinoMap === "undefined" || $("map").hidden) return null;')         < play.index('foldSheet($("start").getBoundingClientRect())')
    # 「とばす」, Enter and Esc end it while it folds too.
    assert '$("fold-skip").onclick = () => finishOpening(run);' in play
    assert '$("fold-skip").textContent = state.texts.opening_skip;' in play
    # Resized or turned while folding: the board is measured again.
    assert 'run.sheet = foldSheet($("start").getBoundingClientRect()) || run.sheet;' in play
    finish = _top("finishOpening")
    assert '$("fold").hidden = true;' in finish and '$("start").style.opacity = "";' in finish
    # The sheet's six faces are the plane's own, the paper's colour.
    fold = HTML[HTML.index('<div id="fold" class="fold" hidden>'):]
    fold = fold[:fold.index("</div>")]
    assert fold.count("<polygon></polygon>") == 6 and 'class="opening-plane"' in fold
    assert ".fold-sheet { fill: var(--paper); stroke: var(--lamp);" in CSS


_FOLD = """
%(source)s
const nodes = () => Array.from({ length: 6 }, () => ({ pts: "", style: {}, setAttribute(k, v) { this.pts = v; } }));
const sheetNode = { pts: "", style: {}, setAttribute(k, v) { this.pts = v; } }, planeNodes = nodes(), start = { style: {} };
const $ = (id) => ({ "fold-sheet": sheetNode, "fold-plane": { children: planeNodes }, start })[id];
globalThis.window = { innerHeight: 700 };
const run = { sheet: foldSheet({ left: 100, right: 400, top: 50, bottom: 800, width: 300 }) };
const seen = [];
for (const t of [0, 300, 500, 800, 1200]) {
  drawFold(run, t);
  seen.push({ t, sheet: sheetNode.pts.split(" ").filter(Boolean).length, faces: planeNodes.filter((n) => n.pts).length, words: start.style.opacity });
}
process.stdout.write(JSON.stringify({ sheet: run.sheet, seen }));
"""


@node
def test_the_tall_board_becomes_a_sheet_then_a_long_triangle_then_the_plane():
    source = APP[APP.index("const PLANE = {"):APP.index("// The seats' points the plane is passing over")]
    program = _FOLD % {"source": "const FOLD = { paper: 300, fold: 900, away: 500 };" + source + _top("foldSheet") + _top("drawFold")}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["sheet"]["T"] == 50 and got["sheet"]["B"] == 700  # Only what is on the screen.
    seen = {s["t"]: s for s in got["seen"]}
    assert seen[0]["words"] == "1" and seen[300]["words"] == "0"  # The words fade, the sheet stays.
    assert seen[500]["sheet"] == 5 and seen[500]["faces"] == 0
    assert seen[1200]["sheet"] == 0 and seen[1200]["faces"] == 6
