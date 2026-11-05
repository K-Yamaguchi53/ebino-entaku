"""直し34-4: at one to one, each time up to three questions of the items not
asked yet, those with words only, in the teacher's order (an article's
rows, a poster's roles, the axes the teacher's table gives the pages); a
question picked shows that item's own words (as spoken words where the
speaker's checks let them through); a question the student writes is
looked for among this seat's words only. What was asked is kept by item
name only."""

import random

import pytest
from conftest import make_seat
from fake_client import FakeClient

from ebino import librarian, session as session_module
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance
from ebino.librarian import Found
from ebino.session import Library, Refused, Session

SEATS = [make_seat(seat_id="A01", kind="adult", title="理容師", company="", display_name=""),
         make_seat(seat_id="P01", kind="poster", title="探究の先輩（架空）", company="", display_name="", district=""),
         make_seat(seat_id="C01", kind="cross", title="県外に出た人（架空）", company="", display_name="", district=""),
         make_seat(seat_id="C02", kind="cross", title="県外に出た人（架空2）", company="", display_name="", district="")]


def _u(seat, kind, section, text, n=0, voice="article"):
    return Utterance(id=f"{seat}-{section}-{n}", seat_id=seat, kind=kind, section=section, voice=voice,
                     text=text, paragraph=text)


UTTERANCES = [
    _u("A01", "adult", "キャッチコピー", "架空の一行。"),
    _u("A01", "adult", "プロフィール", "町で生まれて、店を継ぎました。"),
    _u("A01", "adult", "仕事の内容", "髪を切って、話を聞きます。"),
    _u("A01", "adult", "本文タイトル", "休みは決めて取る"),
    _u("A01", "adult", "本文", "休みは決めて取ります。"),
    _u("A01", "adult", "ランキング", "一番は川です。"),
    _u("A01", "adult", "高校生に一言", "迷ったら、やってみて。"),
    _u("P01", "poster", "目的", "川の色を確かめたかった。", voice="own"),
    _u("P01", "poster", "結果", "季節で色が変わった。", voice="own"),
    _u("C01", "cross", "p1", "向こうに行こうと決めた。", voice="own"),
    _u("C01", "cross", "p2", "向こうでは驚いた。", voice="own"),
    _u("C02", "cross", "p1", "ページの言葉。", voice="own"),
]


class Kept:
    def __init__(self):
        self.sessions = []

    def save_session(self, record):
        self.sessions.append(record)

    def save_prompt(self, *args):
        pass


@pytest.fixture
def sitting(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")  # The words as recorded here (the speaker has its own tests).
    lib = Library.build(SEATS, UTTERANCES, {})
    lib.ask_tables = {"pages": {"C01": {"p1": ["行く前"], "p2": ["向こうで", "これから"]}},
                      "ranking": {"A01": "架空のランキングの質問ですか？"}}
    kept = Kept()
    s = Session(lib, Gate(FakeClient([]), NameList.build(SEATS, {})), rng=random.Random(1), records=kept)
    return s, kept


def test_the_items_with_words_in_the_teachers_order(sitting):
    s, _ = sitting
    assert [item for item, _, _ in s.one_items("A01")] == ["プロフィール", "仕事の内容", "本文", "ランキング", "高校生に一言"]
    # 本文タイトル and 本文 one item; the catch copy none; the ranking with the teacher's own question.
    body = dict((item, pieces) for item, _, pieces in s.one_items("A01"))["本文"]
    assert [u.section for u in body] == ["本文タイトル", "本文"]
    assert dict((item, q) for item, q, _ in s.one_items("A01"))["ランキング"] == "架空のランキングの質問ですか？"
    assert [item for item, _, _ in s.one_items("P01")] == ["目的", "結果"]
    assert [item for item, _, _ in s.one_items("C01")] == ["行く前", "向こうで", "これから"]
    assert s.one_items("C02") == []  # No row in the teacher's table: nothing to offer.


def test_three_at_a_time_of_those_not_asked_then_done(sitting):
    s, kept = sitting
    view = s.one_view("A01")
    assert [q["item"] for q in view["questions"]] == ["プロフィール", "仕事の内容", "本文"] and not view["done"]
    answer = s.one_ask("A01", "仕事の内容")
    assert answer["item"] == "仕事の内容" and answer["pieces"][0]["text"] == "髪を切って、話を聞きます。"
    assert [q["item"] for q in answer["questions"]] == ["プロフィール", "本文", "ランキング"]
    for item in ("プロフィール", "本文", "ランキング", "高校生に一言"):
        last = s.one_ask("A01", item)
    assert last["questions"] == [] and last["done"]
    # Kept by item name only, in the order asked.
    assert kept.sessions[-1]["one_to_one"] == [{"seat_id": "A01", "items": ["仕事の内容", "プロフィール", "本文", "ランキング",
                                                                          "高校生に一言"], "free_found": [], "thanked": False}]
    with pytest.raises(Refused):
        s.one_ask("A01", "キャッチコピー")


def test_fewer_than_three_and_none(sitting):
    s, _ = sitting
    assert len(s.one_view("P01")["questions"]) == 2
    assert s.one_view("C02") == {"seat_id": "C02", "questions": [], "done": False, "asked": []}


def test_a_written_question_is_looked_for_in_this_seats_words_only(sitting, monkeypatch):
    s, kept = sitting
    seen = {}

    def find(gate, entries, question, ai_question=""):
        seen["seats"] = {entry.seat_id for entry in entries}
        return Found(["A01-本文-0", "P01-目的-0"], "picked")

    monkeypatch.setattr(librarian, "find", find)
    found = s.one_free_question("A01", "休みはいつですか？")
    assert seen["seats"] == {"A01"}
    assert found["found"] and [p["text"] for p in found["pieces"]] == ["休みは決めて取ります。"]
    monkeypatch.setattr(librarian, "find", lambda *a, **k: Found([], "none"))
    assert s.one_free_question("A01", "好きな色は？")["found"] is False
    assert kept.sessions[-1]["one_to_one"][0]["free_found"] == [True, False]
    assert "好きな色" not in str(kept.sessions[-1]["one_to_one"])  # The written words are not kept here.
    with pytest.raises(Refused):
        s.one_free_question("A01", "")
