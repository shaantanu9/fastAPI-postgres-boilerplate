"""
Input Validation module.
Provides comprehensive input validation and sanitization for request data.
"""

import re
from typing import Any, Dict, List, Optional, Union, Pattern
from pydantic import BaseModel, validator, EmailStr
from fastapi import HTTPException
from enum import Enum
import html
import json
import uuid

class ValidationRule(str, Enum):
    """Predefined validation rules for common input types."""
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    PASSWORD = "password"
    URL = "url"
    UUID = "uuid"
    SLUG = "slug"
    HTML = "html"
    JSON = "json"
    NO_SCRIPT = "no_script"

class InputValidator:
    """
    Advanced input validation and sanitization utility.
    Provides reusable validation rules and sanitization methods.
    """
    
    # Common validation patterns
    PATTERNS = {
        "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        "phone": re.compile(r'^\+?1?\d{9,15}$'),
        "username": re.compile(r'^[a-zA-Z0-9_-]{3,32}$'),
        "password": re.compile(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        ),
        "url": re.compile(
            r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b'
            r'([-a-zA-Z0-9@:%_\+.~#?&//=]*)$'
        ),
        "slug": re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    }
    
    def __init__(self, custom_patterns: Optional[Dict[str, Pattern]] = None):
        """
        Initialize validator with optional custom patterns.
        
        Args:
            custom_patterns: Dictionary of custom regex patterns to add/override
        """
        self.patterns = {**self.PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
    
    def validate(
        self,
        value: Any,
        rule: ValidationRule,
        custom_pattern: Optional[Pattern] = None,
        **kwargs
    ) -> bool:
        """
        Validate input against a predefined or custom rule.
        
        Args:
            value: Value to validate
            rule: Validation rule to apply
            custom_pattern: Optional custom regex pattern
            **kwargs: Additional validation parameters
            
        Returns:
            bool indicating if validation passed
            
        Raises:
            ValueError: If validation fails
        """
        if value is None:
            raise ValueError("Value cannot be None")
            
        # Use custom pattern if provided
        if custom_pattern:
            return bool(custom_pattern.match(str(value)))
        
        # Apply predefined rules
        if rule == ValidationRule.EMAIL:
            return self._validate_email(value)
        elif rule == ValidationRule.PHONE:
            return self._validate_phone(value)
        elif rule == ValidationRule.USERNAME:
            return self._validate_username(value)
        elif rule == ValidationRule.PASSWORD:
            return self._validate_password(value, **kwargs)
        elif rule == ValidationRule.URL:
            return self._validate_url(value)
        elif rule == ValidationRule.UUID:
            return self._validate_uuid(value)
        elif rule == ValidationRule.SLUG:
            return self._validate_slug(value)
        elif rule == ValidationRule.HTML:
            return self._validate_html(value, **kwargs)
        elif rule == ValidationRule.JSON:
            return self._validate_json(value)
        elif rule == ValidationRule.NO_SCRIPT:
            return self._validate_no_script(value)
        
        raise ValueError(f"Unknown validation rule: {rule}")
    
    def sanitize(
        self,
        value: str,
        rule: ValidationRule,
        **kwargs
    ) -> str:
        """
        Sanitize input based on rule.
        
        Args:
            value: Value to sanitize
            rule: Sanitization rule to apply
            **kwargs: Additional sanitization parameters
            
        Returns:
            Sanitized value
        """
        if value is None:
            return ""
            
        if rule == ValidationRule.HTML:
            return self._sanitize_html(value, **kwargs)
        elif rule == ValidationRule.NO_SCRIPT:
            return self._sanitize_no_script(value)
        elif rule == ValidationRule.JSON:
            return self._sanitize_json(value)
        
        # For other rules, perform basic sanitization
        return html.escape(str(value))
    
    def _validate_email(self, value: str) -> bool:
        """Validate email address."""
        try:
            EmailStr.validate(value)
            return bool(self.patterns["email"].match(value))
        except Exception:
            return False
    
    def _validate_phone(self, value: str) -> bool:
        """Validate phone number."""
        return bool(self.patterns["phone"].match(value))
    
    def _validate_username(self, value: str) -> bool:
        """Validate username."""
        return bool(self.patterns["username"].match(value))
    
    def _validate_password(
        self,
        value: str,
        min_length: int = 8,
        require_special: bool = True
    ) -> bool:
        """
        Validate password strength.
        
        Args:
            value: Password to validate
            min_length: Minimum password length
            require_special: Whether to require special characters
        """
        if len(value) < min_length:
            return False
            
        if require_special:
            return bool(self.patterns["password"].match(value))
            
        return True
    
    def _validate_url(self, value: str) -> bool:
        """Validate URL."""
        return bool(self.patterns["url"].match(value))
    
    def _validate_uuid(self, value: str) -> bool:
        """Validate UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except ValueError:
            return False
    
    def _validate_slug(self, value: str) -> bool:
        """Validate slug."""
        return bool(self.patterns["slug"].match(value))
    
    def _validate_html(
        self,
        value: str,
        allowed_tags: Optional[List[str]] = None
    ) -> bool:
        """
        Validate HTML content.
        
        Args:
            value: HTML content to validate
            allowed_tags: List of allowed HTML tags
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(value, 'html.parser')
            
            if allowed_tags:
                # Check for disallowed tags
                all_tags = [tag.name for tag in soup.find_all()]
                return all(tag in allowed_tags for tag in all_tags)
            
            return True
        except Exception:
            return False
    
    def _validate_json(self, value: Union[str, Dict, List]) -> bool:
        """Validate JSON data."""
        try:
            if isinstance(value, (dict, list)):
                json.dumps(value)  # Validate serializable
                return True
            json.loads(value)  # Validate JSON string
            return True
        except Exception:
            return False
    
    def _validate_no_script(self, value: str) -> bool:
        """Validate that content contains no script tags or dangerous HTML."""
        return "<script" not in value.lower() and "javascript:" not in value.lower()
    
    def _sanitize_html(
        self,
        value: str,
        allowed_tags: Optional[List[str]] = None
    ) -> str:
        """
        Sanitize HTML content.
        
        Args:
            value: HTML content to sanitize
            allowed_tags: List of allowed HTML tags
        """
        from bs4 import BeautifulSoup
        
        # Default allowed tags if none specified
        allowed_tags = allowed_tags or [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'img'
        ]
        
        soup = BeautifulSoup(value, 'html.parser')
        
        # Remove disallowed tags
        for tag in soup.find_all():
            if tag.name not in allowed_tags:
                tag.unwrap()
        
        return str(soup)
    
    def _sanitize_no_script(self, value: str) -> str:
        """Remove script tags and potentially dangerous content."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(value, 'html.parser')
        
        # Remove script tags
        for script in soup.find_all('script'):
            script.decompose()
        
        # Remove on* attributes
        for tag in soup.find_all():
            for attr in list(tag.attrs):
                if attr.lower().startswith('on'):
                    del tag[attr]
        
        return str(soup)
    
    def _sanitize_json(self, value: Union[str, Dict, List]) -> str:
        """Sanitize and format JSON data."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        
        try:
            # Parse and re-serialize to ensure valid JSON
            return json.dumps(json.loads(value), ensure_ascii=False)
        except Exception:
            raise ValueError("Invalid JSON data")
