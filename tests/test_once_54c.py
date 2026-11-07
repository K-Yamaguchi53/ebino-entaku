"""直し54c (the teacher, 11/8 morning: 「先生が ask_pages.tsv に書いたページは、
先生の判断のまま出します」をしっかりチェック): the teacher's rows typed by hand
are read as meant, and a row that does not work as written is said at the
server's start (by its line, the seat ID and the page; never a cell)."""

from pathlib import Path
from types import SimpleNamespace

from ebino import one_to_one

ROOT = Path(__file__).resolve().parent.parent
HEAD = "席\tページ\t軸\n"


def _u(seat, section):
    return SimpleNamespace(seat_id=seat, section=section, id=f"{seat}-{section}")


UTTERANCES = [_u("O01", "p1"), _u("O01", "p2"), _u("O01", "p3"), _u("C01", "p1"), _u("C01", "p2"),
              _u("A01", "プロフィール")]
KINDS = {"O01": "outsider_teacher", "C01": "cross", "A01": "adult"}


def _write(folder, text, name=one_to_one.PAGES_FILE):
    (folder / name).write_text(text, encoding="utf-8")


# --- read as meant ---

def test_a_page_written_as_a_number_or_full_width_is_the_page(tmp_path):
    _write(tmp_path, HEAD + "O01\t3\t来たわけ\nＯ０１\tＰ２\t見えたこと\nO01\tp.1\tしたかったこと\n")
    tables = one_to_one.load_tables(tmp_path)
    assert tables["pages"] == {"O01": {"p3": ["来たわけ"], "p2": ["見えたこと"], "p1": ["したかったこと"]}}
    assert tables["teacher_pages"] == {("O01", "p3"), ("O01", "p2"), ("O01", "p1")}
    assert tables["unread"] == []


def test_the_teachers_row_still_wins_over_the_models_when_written_differently(tmp_path):
    _write(tmp_path, HEAD + "O01\t２\t来たわけ\n")
    _write(tmp_path, HEAD + "O01\tp2\t見えたこと\n", one_to_one.PAGES_MODEL_FILE)
    assert one_to_one.load_tables(tmp_path)["pages"] == {"O01": {"p2": ["来たわけ"]}}


def test_a_row_without_its_last_tab_empty_tabs_after_and_a_memo_column_are_read(tmp_path):
    _write(tmp_path, "席\tページ\t軸\tメモ\nO01\tp1\nO01\tp2\t来たわけ\t\t\nO01\tp3\t見えたこと\t写真のページ\n")
    tables = one_to_one.load_tables(tmp_path)
    assert tables["unread"] == []
    assert tables["pages"] == {"O01": {"p2": ["来たわけ"], "p3": ["見えたこと"]}}
    assert tables["teacher_pages"] == {("O01", "p2"), ("O01", "p3")}  # p1 left empty: the model's.


def test_a_ranking_row_without_its_tab_is_the_models(tmp_path):
    _write(tmp_path, "席\t質問\nA01\n", one_to_one.RANKING_FILE)
    _write(tmp_path, "席\t質問\nA01\tモデルの質問ですか？\n", one_to_one.RANKING_MODEL_FILE)
    tables = one_to_one.load_tables(tmp_path)
    assert tables["unread"] == [] and tables["ranking"] == {"A01": "モデルの質問ですか？"}


def test_still_not_read_a_cell_too_many_a_missing_key_another_header(tmp_path):
    for text, line in ((HEAD + "\nO01\tp1\t来たわけ\tあまり\n", 3), (HEAD + "\tp1\t来たわけ\n", 2),
                       ("ほかの見出し\n", 1)):
        _write(tmp_path, text)
        assert one_to_one.load_tables(tmp_path)["unread"] == [f"{one_to_one.PAGES_FILE} line {line}"]


# --- said at the start ---

def _problems(tmp_path, text):
    _write(tmp_path, HEAD + text)
    return one_to_one.teacher_page_problems(tmp_path, UTTERANCES, KINDS)


def test_rows_that_work_say_nothing(tmp_path):
    assert _problems(tmp_path, "O01\tp1\t来たわけ・見えたこと\nO01\t2\t-\nC01\tp1\t行く前\nC01\tp2\t\n") == (3, [])


