# MIT License
# Copyright (c) 2026 Alexandra Mielke & Marvin Lorber

__license__ = "MIT"
__author__ = ["Alexandra Mielke", "Marvin Lorber", "Thomas Chatagnon"]

from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as qtWid
from PIL import Image
import numpy as np
import os
import pickle
from types import SimpleNamespace

from src.survey_templates import DiagramAreas

# -------- Helper --------


def status_color(status):
    if status == "Done":
        return "green"
    if status == "Needs checking":
        return "gold"
    return "grey"


def imgIcon_color(id: int):
    if id == 0:
        return QtGui.QColor(43, 29, 90, 255)
    elif id == 1:
        return QtGui.QColor(162, 150, 202, 255)
    elif id == 2:
        return QtGui.QColor(76, 28, 70, 255)
    elif id == 3:
        return QtGui.QColor(142, 204, 185, 255)
    elif id == 4:
        return QtGui.QColor(85, 156, 158, 255)
    elif id == 5:
        return QtGui.QColor(255, 255, 255, 255)  # white
    else:
        return QtGui.QColor(100, 100, 100, 255)  # gray


# ---------------------------
# JSON binding
# ---------------------------


class BoundWidget:
    def __init__(self, json_ref):
        self.json_ref = json_ref

    def update_json(self, value):
        self.json_ref["answer"] = value


# ---------------------------
# Image Widget
# ---------------------------


class ImagePage(qtWid.QLabel):
    def __init__(self, pixmap, page_index):
        super().__init__()
        self.setSizePolicy(
            qtWid.QSizePolicy.Ignored,  # ignore sizeHint and just use available space
            qtWid.QSizePolicy.Maximum,  # do not expand more than defined in sizeHint
        )
        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Preferred)
        # print(f"Image Page size {self.width()}, {self.height()}.")
        self.setPixmap(pixmap)
        self.page_index = page_index
        self.highlight_rect = None

    def set_highlight(self, rect):
        self.highlight_rect = rect
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.highlight_rect:
            painter = QtGui.QPainter(self)
            pen = QtGui.QPen(QtGui.QColor("red"))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawRect(self.highlight_rect)


# ---------------------------
# Focus Widgets
# ---------------------------


class BoundCheckBox(qtWid.QCheckBox):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, text, template, json_ref):
        super().__init__(text)

        self.template = template
        self.json_ref = json_ref

        self.setChecked(json_ref["answer"])

        self.stateChanged.connect(self.write_json)
        self.clicked.connect(lambda: self.focused.emit(self.template))

    def write_json(self, state):
        self.json_ref["answer"] = bool(state)

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.toggle()
        else:
            super().keyPressEvent(e)


class BoundTextEdit(qtWid.QTextEdit):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref

        self.setText(json_ref["text"])

        self.textChanged.connect(self.write_json)
        self.setTabChangesFocus(True)
        self.setLineWrapMode(qtWid.QTextEdit.WidgetWidth)
        self.setMinimumWidth(0)
        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Fixed)

    def write_json(self):
        self.json_ref["text"] = self.toPlainText()

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)


class BoundParticipantNrEdit(qtWid.QLineEdit):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref

        # participantNr None means not filled in yet, 0 is a valid number
        participantNr = json_ref.get("participantNr")
        self.setText("" if participantNr is None else str(participantNr))
        self.setValidator(QtGui.QIntValidator(0, 999999))
        self.setMaximumWidth(200)

        self.textChanged.connect(self.write_json)

    def write_json(self, text):
        self.json_ref["participantNr"] = int(text) if text else None

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        # move on to the first question, like up/down between checkboxes
        if e.key() in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(e)


class ClickableImageLabel(qtWid.QLabel):
    clicked = QtCore.pyqtSignal(int, int, bool)

    def mousePressEvent(self, event):
        if self.pixmap() is None:
            return

        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(event.x(), event.y(), True)
        elif event.button() == QtCore.Qt.RightButton:
            self.clicked.emit(event.x(), event.y(), False)


