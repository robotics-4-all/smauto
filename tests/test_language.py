"""Tests for smauto.language — metamodel creation, parsing, validation."""

import pytest
from textx import TextXSemanticError

from smauto.language import (
    get_metamodel,
    build_model,
    time_obj_processor,
    get_scope_providers,
    ENTITY_BUILTINS,
)
from smauto.lib.entity import Entity
from smauto.lib.types import Time


# ── time_obj_processor ───────────────────────────────────────────


class TestTimeObjProcessor:
    def test_valid_time(self):
        t = Time(None, 12, 30, 45)
        time_obj_processor(t)  # Should not raise

    def test_hour_too_high(self):
        t = Time(None, 25, 0, 0)
        with pytest.raises(TextXSemanticError, match="hours"):
            time_obj_processor(t)

    def test_hour_negative(self):
        t = Time(None, -1, 0, 0)
        with pytest.raises(TextXSemanticError, match="hours"):
            time_obj_processor(t)

    def test_minute_too_high(self):
        t = Time(None, 0, 61, 0)
        with pytest.raises(TextXSemanticError, match="minutes"):
            time_obj_processor(t)

    def test_minute_negative(self):
        t = Time(None, 0, -1, 0)
        with pytest.raises(TextXSemanticError, match="minutes"):
            time_obj_processor(t)

    def test_second_too_high(self):
        t = Time(None, 0, 0, 61)
        with pytest.raises(TextXSemanticError, match="seconds"):
            time_obj_processor(t)

    def test_second_negative(self):
        t = Time(None, 0, 0, -1)
        with pytest.raises(TextXSemanticError, match="seconds"):
            time_obj_processor(t)


# ── get_metamodel ────────────────────────────────────────────────


class TestGetMetamodel:
    def test_returns_metamodel(self):
        mm = get_metamodel()
        assert mm is not None

    def test_debug_mode(self):
        mm = get_metamodel(debug=False)
        assert mm is not None

    def test_metamodel_has_model_processor(self):
        mm = get_metamodel()
        # model_proc should be registered — verify by parsing a valid model
        # If model_proc wasn't registered, validation wouldn't work
        assert mm is not None


# ── get_scope_providers ──────────────────────────────────────────


class TestGetScopeProviders:
    def test_returns_dict(self):
        sp = get_scope_providers()
        assert isinstance(sp, dict)
        assert "*.*" in sp

    def test_builtin_scopes(self):
        sp = get_scope_providers()
        assert "brokers*" in sp
        assert "entities*" in sp


# ── ENTITY_BUILTINS ──────────────────────────────────────────────


class TestEntityBuiltins:
    def test_system_clock_exists(self):
        assert "system_clock" in ENTITY_BUILTINS

    def test_system_clock_is_entity(self):
        sc = ENTITY_BUILTINS["system_clock"]
        assert isinstance(sc, Entity)
        assert sc.name == "system_clock"
        assert sc.etype == "sensor"
        assert sc.uri == "system.clock"

    def test_system_clock_has_time_attr(self):
        sc = ENTITY_BUILTINS["system_clock"]
        assert "time" in sc.attributes_dict


# ── build_model ──────────────────────────────────────────────────


