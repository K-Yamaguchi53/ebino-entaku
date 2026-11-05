"""The questions of one to one, with a fast model where the teacher allowed it
(直し36).

The teacher's words (11/5 朝): 「最終的な質問は、その人その人ごとに、早いモデ
ルでパパッと出してもらってもいい。」 The role is asker (gate.py: Haiku,
effort low); every request goes through the gate, so no name is sent, and
what is sent is the ingest's words, the names already taken out.

At ingest, once for each seat whose words are pages only (県外・海外に出た人,
外から来た大人・先生 from a PDF), one request: which of the axes of its
group each page answers, 0 or more. Only the axes' names are taken from the
answer; any other word is dropped, and no sentence is taken at all.

At ingest, once for each seat with a ranking (an article's ランキング: what
it ranks differs from person to person), one request: the model reads the
ranking's paragraph and makes one question on it for that person. Code
checks it before it is kept (check_ranking); one check failed, no question
for that seat:
  - every run of kanji or katakana and every number in it is in the
    ranking's paragraph (the speaker's word_not_in_original, 直し31続き-1);
  - no banned word at all: a ranking has no teacher's question under it, so
    one in the paragraph stops it too; no name (the gate's list);
  - at most MAX_CHARS characters, one line, ending in 「？」.

At one to one, each time 「この人に聞く」 is pressed, one request: the
teacher's questions (texts/ask_questions.txt) offered then (up to three),
each with that item's paragraph, put to that person (rephrase). It is asked
for while the camera flies to the person, waits ONE_TIMEOUT_SECONDS at most
(no retry), and is shown only there: never written to texts/ or a table.
Code checks each before it is shown (check_rephrase), as the ranking's,
except that its words may come from the teacher's question too, a banned
word only stops it when the teacher's question does not hold it
(speaker.banned_added: 「どうして行こうと思ったの？」 holds 行こう), and it
is at most MAX_GROWTH times the teacher's question. One that fails, and
every one when no answer comes in time or the model cannot be used, is
shown as the teacher wrote it; the student is never kept waiting. Only
which was shown and why the teacher's was kept goes to the record.
A ranking's question (the teacher's table or the model's) is that person's
already and is not put again.

What the model gives at ingest is written to tables of its own next to the teacher's
(one_to_one.py: ask_pages_model.tsv and ask_ranking_model.tsv, the same
columns), never into the teacher's, and one_to_one.load_tables reads the
teacher's first. A seat written there once, with 「-」 for a page with no
axis or a ranking with no question that passed, is not asked again;
to have it made anew, the table is deleted and the ingest run again. A seat
whose rows the teacher filled every one of is not asked. A request that
fails or does not come back within INGEST_TIMEOUT_SECONDS leaves the seat
unwritten, so the next ingest asks again.
"""

import json
from collections import Counter
from dataclasses import dataclass

from . import one_to_one
from .banned_words import banned_in
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .prompts import ASK_PAGES, ASK_RANKING, ASK_REPHRASE
from .speaker import (_DIGITS, _KANJI_NUMBER, MAX_GROWTH, STOP_EMPTY, STOP_LONG, STOP_MISSING, STOP_NAME,
                      STOP_NUMBER, STOP_WORD, _plain, _words, banned_added)
from .texts import ask_questions

ROLE = "asker"
# At ingest no student waits: longer than at one to one.
INGEST_TIMEOUT_SECONDS = 30.0
# At one to one the student waits: past this, the teacher's questions
# (直し39: as long as the spoken words'; at 3 seconds the model was late 4 times in 6).
ONE_TIMEOUT_SECONDS = 8.0
# An item's paragraph sent at one to one: at most this many characters.
ITEM_CHARS = 400
# A page's words sent: about this many characters at most.
PAGE_CHARS = 800
# A ranking's paragraph sent: at most this many characters.
RANKING_CHARS = 600
# A question on a button: at most this many characters, ending in this.
MAX_CHARS = 40
QUESTION_END = "？"
# Why a question is not used (with speaker.py's STOP_EMPTY, STOP_NAME,
# STOP_WORD, STOP_NUMBER, STOP_LONG).
STOP_BANNED = "banned_word"
STOP_END = "no_question_mark"
STOP_LINES = "not_one_line"
STOP_SAME = "unchanged"  # The model gave the teacher's question back.
SHOWN_REPHRASED = "rephrased"
SHOWN_SKELETON = "skeleton"


