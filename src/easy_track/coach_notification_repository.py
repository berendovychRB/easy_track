import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CoachNotificationPreference,
    CoachNotificationQueue,
    CoachNotificationType,
)

logger = logging.getLogger(__name__)


class CoachNotificationRepository:
    """Repository for coach notification operations."""

    @staticmethod
    async def create_notification_preference(
        session: AsyncSession,
        coach_id: int,
        notification_type: CoachNotificationType,
        is_enabled: bool = True,
    ) -> CoachNotificationPreference:
        """Create or update coach notification preference."""
        try:
            # Check if preference already exists
            existing = await CoachNotificationRepository.get_notification_preference(
                session, coach_id, notification_type
            )

            if existing:
                existing.is_enabled = is_enabled
                await session.flush()
                return existing

            # Create new preference
            preference = CoachNotificationPreference(
                coach_id=coach_id,
                notification_type=notification_type,
                is_enabled=is_enabled,
            )
            session.add(preference)
            await session.flush()

            logger.debug(
                f"Created notification preference for coach {coach_id}, type {notification_type}"
            )
            return preference

        except Exception as e:
            logger.error(f"Error creating notification preference: {e}")
            raise

    @staticmethod
    async def get_notification_preference(
        session: AsyncSession, coach_id: int, notification_type: CoachNotificationType
    ) -> CoachNotificationPreference | None:
        """Get specific notification preference."""
        try:
            result = await session.execute(
                select(CoachNotificationPreference).where(
                    CoachNotificationPreference.coach_id == coach_id,
                    CoachNotificationPreference.notification_type == notification_type,
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting notification preference: {e}")
            raise

    @staticmethod
    async def get_coach_notification_preferences(
        session: AsyncSession, coach_id: int
    ) -> list[CoachNotificationPreference]:
        """Get all notification preferences for a coach."""
        try:
            result = await session.execute(
                select(CoachNotificationPreference)
                .where(CoachNotificationPreference.coach_id == coach_id)
                .order_by(CoachNotificationPreference.notification_type)
            )
            preferences = result.scalars().all()

            logger.debug(
                f"Found {len(preferences)} notification preferences for coach {coach_id}"
            )
            return preferences

        except Exception as e:
            logger.error(f"Error getting coach notification preferences: {e}")
            raise

    @staticmethod
    async def is_notification_enabled(
        session: AsyncSession, coach_id: int, notification_type: CoachNotificationType
    ) -> bool:
        """Check if notification type is enabled for coach."""
        try:
            preference = await CoachNotificationRepository.get_notification_preference(
                session, coach_id, notification_type
            )

            # Default to enabled if no preference exists
            return preference.is_enabled if preference else True

        except Exception as e:
            logger.error(f"Error checking if notification is enabled: {e}")
            return False

    @staticmethod
    async def queue_notification(
        session: AsyncSession,
        coach_id: int,
        athlete_id: int,
        notification_type: CoachNotificationType,
        message: str,
        measurement_id: int | None = None,
        scheduled_at: datetime | None = None,
    ) -> CoachNotificationQueue:
        """Queue a notification for delivery."""
        try:
            if scheduled_at is None:
                scheduled_at = datetime.now()

            notification = CoachNotificationQueue(
                coach_id=coach_id,
                athlete_id=athlete_id,
                notification_type=notification_type,
                message=message,
                measurement_id=measurement_id,
                scheduled_at=scheduled_at,
                is_sent=False,
            )
            session.add(notification)
            await session.flush()

            logger.debug(
                f"Queued notification for coach {coach_id}, athlete {athlete_id}, type {notification_type}"
            )
            return notification

        except Exception as e:
            logger.error(f"Error queueing notification: {e}")
            raise

    @staticmethod
    async def get_pending_notifications(
        session: AsyncSession, limit: int = 100
    ) -> list[CoachNotificationQueue]:
        """Get pending notifications to be sent."""
        try:
            result = await session.execute(
                select(CoachNotificationQueue)
                .options(
                    selectinload(CoachNotificationQueue.coach),
                    selectinload(CoachNotificationQueue.athlete),
                    selectinload(CoachNotificationQueue.measurement),
                )
                .where(
                    CoachNotificationQueue.is_sent.is_(False),
                    CoachNotificationQueue.scheduled_at <= datetime.now(),
                )
                .order_by(CoachNotificationQueue.scheduled_at)
                .limit(limit)
            )
            notifications = result.scalars().all()

            logger.debug(f"Found {len(notifications)} pending notifications")
            return notifications

        except Exception as e:
            logger.error(f"Error getting pending notifications: {e}")
            raise

    @staticmethod
    async def mark_notification_sent(
        session: AsyncSession, notification_id: int
    ) -> bool:
        """Mark notification as sent."""
        try:
            result = await session.execute(
                select(CoachNotificationQueue).where(
                    CoachNotificationQueue.id == notification_id
                )
            )
            notification = result.scalar_one_or_none()

            if notification:
                notification.is_sent = True
                notification.sent_at = datetime.now()
                await session.flush()
                logger.debug(f"Marked notification {notification_id} as sent")
                return True

            return False

        except Exception as e:
            logger.error(f"Error marking notification as sent: {e}")
            raise

    @staticmethod
    async def get_coach_notification_history(
        session: AsyncSession, coach_id: int, days: int = 30, limit: int = 50
    ) -> list[CoachNotificationQueue]:
        """Get notification history for a coach."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            result = await session.execute(
                select(CoachNotificationQueue)
                .options(
                    selectinload(CoachNotificationQueue.athlete),
                    selectinload(CoachNotificationQueue.measurement),
                )
                .where(
                    CoachNotificationQueue.coach_id == coach_id,
                    CoachNotificationQueue.created_at >= cutoff_date,
                )
                .order_by(desc(CoachNotificationQueue.created_at))
                .limit(limit)
            )
            notifications = result.scalars().all()

            logger.debug(
                f"Found {len(notifications)} notifications for coach {coach_id} in last {days} days"
            )
            return notifications

        except Exception as e:
            logger.error(f"Error getting coach notification history: {e}")
            raise

    @staticmethod
    async def cleanup_old_notifications(session: AsyncSession, days: int = 90) -> int:
        """Clean up old sent notifications."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            result = await session.execute(
                select(func.count(CoachNotificationQueue.id)).where(
                    CoachNotificationQueue.is_sent.is_(True),
                    CoachNotificationQueue.sent_at < cutoff_date,
                )
            )
            count_before = result.scalar()

            # Delete old notifications
            await session.execute(
                select(CoachNotificationQueue).where(
                    CoachNotificationQueue.is_sent.is_(True),
                    CoachNotificationQueue.sent_at < cutoff_date,
                )
            )

            await session.flush()
            logger.info(
                f"Cleaned up {count_before} old notifications older than {days} days"
            )
            return count_before

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
            raise

    @staticmethod
    async def get_notification_stats(
        session: AsyncSession, coach_id: int, days: int = 30
    ) -> dict[str, int]:
        """Get notification statistics for a coach."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            # Total notifications
            total_result = await session.execute(
                select(func.count(CoachNotificationQueue.id)).where(
                    CoachNotificationQueue.coach_id == coach_id,
                    CoachNotificationQueue.created_at >= cutoff_date,
                )
            )
            total = total_result.scalar()

            # Sent notifications
            sent_result = await session.execute(
                select(func.count(CoachNotificationQueue.id)).where(
                    CoachNotificationQueue.coach_id == coach_id,
                    CoachNotificationQueue.is_sent.is_(True),
                    CoachNotificationQueue.created_at >= cutoff_date,
                )
            )
            sent = sent_result.scalar()

            # Pending notifications
            pending = total - sent

            # By type
            type_stats = {}
            for notification_type in CoachNotificationType:
                type_result = await session.execute(
                    select(func.count(CoachNotificationQueue.id)).where(
                        CoachNotificationQueue.coach_id == coach_id,
                        CoachNotificationQueue.notification_type == notification_type,
                        CoachNotificationQueue.created_at >= cutoff_date,
                    )
                )
                type_stats[notification_type.value] = type_result.scalar()

            stats = {"total": total, "sent": sent, "pending": pending, **type_stats}

            logger.debug(f"Generated notification stats for coach {coach_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            raise

    @staticmethod
    async def initialize_default_preferences(
        session: AsyncSession, coach_id: int
    ) -> list[CoachNotificationPreference]:
        """Initialize default notification preferences for a new coach."""
        try:
            preferences = []

            # Default preferences - enable measurement notifications, disable others initially
            default_settings = {
                CoachNotificationType.ATHLETE_MEASUREMENT_ADDED: True,
                CoachNotificationType.ATHLETE_GOAL_ACHIEVED: True,
                CoachNotificationType.ATHLETE_INACTIVE: False,
                CoachNotificationType.DAILY_SUMMARY: False,
            }

            for notification_type, is_enabled in default_settings.items():
                preference = (
                    await CoachNotificationRepository.create_notification_preference(
                        session, coach_id, notification_type, is_enabled
                    )
                )
                preferences.append(preference)

            logger.info(
                f"Initialized default notification preferences for coach {coach_id}"
            )
            return preferences

        except Exception as e:
            logger.error(f"Error initializing default preferences: {e}")
            raise
