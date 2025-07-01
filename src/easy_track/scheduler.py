import asyncio
import logging
from datetime import datetime, time
from typing import Optional
import pytz
from aiogram import Bot
from .database import DatabaseManager
from .repositories import NotificationScheduleRepository
from .i18n.translator import translator

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Handles periodic notification scheduling and sending."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the notification scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Notification scheduler started")

    async def stop(self):
        """Stop the notification scheduler."""
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self._check_and_send_notifications()
                # Check every minute
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _check_and_send_notifications(self):
        """Check for pending notifications and send them."""
        try:
            # Get current UTC time
            utc_now = datetime.now(pytz.UTC)

            # Check common timezones to avoid checking every user individually
            timezones_to_check = [
                "UTC", "Europe/Kiev", "Europe/Berlin",
                "Europe/Paris", "Europe/Madrid", "Europe/Rome",
                "America/New_York", "America/Los_Angeles"
            ]

            for tz_name in timezones_to_check:
                try:
                    # Convert UTC time to this timezone
                    tz = pytz.timezone(tz_name)
                    local_time = utc_now.astimezone(tz)
                    current_time = local_time.time()
                    current_day_of_week = local_time.weekday()

                    # Round to nearest minute for comparison
                    rounded_time = time(current_time.hour, current_time.minute)

                    # Get schedules for this specific time and timezone
                    async def _get_schedules_for_tz(session):
                        return await NotificationScheduleRepository.get_schedules_for_time_and_timezone(
                            session, rounded_time, current_day_of_week, tz_name
                        )

                    schedules = await DatabaseManager.execute_with_session(_get_schedules_for_tz)

                    for schedule in schedules:
                        try:
                            await self._send_notification(
                                schedule.user.telegram_id, schedule.user.language
                            )
                            logger.info(
                                f"Sent notification to user {schedule.user.telegram_id} "
                                f"at {local_time.strftime('%H:%M')} ({tz_name})"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to send notification to user "
                                f"{schedule.user.telegram_id}: {e}"
                            )

                except Exception as e:
                    logger.error(f"Error checking timezone {tz_name}: {e}")

        except Exception as e:
            logger.error(f"Error checking notifications: {e}")

    async def _send_notification(self, telegram_id: int, language: str):
        """Send a notification message to a user."""
        try:
            message = translator.get("notifications.reminder_message", language)
            await self.bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send notification to {telegram_id}: {e}")
            raise

    async def send_test_notification(self, telegram_id: int, language: str = "en"):
        """Send a test notification (for debugging)."""
        try:
            await self._send_notification(telegram_id, language)
            logger.info(f"Test notification sent to user {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
            raise


# Global scheduler instance
scheduler: Optional[NotificationScheduler] = None


def get_scheduler() -> Optional[NotificationScheduler]:
    """Get the global scheduler instance."""
    return scheduler


def set_scheduler(bot: Bot) -> NotificationScheduler:
    """Initialize and set the global scheduler instance."""
    global scheduler
    scheduler = NotificationScheduler(bot)
    return scheduler