def _pages_schema(axes: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "pages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "string"},
                        "axes": {"type": "array", "items": {"type": "string", "enum": axes}},
                    },
                    "required": ["page", "axes"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["pages"],
        "additionalProperties": False,
    }


def page_texts(utterances, seat_id: str, pages: list[str]) -> dict[str, str]:
    """{page: its words, joined, up to about PAGE_CHARS} in the pages' order."""
    out = {page: "" for page in pages}
    for utterance in utterances:
        if utterance.seat_id == seat_id and utterance.section in out and len(out[utterance.section]) < PAGE_CHARS:
            out[utterance.section] += utterance.text
    return {page: text[:PAGE_CHARS] for page, text in out.items()}


def pages_request(texts: dict[str, str], axes: list[tuple[str, str]]) -> dict:
    """axes: (name, the teacher's question) of the seat's group, in order."""
    data = {"axes": [{"name": name, "question": question} for name, question in axes],
            "pages": [{"page": page, "text": text} for page, text in texts.items()]}
    return json_request(ROLE, ASK_PAGES, json.dumps(data, ensure_ascii=False),
                        _pages_schema([name for name, _ in axes]), max_tokens=2000)


def sort_pages(gate: Gate, texts: dict[str, str], axes: list[tuple[str, str]]) -> dict[str, list[str]]:
    """{page: the axes it answers, in the questions' order} for every page
    sent; an axis or a page not sent is dropped. Raises GateError or
    ModelUnavailable (a reason code only)."""
    answer = json_answer(gate.send(ROLE, pages_request(texts, axes), timeout=INGEST_TIMEOUT_SECONDS))
    given = answer.get("pages") if isinstance(answer, dict) else None
    if not isinstance(given, list):
        raise ModelUnavailable("bad_output")
    names = [name for name, _ in axes]
    out = {page: [] for page in texts}
    for row in given:
        if not isinstance(row, dict) or row.get("page") not in out or not isinstance(row.get("axes"), list):
            continue
        said = {axis for axis in row["axes"] if isinstance(axis, str)}
        out[row["page"]] = [name for name in names if name in said]
    return out


def _not_in(question: str, *sources: str) -> str:
    """"" or why not: a number or a run of kanji or katakana of the
    question in none of the sources (as the speaker checks, 直し31続き-1)."""
    plains = [_plain(source) for source in sources]
    for word in _words(question):
        if not any(word in source for source in plains):
            return STOP_NUMBER if _DIGITS.fullmatch(word) or _KANJI_NUMBER.fullmatch(word) else STOP_WORD
    return ""


def _form(question: str) -> str:
    """"" or why not: its length and its end."""
    if "\n" in question or "\t" in question or "\r" in question:
        return STOP_LINES
    if len(question) > MAX_CHARS:
        return STOP_LONG
    if not question.endswith(QUESTION_END):
        return STOP_END
    return ""


def check_ranking(question: str, paragraph: str, gate: Gate) -> str:
    """"" when the question on a ranking may be kept; else why not."""
    question = question.strip()
    if not question:
        return STOP_EMPTY
    if gate.names.hits(question):
        return STOP_NAME
    if banned_in(question):  # Any: there is no teacher's question to compare with.
        return STOP_BANNED
    return _not_in(question, paragraph) or _form(question)


def ranking_paragraph(utterances, seat_id: str) -> str:
    """The seat's ranking as recorded: its paragraphs, each once, joined."""
    found: list[str] = []
    for utterance in utterances:
        if utterance.seat_id == seat_id and utterance.section == "ランキング":
            paragraph = utterance.paragraph or utterance.text
            if paragraph not in found:
                found.append(paragraph)
    return "\n".join(found)[:RANKING_CHARS]


