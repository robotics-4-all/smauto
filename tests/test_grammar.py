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


# ── §5 Constants parsing ────────────────────────────────────────


class TestConstantsParsing:
    CONST_PREAMBLE = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const MAX_TEMP = 30.0
Const COMFORT = 22.0
Const THRESHOLD = 50
Const ENABLED = true
Const MODE = "auto"

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
        - label: str
        - active: bool
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - power: bool
        - level: int
        - setpoint: float
        - mode: str
end
"""

    def test_constants_parsed(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        assert len(model.constants) == 5
        const_dict = {c.name: c.value for c in model.constants}
        assert const_dict["MAX_TEMP"] == 30.0
        assert const_dict["COMFORT"] == 22.0
        assert const_dict["THRESHOLD"] == 50
        assert const_dict["ENABLED"] is True
        assert const_dict["MODE"] == "auto"

    def test_const_in_numeric_condition(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > const(MAX_TEMP)
    then
        act.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "30.0" in auto.condition.cond_lambda

    def test_const_in_bool_condition(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.active is const(ENABLED)
    then
        act.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "True" in auto.condition.cond_lambda

    def test_const_in_string_condition(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.label == const(MODE)
    then
        act.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "auto" in auto.condition.cond_lambda

    def test_const_in_inrange_bounds(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const LOW = 20
Const HIGH = 40

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

Automation a1
    when
        s.temp in range [const(LOW), const(HIGH)]
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "20" in auto.condition.cond_lambda
        assert "40" in auto.condition.cond_lambda

    def test_const_in_float_action(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.setpoint <- const(COMFORT)
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.value == 22.0
        assert action.attribute.name == "setpoint"

    def test_const_in_int_action(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.level <- const(THRESHOLD)
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.value == 50
        assert action.attribute.name == "level"

    def test_const_in_bool_action(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.power <- const(ENABLED)
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.value is True
        assert action.attribute.name == "power"

    def test_const_in_string_action(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.mode <- const(MODE)
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.value == "auto"
        assert action.attribute.name == "mode"

    def test_const_in_else_action(self, tmp_model):
        content = (
            self.CONST_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 10
    then
        act.setpoint <- const(MAX_TEMP)
    else
        act.setpoint <- const(COMFORT)
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.actions[0].value == 30.0
        assert auto.elseActions[0].value == 22.0

    def test_duplicate_const_name_rejected(self, tmp_model):
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const X = 10
Const X = 20

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

Automation a1
    when
        s.v > 0
    then
        act.on <- true
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="already defined"):
            build_model(tmp_model(content))

    def test_undefined_const_in_condition_rejected(self, tmp_model):
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

Automation a1
    when
        s.v > const(NONEXISTENT)
    then
        act.on <- true
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="Undefined constant"):
            build_model(tmp_model(content))

    def test_undefined_const_in_action_rejected(self, tmp_model):
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

Automation a1
    when
        s.v > 0
    then
        act.level <- const(MISSING)
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="Undefined constant"):
            build_model(tmp_model(content))

    def test_no_constants_model_works(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert len(model.constants) == 0

    def test_constants_demo_example(self, constants_demo_path):
        model = build_model(constants_demo_path)
        assert len(model.constants) == 6
        for auto in model.automations:
            auto.condition.build()
            assert auto.condition.cond_lambda is not None


# ── §6 Wait actions ─────────────────────────────────────────────


class TestWaitActionParsing:
    def test_wait_action_parsed(self, tmp_model):
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
        - level: int
end

Automation wait_auto
    when
        s.v > 10
    then
        act.on <- true
        wait 5
        act.level <- 100
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 3
        assert auto.actions[0].__class__.__name__ != "WaitAction"
        assert auto.actions[1].__class__.__name__ == "WaitAction"
        assert auto.actions[1].duration == 5
        assert auto.actions[2].__class__.__name__ != "WaitAction"

    def test_wait_action_float_duration(self, tmp_model):
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

Automation wait_float
    when
        s.v > 10
    then
        act.on <- true
        wait 2.5
        act.on <- false
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        wait = model.automations[0].actions[1]
        assert wait.duration == 2.5

    def test_wait_in_else_block(self, tmp_model):
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
        - level: int
end

Automation wait_else
    when
        s.v > 10
    then
        act.on <- true
    else
        act.on <- false
        wait 3
        act.level <- 0
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.elseActions) == 3
        assert auto.elseActions[1].__class__.__name__ == "WaitAction"
        assert auto.elseActions[1].duration == 3

    def test_multiple_waits(self, tmp_model):
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
        - level: int
end

Automation multi_wait
    when
        s.v > 10
    then
        act.on <- true
        wait 1
        act.level <- 50
        wait 2
        act.level <- 100
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 5
        waits = [a for a in auto.actions if a.__class__.__name__ == "WaitAction"]
        assert len(waits) == 2
        assert waits[0].duration == 1
        assert waits[1].duration == 2


# ── §11 Log actions ─────────────────────────────────────────────


class TestLogActionParsing:
    def test_log_action_parsed(self, tmp_model):
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

Automation log_auto
    when
        s.v > 10
    then
        log "Temperature threshold exceeded"
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        log_action = auto.actions[0]
        assert log_action.__class__.__name__ == "LogAction"
        assert log_action.message == "Temperature threshold exceeded"
        assert log_action.level == "INFO"

    def test_log_action_with_level(self, tmp_model):
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

Automation log_warn
    when
        s.v > 10
    then
        log "Critical temperature" level WARNING
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        log_action = model.automations[0].actions[0]
        assert log_action.level == "WARNING"

    def test_log_in_else_block(self, tmp_model):
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

Automation log_else
    when
        s.v > 10
    then
        act.on <- true
    else
        log "Condition not met, standing down"
        act.on <- false
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert auto.elseActions[0].__class__.__name__ == "LogAction"
        assert auto.elseActions[0].message == "Condition not met, standing down"

    def test_log_with_wait_interleaved(self, tmp_model):
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

Automation log_wait_combo
    when
        s.v > 10
    then
        log "Phase 1 starting"
        act.on <- true
        wait 5
        log "Phase 2 starting" level DEBUG
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 4
        classes = [a.__class__.__name__ for a in auto.actions]
        assert classes == ["LogAction", "BoolSetAction", "WaitAction", "LogAction"]
        assert auto.actions[3].level == "DEBUG"


# ── §9 Multi-error validation ───────────────────────────────────


class TestMultiErrorValidation:
    def test_multiple_errors_collected(self, tmp_model):
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

Entity s
    type: sensor
    freq: 1
    uri: "t2"
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

Automation a1
    when
        s.temp > 30
    then
        act.on <- true
    config
        continuous: true
end

Automation a1
    when
        s.temp > 10
    then
        act.on <- false
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="2 validation error"):
            build_model(tmp_model(content))

    def test_constants_demo_scenes_expanded(self, constants_demo_path):
        """Verify the constants demo example properly expands scenes."""
        model = build_model(constants_demo_path)
        # Model should have 2 scenes defined
        assert len(model.scenes) == 2
        scene_names = {s.name for s in model.scenes}
        assert "emergency_shutdown" in scene_names
        assert "comfort_mode" in scene_names
        # emergency_trigger uses apply emergency_shutdown — should be expanded
        emergency_auto = next(a for a in model.automations if a.name == "emergency_trigger")
        # emergency_shutdown has 4 actions: 3 set + 1 log
        assert len(emergency_auto.actions) == 4
        # restore_comfort uses apply in both then and else
        restore_auto = next(a for a in model.automations if a.name == "restore_comfort")
        # comfort_mode has 3 actions
        assert len(restore_auto.actions) == 3
        # else uses emergency_shutdown with 4 actions
        assert len(restore_auto.elseActions) == 4

    def test_single_error_still_reports(self, tmp_model):
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

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end

Automation bad
    when
        my_sensor.temp > 30
    then
        my_sensor.temp <- 0.0
    config
        continuous: true
end
"""
        with pytest.raises(TextXSemanticError, match="1 validation error"):
            build_model(tmp_model(content))


