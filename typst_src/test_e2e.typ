// Reference end-to-end questionnaire. It exercises every element kind
// (participant-number, checkbox, freetext, checktable, question) over several
// A4 pages, with fresh invented content (it does NOT follow the legacy
// Rope/Bottleneck forms). Each checktable is sized to fit on a single page --
// the legacy CheckTable model has one page per table. Pages are separated by
// an explicit `pagebreak()` so the layout does not depend on element sizes.
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
        // five options in three columns (two rows instead of five)
        checkbox-grid(
          ("sehr gut", "gut", "eher schlecht", "schlecht", "weiß nicht"),
          columns: 3,
          question: 1,
        ),
        freetext(1600, 560, question: 1),
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
        checkbox-grid(
          ("nie", "einmal", "zweimal", "dreimal", "öfter als dreimal"),
          columns: 3,
          question: 3,
        ),
      ),
    ),
    question(4, "Was ist Ihnen während der Übung besonders aufgefallen?",
      stack(
        spacing: 8pt,
        freetext(2800, 640, question: 4),
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
        checkbox-grid(
          ("gar nicht", "leicht", "mäßig", "anstrengend", "sehr anstrengend"),
          columns: 3,
          question: 6,
        ),
      ),
    ),
  ),
  // explicit page break: page 2 starts with question 5
  breaks: (5,),
  // explicit although it is the default: this form carries the ID row
  num-digits: 4,
)
