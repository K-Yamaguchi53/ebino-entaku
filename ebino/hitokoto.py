"""帰る前に、ひとこと (直し38): the reflection, as the teacher's sample shows it.

In place of the reflection sheet (reflection.py, still there when
EBINO_REFLECT=old), the student, at the end of the sitting:

  1. 今日の地図: sees the first question over a small map of up to three
     people of the day (the words marked, then one to one, then the bubbles
     opened; the latest first in each), a dashed line between two of them
     when a split's two sides each hold one, and under it each person's
     words. The listener (a fast model) picks a short part of each card,
     which lights up where code finds it, word for word. The student presses
     one, or the card itself, or 「おまかせ」 (picked by code).
  2. 帰る前に、ひとこと: the listener asks two questions, one per direction
     and in this order: reaction (what came first on reading the words),
     self (does that person's talk fit them too). Only how it is said is the
     model's. Two 「わからない」 in a row turn to the ladder of questions to
     pick from, made from the record and texts/ only: the split's two
     people's words, the people on the map, and a line with a blank.
  3. the teacher's scale question (0 to 15, the first question's doubt as 10)
     and the next question, by the answer (the third direction, 前).
  4. what to keep: a way to keep in mind, a lesson near the talk (③ when
     there was one), and a seat to hear more from (②).
  5. 今日、光ったところ: the light model picks one of the student's own
     sentences and ties it to one of the school's six forces, in two short
     sentences; code decides when it cannot be used.
  6. one sheet to print, with no name on it.

The split's heading (直し40-2): a question the student sent with 「聞く」
that is a split's heading word for word (spaces at its ends aside) is the
moderator's words, not the student's; the first question sent after a split
was pressed that is not one (an answer to an AI's question aside) is the
question rewritten from the split. The student's own words the checks and
the light go by are the first question, the questions sent after it that are
not a heading, and what is written here; code's light takes the rewritten
question (⑤) before the sample's fifth step; the sheet's story says the
split was asked from, or asked again as it was.

Nothing a model writes reaches the screen before code checks it, as
reflection.checked does (「」 holds the record's or the student's own words,
no name, no banned word outside 「」), and more: no lure (coach.LURE_FORMS),
no sentence starting 「あなたは」, one question ending in ？ with at most one
question word, no word of texts/listener_avoid.txt. A question that fails is
the fixed question of its direction (texts/hitokoto.tsv); reason codes are
kept, never the failed words. What the student writes here goes through the
name check first: with a name in it, it is neither kept nor sent.
"""

import json
import re
import time
from dataclasses import dataclass, field

from . import harvest, subjects
from .banned_words import BANNED_WORDS
from .coach import LURE_FORMS
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .ingest.scrub import normalize_for_match
from .prompts import LIGHT as LIGHT_PROMPT
from .prompts import LISTENER as LISTENER_PROMPT
from .prompts import TIE as TIE_PROMPT
from .reflection import _QUOTED, Record, checked
from .seat_label import KIND_LABELS
from .texts import load_lines, load_table

LISTENER = "listener"  # The gate's roles (MODELS, EFFORT).
LIGHT = "light"
LISTENER_SECONDS = 8.0  # The wait, with no retry; past it, the fixed question.
LIGHT_SECONDS = 15.0  # Past it, code picks the light.

MAX_PEOPLE = 3
MAX_PART = 16  # A lit part of a card.
MAX_QUESTION = 60
MAX_WHY = 60
MAX_DEEP = 50
MAX_LINE = 120  # Each line the student writes.
MAX_LISTENER = 2  # Questions the listener puts: one per direction.
MAX_LADDER = 3  # Questions of the ladder.
MAX_QUESTIONS = 6  # The listener's, the ladder's and the scale's, at most.
SCALE_FIRST, SCALE_TOP = 10, 15

REACTION, SELF = "reaction", "self"
DIRECTIONS = (REACTION, SELF)  # In this order, each once. 前 is the scale's.
QUESTION_WORDS = ("なぜ", "どう", "何")
# Praise said by rote (the light): checked outside 「」 like banned_words.
PRAISE_FORMS = ("いいね", "いいですね", "よかった", "良かった", "最高", "完璧", "天才", "上手", "見事",
                "かっこいい", "感心")

# The school's six forces: ① to ⑤ as harvest.py names them (its FORCES stay
# as they are); ⑥ for this screen only.
FORCES = dict(harvest.FORCES) | {6: "⑥ 創り出す力"}
FORCE_WORDS = {number: name.split(" ", 1)[1] for number, name in FORCES.items()}

# Where the sample puts the points (its viewBox is 600 x 330): the split's
# two, then the third. The grey points are other seats met, as decoration.
SLOTS = ((200, 160), (400, 210), (300, 120))
GREY_SLOTS = ((150, 120), (420, 110), (470, 160), (260, 250), (360, 260), (120, 230), (330, 90))

WHY_MARK = "mark"  # How a person came onto the map.
WHY_ONE = "one"
WHY_BUBBLE = "bubble"
WHY_TRAIL = "trail"  # A step marked on the trail (直し45 段5): first on the map.

# Stops (reason codes, never the words).
STOP_LURE = "lure_form"
STOP_YOU_ARE = "you_are"
STOP_NOT_ONE_QUESTION = "not_one_question"
STOP_QUESTION_WORDS = "question_words"
STOP_AVOID = "avoid_word"
STOP_PRAISE = "praise"
STOP_MISSING = "missing"
STOP_FORCE = "unknown_force"
STOP_FORCE_NOT_NAMED = "force_not_named"
STOP_QUOTE_NOT_WRITTEN = "quote_not_written"
STUDENT_AVOID = "student_avoid"  # The student wrote of home, money or health: not dug into.
NO_PEOPLE = "no_people"
NOTHING_WRITTEN = "nothing_written"

# The stages, in order.
MAP, TALK, LADDER_TWO, LADDER_THREE, FILL, SCALE, FORWARD, NOTICE, WAY, SUBJECT, SUBJECT_NOTE, TRY, MEET, USE, \
    END, LIT, SHEET = ("map", "talk", "ladder_two", "ladder_three", "fill", "scale", "forward", "notice", "way",
                       "subject", "subject_note", "try", "meet", "use", "end", "lit", "sheet")
TALKING = (MAP, TALK, LADDER_TWO, LADDER_THREE, FILL, SCALE, FORWARD, NOTICE, WAY, SUBJECT, SUBJECT_NOTE, TRY, MEET,
           USE, END)
