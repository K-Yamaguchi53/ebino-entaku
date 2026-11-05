"""One student's sitting at the round table, and what the screen is sent
(SPEC 5-1, 14-12, 14-51, 14-65: the map over the seat list, which stays).

The screen gets plain data built here, never a model's words except the
quotes the guard passed (which are the pieces' own text), split headings,
and since 直し31-7 the quotes as spoken words that code checked
(speaker.py), each beside its original.
Seat labels come from the seat table through seat_label, so company and
display name reach the screen only when EBINO_SHOW_COMPANY=1 and never reach
a model. The year is never sent (SPEC 14-34).

One sitting at a time: there is no login and no second student at once
(SPEC 3). Starting again makes a new sitting with a new random ID.
"""

import re
import secrets
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import (ask_seat, closing, coach, config, editor, harvest, more, purpose_summary, reflection, relief,
               roundtable, speaker,
               seat_map, subjects, talk_kinds)
from .editor import QuestionCard
from .reflection import CHANGED_CHOICES, CHOSE_NONE, CHOSE_OWN, DIRECTION_LABELS, MAX_LINE_CHARS, Reflection
from .texts import (ASK_ANSWER_SAID, ASK_ANSWER_WRITTEN, ASK_NOT_ANSWERED, ASK_SEAT_HEADER, CLOSING_KIND_LABELS,
                    CLOSING_QUESTION, MODEL_UNAVAILABLE, NAME_IN_QUESTION, SCHOOL_LABEL, load_optional_text, load_table,
                    load_text)
from . import librarian, texts
from .gate import Gate, GateError, ModelUnavailable, NameList, load_names
from .guard import Guard
from . import asker, hitokoto, one_tidy, one_to_one
from .index import Entry, build_index, load_topics, load_utterances
from .ingest.run import OUTPUT_DIR as INGESTED_DIR
from .ingest.scrub import normalize_for_match
from .ingest.seats import Seat, load_seats
from .ingest.utterance import Utterance
from .purpose import PurposeSample, PurposeShelf, samples
from .records import Records, session_record, today
from .seat_label import KIND_LABELS, seat_label

MAX_QUESTION_CHARS = 200
MAX_CARD_CHARS = 200
# Between two different notes on one 「もっと聞く」 passage's source line.
PASSAGE_NOTE_JOIN = "・"
# The one question asked first (SPEC 2-1, 14-20). The keys are what is kept.
LAB_CHOICES = {
    "quest": "Quest",
    "action": "Action",
    "creation": "Creation（生活文化科）",
    "not_said": "言わない",
}


class Refused(Exception):
    """A screen request that cannot be done. Reason code only."""


# The moderator's headings begin 「ここで割れた：」 (prompts.MODERATOR). The
# round table keeps it; the sheet already says 割れたところ and 置いてきた：.
_SPLIT_LEAD = re.compile(r"^\s*ここで割れた\s*[：:]\s*")


def _sheet_heading(heading: str) -> str:
    return _SPLIT_LEAD.sub("", heading) or heading


def _line(text, limit: int, empty_code: str, required: bool = True) -> str:
    """One line the student wrote, trimmed and capped."""
    text = " ".join((text if isinstance(text, str) else "").split())
    if required and not text:
        raise Refused(empty_code)
    if len(text) > limit:
        raise Refused("too_long")
    return text


@dataclass
class Library:
    """What every sitting reads: loaded once when the app starts."""

    seats: list[Seat]
    utterances: list[Utterance]
    entries: list[Entry]
    purposes: list[PurposeSample]
    show_private: bool = False
    # Each seat's pieces that may give the round's last word, by kind of
    # talk (SPEC 14-53 A), and the kinds in the teacher's table order.
    closing_pieces: dict[str, dict[str, list[Entry]]] = field(default_factory=dict)
    kind_order: list[str] = field(default_factory=list)
    # A ranking item's title (the nearest title piece before it in the same
    # seat and section), shown small over the item; never counted as shown.
    ranking_titles: dict[str, str] = field(default_factory=dict)
    # The harvest card's ③ (subjects.py). None: ③ is not shown.
    subject_catalog: subjects.Catalog | None = None
    # Every seat of the table, those kept off the map too: the name list is
    # built from these. `seats` above holds the seats on the map only.
    all_seats: list[Seat] = field(default_factory=list)
    # コーチとオブザーバー (coach.py): the coach's source pieces (the seats in
    # coach.tsv; empty: no coach card), and whether the band is on at all.
    coach_sources: list[str] = field(default_factory=list)
    coach_on: bool = True
    # The map (seat_map.py): None when the map file is missing or unreadable,
    # and the screen keeps the seat list alone. The points are for `seats`.
    map_data: seat_map.MapData | None = None
    placement: seat_map.Placement | None = None
    # The basin drawn as a model under the map (relief.py): None keeps the
    # flat map. The points stay where seat_map.py put them.
    relief: dict | None = None
    # One to one's tables the teacher keeps (直し34-2): which axes a page
    # answers, and a seat's own question on its ranking.
    ask_tables: dict = field(default_factory=lambda: {"pages": {}, "ranking": {}})

    @classmethod
    def build(cls, seats, utterances, topics, show_private=False, saved_kinds=None,
              saved_summaries=None, names=None, subject_catalog=None, coach_seats=None,
              coach_on=None, map_data=None, relief_data=None) -> "Library":
        """coach_seats: coach.tsv as {seat ID: shown on the map}. A seat kept
        off the map is left out of the seat list and of everything the
        librarian and the moderator can pick; its pieces are the coach's only."""
        coach_seats = coach_seats or {}
        hidden = {seat_id for seat_id, shown in coach_seats.items() if not shown}
        every_entry = build_index(utterances, seats, topics)
        entries = [entry for entry in every_entry if entry.seat_id not in hidden]
        shown_seats = [seat for seat in seats if seat.seat_id not in hidden]
        shown_utterances = [u for u in utterances if u.seat_id not in hidden]
        kinds = talk_kinds.load_kinds()
        kind_of = {u.id: talk_kinds.kind_of(saved_kinds or {}, u.id, kinds) for u in utterances}
        # A long sample shows only as its saved summary, checked again here.
        purposes = purpose_summary.shown_samples(samples(shown_utterances, shown_seats),
                                                 saved_summaries or purpose_summary.Saved(),
                                                 names or NameList.build(seats, {}))
        return cls(shown_seats, utterances, entries, purposes, show_private,
                   closing.pieces_by_seat(entries, kind_of), [kind.kind_id for kind in kinds],
                   closing.ranking_titles(shown_utterances), subject_catalog, list(seats),
                   [entry.text for entry in every_entry if entry.seat_id in coach_seats],
                   config.coach_on() if coach_on is None else coach_on,
                   map_data, seat_map.place_seats(map_data, shown_seats) if map_data else None,
                   relief_data if map_data else None)

    @classmethod
    def load(cls, data_dir: Path, show_private: bool = False, map_file: Path | None = None,
             relief_dir: Path | None = None) -> "Library":
        seats = load_seats(data_dir / "seats.tsv")
        map_data = seat_map.load_map(map_file)
        library = cls.build(seats, load_utterances(data_dir), load_topics(data_dir), show_private,
                         talk_kinds.load_saved(data_dir), purpose_summary.load_saved(data_dir),
                         load_names(data_dir, seats), subjects.load_catalog(data_dir),
                         coach.load_coach(data_dir, {seat.seat_id for seat in seats}),
                         map_data=map_data,
                         relief_data=(relief.load_relief((map_data.width, map_data.height), relief_dir)
                                      if map_data else None))
        library.ask_tables = one_to_one.load_tables(data_dir / INGESTED_DIR)
        return library

    def seat_view(self, seat: Seat) -> dict:
        label = seat_label(seat, self.show_private)
        view = {"seat_id": seat.seat_id, "kind": seat.kind, "title": label.title, "detail": label.detail}
        # 直し35-2: who went abroad waits at the way out to 海外 on the map
        # (the seat table's 「越境の線の先」; 県外 or none: the way out to 県外).
        if seat.kind == "cross" and "海外" in seat.crossing_to:
            view["abroad"] = True
        return view

    def map_view(self) -> dict | None:
        """The map part of /api/setup, or None: no map, the seat list alone."""
        if self.map_data is None or self.placement is None:
            return None
        view = seat_map.map_view(self.map_data, self.placement, load_optional_text(SCHOOL_LABEL))
        view["relief"] = self.relief  # None: the flat map.
        return view

    def map_report(self) -> str:
        """The start-up line about the map: counts only."""
        return self.placement.report() if self.placement is not None else "地図なし"

    def relief_report(self) -> str:
        """The start-up line about the picture under the map."""
        return "立体の絵あり" if self.relief else "立体の絵なし（平らな地図）"

    def seat_list(self) -> list[dict]:
        order = list(KIND_LABELS)
        seats = sorted(self.seats, key=lambda s: order.index(s.kind) if s.kind in order else len(order))
        views = [self.seat_view(seat) for seat in seats]
        if self.placement is not None:  # Where each point is on the map.
            for view in views:
                point = self.placement.points[view["seat_id"]]
                view.update(x=point.x, y=point.y, outer=point.outer)
        return views


