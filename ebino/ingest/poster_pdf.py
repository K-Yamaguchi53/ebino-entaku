"""Read an inquiry poster (one-page PDF).

Student names sit at the top. Everything above the first heading that maps to
one of the five roles is dropped by position, a title included. No name list is
needed, and a poster without such a heading fails closed.

Real headings vary (SPEC 14-42): numbering styles, brackets, and two sets of
words. Each heading maps to one of five roles; a heading that maps to none
keeps its own words as a separate section instead of being thrown away.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .masks import SeatMasks
from .pdf_chars import PdfTextStats, fold_radicals, is_control, remove_controls
from .pdf_quiet import quiet_pdf_warnings
from .scrub import forbidden_terms, mask_pairs, normalize_for_match
from .seats import Seat
from .utterance import (
    IngestError, Utterance, VOICE_OWN, assert_clean, make_id, unique_by_id,
)

ROLE_BACKGROUND = "背景と課題"
ROLE_PURPOSE = "目的"
ROLE_METHOD = "手法"
ROLE_RESULT = "結果"
ROLE_OUTLOOK = "結論と展望"
ROLES = (ROLE_BACKGROUND, ROLE_PURPOSE, ROLE_METHOD, ROLE_RESULT, ROLE_OUTLOOK)

# Checked in this order; the first keyword found in a heading decides its role.
# 成果と反省 → 結果, 成果と今後の展望 → 結論と展望, 実践後の課題 → 結論と展望,
# 企画実践前の課題 → 背景と課題 (SPEC 14-44).
_ROLE_KEYWORDS = (
    (ROLE_PURPOSE, ("目的", "仮説", "仮設", "目標")),  # 研究仮設: a real misspelling
    (
        ROLE_BACKGROUND,
        (
            "背景", "経緯", "テーマ設定", "設定理由", "テーマの理由", "初めに", "はじめに",
            "動機", "きっかけ", "前の課題",
        ),
    ),
    (ROLE_OUTLOOK, ("展望", "まとめ", "結論")),
    (ROLE_RESULT, ("結果", "成果", "考察")),
    (ROLE_OUTLOOK, ("課題", "反省")),
    (ROLE_METHOD, ("調査", "活動", "企画", "方法", "手法", "実践", "手順", "実習")),
)
# A line with no number or bracket is a heading only if it is exactly one of these.
# A heading word followed by a space and body text on the same line is split
# only when the word is one of these.
KNOWN_HEADINGS = frozenset(
    {
        *ROLES,
        "研究仮説", "探究仮説", "経緯・目的", "調査活動", "活動調査", "実践", "活動コンセプト",
        "実践後の課題", "課題", "これからの課題", "実践するに当たっての課題",
        "成果と今後の展望", "今後の展望",
        "背景", "企画実践の背景", "企画の目的", "企画実践の目的", "活動内容", "企画実践",
        "企画内容", "考えた企画", "方法", "企画実践手順・手法", "成果と反省",
        "実習先の成果と反省", "成果と反省点", "活動の成果", "反応と実習の成果",
        "考察・結果", "結果と考察", "考察", "展望", "反省・展望", "まとめと反省", "結論",
        # SPEC 14-44
        "テーマ設定", "テーマ設定理由", "テーマ設定の理由", "探究テーマ設定理由",
        "探究テーマ設定の理由", "はじめに", "初めに", "動機", "きっかけ", "目標",
        "企画実践前の課題", "実習活動",
        # SPEC 14-48
        "研究仮設", "探究仮設",
        # SPEC 14-49
        "テーマの理由", "探究テーマの理由",
    }
)
_MAX_HEADING_CHARS = 16
# 「スポーツイベントの開催による効果、研究仮説」: longer, but ends in a purpose word.
# The upper bound keeps a wrapped body line from turning into a heading.
_MAX_LONG_HEADING_CHARS = 30
_LONG_HEADING_ENDINGS = ("研究仮説", "探究仮説", "研究仮設", "探究仮設", "目的")
_NUMBER = re.compile(r"^(\d{1,2})(?!\d)([\s.,、:)）]*)")
_TRAILING_NUMBER = re.compile(r"\d{1,2}$")  # 「探究テーマ設定理由①」 (① is 1 after NFKC)
_GAP = re.compile(r"\s+")
_THEME_REASON = re.compile(r"テーマ設定|設定理由|テーマの理由")
# 「１ なぜ○○なのか（探究テーマ設定理由）」: the role word is in the closing brackets.
_WORD_IN_CLOSING_BRACKETS = re.compile(r"^.+\(([^()]+)\)$")
_OPEN = "<〈《【[◎■●◆◇□▶▼★☆"
_CLOSE = ">〉》】]"
_OPENING = re.compile(rf"^[{re.escape(_OPEN)}\s]+")
_CLOSING = re.compile(rf"[{re.escape(_CLOSE)}\s:：]+$")
_ENGLISH_GLOSS = re.compile(r"\s*\(\s*[A-Za-z][A-Za-z\s&/-]*\)\s*$")
_WORD_GAP = 3  # pdfplumber's default x_tolerance: a wider gap starts a new word.
_X_TOLERANCE = 5
_Y_TOLERANCE = 2
_LINE_TOLERANCE = 3


@dataclass(frozen=True)
class Fragment:
    """A run of text with its position on the page."""

    text: str
    x0: float
    top: float
    char_x0: tuple[float, ...] = ()  # Left edge of each character, when known.

    def x_at(self, index: int) -> float:
        if len(self.char_x0) == len(self.text):
            return self.char_x0[index]
        return self.x0

    def cut(self, start: int, end: int | None = None) -> "Fragment":
        end = len(self.text) if end is None else end
        chars = self.char_x0[start:end] if len(self.char_x0) == len(self.text) else ()
        return Fragment(self.text[start:end], self.x_at(start), self.top, chars)


@dataclass(frozen=True)
class Heading:
    label: str  # The heading's own words, numbering and brackets removed.
    role: str | None  # One of ROLES, or None for a heading that maps to none.


@dataclass(frozen=True)
class Section:
    label: str
    role: str | None
    text: str

    @property
    def name(self) -> str:
        return self.role or self.label


def role_of(label: str) -> str | None:
    if label in ROLES:
        return label
    for role, keywords in _ROLE_KEYWORDS:
        if any(keyword in label for keyword in keywords):
            return role
    return None


def _starts_like_heading(label: str) -> bool:
    keywords = (keyword for _, words in _ROLE_KEYWORDS for keyword in words)
    return label in KNOWN_HEADINGS or any(label.startswith(k) for k in keywords)


def is_why_question(label: str) -> bool:
    """「なぜこのテーマにしたのか？」「なぜ手話？」 — not 「なぜなら」."""
    return (
        label.startswith("なぜ")
        and not label.startswith("なぜなら")
        and label.endswith(("?", "か"))
    )


def heading_of(text: str) -> Heading | None:
    line = unicodedata.normalize("NFKC", text).strip()
    # 「1. 背景と課題 (Background and Issues)」: the gloss does not count toward length.
    line = _ENGLISH_GLOSS.sub("", line)
    length = len(re.sub(r"\s+", "", line))
    if not line or length > _MAX_LONG_HEADING_CHARS:
        return None
    rest = line
    number = _NUMBER.match(rest)
    if number:
        rest = rest[number.end() :]
    bracketed = bool(_OPENING.match(rest))
    rest = _OPENING.sub("", rest)
    if bracketed and rest[:1].isdigit():
        # 「◎10:30〜スタート」「◆1:0.5:2」 are times and ratios, not headings.
        return None
    rest = _CLOSING.sub("", rest)
    label = re.sub(r"\s+", "", rest)
    label = _TRAILING_NUMBER.sub("", label) or label
    if not label or "。" in label:
        return None
    if number:
        # Only numbered lines, so a 「なぜ」 or a bracket inside body text stays body.
        inner = _WORD_IN_CLOSING_BRACKETS.match(label)
        if inner:
            word = _TRAILING_NUMBER.sub("", inner.group(1)) or inner.group(1)
            if word in KNOWN_HEADINGS:
                return Heading(word, role_of(word))
        if is_why_question(label):
            # Treated like テーマ設定の理由 (SPEC 14-48).
            return Heading(label, ROLE_BACKGROUND)
    role = role_of(label)
    if length > _MAX_HEADING_CHARS:
        return Heading(label, role) if label.endswith(_LONG_HEADING_ENDINGS) else None
    if number and not number.group(2) and not _starts_like_heading(label):
        # "10か所で測った" and "3つの課題" are body lines; "1企画実践の背景" is a heading.
        return None
    if not number and not bracketed and label not in KNOWN_HEADINGS:
        return None
    return Heading(label, role)


def _can_start_a_split(heading: Heading | None) -> bool:
    return heading is not None and (
        heading.label in KNOWN_HEADINGS or is_why_question(heading.label)
    )


def _starts_with_number_or_bracket(text: str) -> bool:
    line = unicodedata.normalize("NFKC", text).lstrip()
    return bool(_NUMBER.match(line) or _OPENING.match(line))


def split_fragment(fragment: Fragment) -> list[Fragment]:
    """Split a line that holds a heading and more (SPEC 14-44, 14-48).

    「背景　自由な園児が…」 → heading 「背景」 + body. 「探究テーマ設定理由①　探究テーマ
    設定理由②」 and 「１．なぜこのテーマにしたのか ２．研究仮説」 (two columns read as
    one line) → two headings. Only a heading word from KNOWN_HEADINGS, or a
    numbered 「なぜ」 question, followed by a space starts a split.
    """
    text = fragment.text
    gaps = [gap for gap in _GAP.finditer(text) if gap.start() > 0 and gap.end() < len(text)]
    # Two numbered headings first: the whole line could otherwise pass as one long
    # heading ending in 研究仮説.
    for gap in gaps:
        rest = fragment.cut(gap.end())
        if _can_start_a_split(heading_of(text[: gap.start()])) and _starts_with_number_or_bracket(
            rest.text
        ):
            pieces = split_fragment(rest)
            if heading_of(pieces[0].text):
                return [fragment.cut(0, gap.start()), *pieces]
    if heading_of(text):
        return [fragment]
    for gap in gaps:
        if _can_start_a_split(heading_of(text[: gap.start()])):
            return [fragment.cut(0, gap.start()), *split_fragment(fragment.cut(gap.end()))]
    return [fragment]


def split_sections(fragments: list[Fragment]) -> list[Section]:
    fragments = [piece for fragment in fragments for piece in split_fragment(fragment)]
    found = [(fragment, heading_of(fragment.text)) for fragment in fragments]
    headings = [(f, h) for f, h in found if h]
    known = [f.top for f, h in headings if h.role]
    if not known:
        raise IngestError("poster_heading_missing")
    cutoff = min(known) - _Y_TOLERANCE  # The name line: nothing above survives.
    headings = [(f, h) for f, h in headings if f.top >= cutoff]
    heading_ids = {id(f) for f, h in found if h}

    def owner_of(x0: float, top: float) -> Fragment | None:
        # The owner is the nearest heading above, in this column.
        # Two headings on one line: the one further right owns its column.
        above = [
            (head.top, head.x0, index)
            for index, (head, _) in enumerate(headings)
            if head.top <= top + _Y_TOLERANCE and head.x0 <= x0 + _X_TOLERANCE
        ]
        return headings[max(above)[2]][0] if above else None

    def cut_at_columns(fragment: Fragment) -> list[Fragment]:
        """Body lines of two columns can come out as one fragment, joined by
        spaces. Cut where the text after a space belongs to another heading's
        column, so the right column's body stays under its own heading."""
        if len(fragment.char_x0) != len(fragment.text):
            return [fragment]
        left_owner = owner_of(fragment.x0, fragment.top)
        for gap in _GAP.finditer(fragment.text):
            if gap.start() == 0 or gap.end() >= len(fragment.text):
                continue
            if owner_of(fragment.x_at(gap.end()), fragment.top) is not left_owner:
                return [fragment.cut(0, gap.start()), *cut_at_columns(fragment.cut(gap.end()))]
        return [fragment]

    collected: dict[int, list[Fragment]] = {id(f): [] for f, _ in headings}
    for whole in fragments:
        if id(whole) in heading_ids or whole.top < cutoff:
            continue
        for fragment in cut_at_columns(whole):
            owner = owner_of(fragment.x0, fragment.top)
            if owner is not None:
                collected[id(owner)].append(fragment)

    sections: list[Section] = []
    for head, heading in headings:
        parts = sorted(
            collected[id(head)], key=lambda f: (round(f.top / _LINE_TOLERANCE), f.x0)
        )
        text = "".join(part.text.strip() for part in parts)
        if text:
            sections.append(Section(heading.label, heading.role, text))
    return sections


