"""Wiring and regression tests for layout (JSON)-based experiment types.

These cover the ``initType`` dispatch (built-in layouts in ``src/layouts/``,
explicit layout files, legacy types), the metadata-based lookup the GUI uses, and
the CLI side in ``prepareData.py``. Every built-in layout is checked against the
constraints a layout has to satisfy (valid JSON, single page per checktable), so
adding a form needs no new test. The legacy types must keep working unchanged.
"""

import json
import shutil
from collections import defaultdict
from pathlib import Path

import pytest
from pydantic import ValidationError

import prepareData
from src import questionnaire_layout as ql
from src.survey_templates import (
    Bottleneck,
    ExperimentTypes,
    GrabExperiment,
    Rope,
    RopeShort,
)

TEST_E2E_LAYOUT = GrabExperiment.layoutDir / "test_e2e_layout.json"


def test_builtin_layouts_found():
    assert {"test_e2e", "messwerte_xsens"} <= set(GrabExperiment.layout_types())
    assert GrabExperiment.find_layout("test_e2e") == TEST_E2E_LAYOUT
    assert GrabExperiment.find_layout("does_not_exist") is None


@pytest.mark.parametrize("exp_type", GrabExperiment.layout_types())
def test_builtin_layout_valid(exp_type):
    path = GrabExperiment.find_layout(exp_type)
    layout = ql.load_layout(path)
    # the type name comes from the file name, which export_layout.py derives from the document
    assert Path(layout.doc).stem == exp_type

    template = GrabExperiment.initType(exp_type)
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == layout.pages
    assert template.get_questions()


@pytest.mark.parametrize("exp_type", GrabExperiment.layout_types())
def test_single_page_tables(exp_type):
    """Every layout must keep each checktable on one page: the legacy CheckTable
    model has a single page and cannot represent a split."""
    layout = ql.load_layout(GrabExperiment.find_layout(exp_type))
    pages = defaultdict(set)
    for e in layout.elements:
        if e.kind == "checkcell":
            pages[(e.question, e.table)].add(e.page)
    for key, table_pages in pages.items():
        assert len(table_pages) == 1, (
            f"{exp_type}: table {key} split across pages {sorted(table_pages)}"
        )


def test_messwerte_layout_wired():
    template = GrabExperiment.initType("messwerte_xsens")
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == 1
    assert [q.num for q in template.get_questions()] == [1, 2]

    # the ID row sits in the top page margin, above the printed tag anchor
    pn = template.get_participant_number()
    assert pn is not None
    assert pn.page == 1
    assert pn.dy < 0
    assert pn.size_x == 660
    assert pn.size_y == 200

    by_num = {q.num: q for q in template.get_questions()}
    assert by_num[1].questionText == "Angaben zur Person"
    assert by_num[2].questionText == "Körpermaße"
    assert [cb.text for cb in by_num[1].checkboxes] == ["männlich", "weiblich", "divers"]
    assert len(by_num[2].texts) == 15


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
    with pytest.raises(RuntimeError, match="test_e2e"):
        GrabExperiment.initType("does_not_exist")


# --- explicit layout files --------------------------------------------------
def test_explicit_layout_relative_to_base_dir(tmp_path):
    shutil.copyfile(TEST_E2E_LAYOUT, tmp_path / "layout.json")
    template = GrabExperiment.initType("any_name", "layout.json", tmp_path)
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == 2


def test_explicit_layout_wins_over_type():
    template = GrabExperiment.initType("rope", TEST_E2E_LAYOUT)
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == 2


def test_missing_layout_file_raises(tmp_path):
    with pytest.raises(RuntimeError):
        GrabExperiment.initType("test_e2e", tmp_path / "does_not_exist.json")


def test_init_from_metadata(tmp_path):
    shutil.copyfile(TEST_E2E_LAYOUT, tmp_path / "layout.json")
    metadata = {"Experiment": {"Type": "my_form", "Layout": "layout.json"}}

    template = GrabExperiment.initFromMetadata(metadata, tmp_path)
    assert isinstance(template, ql.Template)
    assert template.get_num_pages() == 2
    # a survey without its own form uses the experiment's
    assert GrabExperiment.initFromMetadata(metadata, tmp_path, {"status": "Open"}).get_num_pages() == 2
    # a survey with its own type does not inherit the experiment's layout
    assert isinstance(GrabExperiment.initFromMetadata(metadata, tmp_path, {"type": "rope"}), Rope)
    # legacy metadata without a layout still resolves built-in layouts by name
    legacy = {"Experiment": {"Type": "test_e2e"}}
    assert GrabExperiment.initFromMetadata(legacy, tmp_path).get_num_pages() == 2


# --- prepareData.py CLI -----------------------------------------------------
def test_resolve_experiment():
    assert prepareData.resolve_experiment("rope") == ("rope", None)
    assert prepareData.resolve_experiment("test_e2e") == ("test_e2e", TEST_E2E_LAYOUT)
    # a path: the type is named after the Typst document
    assert prepareData.resolve_experiment(str(TEST_E2E_LAYOUT)) == ("test_e2e", TEST_E2E_LAYOUT)
    with pytest.raises(RuntimeError):
        prepareData.resolve_experiment("does_not_exist")
    with pytest.raises(RuntimeError):
        prepareData.resolve_experiment("does_not_exist.json")


def test_resolve_experiment_invalid_layout(tmp_path):
    bad = tmp_path / "bad_layout.json"
    bad.write_text('{"doc": "bad.typ"}', encoding="utf-8")
    with pytest.raises(ValidationError):
        prepareData.resolve_experiment(str(bad))


def test_write_metadata(tmp_path):
    metadataFile = prepareData.write_metadata(str(tmp_path), "test_e2e", TEST_E2E_LAYOUT)
    with open(metadataFile, encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["Experiment"] == {"Type": "test_e2e", "Name": "", "Layout": "layout.json"}
    assert (tmp_path / "layout.json").read_bytes() == TEST_E2E_LAYOUT.read_bytes()
    assert GrabExperiment.initFromMetadata(metadata, tmp_path).get_num_pages() == 2

    # a re-run keeps the surveys, also when given the copy itself
    metadata["surveyResponses"] = {"surveyResponse_001": {"status": "Done"}}
    with open(metadataFile, "w", encoding="utf-8") as f:
        json.dump(metadata, f)
    prepareData.write_metadata(str(tmp_path), "test_e2e", tmp_path / "layout.json")
    with open(metadataFile, encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["surveyResponses"] == {"surveyResponse_001": {"status": "Done"}}
    assert metadata["Experiment"]["Layout"] == "layout.json"

    # switching to a legacy type drops the layout reference
    prepareData.write_metadata(str(tmp_path), "rope", None)
    with open(metadataFile, encoding="utf-8") as f:
        metadata = json.load(f)
    assert "Layout" not in metadata["Experiment"]
    assert isinstance(GrabExperiment.initFromMetadata(metadata, tmp_path), Rope)
