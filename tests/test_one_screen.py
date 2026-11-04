"""直し32-1: one screen. From the first question to 「ふりかえりへ」 the
page never scrolls: the title and the band at the top, the map and the
round table in all the height left, the one box at the foot, and a drawer
on the right only when opened (the paragraph, the rounds so far, the seat
list, the seniors' questions). The browser check of the five sizes and
moments is tools/check_one_screen.js (run with playwright against the
preview of invented seats); these are its guards in the code."""

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
ROOT = STATIC.parent.parent
ONE = "body:has(#table:not([hidden])):has(#map:not([hidden]))"


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _part(start, end):
    return HTML[HTML.index(start):HTML.index(end)]


def test_what_was_under_the_map_is_in_the_drawer_or_over_the_map():
    stage = _part('<div id="stage"', '<aside id="drawer"')
    drawer = _part('<aside id="drawer"', '<div class="input-area">')
    foot = _part('<div class="input-area">', '<!-- The reflection sheet')
    assert 'id="map"' in stage and 'id="inside"' in stage and 'id="work-questions"' in stage
    for part in ('id="rounds"', 'class="seats drawer-part"', 'id="purposes"', 'id="drawer-paragraph"'):
        assert part in drawer, part
    assert 'id="ask-form"' in foot and 'id="to-reflect"' in foot and 'id="reflect-needs-answer"' in foot
    assert 'id="heavy-talk"' in _part('<header class="masthead">', "</header>")


def test_the_page_itself_is_the_windows_height_and_only_the_drawer_scrolls():
    assert f"{ONE} {{ height: var(--vh); min-height: 0; display: grid;" in CSS
    assert f"{ONE} .drawer-body {{ flex: 1 1 auto; min-height: 0; overflow: auto;" in CSS
    assert f"{ONE} .map-frame {{ width: min(100cqw, 100cqh * var(--ratio, 1.3)); }}" in CSS
    # No map: none of it, the page as long as before.
    assert ".drawer-head, .drawer-buttons:empty { display: none; }" in CSS


def test_the_drawer_opens_one_part_and_closes_back_to_where_the_keyboard_was():
    assert set(texts.screen_texts()["drawer_parts"]) == {"paragraph", "rounds", "seats", "purposes"}
    opened = _top("openDrawer")
    assert "if (!oneScreen()) return;" in opened and "box.dataset.part = part;" in opened
    closed = _top("closeDrawer")
    assert "back.focus({ preventScroll: true })" in closed
    setup = _top("setupDrawer")
    assert 'event.key !== "Escape"' in setup and "closeDrawer();" in setup
    assert 'openDrawer("rounds", from, { focus: false });' in _top("readBelow")
    # Opened by its button, the keyboard goes in (Esc closes it from there);
    # closed with nowhere to go back to, the keyboard goes to the box, not to nothing.
    assert '$("drawer-title").focus({ preventScroll: true })' in opened
    assert '$("question").focus({ preventScroll: true })' in closed
    assert 'id="drawer-title" class="drawer-title" tabindex="-1"' in HTML
    assert "closeDrawer();" in _top("openReflection")


def test_the_safety_line_shows_only_while_the_table_is_out():
    # Never on the first screen; the reflection has its own (直し32-1).
    assert ".masthead .heavy-talk { display: none; }" in CSS
    assert "body:has(#table:not([hidden])) .masthead .heavy-talk { display: block; }" in CSS
    assert 'class="heavy-talk reflect-heavy-talk"' in HTML


def test_the_check_of_five_sizes_and_five_moments_is_kept():
    check = (ROOT / "tools" / "check_one_screen.js").read_text(encoding="utf-8")
    for size in ("[768, 1024]", "[1180, 820]", "[1366, 650]", "[1536, 760]", "[1920, 1080]"):
        assert size in check
    for moment in ("before_question", "table_out", "bubble_pressed", "writing_to_seat", "answering_ai"):
        assert moment in check
    assert "s.scrollHeight" in check and "window.innerHeight" in check
