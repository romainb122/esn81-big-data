CREATE TABLE conversation_events (
  session_id TEXT,
  event_id TEXT,
  event_index BIGINT,
  event_type TEXT,
  role TEXT,
  content TEXT,
  session_agent TEXT,
  session_provider_id TEXT,
  session_model_id TEXT,
  session_cost DOUBLE,
  session_tokens_input BIGINT,
  session_tokens_output BIGINT,
  session_tokens_reasoning BIGINT,
  session_tokens_cache_read BIGINT,
  session_tokens_cache_write BIGINT,
  message_created_ms BIGINT,
  message_completed_ms BIGINT,
  exported_at_ms BIGINT
) WITH (
  connector = 'kafka',
  type = 'source',
  bootstrap_servers = 'redpanda:9092',
  topic = 'opencode.events',
  format = 'json',
  'source.offset' = 'latest'
);

SELECT
  session_id,
  event_id,
  role,
  content,
  session_agent,
  session_provider_id,
  session_model_id,
  session_cost,
  session_tokens_input,
  session_tokens_output,
  session_tokens_reasoning,
  session_tokens_cache_read,
  session_tokens_cache_write,
  message_created_ms,
  message_completed_ms,
  exported_at_ms
FROM conversation_events
WHERE role = 'assistant' AND event_type = 'text';
