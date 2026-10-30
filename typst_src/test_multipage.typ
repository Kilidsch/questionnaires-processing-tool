// Phase 4 test: template/question composition with auto-pagination.
// Sized so the content overflows one A4 page (the page break is expected
// to land inside question 5's checktable, i.e. one question spans pages).
//
// Compile:  typst compile typst_src/test_multipage.typ output/test_multipage.pdf
// Overlay:  uv run python scripts/render_debug_overlay.py typst_src/test_multipage.typ
// Verify:   uv run python output/verify_multipage.py
#import "lib.typ": *

#set page(
  paper: "a4",
  margin: page-margins,
  background: page-corner-tags,
)

#template(
  "Testfragebogen (Zweiseitentest)",
  (
    question(1, "Hatten Sie sich gerade in einer Situation gedrängt gefühlt?",
      stack(
        spacing: 8pt,
        checkbox("ja", question: 1),
        checkbox("nein", question: 1),
        checkbox("weiß nicht", question: 1),
      ),
    ),
    question(2, "Welche Symbole haben Sie gesehen?",
      stack(
        spacing: 8pt,
        checktable(
          ("immer", "oft", "gelegentlich", "einmalig", "-"),
          ("Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"),
          question: 2,
          table-index: 1,
        ),
        checkbox("Ich habe nichts gesehen", question: 2),
      ),
    ),
    question(3, "Wie wohl haben Sie sich in der Menschenmenge gefühlt?",
      stack(
        spacing: 8pt,
        checkbox("sehr wohl", question: 3),
        checkbox("eher wohl", question: 3),
        checkbox("neutral", question: 3),
        checkbox("eher unwohl", question: 3),
        checkbox("sehr unwohl", question: 3),
        checkbox("weiß nicht", question: 3),
      ),
    ),
    question(4, "Bitte beschreiben Sie kurz, was Sie erlebt haben.",
      stack(
        spacing: 8pt,
        freetext(2800, 390, question: 4),
        checkbox("Ich kann es nicht beschreiben", question: 4),
      ),
    ),
    question(5, "Bitte markieren Sie für jedes Symbol, wie oft Sie es gesehen haben.",
      stack(
        spacing: 8pt,
        checktable(
          ("immer", "oft", "gelegentlich", "einmalig", "-"),
          ("Kreis", "Dreieck", "Quadrat", "Herz", "Stern",
           "Pfeil", "Linie", "Punkt", "Wellenlinie", "Sonstiges"),
          question: 5,
          table-index: 1,
        ),
        checkbox("keins von diesen Symbolen", question: 5),
      ),
    ),
  ),
  // predates the Nummer header row: keep this document's layout unchanged
  num-digits: 0,
)
