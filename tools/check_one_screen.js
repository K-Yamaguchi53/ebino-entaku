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
// one_coach (直し45 段3, in place of writing_to_seat: no box at one to
// one): a question picked and コーチ（AI）'s board over the next ones.
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
// intro (直し46, 直し48 段1: five pages): 司会（AI）から、はじめに, the cards of
// コーチ（AI） and オブザーバー（AI）: its 次へ has the keyboard (autofocus)
// and, scrolled to inside the window if need be, is there and not covered
// ("next button").
// ai_hint (直し46): a bubble pressed and its choices shut, then 「AI の問い
// はここ。押して答えよう」 up; how many of the
// AI's seat's heading and note it is over ("hint over N"), and of the AI's
// question cards ("hint over card N"); none up: "no hint".
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8851/";
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const MOMENTS = ["intro", "before_question", "school_zoom", "table_out", "bubble_pressed", "one_coach", "one_asks", "one_to_one",
    "ai_hint", "answering_ai"];
  // 直し49 段1: hk_notice, 今日の気づき with 「あった」 pressed and a line written.
  // 直し49 段2: hk_try, 次にやってみること with 試してみる pressed and a line written.
  const HK_MOMENTS = ["hk_map", "hk_talk", "hk_ladder", "hk_scale", "hk_notice", "hk_try", "hk_keep", "hk_light", "hk_sheet"];
  // The button that goes on, at each moment.
  const HK_NEXT = { hk_map: "#hk-go", hk_talk: "#hk-input button[type=submit]", hk_ladder: ".hk-options .hk-quote, .hk-picks .hk-pick, .hk-fill .hk-primary",
    hk_scale: ".hk-scale button", hk_notice: ".hk-notice-line .hk-primary", hk_try: ".hk-try-line .hk-primary", hk_keep: "#hk-to-light", hk_light: "#hk-to-sheet", hk_sheet: "#hk-print" };
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
          if (moment === "intro") {
            row[moment] = await intro(p, errors);
            await context.close();
            continue;
          }
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
          if (["bubble_pressed", "one_coach", "one_asks", "one_to_one"].includes(moment)) {
            await p.locator(".table-bubble:not(.unplaced):not(.ai)").first().click();
            await p.waitForSelector(".map-choices");
          }
          if (moment === "one_coach") {
            // 直し45 段3: no box at one to one; a question picked, then
            // コーチ（AI）'s board over the next ones (when one comes).
            await p.locator('.map-choices button[data-choice="card"]').click();
            await p.waitForSelector(".one-asks .one-ask", { timeout: 15000 });
            await p.locator(".one-asks .one-ask:not(.one-finish)").first().click();
            await p.waitForSelector(".one-coach:not(.waiting)", { timeout: 15000 }).catch(() => {});
            await p.waitForTimeout(500);
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
          let hint = "";
          if (moment === "ai_hint") {
            // It comes once a bubble was pressed and its choices shut.
            await p.locator(".table-bubble:not(.unplaced):not(.ai)").first().click();
            await p.waitForSelector(".map-choices");
            await p.keyboard.press("Escape");
            await p.waitForFunction(() => { const g = document.querySelector("#guide");
              return g && !g.hidden && g.dataset.state === "answer_ai"; }, null, { timeout: 20000 }).catch(() => {});
            await p.waitForTimeout(500);
            const over = await p.evaluate(() => {
              const g = document.querySelector("#guide");
              if (!g || g.hidden || g.dataset.state !== "answer_ai") return null;
              const a = g.getBoundingClientRect();
              const hits = (nodes) => nodes.filter((n) => n && n.getClientRects().length).map((n) => n.getBoundingClientRect())
                .filter((b) => b.width && a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom).length;
              // 直し48 段2: no heading nor note; the robots and their names instead.
              return { head: hits([...document.querySelectorAll("#ai-seat-cards .robot, #ai-seat-cards .who-name"),
                document.querySelector("#now-line"), document.querySelector(".map-controls")]),
                cards: hits([...document.querySelectorAll("#ai-seat-cards .ai-question")]) };
            });
            hint = !over ? "no hint" : [over.head ? `hint over ${over.head}` : "", over.cards ? `hint over card ${over.cards}` : ""]
              .filter(Boolean).join(" ");
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
          if (hint) bad.push(hint);
          // 直し48 段2: コーチ（AI）'s board over the map by the person: inside
          // the map's frame, over neither the person's words nor the questions.
          if (moment === "one_coach") {
            const c = await p.evaluate(() => {
              const box = (q) => { const n = document.querySelector(q); return n ? n.getBoundingClientRect() : null; };
              const b = box(".one-coach"), f = box("#map-overlay");
              if (!b) return null;
              const over = (o) => Boolean(o && b.left < o.right && o.left < b.right && b.top < o.bottom && o.top < b.bottom);
              return { words: over(box(".one-bubble")), asks: over(box(".one-asks")),
                out: b.left < f.left - 1 || b.top < f.top - 1 || b.right > f.right + 1 || b.bottom > f.bottom + 1 };
            });
            if (!c) bad.push("no coach");
            else {
              if (c.words) bad.push("coach over words");
              if (c.asks) bad.push("coach over questions");
              if (c.out) bad.push("coach out of the map");
            }
          }
          let put = "";
          if (["one_asks", "one_to_one", "one_coach"].includes(moment)) {
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

  // 直し46, 直し48 段1: 司会（AI）から、はじめに, page by page (five). On
  // each: 次へ in the window without scrolling and not covered ("next N"),
  // the page not wider than the dialog ("wide page N"), the dots saying
  // which page; the cards of コーチ（AI） and オブザーバー（AI） on the
  // third ("cards N"); 戻る back once from the last; the last button shuts it.
  async function intro(p, errors) {
    await p.goto(BASE);
    await p.waitForSelector(".lab-pick button");
    await p.locator(".lab-pick button").first().click();
    await p.waitForFunction(() => { const d = document.querySelector("#first-look"); return d && d.open; }, null, { timeout: 15000 });
    await p.waitForTimeout(600);
    const bad = [];
    const m = await measure(p);
    if (m.h > m.vh) bad.push(`tall ${m.h}>${m.vh}`);
    if (m.w > m.vw) bad.push(`wide ${m.w}>${m.vw}`);
    if (!(await p.evaluate(() => document.activeElement && document.activeElement.id === "first-look-next"))) bad.push("not focused");
    const pages = await p.locator("#first-look-dots li").count();
    if (pages !== 5) bad.push(`pages ${pages}`);
    for (let n = 0; n < pages; n++) {
      const seen = await p.evaluate((n) => {
        const page = [...document.querySelectorAll(".first-look-page")].filter((s) => !s.hidden);
        const dots = [...document.querySelectorAll("#first-look-dots li")];
        const next = document.querySelector("#first-look-next").getBoundingClientRect();
        const top = document.elementFromPoint(next.left + next.width / 2, next.top + next.height / 2);
        return { one: page.length === 1, dot: dots.findIndex((d) => d.classList.contains("here")) === n,
          next: next.top >= 0 && next.bottom <= window.innerHeight && next.left >= 0 && next.right <= window.innerWidth
            && Boolean(top && top.closest("#first-look-next")),
          wide: page[0] && page[0].scrollWidth > page[0].clientWidth + 1,
          cards: document.querySelectorAll("#first-look-roles:not([hidden]) .role-card").length,
          page: page[0] && page[0].dataset.page };
      }, n);
      if (!seen.one || !seen.dot) bad.push(`page ${n + 1} not alone`);
      if (!seen.next) bad.push(`next ${n + 1}`);
      if (seen.wide) bad.push(`wide page ${n + 1}`);
      if (seen.page === "roles" && seen.cards !== 2) bad.push(`cards ${seen.cards}`);
      if (n < pages - 1) await p.click("#first-look-next");
    }
    await p.click("#first-look-back");
    if (!(await p.evaluate(() => !document.querySelector("#first-look-inside").hidden))) bad.push("back");
    await p.click("#first-look-next");
    await p.click("#first-look-next");
    if (await p.evaluate(() => document.querySelector("#first-look").open)) bad.push("not shut");
    if (errors.length) bad.push(`errors ${errors.length}`);
    return bad.length ? bad.join(" ") : "ok";
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
    // 直し45 段5: the trail and its marks first; one mark, then 次へ.
    await p.waitForSelector("#hitokoto:not([hidden]) .hk-marks .hk-mark, #hitokoto:not([hidden]) #hk-cards .hk-said", { timeout: 15000 });
    if (await p.locator(".hk-marks .hk-mark").count()) {
      await p.locator(".hk-marks .hk-mark").first().click();
      await p.locator(".hk-marks .hk-primary").click();
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
    // 直し49 段1: 今日の気づき, 「あった」 and a line.
    await p.waitForSelector(".hk-notice .hk-pick:not([disabled])");
    await p.locator(".hk-notice .hk-pick").first().click();
    await p.fill(".hk-notice-line input", "畑の人は雨の日も休みじゃないと、はじめて知った");
    if (moment === "hk_notice") return;
    await p.locator(".hk-notice-line .hk-primary").click();
    await p.waitForFunction(() => [...document.querySelectorAll("#hk-log .hk-card.teacher form .quiet")].some((b) => !b.disabled));
    await p.locator("#hk-log .hk-card.teacher form .quiet:not([disabled])").last().click();  // いまはない
    await p.locator("#hk-log .hk-picks button:not([disabled])").nth(1).click();  // なかった
    // 直し49 段2: 次にやってみること, 試してみる and a line.
    await p.waitForSelector(".hk-try .hk-pick:not([disabled])");
    await p.locator('.hk-try .hk-pick[data-answer="try"]').click();
    await p.fill(".hk-try-line input", "雨の日の畑を、一回見に行ってみる");
    if (moment === "hk_try") return;
    await p.locator(".hk-try-line .hk-primary").click();
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
