import json
import re

import pytest
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from conftest import (
    ADDRESS, COMPANY, INTERVIEWER, PERSON, PHONE, ROWS, add_table, make_seat, write_article,
)
from ebino.ingest.article_docx import (
    ArticleRows, cell_paragraphs, ingest_article, ingest_article_rows, row_number,
)
from ebino.ingest.scrub import normalize_for_match
from ebino.ingest.utterance import IngestError, VOICE_ARTICLE, VOICE_SPOKEN, make_id


@pytest.fixture
def utterances(tmp_path, seat):
    return ingest_article(write_article(tmp_path / "article01.docx"), seat)[0]


def dump(utterances):
    return normalize_for_match(json.dumps([u.to_dict() for u in utterances], ensure_ascii=False))


@pytest.mark.parametrize(
    "secret",
    [
        PERSON, "山川", "太郎", INTERVIEWER, "海野", "花子", COMPANY, "はるかぜ理容",
        PHONE, "123番地", "やまかわ", "example.invalid", "50歳", "表の外",
    ],
)
def test_removed_items_appear_nowhere(utterances, secret):
    assert normalize_for_match(secret) not in dump(utterances)


def test_used_rows_arrive(utterances):
    sections = {u.section for u in utterances}
    assert sections == {"キャッチコピー", "プロフィール", "仕事の内容", "本文タイトル", "本文", "ランキング"}


def test_name_becomes_this_person(utterances):
    assert any(u.text.startswith("この方は休みの日も") for u in utterances)


def test_company_becomes_workplace(utterances):
    work = next(u for u in utterances if u.section == "仕事の内容")
    assert work.text.startswith("この職場で")


def test_quotes_are_spoken_and_the_rest_is_article(utterances):
    body = [u for u in utterances if u.section == "本文"]
    spoken = [u for u in body if u.voice == VOICE_SPOKEN]
    assert [u.text for u in spoken] == ["この方と呼ばれるのが好きです"]
    assert any(u.voice == VOICE_ARTICLE for u in body)


def test_only_body_quotes_count_as_spoken(tmp_path, seat):
    rows = list(ROWS)
    rows[3] = ("3", "キャッチコピー", "「鏡」の話。", "")
    utterances, _ = ingest_article(write_article(tmp_path / "a.docx", rows), seat)
    catch = [u for u in utterances if u.section == "キャッチコピー"]
    assert [u.voice for u in catch] == [VOICE_ARTICLE]


def test_full_width_row_number_is_read(tmp_path, seat):
    rows = [tuple(r) for r in ROWS]
    rows = [("８", *r[1:]) if r[0] == "8" else r for r in rows]
    rows = [("４－２", *r[1:]) if r[0] == "4-2" else r for r in rows]
    utterances, _ = ingest_article(write_article(tmp_path / "a.docx", rows), seat)
    assert {"本文", "プロフィール"} <= {u.section for u in utterances}


@pytest.mark.parametrize("raw, key", [("９", "9"), ("４－１", "4-1"), ("4ー2", "4-2"), (" 10 ", "10")])
def test_row_number(raw, key):
    assert row_number(raw) == key


def test_unknown_row_is_dropped_and_counted(tmp_path, seat):
    rows = [*ROWS, ("15", "備考", "新しい欄に書いた秘密", "")]
    utterances, stats = ingest_article(write_article(tmp_path / "a.docx", rows), seat)
    assert "秘密" not in dump(utterances)
    assert stats.dropped_rows >= 1


def test_third_column_is_content_even_with_extra_columns(tmp_path, seat):
    rows = [(*r, "") for r in ROWS]
    utterances, _ = ingest_article(write_article(tmp_path / "a.docx", rows), seat)
    assert any(u.section == "本文" for u in utterances)


def test_two_tables_need_a_choice(tmp_path):
    path = tmp_path / "a.docx"
    document = Document()
    draft = [tuple(r) for r in ROWS]
    draft[3] = ("3", "キャッチコピー", "下書きの言葉。", "")
    add_table(document, draft)
    add_table(document, ROWS)
    document.save(path)

    with pytest.raises(IngestError, match="table_choice_required"):
        ingest_article(path, make_seat())
    final, _ = ingest_article(path, make_seat(table_no=2))
    assert "下書き" not in dump(final)
    first, _ = ingest_article(path, make_seat(table_no=1))
    assert "下書き" in dump(first)


def test_no_table_fails(tmp_path, seat):
    path = tmp_path / "a.docx"
    Document().save(path)
    with pytest.raises(IngestError, match="no_table"):
        ingest_article(path, seat)


def test_missing_name_row_fails_closed(seat):
    with pytest.raises(IngestError, match="name_row_missing"):
        ingest_article_rows(ArticleRows({"8": ["本文の文。"]}), seat)


def test_missing_body_fails(seat):
    with pytest.raises(IngestError, match="body_row_missing"):
        ingest_article_rows(ArticleRows({"1": [PERSON], "3": ["キャッチコピー。"]}), seat)


