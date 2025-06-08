"""Email Sender Module.

Handles the core email sending functionality including simple emails,
emails with attachments, and bulk email operations.
"""

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from uuid import uuid4

from botocore.exceptions import ClientError
from loguru import logger

from .attachments import AttachmentHandler
from .client import SESClient, SESClientError
from .models import EmailRecipient, EmailRequest, EmailResponse


class EmailSenderError(Exception):
    """Custom exception for Email Sender errors."""



class EmailSender:
    """Handles email sending operations."""

    def __init__(self, ses_client: SESClient) -> None:
        """Initialize EmailSender.

        Args:
            ses_client: Configured SES client

        """
        if not ses_client:
            msg = "SES client is required"
            raise EmailSenderError(msg)

        self.ses_client = ses_client
        self.attachment_handler = AttachmentHandler()
        logger.debug("EmailSender initialized successfully")

    async def send_email(
        self, email_request: EmailRequest, immediate: bool = True,
    ) -> EmailResponse:
        """Send email immediately.

        Args:
            email_request: Email request object
            immediate: If True, send immediately

        Returns:
            EmailResponse object with sending results

        """
        try:
            logger.debug(
                f"Starting email send process for tracking ID: {email_request.tracking_id}",
            )

            # Validate request
            await self._validate_email_request(email_request)

            # Send immediately
            return await self._send_immediate_email(email_request)

        except EmailSenderError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error in send_email: {e!s}"
            logger.error(error_msg)
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=error_msg,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )

    async def _send_immediate_email(self, email_request: EmailRequest) -> EmailResponse:
        """Send email immediately using SES."""
        try:
            # Check if we have attachments - use different methods
            if email_request.attachments:
                logger.debug(
                    f"Sending email with {len(email_request.attachments)} attachments",
                )
                message_id = await self._send_raw_email_with_attachments(email_request)
            else:
                logger.debug("Sending simple email without attachments")
                message_id = await self._send_simple_email(email_request)

            logger.info(
                f"Email sent successfully. Message ID: {message_id}, Tracking ID: {email_request.tracking_id}",
            )

            return EmailResponse(
                success=True,
                message_id=message_id,
                tracking_id=email_request.tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="sent",
            )

        except SESClientError as e:
            logger.error(f"SES client error: {e!s}")
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=f"SES client error: {e!s}",
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            # Provide specific error messages for common issues
            if error_code == "MessageRejected":
                detailed_error = f"Message rejected by SES: {error_message}"
            elif error_code == "SendingPausedException":
                detailed_error = f"SES sending paused: {error_message}"
            elif error_code == "MailFromDomainNotVerifiedException":
                detailed_error = f"Sender domain not verified: {error_message}"
            elif error_code == "ConfigurationSetDoesNotExistException":
                detailed_error = f"Configuration set does not exist: {error_message}"
            else:
                detailed_error = f"AWS SES error ({error_code}): {error_message}"

            logger.error(f"SES ClientError: {detailed_error}")

            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=detailed_error,
                error_code=error_code,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )
        except Exception as e:
            error_msg = f"Unexpected error sending email: {e!s}"
            logger.error(error_msg)
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=error_msg,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )

    async def _send_simple_email(self, email_request: EmailRequest) -> str:
        """Send simple email without attachments using SES v2 API."""
        try:
            # Ensure SES client is initialized
            self.ses_client._ensure_initialized()

            subject, html_content, text_content = email_request.get_rendered_content()
            logger.debug(f"Rendered email content - Subject: {subject[:50]}...")

            # Prepare destinations
            destination = {}
            if email_request.to_recipients:
                destination["ToAddresses"] = [
                    r.email for r in email_request.to_recipients
                ]
                logger.debug(f"TO recipients: {len(email_request.to_recipients)}")
            if email_request.cc_recipients:
                destination["CcAddresses"] = [
                    r.email for r in email_request.cc_recipients
                ]
                logger.debug(f"CC recipients: {len(email_request.cc_recipients)}")
            if email_request.bcc_recipients:
                destination["BccAddresses"] = [
                    r.email for r in email_request.bcc_recipients
                ]
                logger.debug(f"BCC recipients: {len(email_request.bcc_recipients)}")

            # Prepare message body
            body = {}
            if html_content:
                body["Html"] = {"Data": html_content, "Charset": "UTF-8"}
                logger.debug("HTML content included")
            if text_content:
                body["Text"] = {"Data": text_content, "Charset": "UTF-8"}
                logger.debug("Text content included")

            if not body:
                msg = "Email must have either HTML or text content"
                raise EmailSenderError(msg)

            # Prepare email request
            email_params = {
                "FromEmailAddress": email_request.from_email,
                "Destination": destination,
                "Content": {
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": body,
                    },
                },
            }

            # Add configuration set if specified
            if (
                email_request.configuration_set
                or self.ses_client.default_configuration_set
            ):
                config_set = (
                    email_request.configuration_set
                    or self.ses_client.default_configuration_set
                )
                email_params["ConfigurationSetName"] = config_set
                logger.debug(f"Using configuration set: {config_set}")

            # Add reply-to addresses
            if email_request.reply_to:
                email_params["ReplyToAddresses"] = email_request.reply_to
                logger.debug(f"Reply-to addresses: {email_request.reply_to}")

            # Add message tags
            if email_request.message_tags:
                email_params["EmailTags"] = [
                    {"Name": key, "Value": value}
                    for key, value in email_request.message_tags.items()
                ]
                logger.debug(f"Message tags: {email_request.message_tags}")

            # Send email
            logger.debug("Sending email via SES v2 API...")
            response = self.ses_client.ses_client.send_email(**email_params)
            message_id = response["MessageId"]

            logger.debug(
                f"Email sent successfully via SES v2 API, Message ID: {message_id}",
            )
            return message_id

        except Exception as e:
            logger.error(f"Error in _send_simple_email: {e!s}")
            raise

    async def _send_raw_email_with_attachments(
        self, email_request: EmailRequest,
    ) -> str:
        """Send email with attachments using raw email format."""
        try:
            # Ensure SES client is initialized
            self.ses_client._ensure_initialized()

            subject, html_content, text_content = email_request.get_rendered_content()
            logger.debug(
                f"Preparing raw email with attachments - Subject: {subject[:50]}...",
            )

            # Create multipart message
            msg = MIMEMultipart("mixed")

            # Set headers
            msg["Subject"] = subject
            msg["From"] = (
                formataddr((email_request.from_name, email_request.from_email))
                if email_request.from_name
                else email_request.from_email
            )
            msg["To"] = ", ".join(
                [r.format_address() for r in email_request.to_recipients],
            )

            if email_request.cc_recipients:
                msg["Cc"] = ", ".join(
                    [r.format_address() for r in email_request.cc_recipients],
                )
                logger.debug(f"CC recipients added: {len(email_request.cc_recipients)}")

            if email_request.reply_to:
                msg["Reply-To"] = ", ".join(email_request.reply_to)
                logger.debug(f"Reply-To added: {email_request.reply_to}")

            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain=self.ses_client.from_domain)

            # Add tracking headers
            msg["X-Tracking-ID"] = email_request.tracking_id
            if email_request.campaign_id:
                msg["X-Campaign-ID"] = email_request.campaign_id
                logger.debug(f"Campaign ID added: {email_request.campaign_id}")

            # Create body container
            body_container = MIMEMultipart("alternative")

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                body_container.attach(text_part)
                logger.debug("Text content added to email")

            # Add HTML content
            if html_content:
                html_part = MIMEText(html_content, "html", "utf-8")
                body_container.attach(html_part)
                logger.debug("HTML content added to email")

            if not text_content and not html_content:
                msg = "Email must have either HTML or text content"
                raise EmailSenderError(msg)

            msg.attach(body_container)

            # Add attachments
            logger.debug(f"Adding {len(email_request.attachments)} attachments...")
            for i, attachment in enumerate(email_request.attachments, 1):
                try:
                    await self.attachment_handler.add_attachment_to_message(
                        msg, attachment,
                    )
                    logger.debug(
                        f"Attachment {i}/{len(email_request.attachments)} added: {attachment.filename}",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to add attachment {attachment.filename}: {e!s}",
                    )
                    msg = f"Failed to add attachment {attachment.filename}: {e!s}"
                    raise EmailSenderError(
                        msg,
                    ) from e

            # Prepare destinations
            destinations = []
            destinations.extend([r.email for r in email_request.to_recipients])
            if email_request.cc_recipients:
                destinations.extend([r.email for r in email_request.cc_recipients])
            if email_request.bcc_recipients:
                destinations.extend([r.email for r in email_request.bcc_recipients])

            logger.debug(f"Total destinations: {len(destinations)}")

            # Prepare raw email parameters
            raw_email_params = {
                "Source": email_request.from_email,
                "Destinations": destinations,
                "RawMessage": {"Data": msg.as_string()},
            }

            # Add configuration set if specified
            if (
                email_request.configuration_set
                or self.ses_client.default_configuration_set
            ):
                config_set = (
                    email_request.configuration_set
                    or self.ses_client.default_configuration_set
                )
                raw_email_params["ConfigurationSetName"] = config_set
                logger.debug(f"Using configuration set: {config_set}")

            # Send raw email
            logger.debug("Sending raw email via SES v1 API...")
            response = self.ses_client.ses_v1_client.send_raw_email(**raw_email_params)
            message_id = response["MessageId"]

            logger.debug(
                f"Raw email sent successfully via SES v1 API, Message ID: {message_id}",
            )
            return message_id

        except Exception as e:
            logger.error(f"Error in _send_raw_email_with_attachments: {e!s}")
            raise

    async def send_template_email(
        self,
        to_recipients: list[str | EmailRecipient],
        template_name: str,
        template_data: dict,
        from_email: str,
        cc_recipients: list[str | EmailRecipient] | None = None,
        bcc_recipients: list[str | EmailRecipient] | None = None,
        from_name: str | None = None,
        configuration_set: str | None = None,
    ) -> EmailResponse:
        """Send email using SES template.

        Args:
            to_recipients: List of TO recipients
            template_name: SES template name
            template_data: Template data for rendering
            from_email: Sender email address
            cc_recipients: List of CC recipients
            bcc_recipients: List of BCC recipients
            from_name: Sender name
            configuration_set: SES configuration set

        Returns:
            EmailResponse object

        """
        try:
            # Ensure SES client is initialized
            self.ses_client._ensure_initialized()

            logger.debug(f"Sending template email: {template_name}")

            # Convert string recipients to EmailRecipient objects
            def convert_recipients(recipients):
                if not recipients:
                    return []
                converted = []
                for r in recipients:
                    if isinstance(r, EmailRecipient):
                        converted.append(r)
                    else:
                        converted.append(EmailRecipient(email=r))
                return converted

            to_list = convert_recipients(to_recipients)
            cc_list = convert_recipients(cc_recipients)
            bcc_list = convert_recipients(bcc_recipients)

            logger.debug(
                f"Recipients - TO: {len(to_list)}, CC: {len(cc_list)}, BCC: {len(bcc_list)}",
            )

            # Prepare destinations
            destinations = []
            for recipient in to_list + cc_list + bcc_list:
                destinations.append(
                    {
                        "Destination": {"ToAddresses": [recipient.email]},
                        "ReplacementTemplateData": "{}",
                    },
                )

            # Prepare bulk email parameters
            bulk_email_params = {
                "Source": from_email,
                "Template": template_name,
                "DefaultTemplateData": str(template_data),
                "Destinations": destinations,
            }

            # Add configuration set if specified
            if configuration_set or self.ses_client.default_configuration_set:
                config_set = (
                    configuration_set or self.ses_client.default_configuration_set
                )
                bulk_email_params["ConfigurationSetName"] = config_set
                logger.debug(f"Using configuration set: {config_set}")

            # Send bulk template email
            logger.debug("Sending bulk template email via SES v1 API...")
            response = self.ses_client.ses_v1_client.send_bulk_templated_email(
                **bulk_email_params,
            )

            tracking_id = str(uuid4())

            logger.info(
                f"Template email sent successfully. Template: {template_name}, Tracking ID: {tracking_id}",
            )

            return EmailResponse(
                success=True,
                message_id=response.get("MessageId"),
                tracking_id=tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="sent",
            )

        except SESClientError as e:
            error_msg = f"SES client error sending template email: {e!s}"
            logger.error(error_msg)
            return EmailResponse(
                success=False,
                tracking_id=str(uuid4()),
                error_message=error_msg,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "TemplateDoesNotExistException":
                detailed_error = f"Template '{template_name}' does not exist"
            elif error_code == "InvalidTemplateException":
                detailed_error = (
                    f"Template '{template_name}' is invalid: {error_message}"
                )
            else:
                detailed_error = f"AWS SES error ({error_code}): {error_message}"

            logger.error(f"Template email error: {detailed_error}")

            return EmailResponse(
                success=False,
                tracking_id=str(uuid4()),
                error_message=detailed_error,
                error_code=error_code,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )
        except Exception as e:
            error_msg = f"Unexpected error sending template email: {e!s}"
            logger.error(error_msg)
            return EmailResponse(
                success=False,
                tracking_id=str(uuid4()),
                error_message=error_msg,
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )

    async def _validate_email_request(self, email_request: EmailRequest) -> None:
        """Validate email request before sending."""
        try:
            logger.debug("Validating email request...")

            # Check recipients
            if not email_request.to_recipients and not email_request.bcc_recipients:
                msg = "At least one recipient (TO or BCC) is required"
                raise EmailSenderError(msg)

            # Validate email addresses
            all_recipients = []
            if email_request.to_recipients:
                all_recipients.extend(email_request.to_recipients)
            if email_request.cc_recipients:
                all_recipients.extend(email_request.cc_recipients)
            if email_request.bcc_recipients:
                all_recipients.extend(email_request.bcc_recipients)

            for recipient in all_recipients:
                if not recipient.email or "@" not in recipient.email:
                    msg = f"Invalid email address: {recipient.email}"
                    raise EmailSenderError(msg)

            # Check content
            if not any(
                [
                    email_request.html_content,
                    email_request.text_content,
                    email_request.template,
                ],
            ):
                msg = "Email content (HTML, text, or template) is required"
                raise EmailSenderError(
                    msg,
                )

            # Check subject
            if not email_request.subject and not email_request.template:
                msg = "Email subject is required"
                raise EmailSenderError(msg)

            # Check from email
            if not email_request.from_email or "@" not in email_request.from_email:
                msg = f"Valid from_email is required: {email_request.from_email}"
                raise EmailSenderError(
                    msg,
                )

            # Validate sender domain if configured
            if self.ses_client.from_domain and not email_request.from_email.endswith(
                f"@{self.ses_client.from_domain}",
            ):
                logger.warning(
                    f"Sender email {email_request.from_email} does not match configured domain {self.ses_client.from_domain}",
                )

            # Validate attachments if present
            if email_request.attachments:
                logger.debug(
                    f"Validating {len(email_request.attachments)} attachments...",
                )
                is_valid, errors = self.attachment_handler.validate_attachments(
                    email_request.attachments,
                )
                if not is_valid:
                    msg = f"Attachment validation failed: {'; '.join(errors)}"
                    raise EmailSenderError(
                        msg,
                    )

            logger.debug("Email request validation passed")

        except EmailSenderError:
            raise
        except Exception as e:
            msg = f"Email validation failed: {e!s}"
            raise EmailSenderError(msg) from e

    async def send_bulk_emails(
        self, email_requests: list[EmailRequest],
    ) -> list[EmailResponse]:
        """Send multiple emails in batch.

        Args:
            email_requests: List of email requests

        Returns:
            List of EmailResponse objects

        """
        if not email_requests:
            logger.warning("No email requests provided for bulk sending")
            return []

        logger.debug(f"Starting bulk email send for {len(email_requests)} emails")
        responses = []
        successful_count = 0

        for i, email_request in enumerate(email_requests, 1):
            try:
                logger.debug(
                    f"Sending bulk email {i}/{len(email_requests)}: {email_request.tracking_id}",
                )
                response = await self.send_email(email_request)
                responses.append(response)

                if response.success:
                    successful_count += 1
                    logger.debug(f"Bulk email {i} sent successfully")
                else:
                    logger.warning(f"Bulk email {i} failed: {response.error_message}")

            except Exception as e:
                error_msg = f"Error sending bulk email {i}: {e!s}"
                logger.error(error_msg)
                responses.append(
                    EmailResponse(
                        success=False,
                        tracking_id=email_request.tracking_id,
                        error_message=error_msg,
                        timestamp=datetime.utcnow(),
                        delivery_status="failed",
                    ),
                )

        logger.info(
            f"Bulk email sending completed: {successful_count}/{len(email_requests)} successful",
        )
        return responses
