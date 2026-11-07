"""帰る前に、ひとこと (直し38): the reflection rebuilt as the teacher's sample.
Every record, seat and word here is invented; the model is a fake one."""

import json
import random

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME
from ebino import app as app_module
from ebino import hitokoto
from ebino.banned_words import banned_in
from ebino.coach import LURE_FORMS
from ebino.gate import MODELS, EFFORT, Gate, NameList
from ebino.harvest import MOVES_PREFIX
from ebino.ingest.scrub import normalize_for_match
from ebino.prompts import LIGHT, LISTENER
from ebino.records import Records
from ebino.session import Refused, Session
from ebino.texts import NAME_IN_QUESTION, TEXTS_DIR, load_lines, load_text
from test_session import SEATS, SPLIT, librarian_finds, library, moderator_says

QUESTION = "休みの日って、みんな何してる？"
WORDS = hitokoto.words()
ROUND_QUOTES = [("a1", "休みは決めて取ります。"), ("a2", "月曜は必ず店を閉める。"),
                ("b1", "畑は天気しだいなので、休みは空いたら取ります。")]
REACTION_Q = "「休みは空いたら取ります」を読んで、最初に浮かんだことは？"
SELF_Q = "「空いたら取る」と書いたね。その人の話の、どこが自分にも重なる？"
LIGHT_OK = {"quote": "空いたら取る", "force": 2, "why": "農家の人の話を、自分の休みの取り方につなげて書いた。つなげる力そのもの。",
            "deep": "「休みは空いたら取ります」の先、天気で決まる一日の中身。"}


class Model:
    """The fake model: the round's requests in order, then the listener and
    the light by their own instruction. Each answer may be a value, an
    Exception, or a function of the data sent."""

    def __init__(self, split=True, parts=None, reaction=REACTION_Q, self_q=SELF_Q, light=None):
        quotes = moderator_says(ROUND_QUOTES, [SPLIT] if split else [], silent=["S03"])
        self.round = [librarian_finds("a1", "a2", "b1"), quotes]
        self.parts = parts if parts is not None else {"parts": [{"id": "1", "part": "休みは空いたら取ります"},
                                                                  {"id": "2", "part": "決めて取ります"}]}
        self.answers = {"reaction": reaction, "self": self_q}
        self.light = light if light is not None else dict(LIGHT_OK)
        self.sent: list[tuple[str, dict]] = []

    def __call__(self, request):
        system = request["system"][0]["text"]
        if not system.startswith(("あなたは「聞き手」", "あなたは、高校生が円卓のあとに")):
            return self.round.pop(0)
        data = json.loads(request["messages"][0]["content"])
        if system.startswith("あなたは「聞き手」"):
            kind = "parts" if data["task"] == "keywords" else data["direction"]
            value = self.parts if kind == "parts" else self.answers[kind]
            if isinstance(value, str):
                value = {"question": value}
        else:
            kind, value = "light", self.light
        self.sent.append((kind, data))
        if callable(value) and not isinstance(value, dict):
            value = value(data)
        if isinstance(value, Exception):
            raise value
        return text_response(value)

    def kinds(self) -> list[str]:
        return [kind for kind, _ in self.sent]


def sitting(model=None, tmp_path=None, mark="b1", opened=("a1",)):
    model = model or Model()
    client = FakeClient(model)
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.ask(QUESTION)
    if mark:
        session.mark(1, mark)
    view = session.hitokoto_begin(list(opened))
    return session, model, client, view


def to_scale(session):
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    session.hitokoto_answer("空いたら取るのがいいと思った")
    return session.hitokoto_answer("部活がない日は空いたら休む")


def to_end(session, scale=8, forward="先輩にもう一回聞く", way="農業", subject="no", notice="not_yet"):
    session.hitokoto_scale(scale)
    session.hitokoto_forward(forward)
    session.hitokoto_notice(notice)  # 直し49 段1: 今日の気づき, after the scale's next question.
    session.hitokoto_way(way)
    session.hitokoto_subject(subject)
    if subject == "yes":
        session.hitokoto_subject_note("家庭科")
    return session.hitokoto_meet("")


