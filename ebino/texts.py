"""Screen wording the teacher may edit lives in texts/*.txt, not in code."""

from pathlib import Path

TEXTS_DIR = Path(__file__).resolve().parent.parent / "texts"
SPLIT_NOTICE = "split_notice"  # Shown above every split (SPEC 14-39).
# Always shown on the round-table input screen and the reflection sheet's
# writing box (SPEC 2-1, 14-47).
HEAVY_TALK_NOTICE = "heavy_talk_notice"
# A sentence nobody said, mixed in to show the guard stopping it (SPEC 7-3).
PLANTED_FAKE_QUOTE = "planted_fake_quote"
# Shown when a model refused or failed (SPEC 14-51). Never mixed with
# 「この問いに答えた席：0」: the seats were not silent.
MODEL_UNAVAILABLE = "model_unavailable"
# Shown when the student's question holds a word on the gate's name list.
# Waiting does not help, so it asks for the word to be left out or put
# another way. It never says which word: that would show the name list.
NAME_IN_QUESTION = "name_in_question"
# The seven things told before a student starts (SPEC 2-1), one per line.
START_NOTICE = "start_notice"
LAB_QUESTION = "lab_question"  # The one question asked first (SPEC 2-1).
ANSWERED_COUNT = "answered_count"  # {n} is the number of seats that answered.
NOT_ASKED_YET = "not_asked_yet"  # On a related seat with no words (SPEC 14-12).
INPUT_EXAMPLE = "input_example"  # An invented topic, never a script question.
WORK_QUESTIONS = "work_questions"  # The school's work questions, one per line.
PURPOSE_HEADING = "purpose_heading"  # Above the poster purpose samples.
# The question back when the moderator's fails the code check (SPEC 5-2, 6).
ASK_BACK_FALLBACK = "ask_back_fallback"
# Shown while the screen waits on the models: after a question is sent to
# the table, and while the moderator reads the record for the reflection.
WAITING_ASK = "waiting_ask"
WAITING_REFLECTION = "waiting_reflection"
# Shown when the screen could not reach the app; {error} is a reason code.
SEND_FAILED = "send_failed"
# The sheet's 出会った生き方 when the student marked no words (SPEC 5-2).
MET_LIVES_EMPTY = "met_lives_empty"
# Today's harvest card (SPEC 5-3): its heading, and the line above ②.
HARVEST_HEADING = "harvest_heading"
HARVEST_USE_QUESTION = "harvest_use_question"
# The sheet's optional question for a seat to hear more from, and the card's
# second line, which starts with the same words.
MEET_QUESTION = "meet_question"
HARVEST_MEET_PREFIX = "harvest_meet_prefix"
# Words that show going to meet someone, one per line, looked for in what the
# student wrote on the sheet (the harvest card's ④). Not shown on screen.
GO_WORDS = "go_words"
# The round's last word (SPEC 14-53 A): the moderator's fixed sentence.
CLOSING_QUESTION = "closing_question"
# The kinds of talk a piece is tagged with (columns ID・名前・説明; the 説明 is
# what the tagger model is told), and the line shown over a piece of each
# kind in the round's last word (columns ID・見出し). Tables the teacher edits.
TALK_KINDS = "talk_kinds"
CLOSING_KIND_LABELS = "closing_kind_labels"
# 「もっと聞く」: shown when the seat's section has no next piece (a press on
# it makes a question card), and after that card is made.
MORE_END = "more_end"
MORE_CARD_DONE = "more_card_done"
# 「司会が○○に聞いてみる」 (SPEC 14-53 B): the card's line ({seat} is the
# seat's title), the two forms of the question ({quote} is the record's own
# words), each with a sentence for a piece shown with a source note
# (_written), one for a company's introduction (_company) and one for a senior
# employee's words (_senior), the line over an answer by its voice, and
# 「まだ答えていない」.
ASK_SEAT_HEADER = "ask_seat_header"
ASK_WHY = "ask_why"
ASK_WHY_WRITTEN = "ask_why_written"
ASK_WHY_COMPANY = "ask_why_company"
ASK_WHY_SENIOR = "ask_why_senior"
ASK_OTHER_SIDE = "ask_other_side"
ASK_OTHER_SIDE_WRITTEN = "ask_other_side_written"
ASK_OTHER_SIDE_COMPANY = "ask_other_side_company"
ASK_OTHER_SIDE_SENIOR = "ask_other_side_senior"
ASK_ANSWER_SAID = "ask_answer_said"
ASK_ANSWER_WRITTEN = "ask_answer_written"
ASK_NOT_ANSWERED = "ask_not_answered"
# The small mark on a purpose sample shown as its summary (purpose_summary.py),
# so it is never taken for the senior's own words.
SAMPLE_SUMMARIZED = "sample_summarized"
# The harvest card's ③ (SPEC 5-3, subjects.py): the teacher's tables of
# candidates (札・科目・項目番号・本文の該当句・見出し・ひとこと・手がかりの言葉)
# and of 札 (札・名前・説明), copied as they are from the teacher's side; the
# words for 〔いつ〕 by the mark in 学ぶ人 (記号・いつ); the line with a
# heading and without one ({いつ}{科目}{見出し}); and the button for the next.
HARVEST_SUBJECTS = "harvest_subjects"
HARVEST_FUDA = "harvest_fuda"
HARVEST_SUBJECT_WHEN = "harvest_subject_when"
HARVEST_SUBJECT_LINE = "harvest_subject_line"
HARVEST_SUBJECT_LINE_PLAIN = "harvest_subject_line_plain"
HARVEST_SUBJECT_MORE = "harvest_subject_more"
# ③ as a card tied to the student's question (直し31-3): the line over it, the
# label over the question, and the words when the student picks one of two.
HARVEST_SUBJECT_LINK = "harvest_subject_link"
HARVEST_SUBJECT_QUESTION = "harvest_subject_question"
HARVEST_SUBJECT_CHOOSE = "harvest_subject_choose"
HARVEST_SUBJECT_PICK = "harvest_subject_pick"
HARVEST_SUBJECT_NONE = "harvest_subject_none"
# The line over the two cards once the student chose neither (直し31続き-3).
HARVEST_SUBJECT_NONE_LINE = "harvest_subject_none_line"
# コーチとオブザーバー (SPEC 5-1, coach.py): each card's line (the role's name
# and what it asks from), the mark that it is an AI's question, and the
# observer's view, which is told to the model and never shown.
COACH_LABEL = "coach_label"
OBSERVER_LABEL = "observer_label"
AI_QUESTION_BADGE = "ai_question_badge"
OBSERVER_VIEW = "observer_view"
# The school's landmark on the map (SPEC 14-65): its label, one line. Missing
# or empty: no landmark.
SCHOOL_LABEL = "school_label"

