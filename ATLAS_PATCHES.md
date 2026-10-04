# Atlas fork patches

This fork carries narrowly scoped integration seams for the Atlas desktop runtime.
Defaults preserve Hermes behavior when the new public options are omitted.

| Files | Purpose | Tests |
|---|---|---|
| `agent/agent_hooks.py`, `run_agent.py`, `agent/agent_init.py` | Add public `AgentHooks` callbacks to `AIAgent(hooks=...)`, `identity=...`, and `set_context_handoff_summary(...)`. | `tests/agent/test_atlas_hooks.py` |
| `agent/system_prompt.py` | Let an embedder select the stable first-line identity and append a system prompt suffix after the existing stable prompt prefix. | `tests/agent/test_atlas_hooks.py` |
| `agent/conversation_loop.py`, `agent/status_output.py`, `agent/turn_context.py`, `agent/turn_tool_round.py` | Dispatch before-model, diagnostic, delegate, title, and handoff behavior through the public hooks/setter while preserving legacy defaults. | `tests/agent/test_atlas_hooks.py` |
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
