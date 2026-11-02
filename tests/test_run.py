import json

from conftest import COMPANY, PERSON, make_seat, write_article, write_seats
from ebino.ingest.run import main, run
from ebino.ingest.scrub import normalize_for_match


def setup_data(tmp_path, seats):
    write_seats(tmp_path / "seats.tsv", seats)
    return tmp_path


def test_batch_writes_clean_output(tmp_path):
    write_article(tmp_path / "article01.docx")
    report = run(setup_data(tmp_path, [make_seat()]))
    assert report.ingested_by_kind["adult"] == 1
    assert not report.failed_seats

    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    assert normalize_for_match(PERSON) not in normalize_for_match(raw)
    assert COMPANY not in raw


def test_output_has_no_source_file_or_company_field(tmp_path):
    write_article(tmp_path / "article01.docx")
    run(setup_data(tmp_path, [make_seat()]))
    rows = json.loads((tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8"))
    assert rows
    assert set(rows[0]) == {"id", "seat_id", "kind", "section", "voice", "text", "paragraph", "heading"}
    assert "2026" not in json.dumps(rows)  # The year is never carried (SPEC 14-34).
    assert "article01" not in json.dumps(rows, ensure_ascii=False)


def test_failed_seat_is_counted_and_others_continue(tmp_path):
    write_article(tmp_path / "article01.docx")
    good = make_seat()
    missing = make_seat(seat_id="S02", source_file="山川太郎_欠番.docx")
    report = run(setup_data(tmp_path, [good, missing]))
    assert report.ingested_by_kind["adult"] == 1
    assert report.failed_seats == ["S02"]


def test_report_never_prints_file_names_or_text(tmp_path):
    write_article(tmp_path / "article01.docx")
    missing = make_seat(seat_id="S02", source_file="山川太郎_欠番.docx")
    report = run(setup_data(tmp_path, [make_seat(), missing]))
    printed = "\n".join(report.lines())
    assert "山川" not in printed
    assert "article01" not in printed


def test_slides_wait_for_a_mask_list(tmp_path):
    (tmp_path / "slide01.pdf").write_bytes(b"")
    seat = make_seat(seat_id="C01", kind="cross", company="", source_file="slide01.pdf")
    report = run(setup_data(tmp_path, [seat]))
    assert report.skipped_slide_seats == 1
    assert json.loads((tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")) == []


def test_kind_and_file_type_must_agree(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    report = run(setup_data(tmp_path, [make_seat(source_file="a.txt")]))
    assert report.failures["kind_and_file_type_mismatch"] == 1


def test_batch_counts_poster_roles_and_hypothesis_purposes(tmp_path):
    from test_poster_pdf import write_poster

    write_poster(tmp_path / "poster01.pdf")
    seat = make_seat(seat_id="P01", kind="poster", company="", display_name="卒業生", source_file="poster01.pdf")
    report = run(setup_data(tmp_path, [seat]))
    assert report.ingested_by_kind["poster"] == 1
    assert report.poster_sections_by_role == {"目的": 1, "結果": 1}
    assert report.posters_purpose_from_hypothesis == 1
    assert "posters whose purpose comes from 仮説/経緯: 1" in report.lines()


# --- SPEC 14-45: talk slides and posters of two or more pages ------------------


def work_seat(source_file="talks/T01.pdf"):
    return make_seat(
        seat_id="T01", kind="poster", title="探究の先輩（朝市を開いた）", company="",
        display_name="3年生", source_file=source_file,
    )


def write_work(tmp_path, source_file="talks/T01.pdf"):
    from test_masks import write_slide

    path = tmp_path / source_file
    path.parent.mkdir(parents=True, exist_ok=True)
    write_slide(path, ["発表者 川辺三郎", "朝市に人が集まらない理由を調べた", "川辺の考えは変わった"])
    return path


def write_masks(tmp_path, body):
    (tmp_path / "masks.tsv").write_text("席ID\t種類\t値\n" + body, encoding="utf-8")


def read_output(tmp_path):
    return (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")


def test_multi_page_work_with_rows_is_read_like_slides(tmp_path):
    write_work(tmp_path)
    write_masks(tmp_path, "T01\t語\t川辺三郎\nT01\t語\t川辺\nT01\tページ\t1\n")
    report = run(setup_data(tmp_path, [work_seat()]))
    assert report.ingested_by_kind["poster"] == 1
    assert (report.multi_page_works_read, report.multi_page_works_skipped) == (1, 0)
    rows = json.loads(read_output(tmp_path))
    assert [row["section"] for row in rows] == ["p2", "p3"]
    raw = read_output(tmp_path)
    assert "川辺" not in raw and "三郎" not in raw
    assert "朝市に人が集まらない理由を調べた" in raw
    assert "multi-page inquiry works (read / skipped, no rows in masks.tsv): 1 / 0" in report.lines()


def test_multi_page_work_with_only_a_confirmed_row_is_read(tmp_path):
    from test_masks import write_slide

    path = tmp_path / "talks" / "T01.pdf"
    path.parent.mkdir()
    write_slide(path, ["朝市の写真", "朝市に人が集まらない理由を調べた"])
    write_masks(tmp_path, "T01\t確認済み\t\n")
    report = run(setup_data(tmp_path, [work_seat()]))
    assert report.multi_page_works_read == 1
    assert not report.failed_seats


def test_multi_page_work_without_rows_is_skipped_and_counted(tmp_path):
    write_work(tmp_path, "posters/P05.pdf")
    report = run(setup_data(tmp_path, [work_seat("posters/P05.pdf")]))
    assert (report.multi_page_works_read, report.multi_page_works_skipped) == (0, 1)
    assert report.failures["poster_not_one_page"] == 1
    assert report.failed_seats == ["T01"]
    assert json.loads(read_output(tmp_path)) == []


def test_one_page_poster_is_still_read_by_its_headings(tmp_path):
    from test_poster_pdf import write_poster

    write_poster(tmp_path / "poster01.pdf")
    write_masks(tmp_path, "P01\t確認済み\t\n")
    seat = make_seat(seat_id="P01", kind="poster", company="", display_name="卒業生", source_file="poster01.pdf")
    report = run(setup_data(tmp_path, [seat]))
    assert report.multi_page_works_read == 0
    rows = json.loads(read_output(tmp_path))
    assert {row["section"] for row in rows} == {"目的", "結果"}


# --- SPEC 14-46: seats from the older booklets ----------------------------------


def test_seat_ids_with_any_letter_and_files_in_subfolders(tmp_path):
    (tmp_path / "r6").mkdir()
    (tmp_path / "merged").mkdir()
    write_article(tmp_path / "r6" / "R6_s02L.docx")
    write_article(tmp_path / "merged" / "M_B05.docx")
    seats = [
        make_seat(seat_id="D01", source_file="r6/R6_s02L.docx"),
        make_seat(seat_id="B05", source_file="merged/M_B05.docx"),
        make_seat(seat_id="Z99", source_file="r6/R6_s02L.docx"),
    ]
    write_masks(tmp_path, "D01\t語\t鏡\n")
    report = run(setup_data(tmp_path, seats))
    assert report.ingested_by_kind["adult"] == 3
    assert not report.failed_seats
    rows = json.loads(read_output(tmp_path))
    assert {row["seat_id"] for row in rows} == {"D01", "B05", "Z99"}
    assert all("鏡の前" not in row["text"] for row in rows if row["seat_id"] == "D01")
    assert "R6_s02L" not in read_output(tmp_path)


def test_main_needs_the_data_folder(monkeypatch):
    monkeypatch.delenv("EBINO_DATA_DIR", raising=False)
    assert main() == 2
