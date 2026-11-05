// 直し33-5: where Japanese wraps in a box, it wraps between words, never
// inside one (直し31続き-5 checked the same by eye and Intl.Segmenter). A
// function for the browser (playwright's evaluate, or the page's console):
//
//   (selectors) => [{ selector, text, at }]
//
// With no selectors it reads the boxes listed in DEFAULTS, the question
// buttons at one to one among them (直し36-4: put to the person, they are
// longer than the teacher's).
//
// For each element the selectors find (shown, with text), it reads where
// each line of its text begins (a Range per character) and says each line
// that begins inside a word as Intl.Segmenter (ja, word) cuts the text.
// Nothing is sent anywhere; it reads the page as it is.
(selectors) => {
  const DEFAULTS = [".one-asks .one-ask", ".one-bubble .voice", ".table-bubble .voice", ".ai-seat", ".now-line"];
  if (!selectors || !selectors.length) selectors = DEFAULTS;
  const segmenter = new Intl.Segmenter("ja", { granularity: "word" });
  const found = [];
  for (const selector of selectors) {
    for (const box of document.querySelectorAll(selector)) {
      if (!box.getClientRects().length) continue;
      const walker = document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const text = node.textContent;
        if (text.trim().length < 2) continue;
        // Word edges, as offsets in this text.
        const edges = new Set([0, text.length]);
        for (const { index, segment } of segmenter.segment(text)) {
          edges.add(index);
          edges.add(index + segment.length);
        }
        const range = document.createRange();
        let lastTop = null;
        for (let i = 0; i < text.length; i++) {
          range.setStart(node, i);
          range.setEnd(node, i + 1);
          const rect = range.getClientRects()[0];
          if (!rect || !rect.width) continue;
          if (lastTop !== null && rect.top > lastTop + rect.height * 0.5 && !edges.has(i)) {
            found.push({ selector, text: text.slice(Math.max(0, i - 4), i) + "／" + text.slice(i, i + 4), at: i });
          }
          lastTop = rect.top;
        }
      }
    }
  }
  return found;
}
