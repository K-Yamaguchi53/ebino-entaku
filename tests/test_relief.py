"""The basin drawn as a model under the map (SPEC 14-66): the three files in
the repo, what setup sends, the flat map when they are missing or broken,
the sources on the screen and in the README, and nothing outside loaded."""

import json
import re
import shutil
import threading
from pathlib import Path

import pytest
from conftest import COMPANY, DISPLAY_NAME, make_seat
from fake_client import FakeClient

from ebino import app as app_module
from ebino import relief, seat_map
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from ebino.relief import load_relief, parse_relief, webp_size
from ebino.session import Library
from test_app import request
from test_session import UTTERANCES

REPO = Path(__file__).resolve().parent.parent
SOURCE = ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH "
          "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved")
NO_LIABILITY = ("The organisations in charge of the Copernicus programme by law or by delegation do not incur "
                "any liability for any use of the Copernicus WorldDEM-30.")
MAP = seat_map.load_map()
VIEWBOX = (MAP.width, MAP.height)


def vp8x(width, height):
    """The head of a WebP with a VP8X chunk (as an image with alpha has)."""
    body = b"VP8X" + (10).to_bytes(4, "little") + b"\x10\x00\x00\x00"
    body += (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WEBP" + body + b"\x00" * 8


def copy_relief(tmp_path):
    for name in (relief.IMAGE, relief.PROJECTION, relief.HEIGHTS):
        shutil.copy(relief.RELIEF_DIR / name, tmp_path / name)
    return tmp_path


def library(relief_data, show_private=True):
    table = [make_seat(seat_id="S01", district="えびの市大字原田"),
             make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="",
                       display_name="先輩", district="")]
    return Library.build(table, UTTERANCES, {}, show_private, map_data=MAP, relief_data=relief_data)


def setup_of(lib):
    return App(lib, Gate(FakeClient([]), NameList.build(lib.seats, {}))).setup()


# --- the files in the repo ---

def test_the_three_files_in_the_repo_read_fit_the_map_and_are_small():
    data = load_relief(VIEWBOX)
    assert data is not None
    assert data["image"] == "/relief.webp" and data["res"] == [2400, 1840]
    assert len(data["px"]) == 4 and len(data["py"]) == 4 and data["z"]["m_per_unit"] > 0
    assert data["step"] == 10 and len(data["rows"]) >= 90 and len(data["rows"][0]) == 101
    # Small enough for the repo: the picture under 1 MB, the grid and the projection a few dozen KB.
    assert (relief.RELIEF_DIR / relief.IMAGE).stat().st_size < 400_000
    assert (relief.RELIEF_DIR / relief.HEIGHTS).stat().st_size < 100_000
    assert (relief.RELIEF_DIR / relief.PROJECTION).stat().st_size < 2_000
    # No raw heights and no large picture in the repo.
    assert not list((REPO / "mapdata").glob("*.png")) and not list((REPO / "mapdata").glob("*.npy"))
    assert not list((REPO / "mapdata").glob("*.tif"))


def test_the_grid_keeps_its_source_and_the_day_it_was_taken():
    raw = json.loads((relief.RELIEF_DIR / relief.HEIGHTS).read_text(encoding="utf-8"))
    assert raw["source"] == SOURCE  # Word for word.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw["fetched"])
    assert "Copernicus DEM GLO-30" in raw["dem"]
    assert raw["viewbox"] == [0, 0, MAP.width, MAP.height]


