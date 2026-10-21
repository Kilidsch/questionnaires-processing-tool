"""Round-trip test for the purpose-built end-to-end questionnaire.

Exports typst_src/test_e2e.typ (a fresh form that exercises every element
kind -- participant-number, checkbox, freetext, checktable, question -- over
two auto-paginated pages), loads it through the Pydantic schema, rebuilds a
legacy Template, and asserts the structure: counts, kinds, pages, labels,
sizes, bounds, and the single-page-per-checktable constraint.

Positions use pytest ``approx`` with a small pixel tolerance; counts and
labels are exact.
"""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest
from pytest import approx

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "export_layout.py"
TYP = ROOT / "typst_src" / "test_e2e.typ"
OUT_JSON = ROOT / "output" / "test_e2e_layout.json"

from src import questionnaire_layout as ql  # noqa: E402


@pytest.fixture(scope="module")
def exported():
    """Compile + extract once, then load the JSON and build the Template."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(TYP)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.returncode == 0, f"export failed:\n{r.stdout}\n{r.stderr}"
    assert OUT_JSON.is_file(), "export did not write the layout JSON"
    layout = ql.load_layout(OUT_JSON)
    template = ql.build_template(layout)
    return {
        "raw": json.loads(OUT_JSON.read_text(encoding="utf-8")),
        "layout": layout,
        "template": template,
    }


def test_json_shape(exported):
    data = exported["raw"]
    assert data["doc"] == "test_e2e.typ"
    assert data["pages"] == approx(2)
    assert len(data["elements"]) == approx(56)


def test_element_kind_counts(exported):
    kinds = {}
    for e in exported["layout"].elements:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    assert kinds == {
        "question": 6,
        "checkbox": 17,
        "freetext": 2,
        "checkcell": 30,
        "participant-number": 1,
    }


def test_template_structure(exported):
    template = exported["template"]
    assert template.get_num_pages() == approx(2)

    questions = template.get_questions()
    assert len(questions) == approx(6)
    assert [q.num for q in questions] == [1, 2, 3, 4, 5, 6]
    by_num = {q.num: q for q in questions}

    # German question text round-trips without mojibake
    assert by_num[1].questionText == "Wie haben Sie die Übung insgesamt bewertet?"
    assert by_num[2].questionText == "Welche Tätigkeiten haben Sie während der Übung ausgeführt?"
    assert by_num[5].questionText == "Wie sicher haben Sie sich in jeder Handposition gefühlt?"

    # q1: 5 checkboxes (2-column grid) + 1 freetext (1600x560)
    q1 = by_num[1]
    assert len(q1.checkboxes) == approx(5)
    assert [c.text for c in q1.checkboxes] == [
        "sehr gut", "gut", "eher schlecht", "schlecht", "weiß nicht",
    ]
    assert len(q1.texts) == approx(1)
    assert q1.texts[0].size_x == approx(1600, abs=1)
    assert q1.texts[0].size_y == approx(560, abs=1)
    assert len(q1.tables) == approx(0)

    # q2: one 3x5 table, no checkbox / freetext
    q2 = by_num[2]
    assert len(q2.tables) == approx(1)
    t2 = q2.tables[0]
    assert t2.page == approx(1)
    assert list(t2.columns) == ["einzeln", "in der Gruppe", "beides"]
    assert list(t2.rows) == ["Laufen", "Stehen", "Schieben", "Ziehen", "Tragen"]
    for sx in t2.size_x:
        assert sx == approx(480, abs=1)
    assert t2.size_y == approx(600, abs=1)  # 5 rows * 120 px
    assert len(q2.checkboxes) == approx(0)
    assert len(q2.texts) == approx(0)

    # q3: 5 checkboxes
    assert len(by_num[3].checkboxes) == approx(5)
    assert [c.text for c in by_num[3].checkboxes] == [
        "nie", "einmal", "zweimal", "dreimal", "öfter als dreimal",
    ]

    # q4: 1 freetext (2800x640) + 1 checkbox
    q4 = by_num[4]
    assert len(q4.texts) == approx(1)
    assert q4.texts[0].size_x == approx(2800, abs=1)
    assert q4.texts[0].size_y == approx(640, abs=1)
    assert len(q4.checkboxes) == approx(1)
    assert q4.checkboxes[0].text == "Nichts ist aufgefallen"

    # q5: one 3x5 table + 1 checkbox
    q5 = by_num[5]
    assert len(q5.tables) == approx(1)
    t5 = q5.tables[0]
    assert t5.page == approx(2)
    assert list(t5.columns) == ["unsicher", "neutral", "sicher"]
    assert list(t5.rows) == [
        "Hände oben", "Hände seitlich", "Hände unten", "in den Taschen", "verschränkt",
    ]
    for sx in t5.size_x:
        assert sx == approx(480, abs=1)
    assert t5.size_y == approx(600, abs=1)
    assert len(q5.checkboxes) == approx(1)
    assert q5.checkboxes[0].text == "Keine Angabe"

    # q6: 5 checkboxes
    assert len(by_num[6].checkboxes) == approx(5)
    assert [c.text for c in by_num[6].checkboxes] == [
        "gar nicht", "leicht", "mäßig", "anstrengend", "sehr anstrengend",
    ]


def test_participant_number(exported):
    """The Nummer header row: one box per digit, exposed as the legacy
    ParticipantNumber area (label excluded, so 4*150 + 3*20 = 660 px wide)."""
    elements = exported["layout"].elements
    pn = [e for e in elements if e.kind == "participant-number"]
    assert len(pn) == approx(1)
    pn = pn[0]
    assert pn.page == approx(1)
    assert pn.digits == approx(4)
    assert pn.w == approx(660, abs=1)
    assert pn.h == approx(200, abs=1)
    # the row is centered horizontally on the page
    assert pn.dx == approx(1314, abs=2)

    area = exported["template"].get_participant_number()
    assert area is not None
    assert area.page == approx(1)
    assert area.dx == approx(pn.dx, abs=1)
    assert area.dy == approx(pn.dy, abs=1)
    assert area.size_x == approx(660, abs=1)
    assert area.size_y == approx(200, abs=1)


def test_checkbox_grid_columns(exported):
    """The multi-column helper lays checkboxes out row-major in equal-width
    columns: Q1's five options need two rows of three, so the first three sit
    on one line and the remaining two start the next row."""
    boxes = {(e.question, e.text): e
             for e in exported["layout"].elements if e.kind == "checkbox"}

    first = boxes[(1, "sehr gut")]
    second = boxes[(1, "gut")]
    third = boxes[(1, "eher schlecht")]
    assert second.dy == approx(first.dy, abs=1)
    assert third.dy == approx(first.dy, abs=1)
    # equal column pitch (~1068 px across the text width)
    assert second.dx - first.dx == approx(1068, abs=2)
    assert third.dx - second.dx == approx(1068, abs=2)

    fourth = boxes[(1, "schlecht")]
    assert fourth.dx == approx(first.dx, abs=2)
    assert fourth.dy - first.dy == approx(126, abs=2)  # one grid row

    for qnum in (1, 3, 6):
        rows = {e.dy for e in boxes.values() if e.question == qnum}
        assert len(rows) == approx(2), f"q{qnum} should need two rows"


def test_every_checkbox_is_60x70(exported):
    for e in exported["layout"].elements:
        if e.kind == "checkbox":
            assert e.w == approx(60, abs=1)
            assert e.h == approx(70, abs=1)


def test_every_cell_is_480x120(exported):
    for e in exported["layout"].elements:
        if e.kind == "checkcell":
            assert e.w == approx(480, abs=1)
            assert e.h == approx(120, abs=1)


def test_table_cell_pitch(exported):
    """The detector assumes a uniform row pitch (step_y = size_y / n_rows) and
    reads each column from its own dx; verify both hold in the layout."""
    by_table = defaultdict(list)
    for e in exported["layout"].elements:
        if e.kind == "checkcell":
            by_table[(e.question, e.table)].append(e)

    for (qnum, _), cells in by_table.items():
        # row pitch exactly 120 px
        col0 = [c for c in cells if c.col == 0]
        col0.sort(key=lambda c: c.row)
        for a, b in zip(col0, col0[1:]):
            assert b.dy - a.dy == approx(120, abs=1)
        # column pitch exactly 480 px
        row0 = [c for c in cells if c.row == 0]
        row0.sort(key=lambda c: c.col)
        for a, b in zip(row0, row0[1:]):
            assert b.dx - a.dx == approx(480, abs=1)


def test_each_checktable_on_single_page(exported):
    """Auto-pagination must not split a checktable, because the legacy
    CheckTable model carries a single page. Every cell of a (question, table)
    group must sit on that table's page."""
    by_table = defaultdict(set)
    for e in exported["layout"].elements:
        if e.kind == "checkcell":
            by_table[(e.question, e.table)].add(e.page)
    assert set(by_table) == {(2, 1), (5, 1)}
    for (qnum, _), pages in by_table.items():
        assert len(pages) == approx(1), f"table for question {qnum} split across {pages}"
    assert by_table[(2, 1)] == {1}
    assert by_table[(5, 1)] == {2}