PURPOSE_FROM_PURPOSE = 0  # 目的・目標
PURPOSE_FROM_HYPOTHESIS = 1  # 研究仮説・探究仮説・経緯・目的
PURPOSE_FROM_THEME_REASON = 2  # テーマ設定の理由・なぜの問い (role stays 背景と課題)


def purpose_rank(section: str, heading: str) -> int | None:
    """Where a poster's sample purpose may come from; lower wins (SPEC 14-42, 44)."""
    if section == ROLE_PURPOSE:
        direct = ("目的" in heading or "目標" in heading) and "経緯" not in heading
        return PURPOSE_FROM_PURPOSE if direct else PURPOSE_FROM_HYPOTHESIS
    if _THEME_REASON.search(heading) or is_why_question(heading):
        return PURPOSE_FROM_THEME_REASON
    return None


def purpose_examples(utterances: list[Utterance]) -> list[Utterance]:
    """The poster's purpose to show as a sample question (SPEC 5-1, 14-42, 14-44)."""
    ranked = [(purpose_rank(u.section, u.heading), u) for u in utterances]
    ranked = [(rank, u) for rank, u in ranked if rank is not None]
    if not ranked:
        return []
    best = min(rank for rank, _ in ranked)
    return [u for rank, u in ranked if rank == best]


