"""Tests for SmAuto grammar — parsing various DSL constructs."""

import pytest
from textx import TextXSemanticError

from smauto.language import build_model
from smauto.lib.broker import MQTTBroker, AMQPBroker, RedisBroker
from smauto.lib.entity import (
    IntAttribute,
    FloatAttribute,
    BoolAttribute,
    StringAttribute,
    TimeAttribute,
)


# ── Parse all example models ────────────────────────────────────


class TestParseExamples:
    """Ensure every shipped example parses without errors."""

    def test_parse_all_examples(self, all_example_paths):
        for path in all_example_paths:
            model = build_model(path)
            assert model is not None
            assert model.metadata is not None


# ── Broker parsing ───────────────────────────────────────────────


class TestBrokerParsing:
    def test_mqtt_broker(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> mqtt_b
    host: "10.0.0.1"
    port: 1883
    ssl: true
    auth:
        username: "user"
        password: "pass"
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: mqtt_b
    attributes:
        - v: int
end
"""
        model = build_model(tmp_model(content))
        broker = model.brokers[0]
        assert isinstance(broker, MQTTBroker)
        assert broker.host == "10.0.0.1"
        assert broker.port == 1883
        assert broker.ssl is True
        assert broker.auth.username == "user"

    def test_amqp_broker(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<AMQP> amqp_b
    host: "amqp.local"
    port: 5672
    vhost: "/prod"
    auth:
        username: "u"
        password: "p"
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: amqp_b
    attributes:
        - v: int
end
"""
        model = build_model(tmp_model(content))
        broker = model.brokers[0]
        assert isinstance(broker, AMQPBroker)
        assert broker.vhost == "/prod"

    def test_redis_broker(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<Redis> redis_b
    host: "redis.local"
    port: 6379
    db: 3
    auth:
        username: ""
        password: "secret"
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: redis_b
    attributes:
        - v: int
end
"""
        model = build_model(tmp_model(content))
        broker = model.brokers[0]
        assert isinstance(broker, RedisBroker)
        assert broker.db == 3


# ── Entity parsing ───────────────────────────────────────────────


class TestEntityParsing:
    def test_sensor_entity(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 5
    uri: "room.sensor"
    source: b
    attributes:
        - temperature: float
        - humidity: int
        - label: str
        - active: bool
end
"""
        model = build_model(tmp_model(content))
        e = model.entities[0]
        assert e.name == "my_sensor"
        assert e.etype == "sensor"
        assert e.freq == 5
        assert e.uri == "room.sensor"
        assert len(e.attributes) == 4

        types_found = {a.name: type(a) for a in e.attributes}
        assert types_found["temperature"] is FloatAttribute
        assert types_found["humidity"] is IntAttribute
        assert types_found["label"] is StringAttribute
        assert types_found["active"] is BoolAttribute

    def test_actuator_entity(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_actuator
    type: actuator
    uri: "room.actuator"
    source: b
    attributes:
        - power: bool
end
"""
        model = build_model(tmp_model(content))
        e = model.entities[0]
        assert e.etype == "actuator"

    def test_time_attribute(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity clock
    type: sensor
    freq: 1
    uri: "sys.clock"
    source: b
    attributes:
        - t: time
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert isinstance(attr, TimeAttribute)

    def test_attribute_defaults(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - count: int = 42
        - temp: float = 36.6
        - active: bool = true
        - label: str = "default"
end
"""
        model = build_model(tmp_model(content))
        attrs = {a.name: a for a in model.entities[0].attributes}
        assert attrs["count"].value == 42
        assert attrs["temp"].value == 36.6
        assert attrs["active"].value is True
        assert attrs["label"].value == "default"


# ── Value generators ─────────────────────────────────────────────


class TestValueGeneratorParsing:
    def test_replay_generator(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - detected: bool -> replay([true, false, true], -1)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.generator is not None
        assert attr.generator.__class__.__name__ == "ReplayFun"

    def test_gaussian_generator_with_noise(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float -> gaussian(20, 40, 2) with noise gaussian(0, 0.5)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.generator.__class__.__name__ == "GaussianFun"
        assert attr.noise.__class__.__name__ == "GaussianNoise"

    def test_constant_generator(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - level: int -> constant(42)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.generator.__class__.__name__ == "ConstantFun"
        assert attr.generator.value == 42

    def test_linear_generator(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float -> linear(20, 0.5)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.generator.__class__.__name__ == "LinearFun"

    def test_saw_generator(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - freq_hz: float -> saw(10, 100, 5)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.generator.__class__.__name__ == "SawFun"

    def test_uniform_noise(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity sensor1
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float -> linear(60, 0.5) with noise uniform(-1, 1)
end
"""
        model = build_model(tmp_model(content))
        attr = model.entities[0].attributes[0]
        assert attr.noise.__class__.__name__ == "UniformNoise"


# ── Automation parsing ───────────────────────────────────────────


class TestAutomationParsing:
    def test_basic_automation(self, minimal_model_path):
        model = build_model(minimal_model_path)
        auto = model.automations[0]
        assert auto.name == "test_auto"
        assert auto.enabled is True
        assert auto.continuous is True
        assert auto.condition is not None
        assert len(auto.actions) == 1

    def test_automation_config(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity a
    type: actuator
    uri: "t2"
    source: b
    attributes:
        - p: bool
end

Automation my_auto
    when
        s.v > 10
    then
        a.p <- true
    config
        freq: 5
        enabled: false
        continuous: false
        checkOnce: true
        delay: 2.5
    end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.freq == 5
        assert auto.enabled is False
        assert auto.continuous is False
        assert auto.checkOnce is True
        assert auto.delay == 2.5


# ── Condition parsing ────────────────────────────────────────────


class TestConditionParsing:
    def test_numeric_condition(self, minimal_model_path):
        model = build_model(minimal_model_path)
        auto = model.automations[0]
        cond = auto.condition
        assert cond is not None
        # Build the condition to generate the lambda
        cond.build()
        assert cond.cond_lambda is not None

    def test_bool_condition(self, smart_light_path):
        model = build_model(smart_light_path)
        auto = model.automations[0]
        cond = auto.condition
        cond.build()
        assert cond.cond_lambda is not None
        assert "==" in cond.cond_lambda or "is" in str(cond.cond_lambda).lower()

    def test_time_condition(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity clock
    type: sensor
    freq: 1
    uri: "sys.clock"
    source: b
    attributes:
        - time: time
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation time_auto
    when
        clock.time >= 08:00
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert auto.condition.cond_lambda is not None
        assert "to_int()" in auto.condition.cond_lambda

    def test_condition_group_and(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - temp: float
        - humidity: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation combined
    when
        (s.temp > 30) AND (s.humidity > 70)
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "and" in auto.condition.cond_lambda

    def test_condition_group_or(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - temp: float
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation or_auto
    when
        (s.temp > 35) OR (s.temp < 5)
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "or" in auto.condition.cond_lambda

    def test_inrange_condition(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - temp: float
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation range_auto
    when
        s.temp in range [20, 30]
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert auto.condition.cond_lambda is not None

    def test_automation_status_condition(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation first_auto
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
end

Automation second_auto
    when
        first_auto.status == SUCCESS
    then
        act.on <- false
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto2 = model.automations[1]
        auto2.condition.build()
        assert "automations" in auto2.condition.cond_lambda
        assert "status" in auto2.condition.cond_lambda

    def test_string_condition(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - status: str
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation str_auto
    when
        s.status == "active"
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert auto.condition.cond_lambda is not None

    def test_mean_aggregation(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - temp: float
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation mean_auto
    when
        mean(s.temp, 10) > 30
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "mean" in auto.condition.cond_lambda


# ── Triggers / Terminates ────────────────────────────────────────


class TestTriggersTerminates:
    def test_triggers_parsed(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation auto_a
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
    triggers
        auto_b
end

Automation auto_b
    when
        s.v < 5
    then
        act.on <- false
    config
        enabled: false
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto_a = model.automations[0]
        assert len(auto_a.triggers) == 1
        assert auto_a.triggers[0].name == "auto_b"


# ── Metadata ─────────────────────────────────────────────────────


class TestMetadata:
    def test_metadata_parsed(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert model.metadata.name == "TestModel"
        assert model.metadata.version == "0.1.0"

    def test_full_metadata(self, smart_light_path):
        model = build_model(smart_light_path)
        assert model.metadata.author == "smauto"
        assert model.metadata.email == "smauto@2023"
        assert model.metadata.description is not None


# ── Action parsing ───────────────────────────────────────────────


class TestActionParsing:
    def test_int_action(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - level: int
end

Automation auto1
    when
        s.v > 10
    then
        act.level <- 100
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.value == 100
        assert action.attribute.name == "level"


# ── §2.1 Action target validation ────────────────────────────────


class TestActionTargetValidation:
    """Verify that actions targeting sensor entities are rejected."""

    def test_action_targeting_sensor_rejected(self, tmp_model):
        """Writing to a sensor attribute must raise TextXSemanticError."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float
end

Entity my_actuator
    type: actuator
    uri: "a"
    source: b
    attributes:
        - level: float
end

Automation bad_auto
    when
        my_sensor.temp > 30
    then
        my_sensor.temp <- 0.0
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="sensor"):
            build_model(tmp_model(content))

    def test_action_targeting_actuator_accepted(self, tmp_model):
        """Writing to an actuator attribute must succeed."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float
end

Entity my_actuator
    type: actuator
    uri: "a"
    source: b
    attributes:
        - level: float
end

Automation good_auto
    when
        my_sensor.temp > 30
    then
        my_actuator.level <- 0.0
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        assert len(model.automations) == 1
        assert model.automations[0].actions[0].attribute.name == "level"

    def test_action_targeting_hybrid_accepted(self, tmp_model):
        """Writing to a hybrid entity attribute must succeed."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float
end

Entity my_hybrid
    type: hybrid
    freq: 1
    uri: "h"
    source: b
    attributes:
        - level: float
end

Automation hybrid_auto
    when
        my_sensor.temp > 30
    then
        my_hybrid.level <- 0.0
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        assert len(model.automations) == 1

    def test_action_targeting_sensor_in_else_rejected(self, tmp_model):
        """Writing to a sensor in else branch must also be rejected."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - temp: float
end

Entity my_actuator
    type: actuator
    uri: "a"
    source: b
    attributes:
        - level: float
end

Automation bad_else_auto
    when
        my_sensor.temp > 30
    then
        my_actuator.level <- 1.0
    else
        my_sensor.temp <- 0.0
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="sensor"):
            build_model(tmp_model(content))


# ── §2.2 AutomationStatusRef validation ─────────────────────────


class TestAutomationStatusRefValidation:
    """Verify that referencing non-existent automations is rejected."""

    def test_nonexistent_automation_ref_rejected(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation my_auto
    when
        ghost_auto.status == SUCCESS
    then
        act.on <- true
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="non-existent"):
            build_model(tmp_model(content))

    def test_existing_automation_ref_accepted(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation first_auto
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
end

Automation second_auto
    when
        first_auto.status == SUCCESS
    then
        act.on <- false
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        assert len(model.automations) == 2


# ── §1.1 Else branch parsing ────────────────────────────────────


class TestElseBranchParsing:
    def test_else_branch_populated(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - temp: float
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
        - level: int
end

Automation else_auto
    when
        s.temp > 30
    then
        act.on <- true
        act.level <- 100
    else
        act.on <- false
        act.level <- 0
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        assert len(auto.elseActions) == 2
        # Verify else actions target correct attributes
        else_attrs = {a.attribute.name for a in auto.elseActions}
        assert "on" in else_attrs
        assert "level" in else_attrs

    def test_no_else_branch_empty(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation no_else_auto
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.elseActions == []


# ── §1.4 Cooldown parsing ───────────────────────────────────────


class TestCooldownParsing:
    def test_cooldown_parsed(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation cooldown_auto
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
        cooldown: 30.0
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.cooldown == 30.0

    def test_cooldown_default_zero(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity s
    type: sensor
    freq: 1
    uri: "t"
    source: b
    attributes:
        - v: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation no_cooldown_auto
    when
        s.v > 10
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.cooldown == 0


# ── §1.3 TimeRangeCondition parsing ─────────────────────────────


class TestTimeRangeConditionParsing:
    def test_normal_time_range(self, tmp_model):
        """Normal range [08:00, 22:00] — uses AND logic."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity clock
    type: sensor
    freq: 1
    uri: "sys.clock"
    source: b
    attributes:
        - time: time
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation time_range_auto
    when
        clock.time in range [08:00, 22:00]
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert auto.condition.cond_lambda is not None
        # Normal range uses AND
        assert "and" in auto.condition.cond_lambda
        assert ">=" in auto.condition.cond_lambda
        assert "<=" in auto.condition.cond_lambda

    def test_midnight_wrap_time_range(self, tmp_model):
        """Midnight wrap [22:00, 06:00] — uses OR logic."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity clock
    type: sensor
    freq: 1
    uri: "sys.clock"
    source: b
    attributes:
        - time: time
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation midnight_auto
    when
        clock.time in range [22:00, 06:00]
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert auto.condition.cond_lambda is not None
        # Midnight wrap uses OR
        assert "or" in auto.condition.cond_lambda
        assert ">=" in auto.condition.cond_lambda
        assert "<=" in auto.condition.cond_lambda


# ── §1.2 ExprSetAction parsing ──────────────────────────────────


class TestExprSetActionParsing:
    def test_expr_action_parsed(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_sensor
    type: sensor
    freq: 1
    uri: "s"
    source: b
    attributes:
        - val: float
end

Entity my_actuator
    type: actuator
    uri: "a"
    source: b
    attributes:
        - level: float
end

Automation expr_auto
    when
        my_sensor.val > 10
    then
        my_actuator.level <- expr(my_sensor.val * 0.8 + 10)
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        action = auto.actions[0]
        assert action.__class__.__name__ == "ExprSetAction"
        assert action.attribute.name == "level"
        # Build the expression
        expr_str = action.build_expr()
        assert expr_str is not None
        assert action.value is not None
        # Should reference the sensor attribute and contain operators
        assert "my_sensor" in expr_str
        assert "val" in expr_str
        assert "*" in expr_str or "+" in expr_str
