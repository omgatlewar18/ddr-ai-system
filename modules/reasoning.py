import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.merger import MergedObservation
from modules.llm_client import call_llm
from app.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


# -------------------------------
# 🔹 DATA MODELS
# -------------------------------

@dataclass
class AnalysedObservation:
    obs_id: str
    area: str
    issue: str
    description: str
    sources: list[str]
    temperature_data: str
    image_ids: list[str]
    status: str
    conflict_note: str

    root_cause: str
    severity: str
    severity_reason: str
    recommendations: list[str]
    confidence: float


@dataclass
class ReasoningResult:
    analysed_observations: list[AnalysedObservation]
    overall_summary: str
    priority_actions: list[str]


# -------------------------------
# 🔹 MAIN FUNCTION
# -------------------------------

def reason_over_observations(merged_observations):

    logger.info(f"[Reasoning] {len(merged_observations)} observations")

    obs_dicts = [_to_dict(m) for m in merged_observations]

    prompt = _load_prompt("reasoning_prompt")

    try:
        response = call_llm(prompt.format(observations=json.dumps(obs_dicts, indent=2)))
        data = _parse(response)
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        data = {}

    reasoning_map = {
        r["obs_id"]: r
        for r in data.get("analysed_observations", [])
        if "obs_id" in r
    }

    analysed = []

    for mo in merged_observations:
        r = reasoning_map.get(mo.obs_id, {})

        severity = _normalize_severity(r.get("severity", mo.severity_hint))
        confidence = _compute_confidence(mo, severity)

        analysed.append(AnalysedObservation(
            obs_id=mo.obs_id,
            area=mo.area,
            issue=mo.issue,
            description=mo.description,
            sources=mo.sources,
            temperature_data=mo.temperature_data,
            image_ids=mo.image_ids,
            status=mo.status,
            conflict_note=mo.conflict_note,

            root_cause=r.get("root_cause", "Not Available"),
            severity=severity,
            severity_reason=r.get("severity_reason", "Not Available"),
            recommendations=r.get("recommendations", []),
            confidence=confidence
        ))

    # SYSTEM-CONTROLLED PRIORITIZATION
    priority_actions = _rank_priority_actions(analysed)

    return ReasoningResult(
        analysed_observations=analysed,
        overall_summary=data.get("overall_summary", "Not Available"),
        priority_actions=priority_actions
    )


# -------------------------------
# 🔹 HELPERS
# -------------------------------

def _to_dict(m):
    return {
        "obs_id": m.obs_id,
        "area": m.area,
        "issue": m.issue,
        "description": m.description,
        "sources": m.sources,
        "temperature_data": m.temperature_data,
        "status": m.status,
        "conflict_note": m.conflict_note,
    }


def _load_prompt(name):
    return (PROMPTS_DIR / f"{name}.txt").read_text()


def _parse(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except:
        return {}


# -------------------------------
# 🔹 SYSTEM LOGIC (IMPORTANT)
# -------------------------------

def _normalize_severity(sev):
    sev = str(sev).lower()

    if "high" in sev:
        return "High"
    if "medium" in sev:
        return "Medium"
    if "low" in sev:
        return "Low"

    return "Medium"


def _compute_confidence(mo, severity):
    score = 0.5

    if mo.status == "aligned":
        score += 0.3
    if mo.status == "conflict":
        score -= 0.2

    if severity == "High":
        score += 0.1

    return round(max(0.0, min(1.0, score)), 2)


def _rank_priority_actions(observations):
    high = []
    medium = []
    low = []

    for obs in observations:
        if obs.severity == "High":
            high.extend(obs.recommendations)
        elif obs.severity == "Medium":
            medium.extend(obs.recommendations)
        else:
            low.extend(obs.recommendations)

    return list(dict.fromkeys(high + medium + low))[:10]