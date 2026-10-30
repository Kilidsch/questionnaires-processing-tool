# MIT License
# Copyright (c) 2026 Marvin Lorber & Alexandra Mielke

__license__ = "MIT"
__author__ = ["Marvin Lorber", "Alexandra Mielke", "Thomas Chatagnon"]


import cv2
import json
import numpy as np
from src.survey_templates import Diagramm, Template, AnkerPos, DiagramAreas
import glob
import os
import pickle
import shutil

dpi = 500


class Page:
    def __init__(self, number, img, corners, ids) -> None:
        self.number = number
        self.img = img
        self.corners = corners
        self.ids = ids


def getArucoCenters(corners, ids):
    if ids is None:
        raise RuntimeError(
            "No ArUco markers detected on page. "
            "The scan may be missing the marker tags, or the image is corrupt."
        )
    ids = ids.flatten()
    marker_centers = {}
    for marker_corners, marker_id in zip(corners, ids):
        pts = marker_corners[0]  # shape (4,2)
        cx = np.mean(pts[:, 0])
        cy = np.mean(pts[:, 1])
        marker_centers[marker_id] = (cx, cy)
    return marker_centers


def warpImage(img, src_pts, dst_pts):
    # Find transformation matrix, so source points are morphed to dst_pts (3×3 homography)
    H, _ = cv2.findHomography(src_pts, dst_pts)

    # Warp the whole image
    H_out, W_out, _ = img.shape
    return cv2.warpPerspective(img, H, (W_out, H_out), flags=cv2.INTER_NEAREST)


def deskew(img, corners, ids):
    marker_centers = getArucoCenters(corners, ids)

    required = [1, 2, 3, 4]
    missing = [m for m in required if m not in marker_centers]
    if missing:
        raise RuntimeError(
            f"Page deskew: missing marker IDs {missing}. "
            "Cannot deskew without all 4 corner markers."
        )

    # Source points (from the current image, in correct corner order)
    src_pts = np.array(
        [
            marker_centers[1],  # top-left
            marker_centers[4],  # top-right
            marker_centers[3],  # bottom-right
            marker_centers[2],  # bottom-left
        ],
        dtype=np.float32,
    )

    # Destination points (fixed positions)
    dst_pts = np.array(
        [
            [AnkerPos.X.value, AnkerPos.Y.value],  # top-left
            [3725, 375],  # top-right
            [3725, 5530],  # bottom-right
            [645, 5530],  # bottom-left
        ],
        dtype=np.float32,
    )

    return warpImage(img, src_pts, dst_pts)


def non_background_percentage(img) -> float:
    h, w = img.shape[:2]
    total_pixels = h * w

    # Define what counts as background (here: nearly white)
    # e.g. B,G,R all >= 230
    bg_lower = np.array([200, 200, 200], dtype=np.uint8)
    bg_upper = np.array([255, 255, 255], dtype=np.uint8)

    # Mask of background pixels
    bg_mask = cv2.inRange(img, bg_lower, bg_upper)

    # Invert mask: 255 where we consider "color", 0 where background
    color_mask = cv2.bitwise_not(bg_mask)

    color_pixels = cv2.countNonZero(color_mask)
    color_percentage = color_pixels / total_pixels * 100.0

    return color_percentage


# https://www.30secondsofcode.org/python/s/hex-to-rgb/
# 30secondsofcode 2024
# CC-BY 4.0
def rgb_to_hex(color):
    b = color[0]
    g = color[1]
    r = color[2]
    return ("{:02X}" * 3).format(r, g, b)


def extract_diagramm(diagramm: Diagramm, page: Page):
    ids = page.ids.flatten()
    corners = dict(zip(ids, page.corners))
    missing = [cid for cid in diagramm.corner_ids if cid not in corners]
    if missing:
        return None
    top_left_corner = corners[diagramm.corner_ids[0]]
    top_left_point = top_left_corner[0][0]
    bottom_right_corner = corners[diagramm.corner_ids[3]]
    bottom_right_point = bottom_right_corner[0][2]
    return page.img[
        int(top_left_point[1]) : int(bottom_right_point[1]),
        int(top_left_point[0]) : int(bottom_right_point[0]),
    ]