SUBJECT_ANSWERS = ("yes", "no", "unsure")  # あった・なかった・わからない
# 直し49 段1 (the teacher, 11/7: 「気づきがある、または行動などのきっかけが作れれば
# 良い」): 今日の気づき, asked after the scale (and its next question) and
# before the way to keep: four answers to pick, 「答えない」 always there; a
# line to write (optional) only after 「あった」 or 「ちょっとあった」. What is
# written is the student's own, kept and put on the sheet as written; no
# model is sent it or writes about it (not in written, so not the light's).
NOTICE_ANSWERS = ("yes", "some", "not_yet", "no_answer")  # あった・ちょっとあった・まだない・答えない
NOTICE_WRITE = ("yes", "some")
# 直し49 段2: 「次に会うなら」 widened to 次にやってみること. Before the seat to
# meet, four to pick: 会って聞いてみる goes on to the seat (and ② after it, as
# before); 自分で調べてみる and 試してみる open a line (optional), no seat;
# まだ決めない goes on. The line is the student's own, as 今日の気づき's.
TRY_ANSWERS = ("meet", "look", "try", "later")  # 会って聞いてみる・自分で調べてみる・試してみる・まだ決めない
TRY_WRITE = ("look", "try")
TRY_MEET = "meet"
# 直し51 段3: the student's own two lines on the sheet, each taken off by
# themselves (外す) or put back (戻す): its answers that open a line.
OWN_LINES = {"notice": NOTICE_WRITE, "next_try": TRY_WRITE}

TEXTS = "hitokoto"
FORCE_TEXTS = "hitokoto_forces"
BLANK_TEXTS = "hitokoto_blank"
AVOID_TEXTS = "listener_avoid"
TEXT_IDS = (
    "name", "step_map", "step_talk", "step_light", "step_sheet", "first_label", "map_lead", "map_split",
    "map_counts", "omakase", "omakase_said", "go", "stop", "to_light", "dont_know", "thinking", "summing", "who_ai",
    "who_teacher", "who_me", "send", "placeholder", "again", "ask_reaction", "ask_self", "ladder_two",
    "ladder_two_me", "ladder_three", "ladder_fill", "ladder_fill_line", "fill_ok", "fill_skip", "scale_q",
    "scale_low", "scale_first", "scale_ok", "scale_me", "scale_down", "scale_same", "scale_up", "skip", "way_q",
    "way_ok", "way_none", "way_example", "subject_q", "subject_yes", "subject_no", "subject_unsure",
    "subject_which", "subject_example", "meet_pick", "meet_met", "meet_others", "meet_ok", "meet_none", "light_title", "light_scale",
    "light_lead", "light_lead_chosen", "light_chosen_who", "light_deep_tail", "light_step", "light_split", "now_label",
    "to_sheet", "sheet_title", "sheet_now", "sheet_same", "sheet_story", "sheet_step", "story_people",
    "story_split_new", "story_split_same",
    "story_word", "story_chosen", "story_wrote", "story_scale", "story_more", "story_way", "story_subject",
    "story_subject_note", "print", "print_note", "print_side", "deep_word", "deep_more", "deep_way",
    "deep_need", "deep_chosen", "now_after", "sheet_met", "sheet_moves", "sheet_split", "sheet_meet",
    "sheet_tie", "tie_same", "tie_differ",
    # 直し49 段1.
    "notice_q", "notice_yes", "notice_some", "notice_not_yet", "notice_no_answer", "notice_hint", "sheet_notice",
    # 直し49 段2.
    "try_q", "try_meet", "try_look", "try_try", "try_later", "try_hint",
    # 直し51 段2: 今日の道すじ pointing at words already in full on the sheet.
    "story_word_short", "story_wrote_short", "story_more_short", "story_way_short",
    # 直し51 段3.
    "sheet_hint", "drop", "restore",
)
FILL_BLANK = "［　　］"  # In ladder_fill_line: where the student writes.

_SENTENCE_END = re.compile(r"[。．！!\n]")
_TRAIL = re.compile(r"[。．、，,.！!？?…\s　]+$")
_PLACE = re.compile(r"\{(\*?)(\w+)\}")


def words() -> dict[str, str]:
    """{ID: 文字} from texts/hitokoto.tsv, every row there."""
    rows = {row["ID"]: row["文字"] for row in load_table(TEXTS, ("ID", "文字"))}
    if set(rows) != set(TEXT_IDS):
        raise ValueError(f"{TEXTS}.tsv must have the rows {', '.join(TEXT_IDS)}")
    return rows


def force_sentences() -> dict[int, str]:
    """{number: the fixed sentence} for the six forces (texts/hitokoto_forces.tsv)."""
    rows = {row["番号"]: row["文"] for row in load_table(FORCE_TEXTS, ("番号", "文"))}
    if set(rows) != {str(n) for n in FORCES}:
        raise ValueError(f"{FORCE_TEXTS}.tsv must have the rows 1 to 6")
    return {int(key): value for key, value in rows.items()}


def screen_words() -> dict:
    """What the screen is sent once, with the forces' names; 直し45 段5: the
    marks on the trail and their words, and the name on the AI's questions'
    cards (コーチ（AI） for ① and ②; ③ is 先生の問い, 直し46)."""
    from . import coach, texts
    return {"words": words(), "kinds": KIND_LABELS,
            "marks": texts.id_table(texts.TRAIL_MARKS, texts.TRAIL_MARK_IDS),
            "mark_words": texts.id_table(texts.TRAIL_MARK_WORDS, texts.TRAIL_MARK_WORD_IDS),
            "who_coach": coach.ai_label(coach.COACH)}


def is_blank(text: str) -> bool:
    """「わからない」「ない」 and the like (texts/hitokoto_blank.txt), alone."""
    body = _TRAIL.sub("", (text or "").strip())
    return not body or body in load_lines(BLANK_TEXTS)


def has_avoid(text: str) -> bool:
    body = normalize_for_match(text or "")
    return any(normalize_for_match(word) in body for word in load_lines(AVOID_TEXTS))


def fill(template: str, **values) -> str:
    return _PLACE.sub(lambda m: str(values[m.group(2)]), template)


def segments(template: str, **values) -> list[dict]:
    """A sheet line as parts: {*name} is the student's or the record's words,
    shown in 「」 and stressed; the rest is the teacher's."""
    out, at = [], 0
    for match in _PLACE.finditer(template):
        if match.start() > at:
            out.append({"text": template[at:match.start()], "strong": False})
        value = str(values[match.group(2)])
        out.append({"text": f"「{value}」", "strong": True} if match.group(1) else {"text": value, "strong": False})
        at = match.end()
    if at < len(template):
        out.append({"text": template[at:], "strong": False})
    return out


