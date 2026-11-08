from pathlib import Path
import ast

app = Path('app.py')
if not app.exists():
    raise SystemExit('Run this script from your DataTrust project folder (where app.py exists).')
source = app.read_text(encoding='utf-8-sig')
if 'def extract_invoice(' not in source or 'def evaluate_extraction(' not in source:
    raise SystemExit('Existing extraction/evaluation functions not found. No changes made.')
start = source.find('st.markdown("""\n<style>')
end = source.find('REPO_ID =', start)
marker = '# ============================================================\n# APPLICATION INTERFACE\n# ============================================================'
ui_start = source.find(marker)
if start < 0 or end < 0 or ui_start < 0:
    raise SystemExit('Expected original app structure not found. No changes made.')
css = '''st.markdown("""
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
</style>
""", unsafe_allow_html=True)

'''
ui = '''# ============================================================
# DOCUMENT INTELLIGENCE WORKSPACE
# ============================================================

st.markdown("""
<div class="dt-hero">
  <div class="dt-eyebrow">DOCUMENT INTELLIGENCE / RESEARCH WORKSPACE</div>
  <h1>DataTrust <span style="color:#77E4D4">/</span> Quality Studio</h1>
  <p>Extract invoice data. Investigate inconsistencies. Evaluate reliability against public annotations.</p>
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
                import base64
                encoded = base64.b64encode(content).decode("ascii")
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{encoded}" width="100%" height="530" '
                    'style="border:1px solid #DCE5ED;border-radius:10px;background:white"></iframe>',
                    unsafe_allow_html=True,
                )
                st.caption("If PDF preview is blocked by your browser, download it below.")
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
            with st.expander("Full extraction JSON"):
                st.json(prediction)
            st.download_button("Download extracted JSON", data=json.dumps(prediction, indent=2),
                               file_name=f"{loaded_id}_extraction.json", mime="application/json",
                               use_container_width=True)
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
'''
new_source = source[:start] + css + source[end:ui_start] + ui
ast.parse(new_source)
backup = Path('app.before_ui_redesign.py.bak')
if not backup.exists():
    backup.write_text(source, encoding='utf-8')
app.write_text(new_source, encoding='utf-8')
readme = Path('README.md')
if readme.exists():
    txt = readme.read_text(encoding='utf-8-sig')
    txt = txt.replace('Add your deployed Streamlit URL here', 'https://datatrustt.streamlit.app/')
    readme.write_text(txt, encoding='utf-8')
changelog = Path('CHANGELOG.md')
if changelog.exists():
    txt = changelog.read_text(encoding='utf-8-sig')
    changelog.write_text('## Version 0.2.0 — Quality Studio UI redesign\n\n- Replaced sidebar and four-tab navigation with a document processing workspace.\n- Added side-by-side invoice preview and structured extraction.\n- Integrated validation and reference evaluation into the main page.\n- Improved accessibility, color contrast and responsive layout.\n- Preserved existing extraction, validation and benchmark functions.\n- Updated the live Streamlit link in README.\n\n' + txt, encoding='utf-8')
print('Redesign applied. Python syntax verified. Original backed up locally.')