def find_diagram_edges(img):
    gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()

    # Create the ArUco detector
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    # Detect the markers
    corners, ids, _ = detector.detectMarkers(gray)
    marker_centers = getArucoCenters(corners, ids)

    img_pts = np.array(
        [
            marker_centers[12],  # top-left
            marker_centers[11],  # top-right
            marker_centers[14],  # bottom-right
            marker_centers[13],  # bottom-left
        ],
        dtype=np.float32,
    )
    return img_pts


def create_diagram_masks(path_to_example_diagram):
    imgTemp = cv2.imread("src/ouline_figures_with_label_patches.png")
    src_pts = find_diagram_edges(imgTemp)

    exampleImg = cv2.imread(path_to_example_diagram)
    height, width, depth = exampleImg.shape
    dst_pts = np.array(
        [
            [155, 155],  # top-left
            [3164, 165],  # top-right
            [3165, 1698],  # bottom-right
            [155, 1691],  # bottom-left
        ],
        dtype=np.float32,
    )

    # scale to same size as scanned image
    scaledImg = warpImage(imgTemp, src_pts, dst_pts)
    scaledImg = scaledImg[0:height, 0:width, :]
    if depth != 3:
        raise RuntimeError(
            f"Something wrong with the scaled image. Does only have {depth} channels. Expecting 3."
        )

    tempDiagram = Diagramm(page=0)
    areaDict = {}
    areaValues = np.zeros((height, width))

    for key in tempDiagram.imgAreas:
        area = tempDiagram.imgAreas[key]
        areaDict[area.name] = []

    # loop through pixel in image (probably very unefficient, but easy to understand)
    x_index = np.array(range(width))
    y_index = np.array(range(height))
    for x in x_index:
        for y in y_index:
            color = scaledImg[y, x, :]
            colorHex = "#" + rgb_to_hex(color)
            if colorHex in tempDiagram.imgAreas:
                area = tempDiagram.imgAreas[colorHex]
                areaDict[area.name].append([int(x), int(y)])
            else:
                area = DiagramAreas.SOMETHING_ELSE
            areaValues[y, x] = area.value

    with open("src/outline_figures.pickle", "wb") as f:
        pickle.dump(areaDict, f)

    img = areaValues.astype("uint8")
    cv2.imwrite("src/areaMapping.png", img)


