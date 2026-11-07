"""直し54d (the teacher, 11/8: 質問と回答を全員分作っておく): every seat's
questions at one to one and the words each one shows, in one list for the
teacher to read before filming, written next to the ingest's output in the
data folder (never in the repo):

    .venv\\Scripts\\python tools\\list_one_answers.py

  1対1_質問と出る言葉_全員分.csv (UTF-8, Excel opens it): 席ID・札・項目・
  質問・出る言葉・言葉の種類・どこから・状態. The words are those the screen
  shows (tidied, cut, a page with a name left out), before the speaker turns
  them into spoken words; the question is the teacher's, before the asker
  puts it to the person. No model is asked.

A question whose words do not answer it: copy its 席ID and 項目 into
ask_hide.tsv beside it (written with its header when it is not there, never
over the teacher's) and start the app again: that question is not offered.
On the console: counts and the files' names only.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebino import config, one_to_one  # noqa: E402
from ebino.gate import Gate, load_names  # noqa: E402
from ebino.seat_label import seat_label  # noqa: E402

LIST_FILE = "1対1_質問と出る言葉_全員分.csv"
COLUMNS = ("席ID", "札", "項目", "質問", "出る言葉（画面ではこれを話し言葉にして出す）", "言葉の種類", "どこから", "状態")
STOPPED = "出さない（ask_hide.tsv）"
NOTHING = "出る言葉がない"


class NoModel:
    @property
    def messages(self):
        raise RuntimeError("list_one_answers asks no model")


def rows(session) -> list[list[str]]:
    """Each seat on the map, each of its questions (those stopped too, said so)."""
    tables = session.library.ask_tables
    hidden, teacher = tables.get("hidden", set()), tables.get("teacher_pages", set())
    tables["hidden"] = set()  # Listed all the same, its 状態 says it is stopped.
    try:
        out = []
        for seat in session.library.seats:
            label = seat_label(seat, False)  # As filmed: no company's name.
            for item, question, pieces in session.one_items(seat.seat_id):
                shown, said, _, _ = session.one_shown(pieces)
                kinds = dict.fromkeys(k for k in (session.kind_label(u.id) for u in shown) if k)
                where = dict.fromkeys(
                    u.section + ("（先生）" if (seat.seat_id, u.section) in teacher else "") for u in shown)
                state = STOPPED if (seat.seat_id, item) in hidden else ("" if said else NOTHING)
                out.append([seat.seat_id, f"{label.title} {label.detail}".strip(), item, question,
                            "\n".join(said), "・".join(kinds), "・".join(where), state])
        return out
    finally:
        tables["hidden"] = hidden


def write(folder: Path, listed: list[list[str]]) -> bool:
    """Writes the list (over the last one: it is made again each time) and
    ask_hide.tsv's header when it is not there. True when the header was written."""
    with (folder / LIST_FILE).open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(COLUMNS)
        writer.writerows(listed)
    hide = folder / one_to_one.HIDE_FILE
    if hide.exists():
        return False
    hide.write_text("\t".join(one_to_one.HIDE_COLUMNS) + "\n", encoding="utf-8")
    return True


def main() -> int:
    from ebino.session import INGESTED_DIR, Library, Session
    config.load_env_file()
    try:
        folder = config.data_dir()
    except config.PlaceError as error:
        print(f"list_one_answers: {error}", file=sys.stderr)
        return 2
    library = Library.load(folder)
    session = Session(library, Gate(NoModel(), load_names(folder, library.all_seats)))
    listed = rows(session)
    made = write(folder / INGESTED_DIR, listed)
    seats = len({row[0] for row in listed})
    print(f"席 {seats}・質問 {len(listed)}（出さない {sum(row[7] == STOPPED for row in listed)}・"
          f"出る言葉がない {sum(row[7] == NOTHING for row in listed)}）")
    print(f"書いた：データの {INGESTED_DIR} フォルダの {LIST_FILE}")
    print(f"止める表：同じフォルダの {one_to_one.HIDE_FILE}" + ("（見出しだけ作った）" if made else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
