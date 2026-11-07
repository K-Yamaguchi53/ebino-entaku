"""The map's seasons (the teacher, 11/6): beside the night, the same model at
dusk in spring and in autumn, switched on the screen by 夜・春・秋. Only the
picture and the plain ground's colour change (直し53 段1: no blurred ground);
a season is offered only when its picture is there and is the night's size
(the same camera)."""

import json
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from ebino import app as app_module
from ebino import relief, texts
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from fake_client import FakeClient
from test_relief import VIEWBOX, copy_relief, library, load_relief, request

REPO = Path(__file__).resolve().parents[1]
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
RENDER = (REPO / "tools" / "render_relief.py").read_text(encoding="utf-8")


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


def _with_season(folder, season, image_from=relief.IMAGE):
    shutil.copy(folder / image_from, folder / relief.season_image(season))


def test_the_repo_has_spring_and_autumn_after_the_night():
    data = load_relief(VIEWBOX)
    ids = [look["id"] for look in data["looks"]]
    assert ids == ["night", "spring", "autumn"]
    assert data["looks"][0] == {"id": "night", "image": "/relief.webp"}
    for season in relief.SEASONS:
        # Autumn's crowns of trees (a grain of colours, the teacher's 11/6)
        # cost more than the night's smooth wash; still small for a page
        # served on this computer only (直し53 段8: 4800 px across).
        assert (relief.RELIEF_DIR / relief.season_image(season)).stat().st_size < 3_000_000
    # 直し53 段1: no blurred grounds left in mapdata/.
    assert not list(relief.RELIEF_DIR.glob("relief_blur*"))


def test_a_season_missing_a_file_or_of_another_size_is_left_out(tmp_path):
    folder = copy_relief(tmp_path)
    assert [look["id"] for look in load_relief(VIEWBOX, folder)["looks"]] == ["night"]
    _with_season(folder, "autumn")
    assert [look["id"] for look in load_relief(VIEWBOX, folder)["looks"]] == ["night", "autumn"]
    (folder / relief.season_image("autumn")).unlink()  # No picture: not offered.
    assert [look["id"] for look in load_relief(VIEWBOX, folder)["looks"]] == ["night"]
    # Another size is another camera: never laid misplaced.
    from PIL import Image
    Image.new("RGB", (60, 40)).save(folder / "other.webp", "WEBP")
    _with_season(folder, "spring", image_from="other.webp")
    assert [look["id"] for look in load_relief(VIEWBOX, folder)["looks"]] == ["night"]
    (folder / relief.season_image("spring")).write_bytes(b"not a picture")
    assert [look["id"] for look in load_relief(VIEWBOX, folder)["looks"]] == ["night"]


@pytest.fixture
def server():
    the_app = App(library(load_relief(VIEWBOX)), Gate(FakeClient([]), NameList.build([], {})))
    srv = make_server(the_app, 0, timeout=1)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()
    srv.server_close()


def test_the_seasons_files_are_served_by_name_from_mapdata(server):
    for season in relief.SEASONS:
        name = relief.season_image(season)
        status, body = request(server, "GET", f"/{name}")
        assert status == 200 and body == (relief.RELIEF_DIR / name).read_bytes()
        assert app_module.MAP_FILES[f"/{name}"][1] == "image/webp"
        assert request(server, "GET", f"/mapdata/{name}")[0] == 404
    assert request(server, "GET", "/relief_winter.webp")[0] == 404
    # 直し53 段1: the blurred grounds are no longer served.
    for name in ("relief_blur.webp", "relief_blur_spring.webp", "relief_blur_autumn.webp"):
        assert request(server, "GET", f"/{name}")[0] == 404 and f"/{name}" not in app_module.MAP_FILES


def test_the_switchs_words_are_the_teachers_table():
    words = texts.map_buttons()
    assert [words[key]["text"] for key in ("season_night", "season_spring", "season_autumn")] == ["夜", "春", "秋"]
    assert words["seasons"]["label"]  # The band's name, read aloud.


def test_it_opens_on_the_months_season_and_switches_only_the_two_pictures():
    assert "const SEASON_MONTHS = { spring: [3, 4, 5], autumn: [9, 10, 11] };" in SCRIPT
    start = _inner("startLook")
    assert "new Date().getMonth() + 1" in start and "|| all[0]" in start  # Else the night.
    show = _inner("showLook")
    # The picture only (the ground's colour follows frame.dataset.look in
    # style.css); 直し48 段6: at once, or melted in (a picture over it, then its own href).
    assert "for (const [node, href] of [[lookNodes.picture, look.image]])" in show
    assert show.count("setAttribute(\"href\"") == 3
    # Nothing else is redrawn: no draw, no move, no relayout.
    assert not re.search(r"\b(draw|build|moveTo|relayout)\(", show)
    assert 'aria-pressed", String(button.dataset.look === look.id)' in show
    draw = _inner("draw")
    assert 'layer("relief-ground")' in draw and "href: look.image" in draw and "look.blur" not in draw
    assert '$("map-season").hidden = !view.relief || looksOf().length < 2;' in draw
    # A season that will not load falls back to the night, then the flat map.
    init = _inner("init")
    assert "picture.src = one.image;" in init and "tryLook(look);" in init
    assert "picture.onerror = () => (one === night ? build(seats, false) : tryLook(night));" in init


