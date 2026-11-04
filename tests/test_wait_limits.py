"""直し31-1: every model call the screen waits on after the student acts has
a wait limit, with no retry. Past it the call counts as not usable and takes
the way it already has for that. Everything here is invented.

The fake model here never sleeps: it is given how long it would take, and
when that is past the limit the request carries, it raises what the SDK
raises when the wait runs out."""

import random
from collections import Counter

import anthropic
import httpx2
import pytest
from fake_client import FakeClient

from ebino import ask_seat, closing, coach, editor, gate, librarian, moderator, reflection, roundtable, subjects
from ebino.gate import Gate, NameList
from ebino.session import Session
from ebino.texts import ASK_BACK_FALLBACK, MODEL_UNAVAILABLE, load_text
from test_session import ANSWERED, SEATS, editor_says, library, librarian_finds


class Slow:
    """A response that takes `seconds` to come."""

    def __init__(self, seconds, response=None):
        self.seconds, self.response = seconds, response


class SlowClient(FakeClient):
    """Past the request's timeout, the SDK's timeout error; else the answer."""

    def _create(self, **request):
        waited = self._pending_options.get("timeout")
        answer = self._answers[0] if self._answers else None
        if isinstance(answer, Slow):
            self._answers[0] = answer.response
            if waited is not None and answer.seconds > waited:
                self._answers[0] = anthropic.APITimeoutError(
                    request=httpx2.Request("POST", "https://api.invalid/v1/messages"))
        return super()._create(**request)


def sitting(answers):
    client = SlowClient(list(answers))
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1))
    return session, client


QUESTION = "休みの日って、みんな何してる？"
TIMED_OUT = "api_error:APITimeoutError"


# --- the limits ---

def test_the_limits_are_those_in_the_report():
    assert moderator.TIMEOUT_SECONDS == 60.0
    assert reflection.TIMEOUT_SECONDS == 45.0
    assert coach.TIMEOUT_SECONDS == 30.0
    assert librarian.TIMEOUT_SECONDS == 30.0 and librarian.TOTAL_SECONDS == 45.0
    assert closing.TIMEOUT_SECONDS == 30.0 and ask_seat.TIMEOUT_SECONDS == 30.0
    assert editor.TIMEOUT_SECONDS == 20.0 and subjects.TIMEOUT_SECONDS == 20.0
    assert gate.EFFORT["reflection"] == "medium"


def test_a_round_sends_every_request_with_its_limit_and_no_retry():
    session, client = sitting(ANSWERED)
    session.ask(QUESTION)
    assert client.options == [{"timeout": 30.0, "max_retries": 0}, {"timeout": 60.0, "max_retries": 0}]


# --- past the limit: the way each already has ---

def test_a_slow_moderator_ends_the_round_as_unavailable_and_the_question_can_be_sent_again():
    session, client = sitting([ANSWERED[0], Slow(61, ANSWERED[1])] + list(ANSWERED))
    view = session.ask(QUESTION)
    assert view["status"] == roundtable.UNAVAILABLE and view["message"] == load_text(MODEL_UNAVAILABLE)
    assert session.rounds[0].reason == TIMED_OUT
    assert session.ask(QUESTION)["status"] == roundtable.ANSWERED
    # Under the limit it is answered as always.
    session, _ = sitting([ANSWERED[0], Slow(59, ANSWERED[1])])
    assert session.ask(QUESTION)["status"] == roundtable.ANSWERED


def test_a_slow_librarian_ends_the_round_as_unavailable():
    session, _ = sitting([Slow(31, ANSWERED[0])])
    view = session.ask(QUESTION)
    assert view["status"] == roundtable.UNAVAILABLE and session.rounds[0].reason == TIMED_OUT


