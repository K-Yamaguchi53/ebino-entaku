"""The records of each sitting (SPEC 2-1, 6, 14-51).

Everything is written under EBINO_RECORDS_DIR, which config.check_records_dir
has already checked is outside this repository and outside synced folders.

  sessions/<id>.json   one sitting, rewritten after every step, so a closed
                       window loses nothing. The ID is random; there is no
                       name, class or seat number, and no clock time: the
                       date and the seconds used only.
  prompts/<id>/        what was really sent to the moderator, the
                       instruction part (system and output form) and the
                       data part (question and pieces) in separate files,
                       so each can be searched on its own (SPEC 6).

    python -m ebino.records

prints counts from the records only (sittings, questions, how many no seat
answered), never what anyone wrote.
"""

import datetime
import json
import os
import sys
from collections import Counter
from pathlib import Path

from .config import PlaceError, load_env_file, records_dir

SESSIONS_DIR = "sessions"
PROMPTS_DIR = "prompts"
LOGGED_ROLES = ("moderator", "reflection")


def _write(path: Path, text: str) -> None:
    """Write whole or not at all: a half-written record is never left."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class Records:
    def __init__(self, folder: Path):
        self.folder = folder
        self._sent: Counter = Counter()

    def save_session(self, record: dict) -> Path:
        path = self.folder / SESSIONS_DIR / f"{record['session_id']}.json"
        _write(path, json.dumps(record, ensure_ascii=False, indent=1))
        return path

    def save_prompt(self, session_id: str, role: str, request: dict) -> None:
        if role not in LOGGED_ROLES:
            return
        self._sent[session_id] += 1
        stem = self.folder / PROMPTS_DIR / session_id / f"{self._sent[session_id]:02}-{role}"
        system = "\n\n".join(block.get("text", "") for block in request.get("system", []))
        form = request.get("output_config", {}).get("format", {})
        instruction = f"{system}\n\n--- output form ---\n{json.dumps(form, ensure_ascii=False, indent=1)}\n"
        data = [message.get("content") for message in request.get("messages", [])]
        _write(stem.with_name(stem.name + "-instruction.txt"), instruction)
        _write(stem.with_name(stem.name + "-data.json"), json.dumps(data, ensure_ascii=False, indent=1))


def session_record(session) -> dict:
    """One sitting as kept. Utterance and seat IDs, the student's own words,
    split headings and the guard's counts; never a seat's company or name."""
    rounds = []
    for number, result in enumerate(session.rounds, start=1):
        rounds.append({
            "round": number,
            "question": result.question,  # "" when it held a name.
            "status": result.status,
            "reason": result.reason,
            "librarian_found": len(result.candidates),
            "librarian_ended": result.librarian_ended,
            "seats_lit": result.seat_order,
            "quotes_shown": [quote.utterance_id for quote in result.quotes],
            "guard_passed": result.guard_passed,
            "guard_stopped": result.guard_stopped,
            "guard_stopped_seats": result.guard_stopped_seats,
            "planted_stopped": len(result.planted_stopped),
            "planted_passed": result.planted_passed,
            "splits": [
                {"heading": split.heading, "side_a": list(split.side_a), "side_b": list(split.side_b),
                 "pressed": (number, index) in session.pressed_splits}
                for index, split in enumerate(result.splits)
            ],
            "splits_dropped": result.splits_dropped,
            "silent_seats": result.silent_seats,
            "card_id": result.card.card_id if result.card else "",
        })
    return {
        "session_id": session.session_id,
        "date": session.date,
        "seconds_used": session.seconds_used(),
        "lab": session.lab,
        "rounds": rounds,
        "marked_quotes": dict(session.marks),
        "met_seats": session.met_seats(),
        "cards": [
            card.front() | {"back": {"ask_seat_ids": list(card.back.ask_seat_ids),
                                     "rephrase": card.back.rephrase, "reason": card.back.reason}}
            for card in session.cards
        ],
    }


def today() -> str:
    return datetime.date.today().isoformat()


# --- counts from the records (SPEC 2-1: counted by code, never by hand) ---

def load_sessions(folder: Path) -> list[dict]:
    paths = sorted((folder / SESSIONS_DIR).glob("*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def summary(sessions: list[dict]) -> list[str]:
    rounds = [r for s in sessions for r in s.get("rounds", [])]
    status = Counter(r["status"] for r in rounds)
    asked = status["answered"] + status["silent"]
    rate = f"{status['silent'] / asked:.0%}" if asked else "-"
    return [
        f"sittings: {len(sessions)}",
        f"questions: {len(rounds)}  by status: {dict(status)}",
        f"no seat answered: {status['silent']} of {asked} answered or silent ({rate})",
        f"guard passed / stopped: {sum(r['guard_passed'] for r in rounds)} / "
        f"{sum(r['guard_stopped'] for r in rounds)}",
        f"cards: {sum(len(s.get('cards', [])) for s in sessions)}",
    ]


def main() -> int:
    load_env_file()
    try:
        folder = records_dir()
    except PlaceError as error:
        print(error, file=sys.stderr)
        return 2
    print("\n".join(summary(load_sessions(folder))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