@dataclass
class Person:
    seat_id: str
    title: str
    kind: str
    utterance_id: str
    text: str  # The words as recorded (the guard's), never the spoken words.
    said: bool  # The person's own words (「」) or an article's (its note).
    note: str
    why: str  # WHY_MARK, WHY_ONE or WHY_BUBBLE.
    x: int = 0
    y: int = 0

    def view(self) -> dict:
        return {"seat_id": self.seat_id, "title": self.title, "kind": self.kind,
                "kind_label": KIND_LABELS.get(self.kind, ""), "text": self.text, "said": self.said,
                "note": self.note, "x": self.x, "y": self.y,
                # 直し48 段7: its words, one whole sentence a press.
                "sentences": sentences(self.text)}


@dataclass
class Asked:
    """One question put to the student, as shown."""

    step: str  # A direction, ladder_two, ladder_three, fill, scale, forward.
    text: str
    by: str  # "listener" (passed the checks), "fixed" (texts/), "teacher".
    fallback: str = ""  # Why the listener's question was not used: a code.
    seconds: float = 0.0


@dataclass
class Light:
    quote: str
    source: str  # "written", "chosen" or "first".
    force: int
    why: str
    deep: str
    by: str  # "model" or "code".
    reason: str = ""  # Why code picked: a code ("" when the model's passed).
    chosen_who: str = ""  # source "chosen": whose words.
    seconds: float = 0.0


@dataclass
class Hitokoto:
    first_question: str
    people: list[Person] = field(default_factory=list)
    split: dict | None = None  # {"heading", "a", "b"}: two people's indexes.
    grey: list[tuple[int, int]] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    stage: str = MAP
    parts: dict[int, str] = field(default_factory=dict)  # Person index -> lit part.
    parts_asked: bool = False
    parts_reason: str = ""
    parts_seconds: float = 0.0
    chosen: int | None = None
    chosen_part: str = ""
    omakase: bool = False
    asked: list[Asked] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)  # {"step", "text"} or {"step", "dont_know": True}.
    written: list[dict] = field(default_factory=list)  # The student's own words: {"step", "text"}.
    listener_asked: int = 0
    blank_run: int = 0
    ladder_shown: int = 0
    ladder_two: int | None = None  # The split's side picked (person index).
    ladder_three: int | None = None
    fill_text: str = ""
    scale: int | None = None
    forward: str = ""
    way: str = ""
    subject: str = ""  # A SUBJECT_ANSWERS key.
    subject_note: str = ""
    subject_pick: object = None  # subjects.Pick
    meet_seat: str = ""
    meet_use: str = ""
    light: Light | None = None
    now_question: str = ""
    # The trail's marks (直し45 段5): [{"n", "mark", "note", "label", "text"}],
    # and the person on the map the first word is looked for at (None: none).
    marks: list[dict] = field(default_factory=list)
    start: int | None = None
    # From the rounds (直し40-2): the questions sent with 「聞く」 after the
    # first that are not a split's heading; the first of them sent after a
    # split was pressed; whether a heading was sent as it was after one was;
    # the last question sent that is not a heading (the first if none).
    own_questions: list[str] = field(default_factory=list)
    rewritten: str = ""
    heading_sent: bool = False
    last_question: str = ""
    # 直し48 段4: 司会（AI）のまとめ, two people's sentences and how they go
    # ({"kind", "a", "b"}: people's indexes), or None; asked once.
    tie: dict | None = None
    tie_asked: dict = field(default_factory=dict)  # {"reason", "seconds"} once asked.
    # 直し50 段3: each two people on the map who stood on the two sides of
    # one of the day's splits ([i, j], people's indexes, i < j).
    parted: list[list[int]] = field(default_factory=list)
    # 直し49 段1: 今日の気づき, a NOTICE_ANSWERS key ("" not asked), and the
    # line written after 「あった」 or 「ちょっとあった」 ("" none).
    notice: str = ""
    notice_text: str = ""
    # 直し49 段2: 次にやってみること, a TRY_ANSWERS key ("" not asked), and the
    # line written after 調べる or 試す ("" none).
    next_try: str = ""
    next_try_text: str = ""
    # 直し51 段3 (the teacher, 11/7): the student took their own line off the
    # sheet (外す): its words gone, here and in the record; that it was taken
    # is kept, and the answer picked. Put back (戻す): the line again.
    notice_dropped: bool = False
    next_try_dropped: bool = False

    # --- what the screen gets ---

    def map_view(self) -> dict:
        return {"first_question": self.first_question, "people": [p.view() for p in self.people],
                "split": self.split, "grey": [list(xy) for xy in self.grey], "counts": self.counts,
                "stage": self.stage, "start": self.start}

    def question_count(self) -> int:
        return sum(1 for a in self.asked if a.step != "forward")

    def record(self) -> dict:
        """As kept with the sitting: no name; the student's words passed the name check."""
        light = self.light
        return {
            "people": [{"seat_id": p.seat_id, "utterance_id": p.utterance_id, "why": p.why} for p in self.people],
            "split": bool(self.split),
            "parts": {"asked": self.parts_asked, "lit": len(self.parts), "reason": self.parts_reason,
                      "seconds": self.parts_seconds},
            "chosen": ({"seat_id": self.people[self.chosen].seat_id, "part": self.chosen_part, "omakase": self.omakase}
                       if self.chosen is not None else None),
            "asked": [{"step": a.step, "text": a.text, "by": a.by, "fallback": a.fallback, "seconds": a.seconds}
                      for a in self.asked],
            "answers": list(self.answers),
            "ladder": {"two": self.people[self.ladder_two].seat_id if self.ladder_two is not None else "",
                       "three": self.people[self.ladder_three].seat_id if self.ladder_three is not None else "",
                       "fill": self.fill_text},
            "scale": self.scale,
            "forward": self.forward,
            "way": self.way,
            "subject": self.subject,
            "subject_note": self.subject_note,
            "subject_pick": subjects.record(self.subject_pick),
            "meet_seat": self.meet_seat,
            "meet_use": self.meet_use,
            "light": ({"quote": light.quote, "source": light.source, "force": light.force, "by": light.by,
                       "reason": light.reason, "seconds": light.seconds} if light else None),
            "now_question": self.now_question,
            "stage": self.stage,
            # 直し45 段5: which step of the trail got which mark, and the line.
            "marks": [{"n": m["n"], "mark": m["mark"], "note": m["note"]} for m in self.marks],
            "tie": ({"kind": self.tie["kind"], "a": self.people[self.tie["a"]].seat_id,
                     "b": self.people[self.tie["b"]].seat_id} if self.tie else None),
            "tie_asked": dict(self.tie_asked),
            # 直し49 段1: the answer picked and the student's line, as written.
            "notice": {"answer": self.notice, "text": self.notice_text,
                       **({"dropped": True} if self.notice_dropped else {})},
            # 直し49 段2: what to try next, and the student's line, as written.
            "next_try": {"answer": self.next_try, "text": self.next_try_text,
                         **({"dropped": True} if self.next_try_dropped else {})},
        }


