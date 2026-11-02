"""The quote guard: a quote reaches the screen only if the source holds it.

Plain code, never a model (SPEC 6). Both sides are made alike the same way,
NFKC with every space and line break removed (SPEC 14-15, the same
normalize_for_match the ingest uses), and the quote passes only when it is a
part of its source that starts and ends at a sentence break: the head or end
of the piece, a line break, or 。！？!? (SPEC 14-51). What the screen shows is the
source's own text for that part, as it was before normalizing, never the
words the model wrote.

The source is the piece the quote names by its ID (Utterance.text): the words
said inside 「」, the article text around them, or a poster or slide section.
A piece always lies inside its paragraph, so this is the paragraph text of
SPEC 14-15 cut down to the piece, and a quote cannot borrow article text and
come out in quotation marks as words said.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from .ingest.scrub import normalize_for_match
from .ingest.utterance import VOICE_ANSWER, Utterance

STOP_EMPTY = "empty_quote"
STOP_NOT_IN_SOURCE = "not_in_source"
# In the source, but starting or ending inside a sentence (SPEC 14-51): 「辞めたい」
# cut from 〈辞めたいと思ったことはない。〉 would make the person say the opposite.
STOP_NOT_SENTENCE_BOUNDED = "not_sentence_bounded"
STOP_UNKNOWN_UTTERANCE = "unknown_utterance"
# The normalized source holds the quote, but no span of the original could be
# pointed at. Not expected; stopping is the safe side.
STOP_SPAN_NOT_FOUND = "span_not_found"

_SPACE = re.compile(r"\s+")
# Sentence ends, after NFKC: ！？ become !? and ｡ becomes 。.
_SENTENCE_END = "。!?"
_LINE_BREAK = re.compile(r"[\r\n  ]")
# One sentence: up to and with its end marks, or up to a line break.
_SENTENCE = re.compile(r"[^。！？!?｡\r\n  ]*[。！？!?｡]+|[^。！？!?｡\r\n  ]+")


@dataclass(frozen=True)
class Quote:
    """A quote as the model gave it: which piece, and the words it wrote."""

    utterance_id: str
    text: str
    # Put in on purpose to show the guard at work (SPEC 7-3). The guard does
    # not look at this; it only keeps the planted one out of the real counts.
    planted: bool = False


@dataclass(frozen=True)
class Verdict:
    quote: Quote
    shown: str  # The source's own text for the quote; "" when stopped.
    reason: str = ""  # A STOP_* code; "" when passed.

    @property
    def passed(self) -> bool:
        return not self.reason


def _normalized_spans(source: str) -> tuple[str, list[tuple[int, int]]]:
    """The source made alike, and where in the source each character came from.

    The source is cut into a base character plus the marks NFKC joins to it
    (ｶﾞ becomes ガ), each cut is normalized on its own, and every character it
    gives points back at the whole cut."""
    cuts: list[tuple[int, int]] = []
    for index, char in enumerate(source):
        normal = unicodedata.normalize("NFKC", char)
        if cuts and normal and unicodedata.combining(normal[0]):
            cuts[-1] = (cuts[-1][0], index + 1)
        else:
            cuts.append((index, index + 1))
    chars: list[str] = []
    spans: list[tuple[int, int]] = []
    for start, end in cuts:
        for char in _SPACE.sub("", unicodedata.normalize("NFKC", source[start:end])):
            chars.append(char)
            spans.append((start, end))
    return "".join(chars), spans


def check(quote: str, source: str) -> Verdict:
    """Pass `quote` only if `source` holds it; show the source's own words."""
    verdict = _check(quote, source)
    return Verdict(Quote("", quote), *verdict)


def contains(part: str, source: str) -> Verdict:
    """Only whether `source` holds `part`, sentence breaks aside.

    Not for quotes: the batch check uses it to see that each piece lies inside
    its paragraph, where words said start and end at 「」, not at 。."""
    return Verdict(Quote("", part), *_check(part, source, whole_sentences=False))


def _check(quote: str, source: str, whole_sentences: bool = True) -> tuple[str, str]:
    needle = normalize_for_match(quote)
    if not needle:
        return "", STOP_EMPTY
    if needle not in normalize_for_match(source):
        return "", STOP_NOT_IN_SOURCE
    normal, spans = _normalized_spans(source)
    at = normal.find(needle)
    if at < 0:
        return "", STOP_SPAN_NOT_FOUND
    while at >= 0:
        end = at + len(needle)
        if not whole_sentences or _starts_sentence(normal, spans, source, at) and _ends_sentence(normal, spans, source, end):
            return source[spans[at][0] : spans[end - 1][1]], ""
        at = normal.find(needle, at + 1)
    return "", STOP_NOT_SENTENCE_BOUNDED


