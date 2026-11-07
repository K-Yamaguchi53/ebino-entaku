"""直し41の続き 段4: the frame has no empty black round the map's picture.
直し53 段1: round it, a plain ground of the season's edge colour (no longer
the picture mirrored and blurred, whose upside-down hills showed at the
frame's edges). The whole map shows the basin larger, every seat's home and
its name kept inside the frame first."""

import re
import threading
from pathlib import Path

import pytest

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


def test_no_blurred_ground_is_served_or_made_any_more(server):
    # 直し53 段1 (the teacher, 11/7: 上と左右のぼかしを消して).
    assert request(server, "GET", "/relief_blur.webp")[0] == 404
    assert "/relief_blur.webp" not in app_module.MAP_FILES
    assert not list(relief.RELIEF_DIR.glob("relief_blur*")) and not TOOL.exists()
    assert "BLUR_IMAGE" not in SCRIPT and "relief_blur" not in SCRIPT and "relief-blur" not in CSS


def test_a_plain_ground_three_times_the_picture_lies_under_it_and_takes_no_press():
    draw = _inner("draw")
    assert draw.index('layer("relief-ground")') < draw.index('layer("relief-image")')
    assert 'layer("relief-ground").append(svgEl("rect", { x: ox - base.W, y: oy - base.H, width: 3 * base.W, height: 3 * base.H }));' in draw
    # The picture's own margin melts into it: still masks, across and down,
    # wider than before so there is no seam.
    assert 'mask: "url(#relief-fade-x)"' in draw and '{ mask: "url(#relief-fade-y)" }' in draw
    assert "const RELIEF_FADE_X = [[0, 0], [0.016, 0], [0.07, 1], [0.93, 1], [0.984, 0], [1, 0]];" in SCRIPT
    assert "const RELIEF_FADE_Y = [[0, 0], [0.05, 0], [0.12, 1], [0.88, 1], [0.935, 0], [1, 0]];" in SCRIPT
    assert ".relief-ground { pointer-events: none; }" in CSS
    assert ".dim .relief-image, .dim .relief-ground { opacity: .42; }" in CSS
    # Each season's own edge colour, from the tokens; it melts with the picture.
    assert ".relief-ground rect { fill: var(--ground-night); }" in CSS
    assert '.map-frame[data-look="spring"] .relief-ground rect { fill: var(--ground-spring); }' in CSS
    assert '.map-frame[data-look="autumn"] .relief-ground rect { fill: var(--ground-autumn); }' in CSS
    for token in ("--ground-night", "--ground-spring", "--ground-autumn"):
        assert re.search(token + r": #[0-9a-f]{6};", CSS)
    assert "@media (prefers-reduced-motion: no-preference) { .relief-ground rect { transition: fill 1.6s ease-in-out; } }" in CSS
    # No blur drawn on the screen.
    assert not re.search(r"\.relief-(ground|image)[^{]*\{[^}]*filter", CSS)
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
