"""Remove personal information before any text can reach a model.

Everything here is plain code on purpose: the model only ever reads the output.
Errors never carry document text, because their messages get pasted into chat.
"""

import re
import unicodedata
from dataclasses import dataclass

PERSON_MASK = "この方"
INTERVIEWER_MASK = "取材者"
COMPANY_MASK = "この職場"

_D = "0-9０-９"
_DASH = r"\-－−‐‑–—ーｰ"
_SEP = rf"[{_DASH}\s　]"
_KANJI_NUM = "一二三四五六七八九十百千"
_KANJI = r"㐀-鿿"

_LABELLED_PHONE = re.compile(
    rf"(?:電話番号|電話|TEL|Tel|tel|ＴＥＬ|℡|FAX|Fax|fax|ＦＡＸ|ファックス)"
    rf"[\s　]*[:：]?[\s　]*[(（]?[{_D}]{{2,5}}[)）]?{_SEP}?[{_D}]{{1,4}}(?:{_SEP}?[{_D}]{{3,4}})?"
    rf"(?![{_D}])"
)
_PHONE = re.compile(
    rf"(?<![{_D}])"
    rf"(?:[(（][0０][{_D}]{{1,4}}[)）]{_SEP}?[{_D}]{{1,4}}{_SEP}?[{_D}]{{3,4}}"
    rf"|[0０][{_D}]{{1,4}}(?:{_SEP}|[(（])[{_D}]{{1,4}}(?:{_SEP}|[)）])[{_D}]{{3,4}}"
    rf"|[0０][{_D}]{{9,10}})"
    rf"(?![{_D}])"
)
_ADDRESS = re.compile(
    rf"(?:[{_D}]+|[{_KANJI_NUM}]+)(?:丁目|番地)"
    rf"(?:[{_D}{_KANJI_NUM}]+(?:番地|番|号)?)?(?:[{_DASH}][{_D}]+)*"
    rf"|[{_D}]+番[{_D}]+号?"
    rf"|(?<=[{_KANJI}])[{_D}]{{1,5}}(?:[{_DASH}][{_D}]{{1,5}}){{1,3}}(?![{_D}])"
)
_MONEY = re.compile(
    rf"(?:約|およそ|計|合計)?(?:[{_D},，.．]+|[{_KANJI_NUM}]+)"
    r"(?:億|万|千|百)*(?:円|ドル|リンギット|ウォン|ユーロ)"
)

_LEGAL_FORM = re.compile(r"株式会社|有限会社|合同会社|合資会社|合名会社|（株）|\(株\)|（有）|\(有\)|㈱|㈲")
_NAME_SEP = re.compile(r"[\s　・･]+")
_LIST_SEP = re.compile(r"[、,，/／\n]+")
_HONORIFIC = "(?:さん|氏|様)?"


def normalize_for_match(text: str) -> str:
    """The one normalization shared with the quote guard: NFKC, no whitespace."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def remove_phone(text: str) -> str:
    return _PHONE.sub("", _LABELLED_PHONE.sub("", text))


def remove_address(text: str) -> str:
    return _ADDRESS.sub("", text)


def remove_money(text: str) -> str:
    return _MONEY.sub("", text)


def _spaced(term: str) -> str:
    """Match a term even when spaces were inserted between its characters."""
    return r"\s*".join(re.escape(ch) for ch in term)


@dataclass(frozen=True)
class NameParts:
    terms: tuple[str, ...]
    unsplit: bool
    single_char: bool


def name_parts(raw_name: str) -> NameParts:
    """Full name plus each piece. Articles may use only the family or given name."""
    parts = [p for p in _NAME_SEP.split(raw_name.strip()) if p]
    if not parts:
        return NameParts((), False, False)
    full = "".join(parts)
    terms = {full, *parts}
    unsplit = len(parts) == 1 and len(full) >= 3
    if unsplit:
        # No separator, so the family/given boundary is unknown: mask every
        # plausible piece. A clumsy mask is better than a leaked name.
        for i in range(2, len(full) - 1):
            terms.add(full[:i])
            terms.add(full[i:])
    return NameParts(
        tuple(sorted(terms, key=len, reverse=True)),
        unsplit,
        any(len(p) == 1 for p in parts),
    )


def _term_pattern(term: str) -> str:
    if len(term) == 1:
        # A lone kanji would eat ordinary words, so require a non-kanji edge.
        return rf"(?<![{_KANJI}]){re.escape(term)}(?![{_KANJI}]){_HONORIFIC}"
    return rf"{_spaced(term)}{_HONORIFIC}"


def mask_pairs(text: str, pairs) -> str:
    """Replace in one pass, longest first, so a family name inside a company
    name cannot break the company match. Masks are never re-scanned."""
    ordered = sorted(dict(pairs).items(), key=lambda pair: len(pair[0]), reverse=True)
    if not ordered:
        return text
    pattern = "|".join(f"({_term_pattern(term)})" for term, _ in ordered)
    return re.sub(pattern, lambda match: ordered[match.lastindex - 1][1], text)


def mask_terms(text: str, terms, replacement: str) -> str:
    return mask_pairs(text, [(term, replacement) for term in terms])


def company_terms(company: str) -> list[str]:
    """Full company name, and the short form without its legal form."""
    company = company.strip()
    if not company:
        return []
    short = _LEGAL_FORM.sub("", company).strip()
    return [t for t in {company, short} if t]


def interviewer_terms(raw: str) -> list[str]:
    terms: list[str] = []
    for one in _LIST_SEP.split(raw):
        terms.extend(name_parts(one).terms)
    return terms


@dataclass
class ArticleScrubber:
    """Masks one article's own people, then seat-level pairs and fixed patterns."""

    person_terms: tuple[str, ...]
    interviewer_terms: tuple[str, ...]
    seat_pairs: tuple[tuple[str, str], ...] = ()

    def __call__(self, text: str) -> str:
        pairs = [
            *((term, PERSON_MASK) for term in self.person_terms),
            *((term, INTERVIEWER_MASK) for term in self.interviewer_terms),
            *self.seat_pairs,
        ]
        return remove_address(remove_phone(mask_pairs(text, pairs)))

    def forbidden(self) -> list[str]:
        terms = (*self.person_terms, *self.interviewer_terms)
        return forbidden_terms([*terms, *(term for term, _ in self.seat_pairs)])


def forbidden_terms(terms) -> list[str]:
    """Single characters are excluded: they appear inside ordinary words."""
    return [term for term in terms if len(term) >= 2]


def scrub_slide_text(text: str, pairs=()) -> str:
    return remove_money(remove_address(remove_phone(mask_pairs(text, pairs))))