def sentences(text: str) -> list[str]:
    """直し48 段7 (the teacher, 11/7: 「フレーズよりも文章まるごと選択でいい」):
    the words in whole sentences, word for word: each ends after 。！？!? (a
    」 right after it kept with it), never inside 「」. Joined, they are the
    words as recorded (the spaces between sentences aside)."""
    out, start, depth = [], 0, 0
    chars = text or ""
    n = 0
    while n < len(chars):
        c = chars[n]
        if c == "「":
            depth += 1
        elif c == "」":
            depth = max(0, depth - 1)
            # A whole sentence in 「」 (「…。」): it ends with the 」.
            if depth == 0 and n > 0 and chars[n - 1] in "。！？!?" and chars[start:n + 1].lstrip().startswith("「"):
                out.append(chars[start:n + 1])
                start = n + 1
        elif c in "。！？!?" and depth == 0:
            end = n + 1
            while end < len(chars) and chars[end] in "」』）)":
                end += 1
            out.append(chars[start:end])
            start, n = end, end
            continue
        n += 1
    if chars[start:].strip():
        out.append(chars[start:])
    return [s.strip() for s in out if s.strip()]


# --- who is on the map ---

def pick_people(session, opened: list[str], first: tuple[str, str] | None = None) -> list[Person]:
    """Up to MAX_PEOPLE: the words marked, then one to one, then the bubbles
    opened; within each, the one read last first. Each with one card of
    words: the mark, else a bubble opened, else (one to one only) the first
    piece of the item asked last there. first (直し45 段5): (seat, piece) of
    the step marked on the trail, put first with that piece."""
    shown = {q.utterance_id: q for r in session.rounds for q in r.quotes}
    opened = [uid for uid in dict.fromkeys(opened) if uid in shown]
    marks = [(seat_id, uid) for seat_id, uid in session.marks.items() if uid in shown]
    order: list[tuple[str, str]] = []
    order += [(seat_id, WHY_MARK) for seat_id, _ in reversed(marks)]
    order += [(seat_id, WHY_ONE) for seat_id in reversed(list(session._one_seats()))]
    order += [(shown[uid].seat_id, WHY_BUBBLE) for uid in reversed(opened)]
    marked = dict(marks)
    last_opened = {}
    for uid in opened:
        last_opened[shown[uid].seat_id] = uid
    seats = {seat.seat_id: seat for seat in session.library.seats}
    people: list[Person] = []
    if first and first[0] in seats and first[1] in session._utterances:
        seat_id, uid = first
        utterance = session._utterances[uid]
        text = shown[uid].text if uid in shown else utterance.text
        seat = seats[seat_id]
        people.append(Person(seat_id, seat.title, seat.kind, uid, text, not utterance.note, utterance.note, WHY_TRAIL))
    for seat_id, why in order:
        if len(people) >= MAX_PEOPLE or seat_id not in seats or any(p.seat_id == seat_id for p in people):
            continue
        uid = marked.get(seat_id) or last_opened.get(seat_id)
        if uid:
            utterance = session._utterances[uid]
            text = shown[uid].text
        else:
            utterance = _one_piece(session, seat_id)
            if utterance is None:
                continue
            uid, text = utterance.id, utterance.text
        seat = seats[seat_id]
        people.append(Person(seat_id, seat.title, seat.kind, uid, text, not utterance.note, utterance.note, why))
    return people


def _one_piece(session, seat_id: str):
    """The first piece of the item asked last at one to one, or None."""
    asked = session.one_asked.get(seat_id) or []
    if not asked:
        return None
    found = {item: pieces for item, _, pieces in session.one_items(seat_id)}
    pieces = found.get(asked[-1]) or []
    return pieces[0] if pieces else None


def find_split(session, people: list[Person], sheet_heading) -> dict | None:
    """The first split whose two sides each hold a person on the map: one
    from each side (the one picked first), and its heading."""
    shown = {q.utterance_id: q.seat_id for r in session.rounds for q in r.quotes}
    for result in session.rounds:
        for split in result.splits:
            sides = []
            for side in (split.side_a, split.side_b):
                seats = {shown[uid] for uid in side if uid in shown}
                sides.append(next((i for i, p in enumerate(people) if p.seat_id in seats), None))
            if None not in sides and sides[0] != sides[1]:
                return {"heading": sheet_heading(split.heading), "a": sides[0], "b": sides[1]}
    return None


def parted_pairs(session, people: list[Person]) -> list[list[int]]:
    """直し50 段3: every two people on the map who stood on the two sides of
    one of the day's splits (as recorded: each side's quotes on screen), as
    [i, j] (people's indexes, i < j)."""
    shown = {q.utterance_id: q.seat_id for r in session.rounds for q in r.quotes}
    at: dict[str, list[int]] = {}
    for i, person in enumerate(people):
        at.setdefault(person.seat_id, []).append(i)
    pairs = set()
    for result in session.rounds:
        for split in result.splits:
            a = {i for uid in split.side_a if uid in shown for i in at.get(shown[uid], [])}
            b = {i for uid in split.side_b if uid in shown for i in at.get(shown[uid], [])}
            pairs |= {(min(i, j), max(i, j)) for i in a for j in b if i != j}
    return [list(pair) for pair in sorted(pairs)]


def place(people: list[Person], split: dict | None) -> list[Person]:
    """The sample's places: the split's two at the first two, the dashed line between."""
    order = list(range(len(people)))
    if split:
        order = [split["a"], split["b"]] + [i for i in order if i not in (split["a"], split["b"])]
    for slot, index in zip(SLOTS, order):
        people[index].x, people[index].y = slot
    return people


