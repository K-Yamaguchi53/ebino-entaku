"""The round table reads as a round table of wood one sits round (直し29-2):
its top thick, its side in front, a thin light on its near rim, the top in
dark wood under the lamp, one leg and its foot under it; each seat on a
chair whose back is to the outside, an empty chair the same chair in a
dotted line. The table's size, the seats' spots and the cards' layout are
as before."""

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
ROOT = CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _opened():
    return MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]


def test_the_top_is_thick_wood_with_a_lit_rim_and_one_leg():
    opened = _opened()
    assert "const under = ring(center, 0, TABLE_LIFT - TABLE_THICK);" in opened
    assert 'polygon("table-edge", under)' in opened and '"table-rim-light"' in opened
    assert 'polygon("table-grain"' in opened
    assert 'svgEl("g", { class: "table-foot" })' in opened and 'class: "leg"' in opened and 'class: "base"' in opened
    # Under the top, so the top hides all but a little of it.
    assert opened.index("foot, top);") > opened.index('polygon("table-shadow"')
    for name in ("--wood:", "--wood-deep:", "--wood-side:", "--wood-lit:"):
        assert name in ROOT
    assert ".top-mid { stop-color: var(--wood);" in CSS and ".top-out { stop-color: var(--wood-deep);" in CSS
    # The lamp and its light stay, and the split's dashed line on the top.
    assert 'svgEl("g", { class: "table-lamp" })' in opened and '"table-split"' in opened


def test_the_size_and_the_seats_spots_are_as_before():
    assert "const TABLE_RX = 150, TABLE_RY = 110, TABLE_LIFT = 7, SEAT_OUT = 48;" in MAP
    assert "tableTop = ring(center, 0, TABLE_LIFT);" in _opened()
    assert "const at = onTable(center, sitting.angle, SEAT_OUT);" in _opened()


def test_each_seat_sits_on_a_chair_its_back_to_the_outside():
    back = _inner("chairBack")
    assert "Math.atan2(at[1] - middle[1], at[0] - middle[0])" in back and "rotate(${a + 90})" in back
    assert 'chairBack(at, [lx, ly], 15, "chair-back")' in _opened()
    assert "chair(sitting.id, at, [lx, ly])" in _opened()
    assert 'chairBack(at, middle, CHAIR_R, "back")' in _inner("chair")
    # The empty chair: the same chair, dotted.
    assert ".chair circle, .chair .back { fill: var(--veil-thin); stroke: var(--moon); stroke-width: 1.4; stroke-dasharray: 3 3;" in CSS
    assert ".token .chair-back { fill: var(--wood-lit);" in CSS
