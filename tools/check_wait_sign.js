// 直し42: the sign in the middle of the map while the model is waited for.
// A function for playwright's run_code, against the preview server of
// invented seats whose fake model can be held at a step (no model, no key):
//
//   async (page) => { ... }   with BASE set below
//
// The preview holds /api/ask while its switch names a step (POST
// /api/_preview {"hold": "find" | "moderate" | ""}; the preview alone has
// it). For each of the five sizes, motion on and reduced, it asks a first
// question and holds it at find, then at moderate; then lets it go, and asks
// a second question with the first round's table out. At each held moment
// it reads: whether the page is taller or wider than the window (as
// check_one_screen.js does), the sign's words, whether the sign is inside
// the map's frame, and whether it covers the question box, 「聞く」, a bubble
// or the table's cards, the drawer or the AI's seat; with the words of
// tools/check_word_breaks.js given (globalThis.EBINO_WORD_BREAKS, its
// source), whether the sign's words break inside a word. Between the two
// questions it watches for 「集合中」 while the seats fly (motion on only)
// and says whether its dots move. With globalThis.EBINO_SHOTS (a folder),
// it saves the pictures named in SHOTS there. It returns a table.
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8852/";
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const SHOTS = { "find 1366x650": "42_wait_find_1366x650.png", "moderate 1920x1080": "42_wait_moderate_1920x1080.png",
    "gather 1920x1080": "42_gather_1920x1080.png" };
  const COVER = ["#question", "#ask-button", ".map-bubble", ".table-bubble", ".table-label", ".drawer:not([hidden])", "#ai-seat"];
  const shots = globalThis.EBINO_SHOTS || "";
  const breaks = globalThis.EBINO_WORD_BREAKS || "";
  const browser = page.context().browser();
  const out = {};
  const hold = (p, step) => p.evaluate((step) => fetch("/api/_preview", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ hold: step }) }).then((r) => r.json()), step);
  const read = (p, COVER) => p.evaluate((COVER) => {
    const s = document.scrollingElement;
    const sign = document.getElementById("wait-sign");
    const box = (node) => node.getBoundingClientRect();
    const hit = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
    const seen = { overflow: s.scrollHeight > window.innerHeight + 1 || s.scrollWidth > window.innerWidth + 1 ? `${s.scrollWidth}x${s.scrollHeight}` : "ok" };
    if (sign.hidden || !sign.getClientRects().length) return Object.assign(seen, { sign: null });
    const r = box(sign), frame = box(document.getElementById("map-frame"));
    seen.sign = `${document.getElementById("wait-word").textContent}／${document.getElementById("wait-line").textContent}`;
    seen.inFrame = r.left >= frame.left && r.right <= frame.right && r.top >= frame.top && r.bottom <= frame.bottom;
    seen.centre = [Math.round((r.left + r.right) / 2 - (frame.left + frame.right) / 2), Math.round((r.top + r.bottom) / 2 - (frame.top + frame.bottom) / 2)];
    seen.covers = [];
    for (const selector of COVER) {
      for (const node of document.querySelectorAll(selector)) {
        if (node.getClientRects().length && getComputedStyle(node).visibility !== "hidden" && hit(r, box(node))) seen.covers.push(selector);
      }
    }
    seen.pressable = getComputedStyle(sign).pointerEvents;
    seen.busy = document.getElementById("map").getAttribute("aria-busy") || "";
    seen.moving = sign.getAnimations({ subtree: true }).length;
    return seen;
  }, COVER);
  for (const reduce of [false, true]) {
    for (const [w, h] of SIZES) {
      const size = `${w}x${h}`;
      const row = {};
      const context = await browser.newContext({ viewport: { width: w, height: h }, reducedMotion: reduce ? "reduce" : "no-preference" });
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
        for (const round of [1, 2]) {
          await hold(p, "find");
          await p.fill("#question", round === 1 ? "休みの日って、みんな何してる？" : "休みを決めると、何が変わる？");
          await p.click("#ask-button");
          await p.waitForTimeout(300);
          row[`r${round} 0.3s`] = (await read(p, COVER)).sign;
          await p.waitForTimeout(900);
          row[`r${round} find`] = await read(p, COVER);
          if (breaks && row[`r${round} find`].sign) row[`r${round} find`].breaks = await p.evaluate(`(${breaks})([".wait-sign"])`);
          if (round === 1 && shots && !reduce && SHOTS[`find ${size}`]) await p.screenshot({ path: `${shots}/${SHOTS[`find ${size}`]}` });
          await hold(p, "moderate");
          await p.waitForTimeout(1200);
          row[`r${round} moderate`] = await read(p, COVER);
          if (round === 1 && shots && !reduce && SHOTS[`moderate ${size}`]) await p.screenshot({ path: `${shots}/${SHOTS[`moderate ${size}`]}` });
          await hold(p, "");
          // The answer in: the sign goes; with motion on, 「集合中」 while the seats fly.
          await p.waitForTimeout(300);  // The last round's table goes first.
          let gather = null;
          const until = Date.now() + 9000;
          while (Date.now() < until) {
            const now = await read(p, COVER);
            if (now.sign && now.sign.startsWith("集合中")) {
              gather = now;
              if (round === 1 && shots && !reduce && SHOTS[`gather ${size}`]) await p.screenshot({ path: `${shots}/${SHOTS[`gather ${size}`]}` });
              break;
            }
            if (await p.locator("#map-overlay .table-label").count()) break;
            await p.waitForTimeout(60);
          }
          row[`r${round} gather`] = gather;
          await p.waitForSelector("#map-overlay .table-label", { timeout: 15000, state: "attached" }).catch(() => null);
          await p.waitForTimeout(800);
          row[`r${round} after`] = (await read(p, COVER)).sign;
        }
      } catch (error) {
        row.error = String(error).slice(0, 200);
      } finally {
        await hold(p, "").catch(() => null);
        row.errors = errors;
        await context.close();
      }
      out[`${reduce ? "reduce" : "motion"} ${size}`] = row;
    }
  }
  return out;
}
