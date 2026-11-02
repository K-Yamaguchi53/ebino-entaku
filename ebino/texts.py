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


def load_text(name: str) -> str:
    return (TEXTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