# The map's buttons (map.js): 地図にもどす and the zoom buttons. Columns
# ID・文字・読み上げ; an empty 読み上げ reads the 文字 itself.
MAP_BUTTONS = "map_buttons"
# The drawer's parts (直し32-1): each one's name, on its button and over it.
DRAWER_PARTS = "drawer_parts"
DRAWER_PART_IDS = ("paragraph", "rounds", "seats", "purposes")
# The one box at the foot (直し32-2): to whom it goes (and the × back to
# everyone), its button's word for each, and the line after a send.
# One to one's words (直し34): 「円卓にもどす」 and the rest.
ONE_WORDS = "one_words"
ONE_WORD_IDS = ("back", "not_found", "to_card", "done", "thanks")
INPUT_TO = "input_to"
INPUT_TO_IDS = ("all", "seat", "ai", "clear")
INPUT_SEND = "input_send"
INPUT_SEND_IDS = ("all", "seat", "ai")
INPUT_DONE = "input_done"
INPUT_DONE_IDS = ("seat", "ai", "split")
MAP_BUTTON_IDS = ("back", "zoom_in", "zoom_out", "zoom_all")
# Round the map (map.js): the word on the mark that points north (the north
# row's 方位), and by each of the map's four sides what lies that way.
# Columns ID・方位・その方向にある所.
MAP_AROUND = "map_around"
MAP_AROUND_IDS = ("north", "west", "south", "east")
# At the round table (map.js, 直し26-2): the line by the map's lower edge
# once the table opens, and the choices a seat's lamp card opens, pressed
# (columns ID・文字), with the button that closes them (直し27-1).
BUBBLE_HINT = "bubble_hint"
BUBBLE_CLOSE = "bubble_close"
SEAT_ICONS = "seat_icons"  # 肩書きの言葉 -> 円卓の席の絵 (直し29-3), the first row that fits.
SEAT_ICON_NAMES = ("medical", "care", "child", "beauty", "town", "food", "farm", "forest", "stay", "build",
                   "make", "move", "safety", "culture", "shop", "animal")