def split_questions(session) -> dict:
    """What the student sent with 「聞く」, read against the splits' headings
    (直し40-2): {own, rewritten, heading_sent, last}. A round started by an
    answer to an AI's question is not one."""
    headings = {split.heading.strip() for result in session.rounds for split in result.splits}
    asked = [(number, result.question.strip()) for number, result in enumerate(session.rounds, start=1)
             if result.question and result.ai_question is None]
    pressed = min((number for number, _ in session.pressed_splits), default=None)
    after = [question for number, question in asked if pressed is not None and number > pressed]
    own = [question for _, question in asked[1:] if question not in headings]
    mine = [question for _, question in asked if question not in headings]
    return {"own": own, "rewritten": next((q for q in after if q not in headings), ""),
            "heading_sent": any(q in headings for q in after), "last": mine[-1] if mine else ""}


def begin(session, opened: list[str], sheet_heading, start: tuple[str, str] | None = None) -> Hitokoto:
    first = next((r.question for r in session.rounds if r.question), "")
    talk = Hitokoto(first)
    asked = split_questions(session)
    talk.own_questions, talk.rewritten = asked["own"], asked["rewritten"]
    talk.heading_sent, talk.last_question = asked["heading_sent"], asked["last"] or first
    talk.people = pick_people(session, opened, start)
    if start and talk.people and talk.people[0].why == WHY_TRAIL:
        talk.start = 0
    talk.split = find_split(session, talk.people, sheet_heading)
    talk.parted = parted_pairs(session, talk.people)
    place(talk.people, talk.split)
    on_map = {p.seat_id for p in talk.people}
    met = [s for s in dict.fromkeys([*session.met_seats(), *session._one_seats()]) if s not in on_map]
    talk.grey = list(GREY_SLOTS[:len(met)])
    talk.counts = {"people": len(on_map) + len(met), "marks": len(session.marks), "cards": len(session.cards)}
    if not talk.people:  # No one to read: the first question, then the scale.
        talk.stage = SCALE
        talk.asked.append(Asked("scale", words()["scale_q"], "teacher"))
    return talk


# --- the checks ---

class Words:
    """What 「」 may hold: the record's words (the quotes shown, the people's
    cards and lit parts, the seats' titles) and the student's own words.
    reflection.Record's own_words hold every question and split heading, so
    they are not the student's here (直し40-2): the first question, the
    questions sent after it that are not a heading, and what was written here."""

    def __init__(self, session, talk: Hitokoto):
        self.record = Record(session)
        self.record.quote_texts += [p.text for p in talk.people]
        seats = {seat.seat_id: seat for seat in session.library.seats}
        titles = [seats[q.seat_id].title for r in session.rounds for q in r.quotes if q.seat_id in seats]
        titles += [seats[s].title for s in session.silent_seats() if s in seats]
        self.record.own_words = [w for w in [*titles, *student_words(talk), *talk.parts.values(), talk.chosen_part] if w]


def student_words(talk: Hitokoto) -> list[str]:
    """The student's own words (直し40-2): the first question, the questions
    sent with 「聞く」 after it that are not a split's heading, and what was
    written on this screen."""
    return [talk.first_question, *talk.own_questions, *(w["text"] for w in talk.written)]


def _outside(text: str) -> str:
    return normalize_for_match(_QUOTED.sub("", text))


def _starts_you_are(text: str) -> bool:
    plain = _QUOTED.sub("", text)
    return any(sentence.strip().startswith("あなたは") for sentence in re.split(r"[。．！!？?\n]", plain))


def question_stop(text: str, words_: Words, gate: Gate) -> str:
    """"" when the listener's question may be shown, else a reason code."""
    reason = checked(text, words_.record, gate, MAX_QUESTION)
    if reason:
        return reason
    text = text.strip()
    body = _outside(text)
    if any(normalize_for_match(lure) in body for lure in LURE_FORMS):
        return STOP_LURE
    if _starts_you_are(text):
        return STOP_YOU_ARE
    plain = _QUOTED.sub("", text)
    if not text.endswith(("？", "?")) or plain.count("？") + plain.count("?") != 1:
        return STOP_NOT_ONE_QUESTION
    if sum(body.count(word) for word in QUESTION_WORDS) > 1:
        return STOP_QUESTION_WORDS
    if has_avoid(text):
        return STOP_AVOID
    return ""


def light_stop(text: str, limit: int, words_: Words, gate: Gate) -> str:
    """The light's two sentences: as a question is checked, but a sentence,
    and no rote praise."""
    reason = checked(text, words_.record, gate, limit)
    if reason:
        return reason
    body = _outside(text)
    if any(normalize_for_match(lure) in body for lure in LURE_FORMS):
        return STOP_LURE
    if _starts_you_are(text):
        return STOP_YOU_ARE
    if any(normalize_for_match(word) in body for word in PRAISE_FORMS):
        return STOP_PRAISE
    if has_avoid(text):
        return STOP_AVOID
    return ""


def unquote_forces(text: str) -> str:
    """A force's name the model put in 「」 passes: 「」 taken off (the name
    is never in 「」 on screen)."""
    for number, name in FORCES.items():
        for form in (name, FORCE_WORDS[number]):
            text = text.replace(f"「{form}」", FORCE_WORDS[number])
    return text


# --- the listener ---

def _send(gate: Gate, role: str, system: str, data: dict, schema: dict, seconds: float, max_tokens: int):
    """(answer, reason, seconds waited): the answer is None when the model
    could not be used or did not answer in time."""
    started = time.monotonic()
    try:
        answer = json_answer(gate.send(role, json_request(role, system, json.dumps(data, ensure_ascii=False),
                                                          schema, max_tokens=max_tokens), timeout=seconds))
        reason = "" if isinstance(answer, dict) else "bad_output"
    except (GateError, ModelUnavailable) as error:
        answer, reason = None, str(error)
    return (answer if not reason else None), reason, round(time.monotonic() - started, 1)


def listener_system() -> str:
    return LISTENER_PROMPT.format(part_limit=MAX_PART, question_limit=MAX_QUESTION, banned="・".join(BANNED_WORDS))


PARTS_SCHEMA = {
    "type": "object",
    "properties": {"parts": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "string"}, "part": {"type": "string"}},
        "required": ["id", "part"], "additionalProperties": False}}},
    "required": ["parts"], "additionalProperties": False,
}
QUESTION_SCHEMA = {
    "type": "object", "properties": {"question": {"type": "string"}},
    "required": ["question"], "additionalProperties": False,
}


