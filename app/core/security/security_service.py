"""
Security service module that provides enterprise security features.
This module initializes and exports the security_service singleton.
"""

# Import directly from the module where EnterpriseSecurityService is defined
from app.core.security_base import EnterpriseSecurityService

# Initialize the security service as a singleton
security_service = EnterpriseSecurityService()
