"""A narrower read must not discard unchanged whole-file knowledge."""

import hashlib
import json
import os
from types import SimpleNamespace

import pytest

from tools.file_tools import clear_file_ops_cache
from tools.file_tools_read_tracking import _file_version
from tools.registry import registry


def _call(name, path, task_id, **arguments):
    result = registry.dispatch(name, {"path": str(path), **arguments}, task_id=task_id)
    assert isinstance(result, str)
    return json.loads(result)


@pytest.mark.parametrize("encoding,bom,original,patched,final", [
    ("utf-8", b"\xef\xbb\xbf", "Málaga 東京 before\r\n", "Málaga 東京 after\r\n", "Málaga 東京 final\r\n"),
    ("utf-16-le", b"\xff\xfe", "Málaga 東京 before\r\n", "Málaga 東京 after\r\n", "Málaga 東京 final\r\n"),
    ("utf-16-be", b"\xfe\xff", "Málaga 東京 before\r\n", "Málaga 東京 after\r\n", "Málaga 東京 final\r\n"),
    ("utf-8", b"", "plain before\r\n", "plain after\r\n", "plain final\r\n"),
])
def test_full_read_patch_reread_allows_write_for_text(tmp_path, encoding, bom, original, patched, final):
    """Full reads around a patch authorize a later whole-file write."""
    task = f"bom-write-baseline-{encoding}"
    path = tmp_path / "encoded.txt"
    path.write_bytes(bom + original.encode(encoding))
    try:
        assert "error" not in _call("read_file", path, task)
        patch_result = _call("patch", path, task, old_string="before", new_string="after")
        assert patch_result.get("success") is True, patch_result
        assert path.read_bytes() == bom + patched.encode(encoding)
        reread = _call("read_file", path, task)
        assert "error" not in reread
        written = _call("write_file", path, task, content=final.replace("\r\n", "\n"))
        assert "error" not in written, written.get("error")
        assert path.read_bytes() == bom + final.encode(encoding)
    finally:
        clear_file_ops_cache(task)


