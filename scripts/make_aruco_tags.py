"""Generate the ArUco tag PNGs (DICT_4X4_50) that the Typst templates print.

The four page-corner tags use IDs 1, 4, 3, 2 (top-left, top-right,
bottom-right, bottom-left), which is what deskew() in the processing tool
expects. The body figure already carries its own tags (12, 11, 13, 14)
inside typst_src/assets/diagram.png.
"""

import cv2
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "typst_src" / "assets"

# tag id -> corner on the questionnaire page
PAGE_TAGS = {1: "top-left", 4: "top-right", 3: "bottom-right", 2: "bottom-left"}


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for tag_id in sorted(PAGE_TAGS):
        img = cv2.aruco.generateImageMarker(aruco_dict, tag_id, 512)
        out = ASSETS / f"aruco-{tag_id}.png"
        cv2.imwrite(str(out), img)
        print(f"wrote {out} (id {tag_id}, {PAGE_TAGS[tag_id]})")


if __name__ == "__main__":
    main()