class BoundDiagramWidget(qtWid.QWidget):
    focused = QtCore.pyqtSignal(object)
    tableChanged = QtCore.pyqtSignal()

    def __init__(self, template, json_ref, labels, maxWidth: int):
        super().__init__()

        self.template = template
        self.json_ref = json_ref
        self.labels = labels

        areaMapping = Image.open("src/areaMapping.png")
        self.areaMapping = np.array(areaMapping)
        with open("src/outline_figures.pickle", "rb") as f:
            self.areaDict = pickle.load(f)
        self.value_to_area = {member.value: member for member in DiagramAreas}

        layout = qtWid.QVBoxLayout(self)

        # --- Radio Buttons ---
        self.button_group = qtWid.QButtonGroup(self)
        self.button_group.setExclusive(True)

        radio_layout = qtWid.QHBoxLayout()

        self.buttons = {}

        for i, text in enumerate(self.labels):
            rb = qtWid.QRadioButton(text)
            self.button_group.addButton(rb, i)
            radio_layout.addWidget(rb)
            self.buttons[text] = rb

        layout.addLayout(radio_layout)

        self.button_group.buttonClicked.connect(self.set_curr_symbol)

        # --- Image Stack ---
        self.stack = qtWid.QStackedLayout()
        container = qtWid.QWidget()
        container.setLayout(self.stack)

        self.image_label = ClickableImageLabel()

        imgPath = json_ref["diagram"]["file"]
        if not imgPath or not os.path.isfile(imgPath):
            imgPath = "src/DefaultMapping.png"
        pixmap = QtGui.QPixmap(imgPath)

        # scale to a fixed target size (e.g. nearly half of the screen)
        scaled = pixmap.scaled(
            maxWidth,
            int((template.dy / template.dx) * maxWidth),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

        self.scaled_pixmap = scaled
        self.image_label.setPixmap(scaled)

        # store scale factors
        self.scale_x = pixmap.width() / scaled.width()
        self.scale_y = pixmap.height() / scaled.height()

        layout.addWidget(self.image_label)

        # click handling
        self.image_label.clicked.connect(self.handle_click)

        # load old data
        if "data" in self.json_ref["diagram"]:
            for bodypart in self.json_ref["diagram"]["data"]:
                # match bodypart with DiagramAreas
                areaType = DiagramAreas[bodypart]

                # match selected shape with label number
                selected_shape = self.json_ref["diagram"]["data"][bodypart]
                try:
                    shape_id = self.labels.index(selected_shape)
                    self.color_bodyPart(areaType, shape_id)
                except:
                    pass
        else:
            self.json_ref["diagram"]["data"] = {}

    def set_curr_symbol(self, button):
        self.selected_id = self.button_group.checkedId()

    def handle_click(self, px, py, leftButton: bool):
        selected_id = self.button_group.checkedId()
        if selected_id == -1:
            return

        # check which body part we clicked on
        imgVal = self.areaMapping[int(py * self.scale_y), int(px * self.scale_x)]
        areaType = self.value_to_area.get(imgVal)
        if not areaType or areaType == DiagramAreas.SOMETHING_ELSE:
            # no body area, do nothing
            return

        # clicked on something meaningful
        selected_shape = self.labels[selected_id]
        if leftButton:
            self.color_bodyPart(areaType, selected_id)
            self.json_ref["diagram"]["data"][
                areaType.name
            ] = selected_shape  # store selection
        else:
            self.color_bodyPart(areaType, 5)
            # check if entry actually exists
            if areaType.name in self.json_ref["diagram"]["data"]:
                del self.json_ref["diagram"]["data"][areaType.name]  # undo selection

        self.tableChanged.emit()  # update other widgets that there was change

    def color_bodyPart(self, areaType: DiagramAreas, shape_id: int):
        color = imgIcon_color(shape_id)
        imgPos = np.divide(
            np.array(self.areaDict[areaType.name]), [self.scale_x, self.scale_y]
        )
        coords = imgPos.astype(np.uint16)

        image = self.scaled_pixmap.toImage()
        ptr = image.bits()
        ptr.setsize(image.byteCount())

        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))

        coords[:, 0] = np.clip(coords[:, 0], 0, image.width() - 1)
        coords[:, 1] = np.clip(coords[:, 1], 0, image.height() - 1)
        arr[coords[:, 1], coords[:, 0]] = [
            color.red(),
            color.green(),
            color.blue(),
            color.alpha(),
        ]

        self.scaled_pixmap = QtGui.QPixmap.fromImage(image)
        self.image_label.setPixmap(self.scaled_pixmap)

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)


