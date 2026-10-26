import asyncio
import io
import logging
import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import RECORDINGS_DIR, settings
from app.services.storage.base import StorageService

logger = logging.getLogger(__name__)

LOCAL_RECORDINGS_DIR = RECORDINGS_DIR
LOCAL_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class S3StorageService(StorageService):
    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL or None
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET or "voxora-recordings"
        self.region = settings.S3_REGION or "us-east-1"
        self._client = None
        self._init_client()

    def _init_client(self):
        if not self.access_key or not self.secret_key:
            logger.info("MinIO/S3 credentials not configured; storage service running with local disk storage.")
            return

        try:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, connect_timeout=1.0, read_timeout=1.0, retries={"max_attempts": 1}),
            )
            self._ensure_bucket()
        except Exception as e:
            logger.warning(f"Could not initialize S3/MinIO client: {e}")

    def _ensure_bucket(self):
        if not self._client:
            return
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created S3/MinIO bucket '{self.bucket}'.")
            except Exception as e:
                logger.warning(f"Could not create bucket '{self.bucket}': {e}")
        except Exception:
            pass

    async def upload(self, key: str, data: bytes, content_type: str = "audio/wav") -> str:
        # Always persist to local storage for zero-dependency reliability
        try:
            local_path = LOCAL_RECORDINGS_DIR / key.replace("/", os.sep)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            logger.info(f"[Storage] Persisted recording to local disk: {local_path} ({len(data)} bytes)")

            # Also save convenient top-level file if call key pattern (calls/<call_id>/recording.wav)
            parts = key.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "calls":
                call_id = parts[1]
                flat_file = LOCAL_RECORDINGS_DIR / f"call_{call_id}.wav"
                flat_file.write_bytes(data)
        except Exception as err:
            logger.warning(f"[Storage] Local disk write error for {key}: {err}")

        # Also push to MinIO if client is active
        if self._client:
            def _sync_upload():
                try:
                    self._client.put_object(
                        Bucket=self.bucket,
                        Key=key,
                        Body=data,
                        ContentType=content_type,
                    )
                except Exception as e:
                    logger.debug(f"[Storage] S3 put_object bypassed: {e}")
                return key

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _sync_upload)

        return key

    async def download(self, key: str) -> Optional[bytes]:
        # 1. Check local storage first
        try:
            local_path = LOCAL_RECORDINGS_DIR / key.replace("/", os.sep)
            if local_path.is_file():
                return local_path.read_bytes()
        except Exception as err:
            logger.debug(f"[Storage] Local read error for {key}: {err}")

        # 2. Check MinIO / S3
        if self._client:
            def _sync_download():
                try:
                    resp = self._client.get_object(Bucket=self.bucket, Key=key)
                    return resp["Body"].read()
                except Exception as e:
                    logger.debug(f"[Storage] S3 download error for {key}: {e}")
                    return None

            loop = asyncio.get_event_loop()
            s3_data = await loop.run_in_executor(None, _sync_download)
            if s3_data:
                return s3_data

        return None

    async def delete(self, key: str) -> bool:
        # Delete from local
        try:
            local_path = LOCAL_RECORDINGS_DIR / key.replace("/", os.sep)
            if local_path.is_file():
                local_path.unlink()
        except Exception:
            pass

        if not self._client:
            return True

        def _sync_delete():
            try:
                self._client.delete_object(Bucket=self.bucket, Key=key)
                return True
            except Exception as e:
                logger.warning(f"Error deleting {key} from S3: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_delete)

    async def exists(self, key: str) -> bool:
        local_path = LOCAL_RECORDINGS_DIR / key.replace("/", os.sep)
        if local_path.is_file():
            return True

        if not self._client:
            return False

        def _sync_exists():
            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                return True
            except (ClientError, Exception):
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_exists)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        if not self._client:
            return ""

        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.warning(f"Error generating presigned URL for {key}: {e}")
            return ""


storage_service = S3StorageService()
