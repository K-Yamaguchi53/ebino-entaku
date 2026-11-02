from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from conftest import COMPANY, PERSON, make_seat, write_article, write_seats
from ebino.ingest.article_docx import ArticleRows, ingest_article_rows
from ebino.ingest.masks import SeatMasks, load_masks
from ebino.ingest.poster_pdf import Fragment, ingest_poster_fragments
from ebino.ingest.run import main, run
from ebino.ingest.scrub import PERSON_MASK, COMPANY_MASK, mask_pairs
from ebino.ingest.seats import load_seats
from ebino.ingest.slides_pdf import ingest_slide_pages
from ebino.ingest.utterance import IngestError

SAMPLES = Path(__file__).parent.parent / "samples"
HEADER = "席ID\t種類\t値\n"


def masks_file(tmp_path, body):
    path = tmp_path / "masks.tsv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def slide_seat(**overrides):
    values = dict(seat_id="C01", kind="cross", company="", source_file="slide01.pdf")
    return make_seat(**{**values, **overrides})


def body_of(utterances):
    return "".join(u.text for u in utterances)


def test_sample_keeps_the_real_shape():
    seats = load_seats(SAMPLES / "seats.tsv")
    masks = load_masks(SAMPLES / "masks.tsv", {seat.seat_id for seat in seats})
    assert masks["S01"].words == ("谷口師匠",)
    assert masks["S01"].companies == ("はるかぜ",)
    assert masks["C01"].pages == frozenset({1})
    assert masks["O01"].pages == frozenset({21})
    assert masks["O01"].companies == ("架空研究所",)


def test_company_rows_are_read(tmp_path):
    masks = load_masks(masks_file(tmp_path, "S01\t社名\tはる床\nS01\t語\t谷口\n"), {"S01"})
    assert masks["S01"].companies == ("はる床",)
    assert masks["S01"].words == ("谷口",)


def test_company_row_alone_counts_as_rows_for_slides(tmp_path):
    masks = load_masks(masks_file(tmp_path, "S01\t社名\tはる床\n"), {"S01"})
    assert masks["S01"]


def test_missing_file_means_no_masks(tmp_path):
    assert load_masks(tmp_path / "masks.tsv", {"S01"}) == {}


def test_spaces_inside_a_word_are_removed(tmp_path):
    masks = load_masks(masks_file(tmp_path, "S01\t語\t谷口 師匠\n"), {"S01"})
    assert masks["S01"].words == ("谷口師匠",)


@pytest.mark.parametrize(
    "body, reason",
    [
        ("X99\t語\t谷口\n", "unknown seat"),
        ("S01\t文\t谷口\n", "unknown kind"),
        ("S01\t語\t\n", "empty value"),
        ("S01\tページ\t0\n", "bad page number"),
        ("S01\tページ\t２\n", "bad page number"),
        ("S01\tページ\t1-3\n", "bad page number"),
        ("S01\t語\t谷口、森田\n", "one value per line"),
        ("S01\t社名\t谷口/森田\n", "one value per line"),
        ("S01\t社名\t\n", "empty value"),
        ("S01\t語\t谷口\t森田\n", "wrong column count"),
        ("S01\t語\n", "wrong column count"),
    ],
)
def test_malformed_rows_stop_with_a_line_number_only(tmp_path, body, reason):
    with pytest.raises(ValueError, match=reason) as caught:
        load_masks(masks_file(tmp_path, body), {"S01"})
    assert "line 2" in str(caught.value)
    assert "谷口" not in str(caught.value)


def test_wrong_header_stops(tmp_path):
    path = tmp_path / "masks.tsv"
    path.write_text("席\t種類\t値\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        load_masks(path, {"S01"})


def test_kind_decides_the_replacement():
    masks = SeatMasks(words=("谷口師匠", "はるかぜ"), companies=("はる床",))
    pairs = dict(masks.pairs(make_seat(company="", display_name="")))
    assert pairs == {"谷口師匠": PERSON_MASK, "はるかぜ": PERSON_MASK, "はる床": COMPANY_MASK}


def test_company_row_works_while_the_seat_company_is_empty():
    seat = slide_seat(kind="outsider_teacher", company="")
    masks = SeatMasks(companies=("株式会社架空研究所",))
    utterances = ingest_slide_pages([["架空研究所で働く"]], seat, masks)
    assert body_of(utterances) == "この職場で働く"


def test_company_row_value_is_in_the_final_check():
    # Full-width letters slip past the mask; the final check must still stop it.
    masks = SeatMasks(companies=("ABC床",))
    with pytest.raises(IngestError, match="forbidden_term_remains"):
        ingest_slide_pages([["ＡＢＣ床で働く"]], slide_seat(), masks)


def test_family_name_inside_a_company_name_keeps_the_company_whole():
    pairs = [("山川", PERSON_MASK), ("山川理容", COMPANY_MASK)]
    assert mask_pairs("山川理容の山川さん", pairs) == "この職場のこの方"


def test_masks_apply_to_articles(seat):
    rows = {"1": [PERSON], "8": ["谷口師匠に習った。はる床の朝は早い。"]}
    masks = SeatMasks(words=("谷口師匠",), companies=("はる床",))
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat, masks)
    assert body_of(utterances) == "この方に習った。この職場の朝は早い。"


