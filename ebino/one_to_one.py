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
    the data folder: 席・ページ・軸); with no such row, none.
"""

# 種類 in ask_questions.txt.
GROUP_ARTICLE = "記事"
GROUP_POSTER = "ポスター"
GROUP_CROSS = "県外・海外"
GROUP_OUTSIDER = "外から来た"
GROUPS = (GROUP_ARTICLE, GROUP_POSTER, GROUP_CROSS, GROUP_OUTSIDER)

# The axes of the words that have pages only, in the order asked.
CROSS_AXES = ("行く前", "向こうで", "帰ってきて", "これから")
OUTSIDER_AXES = ("来たわけ", "見えたこと", "したかったこと")

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


def write_tables(folder, utterances, kinds: dict[str, str]) -> dict:
    """Writes the two tables to fill when they are not there (folder: the
    ingest's output); never over the teacher's. kinds: {seat ID: kind}.
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
    tables = load_tables(folder)
    by_axis: dict[str, int] = {}
    for seat, found in tables["pages"].items():
        allowed = OUTSIDER_AXES if kinds.get(seat) == "outsider_teacher" else CROSS_AXES
        for axes in found.values():
            for axis in axes:
                if axis in allowed:
                    by_axis[axis] = by_axis.get(axis, 0) + 1
    asked = sum(1 for seat in ranking if tables["ranking"].get(seat))
    return {"pages_only_seats": len(pages), "pages": sum(len(found) for found in pages.values()),
            "pages_by_axis": by_axis, "ranking_seats": len(ranking), "ranking_questions": asked,
            "ranking_without": {"not_written_by_the_teacher": len(ranking) - asked}, "written": written}


def load_tables(folder) -> dict:
    """{"pages": {seat: {page: [axes]}}, "ranking": {seat: question}} from
    the teacher's tables in folder; a table missing or unreadable: empty."""
    from .texts import read_table
    out = {"pages": {}, "ranking": {}}
    try:
        for row in read_table(folder / PAGES_FILE, PAGES_COLUMNS, may_be_empty=("軸",)):
            axes = axes_of(row["軸"], CROSS_AXES + OUTSIDER_AXES)
            if axes and is_page(row["ページ"]):
                out["pages"].setdefault(row["席"], {})[row["ページ"]] = axes
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    try:
        for row in read_table(folder / RANKING_FILE, RANKING_COLUMNS, may_be_empty=("質問",)):
            if row["質問"].strip():
                out["ranking"][row["席"]] = row["質問"].strip()
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    return out
