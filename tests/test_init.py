"""Tests for smauto package init."""

import smauto


class TestPackageInit:
    def test_version(self):
        assert smauto.__version__ == "0.1.0"

    def test_exports_smauto_language(self):
        assert hasattr(smauto, "smauto_language")
        assert smauto.smauto_language is not None

    def test_exports_get_metamodel(self):
        assert hasattr(smauto, "get_metamodel")
        assert callable(smauto.get_metamodel)