# --- 段1: today's map ---

def test_the_map_shows_the_marked_person_first_then_the_bubble_opened_with_their_own_words():
    session, _, _, view = sitting()
    people = view["people"]
    assert [p["seat_id"] for p in people] == ["S02", "S01"]
    assert people[0]["text"] == "畑は天気しだいなので、休みは空いたら取ります。"  # The mark, as recorded.
    assert people[1]["text"] == "休みは決めて取ります。"  # The bubble opened.
    assert view["first_question"] == QUESTION and view["stage"] == "map"
    assert view["counts"] == {"people": 2, "marks": 1, "cards": 0}


def test_the_split_joins_one_person_from_each_side_and_puts_them_at_the_samples_first_two_places():
    _, _, _, view = sitting()
    split = view["split"]
    assert split["heading"] == '休みを"決めて取る"人と"空いたら取る"人'  # ここで割れた： taken off.
    a, b = view["people"][split["a"]], view["people"][split["b"]]
    assert {a["seat_id"], b["seat_id"]} == {"S01", "S02"}
    assert (a["x"], a["y"]) == hitokoto.SLOTS[0] and (b["x"], b["y"]) == hitokoto.SLOTS[1]


def test_with_no_split_there_is_no_dashed_line_and_no_heading():
    _, _, _, view = sitting(Model(split=False))
    assert view["split"] is None


def test_the_map_holds_three_people_at_most_marks_then_one_to_one_then_bubbles():
    session, _, _, _ = sitting(opened=())
    session.talk = None
    session.marks = {"S01": "a1"}
    session.one_asked = {"S03": []}
    talk = hitokoto.begin(session, ["b1", "a2"], lambda h: h)
    # S03 was at one to one but nothing was asked there: no card, so not on the map.
    assert [p.seat_id for p in talk.people] == ["S01", "S02"]
    assert [p.why for p in talk.people] == ["mark", "bubble"]
    assert len(hitokoto.pick_people(session, ["b1", "a1", "a2"])) <= hitokoto.MAX_PEOPLE


def test_parts_light_only_where_the_card_holds_them_word_for_word():
    parts = {"parts": [{"id": "1", "part": "休みは空いたら取ります"}, {"id": "2", "part": "休みは自由に取ります"}]}
    session, _, client, _ = sitting(Model(parts=parts))
    assert session.hitokoto_parts() == {"parts": {"0": "休みは空いたら取ります"}}
    assert client.options[-1]["timeout"] == hitokoto.LISTENER_SECONDS


def test_a_part_longer_than_sixteen_characters_is_not_lit_and_parts_are_asked_once():
    parts = {"parts": [{"id": "1", "part": "畑は天気しだいなので、休みは空いたら取ります"}]}
    session, model, _, _ = sitting(Model(parts=parts))
    assert session.hitokoto_parts() == {"parts": {}}
    session.hitokoto_parts()
    assert model.kinds() == ["parts"]


def test_parts_not_back_in_time_leave_the_whole_cards_to_press():
    session, _, _, _ = sitting(Model(parts=TimeoutError()))
    assert session.hitokoto_parts() == {"parts": {}}
    assert session.talk.parts_reason == "api_error:TimeoutError"
    assert session.hitokoto_choose(1, "")["next"] == "ask"  # The whole card.


def test_omakase_is_picked_by_code_the_first_lit_part():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    view = session.hitokoto_choose(None, "", omakase=True)
    assert view["omakase"] and view["person"] == 0 and view["part"] == "休みは空いたら取ります"
    assert model.kinds() == ["parts", "reaction"]  # No request to pick.


def test_only_the_lit_part_can_be_pressed():
    session, _, _, _ = sitting()
    session.hitokoto_parts()
    with pytest.raises(Refused):
        session.hitokoto_choose(0, "天気しだい")