def ask_parts(gate: Gate, talk: Hitokoto) -> None:
    """Once: a short part of each card, lit where it is in the card word for word."""
    if talk.parts_asked or not talk.people:
        return
    talk.parts_asked = True
    data = {"task": "keywords", "first_question": talk.first_question,
            "cards": [{"id": str(i + 1), "text": p.text} for i, p in enumerate(talk.people)]}
    answer, reason, talk.parts_seconds = _send(gate, LISTENER, listener_system(), data, PARTS_SCHEMA,
                                               LISTENER_SECONDS, 1000)
    talk.parts_reason = reason
    for item in (answer or {}).get("parts") or []:
        if not isinstance(item, dict) or not isinstance(item.get("part"), str):
            continue
        part = item["part"].strip()
        index = int(item["id"]) - 1 if str(item.get("id", "")).isdigit() else -1
        if not 0 <= index < len(talk.people) or index in talk.parts:
            continue
        if part and len(part) <= MAX_PART and part in talk.people[index].text and not gate.names.hits(part):
            talk.parts[index] = part
    if answer is not None and not talk.parts:
        talk.parts_reason = "no_part_found"


def first_sentence(text: str) -> str:
    match = re.match(r"[^。．！!？?]+", text.strip())
    return match.group(0) if match else text.strip()


def chosen_words(talk: Hitokoto) -> str:
    """What the student picked: the lit part, else the card's first sentence."""
    if talk.chosen is None:
        return ""
    return talk.chosen_part or first_sentence(talk.people[talk.chosen].text)


def fixed_question(direction: str, talk: Hitokoto) -> str:
    texts = words()
    if direction == REACTION:
        return fill(texts["ask_reaction"], word=chosen_words(talk))
    return texts["ask_self"]


def ask_listener(gate: Gate, session, talk: Hitokoto, direction: str, answer: str = "") -> Asked:
    """The question of this direction: the listener's where it passes the
    checks, else the fixed one. answer: what the student wrote just before,
    left out when it is of home, money or health (not dug into)."""
    talk.listener_asked += 1
    if answer and has_avoid(answer):
        asked = Asked(direction, fixed_question(direction, talk), "fixed", STUDENT_AVOID)
        talk.asked.append(asked)
        return asked
    person = talk.people[talk.chosen] if talk.chosen is not None else None
    data = {"task": "question", "direction": direction, "first_question": talk.first_question,
            "chosen": chosen_words(talk), "card": person.text if person else "", "answer": answer}
    reply, reason, seconds = _send(gate, LISTENER, listener_system(), data, QUESTION_SCHEMA, LISTENER_SECONDS, 500)
    text = reply.get("question") if isinstance(reply, dict) else None
    if reply is not None:
        reason = question_stop(text, Words(session, talk), gate) if isinstance(text, str) else STOP_MISSING
    if reason:
        asked = Asked(direction, fixed_question(direction, talk), "fixed", reason, seconds)
    else:
        asked = Asked(direction, text.strip(), LISTENER, "", seconds)
    talk.asked.append(asked)
    return asked


# --- the light ---

LIGHT_SCHEMA = {
    "type": "object",
    "properties": {"quote": {"type": "string"}, "force": {"type": "integer"}, "why": {"type": "string"},
                   "deep": {"type": "string"}},
    "required": ["quote", "force", "why", "deep"], "additionalProperties": False,
}


NEXT_QUESTION = "next_question"  # A question sent after the first, not a heading (直し40-2).


def light_words(talk: Hitokoto) -> list[dict]:
    """The student's own words the light may pick from (student_words but the
    first question): never of home, money or health."""
    asked = [{"step": NEXT_QUESTION, "text": question} for question in talk.own_questions]
    return [w for w in [*talk.written, *asked] if not has_avoid(w["text"])]


def chosen_two(talk: Hitokoto) -> Person | None:
    return talk.people[talk.ladder_two] if talk.ladder_two is not None else None


def code_light(talk: Hitokoto, reason: str) -> Light:
    """The sample's chooseLight, in its order, with the forces' fixed sentences."""
    texts, sentences = words(), force_sentences()
    written = light_words(talk)
    longest = max((w["text"] for w in written if w["step"] in (REACTION, SELF, "fill")), key=len, default="")
    person = talk.people[talk.chosen] if talk.chosen is not None else None
    deep_word = fill(texts["deep_word"], who=person.title, word=chosen_words(talk)) if person else ""
    forward = talk.forward if not has_avoid(talk.forward) else ""
    way = talk.way if not has_avoid(talk.way) else ""
    scale = talk.scale

    def light(quote, force, deep, source="written", who=""):
        return Light(quote, source, force, sentences[force], deep, "code", reason, who)

    if scale is not None and scale < SCALE_FIRST and longest:
        return light(longest, 2, deep_word)
    if scale is not None and scale > SCALE_FIRST and forward:
        return light(forward, 5, texts["deep_more"])
    if way:
        return light(way, 2, texts["deep_way"])
    if scale == SCALE_FIRST and forward:
        return light(forward, 4, texts["deep_need"])
    # 直し40-2: a question rewritten from a split, before the sample's fifth.
    # A heading pressed, or sent as it was, is no ground for the light.
    if talk.rewritten and not has_avoid(talk.rewritten):
        return Light(talk.rewritten, "written", 5, texts["light_split"], "", "code", reason)
    if longest:
        return light(longest, 1, deep_word)
    two = chosen_two(talk)
    if two:
        return light(two.text, 2, texts["deep_chosen"], "chosen", two.title)
    return light(talk.first_question, 1, "", "first")


def ask_light(gate: Gate, session, talk: Hitokoto) -> Light:
    written = light_words(talk)
    two = chosen_two(talk)
    if not written and not two:
        return code_light(talk, NOTHING_WRITTEN)
    data = {"first_question": talk.first_question,
            "written": [{"id": str(i + 1), "step": w["step"], "text": w["text"]} for i, w in enumerate(written)],
            "chosen": "" if written else two.text,
            "forces": [{"number": n, "name": FORCE_WORDS[n]} for n in FORCES]}
    system = LIGHT_PROMPT.format(why_limit=MAX_WHY, deep_limit=MAX_DEEP, banned="・".join(BANNED_WORDS))
    reply, reason, seconds = _send(gate, LIGHT, system, data, LIGHT_SCHEMA, LIGHT_SECONDS, 1500)
    if reply is None:
        light = code_light(talk, reason)
        light.seconds = seconds
        return light
    quote = reply.get("quote").strip() if isinstance(reply.get("quote"), str) else ""
    force = reply.get("force")
    why = unquote_forces(reply.get("why").strip()) if isinstance(reply.get("why"), str) else ""
    deep = unquote_forces(reply.get("deep").strip()) if isinstance(reply.get("deep"), str) else ""
    sources = [w["text"] for w in written] if written else [two.text]
    check_words = Words(session, talk)
    if len(quote) < 2 or not any(quote in source for source in sources) or gate.names.hits(quote):
        reason = STOP_QUOTE_NOT_WRITTEN
    elif not isinstance(force, int) or isinstance(force, bool) or force not in FORCES:
        reason = STOP_FORCE
    elif not why or not deep:
        reason = STOP_MISSING
    else:
        reason = light_stop(why, MAX_WHY, check_words, gate) or light_stop(deep, MAX_DEEP, check_words, gate)
        if not reason and FORCE_WORDS[force] not in why:
            reason = STOP_FORCE_NOT_NAMED
    if reason:
        light = code_light(talk, reason)
    else:
        light = Light(quote, "written" if written else "chosen", force, why, deep, "model", "",
                      "" if written else two.title)
    light.seconds = seconds
    return light


