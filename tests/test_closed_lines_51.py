"""直し51 段1: on 帰る前に、ひとこと's talk, a question answered, skipped or
picked past keeps no line to write, nor its 送る・とばす: the form goes, the
student's words stay in their own card under it, and what was picked stays
pressed no more with its ✓. Only the question waiting at the foot has a line.
The same for the questions from before 直し49 (the way, the lesson, the
blank to fill, the listener's)."""

from ebino import app as app_module

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CHECK = (app_module.STATIC_DIR.parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")


def _inner(name):
    start = HK.index(f"  function {name}(")
    if HK.find(f"  async function {name}(") >= 0:
        start = min(start, HK.index(f"  async function {name}("))
    end = HK.index("\n  }\n", start)
    return HK[start:end]


def _block(name):
    """A function down to the next one at the same depth."""
    start = HK.index(f"function {name}(")
    following = [HK.find(mark, start + 1) for mark in ("\n  function ", "\n  async function ", "\n  // ---")]
    return HK[start:min(i for i in following if i > 0)]


def test_settle_takes_the_form_away_and_nothing_else():
    settle = _inner("settle")
    assert 'if (box && box.matches("form")) box.remove();' in settle
    # Only a form goes: the answers to pick (a div) stay, with the one picked.
    assert settle.count("remove()") == 1


def test_the_line_under_the_answers_goes_once_sent_or_skipped():
    # 今日の気づき・次にやってみること: sent with a line, or 「とばす」 (the same go).
    ask = _block("choiceWithLine")
    go = ask[ask.index("const go = async"):ask.index("const pass =")]
    assert go.index("settle(form);") < go.index('say("me", label')
    # A send that failed or a name in it: the line stays to write again.
    assert go.index("unlock(box);") < go.index("settle(form);")
    assert go.count("settle(form);") == 1


def test_an_optional_line_goes_in_a_card_too():
    # The way (例：農業もおもしろいかも), the lesson, the scale's next one: before, a line in a card stayed.
    box = _block("lineBox")
    assert "settle(form);" in box and "if (!card) form.remove();" not in box
    go = box[box.index("const go = async"):]
    assert go.index('if (result.status === "ask_again")') < go.index("settle(form);")


def test_the_blank_to_fill_goes_and_the_two_to_pick_stay():
    step = _block("ladderStep")
    assert step.index('if (result.status === "ask_again")') < step.index("settle(box);") < step.index('say("me", shown)')
    assert 'ladderStep("fill", { text }, `${result.before}${text}${result.after}`, form);' in HK
    assert 'ladderStep("ladder", { choice: option.index }, option.title, box);' in HK  # A div: it stays.


def test_the_listeners_line_is_under_the_talk_and_cleared_before_the_next():
    # answerBox's form is in #hk-input, emptied by clearInput() when the next comes.
    assert '$("hk-input").append(form);' in _block("answerBox")
    nxt = _block("next")
    assert nxt.index("clearInput();") < nxt.index('if (result.next === "ask")')


def test_picked_answers_keep_their_mark_and_cannot_be_pressed():
    lock = _inner("lock")
    assert "node.disabled = true;" in lock and 'chosen.classList.add("hk-chosen");' in lock


def test_the_screen_check_counts_lines_left_open_or_shut():
    assert "closed line ${lines.shut}" in CHECK and "lines ${lines.open}" in CHECK
    assert '#hk-talk input[type=text], #hk-talk textarea' in CHECK
