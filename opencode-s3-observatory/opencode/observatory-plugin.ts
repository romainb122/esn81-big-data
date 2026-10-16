/** OpenCode -> the existing Redpanda/Iceberg conversation pipeline. */

export const ObservatoryPlugin = async ({ client, serverUrl }) => {
  const published = new Set();
  let eventIndex = 0;

  async function publish(row) {
    const baseUrl = process.env.REDPANDA_PROXY_URL ?? "http://localhost:18082";
    const topic = process.env.REDPANDA_TOPIC ?? "opencode.events";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/topics/${topic}`, {
      method: "POST",
      headers: {
        Accept: "application/vnd.kafka.v2+json",
        "Content-Type": "application/vnd.kafka.json.v2+json",
      },
      body: JSON.stringify({ records: [{ key: `${row.session_id}:${row.event_id}`, value: row }] }),
    });
    if (!response.ok) throw new Error(`Redpanda HTTP ${response.status}`);
  }

  function text(value) {
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return value.map((part) => part?.text ?? "").join("");
    return null;
  }

  async function exportSession(sessionId) {
    const result = await client.session.messages({ path: { id: sessionId } });
    const messages = result.data ?? result;
    if (!Array.isArray(messages)) return;

    const rows = [];
    for (const entry of messages) {
      const info = entry.info ?? entry.message ?? {};
      const parts = entry.parts ?? [];
      const usage = info.tokens ?? {};
      const cache = usage.cache ?? {};
      for (const part of parts) {
        if (part.type === "reasoning") continue;
        const eventId = part.id ?? `${info.id}:${eventIndex}`;
        if (published.has(`${sessionId}:${eventId}`)) continue;
        const isTool = part.type === "tool";
        const state = isTool ? (part.state ?? {}) : {};
        rows.push({
          session_id: sessionId,
          session_title: sessionId,
          session_created_ms: info.time?.created ?? null,
          session_updated_ms: info.time?.completed ?? info.time?.created ?? Date.now(),
          session_agent: "opencode",
          session_provider_id: info.providerID ?? info.model?.providerID ?? null,
          session_model_id: info.modelID ?? info.model?.modelID ?? null,
          session_model_variant: null,
          session_cost: typeof info.cost === "number" ? info.cost : null,
          session_tokens_input: usage.input ?? null,
          session_tokens_output: usage.output ?? null,
          session_tokens_reasoning: usage.reasoning ?? null,
          session_tokens_cache_read: cache.read ?? null,
          session_tokens_cache_write: cache.write ?? null,
          exported_at_ms: Date.now(),
          message_id: info.id ?? part.messageID,
          event_id: eventId,
          event_index: eventIndex++,
          event_type: isTool ? "tool" : part.type,
          role: info.role ?? "assistant",
          message_created_ms: info.time?.created ?? null,
          message_completed_ms: info.time?.completed ?? null,
          agent: info.agent ?? "opencode",
          provider_id: info.providerID ?? info.model?.providerID ?? null,
          model_id: info.modelID ?? info.model?.modelID ?? null,
          content: isTool ? null : text(part.text),
          tool_name: isTool ? part.tool ?? null : null,
          tool_title: isTool ? state.title ?? part.tool ?? null : null,
          tool_status: isTool ? state.status ?? null : null,
          tool_input_json: isTool ? JSON.stringify(state.input ?? {}) : null,
          tool_output: isTool ? text(state.output ?? state.error) : null,
          details_json: JSON.stringify(part),
        });
      }
    }

    for (const row of rows) {
      try {
        await publish(row);
        published.add(`${sessionId}:${row.event_id}`);
      } catch (error) {
        console.error(`[observatory-opencode] ${error instanceof Error ? error.message : error}`);
      }
    }
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        await exportSession(event.properties.sessionID);
      }
    },
  };
};

export default ObservatoryPlugin;
