"""GUI widgets of layout-based forms, built headless (see conftest.py)."""

from src.guiWidgets import BoundCheckBox, BoundCheckTableWidget, QuestionWidget
from src.survey_templates import GrabExperiment


def test_check_table_without_diagram(qt_errors):
    # test_e2e Q5 has a check table but no body diagram; area_grabbing still
    # writes a "diagram" entry for every question
    question = {q.num: q for q in GrabExperiment.initType("test_e2e").get_questions()}[5]
    table = question.tables[0]
    row, column = table.rows[0], table.columns[1]
    question_json = {
        "question": question.questionText,
        "table": [{"name": "Table_2_5", "data": {r: {} for r in table.rows}}],
        "diagram": {"file": ""},
    }

    widget = QuestionWidget(question, question_json, 800)
    focused = []
    widget.elementFocused.connect(focused.append)

    [table_widget] = widget.findChildren(BoundCheckTableWidget)
    cells = table_widget.findChildren(BoundCheckBox)
    assert len(cells) == len(table.rows) * len(table.columns)

    cells[1].setChecked(True)
    assert question_json["table"][0]["data"][row] == {column: True}
    cells[1].setChecked(False)
    assert question_json["table"][0]["data"][row] == {}

    # the highlighted area is the cell, not the whole table
    cells[1].clicked.emit()
    assert (focused[-1].page, focused[-1].dx, focused[-1].dy) == (table.page, table.dx[1], table.dy)


def test_check_table_without_detection(qt_errors):
    question = {q.num: q for q in GrabExperiment.initType("test_e2e").get_questions()}[5]
    question_json = {"question": question.questionText, "table": {"name": "", "data": {}}}

    QuestionWidget(question, question_json, 800)
    assert question_json["table"] == [{"name": "", "data": {}}]
