"""Today's harvest card, ① and ② (SPEC 5-3, 14-1).

① 今日の動き: code counts the student's moves from the record and names each
with one of the school's forces. No model is used. A force names a move,
never the student. At most two are shown; the second must make one of the
allowed pairs with the first, so the two never line up with one Lab's own
set (SPEC 5-3). Only that list of pairs is kept here, not the Labs or their
sets (SPEC 14-1). With no allowed second, one is shown. ⑥ is never shown.

② 会うときに使ってみたい力: offered right after the student picks one seat to
meet. Only the uses the record fits are offered; the student picks one or
none. Nothing marks the forces that came up in ①.

The table is the teacher's (SPEC 14-1: kept as data); its wording may be
changed here.
"""

from dataclasses import dataclass

from . import roundtable
from .seat_label import seat_label
from .texts import WORK_QUESTIONS, load_lines

FORCES = {
    1: "① 自走する力",
    2: "② つなげる力",
    3: "③ 合わせる力",
    4: "④ 向かう力",
    5: "⑤ 解き明かす力",
}
# ④ is only the step before: whether the student went to meet is not measured.
FORCE_IN_MOVES = FORCES | {4: "④ 向かう力の、手前の動き"}
ALLOWED_PAIRS = frozenset(frozenset(pair) for pair in ((1, 3), (1, 4), (2, 4), (3, 5), (4, 5)))
MAX_WORDS = 30  # The record's words in the first move; longer ones end in 「…」.
MOVES_PREFIX = "今日の動き："
MEET_PREFIX = "会いに行きたい1人："
USE_PREFIX = "会うときに："
CHOSE_NO_USE = "none"  # 「選ばない」
MIN_KINDS_MET = 3
MIN_ROUNDS = 4


@dataclass(frozen=True)
class MoveRow:
    """One row of the table: a move the record shows, in priority order."""

    code: str
    force: int
    with_words: str  # For the first move: holds {w}, the record's own words.
    short: str  # For the second move.


# In priority order: the first row the record shows is the first move.
MOVE_TABLE = (
    MoveRow("rewrote", 1, "問いを「{w}」に書き直した", "問いを書き直した"),
    MoveRow("asked_after_silence", 1, "どの席も答えなかったあとも、「{w}」と問いを続けた",
            "どの席も答えなかったあとも、問いを続けた"),
    MoveRow("card_at_silent_seat", 3, "{seat}の席に、質問カード「{w}」を書いた", "{seat}の席に質問カードを書いた"),
    MoveRow("pressed_split", 5, "割れた見出し「{w}」を押して、もう一度聞いた", "割れた見出しを押して、もう一度聞いた"),
    MoveRow("silent_question", 5, "どの席も答えない問い「{w}」を入れた", "どの席も答えない問いを入れた"),
    MoveRow("kinds_met", 2, "{w}と、種類の違う席の言葉を聞いた", "種類の違う席の言葉を、3種類以上聞いた"),
    MoveRow("many_rounds", 1, "「{w}」から、問いを{n}回続けた", "問いを{n}回続けた"),
    MoveRow("own_first_question", 1, "最初の問い「{w}」を自分の言葉で入れた", "最初の問いを自分の言葉で入れた"),
    MoveRow("chose_to_meet", 4, "{w}に会いに行きたいと選んだ", "{w}に会いに行きたいと選んだ"),
)
ROWS = {row.code: row for row in MOVE_TABLE}

# ②: how to act when meeting, in the words of the use; the force name is small.
USES = {
    1: "聞きたいことを、自分で決めて行く",
    2: "今日聞いたほかの席の言葉も、持って行く",
    3: "相手の話に合わせて、聞き方を変える",
    4: "まず、会いたいと伝えてみる",
    5: "割れていた所を、本人に確かめる",
}
ALWAYS_OFFERED = (1, 3, 4)
MIN_KINDS_FOR_CONNECT = 2  # ② only for a student who heard two kinds of seat or more.


@dataclass(frozen=True)
class Found:
    """A move the record shows, with the record's words for it."""

    code: str
    words: str = ""
    seat: str = ""  # A seat's title, for the card move.
    count: int = 0  # Rounds, for the many-rounds move.


