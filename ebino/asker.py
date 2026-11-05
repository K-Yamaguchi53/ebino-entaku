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

What the model gives is written to tables of its own next to the teacher's
(one_to_one.py: ask_pages_model.tsv, the same columns), never into the
teacher's, and one_to_one.load_tables reads the teacher's first. A seat
written there once, with 「-」 for a page with no axis, is not asked again;
to have it made anew, the table is deleted and the ingest run again. A seat
whose rows the teacher filled every one of is not asked. A request that
fails or does not come back within INGEST_TIMEOUT_SECONDS leaves the seat
unwritten, so the next ingest asks again.
"""

import json
from collections import Counter

from . import one_to_one
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .prompts import ASK_PAGES
from .texts import ask_questions

ROLE = "asker"
# At ingest no student waits: longer than at one to one.
INGEST_TIMEOUT_SECONDS = 30.0
# A page's words sent: about this many characters at most.
PAGE_CHARS = 800


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
              "not_written": []}
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
    counts["pages_by_axis"] = dict(counts["pages_by_axis"])
    counts["page_seats_not_sorted"] = dict(counts["page_seats_not_sorted"])
    return counts
