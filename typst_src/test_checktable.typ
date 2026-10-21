// Phase 3.2 test: one checktable on a page with the four corner tags.
// Compile:  typst compile typst_src/test_checktable.typ output/test_checktable.pdf
// Overlay:  uv run python scripts/render_debug_overlay.py typst_src/test_checktable.typ
#import "lib.typ": *

#set page(
  paper: "a4",
  margin: page-margins,
  background: page-corner-tags,
)

#text(size: 14pt)[Frage 1: Welche Symbole haben Sie gesehen?]
#checktable(
  ("immer", "oft", "gelegentlich", "einmalig", "-"),
  ("Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"),
  question: 1,
  table-index: 1,
)
