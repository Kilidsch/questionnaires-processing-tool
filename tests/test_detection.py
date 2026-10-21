"""Detection simulation: render the e2e questionnaire at 500 dpi, draw
pen-like fill marks at the *extracted* positions of a chosen subset of
elements, then run the tool's ``parse_single_data`` with the layout-built
``Template`` and assert the detector reports exactly the marks we drew
(filled vs. empty) for checkboxes and checktable cells.

The template comes from ``GrabExperiment.initType("test_e2e")`` (the real
wiring) and the PDF is the committed ``tests/fixtures/test_e2e.pdf``, i.e. the
same compile the registered layout JSON came from. The only difference from a
real scan is that the "pen marks" are synthetic black shapes; the physical
print/fill/scan step is the remaining manual check.
"""

import json
import os
import tempfile
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytest
from pytest import approx

from src import questionnaire_layout as ql
from src.area_grabbing import parse_single_data
from src.survey_templates import GrabExperiment

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "tests" / "fixtures" / "test_e2e.pdf"
LAYOUT_JSON = ROOT / "src" / "layouts" / "test_e2e_layout.json"

# (question, label) of the checkboxes simulated as ticked with a pen.
FILLED_CHECKBOXES = {
    (1, "sehr gut"),
    (3, "einmal"),
    (4, "Nichts ist aufgefallen"),
    (5, "Keine Angabe"),
    (6, "mäßig"),
}
# (question, row, col) of the table cells simulated as marked.
FILLED_CELLS = {
    (2, 0, 0),   # Laufen / einzeln
    (2, 2, 2),   # Schieben / beides
    (5, 1, 1),   # Hände seitlich / neutral
    (5, 4, 0),   # verschränkt / unsicher
}


@pytest.fixture(scope="module")
def detection():
    # 1. the template through the real dispatch, plus the layout for positions
    template = GrabExperiment.initType("test_e2e")
    layout = ql.load_layout(LAYOUT_JSON)

    # 2. render every page at 500 dpi (BGR, like a scanner would deliver)
    doc = fitz.open(PDF)
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=ql.DPI)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(
            pix.height, pix.width, pix.n
        ).copy()
        imgs.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    doc.close()

    # 3. draw synthetic pen marks at the extracted positions. The layout stores
    # offsets from the *printed* tag anchor; parse_single_data deskews the page
    # afterwards, which translates the printed tags onto AnkerPos.
    for e in layout.elements:
        img = imgs[e.page - 1]
        left = ql.PRINT_ANKER_X + e.dx
        top = ql.PRINT_ANKER_Y + e.dy
        if e.kind == "checkbox" and (e.question, e.text) in FILLED_CHECKBOXES:
            # black dot inside the 60x70 box (the detector crops top:top+70, left:left+60)
            cv2.circle(img, (left + 30, top + 35), 22, (0, 0, 0), -1)
        elif e.kind == "checkcell" and (e.question, e.row, e.col) in FILLED_CELLS:
            # black dot inside the 480x120 cell, well clear of the 13 px crop insets
            cv2.circle(img, (left + 240, top + 60), 30, (0, 0, 0), -1)

    # 4. write the "scan" to a scratch dir and run the real detector
    tmp = tempfile.mkdtemp(prefix="e2e_detect_")
    files = []
    for i, img in enumerate(imgs, start=1):
        name = f"page_{i:03d}.jpg"
        cv2.imwrite(os.path.join(tmp, name), img)
        files.append(name)
    parse_single_data(tmp, files, template)
    with open(os.path.join(tmp, "surveyData.json"), encoding="utf-8") as f:
        survey = json.load(f)
    return {"survey": survey, "layout": layout, "template": template, "tmp": tmp}


def _checkbox_answers(detection, qnum):
    # a question with no checkboxes has no "checkboxes" key in the survey JSON
    return {c["text"]: c["answer"]
            for c in detection["survey"][str(qnum)].get("checkboxes", [])}


def _table_data(detection, qnum):
    table = detection["survey"][str(qnum)]["table"]
    assert isinstance(table, list) and len(table) == approx(1), f"q{qnum}: expected one table"
    return table[0]["data"]


def test_filled_checkboxes_detected(detection):
    for qnum, text in sorted(FILLED_CHECKBOXES):
        answers = _checkbox_answers(detection, qnum)
        assert answers[text] is True, f"q{qnum} '{text}' was drawn but not detected"


def test_empty_checkboxes_not_detected(detection):
    for e in detection["layout"].elements:
        if e.kind == "checkbox" and (e.question, e.text) not in FILLED_CHECKBOXES:
            answers = _checkbox_answers(detection, e.question)
            assert answers[e.text] is False, f"q{e.question} '{e.text}' is empty but detected"


def test_checkbox_counts_match_template(detection):
    for qnum, q in {q.num: q for q in detection["template"].get_questions()}.items():
        answers = _checkbox_answers(detection, qnum)
        assert set(answers) == {c.text for c in q.checkboxes}, f"q{qnum} checkbox set mismatch"


def test_filled_cells_detected(detection):
    cells = {(e.question, e.row, e.col): (e.row_label, e.col_label)
             for e in detection["layout"].elements if e.kind == "checkcell"}
    for key in sorted(FILLED_CELLS):
        qnum, _row, _col = key
        row_label, col_label = cells[key]
        data = _table_data(detection, qnum)
        assert data[row_label][col_label] is True, f"q{qnum} cell {row_label}/{col_label} missed"


def test_empty_cells_not_detected(detection):
    cells = {(e.question, e.row, e.col): (e.row_label, e.col_label)
             for e in detection["layout"].elements if e.kind == "checkcell"}
    for key, (row_label, col_label) in sorted(cells.items()):
        if key in FILLED_CELLS:
            continue
        data = _table_data(detection, key[0])
        assert col_label not in data[row_label], (
            f"q{key[0]} cell {row_label}/{col_label} is empty but detected"
        )


def test_table_row_columns_match_template(detection):
    for qnum, q in {q.num: q for q in detection["template"].get_questions()}.items():
        for table in q.tables:
            data = _table_data(detection, qnum)
            assert set(data) == set(table.rows), f"q{qnum} table rows mismatch"
            for row in table.rows:
                # only filled columns may appear, and only as True
                assert all(v is True for v in data[row].values())


def test_freetext_crops_written(detection):
    survey = detection["survey"]
    for qnum in (1, 4):
        textfields = survey[str(qnum)]["textFields"]
        assert len(textfields) == approx(1)
        path = textfields[0]["file"]
        assert os.path.isabs(path) and os.path.isfile(path)
        crop = cv2.imread(path)
        assert crop is not None
        # q1: 1600x560, q4: 2800x640 (height x width)
        h, w = crop.shape[:2]
        if qnum == 1:
            assert w == approx(1600, abs=2)
            assert h == approx(560, abs=2)
        else:
            assert w == approx(2800, abs=2)
            assert h == approx(640, abs=2)


def test_participant_number_area(detection):
    """The ID box row is exposed as the legacy participant-number area:
    it must cover the row of digit boxes on page 1, inside the page bounds."""
    pn = detection["template"].get_participant_number()
    assert pn is not None
    assert pn.page == approx(1)
    assert pn.size_x == approx(660, abs=1)
    assert pn.size_y == approx(200, abs=1)
    # inside the deskewed page, below the top tag
    assert 0 <= pn.dx
    assert 0 <= pn.dy
    assert pn.dx + pn.size_x <= 3500
    assert pn.dy + pn.size_y <= 5200
