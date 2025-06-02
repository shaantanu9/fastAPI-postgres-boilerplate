"""
AWS SES Client Module

Handles AWS SES client initialization and basic operations like
account management, domain verification, and configuration sets.
"""

from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from loguru import logger

from app.core.config import settings
from .models import EmailAccountInfo


class SESClientError(Exception):
    """Custom exception for SES Client errors"""
    pass


class SESClient:
    """AWS SES Client wrapper for managing SES operations"""
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        configuration_set: Optional[str] = None,
        from_domain: Optional[str] = None,
        validate_connection: bool = False
    ):
        """
        Initialize SES Client
        
        Args:
            aws_access_key_id: AWS access key (if None, uses default credentials)
            aws_secret_access_key: AWS secret key (if None, uses default credentials)
            aws_region: AWS region for SES
            configuration_set: Default SES configuration set
            from_domain: Default from domain for emails
            validate_connection: Whether to validate connection during init
        """
        self.aws_region = aws_region
        self.default_configuration_set = configuration_set
        self.from_domain = from_domain
        self.is_initialized = False
        self.initialization_error = None
        
        # Store credentials for lazy initialization
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        
        # Initialize clients as None - will be created when needed
        self.ses_client = None
        self.ses_v1_client = None
        
        # Try to initialize if validate_connection is True
        if validate_connection:
            try:
                self._initialize_clients()
                self._test_connection()
            except Exception as e:
                logger.error(f"Failed to initialize SES client during init: {str(e)}")
                self.initialization_error = str(e)
        else:
            logger.info("SES Client created with lazy initialization - will connect when first used")
    
    def _initialize_clients(self):
        """Initialize AWS SES clients"""
        if self.is_initialized:
            return
            
        try:
            logger.debug(f"Initializing SES clients for region: {self.aws_region}")
            
            session_kwargs = {"region_name": self.aws_region}
            
            # Add credentials if provided
            if self._aws_access_key_id and self._aws_secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": self._aws_access_key_id,
                    "aws_secret_access_key": self._aws_secret_access_key
                })
                logger.debug("Using provided AWS credentials")
            else:
                logger.debug("Using default AWS credential chain")
            
            # Create clients
            self.ses_client = boto3.client('sesv2', **session_kwargs)
            self.ses_v1_client = boto3.client('ses', **session_kwargs)
            
            self.is_initialized = True
            logger.info(f"SES clients initialized successfully for region: {self.aws_region}")
            
        except NoCredentialsError as e:
            error_msg = "AWS credentials not found. Please configure AWS credentials via environment variables, AWS credentials file, or IAM roles."
            logger.error(error_msg)
            self.initialization_error = error_msg
            raise SESClientError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Failed to initialize SES clients: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            raise SESClientError(error_msg) from e
    
    def _test_connection(self):
        """Test SES connection"""
        try:
            logger.debug("Testing SES connection...")
            self.ses_client.get_account()
            logger.info("SES connection test successful")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'AccessDenied':
                error_msg = f"AWS SES access denied. Please check IAM permissions for SES operations. Error: {error_message}"
            else:
                error_msg = f"AWS SES API error ({error_code}): {error_message}"
                
            logger.error(error_msg)
            raise SESClientError(error_msg) from e
            
        except Exception as e:
            error_msg = f"SES connection test failed: {str(e)}"
            logger.error(error_msg)
            raise SESClientError(error_msg) from e
    
    def _ensure_initialized(self):
        """Ensure SES clients are initialized"""
        if not self.is_initialized:
            if self.initialization_error:
                raise SESClientError(f"SES client was not properly initialized: {self.initialization_error}")
            
            try:
                self._initialize_clients()
            except Exception as e:
                self.initialization_error = str(e)
                raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of SES client"""
        status = {
            "initialized": self.is_initialized,
            "region": self.aws_region,
            "configuration_set": self.default_configuration_set,
            "from_domain": self.from_domain,
            "error": self.initialization_error
        }
        
        if self.is_initialized:
            try:
                # Quick health check
                self.ses_client.get_account()
                status["connection"] = "healthy"
            except Exception as e:
                status["connection"] = "unhealthy"
                status["connection_error"] = str(e)
        else:
            status["connection"] = "not_connected"
            
        return status
    
    async def get_account_info(self) -> EmailAccountInfo:
        """Get SES account information and sending statistics"""
        try:
            self._ensure_initialized()
            logger.debug("Fetching SES account information...")
            
            account_info = self.ses_client.get_account()
            logger.debug("Account info retrieved successfully")
            
            # Get sending quota and rate
            quota_info = self.ses_v1_client.get_send_quota()
            logger.debug("Sending quota retrieved successfully")
            
            # Get sending statistics
            send_stats = self.ses_v1_client.get_send_statistics()
            logger.debug("Sending statistics retrieved successfully")
            
            logger.info("SES account information retrieved successfully")
            
            return EmailAccountInfo(
                account_details=account_info,
                sending_quota=quota_info,
                sending_statistics=send_stats
            )
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            error_msg = f"Failed to get SES account info - AWS Error ({error_code}): {error_message}"
            logger.error(error_msg)
            raise SESClientError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error getting account info: {str(e)}"
            logger.error(error_msg)
            raise SESClientError(error_msg) from e
    
    async def verify_domain_identity(self, domain: str) -> bool:
        """Verify domain identity in SES"""
        try:
            self._ensure_initialized()
            logger.debug(f"Starting domain verification for: {domain}")
            
            self.ses_client.create_email_identity(EmailIdentity=domain)
            logger.info(f"Domain identity verification initiated for: {domain}")
            return True
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'AlreadyExistsException':
                logger.info(f"Domain {domain} is already verified")
                return True
            elif error_code == 'LimitExceededException':
                logger.error(f"Domain verification limit exceeded for {domain}")
            else:
                logger.error(f"Failed to verify domain {domain} - AWS Error ({error_code}): {error_message}")
            
            return False
        except Exception as e:
            logger.error(f"Unexpected error verifying domain {domain}: {str(e)}")
            return False
    
    async def create_configuration_set(
        self,
        name: str,
        tracking_options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create SES configuration set"""
        try:
            self._ensure_initialized()
            logger.debug(f"Creating configuration set: {name}")
            
            config_set_data = {'ConfigurationSetName': name}
            
            if tracking_options:
                config_set_data['TrackingOptions'] = tracking_options
                logger.debug(f"Added tracking options: {tracking_options}")
            
            self.ses_client.create_configuration_set(**config_set_data)
            logger.info(f"Configuration set '{name}' created successfully")
            return True
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'AlreadyExistsException':
                logger.info(f"Configuration set '{name}' already exists")
                return True
            elif error_code == 'LimitExceededException':
                logger.error(f"Configuration set limit exceeded")
            else:
                logger.error(f"Failed to create configuration set '{name}' - AWS Error ({error_code}): {error_message}")
            
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating configuration set '{name}': {str(e)}")
            return False
    
    async def create_template(
        self,
        template_name: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Create SES email template
        
        Args:
            template_name: Unique template name
            subject: Email subject with template variables
            html_content: HTML content with template variables
            text_content: Text content with template variables
        
        Returns:
            True if template created successfully
        """
        try:
            self._ensure_initialized()
            logger.debug(f"Creating email template: {template_name}")
            
            template_data = {
                'TemplateName': template_name,
                'SubjectPart': subject
            }
            
            if html_content:
                template_data['HtmlPart'] = html_content
                logger.debug("HTML content added to template")
            
            if text_content:
                template_data['TextPart'] = text_content
                logger.debug("Text content added to template")
            
            self.ses_v1_client.create_template(Template=template_data)
            logger.info(f"Email template '{template_name}' created successfully")
            return True
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'AlreadyExistsException':
                logger.info(f"Template '{template_name}' already exists")
                return True
            else:
                logger.error(f"Failed to create template '{template_name}' - AWS Error ({error_code}): {error_message}")
            
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating template '{template_name}': {str(e)}")
            return False
    
    async def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get SES email template by name"""
        try:
            self._ensure_initialized()
            logger.debug(f"Retrieving template: {template_name}")
            
            response = self.ses_v1_client.get_template(TemplateName=template_name)
            logger.info(f"Template '{template_name}' retrieved successfully")
            return response.get('Template')
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'TemplateDoesNotExistException':
                logger.warning(f"Template '{template_name}' does not exist")
            else:
                logger.error(f"Failed to get template '{template_name}' - AWS Error ({error_code}): {error_message}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting template '{template_name}': {str(e)}")
            return None
    
    async def delete_template(self, template_name: str) -> bool:
        """Delete SES email template"""
        try:
            self._ensure_initialized()
            logger.debug(f"Deleting template: {template_name}")
            
            self.ses_v1_client.delete_template(TemplateName=template_name)
            logger.info(f"Email template '{template_name}' deleted successfully")
            return True
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'TemplateDoesNotExistException':
                logger.warning(f"Template '{template_name}' does not exist")
                return True
            else:
                logger.error(f"Failed to delete template '{template_name}' - AWS Error ({error_code}): {error_message}")
            
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting template '{template_name}': {str(e)}")
            return False
    
    async def list_templates(self) -> List[str]:
        """List all SES email templates"""
        try:
            self._ensure_initialized()
            logger.debug("Listing all SES templates...")
            
            response = self.ses_v1_client.list_templates()
            templates = [template['Name'] for template in response.get('TemplatesMetadata', [])]
            
            logger.info(f"Retrieved {len(templates)} templates")
            return templates
            
        except SESClientError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to list templates - AWS Error ({error_code}): {error_message}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing templates: {str(e)}")
            return []


def create_ses_client(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    validate_connection: bool = False
) -> SESClient:
    """
    Factory function to create configured SES client
    
    Args:
        aws_access_key_id: AWS access key (optional, uses settings if None)
        aws_secret_access_key: AWS secret key (optional, uses settings if None)
        validate_connection: Whether to validate connection during creation
    
    Returns:
        Configured SESClient instance
    """
    try:
        logger.debug("Creating SES client with factory function")
        
        client = SESClient(
            aws_access_key_id=aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
            aws_region=settings.AWS_REGION or "us-east-1",
            configuration_set=settings.SES_CONFIGURATION_SET,
            from_domain=settings.EMAIL_FROM_DOMAIN,
            validate_connection=validate_connection
        )
        
        logger.debug("SES client created successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create SES client: {str(e)}")
        raise SESClientError(f"Failed to create SES client: {str(e)}") from e 