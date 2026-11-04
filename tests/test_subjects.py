"""The harvest card's ③ 教科とのつながり (SPEC 5-3, 14-1, 14-4). The tables
here are invented: 札, subjects, item numbers and who learns what."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest
from fake_client import FakeClient, text_response

from ebino import subjects
from ebino.gate import Gate, NameList
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.subjects import Catalog, Row, choose, line, load_catalog, load_when_words
from ebino.texts import HARVEST_SUBJECTS, TEXTS_DIR, load_table
from test_reflection import reflection_says
from test_session import ANSWERED, SEATS, UTTERANCES

SAMPLES = Path(__file__).parent.parent / "samples"
FIRST = "休みの日って、みんな何してる？"
FUDA = {"札1": ("比べる", ""), "札2": ("偏り", "集めた情報が一方に寄っていないか"), "札3": ("地域", "")}


def row(fuda, subject, n, heading, note, clues):
    return Row(fuda, subject, f"架空 第{n}項 イ(ア)", heading, note, tuple(clues.split("・")))


# (row, 学ぶ人)
TABLE = [
    (row("札1", "国語ア", 1, "読むこと", "違う言い分を読み比べる。", "比べる・違う"), "み1"),
    (row("札1", "数学イ", 2, "データ", "二つを比べて読む。", "比べる・多い"), "生1"),
    (row("札1", "社会ウ", 3, "資料", "資料の違う所を読む。", "資料・違う"), "み1・生1"),
    (row("札1", "家庭エ", 4, "暮らし", "暮らしを見直す。", "暮らし"), "学科不明"),
    (row("札1", "理科オ", 5, "生き物", "生き物を見比べる。", "生き物"), "Q2選択・A2選択・C2選択"),
    (row("札1", "数学カ", 6, "分布", "分布を読む。", "分布"), "中2"),
    (row("札1", "保健キ", 7, "健康", "体のことを考える。", "体"), "全員"),
    (row("札1", "英語ク", 8, "やり取り", "賛成と反対で話す。", "賛成・反対"), "Q2・A2・C2"),
    (row("札1", "公共ケ", 9, "", "公正に判断する。", "判断"), "Q2"),
    (row("札1", "数学コ", 10, "標本", "一部から全体を考える。", "一部"), "中3"),
    (row("札2", "国語サ", 11, "書くこと", "確かめて書く。", "確か"), "み1"),
    (row("札2", "家庭シ", 12, "設計", "将来を考える。", "将来"), "生1"),
    (row("札3", "地理ス", 13, "地域の調査", "地域を調べる。", "地域・町"), "み1・中2"),
    (row("札3", "歴史セ", 14, "身近な歴史", "身近な昔を考える。", "昔"), "み1"),
    (row("札3", "公共ソ", 15, "", "地域をつくることを考える。", "地域"), "み1"),
]
ROWS = [r for r, _ in TABLE]


def catalog(manabu=True):
    marks = {r.key: frozenset(m.split("・")) for r, m in TABLE} if manabu else None
    return Catalog(FUDA, ROWS, marks, load_when_words())


def names(lab, fuda=None):
    return [c.row.subject for c in catalog().candidates(lab) if fuda is None or c.row.fuda == fuda]


def number(lab, subject):
    """The number the request gives a candidate: its place among this student's."""
    return names(lab).index(subject) + 1


def says(fuda, *numbers):
    return text_response({"fuda": fuda, "numbers": list(numbers)})


def gate(*answers):
    return Gate(FakeClient(list(answers)), NameList.build(SEATS, {}))


WORDS = {"question": "地域の昔を知りたい", "answer": "", "move": ""}


# --- narrowing by the first question's answer ---

@pytest.mark.parametrize("lab, shown", [
    ("quest", ["国語ア", "社会ウ", "理科オ", "数学カ", "保健キ", "英語ク", "公共ケ", "数学コ"]),
    ("action", ["国語ア", "社会ウ", "理科オ", "数学カ", "保健キ", "英語ク", "数学コ"]),
    ("creation", ["数学イ", "社会ウ", "理科オ", "数学カ", "保健キ", "英語ク", "数学コ"]),
    # Not said: 学科不明, 中2, 中3, 全員, み1 with 生1, Q2 with A2 and C2; never a choice.
    ("not_said", ["社会ウ", "家庭エ", "数学カ", "保健キ", "英語ク", "数学コ"]),
])
def test_the_candidates_are_the_subjects_the_student_learns(lab, shown):
    assert names(lab, "札1") == shown


