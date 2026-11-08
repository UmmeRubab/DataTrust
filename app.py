
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, .stApp {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #F5F7FA;
    color: #15243A;
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.035em;
}

h1 {
    color: #10273D !important;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E0E7EF;
    border-radius: 14px;
    padding: 18px;
}

.stButton > button[kind="primary"] {
    background: #087F7A;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}

.stButton > button[kind="primary"]:hover {
    background: #06645F;
}

[data-testid="stSidebar"] {
    background: #10273D;
}

[data-testid="stSidebar"] * {
    color: #E4EFF5;
}

div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)