# --- 段2: the listener's two directions ---

def test_the_two_directions_come_in_order_and_neither_is_asked_twice():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    assert session.hitokoto_choose(0, "休みは空いたら取ります")["question"] == REACTION_Q
    assert session.hitokoto_answer("空いたら取るのがいいと思った")["question"] == SELF_Q
    view = session.hitokoto_answer("部活がない日は空いたら休む")
    assert view == {"next": "scale", "question": WORDS["scale_q"]}
    assert model.kinds() == ["parts", "reaction", "self"]
    assert [a.step for a in session.talk.asked] == ["reaction", "self", "scale"]
    # The self question is sent the answer just written.
    assert model.sent[2][1]["answer"] == "空いたら取るのがいいと思った"


def test_dont_know_once_asks_the_same_question_again_without_the_model():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    view = session.hitokoto_answer("", dont_know=True)
    assert view == {"next": "again", "note": "だいじょうぶ。ひとことでいいよ。", "question": REACTION_Q}
    assert model.kinds() == ["parts", "reaction"]
    assert session.hitokoto_answer("わからない。")["next"] == "ladder_two"  # Typed counts too.


def test_dont_know_twice_turns_to_the_ladder_and_a_blank_written_goes_back_to_the_next_direction():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    session.hitokoto_answer("", dont_know=True)
    two = session.hitokoto_answer("ない")
    assert two["question"] == "2人の言葉。自分に近いのは、どっち？"
    three = session.hitokoto_ladder(two["options"][0]["index"])
    assert three["question"] == WORDS["ladder_three"] and len(three["options"]) == 2
    fill = session.hitokoto_ladder(1)
    assert fill["question"] == WORDS["ladder_fill"]
    assert fill["before"] == "理容師の話の、" and fill["after"] == "のところが近いと思った。"
    back = session.hitokoto_fill("決めて取る")
    # 「空いたら取る」 is in no card and was never written by the student here:
    # only the split's heading held it, and that is the moderator's words, not
    # the student's (直し40-2), so the listener's question gives way to the fixed one.
    assert back == {"next": "ask", "question": WORDS["ask_self"]}
    assert session.hitokoto_answer("店を閉める日を決めたい")["next"] == "scale"
    talk = session.talk
    assert talk.listener_asked == 2 and talk.ladder_shown == 3
    assert talk.question_count() == hitokoto.MAX_QUESTIONS
    assert model.kinds() == ["parts", "reaction", "self"]


def test_the_ladder_is_made_from_the_record_and_texts_only():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "休みは空いたら取ります")
    session.hitokoto_answer("", dont_know=True)
    sent = len(model.sent)
    two = session.hitokoto_answer("", dont_know=True)
    assert {o["text"] for o in two["options"]} == {"休みは決めて取ります。", "畑は天気しだいなので、休みは空いたら取ります。"}
    three = session.hitokoto_ladder(two["options"][1]["index"])
    assert {o["title"] for o in three["options"]} == {"理容師", "農家"}
    session.hitokoto_ladder(0)
    assert len(model.sent) == sent  # No model for any of the ladder.


def test_with_no_split_the_ladder_skips_the_two():
    session, _, _, _ = sitting(Model(split=False))
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    session.hitokoto_answer("", dont_know=True)
    assert session.hitokoto_answer("", dont_know=True)["next"] == "ladder_three"


def test_with_one_person_on_the_map_the_ladder_goes_to_the_blank_line():
    session, _, _, view = sitting(opened=())
    assert len(view["people"]) == 1
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    session.hitokoto_answer("", dont_know=True)
    fill = session.hitokoto_answer("", dont_know=True)
    assert fill["next"] == "fill" and fill["before"] == "農家の話の、"
    assert session.hitokoto_fill("", skip=True)["next"] == "scale"  # Left empty: on to the scale.


