from conftest import make_seat
from ebino.ingest.masks import SeatMasks
from ebino.ingest.scrub import name_parts
from ebino.ingest.slides_pdf import collapse_lines, ingest_slide_pages
from ebino.ingest.utterance import VOICE_OWN


def slide_seat():
    return make_seat(seat_id="C01", kind="cross", company="", source_file="slide01.pdf")


def test_decorative_repeats_become_one_line():
    pages = [["おどろいた", "おどろいた", "お ど ろ い た", "街が広い"]]
    assert collapse_lines(pages) == [["おどろいた", "街が広い"]]


def test_repeats_across_pages_become_one():
    assert collapse_lines([["同じ行"], ["同じ行", "次の行"]]) == [["同じ行"], ["次の行"]]


def test_names_and_money_are_removed():
    pages = [["川辺三郎の発表", "費用は30万円でした", "変わった"]]
    masks = SeatMasks(words=name_parts("川辺 三郎").terms)
    utterances = ingest_slide_pages(pages, slide_seat(), masks)
    text = utterances[0].text
    assert "川辺" not in text and "三郎" not in text
    assert "30万円" not in text
    assert "変わった" in text


def test_work_pages_can_be_skipped():
    pages = [["自分の話"], ["生徒へのワーク"]]
    utterances = ingest_slide_pages(pages, slide_seat(), SeatMasks(pages=frozenset({2})))
    assert [u.section for u in utterances] == ["p1"]


def test_slide_words_are_the_authors_own():
    utterances = ingest_slide_pages([["行くための方法"]], slide_seat())
    assert utterances[0].voice == VOICE_OWN


def test_empty_page_gives_nothing():
    assert ingest_slide_pages([[]], slide_seat()) == []
