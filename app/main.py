
import argparse
import logging
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.extractor import extract_from_pdf
from modules.structurer import structure_observations
from modules.merger import merge_observations
from modules.reasoning import reason_over_observations
from modules.validator import validate_output
from modules.report_generator import generate_report
from app.config import OUTPUTS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def run_pipeline(inspection_pdf, thermal_pdf, property_name, report_date):

    start = time.time()
    report_date = report_date or datetime.now().strftime("%d %B %Y")

    try:
        insp = extract_from_pdf(inspection_pdf, "inspection")
        therm = extract_from_pdf(thermal_pdf, "thermal")
    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}")

    # SAVE RAW
    _save_json("stage1_extraction.json", {
        "inspection": insp.observations,
        "thermal": therm.observations
    })

    # STRUCTURE
    insp_s = structure_observations(insp.observations, insp.images, "inspection")
    therm_s = structure_observations(therm.observations, therm.images, "thermal")

    # MERGE
    merge = merge_observations(insp_s, therm_s)
    _save_json("stage3_merge.json", [m.__dict__ for m in merge.merged_observations])

    # REASON
    reason = reason_over_observations(merge.merged_observations)
    _save_json("stage4_reason.json", [r.__dict__ for r in reason.analysed_observations])

    # VALIDATE
    validation = validate_output(
        reason,
        insp.raw_text,
        therm.raw_text
    )

    # REPORT
    output = generate_report(
        validation,
        reason,
        insp.images + therm.images,
        property_name,
        report_date
    )

    elapsed = time.time() - start

    # 🔥 METRICS
    avg_conf = sum(o.confidence for o in validation.validated_observations) / len(validation.validated_observations)

    print("\n=== PIPELINE SUMMARY ===")
    print(f"Time: {elapsed:.2f}s")
    print(f"Observations: {len(validation.validated_observations)}")
    print(f"Avg Confidence: {avg_conf:.2f}")
    print(f"Validation: {'PASS' if validation.is_valid else 'FAIL'}")
    print(f"Reports: {output}")

    return output




def _save_json(name, data):
    path = OUTPUTS_DIR / name
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    import sys

    # If arguments are passed → CLI mode
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument("--inspection", required=True)
        parser.add_argument("--thermal", required=True)
        parser.add_argument("--property", default="Site")
        parser.add_argument("--date", default=None)

        args = parser.parse_args()

        run_pipeline(
            args.inspection,
            args.thermal,
            args.property,
            args.date
        )

    else:
        # Interactive mode
        print("\n=== DDR AI SYSTEM ===")

        inspection = input("Enter Inspection PDF path: ").strip()
        thermal = input("Enter Thermal PDF path: ").strip()
        property_name = input("Enter Property Name (optional): ").strip() or "Site"

        run_pipeline(
            inspection,
            thermal,
            property_name,
            None
        )

if __name__ == "__main__":
    main()