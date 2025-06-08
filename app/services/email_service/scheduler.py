"""Email Scheduler Module.

Handles scheduled email operations using Procrastinate for job queue management.
"""

from datetime import datetime
from typing import Any

import procrastinate
from loguru import logger

from .client import create_ses_client
from .models import EmailRequest, EmailResponse
from .sender import EmailSender


class EmailScheduler:
    """Handles scheduled email operations."""

    def __init__(self, procrastinate_app: procrastinate.App | None = None) -> None:
        """Initialize EmailScheduler.

        Args:
            procrastinate_app: Procrastinate app for job scheduling

        """
        self.procrastinate_app = procrastinate_app

        # Register the scheduled email task if procrastinate app is provided
        if self.procrastinate_app:
            self._register_tasks()

    def _register_tasks(self) -> None:
        """Register Procrastinate tasks."""

        @self.procrastinate_app.task(name="send_scheduled_email")
        async def send_scheduled_email_task(email_request_dict: dict[str, Any]):
            """Procrastinate task to send scheduled emails."""
            try:
                # Reconstruct email request
                email_request = EmailRequest(**email_request_dict)

                # Initialize SES client and sender
                ses_client = create_ses_client()
                email_sender = EmailSender(ses_client)

                # Send email
                response = await email_sender.send_email(email_request)

                if response.success:
                    logger.info(
                        f"Scheduled email sent successfully. Tracking ID: {response.tracking_id}",
                    )
                else:
                    logger.error(
                        f"Failed to send scheduled email. Tracking ID: {response.tracking_id}, Error: {response.error_message}",
                    )

                return response.dict()

            except Exception as e:
                logger.error(f"Error in scheduled email task: {e!s}")
                raise

        # Store the task function for later use
        self.send_scheduled_email_task = send_scheduled_email_task

    async def schedule_email(
        self, email_request: EmailRequest, send_time: datetime | None = None,
    ) -> EmailResponse:
        """Schedule email for later sending.

        Args:
            email_request: Email request object
            send_time: When to send the email (uses email_request.send_time if None)

        Returns:
            EmailResponse object indicating scheduling status

        """
        if not self.procrastinate_app:
            msg = "Procrastinate app not configured for scheduled emails"
            raise ValueError(msg)

        # Use provided send_time or email_request.send_time
        send_time = send_time or email_request.send_time or datetime.utcnow()

        try:
            # Schedule job
            job = await self.procrastinate_app.defer_async(
                task_name="send_scheduled_email",
                email_request_dict=email_request.dict(),
                schedule_at=send_time,
            )

            logger.info(
                f"Email scheduled for {send_time}. Job ID: {job.id}, Tracking ID: {email_request.tracking_id}",
            )

            return EmailResponse(
                success=True,
                tracking_id=email_request.tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="scheduled",
            )

        except Exception as e:
            logger.error(f"Error scheduling email: {e!s}")
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                delivery_status="failed",
            )

    async def schedule_bulk_emails(
        self, email_requests: list[EmailRequest], send_time: datetime | None = None,
    ) -> list[EmailResponse]:
        """Schedule multiple emails for later sending.

        Args:
            email_requests: List of email requests
            send_time: When to send the emails

        Returns:
            List of EmailResponse objects

        """
        responses = []

        for email_request in email_requests:
            try:
                # Set send time for each email
                if send_time:
                    email_request.send_time = send_time

                response = await self.schedule_email(email_request)
                responses.append(response)

            except Exception as e:
                logger.error(
                    f"Error scheduling bulk email {email_request.tracking_id}: {e!s}",
                )
                responses.append(
                    EmailResponse(
                        success=False,
                        tracking_id=email_request.tracking_id,
                        error_message=str(e),
                        timestamp=datetime.utcnow(),
                        delivery_status="failed",
                    ),
                )

        return responses

    async def cancel_scheduled_email(self, job_id: str) -> bool:
        """Cancel a scheduled email job.

        Args:
            job_id: Procrastinate job ID

        Returns:
            True if cancelled successfully

        """
        if not self.procrastinate_app:
            msg = "Procrastinate app not configured"
            raise ValueError(msg)

        try:
            # Note: This would need to be implemented based on Procrastinate's API
            # for job cancellation. This is a placeholder.
            logger.info(f"Attempting to cancel scheduled email job: {job_id}")
            # job = await self.procrastinate_app.cancel_job(job_id)
            return True

        except Exception as e:
            logger.error(f"Error cancelling scheduled email job {job_id}: {e!s}")
            return False

    async def get_scheduled_jobs(self) -> list[dict]:
        """Get list of scheduled email jobs.

        Returns:
            List of scheduled job information

        """
        if not self.procrastinate_app:
            msg = "Procrastinate app not configured"
            raise ValueError(msg)

        try:
            # Note: This would need to be implemented based on Procrastinate's API
            # for querying jobs. This is a placeholder.
            logger.info("Fetching scheduled email jobs")
            # jobs = await self.procrastinate_app.get_scheduled_jobs()
            return []

        except Exception as e:
            logger.error(f"Error fetching scheduled email jobs: {e!s}")
            return []


def create_email_scheduler(
    procrastinate_app: procrastinate.App | None = None,
) -> EmailScheduler:
    """Factory function to create configured EmailScheduler.

    Args:
        procrastinate_app: Procrastinate app for scheduling

    Returns:
        Configured EmailScheduler instance

    """
    return EmailScheduler(procrastinate_app=procrastinate_app)
