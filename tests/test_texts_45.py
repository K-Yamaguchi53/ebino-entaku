"""直し45: the screen's new words are in texts/ (叩き台 for the teacher); a
table with a row missing stops the app, as every table of texts/ does."""


import pytest

from ebino import texts

TABLES = [
    (texts.TRAIL_WORDS, texts.TRAIL_WORD_IDS),
    (texts.ONE_COACH_CHOICES, texts.ONE_COACH_CHOICE_IDS),
    (texts.ONE_COACH_WORDS, texts.ONE_COACH_WORD_IDS),
    (texts.TRAIL_MARKS, texts.TRAIL_MARK_IDS),
    (texts.TRAIL_MARK_WORDS, texts.TRAIL_MARK_WORD_IDS),
    (texts.DIRECTION_WORDS, texts.DIRECTION_WORD_IDS),
]


@pytest.mark.parametrize("name, ids", TABLES)
def test_each_new_table_has_its_rows_and_one_missing_stops(name, ids, tmp_path, monkeypatch):
    assert list(texts.id_table(name, ids)) == list(ids)
    lines = (texts.TEXTS_DIR / f"{name}.tsv").read_text(encoding="utf-8").splitlines()
    (tmp_path / f"{name}.tsv").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    with pytest.raises(ValueError):
        texts.id_table(name, ids)


def test_the_one_line_files_are_there():
    assert texts.load_text(texts.AI_ROLE_SUFFIX) == "（AI）"
    assert texts.load_lines(texts.AI_ABSTRACT_WORDS) == ["価値観", "本質", "視点", "アイデンティティ", "自己実現"]
