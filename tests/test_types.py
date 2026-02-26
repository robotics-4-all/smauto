"""Tests for smauto.lib.types — List, Dict, Time, Date."""

from smauto.lib.types import List, Dict, Time, Date


class TestTime:
    def test_init_defaults(self):
        t = Time(None, None, None, None)
        assert t.hour == 0
        assert t.minute == 0
        assert t.second == 0

    def test_init_values(self):
        t = Time(None, 14, 30, 45)
        assert t.hour == 14
        assert t.minute == 30
        assert t.second == 45

    def test_to_int(self):
        t = Time(None, 1, 2, 3)
        # second + (minute << 8) + (hour << 16)
        expected = 3 + (2 << 8) + (1 << 16)
        assert t.to_int() == expected

    def test_to_int_zero(self):
        t = Time(None, 0, 0, 0)
        assert t.to_int() == 0

    def test_to_int_max_like(self):
        t = Time(None, 23, 59, 59)
        expected = 59 + (59 << 8) + (23 << 16)
        assert t.to_int() == expected


class TestDate:
    def test_init(self):
        d = Date(None, 12, 25, 2023)
        assert d.month == 12
        assert d.day == 25
        assert d.year == 2023
        assert d.parent is None


class TestList:
    def test_empty(self):
        lst = List(None, [])
        assert lst.items == []
        assert repr(lst) == "[]"

    def test_primitives(self):
        lst = List(None, [1, 2, 3])
        assert List.print_item(lst) == [1, 2, 3]

    def test_nested(self):
        inner = List(None, [4, 5])
        outer = List(None, [1, inner, 3])
        result = List.print_item(outer)
        assert result == [1, [4, 5], 3]

    def test_repr(self):
        lst = List(None, [1, 2])
        assert repr(lst) == "[1, 2]"

    def test_print_item_primitive(self):
        assert List.print_item(42) == 42
        assert List.print_item("hello") == "hello"


class TestDict:
    def test_empty(self):

        class FakeItem:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        d = Dict(None, [])
        assert d.items == []

    def test_repr(self):

        class FakeItem:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        items = [FakeItem("a", 1), FakeItem("b", 2)]
        d = Dict(None, items)
        result = repr(d)
        assert "'a':1" in result
        assert "'b':2" in result
        assert result.startswith("{")
        assert result.endswith("}")

    def test_to_dict(self):

        class FakeItem:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        items = [FakeItem("x", 10), FakeItem("y", 20)]
        d = Dict(None, items)
        assert d.to_dict() == {"x": 10, "y": 20}

    def test_print_item_with_list(self):
        inner = List(None, [1, 2])
        result = Dict.print_item(inner)
        assert result == [1, 2]

    def test_print_item_primitive(self):
        assert Dict.print_item(42) == 42
        assert Dict.print_item("hello") == "hello"

    def test_repr_with_list_value(self):

        class FakeItem:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        lst = List(None, [1, 2])
        items = [FakeItem("data", lst)]
        d = Dict(None, items)
        result = repr(d)
        assert "'data':[1, 2]" in result
