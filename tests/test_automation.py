"""Tests for smauto.lib.automation — Automation and Action classes."""

from unittest.mock import MagicMock, patch
from smauto.lib.automation import (
    Automation,
    Action,
    SetAction,
    IntSetAction,
    FloatSetAction,
    StringSetAction,
    BoolSetAction,
    ListSetAction,
    DictSetAction,
)
from smauto.lib.entity import IntAttribute, BoolAttribute
from smauto.lib.types import List, Dict


def _make_condition(evaluate_return=(False, "not triggered")):
    cond = MagicMock()
    cond.evaluate.return_value = evaluate_return
    cond.build.return_value = None
    cond.cond_lambda = "True"
    return cond


def _make_automation(**overrides):
    defaults = dict(
        parent=None,
        name="test_auto",
        condition=_make_condition(),
        actions=[],
        elseActions=[],
        freq=1,
        enabled=True,
        continuous=True,
        checkOnce=False,
        delay=0,
        cooldown=0,
        triggers=[],
        terminates=[],
        description="",
    )
    defaults.update(overrides)
    return Automation(**defaults)


# ── Action classes ───────────────────────────────────────────────


class TestAction:
    def test_init(self):
        a = Action(None)
        assert a.parent is None


class TestSetAction:
    def test_init(self):
        attr = IntAttribute(None, "temp", 0, None, None)
        sa = SetAction(None, attr, 42)
        assert sa.attribute is attr
        assert sa.value == 42

    def test_int_set_action(self):
        attr = IntAttribute(None, "x", 0, None, None)
        a = IntSetAction(None, attr, 10)
        assert isinstance(a, SetAction)
        assert a.value == 10

    def test_float_set_action(self):
        a = FloatSetAction(None, MagicMock(), 3.14)
        assert isinstance(a, SetAction)
        assert a.value == 3.14

    def test_string_set_action(self):
        a = StringSetAction(None, MagicMock(), "hello")
        assert isinstance(a, SetAction)
        assert a.value == "hello"

    def test_bool_set_action(self):
        a = BoolSetAction(None, MagicMock(), True)
        assert isinstance(a, SetAction)
        assert a.value is True

    def test_list_set_action(self):
        a = ListSetAction(None, MagicMock(), [1, 2, 3])
        assert isinstance(a, SetAction)
        assert a.value == [1, 2, 3]

    def test_dict_set_action(self):
        a = DictSetAction(None, MagicMock(), {"a": 1})
        assert isinstance(a, SetAction)
        assert a.value == {"a": 1}


# ── Automation class ─────────────────────────────────────────────


class TestAutomationInit:
    def test_defaults(self):
        a = _make_automation(
            freq=None,
            enabled=None,
            continuous=None,
            checkOnce=None,
            delay=None,
            triggers=None,
            terminates=None,
            description=None,
        )
        assert a.enabled is True
        assert a.continuous is True
        assert a.checkOnce is False
        assert a.freq == 1
        assert a.delay == 0
        assert a.triggers == []
        assert a.terminates == []
        assert a.description == ""
        assert a.status == Automation.IDLE

    def test_explicit_values(self):
        a = _make_automation(
            freq=5,
            enabled=False,
            continuous=False,
            checkOnce=True,
            delay=2.5,
            description="test desc",
        )
        assert a.freq == 5
        assert a.enabled is False
        assert a.continuous is False
        assert a.checkOnce is True
        assert a.delay == 2.5
        assert a.description == "test desc"

    def test_freq_zero_defaults_to_one(self):
        a = _make_automation(freq=0)
        assert a.freq == 1

    def test_status_constants(self):
        assert Automation.IDLE == "IDLE"
        assert Automation.RUNNING == "RUNNING"
        assert Automation.SUCCESS == "SUCCESS"
        assert Automation.FAILED == "FAILED"
        assert Automation.FINISHED == "FINISHED"
        assert Automation.TERMINATED == "TERMINATED"


