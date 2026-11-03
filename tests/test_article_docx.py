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
from ebino.ingest.utterance import (
    IngestError, VOICE_ARTICLE, VOICE_OWN, VOICE_SPOKEN, make_id, split_voice,
)


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


# A PDF's printed lines, each kept as a paragraph (13 characters to a line).
WRAP_1 = "うちの店では、職員一人ひと"
WRAP_2 = "りの暮らしに合わせて休みを"
WRAP_END = "決めています。"
FULL_LINE = "休みは店で決めて取ります。"  # The width, but it ends a sentence.


def body_texts(body):
    utterances, stats = ingest_article_rows(ArticleRows({"1": [PERSON], "8": body}), make_seat())
    return [u.text for u in utterances], stats


def test_lines_of_the_line_width_become_one_paragraph():
    assert len(WRAP_1) == len(WRAP_2) == len(FULL_LINE) == 13
    texts, stats = body_texts([WRAP_1, WRAP_2, WRAP_END])
    assert texts == [WRAP_1 + WRAP_2 + WRAP_END]
    assert stats.wrapped_lines_joined == 2


def test_a_short_heading_does_not_join_the_body_after_it():
    texts, _ = body_texts(["休みの決め方", WRAP_1, WRAP_2, WRAP_END])
    assert texts == ["休みの決め方", WRAP_1 + WRAP_2 + WRAP_END]


def test_a_line_that_ends_a_sentence_does_not_join_the_next():
    texts, stats = body_texts([WRAP_1, WRAP_2, WRAP_END, FULL_LINE, "朝は早く店を開けます。"])
    assert texts == [WRAP_1 + WRAP_2 + WRAP_END, FULL_LINE, "朝は早く店を開けます。"]
    assert stats.wrapped_lines_joined == 2


def test_one_line_of_a_length_alone_sets_no_width():
    # A single unended paragraph could be a heading: nothing is joined.
    texts, stats = body_texts(["店の休みの決め方について", "休みは決めて取ります。"])
    assert texts == ["店の休みの決め方について", "休みは決めて取ります。"]
    assert stats.wrapped_lines_joined == 0


def test_rows_are_not_joined_into_each_other():
    rows = {"1": [PERSON], "3": [WRAP_1], "8": [WRAP_2, WRAP_END]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), make_seat())
    assert [u.text for u in utterances] == [WRAP_1, WRAP_2 + WRAP_END]


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


# --- SPEC 14-46: the older booklets, copied from paper into the same table ------

SIX = ["坂本", "山川 太郎", "海野 花子", "谷口 一郎", "川辺 三郎", "森田 健"]
SIX_BODY = (
    "坂本さんと山川さん、花子さん、谷口一郎さん、川辺さん、森田社長が並ぶ。"
    "「坂本です」と笑う。三郎さんは山川太郎さんの隣にいる。"
)


def write_booklet_article(path, rows):
    """rows: (number, item, [paragraphs]). Each paragraph is a real w:p in the cell."""
    document = Document()
    table = document.add_table(rows=len(rows), cols=3)
    for row, (number, item, paragraphs) in zip(table.rows, rows):
        row.cells[0].text = number
        row.cells[1].text = item
        cell = row.cells[2]
        if paragraphs:
            cell.paragraphs[0].text = paragraphs[0]
            for paragraph in paragraphs[1:]:
                cell.add_paragraph(paragraph)
    document.save(path)
    return path


def name_pieces(names):
    return {piece for name in names for piece in re.split(r"[\s、]+", name) if len(piece) >= 2}


@pytest.mark.parametrize("name_row", [SIX, ["、".join(SIX)]], ids=["paragraphs", "one_line"])
def test_six_people_in_the_name_row_are_all_masked(tmp_path, name_row):
    rows = [
        ("1", "名前", name_row),
        ("3", "キャッチコピー", ["六人で守る店。"]),
        ("8", "本文", [SIX_BODY]),
        ("10", "取材者名", [INTERVIEWER]),
    ]
    path = write_booklet_article(tmp_path / "R6_s02L.docx", rows)
    utterances, _ = ingest_article(path, make_seat(seat_id="D01", display_name="坂本さん・山川さん"))
    text = dump(utterances)
    for piece in name_pieces(SIX):
        assert piece not in text
    assert "坂本です" not in text and "この方です" in text


