"""
image_utils.py — Advanced Image Handling for DDR Pipeline

Responsibilities:
  - Encode images (Base64 / Data URI)
  - Validate image integrity
  - Map images to observations
  - Generate intelligent captions
  - Render HTML blocks (single & multi-image)
"""

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported formats
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


# ---------------------------
# 🔹 BASIC UTILITIES
# ---------------------------

def encode_image_to_base64(image_path):
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def is_valid_image(image_path):
    path = Path(image_path)

    if not path.exists():
        return False

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        return False

    if path.stat().st_size == 0:
        return False

    return True


def get_image_data_uri(image_path):
    path = Path(image_path)
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported image format: {suffix}")

    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }

    mime_type = mime_map.get(suffix, "image/png")
    encoded = encode_image_to_base64(path)

    return f"data:{mime_type};base64,{encoded}"


# ---------------------------
# 🔹 LOOKUP SYSTEM
# ---------------------------

def build_image_lookup(image_list):
    """
    Create fast lookup: {image_id: metadata}
    """
    return {img["image_id"]: img for img in image_list}


# ---------------------------
# 🔹 IMAGE ↔ OBSERVATION MAPPING
# ---------------------------

def map_images_to_observations(observations, image_lookup):
    """
    Attach best matching image to each observation based on page.
    """
    for obs in observations:
        page = obs.get("page")

        matched = [
            img for img in image_lookup.values()
            if img.get("page") == page
        ]

        if matched:
            # assign first match (can improve later)
            obs["image_id"] = matched[0]["image_id"]
        else:
            obs["image_id"] = "Image Not Available"

    return observations


# ---------------------------
# 🔹 CAPTION GENERATION
# ---------------------------

def generate_image_caption(observation):
    """
    Generate readable caption from observation context.
    """
    issue = observation.get("issue", "")
    area = observation.get("area", "")

    if issue and area:
        return f"{issue} observed in {area}"

    if issue:
        return issue

    return "Inspection Image"


# ---------------------------
# 🔹 HTML GENERATORS
# ---------------------------

def get_html_img_tag(image_path, alt_text="", max_width="600px", caption=""):
    path = Path(image_path) if image_path else None

    if path and is_valid_image(path):
        try:
            data_uri = get_image_data_uri(path)

            html = (
                f'<figure class="report-image">'
                f'<img src="{data_uri}" alt="{alt_text}" '
                f'style="max-width:{max_width}; border:1px solid #ddd; '
                f'border-radius:4px; margin:8px 0;" />'
            )

            if caption:
                html += (
                    f'<figcaption style="font-size:0.85em;color:#666;">'
                    f'{caption}</figcaption>'
                )

            html += '</figure>'
            return html

        except Exception as e:
            logger.warning(f"Failed to embed image {path}: {e}")

    # fallback placeholder
    return (
        f'<div class="image-placeholder" style="'
        f'border:2px dashed #ccc; padding:20px; text-align:center; '
        f'color:#999; border-radius:4px; margin:8px 0; max-width:{max_width};">'
        f'🖼️ Image Not Available'
        f'</div>'
    )


def build_image_block(image_id, image_lookup, observation=None):
    """
    Build HTML for a single image using metadata + observation.
    """
    if image_id == "Image Not Available":
        return get_html_img_tag(None)

    img = image_lookup.get(image_id)

    if not img:
        return get_html_img_tag(None)

    caption = generate_image_caption(observation) if observation else ""

    return get_html_img_tag(
        img["path"],
        alt_text=caption,
        caption=caption
    )


def build_multi_image_block(image_ids, image_lookup, observation=None):
    """
    Build HTML for multiple images under one observation.
    """
    html = '<div class="image-group">'

    for img_id in image_ids:
        html += build_image_block(img_id, image_lookup, observation)

    html += '</div>'

    return html