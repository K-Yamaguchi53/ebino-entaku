"""The question card in the seat list (直し25-4): opened, it goes right under
its seat's line of seats at the list's full width, so the seat keeps its
size and no hole opens beside it; it says whose seat it is for in the seat
list's own words; one is open at a time."""

import re

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def _function(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n}\n", start) + 3]


def test_the_seat_lists_card_goes_under_its_line_and_the_others_stay_where_they_were():
    not_asked = _function("renderNotAsked")
    assert "cardEntry(seat.seat_id, renderSeats, (form, open) => putUnderLine(seat, form, open))" in not_asked
    entry = _function("cardEntry")
    assert "put = (form, open) => open.replaceWith(form)" in entry  # The other cards: in the button's place, as before.
    body = entry[entry.index("{\n"):]  # After the line that names it.
    assert "put(form, open);" in body and "open.replaceWith(form)" not in body
    # The card holds the student's words only: the box stays empty (SPEC 2-2).
    assert ".value =" not in entry


def test_it_goes_after_the_last_seat_on_its_line_names_its_seat_and_closes_another():
    put = _function("putUnderLine")
    assert "next.offsetTop === node.offsetTop" in put and "last.after(form)" in put
    assert 'el("p", { class: "card-for", text: [seat.title, seat.detail].filter(Boolean).join("　") })' in put
    assert not re.search(r"seat\.(company|display_name|name)\b", put)
    assert 'querySelectorAll("#seat-list .card-form")' in put and "other.closeCard()" in put
    assert "open.hidden = true" in put and "open.hidden = false" in put
    assert ".seat-row > .card-form { flex: 1 0 100%; max-width: none;" in CSS
    rule = re.search(r"\.card-form \.card-for \{[^}]*\}", CSS).group(0)
    assert "#" not in rule and "var(--gothic)" in rule
