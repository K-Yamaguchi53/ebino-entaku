"""直し53 段7 (52's screen check, since 直し48): on the first screen
「ここに書いて『聞く』を押そう」 over the question box hid the map's words
under it (霧島山・鹿児島県, 県外・海外に出た人). It now goes over the box, slid
along it, clear of the map's words (the ways out's tags, the homes' names,
the place names, the seniors' count, the scenery's name), its point still on
the box. The screen check counts it ("guide over label N")."""

from pathlib import Path

from ebino import app as app_module

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CHECK = (Path(__file__).resolve().parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")


def test_the_sign_over_the_box_keeps_clear_of_the_maps_words():
    guide = APP[APP.index("const GUIDE = {"):APP.index("  one: {", APP.index("const GUIDE = {"))]
    assert 'write: { at: () => $("question"), voices: () => [], sides: ["above", "below"],' in guide
    assert 'card: { at: () => $("question"), words: "write", voices: () => [], sides: ["above", "below"],' in guide
    assert "clear: () => GUIDE.write.clear() }," in guide
    for part in (".map-around", ".home-names text", ".place-names text", ".school-count", "#map-look-label"):
        assert part in guide


def test_the_screen_check_counts_it():
    assert "guide over label ${g.labels}" in CHECK
    assert '#map-frame .map-around, #map-frame .home-names text, ' in CHECK