def test_empty_interviewer_row_does_not_stop(tmp_path):
    rows = [
        ("1", "名前", [PERSON]),
        ("8", "本文", ["山川さんは朝から店に立つ。"]),
        ("10", "取材者名", []),
    ]
    path = write_booklet_article(tmp_path / "R6_s03L.docx", rows)
    utterances, _ = ingest_article(path, make_seat(seat_id="D02"))
    assert [u.text for u in utterances] == ["この方は朝から店に立つ。"]


def test_missing_interviewer_row_does_not_stop(seat):
    utterances, _ = ingest_article_rows(ArticleRows({"1": [PERSON], "8": ["本文の文。"]}), seat)
    assert [u.text for u in utterances] == ["本文の文。"]


def company_page_rows(name_paragraphs):
    return [
        ("1", "名前", name_paragraphs),
        ("5", "仕事の内容", ["坂本工務店で家を建てる。"]),
        ("8", "本文", []),
        ("10", "取材者名", []),
        ("13", "会社PR", ["坂本が始めた、木の家の会社です。"]),
        ("14", "先輩社員からのメッセージ", ["「坂本社長に教わった」と話す先輩もいる。"]),
    ]


def test_old_company_page_with_empty_body_passes(tmp_path):
    path = write_booklet_article(tmp_path / "R5_c01.docx", company_page_rows(["坂本 一"]))
    seat = make_seat(seat_id="D03", company="坂本工務店", display_name="")
    utterances, _ = ingest_article(path, seat)
    assert {u.section for u in utterances} == {"仕事の内容", "会社PR", "先輩社員からのメッセージ"}
    assert "坂本" not in dump(utterances)


def test_old_company_page_with_empty_name_row_stops(tmp_path):
    path = write_booklet_article(tmp_path / "R5_c02.docx", company_page_rows([]))
    seat = make_seat(seat_id="D04", company="坂本工務店", display_name="")
    with pytest.raises(IngestError, match="name_row_missing"):
        ingest_article(path, seat)


def test_merged_seat_masks_every_article_s_people(tmp_path):
    # Two booklets' articles for one company, rows appended paragraph by paragraph.
    rows = [
        ("1", "名前", ["山川 太郎", "坂本 一"]),
        ("8", "本文", ["山川さんは店を継いだ。", "坂本さんは店を始めた。"]),
        ("10", "取材者名", [INTERVIEWER]),
    ]
    path = write_booklet_article(tmp_path / "M_B05.docx", rows)
    utterances, _ = ingest_article(path, make_seat(seat_id="B05"))
    assert [u.text for u in utterances] == ["この方は店を継いだ。", "この方は店を始めた。"]


# --- SPEC 14-50: the teacher's own article --------------------------------------

TEACHER = "海野 一郎"


def teacher_rows():
    return [
        ("1", "名前", [TEACHER]),
        ("2", "ふりがな", ["うみの いちろう"]),
        ("3", "キャッチコピー", ["「寄り道」をすすめたい。"]),
        ("4-2", "プロフィール", ["海野は架空の町で育った。"]),
        ("5", "仕事の内容", ["高校で「地理」を教えている。"]),
        ("7", "本文タイトル", ["遠回りの話"]),
        ("8", "本文", ["君たちに「急げ」とは言わない。", "海野は「迷っていい」と言いたい。"]),
        ("11", "高校生に一言", ["「なぜ」を大事に。"]),
    ]


@pytest.fixture
def teacher_utterances(tmp_path):
    path = write_booklet_article(tmp_path / "teacher01.docx", teacher_rows())
    seat = make_seat(seat_id="O02", kind="outsider_teacher", company="", display_name="",
                     source_file="teacher01.docx")
    return ingest_article(path, seat)[0]


def test_teacher_article_is_all_own_words_shown_as_the_teacher_s_article(teacher_utterances):
    assert {u.voice for u in teacher_utterances} == {VOICE_OWN}
    assert {u.note for u in teacher_utterances} == {"先生が書いた記事"}


def test_teacher_article_is_not_split_at_quotes(teacher_utterances):
    body = [u.text for u in teacher_utterances if u.section == "本文"]
    assert body == ["君たちに「急げ」とは言わない。", "この方は「迷っていい」と言いたい。"]
    assert [u.text for u in teacher_utterances if u.section == "高校生に一言"] == ["「なぜ」を大事に。"]