def test_the_tools_give_the_same_source_line_and_keep_the_tiles_outside_the_repo():
    fetch = (REPO / "tools" / "fetch_copernicus_dem.py").read_text(encoding="utf-8")
    assert "copernicus-dem-30m.s3.amazonaws.com" in fetch
    for tile in ("N31_00_E130_00", "N31_00_E131_00", "N32_00_E130_00", "N32_00_E131_00"):
        assert tile in fetch
    assert "WORK_DIR must be outside the repo" in fetch
    import importlib.util
    spec = importlib.util.spec_from_file_location("fetch_copernicus_dem", REPO / "tools" / "fetch_copernicus_dem.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SOURCE == SOURCE
    height, _ = module.screen()  # The kept box gives the map file's viewBox.
    assert abs(height - MAP.height) <= 0.06
    assert module.main([str(REPO / "mapdata")]) == 2  # Inside the repo: refused before anything is fetched.


# --- missing or broken: the flat map, and the app still starts ---

@pytest.mark.parametrize("broken", ["no image", "no projection", "no heights", "image not webp", "wrong size",
                                    "grid of another map", "not a number", "no source", "empty json"])
def test_a_missing_or_broken_file_gives_the_flat_map(tmp_path, broken):
    folder = copy_relief(tmp_path)
    projection = json.loads((folder / relief.PROJECTION).read_text(encoding="utf-8"))
    heights = json.loads((folder / relief.HEIGHTS).read_text(encoding="utf-8"))
    if broken == "no image":
        (folder / relief.IMAGE).unlink()
    elif broken == "no projection":
        (folder / relief.PROJECTION).unlink()
    elif broken == "no heights":
        (folder / relief.HEIGHTS).unlink()
    elif broken == "image not webp":
        (folder / relief.IMAGE).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    elif broken == "wrong size":
        projection["res"] = [1200, 920]
    elif broken == "grid of another map":
        heights["viewbox"] = [0, 0, 1000, 800]
    elif broken == "not a number":
        heights["rows"][3][4] = None
    elif broken == "no source":
        heights["source"] = ""
    elif broken == "empty json":
        (folder / relief.HEIGHTS).write_text("{}", encoding="utf-8")
    if broken in ("wrong size",):
        (folder / relief.PROJECTION).write_text(json.dumps(projection), encoding="utf-8")
    if broken in ("grid of another map", "not a number", "no source"):
        (folder / relief.HEIGHTS).write_text(json.dumps(heights), encoding="utf-8")
    assert load_relief(VIEWBOX, folder) is None
    setup = setup_of(library(load_relief(VIEWBOX, folder)))
    assert setup["map"] is not None and setup["map"]["relief"] is None  # The flat map.
    assert setup["map"]["boundary"] and all("x" in seat for seat in setup["seats"])


def test_the_copied_files_give_the_picture(tmp_path):
    assert load_relief(VIEWBOX, copy_relief(tmp_path)) == load_relief(VIEWBOX)


def test_no_map_means_no_picture_either_and_the_seat_list_alone():
    lib = Library.build([make_seat()], [], {}, map_data=None, relief_data=load_relief(VIEWBOX))
    assert lib.relief is None
    setup = setup_of(lib)
    assert setup["map"] is None and [seat["seat_id"] for seat in setup["seats"]] == ["S01"]


def test_library_load_reads_the_picture_and_starts_without_it(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(relief, "load_relief", lambda viewbox, folder=None: calls.append((viewbox, folder)) or None)
    from ebino import session
    monkeypatch.setattr(session, "load_seats", lambda path: [make_seat(district="えびの市大字原田")])
    monkeypatch.setattr(session, "load_utterances", lambda folder: [])
    monkeypatch.setattr(session, "load_topics", lambda folder: {})
    lib = Library.load(tmp_path, relief_dir=tmp_path / "none")
    assert calls == [(VIEWBOX, tmp_path / "none")]
    assert lib.map_view()["relief"] is None and lib.relief_report() == "立体の絵なし（平らな地図）"


def test_the_start_up_line_says_whether_there_is_a_picture():
    assert library(load_relief(VIEWBOX)).relief_report() == "立体の絵あり"
    assert library(None).relief_report() == "立体の絵なし（平らな地図）"


def test_a_webp_header_gives_its_size_and_anything_else_is_refused():
    assert webp_size(vp8x(2400, 1840)) == (2400, 1840)
    lossless = b"RIFF" + b"\x00" * 4 + b"WEBPVP8L" + b"\x00" * 4 + b"\x2f" + \
        ((99) | (49 << 14)).to_bytes(4, "little") + b"\x00" * 8
    assert webp_size(lossless) == (100, 50)
    lossy = b"RIFF" + b"\x00" * 4 + b"WEBPVP8 " + b"\x00" * 4 + b"\x00\x00\x00\x9d\x01\x2a" + \
        (640).to_bytes(2, "little") + (480).to_bytes(2, "little") + b"\x00" * 8
    assert webp_size(lossy) == (640, 480)
    for bad in (b"", b"RIFF1234WEBX" + b"\x00" * 30, b"\x89PNG" + b"\x00" * 40):
        with pytest.raises(ValueError):
            webp_size(bad)


def test_a_picture_too_large_is_refused():
    projection = json.loads((relief.RELIEF_DIR / relief.PROJECTION).read_text(encoding="utf-8"))
    heights = json.loads((relief.RELIEF_DIR / relief.HEIGHTS).read_text(encoding="utf-8"))
    image = vp8x(2400, 1840)
    assert parse_relief(image, projection, heights, VIEWBOX)["res"] == [2400, 1840]
    with pytest.raises(ValueError):
        parse_relief(image + b"\x00" * relief.MAX_IMAGE_BYTES, projection, heights, VIEWBOX)


# --- what setup sends ---

def test_setup_gives_the_picture_with_the_map_and_no_seat_words():
    lib = library(load_relief(VIEWBOX))
    setup = setup_of(lib)
    picture = setup["map"]["relief"]
    assert picture["image"] == "/relief.webp" and picture["source"] == SOURCE
    assert set(picture) == {"image", "res", "px", "py", "z", "step", "rows", "source"}
    sent = json.dumps(picture, ensure_ascii=False)
    for word in (COMPANY, DISPLAY_NAME, "はるかぜ", "山川", "会社名", "表示名", "S01", "P01", "先輩"):
        assert word not in sent
    # The seats' points are still seat_map.py's: the picture moves them on the screen only.
    assert {seat["seat_id"]: (seat["x"], seat["y"]) for seat in setup["seats"]} == \
        {seat["seat_id"]: (seat["x"], seat["y"]) for seat in setup_of(library(None))["seats"]}


def test_the_picture_file_holds_no_seat_table_words():
    for name in (relief.PROJECTION, relief.HEIGHTS):
        text = (relief.RELIEF_DIR / name).read_text(encoding="utf-8")
        for word in ("会社名", "表示名", "はるかぜ理容", "山川さん", COMPANY, DISPLAY_NAME):
            assert word not in text


# --- served, and nothing loaded from outside ---

@pytest.fixture
def server():
    the_app = App(library(load_relief(VIEWBOX)), Gate(FakeClient([]), NameList.build([], {})))
    srv = make_server(the_app, 0, timeout=1)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def test_the_picture_and_the_title_font_are_served(server):
    status, body = request(server, "GET", "/relief.webp")
    assert status == 200 and body == (relief.RELIEF_DIR / relief.IMAGE).read_bytes()
    status, body = request(server, "GET", "/title.woff")
    assert status == 200 and body[:4] == b"wOFF"
    for path in ("/relief_heights.json", "/mapdata/relief.webp", "/title.OFL.txt"):
        assert request(server, "GET", path)[0] == 404


def test_a_picture_gone_after_start_is_a_404_not_a_crash(server, monkeypatch, tmp_path):
    monkeypatch.setitem(app_module.MAP_FILES, "/relief.webp", (tmp_path / "gone.webp", "image/webp"))
    assert request(server, "GET", "/relief.webp")[0] == 404
    assert request(server, "GET", "/api/setup")[0] == 200


def test_the_title_font_holds_only_the_titles_characters_and_its_license_is_beside_it():
    font_file = app_module.STATIC_DIR / "title.woff"
    assert font_file.read_bytes()[:4] == b"wOFF" and font_file.stat().st_size < 20_000
    ttlib = pytest.importorskip("fontTools.ttLib")
    font = ttlib.TTFont(font_file)
    assert {chr(c) for c in font.getBestCmap()} == set("えびの円卓0123456789")
    license_text = (app_module.STATIC_DIR / "title.OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in license_text and "Shippori Mincho" in license_text
    css = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    assert 'url("/title.woff")' in css and '"BIZ UDPMincho"' in css


# --- the sources ---

def test_the_copernicus_source_is_on_the_screen_beside_openstreetmap():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    html = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert '$("map-dem").textContent = view.relief ? map.relief.source : ""' in script
    assert '<span id="map-source"></span><span id="map-dem" hidden></span>' in html
    # The words the screen shows are the grid file's, which setup sends.
    assert library(load_relief(VIEWBOX)).map_view()["relief"]["source"] == SOURCE


def test_the_readme_has_the_source_the_no_liability_line_and_how_to_run_the_two_tools():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert SOURCE in readme and NO_LIABILITY in readme
    assert "python tools/fetch_copernicus_dem.py" in readme
    assert "blender -b --python tools/render_relief.py --" in readme
    assert "numpy" in readme and "Pillow" in readme
    assert "© OpenStreetMap contributors" in readme


# Years (SPEC 14-34): none on the screen or in the README, but a fixed source
# line someone else wrote keeps its years as it is (the Copernicus line), and
# so do the bundled licences of rough.js and the title font.
YEAR = re.compile(r"(?<![0-9])(?:19|20)[0-9]{2}(?![0-9])|令和|平成")
OTHERS_TEXTS = ("rough.js", "rough.LICENSE.txt", "title.OFL.txt", "title.woff")


def test_no_year_on_the_screen_or_in_the_readme_but_the_fixed_source_line():
    places = [path for path in app_module.STATIC_DIR.iterdir() if path.is_file() and path.name not in OTHERS_TEXTS]
    places += [REPO / "README.md", *sorted((REPO / "texts").iterdir())]
    for path in places:
        text = path.read_text(encoding="utf-8").replace(SOURCE, "").replace("http://www.w3.org/2000/svg", "")
        assert not YEAR.search(text), (path.name, YEAR.search(text).group(0))
    # What setup sends the screen: the same.
    sent = json.dumps(setup_of(library(load_relief(VIEWBOX), show_private=False)), ensure_ascii=False)
    assert not YEAR.search(sent.replace(SOURCE, "").replace("http://www.w3.org/2000/svg", ""))


def test_the_map_buttons_words_come_from_texts():
    from ebino.texts import map_buttons, screen_texts
    words = map_buttons()
    assert list(words) == ["back", "zoom_in", "zoom_out", "zoom_all"]
    assert words["back"] == {"text": "地図にもどす", "label": "地図にもどす"}
    assert words["zoom_in"]["text"] == "＋" and words["zoom_in"]["label"]
    assert screen_texts()["map_buttons"] == words
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert "app.state.texts.map_buttons" in script
    html = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    for button in ("map-back", "map-zoom-in", "map-zoom-out", "map-zoom-all"):
        assert re.search(rf'<button type="button" id="{button}"[^>]*></button>', html)  # Empty: words from texts/.


def test_a_map_buttons_table_missing_a_row_is_refused(tmp_path, monkeypatch):
    from ebino import texts
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    (tmp_path / "map_buttons.tsv").write_text("ID\t文字\t読み上げ\nback\t地図にもどす\t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        texts.map_buttons()


def test_the_screen_moves_points_on_the_screen_only_and_keeps_its_fallbacks():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert "picture.onerror = () => build(seats, false)" in script  # A picture that does not load: flat.
    assert "if (withRelief) return build(seats, false);" in script  # One that fails to draw: flat.
    assert "reduced()" in script and "prefers-reduced-motion" in script
    app_js = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "if (data.map && window.rough) onMap(" in app_js  # No map: the seat list alone.
