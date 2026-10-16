import json

import duckdb
import plotly.graph_objects as go
import streamlit as st

from data_access import load_event_metadata, load_thread_page
from design import apply_design, hero

PHASES = {
    "skill": "Contexte", "read": "Analyse", "glob": "Analyse", "grep": "Analyse",
    "task": "Delegation", "apply_patch": "Modification", "edit": "Modification",
    "bash": "Execution", "question": "Clarification", "webfetch": "Recherche externe",
    "todowrite": "Suivi",
}
COLORS = {
    "Contexte": "#64748b", "Analyse": "#2563eb", "Delegation": "#7c3aed",
    "Modification": "#d97706", "Execution": "#0f766e", "Clarification": "#db2777",
    "Recherche externe": "#0891b2", "Suivi": "#64748b", "Reponse": "#16a34a",
    "Demande": "#2563eb", "Operation": "#475467",
}


def task_calls(events):
    calls = []
    for event in events.loc[(events["event_type"] == "tool") & (events["tool_name"] == "task")].to_dict("records"):
        try:
            task = json.loads(event["tool_input_json"] or "{}")
        except json.JSONDecodeError:
            task = {}
        calls.append({
            "subagent": task.get("subagent_type", "inconnu"),
            "objectif": task.get("description", "Sans description"),
            "status": event["tool_status"] or "inconnu",
            "resultat": (event["tool_output"] or "")[:180],
        })
    return calls


def phases_for(events):
    phases = []
    for event in events.to_dict("records"):
        if event["event_type"] == "text":
            phase = "Demande" if event["role"] == "user" else "Reponse"
        elif event["event_type"] == "tool":
            phase = PHASES.get(event["tool_name"], "Operation")
        else:
            continue
        if phase not in phases:
            phases.append(phase)
    return phases


def build_flow(events):
    nodes = []
    edges = []
    previous = None
    prompt_index = 0
    step = 0
    for message_id, group in events.groupby("message_id", sort=False):
        first = group.iloc[0]
        calls = task_calls(group)
        phases = phases_for(group)
        if first["role"] == "user":
            prompt_index += 1
            step = 0
            label = f"Prompt {prompt_index}"
            kind = "prompt"
            color = COLORS["Demande"]
            hover = (group["content"].dropna().iloc[0][:220] if group["content"].notna().any() else "Prompt utilisateur")
        else:
            step += 1
            label = f"{phases[0] if phases else 'Etape'}"
            if calls:
                label = f"Sous-agent : {calls[0]['subagent']}"
            kind = "step"
            color = COLORS.get(phases[0], COLORS["Operation"]) if phases else COLORS["Operation"]
            hover = " · ".join(phases) or "Operation"
        node = {"x": prompt_index * 4, "y": step, "label": label, "color": color, "kind": kind, "hover": hover}
        nodes.append(node)
        if previous:
            edges.append((previous, node))
        previous = node
        for index, call in enumerate(calls, 1):
            branch = {
                "x": node["x"] + 1.0, "y": node["y"] + index * .42,
                "label": f"{call['subagent']}", "color": "#16a34a" if call["status"] in {"completed", "success"} else "#dc2626",
                "kind": "branch", "hover": f"{call['objectif']} · {call['status']}\n{call['resultat']}",
            }
            nodes.append(branch)
            edges.append((node, branch))
    return nodes, edges


def flow_chart(nodes, edges):
    edge_x, edge_y = [], []
    for source, target in edges:
        edge_x += [source["x"], target["x"], None]
        edge_y += [source["y"], target["y"], None]
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", line={"color": "#cbd5e1", "width": 1.5},
        hoverinfo="skip", showlegend=False,
    ))
    for kind, symbol, size in [("prompt", "circle", 18), ("step", "square", 15), ("branch", "diamond", 13)]:
        items = [node for node in nodes if node["kind"] == kind]
        if not items:
            continue
        figure.add_trace(go.Scatter(
            x=[node["x"] for node in items], y=[node["y"] for node in items],
            mode="markers+text" if kind != "branch" else "markers+text",
            text=[node["label"] for node in items], textposition="top center",
            textfont={"size": 10, "color": "#344054"},
            customdata=[node["hover"] for node in items],
            hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
            marker={"size": size, "symbol": symbol, "color": [node["color"] for node in items], "line": {"color": "#ffffff", "width": 2}},
            showlegend=False,
        ))
    figure.update_layout(
        height=max(520, min(760, 360 + len(nodes) * 3)),
        margin={"l": 24, "r": 24, "t": 20, "b": 32},
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font={"family": "Inter, sans-serif", "color": "#344054"},
        hoverlabel={"bgcolor": "#172033", "bordercolor": "#172033", "font": {"color": "#ffffff", "size": 12}},
        hovermode="closest", dragmode="pan", showlegend=False,
        xaxis={"title": "Progression de la discussion", "showgrid": False, "zeroline": False, "fixedrange": False, "color": "#667085"},
        yaxis={"title": "Traitement", "showgrid": True, "gridcolor": "#eef1f6", "zeroline": False, "fixedrange": False, "color": "#667085"},
    )
    return figure


st.set_page_config(page_title="Flux de discussion", page_icon="F", layout="wide")
apply_design()
hero("Lecture chronologique", "Flux de discussion", "Une vue légère des prompts, étapes et délégations.", "FLUX INTERACTIF")
if st.button("← Retour au fil de discussion"):
    st.switch_page("streamlit_app.py")

events = load_event_metadata()
if events is None or events.num_rows == 0:
    st.info("Aucune donnée disponible.")
    st.stop()

connection = duckdb.connect()
connection.register("events_raw", events)
connection.execute("""
    CREATE TEMP VIEW events AS
    SELECT * EXCLUDE (event_rank) FROM (
      SELECT *, row_number() OVER (PARTITION BY session_id, event_id ORDER BY exported_at_ms DESC) AS event_rank
      FROM events_raw
    ) WHERE event_rank = 1
""")
try:
    sessions = connection.execute("""
        SELECT session_id, max(session_title) AS title, max(message_created_ms) AS activity
        FROM events GROUP BY session_id ORDER BY activity DESC
    """).fetchdf()
    options = {f"{row.title or 'Sans titre'} · {row.session_id}": row.session_id for row in sessions.itertuples()}
    stored = st.session_state.get("flow_session")
    selected_index = next((i for i, value in enumerate(options.values()) if value == stored), 0)
    selected_label = st.selectbox("Discussion", list(options), index=selected_index)
    selected_session = options[selected_label]
    st.session_state["flow_session"] = selected_session
    message_ids = connection.execute("SELECT DISTINCT message_id FROM events WHERE session_id = ? AND message_id IS NOT NULL", [selected_session]).fetchdf()["message_id"].tolist()
    full_events = load_thread_page(selected_session, tuple(message_ids))
    connection.register("full_events_raw", full_events)
    trace = connection.execute("""
        SELECT * FROM (
          SELECT *, row_number() OVER (PARTITION BY session_id, event_id ORDER BY exported_at_ms DESC) AS event_rank
          FROM full_events_raw
        ) WHERE event_rank = 1 ORDER BY message_created_ms, event_index
    """).fetchdf()
finally:
    connection.close()

nodes, edges = build_flow(trace)
st.caption(f"{len(nodes)} éléments · Survolez un élément pour voir un résumé. Utilisez le zoom et le déplacement si la discussion est longue.")
st.plotly_chart(flow_chart(nodes, edges), use_container_width=True, config={"scrollZoom": True, "displaylogo": False, "responsive": True})
