"""直し41の続き 段4: the frame has no empty black round the map's picture:
the same picture mirrored, blurred and darkened, made once by
tools/make_relief_blur.py, served from mapdata/ and laid under the picture.
The whole map shows the basin larger, every seat's home and its name kept
inside the frame first."""

import importlib.util
import re
import threading
from pathlib import Path

import pytest
from PIL import Image

from ebino import app as app_module
from ebino import relief
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from fake_client import FakeClient
from test_relief import VIEWBOX, library, load_relief, request

REPO = Path(__file__).resolve().parents[1]
SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
TOOL = REPO / "tools" / "make_relief_blur.py"


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


@pytest.fixture
def server():
    the_app = App(library(load_relief(VIEWBOX)), Gate(FakeClient([]), NameList.build([], {})))
    srv = make_server(the_app, 0, timeout=1)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def test_the_blurred_ground_is_served_from_mapdata(server):
    status, body = request(server, "GET", "/relief_blur.webp")
    assert status == 200 and body == (relief.RELIEF_DIR / "relief_blur.webp").read_bytes()
    assert app_module.MAP_FILES["/relief_blur.webp"][1] == "image/webp"
    assert request(server, "GET", "/mapdata/relief_blur.webp")[0] == 404


def test_the_ground_is_three_times_the_picture_and_small(tmp_path):
    spec = importlib.util.spec_from_file_location("make_relief_blur", TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    made = tool.make(relief.RELIEF_DIR / relief.IMAGE, tmp_path / "ground.webp")
    picture, ground = Image.open(relief.RELIEF_DIR / relief.IMAGE), Image.open(made)
    small = (picture.width // tool.SHRINK, picture.height // tool.SHRINK)
    assert ground.size == (3 * small[0], 3 * small[1])
    kept = Image.open(relief.RELIEF_DIR / "relief_blur.webp")
    assert kept.size == ground.size and (relief.RELIEF_DIR / "relief_blur.webp").stat().st_size < 128 * 1024
    # Made here, from mapdata only: nothing is fetched.
    source = TOOL.read_text(encoding="utf-8")
    assert "http" not in source and "urllib" not in source and "requests" not in source


def test_the_ground_lies_under_the_picture_three_times_as_large_and_takes_no_press():
    draw = _inner("draw")
    assert draw.index('layer("relief-blur")') < draw.index('layer("relief-image")')
    assert "x: ox - base.W, y: oy - base.H, width: 3 * base.W, height: 3 * base.H" in draw
    # The picture's own margin melts into it: still masks, across and down.
    assert 'mask: "url(#relief-fade-x)"' in draw and '{ mask: "url(#relief-fade-y)" }' in draw
    assert "const RELIEF_FADE_X = [[0, 0], [0.016, 0], [0.04, 1]," in SCRIPT
    assert 'const BLUR_IMAGE = "/relief_blur.webp";' in SCRIPT
    assert ".relief-blur { pointer-events: none; }" in CSS
    assert ".dim .relief-image, .dim .relief-blur { opacity: .42; }" in CSS
    # No blur drawn on the screen: the picture comes blurred.
    assert not re.search(r"\.relief-(blur|image)[^{]*\{[^}]*filter", CSS)
    assert "feGaussianBlur" not in SCRIPT and "ctx.filter" not in SCRIPT


def test_the_whole_map_keeps_every_home_and_its_name_before_the_rims_share():
    whole = _inner("wholeView")
    assert "(rim[3] - rim[1]) / RIM_SHARE" in whole
    assert ".home-names text:not(.at-school)" in whole and 'classList.contains("school-home")' in whole
    assert "Math.min(view.H, Math.max(" in whole  # Never past the drawing.
    assert re.search(r"const RIM_SHARE = 0\.85;", SCRIPT) and re.search(r"const WHOLE_EDGE = 0\.015;", SCRIPT)
    # 「全体」 and 地図にもどす go to it; the meeting keeps the whole drawing.
    assert '$("map-zoom-all").addEventListener("click", () => moveTo(view.whole, 500));' in SCRIPT
    assert "moveTo(view.whole, BACK_FOR);" in SCRIPT
    assert "if (vb.w < view.W - 0.5) await moveTo({ x: 0, y: 0, w: view.W, h: view.H }" in SCRIPT
    assert "draw(lastSeats, view.relief, !reopen);" in _inner("recompose")
