"""Today's harvest card ③ 教科とのつながり (SPEC 5-3, 14-1, 14-4).

    あなたの問いに近い考え方は、〔いつ〕〔科目〕の「〔見出し〕」にある。
    〔ひとこと〕

The candidates are the teacher's table (texts/harvest_subjects.tsv) and the
札 theirs too (texts/harvest_fuda.tsv), copied as they are. Who learns each
subject (学ぶ人) comes from school papers, so it is never in the repository:
it is read from EBINO_DATA_DIR/kyoka_manabu.tsv (札・科目・項目番号・学ぶ人,
keyed by 札＋科目＋項目番号; samples/ holds an invented one of the same
shape). A candidate with no 学ぶ人 row is never shown; with no file, ③ is
not shown at all.

1. The candidates are narrowed to the subjects this student learns, by the
   answer to the first question (the Lab) and the marks in 学ぶ人. A student
   who did not say gets only the rows for every student: 学科不明, 中2, 中3,
   全員, and rows with both み1 and 生1 or all of Q2, A2 and C2 (never a
   subject chosen in year 2).
2. The model (the gate, Haiku) reads the record: the question rewritten (or
   the one held now), the answer to the question back and the move picked.
   It answers with one 札 (or なし) and two numbers given in that request
   only; it writes no sentence. It is given the 札's names and descriptions,
   the numbers, subjects and ひとこと, and the record's words, never 学ぶ人,
   a Lab or a company.
3. Code checks the answer: a 札 not in the table, or a number not among that
   札's narrowed candidates, is not used; numbers missing are filled by
   code's way below.
4. When the model says なし, names a 札 with no candidate left for this
   student, or cannot be used or does not answer: of all the narrowed
   candidates, the one whose clue words (手がかりの言葉) the record holds
   most (ties in table order) gives the 札, and the second is the next by
   clue words within that 札 only, so the 札 recorded and the subjects shown
   agree.
   No clue word held either (直し31-3): ③ is never left empty. Two of the
   narrowed candidates, of two 札 when there are, fewest shown first, are
   shown side by side and the student picks the one they think nearer, or
   neither; which is kept. No model gives a reason: each shows its ひとこと.
5. Of the two, the one shown fewer times so far is shown (a tie: the one
   first). 「ほかの教科も見る」 shows the other, then the rest of that 札's
   narrowed candidates, fewest shown first, then starts again. Every one shown
   is counted. The counts are kept in EBINO_RECORDS_DIR by candidate alone
   (records.py: no name, number or time with them) and go when the records
   go (SPEC 2-1).

③ is shown as a card tied by a line to the student's question as they hold
it now (their own words, as on the sheet): いつ・科目・見出し・ひとこと.
The screen never gets the item number (項目番号), the text quoted from the
course of study, the words 「学習指導要領」 or a Lab's name.
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .ingest.scrub import normalize_for_match
from .prompts import SUBJECT_FUDA
from .reflection import CHOSE_OWN, DIRECTION_LABELS
from .texts import (HARVEST_SUBJECT_CHOOSE, HARVEST_SUBJECT_LINK, HARVEST_SUBJECT_NONE_LINE, HARVEST_FUDA, HARVEST_SUBJECT_LINE, HARVEST_SUBJECT_LINE_PLAIN, HARVEST_SUBJECT_WHEN,
                    HARVEST_SUBJECTS, load_table, load_text, read_table)

ROLE = "subjects"
MANABU_FILE = "kyoka_manabu.tsv"
NONE = "なし"
PICKS = 2
LIST_MARK = "・"  # Between the marks in 学ぶ人, and between the clue words.

SUBJECT_COLUMNS = ("札", "科目", "項目番号", "本文の該当句", "見出し", "ひとこと", "手がかりの言葉")
FUDA_COLUMNS = ("札", "名前", "説明")
MANABU_COLUMNS = ("札", "科目", "項目番号", "学ぶ人")
WHEN_COLUMNS = ("記号", "いつ")

# Every mark in 学ぶ人, in the order that decides 〔いつ〕 when two or more of
# a row's marks fit the student: year 1 (and 全員, 学科不明: the high school's
# subjects for everyone now), then year 2, then junior high.
MARKS = ("み1", "生1", "全員", "学科不明", "Q2", "A2", "C2", "Q2選択", "A2選択", "C2選択", "中2", "中3")
EVERYONE = frozenset({"中2", "中3", "全員"})
LAB_MARKS = {
    "quest": frozenset({"み1", "Q2", "Q2選択"}) | EVERYONE,
    "action": frozenset({"み1", "A2", "A2選択"}) | EVERYONE,
    "creation": frozenset({"生1", "C2", "C2選択"}) | EVERYONE,
}
# Not said (or not known): the course is unknown.
NOT_SAID_MARKS = frozenset({"学科不明"}) | EVERYONE
BOTH_FIRST_YEARS = frozenset({"み1", "生1"})
ALL_SECOND_YEARS = frozenset({"Q2", "A2", "C2"})

SOURCE_MODEL = "model"
SOURCE_CODE = "code"  # The clue words, when the model was not used.
SHOWN = "shown"
STATUS_OFF = "off"  # No table loaded (tests that build no catalog).
STATUS_NO_MANABU = "no_manabu_file"
STATUS_NO_CANDIDATE = "no_candidate"  # Nothing at all for this student: no ③.
# Neither the model nor the clue words gave one: two shown, the student picks (直し31-3).
STATUS_CHOOSE = "student_chooses"
SOURCE_STUDENT = "student"
CHOSE_NONE = "none"  # 「どれも選ばない」
BAD_FUDA = "unknown_fuda"
# The wait for the model, with no retry (直し31-1): past it the clue words pick.
TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class Row:
    fuda: str
    subject: str
    item: str  # 項目番号: in the key only, never on the screen or to a model.
    heading: str  # "" when the line names the subject alone.
    note: str  # ひとこと
    clues: tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.fuda}|{self.subject}|{self.item}"


@dataclass(frozen=True)
class Candidate:
    row: Row
    when: str  # The mark that decides 〔いつ〕 for this student.


@dataclass
class Catalog:
    fuda: dict[str, tuple[str, str]]  # 札 -> (名前, 説明), in table order.
    rows: list[Row]
    manabu: dict[str, frozenset[str]] | None  # Key -> marks. None: no file.
    when_words: dict[str, str]
    not_in_table: int = 0  # 学ぶ人 rows whose key is not a candidate.

    def without_manabu(self) -> int:
        return 0 if self.manabu is None else sum(1 for row in self.rows if row.key not in self.manabu)

    def candidates(self, lab: str) -> list[Candidate]:
        """The rows this student learns, in table order."""
        if self.manabu is None:
            return []
        found = []
        for row in self.rows:
            fit = fitting_marks(self.manabu.get(row.key, frozenset()), lab)
            if fit:
                found.append(Candidate(row, fit[0]))
        return found

    def report(self) -> str:
        """For the console when the app starts: counts only."""
        if self.manabu is None:
            return f"subject rows {len(self.rows)}  {MANABU_FILE} not found: ③ is not shown"
        return (f"subject rows {len(self.rows)}  without 学ぶ人 (not shown): {self.without_manabu()}  "
                f"学ぶ人 rows not in the table: {self.not_in_table}")


def fitting_marks(marks: frozenset[str], lab: str) -> list[str]:
    """The row's marks that fit this student, in MARKS order; [] when the
    row is not for them."""
    if lab in LAB_MARKS:
        fit = set(marks & LAB_MARKS[lab])
    else:
        fit = set(marks & NOT_SAID_MARKS)
        if BOTH_FIRST_YEARS <= marks:
            fit |= BOTH_FIRST_YEARS
        if ALL_SECOND_YEARS <= marks:
            fit |= ALL_SECOND_YEARS
    return [mark for mark in MARKS if mark in fit]


def _items(cell: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in cell.split(LIST_MARK) if part.strip())


def read_rows(rows: list[dict[str, str]], fuda: dict[str, tuple[str, str]]) -> list[Row]:
    found, keys = [], set()
    for number, cells in enumerate(rows, start=2):
        row = Row(cells["札"], cells["科目"], cells["項目番号"], cells["見出し"], cells["ひとこと"],
                  _items(cells["手がかりの言葉"]))
        if row.fuda not in fuda or row.key in keys:
            raise ValueError(f"harvest_subjects.tsv line {number}: unknown 札 or the same row twice")
        keys.add(row.key)
        found.append(row)
    return found


def read_manabu(path: Path) -> tuple[dict[str, frozenset[str]], list[str]]:
    """Key -> marks, and the keys in file order. An unknown mark stops."""
    manabu, keys = {}, []
    for number, cells in enumerate(read_table(path, MANABU_COLUMNS), start=2):
        marks = frozenset(_items(cells["学ぶ人"]))
        if not marks or marks - set(MARKS):
            raise ValueError(f"{path.name} line {number}: unknown mark")
        key = f"{cells['札']}|{cells['科目']}|{cells['項目番号']}"
        if key in manabu:
            raise ValueError(f"{path.name} line {number}: the same row twice")
        manabu[key] = marks
        keys.append(key)
    return manabu, keys


def load_when_words() -> dict[str, str]:
    words = {row["記号"]: row["いつ"] for row in load_table(HARVEST_SUBJECT_WHEN, WHEN_COLUMNS)}
    if set(words) != set(MARKS):
        raise ValueError("harvest_subject_when.tsv must hold every mark once")
    return words


def load_catalog(data_dir: Path) -> Catalog:
    fuda = {row["札"]: (row["名前"], row["説明"]) for row in load_table(HARVEST_FUDA, FUDA_COLUMNS, ("説明",))}
    rows = read_rows(load_table(HARVEST_SUBJECTS, SUBJECT_COLUMNS, ("見出し",)), fuda)
    path = data_dir / MANABU_FILE
    if not path.exists():
        return Catalog(fuda, rows, None, load_when_words())
    manabu, keys = read_manabu(path)
    in_table = {row.key for row in rows}
    return Catalog(fuda, rows, manabu, load_when_words(), sum(1 for key in keys if key not in in_table))


# --- choosing ---

@dataclass
class Pick:
    """③ for one sitting. order is what the screen goes through; index the
    one shown now."""

    status: str
    fuda: str = ""
    source: str = ""
    model_error: str = ""  # Why the model's answer was not used: a code.
    order: list[Candidate] = field(default_factory=list)
    index: int = 0
    presses: int = 0  # 「ほかの教科も見る」
    model_said: str = ""  # The model's 札 (or なし) when code picked instead.
    chosen: str = ""  # STATUS_CHOOSE: the key the student picked, or CHOSE_NONE.
    offered: list[str] = field(default_factory=list)  # STATUS_CHOOSE: the two keys shown.

    def shown(self) -> Candidate | None:
        return self.order[self.index] if self.order else None

    @property
    def two_shown(self) -> bool:
        """Both of the two are on the screen: still to pick, or neither picked."""
        return self.status == STATUS_CHOOSE and self.chosen in ("", CHOSE_NONE)

    def on_screen(self) -> list[Candidate]:
        return self.order[:2] if self.two_shown else [c for c in [self.shown()] if c]


def record_words(reflection) -> dict[str, str]:
    """The record the model reads: the question rewritten (or held now), the
    answer to the question back, the move picked (its direction, or the
    student's own words)."""
    if reflection.chosen == CHOSE_OWN:
        move = reflection.own_move
    else:
        move = DIRECTION_LABELS.get(reflection.chosen, "")
    return {"question": reflection.rewrite or reflection.now_question,
            "answer": "" if reflection.declined else reflection.answer,
            "move": move}


def clue_hits(row: Row, words: dict[str, str]) -> int:
    body = normalize_for_match(" ".join(words.values()))
    return sum(1 for clue in row.clues if normalize_for_match(clue) and normalize_for_match(clue) in body)


def by_clues(candidates: list[Candidate], words: dict[str, str]) -> list[Candidate]:
    """Most clue words held first; ties in table order."""
    return sorted(candidates, key=lambda c: -clue_hits(c.row, words))


SCHEMA_NUMBERS = {"type": "array", "items": {"type": "integer"}}


def request_for(catalog: Catalog, numbered: list[Candidate], words: dict[str, str]) -> dict:
    schema = {
        "type": "object",
        "properties": {"fuda": {"type": "string", "enum": [*catalog.fuda, NONE]}, "numbers": SCHEMA_NUMBERS},
        "required": ["fuda", "numbers"],
        "additionalProperties": False,
    }
    data = {
        "fuda": [{"id": fuda_id, "name": name, "description": about}
                 for fuda_id, (name, about) in catalog.fuda.items()],
        "candidates": [{"fuda": c.row.fuda, "number": number, "subject": c.row.subject, "note": c.row.note}
                       for number, c in enumerate(numbered, start=1)],
        "record": words,
    }
    return json_request(ROLE, SUBJECT_FUDA, json.dumps(data, ensure_ascii=False), schema, max_tokens=1000)


def _ask(gate: Gate, catalog: Catalog, numbered: list[Candidate], words) -> tuple[str, list, str]:
    """(札, numbers, error code); 札 is "" when the answer cannot be used."""
    try:
        answer = json_answer(gate.send(ROLE, request_for(catalog, numbered, words), timeout=TIMEOUT_SECONDS))
    except (GateError, ModelUnavailable) as error:
        return "", [], str(error)
    fuda = answer.get("fuda") if isinstance(answer, dict) else None
    numbers = answer.get("numbers") if isinstance(answer, dict) else None
    if fuda != NONE and fuda not in catalog.fuda:
        return "", [], BAD_FUDA
    numbers = [n for n in numbers if isinstance(n, int) and not isinstance(n, bool)] if isinstance(numbers, list) else []
    return fuda, numbers, ""


def _ordered(picked: list[Candidate], pool: list[Candidate], counts: Counter) -> list[Candidate]:
    """The two picked, fewer shown first; then the rest of the 札's pool,
    fewest shown first. Ties keep their order (sorted is stable)."""
    first = sorted(picked, key=lambda c: counts[c.row.key])
    rest = sorted((c for c in pool if c not in picked), key=lambda c: counts[c.row.key])
    return first + rest


def choose(gate: Gate, catalog: Catalog | None, lab: str, words: dict[str, str], counts: Counter) -> Pick:
    if catalog is None:
        return Pick(STATUS_OFF)
    if catalog.manabu is None:
        return Pick(STATUS_NO_MANABU)
    candidates = catalog.candidates(lab)
    if not candidates:  # Nothing could be shown: the model is not asked.
        return Pick(STATUS_NO_CANDIDATE)
    fuda, numbers, error = _ask(gate, catalog, candidates, words)
    pool = [c for c in candidates if c.row.fuda == fuda] if fuda and fuda != NONE else []
    if pool:
        picked: list[Candidate] = []
        for number in numbers:
            if 1 <= number <= len(candidates) and candidates[number - 1] in pool \
                    and candidates[number - 1] not in picked:
                picked.append(candidates[number - 1])
        for candidate in by_clues(pool, words):  # Filled by code's way.
            if len(picked) >= PICKS:
                break
            if candidate not in picked:
                picked.append(candidate)
        picked = picked[:PICKS]
        return Pick(SHOWN, fuda=fuda, source=SOURCE_MODEL, order=_ordered(picked, pool, counts))
    # なし, a 札 with nothing for this student, or no model: the clue words.
    said = fuda
    ranked = by_clues(candidates, words)
    if not clue_hits(ranked[0].row, words):
        # None held either: two to pick from, never an empty ③ (直し31-3).
        two = two_to_choose(candidates, counts)
        return Pick(STATUS_CHOOSE, source=SOURCE_STUDENT, model_error=error, model_said=said, order=two,
                    offered=[c.row.key for c in two])
    # The first one's 札 is the 札; the second comes from the same 札 only,
    # so the 札 recorded and the subjects on screen always agree.
    fuda = ranked[0].row.fuda
    pool = [c for c in candidates if c.row.fuda == fuda]
    picked = by_clues(pool, words)[:PICKS]
    return Pick(SHOWN, fuda=fuda, source=SOURCE_CODE, model_error=error, model_said=said,
                order=_ordered(picked, pool, counts))


def two_to_choose(candidates: list[Candidate], counts: Counter) -> list[Candidate]:
    """The one shown fewest times so far (ties in table order), and the next
    such of another 札 (of the same when there is no other)."""
    ranked = sorted(candidates, key=lambda c: counts[c.row.key])
    other = [c for c in ranked[1:] if c.row.fuda != ranked[0].row.fuda] or ranked[1:]
    return ranked[:1] + other[:1]


def pick_one(catalog: Catalog, lab: str, pick: Pick, choice, counts: Counter) -> None:
    """The student picked one of the two (0 or 1) or neither (CHOSE_NONE).
    Picked: it is shown alone, then 「ほかの教科も見る」 goes through its 札."""
    if choice == CHOSE_NONE:
        pick.chosen = CHOSE_NONE
        return
    chosen = pick.order[choice]
    pool = [c for c in catalog.candidates(lab) if c.row.fuda == chosen.row.fuda]
    pick.chosen, pick.fuda = chosen.row.key, chosen.row.fuda
    pick.order, pick.index = _ordered([chosen], pool, counts), 0


# --- what the screen and the records get ---

def line(catalog: Catalog, candidate: Candidate) -> str:
    row = candidate.row
    template = load_text(HARVEST_SUBJECT_LINE if row.heading else HARVEST_SUBJECT_LINE_PLAIN)
    return template.format(**{"いつ": catalog.when_words[candidate.when], "科目": row.subject, "見出し": row.heading})


def view(catalog: Catalog | None, pick: Pick | None, question: str = "") -> dict | None:
    """None when no ③ is shown (nothing at all for this student). The
    question is the student's own, tied to the card by a line on screen."""
    shown = pick.shown() if pick else None
    if catalog is None or shown is None:
        return None
    two = pick.two_shown
    cards = [{"when": catalog.when_words[c.when], "subject": c.row.subject, "heading": c.row.heading,
              "note": c.row.note, "line": line(catalog, c)} for c in pick.on_screen()]
    # Over the cards: pick one; or, once neither was picked, a line that does
    # not say they are tied (直し31続き-3); else that they are tied.
    link = HARVEST_SUBJECT_LINK
    if two and not pick.chosen:
        link = HARVEST_SUBJECT_CHOOSE
    elif two and pick.chosen == CHOSE_NONE:
        link = HARVEST_SUBJECT_NONE_LINE
    return {"line": line(catalog, shown), "note": shown.row.note, "more": len(pick.order) > 1 and not two,
            "question": question, "link": load_text(link),
            "choose": two and not pick.chosen, "cards": cards}


def record(pick: Pick | None) -> dict | None:
    """The 札, how it was picked, and the key of the candidate last on the
    screen; never the record's words."""
    if pick is None:
        return None
    shown = pick.shown()
    return {"status": pick.status, "fuda": pick.fuda, "source": pick.source, "model_error": pick.model_error,
            "model_said": pick.model_said, "shown": shown.row.key if shown else "", "presses": pick.presses,
            # The two offered and the one the student picked (or none) (直し31-3).
            "offered": list(pick.offered),
            "chosen": pick.chosen}
