"""Tests for smauto.utils — select_clock_broker, make_executable."""

import os
import stat

from smauto.utils import select_clock_broker, make_executable
from smauto.language import build_model


class TestSelectClockBroker:
    def test_selects_first_non_fake(self, smart_light_path):
        model = build_model(smart_light_path)
        broker = select_clock_broker(model)
        assert broker is not None
        assert broker.name != "fake_broker"
        assert broker.name == "home_broker"

    def test_multi_broker_model(self, industrial_monitoring_path):
        model = build_model(industrial_monitoring_path)
        broker = select_clock_broker(model)
        assert broker is not None
        assert broker.name != "fake_broker"
        # Should return the first non-fake broker
        assert broker.name == "factory_mqtt"


class TestMakeExecutable:
    def test_sets_executable(self, tmp_path):
        fpath = tmp_path / "test.py"
        fpath.write_text("#!/usr/bin/env python\nprint('hi')")
        # Remove execute bits first
        os.chmod(str(fpath), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        make_executable(str(fpath))
        assert os.access(str(fpath), os.X_OK)

    def test_preserves_read_write(self, tmp_path):
        fpath = tmp_path / "test.py"
        fpath.write_text("content")
        make_executable(str(fpath))
        new_mode = os.stat(str(fpath)).st_mode
        assert new_mode & stat.S_IRUSR
        assert new_mode & stat.S_IWUSR
