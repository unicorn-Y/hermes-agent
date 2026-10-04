# Atlas fork patches

This fork carries narrowly scoped integration seams for the Atlas desktop runtime.
Defaults preserve Hermes behavior when the new public options are omitted.

| Files | Purpose | Tests |
|---|---|---|
| `agent/agent_hooks.py`, `run_agent.py`, `agent/agent_init.py` | Add public `AgentHooks` callbacks to `AIAgent(hooks=...)`, `identity=...`, and `set_context_handoff_summary(...)`. | `tests/agent/test_atlas_hooks.py` |
| `agent/system_prompt.py` | Let an embedder select the stable first-line identity and append a system prompt suffix after the existing stable prompt prefix. | `tests/agent/test_atlas_hooks.py` |
| `agent/conversation_loop.py`, `agent/status_output.py`, `agent/turn_context.py`, `agent/turn_tool_round.py` | Dispatch before-model, diagnostic, delegate, title, and handoff behavior through the public hooks/setter while preserving legacy defaults. | `tests/agent/test_atlas_hooks.py` |
| `run_agent.py`, `agent/agent_init.py` | Preserve the existing public `credential_pool=None` constructor option for embedders; Atlas can pass a route-scoped pool without private-field mutation, while `None` keeps the upstream auth path. | `tests/agent/test_atlas_hooks.py` |
