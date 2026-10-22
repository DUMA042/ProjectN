"""Data-directory derivation, port truth, and .env typo detection (pure)."""
from __future__ import annotations

from pathlib import Path

from owl.config import Settings, unknown_env_keys


def test_unset_paths_derive_from_flow_data_dir(tmp_path):
    s = Settings(
        flow_data_dir=tmp_path,
        nest_dir=None, inbox_dir=None, report_inbox_dir=None,
    )
    assert s.nest_dir == (tmp_path / "nest").resolve()
    assert s.inbox_dir == (tmp_path / "inbox").resolve()
    assert s.report_inbox_dir == (tmp_path / "report_inbox").resolve()


def test_explicit_paths_win(tmp_path):
    explicit = tmp_path / "custom_nest"
    s = Settings(flow_data_dir=tmp_path / "base", nest_dir=explicit)
    assert s.nest_dir == explicit


def test_development_defaults_resolve_under_project_root():
    s = Settings(flow_data_dir=Path("."), nest_dir=None)
    assert s.flow_data_dir.is_absolute()
    assert s.nest_dir.is_absolute()
    assert s.nest_dir.name == "nest"
    assert s.nest_dir.parent == s.flow_data_dir


def test_env_var_expansion_in_flow_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("MY_FLOW_DATA", str(tmp_path))
    s = Settings(flow_data_dir=Path("%MY_FLOW_DATA%/Flow"))
    assert str(s.flow_data_dir).startswith(str(tmp_path))


def test_api_port_defaults_to_launcher_port():
    assert Settings().api_port == 8001


def test_unknown_env_keys_flags_typo_with_suggestion(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n"
        "DATABASE_URL=postgresql+psycopg2://u:p@localhost:5432/db\n"
        "MAX_FILESIZE_MB=200\n"          # typo (missing underscore)
        "SOMETHING_ELSE=1\n"
        "export API_PORT=8001\n",
        encoding="utf-8",
    )
    unknown = dict(unknown_env_keys(env))
    assert "MAX_FILESIZE_MB" in unknown
    assert unknown["MAX_FILESIZE_MB"] == "MAX_FILE_SIZE_MB"
    assert "SOMETHING_ELSE" in unknown and unknown["SOMETHING_ELSE"] is None
    # Known keys and comments are not reported.
    assert "DATABASE_URL" not in unknown
    assert "API_PORT" not in unknown


def test_unknown_env_keys_missing_file_is_empty(tmp_path):
    assert unknown_env_keys(tmp_path / "absent.env") == []