def _break_between(spans: list[tuple[int, int]], source: str, index: int) -> bool:
    """Whether the original has a line break between normalized chars index-1 and index.
    Line breaks vanish when normalizing, so they are looked up in the original."""
    return bool(_LINE_BREAK.search(source, spans[index - 1][1], spans[index][0]))


def _starts_sentence(normal: str, spans, source: str, index: int) -> bool:
    """The piece's head, right after 。！？!?, or right after a line break."""
    return (
        index == 0
        or normal[index - 1] in _SENTENCE_END
        or _break_between(spans, source, index)
    )


def _ends_sentence(normal: str, spans, source: str, end: int) -> bool:
    """The piece's end, a line break, or just before or after 。！？!? (the quote may
    leave the mark out)."""
    return (
        end == len(normal)
        or normal[end] in _SENTENCE_END
        or normal[end - 1] in _SENTENCE_END
        or _break_between(spans, source, end)
    )


def sentences(text: str) -> list[str]:
    """The sentences of a piece, cut where the guard lets a quote start and end."""
    return [s.strip() for s in _SENTENCE.findall(text) if normalize_for_match(s)]


@dataclass
class Tally:
    """What the guard did, by count. Never holds quote or source text."""

    passed: int = 0
    stopped: int = 0
    stopped_ids: list[str] = field(default_factory=list)
    reasons: Counter = field(default_factory=Counter)
    # Answers returned during the event are taken in as written, so they are
    # counted apart and never swell the guard's numbers (SPEC 14-25).
    answers_passed: int = 0
    answers_stopped: int = 0
    # Planted fakes (SPEC 7-3) are not real quotes either.
    planted_passed: int = 0
    planted_stopped: int = 0

    def lines(self) -> list[str]:
        return [
            f"guard passed / stopped: {self.passed} / {self.stopped}",
            f"guard stop reasons: {dict(self.reasons)}",
            f"guard stopped utterance ids: {self.stopped_ids}",
            "answers returned during the event, passed / stopped (counted apart): "
            f"{self.answers_passed} / {self.answers_stopped}",
            f"planted fake quotes, passed / stopped: {self.planted_passed} / {self.planted_stopped}",
        ]


class Guard:
    """Checks quotes against the ingested pieces and keeps the tally."""

    def __init__(self, utterances: list[Utterance]):
        self._by_id = {utterance.id: utterance for utterance in utterances}
        self.tally = Tally()

    def screen(self, quotes: list[Quote]) -> list[Verdict]:
        """One verdict per quote, in order. Show only the ones that passed."""
        return [self._screen_one(quote) for quote in quotes]

    def shown(self, quotes: list[Quote]) -> list[Verdict]:
        return [verdict for verdict in self.screen(quotes) if verdict.passed]

    def _screen_one(self, quote: Quote) -> Verdict:
        utterance = self._by_id.get(quote.utterance_id)
        if utterance is None:
            verdict = Verdict(quote, "", STOP_UNKNOWN_UTTERANCE)
        else:
            verdict = Verdict(quote, *_check(quote.text, utterance.text))
        self._count(verdict, utterance)
        return verdict

    def _count(self, verdict: Verdict, utterance: Utterance | None) -> None:
        tally = self.tally
        if verdict.quote.planted:
            tally.planted_passed += verdict.passed
            tally.planted_stopped += not verdict.passed
        elif utterance is not None and utterance.voice == VOICE_ANSWER:
            tally.answers_passed += verdict.passed
            tally.answers_stopped += not verdict.passed
        elif verdict.passed:
            tally.passed += 1
        else:
            tally.stopped += 1
            tally.stopped_ids.append(verdict.quote.utterance_id)
            tally.reasons[verdict.reason] += 1


def plant_fake(quotes: list[Quote], fake_text: str) -> list[Quote]:
    """Mix one quote no source holds in among real ones (SPEC 7-3).

    It names the same piece as the first real quote and comes second, so the
    screen shows a real quote, then the guard stopping the fake. The same real
    code runs in the sample mode and with a key."""
    if not quotes or not fake_text.strip():
        return list(quotes)
    fake = Quote(quotes[0].utterance_id, fake_text, planted=True)
    return [quotes[0], fake, *quotes[1:]]
