"""直し41の続き 段3: points over each other are told apart by a thin edge of
the map's ground and a small shadow (no new colour, no wider press); a place
name over a point moves a little, the point does not."""

import re

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
SCRIPT = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


def test_each_point_has_its_edge_behind_its_shape():
    draw = _inner("drawPoint")
    assert 'const edge = shape(seat.kind);' in draw and 'edge.setAttribute("class", "edge");' in draw
    assert draw.index("edge, shape(seat.kind)") > draw.index('class: "halo"')


def test_the_edge_is_the_grounds_colour_takes_no_press_and_follows_the_shape():
    rule = re.search(r"\.pt \.edge \{([^}]*)\}", CSS).group(1)
    assert "stroke: var(--night);" in rule and "fill: none;" in rule and "pointer-events: none;" in rule
    assert "#" not in rule and "rgb" not in rule  # No new colour.
    assert "scale(.84)" in rule  # Not met: as small as the shape.
    assert ".pt.met .edge, .pt.lit .edge { transform: translate(0px, .7px); }" in CSS
    assert ".pt.hover .edge, .pt:focus-visible .edge { transform: translate(0px, .7px) scale(1.15);" in CSS
    reduce = CSS[CSS.index("@media (prefers-reduced-motion: reduce) {"):]
    assert ".pt .halo, .pt .shape, .pt .edge," in reduce[:reduce.index("\n}\n")]


def test_a_place_name_moves_off_the_points_and_the_points_stay():
    clear = _inner("clearPlaceNames")
    assert '".points .pt .shape"' in clear and "leastCovered(" in clear and "nameMoves(" in clear
    assert 'name.setAttribute("dx",' in clear and 'name.removeAttribute("dx")' in clear
    assert "transform" not in clear  # Nothing but the names is moved.
    assert re.search(r"const NAME_MOVE_MOST = (\d+);", SCRIPT).group(1) == "36"
    relayout = _inner("relayout")
    assert relayout.index("clearSchoolName();") < relayout.index("clearPlaceNames();") < relayout.index("fixedBoxes(frameBox)")


def test_the_moves_are_nearest_first_and_no_further_than_the_most():
    moves = _inner("nameMoves")
    assert "const moves = [[0, 0]];" in moves and "d <= NAME_MOVE_MOST" in moves
