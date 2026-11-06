"""直し45 段3: at one to one, the questions to pick only; after the person's
words, one short question from コーチ（AI）, answered with the teacher's
choices. Every seat, piece and question here is invented; the model is fake."""

import json
import random
import threading

import pytest
from fake_client import FakeClient, text_response

from ebino import coach, hitokoto, texts
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.session import Library, Refused, Session
from test_one_to_one import SEATS, UTTERANCES, Kept

QUOTE = "「町で生まれて、店を継ぎました。」のは、なぜ？"  # A whole sentence of the words shown.


@pytest.fixture
def sitting(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")

    def make(answers):
        lib = Library.build(SEATS, UTTERANCES, {})
        lib.ask_tables = {"pages": {}, "ranking": {}}
        client = FakeClient(answers)
        kept = Kept()
        session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1), records=kept)
        return session, client, kept
    return make


def ask(answer):
    return text_response({"question": answer})


def run_coach(session, seat_id, ask_no):
    plan = session.one_coach_plan(seat_id, ask_no)
    if plan is None:
        return None
    text, reason = coach.one_send(session.gate, plan["request"])
    return session.one_coach_done(plan, text, reason)


def test_the_next_questions_come_at_once_and_the_coach_after(sitting):
    session, client, _ = sitting([ask("その人が店を継いだのは、なぜだと思う？")])
    answer = session.one_ask("A01", "プロフィール")
    assert client.requests == []  # Nothing waits for the coach.
    assert answer["questions"] and answer["coach"] == {"ask_no": 1}
    view = run_coach(session, "A01", 1)
    assert view["question"] == "その人が店を継いだのは、なぜだと思う？"
    assert view["label"] == "コーチ（AI）"
    assert client.options[-1] == {"timeout": 12.0, "max_retries": 0}
    assert coach.ONE_TIMEOUT_SECONDS == 12.0 and coach.TIMEOUT_SECONDS == 30.0


def test_the_choices_are_the_teachers_table_never_the_models(sitting):
    out = text_response({"question": "その人は、なぜそうしたと思う？", "choices": ["モデルの選択肢"]})
    session, _, _ = sitting([out])
    session.one_ask("A01", "プロフィール")
    view = run_coach(session, "A01", 1)
    table = texts.id_table(texts.ONE_COACH_CHOICES, texts.ONE_COACH_CHOICE_IDS)
    assert view["choices"] == [{"id": key, "text": text} for key, text in table.items()]
    assert "モデルの選択肢" not in json.dumps(view, ensure_ascii=False)


def test_what_the_model_is_given(sitting):
    session, client, _ = sitting([ask("その人は、なぜそうしたと思う？")])
    session.lab = "quest"
    session.one_ask("A01", "プロフィール")
    run_coach(session, "A01", 1)
    data = json.loads(client.requests[0]["messages"][0]["content"])
    assert data["direction"] == "outside" and data["words"] == ["町で生まれて、店を継ぎました。"]
    assert set(data) == {"direction", "words", "answers", "rounds"}  # No Lab, no subjects, no name.
    assert '"lab"' not in client.all_sent() and "Quest" not in client.all_sent()


@pytest.mark.parametrize("question, shown", [
    (QUOTE, True),  # The person's own sentence in 「」.
    ("「店を継いだ」のは、なぜ？", False),  # Not the words as they are.
    ("その人が店を継いだのは、どんな気持ちからだったと、あなたは思う？", False),  # Over 30 characters.
    ("その人の価値観は、どこから来たと思う？", False),  # An abstract word.
    ("自分の家族なら、どうすると思う？", False),  # Home.
    ("その人は、なぜそうしたと思いませんか？", False),  # A lure (the band's check).
])
def test_the_checks_at_one_to_one(sitting, question, shown):
    session, _, kept = sitting([ask(question)])
    session.one_ask("A01", "プロフィール")
    view = run_coach(session, "A01", 1)
    assert bool(view["question"]) is shown
    assert kept.sessions[-1]["one_coach"][0]["status"] == ("shown" if shown else "stopped")


def test_thirty_characters_and_abstract_words_stop_at_one_to_one_only(sitting):
    session, _, _ = sitting([])
    long = "その人が店を継いだのは、どんな気持ちからだったと、あなたは思う？"
    abstract = "その人の価値観は、どこから来たと思う？"
    record = coach.OneRecord(session, [], [])
    assert len(long) > 30
    assert coach.stop_reason(long, record, session.gate) == ""  # The band's checks let them through.
    assert coach.stop_reason(abstract, record, session.gate) == ""
    assert coach.one_stop_reason(long, record, session.gate) == coach.STOP_ONE_TOO_LONG
    assert coach.one_stop_reason(abstract, record, session.gate) == coach.STOP_ABSTRACT
    # The limits as before (tests/test_coach.py keeps its 60 and 61).
    assert coach.MAX_CHARS == 60 and hitokoto.MAX_QUESTION == 60 and coach.AI_QUESTION_MAX_CHARS == 30


