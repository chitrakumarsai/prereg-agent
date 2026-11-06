"""The agent loop with a stubbed model and a stubbed sandbox."""

from pathlib import Path

import pytest

from prereg import agent, llm
from prereg.schema import AnalysisPlan, RunResult

PLAN = AnalysisPlan(hypothesis="Value differs by group", test="welch_t", outcome="v", predictor="g", alpha=0.05,
                    decision_rule="Reject if p < 0.05")
GOOD = "```python\nprint('ok')\n```"


def _ok_run(*_args, **_kwargs) -> RunResult:
    return RunResult(status="ok", exit_code=0, duration_s=0.1, log="", result={"p_value": 0.5})


def test_reply_without_code_uses_a_retry(monkeypatch):
    replies = iter(["", GOOD])
    monkeypatch.setattr(llm, "chat", lambda *a, **k: (next(replies), "m"))
    monkeypatch.setattr(agent, "run_in_sandbox", _ok_run)
    events: list[tuple[str, dict]] = []
    code, run, attempt = agent.execute(PLAN, {"rows": 1, "columns": []}, Path("x.csv"), lambda k, d: events.append((k, d)))
    assert code == "print('ok')" and attempt == 2
    assert any(k == "retry" for k, _ in events)


def test_execute_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: (GOOD, "m"))
    monkeypatch.setattr(agent, "run_in_sandbox",
                        lambda *a, **k: RunResult(status="error", exit_code=1, duration_s=0.1, log="boom"))
    with pytest.raises(agent.AgentError):
        agent.execute(PLAN, {"rows": 1, "columns": []}, Path("x.csv"), lambda k, d: None)
