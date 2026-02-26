"""Tests for smauto.lib.condition — Condition classes and OPERATORS."""

from smauto.lib.condition import (
    OPERATORS,
    Condition,
    ConditionGroup,
    PrimitiveCondition,
    AdvancedCondition,
    InRangeCondition,
    NumericCondition,
    BoolCondition,
    StringCondition,
    ListCondition,
    DictCondition,
    TimeCondition,
    AutomationStatusRef,
    AutomationStatusCondition,
    PRIMITIVES,
)
from smauto.lib.types import List, Dict, Time


# ── OPERATORS dict ───────────────────────────────────────────────


class TestOperators:
    def test_string_operators(self):
        assert "in" in OPERATORS["~"]("a", "b")
        assert "not in" in OPERATORS["!~"]("a", "b")
        assert "in" in OPERATORS["has"]("a", "b")
        assert "not in" in OPERATORS["has not"]("a", "b")

    def test_comparison_operators(self):
        assert OPERATORS["=="]("a", "b") == "(a == b)"
        assert OPERATORS["!="]("a", "b") == "(a != b)"
        assert OPERATORS["is"]("a", "b") == "(a == b)"
        assert OPERATORS["is not"]("a", "b") == "(a != b)"

    def test_numeric_operators(self):
        assert OPERATORS[">"]("x", "1") == "(x > 1)"
        assert OPERATORS[">="]("x", "1") == "(x >= 1)"
        assert OPERATORS["<"]("x", "1") == "(x < 1)"
        assert OPERATORS["<="]("x", "1") == "(x <= 1)"

    def test_logical_operators(self):
        assert "and" in OPERATORS["AND"]("a", "b")
        assert "or" in OPERATORS["OR"]("a", "b")
        assert "not" in OPERATORS["NOT"]("a", "b")
        assert "^" in OPERATORS["XOR"]("a", "b")

    def test_in_operators(self):
        assert "in" in OPERATORS["in"]("a", "b")
        assert "not in" in OPERATORS["not in"]("a", "b")

    def test_nor_nand_xnor(self):
        r = OPERATORS["NOR"]("a", "b")
        assert "not" in r and "or" in r
        r = OPERATORS["NAND"]("a", "b")
        assert "not" in r and "and" in r
        r = OPERATORS["XNOR"]("a", "b")
        assert "or" in r and "not" in r

    def test_inrange(self):
        r = OPERATORS["InRange"]("x", 0, 100)
        assert "x > 0" in r
        assert "x < 100" in r


# ── PRIMITIVES ───────────────────────────────────────────────────


class TestPrimitives:
    def test_primitives_tuple(self):
        assert int in PRIMITIVES
        assert float in PRIMITIVES
        assert str in PRIMITIVES
        assert bool in PRIMITIVES


# ── Condition.transform_operand ──────────────────────────────────


class TestTransformOperand:
    def test_int(self):
        assert Condition.transform_operand(42) == 42

    def test_float(self):
        assert Condition.transform_operand(3.14) == 3.14

    def test_bool(self):
        assert Condition.transform_operand(True) is True

    def test_string(self):
        assert Condition.transform_operand("hello") == "'hello'"

    def test_list(self):
        lst = List(None, [1, 2])
        result = Condition.transform_operand(lst)
        assert result is lst

    def test_dict(self):
        d = Dict(None, [])
        result = Condition.transform_operand(d)
        assert result is d

    def test_time(self):
        t = Time(None, 10, 30, 0)
        result = Condition.transform_operand(t)
        assert result == t.to_int()


# ── Condition classes ────────────────────────────────────────────


class TestConditionInit:
    def test_condition(self):
        c = Condition(None)
        assert c.parent is None
        assert c.cond_lambda is None
        assert c.cond_raw is None

    def test_condition_group(self):
        r1 = Condition(None)
        r2 = Condition(None)
        cg = ConditionGroup(None, r1, "AND", r2)
        assert cg.r1 is r1
        assert cg.r2 is r2
        assert cg.operator == "AND"

    def test_primitive_condition(self):
        pc = PrimitiveCondition(None)
        assert isinstance(pc, Condition)

    def test_advanced_condition(self):
        ac = AdvancedCondition(None)
        assert isinstance(ac, Condition)


class TestNumericCondition:
    def test_init(self):
        nc = NumericCondition(None, 10, ">", 5)
        assert nc.operand1 == 10
        assert nc.operator == ">"
        assert nc.operand2 == 5
        assert isinstance(nc, PrimitiveCondition)


