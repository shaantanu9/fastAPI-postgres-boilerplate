# app/core/file_manager.py

import os
import uuid
import mimetypes
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO
from enum import Enum

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db


class FileStorageType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCP = "gcp"


class FileCategory(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"


class FileMetadata(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    category: FileCategory
    storage_type: FileStorageType
    checksum: str
    upload_timestamp: datetime
    last_accessed: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    mime_type: str
    category: FileCategory
    storage_path: str
    checksum: str
    upload_url: Optional[str] = None
    download_url: Optional[str] = None


class FileManagerConfig(BaseModel):
    # Storage settings
    default_storage: FileStorageType = FileStorageType.LOCAL
    local_storage_path: str = "./uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # S3 settings
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    
    # Security settings
    allowed_mime_types: List[str] = Field(default_factory=lambda: [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip", "application/x-zip-compressed"
    ])
    
    # Cleanup settings
    cleanup_enabled: bool = True
    cleanup_age_days: int = 30


class FileManager:
    """Enterprise-grade file management system with multiple storage backends"""
    
    def __init__(self, config: Optional[FileManagerConfig] = None):
        self.config = config or FileManagerConfig()
        self.settings = get_settings()
        self._s3_client = None
        
        # Initialize storage directories
        if self.config.default_storage == FileStorageType.LOCAL:
            self._ensure_local_directories()
    
    def _ensure_local_directories(self):
        """Ensure local storage directories exist"""
        base_path = Path(self.config.local_storage_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create category subdirectories
        for category in FileCategory:
            category_path = base_path / category.value
            category_path.mkdir(exist_ok=True)
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.config.s3_access_key,
                    aws_secret_access_key=self.config.s3_secret_key,
                    region_name=self.config.s3_region,
                    endpoint_url=self.config.s3_endpoint_url
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize S3 client: {str(e)}"
                )
        return self._s3_client
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file against security constraints"""
        # Check file size
        if file.size and file.size > self.config.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size {file.size} exceeds maximum allowed size {self.config.max_file_size}"
            )
        
        # Check MIME type
        if file.content_type not in self.config.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} is not allowed"
            )
        
        # Additional security checks can be added here
        # - Virus scanning
        # - Magic number validation
        # - Content inspection
    
    def _categorize_file(self, mime_type: str) -> FileCategory:
        """Categorize file based on MIME type"""
        if mime_type.startswith('image/'):
            return FileCategory.IMAGE
        elif mime_type.startswith('video/'):
            return FileCategory.VIDEO
        elif mime_type.startswith('audio/'):
            return FileCategory.AUDIO
        elif mime_type in ['application/zip', 'application/x-zip-compressed', 'application/x-rar-compressed']:
            return FileCategory.ARCHIVE
        elif mime_type in ['application/pdf', 'text/plain', 'text/csv'] or 'document' in mime_type:
            return FileCategory.DOCUMENT
        else:
            return FileCategory.OTHER
    
    def _generate_file_path(self, category: FileCategory, file_extension: str) -> str:
        """Generate unique file path"""
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        return f"{category.value}/{date_path}/{unique_filename}"
    
    def _calculate_checksum(self, file_content: bytes) -> str:
        """Calculate file checksum for integrity verification"""
        return hashlib.sha256(file_content).hexdigest()
    
    async def upload_file(
        self,
        file: UploadFile,
        storage_type: Optional[FileStorageType] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileUploadResponse:
        """Upload file to specified storage backend"""
        # Validation
        self._validate_file(file)
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Get file info
        original_filename = file.filename or "unknown"
        file_extension = Path(original_filename).suffix
        mime_type = file.content_type or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
        category = self._categorize_file(mime_type)
        
        # Generate metadata
        file_id = str(uuid.uuid4())
        checksum = self._calculate_checksum(file_content)
        file_path = self._generate_file_path(category, file_extension)
        storage_type = storage_type or self.config.default_storage
        
        # Store file based on storage type
        stored_path = None
        if storage_type == FileStorageType.LOCAL:
            stored_path = await self._upload_to_local(file_content, file_path)
        elif storage_type == FileStorageType.S3:
            stored_path = await self._upload_to_s3(file_content, file_path, mime_type)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage type {storage_type} not implemented"
            )
        
        # Create file metadata
        file_metadata = FileMetadata(
            id=file_id,
            original_filename=original_filename,
            stored_filename=Path(file_path).name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            category=category,
            storage_type=storage_type,
            checksum=checksum,
            upload_timestamp=datetime.utcnow(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Store metadata in database (implement based on your needs)
        await self._store_file_metadata(file_metadata)
        
        return FileUploadResponse(
            file_id=file_id,
            filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            category=category,
            storage_path=stored_path,
            checksum=checksum
        )
    
    async def _upload_to_local(self, file_content: bytes, file_path: str) -> str:
        """Upload file to local storage"""
        full_path = Path(self.config.local_storage_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(file_content)
        
        return str(full_path)
    
    async def _upload_to_s3(self, file_content: bytes, file_path: str, mime_type: str) -> str:
        """Upload file to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=file_path,
                Body=file_content,
                ContentType=mime_type,
                Metadata={
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'original_size': str(len(file_content))
                }
            )
            return f"s3://{self.config.s3_bucket}/{file_path}"
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to S3: {str(e)}"
            )
    
    async def generate_presigned_upload_url(
        self,
        filename: str,
        expires_in: int = 3600,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, str]:
        """Generate presigned URL for direct upload to S3"""
        if self.config.default_storage != FileStorageType.S3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Presigned URLs only available for S3 storage"
            )
        
        file_extension = Path(filename).suffix
        category = self._categorize_file(mimetypes.guess_type(filename)[0] or "")
        file_path = self._generate_file_path(category, file_extension)
        
        try:
            conditions = []
            if file_size_limit:
                conditions.append(["content-length-range", 0, file_size_limit])
            
            response = self.s3_client.generate_presigned_post(
                Bucket=self.config.s3_bucket,
                Key=file_path,
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            return {
                "upload_url": response["url"],
                "fields": response["fields"],
                "file_path": file_path
            }
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )
    
    async def generate_presigned_download_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """Generate presigned URL for file download"""
        if self.config.default_storage != FileStorageType.S3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Presigned URLs only available for S3 storage"
            )
        
        try:
            params = {
                'Bucket': self.config.s3_bucket,
                'Key': file_path
            }
            
            if filename:
                params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}"
            )
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from storage and metadata"""
        # Get file metadata first
        file_metadata = await self._get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete from storage
        try:
            if file_metadata.storage_type == FileStorageType.LOCAL:
                await self._delete_from_local(file_metadata.file_path)
            elif file_metadata.storage_type == FileStorageType.S3:
                await self._delete_from_s3(file_metadata.file_path)
            
            # Delete metadata
            await self._delete_file_metadata(file_id)
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )
    
    async def _delete_from_local(self, file_path: str):
        """Delete file from local storage"""
        full_path = Path(self.config.local_storage_path) / file_path
        if full_path.exists():
            full_path.unlink()
    
    async def _delete_from_s3(self, file_path: str):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.config.s3_bucket,
                Key=file_path
            )
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete from S3: {str(e)}"
            )
    
    async def get_file_info(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID"""
        return await self._get_file_metadata(file_id)
    
    async def list_files(
        self,
        category: Optional[FileCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FileMetadata]:
        """List files with filtering options"""
        # Implement based on your database structure
        return await self._list_file_metadata(category, tags, limit, offset)
    
    async def cleanup_old_files(self) -> int:
        """Cleanup old files based on configuration"""
        if not self.config.cleanup_enabled:
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.cleanup_age_days)
        old_files = await self._get_old_files(cutoff_date)
        
        deleted_count = 0
        for file_metadata in old_files:
            try:
                await self.delete_file(file_metadata.id)
                deleted_count += 1
            except Exception:
                # Log error but continue cleanup
                continue
        
        return deleted_count
    
    # Database methods (implement based on your ORM/database structure)
    async def _store_file_metadata(self, metadata: FileMetadata):
        """Store file metadata in database"""
        # Implement based on your database schema
        pass
    
    async def _get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata from database"""
        # Implement based on your database schema
        pass
    
    async def _delete_file_metadata(self, file_id: str):
        """Delete file metadata from database"""
        # Implement based on your database schema
        pass
    
    async def _list_file_metadata(
        self,
        category: Optional[FileCategory],
        tags: Optional[List[str]],
        limit: int,
        offset: int
    ) -> List[FileMetadata]:
        """List file metadata from database"""
        # Implement based on your database schema
        return []
    
    async def _get_old_files(self, cutoff_date: datetime) -> List[FileMetadata]:
        """Get files older than cutoff date"""
        # Implement based on your database schema
        return [] 