import streamlit as st


def apply_design():
    st.markdown(
        """
        <style>
          :root { color-scheme: light; }
          .stApp { background: #f5f7fb; color: #172033; }
          [data-testid="stHeader"] { background: rgba(245,247,251,.9); border-bottom: 1px solid #e5e9f2; }
          .block-container { max-width: 1360px; padding: 2rem 3rem 4rem; }
          [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e9f2; }
          [data-testid="stSidebar"] * { color: #334155; }
          h1, h2, h3 { color: #172033 !important; letter-spacing: -.035em; }
          h1 { font-size: 2.35rem !important; font-weight: 760 !important; }
          p, [data-testid="stCaptionContainer"] { color: #667085 !important; }
          [data-testid="stMetric"] { background: #ffffff; border: 1px solid #e3e8f1; border-radius: 14px; padding: 16px 18px; box-shadow: 0 5px 18px rgba(28,42,67,.05); }
          [data-testid="stMetricLabel"] { color: #667085 !important; font-size: .74rem; text-transform: uppercase; letter-spacing: .08em; }
          [data-testid="stMetricValue"] { color: #172033 !important; font-size: 1.55rem; }
          [data-testid="stSegmentedControl"] { background: #e9edf5; border: 1px solid #dbe2ed; border-radius: 12px; padding: 4px; width: fit-content; box-shadow: 0 3px 12px rgba(28,42,67,.04); }
          [data-testid="stSegmentedControl"] button { color: #667085 !important; border-radius: 9px; font-weight: 700; }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"] { background: #5264d8 !important; color: #ffffff !important; box-shadow: 0 2px 5px rgba(82,100,216,.25); }
          [data-testid="stExpander"] { background: #ffffff; border: 1px solid #e3e8f1; border-radius: 11px; }
          [data-testid="stDataFrame"] { border: 1px solid #e3e8f1; border-radius: 12px; overflow: hidden; }
          [data-testid="stChatMessage"] { background: #ffffff; border: 1px solid #e3e8f1; border-radius: 13px; padding: 9px 15px; box-shadow: 0 3px 12px rgba(28,42,67,.04); }
          [data-testid="stVerticalBlockBorderWrapper"] { background: #ffffff; border-color: #e3e8f1 !important; border-radius: 13px; }
          .stButton > button, .stLinkButton > a { border-radius: 9px; border: 1px solid #d5dce8; background: #ffffff; color: #344054; font-weight: 650; }
          .stButton > button:hover, .stLinkButton > a:hover { border-color: #5b6ee1; color: #4655ba; }
          .stButton > button[kind="primary"] { background: #5264d8; border-color: #5264d8; color: #ffffff; }
          .stSelectbox [data-baseweb="select"] > div { background: #ffffff; border-color: #d5dce8; border-radius: 9px; }
          .stTextArea textarea { background: #ffffff; color: #172033; border-color: #d5dce8; border-radius: 9px; }
          .hero-kicker { color: #5264d8; font-size: .7rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .35rem; }
          .hero-row { display: flex; align-items: start; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; }
          .hero-title { margin: 0; color: #172033; font-size: 2.55rem; font-weight: 780; letter-spacing: -.055em; line-height: 1.05; }
          .hero-copy { color: #667085; font-size: 1rem; max-width: 720px; margin: .7rem 0 0; }
          .hero-badge { color: #3f4ca8; background: #eef0ff; border: 1px solid #cfd5ff; border-radius: 999px; padding: .42rem .7rem; font-size: .72rem; font-weight: 750; white-space: nowrap; }
          .live-note { display: inline-block; color: #176b48; background: #e8f8f0; border: 1px solid #b7e6ce; border-radius: 999px; padding: .28rem .6rem; font-size: .75rem; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(kicker, title, description, badge="ICEBERG · LIVE"):
    st.markdown(
        f"""
        <div class="hero-row">
          <div>
            <div class="hero-kicker">{kicker}</div>
            <div class="hero-title">{title}</div>
            <p class="hero-copy">{description}</p>
          </div>
          <div class="hero-badge">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
