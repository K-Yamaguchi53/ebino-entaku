"""A slide's page tidied for one to one (直し43), by code only, no model.

A page is recorded as ingest/slides_pdf.py read it: the title's line, the
bullets and the lines the PDF broke in the middle of a sentence, joined by
"\\n". Shown as it is, at one to one, the teacher read 「スライドの写し」.
Before it is shown (and before the speaker makes it spoken words), code
tidies it; the words recorded stay as they are.

  - A line that is a page number only, a date only, or marks only goes.
  - The title's line goes: only the first line left, at most one a page,
    and only when it has no 「。」, is short (TITLE_MAX_CHARS or fewer), does
    not end the way a sentence ends (SENTENCE_ENDS, SENTENCE_END_KANA) and is
    not a bullet. A page of one line keeps it.
  - A line that does not end a sentence and the line after it that is not a
    bullet are one: the PDF's break goes. But a heading inside the page (a
    short line after a sentence's end, as a title is, not ending the way a
    line goes on, HEADING_GOES_ON: 「不安だったこと」) is never joined to the
    next: it is a line of its own, 「。」 at its end (the teacher, 11/6).
    The words with each line joined as before are kept beside them
    (Tidied.joined): the name check reads both.
  - A bullet is a sentence: its head mark or number goes, and 「。」 is put at
    its end when it has no sentence's end; so is every line left that way.
Nothing is added but 「。」 (and a space where the PDF broke between two
letters of the alphabet: the break was the space). A page that comes out
empty (its title only, say) is not shown.

What is kept: the words shown, how many lines went, and why (codes).
The name check (gate.names.hits) and the cut at ONE_CHARS are the session's.
"""

import re
import unicodedata
from dataclasses import dataclass

TITLE_MAX_CHARS = 15
SENTENCE_ENDS = "。！？!?」』"
# The last letter of a line that ends the way a sentence ends with no mark
# (〜た, 〜だ, 〜る, 〜う, 〜い, 〜です, 〜よ, 〜ね, 〜か, 〜ん): such a line is
# never taken for a title (「ありがとう」 stays).
SENTENCE_END_KANA = "たださるうくいすよねかん"
STOP = "。"
# The last letter of a line that goes on to the next (〜の, 〜を, 〜は...):
# such a line is never a heading (「だから一度は」 goes on). 「と」 is not
# here: 「こと」 ends a heading.
HEADING_GOES_ON = "のをにがはでもへやてばりし"
# Taken off a line's end before 「。」 is put there (no 「、。」).
OPEN_ENDS = "、，,：:・"

# Why a line or a page went: kept in the record (never the words that went).
DROP_TITLE = "title"
DROP_NUMBER = "page_number"
DROP_DATE = "date"
DROP_MARKS = "marks"
EMPTY = "empty"  # Nothing left: the page is not shown.
NAME = "name"  # The words tidied hold a name (the session checks): not shown.
CUT = "cut"  # Cut at a sentence's end (the session cuts at ONE_CUT_CHARS).

_BULLET = re.compile(r"^(?:[・●○■□◆◇◎▪▫►▶➢✓✔－\-＊*※]|(?:\d{1,2}|[a-zA-Z])[.)）．](?!\d)|[(（]\d{1,2}[)）]|[①-⑳])\s*")
_DASHES = "-‐‑–—―─━~〜"
_NUMBER = re.compile(rf"^[{_DASHES}\s]*(?:[pP]\.?\s*|No\.?\s*)?\d{{1,3}}(?:\s*/\s*\d{{1,3}})?[{_DASHES}\s]*$")
_WEEKDAY = r"(?:\s*[(（][月火水木金土日](?:曜日?)?[)）])?"
_DATE = re.compile(rf"^(?:\d{{1,4}}\s*[./\-年]\s*)?\d{{1,2}}\s*[./\-月]\s*\d{{1,2}}\s*日?{_WEEKDAY}$")


@dataclass(frozen=True)
class Tidied:
    text: str  # The page's words tidied; "" when nothing is left to show.
    dropped: int = 0  # How many of its lines went (a title, a number...).
    reasons: tuple[str, ...] = ()
    # The words with no heading a line of its own (each joined to the next as
    # before): what the name check reads beside text. "" when the same.
    joined: str = ""

    def record(self, utterance_id: str) -> dict:
        return {"utterance_id": utterance_id, "tidied": self.text, "dropped_lines": self.dropped,
                "reasons": list(self.reasons)}


def _plain(line: str) -> str:
    return unicodedata.normalize("NFKC", line).strip()


