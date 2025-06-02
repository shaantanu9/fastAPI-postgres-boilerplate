"""
Enhanced SQLAlchemy models template with authentication support
"""
from typing import List, Dict, Any
import re
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import datetime
import uuid


class AuthModelsTemplate:
    """Generates SQLAlchemy model templates with authentication features"""
    
    def generate(self, model_name: str, fields: List[Dict[str, Any]], field_validator,
                auth_config: Dict[str, Any] = None) -> str:
        """Generate SQLAlchemy model file content with authentication support"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        pascal_name = model_name
        
        # Default auth configuration
        if auth_config is None:
            auth_config = {
                "enable_ownership": False,
                "enable_audit": True,
                "enable_soft_delete": False,
                "enable_versioning": False
            }
        
        # Generate field definitions
        sqlalchemy_fields = []
        for field in fields:
            field_def = field_validator.get_sqlalchemy_column(field)
            sqlalchemy_fields.append(field_def)
        
        sqlalchemy_fields_str = '\n'.join(sqlalchemy_fields)
        
        # Generate authentication fields
        auth_fields = self._generate_auth_fields(auth_config)
        
        # Generate relationships
        relationships = self._generate_relationships(auth_config)
        
        # Generate imports
        imports = self._generate_imports(auth_config)
        
        # Generate additional methods
        additional_methods = self._generate_additional_methods(auth_config, pascal_name, fields)
        
        template = f'''"""
{pascal_name} SQLAlchemy model with enterprise authentication
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
{imports}
from app.db.base import Base


