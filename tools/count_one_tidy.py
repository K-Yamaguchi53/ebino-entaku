"""直し43: how one_tidy.py tidies the slides' pages at one to one, in counts
only, for the teacher to run on the real data. For each seat whose words
are pages only and each item one to one offers it (or would, the axes the
tables give its pages): its pages, the titles' lines that went, the pages
that came out empty, and those not shown for a name.

    .venv\\Scripts\\python tools\\count_one_tidy.py

It reads the data folder (EBINO_DATA_DIR, from .env when it is not set) as
the app does, and prints a table: 席・項目・ページ・表題・空・名前, then
the totals. It never prints words, a name or a path, never writes a file,
and never asks the model (the name list is checked by code only).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebino import config, one_tidy, one_to_one  # noqa: E402
from ebino.gate import Gate, load_names  # noqa: E402

COLUMNS = ("席", "項目", "ページ", "表題", "空", "名前")


class NoModel:
    """The gate's client: never asked here."""

    @property
    def messages(self):
        raise RuntimeError("count_one_tidy asks no model")


def count(session) -> list[dict]:
    """A row for each item of each seat whose words are pages only."""
    rows = []
    pages = one_to_one.pages_only(session.library.utterances)
    tables = session.library.ask_tables["pages"]
    seats = {seat.seat_id: seat for seat in session.library.all_seats}
    for seat_id in pages:
        if seat_id not in seats:
            continue
        _, axes = one_to_one.axes_for(seats[seat_id].kind)
        for item in axes:
            found = [u for u in session.library.utterances if u.seat_id == seat_id and one_to_one.is_page(u.section)
                     and item in tables.get(seat_id, {}).get(u.section, [])]
            if not found:
                continue
            tidied = [session.one_page(u) for u in found]
            rows.append({"席": seat_id, "項目": item, "ページ": len(found),
                         "表題": sum(one_tidy.DROP_TITLE in t.reasons for t in tidied),
                         "空": sum(one_tidy.EMPTY in t.reasons for t in tidied),
                         "名前": sum(one_tidy.NAME in t.reasons for t in tidied)})
    return rows


def table(rows: list[dict]) -> str:
    lines = ["\t".join(COLUMNS)]
    lines += ["\t".join(str(row[c]) for c in COLUMNS) for row in rows]
    totals = {c: sum(row[c] for row in rows) for c in COLUMNS[2:]}
    lines.append("\t".join(["計", str(len(rows))] + [str(totals[c]) for c in COLUMNS[2:]]))
    return "\n".join(lines)


def main() -> int:
    from ebino.session import Library, Session
    config.load_env_file()
    try:
        folder = config.data_dir()
    except config.PlaceError as error:
        print(f"count_one_tidy: {error}", file=sys.stderr)
        return 2
    library = Library.load(folder)
    gate = Gate(NoModel(), load_names(folder, library.all_seats))
    print(table(count(Session(library, gate))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
