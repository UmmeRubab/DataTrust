# Changelog

## 0.2.1 — Preview and evaluation fixes

- Render PDF pages server-side with PyMuPDF instead of browser-blocked data URLs.
- Improve text contrast for download, secondary, and primary buttons.
- Normalize unambiguous currency symbols for field comparison while preserving raw outputs.
- Clarify that the displayed field match rate is per-document, not a full benchmark result.
- No new benchmark-wide accuracy claims.

## Version 0.2.0 — Quality Studio UI redesign

- Replaced sidebar and four-tab navigation with a document processing workspace.
- Added side-by-side invoice preview and structured extraction.
- Integrated validation and reference evaluation into the main page.
- Improved accessibility, color contrast and responsive layout.
- Preserved existing extraction, validation and benchmark functions.
- Updated the live Streamlit link in README.



## Version 0.1.0 — Initial Prototype

### Implemented
- Streamlit application scaffold
- Public benchmark document selection
- Gemini-based invoice extraction
- Rule-based data-quality validation
- Preliminary field-level evaluation
- JSON and CSV export functionality

### Documentation
- Project README
- System architecture
- Research methodology
- Deployment instructions

### Pending Verification
- End-to-end hosted execution
- Benchmark schema compatibility
- Aggregate evaluation

### Planned
- Redesigned document intelligence workspace
- Batch evaluation
- Independent baseline
- More comprehensive reliability metrics
