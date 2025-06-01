# app/api/v1/endpoints/files.py

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_manager import (
    FileManager, FileManagerConfig, FileStorageType, FileCategory,
    FileUploadResponse, FileMetadata
)
from app.db.session import get_db


router = APIRouter()


def get_file_manager() -> FileManager:
    """Get file manager instance with configuration"""
    # Configure based on environment
    config = FileManagerConfig(
        default_storage=FileStorageType.LOCAL,  # Change to S3 in production
        max_file_size=100 * 1024 * 1024,  # 100MB
        # S3 configuration (uncomment for S3 usage)
        # s3_bucket="your-bucket-name",
        # s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        # s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return FileManager(config)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    storage_type: Optional[FileStorageType] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    file_manager: FileManager = Depends(get_file_manager)
) -> FileUploadResponse:
    """Upload a file to the configured storage backend"""
    
    # Parse tags
    parsed_tags = []
    if tags:
        parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    try:
        result = await file_manager.upload_file(
            file=file,
            storage_type=storage_type,
            tags=parsed_tags
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/upload/multiple", response_model=List[FileUploadResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    storage_type: Optional[FileStorageType] = Form(None),
    tags: Optional[str] = Form(None),
    file_manager: FileManager = Depends(get_file_manager)
) -> List[FileUploadResponse]:
    """Upload multiple files"""
    
    # Parse tags
    parsed_tags = []
    if tags:
        parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    results = []
    for file in files:
        try:
            result = await file_manager.upload_file(
                file=file,
                storage_type=storage_type,
                tags=parsed_tags
            )
            results.append(result)
        except Exception as e:
            # Continue with other files, but log the error
            print(f"Failed to upload {file.filename}: {str(e)}")
            continue
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were successfully uploaded"
        )
    
    return results


@router.get("/presigned-upload")
async def generate_presigned_upload_url(
    filename: str = Query(..., description="Original filename"),
    expires_in: int = Query(3600, description="URL expiration in seconds"),
    file_size_limit: Optional[int] = Query(None, description="File size limit in bytes"),
    file_manager: FileManager = Depends(get_file_manager)
) -> Dict[str, Any]:
    """Generate presigned URL for direct file upload to S3"""
    
    try:
        result = await file_manager.generate_presigned_upload_url(
            filename=filename,
            expires_in=expires_in,
            file_size_limit=file_size_limit
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/presigned-download/{file_id}")
async def generate_presigned_download_url(
    file_id: str,
    expires_in: int = Query(3600, description="URL expiration in seconds"),
    filename: Optional[str] = Query(None, description="Download filename"),
    file_manager: FileManager = Depends(get_file_manager)
) -> Dict[str, str]:
    """Generate presigned URL for file download"""
    
    # Get file metadata first
    file_metadata = await file_manager.get_file_info(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        download_url = await file_manager.generate_presigned_download_url(
            file_path=file_metadata.file_path,
            expires_in=expires_in,
            filename=filename or file_metadata.original_filename
        )
        return {"download_url": download_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{file_id}", response_model=FileMetadata)
async def get_file_info(
    file_id: str,
    file_manager: FileManager = Depends(get_file_manager)
) -> FileMetadata:
    """Get file metadata by ID"""
    
    file_metadata = await file_manager.get_file_info(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return file_metadata


@router.get("/", response_model=List[FileMetadata])
async def list_files(
    category: Optional[FileCategory] = Query(None, description="Filter by file category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip"),
    file_manager: FileManager = Depends(get_file_manager)
) -> List[FileMetadata]:
    """List files with optional filtering"""
    
    # Parse tags
    parsed_tags = None
    if tags:
        parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    files = await file_manager.list_files(
        category=category,
        tags=parsed_tags,
        limit=limit,
        offset=offset
    )
    
    return files


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    file_manager: FileManager = Depends(get_file_manager)
) -> Dict[str, str]:
    """Delete a file"""
    
    success = await file_manager.delete_file(file_id)
    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.post("/cleanup")
async def cleanup_old_files(
    file_manager: FileManager = Depends(get_file_manager)
) -> Dict[str, int]:
    """Cleanup old files based on retention policy"""
    
    deleted_count = await file_manager.cleanup_old_files()
    return {"deleted_count": deleted_count}


@router.get("/categories/list")
async def list_file_categories() -> List[str]:
    """Get list of available file categories"""
    return [category.value for category in FileCategory]


@router.get("/storage-types/list")
async def list_storage_types() -> List[str]:
    """Get list of available storage types"""
    return [storage_type.value for storage_type in FileStorageType] 