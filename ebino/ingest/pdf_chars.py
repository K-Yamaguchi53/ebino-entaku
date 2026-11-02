"""Turn look-alike kanji code points from PDFs into ordinary kanji (SPEC 14-48).

Some PDFs carry 「⽬」 (a Kangxi radical) where 「目」 is meant. They look the
same, but a name written that way slips past the masks, 「⽬的」 is not read as
a heading, and screen quotes stop matching what students type.

Only three ranges change; everything else (full-width letters, ①, brackets)
is left exactly as it was. Each character stays one character, so per-character
positions still line up.
"""

import unicodedata

KANGXI_RADICALS = (0x2F00, 0x2FDF)
CJK_COMPATIBILITY_IDEOGRAPHS = (0xF900, 0xFAFF)
CJK_RADICALS_SUPPLEMENT = (0x2E80, 0x2EFF)

# NFKC does not fold all of the supplement, so these go through a table. The
# ones seen in the real data first (SPEC 14-48), then a few common family-name
# radicals of the same kind.
SUPPLEMENT_TABLE = {
    "⻄": "西",
    "⻘": "青",
    "⻲": "亀",
    "⻑": "長",
    "⻁": "虎",
    "⻆": "角",
    "⻝": "食",
    "⻤": "鬼",
    "⻨": "麦",
    "⻩": "黄",
    "⻫": "斉",
    "⻭": "歯",
    "⻯": "竜",
}


def _in(ch: str, bounds: tuple[int, int]) -> bool:
    return bounds[0] <= ord(ch) <= bounds[1]


def _fold_char(ch: str) -> str:
    if _in(ch, CJK_RADICALS_SUPPLEMENT):
        if ch in SUPPLEMENT_TABLE:
            return SUPPLEMENT_TABLE[ch]
    elif not (_in(ch, KANGXI_RADICALS) or _in(ch, CJK_COMPATIBILITY_IDEOGRAPHS)):
        return ch
    folded = unicodedata.normalize("NFKC", ch)
    return folded if len(folded) == 1 else ch


def fold_radicals(text: str) -> str:
    return "".join(_fold_char(ch) for ch in text)


def leftover_supplement_chars(text: str) -> int:
    """Supplement characters neither the table nor NFKC could fold.

    Counted in the batch report so a missing table entry gets noticed.
    """
    return sum(_in(ch, CJK_RADICALS_SUPPLEMENT) for ch in text)
