"""The round's last word, 「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A).
Every seat, piece and table here is invented."""

import json
import random
from pathlib import Path

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino import closing
from ebino.closing import load_hasshin_pages, to_students
from ebino.gate import Gate, NameList
from ebino.ingest.seats import load_seats
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.texts import CLOSING_LABEL, CLOSING_QUESTION, load_text
from test_session import ANSWERED, SEATS, UTTERANCES, librarian_finds, moderator_says, u

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
QUESTION = "休みの日って、みんな何してる？"

MORE_SEATS = [
    make_seat(seat_id="T01", kind="poster", title="生活文化科の先輩（架空の実習）", company="", display_name="先輩",
              source_file="talks/T01.pdf"),
    make_seat(seat_id="O02", kind="outsider_teacher", title="先生（架空）", company="", display_name="",
              source_file="teacher01.docx"),
]
ALL_SEATS = SEATS + MORE_SEATS
TO_STUDENTS = [
    u("a9", "S01", "地元にも、面白い仕事はたくさんあります。休みの日も、町を歩いてみてください。",
      voice="spoken", section="高校生に一言"),
    u("a8", "S01", "1位　朝の店の静けさ", section="ランキング"),
    u("b9", "S02", "畑は毎日ちがう顔をします。", voice="senior", section="先輩社員からのメッセージ"),
    u("p9", "P01", "川は町の鏡だと分かった。これからも調べ続けたい。", voice="own", kind="poster",
      section="結論と展望", heading="結論と展望"),
    u("p8", "P01", "次は上流でも測りたい。", voice="own", kind="poster", section="結果", heading="考察と今後の展望"),
    u("t2", "T01", "実習では、朝の仕込みから入りました。", voice="own", kind="poster", section="p2"),
    u("t3", "T01", "高校生のみなさんへ。\n地域の中に、学びの場はあります。", voice="own", kind="poster", section="p3"),
    u("o9", "O02", "迷う時間も、大事な時間です。", voice="own", kind="outsider_teacher", section="高校生に一言"),
    u("o8", "O02", "1位　朝の読書", voice="own", kind="outsider_teacher", section="ランキング"),
]
PAGES = {"T01": frozenset({3})}


def says(*picks):
    return text_response({"picks": [{"utterance_id": i, "text": t} for i, t in picks]})


