"""Shared fixtures for SmAuto DSL test suite."""

import pathlib
import pytest

# Project root
ROOT = pathlib.Path(__file__).parent.parent.resolve()
EXAMPLES_DIR = ROOT / "examples"


def _example_path(name: str) -> str:
    """Return absolute path to an example model file."""
    return str(EXAMPLES_DIR / name / "model.auto")


@pytest.fixture
def smart_light_path():
    """Path to the simplest example model."""
    return _example_path("01_smart_light")


@pytest.fixture
def smart_thermostat_path():
    return _example_path("02_smart_thermostat")


@pytest.fixture
def home_security_path():
    return _example_path("03_home_security")


@pytest.fixture
def smart_greenhouse_path():
    return _example_path("04_smart_greenhouse")


@pytest.fixture
def industrial_monitoring_path():
    """Path to the most feature-complete example (MQTT, AMQP, Redis)."""
    return _example_path("05_industrial_monitoring")


@pytest.fixture
def smart_building_path():
    return _example_path("06_smart_building")


@pytest.fixture
def startup_sequence_path():
    """Path to example with heavy automation coordination."""
    return _example_path("07_startup_sequence")


@pytest.fixture
def energy_management_path():
    return _example_path("08_energy_management")


@pytest.fixture
def smart_hvac_path():
    """Path to example showcasing else, cooldown, time ranges, and expressions."""
    return _example_path("09_smart_hvac")


@pytest.fixture
def constants_demo_path():
    """Path to example showcasing model-level constants."""
    return _example_path("10_constants_demo")


@pytest.fixture
def entity_groups_path():
    """Path to example showcasing entity groups."""
    return _example_path("11_entity_groups")


@pytest.fixture
def webhook_actions_path():
    """Path to example showcasing webhook/HTTP actions."""
    return _example_path("12_webhook_actions")


@pytest.fixture
def all_example_paths():
    """All example model paths."""
    return [
        _example_path(f"{i:02d}_{name}")
        for i, name in [
            (1, "smart_light"),
            (2, "smart_thermostat"),
            (3, "home_security"),
            (4, "smart_greenhouse"),
            (5, "industrial_monitoring"),
            (6, "smart_building"),
            (7, "startup_sequence"),
            (8, "energy_management"),
            (9, "smart_hvac"),
            (10, "constants_demo"),
            (11, "entity_groups"),
            (12, "webhook_actions"),
        ]
    ]


@pytest.fixture
def tmp_model(tmp_path):
    """Factory fixture to write a temporary .auto model file and return its path."""

    def _write(content: str, filename: str = "test_model.auto") -> str:
        fpath = tmp_path / filename
        fpath.write_text(content)
        return str(fpath)

    return _write


# Minimal valid model string for quick tests
MINIMAL_MODEL = """\
Metadata
    name: TestModel
    version: "0.1.0"
end

Broker<MQTT> test_broker
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end

Entity test_sensor
    type: sensor
    freq: 1
    uri: "test.sensor"
    source: test_broker
    attributes:
        - temperature: float
end

Entity test_actuator
    type: actuator
    uri: "test.actuator"
    source: test_broker
    attributes:
        - power: bool
end

Automation test_auto
    when
        test_sensor.temperature > 30
    then
        test_actuator.power <- true
    config
        enabled: true
        continuous: true
end
"""


@pytest.fixture
def minimal_model_path(tmp_model):
    """Write and return path to a minimal valid model."""
    return tmp_model(MINIMAL_MODEL)


@pytest.fixture
def minimal_model(minimal_model_path):
    """Parse and return a minimal model object."""
    from smauto.language import build_model

    return build_model(minimal_model_path)
