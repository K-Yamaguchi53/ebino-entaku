"""直し33-5: what this morning's check left. Japanese broken between words in
the new boxes too (the AI's cards and name, the drawer's paragraph, the
box's example and its label); a bubble's buttons, pressed a second time,
keep off the map's words where they can; the map's old card and the seat
list's card form are gone. tools/check_word_breaks.js reads a page for a
line that begins inside a word (Intl.Segmenter), as 直し31続き checked."""

from pathlib import Path

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CHECK = Path(__file__).resolve().parents[1] / "tools" / "check_word_breaks.js"


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_the_new_boxes_break_between_words():
    rule = CSS[CSS.index(".now-line, .start-purpose, .inside"):]
    rule = rule[:rule.index("}")]
    for box in (".ai-seat", ".drawer-body", ".ask textarea", ".input-to"):
        assert box in rule, box
    assert "word-break: auto-phrase;" in rule
    # A label with a （…） is never broken inside it: 「架空の川／1」, 「ませ／ん」 no more.
    assert '$("input-to-label").replaceChildren(phrased(label));' in _top("setTo")
    assert '$("ai-seat-label").replaceChildren(phrased(state.texts.ai_seat_label));' in _top("renderAiSeat")


def test_the_choices_keep_off_the_maps_words_where_they_can():
    put = _inner("putChoices")
    assert '.place-names text, .home-names text, .school text' in put
    assert "...seenWords(frameWH, words," in put
    # With the seats gathered the map's words are not shown, so nothing is under the buttons.
    assert ".dim .place-names, .dim .home-names, .dim .school text { visibility: hidden; }" in CSS
    assert "const words = tableTop ? [] :" in _inner("fixedBoxes")
    # Whose card, kept whole in its phrases.
    assert "who.append(app.phrased(whoOf(seatOf(seatId))));" in _inner("openChoices")


def test_the_maps_card_and_the_card_form_are_gone():
    assert 'id="map-card"' not in HTML and '$("map-card")' not in MAP and "keepCardInSight" not in MAP
    assert ".map-card" not in CSS and ".card-form" not in CSS


def test_the_check_reads_the_page_only():
    source = CHECK.read_text(encoding="utf-8")
    assert 'new Intl.Segmenter("ja", { granularity: "word" })' in source
    for outside in ("fetch(", "XMLHttpRequest", "sendBeacon", "http"):
        assert outside not in source
