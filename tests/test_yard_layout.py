"""直し35-2: the map alone, as large as the room lets it be (an upright
screen: at the top, the room's foot left for the AI's seat), the school on
it where it is, put larger (直し37-1: SCHOOL_SCALE times its real size). The school's large picture comes from
outside the repo; with none, a plain building and a ground with no name,
the same seats put on it. The AI's seat over a corner of the map."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino.school_picture import load

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

RELIEF = (2400, 1840)  # The relief picture's size (mapdata/relief_projection.json).
PICTURE = {"width": 1413, "height": 737}  # The large picture as drawn (its size only matters here).
# The rooms the five screens give the drawing (measured: the map's room on the one screen).
ROOMS = {"1920x1080": (1676, 886), "1536x760": (1292, 565), "1366x650": (1122, 491),
         "1180x820": (936, 614), "768x1024": (736, 684)}


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _consts(*names):
    out = []
    for name in names:
        match = re.search(rf"const {name} = [^;]+;", MAP)
        out.append(match.group(0))
    return "\n".join(out)


def _compose(rooms):
    program = "\n".join([_consts("UPRIGHT_UNDER", "AI_BAND_UP"), _inner("compose"),
                         f"const rooms = {json.dumps(rooms)};",
                         "const out = {};",
                         f"for (const [k, [w, h]] of Object.entries(rooms)) out[k] = compose({{ w, h }}, {RELIEF[0]}, {RELIEF[1]});",
                         "process.stdout.write(JSON.stringify(out));"])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


@node
def test_the_map_fills_the_room_and_upright_leaves_its_foot_for_the_ais_seat():
    laid = _compose(ROOMS)
    for size, (w, h) in ROOMS.items():
        one = laid[size]
        assert abs(one["W"] / one["H"] - w / h) < 1e-6  # The drawing is the room's shape.
        mx, my = one["map"]
        box = [mx, my, mx + RELIEF[0], my + RELIEF[1]]
        assert box[0] >= -1e-6 and box[1] >= -1e-6 and box[2] <= one["W"] + 1e-6 and box[3] <= one["H"] + 1e-6, size
        px = w / one["W"]
        if size == "768x1024":
            assert one["upright"] and my == 0  # At the top,
            assert box[3] <= one["H"] * (1 - 0.3) + 1e-6  # over the band left for the AI's seat,
            assert (box[2] - box[0]) * px >= w * 0.78 or (box[3] - box[1]) * px >= h * 0.7 - 1, size
        else:
            # As large as it can be: the room's whole height or width.
            assert not one["upright"]
            assert abs((box[3] - box[1]) * px - h) < 1 or abs((box[2] - box[0]) * px - w) < 1, size
            assert abs(mx - (one["W"] - RELIEF[0]) / 2) < 1e-6  # In the middle.


@node
def test_the_school_is_put_larger_where_it_is_by_one_scale():
    program = "\n".join([_consts("SCHOOL_SCALE"), _inner("schoolOnMap"),
                         "const model = { pxPerM: 6.79, ring: [1081, 368] };",
                         "const unitsPerM = 2.33 / 33.4225;",  # The relief's units to a metre.
                         "process.stdout.write(JSON.stringify(schoolOnMap([1000, 500], model, unitsPerM)));"])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    got = json.loads(done.stdout.decode("utf-8"))
    # The ring's middle on the school's point; 96.2 m of ground (653 px), at
    # its real size about 6.7 units of the map, SCHOOL_SCALE (22) times that.
    scale = float(re.search(r"const SCHOOL_SCALE = ([\d.]+);", MAP).group(1))
    assert scale == 22
    assert abs(got["x"] + 1081 * got["k"] - 1000) < 1e-6 and abs(got["y"] + 368 * got["k"] - 500) < 1e-6
    assert abs(653 * got["k"] - scale * 96.2 * 2.33 / 33.4225) < 0.05 * scale


def test_the_plain_yard_has_its_windows_and_ground_and_no_name():
    model = _inner("yardModel")
    assert "rows.flatMap((y) => Array.from({ length: columns }" in model
    assert re.search(r"rows: \[\d+, \d+\], columns: 20 \}", MAP)  # Two rows of 20 windows.
    drawn = _inner("drawYard")
    assert "text" not in drawn  # No name on it.
    assert 'svgEl("g", { class: "yard-building" })' in drawn and 'group.setAttribute("aria-hidden", "true")' in drawn
    assert ".yard { pointer-events: none; }" in CSS


def test_the_large_picture_first_and_without_it_the_plain_yard():
    begun = _inner("init")
    assert "const yard = map.school_picture && map.school_picture.yard;" in begun
    assert "image.onload = () => { yardPicture = yard; go(); };" in begun and "image.onerror = go;" in begun


def test_the_drawing_follows_the_rooms_shape_but_not_while_a_round_plays():
    again = _inner("recompose")
    assert "if (!view || camera || playing || flights.length || one) return false;" in again
    # The table open: opened again for the same round, at once (直し33-4).
    assert "if (reopen) openTable(reopen.result, reopen.order, tableCenter(), () => true, true);" in again
    assert "const motion = !reduced() && !again;" in MAP
    assert "recompose();" in _inner("show") and "if (recompose()) return;" in _inner("watchSize")


def test_the_plane_lands_at_the_school_on_the_map():
    stage = APP[APP.index("function mapStage("):]
    stage = stage[:stage.index("\n}\n")]
    assert 'const end = sighted("#map-svg .yard-landing", 0.5) || [w / 2, h / 2];' in stage
    # On the building: the middle of its windows, not the ground beside it.
    assert 'svgEl("circle", { class: "yard-landing", r: 1,' in _inner("drawYard")


def test_while_the_opening_plays_the_room_is_as_it_will_be_after():
    # Unseen but keeping their room: the plane lands where the school stays.
    assert "#table.opening-on .map-bar { visibility: hidden; }" in CSS
    assert "#table.opening-on .map-bar { display: none; }" not in CSS


def test_the_ais_seat_sits_in_a_free_corner_of_the_map():
    corner = _inner("placeAiCorner")
    assert 'const AI_CORNERS = ["bottom-right", "bottom-left", "top-left"];' in MAP
    assert "for (const corner of AI_CORNERS)" in corner and "if (!n) break;" in corner
    # Chosen once for the drawing as it is: it stays through a round.
    assert "view.aiCorner === undefined" in corner
    assert "placeAiCorner();" in _inner("relayout") and "placeYardColumn" not in MAP
    assert "left: var(--ai-left, 8px); top: var(--ai-top, auto); bottom: var(--ai-bottom, auto); width: var(--ai-w, 320px);" in CSS
    assert "--yard-left" not in CSS


def _png(width, height):
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\x00" * width * 4 for _ in range(height))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_the_large_picture_and_where_its_seats_go_are_read_from_the_folder(tmp_path):
    (tmp_path / "school_yard.png").write_bytes(_png(40, 20))
    about = {"yard": {"windows_px": [[30, 5], [32, 6]], "field_px": [[1, 1], [10, 1], [10, 18], [1, 18]],
                      "ring_centre_px": [31, 8], "px_per_m": 6.79}}
    (tmp_path / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    view = load(tmp_path)
    assert view["yard"] == {"image": "/school/school_yard.png", "width": 40, "height": 20,
                            "windows": [[30, 5], [32, 6]], "field": [[1, 1], [10, 1], [10, 18], [1, 18]],
                            "ring": [31, 8], "px_per_m": 6.79}
    # A spot outside the picture, a ground not of four corners, or no scale: no picture (the plain yard).
    good = about["yard"]
    for bad in ({**good, "windows_px": [[90, 5]]}, {**good, "field_px": [[1, 1], [10, 1], [10, 18]]},
                {**good, "px_per_m": 0}, {k: v for k, v in good.items() if k != "ring_centre_px"}):
        (tmp_path / "school_sprite.json").write_text(json.dumps({"yard": bad}), encoding="utf-8")
        assert load(tmp_path) is None
