import mimetypes
import os
import shutil
import urllib.error
import urllib.request
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class StorageConfigurationError(RuntimeError):
    pass


class ObjectStorageProvider(ABC):
    name = "base"

    @abstractmethod
    def public_url(self, relative_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def save_bytes(self, content: bytes, *, filename: Optional[str] = None, content_type: str = "") -> str:
        raise NotImplementedError

    @abstractmethod
    def ingest_url(self, url: str, *, base_dir: Optional[Path] = None) -> str:
        raise NotImplementedError

    def upload_config(self, *, purpose: str = "user-upload") -> Dict[str, Any]:
        return {"provider": self.name, "mode": "server_upload", "purpose": purpose}

    def delete_url(self, public_url: str) -> bool:
        return False


def extension_for(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix and len(suffix) <= 8:
        return suffix
    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) if content_type else ""
    return guessed or ".png"


class LocalStorageProvider(ObjectStorageProvider):
    name = "local"

    def __init__(self, root_dir: Path, *, public_prefix: str = "/storage", cdn_base_url: str = "") -> None:
        self.root_dir = root_dir
        self.public_prefix = public_prefix.rstrip("/")
        self.cdn_base_url = cdn_base_url.rstrip("/")

    def public_url(self, relative_path: str) -> str:
        clean = relative_path.strip("/")
        if self.cdn_base_url:
            return f"{self.cdn_base_url}/{clean}"
        return f"{self.public_prefix}/{clean}"

    def relative_path_from_url(self, public_url: str) -> Optional[str]:
        if not public_url:
            return None
        if public_url.startswith(f"{self.public_prefix}/"):
            return public_url[len(self.public_prefix) + 1 :]
        if self.cdn_base_url and public_url.startswith(f"{self.cdn_base_url}/"):
            return public_url[len(self.cdn_base_url) + 1 :]
        return None

    def path_for(self, relative_path: str) -> Path:
        clean = relative_path.strip("/")
        path = (self.root_dir / clean).resolve()
        if not str(path).startswith(str(self.root_dir.resolve())):
            raise ValueError("非法存储路径")
        return path

    def save_bytes(self, content: bytes, *, filename: Optional[str] = None, content_type: str = "") -> str:
        ext = extension_for(filename or "", content_type)
        relative_path = f"images/{uuid.uuid4().hex}{ext}"
        target = self.path_for(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self.public_url(relative_path)

    def copy_local_file(self, source: Path) -> str:
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))
        relative_path = f"images/{uuid.uuid4().hex}{source.suffix or '.bin'}"
        target = self.path_for(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return self.public_url(relative_path)

    def ingest_url(self, url: str, *, base_dir: Optional[Path] = None) -> str:
        if not url or url.startswith(("/static/", "/storage/", "data:", "blob:", "file:", "wxfile:", "ttfile:", "myfile:")):
            return url
        if url.startswith("/generated-images/") and base_dir:
            source = base_dir / "generated-images" / Path(url).name
            try:
                return self.copy_local_file(source)
            except Exception:
                return url
        if url.startswith("/"):
            return url
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return url
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MioDrawStorage/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "")
            filename = Path(parsed.path).name
            return self.save_bytes(content, filename=filename, content_type=content_type)
        except (urllib.error.URLError, OSError, ValueError):
            return url

    def upload_config(self, *, purpose: str = "user-upload") -> Dict[str, Any]:
        return {"provider": self.name, "mode": "server_upload", "endpoint": "/api/storage/upload", "purpose": purpose}

    def delete_url(self, public_url: str) -> bool:
        relative_path = self.relative_path_from_url(public_url)
        if not relative_path:
            return False
        path = self.path_for(relative_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False


class _RemoteStorageProvider(ObjectStorageProvider):
    required_env: tuple[str, ...] = ()

    def _require_config(self) -> None:
        missing = [key for key in self.required_env if not os.getenv(key)]
        if missing:
            raise StorageConfigurationError(f"{self.name} 存储未配置：缺少 {', '.join(missing)}")

    def public_url(self, relative_path: str) -> str:
        self._require_config()
        base = os.getenv("CDN_BASE_URL") or os.getenv(f"{self.name.upper()}_PUBLIC_BASE_URL", "")
        return f"{base.rstrip('/')}/{relative_path.strip('/')}" if base else relative_path

    def save_bytes(self, content: bytes, *, filename: Optional[str] = None, content_type: str = "") -> str:
        self._require_config()
        raise StorageConfigurationError(f"{self.name} 已预留 Provider 边界；上线前接入对应 SDK 的 put_object。")

    def ingest_url(self, url: str, *, base_dir: Optional[Path] = None) -> str:
        return url

    def upload_config(self, *, purpose: str = "user-upload") -> Dict[str, Any]:
        self._require_config()
        return {
            "provider": self.name,
            "mode": "presigned",
            "purpose": purpose,
            "bucket": os.getenv(f"{self.name.upper()}_BUCKET", ""),
            "prefix": f"{purpose.strip('/')}/{uuid.uuid4().hex}/",
            "integration_note": f"已预留 {self.name} 直传签名结构；上线前接入服务端签名和私有 ACL。",
        }


class S3StorageProvider(_RemoteStorageProvider):
    name = "s3"
    required_env = ("S3_BUCKET", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")


class OSSStorageProvider(_RemoteStorageProvider):
    name = "oss"
    required_env = ("OSS_BUCKET", "OSS_ENDPOINT", "OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET")


class COSStorageProvider(_RemoteStorageProvider):
    name = "cos"
    required_env = ("COS_BUCKET", "COS_REGION")

    def __init__(self) -> None:
        self.bucket = os.getenv("COS_BUCKET", "").strip()
        self.region = os.getenv("COS_REGION", "").strip()
        self.public_base_url = (
            os.getenv("CDN_BASE_URL")
            or os.getenv("COS_PUBLIC_BASE_URL")
            or (f"https://{self.bucket}.cos.{self.region}.myqcloud.com" if self.bucket and self.region else "")
        ).rstrip("/")

    def public_url(self, relative_path: str) -> str:
        self._require_config()
        clean = relative_path.strip("/")
        return f"{self.public_base_url}/{clean}" if self.public_base_url else clean

    def save_bytes(self, content: bytes, *, filename: Optional[str] = None, content_type: str = "") -> str:
        self._require_config()
        key = f"images/{uuid.uuid4().hex}{extension_for(filename or '', content_type)}"
        self._client().put_object(
            Bucket=self.bucket,
            Body=content,
            Key=key,
            ContentType=content_type or "application/octet-stream",
        )
        return self.public_url(key)

    def ingest_url(self, url: str, *, base_dir: Optional[Path] = None) -> str:
        if not url or url.startswith(("data:", "blob:", "file:", "wxfile:", "ttfile:", "myfile:")):
            return url
        if self._relative_key_from_url(url):
            return url
        if url.startswith("/generated-images/") and base_dir:
            source = base_dir / "generated-images" / Path(url).name
            if source.exists() and source.is_file():
                return self.save_bytes(source.read_bytes(), filename=source.name)
            return url
        if url.startswith(("/static/", "/mock-images/", "/storage/")):
            return url
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return url
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MioDrawStorage/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "")
            filename = Path(parsed.path).name
            return self.save_bytes(content, filename=filename, content_type=content_type)
        except (urllib.error.URLError, OSError, ValueError, StorageConfigurationError):
            return url

    def upload_config(self, *, purpose: str = "user-upload") -> Dict[str, Any]:
        self._require_config()
        return {"provider": self.name, "mode": "server_upload", "endpoint": "/api/storage/upload", "purpose": purpose}

    def delete_url(self, public_url: str) -> bool:
        key = self._relative_key_from_url(public_url)
        if not key:
            return False
        self._client().delete_object(Bucket=self.bucket, Key=key)
        return True

    def _relative_key_from_url(self, public_url: str) -> str:
        if not public_url:
            return ""
        if self.public_base_url and public_url.startswith(f"{self.public_base_url}/"):
            return public_url[len(self.public_base_url) + 1 :]
        parsed = urlparse(public_url)
        if parsed.netloc and self.bucket and parsed.netloc.startswith(self.bucket):
            return parsed.path.strip("/")
        return ""

    def _credential(self, *keys: str) -> str:
        for key in keys:
            value = os.getenv(key, "").strip()
            if value:
                return value
        return ""

    def _client(self) -> Any:
        secret_id = self._credential("COS_SECRET_ID", "TENCENTCLOUD_SECRETID", "TENCENTCLOUD_SECRET_ID", "TENCENT_SECRET_ID")
        secret_key = self._credential("COS_SECRET_KEY", "TENCENTCLOUD_SECRETKEY", "TENCENTCLOUD_SECRET_KEY", "TENCENT_SECRET_KEY")
        token = self._credential("COS_SESSION_TOKEN", "TENCENTCLOUD_SESSIONTOKEN", "TENCENTCLOUD_TOKEN")
        if not secret_id or not secret_key:
            raise StorageConfigurationError("COS 存储缺少密钥：需要 COS_SECRET_ID/COS_SECRET_KEY，或云托管运行时注入 TENCENTCLOUD_SECRETID/TENCENTCLOUD_SECRETKEY")
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as error:
            raise StorageConfigurationError("COS 存储需要安装 cos-python-sdk-v5") from error
        config = CosConfig(Region=self.region, SecretId=secret_id, SecretKey=secret_key, Token=token or None, Scheme="https")
        return CosS3Client(config)


def local_storage_from_env(root_dir: Path) -> LocalStorageProvider:
    return LocalStorageProvider(root_dir, cdn_base_url=os.getenv("CDN_BASE_URL", "").strip())


def storage_provider_from_env(root_dir: Path) -> ObjectStorageProvider:
    provider = os.getenv("STORAGE_PROVIDER", "local").strip().lower()
    if provider in ("", "local", "dev"):
        return local_storage_from_env(root_dir)
    if provider == "s3":
        return S3StorageProvider()
    if provider == "oss":
        return OSSStorageProvider()
    if provider == "cos":
        return COSStorageProvider()
    raise StorageConfigurationError(f"未知存储渠道：{provider}")
