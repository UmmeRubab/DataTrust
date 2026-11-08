
import io
import json
import mimetypes
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
    page_title="DataTrust | Intelligent Document Processing",
    page_icon="🛡️",
    layout="wide",
)

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


def match_field(field, predicted, expected):
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
            "Correct": match_field(field, predicted, expected),
        })

    return pd.DataFrame(records)


# ============================================================
# APPLICATION INTERFACE
# ============================================================

st.title("🛡️ DataTrust")
st.caption(
    "AI-Powered Invoice Extraction, Data Quality Validation "
    "& Benchmark Evaluation"
)

with st.sidebar:
    st.header("Research Configuration")
    st.write("**Dataset:** Invoice Extraction Benchmark v1")
    st.write("**Extraction:** Gemini multimodal AI")
    st.write("**Validation:** Rule-based quality checks")
    st.write("**Evaluation:** Public reference annotations")

    st.divider()

    st.caption(
        "Public synthetic invoices are used for research and "
        "development. No private company invoices are required."
    )

tab1, tab2, tab3, tab4 = st.tabs([
    "Invoice Laboratory",
    "Quality Validation",
    "Benchmark Evaluation",
    "Research Design",
])

try:
    metadata = load_metadata()
except Exception as error:
    metadata = []
    st.error(
        "Unable to load the public benchmark metadata. "
        f"Details: {error}"
    )