def test_file_version_ignores_only_handle_ctime_mismatch(tmp_path, monkeypatch):
    """Path ctime remains stable while Windows fstat may expose a divergent ctime."""
    path = tmp_path / "snapshot.txt"
    content = b"stable bytes\r\n"
    path.write_bytes(content)
    original_fstat = os.fstat

    def divergent_ctime(fd):
        result = original_fstat(fd)
        return SimpleNamespace(**{
            name: getattr(result, name) + (1 if name == "st_ctime_ns" else 0)
            for name in ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        })

    monkeypatch.setattr(os, "fstat", divergent_ctime)
    version = _file_version(str(path))
    assert version is not None
    st = path.stat()
    assert version[:-1] == (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    assert version[-1] == hashlib.sha256(content).digest()


@pytest.mark.parametrize("changed_field", ["st_dev", "st_ino", "st_size", "st_mtime_ns"])
def test_file_version_rejects_handle_metadata_change_during_hash(tmp_path, monkeypatch, changed_field):
    path = tmp_path / "changed-handle-snapshot.txt"
    path.write_bytes(b"stable before\n")
    original_fstat = os.fstat
    calls = 0

    def changed_second_handle_stat(fd):
        nonlocal calls
        result = original_fstat(fd)
        calls += 1
        if calls == 2:
            return SimpleNamespace(**{
                name: getattr(result, name) + (1 if name == changed_field else 0)
                for name in ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            })
        return result

    monkeypatch.setattr(os, "fstat", changed_second_handle_stat)
    assert _file_version(str(path)) is None


@pytest.mark.parametrize("changed_field", [
    "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns",
])
def test_file_version_rejects_path_metadata_change_during_hash(tmp_path, monkeypatch, changed_field):
    path = tmp_path / "changed-during-snapshot.txt"
    path.write_bytes(b"stable before\n")
    original_stat = os.stat
    calls = 0

    def changed_second_path_stat(resolved, *args, **kwargs):
        nonlocal calls
        result = original_stat(resolved, *args, **kwargs)
        if os.fspath(resolved) == str(path):
            calls += 1
            if calls == 2:
                return SimpleNamespace(**{
                    name: getattr(result, name) + (1 if name == changed_field else 0)
                    for name in ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
                })
        return result

    monkeypatch.setattr(os, "stat", changed_second_path_stat)
    assert _file_version(str(path)) is None


def test_external_same_mtime_content_change_still_blocks_write(tmp_path):
    path = tmp_path / "externally-changed.txt"
    task = "external-full-baseline"
    original = "before---\n"
    path.write_text(original, encoding="utf-8")
    try:
        assert "error" not in _call("read_file", path, task)
        stamp = path.stat()
        path.write_text("changed--\n", encoding="utf-8")
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        refused = _call("write_file", path, task, content="replacement\n")
        assert refused.get("stale_write_blocked"), refused
        assert path.read_text(encoding="utf-8") == "changed--\n"
    finally:
        clear_file_ops_cache(task)


def test_full_read_then_write_plain_ascii(tmp_path):
    path = tmp_path / "plain.txt"
    task = "plain-full-read-write"
    path.write_bytes(b"plain original\r\n")
    try:
        assert "error" not in _call("read_file", path, task)
        written = _call("write_file", path, task, content="plain replacement\n")
        assert "error" not in written, written.get("error")
        assert path.read_bytes() == b"plain replacement\r\n"
    finally:
        clear_file_ops_cache(task)


def test_partial_reread_keeps_an_unchanged_full_read_or_write(tmp_path):
    original = "first\nsecond\nthird\n"
    for source in ("read", "write", "pages"):
        task = f"known-{source}"
        path = tmp_path / f"{source}.txt"
        try:
            if source == "write":
                assert "error" not in _call("write_file", path, task, content=original)
            else:
                path.write_text(original, encoding="utf-8")
                if source == "pages":
                    for offset in (1, 2, 3):
                        assert "error" not in _call("read_file", path, task, offset=offset, limit=1)
                else:
                    assert "error" not in _call("read_file", path, task)
            assert "error" not in _call("read_file", path, task, offset=2, limit=2)
            written = _call("write_file", path, task, content="replacement\n")
            assert "error" not in written, (source, written)
            assert path.read_text(encoding="utf-8") == "replacement\n"
        finally:
            clear_file_ops_cache(task)


def test_partial_read_cannot_refresh_a_changed_full_baseline(tmp_path):
    original = "first\nsecond\nthird\n"
    for source in ("write", "pages"):
        path = tmp_path / f"changed-{source}.txt"
        task = f"snapshot-{source}"
        try:
            if source == "write":
                assert "error" not in _call("write_file", path, task, content=original)
            else:
                path.write_text(original, encoding="utf-8")
                assert "error" not in _call("read_file", path, task, offset=1, limit=1)
            stamp = path.stat()
            path.write_text("other\nsecond\nthird\n", encoding="utf-8")
            # mtime alone cannot identify bytes: editors/copy tools can preserve it.
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            assert "error" not in _call("read_file", path, task, offset=2, limit=2)
            refused = _call("write_file", path, task, content="replacement\n")
            assert refused.get("stale_write_blocked"), (source, refused)
            assert path.read_text(encoding="utf-8") == "other\nsecond\nthird\n"
            # Reading all of the new version is recovery, not a bypass.
            assert "error" not in _call("read_file", path, task)
            assert "error" not in _call("write_file", path, task, content="merged\n")
            assert path.read_text(encoding="utf-8") == "merged\n"
        finally:
            clear_file_ops_cache(task)

    # A page that hides part of a line never supplies whole-file knowledge.
    from tools.tool_output_limits import get_max_line_length

    path = tmp_path / "clamped.txt"
    path.write_text("x" * (get_max_line_length() + 10) + "\nlast\n", encoding="utf-8")
    try:
        assert "error" not in _call("read_file", path, "clamped")
        refused = _call("write_file", path, "clamped", content="replacement\n")
        assert refused.get("stale_write_blocked"), refused
        assert path.read_text(encoding="utf-8").startswith("x" * (get_max_line_length() + 10))
    finally:
        clear_file_ops_cache("clamped")
