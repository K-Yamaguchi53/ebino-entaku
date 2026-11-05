"""One to one (直し34): a student and one seat. The questions offered are the
teacher's (texts/ask_questions.txt), one an item of that seat's words that
has some; what the seat says is its own paragraph for that item, as spoken
words where the speaker's checks let them through, as everywhere.

Which items a seat's words have:
  - an article (地域で働く大人, and 外から来た大人・先生 from a docx): its
    rows (ingest/article_docx.py USED_ROWS), 本文タイトル and 本文 one item;
  - a poster (探究をした先輩): its roles (ingest/poster_pdf.py ROLES);
  - pages only (県外・海外に出た人, 外から来た大人・先生 from a PDF): the
    axes a page answers, from the table the teacher keeps (ask_pages.tsv in
    the data folder: 席・ページ・軸), or where the teacher left a row empty,
    from the model's table beside it (直し36, asker.py); with neither, none.
"""

import re

# 種類 in ask_questions.txt.
GROUP_ARTICLE = "記事"
GROUP_POSTER = "ポスター"
GROUP_CROSS = "県外・海外"
GROUP_OUTSIDER = "外から来た"
GROUPS = (GROUP_ARTICLE, GROUP_POSTER, GROUP_CROSS, GROUP_OUTSIDER)

# The axes of the words that have pages only, in the order asked.
CROSS_AXES = ("行く前", "向こうで", "帰ってきて", "これから")
OUTSIDER_AXES = ("来たわけ", "見えたこと", "したかったこと")

# Each time, the questions offered: at most this many, of the items not asked yet.
ONE_QUESTIONS = 3
# The words shown for an item: its pieces as recorded, up to about this many characters.
ONE_CHARS = 160

# A ranking's item: its question is the seat's own (a table's), not the teacher's.
RANKING_ITEM = "ランキング"
# An article's sections that are one item, and those with no question.
ARTICLE_SAME_ITEM = {"本文タイトル": "本文"}
ARTICLE_NO_QUESTION = ("キャッチコピー", "ランキング")

# The teacher's tables, next to the ingest's output (data folder, ingested/),
# outside the repo (直し34-2). Ingest writes each with its rows to fill when
# it is not there, and never over one that is: the teacher's own stays.
PAGES_FILE = "ask_pages.tsv"  # 席・ページ・軸: which axes a page answers (0 or more).
RANKING_FILE = "ask_ranking.tsv"  # 席・質問: a seat's own question on its ranking (none: none shown).
PAGES_COLUMNS = ("席", "ページ", "軸")
RANKING_COLUMNS = ("席", "質問")
# The model's tables (直し36): the same columns, next to the teacher's, written
# by asker.py at ingest. Read after the teacher's: a row of the teacher's
# with something in it is the teacher's; empty (or not there), the model's.
PAGES_MODEL_FILE = "ask_pages_model.tsv"
RANKING_MODEL_FILE = "ask_ranking_model.tsv"
# In either table: nothing for this row. The teacher's 「-」 keeps it from
# being shown even when the model's table has something; the model writes
# it for a page with no axis and a seat it could make no question for, so
# that seat is not asked again.
NONE_MARK = "-"
PAGE_SECTION = "p"  # A page's section: p1, p2, ... (ingest/slides_pdf.py).
AXIS_SEPARATORS = ("・", "、", ",", " ", "　")


def is_page(section: str) -> bool:
    return section.startswith(PAGE_SECTION) and section[len(PAGE_SECTION):].isdigit()


def pages_only(utterances) -> dict[str, list[str]]:
    """{seat ID: its pages in order} for the seats whose words are pages only."""
    pages: dict[str, list[str]] = {}
    other: set[str] = set()
    for utterance in utterances:
        if is_page(utterance.section):
            if utterance.section not in pages.setdefault(utterance.seat_id, []):
                pages[utterance.seat_id].append(utterance.section)
        else:
            other.add(utterance.seat_id)
    return {seat: sorted(found, key=lambda p: int(p[len(PAGE_SECTION):]))
            for seat, found in pages.items() if seat not in other}


def ranking_seats(utterances) -> list[str]:
    """The seats with a ranking, in the order their pieces come."""
    seats: list[str] = []
    for utterance in utterances:
        if utterance.section == "ランキング" and utterance.seat_id not in seats:
            seats.append(utterance.seat_id)
    return seats


def axes_of(cell: str, allowed: tuple[str, ...]) -> list[str]:
    """The axes a 軸 cell names, in the order asked; any other word is dropped."""
    text = cell or ""
    for mark in AXIS_SEPARATORS:
        text = text.replace(mark, "\t")
    named = {word.strip() for word in text.split("\t") if word.strip()}
    return [axis for axis in allowed if axis in named]


