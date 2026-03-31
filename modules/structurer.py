"""
structurer.py — FINAL UPGRADED VERSION
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StructuredObservation:
    obs_id: str
    area: str
    issue: str
    description: str
    source: str
    temperature_data: str
    image_ids: list[str]
    page_ref: int
    severity_hint: str = "Unknown"
    keywords: list[str] = None
    confidence: float = 0.5


# -------------------------------
# 🔹 MAIN FUNCTION
# -------------------------------

def structure_observations(raw_observations, images, source):

    logger.info(f"[Structurer] {len(raw_observations)} observations")

    page_to_images = {}
    for img in images:
        page_to_images.setdefault(img["page"], []).append(img)

    valid_ids = {img["image_id"] for img in images}

    structured = []

    for idx, obs in enumerate(raw_observations):
        obs_id = f"{source[:4]}_{idx+1:03d}"

        area = _clean(obs.get("area"))
        issue = _clean(obs.get("issue"))
        desc = _clean(obs.get("description"))
        temp = _clean(obs.get("temperature_data"))
        page = int(obs.get("page_ref", 0))

        keywords = _extract_keywords(area, issue, desc)

        image_ids = _assign_images(obs, page, keywords, page_to_images, valid_ids)

        severity = _infer_severity(temp, desc)

        confidence = _compute_confidence(temp, desc, image_ids)

        structured.append(StructuredObservation(
            obs_id=obs_id,
            area=area,
            issue=issue,
            description=desc,
            source=source,
            temperature_data=temp,
            image_ids=image_ids,
            page_ref=page,
            severity_hint=severity,
            keywords=keywords,
            confidence=confidence
        ))

    return structured


# -------------------------------
# 🔹 CLEANING
# -------------------------------

def _clean(text):
    if not text or not isinstance(text, str):
        return "Not Available"

    text = re.sub(r"\s+", " ", text).strip()
    return text


# -------------------------------
# 🔹 KEYWORD EXTRACTION
# -------------------------------

def _extract_keywords(area, issue, desc):
    text = f"{area} {issue} {desc}".lower()

    words = re.findall(r"\b[a-z]{3,}\b", text)

    # remove common noise
    stop = {"the", "and", "with", "from", "this", "that"}
    return list(set(w for w in words if w not in stop))


# -------------------------------
# 🔹 IMAGE MATCHING (UPGRADED)
# -------------------------------

def _assign_images(obs, page, keywords, page_to_images, valid_ids):

    # Priority 1: LLM assigned
    valid = [i for i in obs.get("image_ids", []) if i in valid_ids]
    if valid:
        return valid

    candidates = page_to_images.get(page, [])

    # 🔥 keyword match
    scored = []

    for img in candidates:
        context = (img.get("context_text") or "").lower()
        score = sum(1 for k in keywords if k in context)

        if score > 0:
            scored.append((score, img["image_id"]))

    if scored:
        scored.sort(reverse=True)
        return [s[1] for s in scored[:2]]

    # fallback
    return [img["image_id"] for img in candidates[:1]]


# -------------------------------
# 🔹 SEVERITY (UPGRADED)
# -------------------------------

def _infer_severity(temp, desc):
    desc = desc.lower()

    if any(k in desc for k in ["leak", "crack", "seepage", "damage"]):
        return "High"

    numbers = re.findall(r"[-+]?\d+\.?\d*", temp)
    nums = [float(n) for n in numbers] if numbers else []

    if len(nums) >= 2:
        delta = max(nums) - min(nums)
    elif nums:
        delta = nums[0]
    else:
        return "Unknown"

    if delta > 15:
        return "High"
    elif delta > 5:
        return "Medium"
    return "Low"


# -------------------------------
# 🔹 CONFIDENCE
# -------------------------------

def _compute_confidence(temp, desc, images):

    score = 0.4

    if temp != "Not Available":
        score += 0.2

    if images:
        score += 0.2

    if len(desc) > 30:
        score += 0.2

    return round(min(score, 1.0), 2)


# -------------------------------
# 🔹 EXPORT
# -------------------------------

def observations_to_dict_list(obs_list):
    return [
        {
            "obs_id": o.obs_id,
            "area": o.area,
            "issue": o.issue,
            "description": o.description,
            "source": o.source,
            "temperature_data": o.temperature_data,
            "image_ids": o.image_ids,
            "page_ref": o.page_ref,
            "severity_hint": o.severity_hint,
            "keywords": o.keywords,
            "confidence": o.confidence,
        }
        for o in obs_list
    ]