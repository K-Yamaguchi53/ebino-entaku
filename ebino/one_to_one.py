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
import unicodedata

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
# A slide's pages tidied (one_tidy.py) that come to more than this many
# characters together are cut at a sentence's end to come to this many or
# fewer, the first sentence always whole (直し43: 「大きく超える」, 1.5 times).
ONE_CUT_CHARS = ONE_CHARS * 3 // 2

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


# 直し54 (the teacher, 11/8: 質問への回答になっていない): the kinds of talk
# (closing_kind_labels.tsv, given each piece at ingest) that answer each of
# the teacher's questions. An item's pieces of these kinds are shown first;
# a piece of another kind (plainly something else) is not shown for it; a
# piece with no kind stays (nothing says it is off). An item left with no
# piece is not offered. Items not here (本文, a poster's roles...) as before.
ITEM_KINDS = {
    ("記事", "プロフィール"): ("reason", "school_days"),
    ("記事", "仕事の内容"): ("daily", "values", "joy", "hardship", "skills"),
    ("記事", "高校生に一言"): ("to_students",),
    ("記事", "求める人材"): ("skills", "values", "to_students"),
    ("記事", "会社PR"): ("joy", "values", "local", "daily"),
    ("外から来た", "来たわけ"): ("reason", "local"),
    ("外から来た", "見えたこと"): ("local",),
    ("外から来た", "したかったこと"): ("future", "to_students"),
    ("県外・海外", "行く前"): ("reason",),
    ("県外・海外", "向こうで"): ("hardship", "joy", "daily"),
    ("県外・海外", "これから"): ("future",),
}
NO_KIND = "none"  # talk_kinds.NONE


def fit_kinds(group: str, item: str, pieces: list, kind_of: dict) -> list:
    """The item's pieces that may answer its question, those of its kinds
    first (each part in the order it came): see ITEM_KINDS."""
    wanted = ITEM_KINDS.get((group, item))
    if not wanted:
        return list(pieces)
    good = [p for p in pieces if kind_of.get(p.id, NO_KIND) in wanted]
    unknown = [p for p in pieces if kind_of.get(p.id, NO_KIND) in (NO_KIND, "", None)]
    return good + unknown


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


LINE = "_line"  # A row's line in its file (blank lines counted), for the teacher.


def _read(path, columns: tuple[str, ...]) -> list[dict]:
    """直し54c (the teacher's own table, typed by hand on the morning): a row
    with its last (empty) cell's tab left off, empty cells after the last,
    and columns of the teacher's own after the table's (a memo) are read as
    meant. Anything else as texts.read_table: the header's first columns
    these, the key cells filled, a cell more than the header an error."""
    numbered = [(n, line) for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1)
                if line.strip()]
    header = [cell.strip() for cell in numbered[0][1].split("\t")] if numbered else []
    if tuple(header[:len(columns)]) != columns:
        raise ValueError(f"{path.name} line {numbered[0][0] if numbered else 1}: columns do not match")
    rows = []
    for number, line in numbered[1:]:
        cells = [cell.strip() for cell in line.split("\t")]
        while len(cells) > len(header) and not cells[-1]:
            cells.pop()
        if len(cells) == len(columns) - 1:
            cells.append("")
        if not len(columns) <= len(cells) <= len(header) or not all(cells[:len(columns) - 1]):
            raise ValueError(f"{path.name} line {number}: wrong column count or empty cell")
        row = dict(zip(columns, cells))
        row[LINE] = number
        rows.append(row)
    return rows


def _key(columns: tuple[str, ...], row: dict) -> tuple[str, ...]:
    """A row's key cells as the pieces name them (直し54c): full-width
    letters and digits as half-width; a page 「3」「P3」「ｐ.３」 is p3."""
    out = []
    for column in columns[:-1]:
        cell = unicodedata.normalize("NFKC", row[column]).strip()
        if column == PAGES_COLUMNS[1]:
            cell = re.sub(r"[\s.]", "", cell).lower()
            cell = PAGE_SECTION + cell if cell.isdigit() else cell
        out.append(cell)
    return tuple(out)


def read_rows(path, columns: tuple[str, ...]) -> tuple[list[dict] | None, str]:
    """(rows, problem) of a table; rows None when it is not there or cannot
    be read. problem: "" or the table's name and the line it could not read
    there (直し36: it said nothing before); never a path or a cell."""
    if not path.exists():
        return None, ""
    try:
        return _read(path, columns), ""
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
        cells[_key(columns, row)] = row[columns[-1]].strip()
    for row in teacher or []:
        if row[columns[-1]].strip():
            cells[_key(columns, row)] = row[columns[-1]].strip()
    return {key: cell for key, cell in cells.items() if cell and cell != NONE_MARK}, unread


def _teacher_keys(folder, teacher_file: str, columns: tuple[str, ...]) -> set:
    """直し54: the keys of the rows the teacher filled (a teacher's row is
    the teacher's call: never fitted to kinds, fit_kinds)."""
    rows, problem = read_rows(folder / teacher_file, columns)
    if problem:
        return set()
    return {_key(columns, row) for row in rows or [] if row[columns[-1]].strip()}


