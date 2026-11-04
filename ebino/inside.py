"""What the app holds, as counts (直し31-5): shown over the first question
box so a student sees whose words are in it before asking.

The counts are taken from the seat table when the app starts, never written
by hand: the adults by their workplaces (the company column: one per
company, a seat with none counts as its own), the seniors' posters, the
people who went out of the prefecture or abroad, and the adults and
teachers from outside. The people who went out are split into 県外研修 and
海外研修 when the table's 「越境の線の先」 says 県外 or 海外 for them; with
those empty, one count. A kind with none is left out. Only numbers leave
here: no company, no display name.
"""

from .ingest.seats import Seat
from .texts import INSIDE_COUNTS, load_table

KENGAI, KAIGAI = "県外", "海外"
NUMBER = "{数}"
ROW_IDS = ("adult", "poster", "cross", "cross_kengai", "cross_kaigai", "outsider_teacher")


def counts(seats: list[Seat]) -> list[tuple[str, str, int]]:
    """(row ID, the seat kind its mark is, number) in the screen's order;
    rows of 0 are left out."""
    adult = len({seat.company or f"seat:{seat.seat_id}" for seat in seats if seat.kind == "adult"})
    poster = sum(1 for seat in seats if seat.kind == "poster")
    cross = [seat for seat in seats if seat.kind == "cross"]
    kaigai = sum(1 for seat in cross if KAIGAI in seat.crossing_to)
    kengai = sum(1 for seat in cross if KENGAI in seat.crossing_to and KAIGAI not in seat.crossing_to)
    outsider = sum(1 for seat in seats if seat.kind == "outsider_teacher")
    rows = [("adult", "adult", adult), ("poster", "poster", poster)]
    if kengai or kaigai:
        rows += [("cross_kengai", "cross", kengai), ("cross_kaigai", "cross", kaigai),
                 ("cross", "cross", len(cross) - kengai - kaigai)]
    else:
        rows.append(("cross", "cross", len(cross)))
    rows.append(("outsider_teacher", "outsider_teacher", outsider))
    return [row for row in rows if row[2] > 0]


def ways() -> dict[str, str]:
    """texts/inside_counts.tsv: each row's words, {数} where the number goes."""
    rows = {row["ID"]: row["言い方"] for row in load_table(INSIDE_COUNTS, ("ID", "言い方"))}
    if set(rows) != set(ROW_IDS) or any(rows[key].count(NUMBER) != 1 for key in ROW_IDS):
        raise ValueError(f"{INSIDE_COUNTS}.tsv must have the rows {', '.join(ROW_IDS)}, each with one {NUMBER}")
    return rows


def view(seats: list[Seat]) -> list[dict]:
    """For the screen: each row's mark (a seat kind), the words before the
    number, the number, and the words after it."""
    words = ways()
    out = []
    for row_id, kind, number in counts(seats):
        before, after = words[row_id].split(NUMBER)
        out.append({"id": row_id, "kind": kind, "before": before.strip(), "number": number, "after": after.strip()})
    return out