def test_a_creation_student_never_gets_a_row_for_mi1_alone():
    assert "国語ア" not in names("creation") and "数学イ" in names("creation")


def test_a_student_who_did_not_say_gets_no_mi1_only_row_and_no_choice():
    shown = names("not_said")
    assert "国語ア" not in shown and "理科オ" not in shown and "公共ケ" not in shown
    assert "家庭エ" in shown and "社会ウ" in shown  # 学科不明, and み1 with 生1.


def test_not_said_and_a_fuda_whose_rows_are_each_for_one_course_lets_the_clue_words_pick():
    assert names("not_said", "札2") == []
    pick = choose(gate(says("札2", 1)), catalog(), "not_said", WORDS, Counter())
    # Never an empty ③ (直し31-3): the clue words pick among this student's.
    assert pick.status == subjects.SHOWN and pick.source == subjects.SOURCE_CODE and pick.model_said == "札2"
    assert subjects.view(catalog(), pick) is not None


# --- the line ---

@pytest.mark.parametrize("lab, subject, when", [
    ("quest", "国語ア", "いま習っている"),
    ("quest", "英語ク", "2年で習う"),
    ("creation", "理科オ", "2年で選べる"),
    ("quest", "数学カ", "中学2年で習った"),
    ("quest", "数学コ", "中学3年で習った"),
    ("quest", "地理ス", "いま習っている"),  # み1 and 中2: year 1 comes first.
    ("not_said", "社会ウ", "いま習っている"),  # み1 with 生1.
    ("not_said", "英語ク", "2年で習う"),  # Q2, A2 and C2.
])
def test_when_is_the_teachers_words_for_the_mark_that_fits(lab, subject, when):
    candidate = next(c for c in catalog().candidates(lab) if c.row.subject == subject)
    assert f"、{when}{subject}" in line(catalog(), candidate)


def test_a_row_with_a_heading_and_one_without():
    found = {c.row.subject: c for c in catalog().candidates("quest")}
    assert line(catalog(), found["国語ア"]) == "あなたの問いに近い考え方は、いま習っている国語アの「読むこと」にある。"
    assert line(catalog(), found["公共ケ"]) == "あなたの問いに近い考え方は、2年で習う公共ケにある。"


# --- the model's answer, checked ---

def test_a_number_not_in_the_table_or_of_another_fuda_is_not_used_and_code_fills_the_gap():
    client_gate = gate(says("札3", 99, number("quest", "国語ア"), number("quest", "歴史セ")))
    pick = choose(client_gate, catalog(), "quest", WORDS, Counter())
    assert pick.status == subjects.SHOWN and pick.fuda == "札3" and pick.source == subjects.SOURCE_MODEL
    # 歴史セ from the model; then by clue words: 地理ス and 公共ソ both hold 地域, the table's order.
    assert [c.row.subject for c in pick.order] == ["歴史セ", "地理ス", "公共ソ"]


def test_a_fuda_not_in_the_table_is_not_used():
    pick = choose(gate(says("札9", 1)), catalog(), "quest", WORDS, Counter())
    assert pick.source == subjects.SOURCE_CODE and pick.model_error == subjects.BAD_FUDA


def test_nashi_lets_the_clue_words_pick_and_the_card_is_never_empty():
    pick = choose(gate(says("なし")), catalog(), "quest", WORDS, Counter())
    assert pick.status == subjects.SHOWN and pick.source == subjects.SOURCE_CODE and pick.model_said == "なし"
    assert subjects.view(catalog(), pick)["cards"]


def test_with_no_model_the_clue_words_choose_and_none_held_means_no_third_line():
    words = {"question": "比べると違うのはなぜ？", "answer": "", "move": ""}
    pick = choose(gate(RuntimeError("down")), catalog(), "quest", words, Counter())
    assert pick.source == subjects.SOURCE_CODE and pick.model_error == "api_error:RuntimeError"
    assert [c.row.subject for c in pick.order[:2]] == ["国語ア", "社会ウ"]  # Two words, then one.
    assert pick.fuda == "札1"
    nothing = choose(gate(RuntimeError("down")), catalog(), "quest",
                     {"question": "休みの日は何をする？", "answer": "", "move": ""}, Counter())
    # No clue word held: two to pick from, never nothing (直し31-3).
    assert nothing.status == subjects.STATUS_CHOOSE and len(subjects.view(catalog(), nothing)["cards"]) == 2


