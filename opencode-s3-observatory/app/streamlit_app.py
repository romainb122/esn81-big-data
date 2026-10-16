import json
import urllib.error
import urllib.request

import altair as alt
import duckdb
import pyarrow as pa
import streamlit as st
import streamlit.components.v1 as components
from data_access import load_event_metadata, load_event_metadata_since, load_thread_page
from design import apply_design, hero


def spark_query(statement):
    request = urllib.request.Request(
        f"{__import__('os').environ.get('SPARK_QUERY_URL', 'http://spark-query:4041')}/query",
        data=json.dumps({"sql": statement}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        return json.loads(error.read()).copy()
    except urllib.error.URLError as error:
        return {"error": f"Service Spark indisponible : {error.reason}"}


def event_label(event):
    if event["event_type"] == "tool":
        return event["tool_title"] or event["tool_name"] or "Outil"
    return {"text": "Message", "step-start": "Debut d'etape", "step-finish": "Fin d'etape"}.get(
        event["event_type"], event["event_type"]
    )


def show_event(event):
    label = event_label(event)
    timestamp = event["created_at"].strftime("%H:%M:%S") if event["created_at"] else "-"
    if event["event_type"] == "tool":
        with st.expander(f"{timestamp}  {label}  [{event['tool_status'] or 'inconnu'}]", expanded=False):
            if event["tool_input_json"]:
                st.caption("Commande ou entree")
                st.code(event["tool_input_json"], language="json")
            if event["tool_output"]:
                st.caption("Resultat")
                st.code(event["tool_output"], language="text")
        return

    if event["event_type"] == "text" and event["content"]:
        author = "Vous" if event["role"] == "user" else "Pi"
        with st.chat_message("user" if event["role"] == "user" else "assistant"):
            st.caption(f"{author} - {timestamp}")
            st.markdown(event["content"])
        return

    st.caption(f"{timestamp} - {label}")


def task_calls(trace):
    """Extract pi task delegations recorded in tool events."""
    calls = []
    for event in trace.loc[(trace["event_type"] == "tool") & (trace["tool_name"] == "task")].to_dict("records"):
        try:
            task = json.loads(event["tool_input_json"] or "{}")
        except json.JSONDecodeError:
            task = {}
        calls.append(
            {
                "parent_message_id": event["message_id"],
                "parent_agent": event["agent"] or "Pi",
                "subagent": task.get("subagent_type", "inconnu"),
                "objectif": task.get("description", "Sans description"),
                "prompt": task.get("prompt"),
                "status": event["tool_status"] or "inconnu",
                "resultat": event["tool_output"],
                "heure": event["created_at"],
            }
        )
    branch_counts = {}
    for call in calls:
        branch_counts[call["parent_message_id"]] = branch_counts.get(call["parent_message_id"], 0) + 1
    for call in calls:
        call["branche"] = "Branche issue de la meme etape" if branch_counts[call["parent_message_id"]] > 1 else "Sous-tache unique"
    return calls


PHASES = {
    "skill": ("Contexte", "Instructions ou capacites chargees"),
    "read": ("Analyse", "Lecture des fichiers concernes"),
    "glob": ("Analyse", "Recherche de fichiers"),
    "grep": ("Analyse", "Recherche dans le code"),
    "task": ("Delegation", "Sous-agent lance"),
    "apply_patch": ("Modification", "Code ou documentation modifies"),
    "edit": ("Modification", "Code ou documentation modifies"),
    "bash": ("Execution", "Commande executee ou verification lancee"),
    "question": ("Clarification", "Question posee avant de poursuivre"),
    "webfetch": ("Recherche externe", "Documentation ou source consulte"),
    "todowrite": ("Suivi", "Etapes de travail mises a jour"),
}


def phase_for(event):
    if event["event_type"] == "text":
        return ("Demande", "Instruction utilisateur") if event["role"] == "user" else ("Reponse", "Reponse visible")
    if event["event_type"] == "patch":
        return PHASES["apply_patch"]
    return PHASES.get(event["tool_name"])


def render_processing_trace(trace):
    """Render a chronological, observable execution journal per agent message."""
    for message_id, message_events in trace.groupby("message_id", sort=False):
        events = message_events.to_dict("records")
        role = events[0]["role"]
        timestamp = events[0]["created_at"].strftime("%H:%M:%S") if events[0]["created_at"] else "-"

        if role == "user":
            for event in events:
                if event["event_type"] == "text" and event["content"]:
                    with st.container(border=True):
                        st.caption(f"{timestamp} - Demande utilisateur")
                        st.markdown(event["content"])
            continue

        phase_events = {}
        responses = []
        for event in events:
            phase = phase_for(event)
            if not phase:
                continue
            if phase[0] == "Reponse":
                responses.append(event)
                continue
            phase_events.setdefault(phase, []).append(event)

        if not phase_events and not responses:
            continue
        with st.container(border=True):
            st.caption(f"{timestamp} - Etape executee par {events[0]['agent'] or 'Pi'}")
            for (phase_name, phase_description), phase_items in phase_events.items():
                labels = []
                for event in phase_items:
                    label = event["tool_title"] or event["tool_name"] or event["event_type"]
                    if label not in labels:
                        labels.append(label)
                st.markdown(f"**{phase_name}** - {phase_description} ({len(phase_items)} operation(s))")
                st.caption(" | ".join(labels[:4]))

            calls = task_calls(message_events)
            for index, call in enumerate(calls, start=1):
                with st.expander(f"Branche {index} : {call['subagent']} - {call['objectif']} [{call['status']}]", expanded=False):
                    st.caption(f"Lancee par {call['parent_agent']} - {call['branche']}")
                    if call["prompt"]:
                        st.caption("Mission envoyee")
                        st.code(call["prompt"], language="text")
                    if call["resultat"]:
                        st.caption("Resultat renvoye")
                        st.code(call["resultat"], language="text")

            for response in responses:
                if response["content"]:
                    st.markdown("**Reponse visible**")
                    st.markdown(response["content"])


st.set_page_config(page_title="Conversation Observatory", page_icon="O", layout="wide")
apply_design()
live_listener = components.declare_component("bronze_commit_listener", path="/app/live_component")
commit_event = live_listener(url="http://localhost:8504/events", default=None, key="bronze-commit-listener")
if commit_event and commit_event != st.session_state.get("last_bronze_commit"):
    st.session_state.last_bronze_commit = commit_event
    load_event_metadata_since.clear()
    load_thread_page.clear()
    st.rerun()
hero("Observatoire local", "Conversation Observatory", "Un espace clair pour suivre les conversations, les outils et les étapes de travail.", "● DIRECT · ÉVÉNEMENTS REDPANDA")

with st.sidebar:
    st.header("Navigation")
    st.link_button("Ouvrir le dashboard Arroyo Live", "http://localhost:8503", use_container_width=True)
    st.link_button("Ouvrir la documentation", "http://localhost:8502", use_container_width=True)
    st.page_link("pages/compare.py", label="Comparateur technique", icon="📊")
    st.divider()
    st.header("Donnees")
    if st.button("Actualiser maintenant", use_container_width=True):
        load_event_metadata.clear()
        load_event_metadata_since.clear()
        load_thread_page.clear()
        st.session_state.pop("live_events", None)
        st.session_state.pop("live_event_keys", None)
        st.rerun()
    st.markdown('<span class="live-note">● Donnees Bronze en direct</span>', unsafe_allow_html=True)
    st.caption("Le dashboard est actualisé une seule fois après le commit Bronze d’un message finalisé. Aucun rafraîchissement périodique.")

try:
    if "live_events" not in st.session_state:
        st.session_state.live_events = load_event_metadata()
        current = st.session_state.live_events
        st.session_state.live_event_keys = set(zip(
            current.column("session_id").to_pylist(),
            current.column("event_id").to_pylist(),
            current.column("exported_at_ms").to_pylist(),
        )) if current is not None else set()
    else:
        current = st.session_state.live_events
        if current is not None and current.num_rows:
            last_export = max(value for value in current.column("exported_at_ms").to_pylist() if value is not None)
            recent = load_event_metadata_since(last_export)
            if recent is not None and recent.num_rows:
                recent_keys = list(zip(
                    recent.column("session_id").to_pylist(),
                    recent.column("event_id").to_pylist(),
                    recent.column("exported_at_ms").to_pylist(),
                ))
                unseen = [key not in st.session_state.live_event_keys for key in recent_keys]
                if any(unseen):
                    delta = recent.filter(pa.array(unseen))
                    st.session_state.live_events = pa.concat_tables([current, delta])
                    st.session_state.live_event_keys.update(key for key, keep in zip(recent_keys, unseen) if keep)
    events = st.session_state.live_events
except Exception as error:
    st.error("Impossible de lire la table Iceberg.")
    st.exception(error)
    st.stop()

if events is None or events.num_rows == 0:
    st.info("Aucun evenement Iceberg. Lancez un export pi pour initialiser la table.")
    st.code("./scripts/export-pi-conversations.sh", language="bash")
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
        WITH activity AS (
          SELECT
            session_id,
            max(session_title) AS title,
            max(session_agent) AS agent,
            max(session_provider_id) AS provider_id,
            max(session_model_id) AS model_id,
            max(session_model_variant) AS model_variant,
            count(DISTINCT message_id) AS messages,
            count(*) AS events,
            count(*) FILTER (WHERE event_type = 'tool') AS commands,
            max(to_timestamp(message_created_ms / 1000.0) AT TIME ZONE 'Europe/Paris') AS last_activity
          FROM events
          GROUP BY session_id
        ), message_usage AS (
          SELECT
            session_id,
            message_id,
            max(session_agent) AS session_agent,
            max(session_cost) AS cost,
            max(session_tokens_input) AS input_tokens,
            max(session_tokens_output) AS output_tokens,
            max(session_tokens_reasoning) AS reasoning_tokens,
            max(session_tokens_cache_read) AS cache_read_tokens,
            max(session_tokens_cache_write) AS cache_write_tokens
          FROM events
          WHERE role = 'assistant'
          GROUP BY session_id, message_id
        ), usage AS (
          SELECT
            session_id,
            CASE WHEN max(session_agent) = 'build' THEN max(cost) ELSE sum(cost) END AS cost,
            CASE WHEN max(session_agent) = 'build' THEN max(input_tokens) ELSE sum(input_tokens) END AS input_tokens,
            CASE WHEN max(session_agent) = 'build' THEN max(output_tokens) ELSE sum(output_tokens) END AS output_tokens,
            CASE WHEN max(session_agent) = 'build' THEN max(reasoning_tokens) ELSE sum(reasoning_tokens) END AS reasoning_tokens,
            CASE WHEN max(session_agent) = 'build' THEN max(cache_read_tokens) ELSE sum(cache_read_tokens) END AS cache_read_tokens,
            CASE WHEN max(session_agent) = 'build' THEN max(cache_write_tokens) ELSE sum(cache_write_tokens) END AS cache_write_tokens
          FROM message_usage
          GROUP BY session_id
        )
        SELECT
          activity.*,
          usage.cost,
          usage.input_tokens,
          usage.output_tokens,
          usage.reasoning_tokens,
          usage.cache_read_tokens,
          usage.cache_write_tokens
        FROM activity
        LEFT JOIN usage USING (session_id)
        ORDER BY last_activity DESC
        """
    ).fetchdf()
    numeric = ["cost", "input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens"]
    sessions[numeric] = sessions[numeric].fillna(0)
    sessions["total_tokens"] = sessions[numeric[1:]].sum(axis=1)
    sessions["harness"] = sessions["session_id"].map(lambda value: "OpenCode" if str(value).startswith("ses_") else "Pi")
    sessions["model_label"] = sessions["model_id"].fillna("Modèle inconnu")

    total_cost = float(sessions["cost"].sum())
    total_tokens = int(sessions["total_tokens"].sum())
    total_commands = int(sessions["commands"].sum())
    total_messages = int(sessions["messages"].sum())

    first, second, third, fourth, fifth = st.columns(5)
    first.metric("Discussions", f"{len(sessions):,}")
    second.metric("Messages", f"{total_messages:,}")
    third.metric("Outils", f"{total_commands:,}")
    fourth.metric("Tokens", f"{total_tokens:,}")
    fifth.metric("Coût total", f"${total_cost:,.4f}")

    st.markdown("#### Explorer les donnees")
    latest_activity = sessions["last_activity"].max() if not sessions.empty else None
    st.caption(f"Dernière activité visible : {latest_activity.strftime('%d/%m/%Y à %H:%M')}" if latest_activity is not None else "Aucune activité récente")
    page = st.segmented_control(
        "Navigation principale",
        ["Vue d'ensemble", "Discussion", "Requêtes Spark"],
        default="Vue d'ensemble",
        selection_mode="single",
        label_visibility="collapsed",
    )
    page = {"Vue d'ensemble": "Vue globale", "Discussion": "Fil de discussion", "Requêtes Spark": "Requetes Spark"}.get(page, "Vue globale")

    session_options = {f"{row.title or 'Sans titre'} - {row.session_id}": row.session_id for row in sessions.itertuples()}

    if page == "Vue globale":
        st.subheader("Comparaison des modèles et harnais")
        comparison = (
            sessions.groupby(["harness", "model_label"], as_index=False)
            .agg(
                discussions=("session_id", "count"),
                messages=("messages", "sum"),
                commandes=("commands", "sum"),
                tokens=("total_tokens", "sum"),
                cout=("cost", "sum"),
            )
            .sort_values(["tokens", "discussions"], ascending=False)
        )
        left, right = st.columns([1.15, 1])
        with left:
            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "harness": "Harnais", "model_label": "Modèle",
                    "discussions": "Discussions", "messages": "Messages",
                    "commandes": "Outils", "tokens": "Tokens",
                    "cout": st.column_config.NumberColumn("Coût", format="$%.4f"),
                },
            )
        with right:
            st.altair_chart(
                alt.Chart(comparison).mark_bar(cornerRadiusTopRight=6).encode(
                    x=alt.X("tokens:Q", title="Tokens"),
                    y=alt.Y("model_label:N", sort="-x", title="Modèle"),
                    color=alt.Color("harness:N", title="Harnais", scale=alt.Scale(range=["#5264d8", "#e58b35"])),
                    tooltip=["harness", "model_label", "discussions", "tokens", "cout"],
                ).properties(height=260),
                use_container_width=True,
            )

        activity = connection.execute("""
            SELECT CAST(to_timestamp(message_created_ms / 1000.0) AT TIME ZONE 'Europe/Paris' AS DATE) AS jour,
                   count(DISTINCT message_id) AS messages,
                   count(*) FILTER (WHERE event_type = 'tool') AS outils
            FROM events
            WHERE message_created_ms IS NOT NULL
            GROUP BY jour ORDER BY jour
        """).fetchdf()
        if not activity.empty:
            st.subheader("Activité dans le temps")
            st.altair_chart(
                alt.Chart(activity).transform_fold(["messages", "outils"], as_=["metric", "volume"])
                .mark_line(point=True)
                .encode(
                    x=alt.X("jour:T", title="Jour"), y=alt.Y("volume:Q", title="Volume"),
                    color=alt.Color("metric:N", title="Type"), tooltip=["jour:T", "metric:N", "volume:Q"],
                ).properties(height=260),
                use_container_width=True,
            )

        usage_by_model = connection.execute(
            """
            SELECT model_id, count(DISTINCT session_id) AS discussions,
                   sum(session_tokens_input + session_tokens_output + session_tokens_reasoning) AS tokens
            FROM events
            GROUP BY model_id
            ORDER BY tokens DESC
            """
        ).fetchdf()
        tools = connection.execute(
            """
            SELECT coalesce(tool_name, 'inconnu') AS outil, count(*) AS executions
            FROM events
            WHERE event_type = 'tool'
            GROUP BY tool_name
            ORDER BY executions DESC
            LIMIT 10
            """
        ).fetchdf()
        left, right = st.columns(2)
        with left:
            st.subheader("Répartition des tokens par modèle")
            st.altair_chart(
                alt.Chart(usage_by_model).mark_bar(color="#5264d8", cornerRadiusTopRight=7).encode(
                    x=alt.X("tokens:Q", title="Tokens"),
                    y=alt.Y("model_id:N", sort="-x", title="Modele"),
                    tooltip=["model_id", "discussions", "tokens"],
                ),
                use_container_width=True,
            )
        with right:
            st.subheader("Outils les plus utilisés")
            st.altair_chart(
                alt.Chart(tools).mark_bar(color="#e58b35", cornerRadiusTopRight=7).encode(
                    x=alt.X("executions:Q", title="Executions"),
                    y=alt.Y("outil:N", sort="-x", title="Outil"),
                    tooltip=["outil", "executions"],
                ),
                use_container_width=True,
            )
        st.subheader("Toutes les discussions")
        st.dataframe(
            sessions[["session_id", "title", "harness", "model_id", "messages", "commands", "total_tokens", "cost", "last_activity"]],
            use_container_width=True,
            hide_index=True,
            column_config={"cost": st.column_config.NumberColumn("Cout", format="$%.4f")},
        )

    elif page == "Fil de discussion":
        st.subheader("Fil de discussion")
        st.caption("Les messages les plus récents sont affichés en premier. Les pages anciennes sont chargées à la demande.")
        selected_label = st.selectbox("Choisir une discussion", list(session_options), key="thread_session_select")
        selected_session = session_options[selected_label]
        if st.session_state.get("thread_loaded_session") != selected_session:
            st.session_state["thread_loaded_session"] = selected_session
            st.session_state["thread_page_count"] = 1
        selected = sessions.loc[sessions["session_id"] == selected_session].iloc[0]
        st.caption(f"{selected['provider_id'] or 'provider inconnu'} · {selected['model_id'] or 'modèle inconnu'} · agent {selected['agent'] or 'Pi'}")
        first, second, third, fourth = st.columns(4)
        first.metric("Cout", f"${selected['cost']:,.4f}")
        second.metric("Entree", f"{int(selected['input_tokens']):,} tokens")
        third.metric("Sortie", f"{int(selected['output_tokens']):,} tokens")
        fourth.metric("Commandes", f"{int(selected['commands']):,}")
        if st.button("Visualiser le flux de cette discussion", type="primary"):
            st.session_state["flow_session"] = selected_session
            st.switch_page("pages/flow.py")
        st.caption(
            f"Raisonnement non conserve. Cache lu : {int(selected['cache_read_tokens']):,} | "
            f"Cache ecrit : {int(selected['cache_write_tokens']):,} | Evenements : {int(selected['events']):,}"
        )
        page_size = 12
        page_count = st.session_state["thread_page_count"]
        total_messages = int(selected["messages"])
        for page_index in range(page_count):
            message_ids = connection.execute(
                """
                SELECT message_id
                FROM events
                WHERE session_id = ? AND message_id IS NOT NULL
                GROUP BY message_id
                ORDER BY max(message_created_ms) DESC NULLS LAST, max(event_index) DESC
                LIMIT ? OFFSET ?
                """,
                [selected_session, page_size, page_index * page_size],
            ).fetchdf()["message_id"].tolist()
            thread_events = load_thread_page(selected_session, tuple(message_ids))
            if thread_events is None:
                continue
            connection.register("thread_events_raw", thread_events)
            timeline = connection.execute(
                """
                SELECT *, to_timestamp(message_created_ms / 1000.0) AT TIME ZONE 'Europe/Paris' AS created_at
                FROM (
                  SELECT *, row_number() OVER (
                    PARTITION BY session_id, event_id ORDER BY exported_at_ms DESC
                  ) AS event_rank
                  FROM thread_events_raw
                )
                WHERE event_rank = 1
                ORDER BY message_created_ms DESC NULLS LAST, event_index
                """
            ).fetchdf()
            connection.unregister("thread_events_raw")
            if page_index:
                st.divider()
            for event in timeline.to_dict("records"):
                show_event(event)

        loaded_messages = min(page_count * page_size, total_messages)
        if loaded_messages < total_messages:
            if st.button(f"Charger les {min(page_size, total_messages - loaded_messages)} messages precedents"):
                st.session_state["thread_page_count"] += 1
                st.rerun()
        else:
            st.caption("Debut de la discussion atteint.")

    else:
        st.subheader("Requetes Spark")
        st.caption("Ecrire une requete SQL de lecture. Spark lit les Parquet de conversations depuis S3 et renvoie au plus 500 lignes.")
        statement = st.text_area(
            "SQL",
            value="""SELECT tool_name, count(*) AS executions\nFROM events\nWHERE event_type = 'tool'\nGROUP BY tool_name\nORDER BY executions DESC""",
            height=220,
            key="spark_sql",
        )
        st.caption("Table disponible : `events`. L'alias `opencode.events` est automatiquement traduit vers cette vue Spark.")
        if st.button("Executer avec Spark", type="primary"):
            with st.spinner("Execution de la requete Spark..."):
                result = spark_query(statement)
            if "error" in result:
                st.error(result["error"])
            else:
                st.caption(f"{len(result['rows']):,} ligne(s) affichee(s), limite : {result['max_rows']:,}.")
                st.code(result["sql"], language="sql")
                st.dataframe(result["rows"], use_container_width=True, hide_index=True)

finally:
    connection.close()