BUBBLE_ANSWER = "bubble_answer"  # コーチ・オブザーバーに「答える」 (直し29-1).
BUBBLE_CHOICES = "bubble_choices"
# Under the reflection sheet (直し30-2): 最初にもどる, and the line and the two
# buttons it asks with, on the page itself.
BACK_TO_START = "back_to_start"
# By 「ふりかえりへ」 when no AI question has been answered yet (直し30-1).
REFLECT_NEEDS_ANSWER = "reflect_needs_answer"
# The button that ends the opening after a Lab is picked (直し30-3).
OPENING_SKIP = "opening_skip"
# Just over the two cards of コーチ and オブザーバー, until one is answered (直し30の続き-0).
AI_ANSWER_HINT = "ai_answer_hint"
# The same words to the same seat a second time: no new card, the one there is (直し31-2).
CARD_ALREADY = "card_already"
# 「いまやること」 (直し31-5): the four steps, the one line for each state, the
# first screen's line of what this is for, and over the first question box
# the counts of whose words are in the app, with examples of questions.
NOW_STEPS = "now_steps"
NOW_LINE = "now_line"
NOW_STEP_IDS = ("write", "read", "ask", "reflect")
NOW_LINE_IDS = ("start", "preparing", "write", "asking", "reading", "table", "pressed", "card", "one", "after", "split",
                "reflect")
# The sign in the middle of the map while the model is waited for (直し42):
# a short big word and one small line for each kind of wait the screen
# names; gather, the seats flying to the round table; slow, the small line
# after a long wait (its big word stays the wait's own, so it is empty);
# find, moderate and speak, the steps a question's round is really at
# (roundtable.STEPS, 直し42 段2).
WAIT_SIGN = "wait_sign"
WAIT_SIGN_IDS = ("start", "ask", "coach", "ask_seat", "reflect", "subject", "listen", "light", "gather", "slow",
                 "find", "moderate", "speak")
