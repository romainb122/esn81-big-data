import json
import urllib.error
import urllib.request

import altair as alt
import duckdb
import streamlit as st
from data_access import load_event_metadata, load_thread_page
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
        author = "Vous" if event["role"] == "user" else "OpenCode"
        with st.chat_message("user" if event["role"] == "user" else "assistant"):
            st.caption(f"{author} - {timestamp}")
            st.markdown(event["content"])
        return

    st.caption(f"{timestamp} - {label}")


def task_calls(trace):
    """Extract OpenCode task delegations recorded in tool events."""
    calls = []
    for event in trace.loc[(trace["event_type"] == "tool") & (trace["tool_name"] == "task")].to_dict("records"):
        try:
            task = json.loads(event["tool_input_json"] or "{}")
        except json.JSONDecodeError:
            task = {}
        calls.append(
            {
                "parent_message_id": event["message_id"],
                "parent_agent": event["agent"] or "OpenCode",
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
            st.caption(f"{timestamp} - Etape executee par {events[0]['agent'] or 'OpenCode'}")
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


st.set_page_config(page_title="OpenCode Observatory", page_icon="O", layout="wide")
apply_design()
hero("Observatoire local", "OpenCode Observatory", "Conversations, agents et operations versionnes dans Iceberg puis analyses avec DuckDB.")

with st.sidebar:
    st.header("Donnees")
    if st.button("Rafraichir depuis S3", use_container_width=True):
        load_event_metadata.clear()
        load_thread_page.clear()
    st.caption("L'index Iceberg est mis en cache 60 secondes. Le contenu du fil est charge par pages.")

try:
    events = load_event_metadata()
except Exception as error:
    st.error("Impossible de lire la table Iceberg.")
    st.exception(error)
    st.stop()

if events is None or events.num_rows == 0:
    st.info("Aucun evenement Iceberg. Lancez un export force pour initialiser la table.")
    st.code("./scripts/export-opencode-conversations.sh --force", language="bash")
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
        SELECT
          session_id,
          max(session_title) AS title,
          max(session_agent) AS agent,
          max(session_provider_id) AS provider_id,
          max(session_model_id) AS model_id,
          max(session_model_variant) AS model_variant,
          max(session_cost) AS cost,
          max(session_tokens_input) AS input_tokens,
          max(session_tokens_output) AS output_tokens,
          max(session_tokens_reasoning) AS reasoning_tokens,
          max(session_tokens_cache_read) AS cache_read_tokens,
          max(session_tokens_cache_write) AS cache_write_tokens,
          count(DISTINCT message_id) AS messages,
          count(*) AS events,
          count(*) FILTER (WHERE event_type = 'tool') AS commands,
          max(to_timestamp(message_created_ms / 1000.0)) AS last_activity
        FROM events
        GROUP BY session_id
        ORDER BY last_activity DESC
        """
    ).fetchdf()
    numeric = ["cost", "input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens"]
    sessions[numeric] = sessions[numeric].fillna(0)
    sessions["total_tokens"] = sessions[numeric[1:]].sum(axis=1)

    total_cost = float(sessions["cost"].sum())
    total_tokens = int(sessions["total_tokens"].sum())
    total_commands = int(sessions["commands"].sum())
    total_messages = int(sessions["messages"].sum())

    first, second, third, fourth = st.columns(4)
    first.metric("Discussions", f"{len(sessions):,}")
    second.metric("Messages", f"{total_messages:,}")
    third.metric("Commandes executees", f"{total_commands:,}")
    fourth.metric("Tokens / cout", f"{total_tokens:,} / ${total_cost:,.4f}")

    st.markdown("#### Explorer les donnees")
    page = st.radio(
        "Navigation principale",
        ["Vue globale", "Fil de discussion", "Parcours de traitement", "Requetes Spark"],
        horizontal=True,
        label_visibility="collapsed",
    )

    session_options = {f"{row.title or 'Sans titre'} - {row.session_id}": row.session_id for row in sessions.itertuples()}

    if page == "Vue globale":
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
            st.subheader("Tokens par modele")
            st.altair_chart(
                alt.Chart(usage_by_model).mark_bar(color="#6ee7b7", cornerRadiusTopRight=7).encode(
                    x=alt.X("tokens:Q", title="Tokens"),
                    y=alt.Y("model_id:N", sort="-x", title="Modele"),
                    tooltip=["model_id", "discussions", "tokens"],
                ),
                use_container_width=True,
            )
        with right:
            st.subheader("Outils les plus utilises")
            st.altair_chart(
                alt.Chart(tools).mark_bar(color="#7aa7ff", cornerRadiusTopRight=7).encode(
                    x=alt.X("executions:Q", title="Executions"),
                    y=alt.Y("outil:N", sort="-x", title="Outil"),
                    tooltip=["outil", "executions"],
                ),
                use_container_width=True,
            )
        st.subheader("Toutes les discussions")
        st.dataframe(
            sessions[["session_id", "title", "model_id", "agent", "messages", "commands", "total_tokens", "cost", "last_activity"]],
            use_container_width=True,
            hide_index=True,
            column_config={"cost": st.column_config.NumberColumn("Cout", format="$%.4f")},
        )

    elif page == "Fil de discussion":
        st.subheader("Fil de discussion")
        st.caption("Les 12 derniers messages sont affiches en premier. Les messages plus anciens sont charges a la demande.")
        selected_label = st.selectbox("Choisir une discussion", list(session_options), key="thread_session_select")
        selected_session = session_options[selected_label]
        if st.session_state.get("thread_loaded_session") != selected_session:
            st.session_state["thread_loaded_session"] = selected_session
            st.session_state["thread_page_count"] = 1
        selected = sessions.loc[sessions["session_id"] == selected_session].iloc[0]
        st.caption(f"{selected['provider_id']}/{selected['model_id']} - agent {selected['agent']}")
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
                SELECT *, to_timestamp(message_created_ms / 1000.0) AS created_at
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

    elif page == "Parcours de traitement":
        st.subheader("Parcours de traitement")
        st.caption("Journal observable : demande, analyse, delegation, modification, verification et reponse. Ce n'est pas un raisonnement interne.")
        selected_label = st.selectbox("Choisir une discussion", list(session_options), key="trace_session")
        selected_session = session_options[selected_label]
        selected = sessions.loc[sessions["session_id"] == selected_session].iloc[0]
        trace = connection.execute(
            """
            SELECT *, to_timestamp(message_created_ms / 1000.0) AS created_at
            FROM events
            WHERE session_id = ?
            ORDER BY message_created_ms, event_index
            """,
            [selected_session],
        ).fetchdf()
        calls = task_calls(trace)
        completed = int(sum(call["status"] in ["completed", "success"] for call in calls))
        first, second, third, fourth = st.columns(4)
        first.metric("Agent", selected["agent"] or "OpenCode")
        second.metric("Etapes", f"{trace['message_id'].nunique():,}")
        third.metric("Sous-taches", f"{len(calls):,}")
        fourth.metric("Sous-taches terminees", f"{completed:,}")

        st.subheader("Etapes observees")
        render_processing_trace(trace)

        st.subheader("Iterations de l'agent")
        loops = connection.execute(
            """
            SELECT
              message_id,
              min(to_timestamp(message_created_ms / 1000.0)) AS debut,
              max(agent) AS agent,
              count(*) FILTER (WHERE event_type = 'tool') AS operations,
              string_agg(DISTINCT tool_name, ', ') FILTER (WHERE event_type = 'tool') AS outils,
              string_agg(DISTINCT tool_status, ', ') FILTER (WHERE event_type = 'tool') AS statuts
            FROM events
            WHERE session_id = ?
            GROUP BY message_id
            ORDER BY min(message_created_ms), min(event_index)
            """,
            [selected_session],
        ).fetchdf()
        st.dataframe(loops, use_container_width=True, hide_index=True)

    else:
        st.subheader("Requetes Spark")
        st.caption("Ecrire une requete SQL de lecture. Spark lit les Parquet OpenCode depuis S3 et renvoie au plus 500 lignes.")
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
