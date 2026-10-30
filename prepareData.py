"""This script prepares data for annotation and verification in the GUI.

Expected input: File directory with PDFs. Each PDFs has several surveys of the same type appended after each other.
Output:
    mainFolder
    |-<date>_<experiment>
    |   |-metadata.json
    |   |-layout.json   <-- copy of the form's layout, for layout-based forms only
    |   |-originalData.pdf
    |   |-surveyResponse_<nr>
    |   |   |-page0
    |   |   |-page1
    |   |   |-...
    |   |   |-data.csv    <-- parsed experiment proband data in here
    |   |
    |   |-surveyResponse_<nr>
    |   |   |...
    |   |...

Copyright: Marvin Lorber, Alexandra Mielke 2026
License: MIT
"""

# ----- pip imports
import argparse
import json
import os.path
from pathlib import Path
import platform
import shutil

from pdf2image import convert_from_path

if platform.system() == "Windows":
    # Some additional downloading and setup
    # Check installation guide for pdf2image: https://pypi.org/project/pdf2image/
    path_to_poppler_exe = Path(r"C:/poppler/poppler-25.12.0/Library\bin")
    if not path_to_poppler_exe.is_dir():
        # no local install at the path above: let pdf2image search PATH
        path_to_poppler_exe = None

# ----- project includes
from src.survey_templates import GrabExperiment, ExperimentTypes
from src import area_grabbing, questionnaire_layout

# name of the layout copy next to metadata.json
LAYOUT_FILE = "layout.json"


