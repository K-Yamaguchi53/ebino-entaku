"""直し45 段2: 今日の道すじ, the way one student went, from the record's
numbered steps; 「ここで問いが変わった」 decided by code, never by a model.
Everything here is invented."""

import random

import pytest
from fake_client import FakeClient

from ebino import app as app_module, trail
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.session import Library, Refused, Session
from test_one_to_one import Kept
from test_session import ANSWERED, SEATS, UTTERANCES

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
FIRST = "休みの日って、みんな何してる？"
SECOND = "休みを決めると、仕事はどう変わる？"


@pytest.mark.parametrize("before, after, changed", [
    (FIRST, FIRST, False),
    (FIRST, "休みの日って、 みんな 何してる", False),  # Spaces and ？ only.
    (FIRST, "休みの日って！みんな、何してる？？", False),  # Punctuation only.
    (FIRST, "休みの日って、みんなは何をしてる？", False),  # Two characters: a typo put right.
    (FIRST, "休みの日って、みんなは何をしてるの？", True),  # Three.
    (FIRST, SECOND, True),
    ("ＡＢＣって何？", "ABCって何", False),  # Letter widths folded.
])
def test_another_question_is_decided_by_code(before, after, changed):
    assert trail.changed(before, after) is changed


def sitting(answers, records=None):
    client = FakeClient(list(answers))
    lib = Library.build(SEATS, UTTERANCES, {}, False)
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1), records=records)
    return session, client


def test_the_steps_come_in_turn_and_a_changed_question_ties_to_what_was_heard_last():
    session, client = sitting([*ANSWERED, *ANSWERED, *ANSWERED])
    session.ask(FIRST)
    session.bubble_opened(1, "a1")
    session.bubble_opened(1, "a1")  # Pressed again at once: one step.
    session.bubble_opened(1, "b1")
    session.ask(FIRST + " ")  # The same question again: no mark.
    session.ask(SECOND)
    sent = len(client.requests)
    items = session.trail_view()["items"]
    assert len(client.requests) == sent  # No model for the trail.
    assert [(i["n"], i["kind"]) for i in items] == [
        (1, "question"), (2, "opened"), (3, "opened"), (4, "question"), (5, "question")]
    assert [i.get("changed") for i in items if i["kind"] == "question"] == [False, False, True]
    assert items[4]["came_from"] == 3 and items[4]["text"] == SECOND
    assert items[1]["who"] == "理容師" and items[2]["who"] == "農家"
    # The lit seats, by their titles only (no company without EBINO_SHOW_COMPANY).
    assert items[0]["lit"] == ["理容師", "農家"]
    assert "はるかぜ" not in str(items)


def test_one_to_one_and_cards_go_in_among_them_in_turn(monkeypatch):
    from test_one_to_one import SEATS as ONE_SEATS, UTTERANCES as ONE_UTTERANCES
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    lib = Library.build(ONE_SEATS, ONE_UTTERANCES, {}, False)
    session = Session(lib, Gate(FakeClient([]), NameList.build(ONE_SEATS, {})), rng=random.Random(1))
    session.one_ask("P01", "目的")
    items = session.trail_view()["items"]
    assert items == [{"n": 1, "kind": "one_ask", "who": "探究の先輩（架空）", "text": items[0]["text"], "label": ""}]
    assert items[0]["text"]  # The question as it was offered.


def test_a_bubble_not_shown_is_refused_and_no_step_kept():
    session, _ = sitting(ANSWERED)
    session.ask(FIRST)
    with pytest.raises(Refused):
        session.bubble_opened(1, "c1")
    with pytest.raises(Refused):
        session.bubble_opened(2, "a1")
    assert [s["kind"] for s in session.steps] == ["question"]


def test_the_steps_are_kept_with_the_record_and_nothing_else_goes():
    kept = Kept()
    session, _ = sitting(ANSWERED, kept)
    session.ask(FIRST)
    session.bubble_opened(1, "a1")
    record = kept.sessions[-1]
    assert record["trail"] == [{"n": 1, "kind": "question", "round": 1, "text": FIRST},
                               {"n": 2, "kind": "opened", "round": 1, "seat_id": "S01", "utterance_id": "a1"}]
    # The record's fields as before are all there (none taken away).
    for key in ("rounds", "marked_quotes", "met_seats", "cards", "more", "reflection", "one_to_one", "one_spoken",
                "one_tidied", "one_rephrased", "hitokoto", "spoken", "ai_answered_after_notice"):
        assert key in record


def test_only_this_sittings_trail_is_given_and_by_get(tmp_path):
    lib = Library.build(SEATS, UTTERANCES, {}, False)
    client = FakeClient([*ANSWERED])
    the_app = App(lib, Gate(client, NameList.build(SEATS, {})))
    assert the_app.trail() == {"items": []}
    the_app.handle("/api/start", {"lab": "quest"})
    the_app.handle("/api/ask", {"question": FIRST})
    the_app.handle("/api/trail/opened", {"round": 1, "utterance_id": "a1"})
    assert [i["kind"] for i in the_app.trail()["items"]] == ["question", "opened"]
    the_app.handle("/api/start", {"lab": "quest"})  # Another sitting.
    assert the_app.trail() == {"items": []}


def test_the_screen_asks_for_it_and_shows_it_by_the_map():
    assert 'id="trail"' in HTML and 'id="trail-open"' in HTML and 'id="trail-list"' in HTML
    assert 'fetch("/api/trail")' in APP
    assert 'call("/api/trail/opened"' in APP
    assert 'const small = (text) => el("span", { class: "trail-small" }, phrased(text));' in APP
    # In the column, the room left over only: a long trail never squeezes the buttons.
    assert ".map-bar .trail { flex: 1 1 0; }" in CSS
    # A low screen (1366×650): the column tighter, so every button keeps its room.
    low = CSS[CSS.index("/* A low screen (1366×650): the box one line shorter."):]
    low = low[:low.index("\n}\n")]
    assert ".map-bar { gap: 6px; }" in low and ".map-bar .trail-open { min-height: 34px; }" in low
    # Shut at first where there is no room (1366×650 and upright), open elsewhere.
    assert 'matchMedia("(max-height: 700px), (orientation: portrait)")' in APP
