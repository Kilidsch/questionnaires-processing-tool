"""Round-trip test: export a Typst questionnaire to a layout JSON, load it
through the Pydantic schema, rebuild a legacy Template, and check the
structure.

Runs scripts/export_layout.py once (module-scoped) on
typst_src/test_multipage.typ, then asserts the question/element counts, pages,
labels, sizes, and a few positions. Positions use pytest ``approx`` with a
small pixel tolerance; counts/labels are exact.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import approx

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "export_layout.py"
TYP = ROOT / "typst_src" / "test_multipage.typ"
OUT_JSON = ROOT / "output" / "test_multipage_layout.json"

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
    return {"raw": json.loads(OUT_JSON.read_text(encoding="utf-8")),
            "layout": layout,
            "template": template}


def test_json_shape(exported):
    data = exported["raw"]
    assert data["doc"] == "test_multipage.typ"
    assert data["pages"] == approx(2)
    assert len(data["elements"]) == approx(93)


def test_element_kind_counts(exported):
    kinds = {}
    for e in exported["layout"].elements:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    assert kinds == {"question": 5, "checkbox": 12, "checkcell": 75, "freetext": 1}


def test_template_structure(exported):
    template = exported["template"]
    assert template.get_num_pages() == approx(2)

    questions = template.get_questions()
    assert len(questions) == approx(5)
    assert [q.num for q in questions] == [1, 2, 3, 4, 5]
    by_num = {q.num: q for q in questions}

    # German question text round-trips without mojibake
    assert by_num[1].questionText == (
        "Hatten Sie sich gerade in einer Situation gedrängt gefühlt?"
    )

    # q1: 3 checkboxes, no table / freetext
    q1 = by_num[1]
    assert len(q1.checkboxes) == approx(3)
    assert [c.text for c in q1.checkboxes] == ["ja", "nein", "weiß nicht"]
    assert len(q1.tables) == approx(0)
    assert len(q1.texts) == approx(0)
    for c in q1.checkboxes:
        assert c.page == approx(1)
        assert c.size_x == approx(60, abs=1)
        assert c.size_y == approx(70, abs=1)

    # q3: 6 checkboxes
    assert len(by_num[3].checkboxes) == approx(6)

    # q4: 1 freetext (2800x390) + 1 checkbox
    q4 = by_num[4]
    assert len(q4.texts) == approx(1)
    assert q4.texts[0].size_x == approx(2800, abs=1)
    assert q4.texts[0].size_y == approx(390, abs=1)
    assert len(q4.checkboxes) == approx(1)

    # q2: one 5x5 table + 1 checkbox
    q2 = by_num[2]
    assert len(q2.tables) == approx(1)
    t2 = q2.tables[0]
    assert t2.page == approx(1)
    assert list(t2.columns) == ["immer", "oft", "gelegentlich", "einmalig", "-"]
    assert list(t2.rows) == ["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"]
    for sx in t2.size_x:
        assert sx == approx(480, abs=1)
    assert t2.size_y == approx(600, abs=1)  # 5 rows * 120 px
    assert len(q2.checkboxes) == approx(1)

    # q5: one 5x10 table + 1 checkbox (the table is split across pages 1+2)
    q5 = by_num[5]
    assert len(q5.tables) == approx(1)
    t5 = q5.tables[0]
    assert t5.page == approx(1)  # anchored at row 0's page
    assert len(t5.columns) == approx(5)
    assert list(t5.rows) == [
        "Kreis", "Dreieck", "Quadrat", "Herz", "Stern",
        "Pfeil", "Linie", "Punkt", "Wellenlinie", "Sonstiges",
    ]
    for sx in t5.size_x:
        assert sx == approx(480, abs=1)
    assert t5.size_y == approx(1200, abs=1)  # 10 rows * 120 px
    assert len(q5.checkboxes) == approx(1)

    # the q5 checkcells really span both pages (auto-paginated page break)
    q5_pages = {e.page for e in exported["layout"].elements
                if e.kind == "checkcell" and e.question == 5}
    assert q5_pages == {1, 2}

    # this form predates the Nummer header row (template(..., num-digits: 0))
    assert template.get_participant_number() is None


def test_positions_are_sane(exported):
    elements = exported["layout"].elements

    # a known checkbox: q1 "ja" sits at the left text edge (dx=-20, i.e. the
    # 25.75 mm left margin, just left of the printed top-left tag center); dy
    # shifted with the 33 mm top margin (it was 556 with the old 28 mm margin)
    ja = next(e for e in elements if e.kind == "checkbox" and e.text == "ja")
    assert ja.dx == approx(-20, abs=2)
    assert ja.dy == approx(655, abs=2)
    assert ja.w == approx(60, abs=1)
    assert ja.h == approx(70, abs=1)

    # every element lands inside the deskewed page (A4 @ 500 dpi = 4134x5847)
    # (bounds check, so plain comparisons -- approx only supports ==);
    # dx may be slightly negative: the text edge is a bit left of the tag
    for e in elements:
        assert -200 <= e.dx <= 3500
        assert -10 <= e.dy <= 5200
