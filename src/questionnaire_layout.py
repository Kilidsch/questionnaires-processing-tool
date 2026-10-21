"""Layout schema, conversion, and legacy-Template loader for extracted Typst
questionnaires.

This module lives in the processing tool's ``src/`` package next to
``survey_templates.py``: it turns a Typst-authored questionnaire into the
legacy ``Template`` objects the GUI and the detector use.

Pipeline this module supports:

    typst doc --(compile + eval)--> raw records (page, x_pt, y_pt, value)
        --records_to_layout-->  Layout (validated, deskewed px, ints)
        --build_template----->  legacy ``Template`` (from survey_templates.py)

``survey_templates.py`` is still loaded by file path (see
``_load_survey_templates``) rather than as ``src.survey_templates``, so this
module does not depend on how the tool package is imported. That produces a
*separate* module instance: compare templates behaviourally, not with
``isinstance`` against ``src.survey_templates.Template``.

Coordinate conventions (see NOTES.md "Coordinate space"):
    * The detection space is A4 rendered at 500 dpi, deskewed so the four
      page-corner ArUco tags land on fixed centers. The top-left tag center is
      the anchor ``(ANKER_X, ANKER_Y) = (645, 375)`` px.
    * An element's ``(dx, dy)`` is its offset from that anchor, so
      ``absolute px = (ANKER_X + dx, ANKER_Y + dy)``.
    * ``1 px = 25.4 / 500 mm`` and ``1 pt = 500 / 72 px``, so a Typst length in
      pt converts to deskewed px by multiplying by ``PX_PER_PT``.

All ``dx`` / ``dy`` / sizes in the :class:`Layout` are **ints** (rounded),
matching the legacy integer coordinate system the detector consumes (it casts
``dx`` / ``dy`` with ``int()`` and uses ``size_x`` / ``size_y`` directly as
numpy slice bounds, which require ints).
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# --- coordinate constants (must match deskew() in the processing tool) -----
DPI = 500
PX_PER_PT = DPI / 72.0
ANKER_X = 645  # top-left ArUco tag center, px (AnkerPos.X)
ANKER_Y = 375  # top-left ArUco tag center, px (AnkerPos.Y)

# --- import of the legacy template classes --------------------------------
_ROOT = Path(__file__).resolve().parent
_LEGACY_SURVEY = _ROOT / "survey_templates.py"


def _load_survey_templates():
    """Load ``survey_templates.py`` by path (no sys.path edit, no
    namespace-package ambiguity)."""
    if not _LEGACY_SURVEY.is_file():
        raise ImportError(f"survey_templates not found at {_LEGACY_SURVEY}")
    spec = importlib.util.spec_from_file_location("survey_templates", _LEGACY_SURVEY)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build a module spec for {_LEGACY_SURVEY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_st = _load_survey_templates()
AnkerPos = _st.AnkerPos
Checkbox = _st.Checkbox
Freetext = _st.Freetext
ParticipantNumber = _st.ParticipantNumber
Question = _st.Question
Template = _st.Template
CheckTable = _st.CheckTable
# the detection tool's entry point (initType / get_page_bounds / get_question_top)
GrabExperiment = _st.GrabExperiment


# --- Pydantic schema for the layout JSON -----------------------------------
class _BaseElem(BaseModel):
    # Shared by every element: the page it landed on (auto-pagination), and its
    # deskewed top-left offset from the top-left tag anchor, in whole px.
    page: int
    dx: int
    dy: int


class CheckboxElem(_BaseElem):
    kind: Literal["checkbox"]
    question: int | None = None
    text: str
    # drawn box size in px (the detector hard-codes 60x70, kept here to verify)
    w: int
    h: int


class FreetextElem(_BaseElem):
    kind: Literal["freetext"]
    question: int | None = None
    w: int
    h: int


class CheckCellElem(_BaseElem):
    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["checkcell"]
    question: int | None = None
    # index of the table within its question (disambiguates several tables)
    table: int | None = None
    row: int
    col: int
    row_label: str = Field(alias="row-label")
    col_label: str = Field(alias="col-label")
    # one cell's size in px (uniform over a table)
    w: int
    h: int


class QuestionElem(_BaseElem):
    kind: Literal["question"]
    num: int
    # the question body text (the .typ source is the text source of truth)
    text: str


class ParticipantNumberElem(_BaseElem):
    kind: Literal["participant-number"]
    # number of digit boxes in the header row (the JSON records it for the future;
    # the legacy ParticipantNumber class only carries the area)
    digits: int = 0
    w: int
    h: int


Element = Annotated[
    Union[
        CheckboxElem,
        FreetextElem,
        CheckCellElem,
        QuestionElem,
        ParticipantNumberElem,
    ],
    Field(discriminator="kind"),
]


class Layout(BaseModel):
    """A full questionnaire layout extracted from a compiled Typst document."""

    # the source .typ file (name) this layout came from
    doc: str
    # total page count of the compiled PDF
    pages: int
    elements: list[Element]


# --- conversion: raw typst eval records -> Layout --------------------------
def records_to_layout(records: list[dict], doc: str, pages: int) -> Layout:
    """Convert raw ``typst eval`` records into a validated :class:`Layout`.

    Each record is ``{"value": {...}, "page": int, "x": pt, "y": pt}`` where
    ``x`` / ``y`` are page-absolute pt (origin = page top-left). We convert to
    deskewed px, then to a whole-pixel offset from the top-left tag anchor.
    """
    elements = []
    for rec in records:
        v = rec["value"]
        kind = v["kind"]
        # round the absolute position to the nearest pixel, then take the
        # offset from the anchor (the anchor is exactly on a pixel).
        dx = round(rec["x"] * PX_PER_PT) - ANKER_X
        dy = round(rec["y"] * PX_PER_PT) - ANKER_Y
        base = {"kind": kind, "page": rec["page"], "dx": dx, "dy": dy}

        if kind == "checkbox":
            base.update(
                question=v.get("question"),
                text=v["text"],
                w=round(v["w"] * PX_PER_PT),
                h=round(v["h"] * PX_PER_PT),
            )
        elif kind == "freetext":
            base.update(
                question=v.get("question"),
                w=round(v["w"] * PX_PER_PT),
                h=round(v["h"] * PX_PER_PT),
            )
        elif kind == "checkcell":
            base.update(
                question=v.get("question"),
                table=v.get("table"),
                row=v["row"],
                col=v["col"],
                **{"row-label": v["row-label"], "col-label": v["col-label"]},
                w=round(v["w"] * PX_PER_PT),
                h=round(v["h"] * PX_PER_PT),
            )
        elif kind == "question":
            base.update(num=v["num"], text=v["text"])
        elif kind == "participant-number":
            base.update(
                digits=v.get("digits", 0),
                w=round(v["w"] * PX_PER_PT),
                h=round(v["h"] * PX_PER_PT),
            )
        else:
            raise ValueError(f"unknown element kind: {kind!r}")

        elements.append(base)

    return Layout(doc=doc, pages=pages, elements=elements)


def load_layout(path: str | Path) -> Layout:
    """Read and validate a ``*_layout.json`` file produced by
    ``scripts/export_layout.py``."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Layout.model_validate(data)