def parse_single_data(imgDir, files, template: Template) -> str:
    threshold = 20  # percentage that has to be black for answer to be accepted
    defaultDiagram = "src/DefaultMapping.png"
    pages = {}
    deskew_failed = False
    for fp in files:
        page_nr = int(fp[-5])
        img = cv2.imread(os.path.join(imgDir, fp))
        gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()

        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        corners, ids, _ = detector.detectMarkers(gray)

        try:
            img = deskew(img, corners, ids)
        except RuntimeError:
            deskew_failed = True
            print(f"  Warning: No ArUco markers on page {page_nr}, skipping deskew")
            break

        gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        pages[page_nr] = Page(page_nr, img, corners, ids)

    subjectData = {
        "participantNr": None,  # filled in manually in the GUI, None = not filled yet
    }

    # darkness of the empty checkboxes of each page, for templates whose scans are too dark for the fixed threshold
    baseline = {}
    if template.checkbox_margin is not None and not deskew_failed:
        grades = {}
        for question in template.get_questions():
            for checkbox in question.checkboxes:
                if checkbox.page in pages:
                    top = int(AnkerPos.Y.value + checkbox.dy)
                    left = int(AnkerPos.X.value + checkbox.dx)
                    checkbox_img = pages[checkbox.page].img[top : top + 70, left : left + 60]
                    grades.setdefault(checkbox.page, []).append(non_background_percentage(checkbox_img))
        baseline = {page: float(np.median(g)) for page, g in grades.items()}

    for question in template.get_questions():
        checkboxData = []
        textfieldData = []
        tableData = []

        if not deskew_failed:
            for checkbox in question.checkboxes:
                if checkbox.page not in pages:
                    # page missing in the scan
                    checkboxData.append({"text": checkbox.text, "answer": False})
                    continue
                top = int(AnkerPos.Y.value + checkbox.dy)
                left = int(AnkerPos.X.value + checkbox.dx)

                checkbox_img = pages[checkbox.page].img[
                    top : top + 70, left : left + 60
                ]
                grade = non_background_percentage(checkbox_img)
                checked = grade > threshold
                if checkbox.page in baseline:
                    checked = checked and grade > baseline[checkbox.page] + template.checkbox_margin
                checkboxData.append(
                    {
                        "text": checkbox.text,
                        "answer": checked,
                    }
                )
                if checked:
                    cv2.rectangle(
                        pages[checkbox.page].img,
                        (left, top),
                        (left + 60, top + 70),
                        color=(0, 0, 255),
                        thickness=6,
                    )
                print(f"Question {question.num}-{checkbox.text}:{grade}")

            for text_index, textfield in enumerate(question.texts):
                if textfield.page not in pages:
                    textfieldData.append({"text": "", "file": ""})
                    continue
                top = int(AnkerPos.Y.value + textfield.dy)
                left = int(AnkerPos.X.value + textfield.dx)

                # one file per field: a question may have several free-text
                # boxes (e.g. the 15 measurements) that would overwrite each other
                if len(question.texts) == 1:
                    filePath = f"{imgDir}/question_{question.num}_freeText.jpg"
                else:
                    filePath = (
                        f"{imgDir}/question_{question.num}_freeText_{text_index + 1}.jpg"
                    )
                cv2.imwrite(
                    filePath,
                    pages[textfield.page].img[
                        top : top + textfield.size_y, left : left + textfield.size_x, :
                    ],
                )
                textfieldData.append({"text": "", "file": filePath})

            for table in question.tables:
                if table.page not in pages:
                    # empty table, so the remaining tables keep their position in the merge below
                    tableData.append({"name": f"Table_{table.page}_{question.num}", "data": {}})
                    continue
                top = int(AnkerPos.Y.value + table.dy)
                step_y = int(table.size_y / len(table.rows))
                table_result = {}

                for i, row in enumerate(table.rows):
                    if row not in table_result:
                        table_result[row] = {}

                    for j, (dx, size_x, column) in enumerate(
                        zip(table.dx, table.size_x, table.columns)
                    ):
                        left = int(AnkerPos.X.value + dx)
                        cell_top = top + i * step_y + 13
                        cell_bottom = top + (i + 1) * step_y - 13
                        cell_img = pages[table.page].img[
                            cell_top:cell_bottom,
                            left : left + size_x,
                        ]

                        grade = non_background_percentage(cell_img)
                        print(
                            f"Table Q{question.num} row={row} col={column}: {grade:.1f}%"
                        )

                        if grade > threshold * 0.05:
                            table_result[row][column] = True

                if table_result:
                    tableData.append(
                        {
                            "name": f"Table_{table.page}_{question.num}",
                            "data": table_result,
                        }
                    )

            if len(tableData) == 3:
                merged = {}
                for symbol in tableData[0]["data"].keys():
                    freq_cols = tableData[0]["data"].get(symbol, {})
                    intens_cols = tableData[1]["data"].get(symbol, {})
                    safety_cols = tableData[2]["data"].get(symbol, {})

                    frequency = next(
                        (col for col, checked in freq_cols.items() if checked), None
                    )
                    intensity = next(
                        (col for col, checked in intens_cols.items() if checked), None
                    )
                    safety = next(
                        (col for col, checked in safety_cols.items() if checked), None
                    )

                    if any([frequency, intensity, safety]):
                        merged[symbol] = {
                            "frequency": frequency,
                            "intensity": intensity,
                            "safety": safety,
                        }
                tableData = {"name": f"Symbols_Q{question.num}", "data": merged}

        pathToDiagram = ""
        for diagramm in question.diagramms:
            diagramExtracted = False
            if not deskew_failed and diagramm.page in pages:
                img = extract_diagramm(diagramm, pages[diagramm.page])
                if img is not None:
                    pathToDiagram = os.path.join(
                        imgDir, f"question_{question.num}_diagramm.jpg"
                    )
                    cv2.imwrite(pathToDiagram, img)
                    diagramExtracted = True
            if not diagramExtracted:
                pathToDiagram = os.path.join(
                    imgDir, f"question_{question.num}_diagramm.jpg"
                )
                shutil.copy(defaultDiagram, pathToDiagram)

        questionData = {}
        questionData["question"] = question.questionText
        if len(checkboxData) > 0:
            questionData["checkboxes"] = checkboxData
        if len(textfieldData) > 0:
            questionData["textFields"] = textfieldData
        if len(tableData) > 0:
            questionData["table"] = tableData
        elif len(question.tables) > 0:
            questionData["table"] = {"name": "", "data": {}}
        questionData["diagram"] = {"file": pathToDiagram}
        subjectData[str(question.num)] = questionData

    if not deskew_failed:
        for key, value in pages.items():
            imgFileName = f"page-00{key}.jpg"
            cv2.imwrite(os.path.join(imgDir, imgFileName), value.img)

    dataFileName = "surveyData.json"
    with open(os.path.join(imgDir, dataFileName), "w") as f:
        json.dump(subjectData, f, indent=4)
    return dataFileName