def next_step(talk: Hitokoto) -> str:
    """The 前 answer, shown under the light when the doubt went down or stayed,
    and not already the light's words."""
    if talk.scale is None or talk.scale > SCALE_FIRST or not talk.forward or has_avoid(talk.forward):
        return ""
    return "" if talk.light and talk.light.quote == talk.forward else talk.forward


def light_view(talk: Hitokoto) -> dict:
    light = talk.light
    return {"scale": talk.scale, "quote": light.quote, "source": light.source, "chosen_who": light.chosen_who,
            "why": light.why, "deep": light.deep, "force": FORCES[light.force], "next_step": next_step(talk),
            "now_question": talk.now_question or talk.last_question or talk.first_question}


# --- the sheet ---

def story(talk: Hitokoto, shown: list[str] | None = None) -> list[dict]:
    """今日の道すじ, in the order things happened, from the record and the
    student's own words only (the AI writes none of it). 直し51 段2: words
    in full elsewhere on the sheet (shown) are not quoted again: the person's
    title and 「引っかかった」, or that the student wrote, said short."""
    texts = words()
    out: list[dict] = []

    def elsewhere(text: str) -> bool:
        return on_sheet(text, shown or [])

    if talk.people:
        out += segments(texts["story_people"], people="・".join(p.title for p in talk.people))
    # The split (直し40-2): a question rewritten from it, or the heading sent as it was.
    if talk.rewritten:
        out += segments(texts["story_split_new"])
    elif talk.heading_sent:
        out += segments(texts["story_split_same"])
    if talk.chosen is not None:
        word, who = chosen_words(talk), talk.people[talk.chosen].title
        out += (segments(texts["story_word_short"], who=who) if elsewhere(word)
                else segments(texts["story_word"], who=who, word=word))
    two = chosen_two(talk)
    if two:
        out += segments(texts["story_chosen"], who=two.title)
    first = next((w["text"] for w in talk.written if w["step"] in (REACTION, SELF, "fill")
                  and not has_avoid(w["text"])), "")
    if first:
        out += segments(texts["story_wrote_short"]) if elsewhere(first) else segments(texts["story_wrote"], text=first)
    if talk.scale is not None:
        out += segments(texts["story_scale"], n=talk.scale)
        if talk.scale > SCALE_FIRST and talk.forward and not has_avoid(talk.forward):
            out += (segments(texts["story_more_short"]) if elsewhere(talk.forward)
                    else segments(texts["story_more"], text=talk.forward))
    if talk.way and not has_avoid(talk.way):
        out += (segments(texts["story_way_short"]) if elsewhere(talk.way)
                else segments(texts["story_way"], text=talk.way))
    if talk.subject == "yes":
        out += (segments(texts["story_subject_note"], note=talk.subject_note)
                if talk.subject_note and not elsewhere(talk.subject_note) else segments(texts["story_subject"]))
    return out


# 直し51 段2 (ヒビキ, 49_sheet_notice_try: the same sentence three times on
# the one sheet thins 「なるほど」): one person's words, one sentence, and
# the student's own, in full once on the sheet; again, pointed at by a
# title or a heading of the sheet (texts/), never reworded nor cut. Kept in
# full where it is first read, but for the student's line that is the
# light, or the next step: in full in its own box at the foot (the sheet's
# own words, 直し51 段5), and 自分の言葉の動き points at it by its heading.

_BARE = re.compile(r"[\s　「」『』]+")


def bare(text: str) -> str:
    """The words to compare: no spaces nor 「」, no stop at the end."""
    return _TRAIL.sub("", _BARE.sub("", text or ""))


def on_sheet(text: str, shown: list[str]) -> bool:
    """Whether text is already in full on the sheet: itself, or within a
    sentence there (a part of a person's sentence is that sentence)."""
    body = bare(text)
    return bool(body) and any(body in bare(full) for full in shown if full)


# 直し48 段4 (the teacher, 11/7: 「これで本当に生徒はなるほど！となるか？」):
# more on the sheet, made by code from the record and the student's own
# words (no model writes any of it): each person met with one sentence of
# their words as recorded (the one the lit part is in, else the first) and
# their title; the student's own words in the order written, from the first
# question to the question as held now; the split, when the day had one; and
# one next step (the seat to meet and the force to use, else the 前 answer).

_SENTENCE = re.compile(r"[^。．！!？?\n]*[。．！!？?]?")


def sentence_with(text: str, part: str) -> str:
    """The whole sentence of text that part is in (word for word, as
    recorded); with no part, or part not found, the first sentence."""
    sentences = [m.group(0).strip() for m in _SENTENCE.finditer(text) if m.group(0).strip()]
    if part:
        for sentence in sentences:
            if part in sentence:
                return sentence
    return sentences[0] if sentences else text.strip()


def met_lines(talk: Hitokoto) -> list[dict]:
    """Each person on today's map, one sentence of their recorded words."""
    out = []
    for n, person in enumerate(talk.people):
        part = talk.parts.get(n) or (talk.chosen_part if n == talk.chosen else "")
        out.append({"title": person.title, "kind_label": KIND_LABELS.get(person.kind, ""),
                    "quote": sentence_with(person.text, part), "said": person.said, "note": person.note})
    return out


def own_moves(talk: Hitokoto) -> list[str]:
    """The student's own words, in the order written (none of home, money or
    health), the first question first; the question as held now last."""
    out = [talk.first_question]
    for written in talk.written:
        if written["text"] and not has_avoid(written["text"]) and written["text"] not in out:
            out.append(written["text"])
    now = talk.now_question or ""
    if now and now not in out:
        out.append(now)
    return out