def test_with_no_one_on_the_map_it_goes_to_the_scale_and_on_to_the_end():
    session, model, _, view = sitting(mark=None, opened=())
    assert view["people"] == [] and view["stage"] == "scale" and view["question"] == WORDS["scale_q"]
    to_end(session, forward="", way="")
    light = session.hitokoto_light()
    assert light["quote"] == QUESTION and light["source"] == "first"  # Nothing else to stand on.
    assert model.kinds() == []  # Nothing written: no light request.


def test_the_ladder_is_shown_once_a_sitting():
    session, _, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    session.hitokoto_answer("", dont_know=True)
    session.hitokoto_answer("", dont_know=True)
    session.hitokoto_ladder(0)
    session.hitokoto_ladder(0)
    session.hitokoto_fill("天気しだい")
    session.hitokoto_answer("", dont_know=True)
    assert session.hitokoto_answer("", dont_know=True)["next"] == "scale"
    assert session.talk.ladder_shown == 3


QUESTION_STOPS = [
    ("「休みは自由に取る」を読んで、最初に思ったことは？", "quote_not_in_record"),
    ("谷口さんの言葉を読んで、最初に思ったことは？", "name"),
    ("休みを決めて取るべきだと思った？", "banned_word"),
    ("休みは空いたら取るほうが楽だと思わない？", "lure_form"),
    ("休みを決めるのと空いたら取るのと、それとも別の形？", "lure_form"),
    ("あなたは決めて取るタイプ？", "banned_word"),
    ("あなたは決めて取る人？", "you_are"),
    ("家族と休みの日に何をしている？", "avoid_word"),
    ("お金がかかる休みと、かからない休みは？", "avoid_word"),
    ("「休みは空いたら取ります」を読んで、" + "最初に心に浮かんだことや思い出したことや気づいたことは" * 2 + "？", "too_long"),
    ("「休みは空いたら取ります」を読んで、最初に思ったこと。", "not_one_question"),
    ("最初に思ったことは？ 次に思ったことは？", "not_one_question"),
    ("なぜそう思ったのか、どう感じた？", "question_words"),
]


@pytest.mark.parametrize("text, reason", QUESTION_STOPS)
def test_a_listener_question_that_fails_a_check_becomes_the_fixed_one(text, reason):
    session, _, _, _ = sitting(Model(reaction=text))
    session.hitokoto_parts()
    view = session.hitokoto_choose(0, "休みは空いたら取ります")
    assert view["question"] == "「休みは空いたら取ります」を読んで、最初に思ったことは？"
    assert session.talk.asked[0].by == "fixed" and session.talk.asked[0].fallback == reason


def test_a_listener_question_past_eight_seconds_becomes_the_fixed_one():
    session, _, client, _ = sitting(Model(reaction=TimeoutError()))
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    asked = session.talk.asked[0]
    assert asked.by == "fixed" and asked.fallback == "api_error:TimeoutError"
    assert asked.text == "「畑は天気しだいなので、休みは空いたら取ります」を読んで、最初に思ったことは？"
    assert client.options[-1] == {"timeout": hitokoto.LISTENER_SECONDS, "max_retries": 0}


def test_the_self_question_is_fixed_and_not_sent_the_answer_when_it_is_of_home_or_money():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    view = session.hitokoto_answer("家族が休みの日に働いている")
    assert view["question"] == WORDS["ask_self"]
    assert session.talk.asked[-1].fallback == hitokoto.STUDENT_AVOID
    assert model.kinds() == ["parts", "reaction"]  # Not sent.


