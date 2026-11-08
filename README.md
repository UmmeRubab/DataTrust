# DataTrust
### Intelligent Invoice Processing and Data Quality Evaluation

**DataTrust** is a Python and Streamlit research prototype for extracting structured information from invoices, validating data quality, and comparing extracted fields against reference annotations.

The project investigates the reliability of AI-assisted document processing, with an emphasis on data correctness, transparent validation, and reproducible evaluation.

## Project Links

- **GitHub:** https://github.com/UmmeRubab/DataTrust
- **Dataset:** https://huggingface.co/datasets/drew-ipp/invoice-extraction-benchmark
- **Live Demo:** https://datatrustt.streamlit.app/

## Problem Statement

Invoices contain structured financial information presented in different document layouts. Manual extraction can be time-consuming, while automated extraction can introduce missing fields, incorrect values, and calculation inconsistencies.

DataTrust explores how AI extraction and deterministic validation can be combined to identify potential data-quality problems.

## Objectives

1. Extract structured fields from invoice PDFs and images.
2. Detect missing and inconsistent information.
3. Validate arithmetic and date relationships.
4. Compare extracted values with public reference annotations.
5. Investigate extraction failures and reliability limitations.

## Current Features

| Component | Description |
|---|---|
| Public invoice selection | Select documents from a public benchmark |
| Multimodal extraction | Extract invoice fields using Gemini |
| Structured output | Generate JSON containing invoice information |
| Required-field validation | Identify missing essential information |
| Financial reconciliation | Flag subtotal, tax, and total mismatches |
| Date validation | Check invoice and due-date consistency |
| Line-item validation | Flag quantity and unit-price inconsistencies |
| Benchmark comparison | Compare supported fields with reference annotations |
| Export | Download extracted JSON and evaluation CSV |

**Status:** Initial prototype. End-to-end functionality and benchmark compatibility must be verified on the deployed application.

## System Architecture

```text
Public Invoice Benchmark
          |
          v
Document Selection and Loading
          |
          v
Gemini Multimodal Extraction
          |
          v
Structured Invoice JSON
          |
          +----------------------+
          |                      |
          v                      v
Data Quality Rules       Reference Answer Key
          |                      |
          +-----------+----------+
                      |
                      v
           Evaluation and Reports
                      |
                      v
               JSON / CSV Export
```

## Technology Stack

- **Language:** Python 3.12
- **Application:** Streamlit
- **AI:** Google Gemini API
- **Data Processing:** Pandas
- **Visualization:** Plotly
- **Dataset Access:** Hugging Face Hub
- **PDF Utilities:** pypdf, PyMuPDF (server-side PDF preview)
- **Image Utilities:** Pillow
- **Deployment:** Streamlit Community Cloud
- **Version Control:** Git and GitHub

## Dataset

DataTrust uses the public **Invoice Extraction Benchmark** by drew-ipp.

Dataset repository:
https://huggingface.co/datasets/drew-ipp/invoice-extraction-benchmark

The benchmark contains synthetic invoice documents and reference annotations. Dataset attribution and applicable licensing requirements remain with the original dataset publisher.

The dataset is downloaded as needed and is not bundled with this repository.

## Getting Started

### Prerequisites

- Python 3.12
- Git
- Gemini API key

### Clone

```powershell
git clone https://github.com/UmmeRubab/DataTrust.git
cd DataTrust
```

### Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Configure secrets

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_SUPPORTED_GEMINI_MODEL"
```

Do not commit API keys.

### Run locally (optional)

```powershell
python -m streamlit run app.py
```

The hosted application runs on Streamlit Community Cloud.

## Research Methodology

1. Select an invoice document.
2. Perform multimodal field extraction.
3. Validate the extracted values using deterministic rules.
4. Load the corresponding reference annotation.
5. Compare supported fields.
6. Inspect errors and possible causes.

See [Research Methodology](docs/RESEARCH.md).

## Evaluation

The prototype implements field-level comparison for supported invoice attributes.

Potential evaluation dimensions include:

- Field-level accuracy
- Missing-value detection
- Numeric extraction error
- Document-category performance
- Arithmetic inconsistency detection
- Line-item extraction performance

**No aggregate benchmark accuracy is claimed at this stage.**

## Current Limitations

- The current implementation evaluates one document at a time.
- Reference field mapping may require adaptation to the dataset schema.
- Official benchmark scoring has not yet been integrated.
- Line-item extraction is not comprehensively scored.
- Financial discrepancies can reflect legitimate adjustments.
- Synthetic documents may not represent production invoice distributions.
- Model availability and output quality depend on the configured Gemini API.

## Planned Improvements

- Batch evaluation across benchmark documents
- Comparison with an independent extraction baseline
- Error analysis by document category
- More robust reference annotation mapping
- Field-level uncertainty and human-review workflows
- Improved document processing interface
- Reproducible experiment reports

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Research Methodology](docs/RESEARCH.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Changelog](CHANGELOG.md)

## Author

**Umme Rubab**

Research interests: Machine Learning, Natural Language Processing, Trustworthy AI, and Data Quality.

## Acknowledgments

Public invoice benchmark: drew-ipp / Invoice Extraction Benchmark.

## License

No license has been selected for the DataTrust source code yet. All rights remain with the copyright holder unless a license is added.

Third-party datasets, models, and libraries retain their respective licenses.


## Batch Benchmarking (v0.3)

The **Batch benchmark & error analysis** section processes a selected sample of 1–10 public invoice documents. It records successes, failures, per-document field match rates, validation findings, and per-field mismatches. It provides CSV exports and experiment metadata. Each document makes a Gemini API call; check API quota and pricing before running.

**Metrics:** Micro field match is the proportion of correctly matched mapped fields across successfully evaluated documents. Macro field match is the average of per-document field match rates. Failed documents and documents with no mapped fields are counted separately, not silently treated as successes. Missing reference mappings are not evaluated.

**Sampling:** The first N records in dataset order, optionally filtered by category. This is not a randomized or representative sample. There is no claim of official benchmark accuracy.

**Currency:** A previous example extracted `$` where the answer key recorded `USD`. The application maps `$` to `USD` only when the benchmark document ID indicates US context; otherwise the symbol is left ambiguous. The raw model output is retained. The latest observed extraction returned `USD` directly. Future work should make currency mapping document-context-aware.

**Reproducibility:** Download all available CSVs and the experiment metadata JSON immediately after a run; results are stored in the Streamlit browser session, not a persistent experiment database. Record model version, dataset revision, prompt, and code commit for publication-grade experiments.

**Known limitations:** No independent OCR/regex baseline, no line-item scoring, no confidence calibration, no stratified sampling, and no official benchmark scoring protocol. Gemini model behavior and API availability may vary.