def test_the_band_sits_with_the_zoom_and_shows_the_season_lit():
    assert HTML.index('id="map-season"') < HTML.index('id="map-zoom-in"')
    assert 'id="map-season" class="map-zoom map-season" role="group" hidden' in HTML
    assert ".map-season[hidden] { display: none; }" in CSS
    assert '.map-bar .map-season button[aria-pressed="true"] { color: var(--lamp-bright);' in CSS
    # Over a season's lighter land the place names keep a whole halo.
    assert "frame.dataset.look = look.id;" in _inner("showLook")
    assert ('.map-frame[data-look="spring"] .place-names text, .map-frame[data-look="autumn"] .place-names text '
            '{ stroke: var(--night); }') in CSS
    # Not on the flat map, whose frame has no look.
    assert ':not([data-look' not in CSS


def test_the_pictures_keep_the_camera_and_the_projection():
    # 直し53 段8: drawn twice as wide (4800), the camera framed as before by
    # every STEP-th height at PROJECTION_PX (2400): the projection unchanged;
    # one drawn by another camera is removed.
    assert "PROJECTION_PX = 2400" in RENDER and "STEP = 2" in RENDER
    assert "projection = camera(scene, frame_verts, PROJECTION_PX)" in RENDER
    assert 'if OUT_PROJECTION.is_file() and OUT_PROJECTION.read_text(encoding="utf-8") != written:' in RENDER
    assert "out_image.unlink()" in RENDER
    # The night a little brighter (the moon), the seasons' looks clearer.
    assert "NIGHT_MOON = 2.0" in RENDER and '("moon", NIGHT_MOON, (0.72, 0.80, 1.0), (62, 0, -118))' in RENDER
    data = load_relief(VIEWBOX)
    for look in data["looks"]:
        name = look["image"].lstrip("/")
        size = relief.webp_size((relief.RELIEF_DIR / name).read_bytes())
        assert size == (2 * data["res"][0], 2 * data["res"][1])


def test_a_picture_of_another_size_than_the_projections_times_is_refused(tmp_path):
    folder = copy_relief(tmp_path)
    from PIL import Image
    Image.new("RGB", (4801, 3646)).save(folder / relief.IMAGE, "WEBP")
    assert load_relief(VIEWBOX, folder) is None
    Image.new("RGB", (2400, 1823)).save(folder / relief.IMAGE, "WEBP")  # As before 直し53: still allowed.
    assert load_relief(VIEWBOX, folder) is not None


_MONTHS = """
%(months)s
let map = { relief: { image: "/relief.webp", looks: %(looks)s } };
%(looksOf)s
%(startLook)s
const RealDate = Date;
const out = [];
for (let month = 0; month < 12; month++) {
  globalThis.Date = class extends RealDate { constructor() { super(2026, month, 15); } };
  out.push(startLook().id);
  globalThis.Date = RealDate;
}
process.stdout.write(JSON.stringify(out));
"""


def _opening(looks):
    months = re.search(r"^  const SEASON_MONTHS = .*$", SCRIPT, re.M).group(0)
    program = _MONTHS % {"months": months, "looks": json.dumps(looks), "looksOf": _inner("looksOf"),
                         "startLook": _inner("startLook")}
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout)


@node
def test_each_month_opens_on_its_season_and_the_night_when_it_has_none():
    night = {"id": "night", "image": "/relief.webp"}
    spring = {"id": "spring", "image": "/relief_spring.webp"}
    autumn = {"id": "autumn", "image": "/relief_autumn.webp"}
    # January to December, as the teacher's switch is meant: spring in March
    # to May, autumn in September to November, the night in the rest.
    assert _opening([night, spring, autumn]) == ["night", "night", "spring", "spring", "spring", "night",
                                                 "night", "night", "autumn", "autumn", "autumn", "night"]
    # A season whose picture is not there opens on the night.
    assert _opening([night, autumn]) == ["night"] * 8 + ["autumn"] * 3 + ["night"]
    assert _opening([night]) == ["night"] * 12
