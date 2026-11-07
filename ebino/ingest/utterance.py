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
# An answer to a question card returned during the event (SPEC 2-2, 14-18).
# Taken in as written; the guard counts it apart from the rest (SPEC 14-25).
VOICE_ANSWER = "answer"

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
# SPEC 14-50-4: an article piece made of only these says nothing.
_EMPTY_PIECE_CHARS = str.maketrans("", "", "とや、。")


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


def _joined(gap: str) -> bool:
    """Whether two 「」 with `gap` between them belong to one run.

    Nothing between them (spaces aside), or a lone と: 〈「海」と「山」〉 is the
    と of "A and B", not a quoting と (SPEC 14-50-3)."""
    return gap.strip() in ("", "と")


def _said_quotes(paragraph: str) -> list[re.Match]:
    """The 「」 that hold words said.

    「」 written one after another share the fate of the last one (SPEC 14-50-2,
    14-50-3): 「…」「…」と言われた and 「…」と「…」と言われた make both speech,
    and 「…」「…」というお店 and 「…」と「…」で迷い keep both in the article."""
    matches = list(_QUOTE.finditer(paragraph))
    said: list[re.Match] = []
    run: list[re.Match] = []
    for index, match in enumerate(matches):
        run.append(match)
        following = matches[index + 1] if index + 1 < len(matches) else None
        if following and _joined(paragraph[match.end() : following.start()]):
            continue  # The next 「」 belongs to this run; decide with the last one.
        if is_said(paragraph[match.end() :]):
            said.extend(run)
        run = []
    return said


def _has_content(article_text: str) -> bool:
    """False for "", と, と。 and the like: nothing but と・や・、・。 and spaces."""
    return bool(article_text.translate(_EMPTY_PIECE_CHARS).strip())


def split_voice(paragraph: str) -> list[tuple[str, str]]:
    """Split into words said (inside 「」) and the article text around them.

    A 「」 that is not speech stays in the article text, brackets and all.
    Article text left as only particles and marks, such as the と in
    「…」と「…」と言われた, is not a piece (SPEC 14-50-4)."""
    pieces: list[tuple[str, str]] = []
    position = 0
    for match in _said_quotes(paragraph):
        before = paragraph[position : match.start()].strip()
        if _has_content(before):
            pieces.append((VOICE_ARTICLE, before))
        if match.group(1).strip():
            pieces.append((VOICE_SPOKEN, match.group(1).strip()))
        position = match.end()
    rest = paragraph[position:].strip()
    if _has_content(rest):
        pieces.append((VOICE_ARTICLE, rest))
    return pieces


# 直し54f (the teacher, 11/8): a senior's message signed 入社N年目 in vertical
# text comes out read backwards at the very end, 目年２社入, and when the
# reading slips the 目 or 年 it lacks lands inside the message: 頂け目年る,
# みま目せんか. The label is left out (the seat already says who speaks) and
# a slipped 目・年 between two non-kanji is taken out. Only after 。！？, so a
# message that ends in a word with 社入 is never touched.
_KANJI = "一-鿿"
_TENURE_TAIL = re.compile(r"(?<=[。！？!?])\s*(目?)\s*(年?)\s*[0-9０-９]{1,2}\s*社\s*入\s*$")


def mend_tenure(text: str) -> str:
    """The message without its backwards 入社N年目 label and the 目・年 it slipped."""
    tail = _TENURE_TAIL.search(text)
    if tail is None:
        return text
    body = text[: tail.start()]
    slipped = ("" if tail.group(1) else "目") + ("" if tail.group(2) else "年")
    if slipped:
        stray = re.compile(f"(?<![{_KANJI}])" + r"\s*".join(slipped) + f"(?![{_KANJI}])")
        found = list(stray.finditer(body))
        if found:
            body = body[: found[-1].start()] + body[found[-1].end() :]
    return body


