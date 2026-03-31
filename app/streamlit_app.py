import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import tempfile

from app.main import run_pipeline

from app.main import run_pipeline

st.set_page_config(page_title="DDR AI System", layout="wide")

st.title("🏗️ DDR AI Report Generator")

st.markdown("Upload inspection and thermal reports to generate a diagnostic report.")

# Upload files
inspection_file = st.file_uploader("Upload Inspection Report (PDF)", type=["pdf"])
thermal_file = st.file_uploader("Upload Thermal Report (PDF)", type=["pdf"])

property_name = st.text_input("Property Name", "Final Report")

# Button
if st.button("Generate Report"):

    if not inspection_file or not thermal_file:
        st.error("Please upload both PDFs")
        st.stop()

    with st.spinner("Processing... This may take a few seconds."):

        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f1:
            f1.write(inspection_file.read())
            inspection_path = f1.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f2:
            f2.write(thermal_file.read())
            thermal_path = f2.name

        # Run pipeline
        try:
            result = run_pipeline(
                inspection_path,
                thermal_path,
                property_name,
                None
            )
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.success("Report Generated Successfully!")

    # Show outputs
    html_path = Path(result["html_path"])
    md_path = Path(result["markdown_path"])

    # Display HTML
    st.subheader("📄 Report Preview")

    html_content = html_path.read_text(encoding="utf-8")
    st.components.v1.html(html_content, height=600, scrolling=True)

    # Download buttons
    st.download_button(
        label="Download HTML Report",
        data=html_content,
        file_name="report.html",
        mime="text/html"
    )

    st.download_button(
        label="Download Markdown Report",
        data=md_path.read_text(),
        file_name="report.md",
        mime="text/markdown"
    )