"""直し40-2: 帰る前に、ひとこと and the split's heading. A question sent with
「聞く」 that is a split's heading word for word is the moderator's words,
not the student's; the first question sent after a split was pressed that
is not one (an answer to an AI's question aside) is the question rewritten
from it: the student's own words, the light's ground (⑤) when code picks,
the sheet's story says so, and the question held now starts as the last one
the student sent. Every record, seat and word here is invented; the model
is a fake one."""

import json
import random
from types import SimpleNamespace

from fake_client import FakeClient
from test_hitokoto import QUESTION, ROUND_QUOTES, Model
from test_session import SEATS, SPLIT, librarian_finds, library, moderator_says

from ebino import hitokoto
from ebino.gate import Gate, NameList
from ebino.reflection import Record
from ebino.session import Session

HEADING = SPLIT[0]  # 'ここで割れた：休みを"決めて取る"人と"空いたら取る"人'
REWRITTEN = "休みを決めて取る人は、いつ決めているの？"
WORDS = hitokoto.words()


def sitting(after=(), press=True, ai_answer=None, light=None):
    """A first question, the split pressed (or not), then the questions after,
    each a round (an answer to an AI's question when it is ai_answer), then
    帰る前に、ひとこと."""
    model = Model(light=light)
    for _ in [*after, *([ai_answer] if ai_answer else [])]:
        model.round += [librarian_finds("a1", "a2", "b1"), moderator_says(ROUND_QUOTES, [SPLIT], silent=["S03"])]
    client = FakeClient(model)
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1))
    session.ask(QUESTION)
    if press:
        session.press_split(1, 0)
    for question in after:
        session.ask(question)
    if ai_answer:
        session.ask(ai_answer)
        session.rounds[-1].ai_question = SimpleNamespace(role="coach", text="（架空）AI の問い")
    session.mark(1, "b1")
    session.hitokoto_begin(["a1"])
    return session, model


def test_the_heading_sent_as_it_is_is_not_the_students_words_and_the_rewritten_one_is():
    session, _ = sitting([HEADING, REWRITTEN])
    talk = session.talk
    words = hitokoto.Words(session, talk).record
    assert talk.own_questions == [REWRITTEN] and talk.rewritten == REWRITTEN and talk.heading_sent
    assert not words.holds(HEADING) and not words.holds("決めて取る\"人と")
    assert words.holds(REWRITTEN) and words.holds(QUESTION)
    assert HEADING not in hitokoto.student_words(talk) and REWRITTEN in hitokoto.student_words(talk)
    # The old reflection's record is as it was: every question and heading.
    assert HEADING in Record(session).own_words


def test_spaces_at_the_ends_aside_the_heading_word_for_word_is_the_heading():
    session, _ = sitting([f"  {HEADING} "])
    assert session.talk.own_questions == [] and session.talk.rewritten == "" and session.talk.heading_sent
    other, _ = sitting([HEADING + "？"])  # One mark more: the student's own.
    assert other.talk.rewritten == HEADING + "？"


def test_the_rewritten_question_is_the_first_after_a_split_pressed_and_never_an_answer_to_an_ai():
    session, _ = sitting([REWRITTEN, "二つ目の問い"])
    assert session.talk.rewritten == REWRITTEN
    not_pressed, _ = sitting([REWRITTEN], press=False)
    assert not_pressed.talk.rewritten == "" and not_pressed.talk.own_questions == [REWRITTEN]
    answered, _ = sitting([], ai_answer="決めて取るほうに近い")
    assert answered.talk.rewritten == "" and answered.talk.own_questions == []


def test_the_question_held_now_starts_as_the_last_the_student_sent_not_an_ai_answer_or_a_heading():
    session, _ = sitting([REWRITTEN, HEADING])
    assert session.hitokoto_light()["now_question"] == REWRITTEN
    answered, _ = sitting([REWRITTEN], ai_answer="決めて取るほうに近い")
    assert answered.hitokoto_light()["now_question"] == REWRITTEN
    first_only, _ = sitting([HEADING])
    assert first_only.hitokoto_light()["now_question"] == QUESTION


def test_the_light_is_sent_the_rewritten_question_and_not_the_heading():
    session, model = sitting([HEADING, REWRITTEN])
    session.hitokoto_light()
    sent = next(data for kind, data in model.sent if kind == "light")
    texts = [w["text"] for w in sent["written"]]
    assert REWRITTEN in texts and HEADING not in texts
    assert {"step": hitokoto.NEXT_QUESTION} == {k: v for k, v in sent["written"][0].items() if k == "step"}


def test_code_takes_the_rewritten_question_as_five_before_the_samples_fifth():
    # The light model out: code picks. Nothing written yet: the rewritten question first.
    session, _ = sitting([REWRITTEN], light=TimeoutError("preview"))
    light = session.hitokoto_light()
    assert light["quote"] == REWRITTEN and light["force"] == hitokoto.FORCES[5]
    assert light["why"] == WORDS["light_split"] == "割れたところから、次の問いを立てた。解き明かす力の入り口。"
    assert session.talk.light.by == "code"


def test_a_heading_pressed_or_sent_as_it_was_is_no_ground_for_the_light():
    for after in ([], [HEADING]):
        session, _ = sitting(after, light=TimeoutError("preview"))
        light = session.hitokoto_light()
        assert light["quote"] == QUESTION and light["source"] == "first", after


def test_the_rewritten_question_comes_after_the_samples_first_four():
    talk = hitokoto.Hitokoto(QUESTION, rewritten=REWRITTEN, way="農業もおもしろいかも")
    assert hitokoto.code_light(talk, "x").quote == "農業もおもしろいかも"  # 3: the way, as before.
    talk = hitokoto.Hitokoto(QUESTION, rewritten=REWRITTEN, written=[{"step": "reaction", "text": "決めて取りたい"}])
    assert hitokoto.code_light(talk, "x").quote == REWRITTEN  # Before 5: the longest written.


def _story(session):
    session.hitokoto_light()
    return "".join(part["text"] for part in session.hitokoto_sheet("")["story"])


def test_todays_story_says_rewritten_or_asked_again_or_nothing():
    new = _story(sitting([HEADING, REWRITTEN])[0])
    assert "割れたところから、次の問いを立てた。" in new and "割れたところを、もう一度聞いた。" not in new
    same = _story(sitting([HEADING])[0])
    assert "割れたところを、もう一度聞いた。" in same and "次の問いを立てた" not in same
    for after, press in (([], True), ([REWRITTEN], False)):
        neither = _story(sitting(after, press=press)[0])
        assert "割れたところ" not in neither, (after, press)


def test_the_new_words_are_the_teachers_and_pass_the_checks():
    assert WORDS["story_split_new"] == "割れたところから、次の問いを立てた。"
    assert WORDS["story_split_same"] == "割れたところを、もう一度聞いた。"
    # The banned words and the lures: test_hitokoto checks every row of texts/hitokoto.tsv.
    from test_hitokoto import _fixed_sentences
    keys = {key for key, _ in _fixed_sentences()}
    assert {"light_split", "story_split_new", "story_split_same", "to_light"} <= keys


def test_the_record_keeps_what_it_kept():
    session, _ = sitting([HEADING, REWRITTEN])
    session.hitokoto_light()
    kept = json.dumps(session.talk.record(), ensure_ascii=False)
    assert "own_questions" not in kept and "rewritten" not in kept and "heading_sent" not in kept


def test_the_old_reflection_has_none_of_this():
    from ebino import reflection
    source = open(reflection.__file__, encoding="utf-8").read()
    assert "split_questions" not in source and "student_words" not in source and "light_split" not in source