# ── §4 Scenes ───────────────────────────────────────────────────


class TestSceneParsing:
    SCENE_PREAMBLE = """\
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
        - mode: str
end
"""

    def test_scene_parsed(self, tmp_model):
        """A scene definition is parsed and stored on the model."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene my_scene
    act.on <- true
    act.level <- 100
end

Automation a1
    when
        s.temp > 30
    then
        act.on <- false
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        assert len(model.scenes) == 1
        assert model.scenes[0].name == "my_scene"
        assert len(model.scenes[0].actions) == 2

    def test_apply_scene_expanded(self, tmp_model):
        """apply in then block inlines the scene actions."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene activate
    act.on <- true
    act.level <- 100
end

Automation a1
    when
        s.temp > 30
    then
        apply activate
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        # apply should be replaced by 2 inlined actions
        assert len(auto.actions) == 2
        assert auto.actions[0].attribute.name == "on"
        assert auto.actions[1].attribute.name == "level"

    def test_apply_scene_in_else(self, tmp_model):
        """apply in else block inlines the scene actions."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene deactivate
    act.on <- false
    act.level <- 0
end

Automation a1
    when
        s.temp > 30
    then
        act.on <- true
    else
        apply deactivate
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.elseActions) == 2
        assert auto.elseActions[0].value is False
        assert auto.elseActions[1].value == 0

    def test_scene_with_wait_and_log(self, tmp_model):
        """Scenes can contain wait and log actions."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene startup_sequence
    log "Starting up"
    act.on <- true
    wait 3
    act.level <- 100
    log "Startup complete" level INFO