def test_a_misspelt_axis_says_the_axes_of_that_seat(tmp_path):
    filled, out = _problems(tmp_path, "O01\tp1\t来た理由\n")
    assert filled == 1
    assert out == [f"{one_to_one.PAGES_FILE} 2行目（O01 p1）：軸の言葉が読めない"
                   "（この席の軸：来たわけ・見えたこと・したかったこと。出さないなら -）"]


def test_an_axis_of_the_other_group_and_a_word_more(tmp_path):
    _, out = _problems(tmp_path, "O01\tp1\t向こうで\nC01\tp2\t向こうで・楽しかった\n")
    assert "（O01 p1）：この席の質問にない軸" in out[0]
    assert "（C01 p2）：読めない言葉がある。読めた軸だけ使う（この席の軸：行く前・向こうで・帰ってきて・これから" in out[1]


def test_a_page_the_seat_has_not_and_a_seat_not_of_pages(tmp_path):
    _, out = _problems(tmp_path, "O01\tp9\t来たわけ\nA01\tp1\t来たわけ\n")
    assert out[0].endswith("（O01 p9）：この席にこのページはない（p1〜p3）")
    assert out[1].endswith("（A01 p1）：この席IDは、ページだけの席にない")


def test_a_cell_that_is_no_id_is_never_said(tmp_path):
    _, out = _problems(tmp_path, "山田太郎\tp1\t来たわけ\nO01\t山田のページ\t来たわけ\n")
    assert all("山田" not in line for line in out)
    assert "（席ID? p1）" in out[0] and "（O01 ページ?）" in out[1]


def test_a_page_written_twice_says_the_later_is_used(tmp_path):
    _, out = _problems(tmp_path, "O01\tp1\t来たわけ\nO01\t1\t見えたこと\n")
    assert out == [f"{one_to_one.PAGES_FILE} 3行目（O01 p1）：2行目と同じ席・ページ（あとの行を使う）"]


def test_a_table_not_read_or_not_there_has_no_rows(tmp_path):
    assert one_to_one.teacher_page_problems(tmp_path, UTTERANCES, KINDS) == (0, [])
    _write(tmp_path, "ほかの見出し\n")
    assert one_to_one.teacher_page_problems(tmp_path, UTTERANCES, KINDS) == (0, [])


# --- where it is said ---

def test_the_server_says_the_rows_and_what_a_table_not_read_means():
    app = (ROOT / "ebino" / "app.py").read_text(encoding="utf-8")
    assert "one_to_one.UNREAD_HINT.get(problem.split(\" line \")[0])" in app
    assert "先生が書いた行 {library.ask_tables['teacher_rows']}" in app
    session = (ROOT / "ebino" / "session.py").read_text(encoding="utf-8")
    assert "one_to_one.teacher_page_problems(data_dir / INGESTED_DIR, library.utterances," in session
    assert one_to_one.UNREAD_HINT[one_to_one.PAGES_FILE].startswith("→ この表が読めないので")


def test_the_count_tool_says_whether_each_teachers_page_is_shown():
    import importlib.util
    spec = importlib.util.spec_from_file_location("count_one_fit", ROOT / "tools" / "count_one_fit.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    tidied = {"O01-p1": SimpleNamespace(text="来た理由の文。", reasons=()),
              "O01-p2": SimpleNamespace(text="", reasons=("name",)),
              "O01-p3": SimpleNamespace(text="", reasons=("title", "empty"))}
    library = SimpleNamespace(
        all_seats=[SimpleNamespace(seat_id="O01")], utterances=UTTERANCES,
        ask_tables={"teacher_pages": {("O01", "p1"), ("O01", "p2"), ("O01", "p3"), ("X99", "p1")},
                    "pages": {"O01": {"p1": ["来たわけ"], "p2": ["見えたこと"], "p3": ["したかったこと"]},
                              "X99": {"p1": ["来たわけ"]}}})
    session = SimpleNamespace(library=library, one_page=lambda u: tidied[u.id])
    assert tool.teacher_rows(session) == ["O01\tp1\t来たわけ\t出る",
                                          "O01\tp2\t見えたこと\t出ない（名前が含まれるページ）",
                                          "O01\tp3\tしたかったこと\t出ない（整えると文が残らないページ）"]
