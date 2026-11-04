"""The librarian: looks through the index with tools for pieces that fit a
student's question (SPEC 6, 14-52).

The tool loop is written here rather than left to the SDK's tool runner, so
every request, the tool results included, goes through the one gate
(SPEC 14-52). The loop has a cap on requests; at the cap, the pieces found so
far go on to the moderator.

Searching by words is not an exact match (SPEC 14-52): a word hits a piece
when the word is inside one of its topics, a topic is inside the word, or the
word is inside the piece's text. No hand-written topic list evens the topics
out (SPEC 6).
"""

import json
import time
from collections import Counter
from dataclasses import dataclass, field

from .gate import Gate, ModelUnavailable, block_dict, json_answer, json_request
from .index import Entry
from .ingest.scrub import normalize_for_match
from .prompts import LIBRARIAN

MAX_REQUESTS = 6
# The wait for the model, with no retry (直し31-1): each request at most
# TIMEOUT_SECONDS, and one search's requests together at most TOTAL_SECONDS.
# Past either the search is unavailable, as when the model cannot be used.
TIMEOUT_SECONDS = 30.0
TOTAL_SECONDS = 45.0
MAX_PICKED = 24
SEARCH_LIMIT = 20
READ_LIMIT = 40

ENDED_ANSWERED = "answered"
ENDED_REQUEST_LIMIT = "request_limit"


def _tool(name: str, description: str, properties: dict) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


_KIND = {"type": "string", "description": "席の種類で絞る（adult・poster・cross・outsider_teacher）。絞らないときは空の文字列。"}
_DISTRICT = {"type": "string", "description": "地区で絞る。絞らないときは空の文字列。"}
TOOLS = [
    _tool(
        "search",
        "言葉で片を探す。話題の札に言葉の一部が合うか、片の本文に言葉が入っていれば当たる。当たった数の多い順に返す。",
        {
            "words": {"type": "array", "items": {"type": "string"}, "description": "探す言葉（1つ以上）"},
            "kind": _KIND,
            "district": _DISTRICT,
        },
    ),
    _tool("list_seats", "席の一覧（席ID・種類・肩書き・地区・片の数）を返す。", {"kind": _KIND, "district": _DISTRICT}),
    _tool("read_seat", "1つの席の片を、取り込んだ順に返す。", {"seat_id": {"type": "string"}}),
]

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"utterance_ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["utterance_ids"],
    "additionalProperties": False,
}


@dataclass
class Found:
    utterance_ids: list[str]
    ended: str
    requests: int = 0
    tool_calls: Counter = field(default_factory=Counter)


def word_hits(entry: Entry, word: str) -> int:
    """2 when the word meets a topic (either inside the other), 1 when it is
    only in the text, 0 when it misses (SPEC 14-52)."""
    word = normalize_for_match(word)
    if not word:
        return 0
    for topic in entry.topics:
        topic = normalize_for_match(topic)
        if topic and (word in topic or topic in word):
            return 2
    return 1 if word in normalize_for_match(entry.text) else 0


class Shelf:
    """The tools, run by code over the index."""

    def __init__(self, entries: list[Entry]):
        self.entries = entries
        self.by_id = {entry.utterance_id: entry for entry in entries}
        self.seen: list[str] = []

    def _show(self, entries: list[Entry]) -> list[dict]:
        for entry in entries:
            if entry.utterance_id not in self.seen:
                self.seen.append(entry.utterance_id)
        return [entry.for_model() for entry in entries]

    @staticmethod
    def _keep(entry: Entry, kind: str, district: str) -> bool:
        return (not kind or entry.kind == kind) and (not district or entry.district == district)

    def search(self, words: list[str], kind: str = "", district: str = "") -> dict:
        scored = []
        for entry in self.entries:
            if not self._keep(entry, kind, district):
                continue
            score = sum(word_hits(entry, word) for word in words)
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda pair: -pair[0])  # Stable: index order within a score.
        return {"hits": len(scored), "pieces": self._show([entry for _, entry in scored[:SEARCH_LIMIT]])}

    def list_seats(self, kind: str = "", district: str = "") -> dict:
        seats: dict[str, dict] = {}
        for entry in self.entries:
            if self._keep(entry, kind, district):
                seat = seats.setdefault(entry.seat_id, {
                    "seat_id": entry.seat_id, "kind": entry.kind, "title": entry.title,
                    "district": entry.district, "pieces": 0,
                })
                seat["pieces"] += 1
        return {"seats": list(seats.values())}

    def read_seat(self, seat_id: str) -> dict:
        pieces = [entry for entry in self.entries if entry.seat_id == seat_id]
        return {"pieces_in_seat": len(pieces), "pieces": self._show(pieces[:READ_LIMIT])}

    def run(self, name: str, args: dict) -> tuple[dict, bool]:
        """(result, is_error). Bad calls get an error result, never an exception."""
        try:
            if name == "search":
                words = [w for w in args["words"] if isinstance(w, str)]
                return self.search(words, args.get("kind", ""), args.get("district", "")), False
            if name == "list_seats":
                return self.list_seats(args.get("kind", ""), args.get("district", "")), False
            if name == "read_seat":
                return self.read_seat(str(args["seat_id"])), False
        except (KeyError, TypeError, AttributeError):
            return {"error": "bad_arguments"}, True
        return {"error": "unknown_tool"}, True


def _picked(ids, shelf: Shelf) -> list[str]:
    kept: list[str] = []
    for utterance_id in ids if isinstance(ids, list) else []:
        if utterance_id in shelf.by_id and utterance_id not in kept:
            kept.append(utterance_id)
    return kept[:MAX_PICKED]


def find(gate: Gate, entries: list[Entry], question: str, ai_question: str = "") -> Found:
    """Raises GateError or ModelUnavailable (reason codes only); the caller
    shows the fixed sentence (SPEC 14-51). With ai_question, the question is
    the student's answer to that AI question (coach.py)."""
    shelf = Shelf(entries)
    content = (f"AIの問い：{ai_question}\n生徒の答え：{question}" if ai_question
               else f"生徒の問い：{question}")
    request = json_request("librarian", LIBRARIAN, content, ANSWER_SCHEMA)
    request["tools"] = TOOLS
    messages = request["messages"]
    found = Found([], ENDED_REQUEST_LIMIT)
    began = time.monotonic()
    for _ in range(MAX_REQUESTS):
        left = TOTAL_SECONDS - (time.monotonic() - began)
        if left <= 0:
            raise ModelUnavailable("timeout")
        response = gate.send("librarian", request, timeout=min(TIMEOUT_SECONDS, left))
        found.requests += 1
        calls = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        if not calls:
            answer = json_answer(response)
            if not isinstance(answer, dict):
                raise ModelUnavailable("bad_output")
            found.utterance_ids = _picked(answer.get("utterance_ids"), shelf)
            found.ended = ENDED_ANSWERED
            return found
        messages.append({"role": "assistant", "content": [block_dict(b) for b in response.content]})
        results = []
        for call in calls:
            found.tool_calls[call.name] += 1
            result, is_error = shelf.run(call.name, call.input if isinstance(call.input, dict) else {})
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
                **({"is_error": True} if is_error else {}),
            })
        messages.append({"role": "user", "content": results})
    # At the cap: hand on what the tools showed so far (SPEC 14-52).
    found.utterance_ids = shelf.seen[:MAX_PICKED]
    return found