def mark_target_areas(path_in: str, template: Template):
    pages = {}
    for fp in glob.glob(path_in + "/page_[0-9][0-9][0-9].jpg"):
        if os.path.isfile(fp):
            page_nr = int(fp[-5])
            img = cv2.imread(fp)
            # Convert the image to grayscale
            gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            parameters = cv2.aruco.DetectorParameters()

            # Create the ArUco detector
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            # Detect the markers
            corners, ids, _ = detector.detectMarkers(gray)

            img = deskew(img, corners, ids)

            # redetect markers after transformation
            gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            cv2.aruco.drawDetectedMarkers(img, corners, ids)

            pages[page_nr] = Page(page_nr, img, corners, ids)

    for question in template.get_questions():
        for checkbox in question.checkboxes:
            top = int(AnkerPos.Y.value + checkbox.dy)
            left = int(AnkerPos.X.value + checkbox.dx)
            cv2.rectangle(
                pages[checkbox.page].img,
                (left, top),
                (left + 60, top + 70),
                color=(255, 201, 201),
                thickness=2,
            )
            checkbox_img = pages[checkbox.page].img[top : top + 70, left : left + 60]
            grade = non_background_percentage(checkbox_img)
            print(f"Question {question.num}-{checkbox.text}:{grade}")
        for textfield in question.texts:
            top = int(AnkerPos.Y.value + textfield.dy)
            left = int(AnkerPos.X.value + textfield.dx)
            cv2.rectangle(
                pages[textfield.page].img,
                (left, top),
                (left + textfield.size_x, top + textfield.size_y),
                color=(255, 201, 201),
                thickness=2,
            )
        for table in question.tables:
            top = int(AnkerPos.Y.value + table.dy)
            step_y = (int)(table.size_y / np.size(table.rows))
            for i, row in enumerate(table.rows):
                for dx, size_x, column in zip(table.dx, table.size_x, table.columns):
                    left = int(AnkerPos.X.value + dx)
                    cell_img = pages[table.page].img[
                        (top + i * step_y + 13) : (top + (i + 1) * step_y - 13),
                        (left) : (left + size_x),
                    ]
                    cv2.rectangle(
                        pages[table.page].img,
                        (left, top + i * step_y + 13),
                        (left + size_x, top + (i + 1) * step_y - 13),
                        color=(255, 201, 201),
                        thickness=2,
                    )
                    grade = non_background_percentage(cell_img)
                    print(f"{row}-{column}-{grade}")
        for diagramm in question.diagramms:
            img = extract_diagramm(diagramm, pages[diagramm.page])
            if img is not None:
                cv2.imwrite(f"{path_in}/question_{question.num}_diagramm.jpg", img)

    for key, value in pages.items():
        cv2.imwrite(f"{path_in}/page_00{key}_detected.jpg", value.img)
