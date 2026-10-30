"""Visual QA: render a compiled questionnaire and mark every extracted element.

Compiles the given .typ file to a PDF, extracts all element metadata via
`typst eval` (see README, "Element extraction"), rasterizes each page with
pymupdf, and draws a marker + label at each element's extracted top-left
position. If the red markers sit exactly on the drawn boxes, the extraction
is correct — no printing or scanning needed.

Usage:
    uv run python scripts/render_debug_overlay.py [path/to/doc.typ]
Defaults to typst_src/test_poc.typ. Writes output/<stem>-page-NN.png.
"""

import json
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TYP = ROOT / "typst_src" / "test_poc.typ"
OUT_DIR = ROOT / "output"
DPI = 150
PX_PER_PT = DPI / 72

EXPRESSION = (
    "query(metadata)"
    ".map(it => (value: it.value, page: it.location().page(), "
    "x: it.location().position().x.pt(), y: it.location().position().y.pt()))"
)


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    typ = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TYP
    typ = typ.resolve()
    OUT_DIR.mkdir(exist_ok=True)
    pdf = OUT_DIR / f"{typ.stem}.pdf"

    r = subprocess.run(["typst", "compile", str(typ), str(pdf)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"typst compile failed for {typ}")

    r = subprocess.run(
        ["typst", "eval", EXPRESSION, "--in", str(typ), "--pretty"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"typst eval failed for {typ}")
    records = json.loads(r.stdout)

    doc = fitz.open(pdf)
    pages = {}
    for rec in records:
        pages.setdefault(rec["page"], []).append(rec)
    pages = {p: recs for p, recs in sorted(pages.items())}
    if not pages:
        raise SystemExit("no metadata elements found — nothing to overlay")

    font = load_font(16)
    for page_no, recs in pages.items():
        page = doc[page_no - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(PX_PER_PT, PX_PER_PT))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)

        for rec in recs:
            x = rec["x"] * PX_PER_PT
            y = rec["y"] * PX_PER_PT
            v = rec["value"]
            # crosshair + ring on the extracted top-left corner
            draw.ellipse((x - 9, y - 9, x + 9, y + 9), outline="red", width=2)
            draw.line((x - 14, y, x + 14, y), fill="red", width=1)
            draw.line((x, y - 14, x, y + 14), fill="red", width=1)
            label = (
                f"{v.get('kind')} "
                + (f"q{v['question']} " if v.get("question") is not None else "")
                + (v.get("text") or f"{v.get('w', 0):.0f}x{v.get('h', 0):.0f}pt")
            )
            # white halo so the text is readable over any background
            tx, ty = x + 12, y - 8
            draw.text((tx + 1, ty + 1), label, font=font, fill="white")
            draw.text((tx, ty), label, font=font, fill="red")

        out = OUT_DIR / f"{typ.stem}-page-{page_no:02d}.png"
        img.save(out)
        print(f"page {page_no}: {len(recs)} element(s) -> {out}")


if __name__ == "__main__":
    main()
