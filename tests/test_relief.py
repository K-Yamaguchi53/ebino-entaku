"""The basin drawn as a model under the map (SPEC 14-66): the three files in
the repo, what setup sends, the flat map when they are missing or broken,
the sources on the screen and in the README, and nothing outside loaded."""

import json
import re
import shutil
import subprocess
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


def _inner_function(script, name):
    start = script.index(f"function {name}(")
    return script[start:script.index("\n  }\n", start) + 5]


# The map's frame at a width, as relayout measures it: the heading at the
# table, two empty chairs' labels and four seats' labels round the table, and
# the zoom buttons and the seats as fixed boxes. Sizes follow the width, as
# the narrow labels and the frame's height do on the screen.
_LAYOUT_RUN = """
const TAG_ON_MAP = %(tag_on_map)s;
%(source)s
function at(width) {
  const frame = { w: width, h: Math.round(width / 1.304) };
  const narrow = width < 560, cx = frame.w / 2, cy = frame.h / 2, r = Math.min(frame.w, frame.h) * 0.3;
  const label = narrow ? [70, 18] : [130, 20];
  const items = [{ w: Math.min(frame.w * 0.7, 288), h: narrow ? 52 : 34, px: cx, py: cy + r * 0.3, gap: 0,
    inView: true, heading: true, atTable: true }];
  for (let k = 0; k < 6; k++) {
    const a = k * Math.PI / 3;
    items.push({ w: label[0], h: label[1], px: cx + r * Math.cos(a), py: cy + r * Math.sin(a), gap: 16,
      inView: true, heading: false, atTable: true });
  }
  const fixed = [[frame.w - 120, frame.h - 40, 116, 36]];
  for (let k = 0; k < 6; k++) {
    const a = k * Math.PI / 3, s = Math.max(16, width / 40);
    fixed.push([cx + r * Math.cos(a) - s / 2, cy + r * Math.sin(a) - s / 2, s, s]);
  }
  return { frame, items, fixed };
}
// The window's width changing step by step; the places at the end.
function after(widths) {
  let spots = null;
  for (const width of widths) {
    const { frame, items, fixed } = at(width);
    spots = planLabels(frame, items, fixed);
  }
  return spots;
}
const runs = %(runs)s;
process.stdout.write(JSON.stringify(runs.map(after)));
"""


