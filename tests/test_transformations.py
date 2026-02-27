"""Tests for smauto.transformations — code generation (M2T)."""

import os
import pytest

from smauto.transformations.smauto_m2t import (
    smauto_m2t,
    rtm_set_defaults,
    write_to_file,
)
from smauto.transformations.entity_to_code import (
    model_to_vnodes,
    build_entity_code,
)
from smauto.transformations.ventities_merged import (
    model_to_vent,
)
from smauto.transformations.generators import (
    _write,
)
from smauto.utils import inject_system_clock
from smauto.language import build_model


# ── smauto_m2t ───────────────────────────────────────────────────


class TestSmautoM2T:
    def test_generates_code(self, smart_light_path):
        code = smauto_m2t(smart_light_path)
        assert isinstance(code, str)
        assert len(code) > 0
        assert "Automation" in code
        assert "Entity" in code

    def test_generates_code_with_outdir(self, smart_light_path, tmp_path):
        smauto_m2t(smart_light_path, outdir=str(tmp_path))
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "SmartLight.py"
        # File should be executable
        assert os.access(str(files[0]), os.X_OK)

    def test_includes_broker_params(self, smart_light_path):
        code = smauto_m2t(smart_light_path)
        assert "ConnectionParameters" in code
        assert "localhost" in code

    def test_includes_condition_expression(self, smart_light_path):
        code = smauto_m2t(smart_light_path)
        assert "Condition" in code

    def test_includes_entity_classes(self, smart_light_path):
        code = smauto_m2t(smart_light_path)
        assert "MotionSensorMsg" in code
        assert "BedroomLightMsg" in code

    def test_no_automations_raises(self, tmp_model):
        content = """\
Metadata
    name: NoAuto
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
"""
        path = tmp_model(content)
        with pytest.raises(ValueError, match="does not include any Automations"):
            smauto_m2t(path)

    def test_industrial_monitoring(self, industrial_monitoring_path):
        """Multi-broker model should generate code for all broker types."""
        code = smauto_m2t(industrial_monitoring_path)
        assert "mqtt" in code.lower() or "MQTT" in code
        assert "amqp" in code.lower() or "AMQP" in code
        assert "redis" in code.lower() or "Redis" in code

    def test_all_examples_generate(self, all_example_paths):
        """Every example with automations should generate code."""
        for path in all_example_paths:
            model = build_model(path)
            if len(model.automations) > 0:
                code = smauto_m2t(path)
                assert len(code) > 0


# ── rtm_set_defaults ─────────────────────────────────────────────


class TestRtmSetDefaults:
    def test_no_monitor(self):
        """Model without monitor should not raise."""

        class FakeModel:
            monitor = None

        rtm_set_defaults(FakeModel())

    def test_no_monitor_attr(self):
        """Model without monitor attr should not raise."""

        class FakeModel:
            pass

        rtm_set_defaults(FakeModel())

    def test_sets_defaults(self):

        class FakeMonitor:
            ns = None
            eTopic = None
            lTopic = None

        class FakeModel:
            monitor = FakeMonitor()

        rtm_set_defaults(FakeModel())
        assert FakeModel.monitor.ns == "smauto"
        assert FakeModel.monitor.eTopic == "events"
        assert FakeModel.monitor.lTopic == "logs"

    def test_preserves_custom(self):

        class FakeMonitor:
            ns = "custom"
            eTopic = "my_events"
            lTopic = "my_logs"

        class FakeModel:
            monitor = FakeMonitor()

        rtm_set_defaults(FakeModel())
        assert FakeModel.monitor.ns == "custom"
        assert FakeModel.monitor.eTopic == "my_events"
        assert FakeModel.monitor.lTopic == "my_logs"


# ── write_to_file ────────────────────────────────────────────────


