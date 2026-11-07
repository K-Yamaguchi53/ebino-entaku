"""直し54d (the teacher, 11/8: 質問と回答を全員分作っておく): every seat's
questions and the words each shows, listed for the teacher (no model), and
ask_hide.tsv: a question the teacher stops for a seat is not offered. Every
seat and word here is invented (test_one_to_one)."""

import csv
import importlib.util
import random
from pathlib import Path

import pytest
from fake_client import FakeClient

from ebino import one_to_one
from ebino.gate import Gate, NameList
from ebino.session import Library, Refused, Session
from test_one_to_one import SEATS, UTTERANCES

ROOT = Path(__file__).resolve().parent.parent


def _tool():
    spec = importlib.util.spec_from_file_location("list_one_answers", ROOT / "tools" / "list_one_answers.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def _session(monkeypatch, hidden=()):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    monkeypatch.setenv("EBINO_ASKER", "0")
    lib = Library.build(SEATS, UTTERANCES, {}, False, {})
    lib.ask_tables = {"pages": {}, "ranking": {}, "unread": [], "hidden": set(hidden)}
    return Session(lib, Gate(FakeClient([]), NameList.build(SEATS, {})), rng=random.Random(1))


# --- a question stopped ---

def test_a_stopped_question_is_not_offered_nor_can_be_asked(monkeypatch):
    items = [item for item, _, _ in _session(monkeypatch).one_items("A01")]
    assert "プロフィール" in items
    session = _session(monkeypatch, {("A01", "プロフィール")})
    assert [item for item, _, _ in session.one_items("A01")] == [i for i in items if i != "プロフィール"]
    assert all(q["item"] != "プロフィール" for q in session.one_view("A01")["questions"])
    with pytest.raises(Refused):
        session.one_ask("A01", "プロフィール")


def test_the_stop_table_is_read_as_typed_and_its_rows_that_stop_nothing_are_said(tmp_path):
    (tmp_path / one_to_one.HIDE_FILE).write_text(
        "席\t項目\nＡ０１\tプロフィール\nA01\t\nA01\tプロフ\n山田\t本文\n", encoding="utf-8")
    hidden, rows, problem = one_to_one.load_hidden(tmp_path)
    assert problem == "" and hidden == {("A01", "プロフィール"), ("A01", "プロフ"), ("山田", "本文")}
    out = one_to_one.hide_problems(rows, {"A01"}, {"プロフィール", "本文"})
    assert out == [f"{one_to_one.HIDE_FILE} 4行目（A01 項目?）：この項目の名前はない（一覧の「項目」の欄から写す）",
                   f"{one_to_one.HIDE_FILE} 5行目（席ID? 本文）：この席IDはない"]
    assert all("山田" not in line for line in out)


def test_no_stop_table_stops_nothing(tmp_path):
    assert one_to_one.load_hidden(tmp_path) == (set(), [], "")


# --- 直し54e: a poster read as pages ---

def test_a_poster_read_as_pages_is_not_asked_the_cross_questions(monkeypatch):
    from test_one_to_one import _u
    from ebino import texts
    utterances = UTTERANCES + [_u("P01", "poster", "p1", "探究テーマの設定理由は、地域の資源を使いたかったから。"),
                               _u("C01", "cross", "p1", "向こうでは、毎朝の市場の早さに驚いた。")]
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    lib = Library.build(SEATS, [u for u in utterances if u.seat_id != "P01" or u.section == "p1"], {}, False, {})
    lib.ask_tables = {"pages": {"P01": {"p1": ["向こうで"]}, "C01": {"p1": ["向こうで"]}}, "ranking": {}, "unread": []}
    session = Session(lib, Gate(FakeClient([]), NameList.build(SEATS, {})), rng=random.Random(1))
    assert session.one_items("P01") == []
    cross = dict(texts.ask_questions()[one_to_one.GROUP_CROSS])
    assert [item for item, _, _ in session.one_items("C01")] == ["向こうで"] and "向こうで" in cross


# --- the list ---

def test_the_list_shows_each_question_and_the_words_the_screen_shows(monkeypatch):
    session = _session(monkeypatch, {("A01", "プロフィール")})
    listed = _tool().rows(session)
    a01 = [row for row in listed if row[0] == "A01"]
    assert [row[2] for row in a01] == [item for item, _, _ in _session(monkeypatch).one_items("A01")]
    stopped = next(row for row in a01 if row[2] == "プロフィール")
    assert stopped[7] == "出さない（ask_hide.tsv）"
    # The words are the very words one to one shows for that question.
    shown = _session(monkeypatch).one_ask("A01", "本文")
    row = next(row for row in a01 if row[2] == "本文")
    assert row[4] == "\n".join(piece["text"] for piece in shown["pieces"])
    assert session.library.ask_tables["hidden"] == {("A01", "プロフィール")}  # Put back after listing.


def test_the_list_is_written_for_excel_and_the_stop_tables_header_only_once(tmp_path):
    tool = _tool()
    assert tool.write(tmp_path, [["A01", "札", "本文", "質問？", "言葉\n二行目", "", "本文", ""]]) is True
    with (tmp_path / tool.LIST_FILE).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == list(tool.COLUMNS) and rows[1][4] == "言葉\n二行目"
    assert (tmp_path / tool.LIST_FILE).read_bytes().startswith(b"\xef\xbb\xbf")  # Excel reads it as UTF-8.
    (tmp_path / one_to_one.HIDE_FILE).write_text("席\t項目\nA01\t本文\n", encoding="utf-8")
    assert tool.write(tmp_path, []) is False
    assert "A01\t本文" in (tmp_path / one_to_one.HIDE_FILE).read_text(encoding="utf-8")  # Never written over.


def test_the_list_asks_no_model_and_says_counts_and_names_only():
    src = (ROOT / "tools" / "list_one_answers.py").read_text(encoding="utf-8")
    assert "Gate(NoModel()," in src and "seat_label(seat, False)" in src
    assert 'print(f"書いた：データの {INGESTED_DIR} フォルダの {LIST_FILE}")' in src


def test_the_server_says_the_stopped_questions_at_its_start():
    app = (ROOT / "ebino" / "app.py").read_text(encoding="utf-8")
    assert "1対1 ask_hide.tsv：止めた質問 {library.ask_tables['hide_rows']}" in app
    session = (ROOT / "ebino" / "session.py").read_text(encoding="utf-8")
    assert "hidden, rows, problem = one_to_one.load_hidden(data_dir / INGESTED_DIR)" in session
    assert one_to_one.HIDE_FILE in one_to_one.UNREAD_HINT
