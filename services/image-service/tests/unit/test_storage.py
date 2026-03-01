"""Unit tests for local storage backend."""

import os
import tempfile

import pytest

from app.storage.local import LocalStorage


@pytest.mark.asyncio
class TestLocalStorage:
    async def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save("test/file.bin", b"hello world")
            data = await storage.load("test/file.bin")
            assert data == b"hello world"

    async def test_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            assert await storage.exists("nope.bin") is False
            await storage.save("yes.bin", b"data")
            assert await storage.exists("yes.bin") is True

    async def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save("to_delete.bin", b"data")
            assert await storage.exists("to_delete.bin") is True
            await storage.delete("to_delete.bin")
            assert await storage.exists("to_delete.bin") is False

    async def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            # Should not raise
            await storage.delete("nonexistent.bin")

    async def test_nested_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save("a/b/c/deep.bin", b"deep data")
            data = await storage.load("a/b/c/deep.bin")
            assert data == b"deep data"

    async def test_get_url(self):
        storage = LocalStorage("/storage")
        assert storage.get_url("user/img/file.png") == "user/img/file.png"
