// Phase 6 test: purpose-built end-to-end questionnaire. It exercises every
// element kind (checkbox, freetext, checktable, question) over several
// auto-paginated A4 pages, with fresh invented content (it does NOT follow
// the legacy Rope/Bottleneck forms). Each checktable is sized to fit on a
// single page -- the legacy CheckTable model has one page per table.
//
// Compile:  typst compile typst_src/test_e2e.typ output/test_e2e.pdf
// Overlay:  uv run python scripts/render_debug_overlay.py typst_src/test_e2e.typ
// Export:   uv run python scripts/export_layout.py typst_src/test_e2e.typ
// Test:     uv run pytest tests/test_e2e.py
#import "lib.typ": *

#set page(
  paper: "a4",
  margin: page-margins,
  background: page-corner-tags,
)

#template(
  "End-to-End Testfragebogen",
  (
    question(1, "Wie haben Sie die Übung insgesamt bewertet?",
      stack(
        spacing: 8pt,
        checkbox("sehr gut", question: 1),
        checkbox("gut", question: 1),
        checkbox("eher schlecht", question: 1),
        checkbox("schlecht", question: 1),
        checkbox("weiß nicht", question: 1),
        // 400 px tall: the Nummer header row above the title pushes the page-1
        // content down, so the original 620 px would move Q4 to page 2
        freetext(1600, 400, question: 1),
      ),
    ),
    question(2, "Welche Tätigkeiten haben Sie während der Übung ausgeführt?",
      stack(
        spacing: 8pt,
        checktable(
          ("einzeln", "in der Gruppe", "beides"),
          ("Laufen", "Stehen", "Schieben", "Ziehen", "Tragen"),
          question: 2,
          table-index: 1,
        ),
      ),
    ),
    question(3, "Wie oft sind Sie während der Übung angehalten worden?",
      stack(
        spacing: 8pt,
        checkbox("nie", question: 3),
        checkbox("einmal", question: 3),
        checkbox("zweimal", question: 3),
        checkbox("dreimal", question: 3),
        checkbox("öfter als dreimal", question: 3),
      ),
    ),
    question(4, "Was ist Ihnen während der Übung besonders aufgefallen?",
      stack(
        spacing: 8pt,
        // 520 px tall (was 700): part of the same page-1 space recovery
        freetext(2800, 520, question: 4),
        checkbox("Nichts ist aufgefallen", question: 4),
      ),
    ),
    question(5, "Wie sicher haben Sie sich in jeder Handposition gefühlt?",
      stack(
        spacing: 8pt,
        checktable(
          ("unsicher", "neutral", "sicher"),
          ("Hände oben", "Hände seitlich", "Hände unten", "in den Taschen", "verschränkt"),
          question: 5,
          table-index: 1,
        ),
        checkbox("Keine Angabe", question: 5),
      ),
    ),
    question(6, "Wie anstrengend war die Übung für Sie?",
      stack(
        spacing: 8pt,
        checkbox("gar nicht", question: 6),
        checkbox("leicht", question: 6),
        checkbox("mäßig", question: 6),
        checkbox("anstrengend", question: 6),
        checkbox("sehr anstrengend", question: 6),
      ),
    ),
  ),
  // explicit although it is the default: this form carries the Nummer row
  num-digits: 4,
)
