import streamlit as st


def apply_design():
    st.markdown(
        """
        <style>
          :root { color-scheme: dark; }
          .stApp { background: #0b0d10; color: #f5f7fa; }
          [data-testid="stHeader"] { background: rgba(11, 13, 16, 0.82); backdrop-filter: blur(16px); }
          .block-container { max-width: 1500px; padding-top: 2.25rem; padding-bottom: 3.5rem; }
          [data-testid="stSidebar"] { background: #101318; border-right: 1px solid #252a32; }
          [data-testid="stSidebar"] * { color: #e7ebf0; }
          h1, h2, h3 { color: #f8fafc !important; letter-spacing: -0.035em; }
          h1 { font-size: 2.6rem !important; font-weight: 700 !important; }
          p, [data-testid="stCaptionContainer"] { color: #9ba5b2 !important; }
          [data-testid="stMetric"] { background: linear-gradient(145deg, #15191f 0%, #111419 100%); border: 1px solid #2a3039; border-radius: 16px; padding: 18px 20px; box-shadow: inset 0 1px rgba(255,255,255,0.025); }
          [data-testid="stMetricLabel"] { color: #9ba5b2 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
          [data-testid="stMetricValue"] { color: #f8fafc !important; font-size: 1.65rem; }
          [data-testid="stRadio"] { background: #15191f; border: 1px solid #2a3039; border-radius: 14px; padding: 5px 10px; width: fit-content; }
          [data-testid="stRadio"] label { font-weight: 650; color: #c7ced8 !important; padding: 3px 8px; }
          [data-testid="stExpander"] { background: #13171c; border: 1px solid #2a3039; border-radius: 12px; }
          [data-testid="stDataFrame"] { border: 1px solid #2a3039; border-radius: 14px; overflow: hidden; }
          [data-testid="stChatMessage"] { background: #13171c; border: 1px solid #2a3039; border-radius: 14px; padding: 8px 14px; }
          [data-testid="stVerticalBlockBorderWrapper"] { background: #13171c; border-color: #2a3039 !important; border-radius: 14px; }
          .stButton > button { border-radius: 10px; border: 1px solid #38414d; background: #1b222a; color: #f8fafc; font-weight: 650; }
          .stButton > button:hover { border-color: #6ee7b7; color: #a7f3d0; }
          .stButton > button[kind="primary"] { background: #6ee7b7; border-color: #6ee7b7; color: #092016; }
          .stSelectbox [data-baseweb="select"] > div { background: #15191f; border-color: #2f3742; border-radius: 10px; }
          .hero-kicker { color: #72e6b4; font-size: 0.72rem; font-weight: 750; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.35rem; }
          .hero-row { display: flex; align-items: start; justify-content: space-between; gap: 1rem; margin-bottom: 1.75rem; }
          .hero-title { margin: 0; color: #f8fafc; font-size: 2.7rem; font-weight: 720; letter-spacing: -0.055em; line-height: 1.03; }
          .hero-copy { color: #9ba5b2; font-size: 1rem; max-width: 680px; margin: 0.8rem 0 0; }
          .hero-badge { color: #9ff2ca; background: #123327; border: 1px solid #245b43; border-radius: 999px; padding: 0.45rem 0.7rem; font-size: 0.76rem; font-weight: 700; white-space: nowrap; }
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