class {pascal_name}(Base):
    """SQLAlchemy model for {pascal_name} with authentication features"""
    __tablename__ = "{snake_name}s"
    
    id = Column(Integer, primary_key=True, index=True)
{sqlalchemy_fields_str}
{auth_fields}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
{relationships}
    
    def __repr__(self):
        return f"<{pascal_name}(id={{self.id}})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {{
            'id': self.id,
            {self._generate_dict_fields(fields, auth_config)},
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }}
{additional_methods}
'''
        
        return template
    
    def _generate_auth_fields(self, auth_config: Dict[str, Any]) -> str:
        """Generate authentication-related fields"""
        fields = []
        
        if auth_config.get("enable_ownership", False):
            fields.append("    # Ownership tracking")
            fields.append("    created_by_id = Column(String, ForeignKey('users.id'), nullable=True)")
            fields.append("    updated_by_id = Column(String, ForeignKey('users.id'), nullable=True)")
            
        if auth_config.get("enable_audit", True):
            fields.append("    # Audit fields")
            fields.append("    created_ip = Column(String(45), nullable=True)  # IPv6 support")
            fields.append("    updated_ip = Column(String(45), nullable=True)")
            
        if auth_config.get("enable_soft_delete", False):
            fields.append("    # Soft delete support")
            fields.append("    is_deleted = Column(Boolean, default=False, nullable=False)")
            fields.append("    deleted_at = Column(DateTime, nullable=True)")
            fields.append("    deleted_by_id = Column(String, ForeignKey('users.id'), nullable=True)")
            
        if auth_config.get("enable_versioning", False):
            fields.append("    # Versioning support")
            fields.append("    version = Column(Integer, default=1, nullable=False)")
            fields.append("    revision_notes = Column(Text, nullable=True)")
        
        return '\n'.join(fields) if fields else ""
    
    def _generate_relationships(self, auth_config: Dict[str, Any]) -> str:
        """Generate SQLAlchemy relationships for authentication"""
        relationships = []
        
        if auth_config.get("enable_ownership", False):
            relationships.append("    # Ownership relationships")
            relationships.append("    created_by = relationship('User', foreign_keys=[created_by_id], lazy='select')")
            relationships.append("    updated_by = relationship('User', foreign_keys=[updated_by_id], lazy='select')")
            
        if auth_config.get("enable_soft_delete", False):
            relationships.append("    deleted_by = relationship('User', foreign_keys=[deleted_by_id], lazy='select')")
        
        return '\n'.join(relationships) if relationships else ""
    
    def _generate_imports(self, auth_config: Dict[str, Any]) -> str:
        """Generate additional imports based on configuration"""
        imports = []
        
        # Always needed for relationships if ownership is enabled
        if auth_config.get("enable_ownership", False) or auth_config.get("enable_soft_delete", False):
            pass  # ForeignKey already imported above
            
        return '\n'.join(imports) if imports else ""
    
    def _generate_dict_fields(self, fields: List[Dict[str, Any]], auth_config: Dict[str, Any]) -> str:
        """Generate dictionary fields for to_dict method including auth fields"""
        dict_fields = []
        
        # Add regular fields
        for field in fields:
            field_name = field['name']
            dict_fields.append(f"'{field_name}': self.{field_name}")
        
        # Add auth fields to dict output
        if auth_config.get("enable_ownership", False):
            dict_fields.extend([
                "'created_by_id': self.created_by_id",
                "'updated_by_id': self.updated_by_id"
            ])
            
        if auth_config.get("enable_audit", True):
            dict_fields.extend([
                "'created_ip': self.created_ip",
                "'updated_ip': self.updated_ip"
            ])
            
        if auth_config.get("enable_soft_delete", False):
            dict_fields.extend([
                "'is_deleted': self.is_deleted",
                "'deleted_at': self.deleted_at",
                "'deleted_by_id': self.deleted_by_id"
            ])
            
        if auth_config.get("enable_versioning", False):
            dict_fields.extend([
                "'version': self.version",
                "'revision_notes': self.revision_notes"
            ])
        
        return ',\n            '.join(dict_fields)
    
    def _generate_additional_methods(self, auth_config: Dict[str, Any], pascal_name: str, 
                                   fields: List[Dict[str, Any]]) -> str:
        """Generate additional methods based on authentication configuration"""
        methods = []
        
        if auth_config.get("enable_ownership", False):
            methods.append(self._generate_ownership_methods())
            
        if auth_config.get("enable_soft_delete", False):
            methods.append(self._generate_soft_delete_methods())
            
        if auth_config.get("enable_versioning", False):
            methods.append(self._generate_versioning_methods())
            
        # Always add security helpers
        methods.append(self._generate_security_methods(pascal_name))
        
        return '\n'.join(methods) if methods else ""
    
    def _generate_ownership_methods(self) -> str:
        """Generate ownership-related methods"""
        return '''
    def is_owned_by(self, user_id: str) -> bool:
        """Check if this resource is owned by the specified user"""
        return self.created_by_id == user_id
    
    def can_be_modified_by(self, user_id: str) -> bool:
        """Check if this resource can be modified by the specified user"""
        # Owner can always modify
        if self.created_by_id == user_id:
            return True
        # Add additional logic here (e.g., admin users, collaborators)
        return False
    
    def set_ownership(self, user_id: str, ip_address: str = None):
        """Set ownership information for new records"""
        self.created_by_id = user_id
        self.updated_by_id = user_id
        if ip_address:
            self.created_ip = ip_address
            self.updated_ip = ip_address
    
    def update_ownership(self, user_id: str, ip_address: str = None):
        """Update ownership information for existing records"""
        self.updated_by_id = user_id
        if ip_address:
            self.updated_ip = ip_address'''
    
    def _generate_soft_delete_methods(self) -> str:
        """Generate soft delete methods"""
        return '''
    
    def soft_delete(self, user_id: str = None):
        """Mark record as deleted without removing from database"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if user_id:
            self.deleted_by_id = user_id
    
    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_id = None
    
    @property
    def is_active(self) -> bool:
        """Check if record is not soft-deleted"""
        return not self.is_deleted'''
    
    def _generate_versioning_methods(self) -> str:
        """Generate versioning methods"""
        return '''
    
    def increment_version(self, notes: str = None):
        """Increment version number"""
        self.version += 1
        self.revision_notes = notes
    
    def get_version_info(self) -> dict:
        """Get version information"""
        return {
            'version': self.version,
            'revision_notes': self.revision_notes,
            'updated_at': self.updated_at,
            'updated_by_id': self.updated_by_id
        }'''
    
    def _generate_security_methods(self, pascal_name: str) -> str:
        """Generate security-related methods"""
        return f'''
    
    def to_dict_secure(self, user_id: str = None, is_admin: bool = False) -> dict:
        """Convert to dictionary with security filtering"""
        data = self.to_dict()
        
        # Remove sensitive fields for non-owners/non-admins
        if not is_admin and hasattr(self, 'created_by_id') and self.created_by_id != user_id:
            # Remove audit fields for non-owners
            data.pop('created_ip', None)
            data.pop('updated_ip', None)
            
        return data
    
    def get_audit_trail(self) -> dict:
        """Get audit trail information"""
        trail = {{
            'id': self.id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }}
        
        if hasattr(self, 'created_by_id'):
            trail.update({{
                'created_by_id': self.created_by_id,
                'updated_by_id': self.updated_by_id,
                'created_ip': self.created_ip,
                'updated_ip': self.updated_ip
            }})
            
        if hasattr(self, 'version'):
            trail.update({{
                'version': self.version,
                'revision_notes': self.revision_notes
            }})
            
        return trail
    
    @classmethod
    def get_resource_name(cls) -> str:
        """Get resource name for permission checks"""
        return "{pascal_name.lower()}"''' 