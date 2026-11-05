// 直し32-1: on the one screen the page itself never scrolls. A function for
// playwright's run_code (the screen check runs it against the preview server
// of invented seats; no model, no key):
//
//   async (page) => { ... }   with BASE set below
//
// For each of the five sizes and each of the seven moments it opens the page
// afresh, goes to that moment, and reads whether the page is taller (or
// wider) than the window. Only the drawer and long boxes may scroll inside
// themselves. It returns a table: size -> moment -> "ok" or the overflow.
// one_to_one (直し34-6): the person stood up and a question picked;
// writing_to_seat is now the box written in at one to one.
// school_zoom (直し35-6): the seniors' count pressed, the camera near the
// school with the seniors at its windows; table_out is the meeting round
// the risen school.
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8851/";
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const MOMENTS = ["before_question", "school_zoom", "table_out", "bubble_pressed", "writing_to_seat", "one_to_one", "answering_ai"];
  const browser = page.context().browser();
  const table = {};
  const measure = (p) => p.evaluate(() => {
    const s = document.scrollingElement;
    return { h: s.scrollHeight, vh: window.innerHeight, w: s.scrollWidth, vw: window.innerWidth };
  });
  for (const reduce of [false, true]) {
    for (const [w, h] of SIZES) {
      const row = {};
      for (const moment of MOMENTS) {
        const context = await browser.newContext({ viewport: { width: w, height: h },
          reducedMotion: reduce ? "reduce" : "no-preference" });
        const p = await context.newPage();
        const errors = [];
        p.on("pageerror", (error) => errors.push(String(error)));
        try {
          await p.goto(BASE);
          await p.waitForSelector(".lab-pick button");
          await p.locator(".lab-pick button").first().click();
          await p.waitForTimeout(500);
          await p.keyboard.press("Escape");
          await p.waitForSelector("#table:not([hidden])");
          await p.waitForTimeout(700);
          if (moment === "school_zoom") {
            await p.locator(".school-count").click();
            await p.waitForFunction(() => document.querySelector("#map-frame").classList.contains("seniors-out"), null, { timeout: 8000 });
          }
          if (!["before_question", "school_zoom"].includes(moment)) {
            await p.fill("#question", "休みの日って、みんな何してる？");
            await p.click("#ask-button");
            await p.waitForSelector(".table-bubble:not(.unplaced):not(.ai)", { timeout: 20000 });
            await p.waitForTimeout(reduce ? 600 : 1500);
          }
          if (["bubble_pressed", "writing_to_seat", "one_to_one"].includes(moment)) {
            await p.locator(".table-bubble:not(.unplaced):not(.ai)").first().click();
            await p.waitForSelector(".map-choices");
          }
          if (moment === "writing_to_seat") {
            await p.locator('.map-choices button[data-choice="card"]').click();
            await p.waitForTimeout(300);
            await p.focus("#question");
            await p.keyboard.type("休みの日に、店のことを考えますか？");
          }
          if (moment === "one_to_one") {
            await p.locator('.map-choices button[data-choice="card"]').click();
            await p.waitForSelector(".one-asks .one-ask", { timeout: 15000 });
            await p.locator(".one-asks .one-ask").first().click();
            await p.waitForTimeout(800);
          }
          if (moment === "answering_ai") {
            // The AI's seat (直し32-3) where there is one; else its card at the table.
            const seat = p.locator(".ai-seat-card button, .ai-question").first();
            if (await seat.count()) await seat.click();
            else {
              await p.locator(".table-bubble.ai:not(.unplaced)").first().click();
              await p.locator('.map-choices.ai button[data-choice="answer"]').click();
            }
            await p.waitForTimeout(300);
            await p.keyboard.type("決めて取るほうに近い");
          }
          await p.waitForTimeout(300);
          const m = await measure(p);
          const bad = [];
          if (m.h > m.vh) bad.push(`tall ${m.h}>${m.vh}`);
          if (m.w > m.vw) bad.push(`wide ${m.w}>${m.vw}`);
          if (errors.length) bad.push(`errors ${errors.length}`);
          row[moment] = bad.length ? bad.join(" ") : "ok";
        } catch (error) {
          row[moment] = "could not reach: " + String(error).split("\n")[0].slice(0, 120);
        }
        await context.close();
      }
      table[`${w}x${h}${reduce ? " reduce" : ""}`] = row;
    }
  }
  return JSON.stringify(table, null, 1);
}