class TestAutomationMethods:
    def test_evaluate_condition_enabled(self):
        cond = _make_condition((True, "triggered"))
        a = _make_automation(condition=cond, enabled=True)
        result = a.evaluate_condition()
        assert result == (True, "triggered")
        cond.evaluate.assert_called_once()

    def test_evaluate_condition_disabled(self):
        cond = _make_condition()
        a = _make_automation(condition=cond, enabled=False)
        result = a.evaluate_condition()
        assert result[0] is False
        assert "disabled" in result[1]
        cond.evaluate.assert_not_called()

    def test_build_condition(self):
        cond = _make_condition()
        a = _make_automation(condition=cond)
        a.build_condition()
        cond.build.assert_called_once()

    def test_enable(self):
        a = _make_automation(enabled=False)
        a.enable()
        assert a.enabled is True

    def test_disable(self):
        a = _make_automation(enabled=True)
        a.disable()
        assert a.enabled is False

    def test_terminate(self):
        a = _make_automation(enabled=True)
        a.terminate()
        assert a.enabled is False
        assert a.status == Automation.TERMINATED

    def test_trigger_actions_disables_non_continuous(self):
        """Non-continuous automation disables itself after actions."""
        attr = BoolAttribute(None, "power", False, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        action = SetAction(None, attr, True)
        a = _make_automation(continuous=False, actions=[action])
        a.trigger_actions()
        assert a.enabled is False

    def test_trigger_actions_stays_enabled_continuous(self):
        attr = BoolAttribute(None, "power", False, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        action = SetAction(None, attr, True)
        a = _make_automation(continuous=True, actions=[action])
        a.trigger_actions()
        assert a.enabled is True

    def test_trigger_actions_triggers_automations(self):
        triggered_auto = MagicMock()
        a = _make_automation(triggers=[triggered_auto])
        a.trigger_actions()
        triggered_auto.enable.assert_called_once()

    def test_trigger_actions_terminates_automations(self):
        terminated_auto = MagicMock()
        a = _make_automation(terminates=[terminated_auto])
        a.trigger_actions()
        terminated_auto.terminate.assert_called_once()

    def test_trigger_actions_with_dict_value(self):
        """Dict values should be converted via to_dict()."""

        class FakeItem:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        dict_val = Dict(None, [FakeItem("k", "v")])
        attr = IntAttribute(None, "data", 0, None, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        action = SetAction(None, attr, dict_val)
        a = _make_automation(actions=[action])
        a.trigger_actions()
        entity.publisher.publish.assert_called_once()

    def test_trigger_actions_with_list_value(self):
        """List values should be converted via print_item()."""
        list_val = List(None, [1, 2, 3])
        attr = IntAttribute(None, "data", 0, None, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        action = SetAction(None, attr, list_val)
        a = _make_automation(actions=[action])
        a.trigger_actions()
        entity.publisher.publish.assert_called_once()

    def test_trigger_actions_groups_by_entity(self):
        """Multiple actions on same entity should be grouped into one message."""
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr1 = IntAttribute(None, "a", 0, None, None)
        attr1.parent = entity
        attr2 = IntAttribute(None, "b", 0, None, None)
        attr2.parent = entity
        action1 = SetAction(None, attr1, 1)
        action2 = SetAction(None, attr2, 2)
        a = _make_automation(actions=[action1, action2])
        a.trigger_actions()
        entity.publisher.publish.assert_called_once()
        call_args = entity.publisher.publish.call_args[0][0]
        assert "a" in call_args
        assert "b" in call_args

    def test_print_info(self, capsys):
        a = _make_automation()
        a.print_info()

    @patch("smauto.lib.automation.time")
    def test_start_checkonce_finishes(self, mock_time):
        sleep_count = 0

        def sleep_side_effect(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count > 1:
                raise RuntimeError("break loop")

        mock_time.sleep.side_effect = sleep_side_effect
        cond = _make_condition((False, "not triggered"))
        a = _make_automation(condition=cond, checkOnce=True, freq=100)
        a.start()
        assert a.status == Automation.FAILED
        assert a.enabled is False

    @patch("smauto.lib.automation.time")
    def test_start_triggered_success(self, mock_time):
        sleep_count = 0

        def sleep_side_effect(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count > 1:
                raise RuntimeError("break loop")

        mock_time.sleep.side_effect = sleep_side_effect
        cond = _make_condition((True, "triggered"))
        attr = BoolAttribute(None, "power", False, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        action = SetAction(None, attr, True)
        a = _make_automation(
            condition=cond,
            actions=[action],
            continuous=True,
            checkOnce=False,
            freq=100,
            delay=0,
        )
        a.start()
        assert a.status == Automation.FAILED
        entity.publisher.publish.assert_called()

    @patch("smauto.lib.automation.time")
    def test_start_with_delay(self, mock_time):
        call_count = 0

        def sleep_side_effect(duration):
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                raise RuntimeError("break loop")

        mock_time.sleep.side_effect = sleep_side_effect
        cond = _make_condition((True, "triggered"))
        a = _make_automation(condition=cond, delay=0.5, checkOnce=True, freq=100)
        a.start()
        assert mock_time.sleep.call_count >= 2


# ── §1.4 Cooldown defaults ──────────────────────────────────────


class TestCooldownDefaults:
    def test_cooldown_default_zero(self):
        a = _make_automation(cooldown=None)
        assert a.cooldown == 0

    def test_cooldown_explicit_value(self):
        a = _make_automation(cooldown=30)
        assert a.cooldown == 30

    def test_cooldown_zero_stays_zero(self):
        a = _make_automation(cooldown=0)
        assert a.cooldown == 0


# ── §1.1 Else branch unit tests ─────────────────────────────────


class TestElseActions:
    def test_else_actions_default_empty(self):
        a = _make_automation(elseActions=None)
        assert a.elseActions == []

    def test_else_actions_stored(self):
        attr = BoolAttribute(None, "power", False, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        else_action = SetAction(None, attr, False)
        a = _make_automation(elseActions=[else_action])
        assert len(a.elseActions) == 1
        assert a.elseActions[0].value is False

    def test_trigger_else_actions_executes(self):
        attr = BoolAttribute(None, "power", False, None)
        entity = MagicMock()
        entity.publisher = MagicMock()
        attr.parent = entity
        else_action = SetAction(None, attr, False)
        a = _make_automation(elseActions=[else_action])
        a.trigger_else_actions()
        entity.publisher.publish.assert_called_once()

    def test_trigger_else_actions_noop_when_empty(self):
        a = _make_automation(elseActions=[])
        a.trigger_else_actions()
