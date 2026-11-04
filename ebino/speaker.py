"""The round's bubbles as if the person were talking (直し31-7).

The teacher changed the rule: a seat's words are no longer shown word for
word, but 「できるだけ表現を変えずに、その人が話しているように」, and the
original can always be read (「元の段落を読む」, which shows the paragraph as
recorded, with its source).

Once the moderator has picked the round's words and the guard has passed
them, every bubble's words go to the model (the gate, Haiku, effort low) in
one request, with no name in it, and it gives each back as spoken words:
only the endings, the turns of phrase, and the third person made the first
(「〜と話す」「この方は」 → 「〜なんだよね」「ぼくは／わたしは」). It adds
nothing and leaves nothing out.

Nothing the model writes is shown before code checks it, as everywhere:
  - every number in it is in the original paragraph;
  - every run of two or more kanji or katakana in it is in the original
    paragraph, except the spoken words in texts/spoken_allowed.txt;
  - it is at most MAX_GROWTH times the original's length;
  - it holds no name (the gate's name list).
A bubble that fails any of them is shown in its original words; so is every
bubble when the model cannot be used or does not answer within
TIMEOUT_SECONDS (no retry). The words are never shown first and changed
after: a bubble is shown once, in the words it will keep.

What is kept for each bubble: both texts, which was shown, and why the
original was kept (a reason code).
"""

import json
import re
import unicodedata
from dataclasses import dataclass

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .texts import SPOKEN_ALLOWED, load_lines

ROLE = "speaker"
TIMEOUT_SECONDS = 8.0
MAX_GROWTH = 1.5
SHOWN_SPOKEN = "spoken"
SHOWN_ORIGINAL = "original"
STOP_NUMBER = "number_not_in_paragraph"
STOP_WORD = "word_not_in_paragraph"
STOP_LONG = "too_long"
STOP_NAME = "name"
STOP_EMPTY = "empty"
STOP_MISSING = "missing"

SYSTEM = """あなたは、高校生の問いに町の大人が答える「円卓」の、吹き出しの言葉を整える係です。
渡す各 quotes の text は、取材記事・ポスター・スライドから選んだ、その人の言葉か、その人について書かれた文です。
それぞれを、その人が高校生に向かって話しているような話し言葉に直してください。

決まり：
- 直してよいのは、語尾・言い回し・三人称を一人称にする所だけです（「〜と話す」「〜という」「この方は」→「〜なんだ」「〜んだよね」「ぼくは」「わたしは」など）。
- 中身は足さない・削らない。言っていないことを足さない。数・名前・地名・仕事の言葉は、元の字のまま使う。
- 元の言葉にない漢字の言葉やカタカナの言葉を新しく使わない。
- 長さは元とだいたい同じにする。
- 人の名前を書かない。
- voice が spoken（その人が実際に言った言葉）のものは、ほとんど直さなくてよい。語尾を少し話し言葉にするだけにする。
答えは、各 quotes の id と、直した text を lines に入れて返してください。"""

SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["lines"],
    "additionalProperties": False,
}

_DIGITS = re.compile(r"[0-9]+")
_KANJI_NUMBER = re.compile(r"[〇一二三四五六七八九十百千万]+")
_KANJI = re.compile(r"[一-鿿々〆ヶ]{2,}")
_KATAKANA = re.compile(r"[ァ-ヺー]{2,}")
_RUN = re.compile(r"[一-鿿々〆ヶ]+|[ァ-ヺー]+")


@dataclass(frozen=True)
class Spoken:
    utterance_id: str
    original: str
    spoken: str  # "" when the original is shown.
    reason: str = ""  # Why the original is shown: a code.

    @property
    def shown(self) -> str:
        return SHOWN_SPOKEN if self.spoken else SHOWN_ORIGINAL

    def record(self) -> dict:
        return {"utterance_id": self.utterance_id, "shown": self.shown, "original": self.original,
                "spoken": self.spoken, "reason": self.reason}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def allowed_words() -> frozenset[str]:
    return frozenset(_plain(word) for word in load_lines(SPOKEN_ALLOWED))


def stop_reason(spoken: str, original: str, paragraph: str, gate: Gate, allowed=None) -> str:
    """"" when the spoken words may be shown; else why not."""
    allowed = allowed_words() if allowed is None else allowed
    spoken = spoken.strip()
    if not spoken:
        return STOP_EMPTY
    if gate.names.hits(spoken):
        return STOP_NAME
    source = _plain(paragraph + original)
    plain = _plain(spoken)
    # A spoken word of the list is let in only where it stands alone: a whole
    # run of kanji or katakana that is the word, never a part of a longer one.
    plain = _RUN.sub(lambda m: "・" if m.group(0) in allowed else m.group(0), plain)
    for pattern in (_DIGITS, _KANJI_NUMBER):
        if any(number not in source for number in pattern.findall(plain)):
            return STOP_NUMBER
    for pattern in (_KANJI, _KATAKANA):
        if any(word not in source for word in pattern.findall(plain)):
            return STOP_WORD
    if len(spoken) > len(original) * MAX_GROWTH:
        return STOP_LONG
    return ""


def request_for(quotes: list[dict]) -> dict:
    data = {"quotes": [{"id": q["id"], "voice": q["voice"], "text": q["text"]} for q in quotes]}
    return json_request(ROLE, SYSTEM, json.dumps(data, ensure_ascii=False), SCHEMA, max_tokens=4000)


def speak(gate: Gate, quotes: list[dict]) -> list[Spoken]:
    """quotes: [{"id", "voice", "text", "paragraph"}] in the round's order.
    Each comes back as Spoken: the spoken words, or "" and a reason."""
    if not quotes:
        return []
    try:
        answer = json_answer(gate.send(ROLE, request_for(quotes), timeout=TIMEOUT_SECONDS))
        lines = answer.get("lines") if isinstance(answer, dict) else None
        if not isinstance(lines, list):
            raise ModelUnavailable("bad_output")
    except (GateError, ModelUnavailable) as error:
        return [Spoken(q["id"], q["text"], "", str(error)) for q in quotes]
    given = {line["id"]: line["text"] for line in lines
             if isinstance(line, dict) and isinstance(line.get("id"), str) and isinstance(line.get("text"), str)}
    allowed = allowed_words()
    out = []
    for q in quotes:
        spoken = given.get(q["id"])
        reason = STOP_MISSING if spoken is None else stop_reason(spoken, q["text"], q["paragraph"], gate, allowed)
        out.append(Spoken(q["id"], q["text"], "" if reason else spoken.strip(), reason))
    return out
