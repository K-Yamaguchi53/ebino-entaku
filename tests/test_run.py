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


def test_main_needs_the_data_folder(monkeypatch):
    monkeypatch.delenv("EBINO_DATA_DIR", raising=False)
    assert main() == 2
