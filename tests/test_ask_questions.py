"""直し34-1: the questions offered at one to one, the teacher's draft in
texts/ask_questions.txt, one an item: every line read, and each item's name
one of the names the words are taken in under (an article's rows, a
poster's roles) or one of the axes of the words with pages only. The file
is the teacher's words: the banned words' check is not run on it, as on the
question examples."""

from ebino import one_to_one, texts
from ebino.ingest.article_docx import USED_ROWS
from ebino.ingest.poster_pdf import ROLES

TEXT = (texts.TEXTS_DIR / "ask_questions.txt").read_text(encoding="utf-8")


def test_every_line_is_read():
    asked = texts.ask_questions()
    lines = [line for line in TEXT.splitlines() if line.strip()]
    assert sum(len(rows) for rows in asked.values()) == len(lines) - 1  # The header row.
    assert set(asked) == set(one_to_one.GROUPS)
    for rows in asked.values():
        for item, question in rows:
            assert item and question.endswith(("？", "。"))


def test_the_items_are_the_names_the_words_come_under():
    asked = texts.ask_questions()
    article = [item for item, _ in asked[one_to_one.GROUP_ARTICLE]]
    rows = set(USED_ROWS.values())
    for item in article:
        assert item in rows, item
    # The body's title and the body are one item; the catch copy and the ranking have no question here.
    assert "本文タイトル" not in article and "本文" in article
    for none in one_to_one.ARTICLE_NO_QUESTION:
        assert none not in article
    assert [item for item, _ in asked[one_to_one.GROUP_POSTER]] == list(ROLES)
    assert tuple(item for item, _ in asked[one_to_one.GROUP_CROSS]) == one_to_one.CROSS_AXES
    assert tuple(item for item, _ in asked[one_to_one.GROUP_OUTSIDER]) == one_to_one.OUTSIDER_AXES


def test_the_teachers_words_as_given():
    asked = dict(texts.ask_questions()[one_to_one.GROUP_POSTER])
    assert asked["背景と課題"] == "どうしてこのテーマにしたの？"
    assert dict(texts.ask_questions()[one_to_one.GROUP_ARTICLE])["本文"] == "この仕事の話を、もっと聞かせてください。"
