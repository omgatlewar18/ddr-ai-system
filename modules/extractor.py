import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.pdf_utils import open_pdf, extract_text_by_page, extract_images_from_pdf
from app.config import IMAGES_DIR, PROMPTS_DIR, MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT
from modules.llm_client import call_llm

logger = logging.getLogger(__name__)


# -------------------------------
# 🔹 DATA MODEL
# -------------------------------

@dataclass
class ExtractionResult:
    source: str
    observations: list[dict]
    images: list[dict]
    raw_text: str                      # 🔥 ADDED
    errors: list[str] = field(default_factory=list)


# -------------------------------
# 🔹 PROMPT LOADER (SAFE)
# -------------------------------

def load_prompt(name):
    path = PROMPTS_DIR / f"{name}.txt"

    if not path.exists():
        logger.warning(f"Prompt file missing: {name}.txt — using fallback")
        return "Extract structured observations from the document."

    return path.read_text(encoding="utf-8")


# -------------------------------
# 🔹 MAIN EXTRACTION FUNCTION
# -------------------------------

def extract_from_pdf(pdf_path, source):
    pdf_path = Path(pdf_path)
    logger.info(f"[Extractor] {pdf_path.name} ({source})")

    errors = []

    doc = open_pdf(pdf_path)

    # 🔥 FIX: pass source_name
    pages = extract_text_by_page(doc, source)

    # 🔥 BUILD RAW TEXT (IMPORTANT)
    raw_text = "\n".join(p["text"] for p in pages if p.get("text"))

    images = extract_images_from_pdf(
        doc,
        source_name=source,
        output_dir=IMAGES_DIR,
        min_width=MIN_IMAGE_WIDTH,
        min_height=MIN_IMAGE_HEIGHT,
    )

    prompt = load_prompt("extraction_prompt")

    observations = extract_observations_per_page(
        pages, images, source, prompt, errors
    )

    doc.close()

    return ExtractionResult(
        source=source,
        observations=observations,
        images=images,
        raw_text=raw_text,            # 🔥 ADDED
        errors=errors,
    )


# -------------------------------
# 🔹 PAGE-LEVEL EXTRACTION
# -------------------------------

def extract_observations_per_page(pages, images, source, prompt_template, errors):
    all_obs = []

    for page in pages:
        page_num = page["page"]
        text = page["text"]

        if not text.strip():
            continue

        page_images = [img for img in images if img["page"] == page_num]

        image_summary = "\n".join(
            f"{img['image_id']} | context: {img.get('context_text','')[:100]}"
            for img in page_images
        ) or "None"

        prompt = prompt_template.format(
            source=source.upper(),
            text=text,
            image_list=image_summary,
            page=page_num
        )

        try:
            response = call_llm(prompt)
            parsed = _parse_observations(response, source)

            for obs in parsed:
                obs["page_ref"] = page_num

                # fallback image assignment
                if not obs.get("image_ids"):
                    if page_images:
                        obs["image_ids"] = [page_images[0]["image_id"]]
                    else:
                        obs["image_ids"] = ["Image Not Available"]

            all_obs.extend(parsed)

        except Exception as e:
            msg = f"Page {page_num} extraction failed: {e}"
            logger.error(msg)
            errors.append(msg)

    return all_obs


# -------------------------------
# 🔹 JSON PARSER
# -------------------------------

def _parse_observations(llm_response, source):
    text = llm_response.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        data = json.loads(text)
    except Exception as e:
        logger.error(f"JSON parse failed: {e}")
        return []

    if isinstance(data, dict) and "observations" in data:
        data = data["observations"]

    if not isinstance(data, list):
        return []

    cleaned = []

    for obs in data:
        if not isinstance(obs, dict):
            continue

        if not obs.get("area") or not obs.get("issue"):
            continue

        cleaned.append({
            "area": obs.get("area", "Unknown Area"),
            "issue": obs.get("issue", "Unknown Issue"),
            "description": obs.get("description", "Not Available"),
            "source": source,
            "temperature_data": obs.get("temperature_data", "Not Available"),
            "image_ids": obs.get("image_ids", []),
            "page_ref": obs.get("page_ref", 0),
        })

    return cleaned