"""直し53b: the switch the morning's comparison stands on, checked first
(EBINO_HITOKOTO_VOICE: unset or "ai" the two, "listener" the listener for
both questions), the line at start saying which, room for every request of
one sitting at once, and the prompts kept one at a time while some are asked
ahead in threads. Every seat, word and answer here is invented; the model is
a fake one."""

import random
import threading
import time

import pytest
from fake_client import FakeClient

from ebino import hitokoto
from ebino.app import App
from ebino.gate import Gate, NameList
from test_hitokoto_ai_53 import SOURCES, Model, sitting
from test_session import SEATS, library


@pytest.mark.parametrize("value, voice", [("", "ai"), ("ai", "ai"), ("listener", "listener"), (" Listener ", "listener"),
                                          ("coach", "ai")])
def test_the_switch_reads_the_environment(monkeypatch, value, voice):
    monkeypatch.setenv("EBINO_HITOKOTO_VOICE", value)
    assert hitokoto.voice() == voice


def test_with_the_listener_both_questions_are_the_listeners(monkeypatch):
    monkeypatch.setenv("EBINO_HITOKOTO_VOICE", "listener")
    model = Model()
    session = sitting(model)
    session.hitokoto_parts()
    first = session.hitokoto_choose(0, "休みは空いたら取ります")
    second = session.hitokoto_answer("空いたら取るのがいいと思った")
    assert "who" not in first and "who" not in second
    assert [asked.by for asked in session.talk.asked] == [hitokoto.LISTENER, hitokoto.LISTENER]
    assert model.ai() == [] and session.hitokoto_ahead == {}


def test_by_default_both_questions_are_the_twos(monkeypatch):
    monkeypatch.delenv("EBINO_HITOKOTO_VOICE", raising=False)
    model = Model()
    session = sitting(model)
    session.hitokoto_parts()
    first = session.hitokoto_choose(0, "休みは空いたら取ります")
    second = session.hitokoto_answer("空いたら取るのがいいと思った")
    assert (first["who"], second["who"]) == ("observer", "coach")
    assert [asked.by for asked in session.talk.asked] == ["observer", "coach"]
    assert {data["role"] for data in model.ai()} == {"observer", "coach"}


def test_the_line_at_start_says_who_puts_them(monkeypatch):
    lib = library()
    lib.coach_on, lib.coach_sources = True, list(SOURCES)
    monkeypatch.delenv("EBINO_HITOKOTO_VOICE", raising=False)
    assert hitokoto.voice_report(lib).startswith("hitokoto questions: observer (reaction), coach (self)")
    monkeypatch.setenv("EBINO_HITOKOTO_VOICE", "listener")
    assert hitokoto.voice_report(lib) == "hitokoto questions: listener (EBINO_HITOKOTO_VOICE=listener)"
    monkeypatch.delenv("EBINO_HITOKOTO_VOICE")
    lib.coach_sources = []
    assert hitokoto.voice_report(lib) == "hitokoto questions: observer (reaction), listener (self: no coach pieces)"
    lib.coach_on = False
    assert hitokoto.voice_report(lib) == "hitokoto questions: listener (coach band off)"


def test_room_for_every_request_of_one_sitting():
    # Three asked as the map comes, three again with the lit parts, the student's own.
    assert hitokoto.AHEAD_WORKERS >= 3 + 3 + 1
    assert hitokoto._AHEAD._max_workers == hitokoto.AHEAD_WORKERS


class SlowRecords:
    """Counts as Records does (read, add one, write), slowly enough that two
    threads at once would take the same number without the app's lock."""

    def __init__(self):
        self.count = 0
        self.numbers = []

    def save_prompt(self, session_id, role, request):
        number = self.count + 1
        time.sleep(0.002)
        self.count = number
        self.numbers.append(number)


def test_prompts_kept_from_threads_take_their_own_numbers():
    records = SlowRecords()
    app = App(library(), Gate(FakeClient([]), NameList.build(SEATS, {})), records, rng=random.Random(1))
    app.session = type("Sitting", (), {"session_id": "s1"})()
    threads = [threading.Thread(target=app._on_send, args=("coach", {})) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(records.numbers) == [1, 2, 3, 4, 5, 6]
