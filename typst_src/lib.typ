// Shared library for the Typst questionnaire templates.
//
// Coordinate convention (must match the processing tool's deskewed scan space):
// - The printed page is A4. Scans and PDF renders happen at 500 dpi.
// - deskew() in the processing tool normalizes the four page-corner ArUco tags
//   (DICT_4X4_50, ids 1 = top-left, 4 = top-right, 3 = bottom-right,
//   2 = bottom-left) to fixed centers in 500 dpi pixels:
//     top-left (645, 375), top-right (3725, 375),
//     bottom-left (645, 5530), bottom-right (3725, 5530).
// - Detection coordinates are px in that space. An element's (dx, dy) is its
//   offset from the top-left tag center, so
//     absolute page px = (645 + dx, 375 + dy).
// - Conversion: 1 px = 25.4 / 500 mm, i.e. 1 pt = 500 / 72 px.

// centers of the page-corner tags in 500 dpi px. 527/3607 (not deskew's
// target 645/3725) so that the printed tags are symmetric on the page: the
// pair's spread must stay 3080 px (otherwise deskew() would rescale the scan),
// and 527/3607 is the only placement with equal gaps to the page edges
// (18.97 mm each). deskew() maps these centers onto (645, 375) etc., and
// `corner-tag` emits each center as an "aruco" record, so the export measures
// dx/dy from the document's own printed anchor instead of a Python constant.
#let corner-px = (
  top-left: (x: 527, y: 375),
  top-right: (x: 3607, y: 375),
  bottom-left: (x: 527, y: 5530),
  bottom-right: (x: 3607, y: 5530),
)

// printed size of a corner tag (the body figure's tags measure ~15.6 mm)
#let tag-size = 15.6mm

// 500 dpi pixel -> Typst length
#let px = (n) => n * 25.4mm / 500

// Attach element data as metadata, pinned by the caller to the element's
// top-left corner via `place(top + left, emit(...))`.
//
// `data` is a dict with the element-specific fields (question, w, h, text,
// ...). `kind` must not clash with `data`'s keys. No label syntax is needed
// (and does not parse after a `metadata` call in code mode); the `kind`
// field is the discriminator.
//
// Extraction from the CLI (typst 0.15, `query` is evaluated in the compiled
// document's state; output is JSON):
//   typst eval 'query(metadata)
//     .filter(it => it.value.kind == "checkbox")
//     .map(it => (value: it.value, page: it.location().page(),
//                 x: it.location().position().x.pt(),
//                 y: it.location().position().y.pt()))' --in doc.typ
#let emit = (kind, data) => metadata((kind: kind, ..data))

// content area: below the top tags, above the bottom tags, with equal left and
// right margins (25.75 mm each, i.e. the old 34.6/16.9 mm split evenly) so the
// 158.5 mm content width stays the same. The top margin keeps a visible gap
// between the corner tags and the first line of text.
#let page-margins = (top: 33mm, bottom: 23.9mm, left: 25.75mm, right: 25.75mm)

// one corner tag, centered on a page point (lengths from the page's top-left).
// Also emits an "aruco" record at the tag's center, so the export script can
// read the printed anchor from the document instead of hard-coding it (the
// anchor is the origin every dx/dy is measured from).
#let corner-tag = (id, center) => {
  place(top + left,
    dx: px(center.x) - tag-size / 2,
    dy: px(center.y) - tag-size / 2,
    image("assets/aruco-" + str(id) + ".png", width: tag-size, scaling: "pixelated"),
  )
  place(top + left, dx: px(center.x), dy: px(center.y),
    emit("aruco", (id: id, size: tag-size / 1pt)),
  )
}

// the four page-corner tags at their fixed centers.
//
// Pass this as `background:` to `set page`. The background is laid out over
// the full physical page (margins included) on every page, which is the
// supported way to decorate pages with auto-paginated content (`#show page`
// does not exist in Typst). The tags are fixed in id and position on every
// page: deskew() requires exactly ids 1, 4, 3, 2 at the centers above, so
// they must NOT depend on the page number.
#let page-corner-tags = {
  corner-tag(1, corner-px.top-left)
  corner-tag(4, corner-px.top-right)
  corner-tag(3, corner-px.bottom-right)
  corner-tag(2, corner-px.bottom-left)
}

// a 60×70 px checkbox (deskewed space) with a label to its right
#let checkbox = (label, question: none) => {
  let w = px(60)
  let h = px(70)
  grid(columns: (w, auto), column-gutter: 6pt, align: center,
    box(
      width: w,
      height: h,
      // no inset: the stroke must sit exactly at w x h (60x70 px at 500 dpi)
      inset: 0pt,
      stroke: 0.75pt + black,
      place(top + left,
        emit("checkbox",
          (
            question: question,
            w: w / 1pt,
            h: h / 1pt,
            text: label,
          ),
        ),
      ),
    ),
    text(size: 11pt, label),
  )
}

// several checkboxes laid out in a compact `columns`-column grid (row-major
// order), e.g. to save vertical space for long option lists.
//
// Extraction is unaffected: every checkbox still emits its own record, and the
// loader sorts elements by (page, dy, dx), which reproduces the given order.
// `columns` may be an integer (equal columns) or an explicit column array.
#let checkbox-grid = (labels, columns: 2, question: none) => {
  // an integer means "n equal columns": plain `columns: 3` in a grid would be
  // content-sized (auto) columns, which makes the spacing uneven
  let cols = if type(columns) == int {
    range(0, columns).map(_ => 1fr)
  } else {
    columns
  }
  block(width: 100%, grid(
    columns: cols,
    column-gutter: 12pt,
    row-gutter: 8pt,
    ..labels.map(label => checkbox(label, question: question)),
  ))
}