@dataclass
class Session:
    library: Library
    gate: Gate
    plant: bool = False  # Mix in the planted fake (SPEC 7-3), for the demo.
    rng: object = None
    session_id: str = field(default_factory=lambda: secrets.token_hex(4))
    lab: str = ""
    rounds: list[roundtable.Round] = field(default_factory=list)
    cards: list[QuestionCard] = field(default_factory=list)
    marks: dict[str, str] = field(default_factory=dict)  # seat_id -> utterance_id
    pressed_splits: set[tuple[int, int]] = field(default_factory=set)  # (round, split)
    started: float = field(default_factory=time.monotonic)  # Seconds used, never clock time.
    date: str = field(default_factory=today)
    records: Records | None = None  # None: nothing is kept (tests only).
    reflection: Reflection | None = None
    mores: dict[str, more.More] = field(default_factory=dict)  # 「もっと聞く」, by the piece pressed under.
    # An AI question answered after the screen asked for one before the
    # reflection (直し30-1): one mark, no name, no time.
    ai_answered_after_notice: bool = False
    # One to one (直し34): the items asked, by seat, in the order asked; the
    # free questions' outcome (found or not, no words); the seats thanked.
    one_asked: dict[str, list[str]] = field(default_factory=dict)
    one_free: dict[str, list[bool]] = field(default_factory=dict)
    one_thanked: list[str] = field(default_factory=list)
    one_spoken: list[speaker.Spoken] = field(default_factory=list)
    # A slide's pages tidied before one to one shows them (直し43,
    # one_tidy.py): the words shown, how many lines went, and why.
    one_tidied: list[dict] = field(default_factory=list)
    # The teacher's questions put to each person (直し36-3), by seat and item.
    one_rephrased: dict[str, dict[str, asker.Rephrased]] = field(default_factory=dict)
    # 帰る前に、ひとこと (直し38, hitokoto.py): in place of the reflection
    # sheet unless EBINO_REFLECT=old. None until it starts.
    talk: hitokoto.Hitokoto | None = None

    def __post_init__(self):
        self._subject_counts = Counter()  # With no records (tests): this sitting's only.
        self.guard = Guard(self.library.utterances)
        self.shelf = PurposeShelf(self.library.purposes, self.rng)
        self._seats = {seat.seat_id: seat for seat in self.library.seats}
        self._utterances = {u.id: u for u in self.library.utterances}
        self._tidied: dict[str, one_tidy.Tidied] = {}  # A slide's page tidied, by utterance ID.

    def save(self) -> None:
        """Kept after every step (SPEC 2-1: every action is recorded by itself)."""
        if self.records is not None:
            record = session_record(self)
            record["ai_answered_after_notice"] = self.ai_answered_after_notice
            # Each bubble shown: its original and its spoken words, which was
            # shown, and why the original was kept (直し31-7).
            record["spoken"] = [dict(spoken.record(), round=number) for number, r in enumerate(self.rounds, start=1)
                                for spoken in r.spoken.values()]
            # One to one (直し34): the items asked by name, whether a free
            # question found an answer, who was thanked; and its spoken words.
            record["one_to_one"] = [{"seat_id": seat_id, "items": items, "free_found": self.one_free.get(seat_id, []),
                                     "thanked": seat_id in self.one_thanked}
                                    for seat_id, items in self._one_seats().items()]
            record["one_spoken"] = [spoken.record() for spoken in self.one_spoken]
            record["one_tidied"] = list(self.one_tidied)
            # Which was shown, the teacher's question or one put to the
            # person, and why the teacher's was kept; never the words (直し36-3).
            record["one_rephrased"] = [dict(result.record(), seat_id=seat_id)
                                       for seat_id, found in self.one_rephrased.items() for result in found.values()]
            # 帰る前に、ひとこと (直し38): the questions put and why a fixed one
            # was, the student's words (they passed the name check), the
            # ladder, the scale, what was kept and the light; no name.
            record["hitokoto"] = self.talk.record() if self.talk is not None else None
            self.records.save_session(record)

    # --- what the student does ---

    def set_lab(self, choice: str) -> None:
        if choice not in LAB_CHOICES:
            raise Refused("unknown_lab_choice")
        self.lab = choice
        self.save()

    def ask(self, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            raise Refused("empty_question")
        if len(question) > MAX_QUESTION_CHARS:
            raise Refused("question_too_long")
        result = roundtable.run(self.gate, self.library.entries, self.library.seats, self.guard,
                                question, plant=self.plant)
        self._speak(result)
        self.rounds.append(result)
        if result.card:
            # The same question again with no seat answering: the card there is.
            result.card = self._keep_card(result.card)
        self.save()
        return self.round_view(len(self.rounds))

    def _speak(self, result: roundtable.Round) -> None:
        """The round's bubbles as spoken words, in one request (直し31-7)."""
        if not result.quotes or not config.speaker_on():
            return
        quotes = [{"id": q.utterance_id, "voice": q.voice, "text": q.text,
                   "paragraph": self._utterances[q.utterance_id].paragraph or q.text} for q in result.quotes]
        result.spoken = {spoken.utterance_id: spoken for spoken in speaker.speak(self.gate, quotes)}

    def card_like(self, seat_id: str, text: str) -> QuestionCard | None:
        """The card already made to this seat ("" for none) with these words,
        spaces and letter widths aside (直し31-2), or None."""
        words = normalize_for_match(text or "")
        return next((card for card in self.cards
                     if card.seat_id == seat_id and normalize_for_match(card.text) == words), None)

    def _keep_card(self, card: QuestionCard) -> QuestionCard:
        """One card per seat and words: a second is not kept; the first is given back."""
        same = self.card_like(card.seat_id, card.text)
        if same is not None:
            return same
        self.cards.append(card)
        return card

    def write_card(self, seat_id: str, text: str) -> dict:
        """A card the student writes at a seat shown as 「まだ誰も聞いていない」,
        at a seat 「司会が○○に聞いてみる」 found no answer from, or at a seat
        whose words a round showed, from its lamp card at the table (直し26-2;
        the box opens empty: the card holds the student's words only)."""
        if seat_id not in self.silent_seats() and seat_id not in self.not_answered_seats() \
                and seat_id not in self.spoken_seats():
            raise Refused("not_a_silent_seat")
        if len((text or "").strip()) > MAX_CARD_CHARS:
            raise Refused("card_too_long")
        # Pressed again (or sent from a second box for the seat): no new
        # card and no model; the card there is is shown (直し31-2).
        same = self.card_like(seat_id, (text or "").strip()) if (text or "").strip() else None
        if same is not None:
            return same.front() | {"again": True}
        card = editor.card_from_student(self.gate, seat_id, text or "", self.library.seats)
        if card is None:
            raise Refused("empty_card")
        self.cards.append(card)
        self.save()
        return card.front() | {"again": False}

    def mark(self, round_no: int, utterance_id: str) -> dict:
        """One marked quote per seat (SPEC 5-2). Marking it again takes it off."""
        quote = next((q for q in self._round(round_no).quotes if q.utterance_id == utterance_id), None)
        if quote is None:
            raise Refused("unknown_quote")
        if self.marks.get(quote.seat_id) == utterance_id:
            del self.marks[quote.seat_id]
        else:
            self.marks[quote.seat_id] = utterance_id
        self.save()
        return dict(self.marks)

    def press_split(self, round_no: int, index: int) -> str:
        """The heading goes into the input box as it is (SPEC 5-1 hint 1)."""
        splits = self._round(round_no).splits
        if not isinstance(index, int) or not 0 <= index < len(splits):
            raise Refused("unknown_split")
        self.pressed_splits.add((round_no, index))
        self.save()
        return splits[index].heading

    def close_round(self, round_no: int) -> dict:
        """「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A): asked once at
        the end of a round in which seats spoke; asking again gives the same."""
        result = self._round(round_no)
        if result.status != roundtable.ANSWERED:
            raise Refused("no_seat_spoke")
        if result.closing is None:
            counts = Counter(word.kind for r in self.rounds if r.closing for word in r.closing.words)
            result.closing = closing.run(self.gate, self.guard, result.question, result.seat_order,
                                         self.library.closing_pieces, self.seen_ids(), counts,
                                         self.library.kind_order)
            self.save()
        return self.closing_view(round_no)

    def closing_view(self, round_no: int) -> dict:
        """The fixed sentence and the words only when some seat's words passed;
        otherwise nothing is shown (a seat without such words says nothing).
        Each piece has the line of its kind over it, never 「この人が」: most
        pieces are an interviewer's article or a senior employee's words."""
        labels = {row["ID"]: row["見出し"] for row in load_table(CLOSING_KIND_LABELS, ("ID", "見出し"))}
        words = []
        for word in self._round(round_no).closing.words:
            utterance = self._utterances[word.utterance_id]
            words.append({"seat_id": word.seat_id, "utterance_id": word.utterance_id, "text": word.text,
                          "kind": word.kind, "label": labels.get(word.kind, ""),
                          "ranking_title": self.library.ranking_titles.get(word.utterance_id, ""),
                          "said": not utterance.note, "source": self.source(word.seat_id, utterance)})
        if not words:
            return {"round": round_no, "question": "", "words": []}
        return {"round": round_no, "question": load_text(CLOSING_QUESTION), "words": words}

    # --- コーチとオブザーバー (SPEC 5-1, coach.py) ---

    def coach_band(self, round_no: int) -> dict:
        """The two AI questions at the end of a round the student asked in:
        asked once; asked again, the same band. No cards: nothing is shown."""
        result = self._round(round_no)
        if result.status not in (roundtable.ANSWERED, roundtable.SILENT):
            raise Refused("no_round_for_band")
        if not self.library.coach_on:
            return {"round": round_no, "cards": [], "answered": ""}
        if result.band is None:
            result.band = coach.run(self.gate, self, round_no, self.library.coach_sources)
            self.save()
        return self.band_view(round_no)

    def band_view(self, round_no: int) -> dict:
        band = self._round(round_no).band
        return {"round": round_no, "cards": [coach.card_view(card) for card in band.cards],
                "answered": band.answered}

    def coach_answer(self, round_no: int, role: str, answer: str, after_notice: bool = False) -> dict:
        """The student's one line to one card of a band: it goes with that
        question to the next round, where the seats answer as always.
        after_notice: sent after the screen's line asking for one answer
        before the reflection (直し30-1); kept as one mark."""
        band = self._round(round_no).band
        if band is None or band.answered:
            raise Refused("no_band_to_answer")
        asked = next((card for card in band.cards if card.role == role), None)
        if asked is None:
            raise Refused("unknown_card")
        answer = _line(answer, MAX_LINE_CHARS, "empty_answer")
        if self.gate.names.hits(answer):
            return {"status": roundtable.ASK_AGAIN, "message": load_text(NAME_IN_QUESTION)}
        result = roundtable.run(self.gate, self.library.entries, self.library.seats, self.guard,
                                answer, plant=self.plant, ai_question=asked)
        self._speak(result)
        self.rounds.append(result)
        if result.status != roundtable.UNAVAILABLE:  # Unavailable: the card may be answered again.
            band.answered, band.answer = role, answer
            if after_notice:
                self.ai_answered_after_notice = True
        self.save()
        return self.round_view(len(self.rounds))

    # --- 「司会が○○に聞いてみる」 (SPEC 14-53 B) ---

    def _answered_round(self, round_no: int) -> roundtable.Round:
        result = self._round(round_no)
        if result.status != roundtable.ANSWERED:
            raise Refused("no_seat_spoke")
        return result

    def ask_card(self, round_no: int) -> dict:
        """The card as it stands; no model is called. Asked again after a
        mark, it may change until the student presses it."""
        result = self._answered_round(round_no)
        if result.ask_seat is not None:
            return {"round": round_no, "card": None, "asked": self.asked_view(round_no)}
        card = ask_seat.plan(self, round_no)
        if card is None:
            return {"round": round_no, "card": None, "asked": None}
        title = seat_label(self._seats[card.seat_id], self.library.show_private).title
        return {"round": round_no, "asked": None,
                "card": {"form": card.form, "seat_id": card.seat_id,
                         "header": load_text(ASK_SEAT_HEADER).format(seat=title), "question": card.text}}

    def ask_the_seat(self, round_no: int) -> dict:
        """The student pressed the card: the seat is asked, once per round."""
        result = self._answered_round(round_no)
        if result.ask_seat is not None:
            raise Refused("already_asked")
        card = ask_seat.plan(self, round_no)
        if card is None:
            raise Refused("no_ask_card")
        result.ask_seat = ask_seat.run(self, card)
        self.save()
        return self.asked_view(round_no)

    def asked_view(self, round_no: int) -> dict:
        asked = self._round(round_no).ask_seat
        title = seat_label(self._seats[asked.seat_id], self.library.show_private).title
        view = {"round": round_no, "status": asked.status, "seat_id": asked.seat_id,
                "header": load_text(ASK_SEAT_HEADER).format(seat=title), "question": asked.text,
                "label": "", "piece": None, "not_answered": "", "message": "",
                # Whether the student already wrote a card to this seat.
                "carded": any(c.origin == editor.ORIGIN_STUDENT and c.seat_id == asked.seat_id for c in self.cards)}
        if asked.status == ask_seat.ANSWERED:
            utterance = self._utterances[asked.answer_id]
            said = not utterance.note
            # The person's own words, or an article's: never shown as the person speaking.
            view["label"] = load_text(ASK_ANSWER_SAID if said else ASK_ANSWER_WRITTEN)
            view["piece"] = {"utterance_id": asked.answer_id, "seat_id": asked.seat_id, "text": asked.answer_text,
                             "ranking_title": self.library.ranking_titles.get(asked.answer_id, ""),
                             "said": said, "source": self.source(asked.seat_id, utterance)}
        elif asked.status == ask_seat.NOT_FOUND:
            # Shown only: it makes no card. The screen opens the seat's
            # 「聞きたいことを書く」 under it, with an empty box.
            view["not_answered"] = load_text(ASK_NOT_ANSWERED)
        else:
            view["message"] = load_text(MODEL_UNAVAILABLE)
        return view

    def not_answered_seats(self) -> list[str]:
        """Seats 「司会が○○に聞いてみる」 found no answer from."""
        return [r.ask_seat.seat_id for r in self.rounds
                if r.ask_seat is not None and r.ask_seat.status == ask_seat.NOT_FOUND]

    def more_origins(self) -> dict[str, int]:
        """Pieces 「もっと聞く」 may be pressed under, with their round: the
        rounds' last words and the answers 「司会が○○に聞いてみる」 found."""
        origins: dict[str, int] = {}
        for number, result in enumerate(self.rounds, start=1):
            for word in result.closing.words if result.closing else []:
                origins.setdefault(word.utterance_id, number)
            if result.ask_seat is not None and result.ask_seat.answer_id:
                origins.setdefault(result.ask_seat.answer_id, number)
        return origins

    def hear_more(self, utterance_id: str) -> dict:
        """「もっと聞く」: the next pieces of the same seat and section, to the
        end of the sentence, as recorded, shown as one passage with one
        source line (the notes of the pieces that have one; none when all
        are the person's own words). A ranking's title goes over the first
        of its items only."""
        origins = self.more_origins()
        if not isinstance(utterance_id, str) or utterance_id not in origins:
            raise Refused("not_a_last_word")
        state = self.mores.get(utterance_id)
        if state is None:
            seat_id = self._utterances[utterance_id].seat_id
            state = self.mores[utterance_id] = more.More(utterance_id, origins[utterance_id], seat_id)
        if not state.can_press:
            raise Refused("no_more_presses")
        pieces = more.press(state, self.library.utterances, self.seen_ids())
        self.save()
        shown = []
        title_over = ""
        for piece in pieces:
            title = self.library.ranking_titles.get(piece.id, "")
            shown.append({"utterance_id": piece.id, "seat_id": piece.seat_id, "text": piece.text,
                          "ranking_title": title if title != title_over else "",
                          "ranking_item": bool(title),  # Starts its own line in the passage.
                          "said": not piece.note})
            title_over = title
        return {"utterance_id": utterance_id, "pieces": shown,
                "source": self.passage_source(state.seat_id, pieces) if pieces else None,
                "ended": state.ended, "can_press": state.can_press}

    def more_card(self, utterance_id: str) -> dict:
        """「ここから先は、まだ聞いていない」 pressed: the round's question becomes
        a question card to that seat (SPEC 2-2). Once per piece."""
        state = self.mores.get(utterance_id) if isinstance(utterance_id, str) else None
        if state is None or not state.ended or state.card_id:
            raise Refused("not_ready_for_card")
        question = self._round(state.round_no).question
        card = self.card_like(state.seat_id, question) or self._keep_card(
            editor.card_for_seat(self.gate, editor.ORIGIN_NOT_HEARD, state.seat_id, question, self.library.seats))
        state.card_id = card.card_id
        self.save()
        return card.front()

    # --- one to one (直し34) ---

    def _one_seats(self) -> dict[str, list[str]]:
        seats = {seat_id: list(items) for seat_id, items in self.one_asked.items()}
        for seat_id in [*self.one_free, *self.one_thanked]:
            seats.setdefault(seat_id, [])
        return seats

    def _one_seat(self, seat_id) -> Seat:
        seat = self._seats.get(seat_id) if isinstance(seat_id, str) else None
        if seat is None:
            raise Refused("unknown_seat")
        return seat

    def one_items(self, seat_id: str) -> list[tuple[str, str, list[Utterance]]]:
        """(item, the teacher's question, its pieces) for each item of the
        seat's words that has a question and some words, in the questions'
        order (one_to_one.py says which items a seat's words have)."""
        seat = self._one_seat(seat_id)
        pieces = [u for u in self.library.utterances if u.seat_id == seat_id]
        asked = texts.ask_questions()
        tables = self.library.ask_tables
        out = []
        if pieces and all(one_to_one.is_page(u.section) for u in pieces):
            group = one_to_one.GROUP_OUTSIDER if seat.kind == "outsider_teacher" else one_to_one.GROUP_CROSS
            pages = tables["pages"].get(seat_id, {})
            for item, question in asked[group]:
                found = [u for u in pieces if item in pages.get(u.section, [])]
                # An item none of whose pages has anything to show once tidied
                # (a title only, a name) is not offered (直し43).
                if any(self.one_page(u).text for u in found):
                    out.append((item, question, found))
        elif seat.kind == "poster":
            for item, question in asked[one_to_one.GROUP_POSTER]:
                found = [u for u in pieces if u.section == item]
                if found:
                    out.append((item, question, found))
        else:
            ranking = tables["ranking"].get(seat_id)
            for item, question in asked[one_to_one.GROUP_ARTICLE]:
                found = [u for u in pieces if one_to_one.ARTICLE_SAME_ITEM.get(u.section, u.section) == item]
                if found:
                    out.append((item, question, found))
                if item == "本文" and ranking:  # The ranking after the body, as in the article.
                    found = [u for u in pieces if u.section == "ランキング"]
                    if found:
                        out.append((one_to_one.RANKING_ITEM, ranking, found))
        return out

    def one_open(self, seat_id: str) -> dict:
        """「この人に聞く」 pressed (直し36-3): in one request, the teacher's
        questions offered now (up to ONE_QUESTIONS) put to this person
        (asker.py), each item once a sitting; then the questions to offer.
        One offered later, after a question was asked, is the teacher's
        until 「この人に聞く」 is pressed again (one request a press; with
        every item in it, the model took longer than its limit)."""
        items = self.one_items(seat_id)
        done = self.one_rephrased.setdefault(seat_id, {})
        asked = self.one_asked.get(seat_id, [])
        offered = [(item, question, pieces) for item, question, pieces in items
                   if item not in asked][:one_to_one.ONE_QUESTIONS]
        todo = [{"id": item, "question": question, "paragraph": asker.item_paragraph(pieces)}
                for item, question, pieces in offered if item not in done and item != one_to_one.RANKING_ITEM]
        if todo and config.asker_on():
            for result in asker.rephrase(self.gate, todo):
                done[result.item] = result
            self.save()
        return self.one_view(seat_id)

    def one_view(self, seat_id: str) -> dict:
        """The questions to offer now: up to ONE_QUESTIONS of the items not
        asked yet, in order; done once every item with words has been asked.
        Each as put to this person where that passed (直し36-3)."""
        items = self.one_items(seat_id)
        asked = self.one_asked.get(seat_id, [])
        put = self.one_rephrased.get(seat_id, {})
        left = [(item, question) for item, question, _ in items if item not in asked]
        return {"seat_id": seat_id,
                "questions": [{"item": item, "question": put[item].text if item in put else question,
                               "rephrased": item in put and put[item].shown == asker.SHOWN_REPHRASED}
                              for item, question in left[:one_to_one.ONE_QUESTIONS]],
                "done": bool(items) and not left, "asked": list(asked)}

    def one_page(self, utterance: Utterance) -> one_tidy.Tidied:
        """A slide's page as one to one shows it (直し43, one_tidy.py): "" when
        nothing is left or the words tidied hold a name (lines joined, a
        name's letters may meet). Not a page: its words as recorded."""
        if not one_to_one.is_page(utterance.section):
            return one_tidy.Tidied(utterance.text)
        if utterance.id not in self._tidied:
            tidied = one_tidy.tidy_page(utterance.text)
            if tidied.text and self.gate.names.hits(tidied.text):
                tidied = one_tidy.Tidied("", tidied.dropped, (*tidied.reasons, one_tidy.NAME))
            self._tidied[utterance.id] = tidied
        return self._tidied[utterance.id]

    def _one_words(self, seat_id: str, pieces: list[Utterance]) -> dict:
        """The words shown at one to one: the pieces, up to about ONE_CHARS,
        as spoken words where the speaker's checks let them through. A
        slide's page tidied first (直し43): its title's line, its numbers
        and the PDF's breaks gone; a page with nothing left, or a name, not
        shown; the pages together cut at a sentence's end past ONE_CUT_CHARS.
        The words recorded are never changed: only those shown. The speaker
        is given the words tidied as the original (段2): the title's line
        gone is not a word dropped; stopped, past its limit or turned off,
        the words tidied are shown, never the page as recorded."""
        shown, said, met, total = [], [], [], 0
        for piece in pieces:
            met.append(piece)
            words = self.one_page(piece).text
            if not words:
                continue
            shown.append(piece)
            said.append(words)
            total += len(words)
            if total >= one_to_one.ONE_CHARS:
                break
        was_cut = False
        if any(one_to_one.is_page(u.section) for u in shown):
            said, was_cut = one_tidy.cut(said, one_to_one.ONE_CUT_CHARS)
        kept = {u.id: text for u, text in zip(shown, said)}
        last = shown[len(said) - 1].id if was_cut else ""
        # Each page met, in order: the words shown, or "" and why; "cut" on
        # the last shown when a cut came after it, and on a page cut off whole.
        for piece in met:
            if not one_to_one.is_page(piece.section):
                continue
            words = self.one_page(piece)
            cut_here = was_cut and (piece.id == last or bool(words.text) and piece.id not in kept)
            reasons = (*words.reasons, *([one_tidy.CUT] if cut_here else []))
            self.one_tidied.append(one_tidy.Tidied(kept.get(piece.id, ""), words.dropped, reasons).record(piece.id))
        shown = shown[:len(said)]
        spoken = {}
        if config.speaker_on():
            quotes = [{"id": u.id, "voice": u.voice, "text": text,
                       "paragraph": text if one_to_one.is_page(u.section) else u.paragraph or u.text}
                      for u, text in zip(shown, said)]
            for result in speaker.speak(self.gate, quotes):
                spoken[result.utterance_id] = result
                self.one_spoken.append(result)
        return {"pieces": [{"utterance_id": u.id, "text": text, "spoken": spoken[u.id].spoken if u.id in spoken else "",
                            "said": not u.note} for u, text in zip(shown, said)],
                "source": self.passage_source(seat_id, shown)}

    def one_ask(self, seat_id: str, item: str) -> dict:
        """A question picked: that item's words, and the questions after it."""
        found = {name: pieces for name, _, pieces in self.one_items(seat_id)}
        if not isinstance(item, str) or item not in found:
            raise Refused("unknown_item")
        asked = self.one_asked.setdefault(seat_id, [])
        if item not in asked:
            asked.append(item)
        words = self._one_words(seat_id, found[item])
        self.save()
        return {"item": item, **words, **self.one_view(seat_id)}

    def one_thanks(self, seat_id: str) -> dict:
        """「ありがとうございました」, once every item was asked: the seat is
        kept as thanked (its mark on the map), and one to one ends."""
        self._one_seat(seat_id)
        if not self.one_view(seat_id)["done"]:
            raise Refused("not_done")
        if seat_id not in self.one_thanked:
            self.one_thanked.append(seat_id)
        self.save()
        return {"thanked": list(self.one_thanked)}

    def one_free_question(self, seat_id: str, question: str) -> dict:
        """A question the student wrote: the librarian looks among this
        seat's words only. Found: those words; not: nothing (the screen says
        so and offers the question card)."""
        self._one_seat(seat_id)
        question = (question or "").strip()
        if not question:
            raise Refused("empty_question")
        if len(question) > MAX_QUESTION_CHARS:
            raise Refused("question_too_long")
        entries = [entry for entry in self.library.entries if entry.seat_id == seat_id]
        ids = []
        if entries:
            try:
                ids = librarian.find(self.gate, entries, question).utterance_ids
            except (GateError, ModelUnavailable):
                ids = []
        pieces = [self._utterances[i] for i in ids if i in self._utterances and self._utterances[i].seat_id == seat_id]
        # A slide's page with nothing to show once tidied is none (直し43); why, kept.
        for piece in pieces:
            if not self.one_page(piece).text:
                self.one_tidied.append(self.one_page(piece).record(piece.id))
        pieces = [piece for piece in pieces if self.one_page(piece).text]
        self.one_free.setdefault(seat_id, []).append(bool(pieces))
        self.save()
        if not pieces:
            return {"found": False, **self.one_view(seat_id)}
        return {"found": True, **self._one_words(seat_id, pieces[:1]), **self.one_view(seat_id)}

    def next_purposes(self) -> list[dict]:
        return [self.purpose_view(sample) for sample in self.shelf.next()]

    def paragraph(self, utterance_id: str) -> dict:
        """The paragraph a shown quote came from (SPEC 5-1: back to the source)."""
        if utterance_id not in self.shown_ids():
            raise Refused("not_shown")
        utterance = self._utterances[utterance_id]
        return {"utterance_id": utterance_id, "paragraph": utterance.paragraph or utterance.text}

    # --- the reflection sheet (SPEC 5-2) ---

    def reflect_begin(self, changed: str, now_question: str) -> dict:
        """The student writes first; then the moderator reads the record once."""
        if not any(r.status in (roundtable.ANSWERED, roundtable.SILENT) for r in self.rounds):
            raise Refused("no_round_yet")
        if self.reflection is not None:
            raise Refused("reflection_started")
        if changed not in CHANGED_CHOICES:
            raise Refused("unknown_changed_choice")
        now_question = _line(now_question, MAX_QUESTION_CHARS, "empty_now_question")
        if self.gate.names.hits(now_question):
            return {"status": roundtable.ASK_AGAIN, "message": load_text(NAME_IN_QUESTION)}
        self.reflection = reflection.begin(self.gate, self, changed, now_question)
        self.save()
        return {"status": "ok", "ask_back": self.reflection.ask_back}

    def reflect_answer(self, answer: str, declined: bool = False) -> dict:
        """One line, or 「答えない」. The next moves are shown after this."""
        current = self._reflection()
        if current.answered:
            raise Refused("already_answered")
        if declined:
            current.declined = True
        else:
            current.answer = _line(answer, MAX_LINE_CHARS, "empty_answer")
        current.answered = True
        self.save()
        return {"moves": [{"direction": m.direction, "label": DIRECTION_LABELS[m.direction], "text": m.text}
                          for m in current.moves]}

    def reflect_finish(self, chosen: str, own_move: str, rewrite: str, meet_seat: str, meet_reason: str) -> dict:
        current = self._reflection()
        if not current.answered or current.finished:
            raise Refused("not_ready_to_finish")
        if chosen not in [m.direction for m in current.moves] + [CHOSE_NONE, CHOSE_OWN]:
            raise Refused("unknown_move")
        # The seat to hear more from is optional ("" when none is picked).
        if meet_seat and meet_seat not in self._seats:
            raise Refused("unknown_seat")
        current.chosen = chosen
        if chosen == CHOSE_OWN:
            current.own_move = _line(own_move, MAX_LINE_CHARS, "empty_own_move")
        current.rewrite = _line(rewrite, MAX_QUESTION_CHARS, "", required=False)
        current.meet_seat = meet_seat
        current.meet_reason = _line(meet_reason, MAX_LINE_CHARS, "", required=False)
        current.finished = True
        picked = harvest.pick(harvest.found_moves(self, _sheet_heading))
        current.harvest_moves = [move.code for move in picked]
        current.harvest_go_field = next((m.field for m in picked if m.field), "")
        current.harvest_moves_line = harvest.moves_line(picked)
        self.save()
        sheet = self.sheet_view()
        if meet_seat:
            # ② comes right after the seat is picked (SPEC 5-3); the card after it.
            return sheet | {"uses": [harvest.use_view(force) for force in harvest.uses_offered(self)],
                            "harvest": None}
        # No seat: no ② and no second line; no move either: no card.
        card = {"moves": current.harvest_moves_line, "meet": ""} if picked else None
        return sheet | {"uses": [], "harvest": card}

    def harvest(self, use: str) -> dict:
        """② picked (or 「選ばない」); the card's ① and ② lines (SPEC 5-3)."""
        current = self._reflection()
        if not current.finished or not current.meet_seat or current.harvest_use:
            raise Refused("not_ready_for_harvest")
        offered = [str(force) for force in harvest.uses_offered(self)]
        if use not in offered + [harvest.CHOSE_NO_USE]:
            raise Refused("unknown_use")
        current.harvest_use = use
        self.save()
        title = seat_label(self._seats[current.meet_seat], self.library.show_private).title
        return {
            "moves": current.harvest_moves_line,
            "meet": harvest.meet_line(title, None if use == harvest.CHOSE_NO_USE else int(use)),
        }

    def subject(self) -> dict:
        """③, under ① and ② once they are on screen (SPEC 5-3): the model is
        asked once; asked again, the same ③ is sent back. {"subject": None}
        when no ③ is shown."""
        current = self._reflection()
        if not current.finished or (current.meet_seat and not current.harvest_use):
            raise Refused("not_ready_for_subject")
        if current.subject is None:
            current.subject = subjects.choose(self.gate, self.library.subject_catalog, self.lab,
                                              subjects.record_words(current), self._shown_subjects())
            for shown in current.subject.on_screen():
                self._count_shown_subject(shown)
            self.save()
        return {"subject": self._subject_view(current)}

    def _subject_view(self, current: Reflection) -> dict | None:
        # Tied to the question as the student holds it now (直し31-3).
        return subjects.view(self.library.subject_catalog, current.subject, current.rewrite or current.now_question)

    def subject_choose(self, choice) -> dict:
        """Of the two ③ shows when nothing else fit: 0 or 1, or "none"."""
        current = self._reflection()
        pick = current.subject
        if pick is None or pick.status != subjects.STATUS_CHOOSE or pick.chosen:
            raise Refused("not_choosing")
        if choice != subjects.CHOSE_NONE and (not isinstance(choice, int) or isinstance(choice, bool)
                                              or not 0 <= choice < len(pick.order[:2])):
            raise Refused("unknown_subject")
        subjects.pick_one(self.library.subject_catalog, self.lab, pick, choice, self._shown_subjects())
        self.save()
        return {"subject": self._subject_view(current)}

    def subject_more(self) -> dict:
        """「ほかの教科も見る」: the next candidate, round and round."""
        current = self._reflection()
        pick = current.subject
        if pick is None or len(pick.order) < 2 or pick.two_shown:
            raise Refused("no_other_subject")
        pick.index = (pick.index + 1) % len(pick.order)
        pick.presses += 1
        self._count_shown_subject(pick.shown())
        self.save()
        return {"subject": self._subject_view(current)}

    def _shown_subjects(self) -> Counter:
        return self.records.subject_counts() if self.records is not None else Counter(self._subject_counts)

    def _count_shown_subject(self, shown) -> None:
        if shown is None:
            return
        if self.records is not None:
            self.records.count_subject(shown.row.key)
        else:
            self._subject_counts[shown.row.key] += 1

    def _reflection(self) -> Reflection:
        if self.reflection is None:
            raise Refused("reflection_not_started")
        return self.reflection

    def sheet_view(self) -> dict:
        """The sheet as the student keeps it (SPEC 5-2 table)."""
        current = self._reflection()
        shown = {q.utterance_id: q for r in self.rounds for q in r.quotes}
        met_lives = []
        for seat_id in self.met_seats():
            utterance_id = self.marks.get(seat_id)
            if utterance_id in shown:
                utterance = self._utterances[utterance_id]
                met_lives.append({"text": shown[utterance_id].text, "said": not utterance.note,
                                  "source": self.source(seat_id, utterance)})
        move = next((m for m in current.moves if m.direction == current.chosen), None)
        meet = self.library.seat_view(self._seats[current.meet_seat]) if current.meet_seat else None
        return {
            "first_question": next((r.question for r in self.rounds if r.question), ""),
            "met_lives": met_lives,
            "splits": [{"heading": _sheet_heading(s.heading), "pressed": (n, i) in self.pressed_splits}
                       for n, r in enumerate(self.rounds, start=1) for i, s in enumerate(r.splits)],
            "cards": [card.text for card in self.cards],
            "changed": CHANGED_CHOICES[current.changed],
            "now_question": current.now_question,
            "ask_back": current.ask_back,
            "answer": current.answer,
            "declined": current.declined,
            "chosen": current.chosen,
            "move": {"label": DIRECTION_LABELS[move.direction], "text": move.text} if move else None,
            "own_move": current.own_move,
            "rewrite": current.rewrite,
            "meet": meet | {"reason": current.meet_reason} if meet else None,
            "meet_reason": current.meet_reason,  # Kept even with no seat picked.
        }

    # --- 帰る前に、ひとこと (直し38, hitokoto.py) ---

    def _talk(self, *stages: str) -> hitokoto.Hitokoto:
        if config.reflect_old():
            raise Refused("reflect_old")
        talk = self.talk
        if talk is None:
            raise Refused("hitokoto_not_started")
        if stages and talk.stage not in stages:
            raise Refused("not_now")
        return talk

    def _named(self, text: str) -> dict | None:
        """With a name in it: the line asking for it again (as for an answer
        to an AI's question); the words are neither kept nor sent."""
        if text and self.gate.names.hits(text):
            return {"status": roundtable.ASK_AGAIN, "message": load_text(NAME_IN_QUESTION)}
        return None

    def hitokoto_begin(self, opened) -> dict:
        """Today's map: the people on it, the split between two of them, the
        counts. opened: the bubbles the student opened, in that order."""
        if config.reflect_old():
            raise Refused("reflect_old")
        if not any(r.status in (roundtable.ANSWERED, roundtable.SILENT) for r in self.rounds):
            raise Refused("no_round_yet")
        if self.talk is not None:
            raise Refused("hitokoto_started")
        opened = [uid for uid in opened if isinstance(uid, str)] if isinstance(opened, list) else []
        self.talk = hitokoto.begin(self, opened, _sheet_heading)
        self.save()
        talk = self.talk
        view = talk.map_view()
        if talk.stage == hitokoto.SCALE:  # No one on the map: straight to the scale.
            view["question"] = talk.asked[-1].text
        return view

    def hitokoto_parts(self) -> dict:
        """The listener's short part of each card, asked once (8 seconds)."""
        talk = self._talk(hitokoto.MAP)
        if not talk.parts_asked:
            hitokoto.ask_parts(self.gate, talk)
            self.save()
        return {"parts": {str(index): part for index, part in talk.parts.items()}}

    def hitokoto_choose(self, person, part, omakase: bool = False) -> dict:
        """A lit part or a card pressed, or 「おまかせ」 (code picks: the first
        lit part, else the first card); then the listener's first question."""
        talk = self._talk(hitokoto.MAP)
        if omakase:
            person = min(talk.parts) if talk.parts else 0
            part = talk.parts.get(person, "")
        else:
            if not isinstance(person, int) or isinstance(person, bool) or not 0 <= person < len(talk.people):
                raise Refused("unknown_person")
            part = part if isinstance(part, str) else ""
            if part and talk.parts.get(person) != part:
                raise Refused("unknown_part")
        talk.chosen, talk.chosen_part, talk.omakase = person, part, bool(omakase)
        talk.stage = hitokoto.TALK
        asked = hitokoto.ask_listener(self.gate, self, talk, hitokoto.REACTION)
        self.save()
        return {"next": "ask", "question": asked.text, "omakase": bool(omakase), "person": person, "part": part}

    def _ladder_or_scale(self, talk: hitokoto.Hitokoto) -> dict:
        """Two 「わからない」 in a row: the ladder (once a sitting), else the scale."""
        talk.blank_run = 0
        if talk.ladder_shown:
            return self._to_scale(talk)
        if talk.split:
            return self._ladder_step(talk, hitokoto.LADDER_TWO)
        if len(talk.people) >= 2:
            return self._ladder_step(talk, hitokoto.LADDER_THREE)
        return self._ladder_step(talk, hitokoto.FILL)

    def _ladder_step(self, talk: hitokoto.Hitokoto, step: str) -> dict:
        texts = hitokoto.words()
        talk.stage = step
        talk.ladder_shown += 1
        question = texts[{hitokoto.LADDER_TWO: "ladder_two", hitokoto.LADDER_THREE: "ladder_three",
                          hitokoto.FILL: "ladder_fill"}[step]]
        talk.asked.append(hitokoto.Asked(step, question, "teacher"))
        view = {"next": step, "question": question}
        if step == hitokoto.LADDER_TWO:  # The split's two people's own words.
            view["options"] = [dict(talk.people[i].view(), index=i) for i in (talk.split["a"], talk.split["b"])]
        elif step == hitokoto.LADDER_THREE:  # The people on the map.
            view["options"] = [dict(p.view(), index=i) for i, p in enumerate(talk.people)]
        else:
            index = next(i for i in (talk.ladder_three, talk.ladder_two, 0) if i is not None)
            line = hitokoto.fill(texts["ladder_fill_line"], who=talk.people[index].title)
            before, _, after = line.partition(hitokoto.FILL_BLANK)
            view.update(before=before, after=after)
        return view

    def _to_scale(self, talk: hitokoto.Hitokoto) -> dict:
        talk.stage = hitokoto.SCALE
        question = hitokoto.words()["scale_q"]
        talk.asked.append(hitokoto.Asked("scale", question, "teacher"))
        return {"next": "scale", "question": question}

    def _next_listener(self, talk: hitokoto.Hitokoto, answer: str) -> dict:
        """The direction not asked yet, or the scale."""
        if talk.listener_asked >= hitokoto.MAX_LISTENER:
            return self._to_scale(talk)
        talk.stage = hitokoto.TALK
        asked = hitokoto.ask_listener(self.gate, self, talk, hitokoto.DIRECTIONS[talk.listener_asked], answer)
        return {"next": "ask", "question": asked.text}

    def hitokoto_answer(self, text, dont_know: bool = False) -> dict:
        """An answer to the listener's question, or 「わからない」. Once: the
        same question again; twice in a row: the ladder."""
        talk = self._talk(hitokoto.TALK)
        text = "" if dont_know else _line(text, hitokoto.MAX_LINE, "empty_answer")
        named = self._named(text)
        if named:
            return named
        direction = next(a.step for a in reversed(talk.asked) if a.step in hitokoto.DIRECTIONS)
        if dont_know or hitokoto.is_blank(text):
            talk.answers.append({"step": direction, "dont_know": True})
            talk.blank_run += 1
            if talk.blank_run == 1:
                self.save()
                return {"next": "again", "note": hitokoto.words()["again"], "question": talk.asked[-1].text}
            view = self._ladder_or_scale(talk)
            self.save()
            return view
        talk.blank_run = 0
        talk.answers.append({"step": direction, "text": text})
        talk.written.append({"step": direction, "text": text})
        view = self._next_listener(talk, text)
        self.save()
        return view

    def hitokoto_ladder(self, choice) -> dict:
        """2択 (one of the split's two) or 3択 (one on the map)."""
        talk = self._talk(hitokoto.LADDER_TWO, hitokoto.LADDER_THREE)
        allowed = ((talk.split["a"], talk.split["b"]) if talk.stage == hitokoto.LADDER_TWO
                   else tuple(range(len(talk.people))))
        if not isinstance(choice, int) or isinstance(choice, bool) or choice not in allowed:
            raise Refused("unknown_choice")
        talk.answers.append({"step": talk.stage, "seat_id": talk.people[choice].seat_id})
        if talk.stage == hitokoto.LADDER_TWO:
            talk.ladder_two = choice
            view = self._ladder_step(talk, hitokoto.LADDER_THREE)
        else:
            talk.ladder_three = choice
            view = self._ladder_step(talk, hitokoto.FILL)
        self.save()
        return view

    def hitokoto_fill(self, text, skip: bool = False) -> dict:
        """The blank of 「○○の話の、［　　］のところが近いと思った。」, or left
        empty. Written: back to the direction not asked yet."""
        talk = self._talk(hitokoto.FILL)
        text = "" if skip else _line(text, hitokoto.MAX_LINE, "", required=False)
        named = self._named(text)
        if named:
            return named
        if not text or hitokoto.is_blank(text):
            talk.answers.append({"step": hitokoto.FILL, "dont_know": True})
            view = self._to_scale(talk)
        else:
            talk.fill_text = text
            talk.answers.append({"step": hitokoto.FILL, "text": text})
            talk.written.append({"step": hitokoto.FILL, "text": text})
            view = self._next_listener(talk, text)
        self.save()
        return view

    def hitokoto_scale(self, value) -> dict:
        """The doubt now, 0 to 15 (the first question's as 10): the next
        question by it (the teacher's three)."""
        talk = self._talk(hitokoto.SCALE)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= hitokoto.SCALE_TOP:
            raise Refused("unknown_scale")
        talk.scale = value
        texts = hitokoto.words()
        if value < hitokoto.SCALE_FIRST:
            key = "scale_down"
        elif value == hitokoto.SCALE_FIRST:
            key = "scale_same"
        else:
            key = "scale_up"
        talk.asked.append(hitokoto.Asked("forward", texts[key], "teacher"))
        talk.stage = hitokoto.FORWARD
        self.save()
        return {"next": "forward", "question": texts[key]}

    def _kept_line(self, talk: hitokoto.Hitokoto, step: str, text, skip: bool):
        """One optional line: (its words, or ""), or (None, the ask-again view)."""
        text = "" if skip else _line(text, hitokoto.MAX_LINE, "", required=False)
        named = self._named(text)
        if named:
            return None, named
        if text and not hitokoto.is_blank(text):
            talk.written.append({"step": step, "text": text})
            return text, None
        return "", None

    def hitokoto_forward(self, text, skip: bool = False) -> dict:
        """The answer to the scale's next question (optional; no ladder)."""
        talk = self._talk(hitokoto.FORWARD)
        text, named = self._kept_line(talk, "forward", text, skip)
        if named:
            return named
        talk.forward, talk.stage = text, hitokoto.WAY
        self.save()
        return {"next": "way"}

    def hitokoto_way(self, text, skip: bool = False) -> dict:
        """「まだ決めなくていい。頭に置いておきたい道は？」 (optional)."""
        talk = self._talk(hitokoto.WAY)
        text, named = self._kept_line(talk, "way", text, skip)
        if named:
            return named
        talk.way, talk.stage = text, hitokoto.SUBJECT
        self.save()
        return {"next": "subject"}

    def hitokoto_subject(self, answer) -> dict:
        """「授業で習ったことと近い話はあった？」: yes, no, or not sure."""
        talk = self._talk(hitokoto.SUBJECT)
        if answer not in hitokoto.SUBJECT_ANSWERS:
            raise Refused("unknown_answer")
        talk.subject = answer
        talk.stage = hitokoto.SUBJECT_NOTE if answer == "yes" else hitokoto.MEET
        self.save()
        return {"next": talk.stage}

    def hitokoto_subject_note(self, text, skip: bool = False) -> dict:
        """Which lesson (optional); then ③, asked for once, with the question
        held now and the lesson's name as the record's words."""
        talk = self._talk(hitokoto.SUBJECT_NOTE)
        text, named = self._kept_line(talk, "subject", text, skip)
        if named:
            return named
        talk.subject_note = text
        talk.subject_pick = subjects.choose(self.gate, self.library.subject_catalog, self.lab,
                                            {"question": talk.first_question, "answer": text, "move": ""},
                                            self._shown_subjects())
        for shown in talk.subject_pick.on_screen():
            self._count_shown_subject(shown)
        talk.stage = hitokoto.MEET
        self.save()
        return {"next": "meet", "subject": self._talk_subject(talk)}

    def _talk_subject(self, talk: hitokoto.Hitokoto) -> dict | None:
        return subjects.view(self.library.subject_catalog, talk.subject_pick, talk.first_question)

    def hitokoto_subject_choose(self, choice) -> dict:
        talk = self._talk(hitokoto.MEET, hitokoto.USE, hitokoto.END)
        pick = talk.subject_pick
        if pick is None or pick.status != subjects.STATUS_CHOOSE or pick.chosen:
            raise Refused("not_choosing")
        if choice != subjects.CHOSE_NONE and (not isinstance(choice, int) or isinstance(choice, bool)
                                              or not 0 <= choice < len(pick.order[:2])):
            raise Refused("unknown_subject")
        subjects.pick_one(self.library.subject_catalog, self.lab, pick, choice, self._shown_subjects())
        self.save()
        return {"subject": self._talk_subject(talk)}

    def hitokoto_subject_more(self) -> dict:
        talk = self._talk(hitokoto.MEET, hitokoto.USE, hitokoto.END)
        pick = talk.subject_pick
        if pick is None or len(pick.order) < 2 or pick.two_shown:
            raise Refused("no_other_subject")
        pick.index = (pick.index + 1) % len(pick.order)
        pick.presses += 1
        self._count_shown_subject(pick.shown())
        self.save()
        return {"subject": self._talk_subject(talk)}

    def hitokoto_meet(self, seat_id) -> dict:
        """The seat to hear more from (texts/meet_question.txt), or none. A
        seat: ②'s uses, as the record fits them."""
        talk = self._talk(hitokoto.MEET)
        seat_id = seat_id if isinstance(seat_id, str) else ""
        if seat_id and seat_id not in self._seats:
            raise Refused("unknown_seat")
        talk.meet_seat = seat_id
        talk.stage = hitokoto.USE if seat_id else hitokoto.END
        self.save()
        return {"uses": [harvest.use_view(force) for force in harvest.uses_offered(self)] if seat_id else []}

    def hitokoto_use(self, use) -> dict:
        """② picked, or 「選ばない」: the card's ② line (never ①)."""
        talk = self._talk(hitokoto.USE)
        if use not in [str(force) for force in harvest.uses_offered(self)] + [harvest.CHOSE_NO_USE]:
            raise Refused("unknown_use")
        talk.meet_use, talk.stage = use, hitokoto.END
        self.save()
        title = seat_label(self._seats[talk.meet_seat], self.library.show_private).title
        return {"meet": harvest.meet_line(title, None if use == harvest.CHOSE_NO_USE else int(use))}

    def hitokoto_light(self) -> dict:
        """今日、光ったところ: asked once, at the end or at 「ここまでにする」."""
        talk = self._talk()
        if talk.light is None:
            talk.light = hitokoto.ask_light(self.gate, self, talk)
            talk.stage = hitokoto.LIT
            self.save()
        return hitokoto.light_view(talk)

    def hitokoto_sheet(self, now_question) -> dict:
        """The question as held now (optional) and the one sheet."""
        talk = self._talk(hitokoto.LIT, hitokoto.SHEET)
        text = _line(now_question, MAX_QUESTION_CHARS, "", required=False)
        named = self._named(text)
        if named:
            return named
        talk.now_question = text
        talk.stage = hitokoto.SHEET
        self.save()
        return hitokoto.sheet_view(talk)

    # --- what the sitting has gathered ---

    def met_seats(self) -> list[str]:
        """Seats whose words reached the screen, in the order first met."""
        return list(dict.fromkeys(s for r in self.rounds for s in r.seat_order))

    def silent_seats(self) -> list[str]:
        return list(dict.fromkeys(s for r in self.rounds for s in r.silent_seats))

    def spoken_seats(self) -> list[str]:
        """The seats whose words a round showed."""
        return list(dict.fromkeys(q.seat_id for r in self.rounds for q in r.quotes))

    def shown_ids(self) -> set[str]:
        return {q.utterance_id for r in self.rounds for q in r.quotes}

    def seen_ids(self) -> set[str]:
        """Every piece this student was shown: the rounds' quotes, the
        rounds' last words, what 「もっと聞く」 showed and the seats' answers.
        Never shown again in a last word, a seat's answer or 「もっと聞く」."""
        closings = {w.utterance_id for r in self.rounds if r.closing for w in r.closing.words}
        heard = {piece_id for state in self.mores.values() for piece_id in state.shown}
        answers = {r.ask_seat.answer_id for r in self.rounds if r.ask_seat and r.ask_seat.answer_id}
        return self.shown_ids() | closings | heard | answers

    def seconds_used(self) -> int:
        return int(time.monotonic() - self.started)

    # --- views ---

    def _round(self, round_no: int) -> roundtable.Round:
        if not isinstance(round_no, int) or not 1 <= round_no <= len(self.rounds):
            raise Refused("unknown_round")
        return self.rounds[round_no - 1]

    def source(self, seat_id: str, utterance: Utterance) -> dict:
        seat = self._seats[seat_id]
        label = seat_label(seat, self.library.show_private)
        return {"title": label.title, "detail": label.detail, "note": utterance.note}

    def passage_source(self, seat_id: str, pieces: list[Utterance]) -> dict:
        """One source line for pieces shown together: the seat, and the notes
        of the pieces that have one, each once, in reading order."""
        label = seat_label(self._seats[seat_id], self.library.show_private)
        notes = dict.fromkeys(piece.note for piece in pieces if piece.note)
        return {"title": label.title, "detail": label.detail, "note": PASSAGE_NOTE_JOIN.join(notes)}

    def round_view(self, round_no: int) -> dict:
        result = self._round(round_no)
        quotes = []
        for quote in result.quotes:
            utterance = self._utterances[quote.utterance_id]
            quotes.append({
                "utterance_id": quote.utterance_id,
                "seat_id": quote.seat_id,
                "text": quote.text,
                # The same as spoken words, "" when the original is shown (直し31-7).
                "spoken": result.spoken[quote.utterance_id].spoken if quote.utterance_id in result.spoken else "",
                # A person's own words get 「」; article text gets its note instead.
                "said": not utterance.note,
                "source": self.source(quote.seat_id, utterance),
            })
        return {
            "round": round_no,
            "question": result.question,  # "" when it held a name (ask_again).
            "status": result.status,
            "reason": result.reason,
            "message": result.message,
            "answered_seats": result.answered_seats,
            "seat_order": result.seat_order,
            "steps": {"found": len(result.candidates), "passed": result.guard_passed,
                      "stopped": result.guard_stopped},
            "quotes": quotes,
            "planted_stopped": list(result.planted_stopped),
            "splits": [{"index": i, "heading": s.heading, "side_a": list(s.side_a), "side_b": list(s.side_b)}
                       for i, s in enumerate(result.splits)],
            "silent_seats": list(result.silent_seats),
            "card": result.card.front() if result.card else None,
            "met_seats": self.met_seats(),
            # The AI question this round's question answers (coach.py), or None.
            "ai_question": ({"role": result.ai_question.role, "label": coach.label(result.ai_question.role),
                             "text": result.ai_question.text} if result.ai_question else None),
        }

    def purpose_view(self, sample: PurposeSample) -> dict:
        seat = self._seats[sample.seat_id]
        label = seat_label(seat, self.library.show_private)
        return {"seat_id": sample.seat_id, "texts": list(sample.texts), "summarized": sample.summarized,
                "source": {"title": label.title, "detail": label.detail, "note": ""}}
