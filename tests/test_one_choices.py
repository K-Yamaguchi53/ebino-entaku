"""直し48 段3 (the teacher, 11/7: 「何から始める？」 and 「わかる／ちょっと
ちがう…」 do not go together): コーチ（AI）'s question at one to one is asked
in a form the choices can answer, and the set of choices is chosen by code
from the question's form; a question asking for an answer has no choice
that does not fit (まだわからない only, the line to write in first)."""

import json

import pytest

from conftest import make_seat
from ebino import one_choices, prompts, texts
from ebino.app import App, STATIC_DIR
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance
from ebino.session import Library, Refused
from fake_client import FakeClient, text_response

SEATS = [make_seat(seat_id="A01", title="理容師")]
UTTERANCES = [Utterance(id="u1", seat_id="A01", kind="adult", section="プロフィール", voice="article",
                        text="町で生まれて、店を継ぎました。", paragraph="町で生まれて、店を継ぎました。")]
MAP = (STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (STATIC_DIR / "style.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("question, form", [
    # The teacher's own example, and a question word inside it: can.
    ("目標への道が分からないとき、何から始めればいいかイメージできる？", one_choices.CAN),
    ("自分ならどうするか、イメージできる？", one_choices.CAN),
    ("その人がそうしたわけが、想像できそう？", one_choices.CAN),
    ("どこかで、休みを自分で決めたことある？", one_choices.DID),  # 「どこか」 asks nothing.
    ("何かを続けたことがある？", one_choices.DID),
    ("その人の話は、自分にも重なると思う？", one_choices.THINK),
    # Asking with 何・どう・どこ・だれ・いつ・なぜ・どれ: an answer, not a choice.
    ("自分なら、目標への道が分からないとき、何から始める？", one_choices.OPEN),
    ("その人は、なぜそうしてきたと思う？", one_choices.OPEN),
    ("自分なら、どうすると思う？", one_choices.OPEN),
    ("いつ、それを決めたことがある？", one_choices.OPEN),
    ("だれの話が、いちばん近いと思う？", one_choices.OPEN),
    ("どれを選んだことがある？", one_choices.OPEN),
    # None of the three forms: no choice that may not fit.
    ("休みの日は好き？", one_choices.OPEN),
    # A quote of the person's is not read for the form.
    ("「何でもやってみる」の話、イメージできる？", one_choices.CAN),
    ("「なぜ続けるのか」と聞かれたことがある？", one_choices.DID),
])
def test_the_form_decides_the_set(question, form):
    assert one_choices.form(question) == form


def test_each_set_and_its_words():
    table = texts.id_table(texts.ONE_COACH_CHOICES, texts.ONE_COACH_CHOICE_IDS)
    words = lambda q: [c["text"] for c in one_choices.choices(q)]
    assert words("何から始めればいいか、イメージできる？") == ["できる", "ちょっとできる", "まだできない"]
    assert words("休みを自分で決めたことある？") == ["ある", "まだない"]
    assert words("自分にも重なると思う？") == ["わかる", "ちょっとちがう", "考えたことがなかった", "まだわからない"]
    assert words("何から始める？") == ["まだわからない"]
    assert all(c["text"] == table[c["id"]] for q in ("できる？", "何？") for c in one_choices.choices(q))
    # 答えない is the board's own, always there (texts/one_coach_words.tsv).
    assert texts.id_table(texts.ONE_COACH_WORDS, texts.ONE_COACH_WORD_IDS)["decline"] == "答えない"


def _session(question):
    lib = Library.build(SEATS, UTTERANCES, {})
    lib.ask_tables = {"pages": {}, "ranking": {}}
    the_app = App(lib, Gate(FakeClient(lambda request: text_response({"question": question})), NameList.build(SEATS, {})))
    the_app.handle("/api/start", {"lab": "quest"})
    answer = the_app.handle("/api/one/ask", {"seat_id": "A01", "item": "プロフィール"})
    view = the_app.handle("/api/one/coach", {"seat_id": "A01", "ask_no": answer["coach"]["ask_no"]})
    return the_app, view


def test_the_board_gets_the_set_for_its_question_and_only_those_are_taken(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    the_app, view = _session("その人がそうしたわけが、イメージできる？")
    assert [c["id"] for c in view["choices"]] == ["can", "some", "cannot"]
    with pytest.raises(Refused):  # A choice of another set is not this question's.
        the_app.session.one_coach_answer("A01", view["ask_no"], "know", "")
    assert the_app.handle("/api/one/coach_answer", {"seat_id": "A01", "ask_no": view["ask_no"], "choice": "some",
                                                    "note": ""})["ok"]


def test_a_question_asking_for_an_answer_takes_a_line_and_no_choice_that_does_not_fit(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    the_app, view = _session("自分なら、何から始める？")
    assert [c["id"] for c in view["choices"]] == ["unsure"]
    assert the_app.handle("/api/one/coach_answer", {"seat_id": "A01", "ask_no": view["ask_no"], "choice": "",
                                                    "note": "まず人に聞く"})["ok"]
    kept = the_app.session.one_coach["A01"][0]
    assert kept["choice"] == "" and kept["note"] == "まず人に聞く"
    # On the board: the line and its 「答える」 first, then まだわからない and 答えない.
    ask = MAP[MAP.index("  async function askCoach(mine, askNo) {"):MAP.index("  // The coach's board gone")]
    assert "if (view.choices.length <= 1) {" in ask and 'answer.textContent = words.send;' in ask
    assert 'board.replaceChildren(head, question, div("one-coach-write"), choices, said);' in ask
    assert ".one-coach-write { grid-column: 1 / -1; grid-row: 3;" in CSS
    assert ".one-coach.open-form .one-coach-choices { grid-row: 4; }" in CSS


def test_the_prompt_asks_for_a_form_the_choices_answer():
    # Added to ONE_COACH (直し48 段3); the core (the person's words as they are) as before.
    assert "文の終わりを「〜イメージできる？」「〜と思う？」「〜したことある？」のどれかにする。" in prompts.ONE_COACH
    assert "「何・どう・どこ・だれ・いつ・なぜ・どれ」で答えを聞く形" in prompts.ONE_COACH
    assert "その人の言葉は、いつも本人の元の言葉のままです。" in prompts.ONE_COACH
    # Its examples are of the forms asked for.
    for line in prompts.ONE_COACH.splitlines():
        if line.startswith(("- outside：", "- inside：")):
            assert one_choices.form(line.split("：", 1)[1]) != one_choices.OPEN, line
    json.dumps(prompts.ONE_COACH)
