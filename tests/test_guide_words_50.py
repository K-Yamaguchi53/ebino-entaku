"""直し50 段2 (ヒビキ: on 48_scene_autumn_button the yellow sign
「吹き出しを1つ押してみよう」 hid the farmer's words): the two signs,
「吹き出しを1つ押してみよう」 and 「コーチとオブザーバーの問いはここ。押して答えよう」,
are never over the people's words in their bubbles (the quotes' text). By
the card where it is clear of them; else a free place away from it, inside
the map's frame, its point short; else no sign (never over the words). The
screen check (tools/check_one_screen.js) measures it in the browser."""

from ebino import app as app_module

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
CHECK = (app_module.STATIC_DIR.parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")


def _spec(name):
    start = APP.index(f"  {name}: {{ at: ")
    return APP[start:APP.index("\n  // ", start + 1)]


def test_the_peoples_words_are_the_quotes_text_of_the_peoples_bubbles():
    body = APP[APP.index("function peopleVoices() {"):APP.index("// node if it is on screen")]
    assert ".table-bubble:not(.unplaced):not(.ai) .voice" in body and ".map-bubble .voice" in body


def test_both_signs_keep_off_the_peoples_words():
    assert "voices: peopleVoices" in _spec("table")
    assert "voices: peopleVoices" in _spec("answer_ai")
    # Kept as clear as the AI's questions are (never a cost only).
    assert "const keep = boxes([...spec.clear(), ...(spec.voices ? spec.voices() : [])])" in APP


def test_no_room_by_it_a_free_place_else_no_sign():
    draw = APP[APP.index("function drawGuide() {"):APP.index("function pointGuide(")]
    at = draw.index("if (!spot && spec.voices) {")
    rest = draw[at:]
    assert "const room = guideRoom(spec, box);" in rest
    # None: hidden, and unlit so it does not blink as it comes back.
    assert rest.index("guide.hidden = true;") < rest.index("return pointGuide(guide, room, box);")
    assert 'guide.classList.remove("fresh");' in rest
    # The old place by it (which kept nothing clear) comes only after.
    assert draw.index("const place = spot ||") > at
    room = APP[APP.index("function guideRoom(spec, box) {"):]
    room = room[:room.index("\n}\n")]
    assert 'document.querySelector("#map-overlay")' in room
    assert "rects(spec.voices())" in room and "return null;" in room


def test_far_its_point_short_and_no_new_motion():
    assert ".guide.far::after { border-width: 6px; }" in CSS
    far = CSS[CSS.index("/* 直し50 段2"):CSS.index(".guide.far[data-side=\"right\"]")]
    assert "animation" not in far and "transition" not in far


def test_the_screen_check_measures_the_sign_over_the_words():
    assert "guide over words" in CHECK
    assert '.table-bubble:not(.ai) .voice' in CHECK
