"""
validator.py — FINAL UPGRADED VERSION (HYBRID VALIDATION)
"""

import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reasoning import AnalysedObservation, ReasoningResult
from modules.llm_client import call_llm
from app.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


@dataclass
class ValidationFlag:
    obs_id: str
    field: str
    issue: str
    severity: str


@dataclass
class ValidationResult:
    validated_observations: list[AnalysedObservation]
    flags: list[ValidationFlag]
    missing_info: list[str]
    hallucination_risks: list[str]
    is_valid: bool
    validation_summary: str


# -------------------------------
# 🔹 MAIN
# -------------------------------

def validate_output(reasoning_result, raw_inspection_text, raw_thermal_text):

    logger.info("[Validator] Running validation")

    obs_list = reasoning_result.analysed_observations

    flags = _run_structural_checks(obs_list)

    # 🔥 NEW: deterministic hallucination detection
    hallucination_risks = _detect_hallucinations(
        obs_list, raw_inspection_text, raw_thermal_text, flags
    )

    # 🔥 LLM as secondary validation (not primary)
    try:
        val_data = _llm_validation(obs_list, raw_inspection_text, raw_thermal_text)
        missing_info = val_data.get("missing_info", [])
    except:
        missing_info = []

    # downgrade confidence if hallucination risk
    for obs in obs_list:
        if any(obs.obs_id in r for r in hallucination_risks):
            obs.confidence = max(0.2, obs.confidence - 0.3)

    error_count = sum(1 for f in flags if f.severity == "error")

    return ValidationResult(
        validated_observations=obs_list,
        flags=flags,
        missing_info=missing_info,
        hallucination_risks=hallucination_risks,
        is_valid=(error_count == 0),
        validation_summary=f"{len(flags)} flags, {len(hallucination_risks)} risks",
    )


# -------------------------------
# 🔹 STRUCTURAL CHECKS
# -------------------------------

def _run_structural_checks(obs_list):
    flags = []

    for obs in obs_list:
        if not obs.area:
            flags.append(ValidationFlag(obs.obs_id, "area", "Missing area", "error"))

        if obs.severity not in ("Low", "Medium", "High", "Unknown"):
            flags.append(ValidationFlag(
                obs.obs_id, "severity", "Invalid severity", "error"
            ))

    return flags


# -------------------------------
# 🔹 HALLUCINATION DETECTION
# -------------------------------

def _detect_hallucinations(obs_list, insp_text, therm_text, flags):

    combined_text = (insp_text + " " + therm_text).lower()

    risks = []

    for obs in obs_list:
        keywords = _extract_keywords(obs)

        match_count = sum(1 for k in keywords if k in combined_text)

        if match_count < 2:
            risks.append(f"{obs.obs_id}: weak evidence match")

            flags.append(ValidationFlag(
                obs.obs_id,
                "hallucination",
                "Low keyword match with source text",
                "warning"
            ))

    return risks


def _extract_keywords(obs):
    text = f"{obs.area} {obs.issue} {obs.description}".lower()
    words = [w for w in text.split() if len(w) > 4]
    return words[:5]


# -------------------------------
# 🔹 LLM VALIDATION (SECONDARY)
# -------------------------------

def _llm_validation(obs_list, insp_text, therm_text):

    prompt = _load_prompt("validation_prompt")

    obs_data = [_obs_to_dict(o) for o in obs_list]

    msg = prompt.format(
        observations=json.dumps(obs_data),
        inspection_text=insp_text[:4000],
        thermal_text=therm_text[:3000],
    )

    response = call_llm(msg)

    return _parse_json(response)


# -------------------------------
# 🔹 HELPERS
# -------------------------------

def _load_prompt(name):
    return (PROMPTS_DIR / f"{name}.txt").read_text()


def _parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])

    try:
        return json.loads(text)
    except:
        return {}


def _obs_to_dict(obs):
    return {
        "obs_id": obs.obs_id,
        "area": obs.area,
        "issue": obs.issue,
        "description": obs.description,
        "severity": obs.severity,
    }