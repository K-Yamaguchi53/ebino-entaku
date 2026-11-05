"""直し37-3: two checks for playwright's run_code against the preview server
of invented seats (adults 103, seniors 45, gone out 10, from outside 1).
tools/check_map_steps.js goes from the whole map to the seniors at their
windows one press of ＋ at a time, the AI's seat folded, and counts what
overlaps at each step: pieces, the seniors' count, the AI's seat folded and
opened. tools/check_meeting.js counts the meeting's bubbles against the
least each size must show, and their overlaps with each other, the risen
school and the AI's seat. Both read the page only."""

from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
STEPS = (TOOLS / "check_map_steps.js").read_text(encoding="utf-8")
MEETING = (TOOLS / "check_meeting.js").read_text(encoding="utf-8")
SIZES = ("[768, 1024]", "[1180, 820]", "[1366, 650]", "[1536, 760]", "[1920, 1080]")


def test_the_steps_check_presses_plus_at_the_five_sizes_and_counts_the_ai_seat_both_ways():
    for size in SIZES:
        assert size in STEPS
    assert 'await p.click("#map-zoom-in");' in STEPS and 'await p.click("#map-back");' in STEPS
    assert 'seat.classList.remove("folded");' in STEPS and "aiFolded" in STEPS and "aiOpened" in STEPS
    assert "if (got.out) break;" in STEPS  # Up to the seniors at their windows.


def test_the_meeting_check_holds_each_sizes_least_bubbles():
    assert ('const TARGET = { "1920x1080": 6, "1536x760": 6, "1366x650": 5, "1180x820": 5, "768x1024": 4 };'
            in MEETING)
    for what in ("apart", "offSchool", "offAi", "met: got.bubbles >= TARGET[size]"):
        assert what in MEETING
    assert 'reducedMotion: reduce ? "reduce" : "no-preference"' in MEETING


def test_the_checks_read_the_page_only():
    for source in (STEPS, MEETING):
        for outside in ("fetch(", "XMLHttpRequest", "sendBeacon", "https://"):
            assert outside not in source
        assert "127.0.0.1" in source
