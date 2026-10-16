from datetime import datetime
import hashlib

import pandas as pd
import streamlit as st

from data_access import load_event_metadata
from design import apply_design, hero


def normalize_prompt(value):
    return " ".join(str(value or "").split()).strip().casefold()


def first_value(frame, column):
    if column not in frame:
        return None
    values = frame[column].dropna().tolist()
    return values[0] if values else None


def harness_name(frame):
    markers = " ".join(
        str(value or "").lower()
        for column in ("session_agent", "agent")
        for value in frame[column].dropna().unique().tolist()
        if column in frame
    )
    return "Pi" if "pi" in markers else "OpenCode"


@st.cache_data(ttl=20, show_spinner="Recherche automatique des conversations comparables...")
def load_automatic_comparisons():
    arrow = load_event_metadata()
    if arrow is None or arrow.num_rows == 0:
        return []
    events = arrow.to_pandas()
    exchanges = []

    for session_id, session in events.groupby("session_id", sort=False):
        session = session.sort_values(["event_index", "message_created_ms"], na_position="last")
        # Un message peut contenir plusieurs événements/parties : on les réunit une seule fois.
        messages = []
        for message_id, parts in session.groupby("message_id", sort=False, dropna=False):
            parts = parts.drop_duplicates(subset=["event_id"], keep="last")
            role = first_value(parts, "role")
            contents = [str(value) for value in parts["content"].dropna().tolist() if str(value).strip()]
            if role not in {"user", "assistant"} or not contents:
                continue
            messages.append({
                "message_id": message_id,
                "role": role,
                "content": "\n".join(dict.fromkeys(contents)).strip(),
                "index": first_value(parts, "event_index"),
                "created": first_value(parts, "message_created_ms"),
                "completed": first_value(parts, "message_completed_ms"),
                "input_tokens": first_value(parts, "session_tokens_input"),
                "output_tokens": first_value(parts, "session_tokens_output"),
                "cost": first_value(parts, "session_cost"),
            })
        messages.sort(key=lambda row: (row["index"] if row["index"] is not None else 10**18, row["created"] or 0))

        pending_user = None
        for message in messages:
            if message["role"] == "user":
                pending_user = message
            elif pending_user is not None:
                model = first_value(session, "session_model_id") or first_value(session, "model_id")
                provider = first_value(session, "session_provider_id") or first_value(session, "provider_id")
                input_tokens = message["input_tokens"]
                output_tokens = message["output_tokens"]
                exchanges.append({
                    "harness": harness_name(session),
                    "session_id": session_id,
                    "prompt": pending_user["content"],
                    "prompt_key": normalize_prompt(pending_user["content"]),
                    "response": message["content"],
                    "model": model,
                    "provider": provider,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens if pd.notna(input_tokens) and pd.notna(output_tokens) else None,
                    "cost": message["cost"],
                    "duration_ms": (message["completed"] or message["created"] or 0) - (pending_user["created"] or 0),
                    "created_at_ms": pending_user["created"] or 0,
                })
                pending_user = None

    # Même question normalisée + même modèle. Les répétitions sont appariées par proximité temporelle.
    pi_rows = [row for row in exchanges if row["harness"] == "Pi" and row["model"]]
    oc_rows = [row for row in exchanges if row["harness"] == "OpenCode" and row["model"]]
    comparisons = []
    used_opencode = set()
    for pi in sorted(pi_rows, key=lambda row: row["created_at_ms"], reverse=True):
        candidates = [
            (index, row) for index, row in enumerate(oc_rows)
            if index not in used_opencode
            and row["model"] == pi["model"]
            and row["prompt_key"] == pi["prompt_key"]
        ]
        if not candidates:
            continue
        index, opencode = min(candidates, key=lambda item: abs(item[1]["created_at_ms"] - pi["created_at_ms"]))
        used_opencode.add(index)
        identity = f"{pi['session_id']}:{pi['message_id'] if 'message_id' in pi else pi['created_at_ms']}:{opencode['session_id']}:{opencode['created_at_ms']}"
        comparisons.append({
            "id": hashlib.sha256(identity.encode()).hexdigest()[:12],
            "prompt": pi["prompt"],
            "model": pi["model"],
            "created_at_ms": max(pi["created_at_ms"], opencode["created_at_ms"]),
            "Pi": pi,
            "OpenCode": opencode,
        })
    return sorted(comparisons, key=lambda row: row["created_at_ms"], reverse=True)


def format_time(milliseconds):
    if not milliseconds:
        return "date inconnue"
    return datetime.fromtimestamp(milliseconds / 1000).strftime("%d/%m/%Y %H:%M:%S")


def number(value):
    return "—" if value is None or pd.isna(value) else f"{int(value):,}".replace(",", " ")


st.set_page_config(page_title="Comparateur technique", page_icon="C", layout="wide")
apply_design()
hero(
    "Comparateur technique",
    "Comparaisons détectées automatiquement",
    "Le dashboard rapproche les prompts envoyés manuellement dans tes CLI Pi et OpenCode lorsqu’ils ont la même question et le même modèle.",
    "AUCUN LANCEMENT · AUCUNE SÉLECTION MANUELLE",
)

left, right = st.columns([1, 5])
with left:
    if st.button("← Retour"):
        st.switch_page("streamlit_app.py")
with right:
    if st.button("Actualiser après mes prompts CLI", type="primary"):
        load_automatic_comparisons.clear()
        st.rerun()

comparisons = load_automatic_comparisons()
if not comparisons:
    st.info("Aucune paire détectée. Envoie la même question avec le même modèle dans Pi et OpenCode, attends l’export Bronze, puis actualise.")
    st.stop()

st.subheader(f"Comparaisons disponibles · {len(comparisons)}")
selected_index = st.radio(
    "Sélectionner une comparaison",
    range(len(comparisons)),
    format_func=lambda index: (
        f"{comparisons[index]['prompt'][:85]}  ·  {comparisons[index]['model']}  ·  "
        f"{format_time(comparisons[index]['created_at_ms'])}"
    ),
    label_visibility="collapsed",
)
comparison = comparisons[selected_index]

st.divider()
st.caption(f"COMPARAISON {comparison['id']} · {format_time(comparison['created_at_ms'])}")
st.header(comparison["prompt"])
st.markdown(f"**Modèle commun :** `{comparison['model']}`")

pi = comparison["Pi"]
opencode = comparison["OpenCode"]
st.subheader("Résultats côte à côte")
pi_column, opencode_column = st.columns(2, gap="large")


def render_result(title, row):
    st.markdown(f"## {title}")
    st.caption(f"{row['provider']} · `{row['model']}` · session `{row['session_id']}`")
    token_columns = st.columns(3)
    token_columns[0].metric("Tokens entrée", number(row["input_tokens"]))
    token_columns[1].metric("Tokens sortie", number(row["output_tokens"]))
    token_columns[2].metric("Tokens total", number(row["total_tokens"]))
    execution_columns = st.columns(2)
    execution_columns[0].metric(
        "Temps de réponse",
        "—" if not row["duration_ms"] else f"{row['duration_ms'] / 1000:.2f} s",
    )
    execution_columns[1].metric(
        "Coût",
        "—" if row["cost"] is None or pd.isna(row["cost"]) else f"${row['cost']:.6f}",
    )
    st.markdown("#### Réponse")
    st.markdown(row["response"])


with pi_column:
    render_result("Pi", pi)
with opencode_column:
    render_result("OpenCode", opencode)

st.divider()
st.caption("Évaluation qualitative/JEV : volontairement reportée à une version ultérieure.")
