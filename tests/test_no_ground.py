"""直し39: when the school is shown large (the map put larger, the meeting,
one to one), its sports ground is not drawn (先生「円卓として校舎が出てくる
ときに、グラウンドは不要」). The picture (school_yard.png, the file as it is)
is shown from a little east of its ground's east side (field_px's two east
corners) on; the plain one has a building and its site only. (直し35-1's
track on the plain ground is gone with it.)"""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

# Like the sprite's: the ground's corners north-west, north-east, south-east, south-west.
PICTURE = {"image": "/school/school_yard.png", "width": 1413, "height": 782, "field": [[71.1, 39.7], [724.0, 53.2],
           [701.6, 729.7], [48.6, 716.2]], "windows": [[884.6, 304.1], [1278.8, 312.2], [835.4, 297.6], [1328.4, 307.8]],
           "ring": [1081.0, 368.0], "px_per_m": 6.7893}


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _const(name):
    return re.search(rf"const {name} = [^;]+;", MAP).group(0)


def _run(code):
    done = subprocess.run(["node", "-"], input=code.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


def test_no_track_lanes_infield_or_middle_line_is_drawn_for_either_school():
    drawn = _inner("drawYard")
    for gone in ("yard-ground", "yard-track", "yard-infield", "yard-line", "trackOn", "field"):
        assert gone not in drawn, gone
    for gone in ("const TRACK", "function trackOn(", "function schoolSquares(", "field: [["):
        assert gone not in MAP, gone
    for gone in (".yard-ground", ".yard-track", ".yard-infield", ".yard-line", "--track", "--infield", "--field-line"):
        assert gone not in CSS, gone
    # The plain one: its site under the building, as the part shown.
    assert 'group.append(polygon("yard-site", model.board));' in drawn
    assert "field" not in _const("PLAIN_YARD")


def test_the_picture_is_shown_only_east_of_the_cut_and_its_box_is_that_part():
    drawn = _inner("drawYard")
    # The picture fills the part shown (a pattern), so the building's box,
    # which names and cards keep off, is that part and not the whole file.
    assert 'svgEl("pattern", { id: "yard-picture", patternUnits: "userSpaceOnUse", x: model.imageX' in drawn
    assert 'const shown = polygon("yard-picture", model.board);' in drawn
    assert 'shown.setAttribute("fill", "url(#yard-picture)");' in drawn
    assert 'svgEl("image", { href: model.image, width: model.width' not in drawn


@node
def test_the_cut_is_a_little_east_of_the_grounds_east_corners_and_the_rest_moves_with_it():
    code = "\n".join([_const("CUT_GAP_M"), _inner("cutYard"), f"const p = {json.dumps(PICTURE)};",
                      "process.stdout.write(JSON.stringify(cutYard(p)));"])
    got = _run(code)
    gap = 3 * PICTURE["px_per_m"]
    (ne_x, ne_y), (se_x, se_y) = PICTURE["field"][1], PICTURE["field"][2]
    left = -got["imageX"]
    # The cut's line: the ground's east side, gap east of it, top to foot.
    top = ne_x + (se_x - ne_x) * (0 - ne_y) / (se_y - ne_y) + gap
    foot = ne_x + (se_x - ne_x) * (782 - ne_y) / (se_y - ne_y) + gap
    assert abs(left - min(top, foot)) < 1e-6
    board = got["board"]
    # At each of the ground's east corners, the cut is gap east of it.
    cut_at = lambda y: board[0][0] + left + (board[3][0] - board[0][0]) * y / 782
    assert abs(cut_at(ne_y) - (ne_x + gap)) < 0.01 and abs(cut_at(se_y) - (se_x + gap)) < 0.01
    assert abs(board[0][0] + left - top) < 0.01 and board[0][1] == 0
    assert abs(board[3][0] + left - foot) < 0.01 and board[3][1] == 782
    assert board[1] == [1413 - left, 0] or abs(board[1][0] - (1413 - left)) < 0.01
    assert abs(got["width"] - (1413 - left)) < 1e-6 and got["height"] == 782 and got["imageW"] == 1413
    # The windows and the ring's middle moved with it, so the school stays
    # where it is on the map (its ring's middle on the school's point).
    assert abs(got["ring"][0] - (1081 - left)) < 0.01 and got["ring"][1] == 368
    assert all(abs(w[0] - (o[0] - left)) < 0.01 and w[1] == o[1] for w, o in zip(got["windows"], PICTURE["windows"]))
    # Every window east of the cut, on the part shown.
    assert all(w[0] > board[0][0] for w in got["windows"])


@node
def test_rows_past_the_windows_keep_the_rows_step_and_go_outward_from_the_middle():
    # Two rows of three windows, the outer 10 above the inner.
    windows = [[0, 100], [20, 100], [40, 100], [0, 90], [20, 90], [40, 90]]
    board = [[-50, 0], [90, 0], [90, 200], [-50, 200]]
    code = "\n".join([_inner("within"), _inner("clearOf"), _inner("seniorRows"),
                      f"const a = seniorRows({json.dumps(windows)}, {json.dumps(board)}, 5, 9);",
                      f"const b = seniorRows({json.dumps(windows)}, {json.dumps(board)}, 5, 40);",
                      "process.stdout.write(JSON.stringify({ a, b }));"])
    got = _run(code)
    a = got["a"]
    # The rows at 80, 70, 60 ... (the same step), each from its middle out.
    assert [s["p"] for s in a["spots"][:3]] == [[20, 80], [0, 80], [40, 80]]
    assert [s["p"][1] for s in a["spots"]] == [80, 80, 80, 70, 70, 70, 60, 60, 60]
    assert all(s["shown"] for s in a["spots"])
    # The board holds rows down to y = 5 (5 inside its top): 80 .. 10, eight rows of three.
    assert a["room"] == 24
    # More than the board holds: the rows go on outward past it.
    b = got["b"]
    assert len(b["spots"]) == 40 and sum(s["shown"] for s in b["spots"]) == 24
    assert all(s["p"][1] <= 0 for s in b["spots"] if not s["shown"])


@node
def test_a_row_past_the_windows_is_never_west_of_the_cut():
    # The board's west side is the cut (x = 10 here): the west column of the rows is not used.
    windows = [[0, 100], [20, 100], [40, 100], [0, 90], [20, 90], [40, 90]]
    board = [[10, 0], [90, 0], [90, 200], [10, 200]]
    code = "\n".join([_inner("within"), _inner("clearOf"), _inner("seniorRows"),
                      f"process.stdout.write(JSON.stringify(seniorRows({json.dumps(windows)}, {json.dumps(board)}, 5, 60)));"])
    got = _run(code)
    assert len(got["spots"]) == 60
    assert all(s["p"][0] >= 15 for s in got["spots"])


@node
def test_at_the_meeting_the_school_rises_to_the_size_it_had_with_its_ground():
    # 直し39: cut narrower, the school would rise larger (upright, twice as
    # large: its top out of the room); its scale from the size it had, so the
    # table and the seats round it are as they were (直し37).
    consts = "\n".join(_const(n) for n in ("RISE_PART", "AI_BAND_UP")) + "\nconst TABLE_RX = 100, TABLE_RY = 40;"
    code = "\n".join([consts, _inner("riseAt"),
                      "const whole = { width: 1413, height: 782, ring: [1081, 368], pxPerM: 6.79 };",
                      "const cut = { ...whole, width: 693, ring: [361, 368], rise: [1413, 782] };",
                      "const out = {};",
                      "for (const upright of [true, false]) {",
                      "  const room = upright ? { W: 736, H: 684, mapBox: [0, 0, 736, 479], upright }",
                      "    : { W: 1122, H: 491, mapBox: [240, 0, 640, 491], upright };",
                      "  out[upright] = [riseAt({ ...room, model: whole }), riseAt({ ...room, model: cut })]",
                      "    .map((r) => ({ k: r.pic.k, scale: r.scale, top: r.pic.y }));",
                      "}",
                      "process.stdout.write(JSON.stringify(out));"])
    got = _run(code)
    for upright, (whole, cut) in got.items():
        assert abs(whole["k"] - cut["k"]) < 1e-9 and abs(whole["scale"] - cut["scale"]) < 1e-9, upright
        assert cut["top"] >= 0, upright  # The picture's top in the room.
    assert "const [across, tall] = model.rise || [model.width, model.height];" in _inner("riseAt")
    assert "rise: [p.width, p.height]" in _inner("cutYard") and "rise: [1400, 760]" in _const("PLAIN_YARD")