def _only_marks(line: str) -> bool:
    return not any(unicodedata.category(char)[0] in "LN" for char in line)


def line_drop(line: str) -> str:
    """Why this line goes by itself (a page number, a date, marks), or ""."""
    plain = _plain(line)
    if _NUMBER.match(plain):
        return DROP_NUMBER
    if _DATE.match(plain):
        return DROP_DATE
    if _only_marks(plain):
        return DROP_MARKS
    return ""


def is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line.strip()))


def ends_sentence(line: str) -> bool:
    return line.rstrip().endswith(tuple(SENTENCE_ENDS))


def is_title(line: str) -> bool:
    """A page's first line that is its title: no 「。」, short, not ending as a
    sentence ends, not a bullet."""
    line = line.strip()
    return (STOP not in line and len(_plain(line)) <= TITLE_MAX_CHARS and not ends_sentence(line)
            and not line.endswith(tuple(SENTENCE_END_KANA)) and not is_bullet(line))


def is_heading(line: str) -> bool:
    """A heading inside a page: as a title is, and not ending the way a line
    that goes on to the next does."""
    line = line.strip()
    # Nor a line ending in a letter of the alphabet or a digit: the break
    # there was a space (「Thank / you」).
    return (is_title(line) and not line.endswith(tuple(HEADING_GOES_ON + OPEN_ENDS))
            and not (line[-1:].isascii() and line[-1:].isalnum()))


def _joined(left: str, right: str) -> str:
    """Two lines the PDF broke: one; a space only where the break was between
    two letters of the alphabet or digits."""
    if left[-1:].isascii() and left[-1:].isalnum() and right[:1].isascii() and right[:1].isalnum():
        return f"{left} {right}"
    return left + right


def _sentence(unit: str) -> str:
    unit = unit.rstrip()
    if ends_sentence(unit):
        return unit
    return unit.rstrip(OPEN_ENDS).rstrip() + STOP


def tidy_page(text: str) -> Tidied:
    """A slide's page as one to one shows it: see the module's words."""
    lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
    reasons, kept = [], []
    for line in lines:
        why = line_drop(line)
        if why:
            reasons.append(why)
        else:
            kept.append(line)
    if len(lines) > 1 and kept and is_title(kept[0]):
        kept.pop(0)
        reasons.append(DROP_TITLE)
    words, joined = _words(kept, headings=True), _words(kept, headings=False)
    dropped = len(reasons)
    if not words:
        reasons.append(EMPTY)
    # Each code once, in the order met.
    return Tidied(words, dropped, tuple(dict.fromkeys(reasons)), "" if joined == words else joined)


def _words(kept: list[str], headings: bool) -> str:
    """The lines left as sentences; with headings, each heading a line of its
    own ("\\n" before and after it)."""
    units: list[list] = []  # [words, is a heading]
    for line in kept:
        head = _BULLET.match(line)
        if head:
            body = line[head.end():].strip()
            if body:
                units.append([body, False])
        elif units and not ends_sentence(units[-1][0]) and not units[-1][1]:
            units[-1][0] = _joined(units[-1][0], line)
        else:
            units.append([line, headings and is_heading(line)])
    parts = []
    for unit, heading in units:
        if not unit.strip(OPEN_ENDS + " "):
            continue
        parts.append(f"\n{_sentence(unit)}\n" if heading else _sentence(unit))
    return re.sub(r"\n+", "\n", "".join(parts)).strip("\n")


def sentences(text: str) -> list[str]:
    """text cut after each sentence's end (its marks and closing quotes with it)."""
    out, start, i = [], 0, 0
    while i < len(text):
        if text[i] in "。！？!?":
            while i + 1 < len(text) and text[i + 1] in "。！？!?」』":
                i += 1
            out.append(text[start:i + 1])
            start = i + 1
        i += 1
    if start < len(text):
        out.append(text[start:])
    return out


def cut(texts: list[str], limit: int) -> tuple[list[str], bool]:
    """texts kept whole while they come to limit or fewer characters; past
    it, cut at a sentence's end so that they do, the first sentence always
    kept whole. (texts kept, whether any was cut)."""
    if sum(len(text) for text in texts) <= limit:
        return list(texts), False
    out, used = [], 0
    for text in texts:
        kept = ""
        for part in sentences(text):
            if used + len(part) > limit and used:
                if kept:
                    out.append(kept)
                return out, True
            kept += part
            used += len(part)
        out.append(kept)
    return out, True
