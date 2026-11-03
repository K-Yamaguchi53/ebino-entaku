"""A seat's name by its mark on the map (直し25-2): shown while the mouse or
the keyboard is on the seat, in the seat list's own words, one card at a time,
off the lamp cards and headings; the company's name only on the in-school
screen (EBINO_SHOW_COMPANY=1)."""

import json
import re
import shutil
import subprocess

import pytest
from conftest import COMPANY, DISPLAY_NAME, make_seat
from fake_client import FakeClient

from ebino import app as app_module
from ebino import seat_map
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.seat_label import show_private_labels, short_company
from ebino.session import Library
from test_session import UTTERANCES

MAP = seat_map.load_map()
SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")


def _inner_function(script, name):
    start = script.index(f"function {name}(")
    return script[start:script.index("\n  }\n", start) + 5]


def _setup(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("EBINO_SHOW_COMPANY", raising=False)
    else:
        monkeypatch.setenv("EBINO_SHOW_COMPANY", value)
    table = [make_seat(seat_id="S01", district="えびの市大字原田"),
             make_seat(seat_id="S02", title="農家", district="えびの市大字末永")]
    lib = Library.build(table, UTTERANCES, {}, show_private_labels(), map_data=MAP)
    return App(lib, Gate(FakeClient([]), NameList.build(lib.seats, {}))).setup()


@pytest.mark.parametrize("value", [None, "", "0", "yes", " 1x"])
def test_without_the_in_school_screen_no_company_or_persons_name_reaches_the_screen(monkeypatch, value):
    setup = _setup(monkeypatch, value)
    sent = json.dumps(setup, ensure_ascii=False)
    for word in (COMPANY, short_company(COMPANY), DISPLAY_NAME):
        assert word not in sent
    # The map's card shows what the seat list shows: the title alone.
    assert {seat["seat_id"]: (seat["title"], seat["detail"]) for seat in setup["seats"]}["S02"] == ("農家", "")


def test_on_the_in_school_screen_the_card_has_the_company_as_the_seat_list_does(monkeypatch):
    setup = _setup(monkeypatch, "1")
    seat = next(seat for seat in setup["seats"] if seat["seat_id"] == "S01")
    assert short_company(COMPANY) in seat["detail"]


def test_the_name_card_reads_the_seat_lists_words_only_and_is_not_the_browsers_title():
    tip = _inner_function(SCRIPT, "showTip")
    assert 'div("title", seat.title)' in tip and 'div("detail", seat.detail)' in tip
    # Nothing else of the seat, no new way of naming it; never the browser's own bubble.
    assert not re.search(r"seat\.(company|display_name|name)\b", SCRIPT)
    assert '"title"' not in _inner_function(SCRIPT, "drawPoint") and "<title" not in SCRIPT
    # One card at a time, and it moves no heading.
    assert tip.index("hideTip();") < tip.index("overlay.append(tip)")
    assert "split-tag" not in tip and "place(" not in tip


def test_the_mouse_names_the_seat_nearest_it_and_a_press_goes_to_that_seat_a_touch_as_before():
    hover = _inner_function(SCRIPT, "hoverAt")
    assert 'event.pointerType !== "mouse"' in hover and "nearestPoint(" in hover
    assert "restoreTip()" in hover  # Off every mark: the card goes.
    point = _inner_function(SCRIPT, "drawPoint")
    assert "mouseenter" not in point and "mouseleave" not in point
    assert 'addEventListener("focus", () => showTip(seat.seat_id))' in point
    assert 'event.pointerType === "mouse" && hovered ? hovered : seat.seat_id' in point
    assert 'svg.addEventListener("pointermove", hoverAt)' in SCRIPT
    css = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    assert ".pt.hover .shape, .pt:focus-visible .shape" in css and ".pt:hover" not in css
    tip_rule = re.search(r"\n\.map-tip \{[^}]*\}", css).group(0)
    assert "font-family: var(--gothic)" in tip_rule and "#" not in tip_rule


_TIP_RUN = """
%(source)s
const frame = { w: 600, h: 400 };
const box = { w: 120, h: 40, px: 300, py: 200, gap: 14 };
const mark = [292, 192, 16, 16];
const card = [240, 120, 200, 70];  // A lamp card over the mark.
const out = {
  free: tipSpot(frame, box, [mark], []),
  card: tipSpot(frame, box, [mark, card], []),
  corner: tipSpot(frame, { ...box, px: 4, py: 4 }, [[0, 0, 12, 12]], []),
  boxed: tipSpot(frame, box, [mark, [0, 0, 600, 190], [0, 210, 600, 190]], []),
};
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_name_card_goes_by_its_mark_off_a_lamp_card_and_inside_the_frame():
    program = _TIP_RUN % {"source": _inner_function(SCRIPT, "tipSpot")}
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    spots = json.loads(done.stdout.decode("utf-8"))
    hit = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    # Above its mark when nothing is there.
    assert spots["free"] == [240, 146]
    # A card above: another side by the mark, off the card and the mark.
    left, top = spots["card"]
    assert not hit([left, top, 120, 40], [240, 120, 200, 70]) and not hit([left, top, 120, 40], [292, 192, 16, 16])
    assert abs(left + 60 - 300) <= 60 + 14 + 1 and abs(top + 20 - 200) <= 20 + 14 + 1
    # In a corner: inside the frame.
    left, top = spots["corner"]
    assert 4 <= left <= 600 - 120 - 4 and 4 <= top <= 400 - 40 - 4
    # No side free: still one of the places by its mark, inside the frame.
    left, top = spots["boxed"]
    assert 4 <= left and 4 <= top and left + 120 <= 596 and top + 40 <= 396
