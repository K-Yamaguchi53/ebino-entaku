"""Pressing a lamp card at the round table (直し26-2): one small card of
choices opens by it, each calling what the round's own cards below the map
already do (no new way to the server, no model): 元の段落を読む (in the card),
印をつける (one mark, the cards below follow), この人に聞きたいことを書く (the seat
list's own card, its box empty) and 下のやりとりで読む (the page and the focus
go to that quote). One open at a time; Esc closes it. A line by the map's
lower edge says a card can be pressed, until one is. The words are the
teacher's, in texts/."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_the_words_are_the_teachers():
    assert texts.bubble_choices() == {"paragraph": "元の段落を読む", "mark": "印をつける",
                                      "card": "この人に聞きたいことを書く", "read": "下のやりとりで読む"}
    shown = texts.screen_texts()
    assert shown["bubble_choices"] == texts.bubble_choices()
    assert shown["bubble_hint"] == "吹き出しを押すと、次にできることが出ます"
    for word in ("元の段落を読む", "この人に聞きたいことを書く", "下のやりとりで読む", "吹き出しを押すと"):
        # Not written into the screen's code (a comment may name it).
        assert f'"{word}' not in MAP and f'"{word}' not in APP
    assert "app.state.texts.bubble_choices" in _inner("openChoices")
    assert "app.state.texts.bubble_hint" in _inner("openTable")


def test_a_choices_table_missing_a_row_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    (tmp_path / "bubble_choices.tsv").write_text("ID\t文字\nparagraph\t元の段落を読む\n", encoding="utf-8")
    with pytest.raises(ValueError):
        texts.bubble_choices()


def test_a_card_and_a_seat_left_out_take_a_press_that_opens_one_card_of_choices():
    bubble = _inner("tableBubble")
    assert "node.tabIndex = 0;" in bubble and 'setAttribute("role", "button")' in bubble
    assert "pressable(node, () => toggleChoices(seatId))" in bubble
    assert "toggleChoices(seatId);" in _inner("seatPress")
    toggle = _inner("toggleChoices")
    assert "choices.seatId === seatId) return closeChoices(true)" in toggle
    opened = _inner("openChoices")
    assert opened.index("closeChoices(false);") < opened.index("card.after(node)")  # One at a time.
    assert "dropHint();" in opened and "read.focus({ preventScroll: true })" in opened
    # Esc closes it, the arrows go from one choice to the next.
    move = _inner("moveInChoices")
    assert 'event.key === "Escape"' in move and "ArrowDown: 1" in move and "ArrowUp: -1" in move
    assert "closeChoices(false);" in _inner("clearTable")
    # No browser balloon: the words are on the card.
    assert "title" not in opened.replace("whoOf", "")


def test_each_choice_calls_what_the_round_below_already_does():
    opened = _inner("openChoices")
    assert "app.paragraph(utteranceId)" in opened and "app.mark(tableRoundNo, utteranceId)" in opened
    assert "app.openCard(seatId)" in opened and "app.readBelow(tableRoundNo, utteranceId)" in opened
    assert "fetch(" not in MAP and "call(" not in MAP  # The map asks the server nothing itself.
    lent = APP[APP.index("const lent = {"):APP.index("};", APP.index("const lent = {"))]
    for part in ("paragraph: paragraphOf", "mark: markQuote", "openCard: openCardFor", "readBelow"):
        assert part in lent
    # The quote's own buttons go the same ways.
    quote = _top("renderQuote")
    assert "await paragraphOf(quote.utterance_id)" in quote and "markQuote(roundNo, quote.utterance_id)" in quote
    assert '"/api/paragraph"' in _top("paragraphOf") and '"/api/mark"' in _top("markQuote")


def test_one_mark_in_one_place_and_the_map_follows_it():
    mark = _top("markQuote")
    assert "state.marks = (await call(" in mark and 'classList.toggle("marked"' in mark
    assert "onMap((map) => map.marked())" in mark
    marked = _inner("marked")
    assert "app.state.marks" in marked and 'setAttribute("aria-pressed"' in marked
    assert "return { init, show, round, refresh, marked };" in MAP


def test_the_card_is_the_seat_lists_own_with_its_box_empty():
    open_for = _top("openCardFor")
    assert "cardEntry(seatId, renderSeats, (form, button) => putUnderLine(seat, form, button))" in open_for
    assert ".value" not in open_for and "placeholder" not in open_for
    assert 'open.dataset.quiet = "1"' in open_for and "open.click();" in open_for
    assert "if (open.dataset.quiet) open.remove();" in _top("putUnderLine")
    assert '"data-seat": seat.seat_id' in _top("renderSeat")


def test_reading_below_goes_to_that_quote_in_its_round_and_takes_the_focus():
    below = _top("readBelow")
    assert '.round[data-round="${roundNo}"] .quote' in below and "node.dataset.utterance === utteranceId" in below
    assert "quote.tabIndex = -1;" in below and "quote.focus({ preventScroll: true })" in below
    assert '"data-round": round.round' in _top("renderRound")
    assert ".quote:focus { outline: 2px solid var(--lamp)" in CSS


def test_the_hint_goes_once_a_card_is_pressed_and_keeps_by_the_lower_edge():
    assert "if (!pressedOnce) overlay.append(div(\"map-hint\"" in _inner("openTable")
    assert "pressedOnce = true;" in _inner("dropHint")
    around = _inner("placeAround")
    assert 'querySelectorAll(".map-hint")' in around and "[0, 1], clear)" in around
    assert ".map-compass, .map-around, .map-hint" in _inner("fixedBoxes")  # The cards keep off it.


def test_a_card_shown_by_its_seat_goes_again_with_its_choices_and_the_keyboard_goes_back():
    close = _inner("closeChoices")
    assert "const shownByPress = seatId === opened;" in close and "if (shownByPress) opened = null;" in close
    assert "if ((shownByPress || moved) && !laying) relayout();" in close  # Moved for them (直し27-1): back too.
    assert 'querySelectorAll(".under-choices")) other.classList.remove("under-choices")' in close
    assert "press.focus({ preventScroll: true })" in close
    assert "closeChoices(false, true)" in _inner("putChoices")  # Not laid out again from inside the layout.


def test_what_the_choices_cover_steps_behind_them_their_own_card_too():
    put = _inner("putChoices")
    assert "for (const other of [...shown, card]) if (overlaps(node, other)) other.classList.add(\"under-choices\")" in put
    assert ".under-choices { visibility: hidden; }" in CSS
    assert "for (const overOwn of [false, true])" in put  # Over its own card before the table.


def test_the_hint_goes_a_line_higher_when_the_edge_has_no_room():
    around = _inner("placeAround")
    assert "frameWH.h - up * (box.h + 6)" in around and "coverOf(spot, box, clear) === 0" in around
    assert 'querySelectorAll(".map-compass, .map-around")' in around  # Not its own last spot.


def test_the_choices_are_drawn_in_the_nights_colours_with_a_focus_ring():
    rules = CSS[CSS.index(".table-bubble { pointer-events: auto;"):CSS.index("/* Under the card a seat shows when pressed. */")]
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", rules)
    assert "var(--gothic)" in rules and "var(--mincho)" in rules and "var(--veil)" in rules
    assert ".table-bubble:focus-visible { outline: 2px solid var(--lamp)" in rules


_SPOT = """
%(source)s
const frame = { w: 600, h: 400 };
const own = [100, 100, 150, 60];
const box = { w: 200, h: 90 };
const hit = (s, b) => s[0] < b[0] + b[2] && b[0] < s[0] + box.w && s[1] < b[1] + b[3] && b[1] < s[1] + box.h;
const right = choiceSpot(frame, box, own, [], []);
const table = [[255, 0, 345, 400]];  // Nothing to the right.
const left = choiceSpot(frame, box, own, table, []);
// Room only where its own card is: a band 80px high, the card in it.
const tight = [[0, 0, 600, 90], [255, 0, 345, 400], [0, 170, 600, 230]], low = { w: 200, h: 70 };
const crowded = choiceSpot(frame, low, own, tight, []);
const over = choiceSpot(frame, low, own, tight, [], true);
process.stdout.write(JSON.stringify({ right, left, leftHits: [...table, own].some((b) => hit(left[0], b)), crowded, over }));
"""


@node
def test_the_choices_go_beside_their_card_and_off_the_table_or_say_they_cannot():
    out = subprocess.run(["node", "-"], input=(_SPOT % {"source": _inner("choiceSpot")}).encode("utf-8"),
                         capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    spots = json.loads(out.stdout.decode("utf-8"))
    assert spots["right"] == [[258, 100], True]  # To the right of its card, 8px off, its top level.
    assert spots["left"][1] is True and not spots["leftHits"]  # Off the table and its own card.
    assert spots["crowded"][1] is False  # No room: it says so, and putChoices tries another way.
    assert spots["over"][1] is True  # Over its own card rather than the table.
    plan = _inner("choiceSpot")
    for outside in ("overlay", "dataset", "document", "style", "classList"):
        assert outside not in plan