def sitting(answers, tmp_path=None, pages=PAGES):
    client = FakeClient(list(answers))
    lib = Library.build(ALL_SEATS, UTTERANCES + TO_STUDENTS, {}, False, pages)
    session = Session(lib, Gate(client, NameList.build(ALL_SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    return session, client


def sent_ids(client):
    return [p["utterance_id"] for p in json.loads(client.requests[-1]["messages"][0]["content"])["pieces"]]


# --- which pieces are words to high-school students: by section, in code ---

@pytest.mark.parametrize("piece, held", [
    (u("x", "S01", "…", section="高校生に一言"), True),
    (u("x", "S01", "…", section="ランキング"), True),
    (u("x", "S01", "…", section="先輩社員からのメッセージ"), True),
    (u("x", "S01", "…", section="本文"), False),
    (u("x", "S01", "…", section="キャッチコピー"), False),
    (u("x", "O02", "…", kind="outsider_teacher", section="高校生に一言"), True),
    (u("x", "O02", "…", kind="outsider_teacher", section="ランキング"), False),  # The teacher's: 一言 only.
    (u("x", "P01", "…", kind="poster", section="結論と展望", heading="まとめ"), True),
    (u("x", "P01", "…", kind="poster", section="結果", heading="考察と展望"), True),
    (u("x", "P01", "…", kind="poster", section="目的", heading="目的"), False),
    (u("x", "T01", "…", kind="poster", section="p3"), True),  # A slide-shaped poster: by page.
    (u("x", "T01", "…", kind="poster", section="p2"), False),
    (u("x", "C01", "…", kind="cross", section="p3"), False),  # Not listed for this seat.
])
def test_words_to_high_school_students_are_picked_by_section_not_by_a_model(piece, held):
    assert to_students(piece, PAGES) is held


def test_with_no_pages_table_no_slide_page_speaks(tmp_path):
    assert load_hasshin_pages(tmp_path / "hasshin_pages.tsv", {"T01"}) == {}
    assert not to_students(u("x", "T01", "…", kind="poster", section="p3"), {})


def test_the_pages_table_is_read_and_its_errors_give_line_numbers_only(tmp_path):
    path = tmp_path / "hasshin_pages.tsv"
    path.write_text("席ID\tページ\nT01\t3\nT01\t5\nC01\t4\n", encoding="utf-8")
    assert load_hasshin_pages(path, {"T01", "C01"}) == {"T01": frozenset({3, 5}), "C01": frozenset({4})}
    for body, message in [("T09\t3\n", "line 2: unknown seat"), ("T01\t三\n", "line 2: bad page number"),
                          ("T01\t0\n", "line 2: bad page number"), ("T01\n", "line 2: wrong column count")]:
        path.write_text("席ID\tページ\n" + body, encoding="utf-8")
        with pytest.raises(ValueError, match=message) as error:
            load_hasshin_pages(path, {"T01"})
        assert "T09" not in str(error.value) and "三" not in str(error.value)
    path.write_text("席\tページ\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        load_hasshin_pages(path, {"T01"})


def test_the_sample_pages_table_has_the_same_shape_and_fits_the_sample_seats():
    seats = {seat.seat_id for seat in load_seats(SAMPLES / "seats.tsv")}
    assert load_hasshin_pages(SAMPLES / closing.HASSHIN_PAGES_FILE, seats)


# --- the round's last word ---

def test_the_seats_that_spoke_answer_with_one_piece_each_through_the_guard():
    session, client = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"),
                                                ("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    view = session.close_round(1)
    # Only the lit seats' words to high-school students go to the moderator.
    assert sorted(sent_ids(client)) == ["a8", "a9", "b9"]
    assert client.requests[-1]["model"] == "claude-opus-5-5"
    assert view["question"] == load_text(CLOSING_QUESTION) == "最後に、何か伝えたいことはありますか"
    assert view["label"] == load_text(CLOSING_LABEL) == "この人が、高校生に向けて書いた（話した）言葉"
    assert [(w["seat_id"], w["utterance_id"], w["text"]) for w in view["words"]] == [
        ("S01", "a9", "地元にも、面白い仕事はたくさんあります。"), ("S02", "b9", "畑は毎日ちがう顔をします。")]
    assert view["words"][0]["said"] and view["words"][0]["source"]["title"] == "理容師"
    assert not view["words"][1]["said"] and view["words"][1]["source"]["note"] == "先輩社員の言葉（本人確認済み）"


def test_at_most_three_seats_in_the_order_they_spoke_and_a_slide_page_by_the_table():
    four = [librarian_finds("a1", "b1", "p1", "t2"),
            moderator_says([("t2", "実習では、朝の仕込みから入りました。"), ("a1", "休みは決めて取ります。"),
                            ("b1", "畑は天気しだいなので、休みは空いたら取ります。"),
                            ("p1", "川のにごりは何で決まるのかを知る。")])]
    session, client = sitting(four + [says(("t3", "地域の中に、学びの場はあります。"), ("p9", "川は町の鏡だと分かった。"))])
    session.ask(QUESTION)
    assert session.rounds[0].seat_order == ["T01", "S01", "S02", "P01"]
    view = session.close_round(1)
    assert sorted(sent_ids(client)) == ["a8", "a9", "b9", "t3"]  # P01 is the fourth: not asked.
    assert [w["seat_id"] for w in view["words"]] == ["T01"]  # p9 is not from an asked seat.
    assert session.rounds[0].closing.dropped == 1
    assert session.rounds[0].closing.words[0].text == "地域の中に、学びの場はあります。"


def test_a_seat_without_such_words_says_nothing_and_with_none_no_model_is_called():
    session, client = sitting([librarian_finds("c1"),
                               moderator_says([("c1", "子どもの声で元気が出ます。")])])  # S03 holds none.
    session.ask(QUESTION)
    before = len(client.requests)
    assert session.close_round(1) == {"round": 1, "question": "", "label": "", "words": []}
    assert len(client.requests) == before
    assert session.rounds[0].closing.status == closing.NONE_HOLD


@pytest.mark.parametrize("bad", ["地元にも、面白い仕事", "地元にも面白い仕事がある。", "休みの日も"])
def test_a_copy_the_guard_stops_is_not_shown(bad):
    session, _ = sitting(ANSWERED + [says(("a9", bad), ("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    view = session.close_round(1)
    assert [w["seat_id"] for w in view["words"]] == ["S02"]
    assert session.rounds[0].closing.guard_stopped == 1


def test_a_second_pick_for_one_seat_is_dropped():
    session, _ = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"), ("a8", "1位　朝の店の静けさ"))])
    session.ask(QUESTION)
    assert [w["utterance_id"] for w in session.close_round(1)["words"]] == ["a9"]
    assert session.rounds[0].closing.dropped == 1


def test_a_failed_model_shows_nothing_and_keeps_the_reason():
    session, _ = sitting(ANSWERED)  # Nothing left for the closing call.
    session.ask(QUESTION)
    assert session.close_round(1)["words"] == []
    assert session.rounds[0].closing.status == closing.UNAVAILABLE and session.rounds[0].closing.reason


def test_asked_once_per_round_and_only_after_seats_spoke():
    session, client = sitting(ANSWERED + [says(("b9", "畑は毎日ちがう顔をします。"))]
                              + [librarian_finds()] + [text_response({"ask_seat_ids": [], "rephrase": ""})])
    session.ask(QUESTION)
    first = session.close_round(1)
    count = len(client.requests)
    assert session.close_round(1) == first and len(client.requests) == count
    session.ask("ほかには？")  # No piece found: silent.
    with pytest.raises(Refused, match="no_seat_spoke"):
        session.close_round(2)
    with pytest.raises(Refused):
        session.close_round(3)


def test_nothing_sent_to_the_model_holds_a_company_or_a_name():
    session, client = sitting(ANSWERED + [says(("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    session.close_round(1)
    sent = json.dumps(client.requests[-1], ensure_ascii=False)
    for word in (COMPANY, DISPLAY_NAME, "架空農園", "谷口"):
        assert word not in sent


def test_the_record_keeps_the_seats_and_the_pieces_ids_only(tmp_path):
    session, _ = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"))], tmp_path=tmp_path)
    session.ask(QUESTION)
    session.close_round(1)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = record["rounds"][0]["closing"]
    assert kept == {"status": "shown", "reason": "", "seats_asked": ["S01", "S02"], "seats_shown": ["S01"],
                    "utterance_ids": ["a9"], "guard_stopped": 0, "dropped": 0}
    assert "面白い仕事" not in json.dumps(record, ensure_ascii=False)