def test_with_no_model_the_second_comes_from_the_first_ones_fuda_only():
    # 国語ア (札1) and 地理ス (札3) each hold two clue words; 社会ウ (札1) one.
    words = {"question": "比べると違う町の地域", "answer": "", "move": ""}
    pick = choose(gate(RuntimeError("down")), catalog(), "quest", words, Counter())
    assert pick.fuda == "札1" and pick.source == subjects.SOURCE_CODE
    assert [c.row.subject for c in pick.order[:2]] == ["国語ア", "社会ウ"]
    assert {c.row.fuda for c in pick.order} == {"札1"}
    # The same 札 fills the second even with no clue word: 歴史セ, shown fewer times, first.
    town = {"question": "町のこと", "answer": "", "move": ""}
    pick = choose(gate(RuntimeError("down")), catalog(), "quest", town, Counter({ROWS[12].key: 1}))
    assert [c.row.subject for c in pick.order] == ["歴史セ", "地理ス", "公共ソ"]


def test_of_the_two_the_one_shown_fewer_times_comes_first_and_the_rest_follow_fewest_first():
    counts = Counter({ROWS[12].key: 3, ROWS[13].key: 1, ROWS[14].key: 0})
    pick = choose(gate(says("札3", number("quest", "地理ス"), number("quest", "歴史セ"))),
                  catalog(), "quest", WORDS, counts)
    assert [c.row.subject for c in pick.order] == ["歴史セ", "地理ス", "公共ソ"]


def test_no_manabu_file_shows_no_third_line(tmp_path):
    empty = load_catalog(tmp_path)
    assert empty.manabu is None and "not found" in empty.report()
    pick = choose(gate(), empty, "quest", WORDS, Counter())
    assert pick.status == subjects.STATUS_NO_MANABU


# --- a sitting ---

def sitting(lab, *answers, tmp_path=None, rows=None):
    lib = Library.build(SEATS, UTTERANCES, {}, False, subject_catalog=rows or catalog())
    client = FakeClient(list(ANSWERED))
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.lab = lab
    session.ask(FIRST)
    client._answers.append(reflection_says())
    session.reflect_begin("a_little", "地域の昔を知りたい")
    session.reflect_answer("町の人に聞いてみたい")
    session.reflect_finish("none", "", "", "", "")
    client._answers.extend(answers)
    return session, client


def test_two_students_of_the_same_fuda_in_a_row_get_different_subjects(tmp_path):
    answer = says("札3", number("quest", "地理ス"), number("quest", "歴史セ"))
    first, _ = sitting("quest", answer, tmp_path=tmp_path)
    second, _ = sitting("quest", answer, tmp_path=tmp_path)
    one, two = first.subject()["subject"], second.subject()["subject"]
    assert "地理ス" in one["line"] and "歴史セ" in two["line"]
    counts = json.loads((tmp_path / "subject_counts.json").read_text(encoding="utf-8"))
    assert counts == {ROWS[12].key: 1, ROWS[13].key: 1}  # Keys and counts only.


def test_seeing_other_subjects_goes_round_and_the_last_one_shown_is_recorded(tmp_path):
    session, _ = sitting("quest", says("札3", number("quest", "地理ス"), number("quest", "歴史セ")),
                         tmp_path=tmp_path)
    seen = [session.subject()["subject"]]
    seen += [session.subject_more()["subject"] for _ in range(3)]
    assert [s["note"] for s in seen] == ["地域を調べる。", "身近な昔を考える。", "地域をつくることを考える。", "地域を調べる。"]
    assert all(s["more"] for s in seen)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["reflection"]["harvest_subject"] == {
        "status": "shown", "fuda": "札3", "source": "model", "model_error": "", "model_said": "",
        "shown": ROWS[12].key, "presses": 3, "offered": [], "chosen": ""}
    counts = Records(tmp_path).subject_counts()
    assert counts == Counter({ROWS[12].key: 2, ROWS[13].key: 1, ROWS[14].key: 1})  # Pressed ones count too.