class TestWriteToFile:
    def test_writes_and_makes_executable(self, tmp_path):
        fpath = str(tmp_path / "test.py")
        write_to_file("#!/usr/bin/env python\nprint('hi')", fpath)
        assert os.path.exists(fpath)
        assert os.access(fpath, os.X_OK)
        with open(fpath) as f:
            assert "print" in f.read()


# ── entity_to_code ───────────────────────────────────────────────


class TestEntityToCode:
    def test_model_to_vnodes(self, smart_light_path):
        vnodes = model_to_vnodes(smart_light_path)
        assert len(vnodes) > 0
        for entity, code in vnodes:
            assert isinstance(code, str)
            assert len(code) > 0

    def test_build_entity_code_sensor(self, smart_light_path):
        model = build_model(smart_light_path)
        sensor = [e for e in model.entities if e.etype == "sensor"][0]
        code = build_entity_code(sensor)
        assert "Node" in code
        assert sensor.camel_name in code

    def test_build_entity_code_actuator(self, smart_light_path):
        model = build_model(smart_light_path)
        actuator = [e for e in model.entities if e.etype == "actuator"][0]
        code = build_entity_code(actuator)
        assert "Node" in code
        assert actuator.camel_name in code

    def test_build_entity_code_unsupported(self):
        """Unknown entity type should raise NotImplementedError."""
        from smauto.lib.entity import Entity, IntAttribute
        from smauto.lib.broker import MQTTBroker

        broker = MQTTBroker(None, "b", "localhost", 1883, None)
        e = Entity(
            None, "x", "unknown_type", 1, "u", broker, [IntAttribute(None, "v", 0, None, None)]
        )
        with pytest.raises(NotImplementedError):
            build_entity_code(e)


# ── ventities_merged ─────────────────────────────────────────────


class TestEntityToCodeHybrid:
    def test_build_entity_code_hybrid(self, tmp_model):
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

Entity my_hybrid
    type: hybrid
    freq: 1
    uri: "h"
    source: b
    attributes:
        - temp: float
        - power: bool
end
"""
        path = tmp_model(content)
        model = build_model(path)
        entity = model.entities[0]
        assert entity.etype == "hybrid"
        code = build_entity_code(entity)
        assert entity.camel_name in code

    def test_hybrid_has_publisher_and_subscriber(self, tmp_model):
        """Hybrid codegen should produce both pub (sensor) and sub (actuator) code."""
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

Entity hvac_unit
    type: hybrid
    freq: 2
    uri: "building.hvac"
    source: b
    attributes:
        - temperature: float -> gaussian(22, 35, 5)
        - power: bool
        - setpoint: float
end
"""
        path = tmp_model(content)
        model = build_model(path)
        entity = model.entities[0]
        code = build_entity_code(entity)
        # Should have publisher (sensor side)
        assert "create_publisher" in code
        # Should have subscriber (actuator side)
        assert "create_subscriber" in code
        assert "_on_message" in code
        # Should have value generator components
        assert "init_gen_components" in code
        assert "ValueGenerator" in code

    def test_hybrid_with_generators_and_noise(self, tmp_model):
        """Hybrid entity with generators and noise should generate complete code."""
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

Entity smart_valve
    type: hybrid
    freq: 1
    uri: "pipe.valve"
    source: b
    attributes:
        - flow_rate: float -> linear(0, 0.5) with noise uniform(-0.1, 0.1)
        - position: int
end
"""
        path = tmp_model(content)
        model = build_model(path)
        entity = model.entities[0]
        code = build_entity_code(entity)
        assert "SmartValve" in code
        assert "ValueGeneratorType.Linear" in code
        assert "NoiseType.Uniform" in code

    def test_hybrid_in_automation_codegen(self, tmp_model):
        """Hybrid entities should work in automation codegen (both condition and action)."""
        content = """\
Metadata
    name: HybridTest
    version: "0.1.0"
end

Broker<MQTT> b
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity temp_sensor
    type: sensor
    freq: 1
    uri: "room.temp"
    source: b
    attributes:
        - temperature: float -> constant(25)
