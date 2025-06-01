"""
Enterprise Configuration Module for Scaffold Generator v4

Handles authentication, authorization, and multi-tenancy configuration options.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AuthLevel(Enum):
    """Authentication levels"""
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class TenantScope(Enum):
    """Tenant scoping options"""
    NONE = "none"
    ORGANIZATION = "organization"
    USER = "user"


class CacheStrategy(Enum):
    """Caching strategies"""
    NONE = "none"
    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"


@dataclass
class AuthConfig:
    """Authentication configuration"""
    level: AuthLevel = AuthLevel.REQUIRED
    require_verification: bool = True
    mfa_enabled: bool = False
    session_management: bool = True
    rate_limiting: bool = True
    audit_logging: bool = True


@dataclass
class AuthorizationConfig:
    """Authorization configuration"""
    role_based: bool = True
    allowed_roles: List[str] = field(default_factory=lambda: ["ADMIN", "MANAGER"])
    permission_checking: bool = True
    resource_scoping: bool = True


@dataclass
class TenancyConfig:
    """Multi-tenancy configuration"""
    enabled: bool = False
    scope: TenantScope = TenantScope.ORGANIZATION
    isolation_level: str = "strict"  # strict, relaxed
    tenant_context_required: bool = True


@dataclass
class PerformanceConfig:
    """Performance and optimization configuration"""
    enable_caching: bool = False
    cache_strategy: CacheStrategy = CacheStrategy.MEMORY
    cache_ttl: int = 300
    bulk_operations: bool = True
    pagination_default: int = 20
    pagination_max: int = 1000


@dataclass
class ExportConfig:
    """Data export configuration"""
    enabled: bool = True
    formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    max_records: int = 10000
    async_export: bool = True


@dataclass
class AuditConfig:
    """Audit logging configuration"""
    enabled: bool = False
    track_changes: bool = True
    track_access: bool = True
    retention_days: int = 365


@dataclass
class EnterpriseConfig:
    """Complete enterprise configuration"""
    auth: AuthConfig = field(default_factory=AuthConfig)
    authorization: AuthorizationConfig = field(default_factory=AuthorizationConfig)
    tenancy: TenancyConfig = field(default_factory=TenancyConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    
    # Additional features
    enable_tasks: bool = False
    enable_webhooks: bool = False
    enable_notifications: bool = False
    enable_file_uploads: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "auth": {
                "level": self.auth.level.value,
                "require_verification": self.auth.require_verification,
                "mfa_enabled": self.auth.mfa_enabled,
                "session_management": self.auth.session_management,
                "rate_limiting": self.auth.rate_limiting,
                "audit_logging": self.auth.audit_logging
            },
            "authorization": {
                "role_based": self.authorization.role_based,
                "allowed_roles": self.authorization.allowed_roles,
                "permission_checking": self.authorization.permission_checking,
                "resource_scoping": self.authorization.resource_scoping
            },
            "tenancy": {
                "enabled": self.tenancy.enabled,
                "scope": self.tenancy.scope.value,
                "isolation_level": self.tenancy.isolation_level,
                "tenant_context_required": self.tenancy.tenant_context_required
            },
            "performance": {
                "enable_caching": self.performance.enable_caching,
                "cache_strategy": self.performance.cache_strategy.value,
                "cache_ttl": self.performance.cache_ttl,
                "bulk_operations": self.performance.bulk_operations,
                "pagination_default": self.performance.pagination_default,
                "pagination_max": self.performance.pagination_max
            },
            "export": {
                "enabled": self.export.enabled,
                "formats": self.export.formats,
                "max_records": self.export.max_records,
                "async_export": self.export.async_export
            },
            "audit": {
                "enabled": self.audit.enabled,
                "track_changes": self.audit.track_changes,
                "track_access": self.audit.track_access,
                "retention_days": self.audit.retention_days
            },
            "enable_tasks": self.enable_tasks,
            "enable_webhooks": self.enable_webhooks,
            "enable_notifications": self.enable_notifications,
            "enable_file_uploads": self.enable_file_uploads
        }
    
    @classmethod
    def from_interactive_prompt(cls) -> 'EnterpriseConfig':
        """Create configuration from interactive prompts"""
        print("\n🏢 ENTERPRISE CONFIGURATION")
        print("=" * 50)
        
        config = cls()
        
        # Authentication Configuration
        print("\n🔐 Authentication Settings:")
        auth_required = input("Require authentication? (y/n) [y]: ").strip().lower()
        config.auth.level = AuthLevel.NONE if auth_required == 'n' else AuthLevel.REQUIRED
        
        if config.auth.level != AuthLevel.NONE:
            config.auth.require_verification = input("Require email verification? (y/n) [y]: ").strip().lower() != 'n'
            config.auth.mfa_enabled = input("Enable MFA support? (y/n) [n]: ").strip().lower() == 'y'
            config.auth.rate_limiting = input("Enable rate limiting? (y/n) [y]: ").strip().lower() != 'n'
        
        # Multi-tenancy Configuration
        print("\n🏢 Multi-tenancy Settings:")
        tenancy_enabled = input("Enable multi-tenancy? (y/n) [n]: ").strip().lower() == 'y'
        config.tenancy.enabled = tenancy_enabled
        
        if tenancy_enabled:
            scope_choice = input("Tenant scope (organization/user) [organization]: ").strip().lower()
            config.tenancy.scope = TenantScope.USER if scope_choice == 'user' else TenantScope.ORGANIZATION
            
            isolation = input("Isolation level (strict/relaxed) [strict]: ").strip().lower()
            config.tenancy.isolation_level = isolation if isolation in ['strict', 'relaxed'] else 'strict'
        
        # Role-based Access Control
        print("\n👥 Authorization Settings:")
        if config.auth.level != AuthLevel.NONE:
            config.authorization.role_based = input("Enable role-based access control? (y/n) [y]: ").strip().lower() != 'n'
            
            if config.authorization.role_based:
                print("Available roles: OWNER, ADMIN, MANAGER, MEMBER, VIEWER")
                roles_input = input("Enter allowed roles (comma-separated) [ADMIN,MANAGER]: ").strip()
                if roles_input:
                    config.authorization.allowed_roles = [r.strip().upper() for r in roles_input.split(',')]
        
        # Performance Configuration
        print("\n⚡ Performance Settings:")
        config.performance.enable_caching = input("Enable response caching? (y/n) [n]: ").strip().lower() == 'y'
        
        if config.performance.enable_caching:
            cache_strategy = input("Cache strategy (memory/redis/hybrid) [memory]: ").strip().lower()
            if cache_strategy in ['redis', 'hybrid']:
                config.performance.cache_strategy = CacheStrategy.REDIS if cache_strategy == 'redis' else CacheStrategy.HYBRID
            
            ttl_input = input("Cache TTL in seconds [300]: ").strip()
            if ttl_input.isdigit():
                config.performance.cache_ttl = int(ttl_input)
        
        config.performance.bulk_operations = input("Enable bulk operations? (y/n) [y]: ").strip().lower() != 'n'
        
        # Export Configuration
        print("\n📤 Export Settings:")
        config.export.enabled = input("Enable data export? (y/n) [y]: ").strip().lower() != 'n'
        
        if config.export.enabled:
            formats_input = input("Export formats (csv,json,xlsx) [json,csv]: ").strip()
            if formats_input:
                config.export.formats = [f.strip() for f in formats_input.split(',')]
        
        # Audit Configuration
        print("\n📝 Audit Settings:")
        config.audit.enabled = input("Enable audit logging? (y/n) [n]: ").strip().lower() == 'y'
        
        if config.audit.enabled:
            config.audit.track_changes = input("Track data changes? (y/n) [y]: ").strip().lower() != 'n'
            config.audit.track_access = input("Track access logs? (y/n) [y]: ").strip().lower() != 'n'
        
        # Additional Features
        print("\n🚀 Additional Features:")
        config.enable_tasks = input("Enable background tasks? (y/n) [n]: ").strip().lower() == 'y'
        config.enable_webhooks = input("Enable webhooks? (y/n) [n]: ").strip().lower() == 'y'
        config.enable_file_uploads = input("Enable file uploads? (y/n) [n]: ").strip().lower() == 'y'
        
        return config
    
    @classmethod
    def get_preset(cls, preset_name: str) -> 'EnterpriseConfig':
        """Get predefined configuration presets"""
        presets = {
            "minimal": cls(
                auth=AuthConfig(level=AuthLevel.NONE),
                authorization=AuthorizationConfig(role_based=False),
                tenancy=TenancyConfig(enabled=False),
                performance=PerformanceConfig(enable_caching=False, bulk_operations=False),
                export=ExportConfig(enabled=False),
                audit=AuditConfig(enabled=False)
            ),
            "standard": cls(
                auth=AuthConfig(level=AuthLevel.REQUIRED, mfa_enabled=False),
                authorization=AuthorizationConfig(role_based=True),
                tenancy=TenancyConfig(enabled=False),
                performance=PerformanceConfig(enable_caching=True, bulk_operations=True),
                export=ExportConfig(enabled=True),
                audit=AuditConfig(enabled=False)
            ),
            "enterprise": cls(
                auth=AuthConfig(level=AuthLevel.REQUIRED, mfa_enabled=True, audit_logging=True),
                authorization=AuthorizationConfig(role_based=True, permission_checking=True),
                tenancy=TenancyConfig(enabled=True, scope=TenantScope.ORGANIZATION),
                performance=PerformanceConfig(enable_caching=True, cache_strategy=CacheStrategy.REDIS, bulk_operations=True),
                export=ExportConfig(enabled=True, async_export=True),
                audit=AuditConfig(enabled=True, track_changes=True, track_access=True),
                enable_tasks=True,
                enable_webhooks=True
            )
        }
        
        return presets.get(preset_name, presets["standard"])


class EnterpriseConfigManager:
    """Manages enterprise configuration for scaffold generation"""
    
    @staticmethod
    def prompt_for_config() -> EnterpriseConfig:
        """Interactive prompt for enterprise configuration"""
        print("\n🎯 Configuration Mode:")
        print("1. Interactive (custom configuration)")
        print("2. Preset: Minimal (no auth, basic features)")
        print("3. Preset: Standard (auth + basic enterprise)")
        print("4. Preset: Enterprise (full features)")
        
        choice = input("\nSelect configuration mode [2]: ").strip()
        
        if choice == "1":
            return EnterpriseConfig.from_interactive_prompt()
        elif choice == "3":
            return EnterpriseConfig.get_preset("standard")
        elif choice == "4":
            return EnterpriseConfig.get_preset("enterprise")
        else:  # Default to minimal
            return EnterpriseConfig.get_preset("minimal")
    
    @staticmethod
    def save_config(config: EnterpriseConfig, model_name: str):
        """Save configuration to file"""
        import json
        from pathlib import Path
        
        config_dir = Path("scaffold_configs")
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / f"{model_name.lower()}_config.json"
        with open(config_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        print(f"💾 Configuration saved to {config_file}")
    
    @staticmethod
    def load_config(model_name: str) -> Optional[EnterpriseConfig]:
        """Load configuration from file"""
        import json
        from pathlib import Path
        
        config_file = Path("scaffold_configs") / f"{model_name.lower()}_config.json"
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct config from dict (simplified)
            config = EnterpriseConfig()
            if 'auth' in data:
                config.auth.level = AuthLevel(data['auth'].get('level', 'required'))
                config.auth.require_verification = data['auth'].get('require_verification', True)
                config.auth.mfa_enabled = data['auth'].get('mfa_enabled', False)
            
            if 'tenancy' in data:
                config.tenancy.enabled = data['tenancy'].get('enabled', False)
                config.tenancy.scope = TenantScope(data['tenancy'].get('scope', 'organization'))
            
            # ... load other configs as needed
            
            return config
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}")
            return None 