def test_the_librarians_requests_together_have_a_limit_too(monkeypatch):
    clock = iter([0.0, 0.0, 50.0])  # The search began; first request; the second, past 45 s.
    monkeypatch.setattr(librarian.time, "monotonic", lambda: next(clock))
    from fake_client import tool_response
    session, client = sitting([tool_response(("t1", "list_seats", {}))])
    view = session.ask(QUESTION)
    assert view["status"] == roundtable.UNAVAILABLE and session.rounds[0].reason == "timeout"
    assert len(client.requests) == 1


def test_the_last_word_of_the_wait_left_is_what_the_librarian_waits_at_most(monkeypatch):
    clock = iter([0.0, 0.0, 30.0])
    monkeypatch.setattr(librarian.time, "monotonic", lambda: next(clock))
    from fake_client import tool_response
    session, client = sitting([tool_response(("t1", "list_seats", {})), ANSWERED[0], ANSWERED[1]])
    session.ask(QUESTION)
    assert [o["timeout"] for o in client.options[:2]] == [30.0, 15.0]


def test_a_slow_reflection_gives_the_fixed_question_back():
    from test_reflection import reflection_says
    session, client = sitting(list(ANSWERED) + [Slow(46, reflection_says())])
    session.ask(QUESTION)
    view = session.reflect_begin("a_little", "休みをどう決めるかを知りたい")
    assert view["ask_back"] == load_text(ASK_BACK_FALLBACK)
    assert session.reflection.unavailable == TIMED_OUT and session.reflection.moves == []
    assert client.options[-1] == {"timeout": 45.0, "max_retries": 0}
    # The student goes on: one line, then the sheet.
    assert session.reflect_answer("町の人に聞いてみたい") == {"moves": []}


def test_a_slow_band_is_not_shown():
    session, client = sitting(list(ANSWERED) + [Slow(31)])
    session.ask(QUESTION)
    assert session.coach_band(1)["cards"] == []
    assert session.rounds[0].band.reason == TIMED_OUT


def test_a_slow_card_back_still_makes_the_card():
    session, client = sitting([librarian_finds(), Slow(21, editor_says(["S01"]))])
    view = session.ask(QUESTION)
    assert view["status"] == roundtable.SILENT and view["card"]["text"] == QUESTION
    assert session.cards[0].back.reason == TIMED_OUT
    assert client.options[-1] == {"timeout": 20.0, "max_retries": 0}


def test_a_slow_last_word_shows_nothing():
    from test_closing import says
    from test_closing import sitting as closing_sitting
    client_answers = list(ANSWERED) + [Slow(31, says(("a9", "x")))]
    session, client = closing_sitting([])
    session.gate.client = SlowClient(client_answers)
    session.ask(QUESTION)
    view = session.close_round(1)
    assert view["words"] == [] and session.rounds[0].closing.reason == TIMED_OUT
    assert session.gate.client.options[-1] == {"timeout": 30.0, "max_retries": 0}


def test_a_slow_seat_asked_shows_the_fixed_sentence():
    from test_ask_seat import PIECES
    from test_closing import sitting as closing_sitting
    session, _ = closing_sitting([], kinds={}, pieces=PIECES)
    session.gate.client = SlowClient(list(ANSWERED) + [librarian_finds("b7"), Slow(31)])
    session.ask(QUESTION)
    if session.ask_card(1)["card"] is None:
        pytest.skip("no card for this round")
    asked = session.ask_the_seat(1)
    assert asked["status"] == ask_seat.UNAVAILABLE and asked["message"] == load_text(MODEL_UNAVAILABLE)


def test_a_slow_subject_model_lets_the_clue_words_pick():
    from test_subjects import WORDS, catalog, says
    client = SlowClient([Slow(21, says("札1", 1))])
    pick = subjects.choose(Gate(client, NameList.build(SEATS, {})), catalog(), "quest", WORDS, Counter())
    assert pick.model_error == TIMED_OUT and pick.source == subjects.SOURCE_CODE
    assert client.options == [{"timeout": 20.0, "max_retries": 0}]