class TestBoolCondition:
    def test_init(self):
        bc = BoolCondition(None, True, "is", False)
        assert bc.operand1 is True
        assert bc.operator == "is"
        assert bc.operand2 is False


class TestStringCondition:
    def test_init(self):
        sc = StringCondition(None, "hello", "==", "world")
        assert sc.operand1 == "hello"
        assert sc.operator == "=="
        assert sc.operand2 == "world"


class TestListCondition:
    def test_init(self):
        lc = ListCondition(None, [1], "==", [1])
        assert isinstance(lc, PrimitiveCondition)


class TestDictCondition:
    def test_init(self):
        dc = DictCondition(None, {}, "!=", {})
        assert isinstance(dc, PrimitiveCondition)


class TestTimeCondition:
    def test_init(self):
        tc = TimeCondition(None, "op1", ">=", "op2")
        assert tc.operand1 == "op1"
        assert tc.operator == ">="
        assert tc.operand2 == "op2"


class TestInRangeCondition:
    def test_init(self):
        irc = InRangeCondition(None, "attr", 0, 100)
        assert irc.attribute == "attr"
        assert irc.min == 0
        assert irc.max == 100
        assert isinstance(irc, AdvancedCondition)

    def test_process_node_condition(self):
        """InRangeCondition should build a lambda for primitive attribute."""
        irc = InRangeCondition(None, 42, 0, 100)
        irc.process_node_condition()
        assert "42 > 0" in irc.cond_lambda
        assert "42 < 100" in irc.cond_lambda


class TestAutomationStatusRef:
    def test_init(self):
        ref = AutomationStatusRef(None, "my_auto")
        assert ref.automation == "my_auto"
        assert ref.parent is None


class TestAutomationStatusCondition:
    def test_init(self):
        ref = AutomationStatusRef(None, "auto1")
        asc = AutomationStatusCondition(None, ref, "==", "SUCCESS")
        assert asc.operand1 is ref
        assert asc.operator == "=="
        assert asc.operand2 == "SUCCESS"
        assert isinstance(asc, PrimitiveCondition)


class TestConditionEvaluate:
    def test_evaluate_none_lambda(self):
        class FakeParent:
            name = "test_auto"

        c = Condition(FakeParent())
        c.cond_lambda = None
        result, msg = c.evaluate()
        assert result is False
        assert "not built" in msg

    def test_evaluate_empty_lambda(self):
        class FakeParent:
            name = "test_auto"

        c = Condition(FakeParent())
        c.cond_lambda = ""
        result, msg = c.evaluate()
        assert result is False
        assert "not built" in msg

    def test_evaluate_true(self):
        class FakeAttr:
            value = 50

        class FakeEntity:
            attributes_dict = {"temp": FakeAttr()}

        class FakeModel:
            entities_dict = {"sensor1": FakeEntity()}

        class FakeAuto:
            name = "auto1"
            parent = FakeModel()

        c = Condition(FakeAuto())
        c.cond_lambda = "(entities['sensor1'].attributes_dict['temp'].value > 30)"
        result, msg = c.evaluate()
        assert result is True
        assert "triggered" in msg

    def test_evaluate_false(self):
        class FakeAttr:
            value = 10

        class FakeEntity:
            attributes_dict = {"temp": FakeAttr()}

        class FakeModel:
            entities_dict = {"sensor1": FakeEntity()}

        class FakeAuto:
            name = "auto1"
            parent = FakeModel()

        c = Condition(FakeAuto())
        c.cond_lambda = "(entities['sensor1'].attributes_dict['temp'].value > 30)"
        result, msg = c.evaluate()
        assert result is False
        assert "not triggered" in msg

    def test_evaluate_exception(self):
        class FakeModel:
            entities_dict = {}

        class FakeAuto:
            name = "auto1"
            parent = FakeModel()

        c = Condition(FakeAuto())
        c.cond_lambda = "entities['nonexistent'].value > 0"
        result, msg = c.evaluate()
        assert result is False
        assert "not triggered" in msg

    def test_evaluate_with_automations(self):
        class FakeModel:
            entities_dict = {}
            automations_dict = {"auto1": type("FakeAuto", (), {"status": "SUCCESS"})()}

        class FakeAuto:
            name = "auto2"
            parent = FakeModel()

        c = Condition(FakeAuto())
        c.cond_lambda = "(automations['auto1'].status == 'SUCCESS')"
        result, msg = c.evaluate()
        assert result is True