def pdf_page_count(path: Path) -> int:
    quiet_pdf_warnings()
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def fragments_from_word(word: dict, stats: PdfTextStats | None = None) -> list[Fragment]:
    """One pdfplumber word → fragments, with control characters removed.

    A control character can bridge two columns into one word (it has width but
    is no space). Once it is gone, the word is cut again wherever the remaining
    characters are further apart than pdfplumber's own word gap.
    """
    chars = list(word.get("chars", ()))
    if not chars or "".join(c["text"] for c in chars) != word["text"]:
        text = fold_radicals(remove_controls(word["text"], stats))
        return [Fragment(text, word["x0"], word["top"])] if text else []
    kept = []
    for char in chars:
        if is_control(char["text"]):
            if stats is not None:
                stats.control_chars_removed += 1
        else:
            kept.append(char)
    groups: list[list[dict]] = []
    for char in kept:
        if groups and char["x0"] - groups[-1][-1]["x1"] <= _WORD_GAP:
            groups[-1].append(char)
        else:
            groups.append([char])
    fragments = []
    for number, group in enumerate(groups):
        xs = [c["x0"] for c in group]
        if number == 0:
            # A control glyph at the head of a heading must not push the heading
            # right of its own column, or the body below loses its owner.
            xs[0] = word["x0"]
        text = fold_radicals("".join(c["text"] for c in group))
        fragments.append(Fragment(text, xs[0], word["top"], tuple(xs)))
    return fragments


