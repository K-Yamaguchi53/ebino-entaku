"""While the round table is open, the map's points behind it take no mouse,
press or touch (直し27-4, the teacher's words: 「円卓が出てきた後は、後ろの〇に
カーソルを合わせても反応しないようにしてほしい」): no name card, no press.
The table's own seats, cards, choices and empty chairs, and the map's
buttons, still do. 「地図にもどす」 gives the points back."""

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_the_points_behind_the_table_take_nothing_while_it_is_open():
    assert ".dim .points { pointer-events: none; }" in CSS
    assert 'if (svg.classList.contains("dim")) return;' in _inner("hoverAt")
    assert 'if (svg.classList.contains("dim")) return;' in _inner("drawPoint")
    opened = MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]
    assert opened.index('svg.classList.add("dim");') < opened.index("hovered = null;") < opened.index("hideTip();")
    # The keyboard stays off them as before.
    assert 'node.setAttribute("tabindex", "-1")' in opened


def test_the_map_gives_them_back():
    clear = _inner("clearTable")
    assert 'svg.classList.remove("dim")' in clear and 'node.setAttribute("tabindex", "0")' in clear
    # What is on the table takes presses.
    assert ".table-bubble { pointer-events: auto;" in CSS and ".seat-press { position: absolute;" in CSS
    assert ".chair { cursor: pointer;" in CSS
