"""直し31-2: one question card per seat and words. Pressed again (or sent
from a second box for the seat), no new card is made and the one there is
is shown. Everything here is invented."""

from pathlib import Path

from test_session import ANSWERED, editor_says, librarian_finds, sitting

APP = (Path(__file__).resolve().parent.parent / "ebino" / "static" / "app.js").read_text(encoding="utf-8")
QUESTION = "休みの日って、みんな何してる？"


def spoken():
    session, client = sitting(ANSWERED + [editor_says(), editor_says(), editor_says()])
    session.ask(QUESTION)
    return session, client


def test_the_same_words_to_the_same_seat_twice_make_one_card():
    session, client = spoken()
    first = session.write_card("S01", "休みはだれが決めますか")
    sent = len(client.requests)
    again = session.write_card("S01", " 休みは だれが決めますか ")  # Spaces aside, the same words.
    assert first["again"] is False and again["again"] is True
    assert again["card_id"] == first["card_id"] and len(session.cards) == 1
    assert len(client.requests) == sent  # No model for the second press.


def test_other_words_or_another_seat_make_another_card():
    session, _ = spoken()
    session.write_card("S01", "休みはだれが決めますか")
    session.write_card("S01", "休みの日は何をしますか")
    session.write_card("S02", "休みはだれが決めますか")
    assert [(c.seat_id, c.text) for c in session.cards] == [
        ("S01", "休みはだれが決めますか"), ("S01", "休みの日は何をしますか"), ("S02", "休みはだれが決めますか")]


def test_the_same_question_unanswered_twice_keeps_one_card():
    session, _ = sitting([librarian_finds(), editor_says(), librarian_finds(), editor_says()])
    one = session.ask(QUESTION)
    two = session.ask(QUESTION)
    assert len(session.cards) == 1 and one["card"]["card_id"] == two["card"]["card_id"]
    assert session.rounds[1].card is session.cards[0]


def test_the_screen_sends_a_card_once_and_shows_the_one_there_is():
    entry = APP[APP.index("function cardEntry("):]
    entry = entry[:entry.index("\n}\n")]
    assert entry.index("send.disabled = true;") < entry.index('await call("/api/card"')
    assert "if (send.disabled) return;" in entry
    assert "if (card.again) state.cardAgain[seatId] = card.text;" in entry
    assert 'state.texts.card_already.replace("{card}", again)' in APP
