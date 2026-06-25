"""Tests for smauto.cli — CLI commands."""

import os
import pytest
from click.testing import CliRunner

from smauto.cli.cli import cli, _build_mermaid
from smauto.language import build_model


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIValidate:
    def test_validate_success(self, runner, smart_light_path):
        result = runner.invoke(cli, ["validate", smart_light_path])
        assert result.exit_code == 0
        assert "success" in result.output.lower()

    def test_validate_minimal(self, runner, minimal_model_path):
        result = runner.invoke(cli, ["validate", minimal_model_path])
        assert result.exit_code == 0

    def test_validate_nonexistent_file(self, runner):
        result = runner.invoke(cli, ["validate", "/nonexistent/path.auto"])
        assert result.exit_code != 0

    def test_validate_all_examples(self, runner, all_example_paths):
        for path in all_example_paths:
            result = runner.invoke(cli, ["validate", path])
            assert result.exit_code == 0, f"Failed for {path}: {result.output}"


class TestCLIGen:
    def test_gen_creates_file(self, runner, smart_light_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["gen", smart_light_path])
        assert result.exit_code == 0
        assert "Compiled" in result.output
        # Should create SmartLight.py
        assert (tmp_path / "SmartLight.py").exists()
        assert os.access(str(tmp_path / "SmartLight.py"), os.X_OK)


class TestCLIGenv:
    def test_genv_creates_files(self, runner, smart_light_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["genv", smart_light_path])
        assert result.exit_code == 0
        # Should create per-entity files
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) > 0

    def test_genv_merged(self, runner, smart_light_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["genv", "--merged", smart_light_path])
        assert result.exit_code == 0
        assert "Compiled" in result.output
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) == 1  # Single merged file

    def test_genv_merged_short_flag(self, runner, smart_light_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["genv", "-m", smart_light_path])
        assert result.exit_code == 0


class TestCLIHelp:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_validate_help(self, runner):
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0

    def test_gen_help(self, runner):
        result = runner.invoke(cli, ["gen", "--help"])
        assert result.exit_code == 0

    def test_genv_help(self, runner):
        result = runner.invoke(cli, ["genv", "--help"])
        assert result.exit_code == 0


class TestCLIGraph:
    def test_graph_command_runs(self, runner, smart_light_path):
        result = runner.invoke(cli, ["graph", smart_light_path])
        assert result.exit_code == 0
        assert "graph TD" in result.output

    def test_graph_output_to_file(self, runner, smart_light_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        outfile = str(tmp_path / "diagram.mmd")
        result = runner.invoke(cli, ["graph", smart_light_path, "-o", outfile])
        assert result.exit_code == 0
        assert (tmp_path / "diagram.mmd").exists()
        content = (tmp_path / "diagram.mmd").read_text()
        assert "graph TD" in content

    def test_build_mermaid_contains_nodes(self, smart_light_path):
        model = build_model(smart_light_path)
        mermaid = _build_mermaid(model)
        assert "graph TD" in mermaid
        assert "home_broker" in mermaid
        assert "motion_sensor" in mermaid
        assert "bedroom_light" in mermaid
        assert "turn_on_light" in mermaid

    def test_build_mermaid_contains_edges(self, smart_light_path):
        model = build_model(smart_light_path)
        mermaid = _build_mermaid(model)
        assert "--->" in mermaid or "-.->|" in mermaid
        assert "bedroom.motion" in mermaid or "bedroom.light" in mermaid

    def test_build_mermaid_with_triggers(self, tmp_model):
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
        mermaid = _build_mermaid(model)
        assert "auto_a" in mermaid
        assert "auto_b" in mermaid
        assert "triggers" in mermaid


class TestMain:
    def test_main_callable(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