def test_questions_map_to_one_page_each(exported):
    """In this layout every question's elements land on a single page and the
    questions are in order: Q1-Q4 on page 1, Q5-Q6 on page 2 (the Nummer
    header row shifts the page-1 content down but must not change the break)."""
    layout = exported["layout"]

    def element_pages(qnum):
        return {e.page for e in layout.elements
                if e.kind in ("checkbox", "freetext", "checkcell") and e.question == qnum}

    for qnum in (1, 2, 3, 4):
        assert element_pages(qnum) == {1}, f"q{qnum} spans {element_pages(qnum)}"
    for qnum in (5, 6):
        assert element_pages(qnum) == {2}, f"q{qnum} spans {element_pages(qnum)}"


def test_positions_are_sane(exported):
    elements = exported["layout"].elements

    # known spots (measured with the ID row, 33 mm top margin and grid layout)
    ja = next(e for e in elements if e.kind == "checkbox" and e.text == "sehr gut")
    assert ja.dx == approx(36, abs=2)
    assert ja.dy == approx(1021, abs=2)
    last = next(e for e in elements if e.kind == "checkbox" and e.text == "sehr anstrengend")
    assert last.dx == approx(1104, abs=2)  # second of three grid columns
    assert last.dy == approx(1606, abs=2)

    # table anchors (dx of column 0, dy of row 0)
    q2 = next(e for e in elements if e.kind == "checkcell"
              and e.question == 2 and e.row == 0 and e.col == 0)
    assert q2.dx == approx(371, abs=2)
    assert q2.dy == approx(2346, abs=2)
    q5 = next(e for e in elements if e.kind == "checkcell"
              and e.question == 5 and e.row == 0 and e.col == 0)
    assert q5.dx == approx(562, abs=2)
    assert q5.dy == approx(522, abs=2)

    # every element lands inside the deskewed page (A4 @ 500 dpi = 4134x5847)
    for e in elements:
        assert -10 <= e.dx <= 3500
        assert -10 <= e.dy <= 5200