RANKING_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}


def ranking_question(gate: Gate, paragraph: str) -> tuple[str, str]:
    """(the question, "") or ("", why not). Raises GateError or
    ModelUnavailable when no answer came (a reason code only)."""
    request = json_request(ROLE, ASK_RANKING, json.dumps({"ranking": paragraph}, ensure_ascii=False),
                           RANKING_SCHEMA, max_tokens=500)
    answer = json_answer(gate.send(ROLE, request, timeout=INGEST_TIMEOUT_SECONDS))
    question = answer.get("question") if isinstance(answer, dict) else None
    if not isinstance(question, str):
        raise ModelUnavailable("bad_output")
    reason = check_ranking(question, paragraph, gate)
    return ("", reason) if reason else (question.strip(), "")


def check_rephrase(question: str, skeleton: str, paragraph: str, gate: Gate) -> str:
    """"" when the teacher's question put to the person may be shown;
    else why not. skeleton: the teacher's question; paragraph: the item's."""
    question = question.strip()
    if not question:
        return STOP_EMPTY
    if gate.names.hits(question):
        return STOP_NAME
    if banned_added(question, skeleton):  # One the teacher's question holds stays.
        return STOP_BANNED
    reason = _not_in(question, skeleton, paragraph) or _form(question)
    if not reason and len(question) > len(skeleton) * MAX_GROWTH:
        reason = STOP_LONG
    if not reason and question == skeleton.strip():
        reason = STOP_SAME
    return reason


@dataclass(frozen=True)
class Rephrased:
    item: str
    skeleton: str  # The teacher's question.
    question: str  # "" when the teacher's is shown.
    reason: str = ""  # Why the teacher's is shown: a code.

    @property
    def shown(self) -> str:
        return SHOWN_REPHRASED if self.question else SHOWN_SKELETON

    @property
    def text(self) -> str:
        return self.question or self.skeleton

    def record(self) -> dict:
        """What is kept: which was shown and why, never the words."""
        return {"item": self.item, "shown": self.shown, "reason": self.reason}


def item_paragraph(pieces) -> str:
    """An item's paragraphs as recorded, each once, up to ITEM_CHARS."""
    found: list[str] = []
    for piece in pieces:
        paragraph = piece.paragraph or piece.text
        if paragraph not in found:
            found.append(paragraph)
    return "\n".join(found)[:ITEM_CHARS]


REPHRASE_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "question": {"type": "string"}},
                "required": ["id", "question"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["lines"],
    "additionalProperties": False,
}


def rephrase(gate: Gate, items: list[dict]) -> list[Rephrased]:
    """items: [{"id": the item, "question": the teacher's, "paragraph"}],
    all in one request. Each comes back put to the person, or the teacher's
    with a reason."""
    if not items:
        return []
    data = {"questions": [{"id": i["id"], "question": i["question"], "paragraph": i["paragraph"]} for i in items]}
    request = json_request(ROLE, ASK_REPHRASE, json.dumps(data, ensure_ascii=False), REPHRASE_SCHEMA, max_tokens=1000)
    try:
        answer = json_answer(gate.send(ROLE, request, timeout=ONE_TIMEOUT_SECONDS))
        lines = answer.get("lines") if isinstance(answer, dict) else None
        if not isinstance(lines, list):
            raise ModelUnavailable("bad_output")
    except (GateError, ModelUnavailable) as error:
        return [Rephrased(i["id"], i["question"], "", str(error)) for i in items]
    given = {line["id"]: line["question"] for line in lines
             if isinstance(line, dict) and isinstance(line.get("id"), str) and isinstance(line.get("question"), str)}
    out = []
    for i in items:
        question = given.get(i["id"])
        reason = STOP_MISSING if question is None else check_rephrase(question, i["question"], i["paragraph"], gate)
        out.append(Rephrased(i["id"], i["question"], "" if reason else question.strip(), reason))
    return out


