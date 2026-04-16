from __future__ import annotations

from unittest.mock import MagicMock

from zenve_services.filesystem import FilesystemService


def make_service() -> FilesystemService:
    settings = MagicMock()
    return FilesystemService(settings)


def test_read_agent_files_returns_text_files(tmp_path):
    (tmp_path / "SOUL.md").write_text("soul content")
    (tmp_path / "notes.txt").write_text("some notes")

    svc = make_service()
    result = svc.read_agent_files(str(tmp_path))

    paths = {item["path"] for item in result}
    assert paths == {"SOUL.md", "notes.txt"}
    contents = {item["path"]: item["content"] for item in result}
    assert contents["SOUL.md"] == "soul content"
    assert contents["notes.txt"] == "some notes"


def test_read_agent_files_excludes_dirs(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "run1.json").write_text('{"status": "ok"}')
    (tmp_path / "SOUL.md").write_text("soul content")

    svc = make_service()
    result = svc.read_agent_files(str(tmp_path), exclude_dirs=["runs"])

    paths = {item["path"] for item in result}
    assert paths == {"SOUL.md"}


def test_read_agent_files_skips_binary_files(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
    (tmp_path / "readme.md").write_text("hello")

    svc = make_service()
    result = svc.read_agent_files(str(tmp_path))

    paths = {item["path"] for item in result}
    assert paths == {"readme.md"}


def test_read_agent_files_empty_dir(tmp_path):
    svc = make_service()
    result = svc.read_agent_files(str(tmp_path))

    assert result == []
