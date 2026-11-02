from conftest import make_seat, write_seats
from ebino.ingest.poster_shape import main, shape_lines
from test_poster_pdf import STUDENT, write_two_column_theme_poster

ROLES = ("背景と課題", "目的", "手法", "結果", "結論と展望")


def test_shape_shows_positions_and_roles_but_no_text(tmp_path):
    lines = shape_lines(write_two_column_theme_poster(tmp_path / "poster01.pdf"))
    printed = "\n".join(lines)
    for word in ("川辺", "三郎", "公園", "探究テーマ", "スポーツ", "研究仮説", "遊具"):
        assert word not in printed
    for line in lines:
        stripped = line
        for role in ROLES:
            stripped = stripped.replace(role, "")
        assert stripped.isascii(), line
    assert "-> above the name line (dropped)" in printed
    assert printed.count("-> heading 背景と課題") == 2
    assert "section 3: 目的 chars=12" in printed


def test_main_prints_only_shapes_for_a_poster_seat(tmp_path, monkeypatch, capsys):
    write_two_column_theme_poster(tmp_path / "poster01.pdf")
    seat = make_seat(seat_id="P05", kind="poster", company="", display_name="卒業生",
                     source_file="poster01.pdf")
    write_seats(tmp_path / "seats.tsv", [seat])
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    assert main(["P05"]) == 0
    out = capsys.readouterr().out
    assert "section 1:" in out
    assert STUDENT.split()[0] not in out and "poster01" not in out


def test_main_refuses_unknown_or_non_poster_seats(tmp_path, monkeypatch):
    write_seats(tmp_path / "seats.tsv", [make_seat()])
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    assert main(["S01"]) == 2
    assert main(["X99"]) == 2
    assert main([]) == 2