WAIT_SIGN_NO_WORD = ("slow",)
START_PURPOSE = "start_purpose"
# What the app is, in a few lines, and how it goes, step by step, one line
# for each step of the band at the top: the first look's first page (the
# teacher, 11/6: right before whose words are in, not on the first screen).
START_ABOUT = "start_about"
START_FLOW = "start_flow"
INSIDE_HEADING = "inside_heading"
INSIDE_COUNTS = "inside_counts"
INSIDE_END = "inside_end"
INSIDE_OPEN = "inside_open"
QUESTION_EXAMPLES = "question_examples"
QUESTION_EXAMPLES_LEAD = "question_examples_lead"
QUESTION_EXAMPLES_END = "question_examples_end"
# The AI's seat (直し32-3): its name, the line said the first time, its mark.
AI_SEAT_LABEL = "ai_seat_label"
AI_SEAT_NOTE = "ai_seat_note"
AI_SEAT_MARK = "ai_seat_mark"
# The bubbles as spoken words (直し31-7): the line said once, the small mark
# on each such bubble, and the spoken words code lets in without the paragraph.
SPOKEN_NOTE = "spoken_note"
SPOKEN_MARK = "spoken_mark"
SPOKEN_ALLOWED = "spoken_allowed"
# The words of an original that may be left out of its spoken words, when the
# third person becomes the first (直し31続き-1). One a line; may be empty.
SPOKEN_DROP_OK = "spoken_drop_ok"
BACK_TO_START_CONFIRM = "back_to_start_confirm"
BACK_TO_START_YES = "back_to_start_yes"
BACK_TO_START_NO = "back_to_start_no"
# The map's first stop for the keyboard, seen only when it is there: it goes
# past the points to the map's column (直し41 段2).
MAP_SKIP = "map_skip"
BUBBLE_CHOICE_IDS = ("paragraph", "mark", "card", "read")
# Under each of them, the first time a student presses a bubble (直し32-4).
BUBBLE_CHOICES_HELP = "bubble_choices_help"
# The guide (the teacher, 11/6: the students could not go on without being
# told): the first look at whose words are in, its heading and its button;
# and the bubble by the one thing to press now, for the states that have one.
GUIDE = "guide"
GUIDE_IDS = ("host_mark", "about_title", "about_next", "first_look_title", "first_look_go", "write", "table", "pressed", "answer_ai", "after")

# Everything the screen shows from texts/, sent to it once.
SCREEN_TEXTS = (
    HEAVY_TALK_NOTICE, SPLIT_NOTICE, START_NOTICE, LAB_QUESTION, ANSWERED_COUNT,
    NOT_ASKED_YET, INPUT_EXAMPLE, PURPOSE_HEADING, WAITING_ASK, WAITING_REFLECTION,
    SEND_FAILED, MET_LIVES_EMPTY, HARVEST_HEADING, HARVEST_USE_QUESTION, MEET_QUESTION,
    HARVEST_MEET_PREFIX, MORE_END, MORE_CARD_DONE, SAMPLE_SUMMARIZED, HARVEST_SUBJECT_MORE,
    BUBBLE_HINT, BUBBLE_CLOSE, BUBBLE_ANSWER,
    BACK_TO_START, BACK_TO_START_CONFIRM, BACK_TO_START_YES, BACK_TO_START_NO, REFLECT_NEEDS_ANSWER,
    OPENING_SKIP, AI_ANSWER_HINT, CARD_ALREADY,
    HARVEST_SUBJECT_QUESTION, HARVEST_SUBJECT_PICK, HARVEST_SUBJECT_NONE,
    START_PURPOSE, START_ABOUT, INSIDE_HEADING, INSIDE_END, INSIDE_OPEN, QUESTION_EXAMPLES_LEAD, QUESTION_EXAMPLES_END,
    SPOKEN_NOTE, SPOKEN_MARK, AI_SEAT_LABEL, AI_SEAT_NOTE, AI_SEAT_MARK, MAP_SKIP,
)
SCREEN_LISTS = (START_NOTICE, WORK_QUESTIONS, QUESTION_EXAMPLES)