def axes_for(kind: str) -> tuple[str, tuple[str, ...]]:
    """The group of questions and its axes for a seat whose words are pages only."""
    if kind == "outsider_teacher":
        return GROUP_OUTSIDER, OUTSIDER_AXES
    return GROUP_CROSS, CROSS_AXES


def write_tables(folder, utterances, kinds: dict[str, str], gate=None) -> dict:
    """Writes the two tables to fill when they are not there (folder: the
    ingest's output); never over the teacher's. kinds: {seat ID: kind}.
    gate: the model fills its own tables too (asker.py, 直し36); None, not.
    Returns the counts for the ingest's report (no seat, name or words)."""
    pages = pages_only(utterances)
    ranking = ranking_seats(utterances)
    written = []
    path = folder / PAGES_FILE
    if not path.exists():
        rows = ["\t".join(PAGES_COLUMNS)] + [f"{seat}\t{page}\t" for seat, found in pages.items() for page in found]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        written.append(PAGES_FILE)
    path = folder / RANKING_FILE
    if not path.exists():
        rows = ["\t".join(RANKING_COLUMNS)] + [f"{seat}\t" for seat in ranking]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        written.append(RANKING_FILE)
    model = None
    if gate is not None:
        from . import asker
        model = asker.fill_tables(gate, folder, utterances, kinds)
    tables = load_tables(folder)
    by_axis: dict[str, int] = {}
    for seat, found in tables["pages"].items():
        allowed = axes_for(kinds.get(seat, ""))[1]
        for axes in found.values():
            for axis in axes:
                if axis in allowed:
                    by_axis[axis] = by_axis.get(axis, 0) + 1
    asked = sum(1 for seat in ranking if tables["ranking"].get(seat))
    return {"pages_only_seats": len(pages), "pages": sum(len(found) for found in pages.values()),
            "pages_by_axis": by_axis, "ranking_seats": len(ranking), "ranking_questions": asked,
            "ranking_without": {"not_written": len(ranking) - asked}, "written": written,
            "unread": tables["unread"], "model": model}


def read_rows(path, columns: tuple[str, ...]) -> tuple[list[dict] | None, str]:
    """(rows, problem) of a table; rows None when it is not there or cannot
    be read. problem: "" or the table's name and the line it could not read
    there (直し36: it said nothing before); never a path or a cell."""
    from .texts import read_table
    if not path.exists():
        return None, ""
    try:
        return read_table(path, columns, may_be_empty=(columns[-1],)), ""
    except UnicodeDecodeError:
        lines = path.read_bytes().split(b"\n")
        bad = next((n for n, line in enumerate(lines, start=1) if not _utf8(line)), 1)
        return None, f"{path.name} line {bad}"
    except ValueError as error:  # read_table's: the name and a line number only.
        found = re.search(r"line (\d+)", str(error))
        return None, f"{path.name} line {found.group(1) if found else 1}"
    except OSError:
        return None, f"{path.name} line 1"


def _utf8(line: bytes) -> bool:
    try:
        line.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _cells(folder, teacher_file: str, model_file: str, columns: tuple[str, ...]) -> tuple[dict, list[str]]:
    """{the row's key cells: its last cell} to show, the teacher's first, and
    the tables that could not be read. A teacher's table that cannot be read
    shows nothing, the model's neither: its 「-」 could not be kept."""
    teacher, teacher_problem = read_rows(folder / teacher_file, columns)
    model, model_problem = read_rows(folder / model_file, columns)
    unread = [problem for problem in (teacher_problem, model_problem) if problem]
    if teacher_problem:
        return {}, unread
    cells: dict[tuple, str] = {}
    for row in model or []:
        cells[tuple(row[c] for c in columns[:-1])] = row[columns[-1]].strip()
    for row in teacher or []:
        if row[columns[-1]].strip():
            cells[tuple(row[c] for c in columns[:-1])] = row[columns[-1]].strip()
    return {key: cell for key, cell in cells.items() if cell and cell != NONE_MARK}, unread


def load_tables(folder) -> dict:
    """{"pages": {seat: {page: [axes]}}, "ranking": {seat: question},
    "unread": [the tables not read, by name and line]} from the teacher's
    tables in folder and the model's beside them (直し36): a row the teacher
    filled is the teacher's, 「-」 shows nothing; an empty one is the
    model's. A table not there is empty."""
    out = {"pages": {}, "ranking": {}, "unread": []}
    cells, unread = _cells(folder, PAGES_FILE, PAGES_MODEL_FILE, PAGES_COLUMNS)
    out["unread"] += unread
    for (seat, page), cell in cells.items():
        axes = axes_of(cell, CROSS_AXES + OUTSIDER_AXES)
        if axes and is_page(page):
            out["pages"].setdefault(seat, {})[page] = axes
    cells, unread = _cells(folder, RANKING_FILE, RANKING_MODEL_FILE, RANKING_COLUMNS)
    out["unread"] += unread
    for (seat,), cell in cells.items():
        out["ranking"][seat] = cell
    return out
