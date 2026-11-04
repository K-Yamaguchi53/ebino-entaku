"""A question card being written in the seat list stays open, with the
student's words, when the list is drawn again (直し26-3): when a round ends,
or a card elsewhere is sent. Only the student's own words go back in the box;
the page does not move, and the keyboard stays where it was unless it was in
the card. A card already sent is not opened again."""

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")


def _function(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n}\n", start) + 3]


def test_the_list_keeps_the_open_card_and_its_words_when_drawn_again():
    seats = _function("renderSeats")
    assert seats.index("const draft = keptDraft(list);") < seats.index("list.replaceChildren();")
    assert seats.index("putBackDraft(draft);") > seats.index("list.append(")
    kept = _function("keptDraft")
    assert "form.dataset.seat" in kept and "box.value" in kept and "document.activeElement === box" in kept
    assert "form.dataset.seat = seatId;" in _function("cardEntry")


def test_only_the_students_own_words_go_back_quietly():
    back = _function("putBackDraft")
    assert "state.carded.has(draft.seatId)) return;" in back  # Sent: not opened again.
    assert "openCardFor(draft.seatId, { quiet: true })" in back
    assert "box.value = draft.text;" in back  # Nothing but what the student wrote.
    assert "if (!draft.focused) return;" in back and "box.focus({ preventScroll: true })" in back
    assert "box.setSelectionRange(draft.start, draft.end)" in back
    # Quiet: the box is not focused and the page does not scroll for it.
    entry = _function("cardEntry")
    assert 'if (!open.dataset.still) form.querySelector("textarea").focus();' in entry
    open_for = _function("openCardFor")
    assert 'open.dataset.still = quiet ? "1" : "";' in open_for and "if (form && !quiet) form.scrollIntoView(" in open_for
    assert ".value =" not in entry and ".value =" not in open_for  # The box itself starts empty (SPEC 2-2).
