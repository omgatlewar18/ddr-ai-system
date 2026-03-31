"""
report_generator.py — FINAL PRODUCTION VERSION
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.validator import ValidationResult
from modules.reasoning import ReasoningResult, AnalysedObservation
from utils.image_utils import build_image_block
from app.config import (
    OUTPUTS_DIR, REPORT_TITLE,
    REPORT_FOOTER, COMPANY_NAME,
)

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Unknown": 3}

SEVERITY_COLOURS = {
    "High": "#c0392b",
    "Medium": "#e67e22",
    "Low": "#27ae60",
    "Unknown": "#95a5a6",
}

STATUS_LABELS = {
    "aligned": "✅ Aligned",
    "partial": "⚠️ Partial",
    "conflict": "❌ Conflict",
    "single_source": "📄 Single Source",
}


# -------------------------------
# 🔹 MAIN ENTRY
# -------------------------------

def generate_report(
    validation_result: ValidationResult,
    reasoning_result: ReasoningResult,
    all_images: list[dict],
    property_name="Site Under Inspection",
    report_date=None,
):

    logger.info("[ReportGenerator] Generating report")

    report_date = report_date or datetime.now().strftime("%d %B %Y")

    obs_list = validation_result.validated_observations

    # 🔥 Sort by severity
    obs_list = sorted(obs_list, key=lambda x: SEVERITY_ORDER.get(x.severity, 3))

    image_lookup = {img["image_id"]: img for img in all_images}

    # 🔥 Deterministic summary
    summary = _generate_summary(obs_list)

    # Clean priority actions
    priority_actions = list(dict.fromkeys(reasoning_result.priority_actions))[:10]

    md_content = _build_markdown(
        obs_list,
        summary,
        validation_result,
        reasoning_result,
        image_lookup,
        property_name,
        report_date,
        priority_actions,
    )

    html_content = _build_html(
        obs_list,
        summary,
        validation_result,
        reasoning_result,
        image_lookup,
        property_name,
        report_date,
        priority_actions,
    )

    md_path = OUTPUTS_DIR / "final_report.md"
    html_path = OUTPUTS_DIR / "final_report.html"

    md_path.write_text(md_content, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    return {
        "markdown_path": str(md_path),
        "html_path": str(html_path),
    }


# -------------------------------
# 🔹 SUMMARY
# -------------------------------

def _generate_summary(obs_list):
    high = sum(1 for o in obs_list if o.severity == "High")
    medium = sum(1 for o in obs_list if o.severity == "Medium")
    low = sum(1 for o in obs_list if o.severity == "Low")

    return (
        f"{len(obs_list)} issues identified. "
        f"{high} high, {medium} medium, {low} low severity."
    )


# -------------------------------
# 🔹 MARKDOWN
# -------------------------------

def _build_markdown(
    obs_list, summary, validation_result,
    reasoning_result, image_lookup,
    property_name, report_date, priority_actions
):

    lines = [
        f"# {REPORT_TITLE}",
        f"**Property:** {property_name}",
        f"**Date:** {report_date}",
        f"**Prepared by:** {COMPANY_NAME}",
        "",
        "---",
        "",
        "## 1. Property Issue Summary",
        "",
        summary,
        "",
        "## 2. Area-wise Observations",
        "",
    ]

    areas = {}
    for obs in obs_list:
        areas.setdefault(obs.area, []).append(obs)

    for area, items in areas.items():
        lines.append(f"### {area}")
        lines.append("")

        for obs in items:
            lines += [
                f"#### {obs.issue}",
                f"*Severity: {obs.severity} | Confidence: {obs.confidence}*",
                obs.description,
                "",
            ]

    # FIXED TABLE
    lines += [
        "## 4. Severity Assessment",
        "",
        "| Area | Issue | Severity | Reason |",
        "|------|-------|----------|--------|",
    ]

    for obs in obs_list:
        lines.append(
            f"| {obs.area} | {obs.issue} | {obs.severity} | {obs.severity_reason} |"
        )

    lines.append("")

    # Actions
    lines += ["## 5. Recommended Actions", ""]
    for i, a in enumerate(priority_actions, 1):
        lines.append(f"{i}. {a}")

    return "\n".join(lines)


# -------------------------------
# 🔹 HTML
# -------------------------------

def _build_html(
    obs_list, summary, validation_result,
    reasoning_result, image_lookup,
    property_name, report_date, priority_actions
):

    areas = {}
    for obs in obs_list:
        areas.setdefault(obs.area, []).append(obs)

    area_html = ""

    for area, items in areas.items():
        area_html += f"<h3>{area}</h3>"

        for obs in items:
            color = SEVERITY_COLOURS.get(obs.severity, "#999")

            area_html += f"""
<div>
<h4>{obs.issue}</h4>
<p><strong>Severity:</strong> <span style="color:{color}">{obs.severity}</span></p>
<p><strong>Confidence:</strong> {obs.confidence}</p>
<p>{obs.description}</p>
"""

            for img_id in obs.image_ids:
                area_html += build_image_block(img_id, image_lookup, obs)

            area_html += "</div>"

    priority_html = "".join(f"<li>{a}</li>" for a in priority_actions)

    return f"""
<html>
<body>
<h1>{REPORT_TITLE}</h1>
<p>{property_name} | {report_date}</p>

<h2>Summary</h2>
<p>{summary}</p>

<h2>Observations</h2>
{area_html}

<h2>Recommended Actions</h2>
<ol>{priority_html}</ol>

</body>
</html>
"""