def test_page_mask_on_an_article_is_refused(seat):
    rows = {"1": [PERSON], "8": ["本文の文。"]}
    with pytest.raises(IngestError, match="page_mask_on_article"):
        ingest_article_rows(ArticleRows(rows), seat, SeatMasks(pages=frozenset({1})))


def poster_fragments():
    return [Fragment("目的", 50, 60), Fragment("谷口先生と川を調べる。", 50, 80)]


def test_masks_apply_to_posters():
    seat = make_seat(kind="poster", company="", source_file="p.pdf")
    utterances = ingest_poster_fragments(poster_fragments(), seat, SeatMasks(words=("谷口",)))
    assert "谷口" not in body_of(utterances)


def test_poster_company_from_the_seat_table_is_masked():
    seat = make_seat(kind="poster", company="谷口", source_file="p.pdf")
    assert "谷口" not in body_of(ingest_poster_fragments(poster_fragments(), seat))


def test_poster_page_one_drops_the_poster():
    seat = make_seat(kind="poster", company="", source_file="p.pdf")
    masks = SeatMasks(pages=frozenset({1}))
    assert ingest_poster_fragments(poster_fragments(), seat, masks) == []


def test_poster_page_out_of_range_is_refused():
    seat = make_seat(kind="poster", company="", source_file="p.pdf")
    with pytest.raises(IngestError, match="mask_page_out_of_range"):
        ingest_poster_fragments(poster_fragments(), seat, SeatMasks(pages=frozenset({2})))


def test_slide_masks_hide_words_and_pages():
    pages = [["川辺三郎の発表"], ["川辺三郎が見た町"], ["生徒へのワーク"]]
    masks = SeatMasks(words=("川辺三郎",), pages=frozenset({1, 3}))
    utterances = ingest_slide_pages(pages, slide_seat(), masks)
    assert [u.section for u in utterances] == ["p2"]
    assert utterances[0].text == "この方が見た町"


def test_slide_page_out_of_range_is_refused():
    with pytest.raises(IngestError, match="mask_page_out_of_range"):
        ingest_slide_pages([["一枚"]], slide_seat(), SeatMasks(pages=frozenset({2})))


def test_slide_company_from_the_seat_table_is_masked():
    seat = slide_seat(company="架空研究所")
    utterances = ingest_slide_pages([["架空研究所で働く"]], seat, SeatMasks(pages=frozenset()))
    assert body_of(utterances) == "この職場で働く"


def test_word_split_across_slide_lines_stops_the_seat():
    masks = SeatMasks(words=("川辺三郎",))
    with pytest.raises(IngestError, match="forbidden_term_remains"):
        ingest_slide_pages([["川辺", "三郎"]], slide_seat(), masks)


def write_slide(path, pages):
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for line in pages:
        pdf.setFont("HeiseiKakuGo-W5", 14)
        pdf.drawString(50, 700, line)
        pdf.showPage()
    pdf.save()


def test_batch_runs_a_slide_seat_once_it_has_rows(tmp_path):
    write_slide(tmp_path / "slide01.pdf", ["川辺三郎の発表", "町の人が話しかけてくれた"])
    write_seats(tmp_path / "seats.tsv", [slide_seat()])
    masks_file(tmp_path, "C01\t語\t川辺三郎\nC01\tページ\t1\n")
    report = run(tmp_path)
    assert report.ingested_by_kind["cross"] == 1
    assert report.skipped_slide_seats == 0
    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    assert "川辺" not in raw
    assert "町の人" in raw


def test_batch_masks_an_article_word(tmp_path):
    write_article(tmp_path / "article01.docx")
    write_seats(tmp_path / "seats.tsv", [make_seat()])
    masks_file(tmp_path, "S01\t語\t鏡\n")
    run(tmp_path)
    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    assert "鏡の前" not in raw


def test_broken_masks_stop_main_without_printing_values(tmp_path, monkeypatch, capsys):
    write_seats(tmp_path / "seats.tsv", [make_seat()])
    masks_file(tmp_path, "X99\t語\t谷口\n")
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    assert main() == 2
    captured = capsys.readouterr()
    assert "谷口" not in captured.err + captured.out
    assert not (tmp_path / "ingested").exists()
