"""Public integration hooks for applications embedding AIAgent."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class AgentHooks:
    """Optional callbacks; unset callbacks preserve Hermes behavior."""

    before_model_request: Callable[[], bool] | None = None
    on_diagnostic: Callable[[str], None] | None = None
    delegate_dispatcher: Callable[[dict], str] | None = None
    on_session_title: Callable[[str, str], None] | None = None
    system_prompt_suffix: Callable[[str], str] | None = None
