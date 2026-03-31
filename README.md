# DDR AI System — Detailed Diagnostic Report Generator

> An AI-powered pipeline that converts raw inspection and thermal imaging PDFs into structured, client-ready Detailed Diagnostic Reports (DDR).

---

## Overview

The DDR AI System is a modular, production-grade pipeline that:

1. **Extracts** text and images from inspection + thermal PDFs
2. **Structures** raw text into validated observation objects
3. **Merges** multi-source data, removing duplicates and detecting conflicts
4. **Reasons** over evidence to generate root causes and severity ratings
5. **Validates** all output against source documents (anti-hallucination gate)
6. **Generates** a professional DDR in Markdown and self-contained HTML

The system is LLM-agnostic — it supports OpenAI (GPT-4o), Anthropic (Claude), and Google (Gemini) via a single provider switch.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INPUT LAYER                          │
│   inspection_report.pdf    thermal_report.pdf           │
└──────────────────┬──────────────────┬───────────────────┘
                   │                  │
         ┌─────────▼──────────────────▼─────────┐
         │        STAGE 1: EXTRACTION             │
         │  • PDF text extraction (PyMuPDF)       │
         │  • Image extraction + ID assignment    │
         │  • LLM structuring (extraction_prompt) │
         └─────────────────┬─────────────────────┘
                           │
         ┌─────────────────▼─────────────────────┐
         │        STAGE 2: STRUCTURING            │
         │  • Normalise fields                    │
         │  • Assign images to observations       │
         │  • Infer severity hints from temps     │
         └─────────────────┬─────────────────────┘
                           │
         ┌─────────────────▼─────────────────────┐
         │          STAGE 3: MERGING              │
         │  • Combine inspection + thermal data   │
         │  • Deduplicate observations            │
         │  • Detect conflicts (status tagging)   │
         │  • LLM merge (merge_prompt)            │
         └─────────────────┬─────────────────────┘
                           │
         ┌─────────────────▼─────────────────────┐
         │         STAGE 4: REASONING             │
         │  • Root cause analysis                 │
         │  • Severity: Low / Medium / High       │
         │  • Recommendations per observation     │
         │  • LLM reasoning (reasoning_prompt)    │
         └─────────────────┬─────────────────────┘
                           │
         ┌─────────────────▼─────────────────────┐
         │  STAGE 5: VALIDATION (anti-hallucin.)  │
         │  • Structural field checks             │
         │  • LLM cross-check vs raw text         │
         │  • Fill missing → "Not Available"      │
         │  • Flag conflicts and risks            │
         └─────────────────┬─────────────────────┘
                           │
         ┌─────────────────▼─────────────────────┐
         │       STAGE 6: REPORT GENERATION       │
         │  • Client-friendly narrative (LLM)     │
         │  • Markdown DDR                        │
         │  • Self-contained HTML with images     │
         └─────────────────┬─────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    OUTPUT LAYER                          │
│   outputs/final_report.md    outputs/final_report.html  │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ddr-ai-system/
│
├── app/
│   ├── main.py          # Pipeline orchestrator + CLI
│   └── config.py        # All configuration + env variables
│
├── modules/
│   ├── llm_client.py    # Provider-agnostic LLM interface
│   ├── extractor.py     # Stage 1: PDF text + image extraction
│   ├── structurer.py    # Stage 2: Observation normalisation
│   ├── merger.py        # Stage 3: Multi-source merging
│   ├── reasoning.py     # Stage 4: Root cause + severity
│   ├── validator.py     # Stage 5: Anti-hallucination validation
│   └── report_generator.py  # Stage 6: Markdown + HTML output
│
├── prompts/
│   ├── extraction_prompt.txt   # LLM prompt for structuring raw text
│   ├── merge_prompt.txt        # LLM prompt for merging sources
│   ├── reasoning_prompt.txt    # LLM prompt for root cause analysis
│   ├── validation_prompt.txt   # LLM prompt for hallucination check
│   └── report_prompt.txt       # LLM prompt for narrative generation
│
├── utils/
│   ├── pdf_utils.py     # PyMuPDF wrappers (text + image extraction)
│   └── image_utils.py   # Base64 encoding, HTML img tags, Data URIs
│
├── outputs/             # All generated files land here
│   ├── images/          # Extracted PDF images
│   ├── final_report.md
│   ├── final_report.html
│   └── pipeline.log
│
├── demo/
│   └── demo.py          # Self-contained demo with synthetic PDFs
│
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-org/ddr-ai-system.git
cd ddr-ai-system
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Choose your LLM provider: openai | anthropic | gemini
LLM_PROVIDER=anthropic