def test_the_model_is_asked_once_and_waits_for_the_second_use_when_a_seat_was_picked():
    session, client = sitting("quest", says("札3", 13, 14))
    sent = len(client.requests)
    assert session.subject() == session.subject()
    assert len(client.requests) == sent + 1
    picked, _ = sitting("quest")
    picked.reflection.meet_seat, picked.reflection.harvest_use = "S02", ""
    with pytest.raises(Refused):
        picked.subject()  # ② first.


def test_one_candidate_only_has_no_button_and_cannot_be_pressed():
    rows = Catalog(FUDA, ROWS, {ROWS[13].key: frozenset({"み1"})}, load_when_words())
    session, _ = sitting("quest", says("札3", 1), rows=rows)
    assert session.subject()["subject"]["more"] is False
    with pytest.raises(Refused):
        session.subject_more()


def test_the_model_gets_no_mark_lab_company_or_item_number():
    session, client = sitting("quest", says("札3", 13, 14))
    session.subject()
    request = next(r for r in client.requests if r["model"] == "claude-haiku-5-5")
    sent = json.dumps(request, ensure_ascii=False)
    for mark in subjects.MARKS + ("Quest", "Action", "Creation", "生活文化科", "みらい探究科"):
        assert mark not in sent
    for seat in SEATS:
        assert not seat.company or seat.company not in sent
    assert all(r.item not in sent for r in ROWS)
    data = json.loads(request["messages"][0]["content"])
    assert data["record"] == {"question": "地域の昔を知りたい", "answer": "町の人に聞いてみたい", "move": ""}
    assert {"fuda", "number", "subject", "note"} == set(data["candidates"][0])


# --- the teacher's tables in texts/, with the invented 学ぶ人 sample ---

def test_the_screen_never_shows_the_course_of_study_an_item_number_or_a_lab():
    real = load_catalog(SAMPLES)  # texts/ tables; samples/ holds an invented 学ぶ人.
    shown = 0
    for lab in ("quest", "action", "creation", "not_said"):
        for candidate in real.candidates(lab):
            pick = subjects.Pick(subjects.SHOWN, order=[candidate])
            text = json.dumps(subjects.view(real, pick), ensure_ascii=False)
            assert "学習指導要領" not in text and candidate.row.item not in text
            assert not any(word in text for word in ("Quest", "Action", "Creation", "Lab"))
            shown += 1
    assert shown


def test_the_tables_load_and_the_start_line_gives_counts_only():
    real = load_catalog(SAMPLES)
    assert len(real.fuda) == 7 and all(r.fuda in real.fuda for r in real.rows)
    assert len({r.key for r in real.rows}) == len(real.rows)
    assert real.not_in_table == 0
    assert real.report() == (f"subject rows {len(real.rows)}  without 学ぶ人 (not shown): "
                             f"{len(real.rows) - len(real.manabu)}  学ぶ人 rows not in the table: 0")


def test_no_note_says_use_shall_should_good_at_or_suited():
    rows = load_table(HARVEST_SUBJECTS, subjects.SUBJECT_COLUMNS, ("見出し",))
    for cells in rows:
        assert not any(word in cells["ひとこと"] for word in ("使える", "しよう", "べき", "得意", "向いて"))


def test_the_copies_keep_the_teachers_columns():
    header = (TEXTS_DIR / "harvest_subjects.tsv").read_text(encoding="utf-8").splitlines()[0]
    assert tuple(header.split("\t")) == subjects.SUBJECT_COLUMNS
    header = (SAMPLES / "kyoka_manabu.tsv").read_text(encoding="utf-8").splitlines()[0]
    assert tuple(header.split("\t")) == subjects.MANABU_COLUMNS


def test_an_unknown_mark_in_manabu_stops_with_a_line_number(tmp_path):
    (tmp_path / "kyoka_manabu.tsv").write_text("札\t科目\t項目番号\t学ぶ人\n札1\t国語ア\t架空\tみ9\n",
                                                encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_catalog(tmp_path)


def test_every_mark_has_its_when_words():
    assert set(load_when_words()) == set(subjects.MARKS)
