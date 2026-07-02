"""Tests for engine.executor.PlanExecutor step dispatch and failure handling."""

from engine.executor import PlanExecutor


def test_execute_plan_stops_on_first_failure():
    executor = PlanExecutor()
    executor._dispatch = {
        "ok_step": lambda p: {"done": True},
        "bad_step": lambda p: (_ for _ in ()).throw(RuntimeError("boom")),
    }
    plan = [
        {"step": 1, "action": "ok_step", "params": {}},
        {"step": 2, "action": "bad_step", "params": {}},
        {"step": 3, "action": "ok_step", "params": {}},
    ]
    result = executor.execute_plan(plan, stop_on_error=True)

    assert result["success"] is False
    assert len(result["completed_steps"]) == 2
    assert result["failed_step"]["step"] == 2


def test_execute_plan_unknown_action():
    executor = PlanExecutor()
    executor._dispatch = {}
    plan = [{"step": 1, "action": "does_not_exist", "params": {}}]
    result = executor.execute_plan(plan)

    assert result["success"] is False
    assert "Unknown action" in result["completed_steps"][0]["error"]


def test_execute_plan_all_success():
    executor = PlanExecutor()
    executor._dispatch = {"noop": lambda p: {"ok": True}}
    plan = [
        {"step": 1, "action": "noop", "params": {}},
        {"step": 2, "action": "noop", "params": {}},
    ]
    result = executor.execute_plan(plan)

    assert result["success"] is True
    assert len(result["completed_steps"]) == 2