def test_teacher_name_is_masked_and_reading_row_is_dropped(teacher_utterances):
    text = dump(teacher_utterances)
    assert "海野" not in text and "一郎" not in text and "うみの" not in text


def test_interview_articles_keep_their_note(utterances):
    assert {u.note for u in utterances if u.voice == VOICE_ARTICLE} == {"取材記事（本人確認済み）"}
    assert {u.note for u in utterances if u.voice == VOICE_SPOKEN} == {""}


# --- SPEC 14-50: only a quoting と or って makes 「」 speech -----------------------


@pytest.mark.parametrize(
    "paragraph, pieces",
    [
        (
            "先生に「好きにやれ」と言われた。",
            [("article", "先生に"), ("spoken", "好きにやれ"), ("article", "と言われた。")],
        ),
        ("「店を継ぐ」と思った。", [("spoken", "店を継ぐ"), ("article", "と思った。")]),
        ("「やるしかない」って笑う。", [("spoken", "やるしかない"), ("article", "って笑う。")]),
        ("最後に話した。「また来てね」", [("article", "最後に話した。"), ("spoken", "また来てね")]),
        ("「釣り部」というサークルに入った。", [("article", "「釣り部」というサークルに入った。")]),
        ("君たちに「近道」を言わないと決めた。", [("article", "君たちに「近道」を言わないと決めた。")]),
        ("「木工部」に入りたくて高校を選んだ。", [("article", "「木工部」に入りたくて高校を選んだ。")]),
        ("「朝市」といった行事がある。", [("article", "「朝市」といった行事がある。")]),
        ("「漁」とか「畑」とか、何でもやる。", [("article", "「漁」とか「畑」とか、何でもやる。")]),
        ("「川の会」との縁が長い。", [("article", "「川の会」との縁が長い。")]),
        ("「仕事」とは何か考えた。", [("article", "「仕事」とは何か考えた。")]),
        ("店の名は「はるかぜ」。", [("article", "店の名は「はるかぜ」。")]),
        (
            "「木工部」で学び、「続けて」と言われた。",
            [("article", "「木工部」で学び、"), ("spoken", "続けて"), ("article", "と言われた。")],
        ),
    ],
)
def test_only_a_quoting_to_or_tte_makes_a_quote_speech(paragraph, pieces):
    assert split_voice(paragraph) == pieces


# --- SPEC 14-50-2: だと・そう before a verb of saying -------------------------------


@pytest.mark.parametrize(
    "paragraph, pieces",
    [
        ("「朝が一番好き」だと語る。", [("spoken", "朝が一番好き"), ("article", "だと語る。")]),
        ("「店は町の台所」だと話した。", [("spoken", "店は町の台所"), ("article", "だと話した。")]),
        ("「失敗も財産」だと言う。", [("spoken", "失敗も財産"), ("article", "だと言う。")]),
        ("「ここが自分の場所」だと思った。", [("spoken", "ここが自分の場所"), ("article", "だと思った。")]),
        ("「まずやってみる」そう語る。", [("spoken", "まずやってみる"), ("article", "そう語る。")]),
        ("「船は家族」そう話してくれた。", [("spoken", "船は家族"), ("article", "そう話してくれた。")]),
        ("「また来いよ」そう言って手を振った。", [("spoken", "また来いよ"), ("article", "そう言って手を振った。")]),
        ("「戻ってよかった」そう思う。", [("spoken", "戻ってよかった"), ("article", "そう思う。")]),
        ("「なんとかなる」そう笑った。", [("spoken", "なんとかなる"), ("article", "そう笑った。")]),
        ("「町の宝」だという。", [("article", "「町の宝」だという。")]),
        ("「町の宝」だそうだ。", [("article", "「町の宝」だそうだ。")]),
        ("「町の宝」だと話題になった。", [("article", "「町の宝」だと話題になった。")]),
        ("「負けたくない」そんな思いで続けた。", [("article", "「負けたくない」そんな思いで続けた。")]),
        ("「負けたくない」そのような気持ちだった。", [("article", "「負けたくない」そのような気持ちだった。")]),
        ("「朝市」そうした行事が好きだ。", [("article", "「朝市」そうした行事が好きだ。")]),
    ],
)
def test_dato_and_sou_before_saying_make_a_quote_speech(paragraph, pieces):
    assert split_voice(paragraph) == pieces


# --- SPEC 14-50-2: 「」 in a row follow the last one ------------------------------