@pytest.mark.parametrize("key", ["13", "14"])
def test_company_page_without_body_passes_on_row_13_or_14(key):
    rows = {"1": ["森田 健"], key: ["森田が始めた、木の家の会社です。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), make_seat(display_name=""))
    assert [u.text for u in utterances] == ["この方が始めた、木の家の会社です。"]


def test_company_page_without_head_name_still_stops():
    with pytest.raises(IngestError, match="name_row_missing"):
        ingest_article_rows(ArticleRows({"13": ["会社の紹介。"]}), make_seat(display_name=""))


def test_variant_the_mask_misses_stops_the_article(seat):
    # A full-width company name differs from the seat table, so no mask fires.
    latin = make_seat(company="ABC理容")
    rows = {"1": [PERSON], "8": ["ＡＢＣ理容で働く。"]}
    with pytest.raises(IngestError, match="forbidden_term_remains"):
        ingest_article_rows(ArticleRows(rows), latin)


def test_error_text_never_quotes_the_document(seat):
    latin = make_seat(company="ABC理容")
    with pytest.raises(IngestError) as caught:
        ingest_article_rows(ArticleRows({"1": [PERSON], "8": ["ＡＢＣ理容で働く。"]}), latin)
    assert re.fullmatch(r"[a-z_]+", str(caught.value))


def test_repeated_sentence_becomes_one(seat):
    sentence = "朝の店を開ける時間が好きです。"
    rows = {"1": [PERSON], "8": [sentence + sentence]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    assert [u.text for u in utterances] == [sentence]


def test_repeated_paragraph_becomes_one(seat):
    rows = {"1": [PERSON], "8": ["同じ段落がここにある文です。", "同じ段落がここにある文です。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    assert len(utterances) == 1


@pytest.mark.parametrize(
    "names",
    [
        ["山川 太郎", "海野 花子"],
        ["山川 太郎", "海野 花子", "谷 一"],
        ["山川 太郎、海野 花子"],
    ],
)
def test_every_person_in_the_name_row_is_masked(names):
    seat = make_seat(display_name="")
    body = "山川太郎さんと海野さん、花子さん、谷さんが話す。太郎は笑う。"
    rows = {"1": names, "8": [body]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    text = dump(utterances)
    for name in names:
        for part in re.split(r"[\s、]+", name):
            assert part not in text


def test_two_people_never_merge_into_one_masked_name(seat):
    rows = {"1": ["山川 太郎", "海野 花子"], "8": ["山川太郎と海野花子が話す。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), make_seat(display_name=""))
    assert utterances[0].text == "この方と この方が話す。".replace(" ", "")


def test_company_page_head_name_is_masked():
    rows = {
        "1": ["森田 健"],
        "8": ["森田社長は地元の木を使う。"],
        "13": ["森田が始めた会社です。"],
    }
    utterances, _ = ingest_article_rows(ArticleRows(rows), make_seat(display_name=""))
    assert "森田" not in dump(utterances)


def test_one_character_family_name_before_kanji_is_flagged_not_masked():
    # SPEC 14-28: left for a human check, so the count must say so.
    rows = {"1": ["森 健"], "8": ["森社長は地元の木を使う。"]}
    utterances, stats = ingest_article_rows(ArticleRows(rows), make_seat(display_name=""))
    assert stats.single_char_name
    assert utterances[0].text == "森社長は地元の木を使う。"


@pytest.mark.parametrize(
    "key, section, voice",
    [
        ("11", "高校生に一言", "spoken"),
        ("12", "求める人材", "company"),
        ("13", "会社PR", "company"),
        ("14", "先輩社員からのメッセージ", "senior"),
    ],
)
def test_last_years_extra_rows_carry_their_source(seat, key, section, voice):
    rows = {"1": [PERSON], "8": ["本文の文。"], key: ["行の言葉です。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    extra = [u for u in utterances if u.section == section]
    assert [(u.voice, u.text) for u in extra] == [(voice, "行の言葉です。")]


def test_source_notes_for_each_written_voice():
    from ebino.ingest.utterance import SOURCE_NOTES

    assert SOURCE_NOTES == {
        "article": "取材記事（本人確認済み）",
        "company": "会社の紹介文（本人確認済み）",
        "senior": "先輩社員の言葉（本人確認済み）",
    }


def test_same_piece_in_two_paragraphs_is_one_utterance_with_one_id(seat):
    rows = {"1": [PERSON], "8": ["朝に「店を開けます」と言う。", "夜も「店を開けます」と言う。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    pieces = [u for u in utterances if u.text == "店を開けます"]
    assert len(pieces) == 1
    assert pieces[0].paragraph == "朝に「店を開けます」と言う。"
    assert len({u.id for u in utterances}) == len(utterances)


def test_text_box_is_read_once_without_its_fallback_copy(tmp_path):
    document = Document()
    cell = document.add_table(rows=1, cols=1).rows[0].cells[0]
    run = cell.paragraphs[0].add_run()._r
    run.append(
        parse_xml(
            f'<mc:AlternateContent {nsdecls("w")}'
            ' xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"'
            ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
            "<mc:Choice Requires=\"wps\"><w:drawing><wps:txbx><w:txbxContent>"
            "<w:p><w:r><w:t>枠の中の文</w:t></w:r></w:p>"
            "</w:txbxContent></wps:txbx></w:drawing></mc:Choice>"
            "<mc:Fallback><w:pict><w:txbxContent>"
            "<w:p><w:r><w:t>枠の中の文</w:t></w:r></w:p>"
            "</w:txbxContent></w:pict></mc:Fallback>"
            "</mc:AlternateContent>"
        )
    )
    assert cell_paragraphs(cell) == ["枠の中の文"]


def test_ids_survive_a_rerun(tmp_path, seat):
    path = write_article(tmp_path / "article01.docx")
    first = [u.id for u in ingest_article(path, seat)[0]]
    second = [u.id for u in ingest_article(path, seat)[0]]
    assert first == second
    assert len(set(first)) == len(first)


def test_id_shape_and_normalization():
    identifier = make_id("adult", "a.docx", "朝 の 店")
    assert re.fullmatch(r"adult-[0-9a-f]{8}-[0-9a-f]{8}", identifier)
    assert identifier == make_id("adult", "a.docx", "朝の店")


def test_address_constant_is_really_in_the_fixture():
    assert any(ADDRESS in cell for row in ROWS for cell in row)
