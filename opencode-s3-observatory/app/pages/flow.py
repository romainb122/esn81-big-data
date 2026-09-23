import json

import duckdb
import plotly.graph_objects as go
import streamlit as st

from data_access import load_event_metadata, load_thread_page
from design import apply_design, hero


PHASES = {
    "skill": "Contexte",
    "read": "Analyse",
    "glob": "Analyse",
    "grep": "Analyse",
    "task": "Delegation",
    "apply_patch": "Modification",
    "edit": "Modification",
    "bash": "Execution",
    "question": "Clarification",
    "webfetch": "Recherche externe",
    "todowrite": "Suivi",
}

PHASE_COLORS = {
    "Contexte": "#6b7280",
    "Analyse": "#2563eb",
    "Delegation": "#7c3aed",
    "Modification": "#d97706",
    "Execution": "#0f766e",
    "Clarification": "#db2777",
    "Recherche externe": "#0891b2",
    "Suivi": "#64748b",
    "Reponse": "#16a34a",
}


def task_calls(events):
    calls = []
    for event in events.loc[(events["event_type"] == "tool") & (events["tool_name"] == "task")].to_dict("records"):
        try:
            task = json.loads(event["tool_input_json"] or "{}")
        except json.JSONDecodeError:
            task = {}
        calls.append(
            {
                "subagent": task.get("subagent_type", "inconnu"),
                "objectif": task.get("description", "Sans description"),
                "status": event["tool_status"] or "inconnu",
                "resultat": event["tool_output"] or "",
            }
        )
    return calls


def phase_for_message(events):
    phases = []
    for event in events.to_dict("records"):
        if event["event_type"] == "text" and event["role"] == "assistant":
            phases.append("Reponse")
        elif event["event_type"] == "patch":
            phases.append("Modification")
        elif event["event_type"] == "tool":
            phases.append(PHASES.get(event["tool_name"], "Operation"))
    return list(dict.fromkeys(phases))


def message_usage(events):
    tokens = 0
    cost = 0.0
    for event in events.to_dict("records"):
        if event["event_type"] != "step-finish":
            continue
        try:
            details = json.loads(event["details_json"] or "{}")
        except json.JSONDecodeError:
            details = {}
        step_tokens = details.get("tokens", {})
        tokens += sum(value for value in step_tokens.values() if isinstance(value, int))
        step_cost = details.get("cost")
        if isinstance(step_cost, (int, float)):
            cost += step_cost
    return tokens, cost


def build_flow(events):
    nodes = []
    edges = []
    prompt_index = 0
    vertical_step = 0
    previous_node = None

    for message_id, message_events in events.groupby("message_id", sort=False):
        first = message_events.iloc[0]
        if first["role"] == "user":
            prompt_index += 1
            vertical_step = 0
            content = next((event["content"] for event in message_events.to_dict("records") if event["event_type"] == "text"), "")
            node = {
                "id": message_id,
                "x": prompt_index * 3,
                "y": 0,
                "label": f"Prompt {prompt_index}",
                "shape": "circle",
                "color": "#2563eb",
                "hover": f"<b>Utilisateur</b><br>{content}<extra></extra>",
            }
        else:
            vertical_step += 1
            phases = phase_for_message(message_events)
            tokens, cost = message_usage(message_events)
            calls = task_calls(message_events)
            label = " + ".join(phases[:2]) or "Etape"
            if calls:
                label = f"Delegation: {calls[0]['subagent']}"
            node = {
                "id": message_id,
                "x": prompt_index * 3,
                "y": vertical_step,
                "label": label,
                "shape": "square",
                "color": PHASE_COLORS.get(phases[0], "#475569") if phases else "#475569",
                "hover": (
                    f"<b>Agent: {first['agent'] or 'OpenCode'}</b><br>"
                    f"Etapes: {', '.join(phases) or 'operation'}<br>"
                    f"Tokens de l'etape: {tokens:,}<br>Cout de l'etape: ${cost:,.4f}<extra></extra>"
                ),
            }
        nodes.append(node)
        if previous_node:
            edges.append((previous_node, node))
        previous_node = node

        if first["role"] != "user":
            for branch_index, call in enumerate(task_calls(message_events), start=1):
                branch = {
                    "id": f"{message_id}-task-{branch_index}",
                    "x": node["x"] + 1.05,
                    "y": node["y"] + branch_index * 0.35,
                    "label": f"Sous-agent: {call['subagent']}",
                    "shape": "diamond",
                    "color": "#16a34a" if call["status"] in {"completed", "success"} else "#dc2626",
                    "hover": (
                        f"<b>Sous-agent: {call['subagent']}</b><br>"
                        f"Objectif: {call['objectif']}<br>"
                        f"Statut: {call['status']}<br>"
                        f"Resultat: {call['resultat'][:600]}<extra></extra>"
                    ),
                }
                nodes.append(branch)
                edges.append((node, branch))
    return nodes, edges


