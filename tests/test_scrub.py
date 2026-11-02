import pytest

from ebino.ingest.scrub import (
    company_terms,
    mask_terms,
    name_parts,
    normalize_for_match,
    remove_address,
    remove_money,
    remove_phone,
)


@pytest.mark.parametrize(
    "number",
    [
        "0984-00-0000",
        "０９８４－００－００００",
        "0984(00)0000",
        "(0984)00-0000",
        "09840000000",
        "090-0000-0000",
        "0984 00 0000",
    ],
)
def test_phone_forms_are_removed(number):
    assert remove_phone(f"連絡は{number}まで") == "連絡はまで"


@pytest.mark.parametrize("text", ["電話 00-0000 です", "TEL:00-0000 です", "℡００－００００ です"])
def test_labelled_local_number_is_removed(text):
    assert "0000" not in remove_phone(text)
    assert "００００" not in remove_phone(text)


@pytest.mark.parametrize("text", ["2026-11-02に開店", "1998年に戻った", "写真は12枚", "従業員は3人"])
def test_ordinary_numbers_stay(text):
    assert remove_phone(text) == text


@pytest.mark.parametrize(
    "text, gone",
    [
        ("大字架空町123番地にある", "123"),
        ("架空町１２３番地４にある", "１２３"),
        ("架空町1丁目2番3号にある", "2番3"),
        ("架空町123-4にある", "123-4"),
        ("百二十三番地にある", "百二十三"),
    ],
)
def test_address_numbers_are_removed(text, gone):
    assert gone not in remove_address(text)


@pytest.mark.parametrize("text", ["一番好きな仕事", "3番目の店", "朝の8時から", "2位の答え"])
def test_ordinary_words_are_not_addresses(text):
    assert remove_address(text) == text


@pytest.mark.parametrize("text", ["研修に30万円かかった", "約300,000円", "１５万円", "三十万円", "500ドル"])
def test_money_is_removed(text):
    cleaned = remove_money(text)
    assert "円" not in cleaned and "ドル" not in cleaned


def test_name_parts_cover_family_and_given_names():
    assert set(name_parts("山川 太郎").terms) == {"山川太郎", "山川", "太郎"}
    assert set(name_parts("山川　太郎").terms) == {"山川太郎", "山川", "太郎"}


def test_unsplit_name_masks_plausible_pieces_and_is_flagged():
    parts = name_parts("山川太郎")
    assert parts.unsplit
    assert {"山川", "太郎"} <= set(parts.terms)


def test_empty_name_gives_no_terms():
    assert name_parts("  ").terms == ()


@pytest.mark.parametrize(
    "text",
    ["山川太郎さんの店", "山川 太郎の店", "山　川　太　郎の店", "山川さんの店", "太郎の店", "山川氏の店"],
)
def test_name_variants_become_the_mask(text):
    masked = mask_terms(text, name_parts("山川 太郎").terms, "この方")
    assert masked == "この方の店"


def test_single_character_name_does_not_eat_words():
    terms = name_parts("林 誠").terms
    assert mask_terms("林業と誠実さ", terms, "この方") == "林業と誠実さ"
    assert mask_terms("誠さんと、林は話す", terms, "この方") == "この方と、この方は話す"


def test_company_short_form_is_included():
    assert set(company_terms("有限会社はるかぜ理容")) == {"有限会社はるかぜ理容", "はるかぜ理容"}
    assert company_terms("") == []


def test_normalize_unifies_width_and_space():
    assert normalize_for_match("Ａ Ｂ　Ｃ\n１") == "ABC1"
