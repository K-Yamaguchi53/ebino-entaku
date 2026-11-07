"""直し52 段4 (ヒビキ, 48_scene_autumn_start / 48_ai_seat): the small words read.
On the screen 14px at least (the place names 13px), and 4.5:1 at least with
what is right behind them: the steps' names, the column's items and today's
trail, the place names and the ways out (方面), the homes' names, 会った席, the
seasons and ＋ − 全体, the scenery's label and the seats' labels at the table.
The map's sources at its foot stay as they were. (The screen check measured
them in a browser, the words hidden and the screen's own pixels read behind
them: see the report.)"""

import re

from ebino import app as app_module

CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")


def rule(selector):
    """The rule of that selector alone that sets its font-size (the last such, as the browser takes)."""
    found = [m.start() for m in re.finditer(r"(?m)^" + re.escape(selector) + r" \{", CSS)]
    blocks = [CSS[at:CSS.index("}", at)] for at in found]
    sized = [b for b in blocks if "font-size" in b]
    return sized[-1] if sized else blocks[-1]


def px(block):
    size = re.search(r"font-size: ([0-9.]+)px", block)
    assert size, block
    return float(size.group(1))


def test_the_steps_names():
    assert px(rule(".now-steps")) == 15 and "color: var(--soft);" in rule(".now-steps")
    short = CSS[CSS.index("@media (max-height: 720px) {\n  .now {"):]
    assert "  .now-steps { font-size: 14px; }" in short[:short.index("}\n}")]


def test_the_trail_and_the_column():
    for selector in (".trail-small", ".trail-label", ".trail-ai .trail-ai-name"):
        assert px(rule(selector)) >= 14, selector
    assert px(rule(".trail-turn")) >= 14
    assert px(rule(".trail-list")) >= 14


def test_the_maps_words():
    assert "const TEXT_PX = { place: 13, school: 12, home: 14 };" in MAP
    assert "text.style.strokeWidth = `${3 * perPx}px`;" in MAP
    assert "stroke: var(--night);" in rule(".place-names text")
    around = rule(".map-around")
    assert px(around) == 14 and "background: color-mix(in srgb, var(--night-deep) 72%, transparent);" in around
    assert px(rule(".map-look-label .look-note")) == 14 and px(rule(".map-look-label .look-name")) == 14
    assert px(rule(".table-label")) == 14


def test_the_sources_as_they_were():
    assert "--fs-s: .88rem;" in CSS  # 会った席, the seasons and ＋ − 全体: 14.1px, as before.