if metadata:

    with tab1:
        st.subheader("Invoice Laboratory")

        st.write(
            "Select a public invoice, inspect its contents, "
            "and extract structured data using Gemini."
        )

        categories = sorted({
            str(row.get("category", "Unknown"))
            for row in metadata
        })

        selected_category = st.selectbox(
            "Invoice category",
            ["All"] + categories,
        )

        filtered = [
            row for row in metadata
            if selected_category == "All"
            or str(row.get("category", "Unknown")) == selected_category
        ]

        selected_index = st.selectbox(
            "Choose an invoice",
            range(len(filtered)),
            format_func=lambda index: (
                f"{filtered[index].get('doc_id', 'Unknown')} "
                f"— {filtered[index].get('difficulty', 'Unspecified')}"
            ),
        )

        selected_record = filtered[selected_index]
        selected_id = str(selected_record.get("doc_id"))

        st.write(
            "**Category:**",
            selected_record.get("category", "Unknown"),
        )

        st.write(
            "**Difficulty:**",
            selected_record.get("difficulty", "Unspecified"),
        )

        if st.button("Load Public Invoice", type="primary"):
            try:
                with st.spinner("Downloading public invoice..."):
                    document_bytes, mime_type = load_selected_document(
                        selected_record
                    )

                st.session_state["document_bytes"] = document_bytes
                st.session_state["mime_type"] = mime_type
                st.session_state["record"] = selected_record
                st.session_state.pop("prediction", None)
                st.session_state.pop("issues", None)

                st.success("Invoice loaded successfully.")

            except Exception as error:
                st.error(f"Invoice loading failed: {error}")

        loaded_record = st.session_state.get("record")

        if loaded_record is not None:
            loaded_id = loaded_record.get("doc_id")

            st.info(f"Loaded invoice: {loaded_id}")

            document_bytes = st.session_state["document_bytes"]
            mime_type = st.session_state["mime_type"]

            if mime_type.startswith("image/"):
                st.image(
                    document_bytes,
                    caption="Public benchmark invoice",
                    use_container_width=True,
                )

            else:
                st.download_button(
                    "View / Download Invoice PDF",
                    data=document_bytes,
                    file_name=f"{loaded_id}.pdf",
                    mime="application/pdf",
                )

            if st.button("Run AI Extraction & Validation"):
                try:
                    with st.spinner("Analyzing invoice with Gemini..."):
                        prediction = extract_invoice(
                            document_bytes,
                            mime_type,
                        )

                    issues = validate_invoice(prediction)

                    st.session_state["prediction"] = prediction
                    st.session_state["issues"] = issues

                    st.success("Invoice analysis completed.")

                except Exception as error:
                    st.error(f"AI extraction failed: {error}")

            prediction = st.session_state.get("prediction")

            if prediction is not None:
                st.subheader("Extracted Information")
                st.json(prediction)

                st.download_button(
                    "Download Extracted JSON",
                    data=json.dumps(prediction, indent=2),
                    file_name=f"{loaded_id}_extraction.json",
                    mime="application/json",
                )

    with tab2:
        st.subheader("Data Quality Validation")

        prediction = st.session_state.get("prediction")
        issues = st.session_state.get("issues")

        if prediction is None:
            st.info(
                "Load and extract an invoice in the "
                "Invoice Laboratory first."
            )

        elif issues:
            st.warning(
                f"{len(issues)} potential data-quality issue(s) found."
            )

            st.dataframe(
                pd.DataFrame(issues),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.success(
                "No problems were detected by the current validation "
                "rules. This is not a guarantee that the document "
                "is error-free."
            )

    with tab3:
        st.subheader("Benchmark Evaluation")

        prediction = st.session_state.get("prediction")
        loaded_record = st.session_state.get("record")

        if prediction is None or loaded_record is None:
            st.info(
                "Extract an invoice before running the benchmark."
            )

        else:
            if st.button("Compare With Ground Truth"):
                try:
                    reference = load_reference(loaded_record)

                    st.session_state["reference"] = reference
                    st.session_state["reference_id"] = (
                        loaded_record.get("doc_id")
                    )

                except Exception as error:
                    st.error(f"Unable to load answer key: {error}")

            if (
                "reference" in st.session_state
                and st.session_state.get("reference_id")
                == loaded_record.get("doc_id")
            ):
                reference = st.session_state["reference"]

                results = evaluate_extraction(
                    prediction,
                    reference,
                )

                if results.empty:
                    st.warning(
                        "The reference file was downloaded, but its "
                        "field schema could not be mapped safely. "
                        "Inspect the raw answer key below."
                    )

                else:
                    correct = int(results["Correct"].sum())
                    total_fields = len(results)
                    score = correct / total_fields

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Field Match Rate",
                        f"{score:.1%}",
                    )

                    col2.metric(
                        "Correct Fields",
                        correct,
                    )

                    col3.metric(
                        "Compared Fields",
                        total_fields,
                    )

                    st.dataframe(
                        results,
                        use_container_width=True,
                        hide_index=True,
                    )

                    chart_data = pd.DataFrame({
                        "Result": ["Correct", "Incorrect"],
                        "Count": [
                            correct,
                            total_fields - correct,
                        ],
                    })

                    fig = px.bar(
                        chart_data,
                        x="Result",
                        y="Count",
                        title="Invoice Field Extraction Results",
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

                    st.download_button(
                        "Download Evaluation CSV",
                        data=results.to_csv(index=False),
                        file_name="datatrust_evaluation.csv",
                        mime="text/csv",
                    )

                with st.expander("View Original Answer Key"):
                    st.json(reference)

    with tab4:
        st.subheader("Research Methodology")

        st.markdown("""
### Research Objective

Investigate the reliability of multimodal AI systems
for extracting structured information from invoices.

### Research Questions

**RQ1:** How accurately can a multimodal language model
extract invoice header fields?

**RQ2:** Which document categories cause the greatest
extraction difficulties?

**RQ3:** Can deterministic data-quality rules identify
potential inconsistencies in extracted information?

### Experimental Pipeline

1. Select a public benchmark document.
2. Extract invoice information with a multimodal model.
3. Apply deterministic validation rules.
4. Compare predictions with the reference answer key.
5. Inspect incorrect fields and document failure cases.

### Evaluation

The first version supports per-document field matching.

A full research evaluation will require:
- Batch testing across the benchmark.
- Official scorer integration.
- Category-wise accuracy analysis.
- Line-item matching.
- An independent extraction baseline.
- Evaluation of inconsistency-detection precision and recall.

### Limitations

This benchmark contains synthetic invoices. Its results
do not establish performance on real business records.

The current field matching is a simplified evaluation,
not the benchmark's official scoring methodology.

Financial discrepancies are flagged for review rather
than automatically treated as proven accounting errors.

### Dataset

Invoice Extraction Benchmark v1

Source: drew-ipp / InvoiceParser Pro

License: CC BY 4.0
        """)

        st.link_button(
            "View Dataset on Hugging Face",
            f"https://huggingface.co/datasets/{REPO_ID}",
        )

else:
    st.info(
        "The application is waiting for public dataset metadata."
    )
