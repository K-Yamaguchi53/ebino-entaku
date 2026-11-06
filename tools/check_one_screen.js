// 直し32-1: on the one screen the page itself never scrolls. A function for
// playwright's run_code (the screen check runs it against the preview server
// of invented seats; no model, no key):
//
//   async (page) => { ... }   with BASE set below
//
// For each of the five sizes and each of the eight moments it opens the page
// afresh, goes to that moment, and reads whether the page is taller (or
// wider) than the window. Only the drawer and long boxes may scroll inside
// themselves. It returns a table: size -> moment -> "ok" or the overflow.
// one_to_one (直し34-6): the person stood up and a question picked;
// writing_to_seat is now the box written in at one to one.
// school_zoom (直し35-6): the seniors' count pressed, the camera near the
// school with the seniors at its windows; table_out is the meeting round
// the risen school.
// one_asks (直し36-4): the person stood up, its questions offered, before
// any is pressed; with a model that puts them to the person (the preview's
// fake one), the questions put. A question button cut off is said too
// ("clipped"), and how many were put ("put N").
// 帰る前に、ひとこと (直し38): its page scrolls, as in the teacher's sample.
// For each of its moments (段1 to 段6: hk_map, hk_talk, hk_ladder,
// hk_scale, hk_keep, hk_light, hk_sheet) it reads, apart from the eight
// above, whether the page is wider than the window, and whether the button
// that goes on is reached by scrolling and not covered ("next button").
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8851/";
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const MOMENTS = ["before_question", "school_zoom", "table_out", "bubble_pressed", "writing_to_seat", "one_asks", "one_to_one", "answering_ai"];
  const HK_MOMENTS = ["hk_map", "hk_talk", "hk_ladder", "hk_scale", "hk_keep", "hk_light", "hk_sheet"];
  // The button that goes on, at each moment.
  const HK_NEXT = { hk_map: "#hk-go", hk_talk: "#hk-input button[type=submit]", hk_ladder: ".hk-options .hk-quote, .hk-picks .hk-pick, .hk-fill .hk-primary",
    hk_scale: ".hk-scale button", hk_keep: "#hk-to-light", hk_light: "#hk-to-sheet", hk_sheet: "#hk-print" };
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
          await closeFirstLook(p);
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
          if (["bubble_pressed", "writing_to_seat", "one_asks", "one_to_one"].includes(moment)) {
            await p.locator(".table-bubble:not(.unplaced):not(.ai)").first().click();
            await p.waitForSelector(".map-choices");
          }
          if (moment === "writing_to_seat") {
            await p.locator('.map-choices button[data-choice="card"]').click();
            await p.waitForTimeout(300);
            await p.focus("#question");
            await p.keyboard.type("休みの日に、店のことを考えますか？");
          }
          if (moment === "one_asks") {
            await p.locator('.map-choices button[data-choice="card"]').click();
            await p.waitForSelector(".one-asks .one-ask", { timeout: 15000 });
            await p.waitForTimeout(800);
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
          let put = "";
          if (["one_asks", "one_to_one"].includes(moment)) {
            const asks = await p.locator(".one-asks .one-ask").evaluateAll((els) => els.map((e) => ({
              cut: e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1, put: e.dataset.rephrased === "1" })));
            if (asks.some((a) => a.cut)) bad.push("clipped");
            put = ` (put ${asks.filter((a) => a.put).length})`;
          }
          row[moment] = (bad.length ? bad.join(" ") : "ok") + put;
        } catch (error) {
          row[moment] = "could not reach: " + String(error).split("\n")[0].slice(0, 120);
        }
        await context.close();
      }
      for (const moment of HK_MOMENTS) {
        const context = await browser.newContext({ viewport: { width: w, height: h },
          reducedMotion: reduce ? "reduce" : "no-preference" });
        const p = await context.newPage();
        const errors = [];
        p.on("pageerror", (error) => errors.push(String(error)));
        try {
          await toHitokoto(p);
          await goTo(p, moment);
          await p.waitForTimeout(300);
          const m = await measure(p);
          const bad = [];
          if (m.w > m.vw) bad.push(`wide ${m.w}>${m.vw}`);
          if (!(await reached(p, HK_NEXT[moment]))) bad.push("next button");
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

  // 司会（AI）から、はじめに (the teacher, 11/6): its two pages shut once
  // they show, as a student's 「はじめる」 would.
  async function closeFirstLook(p) {
    await p.waitForFunction(() => { const d = document.querySelector("#first-look"); return !d || d.open; },
      null, { timeout: 4000 }).catch(() => {});
    if (await p.evaluate(() => Boolean(document.querySelector("#first-look") && document.querySelector("#first-look").open))) {
      await p.keyboard.press("Escape");
      await p.waitForTimeout(200);
    }
  }

  // A round, one bubble marked and one opened, then 帰る前に、ひとこと (an AI's
  // question answered first, when the screen asks for one).
  async function toHitokoto(p) {
    await p.goto(BASE);
    await p.waitForSelector(".lab-pick button");
    await p.locator(".lab-pick button").first().click();
    await p.waitForTimeout(500);
    await p.keyboard.press("Escape");
    await p.waitForSelector("#table:not([hidden])");
    await closeFirstLook(p);
    await p.fill("#question", "休みの日って、みんな何してる？");
    await p.click("#ask-button");
    await p.waitForSelector(".table-bubble:not(.unplaced):not(.ai)", { timeout: 20000 });
    await p.waitForTimeout(1500);
    await p.locator(".table-bubble:not(.unplaced):not(.ai)").nth(1).click();
    await p.waitForSelector(".map-choices");
    await p.locator('.map-choices button[data-choice="mark"]').click();
    await p.waitForTimeout(300);
    await p.keyboard.press("Escape");
    await p.locator(".table-bubble:not(.unplaced):not(.ai)").nth(0).click();
    await p.waitForSelector(".map-choices");
    await p.keyboard.press("Escape");
    await p.waitForTimeout(300);
    await p.click("#to-reflect");
    if (await p.locator("#reflect-needs-answer:not([hidden])").count()) {
      const seat = p.locator(".ai-seat-card button, .ai-question").first();
      if (await seat.count()) await seat.click();
      await p.waitForTimeout(300);
      await p.keyboard.type("決めて取るほうに近い");
      await p.click("#ask-button");
      await p.waitForTimeout(2500);
      await p.click("#to-reflect");
    }
    await p.waitForSelector("#hitokoto:not([hidden]) #hk-cards .hk-said", { timeout: 15000 });
  }

  async function answer(p, text) {
    await p.waitForSelector("#hk-input input:not([disabled])", { timeout: 15000 });
    await p.fill("#hk-input input", text);
    await p.keyboard.press("Enter");
  }

  async function goTo(p, moment) {
    const at = HK_MOMENTS.indexOf(moment);
    if (at === 0) {
      await p.waitForTimeout(1500);  // The parts lit, or not.
      return;
    }
    await p.locator("#hk-cards .hk-kw, #hk-cards button.hk-said").first().click();
    await p.click("#hk-go");
    await p.waitForSelector("#hk-input input:not([disabled])", { timeout: 15000 });
    if (moment === "hk_talk") return;
    if (moment === "hk_ladder") {
      await p.locator("#hk-input .hk-pick").click();
      await p.waitForSelector("#hk-input input:not([disabled])");
      await p.locator("#hk-input .hk-pick").click();
      await p.waitForSelector(".hk-options .hk-quote, .hk-picks .hk-pick, .hk-fill input", { timeout: 15000 });
      return;
    }
    await answer(p, "雨の日も休みになるのはいいな");
    await p.waitForFunction(() => document.querySelectorAll("#hk-log .hk-card.ai:not(.waiting)").length >= 2, null, { timeout: 15000 });
    await answer(p, "部活がない日は空いたら休む");
    await p.waitForSelector(".hk-scale button", { timeout: 15000 });
    if (moment === "hk_scale") return;
    await p.locator(".hk-scale button").click();
    await p.waitForSelector("#hk-input form .quiet");
    await p.locator("#hk-input form .quiet").click();  // とばす
    await p.waitForFunction(() => [...document.querySelectorAll("#hk-log .hk-card.teacher form .quiet")].some((b) => !b.disabled));
    await p.locator("#hk-log .hk-card.teacher form .quiet:not([disabled])").last().click();  // いまはない
    await p.locator("#hk-log .hk-picks button:not([disabled])").nth(1).click();  // なかった
    await p.waitForSelector(".hk-meet select");
    await p.locator(".hk-meet .quiet").click();  // 選ばない
    // 段4 over: the main button goes on to the light (直し40-0).
    await p.waitForFunction(() => document.activeElement && document.activeElement.id === "hk-to-light");
    if (moment === "hk_keep") return;
    await p.click("#hk-to-light");
    await p.waitForSelector("#hk-light-box .hk-big", { timeout: 20000 });
    if (moment === "hk_light") return;
    await p.click("#hk-to-sheet");
    await p.waitForSelector("#hk-sheet:not([hidden]) .hk-story");
  }

  // The button is brought into view by scrolling (to the window's middle,
  // the scroll let settle), and at its middle it is itself there, not
  // something over it (the band at the top, say).
  async function reached(p, selector) {
    const node = p.locator(selector).first();
    if (!(await node.count())) return false;
    await node.evaluate((el) => el.scrollIntoView({ block: "center" }));
    await p.waitForTimeout(600);
    return node.evaluate((el) => {
      const r = el.getBoundingClientRect();
      if (!r.width || r.top < 0 || r.bottom > window.innerHeight || r.left < 0 || r.right > window.innerWidth) return false;
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return Boolean(top && (top === el || el.contains(top)));
    });
  }
}
