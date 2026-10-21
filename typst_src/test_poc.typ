// Phase 1 proof of concept: two checkboxes on a page with the four corner tags.
// Compile:  typst compile typst_src/test_poc.typ output/test_poc.pdf
// Extract:  typst eval 'query(metadata).map(it => (value: it.value,
//   page: it.location().page(), x: it.location().position().x.pt(),
//   y: it.location().position().y.pt()))' --in typst_src/test_poc.typ
// See README.md ("Element extraction") for details.
#import "lib.typ": *

#set page(
  paper: "a4",
  margin: page-margins,
  background: page-corner-tags,
)

#checkbox("ja", question: 1)
#v(20pt)
#checkbox("nein", question: 1)
