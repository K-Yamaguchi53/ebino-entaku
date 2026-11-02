"""Screen wording the teacher may edit lives in texts/*.txt, not in code."""

from pathlib import Path

TEXTS_DIR = Path(__file__).resolve().parent.parent / "texts"
SPLIT_NOTICE = "split_notice"  # Shown above every split (SPEC 14-39).
# Always shown on the round-table input screen and the reflection sheet's
# writing box (SPEC 2-1, 14-47).
HEAVY_TALK_NOTICE = "heavy_talk_notice"


def load_text(name: str) -> str:
    return (TEXTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
