"""Wiring and regression tests for layout (JSON)-based experiment types.

These cover ``GrabExperiment._layout_files`` and the ``initType`` dispatch, and
guard the constraints every registered layout has to satisfy (valid JSON,
single page per checktable). The legacy types must keep working unchanged.
"""

from collections import defaultdict

import pytest

from src import questionnaire_layout as ql
from src.survey_templates import (
    Bottleneck,
    ExperimentTypes,
    GrabExperiment,
    Rope,
    RopeShort,
)


def test_registered_layout_files_exist():
    assert ExperimentTypes.TEST_E2E in GrabExperiment._layout_files
    for exp_type, path in GrabExperiment._layout_files.items():
        assert path.is_file(), f"missing layout file for {exp_type}: {path}"
        layout = ql.load_layout(path)
        if exp_type == ExperimentTypes.TEST_E2E:
            assert layout.doc == "test_e2e.typ"
            assert layout.pages == 2


def test_init_type_layout():
    # NB: not isinstance(t, src.survey_templates.Template) -- questionnaire_layout
    # loads survey_templates.py by path, so it builds its own Template class.
    template = GrabExperiment.initType("test_e2e")
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == 2

    questions = template.get_questions()
    assert [q.num for q in questions] == [1, 2, 3, 4, 5, 6]
    by_num = {q.num: q for q in questions}
    assert by_num[1].questionText == "Wie haben Sie die Übung insgesamt bewertet?"
    assert by_num[2].questionText == "Welche Tätigkeiten haben Sie während der Übung ausgeführt?"
    assert by_num[5].questionText == "Wie sicher haben Sie sich in jeder Handposition gefühlt?"

    assert set(GrabExperiment.get_page_bounds(template)) == {1, 2}

    # question tops are finite and increase within each page
    tops = [(q.num, GrabExperiment.get_question_top(q)) for q in questions]
    for _, top in tops:
        assert isinstance(top, int)
    page_of = {
        q.num: min(e.page for e in (*q.checkboxes, *q.texts, *q.tables)) for q in questions
    }
    for page in set(page_of.values()):
        page_tops = [top for num, top in tops if page_of[num] == page]
        assert page_tops == sorted(page_tops), f"question tops not ordered on page {page}"


def test_participant_number_wired():
    pn = GrabExperiment.initType("test_e2e").get_participant_number()
    assert pn is not None
    assert pn.page == 1
    assert pn.size_x == 660
    assert pn.size_y == 200


def test_legacy_types_unchanged():
    for exp_type, cls in (
        (ExperimentTypes.ROPE, Rope),
        (ExperimentTypes.BOTTLENECK, Bottleneck),
        (ExperimentTypes.ROPE_SHORT, RopeShort),
    ):
        template = GrabExperiment.initType(exp_type)
        assert isinstance(template, cls)
        assert template.get_num_pages() == cls().get_num_pages()
        assert template.get_participant_number() is not None


def test_unknown_type_raises():
    with pytest.raises(RuntimeError):
        GrabExperiment.initType("does_not_exist")


def test_single_page_tables_all_layouts():
    """Every registered layout must keep each checktable on one page: the
    legacy CheckTable model has a single page and cannot represent a split."""
    for exp_type, path in GrabExperiment._layout_files.items():
        layout = ql.load_layout(path)
        pages = defaultdict(set)
        for e in layout.elements:
            if e.kind == "checkcell":
                pages[(e.question, e.table)].add(e.page)
        for key, table_pages in pages.items():
            assert len(table_pages) == 1, (
                f"{exp_type}: table {key} split across pages {sorted(table_pages)}"
            )


def test_missing_layout_file_raises(monkeypatch, tmp_path):
    monkeypatch.setitem(
        GrabExperiment._layout_files,
        ExperimentTypes.TEST_E2E,
        tmp_path / "does_not_exist.json",
    )
    with pytest.raises(RuntimeError):
        GrabExperiment.initType("test_e2e")