def read_fragments(path: Path, stats: PdfTextStats | None = None) -> list[Fragment]:
    quiet_pdf_warnings()
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise IngestError("poster_not_one_page")
        words = pdf.pages[0].extract_words(
            keep_blank_chars=True, return_chars=True, x_tolerance=_WORD_GAP
        )
    return [fragment for word in words for fragment in fragments_from_word(word, stats)]


def ingest_poster_fragments(
    fragments: list[Fragment], seat: Seat, masks: SeatMasks = SeatMasks()
) -> list[Utterance]:
    masks.check_pages(1)
    if 1 in masks.pages:
        return []
    sections = split_sections(fragments)
    pairs = masks.pairs(seat)
    utterances: list[Utterance] = []
    for section in sections:
        text = mask_pairs(section.text, pairs).strip()
        if text:
            utterances.append(
                Utterance(
                    id=make_id(seat.kind, seat.source_file, text),
                    seat_id=seat.seat_id,
                    kind=seat.kind,
                    section=section.name,
                    voice=VOICE_OWN,
                    text=text,
                    paragraph=text,
                    heading=mask_pairs(section.label, pairs),
                )
            )
    utterances = unique_by_id(utterances)
    if not purpose_examples(utterances):
        # The purpose sample is part of the core (SPEC 8), so stop and say so.
        # Neither a purpose role nor a theme-reason section (SPEC 14-44).
        raise IngestError("purpose_heading_missing")
    assert_clean(utterances, forbidden_terms(term for term, _ in pairs))
    return utterances


def ingest_poster(
    path: Path, seat: Seat, masks: SeatMasks = SeatMasks(), stats: PdfTextStats | None = None
) -> list[Utterance]:
    return ingest_poster_fragments(read_fragments(path, stats), seat, masks)