class BoundTableWidget(qtWid.QFrame):
    # emits the template table of the column that is being edited
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref
        self.labels = template.tables[0].rows

        self.json_ref["table"].setdefault("data", {})

        self.layout = qtWid.QGridLayout(self)

        # ---- HEADER ----
        headers = ["Bodypart", "Frequency", "Intensity", "Safety"]
        for col, text in enumerate(headers):
            wHeader = qtWid.QLabel(text)
            wHeader.setStyleSheet("font-weight:bold")
            self.layout.addWidget(wHeader, 0, col)

        # load table
        self.update_table()

        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Fixed)

    def update_table(self):
        # ---- CLEAR OLD ROWS (except header row 0) ----
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            row, col, _, _ = self.layout.getItemPosition(i)

            if row > 0:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                self.layout.removeItem(item)

        if "data" not in self.json_ref["diagram"]:
            return

        # ---- CREATE ROWS ----
        for row_index, bodypart in enumerate(self.json_ref["diagram"]["data"], start=1):
            selected_shape = self.json_ref["diagram"]["data"][bodypart]

            # ---- BODY PART LABEL ----
            self.layout.addWidget(qtWid.QLabel(bodypart), row_index, 0)

            combos = []

            # ---- CREATE DROPDOWNS ----
            for col_index in range(3):
                combo = qtWid.QComboBox()
                combo.setProperty("column", col_index)
                combo.installEventFilter(self)

                # add placeholder first
                combo.addItem("-- select --")

                # add real options
                combo.addItems(self.template.tables[col_index].columns)

                combos.append(combo)
                self.layout.addWidget(combo, row_index, col_index + 1)

            # ---- LOAD EXISTING DATA ----
            data = self.json_ref["table"]["data"].get(selected_shape, {})

            values = [
                data.get("frequency"),
                data.get("intensity"),
                data.get("safety"),
            ]

            for combo, value in zip(combos, values):
                if value and combo.findText(value) != -1:
                    combo.setCurrentText(value)
                else:
                    combo.setCurrentIndex(0)  # "-- select --"

            # ---- SAVE CALLBACK ----
            def make_callback(shape, cbs):
                def callback():
                    self.json_ref["table"]["data"][shape] = {
                        "frequency": (
                            cbs[0].currentText() if cbs[0].currentIndex() != 0 else ""
                        ),
                        "intensity": (
                            cbs[1].currentText() if cbs[1].currentIndex() != 0 else ""
                        ),
                        "safety": (
                            cbs[2].currentText() if cbs[2].currentIndex() != 0 else ""
                        ),
                    }
                    self.update_table()

                return callback

            cb = make_callback(selected_shape, combos)

            for combo in combos:
                combo.currentIndexChanged.connect(cb)

    def eventFilter(self, obj, e):
        if e.type() in (QtCore.QEvent.FocusIn, QtCore.QEvent.MouseButtonPress):
            col_index = obj.property("column")
            if col_index is not None:
                self.focused.emit(self.template.tables[col_index])
        return super().eventFilter(obj, e)


class BoundCheckTableWidget(qtWid.QFrame):
    """Check table of a layout-based form (no body diagram): one checkbox per cell,
    a ticked cell is stored as data[row][column] = True like area_grabbing does."""

    # emits the area of the cell that is being edited
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.json_ref = json_ref
        self.json_ref.setdefault("data", {})

        layout = qtWid.QGridLayout(self)

        # ---- HEADER ----
        for col, text in enumerate(template.columns, start=1):
            wHeader = qtWid.QLabel(text)
            wHeader.setStyleSheet("font-weight:bold")
            layout.addWidget(wHeader, 0, col)

        # ---- ROWS ----
        # same row height as the detection in area_grabbing.parse_single_data
        step_y = int(template.size_y / len(template.rows))
        for i, row in enumerate(template.rows):
            layout.addWidget(qtWid.QLabel(row), i + 1, 0)
            for j, column in enumerate(template.columns):
                cell = SimpleNamespace(
                    page=template.page,
                    dx=template.dx[j],
                    dy=template.dy + i * step_y,
                    size_x=template.size_x[j],
                    size_y=step_y,
                )
                checked = bool(self.json_ref["data"].get(row, {}).get(column, False))
                # BoundCheckBox for focus and enter handling, its own json is not used
                w = BoundCheckBox("", cell, {"answer": checked})
                w.stateChanged.connect(lambda state, r=row, c=column: self.write_json(r, c, state))
                w.focused.connect(self.focused)
                layout.addWidget(w, i + 1, j + 1)

        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Fixed)

    def write_json(self, row, column, state):
        cells = self.json_ref["data"].setdefault(row, {})
        if state:
            cells[column] = True
        else:
            cells.pop(column, None)