def test_a_name_in_the_students_words_is_neither_sent_nor_kept(tmp_path):
    session, model, client, _ = sitting(tmp_path=tmp_path)
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    sent = len(client.requests)
    view = session.hitokoto_answer("谷口さんの話がよかった")
    assert view == {"status": "ask_again", "message": load_text(NAME_IN_QUESTION)}
    assert len(client.requests) == sent and session.talk.written == []
    kept = (tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")
    assert "谷口" not in kept
    for step in (lambda: session.hitokoto_answer("森川さんみたいに"),):
        assert step()["status"] == "ask_again"


# --- 段3: the scale ---

@pytest.mark.parametrize("value, key", [(8, "scale_down"), (10, "scale_same"), (13, "scale_up")])
def test_the_scale_answer_picks_the_teachers_next_question(value, key):
    session, _, _, _ = sitting()
    to_scale(session)
    assert session.hitokoto_scale(value)["question"] == WORDS[key]


def test_the_scale_is_zero_to_fifteen():
    session, _, _, _ = sitting()
    to_scale(session)
    for value in (-1, 16, "8", True):
        with pytest.raises(Refused):
            session.hitokoto_scale(value)


# --- 段4: what to keep, and the harvest card's ② and ③ ---

def test_the_subject_card_comes_only_after_yes():
    session, _, _, _ = sitting()
    to_scale(session)
    session.hitokoto_scale(10)
    session.hitokoto_forward("", skip=True)
    session.hitokoto_notice("no_answer")
    session.hitokoto_way("", skip=True)
    assert session.hitokoto_subject("no") == {"next": "meet"}
    with pytest.raises(Refused):
        session.hitokoto_subject_note("家庭科")
    other, _, _, _ = sitting()
    to_scale(other)
    other.hitokoto_scale(10)
    other.hitokoto_forward("", skip=True)
    other.hitokoto_notice("no_answer")
    other.hitokoto_way("", skip=True)
    assert other.hitokoto_subject("yes") == {"next": "subject_note"}
    view = other.hitokoto_subject_note("家庭科")
    assert view["next"] == "meet" and "subject" in view  # None with no catalog: no ③ to show.


def test_the_subject_card_is_asked_with_the_question_and_the_lessons_name(monkeypatch):
    from ebino import subjects
    seen = {}

    def choose(gate, catalog, lab, words, counts):
        seen.update(words)
        return subjects.Pick(subjects.STATUS_OFF)

    monkeypatch.setattr(subjects, "choose", choose)
    session, _, _, _ = sitting()
    to_scale(session)
    to_end(session, subject="yes")
    assert seen == {"question": QUESTION, "answer": "家庭科", "move": ""}


def test_the_meet_line_comes_only_when_a_seat_is_picked_and_the_first_line_never():
    session, _, _, _ = sitting()
    to_scale(session)
    assert to_end(session) == {"uses": []}
    with pytest.raises(Refused):
        session.hitokoto_use("none")
    other, _, _, _ = sitting()
    to_scale(other)
    other.hitokoto_scale(8)
    other.hitokoto_forward("", skip=True)
    other.hitokoto_notice("no_answer")
    other.hitokoto_way("", skip=True)
    other.hitokoto_subject("unsure")
    uses = other.hitokoto_meet("S02")["uses"]
    assert uses and all(set(u) == {"force", "name", "text"} for u in uses)
    line = other.hitokoto_use(uses[0]["force"])["meet"]
    assert line.startswith(load_text("harvest_meet_prefix") + "農家")
    everything = json.dumps([other.hitokoto_light(), other.hitokoto_sheet("")], ensure_ascii=False)
    assert MOVES_PREFIX not in everything and MOVES_PREFIX not in line


# --- 段5: today's light ---

def test_the_light_quotes_the_students_own_words_and_ties_them_to_one_force():
    session, model, client, _ = sitting()
    to_scale(session)
    to_end(session)
    light = session.hitokoto_light()
    assert light["quote"] == "空いたら取る" and light["force"] == "② つなげる力"
    assert light["why"] == LIGHT_OK["why"] and light["deep"] == LIGHT_OK["deep"]
    assert session.talk.light.by == "model"
    assert client.options[-1]["timeout"] == hitokoto.LIGHT_SECONDS
    sent = model.sent[-1][1]
    assert [w["step"] for w in sent["written"]] == ["reaction", "self", "forward", "way"]
    assert sent["chosen"] == "" and len(sent["forces"]) == 6
    assert session.hitokoto_light() == light and model.kinds().count("light") == 1  # Asked once.


def test_a_forces_name_alone_in_quotes_passes_and_is_shown_without_them():
    why = "人の話を、自分の休みにつなげた。「つなげる力」そのもの。"
    session, _, _, _ = sitting(Model(light=dict(LIGHT_OK, why=why)))
    to_scale(session)
    to_end(session)
    assert session.hitokoto_light()["why"] == "人の話を、自分の休みにつなげた。つなげる力そのもの。"


@pytest.mark.parametrize("change, reason", [
    ({"quote": "休みは自由に取る"}, "quote_not_written"),
    ({"quote": "休みは決めて取ります。"}, "quote_not_written"),  # A person's words, not the student's.
    ({"force": 7}, "unknown_force"),
    ({"why": "あなたは人の話をつなげる人。つなげる力。"}, "you_are"),
    ({"why": "すばらしい。つなげる力が出ている。"}, "banned_word"),
    ({"why": "いいね、つなげる力が出ている。"}, "praise"),
    ({"why": "自分の休みにつなげて書いた。合わせる力の形。"}, "force_not_named"),
    ({"deep": "「休みは好きに取る」の先を深める。"}, "quote_not_in_record"),
    ({"deep": "家族と休む日の決め方。"}, "avoid_word"),
])
def test_a_light_that_fails_a_check_is_picked_by_code_in_the_samples_order(change, reason):
    session, _, _, _ = sitting(Model(light=dict(LIGHT_OK, **change)))
    to_scale(session)
    to_end(session, scale=8)
    light = session.hitokoto_light()
    assert session.talk.light.by == "code" and session.talk.light.reason == reason
    # Down from 10 with words written: the longest of the answers, ② and its fixed sentence.
    assert light["quote"] == "空いたら取るのがいいと思った"
    assert light["why"] == hitokoto.force_sentences()[2]
    assert light["deep"] == "農家の「休みは空いたら取ります」の先。その人はどうやってそこにたどり着いたのか。"


def test_code_picks_in_the_samples_order():
    talk = hitokoto.Hitokoto(QUESTION)
    assert code_quote(talk) == (QUESTION, 1, "first")
    talk.scale, talk.forward = 13, "何をしたいかが増えた"
    talk.written = [{"step": "forward", "text": talk.forward}]
    assert code_quote(talk) == ("何をしたいかが増えた", 5, "written")
    talk.scale, talk.way = 10, "農業"
    talk.written.append({"step": "way", "text": "農業"})
    assert code_quote(talk) == ("農業", 2, "written")
    talk.way, talk.written = "", talk.written[:1]
    assert code_quote(talk) == ("何をしたいかが増えた", 4, "written")


def code_quote(talk):
    light = hitokoto.code_light(talk, "test")
    return light.quote, light.force, light.source


def test_the_light_never_stands_on_steps_everyone_takes_and_the_first_question_only_when_nothing_else():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    session.hitokoto_answer("", dont_know=True)
    session.hitokoto_answer("", dont_know=True)
    session.hitokoto_ladder(session.talk.split["b"])  # 農家 (b1's side).
    session.hitokoto_ladder(0)
    session.hitokoto_fill("", skip=True)
    to_end(session, scale=10, forward="", way="")
    model.light = dict(LIGHT_OK, quote="休みは空いたら取ります")
    light = session.hitokoto_light()
    # Nothing written: the words picked at the ladder's 2択, shown as picked.
    sent = model.sent[-1][1]
    assert sent["written"] == [] and sent["chosen"] == "畑は天気しだいなので、休みは空いたら取ります。"
    assert light["source"] == "chosen" and light["chosen_who"] == "農家" and light["quote"] == "休みは空いたら取ります"
    for step in ("pressed", "bubble", "mark", "opened"):
        assert step not in json.dumps(sent, ensure_ascii=False)


def test_the_next_step_is_shown_under_the_light_when_the_doubt_went_down_or_stayed():
    session, _, _, _ = sitting()
    to_scale(session)
    to_end(session, scale=8)
    assert session.hitokoto_light()["next_step"] == "先輩にもう一回聞く"
    other, _, _, _ = sitting()
    to_scale(other)
    to_end(other, scale=12, forward="何をしたいかが増えた")
    assert other.hitokoto_light()["next_step"] == ""


def test_stop_here_goes_to_the_light_at_once():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    session.hitokoto_choose(0, "")
    session.hitokoto_answer("空いたら取る日が好き")
    light = session.hitokoto_light()
    assert session.talk.stage == "lit" and light["scale"] is None
    with pytest.raises(Refused):
        session.hitokoto_answer("もう一つ")


# --- 段6: the sheet ---

def test_the_sheet_reads_in_order_from_the_record_and_the_students_words(tmp_path):
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_scale(session)
    to_end(session, subject="yes")
    session.hitokoto_light()
    sheet = session.hitokoto_sheet("休みの決め方で、仕事はどう変わる？")
    story = "".join(part["text"] for part in sheet["story"])
    assert story == ("農家・理容師の話を聞いた。農家の「休みは空いたら取ります」が引っかかった。"
                     "そこで「空いたら取るのがいいと思った」と書いた。迷いは10から8へ。"
                     "頭に置いておきたい進み方は「農業」。授業とつながった話もあった（家庭科）。")
    assert [p["text"] for p in sheet["story"] if p["strong"]] == [
        "「休みは空いたら取ります」", "「空いたら取るのがいいと思った」", "「農業」"]
    assert sheet["now_question"] == "休みの決め方で、仕事はどう変わる？"
    assert sheet["light"] == {"quote": "空いたら取る", "why": LIGHT_OK["why"]}
    assert sheet["next_step"] == "先輩にもう一回聞く"


def test_the_sheet_and_the_record_hold_no_name(tmp_path, monkeypatch):
    monkeypatch.setenv("EBINO_SHOW_COMPANY", "1")
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_scale(session)
    session.hitokoto_scale(8)
    session.hitokoto_forward("先輩にもう一回聞く")
    session.hitokoto_notice("no_answer")
    session.hitokoto_way("農業")
    session.hitokoto_subject("no")
    session.hitokoto_meet("S01")
    session.hitokoto_use("none")
    shown = json.dumps([session.hitokoto_light(), session.hitokoto_sheet("")], ensure_ascii=False)
    kept = (tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")
    for name in (COMPANY, DISPLAY_NAME, "山川", "谷口", "森川", "架空農園"):
        assert name not in shown and name not in json.dumps(json.loads(kept)["hitokoto"], ensure_ascii=False)


def test_the_record_keeps_the_questions_and_why_a_fixed_one_was_used(tmp_path):
    session, _, _, _ = sitting(Model(reaction="あなたは決めて取る人？"), tmp_path=tmp_path)
    to_scale(session)
    to_end(session)
    session.hitokoto_light()
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = record["hitokoto"]
    assert kept["asked"][0]["by"] == "fixed" and kept["asked"][0]["fallback"] == "you_are"
    assert "あなたは決めて取る人" not in json.dumps(record, ensure_ascii=False)  # Failed words are not kept.
    assert kept["asked"][1]["text"] == SELF_Q and kept["asked"][1]["by"] == "listener"
    assert kept["scale"] == 8 and kept["way"] == "農業"
    assert kept["light"]["quote"] == "空いたら取る" and kept["light"]["force"] == 2 and kept["light"]["by"] == "model"
    assert record["reflection"] is None


# --- 段7: the switch, the roles, texts ---

def test_the_old_reflection_comes_back_with_ebino_reflect_old(monkeypatch):
    session, _, _, _ = sitting()
    assert app_module.App(library(), session.gate).setup()["reflect"] == "hitokoto"
    monkeypatch.setenv("EBINO_REFLECT", "old")
    assert app_module.App(library(), session.gate).setup()["reflect"] == "old"
    with pytest.raises(Refused):
        session.hitokoto_parts()
    other = Session(library(), session.gate, rng=random.Random(1))
    with pytest.raises(Refused):
        other.hitokoto_begin([])


def test_the_new_api_has_a_path_for_each_step():
    for step in ("begin", "parts", "choose", "answer", "ladder", "fill", "scale", "forward", "way", "subject",
                 "subject_note", "subject_choose", "subject_more", "meet", "use", "light", "sheet"):
        assert f'"{step}":' in (app_module.Path(app_module.__file__)).read_text(encoding="utf-8")


def test_the_listener_and_the_light_use_their_own_models_and_low_effort():
    assert (MODELS["listener"], EFFORT["listener"]) == ("claude-haiku-5-5", "low")
    assert (MODELS["light"], EFFORT["light"]) == ("claude-sonnet-5-5", "low")
    session, _, client, _ = sitting()
    to_scale(session)
    to_end(session)
    session.hitokoto_light()
    models = [r["model"] for r in client.requests[2:]]
    assert models == ["claude-haiku-5-5"] * 3 + ["claude-sonnet-5-5"]
    assert all(r["output_config"]["effort"] == "low" for r in client.requests[2:])
    assert client.requests[2]["system"][0]["text"].startswith(LISTENER.split("\n")[0])
    assert client.requests[-1]["system"][0]["text"].startswith(LIGHT.split("\n")[0])


def test_nothing_sent_to_the_listener_or_the_light_holds_a_name():
    session, _, client, _ = sitting()
    to_scale(session)
    to_end(session)
    session.hitokoto_light()
    sent = json.dumps(client.requests[2:], ensure_ascii=False)
    for name in (COMPANY, DISPLAY_NAME, "山川", "谷口", "森川", "架空農園"):
        assert name not in sent


# The card's label 「聞き手（AI・町の人ではありません）」, from the sample, holds
# the lure form 「ではありません」; it is a label over the AI's card, not a
# question. Left as the teacher wrote it, and only the lures are excused
# (the teacher is asked about it in the report).
LABEL_NOT_A_QUESTION = ("who_ai",)


def _fixed_sentences() -> list[tuple[str, str]]:
    return list(WORDS.items()) + [(f"force_{n}", s) for n, s in hitokoto.force_sentences().items()]


@pytest.mark.parametrize("key, text", _fixed_sentences())
def test_every_fixed_sentence_added_to_texts_passes_the_banned_words_and_the_lures(key, text):
    assert not banned_in(text)
    if key in LABEL_NOT_A_QUESTION:
        return
    body = normalize_for_match(text)
    assert not any(normalize_for_match(lure) in body for lure in LURE_FORMS)


def test_the_force_sentences_hold_their_forces_name_out_of_quotes():
    for number, sentence in hitokoto.force_sentences().items():
        assert hitokoto.FORCE_WORDS[number] in sentence and "「" not in sentence


def test_the_sixth_force_is_this_screens_and_harvests_five_stay():
    from ebino import harvest
    assert hitokoto.FORCES[6] == "⑥ 創り出す力" and 6 not in harvest.FORCES
    assert all(hitokoto.FORCES[n] == harvest.FORCES[n] for n in range(1, 6))


def test_dont_know_words_and_the_listeners_avoid_words_are_in_texts():
    assert "わからない" in load_lines("hitokoto_blank") and hitokoto.is_blank("特にない。")
    assert not hitokoto.is_blank("わからないけど、決めて取りたい")
    assert load_lines("listener_avoid") == ["家庭", "家族", "親", "お金", "家計", "病気", "体調"]
    assert (TEXTS_DIR / "hitokoto.tsv").exists()
