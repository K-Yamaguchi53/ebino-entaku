"""直し53 段9 (the teacher, 11/7: 最後まで質を高めたい。妥協はしたくない):
帰る前に、ひとこと's two questions are put by the round table's two AIs:
reaction by オブザーバー（AI）, self by コーチ（AI）, in the same order (no
choosing). They read what the table's two read (every round today, コーチ the
coach's pieces), the words picked and their card, the answer before, and
what the two asked at the table (asked_before). The same model as at the
table. reaction is asked ahead for the people on the map; past AI_SECONDS,
or failing the listener's checks, the fixed question, its reason a code.
EBINO_HITOKOTO_VOICE=listener: the listener as before. Every seat, word and
answer here is invented; the model is a fake one."""

import json
import random
import threading
import time

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME
from ebino import coach, hitokoto
from ebino.gate import MODELS, Gate, NameList
from ebino.prompts import COACH, HITOKOTO_AI, LISTENER
from ebino.records import Records
from ebino.session import Session
from test_hitokoto import QUESTION, REACTION_Q, ROUND_QUOTES, SELF_Q, WORDS
from test_session import SEATS, SPLIT, librarian_finds, library, moderator_says

SOURCES = ["（架空）問いは、答えより先に立てる。"]
TABLE = {"coach": "身の回りで、休みを自分で決めた場面は？", "observer": "休みの話で、まだ聞いていない人はだれ？"}
OBSERVER_Q = "「休みは空いたら取ります」を読んで、最初に浮かんだことは？"
COACH_Q = "「空いたら取る」と書いたね。身の回りで、その人の話と重なる場面は？"


def _first_line(prompt):
    return prompt.split("\n")[0]


class Model:
    """The round (librarian, moderator), the table's two, the listener's
    parts, and the two's questions here, each by its own instruction."""

    def __init__(self, observer=OBSERVER_Q, coach_q=COACH_Q, delay=0.0):
        self.round = [librarian_finds("a1", "a2", "b1"), moderator_says(ROUND_QUOTES, [SPLIT], silent=["S03"])]
        self.answers = {"observer": observer, "coach": coach_q}
        self.delay = delay
        self.sent: list[tuple[str, dict, str]] = []
        self.lock = threading.Lock()

    def __call__(self, request):
        system = request["system"][0]["text"]
        if system.startswith(_first_line(COACH)):
            return text_response(TABLE)
        if system.startswith(_first_line(HITOKOTO_AI)):
            data = json.loads(request["messages"][0]["content"])
            with self.lock:
                self.sent.append(("ai", data, request["model"]))
            if self.delay:
                time.sleep(self.delay)
            value = self.answers[data["role"]]
            if isinstance(value, Exception):
                raise value
            return text_response({"question": value})
        if system.startswith(_first_line(LISTENER)):
            data = json.loads(request["messages"][0]["content"])
            with self.lock:
                self.sent.append(("listener", data, request["model"]))
            if data["task"] == "keywords":
                return text_response({"parts": [{"id": "1", "part": "休みは空いたら取ります"}]})
            return text_response({"question": REACTION_Q if data["direction"] == "reaction" else SELF_Q})
        return self.round.pop(0)

    def ai(self):
        with self.lock:
            return [data for kind, data, _ in self.sent if kind == "ai"]


@pytest.fixture
def ai_voice(monkeypatch):
    monkeypatch.delenv("EBINO_HITOKOTO_VOICE", raising=False)  # The default: the two.