end

Automation a1
    when
        s.temp > 30
    then
        apply startup_sequence
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 5
        classes = [a.__class__.__name__ for a in auto.actions]
        assert classes == [
            "LogAction",
            "BoolSetAction",
            "WaitAction",
            "IntSetAction",
            "LogAction",
        ]

    def test_multiple_scenes(self, tmp_model):
        """Multiple scenes can be defined and applied independently."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene on_preset
    act.on <- true
    act.level <- 100
end

Scene off_preset
    act.on <- false
    act.level <- 0
end

Automation a1
    when
        s.temp > 30
    then
        apply on_preset
    else
        apply off_preset
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        assert len(model.scenes) == 2
        auto = model.automations[0]
        assert len(auto.actions) == 2
        assert auto.actions[0].value is True
        assert len(auto.elseActions) == 2
        assert auto.elseActions[0].value is False

    def test_scene_with_const(self, tmp_model):
        """Scenes can use const() references which are resolved after expansion."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const TARGET_LEVEL = 75

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
        - level: int
        - on: bool
end

Scene set_target
    act.on <- true
    act.level <- const(TARGET_LEVEL)
end

Automation a1
    when
        s.temp > 30
    then
        apply set_target
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        assert auto.actions[1].value == 75

    def test_undefined_scene_rejected(self, tmp_model):
        """Applying a non-existent scene raises an error."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Automation a1
    when
        s.temp > 30
    then
        apply ghost_scene
    config
        continuous: true
end
"""
        )
        with pytest.raises(TextXSemanticError, match="Undefined scene"):
            build_model(tmp_model(content))

    def test_duplicate_scene_name_rejected(self, tmp_model):
        """Two scenes with the same name raises a validation error."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene dup
    act.on <- true
end

Scene dup
    act.on <- false
end

Automation a1
    when
        s.temp > 30
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        with pytest.raises(TextXSemanticError, match="already defined"):
            build_model(tmp_model(content))

    def test_no_scenes_model_works(self, minimal_model_path):
        """Models without scenes still work fine."""
        model = build_model(minimal_model_path)
        assert len(model.scenes) == 0

    def test_scene_mixed_with_direct_actions(self, tmp_model):
        """apply can be mixed with direct actions in the same then block."""
        content = (
            self.SCENE_PREAMBLE
            + """\
