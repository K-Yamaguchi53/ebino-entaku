"""直し33-1: whose words are in, and the examples, shut until asked for:
before the first question too, only the small button 「入っている言葉を見る」
over the map. Pressed it opens at once; pressed again, Esc or a press
outside shuts it. Before the first question the eye goes to the button
once (no blinking; with motion reduced it does not move)."""

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_shut_from_the_start_its_button_in_the_teachers_words():
    assert '<details id="inside-fold">' in HTML and '<details id="inside-fold" open>' not in HTML
    assert texts.screen_texts()["inside_open"] == "入っている言葉を見る"
    assert '$("inside-open").textContent = state.texts.inside_open;' in _top("renderInside")


def test_pressed_again_esc_or_outside_shuts_it_and_the_keyboard_goes_back():
    setup = _top("setupInside")
    assert 'event.key !== "Escape" || !fold.open' in setup
    assert "fold.open = false;\n    button.focus({ preventScroll: true });" in setup
    assert 'if (fold.open && !$("inside").contains(event.target)) fold.open = false;' in setup
    assert "setupInside();" in _top("setupDrawer")
    # A question sent shuts it, and the button is no longer lit.
    ask = _top("ask")
    assert '$("inside-fold").open = false;' in ask and '$("inside").classList.remove("beckon");' in ask


def test_its_button_is_over_no_part_of_the_map():
    # 直し41の続き: in the map's column (200px, map-bar), with the drawer's
    # buttons, in index.html's order; upright, in the same row as theirs.
    bar = HTML[HTML.index('<div class="map-drawers">'):HTML.index('<div class="map-zoom">')]
    assert bar.index('<section id="inside" class="inside" hidden>') < bar.index('<div id="drawer-buttons"')
    assert "#inside { position: static; width: auto; margin: 0; padding: 0;" in CSS
    assert "#inside { position: static; width: auto; margin: 0; }" in CSS
    assert ".map-bar { flex: 0 0 200px;" in CSS
    # With no map it goes back to the page, before the AI's seat.
    assert '$("ai-seat").before($("inside"))' in _top("placeInside")


def test_the_map_does_not_move_for_it():
    assert "details[open]) .map-room" not in CSS
    assert '$("inside-fold").addEventListener("toggle", mapMoved)' not in APP


def test_the_eye_goes_to_it_once_and_not_with_motion_reduced():
    setup = _top("setupInside")
    assert '$("inside").classList.add("beckon");' in setup
    # Opened once, the light goes for good (not again each time it shuts).
    assert 'fold.addEventListener("toggle", () => { if (fold.open) $("inside").classList.remove("beckon"); });' in setup
    moving = CSS[CSS.index("@media (prefers-reduced-motion: no-preference) {\n  #inside.beckon"):]
    moving = moving[:moving.index("\n}\n")]
    # Once: one ring going out, not a blink.
    assert "animation: beckon 1.6s ease-out .6s 1 both;" in moving
    assert "infinite" not in moving
    # Lit and still otherwise (no animation outside the no-preference block).
    still = CSS[CSS.index("#inside.beckon:not(:has(details[open])) summary { border-color"):]
    assert "animation" not in still[:still.index("}")]
