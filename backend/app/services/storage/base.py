from abc import ABC, abstractmethod
from typing import Optional


class StorageService(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "audio/wav") -> str:
        """Uploads binary data to object storage and returns the object key."""
        pass

    @abstractmethod
    async def download(self, key: str) -> Optional[bytes]:
        """Downloads binary data from object storage."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletes object from storage."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Checks if object exists in storage."""
        pass

    @abstractmethod
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generates a secure temporary presigned download URL."""
        pass
