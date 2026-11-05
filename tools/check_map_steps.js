// 直し37-3: the map from the whole to the seniors at their windows, one
// press of ＋ at a time. A function for playwright's run_code (the screen
// check runs it against the preview server of invented seats: adults 103,
// seniors 45, gone out 10, from outside 1; no model, no key):
//
//   async (page) => { ... }   with BASE set below
//
// For each of the five sizes it asks one question and closes the meeting,
// so it is back at the map with the AI's seat folded (直し37-2). Then, at
// the whole map and after each press of ＋ until the seniors are out at
// their windows, it counts what overlaps on screen: two seats' pieces, a
// piece and the seniors' count (the label), a piece or the label and the
// AI's seat, folded and opened (its cards shown for the count only). It
// returns a table: size -> [{ press, zoom, out, pieces, label, aiFolded,
// aiOpened }], and the folded seat's size. Nothing is sent anywhere.
async (page) => {
  const BASE = globalThis.EBINO_BASE || "http://127.0.0.1:8851/";
  const SIZES = [[768, 1024], [1180, 820], [1366, 650], [1536, 760], [1920, 1080]];
  const browser = page.context().browser();
  const table = {};
  for (const [w, h] of SIZES) {
    const context = await browser.newContext({ viewport: { width: w, height: h }, reducedMotion: "reduce" });
    const p = await context.newPage();
    const rows = [];
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
      await p.waitForTimeout(800);
      await p.click("#map-back");
      await p.waitForFunction(() => !document.querySelector("#map-back") || document.querySelector("#map-back").hidden);
      await p.waitForTimeout(600);
      const first = await p.evaluate(() => document.querySelector("#map-frame svg").viewBox.baseVal.width);
      for (let press = 0; press <= 12; press++) {
        const got = await p.evaluate(() => {
          const frame = document.querySelector("#map-frame").getBoundingClientRect();
          const inFrame = (b) => b.width > 0 && b.right > frame.left && b.left < frame.right && b.bottom > frame.top && b.top < frame.bottom;
          const meet = (a, b, pad = 0) => a.left < b.right - pad && a.right > b.left + pad && a.top < b.bottom - pad && a.bottom > b.top + pad;
          const shown = (node) => node.getClientRects().length && getComputedStyle(node).visibility !== "hidden";
          const pieces = [...document.querySelectorAll(".pt")].filter(shown)
            .map((node) => (node.querySelector(".shape") || node).getBoundingClientRect()).filter(inFrame);
          const label = [...document.querySelectorAll(".school-count")].filter((n) => !n.hidden && shown(n)).map((n) => n.getBoundingClientRect());
          // Two pieces overlap when their middles are nearer than their half sizes together (they are round or nearly).
          const half = (b) => Math.min(b.width, b.height) / 2, mid = (b) => [b.left + b.width / 2, b.top + b.height / 2];
          let pairs = 0;
          for (let i = 0; i < pieces.length; i++) for (let j = i + 1; j < pieces.length; j++) {
            const [a, b] = [mid(pieces[i]), mid(pieces[j])];
            if (Math.hypot(a[0] - b[0], a[1] - b[1]) < half(pieces[i]) + half(pieces[j]) - 0.5) pairs++;
          }
          const onLabel = pieces.filter((b) => label.some((l) => meet(b, l))).length;
          const seat = document.querySelector("#ai-seat");
          const covered = () => {
            const box = seat.getBoundingClientRect();
            return pieces.filter((b) => meet(b, box)).length + label.filter((b) => meet(b, box)).length;
          };
          const folded = seat.classList.contains("folded");
          const aiFolded = covered();
          const foldedBox = seat.getBoundingClientRect();
          seat.classList.remove("folded");
          const aiOpened = covered();
          if (folded) seat.classList.add("folded");
          return { out: document.querySelector("#map-frame").classList.contains("seniors-out"), pieces: pairs, label: onLabel,
            aiFolded, aiOpened, folded, foldedSize: [Math.round(foldedBox.width), Math.round(foldedBox.height)],
            vb: document.querySelector("#map-frame svg").viewBox.baseVal.width };
        });
        rows.push({ press, zoom: +(first / got.vb).toFixed(2), out: got.out, pieces: got.pieces, label: got.label,
          aiFolded: got.aiFolded, aiOpened: got.aiOpened, folded: got.folded, foldedSize: got.foldedSize });
        if (got.out) break;
        await p.click("#map-zoom-in");
        await p.waitForTimeout(450);
      }
    } catch (error) {
      rows.push({ error: String(error).split("\n")[0].slice(0, 120) });
    }
    table[`${w}x${h}`] = rows;
    await context.close();
  }
  return JSON.stringify(table);
}
