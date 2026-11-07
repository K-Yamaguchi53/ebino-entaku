"""The choices to answer コーチ（AI）'s question at one to one with (直し48 段3).

The teacher (11/7): 「わかる／ちょっとちがう／考えたことがなかった／まだわからない」
do not fit a question like 「何から始める？」. So the question is asked in a
form the choices can answer (the prompt asks for 「〜イメージできる？」, 「〜と
思う？」 or 「〜したことある？」), and the set of choices is chosen here, by
code, from the form of the question as it came:

- 「〜できる？」「〜できそう？」 (「何から始めればいいか、イメージできる？」:
  a question word inside it is fine): できる／ちょっとできる／まだできない.
- 「〜したことある？」 with no question word: ある／まだない.
- 「〜と思う？」 with no question word: the teacher's first four
  (わかる／ちょっとちがう／考えたことがなかった／まだわからない).
- Anything else, and any of the above asking with 何・どう・どこ・だれ・いつ・
  なぜ・どれ (the model asked for an answer, not a choice): まだわからない
  only, the line to write in is the answer (no choice that does not fit).

答えない is always there besides (the board's own button). The words are the
teacher's table (texts/one_coach_choices.tsv); the sets are their IDs.
Words in 「」 (a quote of the person's) are not read for the form.
"""

import re

from . import texts

CAN = "can"
DID = "did"
THINK = "think"
OPEN = "open"
SETS = {
    CAN: ("can", "some", "cannot"),
    DID: ("did", "not_yet"),
    THINK: ("know", "differ", "new", "unsure"),
    OPEN: ("unsure",),
}

_QUOTED = re.compile(r"「[^」]*」")
# Not asking: 「何か」「どこかで」「いつも」「だれでも」… (some, any, always).
_NOT_ASKING = re.compile(r"(何|なに|どこ|だれ|誰|いつ|どれ)(か|も|でも)")
_ASKING = re.compile(r"何|なに|なん|どう|どこ|どの|どんな|だれ|誰|いつ|なぜ|どれ|どちら|いくつ")
_END = re.compile(r"[\s？?！!。、]+$")


def form(question: str) -> str:
    """CAN, DID, THINK or OPEN for the question as it is worded."""
    text = _END.sub("", _QUOTED.sub("", question or "").strip())
    if text.endswith(("できる", "できそう")):
        return CAN
    asking = bool(_ASKING.search(_NOT_ASKING.sub("", text)))
    if asking:
        return OPEN
    if text.endswith(("ことある", "ことがある", "ことはある")):
        return DID
    if text.endswith(("と思う", "と思います", "と思いますか")):
        return THINK
    return OPEN


def choices(question: str) -> list[dict]:
    """[{"id", "text"}] for the question, in the set's order."""
    table = texts.id_table(texts.ONE_COACH_CHOICES, texts.ONE_COACH_CHOICE_IDS)
    return [{"id": key, "text": table[key]} for key in SETS[form(question)]]
