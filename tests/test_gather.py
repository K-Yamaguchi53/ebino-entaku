"""直し33-4, 直し35-3: when a round's table opens, the school rises from the
map and the seats that spoke gather where their cards have room, wherever
their homes are: on an arc round its ring (the round table), the camera on the whole
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
def test_the_school_rises_to_the_middle_large_and_whole_and_its_ring_is_the_table():
    # 直し35-3: the picture at least 6 tenths of the map's height (upright: 8
    # tenths of the width), whole in the drawing, its ring's middle the
    # meeting's middle; the ring the table's top.
    program = "\n".join([
        _consts("UPRIGHT_UNDER", "AI_BAND_UP", "TABLE_RX", "TABLE_TILT", "GATHER_CARD", "RISE_PART"),
        _inner("compose"), _inner("riseAt"), _inner("onTable"),
        f"const rooms = {json.dumps(ROOMS)}; const out = {{}};",
        "const model = { width: 1413, height: 782, ring: [1081, 368], pxPerM: 6.79 };",
        "for (const [k, [w, h]] of Object.entries(rooms)) {",
        "  const laid = compose({ w, h }, 2400, 1840);",
        "  const unit = laid.W / w;",
        "  const c = riseAt({ W: laid.W, H: laid.H, mapBox: [...laid.map, 2400, 1840], upright: laid.upright, model });",
        "  const p = c.pic, box = [p.x, p.y, p.x + model.width * p.k, p.y + model.height * p.k].map((v) => v / unit);",
        "  const east = onTable(c, 0, 0, 0).map((v) => v / unit), north = onTable(c, 270, 0, 0).map((v) => v / unit);",
        "  out[k] = { box, at: c.at.map((v) => v / unit), ring: [p.x / unit + 1081 * p.k / unit, p.y / unit + 368 * p.k / unit],",
        "    east, north, mapH: 1840 / unit, upright: laid.upright, w, h, rx: 40.35 * 6.79 * p.k / unit };",
        "}",
        "process.stdout.write(JSON.stringify(out));",
    ])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    for name, one in json.loads(done.stdout.decode("utf-8")).items():
        x0, y0, x1, y1 = one["box"]
        assert x0 >= 0 and y0 >= 0 and x1 <= one["w"] + 0.5 and y1 <= one["h"] + 0.5, name  # Whole.
        if one["upright"]:
            assert x1 - x0 >= one["w"] * 0.8 - 0.5, name
            assert y1 <= one["h"] * (1 - 0.3) + 0.5, name  # Over the AI's band, not into it.
        else:
            assert y1 - y0 >= min(one["mapH"], one["h"]) * 0.6 - 0.5, name
        # The ring's middle is the meeting's; the ring's edge the table's.
        assert abs(one["ring"][0] - one["at"][0]) < 0.01 and abs(one["ring"][1] - one["at"][1]) < 0.01, name
        assert abs(one["east"][0] - one["at"][0] - one["rx"]) < 0.5, name
        assert abs((one["at"][1] - one["north"][1]) - one["rx"] * 0.788) < 0.5, name


def test_the_seats_sit_on_an_arc_round_the_ring_and_the_school_goes_back_down():
    opened = MAP[MAP.index("  async function openTable("):]
    opened = opened[:opened.index("\n  }\n")]
    assert "const risen = riseSchool(center, motion);" in opened and "await risen.done;" in opened
    assert "onArc(gatherSpots(" in opened
    assert "table-grain" not in MAP and "table-foot" not in opened  # No wooden table any more.
    rise = _inner("riseSchool")
    assert 'from.classList.add("lifted");' in rise and "if (motion) {" in rise
    assert ".yard.lifted { visibility: hidden; }" in CSS
    closed = _inner("closeTable")
    assert "sinkSchool()" in closed
    assert 'classList.remove("lifted")' in _inner("clearTable")


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
    assert closed.index("await Promise.all([...back, sinkSchool()]);") < closed.index("clearTable();")
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


def test_the_meeting_is_laid_out_for_the_room_as_it_is_and_the_maps_ways_step_back():
    # The room changes with the question sent: the round draws again first (直し35-3).
    table = _inner("tableRound")
    assert table.index("recompose();") < table.index("playing = true;")
    # At the meeting the map's ways and its arrow are unseen and take no room from the cards.
    assert '[...overlay.querySelectorAll(tableTop ? ".map-hint" : ".map-compass, .map-around, .map-hint")]' in _inner("fixedBoxes")
    assert ".map-frame:has(svg.dim) .map-around, .map-frame:has(svg.dim) .map-compass { visibility: hidden; }" in CSS


def test_the_column_on_the_ais_side_stops_over_it_and_its_corner_stays_for_the_drawing():
    spots = _inner("gatherSpots")
    assert 'const limits = { left: ai === "bottom-left" ? under : foot, right: ai === "bottom-right" ? under : foot };' in spots
    assert "ai: view.aiCorner }), center.at);" in MAP
    corner = _inner("placeAiCorner")
    assert "const tall = h;" in corner and "view.aiFor !== key" in corner
    assert "height: var(--ai-h, 40%);" in CSS
