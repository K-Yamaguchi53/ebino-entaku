"""The school as a 3D picture on the map (直し25-1): read only from the folder
EBINO_SCHOOL_DIR names (never the repo), only its three files, served from
there alone; the line mark when any of it is missing; on the map no larger
than its most however near, its name under it, taking no presses."""

import json
import struct
import threading
import zlib
from pathlib import Path

import pytest
from conftest import make_seat
from fake_client import FakeClient

from ebino import app as app_module
from ebino import school_picture, seat_map
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from ebino.school_picture import SchoolPicture, folder_from_env, load, png_size
from ebino.session import Library
from test_app import request
from test_session import UTTERANCES

REPO = Path(__file__).resolve().parent.parent
SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def png(width, height):
    """A small, real, all-clear PNG."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + b"\x00" * (4 * width) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def sprite(folder, relief=(173, 168, [92.38, 104.85]), flat=(173, 147, [80.67, 77.06]), extra=True):
    folder.mkdir(parents=True, exist_ok=True)
    about = {"_about": "架空の見本"}
    for kind, entry in (("relief", relief), ("flat", flat)):
        if entry is None:
            continue
        width, height, point = entry
        (folder / f"school_{kind}.png").write_bytes(png(width, height))
        about[kind] = {"file": f"school_{kind}.png", "width": width, "height": height, "school_point_px": point}
    (folder / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    if extra:  # Anything else in the folder is never read nor served.
        (folder / "_raw.json").write_text("{}", encoding="utf-8")
        (folder / "_raw_relief.png").write_bytes(png(4, 4))
    return folder


def test_the_picture_sizes_and_the_schools_point_are_read_from_the_three_files(tmp_path):
    view = load(sprite(tmp_path))
    assert view == {
        "relief": {"image": "/school/school_relief.png", "width": 173, "height": 168, "point": [92.38, 104.85]},
        "flat": {"image": "/school/school_flat.png", "width": 173, "height": 147, "point": [80.67, 77.06]},
        "yard": None,  # No large picture in this folder (直し33-2).
    }
    assert png_size(png(7, 5)) == (7, 5)


def test_a_point_given_for_another_size_is_put_on_the_file_as_it_is(tmp_path):
    folder = sprite(tmp_path)
    about = json.loads((folder / "school_sprite.json").read_text(encoding="utf-8"))
    about["relief"].update(width=346, height=336)  # Said at twice the file's size.
    (folder / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    assert load(folder)["relief"]["point"] == [46.19, 52.42]


@pytest.mark.parametrize("spoil", ["no json", "bad json", "not png", "no point", "point outside", "both gone"])
def test_with_a_file_missing_or_broken_the_school_keeps_its_line_mark(tmp_path, spoil):
    folder = sprite(tmp_path)
    if spoil == "no json":
        (folder / "school_sprite.json").unlink()
    elif spoil == "bad json":
        (folder / "school_sprite.json").write_text("{", encoding="utf-8")
    elif spoil == "not png":
        (folder / "school_relief.png").write_bytes(b"GIF89a" + b"\x00" * 30)
    elif spoil == "no point":
        about = json.loads((folder / "school_sprite.json").read_text(encoding="utf-8"))
        del about["relief"]["school_point_px"]
        (folder / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    elif spoil == "point outside":
        about = json.loads((folder / "school_sprite.json").read_text(encoding="utf-8"))
        about["relief"]["school_point_px"] = [500, 20]
        (folder / "school_sprite.json").write_text(json.dumps(about), encoding="utf-8")
    elif spoil == "both gone":
        (folder / "school_relief.png").unlink()
        (folder / "school_flat.png").unlink()
    view = load(folder)
    if spoil in ("no json", "bad json", "both gone"):
        assert view is None
    else:  # The one picture spoiled goes; the other stays.
        assert view["relief"] is None and view["flat"]["width"] == 173


def test_the_folder_is_the_one_the_env_names_or_its_sprite_folder(tmp_path, monkeypatch):
    monkeypatch.delenv(school_picture.ENV, raising=False)
    assert folder_from_env() is None
    monkeypatch.setenv(school_picture.ENV, str(tmp_path))
    assert folder_from_env() is None  # No sprite file there.
    sprite(tmp_path / "sprite")
    assert folder_from_env() == tmp_path / "sprite"
    sprite(tmp_path)
    assert folder_from_env() == tmp_path
    assert SchoolPicture(None).report() == "校舎の絵なし（線の印）"
    assert SchoolPicture(tmp_path).report() == "校舎の絵あり（relief・flat）"


def test_no_picture_of_the_school_is_in_the_repo():
    for name in ("school_relief.png", "school_flat.png", "school_sprite.json"):
        assert not list(REPO.glob(f"**/{name}")), name


def _app(school):
    table = [make_seat(seat_id="S01", district="えびの市大字原田")]
    lib = Library.build(table, UTTERANCES, {}, False, map_data=seat_map.load_map())
    return App(lib, Gate(FakeClient([]), NameList.build(lib.seats, {})), school=school)


def test_setup_tells_the_map_of_the_pictures_or_of_none(tmp_path):
    assert _app(None).setup()["map"]["school_picture"] is None
    assert _app(SchoolPicture(None)).setup()["map"]["school_picture"] is None
    view = _app(SchoolPicture(sprite(tmp_path))).setup()["map"]["school_picture"]
    assert view["relief"]["image"] == "/school/school_relief.png"
    assert str(tmp_path) not in json.dumps(view)  # The folder itself never reaches the screen.


@pytest.fixture
def served(tmp_path):
    folder = sprite(tmp_path / "school")
    srv = make_server(_app(SchoolPicture(folder)), 0, timeout=1)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, folder
    srv.shutdown()
    srv.server_close()


def test_the_two_pictures_are_served_from_their_folder_and_nothing_else(served):
    srv, folder = served
    for name in ("school_relief.png", "school_flat.png"):
        status, body = request(srv, "GET", f"/school/{name}")
        assert status == 200 and body == (folder / name).read_bytes()
    for path in ("/school/school_sprite.json", "/school/_raw.json", "/school/_raw_relief.png", "/school/",
                 "/school/../school/school_relief.png", "/school/%2e%2e/app.py", "/school_relief.png"):
        assert request(srv, "GET", path)[0] == 404, path


def test_a_picture_gone_after_start_is_a_404(served):
    srv, folder = served
    (folder / "school_flat.png").unlink()
    assert request(srv, "GET", "/school/school_flat.png")[0] == 404
    assert request(srv, "GET", "/api/setup")[0] == 200


def _inner_function(script, name):
    start = script.index(f"function {name}(")
    return script[start:script.index("\n  }\n", start) + 5]


def test_one_school_on_the_map_under_the_points_and_it_takes_no_presses():
    # 直し35-2: the school's large picture (or the plain one) on the map
    # where the school is; no small picture or mark beside it any more.
    draw = SCRIPT[SCRIPT.index("function draw(seats"):]
    draw = draw[:draw.index("\n  }\n")]
    assert draw.index('drawYard(layer("yard"))') < draw.index('layer("points")')
    assert "school_picture[" not in SCRIPT and "loadSchoolPicture" not in SCRIPT
    assert ".yard { pointer-events: none; }" in CSS and ".school { pointer-events: none; }" in CSS
    # Its box is kept clear like the school's name: by labels, cards, 「？」 and place names.
    for name in ("fixedBoxes", "placeAskMarks", "clearSchoolName"):
        assert ".yard-building" in _inner_function(SCRIPT, name)


def test_the_school_is_its_real_size_on_the_map_and_its_name_has_a_most():
    on_map = _inner_function(SCRIPT, "schoolOnMap")
    assert "const k = unitsPerM / model.pxPerM;" in on_map
    assert "x: px - model.ring[0] * k, y: py - model.ring[1] * k, k" in on_map
    draw = SCRIPT[SCRIPT.index("function draw(seats"):]
    assert "schoolOnMap(schoolAt, model, base.S / mPerUnit)" in draw
    assert "map.relief.z.m_per_unit" in draw
    consts = dict((name, float(value)) for name, value in
                  __import__("re").findall(r"(SCHOOL_[A-Z_]+) = ([\d.]+)", SCRIPT))
    assert consts["SCHOOL_TEXT_MAX_PX"] <= 24
    assert "Math.min(TEXT_PX.school * 1.4, SCHOOL_TEXT_MAX_PX)" in _inner_function(SCRIPT, "placeSchool")
