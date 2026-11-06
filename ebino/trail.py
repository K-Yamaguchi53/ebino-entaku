"""今日の道すじ (直し45 段2): the way one student went, in the order it went.

The session keeps one list of steps, each numbered in turn (never a clock
time, never a name): a question put to the round table, a bubble pressed (its
seat and piece), a question picked at one to one, an AI's question and the
student's answer, a way pressed when no one answered (段4), a question card.
Only what the student wrote or chose, and which piece was shown; nothing a
model judged. Whether a question went deeper is never judged here: the
student marks that at the reflection (段5).

Where a new question to the round table is another sentence than the one
before it, the screen marks it 「ここで問いが変わった」 and ties it to the
nearest thing heard before it. Code decides "another sentence": letters and
digits only (spaces, punctuation, symbols and ？ left out, letter widths
folded), and a difference of at most TYPO_CHARS characters (a typo put right)
is the same question.
"""

import unicodedata

QUESTION = "question"  # A question put to the round table.
OPENED = "opened"  # A bubble pressed: its seat and piece.
ONE_ASK = "one_ask"  # A question picked at one to one (段3).
ONE_COACH = "one_coach"  # コーチ（AI）'s question at one to one and the answer (段3).
AI_ANSWER = "ai_answer"  # コーチ・オブザーバー's question at the table and the answer.
DIRECTION = "direction"  # A way pressed when no one answered (段4).
CARD = "card"  # A question card made.
KINDS = (QUESTION, OPENED, ONE_ASK, ONE_COACH, AI_ANSWER, DIRECTION, CARD)
# What was heard before a question changed: the line goes back to the nearest.
HEARD = (OPENED, ONE_ASK, ONE_COACH, AI_ANSWER)
TYPO_CHARS = 2


def letters(text: str) -> str:
    """The question's letters and digits only, widths folded (NFKC)."""
    folded = unicodedata.normalize("NFKC", text or "")
    return "".join(ch for ch in folded if unicodedata.category(ch)[0] in ("L", "N"))


def distance(a: str, b: str) -> int:
    """How many characters to add, drop or change to make a into b."""
    if len(a) < len(b):
        a, b = b, a
    before = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        now = [i]
        for j, cb in enumerate(b, start=1):
            now.append(min(before[j] + 1, now[j - 1] + 1, before[j - 1] + (ca != cb)))
        before = now
    return before[-1]


def changed(before: str, after: str) -> bool:
    """Whether after is another question than before (see the module)."""
    a, b = letters(before), letters(after)
    if a == b:
        return False
    return distance(a, b) > TYPO_CHARS


def turns(steps: list[dict]) -> dict[int, int | None]:
    """{the number of each question that changed: the number of the nearest
    step heard before it (None when nothing was)}. The first question never
    changes; nor one the same as the question before it."""
    found: dict[int, int | None] = {}
    last_question = None
    last_heard = None
    for step in steps:
        kind = step.get("kind")
        if kind in HEARD:
            last_heard = step["n"]
        elif kind == QUESTION:
            if last_question is not None and changed(last_question, step.get("text", "")):
                found[step["n"]] = last_heard
            last_question = step.get("text", "")
    return found
