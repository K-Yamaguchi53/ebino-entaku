"""直し33-2: the map on the left and the school with its sports ground on the
right (an upright screen: the map on top, the school under it), both as
large as the room lets them be, the room round them left for the round
table. The school's large picture comes from outside the repo; with none,
a plain building and a ground with no name, the same seats put on it."""

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


def _compose(rooms, yard=PICTURE):
    program = "\n".join([_consts("MAP_SHARE", "YARD_SHARE", "MAP_SHARE_UP", "ROOM_GAP", "UPRIGHT_UNDER"), _inner("compose"),
                         f"const rooms = {json.dumps(rooms)}, yard = {json.dumps(yard)};",
                         "const out = {};",
                         f"for (const [k, [w, h]] of Object.entries(rooms)) out[k] = compose({{ w, h }}, {RELIEF[0]}, {RELIEF[1]}, yard);",
                         "process.stdout.write(JSON.stringify(out));"])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


def _boxes(laid, yard=PICTURE):
    mx, my = laid["map"]
    y = laid["yard"]
    return [mx, my, mx + RELIEF[0], my + RELIEF[1]], [y["x"], y["y"], y["x"] + yard["width"] * y["k"],
                                                     y["y"] + yard["height"] * y["k"]]


@node
@pytest.mark.parametrize("yard", [PICTURE, {"width": 1400, "height": 760}], ids=["picture", "plain"])
def test_the_map_is_left_and_the_school_right_or_under_it_upright(yard):
    laid = _compose(ROOMS, yard)
    for size, (w, h) in ROOMS.items():
        one = laid[size]
        assert abs(one["W"] / one["H"] - w / h) < 1e-6  # The drawing is the room's shape.
        m, s = _boxes(one, yard)
        # Both inside the drawing, and apart.
        for box in (m, s):
            assert box[0] >= -1e-6 and box[1] >= -1e-6 and box[2] <= one["W"] + 1e-6 and box[3] <= one["H"] + 1e-6, size
        if size == "768x1024":
            assert one["upright"] and s[1] >= m[3]  # The school under the map.
        else:
            assert not one["upright"] and s[0] >= m[2] and m[0] == 0  # The map on the left, the school right of it.
        # Large: the map at least half the room one way, the school a fifth of its width.
        px = w / one["W"]
        assert (m[2] - m[0]) * px >= w * 0.5 or (m[3] - m[1]) * px >= h * 0.55, size
        assert (s[2] - s[0]) * px >= w * 0.2, size


@node
def test_landscape_leaves_the_room_under_the_school_for_the_ais_seat():
    laid = _compose(ROOMS)
    for size in ("1920x1080", "1536x760", "1366x650", "1180x820"):
        one = laid[size]
        _, s = _boxes(one)
        assert s[3] <= one["H"] * 0.62, size  # Under it, four tenths of the height or so.
        assert one["column"][0] <= s[0] and s[2] <= one["column"][1]


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
    assert "if (!view || tableAt || camera || timers.length || flights.length) return false;" in again
    assert "recompose();" in _inner("show") and "if (recompose()) return;" in _inner("watchSize")


def test_the_plane_lands_at_the_school_beside_the_map():
    stage = APP[APP.index("function mapStage("):]
    stage = stage[:stage.index("\n}\n")]
    assert 'const end = sighted("#map-svg .yard-landing", 0.5) || [w / 2, h / 2];' in stage
    # On the building: the middle of its windows, not the ground beside it.
    assert 'svgEl("circle", { class: "yard-landing", r: 1,' in _inner("drawYard")


def test_while_the_opening_plays_the_room_is_as_it_will_be_after():
    # Unseen but keeping their room: the plane lands where the school stays.
    assert "#table.opening-on .map-bar { visibility: hidden; }" in CSS
    assert "#table.opening-on .map-bar { display: none; }" not in CSS


def test_the_ais_seat_sits_in_the_schools_column():
    assert "--yard-left" in _inner("placeYardColumn") and "placeYardColumn();" in _inner("relayout")
    assert "#ai-seat { position: absolute; z-index: 6; left: calc(var(--yard-left, 0px)" in CSS
    assert "padding-left: min(var(--ai-w)" not in CSS  # The map no longer steps aside for it.


def _png(width, height):
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\x00" * width * 4 for _ in range(height))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_the_large_picture_and_where_its_seats_go_are_read_from_the_folder(tmp_path):
    (tmp_path / "school_yard.png").write_bytes(_png(40, 20))
    about = {"yard": {"windows_px": [[30, 5], [32, 6]], "field_px": [[1, 1], [10, 1], [10, 18], [1, 18]]}}
    (tmp_path / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    view = load(tmp_path)
    assert view["yard"] == {"image": "/school/school_yard.png", "width": 40, "height": 20,
                            "windows": [[30, 5], [32, 6]], "field": [[1, 1], [10, 1], [10, 18], [1, 18]]}
    # A spot outside the picture, or a ground not of four corners: no picture (the plain yard).
    for bad in ({"windows_px": [[90, 5]], "field_px": about["yard"]["field_px"]},
                {"windows_px": [[30, 5]], "field_px": [[1, 1], [10, 1], [10, 18]]}):
        (tmp_path / "school_sprite.json").write_text(json.dumps({"yard": bad}), encoding="utf-8")
        assert load(tmp_path) is None
