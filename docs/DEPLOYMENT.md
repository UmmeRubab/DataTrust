# DataTrust — Deployment Guide

## Deployment Platform

Streamlit Community Cloud

## Source Repository

https://github.com/UmmeRubab/DataTrust

## Entry Point

`app.py`

## Python Dependencies

Defined in `requirements.txt`.

## Secrets

Configure the following in Streamlit Community Cloud app settings:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_SUPPORTED_GEMINI_MODEL"
```

Never commit `.streamlit/secrets.toml`.

## Deployment Procedure

1. Connect the GitHub repository to Streamlit Community Cloud.
2. Select the `main` branch.
3. Set the application entry point to `app.py`.
4. Configure the required secrets.
5. Deploy the application.
6. Review application logs if loading or extraction fails.

## Verification Checklist

- [ ] Application loads
- [ ] Dataset metadata loads
- [ ] Invoice document downloads
- [ ] Extraction completes
- [ ] Validation findings display
- [ ] Reference annotations load
- [ ] Evaluation results display
- [ ] Exports download
- [ ] No credentials appear in GitHub

## Troubleshooting

### Dataset loading error
Check repository paths, metadata structure, and network access.

### Gemini model error
Verify the API key and supported model identifier.

### Reference comparison error
Inspect the dataset answer-key schema and field mapping.

### Dependency error
Review `requirements.txt` and Streamlit deployment logs.
