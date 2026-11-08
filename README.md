# DataTrust / Quality Studio

**Multimodal Invoice Extraction, Data Quality Validation, and Benchmark Evaluation**

[Live Application](https://datatrustst.streamlit.app/) · [Source Code](https://github.com/UmmeRubab/DataTrust)

## Overview

DataTrust is an interactive research prototype for examining the reliability of AI-assisted invoice data extraction. It combines multimodal document understanding with deterministic data-quality checks and comparison against publicly available reference annotations.

The application is designed to answer a practical question: **Can structured information extracted from an invoice be checked systematically before it is trusted or used downstream?**

Rather than presenting model-generated fields as automatically correct, DataTrust separates extraction, validation, and benchmark evaluation. It supports individual document inspection and exploratory batch experiments through a Streamlit interface.

## Key Features

- **Public invoice explorer:** Select and inspect synthetic invoice documents from a public benchmark, including document category and difficulty where available.
- **Multimodal extraction:** Use the Gemini API to extract invoice fields and line items from document content.
- **Readable extraction results:** Display supplier information, invoice identifiers, dates, currency, financial totals, and itemized entries in tables.
- **Deterministic quality checks:** Identify missing or inconsistent fields, date issues, line-item arithmetic discrepancies, and differences between subtotal, tax, and total.
- **Reference comparison:** Compare supported extracted fields with the dataset's answer keys using field-aware normalization, including supported currency symbol/code equivalences.
- **Batch evaluation:** Evaluate a selected number of benchmark documents, with document-level status, field-level matches, aggregate match rates, and error analysis.
- **Research exports:** Download field-level results, per-field summaries, document-level results, and single-document evaluation results as CSV files.
- **Failure visibility:** Report failed or unmapped documents separately instead of treating them as successful evaluations.

## System Workflow

```text
Public Synthetic Invoice Dataset
             |
             v
   Document Selection & Preview
             |
             v
    Gemini Multimodal Extraction
             |
             v
      Structured Invoice Fields
             |
       +-----+------+
       |            |
       v            v
Deterministic    Reference Answer
Quality Checks      Comparison
       |            |
       +-----+------+
             |
             v
    Evaluation & Error Analysis
             |
             v
   Streamlit Dashboard / CSV Export
```

## Extracted Information

The prototype is designed to extract and display:

| Group | Example fields |
| --- | --- |
| Supplier | Supplier/vendor name |
| Invoice identity | Invoice number, invoice date, due date |
| Currency | Currency symbol or code |
| Amounts | Subtotal, tax, total |
| Line items | Description, quantity, unit price, amount |

The exact fields available depend on the document and extraction response. A missing value is not automatically an extraction error if the original invoice does not contain that information.

## Dataset

**Public benchmark:** [`drew-ipp/invoice-extraction-benchmark`](https://huggingface.co/datasets/drew-ipp/invoice-extraction-benchmark) on Hugging Face.

The deployed interface displays **181 available benchmark documents**. The dataset contains synthetic invoice examples and reference annotations used for exploratory evaluation. DataTrust does not require users to upload private invoices.

**Important:** The number of available documents is not the number of documents evaluated in a given experiment. Report the evaluated sample size alongside every result.

## Technology Stack

- **Python** — application logic, validation, and evaluation
- **Streamlit** — interactive research interface
- **Google Gemini API (`google-genai`)** — multimodal document extraction
- **Pandas** — tabular analysis and CSV exports
- **Plotly** — evaluation charts
- **Hugging Face Hub** — public benchmark access
- **PyPDF / Pillow** — document and image handling where applicable

The Gemini model is configured through the `GEMINI_MODEL` secret. Model availability, API limits, and billing conditions are controlled by the API provider and may change.

## Local Setup

### Prerequisites

- Python 3.12 recommended
- A Gemini API key with access to a compatible multimodal model
- Internet connectivity for API calls and public dataset downloads

### Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/UmmeRubab/DataTrust.git
cd DataTrust
```

Create and activate a virtual environment on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` locally:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_AVAILABLE_GEMINI_MODEL"
```

Set `GEMINI_MODEL` to a model supported by your API account. The deployed prototype has been demonstrated using a configured Gemini model; the README intentionally does not assume universal access to a particular model ID.

Run the application:

```powershell
python -m streamlit run app.py
```

**Security:** Never commit `.streamlit/secrets.toml`, API keys, or other credentials. Confirm the secrets file is excluded by `.gitignore` before pushing changes.

## Using the Application

### Individual Invoice Analysis

1. Choose a document category and benchmark invoice.
2. Click **Load selected invoice** to inspect the source document.
3. Click **Extract & validate** to request multimodal extraction.
4. Review the extracted fields, line items, and quality findings.
5. Click **Compare with ground truth** to evaluate supported fields against the public answer key.
6. Export the available evaluation results as CSV when needed.

### Batch Benchmark & Error Analysis

1. Select the experiment category and number of documents.
2. Review the configured model and potential API usage.
3. Click **Run batch evaluation**.
4. Inspect attempted, evaluated, and failed document counts; micro field match; macro document-average match; and per-field results.
5. Review document-level failures and validation findings before interpreting aggregate metrics.
6. Export field-level, per-field, or document-level CSV reports for further analysis.

The current sampling approach processes the first *N* documents in dataset order for the selected category; it is **not randomized**. Batch results are maintained in the active Streamlit session and may be lost when that session resets.

## Evaluation Methodology

### Field Comparison

Supported predicted fields are mapped to corresponding reference annotations. The comparison applies field-aware normalization where appropriate. For example, an unambiguous US-dollar symbol (`$`) may be considered equivalent to `USD` for comparison purposes while the original predicted and reference values remain visible.

The displayed field match rate is:

```text
Field match rate = Number of correct compared fields / Number of compared fields
```

### Batch Metrics

- **Micro field match:** Total correct mapped fields divided by total compared mapped fields across successfully evaluated documents.
- **Macro document-average field match:** Mean of per-document field match rates for successfully evaluated documents.
- **Per-field match rate:** Correct comparisons for a given field divided by its number of comparisons.
- **Failure count:** Documents that could not be successfully extracted or evaluated are recorded separately.
- **Validation findings:** Rule-based inconsistencies, which are distinct from reference-label mismatches.

These metrics describe the implemented field comparisons, not a comprehensive measure of semantic correctness or end-to-end production reliability. Failed documents are excluded from the successful-evaluation match-rate denominator and must always be reported separately.

### Observed Prototype Results

During a small exploratory batch test, **3 of 3 documents were evaluated**, with **24 of 24 compared fields matching** (100% micro field match) for that specific run. This is a small, non-random sample and **must not be presented as accuracy across the full benchmark**.

In a separate run, some requests returned **HTTP 429 `RESOURCE_EXHAUSTED`** due to Gemini API quota or rate limits. Those documents were marked as failed, not as extraction successes. A transient **HTTP 503 `UNAVAILABLE`** response was also observed during testing. These are service-availability limitations and should be distinguished from model extraction errors.

## Data Quality Rules

The implemented checks examine issues such as:

- Required fields that are absent or incomplete
- Financial reconciliation between subtotal, tax, and total
- Due dates that precede invoice dates, when both are available
- Line-item quantity × unit price versus stated line amount

A flagged inconsistency is a **review signal**, not necessarily proof that the extracted data is wrong. For example, shipping charges, discounts, or other adjustments can explain a difference between subtotal + tax and the final total. Likewise, passing all current rules does not guarantee that an extraction is correct.

## Research Questions

DataTrust can support exploratory investigation of:

1. Which invoice fields are most frequently misread or omitted by a multimodal model?
2. How does extraction reliability vary by document category or difficulty?
3. Which errors can be detected through deterministic validation without access to the reference answer key?
4. How do service failures and missing reference mappings affect reported evaluation metrics?
5. How do discounts, delivery fees, and other legitimate adjustments influence financial consistency checks?

## Reproducibility and Limitations

- The prototype uses **synthetic public invoices**; performance may differ on real-world documents.
- The displayed 181-document collection has **not** been exhaustively evaluated in the results described here.
- Small, sequential samples may overrepresent easy documents and are not statistically representative.
- The model can return different outputs over time as provider behavior or model versions change.
- API quotas, transient errors, and service availability can interrupt extraction and batch evaluation.
- The current validation rules do not model every possible financial adjustment or invoice format.
- The reported field match covers mapped reference fields; it does not necessarily score every extracted line item or all possible document attributes.
- A missing field may be correctly absent, and matching null values can affect apparent accuracy; results should be interpreted alongside field coverage.
- No independently implemented OCR-only or non-LLM baseline is included in the current prototype.
- These results are **exploratory project measurements**, not official benchmark leaderboard scores.

For reproducible future experiments, record the run date, configured model ID, selected category, document IDs, attempted and evaluated counts, failed requests, and exported CSV outputs.

## Future Improvements

- Add bounded retries and exponential backoff for transient 429/503 responses, respecting provider limits.
- Introduce randomized or stratified sampling across categories and difficulty levels.
- Expand experiments to larger samples and publish reproducible result files.
- Add an independent baseline for meaningful model comparison.
- Evaluate line-item extraction and field coverage more comprehensively.
- Extend reconciliation logic for shipping, discounts, and other invoice adjustments.
- Add optional confidence and error taxonomy analyses.

## Project Status

**Version 1.0 — Deployed Research Prototype**

The interactive invoice inspection, extraction, validation, reference comparison, exploratory batch evaluation, and CSV reporting workflows have been demonstrated. Broader benchmark claims require additional controlled experiments.

## Links

- **Live demo:** [https://datatrustst.streamlit.app/](https://datatrustt.streamlit.app/)
- **Repository:** https://github.com/UmmeRubab/DataTrust
- **Dataset:** https://huggingface.co/datasets/drew-ipp/invoice-extraction-benchmark

## License

No license is declared in this README. Refer to the repository for any subsequently added license file and to the dataset provider for dataset-specific terms.