@pytest.mark.parametrize(
    "paragraph, pieces",
    [
        (
            "先輩に「焦るな」「よく見ろ」と言われた。",
            [("article", "先輩に"), ("spoken", "焦るな"), ("spoken", "よく見ろ"), ("article", "と言われた。")],
        ),
        (
            "「よし」「行こう」「今だ」そう笑う。",
            [("spoken", "よし"), ("spoken", "行こう"), ("spoken", "今だ"), ("article", "そう笑う。")],
        ),
        ("最後にひと言。「ありがとう」「またね」", [("article", "最後にひと言。"), ("spoken", "ありがとう"), ("spoken", "またね")]),
        ("「海」「山」というお店を開いた。", [("article", "「海」「山」というお店を開いた。")]),
        ("「海」「山」の二つの店がある。", [("article", "「海」「山」の二つの店がある。")]),
        (
            "「海」や「山」で迷い、「両方やれ」と言われた。",
            [("article", "「海」や「山」で迷い、"), ("spoken", "両方やれ"), ("article", "と言われた。")],
        ),
    ],
)
def test_quotes_in_a_row_follow_the_last_one(paragraph, pieces):
    assert split_voice(paragraph) == pieces


# --- SPEC 14-50-3: 「」 joined by と follow the last one --------------------------


@pytest.mark.parametrize(
    "paragraph, pieces",
    [
        (
            "先輩に「焦るな」と「よく見ろ」と言われた。",
            [("article", "先輩に"), ("spoken", "焦るな"), ("spoken", "よく見ろ"), ("article", "と言われた。")],
        ),
        ("「海」と「山」で迷い、店を開いた。", [("article", "「海」と「山」で迷い、店を開いた。")]),
        ("店の名前は「海」と「山」だ。", [("article", "店の名前は「海」と「山」だ。")]),
        ("店の名前は「海」 と　「山」だ。", [("article", "店の名前は「海」 と　「山」だ。")]),
        (
            "「海」や「山」で迷い、「両方やれ」と言われた。",
            [("article", "「海」や「山」で迷い、"), ("spoken", "両方やれ"), ("article", "と言われた。")],
        ),
    ],
)
def test_quotes_joined_by_to_follow_the_last_one(paragraph, pieces):
    assert split_voice(paragraph) == pieces


# --- SPEC 14-50-4: article pieces of only particles and marks are dropped -------


@pytest.mark.parametrize(
    "paragraph, pieces",
    [
        (
            "先輩に「焦るな」と「よく見ろ」と言われた。",
            [("article", "先輩に"), ("spoken", "焦るな"), ("spoken", "よく見ろ"), ("article", "と言われた。")],
        ),
        ("最後に父が「ありがとう」と。", [("article", "最後に父が"), ("spoken", "ありがとう")]),
        ("「行くぞ」と、「おう」と 。", [("spoken", "行くぞ"), ("spoken", "おう")]),
        ("「好きにやれ」と言われた。", [("spoken", "好きにやれ"), ("article", "と言われた。")]),
        ("朝が好きだと「店主」と話す。", [("article", "朝が好きだと"), ("spoken", "店主"), ("article", "と話す。")]),
    ],
)
def test_article_pieces_of_only_particles_and_marks_are_dropped(paragraph, pieces):
    assert split_voice(paragraph) == pieces


def test_a_quote_kept_in_the_article_is_one_piece_with_one_id(seat):
    paragraph = "「釣り部」というサークルに入った。君たちに「近道」を言わないと決めた。"
    rows = {"1": [PERSON], "8": [paragraph]}
    first, _ = ingest_article_rows(ArticleRows(rows), seat)
    again, _ = ingest_article_rows(ArticleRows(rows), seat)
    assert [(u.voice, u.text) for u in first] == [("article", paragraph)]
    assert first[0].id == make_id(seat.kind, seat.source_file, paragraph)
    assert [u.id for u in first] == [u.id for u in again]


def test_ids_of_split_pieces_follow_the_same_rule(seat):
    rows = {"1": [PERSON], "8": ["先生に「好きにやれ」と言われた。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), seat)
    assert [u.id for u in utterances] == [
        make_id(seat.kind, seat.source_file, text) for text in ("先生に", "好きにやれ", "と言われた。")
    ]


def test_address_constant_is_really_in_the_fixture():
    assert any(ADDRESS in cell for row in ROWS for cell in row)