class pdfConverter:
    def __init__(self, mainDir, metadataFile):
        self.mainDir = mainDir
        self.tempDir = os.path.join(self.mainDir, "temp")
        self.metadataFile = metadataFile

        self.imgType = "jpg"

        # check for metadata, if not there create default file
        if not self._readMetadata():
            self.metadata = {
                "Experiment": {"Type": "unknown", "Name": ""},
                "Description": "",
                "Date": "",
                "Comment": "",
            }
            self._saveMetadata()

    def _readMetadata(self) -> bool:
        if os.path.isfile(self.metadataFile):
            with open(self.metadataFile, "r") as f:
                self.metadata = json.load(f)
            return True
        else:
            return False

    def _saveMetadata(self):
        with open(self.metadataFile, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def _page_name_generator(self):
        while True:
            yield "page"  # return value, but continue

    def convert_pages(self, path_to_pdf: str):
        if os.path.isdir(self.tempDir):
            converted = [
                f for f in os.listdir(self.tempDir) if f.endswith("." + self.imgType)
            ]
            if converted:
                print("Found /temp. Assuming PDF(s) already converted.")
                return
            # A previous run failed before sorting: keep no stale empty /temp,
            # otherwise the pages would never be converted.
            shutil.rmtree(self.tempDir)
        os.mkdir(self.tempDir)
        print(f"Converting {path_to_pdf} to images ... ")
        pdf_file = Path(path_to_pdf)
        if platform.system() == "Windows":
            convert_from_path(
                pdf_file,
                fmt=self.imgType,
                dpi=area_grabbing.dpi,
                output_folder=self.tempDir,
                paths_only=True,
                output_file=self._page_name_generator(),
                poppler_path=path_to_poppler_exe,
            )
        else:
            convert_from_path(
                pdf_file,
                fmt=self.imgType,
                dpi=area_grabbing.dpi,
                output_file=self._page_name_generator(),
                output_folder=self.tempDir,
                paths_only=True,
            )  # Read in the PDF file at 500 DPI

    def sort_pages(self):
        # load metadata again, in case user changed something in conversion time
        self._readMetadata()
        # TODO determine an unknown type from the data (raises for now)
        typeTemplate = GrabExperiment.initFromMetadata(self.metadata, self.mainDir)

        # loop through image files and resort them
        surveyResponses = {}
        nr_pages = typeTemplate.get_num_pages()
        surveyPage = 0
        participantNr = 0
        currDir = ""
        files = []

        import re

        # get all files
        all_files = os.listdir(self.tempDir)

        # filter pages an not the numbers
        page_files = [f for f in all_files if re.match(r"page-\d+\." + self.imgType, f)]

        # now sort in page numbers
        page_files.sort(key=lambda x: int(re.search(r"\d+", x).group()))

        if len(page_files) % nr_pages != 0:
            print(
                f"Warning: {len(page_files)} pages is not a multiple of {nr_pages} pages per survey. "
                "Pages are missing in the scan and the surveys after them are shifted. "
                "Check the page order of the surveys!"
            )

        for nr, file_name in enumerate(page_files):
            if surveyPage == 0:
                participantNr += 1  # start at one
                currDir = os.path.join(
                    self.mainDir, f"surveyResponse_{participantNr:03}"
                )
                if not os.path.isdir(currDir):
                    os.mkdir(currDir)

            pathToFile = os.path.join(self.tempDir, file_name)
            if os.path.isfile(pathToFile):
                pageName = f"page-{(surveyPage+1):03}." + self.imgType
                # replace: a re-run of prepareData must overwrite the pages of
                # an earlier run instead of failing on the existing files
                os.replace(pathToFile, os.path.join(currDir, pageName))
                files.append(pageName)
            else:
                raise RuntimeError(
                    f"Could not find {pathToFile}. Recheck if expected file names are correct!"
                )

            surveyPage += 1
            if surveyPage >= nr_pages:
                dataFileName = area_grabbing.parse_single_data(
                    currDir, files, typeTemplate
                )
                surveyResponses[f"surveyResponse_{participantNr:03}"] = {
                    "status": "Open",
                    "dir": currDir,
                    "dataFile": dataFileName,
                }
                surveyPage = 0
                files = []

        if surveyPage != 0:
            # the PDF ended in the middle of a survey, register it anyway so it shows up in the GUI
            dataFileName = area_grabbing.parse_single_data(currDir, files, typeTemplate)
            dataPath = os.path.join(currDir, dataFileName)
            with open(dataPath, "r") as f:
                surveyData = json.load(f)
            surveyData["comment"] = (
                f"Only {surveyPage} of {nr_pages} pages in the scan. Pages are missing somewhere in the PDF, "
                "check the page order of this and the previous surveys."
            )
            with open(dataPath, "w") as f:
                json.dump(surveyData, f, indent=4)
            surveyResponses[f"surveyResponse_{participantNr:03}"] = {
                "status": "Needs checking",
                "dir": currDir,
                "dataFile": dataFileName,
            }

        self.metadata["participants"] = participantNr
        self.metadata["surveyResponses"] = surveyResponses

        # We're done, update metadata
        self._saveMetadata()

        # and delete temp folder
        for file in os.listdir(self.tempDir):
            os.remove(os.path.join(self.tempDir, file))
        os.rmdir(self.tempDir)

    def prepareFigureImg(self):
        imgPath = ""
        for resp in self.metadata["surveyResponses"]:
            dir = self.metadata["surveyResponses"][resp]["dir"]
            for img in os.listdir(dir):
                if img.endswith("diagramm.jpg"):
                    imgPath = os.path.join(dir, img)
                    break
            if imgPath != "":
                break
        if imgPath == "":
            # layout-based forms need not contain a body diagram
            print("No diagram found, skipping diagram masks.")
            return
        area_grabbing.create_diagram_masks(imgPath)


def resolve_experiment(typeOrLayout: str) -> tuple[str, Path | None]:
    """Experiment type and layout file of the CLI argument: a legacy type, the name
    of a built-in layout (src/layouts/<name>_layout.json) or a path to a layout JSON
    file. The layout is None for legacy types."""
    if typeOrLayout.lower().endswith(".json"):
        layoutPath = Path(typeOrLayout)
        if not layoutPath.is_file():
            raise RuntimeError(f"Layout file not found: {layoutPath}")
        # validate now rather than after converting all PDFs
        layout = questionnaire_layout.load_layout(layoutPath)
        return Path(layout.doc).stem, layoutPath
    if typeOrLayout in ExperimentTypes:
        return typeOrLayout, None
    layoutPath = GrabExperiment.find_layout(typeOrLayout)
    if layoutPath is None:
        GrabExperiment.initType(typeOrLayout)  # raises with the valid types
    return typeOrLayout, layoutPath


def write_metadata(outputDir: str, expType: str, layoutPath: Path | None) -> str:
    """Write metadata.json (and the layout copy) of one PDF's output directory,
    keeping whatever an earlier run or the user already put there (surveyResponses,
    statuses). Returns the path of metadata.json."""
    metadataFile = os.path.join(outputDir, "metadata.json")
    metadata = {
        "Experiment": {"Type": expType, "Name": ""},
        "Description": "",
        "Date": "",
        "Comment": "",
    }
    if os.path.isfile(metadataFile):
        with open(metadataFile, encoding="utf-8") as f:
            metadata.update(json.load(f))
        metadata.setdefault("Experiment", {})
        metadata["Experiment"]["Type"] = expType

    layoutCopy = os.path.join(outputDir, LAYOUT_FILE)
    if layoutPath is None:
        metadata["Experiment"].pop("Layout", None)
    else:
        # a copy, not a reference: re-exporting the form later must not move the
        # areas of surveys that were already processed
        if not (os.path.isfile(layoutCopy) and os.path.samefile(layoutPath, layoutCopy)):
            shutil.copyfile(layoutPath, layoutCopy)
        metadata["Experiment"]["Layout"] = LAYOUT_FILE

    with open(metadataFile, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    return metadataFile


def main():
    parser = argparse.ArgumentParser(description="Prepare PDF questionnaires for annotation")
    parser.add_argument("expDir", type=str, help="Directory containing PDF files to process")
    parser.add_argument("expType", type=str,
                        help="Experiment type (rope, bottleneck, rope_short, a built-in "
                             "layout-based type such as test_e2e) or the path to a "
                             "layout JSON file (output/<name>_layout.json)")
    args = parser.parse_args()

    expDir = args.expDir
    expType, layoutPath = resolve_experiment(args.expType)

    # Find all PDFs in the directory
    pdfFiles = sorted(
        [f for f in os.listdir(expDir) if f.endswith(".pdf")]
    )

    if not pdfFiles:
        raise RuntimeError(f"Could not find pdf files in {expDir}.")

    for pdfFileName in pdfFiles:
        pdfFile = os.path.join(expDir, pdfFileName)

        # Create a subfolder for each PDF, named after the PDF without extension
        pdfBaseName = os.path.splitext(pdfFileName)[0]
        outputDir = os.path.join(expDir, pdfBaseName)
        os.makedirs(outputDir, exist_ok=True)

        metadataFile = write_metadata(outputDir, expType, layoutPath)

        converter = pdfConverter(mainDir=outputDir, metadataFile=metadataFile)
        converter.convert_pages(pdfFile)
        converter.sort_pages()
        converter.prepareFigureImg()


if __name__ == "__main__":
    main()
