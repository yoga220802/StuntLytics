import streamlit as st

def load_css():
    """Inject custom CSS to style the app."""
    st.markdown(
        """
        <style>
        .app-header {font-size: 28px; font-weight: 700; margin-bottom: 0.2rem;}
        .app-subtitle {color: #4b5563; margin-bottom: 1rem;}
        .metric-card {border-radius: 1rem; padding: 1rem; background: #f8fafc; border: 1px solid #e5e7eb}
        .pill {display:inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; background:#eef2ff; color:#3730a3; font-weight:600}
        .small-muted {color:#6b7280; font-size: 0.85rem}
        .section {margin-top: 0.25rem;}
        .footer {color:#6b7280; font-size: 0.85rem; margin-top: 2rem;}
        .stTabs [data-baseweb="tab"] {font-size: 0.95rem; font-weight: 600}
        .stDataFrame {border-radius: 0.75rem; overflow: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )
