"""The model gate (SPEC 14-3, 14-39, 14-51). Every name here is invented."""

import pytest
from fake_client import FakeClient, text_response

from conftest import make_seat
from ebino.gate import (
    KIND_DISPLAY_NAME,
    KIND_MASK_WORD,
    Gate,
    GateError,
    ModelUnavailable,
    NameList,
    json_answer,
    json_request,
    load_allowed,
)
from ebino.ingest.masks import SeatMasks

SEATS = [
    make_seat(seat_id="S01", display_name="山川さん"),
    make_seat(seat_id="S02", display_name="谷さん・森さん"),  # 森 is under two chars.
    make_seat(seat_id="P01", kind="poster", company="", display_name="先輩"),
    make_seat(seat_id="C01", kind="cross", company="", display_name="１年生"),
]
MASKS = {"S01": SeatMasks(words=("谷口師匠",), companies=("はるかぜ",)), "C01": SeatMasks(words=("川辺三郎",))}


def names(allowed=frozenset()):
    return NameList.build(SEATS, MASKS, allowed)


def test_names_are_display_names_and_mask_words_only():
    assert names().terms == {"山川": KIND_DISPLAY_NAME, "谷口師匠": KIND_MASK_WORD, "川辺三郎": KIND_MASK_WORD}


def test_company_names_and_label_words_are_not_names():
    assert names().hits("はるかぜ理容で、先輩と1年生が架空農園の話をした。") == []


def test_names_are_found_after_normalizing():
    assert names().hits("ｶﾜﾍﾞではなく 川 辺 三 郎 さん") == ["川辺三郎"]


def test_words_a_person_checked_are_let_through():
    assert names({"山川"}).hits("山川の河原で遊んだ。") == []
    assert names().hits("山川の河原で遊んだ。") == ["山川"]


def test_a_name_inside_a_let_through_string_passes_but_not_outside_it():
    # SPEC 14-52: the line is the string around the name, not the name.
    allowed = names({"山川公園"})
    assert allowed.hits("山川公園で遊んだ。") == []
    assert allowed.hits("山 川 公 園で遊んだ。") == []  # Matched after normalizing.
    assert allowed.hits("山川公園で山川さんと遊んだ。") == ["山川"]
    assert allowed.hits("山川で遊んだ。") == ["山川"]


def test_text_on_each_side_of_a_let_through_string_does_not_join_up():
    # 谷 + [口公園] + 師匠 must not become 谷口師匠 once the string is taken out.
    assert names({"口公園"}).hits("谷口公園師匠") == []
    assert names({"山川公園"}).hits("谷口師匠と山川公園") == ["谷口師匠"]


def test_gate_ok_file_is_read_and_missing_means_none(tmp_path):
    assert load_allowed(tmp_path) == set()
    (tmp_path / "gate_ok.tsv").write_text("山川\n\n 谷口 \n", encoding="utf-8")
    assert load_allowed(tmp_path) == {"山川", "谷口"}


def request_with(text):
    return json_request("moderator", "指示の文。", text, {"type": "object"})


def test_a_request_with_a_name_is_never_sent():
    client = FakeClient([text_response({})])
    gate = Gate(client, names())
    with pytest.raises(GateError) as error:
        gate.send("moderator", request_with("山川さんは店に立つ。"))
    assert str(error.value) == "name_in_request"
    assert "山川" not in str(error.value)
    assert client.requests == []
    assert (gate.sent, gate.stopped) == (0, 1)


def test_names_in_tool_results_are_caught_too():
    client = FakeClient([text_response({})])
    request = request_with("問い")
    request["messages"].append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "谷口師匠に習った。"},
    ]})
    with pytest.raises(GateError):
        Gate(client, names()).send("librarian", request)
    assert client.requests == []


def test_a_clean_request_is_sent_and_answered():
    client = FakeClient([text_response({"ok": True})])
    sent = []
    gate = Gate(client, names(), on_send=lambda role, request: sent.append(role))
    response = gate.send("moderator", request_with("この方は店に立つ。"))
    assert json_answer(response) == {"ok": True}
    assert sent == ["moderator"]
    request = client.requests[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert request["output_config"]["effort"] == "medium"
    assert "fallbacks" not in request and "betas" not in request  # SPEC 14-51.


@pytest.mark.parametrize(
    "answer, reason",
    [
        (text_response("", stop_reason="refusal"), "refusal"),
        (text_response('{"a"', stop_reason="max_tokens"), "max_tokens"),
        (RuntimeError("この方は店に立つ。"), "api_error:RuntimeError"),
    ],
)
def test_no_usable_answer_gives_a_reason_code_only(answer, reason):
    gate = Gate(FakeClient([answer]), names())
    with pytest.raises(ModelUnavailable) as error:
        gate.send("moderator", request_with("問い"))
    assert str(error.value) == reason


def test_an_answer_that_is_not_json_is_unavailable():
    with pytest.raises(ModelUnavailable, match="bad_output"):
        json_answer(text_response("はい、わかりました。"))