def _layouts(runs):
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    tag_on_map = re.search(r"const TAG_ON_MAP = (\d+);", script).group(1)
    source = _inner_function(script, "chooseSpot") + _inner_function(script, "planLabels")
    program = _LAYOUT_RUN % {"tag_on_map": tag_on_map, "source": source, "runs": json.dumps(runs)}
    done = subprocess.run(["node", "-e", program], capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8")), int(tag_on_map)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_headings_place_depends_on_the_width_now_not_on_the_widths_before():
    # 768 -> 375 and 1440 -> 375 (and the long way round) end the same; so do
    # two ways to 700.
    (a, b, c, d, e), tag_on_map = _layouts([[768, 343], [1440, 343], [1440, 768, 520, 600, 343],
                                            [343, 700], [1440, 700]])
    assert tag_on_map == 600
    assert a == b == c
    assert d == e
    # Narrower than TAG_ON_MAP the heading is not on the map; wider, it is.
    assert a[0] is None and d[0] is not None
    # The labels that are shown keep inside the frame and off one another.
    for spots, width in ((a, 343), (d, 700)):
        height = round(width / 1.304)
        assert all(4 <= left and 4 <= top and left < width and top < height for left, top in filter(None, spots))


def test_a_box_is_measured_from_the_frames_corner_and_put_by_planlabels_alone():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    measure = _inner_function(script, "measure")
    # Measured where it was, a box further right wraps narrower and taller.
    assert measure.index('node.style.left = "0px"') < measure.index("getBoundingClientRect")
    relayout = _inner_function(script, "relayout")
    assert "measure(node, frameBox)" in relayout and "planLabels(" in relayout
    assert "place(" not in relayout
    plan = _inner_function(script, "planLabels") + _inner_function(script, "chooseSpot")
    # Nothing from before: only what it is given.
    for outside in ("overlay", "dataset", "document", "vb", "style", "classList"):
        assert outside not in plan


def test_with_motion_reduced_the_camera_still_goes_to_the_table_at_once():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    table = _inner_function(script, "tableRound")
    assert "await moveTo(tableView(center), CAMERA_FOR);" in table
    assert "if (!reduced()) await moveTo(tableView" not in table
    move = _inner_function(script, "moveTo")
    assert "if (reduced() || !ms) {" in move and "setView(target);" in move  # At once, no steps.


def test_the_screen_moves_points_on_the_screen_only_and_keeps_its_fallbacks():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert "picture.onerror = () => build(seats, false)" in script  # A picture that does not load: flat.
    assert "if (withRelief) return build(seats, false);" in script  # One that fails to draw: flat.
    assert "reduced()" in script and "prefers-reduced-motion" in script
    app_js = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "if (data.map && window.rough) onMap(" in app_js  # No map: the seat list alone.


# --- the words drawn on the map, at the four screens it is seen on ---

# The map frame's width (CSS px) in the four windows it is seen in: iPad
# upright and lying, a Chromebook's window under its bars, a PC. As measured
# in the browser (style.css: the map is as wide as the window lets it be with
# its buttons and sources under it, (100vh - 164px) x the drawing's ratio).
SCREENS = {"768x1024": 721, "1180x820": 856, "1366x650": 634, "1920x1080": 1195}

# A round over the real map and picture: seats in the basin and on two of
# the four shelves (a seat with no place, and one from outside, fill the
# other two), a split between two pairs, two empty chairs. The labels, the
# bubbles and the heading are sized as style.css sets them (their words are
# made up here).
_ROUND_SEATS = [("A1", "adult", "えびの市大字原田"), ("A2", "adult", "えびの市大字末永"),
                ("A3", "adult", "えびの市大字亀沢"), ("A4", "adult", "えびの市大字上江"),
                ("P1", "poster", ""), ("C1", "cross", ""), ("A5", "adult", "えびの市大字永山"),
                ("P2", "poster", ""), ("A6", "adult", "架空地区"), ("O1", "outsider_teacher", "")]
_ROUND = {
    "seat_order": ["A1", "A2", "P1", "A4", "C1", "A3"],
    "quotes": [{"utterance_id": f"u{k}", "seat_id": seat, "text": "架空の言葉" * 7}
               for k, seat in enumerate(["A1", "A2", "P1", "A4", "C1", "A3"])],
    "splits": [{"heading": "ここで割れた：休みを\"決めて取る\"か\"空いたら取る\"か", "side_a": ["u0", "u3"],
                "side_b": ["u1", "u5"]}],
    "silent_seats": ["A5", "P2"],
}

_SCENE_RUN = r"""
%(consts)s
let view, vb, frame = { clientWidth: 0 }, shelves = [], points = {};
%(source)s
const setup = %(setup)s, round = %(round)s, screens = %(screens)s;
const map = setup.map;
view = reliefView(map.relief);
const P = view.proj;
const stub = () => { const node = {}; node.setAttribute = (key, value) => { node[key] = value; }; return node; };
for (const seat of setup.seats) points[seat.seat_id] = { seat };
const isSilent = (id) => round.silent_seats.includes(id);
const spotOf = (id) => points[id].seat.outer ? shelfSpot(id) : P(points[id].seat.x, points[id].seat.y, 1.5);
const chars = (text) => [...text].length;
const area = (a, b) => Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0])) *
  Math.max(0, Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]));
const covers = (box, boxes) => boxes.reduce((sum, other) => sum + area(box, other), 0);
const inFrame = (fr, w) => w[2] && w[0] < fr.w && w[1] < fr.h && w[0] + w[2] > 0 && w[1] + w[3] > 0;
// A voice's card as style.css sets it: the voice in 17px Mincho, line height
// 1.8, at most 20em and half the frame across; under it one line of 13px;
// padding 11px 16px 9px.
const REM = 16;
function cardBox(fr, text) {
  const most = Math.min(fr.w * 0.5, fr.w - 8, 20 * 17 + 32);
  const across = chars(text) * 17;
  const w = Math.min(most, across + 32), lines = Math.ceil(across / (w - 32));
  return { w, h: 11 + lines * 17 * 1.8 + 3 + 13 * 1.5 + 9 };
}

function scene(width) {
  frame.clientWidth = width;
  const fr = { w: width, h: width * view.H / view.W };
  const toFrame = (x, y) => [(x - vb.x) / vb.w * fr.w, (y - vb.y) / vb.h * fr.h];
  const perPx = () => vb.w / fr.w;
  shelves = map.shelves.filter((shelf) => setup.kinds[shelf.kind]).map((shelf) => ({ shelf, rect: stub(),
    name: stub(), words: setup.kinds[shelf.kind],
    seats: setup.seats.filter((s) => s.outer && s.kind === shelf.kind).map((s) => s.seat_id) }));
  // The words on the map in the frame, as the screen draws them: each its
  // size in CSS px whatever the zoom, place names a little spaced out.
  // Place names first, then the shelves' names, then the school's.
  const words = () => {
    const out = [];
    const word = (x, y, text, size, spacing, middle) => {
      const w = chars(text) * size * spacing;
      out.push([middle ? x - w / 2 : x, y - size * 1.05, w, size * 1.3]);
    };
    for (const place of map.places) word(...toFrame(...P(place.x, place.y, 2)), place.name, TEXT_PX.place, 1.18, true);
    for (const entry of shelves) word(...toFrame(entry.name.x, entry.name.y), entry.words, TEXT_PX.shelf, 1, false);
    if (map.school) {
      const [x, y] = P(map.school.x, map.school.y, 1), k = Math.max(view.S, TEXT_PX.school * perPx() / 20);
      word(...toFrame(x, y + 28 * k), map.school.label, 20 * k / perPx(), 1, true);
    }
    return out;
  };
  // The buttons are under the map, not over it: nothing of them is in the frame.
  const out = { bubbles: [], labels: [], unplaced: 0, wordsLeftOut: 0, shelfNames: 0, shelfNamesSeen: 0 };

  // The seats light up one by one on the whole map, each with its bubble;
  // the bubbles of the seats just before are still up. Every seat of the
  // round is kept clear from the start (one lit later is not under a bubble).
  vb = { x: 0, y: 0, w: view.W, h: view.H };
  layoutShelves(pointScale());
  out.shelfNames = shelves.length;
  const up = [];
  const still = Math.ceil(BUBBLE_FOR / LIGHT_EVERY) - 1;
  const lit = round.seat_order.map((id) => {
    const [px, py] = toFrame(...spotOf(id)), r = 9.5 * pointScale() / perPx();
    return [px - r, py - r, 2 * r, 2 * r];
  });
  round.seat_order.forEach((id, k) => {
    const [px, py] = toFrame(...spotOf(id));
    const quote = round.quotes.find((q) => q.seat_id === id);
    const text = `「${[...quote.text].slice(0, BUBBLE_CHARS).join("")}…」`;
    const box = { ...cardBox(fr, text), px, py, gap: 18 };
    const all = words();
    const shelfNames = all.slice(map.places.length, map.places.length + shelves.length).filter((w) => inFrame(fr, w));
    out.shelfNamesSeen = Math.max(out.shelfNamesSeen, shelfNames.length);
    const seen = seenWords(fr, all, null);
    const fixed = [...seen, ...lit];
    const alive = up.filter((b) => b.k >= k - still && !b.gone);
    const [spot, least, drop] = planBubble(fr, box, fixed, [], alive.map((b) => b.box));
    const placed = [spot[0], spot[1], box.w, box.h];
    if (drop) for (const b of alive) if (area(placed, b.box)) b.gone = true;
    up.push({ k, box: placed });
    const without = chooseSpot(fr, box, [...lit, ...alive.filter((b) => !b.gone).map((b) => b.box)])[0];
    out.wordsLeftOut += covers([without[0], without[1], box.w, box.h], seen) ? 1 : 0;
    const away = Math.hypot(Math.max(placed[0] - px, 0, px - placed[0] - placed[2]),
      Math.max(placed[1] - py, 0, py - placed[1] - placed[3]));
    out.bubbles.push({ least, near: away <= Math.max(BUBBLE_NEAR, fr.w * BUBBLE_NEAR_PART), onFixed: covers(placed, fixed), onShelfNames: covers(placed, shelfNames),
      onBubbles: covers(placed, alive.filter((b) => !b.gone).map((b) => b.box)),
      inside: placed[0] >= 0 && placed[1] >= 0 && placed[0] + placed[2] <= fr.w && placed[1] + placed[3] <= fr.h });
  });

  // The round table: the camera at it, the seats and chairs round it (an
  // empty chair takes a press over a square HIT_PX each way), every label
  // put by planLabels clear of the table's top. The split's heading is
  // under the map, not in the frame.
  const [cx, cy] = centroid(map.boundary);
  const center = { x: cx, y: cy, level: view.zAt(cx, cy) };
  vb = tableView(center);
  const f = pointScale();
  layoutShelves(f);
  const { seats } = seating(round, round.seat_order);
  const cover = ring(center, 0, TABLE_LIFT).map((p) => toFrame(...p));
  const fixed = [...topStrips(cover)], labels = [];
  for (const sitting of seats) {
    const at = onTable(center, sitting.angle, SEAT_OUT), chair = sitting.group === "front";
    const k = chair ? Math.max(f * 1.2, MIN_CHAIR_PX * perPx() / CHAIR_R) : f * TOKEN;
    const r = chair ? HIT_PX : POINT_R * k / perPx();
    const [px, py] = toFrame(...at);
    fixed.push([px - r, py - r, 2 * r, 2 * r]);
    const title = points[sitting.id].seat.title;
    labels.push({ empty: chair, item: { w: chars(title) * 0.8 * REM + 18, h: 0.8 * REM * 1.5 + 4, px, py,
      gap: chair ? CHAIR_GAP : 16, inView: true, heading: false, atTable: true } });
  }
  const items = [...labels.filter((l) => l.empty).map((l) => l.item), ...labels.filter((l) => !l.empty).map((l) => l.item)];
  const all = words();
  const seen = seenWords(fr, all, cover);
  out.underTable = all.filter((w) => inFrame(fr, w)).length - seen.length;
  const spots = planLabels(fr, items, [...fixed, ...seen]);
  const boxes = spots.map((spot, k) => spot && [spot[0], spot[1], items[k].w, items[k].h]);
  boxes.forEach((box, k) => {
    if (!box) { out.unplaced += 1; return; }
    out.labels.push({ onFixed: covers(box, [...fixed, ...seen]),
      onOthers: covers(box, boxes.filter((other, j) => other && j !== k)),
      inside: box[0] >= 0 && box[1] >= 0 && box[0] + box[2] <= fr.w && box[1] + box[3] <= fr.h });
  });
  const without = planLabels(fr, items, fixed);
  out.onTop = boxes.filter((box) => box && covers(box, topStrips(cover))).length;
  out.wordsLeftOut += without.filter((spot, k) => spot && covers([spot[0], spot[1], items[k].w, items[k].h], seen)).length;
  return out;
}
const result = {};
for (const [name, width] of Object.entries(screens)) result[name] = scene(width);
process.stdout.write(JSON.stringify(result));
"""


def _scenes():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    consts = script[script.index("  const NS ="):script.index("  let map = null;")]
    names = ["centroid", "reliefView", "onTable", "ring", "tableView", "seating", "pointScale", "layoutShelves",
             "shelfSpot", "chooseSpot", "planLabels", "within", "seenWords", "planBubble", "topStrips"]
    source = "".join(_inner_function(script, name) for name in names)
    seats = [make_seat(seat_id=seat, kind=kind, title=f"架空の席{seat}", company="", display_name="",
                       district=district) for seat, kind, district in _ROUND_SEATS]
    lib = Library.build(seats, [], {}, False, map_data=MAP, relief_data=load_relief(VIEWBOX))
    setup = setup_of(lib)
    program = _SCENE_RUN % {"consts": consts, "source": source, "setup": json.dumps(setup, ensure_ascii=False),
                            "round": json.dumps(_ROUND, ensure_ascii=False), "screens": json.dumps(SCREENS)}
    # On stdin: the picture's grid is too long for a command line.
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_bubbles_labels_and_the_heading_keep_off_the_maps_words_seats_and_buttons_on_the_four_screens():
    scenes = _scenes()
    assert set(scenes) == set(SCREENS)
    left_out = 0
    for name, scene in scenes.items():
        # The four shelves' names are on screen while the seats light up.
        assert scene["shelfNames"] == 4 and scene["shelfNamesSeen"] == 4, name
        # Each bubble clear of the place names, the shelves' names, the
        # school's name, the seats of the round, the buttons and the bubbles
        # still up, inside the frame, and near its own seat.
        assert len(scene["bubbles"]) == len(_ROUND["seat_order"]), name
        for bubble in scene["bubbles"]:
            assert bubble == {"least": 0, "near": True, "onFixed": 0, "onShelfNames": 0, "onBubbles": 0,
                              "inside": True}, name
        # At the table every label is put, clear of those words (but the
        # ones the table's top hides), the table's top, the seats, the
        # empty chairs' squares that take a press, and one another.
        assert scene["unplaced"] == 0 and scene["onTop"] == 0, name
        assert len(scene["labels"]) == len(_ROUND["seat_order"]) + len(_ROUND["silent_seats"]), name
        for label in scene["labels"]:
            assert label == {"onFixed": 0, "onOthers": 0, "inside": True}, name
        left_out += scene["wordsLeftOut"]
    # Not by luck: put without the map's words, some would cover them.
    assert left_out > 0


def test_the_maps_words_are_among_what_a_label_or_bubble_keeps_off():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    fixed = _inner_function(script, "fixedBoxes")
    assert ".place-names text, .shelf-names text, .school text" in fixed and "seenWords(" in fixed
    # On the map, every seat the round lights, from the start; at the table, its seats and chairs.
    assert "roundSeats.map(" in fixed and ".token .shape, .chair circle" in fixed
    place = _inner_function(script, "place")
    assert "planBubble(" in place and "fixedBoxes(frameBox)" in place
    assert "fixedBoxes(frameBox)" in _inner_function(script, "relayout")
    plan = _inner_function(script, "planBubble") + _inner_function(script, "seenWords") + _inner_function(script, "within")
    for outside in ("overlay", "dataset", "document", "vb", "style", "classList", "svg"):
        assert outside not in plan


def test_a_round_brings_the_whole_map_and_its_sources_on_screen():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    start = _inner_function(script, "round")
    assert '$("map").scrollIntoView({ block: "nearest" });' in start
    assert start.index("if (!order.length) return;") < start.index("scrollIntoView")
    assert start.index("scrollIntoView") < start.index("tableRound(")


# --- 「夜の灯り」 (直し22): the colours, the type, the buttons, the chairs, the motion ---

def _css():
    return (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def test_every_colour_is_named_once_at_the_top_and_used_by_its_name():
    css = _css()
    root = re.search(r":root \{(.*?)\n\}", css, re.S)
    assert root and css.index(":root {") < css.index("body {")
    rest = css[:root.start()] + css[root.end():]
    colour = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
    assert not colour.search(rest), colour.search(rest).group(0)
    for name in ("--night", "--lamp", "--paper", "--moon"):  # Night, the lamp's honey, paper, moonlight.
        assert re.search(rf"{name}: #[0-9a-f]{{6}};", root.group(1)), name
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert not re.search(r'(fill|stroke)[:"]\s*"?#(?!000")', script)  # rough's "#000" is overridden by style.css.


def test_the_voices_and_headings_are_mincho_the_small_words_gothic_from_the_machine():
    css = _css()
    assert ('--mincho: "Hiragino Mincho ProN", "Yu Mincho", "BIZ UDPMincho", "Noto Serif CJK JP", serif;' in css)
    assert ('--gothic: "Hiragino Sans", "BIZ UDPGothic", "Yu Gothic UI", "Noto Sans CJK JP", sans-serif;' in css)
    assert '--display: "Ebino Title", var(--mincho);' in css
    assert "@import" not in css and "http" not in css  # Nothing from outside.
    body = re.search(r"\nbody \{([^}]*)\}", css).group(1)
    assert "font-size: 17px" in body and "var(--gothic)" in body
    # A voice: 17-18px Mincho, line height 1.8, about twenty characters to a line.
    for rule in (r"\.map-bubble \.voice \{([^}]*)\}", r"\.quote \.words \{([^}]*)\}"):
        found = re.search(rule, css).group(1)
        assert "var(--mincho)" in found and "line-height: 1.8" in found and re.search(r"font-size: 1[78]px", found)
        assert re.search(r"max-width: 2[01]em", found)


def test_the_maps_buttons_and_the_tables_heading_are_under_the_map_not_over_it():
    html = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    frame = html[html.index('<div id="map-frame"'):html.index('<div id="map-overlay"')]
    assert "<button" not in frame
    bar = html[html.index('class="map-bar'):html.index('<div class="map-foot">')]
    for button in ("map-back", "map-zoom-in", "map-zoom-out", "map-zoom-all"):
        assert f'id="{button}"' in bar
    assert 'id="map-heading"' in bar
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    table = _inner_function(script, "openTable")
    assert '$("map-heading").textContent = app.shownQuotes(split.heading)' in table and "split-tag" not in table
    assert "overlay.clientWidth >= TAG_ON_MAP" in table  # Narrower: in the split block only, as before.
    # While the table is open, Tab goes to its chairs, not to the map's points under it.
    assert 'node.setAttribute("tabindex", "-1")' in table
    assert 'node.setAttribute("tabindex", "0")' in _inner_function(script, "clearTable")
    # The labels at the table keep off its top.
    assert "topStrips(cover)" in _inner_function(script, "fixedBoxes")


def test_an_empty_chair_takes_a_press_over_44px_and_shows_the_keyboard_there():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert re.search(r"const HIT_PX = (\d+);", script).group(1) == "22"
    assert 'svgEl("rect", { class: "hit" })' in _inner_function(script, "chair")
    rescale = _inner_function(script, "rescale")
    assert "Math.max(CHAIR_R, HIT_PX * perPx / k)" in rescale and "width: 2 * half" in rescale
    css = _css()
    assert ".chair .hit { fill: transparent;" in css
    assert re.search(r"\.chair:focus-visible \.hit \{[^}]*stroke: var\(--lamp\)", css)


def test_the_flat_map_has_no_mountain_marks():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert "drawMountains" not in script and "mountains" not in script and "MOUNTAINS" not in script
    assert ".mountains" not in _css()


def test_with_motion_reduced_no_ring_goes_out_and_the_cards_do_not_move():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    light = _inner_function(script, "light")
    assert light.index('classList.add("lit")') < light.index("if (reduced() || !node.animate) return;")
    assert light.index("return;") < light.index(".animate(")
    css = _css()
    reduced = css[css.index("@media (prefers-reduced-motion: reduce)"):]
    assert ".map-bubble, .map-bubble .thread { animation: none !important; }" in reduced
