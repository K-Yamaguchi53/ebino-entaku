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
    return 0


if __name__ == "__main__":
    sys.exit(main())
