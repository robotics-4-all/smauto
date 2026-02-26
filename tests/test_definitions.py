"""Tests for smauto.definitions — path constants."""

import os
from smauto.definitions import THIS_DIR, TEMPLATES_PATH, BUILTIN_MODELS, MODEL_REPO_PATH


class TestDefinitions:
    def test_this_dir_exists(self):
        assert os.path.isdir(THIS_DIR)

    def test_templates_path_exists(self):
        assert os.path.isdir(TEMPLATES_PATH)

    def test_builtin_models_exists(self):
        assert os.path.isdir(BUILTIN_MODELS)

    def test_templates_has_jinja_files(self):
        files = os.listdir(TEMPLATES_PATH)
        jinja_files = [f for f in files if f.endswith(".jinja")]
        assert len(jinja_files) > 0

    def test_builtin_models_has_broker(self):
        broker_dir = os.path.join(BUILTIN_MODELS, "broker")
        assert os.path.isdir(broker_dir)
        assert "fake_broker.br" in os.listdir(broker_dir)

    def test_builtin_models_has_entity(self):
        entity_dir = os.path.join(BUILTIN_MODELS, "entity")
        assert os.path.isdir(entity_dir)
        assert "system_clock.ent" in os.listdir(entity_dir)

    def test_model_repo_path_default_none(self):
        # By default (no env var), should be None
        # Only test if env var is not set
        if "SMAUTO_MODEL_REPO" not in os.environ:
            assert MODEL_REPO_PATH is None
