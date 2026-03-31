import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.llm_client import call_llm
from app.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


# -------------------------------
# 🔹 DATA MODELS
# -------------------------------

@dataclass
class MergedObservation:
    obs_id: str
    area: str
    issue: str
    description: str
    sources: list[str]
    temperature_data: str
    image_ids: list[str]
    status: str
    conflict_note: str
    confidence: float


@dataclass
class MergeResult:
    merged_observations: list[MergedObservation]
    conflicts: list[dict]
    merge_summary: str


# -------------------------------
# 🔹 MAIN FUNCTION
# -------------------------------

def merge_observations(inspection_obs, thermal_obs):
    logger.info(f"[Merger] {len(inspection_obs)} + {len(thermal_obs)}")

    # Step 1: Normalize text
    insp = [_normalize(o) for o in inspection_obs]
    therm = [_normalize(o) for o in thermal_obs]

    # Step 2: Pre-match by area
    grouped = _group_by_area(insp, therm)

    merged = []
    conflicts = []

    for idx, group in enumerate(grouped):
        result = _merge_group(group)

        mo = MergedObservation(
            obs_id=f"merged_{idx+1:03d}",
            area=result["area"],
            issue=result["issue"],
            description=result["description"],
            sources=result["sources"],
            temperature_data=result["temperature_data"],
            image_ids=result["image_ids"],
            status=result["status"],
            conflict_note=result["conflict_note"],
            confidence=result["confidence"],
        )

        merged.append(mo)

        if mo.status == "conflict":
            conflicts.append({
                "obs_id": mo.obs_id,
                "area": mo.area,
                "issue": mo.issue,
                "note": mo.conflict_note
            })

    return MergeResult(
        merged_observations=merged,
        conflicts=conflicts,
        merge_summary=f"{len(merged)} merged observations, {len(conflicts)} conflicts."
    )


# -------------------------------
# 🔹 NORMALIZATION
# -------------------------------

def _normalize(obs):
    return {
        **obs,
        "area": obs["area"].lower().strip(),
        "issue": obs["issue"].lower().strip(),
    }


# -------------------------------
# 🔹 GROUPING LOGIC
# -------------------------------

def _group_by_area(insp, therm):
    groups = []

    used = set()

    for i in insp:
        match = next(
            (t for t in therm if t["area"] == i["area"]),
            None
        )

        if match:
            groups.append({"inspection": i, "thermal": match})
            used.add(id(match))
        else:
            groups.append({"inspection": i})

    for t in therm:
        if id(t) not in used:
            groups.append({"thermal": t})

    return groups


# -------------------------------
# 🔹 MERGE LOGIC
# -------------------------------

def _merge_group(group):
    insp = group.get("inspection")
    therm = group.get("thermal")

    # Case 1: both present
    if insp and therm:
        conflict = _detect_conflict(insp, therm)

        return {
            "area": insp["area"],
            "issue": insp["issue"],
            "description": _combine_text(insp, therm),
            "sources": ["inspection", "thermal"],
            "temperature_data": therm.get("temperature_data", "Not Available"),
            "image_ids": list(set(insp["image_ids"] + therm["image_ids"])),
            "status": "conflict" if conflict else "aligned",
            "conflict_note": conflict,
            "confidence": 0.9 if not conflict else 0.6,
        }

    # Case 2: single source
    obs = insp or therm

    return {
        "area": obs["area"],
        "issue": obs["issue"],
        "description": obs["description"],
        "sources": [obs["source"]],
        "temperature_data": obs.get("temperature_data", "Not Available"),
        "image_ids": obs.get("image_ids", []),
        "status": "single_source",
        "conflict_note": "",
        "confidence": 0.5,
    }


# -------------------------------
# 🔹 CONFLICT LOGIC (IMPORTANT)
# -------------------------------

def _detect_conflict(insp, therm):
    insp_text = insp["description"].lower()
    therm_text = therm["description"].lower()

    if "no issue" in insp_text and "moisture" in therm_text:
        return "Inspection says no issue, but thermal indicates moisture."

    if "dry" in insp_text and "cold" in therm_text:
        return "Dry surface but thermal anomaly detected."

    return ""


# -------------------------------
# 🔹 TEXT COMBINATION
# -------------------------------

def _combine_text(insp, therm):
    return f"{insp['description']} | Thermal: {therm['description']}"