def _words(cell: str) -> list[str]:
    text = cell or ""
    for mark in AXIS_SEPARATORS:
        text = text.replace(mark, "\t")
    return [word.strip() for word in text.split("\t") if word.strip()]


def teacher_page_problems(folder, utterances, kinds: dict[str, str]) -> tuple[int, list[str]]:
    """直し54c: (the rows the teacher filled in ask_pages.tsv, those that do
    not work as written), said at the server's start: a row whose seat or
    page the pieces do not have, whose 軸 names no axis, an axis of the other
    group, a word that is not an axis, or a seat and page written twice (the
    later row is used). Each by its line, the seat ID and the page; a seat
    or page cell that is no ID is not said (it may hold a name), nor the 軸."""
    rows, problem = read_rows(folder / PAGES_FILE, PAGES_COLUMNS)
    if problem or not rows:
        return 0, []
    pages = pages_only(utterances)
    seen: dict[tuple, int] = {}
    filled, out = 0, []
    for row in rows:
        cell = row[PAGES_COLUMNS[-1]].strip()
        if not cell:
            continue
        filled += 1
        seat, page = _key(PAGES_COLUMNS, row)
        known_seat = seat in pages or seat in kinds
        where = (f"{PAGES_FILE} {row[LINE]}行目（{seat if known_seat else '席ID?'} "
                 f"{page if is_page(page) else 'ページ?'}）")
        if (seat, page) in seen:
            out.append(f"{where}：{seen[(seat, page)]}行目と同じ席・ページ（あとの行を使う）")
        seen[(seat, page)] = row[LINE]
        if seat not in pages:
            out.append(f"{where}：この席IDは、ページだけの席にない")
            continue
        if page not in pages[seat]:
            out.append(f"{where}：この席にこのページはない（{pages[seat][0]}〜{pages[seat][-1]}）")
            continue
        if cell == NONE_MARK:
            continue
        allowed = axes_for(kinds.get(seat, ""))[1]
        hint = f"この席の軸：{'・'.join(allowed)}。出さないなら -"
        words = _words(cell)
        known = [word for word in words if word in CROSS_AXES + OUTSIDER_AXES]
        here = [word for word in known if word in allowed]
        if not known:
            out.append(f"{where}：軸の言葉が読めない（{hint}）")
        elif not here:
            out.append(f"{where}：この席の質問にない軸（{hint}）")
        elif len(here) < len(words):
            out.append(f"{where}：読めない言葉がある。読めた軸だけ使う（{hint}）")
    return filled, out


# 直し54d (the teacher, 11/8: 質問と回答を全員分見ておく): a question the teacher
# stops for a seat, having seen in the list (tools/list_one_answers.py) that
# its words do not answer it. Next to the other tables (ingested/); never
# written over (the list tool writes its header when it is not there).
HIDE_FILE = "ask_hide.tsv"
HIDE_COLUMNS = ("席", "項目")


def load_hidden(folder) -> tuple[set, list[dict], str]:
    """({(seat ID, item)} stopped, the rows, "" or the table not read)."""
    rows, problem = read_rows(folder / HIDE_FILE, HIDE_COLUMNS)
    rows = [row for row in rows or [] if row[HIDE_COLUMNS[1]].strip()]
    return {(_key(HIDE_COLUMNS, row)[0], row[HIDE_COLUMNS[1]].strip()) for row in rows}, rows, problem


def hide_problems(rows: list[dict], seats: set, items: set) -> list[str]:
    """The rows of ask_hide.tsv that stop nothing: a seat ID or an item that
    is not there (a cell that is neither is not said: it may hold a name)."""
    out = []
    for row in rows:
        seat, item = _key(HIDE_COLUMNS, row)[0], row[HIDE_COLUMNS[1]].strip()
        where = f"{HIDE_FILE} {row[LINE]}行目（{seat if seat in seats else '席ID?'} {item if item in items else '項目?'}）"
        if seat not in seats:
            out.append(f"{where}：この席IDはない")
        elif item not in items:
            out.append(f"{where}：この項目の名前はない（一覧の「項目」の欄から写す）")
    return out


# 直し54c: said at the server's start under a table not read (app.py).
UNREAD_HINT = {
    PAGES_FILE: "→ この表が読めないので、県外・海外と外から来た人の席の1対1の質問は、ひとつも出ません。",
    RANKING_FILE: "→ この表が読めないので、ランキングの質問は出ません。",
    HIDE_FILE: "→ この表が読めないので、止めたはずの質問も出ます。",
}
UNREAD_FIX = "  メモ帳で開き、UTF-8・タブ区切りのまま保存し直して、起動し直してください。"


def load_tables(folder) -> dict:
    """{"pages": {seat: {page: [axes]}}, "ranking": {seat: question},
    "unread": [the tables not read, by name and line]} from the teacher's
    tables in folder and the model's beside them (直し36): a row the teacher
    filled is the teacher's, 「-」 shows nothing; an empty one is the
    model's. A table not there is empty."""
    out = {"pages": {}, "ranking": {}, "unread": [],
           "teacher_pages": _teacher_keys(folder, PAGES_FILE, PAGES_COLUMNS)}
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