// an empty ruled box (size in 500 dpi px) for handwritten answers
#let freetext = (w, h, question: none) => {
  let width = px(w)
  let height = px(h)
  box(
    width: width,
    height: height,
    // no inset: the stroke must sit exactly at width x height
    inset: 0pt,
    stroke: 0.5pt + black,
    place(top + left,
      emit("freetext",
        (
          question: question,
          w: width / 1pt,
          h: height / 1pt,
        ),
      ),
    ),
  )
}

// a check-marking table: column-label header row, row-label column, and one
// empty cell per (row, col). The detector crops each cell interior
// (area_grabbing.py: step_y = size_y / len(rows), 13 px inset top/bottom),
// so the row pitch must be exactly cell-h.
//
// `cell-w` / `cell-h` are in 500 dpi px (defaults = the legacy 480x120).
// Emits one "checkcell" metadata per cell (row/col index and label), pinned
// to the cell's top-left corner. `table-index` disambiguates several tables
// of the same question (e.g. the three symbol tables in Bottleneck); it is
// stored in the metadata under the key `table`.
#let checktable = (columns, rows, question: none, table-index: none,
                   cell-w: px(480), cell-h: px(120)) => {
  let cells = ()
  cells.push({})
  for j in range(0, columns.len()) {
    cells.push(box(inset: 4pt, text(size: 11pt, columns.at(j))))
  }
  for i in range(0, rows.len()) {
    cells.push(box(inset: 4pt, text(size: 11pt, rows.at(i))))
    for j in range(0, columns.len()) {
      cells.push(
        place(top + left,
          emit("checkcell",
            (
              question: question,
              table: table-index,
              row: i,
              col: j,
              row-label: rows.at(i),
              col-label: columns.at(j),
              w: cell-w / 1pt,
              h: cell-h / 1pt,
            ),
          ),
        ),
      )
    }
  }
  table(
    columns: (auto, ..range(0, columns.len()).map(_ => cell-w)),
    rows: (auto, ..range(0, rows.len()).map(_ => cell-h)),
    stroke: 0.5pt + black,
    // the cell content (and the pinned metadata) must sit at the cell edge
    inset: 0pt,
    align: center,
    ..cells,
  )
}

// one question: bold "Frage N." heading, 12pt gap, then the question's
// elements (any content: a stack of checkboxes, a checktable, freetext, ...).
//
// `body` (not `text`: that would shadow the built-in `text()`).
//
// Built with `stack`: it takes variadic content children and breaks across
// pages (both probe-verified; `block` only takes ONE content argument).
//
// Emits a "question" record (num, text) pinned to the heading's top-left.
// The legacy Question class has no position of its own (the detector derives
// the question top from its elements' minimum dy), but the record lets the
// Phase 5 loader report where each question starts and on which page it is.
#let question = (num, body, elements) => {
  // box takes exactly one content argument, so the place + heading live in
  // a zero-spacing stack inside the box (the place is anchored to the
  // box's frame, i.e. the heading's top-left -- the verified checkbox
  // anchor pattern).
  stack(
    spacing: 12pt,
    box(
      stack(
        spacing: 0pt,
        place(top + left, emit("question", (num: num, text: body))),
        text(size: 13pt, weight: "bold", "Frage " + str(num) + ". " + body),
      ),
    ),
    elements,
  )
}

// the participant-number header: an "ID" label followed by `n` empty boxes,
// one digit per box (sizes in 500 dpi px). The row is centered horizontally;
// the label is part of the row.
//
// Emits one "participant-number" record pinned to the top-left of the first
// box and sized to the full row of boxes (label excluded). The annotation GUI
// shows that area so the number can be typed in; the detector itself ignores
// it (the digit boxes are not part of the automatic extraction).
#let participant-number = (n) => {
  let w = px(150)
  let h = px(200)
  let gutter = px(20)
  let row-w = w * n + gutter * (n - 1)
  let cells = (text(size: 11pt, "ID"),)
  for i in range(0, n) {
    let marker = if i == 0 {
      place(top + left,
        emit("participant-number", (digits: n, w: row-w / 1pt, h: h / 1pt)))
    } else { none }
    // box takes exactly one content child; `none` is fine for the other boxes
    cells.push(box(width: w, height: h, inset: 0pt, stroke: 0.5pt + black, marker))
  }
  block(width: 100%, align(center, grid(
    columns: (auto, ..range(0, n).map(_ => w)),
    column-gutter: gutter,
    // `center` alone is horizontal only; `horizon` adds vertical centering
    // so the "ID" caption sits mid-height of the digit boxes
    align: center + horizon,
    ..cells,
  )))
}

// a questionnaire: title, then all questions, 24pt apart, auto-paginating
// (each element's page is read back from the layout).
//
// `questions` is an array of content (each entry a question(...) call).
//
// `num-digits` > 0 puts the participant-number row ("ID" + one box per digit)
// above the title; it is on by default, forms that predate it pass
// `num-digits: 0`.
//
// `breaks` lists question numbers that start a new page, e.g. `breaks: (5,)`
// (use it instead of sizing elements to force a break). The content is
// emitted as top-level blocks rather than one `stack` because Typst forbids
// `pagebreak()` inside a container.
#let template = (title, questions, num-digits: 4, breaks: ()) => {
  if num-digits > 0 {
    block(below: 24pt, participant-number(num-digits))
  }
  // `block(below:)` gives exact spacing; a bare `v()` at the top level would
  // add the surrounding paragraph's line leading on top of it
  block(below: 24pt, text(size: 16pt, weight: "bold", title))
  for (i, q) in questions.enumerate() {
    if (i + 1) in breaks {
      pagebreak()
      q
    } else {
      block(below: 24pt, q)
    }
  }
}