# --- loader: Layout -> legacy Template -------------------------------------
class LayoutTemplate(Template):
    """A concrete :class:`Template` built from an extracted layout.

    Fills in the questions (with their checkboxes / freetext / check tables)
    and the page count; there is no participant-number box or diagram in the
    Typst templates yet, so those return ``None`` / empty.
    """

    def __init__(
        self,
        questions: Sequence[Question],
        num_pages: int,
        participant_number: ParticipantNumber | None = None,
    ) -> None:
        self.questions = list(questions)
        self._num_pages = num_pages
        self._participant_number = participant_number

    def get_num_pages(self) -> int:
        return self._num_pages

    def get_questions(self) -> Sequence[Question]:
        return self.questions

    def get_participant_number(self) -> ParticipantNumber | None:
        return self._participant_number


def _element_sort_key(e) -> tuple:
    # natural top-to-bottom, left-to-right reading order
    return (e.page, e.dy, e.dx)


def _build_checktable(cells: list[CheckCellElem]) -> CheckTable:
    """Group the checkcell elements of one (question, table) into a single
    legacy :class:`CheckTable`.

    ``dx[j]`` is the x offset of column ``j``, ``dy`` is the y offset of row
    0, ``size_x[j]`` is column ``j``'s cell width, and ``size_y`` is the total
    table height (``n_rows * cell_h``). This matches how the detector crops a
    table (``step_y = size_y // len(rows)``).

    Note: if the table was split across a page break by auto-pagination, the
    cells span more than one page; we still emit one table anchored at row 0's
    page (the legacy model has a single page per table). See NOTES.md watch-outs.
    """
    n_rows = max(c.row for c in cells) + 1
    n_cols = max(c.col for c in cells) + 1

    def col_cell(j: int) -> CheckCellElem:
        # prefer the row-0 cell of the column, else any cell in the column
        for c in cells:
            if c.col == j and c.row == 0:
                return c
        return next(c for c in cells if c.col == j)

    dx = [col_cell(j).dx for j in range(n_cols)]
    size_x = [col_cell(j).w for j in range(n_cols)]
    columns = [col_cell(j).col_label for j in range(n_cols)]

    rows = []
    for i in range(n_rows):
        rc = next(c for c in cells if c.row == i)
        rows.append(rc.row_label)

    # reference cell for the table's page and top (row 0, col 0)
    ref = next((c for c in cells if c.row == 0 and c.col == 0), cells[0])
    page = ref.page
    dy = ref.dy
    size_y = n_rows * ref.h

    return CheckTable(
        page=page,
        dx=dx,
        dy=dy,
        size_x=size_x,
        size_y=size_y,
        columns=columns,
        rows=rows,
    )