def test_stopped_or_past_its_time_nothing_is_added(sitting):
    session, _, kept = sitting([TimeoutError("slow"), ask("")])
    session.one_ask("A01", "プロフィール")
    assert run_coach(session, "A01", 1)["question"] == ""
    session.one_ask("A01", "仕事の内容")
    assert run_coach(session, "A01", 2)["question"] == ""
    found = kept.sessions[-1]["one_coach"]
    assert [a["status"] for a in found] == ["unavailable", "stopped"]
    assert found[0]["reason"].startswith("api_error")


def test_the_next_question_picked_first_drops_the_coach(sitting):
    session, _, kept = sitting([ask("その人は、なぜそうしたと思う？")])
    session.one_ask("A01", "プロフィール")
    plan = session.one_coach_plan("A01", 1)
    session.one_ask("A01", "仕事の内容")  # Picked while the coach was asked.
    text, reason = coach.one_send(session.gate, plan["request"])
    assert session.one_coach_done(plan, text, reason)["question"] == ""
    assert kept.sessions[-1]["one_coach"][0]["status"] == "dropped"
    assert session.one_coach_plan("A01", 1) is None  # An old one is not asked for.


def test_three_at_most_and_never_the_same_way_twice(sitting):
    session, client, _ = sitting([ask("その人は、なぜそうしたと思う？"), ask("自分なら、どうすると思う？"),
                                  ask("その人は、何を見ていたと思う？")])
    items = ["プロフィール", "仕事の内容", "本文", "高校生に一言"]
    for number, item in enumerate(items, start=1):
        answer = session.one_ask("A01", item)
        if number <= 3:
            assert run_coach(session, "A01", number)["question"]
        else:
            assert answer["coach"] is None and session.one_coach_plan("A01", number) is None
    ways = [json.loads(r["messages"][0]["content"])["direction"] for r in client.requests]
    assert ways == ["outside", "inside", "outside"]


def test_an_answer_is_a_choice_a_line_or_none_and_kept(sitting):
    session, _, kept = sitting([ask("その人は、なぜそうしたと思う？"), ask("自分なら、どうすると思う？")])
    session.one_ask("A01", "プロフィール")
    run_coach(session, "A01", 1)
    with pytest.raises(Refused):
        session.one_coach_answer("A01", 1, "made_up", "")
    assert session.one_coach_answer("A01", 1, "new", "")["ok"]
    with pytest.raises(Refused):
        session.one_coach_answer("A01", 1, "know", "")  # Once.
    session.one_ask("A01", "仕事の内容")
    run_coach(session, "A01", 2)
    assert session.one_coach_answer("A01", 2, "", "", declined=True)["ok"]
    found = kept.sessions[-1]["one_coach"]
    assert [(a["choice"], a["declined"]) for a in found] == [("new", False), ("", True)]
    assert all("seat_id" in a and "time" not in json.dumps(a) for a in found)
    steps = [i for i in session.trail_view()["items"] if i["kind"] == "one_coach"]
    assert [(i["ai_label"], i["choice"], i["declined"]) for i in steps] == [
        ("コーチ（AI）", "考えたことがなかった", False), ("コーチ（AI）", "", True)]


def test_a_line_with_a_name_is_asked_again(sitting):
    from conftest import DISPLAY_NAME, make_seat
    session, _, kept = sitting([ask("その人は、なぜそうしたと思う？")])
    session.gate.names = NameList.build([*SEATS, make_seat(seat_id="X99")], {})
    session.one_ask("A01", "プロフィール")
    run_coach(session, "A01", 1)
    assert session.one_coach_answer("A01", 1, "know", f"{DISPLAY_NAME}の話")["status"] == "ask_again"
    assert DISPLAY_NAME not in json.dumps(kept.sessions[-1], ensure_ascii=False)


def test_thanks_at_any_time(sitting):
    session, _, _ = sitting([])
    session.one_ask("A01", "プロフィール")
    assert session.one_thanks("A01") == {"thanked": ["A01"]}


def test_the_model_is_asked_outside_the_lock(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    lib = Library.build(SEATS, UTTERANCES, {})
    lib.ask_tables = {"pages": {}, "ranking": {}}
    seen = {}

    def model(request):
        seen["locked"] = the_app.lock.locked()
        return ask("その人は、なぜそうしたと思う？")
    the_app = App(lib, Gate(FakeClient(model), NameList.build(SEATS, {})))
    the_app.handle("/api/start", {"lab": "quest"})
    answer = the_app.handle("/api/one/ask", {"seat_id": "A01", "item": "プロフィール"})
    view = the_app.handle("/api/one/coach", {"seat_id": "A01", "ask_no": answer["coach"]["ask_no"]})
    assert seen["locked"] is False and view["question"]
    assert the_app.handle("/api/one/coach_answer", {"seat_id": "A01", "ask_no": view["ask_no"], "choice": "know",
                                                    "note": ""})["ok"]
    assert isinstance(threading.Lock(), type(the_app.lock))
