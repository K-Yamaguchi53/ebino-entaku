// 直し40-1: the split's heading pressed where it is seen. A function for
// playwright's run_code against the preview servers of invented seats (no
// model, no key): BASES.picture draws the round table (the heading under the
// map, #map-heading, on a map TAG_ON_MAP wide or wider), BASES.flat the flat
// map (the heading as a tag over the map, .split-tag).
//
//   async (page) => { ... }
//
// For each of the five sizes and each map it asks one question, waits for
// the round to be read, and reads: where the heading is and how large; what
// pressable it covers (a seat's point or chair, a bubble, a seat's label, the
// AI's seat, the seniors' count); whether the page scrolls; whether the
// keyboard reaches the heading by Tab (and in how many presses) and Enter
// puts it in the question box with the one line over it; and, that line in,
// the map a little lower, what the heading covers then. It returns a table:
// map -> size -> counts.
// Nothing is sent anywhere but the preview server.
async (page) => {
  const BASES = globalThis.EBINO_BASES || { picture: "http://127.0.0.1:8851/", flat: "http://127.0.0.1:8853/" };
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const browser = page.context().browser();
  const table = {}, missing = [];
  for (const [map, base] of Object.entries(BASES)) {
    table[map] = {};
    for (const [w, h] of SIZES) {
      const context = await browser.newContext({ viewport: { width: w, height: h }, reducedMotion: "reduce" });
      const p = await context.newPage();
      const errors = [];
      p.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));
      p.on("response", (r) => { if (r.status() === 404) missing.push(r.url()); });
      let row;
      try {
        await p.goto(base);
        await p.waitForSelector(".lab-pick button");
        await p.locator(".lab-pick button").first().click();
        await p.waitForTimeout(500);
        await p.keyboard.press("Escape");
        await p.waitForSelector("#table:not([hidden])");
        await p.fill("#question", "休みの日って、みんな何してる？");
        await p.click("#ask-button");
        await p.waitForFunction(() => document.querySelector(".split-tag:not(.unplaced), #map-heading:not(:empty)")
          || document.querySelector(".table-bubble:not(.unplaced)"), null, { timeout: 20000 });
        await p.waitForTimeout(1800);
        const read = () => p.evaluate(() => {
          const shown = (n) => n.getClientRects().length && getComputedStyle(n).visibility !== "hidden" && !n.classList.contains("unplaced");
          const box = (n) => n.getBoundingClientRect();
          const meet = (a, b) => a.left < b.right - 0.5 && a.right > b.left + 0.5 && a.top < b.bottom - 0.5 && a.bottom > b.top + 0.5;
          const headings = [...document.querySelectorAll(".split-tag, #map-heading > *")].filter(shown);
          const pressable = {
            points: [...document.querySelectorAll(".pt")].filter(shown).map((n) => box(n.querySelector(".shape") || n)),
            chairs: [...document.querySelectorAll(".seat-press, .table .token .shape, .chair .hit")].filter(shown).map(box),
            bubbles: [...document.querySelectorAll(".map-bubble, .table-bubble, .map-tip")].filter(shown).map(box),
            labels: [...document.querySelectorAll(".table-label")].filter(shown).map(box),
            ai: [...document.querySelectorAll("#ai-seat")].filter(shown).map(box),
            count: [...document.querySelectorAll(".school-count")].filter((n) => !n.hidden && shown(n)).map(box),
          };
          const covers = {};
          for (const [what, boxes] of Object.entries(pressable)) {
            covers[what] = headings.reduce((n, head) => n + boxes.filter((b) => b.width && meet(box(head), b)).length, 0);
          }
          const s = document.scrollingElement;
          return {
            headings: headings.map((n) => {
              const b = box(n), cs = getComputedStyle(n);
              return { tag: n.tagName.toLowerCase(), cls: n.className, at: [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)],
                font: cs.fontSize, cursor: cs.cursor, pointer: cs.pointerEvents };
            }),
            covers, scrolls: s.scrollHeight > window.innerHeight + 1 || s.scrollWidth > window.innerWidth + 1,
          };
        });
        row = await read();
        // The keyboard: Tab from the page's top until the heading has it, then Enter.
        const target = await p.evaluate(() => Boolean(document.querySelector("button.split-tag:not(.unplaced), #map-heading button")));
        if (target) {
          await p.evaluate(() => document.activeElement && document.activeElement.blur());
          await p.locator("body").focus();
          let tabs = 0, reached = false;
          for (; tabs < 250 && !reached; tabs++) {
            await p.keyboard.press("Tab");
            reached = await p.evaluate(() => Boolean(document.activeElement && document.activeElement.matches("button.split-tag, #map-heading button")));
          }
          row.tabs = reached ? tabs : null;
          if (reached) {
            row.name = await p.evaluate(() => document.activeElement.getAttribute("aria-label"));
            await p.keyboard.press("Enter");
            await p.waitForTimeout(600);
            row.after = await p.evaluate(() => ({ box: document.querySelector("#question").value,
              focused: document.activeElement && document.activeElement.id, line: document.querySelector("#input-done").hidden ? "" : document.querySelector("#input-done").textContent,
              to: document.querySelector("#ask-form").dataset.to }));
            await p.waitForTimeout(600);
            const then = await read();
            row.coversAfter = then.covers;
            row.scrollsAfter = then.scrolls;
          }
        }
        row.errors = errors;
      } catch (error) {
        row = { error: String(error).split("\n")[0].slice(0, 120) };
      }
      table[map][`${w}x${h}`] = row;
      await context.close();
    }
  }
  return JSON.stringify({ table, missing }, null, 1);
}
