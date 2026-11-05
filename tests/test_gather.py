"""直し33-4: when a round's table opens, the seats that spoke gather where
their cards have room, wherever their homes are: round a table where the
map meets the school (upright: between the two), the camera on the whole
drawing. Each card comes from its seat there, no long line from its home;
only while they gather is a seat seen flying from its home. The round over
(the next question, or 「地図にもどす」) they go back home; with motion
reduced they are there at once."""

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
ROOMS = {"1920x1080": (1676, 886), "1536x760": (1292, 565), "1366x650": (1122, 491),
         "1180x820": (936, 614), "768x1024": (736, 684)}


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _consts(*names):
    return "\n".join(re.search(rf"const {name} = [^;]+;", MAP).group(0) for name in names)


@node
def test_the_table_is_where_the_map_meets_the_school_and_of_a_size_for_the_room():
    program = "\n".join([
        _consts("MAP_SHARE", "YARD_SHARE", "MAP_SHARE_UP", "ROOM_GAP", "UPRIGHT_UNDER", "AI_BAND_UP", "TABLE_RX", "TABLE_TILT", "GATHER_CARD"),
        _inner("compose"), _inner("gatherAt"), _inner("onTable"),
        f"const rooms = {json.dumps(ROOMS)}; const out = {{}};",
        "for (const [k, [w, h]] of Object.entries(rooms)) {",
        "  const laid = compose({ w, h }, 2400, 1840, { width: 1413, height: 737 });",
        "  const unit = laid.W / w, center = gatherAt({ W: laid.W, H: laid.H, mapBox: [...laid.map, 2400, 1840], upright: laid.upright, unit });",
        "  const seats = [0, 90, 180, 270].map((a) => onTable(center, a, SEAT_OUT).map((v) => v / unit));",
        "  out[k] = { at: center.at.map((v) => v / unit), upright: laid.upright, mapRight: (laid.map[0] + 2400) / unit,",
        "    mapBottom: (laid.map[1] + 1840) / unit, seats, w, h };",
        "}",
        "process.stdout.write(JSON.stringify(out));",
    ])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    got = json.loads(done.stdout.decode("utf-8"))
    for name, one in got.items():
        x, y = one["at"]
        if one["upright"]:
            assert abs(x - one["w"] / 2) < 1 and one["mapBottom"] <= y <= one["mapBottom"] + 16, name
        else:
            assert one["mapRight"] <= x <= one["mapRight"] + 16 and abs(y - one["h"] / 2) < 1, name
        # The seats round it inside the room, the ring wider than high (seen from above at a slant).
        xs = [p[0] for p in one["seats"]]
        ys = [p[1] for p in one["seats"]]
        assert min(xs) > 0 and max(xs) < one["w"] and min(ys) > 0 and max(ys) < one["h"], name
        assert max(xs) - min(xs) > max(ys) - min(ys), name
        assert 54 <= (max(xs) - min(xs)) / 2 * 150 / (150 + 48) <= 97, name  # The top's half across, CSS px.


def test_no_camera_goes_to_the_basin_the_seats_fly_from_their_homes():
    table = _inner("tableRound")
    assert "tableView" not in MAP and "moveTo(tableView" not in table
    assert "openTable(result, order, tableCenter(), still);" in table
    # They light at their homes with no card there: cards only from the table.
    assert "bubble(id, first[id])" not in _inner("tableRound")
    opened = _inner("openTable")
    assert "const [x0, y0] = spotOf(sitting.id);" in opened  # From its home.
    assert 'points[sitting.id].node.classList.add("away");' in opened
    assert "if (!motion) return landed.push(Promise.resolve(token));" in opened  # Reduced: at once.
    assert ".pt.away { visibility: hidden; }" in CSS


def test_the_round_over_they_go_back_home():
    cleared = _inner("clearTable")
    assert 'node.classList.remove("away");' in cleared
    closed = MAP[MAP.index("async function closeTable("):]
    closed = closed[:closed.index("\n  }\n")]
    assert "if (!reduced()) {" in closed and "const [x, y] = spotOf(t.id);" in closed
    assert closed.index("await Promise.all(back);") < closed.index("clearTable();")
    # The next question clears the table at once (clearRound), the seats at home.
    assert "clearTable();" in _inner("clearRound")


def test_a_card_shows_the_head_of_its_words_and_all_of_them_pressed():
    clamp = CSS[CSS.index('.table-bubble:not([aria-expanded="true"]) .voice {'):]
    clamp = clamp[:clamp.index("}")]
    assert "-webkit-line-clamp: 2;" in clamp and "overflow: hidden;" in clamp


def test_the_cards_are_put_before_the_empty_chairs_labels():
    # A long label put first took a card's place in its column (直し33-5).
    laid = _inner("relayout")
    assert laid.index("placeTableBubbles(frameBox, frameSize, taken)") < laid.index('".table-label.empty"')