# ---------------------------
# Question Widget
# ---------------------------


class QuestionWidget(qtWid.QFrame):
    elementFocused = QtCore.pyqtSignal(object)

    def __init__(self, question_template, question_json, maxWidgetWidth: int):
        super().__init__()

        self.setSizePolicy(
            qtWid.QSizePolicy.Ignored,  # ignore sizeHint and just use available space
            qtWid.QSizePolicy.Maximum,  # do not expand more than vertically available
        )

        self.qnum = question_template.num

        layout = qtWid.QVBoxLayout()

        title = qtWid.QLabel(f"Q{self.qnum}: {question_template.questionText}")
        title.setWordWrap(True)
        title.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Preferred)
        title.setStyleSheet("font-weight:bold")
        layout.addWidget(title)

        elements = []

        # checkboxes
        cb_jsons = question_json.get("checkboxes")
        if cb_jsons is None:
            cb_jsons = [{"answer": False} for _ in question_template.checkboxes]
        for cb_template, cb_json in zip(question_template.checkboxes, cb_jsons):
            w = BoundCheckBox(cb_template.text, cb_template, cb_json)
            w.focused.connect(self.elementFocused)
            layout.addWidget(w)

            elements.append(cb_template)

        # free text
        txt_jsons = question_json.get("textFields")
        if txt_jsons is None:
            txt_jsons = [{"text": ""} for _ in question_template.texts]
        for txt_template, txt_json in zip(question_template.texts, txt_jsons):
            w = BoundTextEdit(txt_template, txt_json)
            w.focused.connect(self.elementFocused)
            w.setFixedHeight(70)

            layout.addWidget(w)
            elements.append(txt_template)

        # diagram (its tables are shown merged below it); every question has a "diagram" entry in the json
        if question_template.diagramms and ("diagram" in question_json) and ("table" in question_json):
            wDiagram = BoundDiagramWidget(
                question_template.diagramms[0],
                question_json,
                question_template.tables[0].rows,
                maxWidgetWidth,
            )
            wDiagram.focused.connect(self.elementFocused)
            layout.addWidget(wDiagram)
            elements.append(question_template.diagramms[0])

            # we create single table and do not focus, as mapping 3 tables in template to 1 in GUI impossible
            wTable = BoundTableWidget(question_template, question_json)
            # wTable.focused.connect(self.elementFocused) #Don't focus, so there is no unnecessary jumping
            wDiagram.tableChanged.connect(wTable.update_table)
            layout.addWidget(wTable)
            # elements.append(table_template)

        # check tables without a diagram (layout-based forms)
        elif question_template.tables:
            table_jsons = question_json.get("table")
            if not isinstance(table_jsons, list) or len(table_jsons) != len(question_template.tables):
                # nothing usable detected: one empty entry per table
                table_jsons = [{"name": "", "data": {}} for _ in question_template.tables]
                question_json["table"] = table_jsons
            for table_template, table_json in zip(question_template.tables, table_jsons):
                w = BoundCheckTableWidget(table_template, table_json)
                w.focused.connect(self.elementFocused)
                layout.addWidget(w)
                elements.append(table_template)

        self.setLayout(layout)

        # ---- compute template bounds ----
        if len(elements) > 0:
            self.template_page = elements[0].page
        else:
            raise RuntimeError("No known elements found on page.")

        self.template_top = min(e.dy for e in elements)
        self.template_bottom = max(e.dy + getattr(e, "size_y", 70) for e in elements)

    def sizeHint(self):
        return super().sizeHint()


# ---------------------------
# Participant Number Widget
# ---------------------------


