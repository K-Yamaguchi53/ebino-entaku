"""直し37-2: back at the map, the AI's seat is folded: its heading and the
button that opens it, at the same corner. Its corner is still chosen by the
opened seat's size, and the upright screen's band under the map stays as it
was, so the meeting's bubbles and the map do not move when it comes out
again. While the meeting is out, and while one of its questions is being
answered, it is open. Folded, the keyboard reaches its button, and Enter
(a button) opens it."""

import re

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_back_at_the_map_it_is_folded_and_the_meeting_or_an_answer_opens_it():
    assert "app.foldAiSeat(true);" in _inner("closeTable")
    assert "foldAiSeat(false);" in _top("renderAiSeat")  # A round's questions: the meeting is out.
    assert "foldAiSeat(false);" in _top("answerTo")
    assert "foldAiSeat };" in APP  # Lent to the map.


def test_folded_it_is_its_heading_and_a_button_named_by_it_with_no_new_words():
    button = re.search(r'<button id="ai-seat-open"[^>]*>', HTML.replace("\n", " ")).group(0)
    assert 'type="button"' in button and 'aria-controls="ai-seat-cards"' in button
    assert 'aria-labelledby="ai-seat-label"' in button and "hidden" in button
    fold = _top("foldAiSeat")
    assert 'seat.classList.toggle("folded", fold);' in fold and "open.hidden = !fold;" in fold
    assert 'open.setAttribute("aria-expanded", String(!fold));' in fold
    # Opened from its button, the keyboard to its first question.
    assert '$("ai-seat-open").onclick = openAiSeat;' in _top("renderAiSeat")
    assert "first.focus({ preventScroll: true });" in _top("openAiSeat")
    assert ".ai-seat.folded .ai-seat-note, .ai-seat.folded .ai-seat-cards { display: none; }" in CSS


def test_its_corner_and_the_upright_band_are_as_before_only_its_inside_folds():
    place = _inner("placeAiCorner")
    # The corner is still chosen with the opened seat's height.
    assert "const h = Math.round(view.upright ? Math.max(f.height * AI_BAND_UP, free) : f.height * AI_ROOM);" in place
    assert "const tall = h;" in place
    assert "AI_BAND_UP = 0.3" in MAP
    # Folded: as tall and as wide as its heading, at the same corner and side.
    assert re.search(r"#ai-seat\.folded \{ height: auto; width: auto;\s+max-width: var\(--ai-w, 320px\);", CSS)
    assert '.stage[data-ai-corner$="right"] #ai-seat.folded { left: auto;' in CSS
    assert 'stage.style.setProperty("--ai-right",' in place


def test_folded_it_sits_where_it_covers_least_within_its_open_seats_room():
    # 直し37-3 (the screen check at 1180: the corner's edge covered a way out's name).
    folded = _inner("placeFoldedSeat")
    assert "const boxes = seatKeepsOff(f);" in folded
    assert "for (let shift = 0; shift <= Math.max(0, room - s.height); shift += 8) {" in folded
    assert 'stage.style.setProperty("--ai-fold-shift", `${best}px`);' in folded
    assert "placeFoldedSeat();" in _inner("placeAiCorner") and "requestAnimationFrame(placeFoldedSeat);" in _inner("closeTable")
    assert "bottom: calc(var(--ai-bottom, 8px) + var(--ai-fold-shift, 0px));" in CSS
    assert "top: calc(var(--ai-top, 8px) + var(--ai-fold-shift, 0px));" in CSS
