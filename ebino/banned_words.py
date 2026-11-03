"""Words a model's sentence to a student must not hold (SPEC 5-2, 14-14).

A first list made by Claude Code, then widened by the teacher, who adds to
it and takes from it. They are commands, advice, judgments of the student,
and steering toward a path (SPEC 1-1, 3). Checked after NFKC with spaces
removed, as a part of the sentence, so 向いてい also catches 向いていない.
Only the moderator's own words are checked, not the record's words it puts
in 「」『』 (reflection.checked).
"""

from .ingest.scrub import normalize_for_match

BANNED_WORDS = (
    # Telling or nudging the student what to do.
    # てみたら covers してみたら, やってみたら, 確かめてみたら; でみたら covers 読んでみたら.
    # てみて covers 聞いてみて, てみては; でみて covers 読んでみて.
    "しなさい", "てみたら", "てみては", "てみよう", "でみたら", "でみては", "でみよう",
    "てみて", "でみて", "ましょう",
    "したらいい", "すればいい", "するといい", "した方がいい", "したほうがいい", "べき",
    "といい", "たらいい", "だらいい", "ればいい",
    "方がいい", "ほうがいい", "方が良い", "ほうが良い", "てほしい",
    "しよう", "行こう", "聞こう", "確かめよう", "読もう", "会おう",
    "おすすめ", "お勧め", "お薦め", "オススメ",
    # Judging the student or sorting them.
    "よくできました", "すごい", "すばらしい", "素晴らしい", "えらい", "偉い", "さすが",
    "偉か", "えらか", "素敵", "立派", "いい問い", "良い問い", "よく考え",
    "頑張", "がんば", "正解", "間違って", "向き不向き",
    # 向いてい covers 向いている and 向いていない.
    "向いてい", "向いてな", "向いてる", "向かない",
    "適性", "才能", "タイプ", "性格",
    # Steering toward a path.
    "進路",
)
_NORMALIZED = tuple(normalize_for_match(word) for word in BANNED_WORDS)


def banned_in(text: str) -> bool:
    body = normalize_for_match(text)
    return any(word in body for word in _NORMALIZED)
