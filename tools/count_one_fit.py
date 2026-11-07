"""直し54: what one to one offers once each question shows only words that
may answer it (one_to_one.ITEM_KINDS), in counts only, for the teacher to
run on the real data before filming.

    .venv\\Scripts\\python tools\\count_one_fit.py

For each group of questions (記事・外から来た・県外・海外・ポスター): the
items offered before and after, and the seats left with no question at all.
Then each item that is no longer offered, as 席ID・項目 (an ID, never a
name). It never prints words, a name or a path, never writes a file, and
never asks the model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebino import config, one_to_one  # noqa: E402
from ebino.gate import Gate, load_names  # noqa: E402


class NoModel:
    @property
    def messages(self):
        raise RuntimeError("count_one_fit asks no model")


def _group(seat, pieces) -> str:
    if pieces and all(one_to_one.is_page(u.section) for u in pieces):
        return one_to_one.GROUP_OUTSIDER if seat.kind == "outsider_teacher" else one_to_one.GROUP_CROSS
    return one_to_one.GROUP_POSTER if seat.kind == "poster" else one_to_one.GROUP_ARTICLE


def count(session) -> tuple[dict, list[tuple[str, str]]]:
    seats = {seat.seat_id: seat for seat in session.library.all_seats}
    fit = one_to_one.fit_kinds
    groups: dict[str, dict] = {}
    gone: list[tuple[str, str]] = []
    for seat_id, seat in seats.items():
        pieces = [u for u in session.library.utterances if u.seat_id == seat_id]
        if not pieces:
            continue
        one_to_one.fit_kinds = lambda group, item, found, kind_of: list(found)
        try:
            before = [item for item, _, _ in session.one_items(seat_id)]
        finally:
            one_to_one.fit_kinds = fit
        after = [item for item, _, _ in session.one_items(seat_id)]
        g = groups.setdefault(_group(seat, pieces), {"席": 0, "前": 0, "後": 0, "質問が0になる席": 0})
        g["席"] += 1
        g["前"] += len(before)
        g["後"] += len(after)
        if before and not after:
            g["質問が0になる席"] += 1
        gone += [(seat_id, item) for item in before if item not in after]
    return groups, gone


def main() -> int:
    from ebino.session import Library, Session
    config.load_env_file()
    try:
        folder = config.data_dir()
    except config.PlaceError as error:
        print(f"count_one_fit: {error}", file=sys.stderr)
        return 2
    library = Library.load(folder)
    session = Session(library, Gate(NoModel(), load_names(folder, library.all_seats)))
    groups, gone = count(session)
    print("種類\t席\t質問（前）\t質問（後）\t質問が0になる席")
    for name, g in groups.items():
        print(f"{name}\t{g['席']}\t{g['前']}\t{g['後']}\t{g['質問が0になる席']}")
    print()
    print("出なくなる質問（席ID・項目）")
    for seat_id, item in gone:
        print(f"{seat_id}\t{item}")
    print()
    print("先生の行（ask_pages.tsv）が画面に出るか（席ID・ページ・軸）")
    for line in teacher_rows(session):
        print(line)
    for problem in session.library.ask_tables.get("teacher_problems", []):
        print(f"書いたとおりに効かない：{problem}")
    return 0


def teacher_rows(session) -> list[str]:
    """直し54c: each page the teacher gave axes, and whether one to one shows
    it (a page whose words tidied leave nothing, or hold a name, is never
    shown: one_tidy.py). A row naming no seat the pieces have is left to the
    start's check (its cell may hold a name)."""
    from ebino import one_tidy
    tables = session.library.ask_tables
    seats = {seat.seat_id for seat in session.library.all_seats}
    out = []
    for seat_id, page in sorted(tables.get("teacher_pages", ())):
        axes = tables["pages"].get(seat_id, {}).get(page)
        if seat_id not in seats or not axes:
            continue  # 「-」, no axis read, or no such seat: the start's check says which.
        pieces = [u for u in session.library.utterances if u.seat_id == seat_id and u.section == page]
        tidied = [session.one_page(u) for u in pieces]
        if any(t.text for t in tidied):
            state = "出る"
        elif any(one_tidy.NAME in t.reasons for t in tidied):
            state = "出ない（名前が含まれるページ）"
        else:
            state = "出ない（整えると文が残らないページ）" if pieces else "出ない（このページがない）"
        out.append(f"{seat_id}\t{page}\t{'・'.join(axes)}\t{state}")
    return out


if __name__ == "__main__":
    sys.exit(main())
