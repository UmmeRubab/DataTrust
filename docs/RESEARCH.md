# DataTrust — Research Methodology

## Research Motivation

Automated document understanding systems can extract structured data but may produce incorrect, incomplete, or inconsistent values.

DataTrust explores how independent validation rules can complement multimodal AI extraction.

## Research Questions

**RQ1:** How accurately does multimodal extraction recover invoice fields?

**RQ2:** Which invoice attributes and document characteristics contribute to extraction errors?

**RQ3:** Which potential inconsistencies can deterministic validation identify?

## Current Method

1. Select a public invoice.
2. Extract structured data with a multimodal model.
3. Apply rule-based validation.
4. Compare supported fields against available reference annotations.
5. Inspect individual failures.

## Experimental Variables

- Document category
- Document layout
- Target field
- Extraction model
- Validation rule

## Current Evaluation

The application supports simplified field matching, including numeric tolerance for monetary values.

A field match rate from one document is not an aggregate benchmark result.

## Planned Experiments

### Experiment A — Extraction Reliability
Evaluate multiple documents and report field-level results.

### Experiment B — Baseline Comparison
Compare multimodal extraction with a separate document extraction baseline.

### Experiment C — Data Quality Validation
Evaluate whether validation rules identify known inconsistencies.

### Experiment D — Failure Analysis
Group extraction errors by field type and document category.

## Metrics to Consider

- Exact-match accuracy
- Numeric absolute error
- Precision, recall, and F1 where applicable
- Missing-field detection rate
- Error rate by document category

## Reproducibility Requirements

Future benchmark reports should record:

- Dataset version and document IDs
- Model identifier
- Extraction prompt version
- Validation rules
- Evaluation code version
- Run date
- Failed and skipped records

## Limitations

The current application has not completed a full benchmark evaluation.

Synthetic invoice performance cannot be assumed to generalize to real-world business documents.

The implemented validation checks identify possible issues, not independently verified fraud or accounting errors.

## Research Integrity

Only observed, reproducible experimental results should be reported as findings. Planned features and experiments must be clearly distinguished from implemented functionality.


## Implemented exploratory batch evaluation (v0.3)

A controlled 1–10-document experiment now reports micro/macro mapped-field match, per-field comparisons, document-level failures and exports. See [EXPERIMENTS.md](EXPERIMENTS.md). This does not establish official benchmark accuracy.
