"""Which way is north on the map (直し25-3): a small arrow with 「北」 in a
corner, worked out from the map's own projection (on the picture north is
towards the front, on the flat map it is up), and by each edge what lies that
way, in the teacher's words (texts/map_around.tsv), off the shelves, the
words and the points."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import seat_map, texts
from ebino.relief import load_relief

SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner_function(script, name):
    start = script.index(f"function {name}(")
    return script[start:script.index("\n  }\n", start) + 5]


def _run(program):
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


def test_the_four_ways_come_from_the_teachers_table():
    around = texts.map_around()
    assert set(around) == {"north", "east", "south", "west"}
    assert around["north"] == {"word": "北", "place": "熊本県（人吉方面）"}
    assert around["west"] == {"word": "西", "place": "鹿児島県（伊佐方面）"}
    assert around["south"] == {"word": "南", "place": "霧島山・鹿児島県"}
    assert around["east"] == {"word": "東", "place": "小林市"}
    assert texts.screen_texts()["map_around"] == around


def test_a_map_around_table_missing_a_way_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    (tmp_path / "map_around.tsv").write_text("ID\t方位\tその方向にある所\nnorth\t北\t熊本県\n", encoding="utf-8")
    with pytest.raises(ValueError):
        texts.map_around()


def test_the_screen_reads_the_words_and_writes_none_of_its_own():
    draw = _inner_function(SCRIPT, "drawAround")
    assert "app.state.texts && app.state.texts.map_around" in draw
    assert "words.north.word" in draw and "words[way].place" in draw
    for word in ("熊本", "鹿児島", "霧島", "小林", '"北"'):
        assert word not in SCRIPT
    # Put afresh with every layout, before the labels, which then keep off them.
    relayout = _inner_function(SCRIPT, "relayout")
    assert relayout.index("placeAround();") < relayout.index("planLabels(")
    assert ".map-compass, .map-around" in _inner_function(SCRIPT, "fixedBoxes")
    # On the overlay, which takes no presses; colours by name only.
    assert "overlay.append(compass)" in draw and "overlay.append(note)" in draw
    rules = CSS[CSS.index(".map-compass, .map-around {"):CSS.index(".map-frame:has(svg.dim) .map-compass")]
    assert "#" not in rules and "var(--moon)" in rules and "var(--gothic)" in rules


@node
def test_north_is_up_on_the_picture_and_on_the_flat_map():
    data = seat_map.load_map()
    relief = load_relief((data.width, data.height))
    if relief is None:
        pytest.skip("the relief files are not here")
    program = "\n".join([
        f"const map = {json.dumps({'boundary': [list(p) for p in data.boundary], 'viewbox': [0, 0, data.width, data.height]})};",
        f"const relief = {json.dumps(relief)};",
        _inner_function(SCRIPT, "centroid"), _inner_function(SCRIPT, "flatView"),
        _inner_function(SCRIPT, "reliefView"), _inner_function(SCRIPT, "compassWays"),
        "let view = reliefView(relief); const onRelief = compassWays();",
        "view = flatView(); const onFlat = compassWays();",
        "process.stdout.write(JSON.stringify({ onRelief, onFlat }));",
    ])
    ways = _run(program)
    north, east = ways["onRelief"]["north"], ways["onRelief"]["east"]
    # The picture looks north from the south (直し31-4): north up, east right,
    # as on an ordinary map, so 人吉方面 is put at the top, 霧島山 at the
    # bottom, 小林市 on the right and 伊佐方面 on the left.
    assert north[1] < -0.95
    assert east[0] > 0.95
    assert ways["onFlat"]["north"] == [0, -1] and ways["onFlat"]["east"] == [1, 0]
    assert ways["onFlat"]["south"] == [0, 1] and ways["onFlat"]["west"] == [-1, 0]


_SPOTS = """
%(source)s
const frame = { w: 600, h: 400 };
const box = { w: 120, h: 20 };
const shelves = [[0, 0, 150, 60], [450, 0, 150, 120], [0, 340, 200, 60], [400, 350, 200, 50]];
const hit = (a, b) => a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
process.stdout.write(JSON.stringify({
  down: aroundSpot(frame, box, [0, 1], []),
  up: aroundSpot(frame, box, [0, -1], []),
  left: aroundSpot(frame, box, [-1, 0], []),
  right: aroundSpot(frame, box, [1, 0], []),
  pushed: aroundSpot(frame, box, [0, 1], [[200, 340, 200, 60]]),
  full: aroundSpot(frame, box, [0, 1], [[0, 300, 600, 100]]),
  compass: compassSpot(frame, { w: 56, h: 56 }, shelves),
  free: compassSpot(frame, { w: 56, h: 56 }, []),
}));
"""


@node
def test_a_ways_name_goes_by_its_edge_slid_off_what_is_there_and_inside_the_frame():
    source = "\n".join(_inner_function(SCRIPT, name) for name in ("coverOf", "aroundSpot", "compassSpot"))
    spots = _run(_SPOTS % {"source": source})
    hit = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    assert spots["down"] == [240, 372]  # The middle of the bottom edge, 8px in.
    assert spots["up"] == [240, 8]
    assert spots["left"] == [8, 190] and spots["right"] == [472, 190]
    left, top = spots["pushed"]
    assert top == 372 and not hit([left, top, 120, 20], [200, 340, 200, 60])
    left, top = spots["full"]  # Nothing free: still by its edge, inside the frame.
    assert top == 372 and 8 <= left <= 472
    # The arrow: the bottom right corner when free, off the four shelves when not.
    assert spots["free"] == [536, 336]
    left, top = spots["compass"]
    shelves = [[0, 0, 150, 60], [450, 0, 150, 120], [0, 340, 200, 60], [400, 350, 200, 50]]
    assert not any(hit([left, top, 56, 56], shelf) for shelf in shelves)
    assert 8 <= left <= 536 and 8 <= top <= 336


def test_with_less_motion_the_arrow_and_the_names_do_not_fade():
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    reduced = reduced[:reduced.index("transition: none !important")]
    assert ".map-compass" in reduced and ".map-around" in reduced


@node
def test_the_tables_front_is_the_side_nearest_the_camera_now_the_south():
    data = seat_map.load_map()
    relief = load_relief((data.width, data.height))
    if relief is None:
        pytest.skip("the relief files are not here")
    consts = SCRIPT[SCRIPT.index("  const NS ="):SCRIPT.index("  let map = null;")]
    program = "\n".join([
        consts,
        f"const map = {json.dumps({'boundary': [list(p) for p in data.boundary], 'viewbox': [0, 0, data.width, data.height]})};",
        f"const relief = {json.dumps(relief)};",
        _inner_function(SCRIPT, "centroid"), _inner_function(SCRIPT, "reliefView"),
        _inner_function(SCRIPT, "onTable"), _inner_function(SCRIPT, "frontAngle"), _inner_function(SCRIPT, "aiAngles"),
        "const view = reliefView(relief); const [x, y] = centroid(map.boundary);",
        "const front = frontAngle({ x, y, level: view.zAt(x, y) });",
        "process.stdout.write(JSON.stringify({ front, ai: aiAngles([], true, 2, front), free: aiAngles([], false, 2, front) }));",
    ])
    got = _run(program)
    assert got["front"] == 90  # The map's south: nearest the camera, lowest on the picture.
    assert got["ai"] == [90, 270]  # With a split: the dashed line's two ends.
    assert got["free"] == [45, 135]  # Else the front's two diagonals first.
