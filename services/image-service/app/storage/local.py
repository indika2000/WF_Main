import logging
from pathlib import Path

import aiofiles
import aiofiles.os

logger = logging.getLogger("image")


class LocalStorage:
    """Local filesystem storage backend."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    async def save(self, path: str, data: bytes) -> None:
        """Save binary data to a local file."""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

    async def load(self, path: str) -> bytes:
        """Load binary data from a local file."""
        full_path = self.base_path / path
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        """Delete a local file."""
        full_path = self.base_path / path
        if full_path.exists():
            await aiofiles.os.remove(full_path)

    async def exists(self, path: str) -> bool:
        """Check if a local file exists."""
        full_path = self.base_path / path
        return full_path.exists()

    def get_url(self, path: str) -> str:
        """Return the storage path (for local, it's just the relative path)."""
        return path
