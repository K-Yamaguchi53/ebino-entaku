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
# Shown while the screen waits on the models: after a question is sent to
# the table, and while the moderator reads the record for the reflection.
WAITING_ASK = "waiting_ask"
WAITING_REFLECTION = "waiting_reflection"
# Shown when the screen could not reach the app; {error} is a reason code.
SEND_FAILED = "send_failed"
# The sheet's 出会った生き方 when the student marked no words (SPEC 5-2).
MET_LIVES_EMPTY = "met_lives_empty"
# Today's harvest card (SPEC 5-3): its heading, and the line above ②.
HARVEST_HEADING = "harvest_heading"
HARVEST_USE_QUESTION = "harvest_use_question"
# The sheet's optional question for a seat to hear more from, and the card's
# second line, which starts with the same words.
MEET_QUESTION = "meet_question"
HARVEST_MEET_PREFIX = "harvest_meet_prefix"
# Words that show going to meet someone, one per line, looked for in what the
# student wrote on the sheet (the harvest card's ④). Not shown on screen.
GO_WORDS = "go_words"
# The round's last word (SPEC 14-53 A): the moderator's fixed sentence.
CLOSING_QUESTION = "closing_question"
# The kinds of talk a piece is tagged with (columns ID・名前・説明; the 説明 is
# what the tagger model is told), and the line shown over a piece of each
# kind in the round's last word (columns ID・見出し). Tables the teacher edits.
TALK_KINDS = "talk_kinds"
CLOSING_KIND_LABELS = "closing_kind_labels"
# 「もっと聞く」: shown when the seat's section has no next piece (a press on
# it makes a question card), and after that card is made.
MORE_END = "more_end"
MORE_CARD_DONE = "more_card_done"
# 「司会が○○に聞いてみる」 (SPEC 14-53 B): the card's line ({seat} is the
# seat's title), the two forms of the question ({quote} is the record's own
# words), each with a sentence for a piece shown with a source note
# (_written) and one for a company's introduction (_company), the line over
# an answer by its voice, and 「まだ答えていない」.
ASK_SEAT_HEADER = "ask_seat_header"
ASK_WHY = "ask_why"
ASK_WHY_WRITTEN = "ask_why_written"
ASK_WHY_COMPANY = "ask_why_company"
ASK_OTHER_SIDE = "ask_other_side"
ASK_OTHER_SIDE_WRITTEN = "ask_other_side_written"
ASK_OTHER_SIDE_COMPANY = "ask_other_side_company"
ASK_ANSWER_SAID = "ask_answer_said"
ASK_ANSWER_WRITTEN = "ask_answer_written"
ASK_NOT_ANSWERED = "ask_not_answered"

# Everything the screen shows from texts/, sent to it once.
SCREEN_TEXTS = (
    HEAVY_TALK_NOTICE, SPLIT_NOTICE, START_NOTICE, LAB_QUESTION, ANSWERED_COUNT,
    NOT_ASKED_YET, INPUT_EXAMPLE, PURPOSE_HEADING, WAITING_ASK, WAITING_REFLECTION,
    SEND_FAILED, MET_LIVES_EMPTY, HARVEST_HEADING, HARVEST_USE_QUESTION, MEET_QUESTION,
    HARVEST_MEET_PREFIX, MORE_END, MORE_CARD_DONE,
)
SCREEN_LISTS = (START_NOTICE, WORK_QUESTIONS)


def load_text(name: str) -> str:
    return (TEXTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def load_lines(name: str) -> list[str]:
    return [line.strip() for line in load_text(name).splitlines() if line.strip()]


def load_table(name: str, columns: tuple[str, ...]) -> list[dict[str, str]]:
    """A tab-separated table in texts/: its rows, in order. Errors give line
    numbers only."""
    lines = [line for line in (TEXTS_DIR / f"{name}.tsv").read_text(encoding="utf-8-sig").splitlines()
             if line.strip()]
    if not lines or tuple(cell.strip() for cell in lines[0].split("\t")) != columns:
        raise ValueError(f"{name}.tsv columns do not match")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) != len(columns) or not all(cells):
            raise ValueError(f"{name}.tsv line {number}: wrong column count or empty cell")
        rows.append(dict(zip(columns, cells)))
    return rows


def screen_texts() -> dict:
    texts: dict = {name: load_text(name) for name in SCREEN_TEXTS}
    texts.update({name: load_lines(name) for name in SCREEN_LISTS})
    return texts
