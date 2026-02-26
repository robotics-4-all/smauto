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
