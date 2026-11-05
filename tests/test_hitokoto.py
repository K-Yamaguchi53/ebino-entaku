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
from ebino.prompts import LISTENER
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
    assert session.hitokoto_choose(1, "")["next"] == "chosen"  # The whole card.


def test_omakase_is_picked_by_code_the_first_lit_part():
    session, model, _, _ = sitting()
    session.hitokoto_parts()
    view = session.hitokoto_choose(None, "", omakase=True)
    assert view["omakase"] and view["person"] == 0 and view["part"] == "休みは空いたら取ります"
    assert model.kinds() == ["parts"]  # No request to pick.


def test_only_the_lit_part_can_be_pressed():
    session, _, _, _ = sitting()
    session.hitokoto_parts()
    with pytest.raises(Refused):
        session.hitokoto_choose(0, "天気しだい")










# --- 段7: the switch, the roles, texts ---



# The card's label 「聞き手（AI・町の人ではありません）」, from the sample, holds
# the lure form 「ではありません」; it is a label over the AI's card, not a
# question. Left as the teacher wrote it, and only the lures are excused
# (the teacher is asked about it in the report).
LABEL_NOT_A_QUESTION = ("who_ai",)


def _fixed_sentences() -> list[tuple[str, str]]:
    return list(WORDS.items())


@pytest.mark.parametrize("key, text", _fixed_sentences())
def test_every_fixed_sentence_added_to_texts_passes_the_banned_words_and_the_lures(key, text):
    assert not banned_in(text)
    if key in LABEL_NOT_A_QUESTION:
        return
    body = normalize_for_match(text)
    assert not any(normalize_for_match(lure) in body for lure in LURE_FORMS)




