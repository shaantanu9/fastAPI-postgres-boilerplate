"""Enterprise File Upload Service
Secure file handling with multiple storage backends, virus scanning, and metadata management.
"""

import hashlib
import mimetypes
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import aiofiles

# Import magic with fallback
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

from fastapi import HTTPException, UploadFile, status
from loguru import logger
from PIL import Image
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.redis_manager import RedisNamespace, redis_manager


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"


class FileCategory(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"


class FileMetadata(BaseModel):
    """File metadata model."""

    id: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_hash: str
    category: FileCategory
    upload_timestamp: datetime
    user_id: str | None = None
    is_public: bool = False
    download_count: int = 0
    expiry_date: datetime | None = None
    metadata: dict | None = None


class FileValidationResult(BaseModel):
    """File validation result."""

    is_valid: bool
    errors: list[str]
    file_info: dict | None = None


class EnterpriseFileUploadService:
    """Enterprise-grade file upload service with security and validation."""

    def __init__(self) -> None:
        self.settings = get_settings()

        # Configuration
        self.max_file_size = getattr(
            self.settings, "max_file_size", 10 * 1024 * 1024,
        )  # 10MB
        self.allowed_extensions = getattr(
            self.settings,
            "allowed_extensions",
            {
                "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
                "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            },
        )

        # Dangerous file types to always reject
        self.forbidden_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
            ".jar",
            ".php",
            ".py",
            ".pl",
            ".sh",
            ".ps1",
            ".msi",
        ]

        # Storage configuration
        self.storage_backend = getattr(
            self.settings, "storage_backend", StorageBackend.LOCAL,
        )
        self.upload_path = Path(getattr(self.settings, "upload_path", "./uploads"))
        self.temp_path = Path(getattr(self.settings, "temp_path", "./temp"))

        # Create directories
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)

    def _get_file_category(self, filename: str, mime_type: str) -> FileCategory:
        """Determine file category based on extension and MIME type."""
        ext = Path(filename).suffix.lower()

        if mime_type.startswith("image/") or ext in self.allowed_extensions.get(
            "images", [],
        ):
            return FileCategory.IMAGE
        if mime_type.startswith("video/") or ext in self.allowed_extensions.get(
            "videos", [],
        ):
            return FileCategory.VIDEO
        if mime_type.startswith("audio/") or ext in self.allowed_extensions.get(
            "audio", [],
        ):
            return FileCategory.AUDIO
        if ext in self.allowed_extensions.get("documents", []):
            return FileCategory.DOCUMENT
        if ext in self.allowed_extensions.get("archives", []):
            return FileCategory.ARCHIVE
        return FileCategory.OTHER

    def _is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = Path(filename).suffix.lower()

        if ext in self.forbidden_extensions:
            return False

        all_allowed = []
        for category_exts in self.allowed_extensions.values():
            all_allowed.extend(category_exts)

        return ext in all_allowed or not all_allowed  # Allow all if no restrictions

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type using python-magic with fallback."""
        try:
            if MAGIC_AVAILABLE and magic:
                # Use python-magic for accurate detection
                return magic.from_file(str(file_path), mime=True)
            logger.debug("python-magic not available, using mimetypes fallback")
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or "application/octet-stream"
        except Exception as e:
            logger.warning(f"Failed to detect MIME type for {file_path}: {e}")
            # Final fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or "application/octet-stream"

    async def _scan_for_viruses(self, file_path: Path) -> bool:
        """Scan file for viruses (placeholder for virus scanning integration)
        In production, integrate with ClamAV or similar.
        """
        try:
            # This is a placeholder - in production you would integrate with:
            # - ClamAV
            # - Windows Defender
            # - Cloud-based scanning services

            # For now, just check file size and some basic patterns
            file_size = file_path.stat().st_size

            # Reject files that are too large (potential zip bombs)
            if file_size > self.max_file_size * 10:  # 10x the normal limit
                return False

            # Check for suspicious file signatures (basic check)
            with open(file_path, "rb") as f:
                header = f.read(1024)

                # Check for executable signatures
                suspicious_signatures = [
                    b"MZ",  # PE executable
                    b"\x7fELF",  # ELF executable
                    b"\xca\xfe\xba\xbe",  # Java class file
                ]

                for sig in suspicious_signatures:
                    if header.startswith(sig):
                        logger.warning(
                            f"Suspicious file signature detected: {file_path}",
                        )
                        return False

            return True

        except Exception as e:
            logger.error(f"Virus scan failed for {file_path}: {e}")
            return False

    async def _validate_image(self, file_path: Path) -> dict:
        """Validate and get information about image files."""
        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ("RGBA", "LA")
                    or "transparency" in img.info,
                }
        except Exception as e:
            msg = f"Invalid image file: {e}"
            raise ValueError(msg)

    async def _create_image_thumbnail(
        self, file_path: Path, thumbnail_path: Path, size: tuple = (200, 200),
    ) -> None:
        """Create thumbnail for image files."""
        try:
            with Image.open(file_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, optimize=True, quality=85)
                logger.info(f"Created thumbnail: {thumbnail_path}")
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {file_path}: {e}")

    async def validate_file(self, file: UploadFile) -> FileValidationResult:
        """Comprehensive file validation."""
        errors = []
        file_info = {}

        try:
            # Check file size
            if hasattr(file, "size") and file.size > self.max_file_size:
                errors.append(
                    f"File size ({file.size} bytes) exceeds maximum allowed ({self.max_file_size} bytes)",
                )

            # Check filename
            if not file.filename:
                errors.append("Filename is required")
                return FileValidationResult(is_valid=False, errors=errors)

            # Check extension
            if not self._is_allowed_extension(file.filename):
                ext = Path(file.filename).suffix.lower()
                errors.append(f"File extension '{ext}' is not allowed")

            # Save to temporary file for detailed inspection
            temp_file_path = self.temp_path / f"temp_{uuid.uuid4().hex}_{file.filename}"

            try:
                content = await file.read()
                await file.seek(0)  # Reset file pointer

                # Check actual file size
                actual_size = len(content)
                if actual_size > self.max_file_size:
                    errors.append(
                        f"File size ({actual_size} bytes) exceeds maximum allowed ({self.max_file_size} bytes)",
                    )

                # Write to temp file for analysis
                async with aiofiles.open(temp_file_path, "wb") as temp_file:
                    await temp_file.write(content)

                # Detect MIME type
                mime_type = await self._detect_mime_type(temp_file_path)
                file_info["mime_type"] = mime_type
                file_info["file_size"] = actual_size

                # Virus scan
                if not await self._scan_for_viruses(temp_file_path):
                    errors.append("File failed security scan")

                # Category-specific validation
                category = self._get_file_category(file.filename, mime_type)
                file_info["category"] = category.value

                if category == FileCategory.IMAGE:
                    try:
                        image_info = await self._validate_image(temp_file_path)
                        file_info["image_info"] = image_info

                        # Check image dimensions
                        max_width = getattr(self.settings, "max_image_width", 4096)
                        max_height = getattr(self.settings, "max_image_height", 4096)

                        if (
                            image_info["width"] > max_width
                            or image_info["height"] > max_height
                        ):
                            errors.append(
                                f"Image dimensions ({image_info['width']}x{image_info['height']}) exceed maximum allowed ({max_width}x{max_height})",
                            )

                    except ValueError as e:
                        errors.append(str(e))

            finally:
                # Clean up temp file
                if temp_file_path.exists():
                    temp_file_path.unlink()

            return FileValidationResult(
                is_valid=len(errors) == 0, errors=errors, file_info=file_info,
            )

        except Exception as e:
            logger.error(f"File validation error: {e}")
            errors.append(f"Validation failed: {e!s}")
            return FileValidationResult(is_valid=False, errors=errors)

    async def upload_file(
        self,
        file: UploadFile,
        user_id: str | None = None,
        is_public: bool = False,
        expiry_hours: int | None = None,
    ) -> FileMetadata:
        """Upload and store file securely."""
        # Validate file first
        validation_result = await self.validate_file(file)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {', '.join(validation_result.errors)}",
            )

        file_info = validation_result.file_info

        try:
            # Generate unique file ID and stored filename
            file_id = str(uuid.uuid4())
            file_ext = Path(file.filename).suffix.lower()
            stored_filename = f"{file_id}{file_ext}"

            # Determine storage path
            category = FileCategory(file_info["category"])
            category_path = self.upload_path / category.value
            category_path.mkdir(exist_ok=True)

            final_file_path = category_path / stored_filename

            # Save file
            content = await file.read()
            async with aiofiles.open(final_file_path, "wb") as stored_file:
                await stored_file.write(content)

            # Calculate file hash
            file_hash = self._calculate_file_hash(final_file_path)

            # Create thumbnail for images
            thumbnail_path = None
            if category == FileCategory.IMAGE:
                thumbnail_filename = f"thumb_{file_id}.jpg"
                thumbnail_path = category_path / "thumbnails"
                thumbnail_path.mkdir(exist_ok=True)
                await self._create_image_thumbnail(
                    final_file_path, thumbnail_path / thumbnail_filename,
                )

            # Calculate expiry date
            expiry_date = None
            if expiry_hours:
                expiry_date = datetime.utcnow() + timedelta(hours=expiry_hours)

            # Create metadata
            metadata = FileMetadata(
                id=file_id,
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=str(final_file_path.relative_to(self.upload_path)),
                file_size=file_info["file_size"],
                mime_type=file_info["mime_type"],
                file_hash=file_hash,
                category=category,
                upload_timestamp=datetime.utcnow(),
                user_id=user_id,
                is_public=is_public,
                expiry_date=expiry_date,
                metadata=file_info,
            )

            # Store metadata in Redis (and later database)
            await redis_manager.cache_set(
                f"file_metadata:{file_id}",
                metadata.dict(),
                ttl=86400 * 7,  # 7 days
                namespace=RedisNamespace.CACHE,
            )

            logger.info(f"File uploaded successfully: {file_id} ({file.filename})")
            return metadata

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {e!s}",
            )

    async def get_file_metadata(self, file_id: str) -> FileMetadata | None:
        """Get file metadata by ID."""
        try:
            cached_metadata = await redis_manager.cache_get(
                f"file_metadata:{file_id}", namespace=RedisNamespace.CACHE,
            )

            if cached_metadata:
                return FileMetadata(**cached_metadata)

            return None

        except Exception as e:
            logger.error(f"Failed to get file metadata for {file_id}: {e}")
            return None

    async def delete_file(self, file_id: str, user_id: str | None = None) -> bool:
        """Delete file and its metadata."""
        try:
            metadata = await self.get_file_metadata(file_id)
            if not metadata:
                return False

            # Check permissions
            if user_id and metadata.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete this file",
                )

            # Delete physical file
            file_path = self.upload_path / metadata.file_path
            if file_path.exists():
                file_path.unlink()

            # Delete thumbnail if exists
            if metadata.category == FileCategory.IMAGE:
                thumbnail_path = (
                    file_path.parent / "thumbnails" / f"thumb_{file_id}.jpg"
                )
                if thumbnail_path.exists():
                    thumbnail_path.unlink()

            # Remove metadata from cache
            await redis_manager.cache_delete(
                f"file_metadata:{file_id}", namespace=RedisNamespace.CACHE,
            )

            logger.info(f"File deleted successfully: {file_id}")
            return True

        except Exception as e:
            logger.error(f"File deletion failed for {file_id}: {e}")
            return False

    async def cleanup_expired_files(self) -> None:
        """Clean up expired files (background task)."""
        try:
            # This would typically be run as a scheduled task
            # For now, we'll just log that cleanup should happen
            logger.info("File cleanup task should be implemented as background job")

        except Exception as e:
            logger.error(f"File cleanup failed: {e}")


# Global file upload service instance
file_upload_service = EnterpriseFileUploadService()