end

Entity smart_ac
    type: hybrid
    freq: 1
    uri: "room.ac"
    source: b
    attributes:
        - current_temp: float -> gaussian(22, 30, 3)
        - power: bool
        - mode: str
end

Automation ac_control
    when
        smart_ac.current_temp > 28
    then
        smart_ac.power <- true
        smart_ac.mode <- "cooling"
    config
        continuous: true
end
"""
        code = smauto_m2t(tmp_model(content))
        assert "SmartAcMsg" in code
        assert "'power'" in code or "power" in code

    def test_hybrid_merged_codegen(self, tmp_model):
        """Hybrid entities should appear in merged ventities codegen."""
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
    uri: "s1"
    source: b
    attributes:
        - v: int -> constant(10)
end

Entity hybrid1
    type: hybrid
    freq: 1
    uri: "h1"
    source: b
    attributes:
        - reading: float -> saw(0, 100, 1)
        - command: int
end

Entity actuator1
    type: actuator
    uri: "a1"
    source: b
    attributes:
        - on: bool
end
"""
        code = model_to_vent(tmp_model(content))
        # All three entity types should appear
        assert "Sensor1" in code
        assert "Hybrid1" in code
        assert "Actuator1" in code
        # Hybrid should have both pub and sub
        assert "create_publisher" in code
        assert "create_subscriber" in code


class TestVentitiesMerged:
    def test_model_to_vent(self, smart_light_path):
        code = model_to_vent(smart_light_path)
        assert isinstance(code, str)
        assert len(code) > 0


# ── generators module ────────────────────────────────────────────


class TestGeneratorsModule:
    def testinject_system_clock(self, smart_light_path):
        model = build_model(smart_light_path)
        ent = inject_system_clock(model)
        assert ent is not None
        assert ent.name == "system_clock"
        assert hasattr(model, "system_clock")

    def testinject_system_clock_idempotent(self, smart_light_path):
        model = build_model(smart_light_path)
        inject_system_clock(model)
        count_before = len(model.entities)
        inject_system_clock(model)
        assert len(model.entities) == count_before

    def test_write_helper(self, tmp_path):
        fpath = str(tmp_path / "out.py")
        _write("print('hello')", fpath)
        assert os.path.exists(fpath)
        assert os.access(fpath, os.X_OK)

    def test_gen_automations(self, smart_light_path, tmp_path):
        from smauto.transformations import generators
        from smauto.language import get_metamodel

        metamodel = get_metamodel()
        model = metamodel.model_from_file(smart_light_path)
        gen_fn = generators.smauto_gen_automations.generator
        gen_fn(metamodel, model, str(tmp_path), True, False)
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) == 1

    def test_gen_automations_no_automations(self, tmp_model, tmp_path):
        content = """\
Metadata
    name: NoAuto
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
"""
        from smauto.transformations import generators
        from smauto.language import get_metamodel

        path = tmp_model(content)
        metamodel = get_metamodel()
        model = metamodel.model_from_file(path)
        gen_fn = generators.smauto_gen_automations.generator
        gen_fn(metamodel, model, str(tmp_path), True, False)
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) == 0

    def test_gen_ventities(self, smart_light_path, tmp_path):
        from smauto.transformations import generators
        from smauto.language import get_metamodel

        metamodel = get_metamodel()
        model = metamodel.model_from_file(smart_light_path)
        gen_fn = generators.smauto_gen_ventities.generator
        gen_fn(metamodel, model, str(tmp_path), True, False)
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) > 0

    def test_gen_ventities_merged(self, smart_light_path, tmp_path):
        from smauto.transformations import generators
        from smauto.language import get_metamodel

        metamodel = get_metamodel()
        model = metamodel.model_from_file(smart_light_path)
        gen_fn = generators.smauto_gen_ventities_merged.generator
        gen_fn(metamodel, model, str(tmp_path), True, False)
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) == 1
