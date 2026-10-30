# MIT License
# Copyright (c) 2026 Alexandra Mielke & Marvin Lorber

__license__ = "MIT"
__author__ = ["Alexandra Mielke", "Marvin Lorber"]

import sys
import os
from PyQt5 import QtWidgets as qtWid
from PyQt5 import QtGui, QtCore

import qdarktheme

from src.survey_templates import GrabExperiment, AnkerPos
from src.guiWidgets import ImagePage, NoHorizontalScrollArea, ParticipantNumberWidget, QuestionWidget, SnappingScrollBar, SurveyEntryWidget
from src.guiIO import readData, saveData

# ---------------------------
# Survey Checking Window
# ---------------------------

class SurveyWindow(qtWid.QWidget):
    # add signal to send out once survey is closed
    surveyClosed = QtCore.pyqtSignal(str, str)

    def __init__(self, name, dataDir, typeTemplate, status):
        super().__init__()

        self.name = name
        self.status = status
        self.dataDir = dataDir

        # General data handling
        self.dataPath = os.path.join(self.dataDir, "surveyData.json")
        self.data = readData(self.dataPath)
        self.pages = []
        self.typeTemplate = typeTemplate

        # QT GUI stuff
        self.setWindowTitle(name)
        mainLayout = qtWid.QVBoxLayout()
        self.flag_containersInit = False # we init later, so flag needed
        screen = QtGui.QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry() 
        self.maxWidgetWidth = int(geometry.width() * 0.45)

        # --------------------- BUTTONS AT THE TOP ----------------
        buttonLayout = qtWid.QHBoxLayout()

        noMoreTimeButton = qtWid.QPushButton("Not done yet, but go back")
        noMoreTimeButton.clicked.connect(self.go_back)
        buttonLayout.addWidget(noMoreTimeButton)

        doneButton = qtWid.QPushButton("Done")
        doneButton.clicked.connect(self.done)
        buttonLayout.addWidget(doneButton)

        weirdButton = qtWid.QPushButton("Report weird things and go back")
        weirdButton.clicked.connect(self.reportWeirdness)
        buttonLayout.addWidget(weirdButton)

        mainLayout.addLayout(buttonLayout)
        self.buttonLayout = buttonLayout

        # Save shortcut
        saveShortcut = qtWid.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        saveShortcut.activated.connect(self.save)

        # ------- CONTAINER FOR IMAGES AND QUESTIONS --------------
        contentLayout = qtWid.QHBoxLayout()

        self.questionContainer = qtWid.QWidget()
        self.questionLayout = qtWid.QVBoxLayout(self.questionContainer)
        self.questionLayout.setContentsMargins(0, 0, 0, 0)
        self.questionLayout.setSpacing(6)
        self.questionScroll = NoHorizontalScrollArea()
        self.questionScroll.setWidget(self.questionContainer)
        self.questionScroll.setWidgetResizable(True)
        self.questionScroll.setSizePolicy(qtWid.QSizePolicy.Preferred, qtWid.QSizePolicy.Expanding)

        self.imageScroll = qtWid.QScrollArea()
        self.imageScroll.setWidgetResizable(True)

        self.imageContainer = qtWid.QWidget()
        self.imageContainer.setSizePolicy(
            qtWid.QSizePolicy.Expanding,   
            qtWid.QSizePolicy.Preferred    # do not expand more than vertically available
        )
        imageLayout = qtWid.QVBoxLayout(self.imageContainer)
        imageLayout.addStretch()
        self.imageScroll.setWidget(self.imageContainer)

        # ---- ADD LAYOUTS AND SHOW ----
        contentLayout.addWidget(self.questionScroll, 1)
        contentLayout.addWidget(self.imageScroll, 1)

        mainLayout.addLayout(contentLayout)
        self.margins = mainLayout.getContentsMargins()
        self.setLayout(mainLayout)

        self.showMaximized()

    def resizeEvent(self, event):
        """This is called every time the window is resized, e.g. also when
        layout is settled after calling showMaximized(), so we use to init content.
        """
        super().resizeEvent(event)
        if not self.flag_containersInit:
            self.init_questions()
            self.init_images()
            self.flag_containersInit = True
    
    # ----------- RETURN HANDLING ----------------------------
    def save(self):
        saveData(self.dataPath, self.data)

    def go_back(self):
        self.save()
        self.surveyClosed.emit(self.name, self.status)
        self.close()

    def reportWeirdness(self):
        if "comment" in self.data:
            lastComment = self.data["comment"]
        else:
            lastComment = ""
        self.commentWindow = CommentWindow(lastComment)
        self.commentWindow.commentClosed.connect(self.updateComment)
        self.commentWindow.show()

    def updateComment(self, comment: str):
        self.status = "Needs checking"
        self.data["comment"] = comment
        self.go_back()

    def done(self):
        self.status = "Done"
        self.go_back()

    # ----------- IMAGE HANDLING ------------------------------
    def init_images(self):
        nr_pages = self.typeTemplate.get_num_pages()

        self.pageWidgets = []
        for i in range(1, nr_pages + 1):
            path = os.path.join(self.dataDir, f"page-{i:03}.jpg")
            pix = QtGui.QPixmap(path)

            # Draw red squares for detected checkboxes
            painter = QtGui.QPainter(pix)
            pen = QtGui.QPen(QtGui.QColor("red"), 8)
            painter.setPen(pen)
            for question in self.typeTemplate.get_questions():
                q_json = self.data.get(str(question.num), {})
                cb_jsons = q_json.get("checkboxes")
                if cb_jsons is None:
                    cb_jsons = [{"answer": False} for _ in question.checkboxes]
                for cb_template, cb_json in zip(question.checkboxes, cb_jsons):
                    if cb_json.get("answer") and cb_template.page == i:
                        left = int(AnkerPos.X.value + cb_template.dx)
                        top = int(AnkerPos.Y.value + cb_template.dy)
                        painter.drawRect(left, top, 60, 70)
            painter.end()

            if i == 1:
                scale = self.maxWidgetWidth / pix.width()

            pix = pix.scaled(
                int(pix.width() * scale),
                int(pix.height() * scale),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

            page = ImagePage(pix, i)
            page.scale = scale

            self.pageWidgets.append(page)
            self.imageScroll.widget().layout().addWidget(page)

        scroll_ticks_right = [int(tick * scale) for tick in self.scroll_ticks_right]
        self.imageScrollBar = SnappingScrollBar(scroll_ticks_right)
        self.imageScroll.setVerticalScrollBar(self.imageScrollBar)
        self.imageScroll.setWidget(self.imageContainer)
        self.imageScroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def highlight_element(self, element):
        page = element.page

        for p in self.pageWidgets:
            p.set_highlight(None)

        page_widget = self.get_page_widget(page)
        if page_widget is None:
            return

        if hasattr(element, "size_x"):
            w = element.size_x
            h = element.size_y
        else:
            w = 60
            h = 70

        rect = QtCore.QRect(
            int((element.dx + AnkerPos.X.value) * page_widget.scale),
            int((element.dy + AnkerPos.Y.value) * page_widget.scale),
            int(w * page_widget.scale),
            int(h * page_widget.scale),
        )
        page_widget.set_highlight(rect)
        self.center_on(page_widget, rect)

    def get_page_widget(self, page):
        return self.pageWidgets[page - 1]

    def get_page_widget_heights(self):
        heights = {}
        for qw in self.questions:
            elements = []
            elements.extend(qw.question.checkboxes)
            if hasattr(qw.question, "texts"):
                elements.extend(qw.question.texts)

            pages = {e.page for e in elements}
            for p in pages:
                heights.setdefault(p, 0)
                heights[p] += qw.sizeHint().height()

        return heights

    def compute_page_scales(self):
        page_template_heights = {}
        page_gui_heights = {}
        for q in self.questions:
            page = q.template_page

            template_h = q.template_bottom - q.template_top
            gui_h = q.height()

            page_template_heights.setdefault(page, 0)
            page_gui_heights.setdefault(page, 0)

            page_template_heights[page] += template_h
            page_gui_heights[page] += gui_h

        scales = {}
        for p in page_template_heights:
            scales[p] = page_gui_heights[p] / page_template_heights[p]
        return scales

    def center_on(self, page_widget, rect):
        """Move image so it centers on page_widget"""
        scroll = self.imageScroll.verticalScrollBar()
        y = page_widget.y() + rect.y()
        scroll.setValue(y - self.imageScroll.height() // 2)

    # ----------- QUESTION HANDLING ------------------------------
    def init_questions(self):
        # Example questions
        self.questions = []
        questions = self.typeTemplate.get_questions()

        scroll_ticks_left = []
        self.scroll_ticks_right = [] #we need these later for the image
        bottom_of_last_question = 0

        # participant number is written at the top of the form, so it comes first
        widgets = []
        participantNr = self.typeTemplate.get_participant_number()
        if participantNr is not None:
            top = participantNr.dy + (participantNr.page - 1) * 5850
            widgets.append((ParticipantNumberWidget(participantNr, self.data), top))
        for q in questions:
            q_json = self.data[str(q.num)]
            qw = QuestionWidget(q, q_json, self.maxWidgetWidth)
            widgets.append((qw, GrabExperiment.get_question_top(q)))

        for qw, current_top in widgets:
            scroll_ticks_left.append(bottom_of_last_question)
            self.scroll_ticks_right.append(max(0, int(current_top)))
            qw.elementFocused.connect(self.highlight_element)
            self.questions.append(qw)
            self.questionLayout.addWidget(qw)
            bottom_of_last_question = bottom_of_last_question + qw.sizeHint().height()

        self.questionLayout.addStretch()

        
        
        
        self.questionScrollBar = SnappingScrollBar(scroll_ticks_left)
        self.questionScroll.setVerticalScrollBar(self.questionScrollBar)

        self.questionContainer.setLayout(self.questionLayout)
        self.questionContainer.setSizePolicy(
            qtWid.QSizePolicy.Expanding,
            qtWid.QSizePolicy.Maximum
        )
        self.questionScroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Down:
            self.jump_question(+1)

        elif e.key() == QtCore.Qt.Key_Up:
            self.jump_question(-1)

        else:
            super().keyPressEvent(e)

    def jump_question(self, direction):
        focus = self.focusWidget()

        for i, q in enumerate(self.questions):
            if q.isAncestorOf(focus):
                new_i = max(0, min(len(self.questions) - 1, i + direction))
                next_q = self.questions[new_i]
                self.scroll_to_question(next_q)

                # focus first widget in question
                child = next_q.findChild((qtWid.QCheckBox, qtWid.QTextEdit, qtWid.QLineEdit))
                if child:
                    child.setFocus()
                break

    def scroll_to_question(self, qwidget):
        """Move questionScroll so it center on the current question"""
        bar = self.questionScroll.verticalScrollBar()
        y = qwidget.y()
        bar.setValue(y - self.questionScroll.height() // 2)

# ---------------------------
# Comment Window
# ---------------------------

# Basic comment input window that returns comment once it's closed
class CommentWindow(qtWid.QWidget):
    # signal to be send once comment is closed
    commentClosed = QtCore.pyqtSignal(str)

    def __init__(self, lastComment):
        super().__init__()

        self.comment = lastComment

        mainLayout = qtWid.QVBoxLayout()
        self.setWindowTitle("Add comment")
        qtWid.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self, self.done)

        doneButton = qtWid.QPushButton("Done")
        doneButton.clicked.connect(self.done)
        mainLayout.addWidget(doneButton)

        self.textBox = qtWid.QTextEdit("Comment")
        self.textBox.setPlainText(lastComment)
        self.textBox.textChanged.connect(self.changeComment)
        mainLayout.addWidget(self.textBox)

        self.setLayout(mainLayout)
        self.showMaximized()

    def done(self):
        self.commentClosed.emit(self.comment)
        self.close()

    def changeComment(self):
        self.comment = self.textBox.toPlainText()


# ---------------------------
# Main Window
# ---------------------------


class MainWindow(qtWid.QWidget):
    # key of the survey status in metadata.json and window used to annotate a survey
    statusKey = "status"
    surveyWindowClass = SurveyWindow

    def __init__(self, experimentDir: str):
        super().__init__()

        self.metadataPath = os.path.join(experimentDir, "metadata.json")
        self.metadata = readData(self.metadataPath)
        self.experimentDir = experimentDir
        self.surveyWindow = None
        self.sortMode = "Status"

        # QT stuff
        self.setWindowTitle("Survey Digitizer")

        layout = qtWid.QVBoxLayout()

        # ---- SORT BUTTONS ----
        sortLayout = qtWid.QHBoxLayout()
        sortLayout.addWidget(qtWid.QLabel("Sort by:"))
        self.sortButtons = qtWid.QButtonGroup(self)
        for mode in ("Status", "Survey name", "Participant number"):
            button = qtWid.QPushButton(mode)
            button.setCheckable(True)
            button.setChecked(mode == self.sortMode)
            self.sortButtons.addButton(button)
            sortLayout.addWidget(button)
        self.sortButtons.buttonClicked.connect(self.change_sort)
        sortLayout.addStretch()
        self.countLabel = qtWid.QLabel()
        sortLayout.addWidget(self.countLabel)
        layout.addLayout(sortLayout)

        scroll = qtWid.QScrollArea()
        scroll.setWidgetResizable(True)

        container = qtWid.QWidget()
        self.vbox = qtWid.QVBoxLayout()

        self.rebuild_list()

        container.setLayout(self.vbox)
        scroll.setWidget(container)

        layout.addWidget(scroll)
        self.setLayout(layout)

    def get_status(self, surveyMetadata):
        return surveyMetadata.get(self.statusKey, "Open")

    def get_template(self, surveyMetadata):
        # a survey can have another form than the rest of the experiment
        return GrabExperiment.initFromMetadata(self.metadata, self.experimentDir, surveyMetadata)

    def sortSurveys(self):
        # Sort entries
        order = {"Open": 0, "Needs checking": 1, "Done": 2}
        return sorted(
            self.metadata["surveyResponses"].items(),
            key=lambda x: order[self.get_status(x[1])],
        )

    def change_sort(self, button):
        self.sortMode = button.text()
        self.rebuild_list()

    def open_survey(self, name):
        # a second window of the same survey would overwrite the entries of the first one when closed
        if self.surveyWindow is not None and self.surveyWindow.isVisible() and self.surveyWindow.name == name:
            self.surveyWindow.raise_()
            self.surveyWindow.activateWindow()
            return

        self.surveyWindow = self.surveyWindowClass(
            name,
            self.metadata["surveyResponses"][name]["dir"],
            self.get_template(self.metadata["surveyResponses"][name]),
            self.get_status(self.metadata["surveyResponses"][name]),
        )
        self.surveyWindow.surveyClosed.connect(self.update_survey_status)
        self.surveyWindow.show()

    def update_survey_status(self, name, new_status):
        self.metadata["surveyResponses"][name][self.statusKey] = new_status
        saveData(os.path.join(self.experimentDir, "metadata.json"), self.metadata)
        self.rebuild_list()

        # after "Done" or "Report weird things" continue with the next open survey
        if new_status in ("Done", "Needs checking"):
            next_name = self.next_open_survey(name)
            if next_name is not None:
                self.open_survey(next_name)

    def next_open_survey(self, name):
        """Next survey after name (in survey order) that is still open, starting over at the beginning if needed."""
        shown = self.sortSurveys()[: self.metadata["participants"]]
        open_names = sorted(n for n, data in shown if self.get_status(data) == "Open")
        later = [n for n in open_names if n > name]
        if later:
            return later[0]
        return open_names[0] if open_names else None

    def rebuild_list(self):
        # remove old widgets
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        entries = []
        for name, data in self.sortSurveys()[: self.metadata["participants"]]:
            surveyData = readData(os.path.join(data["dir"], data.get("dataFile", "surveyData.json")))
            entries.append((name, data, surveyData.get("participantNr"), surveyData.get("comment", "")))

        # sortSurveys already sorts by status
        if self.sortMode == "Survey name":
            entries.sort(key=lambda e: e[0])
        elif self.sortMode == "Participant number":
            # surveys without a number (None) at the end
            entries.sort(key=lambda e: (e[2] is None, e[2] or 0, e[0]))

        # surveys sharing a participant number, probably a typo in one of them
        surveysByNr = {}
        for name, _, participantNr, _ in entries:
            if participantNr is not None:
                surveysByNr.setdefault(participantNr, []).append(name)

        for name, data, participantNr, comment in entries:
            duplicates = [n for n in surveysByNr.get(participantNr, []) if n != name]
            w = SurveyEntryWidget(name, self.get_status(data), participantNr, comment, duplicates)
            w.clicked.connect(self.open_survey)
            self.vbox.addWidget(w)

        self.vbox.addStretch()

        statuses = [self.get_status(data) for _, data, _, _ in entries]
        done = statuses.count("Done")
        weird = statuses.count("Needs checking")
        self.countLabel.setText(f"Processed: {done + weird} / {len(statuses)}   (done {done}, weird {weird})")


def main(experimentDir, windowClass=MainWindow):
    app = qtWid.QApplication(sys.argv)
    qdarktheme.setup_theme()

    window = windowClass(experimentDir)
    window.resize(900, 600)
    window.show()

    sys.exit(app.exec_())
