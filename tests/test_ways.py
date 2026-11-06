"""直し45 段4: 行き止まりの道案内. No seat answered: the card as before, and
two or three ways on by kind of talk, picked by code; a way pressed shows up
to three seats' own words of that kind, with no model. Everything is invented."""

import random

import pytest
from fake_client import FakeClient

from ebino import app as app_module, closing, directions, roundtable, texts
from ebino.gate import Gate, NameList
from ebino.session import Library, Refused, Session
from test_closing import ALL_SEATS, KINDS, PIECES
from test_session import UTTERANCES, editor_says, librarian_finds

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
NOBODY = "宇宙の話は？"
SILENT = [librarian_finds(), editor_says()]


def sitting(answers, kinds=KINDS):
    client = FakeClient(list(answers))
    lib = Library.build(ALL_SEATS, UTTERANCES + PIECES, {}, False, kinds)
    session = Session(lib, Gate(client, NameList.build(ALL_SEATS, {})), rng=random.Random(1))
    return session, client


def test_no_one_answered_the_card_as_before_and_ways_by_kind():
    session, _ = sitting(SILENT)
    view = session.ask(NOBODY)
    assert view["status"] == "silent" and view["card"] is not None and session.cards
    assert view["ways_notice"] == texts.id_table(texts.DIRECTION_WORDS, texts.DIRECTION_WORD_IDS)["notice"]
    assert 2 <= len(view["ways"]) <= 3
    order = [k for k in ("to_students", "reason", "joy", "hardship", "refresh", "school_days", "values", "skills",
                         "daily", "local", "future")]
    assert [w["kind"] for w in view["ways"]] == sorted((w["kind"] for w in view["ways"]), key=order.index)
    assert view["ways"][0]["text"].startswith("『") and "』の話を聞く" in view["ways"][0]["text"]


def test_a_way_pressed_shows_the_seats_words_with_no_model():
    session, client = sitting(SILENT)
    view = session.ask(NOBODY)
    sent = len(client.requests)
    kind = view["ways"][0]["kind"]
    way = session.take_way(1, kind)
    assert len(client.requests) == sent  # No model.
    assert way["status"] == "answered" and 1 <= len(way["quotes"]) <= 3
    held = session.library.closing_pieces
    for quote in way["quotes"]:
        assert any(e.utterance_id == quote["utterance_id"] for e in held[quote["seat_id"]][kind])
        assert quote["text"] in session._utterances[quote["utterance_id"]].text  # Its own words, as recorded.
    # In the seats' order.
    order = [s.seat_id for s in session.library.seats]
    assert [q["seat_id"] for q in way["quotes"]] == sorted((q["seat_id"] for q in way["quotes"]), key=order.index)
    # Back to the source works; nothing asked of a model after it either.
    assert session.paragraph(way["quotes"][0]["utterance_id"])["paragraph"]
    assert session.close_round(2)["words"] == [] and session.coach_band(2)["cards"] == []
    assert len(client.requests) == sent
    assert [i["kind"] for i in session.trail_view()["items"]][-1] == "direction"


def test_pressed_twice_no_piece_again_and_the_way_goes():
    session, _ = sitting(SILENT)
    view = session.ask(NOBODY)
    kind = view["ways"][0]["kind"]
    first = session.take_way(1, kind)
    with pytest.raises(Refused):
        session.take_way(1, kind)
    assert kind not in [w["kind"] for w in session.ways_view(1)]
    shown = {q["utterance_id"] for q in first["quotes"]}
    for other in session.ways_view(1):
        again = session.take_way(1, other["kind"])
        assert not shown & {q["utterance_id"] for q in again["quotes"]}


def test_the_guard_and_the_name_list_stand():
    session, _ = sitting(SILENT)
    session.ask(NOBODY)
    held = {"S01": {"refresh": [e for e in session.library.entries if e.utterance_id == "a7"]}}
    names = NameList.build(ALL_SEATS, {})
    picked = directions.pick(held, ["S01"], "refresh", set(), NOBODY, session.guard, names)
    assert picked == [("S01", "a7", "休みの日は、川で釣りをします。")]
    class EveryWordAName:
        def hits(self, text):
            return ["x"]
    assert directions.pick(held, ["S01"], "refresh", set(), NOBODY, session.guard, EveryWordAName()) == []


def test_the_kinds_with_most_pieces_not_shown_yet_in_the_tables_order():
    held = {"A": {"joy": [1, 2, 3], "reason": [1], "local": [1, 2]}, "B": {"joy": [1], "daily": [1, 2]}}
    order = ["reason", "joy", "daily", "local", "future"]
    assert directions.offered(held, order, set()) == ["joy", "daily", "local"]  # 4, 2, 2 pieces; reason 1.
    assert directions.offered(held, order, {"joy"}) == ["reason", "daily", "local"]


def test_every_kind_shown_no_way_offered():
    session, _ = sitting(SILENT)
    shown = set(session.library.kind_order) - {"none"}
    assert directions.offered(session.library.closing_pieces, session.library.kind_order, shown) == []


def test_a_long_piece_is_cut_where_a_sentence_ends():
    text = "一つ目の文です。" * 20
    out = directions.cut(text)
    assert out.endswith("。") and len(out) <= directions.CUT_CHARS and text.startswith(out)


def test_the_screen_shows_the_ways_over_the_box():
    assert 'id="ways"' in HTML and 'id="ways-buttons"' in HTML
    assert 'call("/api/direction", { round: roundNo, kind })' in APP
    assert "if (!round.way) showWays(round);" in APP


def test_a_kind_shown_only_in_a_last_word_is_still_offered():
    """直し46: the kinds counted as shown are those of the bubbles (and 1対1,
    「もっと聞く」, the seats' answers); a last word (締めの一言) alone does
    not make its kind shown, so the way to it stays."""
    session, _ = sitting(SILENT)
    session.ask(NOBODY)
    held = session.library.closing_pieces
    seat, by_kind = next((s, k) for s, k in held.items() if k)
    kind, pieces = next((k, p) for k, p in by_kind.items() if p and k != "none")
    uid = pieces[0].utterance_id
    session.rounds[0].closing = closing.Closing("shown", words=[closing.Word(seat, uid, "架空", kind)])
    assert uid in session.seen_ids()  # Never shown again, as before.
    assert kind not in session._shown_kinds()
    order = session.library.kind_order
    assert directions.offered(held, order, session._shown_kinds()) == directions.offered(held, order, set())
    # The same piece in a bubble: its kind is shown.
    session.rounds[0].quotes.append(roundtable.ShownQuote(uid, seat, "spoken", "架空"))
    assert kind in session._shown_kinds()