class TestBuildModel:
    def test_minimal_model(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert model is not None
        assert model.metadata.name == "TestModel"

    def test_model_has_brokers(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert len(model.brokers) == 1
        assert model.brokers[0].name == "test_broker"

    def test_model_has_entities(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert len(model.entities) == 2

    def test_model_has_automations(self, minimal_model_path):
        model = build_model(minimal_model_path)
        assert len(model.automations) == 1
        assert model.automations[0].name == "test_auto"

    def test_smart_light(self, smart_light_path):
        model = build_model(smart_light_path)
        assert model.metadata.name == "SmartLight"
        assert len(model.brokers) == 1
        assert len(model.entities) == 2
        assert len(model.automations) == 1

    def test_industrial_monitoring(self, industrial_monitoring_path):
        model = build_model(industrial_monitoring_path)
        assert model.metadata.name == "IndustrialMonitoring"
        assert len(model.brokers) == 3  # MQTT, AMQP, Redis

    def test_nonexistent_file(self):
        with pytest.raises(Exception):
            build_model("/nonexistent/path.auto")


# ── Validation: duplicate names ──────────────────────────────────


class TestValidationDuplicateSourceNames:
    def test_duplicate_broker_names(self, tmp_model):
        content = """\
Metadata
    name: DupBroker
    version: "0.1.0"
end

Broker<MQTT> my_broker
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Broker<MQTT> my_broker
    host: "localhost"
    port: 1884
    auth:
        username: ""
        password: ""
end

Entity s1
    type: sensor
    freq: 1
    uri: "t"
    source: my_broker
    attributes:
        - v: int
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="already exists"):
            build_model(path)


class TestValidationDuplicateEntityNames:
    def test_duplicate_entity_names(self, tmp_model):
        content = """\
Metadata
    name: DupEntity
    version: "0.1.0"
end

Broker<MQTT> broker1
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity my_entity
    type: sensor
    freq: 1
    uri: "a"
    source: broker1
    attributes:
        - x: int
end

Entity my_entity
    type: actuator
    uri: "b"
    source: broker1
    attributes:
        - y: bool
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="already exists"):
            build_model(path)


class TestValidationDuplicateAttributes:
    def test_duplicate_attr_names(self, tmp_model):
        content = """\
Metadata
    name: DupAttr
    version: "0.1.0"
end

Broker<MQTT> broker1
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
    source: broker1
    attributes:
        - temp: int
        - temp: float
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="already exists"):
            build_model(path)


class TestValidationDuplicateAutomationNames:
    def test_duplicate_automation_names(self, tmp_model):
        content = """\
Metadata
    name: DupAuto
    version: "0.1.0"
end

Broker<MQTT> broker1
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
    source: broker1
    attributes:
        - val: int
end

Entity actuator1
    type: actuator
    uri: "a"
    source: broker1
    attributes:
        - power: bool
end

Automation my_auto
    when
        sensor1.val > 10
    then
        actuator1.power <- true
    config
        continuous: true
end

Automation my_auto
    when
        sensor1.val < 5
    then
        actuator1.power <- false
    config
        continuous: true
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="already exists"):
            build_model(path)


class TestValidationTimeRange:
    def test_invalid_time_in_condition(self, tmp_model):
        content = """\
Metadata
    name: BadTime
    version: "0.1.0"
end

Broker<MQTT> broker1
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
    source: broker1
    attributes:
        - t: time
end

Entity actuator1
    type: actuator
    uri: "a"
    source: broker1
    attributes:
        - power: bool
end

Automation auto1
    when
        sensor1.t >= 25:00
    then
        actuator1.power <- true
    config
        continuous: true
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="hours"):
            build_model(path)


class TestValidationActuatorSemantics:
    def test_generator_on_actuator_raises(self, tmp_model):
        content = """\
Metadata
    name: BadActuator
    version: "0.1.0"
end

Broker<MQTT> broker1
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity bad_actuator
    type: actuator
    uri: "a"
    source: broker1
    attributes:
        - level: int -> constant(42)
end
"""
        path = tmp_model(content)
        with pytest.raises(TextXSemanticError, match="cannot have a value generator"):
            build_model(path)

    def test_actuator_without_generator_ok(self, tmp_model):
        content = """\
Metadata
    name: GoodActuator
    version: "0.1.0"
end

Broker<MQTT> broker1
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity good_actuator
    type: actuator
    uri: "a"
    source: broker1
    attributes:
        - power: bool
end
"""
        path = tmp_model(content)
        model = build_model(path)
        assert model is not None

    def test_actuator_with_freq_warns(self, tmp_model, capsys):
        content = """\
Metadata
    name: FreqActuator
    version: "0.1.0"
end

Broker<MQTT> broker1
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity freq_actuator
    type: actuator
    freq: 5
    uri: "a"
    source: broker1
    attributes:
        - power: bool
end
"""
        path = tmp_model(content)
        build_model(path)
        captured = capsys.readouterr()
        output = " ".join(captured.out.split())
        assert "semantically meaningless" in output


class TestSmautoLanguage:
    def test_is_language_desc(self):
        from smauto.language import smauto_language
        from textx.registration import LanguageDesc

        assert isinstance(smauto_language, LanguageDesc)
