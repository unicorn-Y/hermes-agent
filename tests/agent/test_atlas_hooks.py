"""Public hook and identity integration points used by Atlas."""

from types import SimpleNamespace
from unittest.mock import patch

from agent.agent_hooks import AgentHooks
from agent.prompt_builder import DEFAULT_AGENT_IDENTITY
from agent.status_output import StatusOutputMixin
from agent.system_prompt import _identity_parts
from agent.system_prompt import build_system_prompt_parts
from run_agent import AIAgent


def test_agent_hooks_and_identity_are_public_constructor_options():
    hooks = AgentHooks()
    assert "hooks" in AIAgent.__init__.__code__.co_varnames
    assert "identity" in AIAgent.__init__.__code__.co_varnames
    assert AgentHooks(before_model_request=lambda: False).before_model_request() is False
    assert _identity_parts(SimpleNamespace(
        identity="You are Atlas.", load_soul_identity=False, skip_context_files=True,
    ), 1000)[0] == ["You are Atlas."]
    assert DEFAULT_AGENT_IDENTITY.startswith("You are Hermes Agent")
    assert hooks.delegate_dispatcher is None
    assert hooks.disable_provider_retries is False


def test_credential_pool_constructor_option_preserves_default_and_forwards_value():
    from unittest.mock import patch

    with patch("agent.agent_init.init_agent") as init_agent:
        AIAgent()
        assert init_agent.call_args.kwargs["credential_pool"] is None

        pool = object()
        AIAgent(credential_pool=pool)
        assert init_agent.call_args.kwargs["credential_pool"] is pool


def test_unconfigured_identity_keeps_hermes_default():
    from agent.system_prompt import DEFAULT_AGENT_IDENTITY

    identity, soul_loaded = _identity_parts(SimpleNamespace(
        identity=None, load_soul_identity=False, skip_context_files=True,
    ), 1000)
    assert identity == [DEFAULT_AGENT_IDENTITY]
    assert soul_loaded is False


def test_diagnostic_hook_receives_buffered_diagnostic_without_replacing_status():
    seen = []
    class Agent(StatusOutputMixin):
        hooks = AgentHooks(on_diagnostic=seen.append)
        def _buffer_status(self, value):
            self.buffered = value

    agent = Agent()
    agent._buffer_diagnostic_status("recovering")
    assert seen == ["recovering"]
    assert str(agent.buffered) == "recovering"


def test_diagnostic_hook_runs_even_when_output_is_suppressed():
    seen = []
    class Agent(StatusOutputMixin):
        hooks = AgentHooks(on_diagnostic=seen.append)
        suppress_status_output = True

    Agent()._vprint("quiet diagnostic", diagnostic=True)
    assert seen == ["quiet diagnostic"]


def test_delegate_hook_overrides_default_dispatcher():
    expected = '{"delegated": true}'
    agent = AIAgent.__new__(AIAgent)
    agent.hooks = AgentHooks(delegate_dispatcher=lambda args: expected)
    assert agent._dispatch_delegate_task({"goal": "work"}) == expected


def test_context_handoff_summary_has_public_setter_and_is_consumed():
    from agent.turn_tool_round import _apply_atlas_context_handoff

    agent = AIAgent.__new__(AIAgent)
    agent.set_context_handoff_summary("continue work")
    assert agent.context_handoff_summary == "continue work"
    agent._todo_store = None
    messages = [{"role": "user", "content": "old context"}]
    assert _apply_atlas_context_handoff(agent, messages, "stable") is True
    assert messages[0] == {"role": "system", "content": "stable"}
    assert "continue work" in messages[1]["content"]
    assert agent.context_handoff_summary is None


def test_before_model_hook_is_invoked_at_request_gate():
    from agent.conversation_loop import _before_model_request

    called = []
    agent = SimpleNamespace(hooks=AgentHooks(before_model_request=lambda: called.append(True) or True))
    assert _before_model_request(agent) is True
    assert called == [True]


def test_before_provider_hook_receives_estimate_and_request_id():
    from agent.conversation_loop import _before_provider_request

    called = []
    agent = SimpleNamespace(hooks=AgentHooks(
        before_provider_request=lambda estimate, request_id: called.append((estimate, request_id)) or False,
    ))
    assert _before_provider_request(agent, 123, "turn-1:api:2") is False
    assert called == [(123, "turn-1:api:2")]


def test_before_provider_hook_exception_fails_closed():
    from agent.conversation_loop import _before_provider_request

    def fail(_estimate, _request_id):
        raise RuntimeError("budget audit unavailable")

    agent = SimpleNamespace(hooks=AgentHooks(before_provider_request=fail))
    assert _before_provider_request(agent, 123, "turn-1:api:3") is True


def test_title_hook_is_passed_to_auto_title_callback(monkeypatch):
    from agent.turn_context import _maybe_title_session_at_turn_start

    called = []
    callback = lambda title, source: called.append((title, source))
    agent = SimpleNamespace(
        _session_db=object(), _session_db_created=True, session_id="session",
        platform="desktop", model="m", provider="p", base_url="", api_key="k",
        api_mode="openai", hooks=AgentHooks(on_session_title=callback),
    )
    captured = {}

    def fake_maybe_auto_title(*_args, **kwargs):
        captured["callback"] = kwargs["title_callback"]
        return None

    monkeypatch.setattr("agent.title_generator.maybe_auto_title", fake_maybe_auto_title)
    _maybe_title_session_at_turn_start(agent, [{"role": "user", "content": "hello"}])
    captured["callback"]("A title", "generated")
    assert called == [("A title", "generated")]


def test_prompt_suffix_is_appended_after_stable_identity_prefix():
    seen = []
    agent = SimpleNamespace(
        identity="You are Atlas.", hooks=AgentHooks(
            system_prompt_suffix=lambda prefix: seen.append(prefix) or "Atlas runtime guidance.",
        ),
        load_soul_identity=False, skip_context_files=True, valid_tool_names=[],
        _task_completion_guidance=False, _tool_use_enforcement=False,
        _environment_probe=False, _kanban_worker_guidance="", _memory_store=None,
        _memory_manager=None, model="", provider="", platform="", pass_session_id=False,
        session_id="", _parallel_tool_call_guidance=False,
        _emit_status=lambda *_args, **_kwargs: None,
    )
    with (
        patch("agent.prompt_builder.build_environment_hints", return_value=""),
        patch("agent.coding_context.coding_system_prompt_parts", return_value=([], [], [])),
        patch("agent.file_safety._resolve_active_profile_name", return_value="default"),
    ):
        parts = build_system_prompt_parts(agent)

    assert seen and seen[0].startswith("You are Atlas.")
    assert parts["stable"].startswith("You are Atlas.")
    assert parts["stable"].endswith("Atlas runtime guidance.")