Scene preset
    act.level <- 50
end

Automation a1
    when
        s.temp > 30
    then
        act.on <- true
        apply preset
        act.mode <- "auto"
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        # on=true + level=50 (from scene) + mode="auto"
        assert len(auto.actions) == 3
        assert auto.actions[0].value is True
        assert auto.actions[1].value == 50
        assert auto.actions[2].value == "auto"


# ── §7 Hysteresis/Deadband conditions ──────────────────────────


class TestHysteresisDeadband:
    DEADBAND_PREAMBLE = """\
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
        - level: int
end
"""

    def test_deadband_parsed(self, tmp_model):
        """Deadband modifier is parsed and stored on NumericCondition."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_auto
    when
        s.temp > 30 deadband 2
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        cond = auto.condition
        assert cond.deadband == 2

    def test_deadband_float(self, tmp_model):
        """Deadband can be a float value."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_auto
    when
        s.temp > 30 deadband 1.5
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.deadband == 1.5

    def test_no_deadband_default_zero(self, tmp_model):
        """Without deadband modifier, deadband is 0."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation no_db
    when
        s.temp > 30
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.deadband == 0

    def test_deadband_gt_generates_deactivate(self, tmp_model):
        """'> T deadband D' generates deactivation expression '< T-D'."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_gt
    when
        s.temp > 30 deadband 2
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        # Activation: temp > 30
        assert "30" in cond.cond_lambda
        assert ">" in cond.cond_lambda
        # Deactivation: temp < 28 (30 - 2)
        assert cond.cond_deactivate is not None
        assert "28" in str(cond.cond_deactivate)
        assert "<" in cond.cond_deactivate

    def test_deadband_lt_generates_deactivate(self, tmp_model):
        """'< T deadband D' generates deactivation expression '> T+D'."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_lt
    when
        s.temp < 20 deadband 3
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        assert cond.cond_deactivate is not None
        # Deactivation: temp > 23 (20 + 3)
        assert "23" in str(cond.cond_deactivate)
        assert ">" in cond.cond_deactivate

    def test_deadband_gte_generates_deactivate(self, tmp_model):
        """'>= T deadband D' generates deactivation expression '< T-D'."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_gte
    when
        s.temp >= 30 deadband 5
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        assert cond.cond_deactivate is not None
        assert "25" in str(cond.cond_deactivate)

    def test_deadband_lte_generates_deactivate(self, tmp_model):
        """'<= T deadband D' generates deactivation expression '> T+D'."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_lte
    when
        s.temp <= 20 deadband 4
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        assert cond.cond_deactivate is not None
        assert "24" in str(cond.cond_deactivate)

    def test_deadband_eq_no_deactivate(self, tmp_model):
        """'== T deadband D' — no deactivation (== not supported for hysteresis)."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_eq
    when
        s.temp == 30 deadband 2
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        # == has no hysteresis semantics — deadband is stored but no deactivation
        assert cond.deadband == 2
        assert cond.cond_deactivate is None

    def test_deadband_in_compound_condition(self, tmp_model):
        """Deadband works in compound conditions with AND/OR."""
        content = (
            self.DEADBAND_PREAMBLE
            + """\
Automation db_compound
    when
        (s.temp > 30 deadband 2) AND (s.humidity > 60)
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        # Top-level condition group should have propagated deactivation
        assert cond.cond_deactivate is not None
        # The deactivation expression should contain the deadband threshold
        assert "28" in str(cond.cond_deactivate)

    def test_deadband_with_const(self, tmp_model):
        """Deadband works with const() threshold values."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const MAX_TEMP = 30.0

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

Automation db_const
    when
        s.temp > const(MAX_TEMP) deadband 2
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        assert cond.deadband == 2
        assert cond.cond_deactivate is not None
        # const(MAX_TEMP) resolved to 30.0, deadband 2 → deactivate at < 28.0
        assert "28" in str(cond.cond_deactivate)


# ── §1 Duration-based conditions (for modifier) ────────────────


class TestDurationCondition:
    DURATION_PREAMBLE = """\
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
        - level: int
end
"""

    def test_for_modifier_parsed(self, tmp_model):
        """'for N' modifier is parsed and stored on NumericCondition."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation dur_auto
    when
        s.temp > 30 for 10
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.forDuration == 10

    def test_for_modifier_float(self, tmp_model):
        """'for' can accept float duration."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation dur_float
    when
        s.temp > 30 for 5.5
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.forDuration == 5.5

    def test_no_for_default_zero(self, tmp_model):
        """Without for modifier, forDuration is 0."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation no_dur
    when
        s.temp > 30
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.forDuration == 0

    def test_for_with_deadband(self, tmp_model):
        """'deadband' and 'for' can be combined."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation dur_db
    when
        s.temp > 30 deadband 2 for 10
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.deadband == 2
        assert cond.forDuration == 10
        cond.build()
        assert cond.cond_deactivate is not None

    def test_for_builds_normally(self, tmp_model):
        """'for' modifier doesn't change the condition expression."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation dur_build
    when
        s.temp > 30 for 5
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        assert cond.cond_lambda is not None
        assert "30" in cond.cond_lambda
        assert ">" in cond.cond_lambda

    def test_for_in_compound_condition(self, tmp_model):
        """'for' modifier propagates through compound conditions."""
        content = (
            self.DURATION_PREAMBLE
            + """\
Automation dur_compound
    when
        (s.temp > 30 for 10) AND (s.humidity > 60)
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        cond.build()
        # forDuration should propagate to top-level (max of children)
        assert cond.forDuration == 10

    def test_for_with_const(self, tmp_model):
        """'for' modifier works with const() thresholds."""
        content = """\
Metadata
    name: Test
    version: "0.1.0"
end

Const MAX_TEMP = 30.0

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

Automation dur_const
    when
        s.temp > const(MAX_TEMP) for 15
    then
        act.on <- true
    config
        continuous: true
end
"""
        model = build_model(tmp_model(content))
        cond = model.automations[0].condition
        assert cond.forDuration == 15
        cond.build()
        assert "30.0" in cond.cond_lambda


# ── §3 Entity Groups ───────────────────────────────────────────


class TestEntityGroups:
    GROUP_PREAMBLE = """\
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

Entity light1
    type: actuator
    uri: "l1"
    source: b
    attributes:
        - power: bool
        - brightness: int
end

Entity light2
    type: actuator
    uri: "l2"
    source: b
    attributes:
        - power: bool
        - brightness: int
end
"""

    def test_group_parsed(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        light1.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        assert len(model.groups) == 1
        assert model.groups[0].name == "all_lights"
        assert len(model.groups[0].members) == 2
        member_names = {m.name for m in model.groups[0].members}
        assert member_names == {"light1", "light2"}

    def test_group_set_action_expanded(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        set all_lights.power <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        targets = {a.attribute.parent.name for a in auto.actions}
        assert targets == {"light1", "light2"}
        assert all(a.value is True for a in auto.actions)

    def test_group_set_int_value(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        set all_lights.brightness <- 100
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        assert all(a.value == 100 for a in auto.actions)

    def test_group_in_else_block(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        set all_lights.power <- true
    else
        set all_lights.power <- false
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 2
        assert len(auto.elseActions) == 2
        assert all(a.value is True for a in auto.actions)
        assert all(a.value is False for a in auto.elseActions)

    def test_group_mixed_with_direct_actions(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        set all_lights.power <- true
        light1.brightness <- 50
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        # 2 from group + 1 direct
        assert len(auto.actions) == 3

    def test_no_groups_works(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert len(model.groups) == 0

    def test_group_missing_attr_rejected(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group all_lights
    light1, light2
end

Automation a1
    when
        s.temp > 30
    then
        set all_lights.nonexistent <- true
    config
        continuous: true
end
"""
        )
        with pytest.raises(TextXSemanticError, match="has no attribute"):
            build_model(tmp_model(content))

    def test_duplicate_group_name_rejected(self, tmp_model):
        content = (
            self.GROUP_PREAMBLE
            + """\
Group g1
    light1
end

Group g1
    light2
end

Automation a1
    when
        s.temp > 30
    then
        light1.power <- true
    config
        continuous: true
end
"""
        )
        with pytest.raises(TextXSemanticError, match="already defined"):
            build_model(tmp_model(content))


# ── §2 Rate-of-change conditions (delta/rate) ──────────────────


class TestRateOfChangeConditions:
    ROC_PREAMBLE = """\
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
        - pressure: int
end

Entity act
    type: actuator
    uri: "a"
    source: b
    attributes:
        - on: bool
end
"""

    def test_delta_parsed(self, tmp_model):
        """delta() condition is parsed correctly."""
        content = (
            self.ROC_PREAMBLE
            + """\
Automation delta_auto
    when
        delta(s.temp, 5) > 10
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "delta" in auto.condition.cond_lambda

    def test_rate_parsed(self, tmp_model):
        """rate() condition is parsed correctly."""
        content = (
            self.ROC_PREAMBLE
            + """\
Automation rate_auto
    when
        rate(s.temp, 10) > 2.0
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "rate" in auto.condition.cond_lambda

    def test_delta_initializes_buffer(self, tmp_model):
        """delta() should initialize attribute buffer like other aggregate functions."""
        content = (
            self.ROC_PREAMBLE
            + """\
Automation delta_buf
    when
        delta(s.temp, 8) > 5
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        # Check that the entity has buffer initialized
        sensor = model.entities[0]
        assert len(sensor.attr_buffs) > 0
        buf_names = [name for name, size in sensor.attr_buffs]
        assert "temp" in buf_names

    def test_rate_in_compound_condition(self, tmp_model):
        """rate() works in compound conditions."""
        content = (
            self.ROC_PREAMBLE
            + """\
Automation rate_compound
    when
        (rate(s.temp, 10) > 2.0) AND (s.temp > 25)
    then
        act.on <- true
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        auto.condition.build()
        assert "rate" in auto.condition.cond_lambda
        assert "and" in auto.condition.cond_lambda

    def test_delta_and_rate_together(self, tmp_model):
        """delta() and rate() can both be used in the same model."""
        content = (
            self.ROC_PREAMBLE
            + """\
Automation delta_auto
    when
        delta(s.temp, 5) > 10
    then
        act.on <- true
    config
        continuous: true
end

Automation rate_auto
    when
        rate(s.pressure, 10) > 3
    then
        act.on <- false
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        assert len(model.automations) == 2
        for auto in model.automations:
            auto.condition.build()
            assert auto.condition.cond_lambda is not None

    def test_delta_function_logic(self):
        """Unit test for the delta computation."""
        from smauto.lib.condition import Condition

        assert Condition._delta([1, 2, 3, 4, 5]) == 4  # 5 - 1
        assert Condition._delta([10, 5]) == -5  # 5 - 10
        assert Condition._delta([]) == 0
        assert Condition._delta([42]) == 0  # Need at least 2 values

    def test_rate_function_logic(self):
        """Unit test for the rate computation."""
        from smauto.lib.condition import Condition

        # 5 values: delta=4, steps=4, rate=1.0
        assert Condition._rate([1, 2, 3, 4, 5]) == 1.0
        assert Condition._rate([10, 5]) == -5.0  # delta=-5, steps=1
        assert Condition._rate([]) == 0
        assert Condition._rate([42]) == 0


class TestHttpActionParsing:
    """Tests for HttpAction (webhook) parsing."""

    PREAMBLE = """\
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
        - level: int
end

"""

    def test_http_get_minimal(self, tmp_model):
        """GET with only URL and end."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http GET "https://example.com/ping"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 1
        action = auto.actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "GET"
        assert action.url == "https://example.com/ping"
        assert action.headers == []
        assert action.body == ""
        assert action.timeout == 10

    def test_http_post_with_body(self, tmp_model):
        """POST with body only."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http POST "https://example.com/alert"
            body: "alert=true"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "POST"
        assert action.url == "https://example.com/alert"
        assert action.body == "alert=true"
        assert action.headers == []

    def test_http_post_with_headers(self, tmp_model):
        """POST with headers only."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http POST "https://example.com/webhook"
            headers:
                - "Content-Type" = "application/json"
                - "X-Api-Key" = "secret123"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "POST"
        assert len(action.headers) == 2
        assert action.headers[0].key == "Content-Type"
        assert action.headers[0].value == "application/json"
        assert action.headers[1].key == "X-Api-Key"
        assert action.headers[1].value == "secret123"
        assert action.body == ""

    def test_http_post_full(self, tmp_model):
        """POST with headers, body, and timeout (all three)."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http POST "https://example.com/notify"
            headers:
                - "Authorization" = "Bearer tok"
            body: "event=threshold_exceeded"
            timeout: 30
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "POST"
        assert action.url == "https://example.com/notify"
        assert len(action.headers) == 1
        assert action.headers[0].key == "Authorization"
        assert action.headers[0].value == "Bearer tok"
        assert action.body == "event=threshold_exceeded"
        assert action.timeout == 30

    def test_http_put_method(self, tmp_model):
        """PUT method works."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http PUT "https://example.com/state"
            body: "status=active"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "PUT"
        assert action.url == "https://example.com/state"
        assert action.body == "status=active"

    def test_http_delete_method(self, tmp_model):
        """DELETE method works."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http DELETE "https://example.com/resource/42"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.__class__.__name__ == "HttpAction"
        assert action.method == "DELETE"
        assert action.url == "https://example.com/resource/42"

    def test_http_default_timeout(self, tmp_model):
        """Timeout defaults to 10 when not specified."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        http POST "https://example.com/data"
            body: "payload=test"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        action = model.automations[0].actions[0]
        assert action.timeout == 10

    def test_http_action_in_else_block(self, tmp_model):
        """HttpAction in else block."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        act.on <- true
    else
        http POST "https://example.com/fallback"
            body: "status=normal"
        end
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 1
        assert auto.actions[0].__class__.__name__ != "HttpAction"
        assert len(auto.elseActions) == 1
        else_action = auto.elseActions[0]
        assert else_action.__class__.__name__ == "HttpAction"
        assert else_action.method == "POST"
        assert else_action.body == "status=normal"

    def test_http_mixed_with_regular_actions(self, tmp_model):
        """HttpAction mixed with SetAction and LogAction."""
        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        act.on <- true
        log "Threshold exceeded"
        http POST "https://example.com/webhook"
            body: "alert=threshold"
        end
        act.level <- 100
    config
        continuous: true
end
"""
        )
        model = build_model(tmp_model(content))
        auto = model.automations[0]
        assert len(auto.actions) == 4
        assert auto.actions[0].__class__.__name__ != "HttpAction"
        assert auto.actions[1].__class__.__name__ == "LogAction"
        assert auto.actions[2].__class__.__name__ == "HttpAction"
        assert auto.actions[2].body == "alert=threshold"
        assert auto.actions[3].__class__.__name__ != "HttpAction"

    def test_http_codegen(self, tmp_model):
        """HttpAction appears in generated code."""
        from smauto.transformations.smauto_m2t import smauto_m2t

        content = (
            self.PREAMBLE
            + """\
Automation http_auto
    when
        s.v > 10
    then
        act.on <- true
        http POST "https://example.com/notify"
            headers:
                - "Content-Type" = "text/plain"
            body: "triggered=true"
            timeout: 15
        end
    config
        continuous: true
end
"""
        )
        code = smauto_m2t(tmp_model(content))
        assert "HttpAction" in code
        assert "https://example.com/notify" in code
        assert "Content-Type" in code
        assert "triggered=true" in code
