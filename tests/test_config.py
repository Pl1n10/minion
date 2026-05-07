from __future__ import annotations

from pathlib import Path

from minion.config import MinionConfig, load_config, save_config


def test_default_config_roundtrip(tmp_path: Path) -> None:
    cfg = MinionConfig()
    save_config(tmp_path, cfg)
    loaded = load_config(tmp_path)
    assert loaded.version == 1
    assert loaded.teacher.provider == "noop"
    assert loaded.reviewer.provider == "noop"
    assert loaded.backend.preferred == "auto"
    assert ".git/**" in loaded.brief.ignore_globs


def test_load_config_missing_returns_default(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert isinstance(cfg, MinionConfig)
    assert cfg.teacher.provider == "noop"
