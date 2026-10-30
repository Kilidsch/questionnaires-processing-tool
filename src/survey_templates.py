# MIT License
# Copyright (c) 2026 Marvin Lorber & Alexandra Mielke

__license__ = "MIT"
__author__ = ["Marvin Lorber", "Alexandra Mielke"]

import copy
from enum import StrEnum, Enum
from pathlib import Path
from typing import Sequence


class ExperimentTypes(StrEnum):
    # hardcoded legacy forms only; layout (JSON)-based forms need no entry here,
    # see GrabExperiment.initType and the README
    ROPE = "rope"
    BOTTLENECK = "bottleneck"
    # Rope sessions that used only the two contact pages of the Bottleneck form
    ROPE_SHORT = "rope_short"

    @classmethod
    def _missing_(cls, value):
        value = str(value).lower()
        for member in cls:
            if member.value == value:
                return member
        return None


class DiagramAreas(Enum):
    HEAD = 0
    NECK = 1
    BREAST = 2
    UPPER_BACK = 3
    LOWER_BACK = 4
    BUTTOCKS = 5
    CROTCH = 6
    STOMACH = 7
    LEFT_SHOULDER = 8
    LEFT_UPPER_ARM = 9
    LEFT_LOWER_ARM = 10
    LEFT_HAND = 11
    LEFT_THIGH = 12
    LEFT_CALF = 13
    LEFT_FOOT = 14
    RIGHT_SHOULDER = 15
    RIGHT_UPPER_ARM = 16
    RIGHT_LOWER_ARM = 17
    RIGHT_HAND = 18
    RIGHT_THIGH = 19
    RIGHT_CALF = 20
    RIGHT_FOOT = 21
    SOMETHING_ELSE = 99


# pixel position of mid of top left AruCo tag
class AnkerPos(Enum):
    X = 645
    Y = 375


class Checkbox:
    size_x: int = 60
    size_y: int = 70

    def __init__(self, page: int, dx: int, dy: int, text: str):
        self.page = page
        self.dx = dx
        self.dy = dy
        self.text = text


class Freetext:
    def __init__(self, page: int, dx: int, dy: int, size_x: int, size_y: int):
        self.page = page
        self.dx = dx
        self.dy = dy
        self.size_x = size_x
        self.size_y = size_y


class ParticipantNumber:
    """Area at the top of the form where the participant number is written.
    Only used to show the area in the GUI, the number itself is typed in manually."""

    def __init__(self, page: int, dx: int, dy: int, size_x: int, size_y: int):
        self.page = page
        self.dx = dx
        self.dy = dy
        self.size_x = size_x
        self.size_y = size_y


class CheckTable:
    def __init__(
        self,
        page: int,
        dx: Sequence[int],
        dy: int,
        size_x: Sequence[int],
        size_y: int,
        columns: Sequence[str],
        rows: Sequence[str],
    ):
        self.page = page
        self.dx = dx
        self.dy = dy
        self.size_x = size_x
        self.size_y = size_y
        self.columns = columns
        self.rows = rows


class Diagramm:
    def __init__(
        self,
        page: int,
        dx: int = 3317,
        dy: int = 1850,
        corner_ids: Sequence[int] = [12, 11, 13, 14],
    ):
        self.page = page
        self.corner_ids = corner_ids
        self.dx = dx
        self.dy = dy
        self.imgAreas = {  # We map colors to body areas, as we later want to get body area back out when feeding in color
            "#E13F48": DiagramAreas.HEAD,
            "#4CBCC3": DiagramAreas.NECK,
            "#7A7A7A": DiagramAreas.BREAST,
            "#EBEB64": DiagramAreas.UPPER_BACK,
            "#65BA55": DiagramAreas.LOWER_BACK,
            "#FE9C11": DiagramAreas.BUTTOCKS,
            "#4C6FC3": DiagramAreas.CROTCH,
            "#34DB91": DiagramAreas.STOMACH,
            "#DFA730": DiagramAreas.LEFT_SHOULDER,
            "#DF309A": DiagramAreas.LEFT_UPPER_ARM,
            "#1C9617": DiagramAreas.LEFT_LOWER_ARM,
            "#171E96": DiagramAreas.LEFT_HAND,
            "#C34C60": DiagramAreas.LEFT_THIGH,
            "#B3C34C": DiagramAreas.LEFT_CALF,
            "#30BDDF": DiagramAreas.LEFT_FOOT,
            "#DF7230": DiagramAreas.RIGHT_SHOULDER,
            "#30DFB6": DiagramAreas.RIGHT_UPPER_ARM,
            "#961739": DiagramAreas.RIGHT_LOWER_ARM,
            "#DFE13F": DiagramAreas.RIGHT_HAND,
            "#BC4CC3": DiagramAreas.RIGHT_THIGH,
            "#40DF30": DiagramAreas.RIGHT_CALF,
            "#305FDF": DiagramAreas.RIGHT_FOOT,
        }


