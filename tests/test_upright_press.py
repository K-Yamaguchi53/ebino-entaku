"""直し45: at 768×1024 pressing a bubble made the top line wrap to two lines;
the map's room shrank, the map was laid out again and the bubble's choices
closed at once. Upright, the top line is two lines high whatever it says."""

from ebino import app as app_module

CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def test_upright_the_top_line_keeps_two_lines_of_room():
    upright = CSS[CSS.index("@media (orientation: portrait) {"):]
    upright = upright[:upright.index("\n}\n")]
    assert ".now-line { min-height: calc(2.9em + 12px); }" in upright
