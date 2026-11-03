"""「もっと聞く」 under a round's last word (SPEC 14-53, the teacher's call on
11/3).

Each press shows the next piece of the same seat and the same section, in
reading order, as it was recorded, passing over every piece this student has
already been shown (a piece quoted in the round is never shown again here):
no model is used, and the source is shown
by the piece's voice. One piece can be pressed from at most twice, the
second press going on from the piece the first one showed. When the section
has no next piece, the screen says 「ここから先は、まだ聞いていない」, and a press
on it makes a question card to that seat (SPEC 2-2), holding the round's
question.

Presses are recorded with the pieces' IDs; they are not counted among the
harvest card's moves (the teacher decides whether they should be).
"""

from dataclasses import dataclass, field

from .ingest.utterance import Utterance

MAX_PRESSES = 2


@dataclass
class More:
    origin_id: str  # The piece the button was under.
    round_no: int
    seat_id: str
    presses: int = 0
    shown: list[str] = field(default_factory=list)  # Piece IDs, in the order shown.
    ended: bool = False  # The section ran out.
    card_id: str = ""  # The card made from 「まだ聞いていない」.

    @property
    def can_press(self) -> bool:
        return not self.ended and self.presses < MAX_PRESSES


def next_after(utterances: list[Utterance], piece_id: str, skip=frozenset()) -> Utterance | None:
    """The next piece of the same seat and section, in reading order, passing
    over the pieces in skip."""
    position = next((i for i, u in enumerate(utterances) if u.id == piece_id), None)
    if position is None:
        return None
    piece = utterances[position]
    return next((u for u in utterances[position + 1:]
                 if u.seat_id == piece.seat_id and u.section == piece.section and u.id not in skip), None)


def press(state: More, utterances: list[Utterance], seen=frozenset()) -> Utterance | None:
    """One press: the next piece this student has not been shown (seen: the
    round's quotes, last words, pieces heard here and the seats' answers), or
    None when the section has ended."""
    piece = next_after(utterances, state.shown[-1] if state.shown else state.origin_id, seen)
    state.presses += 1
    if piece is None:
        state.ended = True
    else:
        state.shown.append(piece.id)
    return piece
