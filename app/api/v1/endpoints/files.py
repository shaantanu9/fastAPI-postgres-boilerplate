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
    """
    Get a configured file manager instance for handling file operations.

    Returns:
        FileManager: The configured file manager instance.
    """
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
    """
    Upload a file to the configured storage backend (local or S3).

    Args:
        file (UploadFile): The file to upload.
        storage_type (Optional[FileStorageType]): Storage backend to use.
        tags (Optional[str]): Comma-separated tags for the file.
        file_manager (FileManager): The file manager dependency.
    Returns:
        FileUploadResponse: Metadata and status of the uploaded file.
    Raises:
        HTTPException: If the upload fails.
    """
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
    """
    Upload multiple files to the configured storage backend.

    Args:
        files (List[UploadFile]): List of files to upload.
        storage_type (Optional[FileStorageType]): Storage backend to use.
        tags (Optional[str]): Comma-separated tags for the files.
        file_manager (FileManager): The file manager dependency.
    Returns:
        List[FileUploadResponse]: List of metadata and status for each uploaded file.
    Raises:
        HTTPException: If any upload fails.
    """
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
    """
    Generate a presigned URL for direct file upload to S3.

    Args:
        filename (str): Name of the file to be uploaded.
        expires_in (int): Expiration time of the URL in seconds.
        file_size_limit (Optional[int]): Maximum allowed file size in bytes.
        file_manager (FileManager): The file manager dependency.
    Returns:
        dict: Presigned URL and upload parameters.
    Raises:
        HTTPException: If URL generation fails or S3 is not configured.
    """
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
    """
    Generate a presigned URL for downloading a file from S3.

    Args:
        file_id (str): Unique identifier of the file.
        expires_in (int): Expiration time of the URL in seconds.
        filename (Optional[str]): Custom filename for the download.
        file_manager (FileManager): The file manager dependency.
    Returns:
        dict: Presigned download URL and parameters.
    Raises:
        HTTPException: If URL generation fails or file does not exist.
    """
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
    """
    Retrieve file metadata by its unique ID.

    Args:
        file_id (str): Unique identifier of the file.
        file_manager (FileManager): The file manager dependency.
    Returns:
        FileMetadata: Metadata for the requested file.
    Raises:
        HTTPException: If the file does not exist or retrieval fails.
    """
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
    """
    List files with optional filtering by category, tags, and pagination.

    Args:
        category (Optional[FileCategory]): Filter files by category.
        tags (Optional[str]): Comma-separated tags to filter files.
        limit (int): Maximum number of files to return.
        offset (int): Number of files to skip for pagination.
        file_manager (FileManager): The file manager dependency.
    Returns:
        List[FileMetadata]: List of file metadata objects.
    Raises:
        HTTPException: If file listing fails.
    """
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
    """
    Delete a file by its unique ID from the storage backend.

    Args:
        file_id (str): Unique identifier of the file to delete.
        file_manager (FileManager): The file manager dependency.
    Returns:
        dict: Status message indicating deletion result.
    Raises:
        HTTPException: If deletion fails or file does not exist.
    """
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
    """
    Cleanup old files based on the configured retention policy.

    Args:
        file_manager (FileManager): The file manager dependency.
    Returns:
        dict: Status and number of files cleaned up.
    Raises:
        HTTPException: If cleanup fails.
    """
    deleted_count = await file_manager.cleanup_old_files()
    return {"deleted_count": deleted_count}


@router.get("/categories/list")
async def list_file_categories() -> List[str]:
    """
    Get the list of available file categories.

    Returns:
        List[str]: List of file category names.
    """
    return [c.value for c in FileCategory]


@router.get("/storage-types/list")
async def list_storage_types() -> List[str]:
    """
    Get the list of available storage types (e.g., local, S3).

    Returns:
        List[str]: List of storage type names.
    """
    return [s.value for s in FileStorageType]