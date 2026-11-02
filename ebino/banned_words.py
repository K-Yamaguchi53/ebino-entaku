"""Words a model's sentence to a student must not hold (SPEC 5-2, 14-14).

A first list made by Claude Code for the teacher to add to and take from.
They are commands, advice, judgments of the student, and steering toward a
path (SPEC 1-1, 3). Checked after NFKC with spaces removed, as a part of the
sentence, so 向いている also catches 向いているかも.
"""

from .ingest.scrub import normalize_for_match

BANNED_WORDS = (
    # Telling or nudging the student what to do.
    # てみたら covers してみたら, やってみたら, 確かめてみたら; でみたら covers 読んでみたら.
    "しなさい", "てみたら", "てみては", "てみよう", "でみたら", "でみては", "でみよう",
    "したらいい", "すればいい", "するといい", "した方がいい", "したほうがいい", "べき",
    "おすすめ", "お勧め", "お薦め", "オススメ",
    # Judging the student or sorting them.
    "よくできました", "すごい", "すばらしい", "素晴らしい", "えらい", "偉い", "さすが",
    "頑張", "がんば", "正解", "間違って", "向いている", "向いてる", "向き不向き",
    "適性", "才能", "タイプ", "性格",
)
_NORMALIZED = tuple(normalize_for_match(word) for word in BANNED_WORDS)


def banned_in(text: str) -> bool:
    body = normalize_for_match(text)
    return any(word in body for word in _NORMALIZED)
