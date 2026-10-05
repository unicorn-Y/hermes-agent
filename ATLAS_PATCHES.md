# Atlas fork patches

This fork carries narrowly scoped integration seams for the Atlas desktop runtime.
Defaults preserve Hermes behavior when the new public options are omitted.

| Files | Purpose | Tests |
|---|---|---|
| `agent/agent_hooks.py`, `run_agent.py`, `agent/agent_init.py` | Add public `AgentHooks` callbacks to `AIAgent(hooks=...)`, `identity=...`, and `set_context_handoff_summary(...)`. | `tests/agent/test_atlas_hooks.py` |
| `agent/system_prompt.py` | Let an embedder select the stable first-line identity and append a system prompt suffix after the existing stable prompt prefix. | `tests/agent/test_atlas_hooks.py` |
| `agent/conversation_loop.py`, `agent/status_output.py`, `agent/turn_context.py`, `agent/turn_tool_round.py` | Dispatch before-model, diagnostic, delegate, title, and handoff behavior through the public hooks/setter while preserving legacy defaults. | `tests/agent/test_atlas_hooks.py` |
| `agent/agent_hooks.py`, `agent/conversation_loop.py`, `agent/turn_usage.py` | Publish one public usage row per completed provider response, including current context limit, request identity, request-sent flag, and cache-field presence metadata without raw values; expose optional pre-provider reserve/release hooks. | Atlas fake-provider R7 runtime/context-limit tests; `tests/agent/test_actual_auxiliary_routing.py::test_cache_usage_fields_distinguish_absent_from_explicit_zero` |
| `agent/context_compressor.py`, `agent/turn_context.py`, `agent/title_generator.py` | Forward the same request ID through title/compression preflight reservation, usage settlement, and release hooks. | `tests/agent/test_actual_auxiliary_routing.py::test_title_and_compression_share_request_ids_with_budget_hooks` |
| `agent/agent_hooks.py`, `agent/conversation_loop.py`, `agent/agent_runtime_helpers.py`, `agent/chat_completion_helpers.py`, `agent/auxiliary_client.py`, `agent/context_compressor.py` | Add an opt-in `disable_provider_retries` hook so budgeted main and auxiliary requests send once — including the hidden primary-transport recovery resend and the stream_options compatibility retry — and unknown usage fails closed; failed dispatches report `request_sent: false` so the host budget refunds instead of charging; the default preserves Hermes retries. | Atlas fake-provider budget tests; `tests/agent/test_atlas_hooks.py::test_before_provider_hook_exception_fails_closed`; `tests/agent/test_auxiliary_client.py::TestTransientTransportRetry::test_run_budget_mode_stops_after_one_failed_send` |
| `run_agent.py`, `agent/agent_init.py` | Preserve the existing public `credential_pool=None` constructor option for embedders; Atlas can pass a route-scoped pool without private-field mutation, while `None` keeps the upstream auth path. | `tests/agent/test_atlas_hooks.py` |
| `run_agent.py`, `agent/context_compressor.py`, `toolsets.py` | Preserve Atlas context handoff through the live model context and include ordered Next Steps in compression summaries; expose the existing new-context tool in the core toolset. | `tests/agent/test_atlas_context_handoff.py`, `tests/agent/test_context_compressor.py::test_summary_template_has_fixed_handoff_fields` |
| `agent/tool_guardrails.py` | Hash multimodal tool-result dictionaries without a string-only failure. | `tests/agent/test_tool_guardrails.py::test_tool_result_hash_accepts_multimodal_image_envelopes` |
| `tools/file_operations.py` | Preserve UTF-8/UTF-16 BOMs and CRLF during native patches/writes, including UTF-16 sample boundaries inside surrogate pairs. | `tests/tools/test_file_operations.py` |
| `tools/file_tools_read_tracking.py` | Keep the full-read baseline valid after atomic replacement while detecting external content or metadata changes. | `tests/tools/test_known_file_write_baseline.py` |
| `tools/fuzzy_match.py` | Match block anchors whose middle spans have different lengths. | `tests/tools/test_fuzzy_match.py::TestIndentDifference::test_block_anchor_matches_a_variable_length_middle` |
| `tests/tools/test_mcp_windows_orphan_fix.py` | Separate Windows native tree-kill signal expectations from POSIX process-group behavior; production tree cleanup is inherited from upstream. | `tests/tools/test_mcp_windows_orphan_fix.py` |
| `pyproject.toml` | Align OpenAI 2.26.0 and Pydantic 2.13.5 pins with Atlas browser-use dependencies on Python 3.14. | Installed package metadata compatibility check (browser-use 0.13.10 requires the same exact versions), plus `tests/agent/test_atlas_hooks.py` public-constructor integration |

Inventory reviewed against upstream `c8301ea6c9` for the H1R closeout. Earlier
patches absorbed into upstream are not additional fork deltas. The fixed-date
context-compressor test remains a known failure on the old fork as well; it has
not been disabled or given a date workaround.