def sitting(model, tmp_path=None):
    lib = library()
    lib.coach_on, lib.coach_sources = True, list(SOURCES)
    session = Session(lib, Gate(FakeClient(model), NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.ask(QUESTION)
    session.coach_band(1)  # The table's two, as the screen asks for them.
    session.mark(1, "b1")
    session.hitokoto_begin(["a1"])
    return session


def _wait_for(check, seconds=5.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end and not check():
        time.sleep(0.02)


def test_the_two_put_the_two_questions_by_their_names(ai_voice, tmp_path):
    model = Model()
    session = sitting(model, tmp_path)
    session.hitokoto_parts()
    first = session.hitokoto_choose(0, "休みは空いたら取ります")
    assert first["question"] == OBSERVER_Q and first["who"] == "observer"
    second = session.hitokoto_answer("空いたら取るのがいいと思った")
    assert second == {"next": "ask", "question": COACH_Q, "who": "coach"}
    talk = session.talk
    assert [(a.step, a.by, a.who) for a in talk.asked[:2]] == [("reaction", "observer", "observer"), ("self", "coach", "coach")]
    # The screen's names: as at the round table.
    words = hitokoto.screen_words()
    assert words["who_observer"] == coach.ai_label(coach.OBSERVER) == "オブザーバー（AI）"
    assert words["who_coach"] == coach.ai_label(coach.COACH) == "コーチ（AI）"
    # The record keeps what it kept (by, a reason code), never more.
    kept = json.loads((tmp_path / next(p.name for p in tmp_path.iterdir() if p.suffix == ".json")).read_text(encoding="utf-8")) \
        if any(p.suffix == ".json" for p in tmp_path.iterdir()) else None
    if kept:
        assert "hitokoto_ahead" not in json.dumps(kept, ensure_ascii=False)


def test_they_read_every_round_asked_before_and_coach_its_pieces(ai_voice):
    model = Model()
    session = sitting(model)
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    session.hitokoto_answer("空いたら取るのがいいと思った")
    sent = model.ai()
    reaction = next(d for d in sent if d["direction"] == "reaction" and d["chosen"] == "休みは空いたら取ります")
    self_ = next(d for d in sent if d["direction"] == "self")
    for data in (reaction, self_):
        assert len(data["rounds"]) == len(session.rounds) == 1 and data["rounds"][0]["question"] == QUESTION
        assert data["rounds"][0]["quotes"] and data["first_question"] == QUESTION
        assert data["asked_before"] == [{"role": "coach", "text": TABLE["coach"]}, {"role": "observer", "text": TABLE["observer"]}]
        assert data["card"] == session.talk.people[0].text
    assert reaction["role"] == "observer" and "coach_sources" not in reaction and reaction["answer"] == ""
    assert self_["role"] == "coach" and self_["coach_sources"] == SOURCES and self_["answer"] == "空いたら取るのがいいと思った"
    # The same model as at the table.
    assert {m for k, _, m in model.sent if k == "ai"} == {MODELS[coach.ROLE]}


def test_reaction_is_asked_ahead_and_the_pick_takes_that_persons(ai_voice):
    model = Model()
    session = sitting(model)
    # As the map came: one for each person on it (at most three).
    people = len(session.talk.people)
    _wait_for(lambda: len(model.ai()) >= min(3, people))
    assert {d["card"] for d in model.ai()} == {p.text for p in session.talk.people[:3]}
    session.hitokoto_parts()
    _wait_for(lambda: len(model.ai()) >= min(3, people) + 1)
    before = len(model.ai())
    asked = session.hitokoto_choose(0, "休みは空いたら取ります")
    assert asked["question"] == OBSERVER_Q
    assert len(model.ai()) == before  # The one asked ahead, not one more.
    assert ((0, "休みは空いたら取ります") in session.hitokoto_ahead)


def test_past_the_wait_the_fixed_question_and_its_reason(ai_voice, monkeypatch):
    monkeypatch.setattr(hitokoto, "AI_SECONDS", 0.2)
    model = Model(delay=1.0)
    session = sitting(model)
    session.hitokoto_parts()
    session.talk.parts.clear()  # Picked words asked for at the pick (none ahead for them).
    started = time.monotonic()
    asked = session.hitokoto_choose(0, "")
    assert time.monotonic() - started < 0.9
    talk = session.talk
    assert asked["question"] == hitokoto.fixed_question("reaction", talk) and asked["who"] == "observer"
    assert (talk.asked[-1].by, talk.asked[-1].fallback) == ("fixed", hitokoto.STOP_WAIT)
    assert hitokoto.AI_SECONDS == 0.2 and hitokoto.AI_REQUEST_SECONDS >= 20


def test_the_wait_is_twenty_seconds():
    assert hitokoto.AI_SECONDS == 20.0


@pytest.mark.parametrize("bad", ["あなたは休みを大事にする人？", "休みは決めて取るほうがいいよね？", "休みの話。どう思った", "「休みは月曜」を読んで、何を思った？"])
def test_a_question_failing_the_checks_is_the_fixed_one(ai_voice, bad):
    model = Model(observer=bad)
    session = sitting(model)
    session.hitokoto_parts()
    asked = session.hitokoto_choose(0, "休みは空いたら取ります")
    talk = session.talk
    assert asked["question"] == hitokoto.fixed_question("reaction", talk)
    assert talk.asked[-1].by == "fixed" and talk.asked[-1].fallback  # A code, never the words.
    assert bad not in json.dumps(talk.record(), ensure_ascii=False)


def test_the_listener_as_before_when_asked(monkeypatch):
    monkeypatch.setenv("EBINO_HITOKOTO_VOICE", "listener")
    model = Model()
    session = sitting(model)
    session.hitokoto_parts()
    asked = session.hitokoto_choose(0, "休みは空いたら取ります")
    assert asked["question"] == REACTION_Q and "who" not in asked
    assert model.ai() == [] and session.hitokoto_ahead == {}
    assert session.talk.asked[-1].by == hitokoto.LISTENER


def test_no_name_goes_to_the_model(ai_voice):
    model = Model()
    session = sitting(model)
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    session.hitokoto_answer("空いたら取るのがいいと思った")
    sent = json.dumps(model.ai(), ensure_ascii=False)
    for name in (DISPLAY_NAME, COMPANY):
        assert name not in sent


def test_the_instruction_keeps_the_tables_rules():
    for rule in ("「なぜ」「どうして」は使わない", "経験があることを前提にしない", "引用（chosen・card・rounds の quotes）を手がかりに問う",
                 "asked_before と同じ問い・同じ形の問いをくり返さない", "{observer_view}", "{banned}", "{abstract}"):
        assert rule in HITOKOTO_AI
    system = hitokoto.ai_system()
    assert "{" not in system.replace("{{", "").replace('{"question"', "")
    # The keywords stay the listener's (Haiku).
    assert MODELS[hitokoto.LISTENER] != MODELS[coach.ROLE]
