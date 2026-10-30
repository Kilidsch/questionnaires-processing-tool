# MIT License
# Copyright (c) 2026 Marvin Lorber

__license__ = "MIT"
__author__ = ["Marvin Lorber"]

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

# If you want to use this, you have to install torch and transformers.
# ATTENTION: Running this script downloads additional ~40 GB of hand-writing detection model

# choose a small handwritten model; first run downloads it, then it’s cached locally
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


def recognize_handwriting(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        generated_ids = model.generate(pixel_values, max_length=64)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()