def split_view(talk: Hitokoto) -> dict | None:
    """The day's split (the moderator's heading, as shown) and its two people's titles."""
    split = talk.split
    if not split or split.get("a") is None or split.get("b") is None:
        return None
    return {"heading": split["heading"], "a": talk.people[split["a"]].title, "b": talk.people[split["b"]].title}


TIE_KINDS = ("same", "differ")
SAME_ON_SPLIT = "same_on_split"  # 直し50 段3: the reason kept when 「同じ向き」 was held back.
TIE_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string", "enum": ["same", "differ", "none"]}, "a": {"type": "string"},
                   "b": {"type": "string"}},
    "required": ["kind", "a", "b"], "additionalProperties": False,
}


def ask_tie(gate: Gate, talk: Hitokoto) -> None:
    """司会（AI）のまとめ (直し48 段4): with two people or more, the model
    picks two and whether their sentences go the same way or part. It is
    sent the sentences only (met_lines: as recorded; no title, no name) and
    writes no words; code checks the two ids. Asked once; nothing on a failure."""
    if talk.tie_asked:
        return
    lines = met_lines(talk)
    if len(lines) < 2:
        talk.tie_asked = {"reason": NO_PEOPLE, "seconds": 0.0}
        return
    data = {"people": [{"id": str(n + 1), "text": line["quote"]} for n, line in enumerate(lines)]}
    reply, reason, seconds = _send(gate, LIGHT, TIE_PROMPT, data, TIE_SCHEMA, LIGHT_SECONDS, 200)
    if reply is not None:
        ids = [str(n + 1) for n in range(len(lines))]
        kind, a, b = reply.get("kind"), reply.get("a"), reply.get("b")
        if kind == "none":
            reason = "none"
        elif kind not in TIE_KINDS or a not in ids or b not in ids or a == b:
            reason = "bad_output"
        elif kind == "same" and sorted((int(a) - 1, int(b) - 1)) in talk.parted:
            # 直し50 段3: 「同じ向き」 for two who parted on a split of the day
            # (割れていたところ, just under it on the sheet) says both: shown
            # as none. 「分かれている」 goes on as it is.
            reason = SAME_ON_SPLIT
        else:
            talk.tie = {"kind": kind, "a": int(a) - 1, "b": int(b) - 1}
    talk.tie_asked = {"reason": reason, "seconds": seconds}


def tie_view(talk: Hitokoto) -> dict | None:
    if not talk.tie:
        return None
    lines = met_lines(talk)
    return {"kind": talk.tie["kind"], "a": lines[talk.tie["a"]], "b": lines[talk.tie["b"]]}


def notice_view(talk: Hitokoto) -> str:
    """直し49 段1: 今日の気づき on the sheet, the student's line as written
    (never a model's words); "" when none was written (no box, not 「なし」)."""
    return talk.notice_text if talk.notice in NOTICE_WRITE else ""


def try_view(talk: Hitokoto, meet: str = "") -> dict | None:
    """直し49 段2: 次にやってみること on the sheet: what was picked (texts/),
    the student's line as written (調べる・試す), or the seat to meet and the
    force to use (会って聞いてみる, as the card says it). None when まだ決めない
    or not asked: no box."""
    if talk.next_try not in (TRY_MEET, *TRY_WRITE):
        return None
    return {"answer": talk.next_try, "label": words()[f"try_{talk.next_try}"],
            "text": talk.next_try_text if talk.next_try in TRY_WRITE else "",
            "meet": meet if talk.next_try == TRY_MEET else ""}


def sheet_view(talk: Hitokoto, meet: str = "") -> dict:
    light = talk.light
    now = talk.now_question if talk.now_question and talk.now_question != talk.first_question else ""
    trying = try_view(talk, meet)
    step = "" if trying else next_step(talk)
    met, moves, notice = met_lines(talk), own_moves(talk), notice_view(talk)
    # 直し51 段2: what is in full on the sheet, read from the top: 今日の気づき,
    # the two questions, each person's sentence.
    shown = [notice, talk.first_question, now, *[m["quote"] for m in met]]
    lit = None
    if light:
        lit = {"quote": light.quote, "why": light.why}
        if bare(light.quote) == bare(talk.first_question):
            lit["ref"] = "first_label"  # The first question, in full above.
        elif light.source == "chosen" and on_sheet(light.quote, shown):
            lit["ref"], lit["who"] = "chosen", light.chosen_who  # （農家の言葉）: in full above.
        elif light.source == "chosen":
            lit["who"] = light.chosen_who
    own_light = bool(lit) and "ref" not in lit and "who" not in lit
    # 自分の言葉の動き: the first and the now question in full above, the light
    # and the next step in full below: each pointed at by its heading.
    tops = {bare(talk.first_question): "first_label"}
    if now:
        tops[bare(now)] = "sheet_now"
    refs = dict(tops)
    if own_light:
        refs.setdefault(bare(light.quote), "light_title")
    if step:
        refs.setdefault(bare(step), "sheet_step")
    moves_ref = [refs.get(bare(text), "") for text in moves]
    if all(moves_ref):  # Nothing of its own in full: no list of pointers alone.
        moves, moves_ref = [], []
    shown += [text for text, ref in zip(moves, moves_ref) if not ref]
    if own_light:
        shown.append(light.quote)
    if step:
        shown.append(step)
    tie = tie_view(talk)
    if tie and on_sheet(tie["a"]["quote"], shown) and on_sheet(tie["b"]["quote"], shown):
        tie["short"] = True  # The fixed line and the two titles.
    marks = []
    for m in talk.marks:
        mark = {"label": m["label"], "text": m["text"], "note": m["note"]}
        if bare(m["text"]) in tops:
            mark["ref"] = tops[bare(m["text"])]  # The question, in full above.
        marks.append(mark)
    shown += [m["note"] for m in talk.marks if m["note"]]
    if trying and trying["text"]:
        shown.append(trying["text"])
    return {"first_question": talk.first_question, "now_question": now, "story": story(talk, shown),
            "light": lit,
            # 直し49 段2: 次の一歩になりそうなこと only with no 次にやってみること
            # (one next step on the sheet, not two; its words are in 自分の言葉の動き).
            "next_step": step, "next_try": trying,
            # 直し45 段5: the steps marked on the trail, with the student's line.
            "marks": marks,
            # 直し48 段4.
            "met": met, "moves": moves, "moves_ref": moves_ref, "split": split_view(talk), "meet": meet,
            "tie": tie, "notice": notice}
