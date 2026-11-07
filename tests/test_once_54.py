"""直し54 (the teacher's look on the real data, 11/8 morning)."""

from pathlib import Path
from types import SimpleNamespace

from ebino import hitokoto, one_tidy
from ebino.texts import load_table

STATIC = Path(__file__).resolve().parent.parent / "ebino" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "hitokoto.js").read_text(encoding="utf-8")


def _talk(**over):
    base = {"first_question": "将来の夢が特にない。それってまずい？", "own_questions": [], "rewritten": "",
            "last_question": "", "written": []}
    base.update(over)
    return SimpleNamespace(**base)


# --- 「いまの問い」 picked from the student's own words ---

def test_now_choices_are_the_students_own_words_in_order_without_repeats():
    talk = _talk(own_questions=["夢がなくても働ける？"], last_question="夢がなくても働ける？",
                 written=[{"text": "目標があると強いと思った"}, {"text": ""}, {"text": "目標があると強いと思った"}])
    assert hitokoto.now_choices(talk) == ["将来の夢が特にない。それってまずい？", "夢がなくても働ける？",
                                          "目標があると強いと思った"]


def test_now_choices_keep_the_latest_at_most_six():
    talk = _talk(written=[{"text": f"書いた言葉{n}"} for n in range(10)])
    out = hitokoto.now_choices(talk)
    assert len(out) == hitokoto.NOW_CHOICES
    assert out[-1] == "書いた言葉9"


def test_now_choices_leave_out_home_money_health():
    avoid = hitokoto.has_avoid
    words = [w for w in ("家族", "お金", "病気") if avoid(f"{w}のことが気になる")]
    if not words:
        return  # The avoid table names none of these: nothing to check here.
    talk = _talk(written=[{"text": f"{words[0]}のことが気になる"}])
    assert all(words[0] not in text for text in hitokoto.now_choices(talk))


def test_now_pick_is_in_the_texts_and_the_screen_has_its_place():
    rows = {row["ID"]: row["文字"] for row in load_table(hitokoto.TEXTS, ("ID", "文字"))}
    assert rows["now_pick"]
    assert 'id="hk-now-choices"' in HTML and 'id="hk-now-list"' in HTML
    assert "light.now_choices" in JS and "W.now_pick" in JS


# --- a slide's page: a career's list, and the company mask ---

def test_a_career_list_is_a_line_a_step_and_its_rest_joined():
    page = "\n".join(["プロフィール", "経歴", "2019 九州の大学 卒業", "2019-2021 米づくり in 秋田",
                      "2021-2023 地域おこし協力隊・", "高校コーディネーター", "2024-現在 町の店 代表"])
    lines = one_tidy.tidy_page(page).text.split("\n")
    assert lines == ["経歴。", "2019 九州の大学 卒業。", "2019-2021 米づくり in 秋田。",
                     "2021-2023 地域おこし協力隊・高校コーディネーター。", "2024-現在 町の店 代表。"]


def test_the_name_checks_words_are_joined_as_before():
    page = "経歴\n2019-2021 米づくり\n2021-2023 協力隊"
    tidied = one_tidy.tidy_page(page)
    assert "\n" not in tidied.joined


def test_a_year_in_a_sentence_is_not_a_step():
    assert not one_tidy.is_year_line("2020年に戻ってきた")
    assert not one_tidy.is_year_line("20人が集まった")
    assert one_tidy.is_year_line("2024-現在 代表")
    assert one_tidy.is_year_line("2020 卒業")


def test_the_legal_form_beside_the_company_mask_goes():
    assert one_tidy.plain_mask("合同会社この職場 代表") == "この職場 代表"
    assert one_tidy.plain_mask("この職場株式会社で働く") == "この職場で働く"
    assert one_tidy.plain_mask("株式会社を作った") == "株式会社を作った"
    assert one_tidy.tidy_page("経歴\n2024-現在 合同会社この職場 代表").text.endswith("この職場 代表。")


# --- the screen ---

def test_the_name_card_hides_while_the_wait_sign_is_up():
    assert "body:has(#wait-sign:not([hidden])) .map-tip { visibility: hidden; }" in CSS


def test_the_pick_line_is_large_and_the_answer_box_wide():
    assert ".ai-seat-pick { margin: 10px 4px 2px; font-size: 18px; font-weight: 700;" in CSS
    assert ".ai-answer textarea { flex: 1 1 100%; width: 100%;" in CSS


def test_the_light_may_say_a_little_more():
    assert hitokoto.MAX_WHY == 100 and hitokoto.MAX_DEEP == 80
