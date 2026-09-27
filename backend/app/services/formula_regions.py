import os
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image


@lru_cache(maxsize=1)
def _load_detector():
    from pix2text import MathFormulaDetector

    device = os.getenv("MATH_DETECTOR_DEVICE") or None
    model_backend = os.getenv("MATH_DETECTOR_BACKEND", "onnx")
    return MathFormulaDetector(device=device, model_backend=model_backend)


def save_formula_crop(page_image: Path, bounds: tuple[int, int, int, int], crop_path: Path) -> None:
    x_min, y_min, x_max, y_max = bounds
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(page_image) as source:
        source.crop((x_min, y_min, x_max, y_max)).save(crop_path, format="PNG")


def detect_page_regions(
    document_id: UUID,
    page_number: int,
    page_image: Path,
    formulas_dir: Path,
) -> list[dict]:
    detector = _load_detector()
    detections = detector(str(page_image), resized_shape=1024)

    with Image.open(page_image) as source:
        image_width, image_height = source.size

    proposals = []
    for detection in detections:
        points = detection["box"]
        x_min = max(0, int(min(point[0] for point in points)))
        y_min = max(0, int(min(point[1] for point in points)))
        x_max = min(image_width, int(max(point[0] for point in points)) + 1)
        y_max = min(image_height, int(max(point[1] for point in points)) + 1)
        if x_max <= x_min or y_max <= y_min:
            continue

        formula_id = uuid4()
        crop_path = formulas_dir / f"{formula_id}.png"
        save_formula_crop(page_image, (x_min, y_min, x_max, y_max), crop_path)
        proposals.append(
            {
                "id": formula_id,
                "document_id": document_id,
                "page_number": page_number,
                "image_path": str(crop_path),
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
                "confidence": float(detection.get("score", 0.0)),
                "status": "proposed",
            }
        )
    return proposals