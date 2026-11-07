"""直し52 段5: at the meeting, a breath of 0.25 s between the last seat
landing and the cards lighting (landed, then lit), with motion only; the
camera, the table rising and the seats' flights as they were. (In a browser:
the first card ~300 ms after the last flight, was 50 to 130 ms.)"""

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
OPEN = MAP[MAP.index("  async function openTable("):MAP.index("  // Each seat that spoke: its lamp card by its chair")]


def test_a_breath_after_the_last_seat_lands_with_motion_only():
    assert "const LANDED_PAUSE = 250;" in MAP
    assert "const CAMERA_FOR = 700, FLY_FOR = 700, FLY_GAP = 90, BACK_FOR = 700;" in MAP
    assert "RISE_FOR = 700" in MAP
    landed = OPEN.index("const done = await Promise.all(landed)")
    pause = OPEN.index("if (motion) {\n      await wait(LANDED_PAUSE);\n      if (!still()) return;\n    }")
    assert landed < pause < OPEN.index('const label = div("table-label", title);')
    assert LANDED_PAUSE_MS() <= 500


def LANDED_PAUSE_MS():
    return int(MAP.split("const LANDED_PAUSE = ", 1)[1].split(";", 1)[0])