def flow_chart(nodes, edges):
    figure = go.Figure()
    for source, target in edges:
        figure.add_annotation(
            x=target["x"],
            y=target["y"],
            ax=source["x"],
            ay=source["y"],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor="#94a3b8",
        )
    figure.add_trace(
        go.Scatter(
            x=[node["x"] for node in nodes],
            y=[node["y"] for node in nodes],
            mode="markers+text",
            text=[node["label"] for node in nodes],
            textposition="top center",
            hovertemplate=[node["hover"] for node in nodes],
            marker={
                "size": 28,
                "color": [node["color"] for node in nodes],
                "symbol": [node["shape"] for node in nodes],
                "line": {"color": "#0b0d10", "width": 3},
            },
            textfont={"color": "#d7dde6", "size": 11},
        )
    )
    figure.update_layout(
        height=760,
        margin={"l": 32, "r": 32, "t": 24, "b": 28},
        paper_bgcolor="#13171c",
        plot_bgcolor="#13171c",
        font={"family": "Inter, ui-sans-serif, system-ui, sans-serif", "color": "#d7dde6"},
        hoverlabel={"bgcolor": "#20262e", "bordercolor": "#3b4653", "font": {"color": "#f8fafc"}},
        dragmode="pan",
        showlegend=False,
        xaxis={"title": "Progression de la discussion", "showgrid": False, "zeroline": False, "fixedrange": False, "color": "#8f9aaa"},
        yaxis={"title": "Traitement declenche", "showgrid": True, "gridcolor": "#222831", "zeroline": False, "fixedrange": False, "color": "#8f9aaa"},
    )
    return figure


st.set_page_config(page_title="Flux de discussion", page_icon="F", layout="wide")
apply_design()
hero("Lecture chronologique", "Flux de discussion", "Les prompts progressent vers la droite. Les traitements et delegations se developpent verticalement au-dessus de leur origine.", "CANVAS INTERACTIF")
if st.button("Retour au fil de discussion"):
    st.switch_page("streamlit_app.py")

events = load_event_metadata()
if events is None or events.num_rows == 0:
    st.info("Aucune donnee Iceberg disponible.")
    st.stop()

connection = duckdb.connect()
connection.register("events_raw", events)
connection.execute(
    """
    CREATE TEMP VIEW events AS
    SELECT * EXCLUDE (event_rank)
    FROM (
      SELECT *, row_number() OVER (
        PARTITION BY session_id, event_id ORDER BY exported_at_ms DESC
      ) AS event_rank
      FROM events_raw
    )
    WHERE event_rank = 1
    """
)
try:
    sessions = connection.execute(
        """
        SELECT session_id, max(session_title) AS title, max(to_timestamp(message_created_ms / 1000.0)) AS activity
        FROM events GROUP BY session_id ORDER BY activity DESC
        """
    ).fetchdf()
    options = {f"{row.title or 'Sans titre'} - {row.session_id}": row.session_id for row in sessions.itertuples()}
    stored_session = st.session_state.get("flow_session")
    selected_index = next((index for index, session_id in enumerate(options.values()) if session_id == stored_session), 0)
    selected_label = st.selectbox("Discussion", list(options), index=selected_index)
    selected_session = options[selected_label]
    st.session_state["flow_session"] = selected_session
    message_ids = connection.execute(
        """
        SELECT DISTINCT message_id
        FROM events
        WHERE session_id = ? AND message_id IS NOT NULL
        """,
        [selected_session],
    ).fetchdf()["message_id"].tolist()
    full_trace_events = load_thread_page(selected_session, tuple(message_ids))
    connection.register("full_trace_events_raw", full_trace_events)
    trace = connection.execute(
        """
        SELECT *, to_timestamp(message_created_ms / 1000.0) AS created_at
        FROM (
          SELECT *, row_number() OVER (
            PARTITION BY session_id, event_id ORDER BY exported_at_ms DESC
          ) AS event_rank
          FROM full_trace_events_raw
        )
        WHERE event_rank = 1
        ORDER BY message_created_ms, event_index
        """,
    ).fetchdf()
    connection.unregister("full_trace_events_raw")
finally:
    connection.close()

nodes, edges = build_flow(trace)
st.caption("Legende : cercle bleu = prompt utilisateur, carre colore = etape de l'agent, losange vert/rouge = sous-agent termine/en erreur. Utiliser la molette pour zoomer et glisser pour se deplacer.")
st.plotly_chart(flow_chart(nodes, edges), use_container_width=True, config={"scrollZoom": True, "displaylogo": False})
