"""Screen wording the teacher may edit lives in texts/*.txt, not in code."""

from pathlib import Path

TEXTS_DIR = Path(__file__).resolve().parent.parent / "texts"
SPLIT_NOTICE = "split_notice"  # Shown above every split (SPEC 14-39).
# Always shown on the round-table input screen and the reflection sheet's
# writing box (SPEC 2-1, 14-47).
HEAVY_TALK_NOTICE = "heavy_talk_notice"
# A sentence nobody said, mixed in to show the guard stopping it (SPEC 7-3).
PLANTED_FAKE_QUOTE = "planted_fake_quote"
# Shown when a model refused or failed (SPEC 14-51). Never mixed with
# 「この問いに答えた席：0」: the seats were not silent.
MODEL_UNAVAILABLE = "model_unavailable"
# Shown when the student's question holds a word on the gate's name list.
# Waiting does not help, so it asks for the word to be left out or put
# another way. It never says which word: that would show the name list.
NAME_IN_QUESTION = "name_in_question"
# The seven things told before a student starts (SPEC 2-1), one per line.
START_NOTICE = "start_notice"
LAB_QUESTION = "lab_question"  # The one question asked first (SPEC 2-1).
ANSWERED_COUNT = "answered_count"  # {n} is the number of seats that answered.
NOT_ASKED_YET = "not_asked_yet"  # On a related seat with no words (SPEC 14-12).
INPUT_EXAMPLE = "input_example"  # An invented topic, never a script question.
WORK_QUESTIONS = "work_questions"  # The school's work questions, one per line.
PURPOSE_HEADING = "purpose_heading"  # Above the poster purpose samples.
# The question back when the moderator's fails the code check (SPEC 5-2, 6).
ASK_BACK_FALLBACK = "ask_back_fallback"

# Everything the screen shows from texts/, sent to it once.
SCREEN_TEXTS = (
    HEAVY_TALK_NOTICE, SPLIT_NOTICE, START_NOTICE, LAB_QUESTION, ANSWERED_COUNT,
    NOT_ASKED_YET, INPUT_EXAMPLE, PURPOSE_HEADING,
)
SCREEN_LISTS = (START_NOTICE, WORK_QUESTIONS)


def load_text(name: str) -> str:
    return (TEXTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def load_lines(name: str) -> list[str]:
    return [line.strip() for line in load_text(name).splitlines() if line.strip()]


def screen_texts() -> dict:
    texts: dict = {name: load_text(name) for name in SCREEN_TEXTS}
    texts.update({name: load_lines(name) for name in SCREEN_LISTS})
    return texts
