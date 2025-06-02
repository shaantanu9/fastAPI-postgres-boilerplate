"""
Email Attachment Handler Module

Handles email attachments including file processing, MIME type detection,
and attachment validation.
"""

import base64
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional, Union

from loguru import logger

from .models import EmailAttachment


class AttachmentHandler:
    """Handles email attachment operations"""
    
    @staticmethod
    def create_attachment_from_file(
        file_path: Union[str, Path],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        disposition: str = "attachment",
        content_id: Optional[str] = None
    ) -> EmailAttachment:
        """
        Create EmailAttachment from file path
        
        Args:
            file_path: Path to the file
            filename: Override filename (uses file path name if None)
            content_type: MIME type (auto-detected if None)
            disposition: attachment or inline
            content_id: Content ID for inline images
        
        Returns:
            EmailAttachment object
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = filename or file_path.name
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or 'application/octet-stream'
        
        return EmailAttachment(
            filename=filename,
            content=content,
            content_type=content_type,
            disposition=disposition,
            content_id=content_id
        )
    
    @staticmethod
    def create_attachment_from_bytes(
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        disposition: str = "attachment",
        content_id: Optional[str] = None
    ) -> EmailAttachment:
        """
        Create EmailAttachment from bytes
        
        Args:
            content: File content as bytes
            filename: File name
            content_type: MIME type (auto-detected if None)
            disposition: attachment or inline
            content_id: Content ID for inline images
        
        Returns:
            EmailAttachment object
        """
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        return EmailAttachment(
            filename=filename,
            content=content,
            content_type=content_type,
            disposition=disposition,
            content_id=content_id
        )
    
    @staticmethod
    def create_inline_image(
        image_path: Union[str, Path],
        content_id: str,
        filename: Optional[str] = None
    ) -> EmailAttachment:
        """
        Create inline image attachment
        
        Args:
            image_path: Path to the image file
            content_id: Content ID for referencing in HTML
            filename: Override filename
        
        Returns:
            EmailAttachment configured for inline display
        """
        return AttachmentHandler.create_attachment_from_file(
            file_path=image_path,
            filename=filename,
            disposition="inline",
            content_id=content_id
        )
    
    @staticmethod
    async def add_attachment_to_message(
        msg: MIMEMultipart,
        attachment: EmailAttachment
    ) -> None:
        """
        Add attachment to email message
        
        Args:
            msg: Email message object
            attachment: EmailAttachment to add
        """
        try:
            if attachment.content_type.startswith('image/') and attachment.disposition == 'inline':
                # Handle inline images
                img = MIMEImage(attachment.content)
                img.add_header('Content-Disposition', 'inline', filename=attachment.filename)
                if attachment.content_id:
                    img.add_header('Content-ID', f'<{attachment.content_id}>')
                msg.attach(img)
            else:
                # Handle regular attachments
                part = MIMEApplication(attachment.content)
                part.add_header(
                    'Content-Disposition',
                    f'{attachment.disposition}; filename="{attachment.filename}"'
                )
                part.add_header('Content-Type', attachment.content_type)
                msg.attach(part)
                
        except Exception as e:
            logger.error(f"Error adding attachment {attachment.filename}: {str(e)}")
            raise
    
    @staticmethod
    def validate_attachments(
        attachments: List[EmailAttachment],
        max_size_mb: int = 25,
        allowed_types: Optional[List[str]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate email attachments
        
        Args:
            attachments: List of attachments to validate
            max_size_mb: Maximum total size in MB
            allowed_types: List of allowed MIME types (None for no restriction)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        total_size = 0
        
        for attachment in attachments:
            # Check file size
            file_size_mb = len(attachment.content) / (1024 * 1024)
            total_size += file_size_mb
            
            if file_size_mb > 10:  # AWS SES limit per attachment
                errors.append(f"Attachment '{attachment.filename}' exceeds 10MB limit")
            
            # Check allowed types
            if allowed_types and attachment.content_type not in allowed_types:
                errors.append(f"Attachment '{attachment.filename}' type '{attachment.content_type}' not allowed")
            
            # Check for potentially dangerous files
            dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.jar']
            if any(attachment.filename.lower().endswith(ext) for ext in dangerous_extensions):
                errors.append(f"Attachment '{attachment.filename}' has potentially dangerous extension")
        
        # Check total size
        if total_size > max_size_mb:
            errors.append(f"Total attachment size {total_size:.2f}MB exceeds {max_size_mb}MB limit")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_attachment_info(attachment: EmailAttachment) -> dict:
        """Get attachment information summary"""
        return {
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "size_bytes": len(attachment.content),
            "size_mb": round(len(attachment.content) / (1024 * 1024), 2),
            "disposition": attachment.disposition,
            "content_id": attachment.content_id
        }
    
    @staticmethod
    def create_pdf_attachment(
        content: bytes,
        filename: str = "document.pdf"
    ) -> EmailAttachment:
        """Create PDF attachment"""
        return AttachmentHandler.create_attachment_from_bytes(
            content=content,
            filename=filename,
            content_type="application/pdf"
        )
    
    @staticmethod
    def create_excel_attachment(
        content: bytes,
        filename: str = "spreadsheet.xlsx"
    ) -> EmailAttachment:
        """Create Excel attachment"""
        return AttachmentHandler.create_attachment_from_bytes(
            content=content,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    @staticmethod
    def create_csv_attachment(
        content: Union[str, bytes],
        filename: str = "data.csv"
    ) -> EmailAttachment:
        """Create CSV attachment"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        return AttachmentHandler.create_attachment_from_bytes(
            content=content,
            filename=filename,
            content_type="text/csv"
        ) 