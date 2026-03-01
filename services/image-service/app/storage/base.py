from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for image storage backends."""

    async def save(self, path: str, data: bytes) -> None:
        """Save binary data to the given path."""
        ...

    async def load(self, path: str) -> bytes:
        """Load binary data from the given path."""
        ...

    async def delete(self, path: str) -> None:
        """Delete data at the given path."""
        ...

    async def exists(self, path: str) -> bool:
        """Check if data exists at the given path."""
        ...

    def get_url(self, path: str) -> str:
        """Get a URL or path reference for the stored data."""
        ...
