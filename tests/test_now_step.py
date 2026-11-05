"""The step the round is at, for the sign in the middle of the map (直し42
段2): find (the librarian), moderate (the moderator), speak (the bubbles as
spoken words; none when that is off), as the server really goes into each.
Asked by GET /api/now_step, which does not wait for the round's lock and
gives the step's name and nothing else. Invented data, a fake model held at
each request by a threading.Event."""

import http.client
import json
import random
import threading
import time

import pytest
from fake_client import FakeClient, text_response

from ebino import roundtable
from ebino.app import NOW_STEP, App, make_server
from ebino.gate import Gate, NameList
from test_session import ANSWERED, SEATS, library


class Held:
    """A fake model whose n-th request waits until let(n)."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.entered = [threading.Event() for _ in range(4)]
        self.gates = [threading.Event() for _ in range(4)]
        self.client = FakeClient(self._answer)

    def _answer(self, request):
        n = len(self.client.requests) - 1
        self.entered[n].set()
        assert self.gates[n].wait(10)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def let(self, n):
        self.gates[n].set()


@pytest.fixture
def held():
    return Held(ANSWERED)


@pytest.fixture
def server(held):
    the_app = App(library(), Gate(held.client, NameList.build(SEATS, {})), rng=random.Random(1))
    server = make_server(the_app, 0, timeout=5)
    server.the_app = the_app
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    for gate in held.gates:
        gate.set()
    server.shutdown()
    server.server_close()


def request(server, method, path, body=None, timeout=10):
    port = server.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    headers = {"Host": f"127.0.0.1:{port}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=data, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    return response.status, json.loads(raw)


def step_now(server):
    began = time.monotonic()
    status, data = request(server, "GET", NOW_STEP, timeout=2)
    return status, data, time.monotonic() - began


def asking(server, question="休みは？"):
    out = {}
    thread = threading.Thread(target=lambda: out.update(answer=request(server, "POST", "/api/ask",
                                                                         {"question": question})), daemon=True)
    thread.start()
    return thread, out


def test_no_sitting_yet_is_an_empty_step(server):
    assert request(server, "GET", NOW_STEP) == (200, {"step": ""})


def test_while_the_round_waits_the_step_comes_back_at_once_and_only_its_name(server, held):
    request(server, "POST", "/api/start", {"lab": "quest"})
    assert request(server, "GET", NOW_STEP) == (200, {"step": ""})
    thread, out = asking(server)
    assert held.entered[0].wait(5)  # The librarian is asked, and held.
    status, data, took = step_now(server)
    assert (status, data) == (200, {"step": "find"}) and took < 1
    assert not held.entered[1].is_set()  # The moderator is not asked yet: its step is not said.
    held.let(0)
    assert held.entered[1].wait(5)  # The moderator is asked, and held.
    status, data, took = step_now(server)
    assert (status, data) == (200, {"step": "moderate"}) and took < 1
    held.let(1)
    thread.join(10)
    assert out["answer"][0] == 200 and out["answer"][1]["status"] == "answered"
    assert request(server, "GET", NOW_STEP) == (200, {"step": ""})


def test_the_spoken_words_are_a_step_only_when_they_are_asked_for(server, held, monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "1")
    held.answers.append(text_response({"lines": []}))
    request(server, "POST", "/api/start", {"lab": "quest"})
    seen = []
    the_app = server.the_app
    real = the_app.set_step
    monkeypatch.setattr(the_app, "set_step", lambda name: (seen.append(name), real(name)))
    the_app.session.on_step = the_app.set_step
    thread, out = asking(server)
    held.let(0)
    held.let(1)
    assert held.entered[2].wait(5)  # The speaker is asked, and held.
    assert step_now(server)[1] == {"step": "speak"}
    held.let(2)
    thread.join(10)
    assert out["answer"][0] == 200
    assert seen == ["", "find", "moderate", "speak", ""]
    assert request(server, "GET", NOW_STEP)[1] == {"step": ""}


def test_with_the_speaker_off_there_is_no_speak_step(server, held, monkeypatch):
    request(server, "POST", "/api/start", {"lab": "quest"})
    seen = []
    the_app = server.the_app
    the_app.session.on_step = lambda name: (seen.append(name), the_app.set_step(name))
    held.let(0)
    held.let(1)
    assert request(server, "POST", "/api/ask", {"question": "休みは？"})[0] == 200
    assert seen == ["", "find", "moderate", ""]


def test_after_a_failure_the_step_is_empty(server, held):
    held.answers[0] = RuntimeError("the model is out")
    request(server, "POST", "/api/start", {"lab": "quest"})
    thread, out = asking(server)
    assert held.entered[0].wait(5)
    assert step_now(server)[1] == {"step": "find"}
    held.let(0)
    thread.join(10)
    assert out["answer"][1]["status"] == "unavailable"
    assert request(server, "GET", NOW_STEP)[1] == {"step": ""}
    # A question refused before any step: empty, and never a step it did not go into.
    assert request(server, "POST", "/api/ask", {"question": ""})[0] == 400
    assert request(server, "GET", NOW_STEP)[1] == {"step": ""}


def test_a_name_in_the_question_goes_into_no_step(server, held):
    request(server, "POST", "/api/start", {"lab": "quest"})
    seen = []
    the_app = server.the_app
    the_app.session.on_step = lambda name: (seen.append(name), the_app.set_step(name))
    status, view = request(server, "POST", "/api/ask", {"question": "山川さんの休みは？"})
    assert status == 200 and view["status"] == roundtable.ASK_AGAIN
    assert set(seen) == {""} and not held.entered[0].is_set()


def test_the_answer_to_an_ai_question_goes_through_the_same_steps(held):
    # session.coach_answer runs the same round: its steps are said the same way.
    from types import SimpleNamespace

    from ebino.session import Refused, Session
    seen = []
    session = Session(library(), Gate(held.client, NameList.build(SEATS, {})), rng=random.Random(1),
                      on_step=seen.append)
    held.let(0)
    held.let(1)
    session.ask("休みは？")
    assert seen == ["", "find", "moderate", ""]
    # The round's two AI questions, as coach.run would leave them (no model here).
    session.rounds[0].band = SimpleNamespace(answered=None, answer=None,
                                             cards=[SimpleNamespace(role="coach", text="休みは決めて取る？")])
    held.answers += list(ANSWERED)
    held.let(2)
    held.let(3)
    seen.clear()
    view = session.coach_answer(1, "coach", "決めて取るほうに近い")
    assert view["status"] == "answered"
    assert seen == ["find", "moderate", ""]
    # A refusal on the way in says no step.
    seen.clear()
    with pytest.raises(Refused):
        session.coach_answer(1, "coach", "もう一度")  # Already answered.
    assert seen == []


def test_the_step_is_never_a_question_words_or_a_seat():
    # Only these names, set in code; the page gets a name or "".
    assert roundtable.STEPS == ("find", "moderate", "speak")
