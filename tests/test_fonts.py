"""直し41 段1: the Mincho and the Gothic are bundled, so every machine shows
the same words; and the tab has its small picture (no 404 for it)."""

import http.client
import random
import re
import threading
import xml.etree.ElementTree as ET

import pytest
from fake_client import FakeClient

from ebino import app as app_module
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from test_session import ANSWERED, SEATS, library

STATIC = app_module.STATIC_DIR
FONTS = {
    "/fonts/BIZUDPMincho-Regular.woff2": ("Ebino Mincho", 400),
    "/fonts/BIZUDPMincho-Bold.woff2": ("Ebino Mincho", 700),
    "/fonts/BIZUDPGothic-Regular.woff2": ("Ebino Gothic", 400),
    "/fonts/BIZUDPGothic-Bold.woff2": ("Ebino Gothic", 700),
}


@pytest.fixture
def server():
    the_app = App(library(), Gate(FakeClient(list(ANSWERED)), NameList.build(SEATS, {})), rng=random.Random(1))
    srv = make_server(the_app, 0, timeout=1)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def get(srv, path):
    port = srv.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
    response = connection.getresponse()
    body = response.read()
    headers = {k.lower(): v for k, v in response.getheaders()}
    connection.close()
    return response.status, headers, body


def test_the_four_fonts_are_in_static_fonts_with_their_license_beside_them():
    for path in FONTS:
        name, kind = app_module.STATIC_FILES[path]
        assert kind == "font/woff2" and name == path.lstrip("/")
        data = (STATIC / name).read_bytes()
        assert data[:4] == b"wOF2" and len(data) > 1_000_000  # Whole: every character, not cut out.
    license_text = (STATIC / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in license_text
    assert "BIZ UDMincho" in license_text and "BIZ UDGothic" in license_text
    # Beside them, not served (it names a place outside, as title.OFL.txt does).
    assert all(name != "fonts/OFL.txt" for name, _ in app_module.STATIC_FILES.values())
    # Nothing of the fonts sits in static/ itself (its year check reads that folder).
    assert not list(STATIC.glob("*.woff2")) and not list(STATIC.glob("OFL*"))


def test_the_fonts_are_served_and_kept_by_the_browser_the_rest_is_not(server):
    for path in FONTS:
        status, headers, body = get(server, path)
        assert status == 200 and headers["content-type"] == "font/woff2"
        assert re.fullmatch(r"max-age=\d+", headers["cache-control"]) and body[:4] == b"wOF2"
        assert headers["content-security-policy"] == "default-src 'self'"
    for path in ("/", "/style.css", "/app.js", "/favicon.svg", "/title.woff"):
        assert get(server, path)[1]["cache-control"] == "no-store"
    assert get(server, "/fonts/OFL.txt")[0] == 404


def test_the_mincho_and_the_gothic_are_declared_at_400_and_700_and_come_first():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    faces = re.findall(r"@font-face \{(.*?)\}", css, re.S)
    declared = set()
    for face in faces:
        family = re.search(r'font-family: "([^"]+)"', face).group(1)
        if family == "Ebino Title":
            continue
        src = re.search(r'url\("([^"]+)"\) format\("woff2"\)', face).group(1)
        weight = int(re.search(r"font-weight: (\d+)", face).group(1))
        assert "font-display: swap" in face
        assert FONTS[src] == (family, weight)
        declared.add(src)
    assert declared == set(FONTS)
    assert re.search(r'--mincho: "Ebino Mincho", ', css) and re.search(r'--gothic: "Ebino Gothic", ', css)


def test_the_page_asks_for_the_four_fonts_early_and_waits_for_them_before_measuring():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for path in FONTS:
        assert f'<link rel="preload" href="{path}" as="font" type="font/woff2" crossorigin>' in html
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    for family, weight in FONTS.values():
        assert f"'{weight} 16px \"{family}\"'" in script
    assert "document.fonts.load" in script and "Promise.all" in script
    assert 'document.fonts.addEventListener("loadingdone", fontsDone)' in script
    # The setup waits for them before the screen (and the map) is made.
    setup = script[script.index("async function setup()"):]
    assert setup.index("fontsReady()") < setup.index("renderSeats();") < setup.index("map.init(")


def test_the_tab_has_its_small_picture_a_round_table_on_the_night(server):
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg">' in html
    assert app_module.STATIC_FILES["/favicon.svg"] == ("favicon.svg", "image/svg+xml")
    status, headers, body = get(server, "/favicon.svg")
    assert status == 200 and headers["content-type"] == "image/svg+xml"
    svg = ET.fromstring(body)
    ns = "{http://www.w3.org/2000/svg}"
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    night = re.search(r"--night: (#[0-9a-f]{6});", css).group(1)
    paper = re.search(r"--paper: (#[0-9a-f]{6});", css).group(1)
    ground, ring = svg.find(f"{ns}circle"), svg.find(f"{ns}g")
    assert ground.get("fill") == night and ring.get("fill") == paper  # The night and the paper, no new colour.
    dots = ring.findall(f"{ns}circle")
    assert len(dots) >= 6
    # A ring: every dot the same way from the middle, and the middle empty.
    far = {round(((float(d.get("cx")) - 16) ** 2 + (float(d.get("cy")) - 16) ** 2) ** 0.5, 1) for d in dots}
    assert len(far) == 1 and far.pop() > 2 * float(dots[0].get("r"))
    # The only address in it is its namespace.
    assert re.findall(r"https?://[^\"' ]+", body.decode("utf-8")) == ["http://www.w3.org/2000/svg"]
