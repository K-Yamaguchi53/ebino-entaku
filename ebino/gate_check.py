"""Try the model gate on the real data, without calling any model.

    python -m ebino.gate_check

Reads the seat table, masks.tsv, gate_ok.tsv and the ingested pieces from
EBINO_DATA_DIR, and looks for names in everything a request can carry: each
seat's model-facing fields and each piece's text and heading.

THIS OUTPUT SHOWS THE WORDS THAT WERE HIT, which may be names. It is for the
teacher's own screen only (SPEC 14-51) and is not to be pasted into chat.
The teacher looks at each word; words that are not names (a family name that
is also a place name) go one per line into EBINO_DATA_DIR/gate_ok.tsv.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .gate import NameList, load_allowed
from .ingest.masks import load_masks
from .ingest.run import OUTPUT_DIR, OUTPUT_FILE
from .ingest.seats import load_seats

WARNING = "*** この出力には名前が出ることがあります。チャットに貼らないでください。 ***"


def run(data_dir: Path) -> tuple[list[str], int]:
    seats = load_seats(data_dir / "seats.tsv")
    masks = load_masks(data_dir / "masks.tsv", {seat.seat_id for seat in seats})
    names = NameList.build(seats, masks, load_allowed(data_dir))
    rows = json.loads((data_dir / OUTPUT_DIR / OUTPUT_FILE).read_text(encoding="utf-8"))

    pieces_by_term: Counter = Counter()
    seats_by_term: dict[str, set[str]] = defaultdict(set)
    hit_pieces = 0
    for row in rows:
        found = names.hits(row.get("text", "") + row.get("heading", ""))
        hit_pieces += bool(found)
        for term in found:
            pieces_by_term[term] += 1
            seats_by_term[term].add(row.get("seat_id", ""))
    for seat in seats:
        for term in names.hits(json.dumps(seat.for_model(), ensure_ascii=False)):
            pieces_by_term[term] += 0
            seats_by_term[term].add(f"{seat.seat_id}(table)")

    by_kind = Counter(names.terms[term] for term in seats_by_term)
    lines = [
        WARNING,
        f"seats: {len(seats)}  pieces: {len(rows)}  names looked for: {len(names.terms)}",
        f"pieces with a hit: {hit_pieces}",
        f"hit words by kind: {dict(by_kind)}",
    ]
    for term in sorted(seats_by_term, key=lambda t: (names.terms[t], t)):
        where = ", ".join(sorted(seats_by_term[term]))
        lines.append(f"  [{names.terms[term]}] {term}  pieces: {pieces_by_term[term]}  seats: {where}")
    lines.append(WARNING)
    return lines, len(seats_by_term)


def main() -> int:
    data_dir = os.environ.get("EBINO_DATA_DIR")
    if not data_dir:
        print("EBINO_DATA_DIR is not set", file=sys.stderr)
        return 2
    try:
        lines, hit_words = run(Path(data_dir))
    except FileNotFoundError:
        print("a table or the ingested pieces are missing: run python -m ebino.ingest.run first",
              file=sys.stderr)
        return 2
    except ValueError as error:  # Table errors give line numbers, never values.
        print(error, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 1 if hit_words else 0


if __name__ == "__main__":
    sys.exit(main())
