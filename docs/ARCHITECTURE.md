# DataTrust — System Architecture

## Overview

DataTrust combines AI-based document extraction with deterministic validation and reference-based evaluation.

## Components

### 1. Dataset Interface
Retrieves public benchmark metadata and selected invoice documents through Hugging Face Hub.

### 2. Extraction Engine
Sends supported PDF or image documents to a configured Gemini multimodal model and requests structured JSON.

### 3. Validation Engine
Checks required fields, dates, totals, and line-item arithmetic.

### 4. Evaluation Engine
Compares mapped extraction fields against public reference annotations.

### 5. Presentation Layer
Uses Streamlit to present document selection, extraction output, validation findings, and evaluation reports.

## Processing Flow

```text
Dataset -> Document -> AI Extraction -> Structured JSON
                                         |
                           +-------------+-------------+
                           |                           |
                     Validation                  Ground Truth
                           |                           |
                           +-------------+-------------+
                                         |
                                    Evaluation
                                         |
                                  User Interface
```

## Design Principles

- Keep extraction separate from validation.
- Treat AI outputs as unverified until checked.
- Preserve original extracted values.
- Flag potential inconsistencies instead of silently correcting them.
- Avoid reporting unsupported accuracy claims.
- Keep secrets outside source control.

## Future Architecture

Potential extensions include batch processing, a non-LLM extraction baseline, experiment tracking, and more comprehensive benchmark scoring.