# API keys (only the one you use needs to be set)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# Optional overrides
MAX_TOKENS=4096
TEMPERATURE=0.2
COMPANY_NAME=Your Company Name
```

---

## How to Run

### Option A: Run on your own PDFs

```bash
python app/main.py \
    --inspection path/to/inspection_report.pdf \
    --thermal    path/to/thermal_report.pdf \
    --property   "42 Green Lane, Sector 7" \
    --date       "16 January 2025"
```

### Option B: Run the built-in demo

The demo creates synthetic PDFs and runs the full pipeline — no real PDFs needed:

### Option C: Use as a library

```python
from app.main import run_pipeline

result = run_pipeline(
    inspection_pdf="reports/inspection.pdf",
    thermal_pdf="reports/thermal.pdf",
    property_name="42 Green Lane",
)

print(result["html_path"])   # Path to the HTML report
print(result["markdown_path"])  # Path to the Markdown report
```

### Output

After running, check the `outputs/` directory:

| File | Description |
|------|-------------|
| `final_report.html` | Self-contained HTML report (open in browser or convert to PDF) |
| `final_report.md` | Markdown version of the DDR |
| `images/` | All images extracted from both PDFs |
| `pipeline.log` | Full execution log for debugging |

---

## DDR Output Structure

The generated report contains these sections:

| # | Section | Description |
|---|---------|-------------|
| 1 | Property Issue Summary | Executive overview of findings |
| 2 | Area-wise Observations | Each finding with description, temperature data, and images |
| 3 | Probable Root Cause | Evidence-based cause per observation |
| 4 | Severity Assessment | Low / Medium / High with reasoning |
| 5 | Recommended Actions | Prioritised action list |
| 6 | Additional Notes | Contextual notes and limitations |
| 7 | Missing Information | Explicitly notes "Not Available" items |
| 8 | Conflicts & Flags | Where sources disagree or validation raised issues |

---

## LLM Prompt Design

The system uses **5 focused prompts** — one per pipeline stage — rather than one large prompt. This improves reliability, debuggability, and allows each stage to be improved independently.

| Prompt | Purpose |
|--------|---------|
| `extraction_prompt.txt` | Convert raw PDF text into structured JSON observations |
| `merge_prompt.txt` | Intelligently merge and deduplicate from two sources |
| `reasoning_prompt.txt` | Generate root causes and severity ratings from evidence |
| `validation_prompt.txt` | Cross-check output against source text for hallucinations |
| `report_prompt.txt` | Generate client-friendly narrative sections |

---

## Limitations

1. **Token limits** — Very long PDFs are truncated to 12,000 characters for the extraction prompt. Future versions should implement chunking.
2. **Image-text association** — Image-to-observation mapping is heuristic (page proximity). A vision model would improve precision.
3. **No vision input** — The LLM currently analyses text only; thermal images are referenced but not interpreted by the model.
4. **Language** — Optimised for English-language reports.
5. **PDF quality** — Scanned PDFs without OCR will produce empty text extraction.
6. **API dependency** — Requires a live LLM API key. No offline mode.

---

## Future Improvements

- [ ] **PDF chunking** — Handle very long documents via sliding window extraction
- [ ] **Vision integration** — Pass thermal images to a vision-capable LLM for direct interpretation
- [ ] **OCR support** — Add Tesseract/EasyOCR for scanned PDFs
- [ ] **Web interface** — Drag-and-drop upload portal
- [ ] **PDF output** — WeasyPrint integration for direct PDF generation from HTML
- [ ] **Confidence scores** — Each observation rated by extraction confidence
- [ ] **Multi-property batch** — Process multiple properties in parallel
- [ ] **Audit trail** — Full provenance tracking for each claim in the report
- [ ] **Template system** — Client-specific DDR templates

---

## License

MIT License — see LICENSE for details.
