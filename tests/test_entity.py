"""Tests for smauto.lib.entity — Entity and Attribute classes."""

from smauto.lib.entity import (
    Entity,
    Attribute,
    IntAttribute,
    FloatAttribute,
    StringAttribute,
    BoolAttribute,
    TimeAttribute,
    ListAttribute,
    DictAttribute,
)
from smauto.lib.broker import MQTTBroker, EntitySource
from smauto.lib.types import Time


# ── Attribute classes ────────────────────────────────────────────


class TestAttribute:
    def test_init(self):
        a = Attribute(None, "temp", 25.0)
        assert a.name == "temp"
        assert a.value == 25.0
        assert a.parent is None

    def test_init_default_none(self):
        a = Attribute(None, "x")
        assert a.value is None


class TestIntAttribute:
    def test_default_zero(self):
        a = IntAttribute(None, "count", None, None, None)
        assert a.value == 0
        assert a.type == "int"
        assert a.generator is None
        assert a.noise is None

    def test_explicit_default(self):
        a = IntAttribute(None, "count", 42, None, None)
        assert a.value == 42


class TestFloatAttribute:
    def test_default_zero(self):
        a = FloatAttribute(None, "temp", None, None, None)
        assert a.value == 0.0
        assert a.type == "float"

    def test_explicit_default(self):
        a = FloatAttribute(None, "temp", 36.6, None, None)
        assert a.value == 36.6


class TestStringAttribute:
    def test_default_empty(self):
        a = StringAttribute(None, "label", None)
        assert a.value == ""
        assert a.type == "str"

    def test_explicit_default(self):
        a = StringAttribute(None, "label", "hello")
        assert a.value == "hello"


class TestBoolAttribute:
    def test_default_false(self):
        a = BoolAttribute(None, "active", None, None)
        assert a.value is False
        assert a.type == "bool"

    def test_explicit_default(self):
        a = BoolAttribute(None, "active", True, None)
        assert a.value is True


class TestTimeAttribute:
    def test_default_zero_time(self):
        a = TimeAttribute(None, "t", None)
        assert a.type == "time"
        assert isinstance(a.value, Time)
        assert a.value.hour == 0
        assert a.value.minute == 0
        assert a.value.second == 0

    def test_explicit_default(self):
        t = Time(None, 14, 30, 0)
        a = TimeAttribute(None, "t", t)
        assert a.value.hour == 14


class TestListAttribute:
    def test_default_empty(self):
        a = ListAttribute(None, "items", None, None)
        assert a.value == []
        assert a.type == "list"

    def test_explicit_default(self):
        a = ListAttribute(None, "items", [1, 2, 3], None)
        assert a.value == [1, 2, 3]


class TestDictAttribute:
    def test_init(self):
        item1 = IntAttribute(None, "x", 1, None, None)
        item2 = IntAttribute(None, "y", 2, None, None)
        a = DictAttribute(None, "coords", [item1, item2], None)
        assert a.type == "dict"
        assert "x" in a.value
        assert "y" in a.value
        assert a.items == [item1, item2]

    def test_empty_items(self):
        a = DictAttribute(None, "empty", [], None)
        assert a.value == {}
        assert a.items == []


# ── Entity class ─────────────────────────────────────────────────


def _make_entity(name="test", etype="sensor", freq=1, attrs=None, source=None):
    """Helper to create an Entity with minimal boilerplate."""
    if source is None:
        source = MQTTBroker(None, "b", "localhost", 1883, None)
    if attrs is None:
        attrs = [IntAttribute(None, "val", 0, None, None)]
    return Entity(None, name, etype, freq, "test.uri", source, attrs)