def _cut(words: str) -> str:
    return words if len(words) <= MAX_WORDS else words[:MAX_WORDS] + "…"


def _same(a: str, b: str) -> bool:
    return " ".join(a.split()) == " ".join(b.split())


def found_moves(session, sheet_heading) -> list[Found]:
    """Every move of the table the record shows, in priority order."""
    titles = {seat.seat_id: seat_label(seat, session.library.show_private).title
              for seat in session.library.seats}
    kinds = {seat.seat_id: seat.kind for seat in session.library.seats}
    current = session.reflection
    asked = [r for r in session.rounds if r.question]
    found: dict[str, Found] = {}

    if current.rewrite:
        found["rewrote"] = Found("rewrote", current.rewrite)
    for index, result in enumerate(asked):
        if result.status == roundtable.SILENT:
            found.setdefault("silent_question", Found("silent_question", result.question))
            if index + 1 < len(asked):
                found.setdefault("asked_after_silence", Found("asked_after_silence", asked[index + 1].question))
    card = next((c for c in session.cards if c.seat_id), None)
    if card is not None:
        found["card_at_silent_seat"] = Found("card_at_silent_seat", card.text, seat=titles[card.seat_id])
    for number, result in enumerate(session.rounds, start=1):
        # Pressed, then asked again: a later round exists.
        pressed = [i for i in range(len(result.splits)) if (number, i) in session.pressed_splits]
        if pressed and number < len(session.rounds) and "pressed_split" not in found:
            found["pressed_split"] = Found("pressed_split", sheet_heading(result.splits[pressed[0]].heading))
    by_kind: dict[str, str] = {}
    for seat_id in session.met_seats():
        by_kind.setdefault(kinds[seat_id], titles[seat_id])
    if len(by_kind) >= MIN_KINDS_MET:
        found["kinds_met"] = Found("kinds_met", "・".join(list(by_kind.values())[:3]))
    if asked:
        first = asked[0].question
        if len(asked) >= MIN_ROUNDS:
            found["many_rounds"] = Found("many_rounds", first, count=len(asked))
        if not any(_same(first, line) for line in load_lines(WORK_QUESTIONS)):
            found["own_first_question"] = Found("own_first_question", first)
    if current.meet_seat:
        found["chose_to_meet"] = Found("chose_to_meet", titles[current.meet_seat])
    return [found[row.code] for row in MOVE_TABLE if row.code in found]


def pick(found: list[Found]) -> list[Found]:
    """The first move, and a second whose force makes an allowed pair."""
    if not found:
        return []
    first = found[0]
    force = ROWS[first.code].force
    second = next((f for f in found[1:] if frozenset((force, ROWS[f.code].force)) in ALLOWED_PAIRS), None)
    return [first, second] if second else [first]


def _move_text(move: Found, with_words: bool) -> str:
    row = ROWS[move.code]
    template = row.with_words if with_words else row.short
    return template.format(w=_cut(move.words), seat=move.seat, n=move.count)


def moves_line(picked: list[Found]) -> str:
    parts = [f"{_move_text(move, index == 0)}（{FORCE_IN_MOVES[ROWS[move.code].force]}）"
             for index, move in enumerate(picked)]
    return MOVES_PREFIX + "／".join(parts)


def uses_offered(session) -> list[int]:
    """② as the record fits: ② after two kinds of seat, ⑤ after a split."""
    kinds = {seat.seat_id: seat.kind for seat in session.library.seats}
    offered = set(ALWAYS_OFFERED)
    if len({kinds[s] for s in session.met_seats()}) >= MIN_KINDS_FOR_CONNECT:
        offered.add(2)
    if any(r.splits for r in session.rounds):
        offered.add(5)
    return sorted(offered)


def use_view(force: int) -> dict:
    return {"force": str(force), "name": FORCES[force], "text": USES[force]}


def meet_line(title: str, use: int | None) -> str:
    line = MEET_PREFIX + title
    if use is None:
        return line
    return f"{line}　／　{USE_PREFIX}{FORCES[use][0]} {USES[use]}"
