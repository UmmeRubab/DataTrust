
import io
import json
import mimetypes
import fitz  # PyMuPDF
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types
from huggingface_hub import hf_hub_download
from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Invoice Data Extraction & Validation | Intelligent Document Processing",
    page_icon="📑",
    layout="wide",
)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
.stApp {background:#F3F6FA;color:#18283D;font-family:'DM Sans',sans-serif}
.block-container {max-width:1480px;padding:1.2rem 2.4rem 4rem}
h1,h2,h3 {font-family:'Manrope',sans-serif!important;color:#12253A!important;letter-spacing:-.035em}
[data-testid="stSidebar"] {display:none}
[data-testid="stMetric"] {background:white;border:1px solid #E2E9F0;border-radius:14px;padding:16px}
[data-testid="stMetricLabel"] {color:#65768A}
[data-testid="stMetricValue"] {color:#12334C}
.stButton>button[kind="primary"] {background:#087F78;color:white;border:0;border-radius:10px;font-weight:700}
.stButton>button[kind="primary"]:hover {background:#06655F;color:white}
.stButton>button {border-radius:10px}
[data-baseweb="select"]>div {background:#FFFFFF!important;border:1px solid #D7E1E9!important;border-radius:10px!important}
[data-baseweb="select"] * {color:#17344B!important}
[data-testid="stWidgetLabel"] p {color:#31465B!important;font-weight:600}
[data-testid="stDataFrame"] {border:1px solid #E2E9F0;border-radius:12px;overflow:hidden}
[data-testid="stExpander"] {border:1px solid #DFE8F0;border-radius:12px;background:white}
.dt-hero {background:linear-gradient(110deg,#10283D 0%,#153D50 68%,#0B756F 100%);border-radius:20px;padding:31px 34px;color:white;margin:10px 0 24px}
.dt-eyebrow {font-size:11px;letter-spacing:.16em;color:#89E1D5;font-weight:800}
.dt-hero h1 {color:white!important;font-size:35px;margin:9px 0 5px}
.dt-hero p {color:#C5D8E1;font-size:14px;margin:0}
.dt-kicker {font-size:11px;color:#087F78;font-weight:800;letter-spacing:.13em;text-transform:uppercase;margin:18px 0 4px}
.dt-section {font-family:'Manrope',sans-serif;font-size:22px;font-weight:800;color:#152C41;margin:0 0 5px}
.dt-sub {font-size:13px;color:#65768A;margin-bottom:15px}
.dt-note {border-left:3px solid #0E9C91;padding:12px 14px;background:#E9F6F3;color:#23534E;border-radius:0 9px 9px 0;font-size:13px}
.dt-placeholder {height:290px;background:#F0F5F8;border:1px dashed #C9D8E2;border-radius:12px;display:flex;align-items:center;justify-content:center;text-align:center;color:#6C8292;padding:20px}
/* Contrast fixes for all native Streamlit buttons and download actions */
.stButton button[kind="secondary"],
.stDownloadButton button,
.stLinkButton a {
    background:#FFFFFF!important;
    color:#12334C!important;
    border:1px solid #B7C8D5!important;
    border-radius:10px!important;
    font-weight:700!important;
}
.stButton button[kind="secondary"]:hover,
.stDownloadButton button:hover,
.stLinkButton a:hover {
    background:#E9F6F3!important;
    color:#075F5A!important;
    border-color:#087F78!important;
}
.stButton button[kind="primary"] {
    background:#087F78!important;
    color:#FFFFFF!important;
    border:1px solid #087F78!important;
}
.stButton button[kind="primary"]:hover {
    background:#06655F!important;
    color:#FFFFFF!important;
}
.stButton button p, .stDownloadButton button p, .stLinkButton a p {color:inherit!important}
</style>
""", unsafe_allow_html=True)

REPO_ID = "drew-ipp/invoice-extraction-benchmark"
ROOT = "corpus/v1"

FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax",
    "total",
]

NUMERIC_FIELDS = {"subtotal", "tax", "total"}

EXTRACTION_PROMPT = """
You are a careful invoice information extraction system.

Read the attached invoice document and extract the following
fields into a JSON object:

{
  "vendor_name": null,
  "invoice_number": null,
  "invoice_date": null,
  "due_date": null,
  "currency": null,
  "subtotal": null,
  "tax": null,
  "total": null,
  "document_type": null,
  "line_items": []
}

Requirements:

1. Use only information visible in the document.
2. Never invent missing values.
3. Use null for unknown or unreadable fields.
4. Represent dates as YYYY-MM-DD when unambiguous.
5. Represent monetary amounts as JSON numbers.
6. Preserve the document's printed amounts.
7. Do not silently fix incorrect calculations.
8. Do not confuse purchase order numbers with invoice numbers.
9. Treat credit notes and invoices differently.
10. Return line_items as a list of objects containing:
    description, quantity, unit_price, amount.
11. Return valid JSON only.
"""


# ============================================================
# SETTINGS
# ============================================================

def get_setting(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


# ============================================================
# PUBLIC DATASET
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Loading benchmark records...")
def load_metadata():
    path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        filename=f"{ROOT}/metadata.jsonl",
    )

    records = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def repository_path(relative_path):
    path = str(relative_path).replace("\\", "/").lstrip("/")

    if path.startswith(ROOT + "/"):
        return path

    return f"{ROOT}/{path}"


@st.cache_data(ttl=3600, show_spinner=False)
def download_public_file(relative_path):
    path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        filename=repository_path(relative_path),
    )

    return Path(path).read_bytes()


def document_path(record):
    file_name = record.get("file_name")

    if not file_name:
        raise ValueError("Document file_name is missing.")

    file_name = str(file_name).replace("\\", "/")

    if file_name.startswith("documents/"):
        return file_name

    if "/documents/" in file_name:
        return file_name

    return f"documents/{file_name}"


def answer_path(record):
    answer_file = record.get("answer_file") or record.get("answer_key")

    if isinstance(answer_file, str) and answer_file.endswith(".json"):
        return answer_file

    doc_id = record.get("doc_id")

    if not doc_id:
        raise ValueError("Document ID is missing.")

    return f"answers/{doc_id}.json"


def load_selected_document(record):
    path = document_path(record)
    content = download_public_file(path)

    mime_type = mimetypes.guess_type(path)[0]

    if mime_type not in [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]:
        raise ValueError(f"Unsupported document format: {mime_type}")

    return content, mime_type


def load_reference(record):
    content = download_public_file(answer_path(record))
    return json.loads(content.decode("utf-8"))


# ============================================================
# GEMINI EXTRACTION
# ============================================================

def extract_invoice(document_bytes, mime_type):
    api_key = get_setting("GEMINI_API_KEY")
    model_name = get_setting("GEMINI_MODEL", "gemini-3.6-flash")

    if not api_key or api_key.startswith("PASTE_"):
        raise RuntimeError(
            "Please configure GEMINI_API_KEY in Streamlit secrets."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(
                data=document_bytes,
                mime_type=mime_type,
            ),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        raise ValueError("The model returned an empty response.")

    result = json.loads(response.text)

    if not isinstance(result, dict):
        raise ValueError("The model returned an invalid JSON structure.")

    return result


# ============================================================
# DATA QUALITY RULES
# ============================================================

def to_decimal(value):
    if value is None or isinstance(value, bool):
        return None

    try:
        amount = Decimal(str(value).replace(",", "").strip())
        return amount if amount.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def add_issue(issues, severity, rule, description):
    issues.append({
        "Severity": severity,
        "Rule": rule,
        "Description": description,
    })


def validate_invoice(extracted):
    issues = []

    required_fields = [
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "currency",
        "total",
    ]

    for field in required_fields:
        value = extracted.get(field)

        if value is None or str(value).strip() == "":
            add_issue(
                issues,
                "High",
                "Required field",
                f"Missing or unreadable field: {field}",
            )

    subtotal = to_decimal(extracted.get("subtotal"))
    tax = to_decimal(extracted.get("tax"))
    total = to_decimal(extracted.get("total"))

    if all(value is not None for value in [subtotal, tax, total]):
        expected = subtotal + tax
        difference = total - expected

        if abs(difference) > Decimal("0.01"):
            add_issue(
                issues,
                "Review",
                "Total reconciliation",
                (
                    f"Subtotal + tax = {expected}, but total = {total}. "
                    f"Difference: {difference}. Check discounts, shipping, "
                    "credits, and other adjustments before deciding "
                    "whether this is an error."
                ),
            )

    invoice_date = extracted.get("invoice_date")
    due_date = extracted.get("due_date")

    if invoice_date and due_date:
        try:
            invoice_dt = pd.Timestamp(invoice_date)
            due_dt = pd.Timestamp(due_date)

            if due_dt < invoice_dt:
                add_issue(
                    issues,
                    "Review",
                    "Date consistency",
                    "Due date precedes the invoice date.",
                )

        except (ValueError, TypeError):
            add_issue(
                issues,
                "Review",
                "Date parsing",
                "One or more dates could not be parsed.",
            )

    line_items = extracted.get("line_items", [])

    if isinstance(line_items, list):
        for index, item in enumerate(line_items, start=1):
            if not isinstance(item, dict):
                continue

            quantity = to_decimal(item.get("quantity"))
            price = to_decimal(item.get("unit_price"))
            amount = to_decimal(item.get("amount"))

            if all(
                value is not None
                for value in [quantity, price, amount]
            ):
                difference = amount - (quantity * price)

                if abs(difference) > Decimal("0.01"):
                    add_issue(
                        issues,
                        "Review",
                        "Line item calculation",
                        (
                            f"Line {index}: quantity × unit price "
                            f"does not match the extracted line amount. "
                            "Check discounts and tax conventions."
                        ),
                    )

    return issues


# ============================================================
# EVALUATION
# ============================================================

def normalize_text(value):
    if value is None:
        return None

    return " ".join(str(value).casefold().split())


def normalize_date(value):
    if value is None:
        return None

    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return normalize_text(value)


def normalize_currency(value):
    """Normalize only unambiguous currency representations for evaluation."""
    if value is None:
        return None
    normalized = str(value).strip().upper()
    symbols = {"US$": "USD", "USD": "USD",
               "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP",
               "¥": "JPY", "JPY": "JPY"}
    return symbols.get(normalized, normalized)


def match_field(field, predicted, expected, country_hint=None):
    if field == "currency":
        if country_hint == "US":
            predicted = "USD" if str(predicted).strip() == "$" else predicted
            expected = "USD" if str(expected).strip() == "$" else expected
        return normalize_currency(predicted) == normalize_currency(expected)

    if field in NUMERIC_FIELDS:
        a = to_decimal(predicted)
        b = to_decimal(expected)

        if a is None or b is None:
            return a is None and b is None

        return abs(a - b) <= Decimal("0.01")

    if field.endswith("_date"):
        return normalize_date(predicted) == normalize_date(expected)

    return normalize_text(predicted) == normalize_text(expected)


def find_reference_fields(reference):
    """
    Only evaluate fields when the answer key contains an
    identifiable field mapping. Never treat absent reference
    fields as automatically correct.
    """

    if not isinstance(reference, dict):
        return {}

    candidates = [reference]

    for key in ["fields", "header", "invoice", "expected", "answer"]:
        nested = reference.get(key)

        if isinstance(nested, dict):
            candidates.append(nested)

    aliases = {
        "vendor_name": ["vendor_name", "supplier_name", "vendor"],
        "invoice_number": ["invoice_number", "invoice_no"],
        "invoice_date": ["invoice_date", "date"],
        "due_date": ["due_date", "payment_due_date"],
        "currency": ["currency", "currency_code"],
        "subtotal": ["subtotal", "sub_total"],
        "tax": ["tax", "tax_total", "tax_amount"],
        "total": ["total", "grand_total", "amount_due"],
    }

    mapped = {}

    for field, names in aliases.items():
        for candidate in candidates:
            found = False

            for name in names:
                if name in candidate:
                    value = candidate[name]

                    if isinstance(value, (str, int, float)) or value is None:
                        mapped[field] = value
                        found = True
                        break

            if found:
                break

    return mapped


def evaluate_extraction(prediction, reference):
    expected_fields = find_reference_fields(reference)
    doc_id = str(reference.get("doc_id", "")).lower() if isinstance(reference, dict) else ""
    country_hint = "US" if doc_id.startswith("us-") or "-us-" in doc_id else None

    records = []

    for field in FIELDS:
        if field not in expected_fields:
            continue

        predicted = prediction.get(field)
        expected = expected_fields[field]

        records.append({
            "Field": field,
            "Predicted": predicted,
            "Reference": expected,
            "Correct": match_field(field, predicted, expected, country_hint=country_hint),
        })

    return pd.DataFrame(records)


# ============================================================
# DOCUMENT INTELLIGENCE WORKSPACE
# ============================================================

st.markdown("""
<div class="dt-hero">
  <div class="dt-eyebrow">DOCUMENT INTELLIGENCE / RESEARCH WORKSPACE</div>
  <h1>Data Trust</h1>
  <h4><span style="color:#77777">Invoice Data Extraction, Validation &amp; Evaluation.</span> </h4>
</div>
""", unsafe_allow_html=True)

try:
    metadata = load_metadata()
except Exception as error:
    metadata = []
    st.error(f"Unable to load benchmark metadata: {error}")

if not metadata:
    st.info("The workspace is waiting for public benchmark metadata.")
    st.stop()

st.markdown('<div class="dt-kicker">01 / Document selection</div>', unsafe_allow_html=True)
filter_col, doc_col = st.columns([1, 2], gap="medium")
with filter_col:
    categories = sorted({str(row.get("category", "Unknown")) for row in metadata})
    category = st.selectbox("Document category", ["All categories"] + categories)
filtered = [r for r in metadata if category == "All categories" or str(r.get("category", "Unknown")) == category]
with doc_col:
    selected_index = st.selectbox(
        "Benchmark document", range(len(filtered)),
        format_func=lambda i: f"{filtered[i].get('doc_id', 'Unknown')} · {filtered[i].get('difficulty', 'Unspecified')}",
    )
selected_record = filtered[selected_index]
selected_id = str(selected_record.get("doc_id"))
loaded_record = st.session_state.get("record")
loaded_id = str(loaded_record.get("doc_id")) if loaded_record else None
document_ready = loaded_record is not None and "document_bytes" in st.session_state
prediction = st.session_state.get("prediction") if document_ready else None
issues = st.session_state.get("issues", []) if prediction is not None else []
reference_ready = (
    prediction is not None and st.session_state.get("reference_id") == loaded_id
    and "reference" in st.session_state
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Benchmark documents", len(metadata))
m2.metric("Selected category", str(selected_record.get("category", "Unknown")).title())
m3.metric("Extraction", "Complete" if prediction is not None else "Pending")
m4.metric("Quality findings", len(issues) if prediction is not None else "—")

st.markdown('<div class="dt-kicker">02 / Document processing</div>', unsafe_allow_html=True)
st.markdown('<div class="dt-section">Inspection & extraction</div>', unsafe_allow_html=True)
st.markdown('<div class="dt-sub">Original invoice on the left. Structured AI extraction on the right.</div>', unsafe_allow_html=True)
left, right = st.columns([1.12, 1], gap="large")

with left:
    with st.container(border=True):
        st.markdown("#### Document inspector")
        st.caption(f"Selected: {selected_id} · Difficulty: {selected_record.get('difficulty', 'Unspecified')}")
        if st.button("Load selected invoice", type="primary", use_container_width=True):
            try:
                with st.spinner("Downloading public invoice..."):
                    content, mime = load_selected_document(selected_record)
                st.session_state["document_bytes"] = content
                st.session_state["mime_type"] = mime
                st.session_state["record"] = selected_record
                for key in ("prediction", "issues", "reference", "reference_id"):
                    st.session_state.pop(key, None)
                st.rerun()
            except Exception as error:
                st.error(f"Invoice loading failed: {error}")
        if document_ready:
            st.success(f"Loaded invoice: {loaded_id}")
            content = st.session_state["document_bytes"]
            mime = st.session_state["mime_type"]
            if mime.startswith("image/"):
                st.image(content, use_container_width=True)
            elif mime == "application/pdf":
                try:
                    with fitz.open(stream=content, filetype="pdf") as pdf:
                        page_count = len(pdf)
                        page_number = st.selectbox(
                            "Preview page",
                            range(1, page_count + 1),
                            key=f"pdf_page_{loaded_id}",
                        ) if page_count > 1 else 1
                        page = pdf.load_page(page_number - 1)
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
                        st.image(pix.tobytes("png"), caption=f"Original invoice · Page {page_number}/{page_count}", use_container_width=True)
                except Exception as error:
                    st.warning(f"Preview unavailable: {error}. You can still download the original PDF.")
                st.download_button("Download original PDF", data=content, file_name=f"{loaded_id}.pdf",
                                   mime="application/pdf", use_container_width=True)
        else:
            st.markdown('<div class="dt-placeholder">Load a benchmark invoice to inspect its original document here.</div>',
                        unsafe_allow_html=True)

with right:
    with st.container(border=True):
        st.markdown("#### AI extraction")
        st.caption("Gemini multimodal extraction · Structured JSON")
        if not document_ready:
            st.info("Load an invoice to enable extraction.")
        else:
            if selected_id != loaded_id:
                st.warning("The selected invoice differs from the loaded one. Load it to switch.")
            if st.button("Extract & validate", type="primary", use_container_width=True):
                try:
                    with st.spinner("Extracting invoice fields and validating..."):
                        result = extract_invoice(st.session_state["document_bytes"], st.session_state["mime_type"])
                        findings = validate_invoice(result)
                    st.session_state["prediction"] = result
                    st.session_state["issues"] = findings
                    st.session_state.pop("reference", None)
                    st.session_state.pop("reference_id", None)
                    st.rerun()
                except Exception as error:
                    st.error(f"AI extraction failed: {error}")
        if prediction is not None:
            labels = {"vendor_name": "Supplier", "invoice_number": "Invoice number",
                      "invoice_date": "Invoice date", "due_date": "Due date", "currency": "Currency",
                      "subtotal": "Subtotal", "tax": "Tax", "total": "Total"}
            rows = [{"Field": labels.get(field, field),
                     "Extracted value": str(prediction.get(field)) if prediction.get(field) is not None else "Not found"}
                    for field in FIELDS]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            items = prediction.get("line_items")
            if isinstance(items, list) and items:
                with st.expander(f"Line items ({len(items)})"):
                    st.dataframe(pd.DataFrame(items), hide_index=True, use_container_width=True)
        else:
            st.markdown('<div class="dt-note">AI output is unverified until independent quality checks and reference comparison.</div>',
                        unsafe_allow_html=True)

st.markdown('<div class="dt-kicker">03 / Quality assurance</div>', unsafe_allow_html=True)
st.markdown('<div class="dt-section">Validation & benchmark evidence</div>', unsafe_allow_html=True)
qa, bench = st.columns(2, gap="large")
with qa:
    with st.container(border=True):
        st.markdown("#### Data quality checks")
        st.caption("Required fields · Totals · Dates · Line-item arithmetic")
        if prediction is None:
            st.info("Extract an invoice to view validation findings.")
        elif issues:
            st.warning(f"{len(issues)} potential issue(s) require review.")
            st.dataframe(pd.DataFrame(issues), hide_index=True, use_container_width=True)
        else:
            st.success("No issues detected by current rules. This is not a guarantee of correctness.")
with bench:
    with st.container(border=True):
        st.markdown("#### Reference benchmark")
        st.caption("Field comparison against public reference annotations")
        if prediction is None:
            st.info("Extract an invoice to enable benchmark comparison.")
        else:
            if st.button("Compare with ground truth", use_container_width=True):
                try:
                    with st.spinner("Loading reference annotation..."):
                        reference = load_reference(loaded_record)
                    st.session_state["reference"] = reference
                    st.session_state["reference_id"] = loaded_id
                    st.rerun()
                except Exception as error:
                    st.error(f"Reference loading failed: {error}")
            if reference_ready:
                reference = st.session_state["reference"]
                results = evaluate_extraction(prediction, reference)
                if results.empty:
                    st.warning("Reference loaded but supported fields could not be mapped safely.")
                else:
                    correct = int(results["Correct"].sum())
                    total = len(results)
                    a, b, c = st.columns(3)
                    a.metric("Field match", f"{correct / total:.1%}")
                    b.metric("Correct", correct)
                    c.metric("Compared", total)
                    st.dataframe(results, hide_index=True, use_container_width=True)
                    st.caption("Currency comparison normalizes unambiguous symbols (e.g., $ → USD). Original predictions and reference values remain unchanged. Per-document score only.")
                    st.download_button("Export evaluation CSV", data=results.to_csv(index=False),
                                       file_name=f"{loaded_id}_evaluation.csv", mime="text/csv",
                                       use_container_width=True)
                with st.expander("Original answer key"):
                    st.json(reference)

with st.expander("Research protocol · Methods, limitations and reproducibility"):
    st.markdown("""
**Objective:** Study the reliability of multimodal invoice extraction using rule-based validation
and public reference annotations.

**Method:** Select a public invoice → extract structured fields → apply independent quality checks
→ compare supported fields with the answer key → inspect discrepancies.

**Research questions:** Which fields are hardest to extract? How do document categories affect
reliability? What inconsistencies can deterministic checks flag?

**Limitations:** This is per-document evaluation, not an official benchmark score. Synthetic invoices
may not represent production documents. Discrepancies can reflect legitimate adjustments.
Batch evaluation and independent baselines are planned work.
""")
    st.link_button("View public benchmark dataset", f"https://huggingface.co/datasets/{REPO_ID}")

st.caption("DataTrust · Research prototype · Public synthetic invoice data · No private invoices required")


# ============================================================
# BATCH BENCHMARK RESEARCH
# ============================================================

st.markdown('<div class="dt-kicker">04 / Research experiments</div>', unsafe_allow_html=True)
st.markdown('<div class="dt-section">Batch benchmark & error analysis</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dt-sub">Run a controlled experiment across several public invoices. '
    'Every document invokes Gemini and may incur API usage.</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown("#### Experiment configuration")
    st.caption("Run a small sample first. Results are saved in this browser session until it is reset.")
    b1, b2, b3 = st.columns([1.2, 1, 1])
    with b1:
        batch_category = st.selectbox(
            "Experiment category", ["All categories"] + categories,
            key="dt_batch_category",
        )
    with b2:
        batch_count = st.number_input(
            "Number of documents", min_value=1, max_value=10, value=3, step=1,
            help="Maximum 10 per run to control API usage.",
            key="dt_batch_count",
        )
    with b3:
        st.text_input("Model", value=get_setting("GEMINI_MODEL", "gemini-3.6-flash"), disabled=True)

    batch_pool = [
        row for row in metadata
        if batch_category == "All categories"
        or str(row.get("category", "Unknown")) == batch_category
    ]
    batch_sample = batch_pool[:int(batch_count)]
    st.caption(
        f"This run will process {len(batch_sample)} document(s) in dataset order. "
        "Each model request may consume API quota."
    )
    run_batch = st.button(
        "Run batch evaluation", type="primary", use_container_width=True,
        key="dt_run_batch",
    )
    if run_batch:
        from datetime import datetime, timezone
        batch_rows = []
        field_rows = []
        progress = st.progress(0, text="Starting experiment...")
        for position, record in enumerate(batch_sample, start=1):
            doc_id = str(record.get("doc_id", "unknown"))
            progress.progress(
                (position - 1) / max(len(batch_sample), 1),
                text=f"Processing {position}/{len(batch_sample)}: {doc_id}",
            )
            result_row = {
                "doc_id": doc_id,
                "category": str(record.get("category", "Unknown")),
                "difficulty": str(record.get("difficulty", "Unknown")),
                "status": "failed", "correct": 0, "compared": 0,
                "match_rate": None, "validation_findings": None,
                "error": "",
            }
            try:
                document_bytes, document_mime = load_selected_document(record)
                predicted = extract_invoice(document_bytes, document_mime)
                validation = validate_invoice(predicted)
                reference = load_reference(record)
                comparisons = evaluate_extraction(predicted, reference)
                if comparisons.empty:
                    result_row["status"] = "no_mapped_fields"
                    result_row["error"] = "No reference fields could be mapped"
                else:
                    n_correct = int(comparisons["Correct"].sum())
                    n_compared = len(comparisons)
                    result_row.update({
                        "status": "evaluated",
                        "correct": n_correct,
                        "compared": n_compared,
                        "match_rate": n_correct / n_compared,
                        "validation_findings": len(validation),
                    })
                    for _, field_row in comparisons.iterrows():
                        field_rows.append({
                            "doc_id": doc_id,
                            "category": result_row["category"],
                            "difficulty": result_row["difficulty"],
                            "field": str(field_row["Field"]),
                            "predicted": str(field_row["Predicted"]),
                            "reference": str(field_row["Reference"]),
                            "correct": bool(field_row["Correct"]),
                        })
            except Exception as error:
                result_row["error"] = str(error)[:400]
            batch_rows.append(result_row)
        progress.progress(1.0, text="Experiment finished")
        st.session_state["dt_batch_results"] = batch_rows
        st.session_state["dt_batch_fields"] = field_rows
        st.session_state["dt_batch_meta"] = {
            "run_utc": datetime.now(timezone.utc).isoformat(),
            "model": get_setting("GEMINI_MODEL", "gemini-3.6-flash"),
            "dataset": REPO_ID,
            "category": batch_category,
            "requested_documents": len(batch_sample),
            "prompt_version": "app.py / EXTRACTION_PROMPT",
            "sampling": "first N in dataset order; not randomized",
        }
        st.rerun()

if "dt_batch_results" in st.session_state:
    batch_df = pd.DataFrame(st.session_state["dt_batch_results"])
    fields_df = pd.DataFrame(st.session_state["dt_batch_fields"])
    meta = st.session_state["dt_batch_meta"]
    valid = batch_df[batch_df["status"] == "evaluated"]
    failed = batch_df[batch_df["status"] != "evaluated"]
    st.markdown("#### Experiment results")
    st.caption(
        f"Run: {meta['run_utc']} · Model: {meta['model']} · "
        f"Sampling: {meta['sampling']}"
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Documents attempted", len(batch_df))
    k2.metric("Documents evaluated", len(valid))
    k3.metric("Failures / unmapped", len(failed))
    if not fields_df.empty:
        micro = float(fields_df["correct"].mean())
        k4.metric("Micro field match", f"{micro:.1%}")
        st.caption(
            "Micro field match = correct mapped fields / all mapped fields in successfully "
            "evaluated documents. Failed documents are excluded from this denominator."
        )
        macro = float(valid["match_rate"].mean()) if not valid.empty else 0
        st.write(f"**Macro document-average field match:** {macro:.1%}")
        by_field = (
            fields_df.groupby("field", as_index=False)
            .agg(correct=("correct", "sum"), compared=("correct", "size"))
        )
        by_field["match_rate"] = by_field["correct"] / by_field["compared"]
        st.markdown("##### Accuracy by extracted field")
        st.dataframe(by_field, hide_index=True, use_container_width=True)
        st.bar_chart(by_field.set_index("field")["match_rate"])
        errors = fields_df[~fields_df["correct"]]
        st.markdown("##### Field-level errors")
        if errors.empty:
            st.success("No mismatches among evaluated fields in this sample.")
        else:
            st.dataframe(errors, hide_index=True, use_container_width=True)
        st.download_button(
            "Download field-level results CSV",
            fields_df.to_csv(index=False).encode("utf-8"),
            file_name="datatrust_batch_fields.csv", mime="text/csv",
            key="dt_download_fields",
        )
        st.download_button(
            "Download per-field summary CSV",
            by_field.to_csv(index=False).encode("utf-8"),
            file_name="datatrust_field_summary.csv", mime="text/csv",
            key="dt_download_summary",
        )
    else:
        k4.metric("Micro field match", "N/A")
        st.warning("No documents produced mapped reference comparisons.")
    st.markdown("##### Document-level results")
    st.dataframe(batch_df, hide_index=True, use_container_width=True)
    st.download_button(
        "Download document-level results CSV",
        batch_df.to_csv(index=False).encode("utf-8"),
        file_name="datatrust_batch_documents.csv", mime="text/csv",
        key="dt_download_documents",
    )
    if not failed.empty:
        st.warning(
            "Some documents failed or had unmapped reference fields. "
            "Review the errors before interpreting these metrics."
        )

st.caption(
    "Batch results are exploratory, sample-dependent, and not official benchmark scores. "
    "No independent baseline is included in this version."
)
