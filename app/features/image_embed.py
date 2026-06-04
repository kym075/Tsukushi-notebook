import os
from PIL import Image


DEFAULT_IMAGE_WIDTH = 350
IMAGE_SIZE_OPTIONS = [
    ("小", 250),
    ("中", 350),
    ("大", 500),
]


def clamp_image_width(width):
    try:
        width = int(width)
    except (TypeError, ValueError):
        width = DEFAULT_IMAGE_WIDTH
    return max(100, min(width, 900))


def image_marker_text(img_filename, width=DEFAULT_IMAGE_WIDTH):
    return f"[image:{img_filename}|width={clamp_image_width(width)}]"


def parse_image_marker(line):
    if not line.startswith("[image:"):
        return None

    body = line[7:]
    if body.endswith("]"):
        body = body[:-1]

    img_filename = body
    width = DEFAULT_IMAGE_WIDTH
    if "|width=" in body:
        img_filename, width_text = body.split("|width=", 1)
        width_text = width_text.strip().rstrip("]")
        try:
            width = int(width_text)
        except ValueError:
            width = DEFAULT_IMAGE_WIDTH
        if width in (2, 3, 5):
            width = {2: 250, 3: 350, 5: 500}[width]

    return img_filename.strip(), clamp_image_width(width)


def normalize_image_markers_in_text(text):
    normalized_lines = []
    for line in text.split("\n"):
        image_marker = parse_image_marker(line)
        if image_marker:
            img_filename, image_width = image_marker
            normalized_lines.append(image_marker_text(img_filename, image_width))
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


def load_resized_image(img_path, width=DEFAULT_IMAGE_WIDTH):
    if not os.path.exists(img_path):
        return None

    with Image.open(img_path) as pil_img:
        orig_w, orig_h = pil_img.size
        new_w = clamp_image_width(width)
        if orig_w <= 0:
            return None
        new_h = max(1, int((new_w / orig_w) * orig_h))
        return pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS).copy()
