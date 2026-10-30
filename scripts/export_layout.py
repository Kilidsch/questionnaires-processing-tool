"""Export a compiled Typst questionnaire's element layout to JSON.

Compiles the given .typ file to a PDF, extracts every element's metadata via
`typst eval` (see README, "Layout-based questionnaires"), converts the
page-absolute pt positions to 500 dpi px (x_px = x_pt * 500/72) and then to
the legacy (dx, dy) offsets from the printed top-left ArUco tag anchor, and
writes the result to output/<stem>_layout.json. The anchor itself is read from
the document: lib.typ emits an "aruco" record at each tag centre, and the
top-left one is stored in the JSON as "anchor" (px).

The JSON validates against the Pydantic schema in src/questionnaire_layout.py
(Layout) and can be turned back into a legacy Template with
src.questionnaire_layout.build_template.

Usage:
    uv run python scripts/export_layout.py [path/to/doc.typ]
Defaults to typst_src/test_poc.typ. Writes output/<stem>.pdf and
output/<stem>_layout.json.
"""

import json
import subprocess
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
# make the project root importable regardless of the current working directory
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.questionnaire_layout import (  # noqa: E402
    Layout,
    records_to_layout,
)

DEFAULT_TYP = ROOT / "typst_src" / "test_poc.typ"
OUT_DIR = ROOT / "output"

EXPRESSION = (
    "query(metadata)"
    ".map(it => (value: it.value, page: it.location().page(), "
    "x: it.location().position().x.pt(), y: it.location().position().y.pt()))"
)


def main() -> None:
    typ = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TYP
    typ = typ.resolve()
    OUT_DIR.mkdir(exist_ok=True)
    pdf = OUT_DIR / f"{typ.stem}.pdf"

    r = subprocess.run(
        ["typst", "compile", str(typ), str(pdf)], capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"typst compile failed for {typ}")

    # typst emits UTF-8; decode as such (the Windows locale is cp1252, which
    # would mangle the German umlauts in the question texts)
    r = subprocess.run(
        ["typst", "eval", EXPRESSION, "--in", str(typ)],
        capture_output=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"typst eval failed for {typ}")
    records = json.loads(r.stdout)

    doc = fitz.open(pdf)
    pages = doc.page_count
    doc.close()

    layout: Layout = records_to_layout(records, doc=typ.name, pages=pages)

    out = OUT_DIR / f"{typ.stem}_layout.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(layout.model_dump(by_alias=True), f, ensure_ascii=False, indent=2)

    kinds = {}
    for e in layout.elements:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    print(f"{typ.name}: {pages} page(s), {len(layout.elements)} element(s) {kinds}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