class Question:
    def __init__(
        self,
        num: int,
        questionText: str,
        checkboxes: Sequence[Checkbox] = [],
        texts: Sequence[Freetext] = [],
        diagramms: Sequence[Diagramm] = [],
        tables: Sequence[CheckTable] = [],
    ):
        self.num = num
        self.questionText = questionText
        self.checkboxes = checkboxes
        self.texts = texts
        self.diagramms = diagramms
        self.tables = tables


class Template:
    # if set, a checkbox only counts as ticked if it is this many percentage points darker than the empty
    # checkboxes of its page (median of all checkboxes of the page), for scans too dark for the fixed threshold
    checkbox_margin: float | None = None

    def get_num_pages(self) -> int:
        return 0

    def get_questions(self) -> Sequence[Question]:
        return []

    def get_participant_number(self) -> ParticipantNumber | None:
        return None


class Bottleneck(Template):
    def __init__(self) -> None:
        question1 = Question(
            num=1,
            questionText="Hatten Sie gerade das Gefuehl in einer Situation zu sein, in der Sie sich gedraengt oder gequetscht gefuehlt haben?",
            checkboxes=[
                Checkbox(page=1, dx=37, dy=800, text="ja"),
                Checkbox(page=1, dx=37, dy=1385, text="nein"),
                Checkbox(page=1, dx=37, dy=1505, text="weiss nicht"),
            ],
            texts=[Freetext(page=1, dx=380, dy=1110, size_x=2800, size_y=390)],
        )
        question2 = Question(
            num=2,
            questionText="Wie wohl haben Sie sich in der Menschenmenge gefuehlt?",
            checkboxes=[
                Checkbox(page=1, dx=37, dy=1939, text="sehr wohl"),
                Checkbox(page=1, dx=37, dy=2059, text="eher wohl"),
                Checkbox(page=1, dx=37, dy=2183, text="neutral"),
                Checkbox(page=1, dx=37, dy=2306, text="eher unwohl"),
                Checkbox(page=1, dx=37, dy=2430, text="sehr unwohl"),
            ],
        )
        question3 = Question(
            num=3,
            questionText="Hatten Sie waehrend des Durchlaufs Angst in der Menschenmenge?",
            checkboxes=[
                Checkbox(page=1, dx=37, dy=2860, text="nein"),
                Checkbox(page=1, dx=37, dy=2986, text="leicht"),
                Checkbox(page=1, dx=37, dy=3109, text="mittel"),
                Checkbox(page=1, dx=37, dy=3232, text="stark"),
            ],
        )
        question4 = Question(
            num=4,
            questionText="Wie wuerden Sie Ihre eigene koerperliche Stabilitaet / Standfestigkeit im letzten Durchlauf einschaetzen?",
            checkboxes=[
                Checkbox(page=1, dx=37, dy=3764, text="sehr gut"),
                Checkbox(page=1, dx=37, dy=3886, text="gut"),
                Checkbox(page=1, dx=37, dy=4006, text="neutral"),
                Checkbox(page=1, dx=37, dy=4130, text="eher gering"),
                Checkbox(page=1, dx=37, dy=4251, text="gering"),
            ],
        )
        question5 = Question(
            num=5,
            questionText="Wie hoch schaetzen Sie Ihr persoenliches Risiko ein, im letzten Durchlauf Ihr Gleichgewicht zu verlieren?",
            checkboxes=[
                Checkbox(page=2, dx=37, dy=455, text="sehr hoch"),
                Checkbox(page=2, dx=37, dy=575, text="hoch"),
                Checkbox(page=2, dx=37, dy=697, text="neutral"),
                Checkbox(page=2, dx=37, dy=819, text="eher gering"),
                Checkbox(page=2, dx=37, dy=941, text="gering"),
            ],
        )
        question6 = Question(
            num=6,
            questionText="Haben Sie eine Strategie/Routine waehrend der letzten Durchlaeufe entwickelt, wie Sie sich in der Menschemenge bewegen?",
            checkboxes=[
                Checkbox(page=2, dx=37, dy=1472, text="Ja"),
                Checkbox(page=2, dx=37, dy=1836, text="Nein"),
            ],
            texts=[Freetext(page=2, dx=380, dy=1660, size_x=2800, size_y=275)],
        )
        question7 = Question(
            num=7,
            questionText="Haben Sie das efuehl, dass die Gruppe eine Strategie/Routine waehrend der letzten Durchlaeufe entwickelt hat,"
            + " wie sie sich durch die Engstellt bewegen?",
            checkboxes=[
                Checkbox(page=2, dx=37, dy=2487, text="Ja"),
                Checkbox(page=2, dx=37, dy=2851, text="Nein"),
            ],
            texts=[Freetext(page=2, dx=380, dy=2680, size_x=2800, size_y=275)],
        )
        question8 = Question(
            num=8,
            questionText="Wenn es eng wird, haben Sie eher Abstand gehalten oder sind Sie naeher an andere heran gegangen?",
            checkboxes=[
                Checkbox(page=2, dx=37, dy=3386, text="Abstand gehalten"),
                Checkbox(page=2, dx=37, dy=3509, text="neutral"),
                Checkbox(page=2, dx=37, dy=3631, text="naeher heran gegangen"),
            ],
        )
        question9 = Question(
            num=9,
            questionText="Haben Sie sich eher zurueckhaltend oder durchsetzungsstark waehrend "
            + "des Durchlaufs verhalten, wenn viele Menschen gleichzeitif durch eine Engstelle wollen?",
            checkboxes=[
                Checkbox(page=2, dx=37, dy=4279, text="sehr zurueckhaltend"),
                Checkbox(page=2, dx=37, dy=4400, text="eher zurueckhaltend"),
                Checkbox(page=2, dx=37, dy=4522, text="weder noch"),
                Checkbox(page=2, dx=37, dy=4647, text="eher durchsetzungsstark"),
                Checkbox(page=2, dx=37, dy=4769, text="sehr durchsetzungsstark"),
            ],
        )
        question10 = Question(
            num=10,
            questionText="Wie sehr haben Sie im Gedraenge auf die Bewegungen anderer Personen geachtet?",
            checkboxes=[
                Checkbox(page=3, dx=37, dy=454, text="wenig"),
                Checkbox(page=3, dx=37, dy=576, text="neutral"),
                Checkbox(page=3, dx=37, dy=698, text="stark"),
            ],
        )
        question11 = Question(
            num=11,
            questionText="Gab es Situationen in denen Sie aufgrund der Menschenmenge nicht selbstbestimmt gehen konnten?",
            checkboxes=[
                Checkbox(page=3, dx=37, dy=1323, text="ja"),
                Checkbox(page=3, dx=37, dy=1446, text="nein"),
                Checkbox(page=3, dx=37, dy=1571, text="weiss nicht"),
            ],
        )
        question12 = Question(
            num=12,
            questionText="Wie haben SIe Ihre ARme waehrend dieses Durchlaufs gehalten? (Mehrfachnennung moeglich)",
            checkboxes=[
                Checkbox(
                    page=3, dx=37, dy=2100, text="hinter dem Ruecken verschraenkt"
                ),
                Checkbox(page=3, dx=37, dy=2223, text="vor dem Bauch verschraenkt"),
                Checkbox(page=3, dx=37, dy=2347, text="vor der Brust verschraenkt"),
                Checkbox(page=3, dx=37, dy=2469, text="in die Huefte gestuetzt"),
                Checkbox(page=3, dx=37, dy=2592, text="seitlich herabhaengend"),
                Checkbox(
                    page=3,
                    dx=37,
                    dy=2716,
                    text="Arme nach vorne gerichtet, ggf. leicht gestreckt",
                ),
                Checkbox(
                    page=3,
                    dx=37,
                    dy=2837,
                    text="Haende nah vor dem Oberkoerper auf Brusthoehe",
                ),
                Checkbox(page=3, dx=37, dy=2961, text="Andere Haltung:"),
            ],
            texts=[Freetext(page=3, dx=830, dy=2930, size_x=2370, size_y=130)],
        )
        question13 = Question(
            num=13,
            questionText="Hatten Sie den Eindruck, Ihre Arme aktiv zur Stabilisierung einzusetzen?",
            checkboxes=[
                Checkbox(page=3, dx=37, dy=3495, text="ja, deutlich"),
                Checkbox(page=3, dx=37, dy=3617, text="eher ja"),
                Checkbox(page=3, dx=37, dy=3740, text="eher nein"),
                Checkbox(page=3, dx=37, dy=3864, text="nein, gar nicht"),
            ],
        )
        question14 = Question(
            num=14,
            questionText="WElche Funktion hatte Ihr Armeinsatz aus Ihrer Sicht (Mehrfachnennung moeglich)",
            checkboxes=[
                Checkbox(page=4, dx=37, dy=452, text="Druck auf Vordermann ausueben"),
                Checkbox(page=4, dx=37, dy=575, text="Schutz des eigenen Koerpers"),
                Checkbox(
                    page=4,
                    dx=37,
                    dy=696,
                    text="Platz schaffen beziehungsweise Raum halten",
                ),
                Checkbox(
                    page=4, dx=37, dy=818, text="Gleichgewicht bewusst unterstuetzen"
                ),
                Checkbox(
                    page=4,
                    dx=37,
                    dy=940,
                    text="unbewusste Bewegung ohne klare Funktion",
                ),
                Checkbox(page=4, dx=37, dy=1062, text="keine Funktion"),
                Checkbox(page=4, dx=37, dy=1186, text="Andere Funktion:"),
            ],
            texts=[Freetext(page=4, dx=880, dy=1150, size_x=2330, size_y=130)],
        )
        question15 = Question(
            num=15,
            questionText="Haben Sie bewusst mit den Armen andere Persnen weggedrueckt?",
            checkboxes=[
                Checkbox(page=4, dx=37, dy=1611, text="ja, bewusst"),
                Checkbox(page=4, dx=37, dy=1736, text="teilweise bewusst"),
                Checkbox(page=4, dx=37, dy=1857, text="nein, eher unbewusst"),
                Checkbox(page=4, dx=37, dy=1979, text="nein, ueberhaupt nicht"),
            ],
        )
        question16 = Question(
            num=16,
            questionText="Haben Sie bewusst Ihre Arme als Schutzreaktion eingesetzt, um Raum zu gewinnen?",
            checkboxes=[
                Checkbox(page=4, dx=37, dy=2513, text="ja, bewusst"),
                Checkbox(page=4, dx=37, dy=2636, text="teilweise bewusst"),
                Checkbox(page=4, dx=37, dy=2759, text="nein, eher unbewusst"),
                Checkbox(page=4, dx=37, dy=2881, text="nein, ueberhaupt nicht"),
            ],
        )
        question17 = Question(
            num=17,
            questionText="Bitte markieren Sie die Koerperstellen",
            diagramms=[Diagramm(page=5)],
            tables=[
                CheckTable(
                    page=5,
                    dx=[490, 1030, 1560, 2130, 2670],
                    dy=2800,
                    size_x=[480, 480, 480, 480, 480],
                    size_y=600,
                    columns=["immer", "oft", "gelegentlich", "einmalig", "-"],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
                CheckTable(
                    page=5,
                    dx=[490, 1030, 1560, 2130, 2670],
                    dy=3837,
                    size_x=[480, 480, 480, 480, 480],
                    size_y=600,
                    columns=[
                        "sehr stark",
                        "stark",
                        "mittelmaessig",
                        "schwach",
                        "sehr schwach",
                    ],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
                CheckTable(
                    page=6,
                    dx=[490, 1030, 1560, 2130, 2670],
                    dy=546,
                    size_x=[480, 480, 480, 480, 480],
                    size_y=600,
                    columns=[
                        "sehr sicher",
                        "sicher",
                        "mittelmaessig",
                        "unsicher",
                        "sehr unsicher",
                    ],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
            ],
        )
        question18 = Question(
            num=18,
            questionText="Wie erschoepft fuehlen Sie sich nach diesem Durchlauf?",
            checkboxes=[
                Checkbox(page=6, dx=37, dy=1479, text="ueberhaupt nicht erschoepft"),
                Checkbox(page=6, dx=37, dy=1601, text="eher nicht erschoepft"),
                Checkbox(page=6, dx=37, dy=1724, text="neutral"),
                Checkbox(page=6, dx=37, dy=1846, text="eher erschoepft"),
                Checkbox(page=6, dx=37, dy=1968, text="sehr erschoepft"),
            ],
        )
        question19 = Question(
            num=19,
            questionText="Wie gelangweilt fuehlen Sie sich nach diesem Durchlauf?",
            checkboxes=[
                Checkbox(page=6, dx=37, dy=2406, text="überhaupt nicht gelangweilt"),
                Checkbox(page=6, dx=37, dy=2530, text="eher nicht gelangweilt"),
                Checkbox(page=6, dx=37, dy=2653, text="neutral"),
                Checkbox(page=6, dx=37, dy=2776, text="eher gelangweiligt"),
                Checkbox(page=6, dx=37, dy=2900, text="sehr gelangweiligt"),
            ],
        )

        self.questions = [
            question1,
            question2,
            question3,
            question4,
            question5,
            question6,
            question7,
            question8,
            question9,
            question10,
            question11,
            question12,
            question13,
            question14,
            question15,
            question16,
            question17,
            question18,
            question19,
        ]

    def get_num_pages(self) -> int:
        return 6

    def get_questions(self) -> Sequence[Question]:
        return self.questions

    def get_participant_number(self) -> ParticipantNumber:
        # "Nummer" boxes below the title
        return ParticipantNumber(page=1, dx=855, dy=185, size_x=465, size_y=200)


class Rope(Template):
    def __init__(self) -> None:
        question1 = Question(
            num=1,
            questionText="not defined yet",
            diagramms=[Diagramm(page=1)],
            tables=[
                CheckTable(
                    page=1,
                    dx=[415, 940, 1430, 1995, 2510],
                    dy=3307,
                    size_x=[475, 430, 515, 475, 740],
                    size_y=600,
                    columns=["immer", "oft", "gelegentlich", "einmalig", "-"],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
                CheckTable(
                    page=2,
                    dx=[435, 970, 1505, 2075, 2610],
                    dy=629,
                    size_x=[505, 500, 540, 504, 500],
                    size_y=600,
                    columns=[
                        "sehr stark",
                        "stark",
                        "mittelmaessig",
                        "schwach",
                        "sehr schwach",
                    ],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
                CheckTable(
                    page=2,
                    dx=[440, 960, 1515, 2070, 2615],
                    dy=1704,
                    size_x=[480, 520, 520, 510, 480],
                    size_y=600,
                    columns=[
                        "sehr sicher",
                        "sicher",
                        "mittelmaessig",
                        "unsicher",
                        "sehr unsicher",
                    ],
                    rows=["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"],
                ),
            ],
        )
        self.questions = [question1]

    def get_num_pages(self) -> int:
        return 2

    def get_questions(self) -> Sequence[Question]:
        return self.questions

    def get_participant_number(self) -> ParticipantNumber:
        # some forms have "Nummer" boxes, on others the number is written anywhere in the header
        return ParticipantNumber(page=1, dx=-245, dy=-325, size_x=3550, size_y=710)


class RopeShort(Template):
    """Form used in some Rope sessions instead of the Rope form: only the two contact pages (pages 5 and 6)
    of the Bottleneck form, so the questions and positions are those of Bottleneck questions 17-19 on pages 1-2.
    """

    first_page = 5  # page of the Bottleneck form that is page 1 here
    # these scans are darker: empty checkboxes are ~25% non-background, ticked ones ~35-65%
    checkbox_margin = 10

    def __init__(self) -> None:
        self.questions = []
        for question in Bottleneck().get_questions():
            elements = [
                *question.checkboxes,
                *question.texts,
                *question.diagramms,
                *question.tables,
            ]
            if not elements or min(e.page for e in elements) < self.first_page:
                continue
            question = copy.deepcopy(question)
            for e in [
                *question.checkboxes,
                *question.texts,
                *question.diagramms,
                *question.tables,
            ]:
                e.page -= self.first_page - 1
            self.questions.append(question)

    def get_num_pages(self) -> int:
        return 2

    def get_questions(self) -> Sequence[Question]:
        return self.questions

    def get_participant_number(self) -> ParticipantNumber:
        # no "Nummer" boxes, the number is written somewhere in the header, often at the very top of the page
        return ParticipantNumber(page=1, dx=-245, dy=-375, size_x=3550, size_y=760)


class GrabExperiment:
    # built-in layout (JSON)-based questionnaires: <type>_layout.json in here
    layoutDir = Path(__file__).resolve().parent / "layouts"
    layoutSuffix = "_layout.json"

    @staticmethod
    def layout_types() -> list[str]:
        """Names of the built-in layout-based types found in ``layoutDir``."""
        suffix = GrabExperiment.layoutSuffix
        return sorted(p.name.removesuffix(suffix) for p in GrabExperiment.layoutDir.glob("*" + suffix))

    @staticmethod
    def find_layout(experimentType: str) -> Path | None:
        """Layout file of a built-in layout-based type, None if there is none."""
        path = GrabExperiment.layoutDir / (experimentType + GrabExperiment.layoutSuffix)
        return path if path.is_file() else None

    @staticmethod
    def load_layout_template(path: str | Path) -> Template:
        path = Path(path)
        if not path.is_file():
            raise RuntimeError(f"layout file not found: {path}")
        # deferred: questionnaire_layout imports this module by file path
        from src import questionnaire_layout

        return questionnaire_layout.build_template(questionnaire_layout.load_layout(path))

    @staticmethod
    def initType(experimentType: str, layout: str | Path | None = None, baseDir: str | Path | None = None) -> Template:
        """Template of a survey form.

        An explicit ``layout`` file (relative paths are taken relative to ``baseDir``)
        wins over the type name; the name then only labels the form. Otherwise the
        name is a legacy type or a built-in layout in ``layoutDir``.
        """
        if layout is not None:
            path = Path(layout)
            if baseDir is not None and not path.is_absolute():
                path = Path(baseDir) / path
            return GrabExperiment.load_layout_template(path)
        if experimentType in ExperimentTypes:
            experimentType = ExperimentTypes(experimentType)
            if experimentType == ExperimentTypes.ROPE:
                return Rope()
            elif experimentType == ExperimentTypes.BOTTLENECK:
                return Bottleneck()
            elif experimentType == ExperimentTypes.ROPE_SHORT:
                return RopeShort()
        path = GrabExperiment.find_layout(experimentType)
        if path is not None:
            return GrabExperiment.load_layout_template(path)
        raise RuntimeError(
            f"Unknown experiment type {experimentType!r}. Valid types: "
            f"{[str(t) for t in ExperimentTypes] + GrabExperiment.layout_types()} or a path to a layout JSON file."
        )

    @staticmethod
    def initFromMetadata(metadata: dict, baseDir: str | Path, surveyMetadata: dict | None = None) -> Template:
        """Template of the experiment in ``metadata.json`` (in ``baseDir``), or of one of
        its surveys: a survey with its own "type" and/or "layout" uses only those, as its
        form differs from the rest of the experiment."""
        experiment = metadata["Experiment"]
        if surveyMetadata is not None and ("type" in surveyMetadata or "layout" in surveyMetadata):
            experimentType = surveyMetadata.get("type", experiment["Type"])
            layout = surveyMetadata.get("layout")
        else:
            experimentType, layout = experiment["Type"], experiment.get("Layout")
        return GrabExperiment.initType(experimentType, layout, baseDir)

    @staticmethod
    def get_page_bounds(template: Template):
        bounds = {}

        for q in template.get_questions():
            elements = []
            elements.extend(q.checkboxes)
            elements.extend(q.texts)
            elements.extend(q.tables)
            elements.extend(q.diagramms)

            for e in elements:
                page = e.page
                top = e.dy
                bottom = e.dy + getattr(e, "size_y", 70)

                if page not in bounds:
                    bounds[page] = [top, bottom]
                else:
                    bounds[page][0] = min(bounds[page][0], top)
                    bounds[page][1] = max(bounds[page][1], bottom)

        return bounds

    @staticmethod
    def get_question_top(question: Question) -> int:
        # start value at page bottom
        top = 5850
        elements = []
        elements.extend(question.checkboxes)
        elements.extend(question.texts)
        elements.extend(question.tables)
        elements.extend(question.diagramms)

        page = elements[0].page
        for e in elements:
            if e.page <= page and e.dy <= top:
                page = e.page
                top = e.dy

        result = top + ((page - 1) * 5850)
        return result