class ParticipantNumberWidget(qtWid.QFrame):
    """Entry for the participant number written at the top of the form, shown like a question."""

    elementFocused = QtCore.pyqtSignal(object)

    def __init__(self, template, survey_json):
        super().__init__()

        self.setSizePolicy(qtWid.QSizePolicy.Ignored, qtWid.QSizePolicy.Maximum)

        layout = qtWid.QVBoxLayout()

        title = qtWid.QLabel("Participant number")
        title.setStyleSheet("font-weight:bold")
        layout.addWidget(title)

        w = BoundParticipantNrEdit(template, survey_json)
        w.focused.connect(self.elementFocused)
        layout.addWidget(w)

        self.setLayout(layout)

        self.template_page = template.page
        self.template_top = template.dy
        self.template_bottom = template.dy + template.size_y


# ---------------------------
# Survey Entry Widget
# ---------------------------


class SurveyEntryWidget(qtWid.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, name, status, participantNr=None, comment="", duplicates=()):
        super().__init__()

        self.name = name
        self.status = status

        self.setFrameShape(qtWid.QFrame.Box)
        self.setStyleSheet(f"border: 2px solid {status_color(status)};")

        layout = qtWid.QHBoxLayout()

        # participantNr None means not filled in yet
        label = name if participantNr is None else f"{name}   (participant {participantNr})"
        self.label = qtWid.QLabel(label)
        self.statusLabel = qtWid.QLabel(status)

        # operator comment about what might be weird, on one line (full text in the tooltip)
        comment = (comment or "").strip()
        self.commentLabel = qtWid.QLabel(" ".join(comment.split()))
        self.commentLabel.setStyleSheet("border: none; font-style: italic;")
        self.commentLabel.setToolTip(comment)
        self.commentLabel.setSizePolicy(qtWid.QSizePolicy.Ignored, qtWid.QSizePolicy.Preferred)

        layout.addWidget(self.label)

        # other surveys with the same participant number
        if duplicates:
            self.duplicateLabel = qtWid.QLabel(
                "\u26a0 same nr as " + ", ".join(n.split("_")[-1] for n in duplicates)
            )
            self.duplicateLabel.setStyleSheet("border: none; color: orange; font-weight: bold;")
            self.duplicateLabel.setToolTip("Participant number also used by:\n" + "\n".join(duplicates))
            layout.addSpacing(10)
            layout.addWidget(self.duplicateLabel)

        layout.addSpacing(20)
        layout.addWidget(self.commentLabel, 1)
        layout.addWidget(self.statusLabel)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)

    def mouseDoubleClickEvent(self, event):
        # Qt treats the second click of a double click as another press, which would open the survey twice
        pass


# ---------------------------
# Scroll Bar Widget
# ---------------------------
class SnappingScrollBar(qtWid.QScrollBar):
    def __init__(self, positions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_positions = positions
        self.setRange(0, self.fixed_positions[-1])
        self.setSingleStep(1)
        self.sliderReleased.connect(self.snapToNearest)
        self.index = 0
        self.toSync = []

    def snapToNearest(self, value=None):
        if value is None:
            value = self.value()
        self.setValue(value)

    def setValue(self, value):
        closest_idx = min(
            range(len(self.fixed_positions)),
            key=lambda i: abs(self.fixed_positions[i] - value),
        )
        super().setValue(self.fixed_positions[closest_idx])
        if self.index != closest_idx:
            self.index = closest_idx
            for other in self.toSync:
                other.snapToIndex(closest_idx)

    def snapToIndex(self, index):
        if index < len(self.fixed_positions):
            self.setValue(self.fixed_positions[index])

    def addSync(self, other):
        self.toSync.append(other)


# ---------------------------
# Scroll area hack
# ---------------------------
class NoHorizontalScrollArea(qtWid.QScrollArea):
    def ensureWidgetVisible(self, childWidget, xMargin=0, yMargin=0):
        # Only adjust vertical scrollbar
        if childWidget:
            pos = childWidget.mapTo(self.widget(), QtCore.QPoint(0, 0))
            self.verticalScrollBar().setValue(pos.y())

    def focusNextPrevChild(self, next):
        hbar = self.horizontalScrollBar()
        old = hbar.value()

        result = super().focusNextPrevChild(next)

        hbar.setValue(old)  # restore horizontal position
        return result
