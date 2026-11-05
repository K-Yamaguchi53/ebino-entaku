"""The round table (直し35-3: the school's ring, risen from the map; before
it a table of wood, 直し29-2): its rim lit, the lamp in its middle; each
seat on a chair whose back is to the outside, an empty chair the same chair
in a dotted line. The seats' spots and the cards' layout are as before."""

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
ROOT = CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _opened():
    return MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]


def test_the_table_is_the_risen_schools_ring_its_rim_lit_and_the_lamp_in_its_middle():
    opened = _opened()
    assert "const risen = riseSchool(center, motion);" in opened
    assert 'top.append(risen.group, polygon("table-rim-glow", tableTop), lamp);' in opened
    assert "table-grain" not in opened and "table-foot" not in opened  # No table of wood any more.
    # The lamp and its light stay (in the glass roof), and the split's dashed line.
    assert 'svgEl("g", { class: "table-lamp" })' in opened and '"table-split"' in opened


def test_the_size_and_the_seats_spots_are_as_before():
    assert "const TABLE_RX = 150, TABLE_RY = 110, TABLE_LIFT = 7, SEAT_OUT = 48;" in MAP
    assert "tableTop = ring(center, 0, TABLE_LIFT);" in _opened()
    # The seats that spoke sit where their cards have room (直し33-4); the
    # empty chairs, and a seat with no room there, round the table as before.
    assert "const at = spot ? spot.at : onTable(center, sitting.angle, SEAT_OUT);" in _opened()


def test_each_seat_sits_on_a_chair_its_back_to_the_outside():
    back = _inner("chairBack")
    assert "Math.atan2(at[1] - middle[1], at[0] - middle[0])" in back and "rotate(${a + 90})" in back
    assert 'chairBack(at, [lx, ly], 15, "chair-back")' in _opened()
    assert "chair(sitting.id, at, [lx, ly])" in _opened()
    assert 'chairBack(at, middle, CHAIR_R, "back")' in _inner("chair")
    # The empty chair: the same chair, dotted.
    assert ".chair circle, .chair .back { fill: var(--veil-thin); stroke: var(--moon); stroke-width: 1.4; stroke-dasharray: 3 3;" in CSS
    assert ".token .chair-back { fill: var(--wood-lit);" in CSS


def test_cards_and_names_keep_off_the_chairs_backs_and_the_tables_leg():
    fixed = _inner("fixedBoxes")
    assert '".token .shape, .chair circle, .chair .hit"' in fixed
    assert '", .token .chair-back, .chair .back, .table-foot .leg, .table-foot .base"' in fixed


def test_the_choices_give_up_the_chairs_backs_only_where_they_find_no_room_else():
    put = _inner("putChoices")
    assert "fixedBoxes(frameBox, false, false, withBacks)" in put
    assert put.index("if (withBacks) return putChoices(false);") < put.index("// No such spot: as before")
    assert "withBacks = true" in _inner("fixedBoxes")