def build_template(layout: Layout) -> LayoutTemplate:
    """Build a legacy :class:`Template` from a validated :class:`Layout`.

    Checkboxes / freetext are attached to their question by the element's
    ``question`` number; checkcells are grouped per (question, table) into one
    :class:`CheckTable` each. Question body text comes from the ``question``
    metadata records.
    """
    qtext: dict[int, str] = {}
    boxes: dict[int, list[Checkbox]] = {}
    texts: dict[int, list[Freetext]] = {}
    cells: dict[tuple, list[CheckCellElem]] = {}
    participant_numbers: list[ParticipantNumberElem] = []

    for e in layout.elements:
        if isinstance(e, QuestionElem):
            qtext[e.num] = e.text
        elif isinstance(e, CheckboxElem):
            if e.question is None:
                continue
            boxes.setdefault(e.question, []).append(
                Checkbox(page=e.page, dx=e.dx, dy=e.dy, text=e.text)
            )
        elif isinstance(e, FreetextElem):
            if e.question is None:
                continue
            texts.setdefault(e.question, []).append(
                Freetext(page=e.page, dx=e.dx, dy=e.dy, size_x=e.w, size_y=e.h)
            )
        elif isinstance(e, CheckCellElem):
            if e.question is None:
                continue
            cells.setdefault((e.question, e.table), []).append(e)
        elif isinstance(e, ParticipantNumberElem):
            participant_numbers.append(e)

    tables: dict[int, list[CheckTable]] = {}
    for (qnum, _table_idx), cellem in cells.items():
        tables.setdefault(qnum, []).append(_build_checktable(cellem))

    qnums = set(qtext) | set(boxes) | set(texts) | set(tables)
    questions = [
        Question(
            num=num,
            questionText=qtext.get(num, ""),
            checkboxes=sorted(boxes.get(num, []), key=_element_sort_key),
            texts=sorted(texts.get(num, []), key=_element_sort_key),
            diagramms=[],
            tables=sorted(tables.get(num, []), key=lambda t: (t.page, t.dy)),
        )
        for num in sorted(qnums)
    ]

    if len(participant_numbers) > 1:
        raise ValueError("layout has multiple participant-number elements")
    participant_number = None
    if participant_numbers:
        pn = participant_numbers[0]
        participant_number = ParticipantNumber(
            page=pn.page, dx=pn.dx, dy=pn.dy, size_x=pn.w, size_y=pn.h
        )

    return LayoutTemplate(
        questions=questions,
        num_pages=layout.pages,
        participant_number=participant_number,
    )


__all__ = [
    "DPI",
    "PX_PER_PT",
    "ANKER_X",
    "ANKER_Y",
    "AnkerPos",
    "Checkbox",
    "Freetext",
    "ParticipantNumber",
    "Question",
    "Template",
    "CheckTable",
    "GrabExperiment",
    "Layout",
    "Element",
    "CheckboxElem",
    "FreetextElem",
    "CheckCellElem",
    "QuestionElem",
    "ParticipantNumberElem",
    "LayoutTemplate",
    "records_to_layout",
    "load_layout",
    "build_template",
]