class TestEntity:
    def test_basic_init(self):
        broker = MQTTBroker(None, "broker", "localhost", 1883, None)
        attr = IntAttribute(None, "temp", 0, None, None)
        e = Entity(None, "sensor1", "sensor", 2, "room.temp", broker, [attr])
        assert e.name == "sensor1"
        assert e.etype == "sensor"
        assert e.freq == 2
        assert e.uri == "room.temp"
        assert e.source is broker
        assert "temp" in e.attributes_dict
        assert e.camel_name == "Sensor1"

    def test_freq_defaults(self):
        e = _make_entity(freq=None)
        assert e.freq == 1

        e = _make_entity(freq=0)
        assert e.freq == 1

    def test_source_unwrap_entity_source(self):
        broker = MQTTBroker(None, "b", "localhost", 1883, None)
        es = EntitySource(None, broker)
        e = _make_entity(source=es)
        assert e.source is broker

    def test_source_no_unwrap(self):
        broker = MQTTBroker(None, "b", "localhost", 1883, None)
        e = _make_entity(source=broker)
        assert e.source is broker

    def test_to_camel_case(self):
        e = _make_entity(name="my_cool_sensor")
        assert e.camel_name == "MyCoolSensor"
        assert e.to_camel_case("hello_world") == "HelloWorld"

    def test_attributes_dict(self):
        a1 = IntAttribute(None, "x", 1, None, None)
        a2 = FloatAttribute(None, "y", 2.0, None, None)
        e = _make_entity(attrs=[a1, a2])
        assert set(e.attributes_dict.keys()) == {"x", "y"}
        assert e.attributes_dict["x"] is a1

    def test_attributes_buff_initialized(self):
        a = IntAttribute(None, "val", 0, None, None)
        e = _make_entity(attrs=[a])
        assert "val" in e.attributes_buff
        assert e.attributes_buff["val"] is None

    def test_init_attr_buffer(self):
        e = _make_entity()
        e.init_attr_buffer("val", 5)
        assert e.attributes_buff["val"].maxlen == 5

    def test_get_buffer_empty(self):
        e = _make_entity()
        e.init_attr_buffer("val", 3)
        result = e.get_buffer("val")
        assert result == [0, 0, 0]

    def test_get_buffer_full(self):
        e = _make_entity()
        e.init_attr_buffer("val", 3)
        e.attributes_buff["val"].append(10)
        e.attributes_buff["val"].append(20)
        e.attributes_buff["val"].append(30)
        result = e.get_buffer("val")
        assert list(result) == [10, 20, 30]

    def test_dict_attribute_items_dict(self):
        """DictAttribute items should get items_dict created."""
        inner1 = IntAttribute(None, "a", 0, None, None)
        inner2 = IntAttribute(None, "b", 0, None, None)
        da = DictAttribute(None, "data", [inner1, inner2], None)
        e = _make_entity(attrs=[da])
        # items_dict should be populated by Entity.__init__
        assert hasattr(e.attributes_dict["data"], "items_dict")
        assert "a" in e.attributes_dict["data"].items_dict

    def test_update_attributes_basic(self):
        a = IntAttribute(None, "val", 0, None, None)
        e = _make_entity(attrs=[a])
        Entity.update_attributes(e.attributes_dict, {"val": 42})
        assert e.attributes_dict["val"].value == 42

    def test_update_attributes_time(self):
        a = TimeAttribute(None, "t", None)
        e = _make_entity(attrs=[a])
        Entity.update_attributes(
            e.attributes_dict,
            {"t": {"hour": 10, "minute": 30, "second": 0}},
        )
        assert e.attributes_dict["t"].value.hour == 10
        assert e.attributes_dict["t"].value.minute == 30

    def test_update_state(self):
        a = IntAttribute(None, "val", 0, None, None)
        e = _make_entity(attrs=[a])
        e.init_attr_buffer("val", 5)
        e.update_state({"val": 99})
        assert e.state == {"val": 99}
        assert e.attributes_dict["val"].value == 99

    def test_update_buffers(self):
        e = _make_entity()
        e.init_attr_buffer("val", 3)
        Entity.update_buffers(e.attributes_buff, {"val": 7})
        assert 7 in e.attributes_buff["val"]

    def test_update_buffers_none_skipped(self):
        """Buffers that are None should be skipped."""
        e = _make_entity()
        # attributes_buff["val"] is None by default
        Entity.update_buffers(e.attributes_buff, {"val": 7})
        # Should not raise — None buffer skips append

    def test_description_default(self):
        e = _make_entity()
        assert e.description == ""

    def test_update_attributes_dict_nested(self):
        inner = IntAttribute(None, "x", 0, None, None)
        da = DictAttribute(None, "data", [inner], None)
        e = _make_entity(attrs=[da])
        Entity.update_attributes(
            e.attributes_dict,
            {"data": {"x": 42}},
        )
        assert e.attributes_dict["data"].value["x"].value == 42
