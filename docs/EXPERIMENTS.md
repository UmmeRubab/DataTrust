# DataTrust — Experiment Guide

## Run an experiment

1. Open the deployed application and scroll to **Batch benchmark & error analysis**.
2. Select a document category or all categories.
3. Start with three documents; maximum ten per run. Each document triggers a model API request.
4. Run the experiment and inspect the failure count.
5. Download document-level CSV, field-level CSV, field-summary CSV, and metadata JSON.
6. Record the Git commit, dataset revision, and prompt version separately for repeatability.

## Metrics

- **Micro field match:** correct mapped fields divided by all mapped fields from successfully evaluated documents.
- **Macro field match:** unweighted mean of each evaluated document's mapped-field match rate.
- **Per-field match:** correct comparisons for a field divided by mapped comparisons for that field.
- **Failures:** model, retrieval, parsing, or evaluation failures are reported separately and excluded from accuracy denominators.

These are prototype comparison metrics, not an official benchmark score. The evaluation may count a pair of missing values as a match if the reference explicitly contains null. Missing reference fields are skipped.

## Currency caveat

The evaluator maps `$` to `USD` only for documents with an explicitly US-coded document ID. Without that context, `$` remains ambiguous. More robust document-context inference remains future work.

## Validity threats

- Small, first-N sample is not random or stratified.
- Synthetic invoices do not establish production performance.
- Gemini outputs may vary across model versions and runs.
- Only eight selected header fields are compared; line items are not benchmark-scored.
- No independent baseline or official scoring protocol is included.
- API failures reduce the number of evaluated documents.

## Next research work

Introduce an independent OCR/text-extraction baseline, randomized or stratified sampling with a fixed seed, line-item evaluation, robust context-aware currency mapping, persistent experiment logs, and repeated-run confidence intervals.
