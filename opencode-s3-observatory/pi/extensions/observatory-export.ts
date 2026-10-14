import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/** Publish finalized pi messages directly to the existing Redpanda topic. */
export default function (pi: ExtensionAPI) {
  let eventIndex = 0;

  const publish = async (value: Record<string, unknown>) => {
    const baseUrl = process.env.REDPANDA_PROXY_URL ?? "http://localhost:18082";
    const topic = process.env.REDPANDA_TOPIC ?? "opencode.events";
    try {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/topics/${topic}`, {
        method: "POST",
        headers: {
          Accept: "application/vnd.kafka.v2+json",
          "Content-Type": "application/vnd.kafka.json.v2+json",
        },
        body: JSON.stringify({
          records: [{ key: `${value.session_id}:${value.event_id}`, value }],
        }),
      });
      if (!response.ok) throw new Error(`Redpanda HTTP ${response.status}`);
    } catch (error) {
      // Do not break a pi conversation because the local analytics stack is down.
      console.error(`[observatory-export] ${error instanceof Error ? error.message : error}`);
    }
  };

  pi.on("session_start", () => {
    eventIndex = 0;
  });

  pi.on("message_end", async (event, ctx) => {
    const message = event.message as any;
    const sessionId = ctx.sessionManager.getSessionId();
    const now = Date.now();
    const messageId = message.id ?? `${message.role}:${now}:${eventIndex}`;
    const model = message.model;
    const usage = message.usage ?? {};
    const cost = usage.cost?.total;
    const common = {
      session_id: sessionId,
      session_title: ctx.sessionManager.getSessionName() ?? ctx.cwd,
      session_created_ms: null,
      session_updated_ms: now,
      session_agent: "pi",
      session_provider_id: message.provider,
      session_model_id: model,
      session_model_variant: null,
      session_cost: typeof cost === "number" ? cost : null,
      session_tokens_input: usage.input ?? null,
      session_tokens_output: usage.output ?? null,
      session_tokens_reasoning: null,
      session_tokens_cache_read: usage.cacheRead ?? null,
      session_tokens_cache_write: usage.cacheWrite ?? null,
      exported_at_ms: now,
      message_id: messageId,
      message_created_ms: message.timestamp ?? now,
      message_completed_ms: now,
      agent: "pi",
      provider_id: message.provider,
      model_id: model,
    };

    const parts = Array.isArray(message.content) ? message.content : [];
    const publishRows = parts.flatMap((part: any) => {
      if (part.type === "thinking") return [];
      const isTool = part.type === "toolCall";
      const row = {
        ...common,
        event_id: part.id ?? `${messageId}:${eventIndex}`,
        event_index: eventIndex++,
        event_type: isTool ? "tool" : "text",
        role: message.role,
        content: isTool ? null : (part.text ?? null),
        tool_name: isTool ? (part.name ?? null) : null,
        tool_title: isTool ? (part.name ?? null) : null,
        tool_status: isTool ? "pending" : null,
        tool_input_json: isTool ? JSON.stringify(part.arguments ?? {}) : null,
        tool_output: null,
        details_json: JSON.stringify({ stopReason: message.stopReason ?? null }),
      };
      return [row];
    });

    if (message.role === "toolResult") {
      publishRows.push({
        ...common,
        event_id: messageId,
        event_index: eventIndex++,
        event_type: "tool",
        role: "tool",
        content: null,
        tool_name: message.toolName ?? null,
        tool_title: message.toolName ?? null,
        tool_status: message.isError ? "error" : "success",
        tool_input_json: null,
        tool_output: parts.map((part: any) => part.text ?? "").join(""),
        details_json: JSON.stringify({ durationMs: message.durationMs ?? null }),
      });
    }

    await Promise.all(publishRows.map((row) => publish(row)));
  });
}
