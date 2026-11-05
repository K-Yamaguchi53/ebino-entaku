// 直し37-3: the meeting as it comes out, at the five sizes, with motion and
// with motion reduced. A function for playwright's run_code against the
// preview server of invented seats (no model, no key):
//
//   async (page) => { ... }   with BASE set below
//
// It asks one question, waits for the meeting round the risen school, and
// counts the seats' bubbles placed (not the AI's: it is in its own seat),
// against the least each size must show (TARGET), and what overlaps: two
// bubbles, a bubble and the risen school, a bubble and the AI's seat. It
// returns a table: size -> { bubbles, target, met, apart, offSchool, offAi }.
// Nothing is sent anywhere.
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8851/";
  const TARGET = { "1920x1080": 6, "1536x760": 6, "1366x650": 5, "1180x820": 5, "768x1024": 4 };
  const browser = page.context().browser();
  const table = {};
  for (const reduce of [false, true]) {
    for (const size of Object.keys(TARGET)) {
      const [w, h] = size.split("x").map(Number);
      const context = await browser.newContext({ viewport: { width: w, height: h }, reducedMotion: reduce ? "reduce" : "no-preference" });
      const p = await context.newPage();
      try {
        await p.goto(BASE);
        await p.waitForSelector(".lab-pick button");
        await p.locator(".lab-pick button").first().click();
        await p.waitForTimeout(500);
        await p.keyboard.press("Escape");
        await p.waitForSelector("#table:not([hidden])");
        await p.fill("#question", "休みの日って、みんな何してる？");
        await p.click("#ask-button");
        await p.waitForSelector(".table-bubble:not(.unplaced):not(.ai)", { timeout: 20000 });
        await p.waitForTimeout(reduce ? 1200 : 4500);
        const got = await p.evaluate(() => {
          const shown = (n) => n.getClientRects().length && getComputedStyle(n).visibility !== "hidden";
          const meet = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
          const bubbles = [...document.querySelectorAll(".table-bubble:not(.unplaced):not(.ai)")].filter(shown).map((n) => n.getBoundingClientRect());
          let apart = 0;
          for (let i = 0; i < bubbles.length; i++) for (let j = i + 1; j < bubbles.length; j++) if (meet(bubbles[i], bubbles[j])) apart++;
          const school = [...document.querySelectorAll(".risen-school")].filter(shown).map((n) => n.getBoundingClientRect());
          const seat = document.querySelector("#ai-seat");
          const ai = seat && shown(seat) && !seat.hidden ? seat.getBoundingClientRect() : null;
          const s = document.scrollingElement;
          return { bubbles: bubbles.length, apart, offSchool: bubbles.filter((b) => school.some((r) => meet(b, r))).length,
            offAi: ai ? bubbles.filter((b) => meet(b, ai)).length : 0, aiFolded: Boolean(seat && seat.classList.contains("folded")),
            scrolls: s.scrollHeight > window.innerHeight || s.scrollWidth > window.innerWidth };
        });
        table[`${size}${reduce ? " reduce" : ""}`] = { ...got, target: TARGET[size], met: got.bubbles >= TARGET[size] };
      } catch (error) {
        table[`${size}${reduce ? " reduce" : ""}`] = { error: String(error).split("\n")[0].slice(0, 120) };
      }
      await context.close();
    }
  }
  return JSON.stringify(table);
}
