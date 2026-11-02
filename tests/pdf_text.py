"""Write a one-page PDF whose text reads back as exactly the characters given.

Real PDFs sometimes carry look-alike code points such as Kangxi radicals
(「⽬的」). A normal CJK font maps them back to ordinary kanji on reading, so it
cannot reproduce the problem. Here a Type3 font with a ToUnicode map is built
by hand: every character is a blank 1000-unit glyph, and reading it back gives
the original code point. No font file is needed.
"""

from pathlib import Path

_PAGE = (595, 842)  # A4 in points


def _utf16_hex(text: str) -> str:
    return text.encode("utf-16-be").hex().upper()


def write_text_pdf(path: Path, lines: list[tuple[float, float, str]], size: float = 12) -> Path:
    """lines: (x, y from the bottom, text). Each character is `size` points wide."""
    chars = sorted({ch for _, _, text in lines for ch in text})
    if len(chars) > 255:
        raise ValueError("too many distinct characters for one simple font")
    code = {ch: i + 1 for i, ch in enumerate(chars)}

    content = "".join(
        f"BT /F1 {size} Tf {x} {y} Td <{''.join(f'{code[ch]:02X}' for ch in text)}> Tj ET\n"
        for x, y, text in lines
    )
    cmap = (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
        "1 begincodespacerange <01> <FF> endcodespacerange\n"
        f"{len(chars)} beginbfchar\n"
        + "".join(f"<{code[ch]:02X}> <{_utf16_hex(ch)}>\n" for ch in chars)
        + "endbfchar endcmap CMapName currentdict /CMap defineresource pop end end\n"
    )
    names = " ".join(f"/g{code[ch]}" for ch in chars)
    procs = " ".join(f"/g{code[ch]} 8 0 R" for ch in chars)
    widths = " ".join("1000" for _ in chars)
    glyph = "1000 0 0 0 1000 1000 d1\n"

    def stream(body: str) -> str:
        return f"<< /Length {len(body.encode('latin-1'))} >>\nstream\n{body}endstream"

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE[0]} {_PAGE[1]}] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        stream(content),
        "<< /Type /Font /Subtype /Type3 /FontBBox [0 0 1000 1000] "
        "/FontMatrix [0.001 0 0 0.001 0 0] /CharProcs 6 0 R "
        f"/Encoding << /Type /Encoding /Differences [1 {names}] >> "
        f"/FirstChar 1 /LastChar {len(chars)} /Widths [{widths}] "
        "/ToUnicode 7 0 R /Resources << >> >>",
        f"<< {procs} >>",
        stream(cmap),
        stream(glyph),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode("latin-1")
    path.write_bytes(bytes(out))
    return path
