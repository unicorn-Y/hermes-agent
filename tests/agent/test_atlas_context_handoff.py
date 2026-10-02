from types import SimpleNamespace

from agent.turn_tool_round import _apply_atlas_context_handoff
from agent.context_compressor import _DB_PERSISTED_MARKER


def test_context_handoff_replaces_only_the_live_model_context():
    agent = SimpleNamespace(
        _atlas_context_handoff_summary="## 当前目标/约束\n修复问题",
        _todo_store=SimpleNamespace(read=lambda: [{"text": "检查回归", "status": "pending"}]),
    )
    messages = [
        {"role": "system", "content": "Atlas stable rules"},
        {"role": "user", "content": "old task"},
        {"role": "assistant", "content": "old answer"},
    ]

    assert _apply_atlas_context_handoff(agent, messages, "Atlas stable rules") is True
    assert messages[0] == {"role": "system", "content": "Atlas stable rules"}
    assert messages[1]["role"] == "user"
    assert "修复问题" in messages[1]["content"]
    assert "检查回归" in messages[1]["content"]
    assert messages[1][_DB_PERSISTED_MARKER] is True
    assert agent._atlas_context_handoff_summary is None
