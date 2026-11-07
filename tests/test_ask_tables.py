"""直し34-2: the words of the people who went out (and of those from outside
in a PDF) have pages only; which item of the questions a page answers is in
a table the teacher keeps, ask_pages.tsv (席・ページ・軸), next to the
ingest's output, outside the repo; a seat's own question on its ranking in
ask_ranking.tsv (席・質問). Ingest writes each with its rows to fill when it
is not there, and never over one that is. Only an axis's name is taken from
a 軸 cell, any other word dropped. No model writes either of the teacher's
tables: since 直し36 the model writes its own beside them (test_asker.py)."""

from ebino import one_to_one
from ebino.ingest.utterance import Utterance


def _u(seat, section, n=0):
    return Utterance(id=f"{seat}-{section}-{n}", seat_id=seat, kind="x", section=section, voice="own",
                     text="架空の言葉", paragraph="架空の言葉")


UTTERANCES = [_u("C01", "p1"), _u("C01", "p2"), _u("C01", "p2", 1), _u("O01", "p1"),
              _u("A01", "プロフィール"), _u("A01", "ランキング"), _u("A02", "本文"), _u("A03", "ランキング")]
KINDS = {"C01": "cross", "O01": "outsider_teacher", "A01": "adult", "A02": "adult", "A03": "adult"}


def test_the_tables_to_fill_are_written_with_their_rows(tmp_path):
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS)
    pages = (tmp_path / "ask_pages.tsv").read_text(encoding="utf-8").splitlines()
    assert pages == ["席\tページ\t軸", "C01\tp1\t", "C01\tp2\t", "O01\tp1\t"]
    ranking = (tmp_path / "ask_ranking.tsv").read_text(encoding="utf-8").splitlines()
    assert ranking == ["席\t質問", "A01\t", "A03\t"]
    assert counts["pages_only_seats"] == 2 and counts["pages"] == 3 and counts["pages_by_axis"] == {}
    assert counts["ranking_seats"] == 2 and counts["ranking_questions"] == 0
    assert counts["written"] == ["ask_pages.tsv", "ask_ranking.tsv"]
    # Counts only: no seat, no words in what goes to the report.
    assert "C01" not in str(counts) and "架空" not in str(counts)


def test_the_teachers_tables_are_never_written_over_and_only_axes_are_taken(tmp_path):
    (tmp_path / "ask_pages.tsv").write_text("席\tページ\t軸\nC01\tp1\t行く前・向こうで\nC01\tp2\t好きな食べ物\n"
                                            "O01\tp1\t来たわけ\n", encoding="utf-8")
    (tmp_path / "ask_ranking.tsv").write_text("席\t質問\nA01\t一番の思い出は何ですか？\nA03\t\n", encoding="utf-8")
    before = [(tmp_path / name).read_bytes() for name in ("ask_pages.tsv", "ask_ranking.tsv")]
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS)
    assert [(tmp_path / name).read_bytes() for name in ("ask_pages.tsv", "ask_ranking.tsv")] == before
    assert counts["written"] == []
    tables = one_to_one.load_tables(tmp_path)
    assert tables["pages"] == {"C01": {"p1": ["行く前", "向こうで"]}, "O01": {"p1": ["来たわけ"]}}
    assert tables["ranking"] == {"A01": "一番の思い出は何ですか？"}  # A03's left empty: none shown.
    assert counts["pages_by_axis"] == {"行く前": 1, "向こうで": 1, "来たわけ": 1}
    assert counts["ranking_questions"] == 1 and counts["ranking_without"] == {"not_written": 1}


def test_no_table_or_a_broken_one_is_empty_and_the_broken_one_is_said(tmp_path):
    # 直し54: the teacher's own page rows are kept apart too (none here).
    assert one_to_one.load_tables(tmp_path) == {"pages": {}, "ranking": {}, "unread": [], "teacher_pages": set()}
    (tmp_path / "ask_pages.tsv").write_text("ほかの見出し\n", encoding="utf-8")
    assert one_to_one.load_tables(tmp_path)["pages"] == {}
    assert one_to_one.load_tables(tmp_path)["unread"] == ["ask_pages.tsv line 1"]


def test_ingest_writes_them_and_says_the_counts():
    from pathlib import Path
    run = (Path(one_to_one.__file__).parent / "ingest" / "run.py").read_text(encoding="utf-8")
    assert "report.ask_tables = one_to_one.write_tables(output, utterances," in run
    assert "{seat.seat_id: seat.kind for seat in seats}, gate)" in run
    assert "one to one, ranking questions:" in run
