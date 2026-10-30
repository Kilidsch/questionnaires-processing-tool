"""Headless smoke test of the annotation GUI (see conftest.py): builds a processed
experiment directory like prepareData.py does, opens the survey window from the
main window and finishes it, for every layout-based form.

The legacy forms are not covered: their body-diagram widget needs
src/outline_figures.pickle, which prepareData.py generates from a scanned diagram.
"""

import json
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytest

import prepareData
from src import questionnaire_layout as ql
from src.area_grabbing import parse_single_data
from src.survey_templates import GrabExperiment

PDF = Path(__file__).resolve().parent / "fixtures" / "test_e2e.pdf"
# A4 at 500 dpi
PAGE_SIZE = (5846, 4134)


def blank_pages(num_pages):
    # no corner tags: deskew fails and nothing is detected, like an unusable scan
    return [np.full((*PAGE_SIZE, 3), 255, np.uint8) for _ in range(num_pages)]


def rendered_pages():
    doc = fitz.open(PDF)
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=ql.DPI)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
        imgs.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    doc.close()
    return imgs


def make_experiment(expDir: Path, expType: str, imgs) -> Path:
    """Experiment directory with one survey, as prepareData.py leaves it."""
    expType, layoutPath = prepareData.resolve_experiment(expType)
    surveyDir = expDir / "surveyResponse_001"
    surveyDir.mkdir(parents=True)
    files = []
    for i, img in enumerate(imgs, start=1):
        name = f"page-{i:03}.jpg"
        cv2.imwrite(str(surveyDir / name), img)
        files.append(name)
    template = GrabExperiment.initType(expType, layoutPath)
    dataFile = parse_single_data(str(surveyDir), files, template)

    metadataFile = prepareData.write_metadata(str(expDir), expType, layoutPath)
    with open(metadataFile, encoding="utf-8") as f:
        metadata = json.load(f)
    metadata["participants"] = 1
    metadata["surveyResponses"] = {
        "surveyResponse_001": {"status": "Open", "dir": str(surveyDir), "dataFile": dataFile}
    }
    with open(metadataFile, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    return surveyDir


def open_and_finish(expDir: Path, qt_app):
    from src import guiWindows

    main = guiWindows.MainWindow(str(expDir))
    main.open_survey("surveyResponse_001")
    qt_app.processEvents()  # the window fills itself on its first resizeEvent
    survey = main.surveyWindow

    template = survey.typeTemplate
    assert survey.flag_containersInit
    assert len(survey.pageWidgets) == template.get_num_pages()
    num_widgets = len(template.get_questions()) + (template.get_participant_number() is not None)
    assert len(survey.questions) == num_widgets

    survey.done()  # saves surveyData.json and the status in metadata.json
    qt_app.processEvents()
    with open(expDir / "metadata.json", encoding="utf-8") as f:
        assert json.load(f)["surveyResponses"]["surveyResponse_001"]["status"] == "Done"
    main.close()


@pytest.mark.parametrize("expType", GrabExperiment.layout_types())
def test_survey_window_blank_scan(expType, tmp_path, qt_app, qt_errors):
    num_pages = GrabExperiment.initType(expType).get_num_pages()
    make_experiment(tmp_path, expType, blank_pages(num_pages))
    open_and_finish(tmp_path, qt_app)


def test_survey_window_detected_scan(tmp_path, qt_app, qt_errors):
    # the reference form with real detection results (tables as lists, deskewed pages)
    surveyDir = make_experiment(tmp_path, "test_e2e", rendered_pages())
    with open(surveyDir / "surveyData.json", encoding="utf-8") as f:
        assert isinstance(json.load(f)["5"]["table"], list)
    open_and_finish(tmp_path, qt_app)


def test_qt_errors_catches_callback_exceptions(qt_app, qt_errors):
    # without the recording hook this would abort the whole test run
    from PyQt5 import QtWidgets as qtWid

    class Broken(qtWid.QWidget):
        def resizeEvent(self, event):
            raise ValueError("boom")

    w = Broken()
    w.resize(10, 10)
    w.show()
    qt_app.processEvents()
    w.close()
    assert len(qt_errors) == 1 and "boom" in qt_errors[0]
    qt_errors.clear()  # expected here, so do not fail the test
