"""The one gate every model request passes through (SPEC 14-3, 14-39, 14-51).

Two layers keep people's names away from the models:
  1. Code never puts the seat table's company or display-name columns into a
     request (Seat.for_model has neither; tests check every role with a fake
     client).
  2. Right before sending, the gate reads the whole request (system, messages,
     tool definitions and tool results) and stops it if a name is in it. Names
     are the family names from the display-name column (without さん) and the
     「語」 rows of masks.tsv. Words under two characters and label words such
     as 先輩 are not used. Company names are not used either: other seats'
     words can name a company, kindergarten or school as the place they worked,
     and that is part of what they said; each seat's own company was masked at
     ingest. Where a person checked a hit and found it is not a name (a
     family name inside a place name), they write the string around it, one
     per line, in EBINO_DATA_DIR/gate_ok.tsv. The gate takes those strings out
     of the request first and then looks for names, so 〈山川公園〉 passes
     while 〈山川〉 elsewhere is still stopped (SPEC 14-52). A line that is
     just the name lets that name through everywhere. Without the file
     nothing is let through.

Failures never carry request text: GateError and ModelUnavailable hold reason
codes only. No fallback model answers in place of the one named for a role
(SPEC 14-51): the screen shows a fixed sentence instead.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .ingest.masks import SeatMasks, load_masks
from .ingest.scrub import display_name_terms, normalize_for_match
from .ingest.seats import Seat

GATE_OK_FILE = "gate_ok.tsv"
MIN_NAME_CHARS = 2
# Label words in the display-name column that are not names (SPEC 14-39).
LABEL_WORDS = frozenset(
    normalize_for_match(word) for word in ("先輩", "卒業生", "1年生", "2年生", "3年生")
)
KIND_DISPLAY_NAME = "display_name"
KIND_MASK_WORD = "mask_word"

# One model per role (SPEC 6, the plan taken in 14-51).
MODELS = {
    "tagger": "claude-haiku-5-5",
    "librarian": "claude-sonnet-5-5",
    # Lowered from Opus with effort high so the round table comes in about
    # ten seconds (直し31-6; the teacher allowed the model or effort lowered).
    "moderator": "claude-sonnet-5-5",
    "reflection": "claude-opus-5-5",
    "editor": "claude-sonnet-5-5",
    # The harvest card's ③: sorts the record into one 札 and two numbers.
    "subjects": "claude-haiku-5-5",
    # コーチとオブザーバー: two questions to the student at a round's end.
    "coach": "claude-opus-5-5",
}
EFFORT = {
    "tagger": "low",
    "librarian": "medium",
    "moderator": "medium",
    # Lowered from high so the student is not kept waiting (直し31-1).
    "reflection": "medium",
    "editor": "low",
    "subjects": "low",
    "coach": "medium",
}


class GateError(Exception):
    """A request was stopped before sending. Reason code only."""


class ModelUnavailable(Exception):
    """The model did not give a usable answer. Reason code only."""


@dataclass(frozen=True)
class NameList:
    """Normalized names to look for, each with where it came from, and the
    strings a person let through."""

    terms: dict[str, str] = field(default_factory=dict)  # term -> KIND_*
    allowed: tuple[str, ...] = ()  # Normalized, longest first.

    @classmethod
    def build(cls, seats: list[Seat], masks: dict[str, SeatMasks], allowed: set[str] = frozenset()):
        terms: dict[str, str] = {}

        def add(word: str, kind: str) -> None:
            term = normalize_for_match(word)
            if len(term) < MIN_NAME_CHARS or term in LABEL_WORDS:
                return
            terms.setdefault(term, kind)

        for seat in seats:
            for word in display_name_terms(seat.display_name):
                add(word, KIND_DISPLAY_NAME)
        for seat_masks in masks.values():
            for word in seat_masks.words:
                add(word, KIND_MASK_WORD)
        kept = {normalize_for_match(line) for line in allowed} - {""}
        return cls(terms, tuple(sorted(kept, key=lambda s: (-len(s), s))))

    def hits(self, text: str) -> list[str]:
        body = normalize_for_match(text)
        for string in self.allowed:
            # A mark no name holds, so the text on each side cannot join up.
            body = body.replace(string, "\0")
        return [term for term in self.terms if term in body]


def load_names(data_dir: Path, seats: list[Seat]) -> NameList:
    """The name list for the real data: seats, masks.tsv and gate_ok.tsv."""
    masks = load_masks(data_dir / "masks.tsv", {seat.seat_id for seat in seats})
    return NameList.build(seats, masks, load_allowed(data_dir))


def load_allowed(data_dir: Path) -> set[str]:
    """Strings a person let through, one per line. No file: nothing is."""
    path = data_dir / GATE_OK_FILE
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    return {line.strip() for line in lines if line.strip()}


def request_text(request: dict) -> str:
    """Everything a request would send, as one string."""
    return json.dumps(request, ensure_ascii=False, default=_plain)


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return vars(value)
    return str(value)


def block_dict(block: Any) -> dict:
    """An SDK content block as a plain dict, to send back unchanged."""
    if isinstance(block, dict):
        return block
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_none=True)
    return {key: value for key, value in vars(block).items() if value is not None}


@dataclass
class Gate:
    client: Any  # anthropic.Anthropic, or a fake one in tests.
    names: NameList
    # Called with (role, request) after the check passes; the records hook.
    on_send: Callable[[str, dict], None] | None = None
    sent: int = 0
    stopped: int = 0

    def send(self, role: str, request: dict, timeout: float | None = None):
        """timeout: seconds to wait for this request, with no retry; None
        keeps the SDK's defaults. Past it the model counts as not usable."""
        if self.names.hits(request_text(request)):
            self.stopped += 1
            raise GateError("name_in_request")
        if self.on_send:
            self.on_send(role, request)
        self.sent += 1
        client = self.client if timeout is None else self.client.with_options(timeout=timeout, max_retries=0)
        try:
            response = client.messages.create(**request)
        except Exception as error:  # SDK messages can echo the request.
            raise ModelUnavailable(f"api_error:{type(error).__name__}") from None
        if response.stop_reason == "refusal":
            raise ModelUnavailable("refusal")
        if response.stop_reason == "max_tokens":
            raise ModelUnavailable("max_tokens")
        return response


def json_request(
    role: str, system: str, content: Any, schema: dict, max_tokens: int = 16000
) -> dict:
    """A request whose answer is JSON in the given schema (structured output).

    The system text is fixed per role and comes first with a cache mark, so
    repeated questions reuse it."""
    return {
        "model": MODELS[role],
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": content}],
        "output_config": {
            "effort": EFFORT[role],
            "format": {"type": "json_schema", "schema": schema},
        },
    }


def json_answer(response) -> Any:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except ValueError:
                raise ModelUnavailable("bad_output") from None
    raise ModelUnavailable("bad_output")