def load_text(name: str) -> str:
    return (TEXTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def load_optional_text(name: str) -> str:
    """A text that may be missing: "" then."""
    try:
        return load_text(name)
    except (OSError, UnicodeDecodeError):
        return ""


def load_lines(name: str) -> list[str]:
    return [line.strip() for line in load_text(name).splitlines() if line.strip()]


# The questions offered at one to one (直し34-1): the teacher's draft, one a
# line, 種類 (the kind of the seat's words) / 項目 (an item of them) / 質問.
ASK_QUESTIONS = "ask_questions"
ASK_QUESTION_COLUMNS = ("種類", "項目", "質問")


def ask_questions() -> dict[str, list[tuple[str, str]]]:
    """{種類: [(項目, 質問), ...] in the file's order}, from ask_questions.txt
    (a table with a header row, though a .txt: the teacher's own file)."""
    out: dict[str, list[tuple[str, str]]] = {}
    for row in read_table(TEXTS_DIR / f"{ASK_QUESTIONS}.txt", ASK_QUESTION_COLUMNS):
        out.setdefault(row["種類"], []).append((row["項目"], row["質問"]))
    return out


def load_table(name: str, columns: tuple[str, ...], may_be_empty: tuple[str, ...] = ()) -> list[dict[str, str]]:
    """A tab-separated table in texts/: its rows, in order."""
    return read_table(TEXTS_DIR / f"{name}.tsv", columns, may_be_empty)


def read_table(path: Path, columns: tuple[str, ...], may_be_empty: tuple[str, ...] = ()) -> list[dict[str, str]]:
    """A tab-separated table with a header row: its rows, in order. Only the
    columns in may_be_empty may hold an empty cell. Errors give the file's
    name and line numbers only, never a path or a cell."""
    lines = [line for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not lines or tuple(cell.strip() for cell in lines[0].split("\t")) != columns:
        raise ValueError(f"{path.name} columns do not match")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) != len(columns) or not all(cell or column in may_be_empty
                                                 for column, cell in zip(columns, cells)):
            raise ValueError(f"{path.name} line {number}: wrong column count or empty cell")
        rows.append(dict(zip(columns, cells)))
    return rows


def screen_texts() -> dict:
    texts: dict = {name: load_text(name) for name in SCREEN_TEXTS}
    texts.update({name: load_lines(name) for name in SCREEN_LISTS})
    texts[MAP_BUTTONS] = map_buttons()
    texts[MAP_AROUND] = map_around()
    texts[BUBBLE_CHOICES] = bubble_choices()
    texts[DRAWER_PARTS] = id_table(DRAWER_PARTS, DRAWER_PART_IDS)
    texts[BUBBLE_CHOICES_HELP] = id_table(BUBBLE_CHOICES_HELP, BUBBLE_CHOICE_IDS)
    texts[INPUT_TO] = id_table(INPUT_TO, INPUT_TO_IDS)
    texts[ONE_WORDS] = id_table(ONE_WORDS, ONE_WORD_IDS)
    texts[INPUT_SEND] = id_table(INPUT_SEND, INPUT_SEND_IDS)
    texts[INPUT_DONE] = id_table(INPUT_DONE, INPUT_DONE_IDS)
    texts[SEAT_ICONS] = seat_icons()
    texts[NOW_STEPS] = now_steps()
    texts[NOW_LINE] = now_lines()
    texts[GUIDE] = id_table(GUIDE, GUIDE_IDS)
    texts[START_FLOW] = id_table(START_FLOW, NOW_STEP_IDS)
    texts[WAIT_SIGN] = wait_signs()
    return texts


def wait_signs() -> dict[str, dict[str, str]]:
    """{kind: {"word": the big word, "line": the small line}} (直し42).
    A row missing or one too many, or a big word missing where one is
    needed: ValueError."""
    rows = {row["ID"]: row for row in load_table(WAIT_SIGN, ("ID", "大きな言葉", "小さな1行"),
                                                 may_be_empty=("大きな言葉",))}
    if set(rows) != set(WAIT_SIGN_IDS) or any(not rows[k]["大きな言葉"] for k in rows if k not in WAIT_SIGN_NO_WORD):
        raise ValueError(f"{WAIT_SIGN}.tsv must have the rows {', '.join(WAIT_SIGN_IDS)}, each with its big word")
    return {key: {"word": rows[key]["大きな言葉"], "line": rows[key]["小さな1行"]} for key in WAIT_SIGN_IDS}


def now_steps() -> list[dict[str, str]]:
    """[{"id", "text"}] in the band's order (直し31-5)."""
    rows = {row["ID"]: row["文"] for row in load_table(NOW_STEPS, ("ID", "文"))}
    if set(rows) != set(NOW_STEP_IDS):
        raise ValueError(f"{NOW_STEPS}.tsv must have the rows {', '.join(NOW_STEP_IDS)}")
    return [{"id": key, "text": rows[key]} for key in NOW_STEP_IDS]


def now_lines() -> dict[str, dict[str, str]]:
    """{state: {"step": the step lit ("" none), "text": the one line}}. The
    line for an AI question still to answer is ai_answer_hint.txt's."""
    rows = {row["ID"]: row for row in load_table(NOW_LINE, ("ID", "段階", "文"), may_be_empty=("段階",))}
    if set(rows) != set(NOW_LINE_IDS) or any(rows[k]["段階"] not in ("",) + NOW_STEP_IDS for k in rows):
        raise ValueError(f"{NOW_LINE}.tsv must have the rows {', '.join(NOW_LINE_IDS)}, each with a known step")
    lines = {key: {"step": rows[key]["段階"], "text": rows[key]["文"]} for key in NOW_LINE_IDS}
    lines["answer_ai"] = {"step": "ask", "text": load_text(AI_ANSWER_HINT)}
    return lines


def seat_icons() -> list[list[str]]:
    """[[言葉, 絵], ...] in the table's order: a seat's title is looked at
    from the top row down, the first word in it giving its picture."""
    rows = [[row["言葉"], row["絵"]] for row in load_table(SEAT_ICONS, ("言葉", "絵"))]
    unknown = sorted({icon for _, icon in rows} - set(SEAT_ICON_NAMES))
    if unknown:
        raise ValueError(f"{SEAT_ICONS}.tsv has pictures there is no drawing for: {', '.join(unknown)}")
    return rows


def map_buttons() -> dict[str, dict[str, str]]:
    """{ID: {"text": what the button shows, "label": what it reads out}}."""
    rows = {row["ID"]: row for row in load_table(MAP_BUTTONS, ("ID", "文字", "読み上げ"), may_be_empty=("読み上げ",))}
    if set(rows) != set(MAP_BUTTON_IDS):
        raise ValueError(f"{MAP_BUTTONS}.tsv must have the rows {', '.join(MAP_BUTTON_IDS)}")
    return {key: {"text": rows[key]["文字"], "label": rows[key]["読み上げ"] or rows[key]["文字"]}
            for key in MAP_BUTTON_IDS}


def id_table(name: str, ids: tuple[str, ...]) -> dict[str, str]:
    """{ID: 文字} from a table of exactly these rows."""
    rows = {row["ID"]: row["文字"] for row in load_table(name, ("ID", "文字"))}
    if set(rows) != set(ids):
        raise ValueError(f"{name}.tsv must have the rows {', '.join(ids)}")
    return {key: rows[key] for key in ids}


def bubble_choices() -> dict[str, str]:
    """{ID: what the choice shows}, the four of them."""
    rows = {row["ID"]: row["文字"] for row in load_table(BUBBLE_CHOICES, ("ID", "文字"))}
    if set(rows) != set(BUBBLE_CHOICE_IDS):
        raise ValueError(f"{BUBBLE_CHOICES}.tsv must have the rows {', '.join(BUBBLE_CHOICE_IDS)}")
    return {key: rows[key] for key in BUBBLE_CHOICE_IDS}


def map_around() -> dict[str, dict[str, str]]:
    """{ID: {"word": its 方位, "place": what lies that way}}, the four of them."""
    rows = {row["ID"]: row for row in load_table(MAP_AROUND, ("ID", "方位", "その方向にある所"))}
    if set(rows) != set(MAP_AROUND_IDS):
        raise ValueError(f"{MAP_AROUND}.tsv must have the rows {', '.join(MAP_AROUND_IDS)}")
    return {key: {"word": rows[key]["方位"], "place": rows[key]["その方向にある所"]} for key in MAP_AROUND_IDS}