def _append(path, columns: tuple[str, ...], rows: list[str]) -> None:
    """Rows added to the model's table, its header first when it is new."""
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="\n") as out:
        if new:
            out.write("\t".join(columns) + "\n")
        for row in rows:
            out.write(row + "\n")


def fill_tables(gate: Gate, folder, utterances, kinds: dict[str, str]) -> dict:
    """The model's tables at ingest (folder: the ingest's output). Returns
    counts for the ingest's report: no seat, name or words."""
    counts = {"page_seats_sorted": 0, "page_seats_already": 0, "page_seats_by_the_teacher": 0,
              "pages_by_axis": Counter(), "pages_no_axis": 0, "page_seats_not_sorted": Counter(),
              "ranking_made": 0, "ranking_not_made": Counter(), "ranking_already": 0,
              "ranking_by_the_teacher": 0, "ranking_not_asked": Counter(), "not_written": []}
    asked = ask_questions()
    teacher, _ = one_to_one.read_rows(folder / one_to_one.PAGES_FILE, one_to_one.PAGES_COLUMNS)
    filled = {(row["席"], row["ページ"]) for row in teacher or [] if row["軸"].strip()}
    path = folder / one_to_one.PAGES_MODEL_FILE
    model, problem = one_to_one.read_rows(path, one_to_one.PAGES_COLUMNS)
    if problem:  # Never written over: the teacher may want to look at it.
        counts["not_written"].append(problem)
    else:
        done = {row["席"] for row in model or []}
        for seat, pages in one_to_one.pages_only(utterances).items():
            if seat in done:
                counts["page_seats_already"] += 1
                continue
            if all((seat, page) in filled for page in pages):
                counts["page_seats_by_the_teacher"] += 1
                continue
            group, _ = one_to_one.axes_for(kinds.get(seat, ""))
            try:
                found = sort_pages(gate, page_texts(utterances, seat, pages), asked[group])
            except (GateError, ModelUnavailable) as error:
                counts["page_seats_not_sorted"][str(error)] += 1
                continue
            rows = []
            for page in pages:
                rows.append(f"{seat}\t{page}\t{'・'.join(found[page]) or one_to_one.NONE_MARK}")
                counts["pages_by_axis"].update(found[page])
                counts["pages_no_axis"] += not found[page]
            _append(path, one_to_one.PAGES_COLUMNS, rows)  # Seat by seat: what is done stays done.
            counts["page_seats_sorted"] += 1
    _fill_ranking(gate, folder, utterances, counts)
    for key in ("pages_by_axis", "page_seats_not_sorted", "ranking_not_made", "ranking_not_asked"):
        counts[key] = dict(counts[key])
    return counts


def _fill_ranking(gate: Gate, folder, utterances, counts: dict) -> None:
    """A question on each seat's ranking, in the model's table: the question,
    or 「-」 when it failed a check (no question for that seat). A request
    that failed or came back late leaves the seat to ask again."""
    teacher, _ = one_to_one.read_rows(folder / one_to_one.RANKING_FILE, one_to_one.RANKING_COLUMNS)
    filled = {row["席"] for row in teacher or [] if row["質問"].strip()}
    path = folder / one_to_one.RANKING_MODEL_FILE
    model, problem = one_to_one.read_rows(path, one_to_one.RANKING_COLUMNS)
    if problem:
        counts["not_written"].append(problem)
        return
    done = {row["席"] for row in model or []}
    for seat in one_to_one.ranking_seats(utterances):
        if seat in done:
            counts["ranking_already"] += 1
            continue
        if seat in filled:
            counts["ranking_by_the_teacher"] += 1
            continue
        try:
            question, reason = ranking_question(gate, ranking_paragraph(utterances, seat))
        except (GateError, ModelUnavailable) as error:
            counts["ranking_not_asked"][str(error)] += 1
            continue
        if reason:
            counts["ranking_not_made"][reason] += 1
        else:
            counts["ranking_made"] += 1
        _append(path, one_to_one.RANKING_COLUMNS, [f"{seat}\t{question or one_to_one.NONE_MARK}"])