# 直し54g: vertical text read one character at a time, a space after each:
# 自 分 を 変 え た か っ た。 Five or more such characters in a row are
# joined; the name check already reads text without spaces, so it sees the same.
_SPACED_CHAR = f"[{_KANJI}ぁ-んァ-ヶー々。、！？「」『』（）A-Za-z0-9]"
_SPACED_RUN = re.compile(f"(?:{_SPACED_CHAR}[ 　]){{4,}}{_SPACED_CHAR}")


def mend_spacing(text: str) -> str:
    return _SPACED_RUN.sub(lambda run: re.sub("[ 　]", "", run.group()), text)


# 直し54h (the teacher, 11/8: 直せるところは直して): what reads badly on the
# screen and has one meaning.
# A web address, read aloud, says nothing: it goes, with the digits run into
# it, a 「ページはこちらから」 that only pointed to it, and the brackets left empty.
# The pointer stays inside its own bullet; an address ends at its .html when
# it has one (the date written right after it is kept).
_URL_POINTER = re.compile(r"(?:[•・]\s*)?[^。\n（()）•・]*こちら(?:から)?\s*[（(]\s*https?://[\x21-\x7e]*?\s*[）)]")
_URL = re.compile(r"\d{6,}(?=https?://)|(?:https?://|www\.)(?:[\x21-\x7e]*?\.html?|[\x21-\x7e]+)")
_EMPTY_BRACKETS = re.compile(r"[（(]\s*[）)]")
# A word's reading set over it, read as each kana twice: リリ　ババ　イイ　ババ　ルル.
_DOUBLED_KANA = re.compile(r"(?:([ァ-ヶぁ-んー])\1[ 　]+){3,}")
# The masks (SPEC 14-3) put この職場 for a company's name and この方 for a
# person's. Around them: the company's form left (株式会社この職場 → この会社),
# 様 taken as a name (お客この方 → お客さん), 「この職場」というカフェ → カフェ.
_COMPANY_FORM = "株式会社|有限会社|合資会社|合同会社|[(（]株[)）]|㈱|[(（]有[)）]|㈲"
_MASK_WORDS = [
    (re.compile(f"(?:{_COMPANY_FORM})\\s*この職場|この職場\\s*(?:{_COMPANY_FORM})"), "この会社"),
    (re.compile("お客この方"), "お客さん"),
    (re.compile("奥この方"), "奥さん"),
    (re.compile("この方先生"), "この先生"),
    # Only before a noun: 「この職場」というのは stays.
    (re.compile(f"「?この職場」という(?=[{_KANJI}ァ-ヶ])"), ""),
    # 直し54i: a name masked with nothing after it before the next word (the
    # teacher, 11/8): 協力者：この方農園 (the family's farm) → この方の農園,
    # この方小学校四年 (a slide's self-introduction) → この方、小学校四年.
    (re.compile("この方(?=農園|農場|牧場|商店|工房|食堂)"), "この方の"),
    (re.compile(f"この方(?=[{_KANJI}ァ-ヶ])(?!自身|以外|以上|達|曰|様|宅|家|側|の)"), "この方、"),
]


def mend_reading(text: str) -> str:
    text = _URL.sub("", _URL_POINTER.sub("", text))
    text = _EMPTY_BRACKETS.sub("", text)
    text = _DOUBLED_KANA.sub(lambda run: "".join(re.findall(r"([ァ-ヶぁ-んー])\1", run.group())), text)
    for pattern, word in _MASK_WORDS:
        text = pattern.sub(word, text)
    return text


def _mend(text: str) -> str:
    return mend_reading(mend_spacing(mend_tenure(text)))


def mended(utterance: Utterance) -> Utterance:
    text, paragraph = _mend(utterance.text), _mend(utterance.paragraph)
    if (text, paragraph) == (utterance.text, utterance.paragraph):
        return utterance
    return Utterance(**(utterance.to_dict() | {"text": text, "paragraph": paragraph}))


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
