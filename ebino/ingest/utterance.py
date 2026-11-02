"""The ingested unit, its stable ID, and the final leak check."""

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .scrub import normalize_for_match

VOICE_SPOKEN = "spoken"  # Inside 「」 in an article body: words actually said.
VOICE_ARTICLE = "article"  # Interview article text, confirmed by the person.
VOICE_COMPANY = "company"  # Company introduction, confirmed by the company.
VOICE_SENIOR = "senior"  # Message from an unnamed senior employee.
VOICE_OWN = "own"  # Written by the speaker: posters and slides.

# Shown with the source. Spoken words get quotation marks instead of a note.
SOURCE_NOTES = {
    VOICE_ARTICLE: "取材記事（本人確認済み）",
    VOICE_COMPANY: "会社の紹介文（本人確認済み）",
    VOICE_SENIOR: "先輩社員の言葉（本人確認済み）",
}
# The teacher's own article (SPEC 14-50): own words, but shown as an article.
TEACHER_ARTICLE_NOTE = "先生が書いた記事"

_SENTENCE = re.compile(r"[^。！？!?]+[。！？!?]*")
_QUOTE = re.compile(r"「([^「」]*)」")
_MIN_DEDUPE_CHARS = 8
_NOT_QUOTING_TO = ("という", "といった", "とか", "との", "とは")
# 語る・話す・言う・思う・笑う in any form; the kana after the kanji keeps 話題・言葉 out.
_SAY = "語[らりるれろっ]|話[さしすせそ]|言[わいうえおっ]|思[わいうえおっ]"
_LAUGH = "笑[わいうえおっ]"
# SPEC 14-50-2: 「…」だと語る, 「…」そう話す. だという・だそうだ・そんな do not match.
_SAID_AFTER = re.compile(f"だと(?:{_SAY})|そう(?:{_SAY}|{_LAUGH})")


class IngestError(Exception):
    """Carries a reason code only, never document text."""


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def source_hash(file_name: str) -> str:
    return _hash(normalize_for_match(Path(file_name).name))


def make_id(kind: str, file_name: str, text: str) -> str:
    """Re-ingesting unchanged text yields the same ID."""
    return f"{kind}-{source_hash(file_name)}-{_hash(normalize_for_match(text))}"


@dataclass
class Utterance:
    id: str
    seat_id: str
    kind: str
    section: str
    voice: str
    text: str
    paragraph: str
    heading: str = ""  # Posters: the heading's own words, e.g. 研究仮説.
    source_note: str = ""  # Set when the note depends on more than the voice.

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def note(self) -> str:
        """What to show with the source; "" for spoken and own words."""
        return self.source_note or SOURCE_NOTES.get(self.voice, "")


def dedupe_sentences(text: str) -> str:
    """Word text boxes can repeat a sentence; keep its first appearance."""
    seen: set[str] = set()
    kept: list[str] = []
    for sentence in _SENTENCE.findall(text):
        key = normalize_for_match(sentence)
        if len(key) >= _MIN_DEDUPE_CHARS and key in seen:
            continue
        seen.add(key)
        kept.append(sentence)
    return "".join(kept)


def is_said(after: str) -> bool:
    """Whether a 「」 followed by `after` holds words said (SPEC 14-50).

    Only a quoting と or って makes it speech: 「…」と言われ, 「…」と思っ,
    「…」って. 「…」という・といった・とか・との・とは name or stress a word,
    and so does any other follower (を・に・が・の・は・。). A 「」 that closes
    the paragraph is speech, as before.

    SPEC 14-50-2 adds だと and そう before a verb of saying or thinking:
    「…」だと語る, 「…」だと思った, 「…」そう話す, 「…」そう笑う.
    「…」だという, 「…」だそうだ and 「…」そんな stay in the article.
    """
    after = after.lstrip()
    if not after or after.startswith("って") or _SAID_AFTER.match(after):
        return True
    return after.startswith("と") and not after.startswith(_NOT_QUOTING_TO)


def split_voice(paragraph: str) -> list[tuple[str, str]]:
    """Split into words said (inside 「」) and the article text around them.

    A 「」 that is not speech stays in the article text, brackets and all."""
    pieces: list[tuple[str, str]] = []
    position = 0
    for match in _QUOTE.finditer(paragraph):
        if not is_said(paragraph[match.end() :]):
            continue
        before = paragraph[position : match.start()].strip()
        if before:
            pieces.append((VOICE_ARTICLE, before))
        if match.group(1).strip():
            pieces.append((VOICE_SPOKEN, match.group(1).strip()))
        position = match.end()
    rest = paragraph[position:].strip()
    if rest:
        pieces.append((VOICE_ARTICLE, rest))
    return pieces


def unique_by_id(utterances: list[Utterance]) -> list[Utterance]:
    """The same piece twice in one file has one ID, so it becomes one utterance."""
    unique: dict[str, Utterance] = {}
    for utterance in utterances:
        unique.setdefault(utterance.id, utterance)
    return list(unique.values())


def assert_clean(utterances: list[Utterance], forbidden: list[str]) -> None:
    """Last gate: catches variants the masks missed, such as full-width forms."""
    terms = {normalize_for_match(t) for t in forbidden if t}
    for utterance in utterances:
        body = normalize_for_match(utterance.text + utterance.paragraph)
        if any(term and term in body for term in terms):
            raise IngestError("forbidden_term_remains")
