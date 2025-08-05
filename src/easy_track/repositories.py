import logging
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CoachNotificationType,
    Measurement,
    MeasurementType,
    NotificationSchedule,
    User,
    UserMeasurementType,
    UserRole,
)

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations."""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language: str = "en",
    ) -> User:
        """Create a new user."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> User | None:
        """Get user by Telegram ID."""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
        """Get user by ID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user(session: AsyncSession, user_id: int, **kwargs) -> User | None:
        """Update user information."""
        user = await UserRepository.get_user_by_id(session, user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await session.flush()
        return user

    @staticmethod
    async def update_user_language(
        session: AsyncSession, telegram_id: int, language: str
    ) -> User | None:
        """Update user's language preference."""
        user = await UserRepository.get_user_by_telegram_id(session, telegram_id)
        if user:
            user.language = language
            await session.flush()
        return user

    @staticmethod
    async def get_user_language(session: AsyncSession, telegram_id: int) -> str:
        """Get user's language preference."""
        user = await UserRepository.get_user_by_telegram_id(session, telegram_id)
        return user.language if user else "uk"

    @staticmethod
    async def update_user_role(
        session: AsyncSession, user_id: int, role: UserRole
    ) -> User:
        """Update user role."""
        user = await UserRepository.get_user_by_id(session, user_id)
        if user:
            user.user_role = role
            await session.flush()
        return user

    @staticmethod
    async def find_user_by_telegram_id_or_username(
        session: AsyncSession, identifier: str
    ) -> User | None:
        """Find user by telegram ID or username."""
        try:
            # Try to parse as telegram ID (numeric)
            if identifier.isdigit():
                telegram_id = int(identifier)
                return await UserRepository.get_user_by_telegram_id(
                    session, telegram_id
                )

            # Remove @ if present
            username = identifier.lstrip("@")

            # Search by username
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error finding user by identifier '{identifier}': {e}")
            return None

    @staticmethod
    async def is_user_coach(session: AsyncSession, user_id: int) -> bool:
        """Check if user is a coach."""
        user = await UserRepository.get_user_by_id(session, user_id)
        return user and user.user_role in [UserRole.COACH, UserRole.BOTH]

    @staticmethod
    async def get_users_by_role(session: AsyncSession, role: UserRole) -> list[User]:
        """Get users by role."""
        result = await session.execute(
            select(User)
            .where(User.user_role == role)
            .where(User.is_active.is_(True))
            .order_by(User.first_name, User.username)
        )
        return result.scalars().all()

    @staticmethod
    async def find_user_by_username(
        session: AsyncSession, username: str
    ) -> User | None:
        """Find user by username."""
        if not username:
            return None

        # Remove @ symbol if present
        username = username.lstrip("@")

        result = await session.execute(
            select(User)
            .where(User.username == username)
            .where(User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_role(session: AsyncSession, user_id: int) -> UserRole | None:
        """Get user's role."""
        user = await UserRepository.get_user_by_id(session, user_id)
        return UserRole(user.user_role) if user else None

    @staticmethod
    async def is_user_athlete(session: AsyncSession, user_id: int) -> bool:
        """Check if user is an athlete."""
        role = await UserRepository.get_user_role(session, user_id)
        return role in [UserRole.ATHLETE, UserRole.BOTH]


class MeasurementTypeRepository:
    """Repository for MeasurementType operations."""

    @staticmethod
    async def get_all_active_types(session: AsyncSession) -> list[MeasurementType]:
        """Get all active measurement types."""
        result = await session.execute(
            select(MeasurementType)
            .where(MeasurementType.is_active.is_(True))
            .order_by(MeasurementType.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_type_by_id(
        session: AsyncSession, type_id: int
    ) -> MeasurementType | None:
        """Get measurement type by ID."""
        result = await session.execute(
            select(MeasurementType).where(MeasurementType.id == type_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_type_by_name(
        session: AsyncSession, name: str
    ) -> MeasurementType | None:
        """Get measurement type by name."""
        result = await session.execute(
            select(MeasurementType).where(MeasurementType.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_measurement_type(
        session: AsyncSession, name: str, unit: str, description: str = None
    ) -> MeasurementType:
        """Create a new measurement type."""
        measurement_type = MeasurementType(
            name=name, unit=unit, description=description
        )
        session.add(measurement_type)
        await session.flush()
        return measurement_type

    @staticmethod
    async def create_custom_measurement_type(
        session: AsyncSession,
        name: str,
        unit: str,
        user_id: int,
        description: str = None,
    ) -> MeasurementType:
        """Create a new custom measurement type for a specific user."""
        measurement_type = MeasurementType(
            name=name,
            unit=unit,
            description=description,
            is_custom=True,
            created_by_user_id=user_id,
        )
        session.add(measurement_type)
        await session.flush()
        return measurement_type

    @staticmethod
    async def get_user_custom_types(
        session: AsyncSession, user_id: int
    ) -> list[MeasurementType]:
        """Get all custom measurement types created by a specific user."""
        result = await session.execute(
            select(MeasurementType)
            .where(MeasurementType.created_by_user_id == user_id)
            .where(MeasurementType.is_active.is_(True))
            .order_by(MeasurementType.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_available_types_for_user(
        session: AsyncSession, user_id: int
    ) -> list[MeasurementType]:
        """Get all measurement types available to a user (system + their custom types)."""
        result = await session.execute(
            select(MeasurementType)
            .where(
                (MeasurementType.is_custom.is_(False))
                | (MeasurementType.created_by_user_id == user_id)
            )
            .where(MeasurementType.is_active.is_(True))
            .order_by(MeasurementType.name)
        )
        return result.scalars().all()

    @staticmethod
    async def check_custom_type_name_exists(
        session: AsyncSession, name: str, user_id: int
    ) -> bool:
        """Check if a custom measurement type name already exists for a user."""
        result = await session.execute(
            select(MeasurementType)
            .where(MeasurementType.name.ilike(name))
            .where(
                (MeasurementType.is_custom.is_(False))
                | (MeasurementType.created_by_user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def delete_custom_measurement_type(
        session: AsyncSession, type_id: int, user_id: int
    ) -> bool:
        """Delete a custom measurement type if it belongs to the user."""
        result = await session.execute(
            select(MeasurementType)
            .where(MeasurementType.id == type_id)
            .where(MeasurementType.created_by_user_id == user_id)
            .where(MeasurementType.is_custom.is_(True))
        )
        measurement_type = result.scalar_one_or_none()

        if measurement_type:
            measurement_type.is_active = False
            await session.flush()
            return True
        return False


class UserMeasurementTypeRepository:
    """Repository for UserMeasurementType operations."""

    @staticmethod
    async def get_user_measurement_types(
        session: AsyncSession, user_id: int
    ) -> list[UserMeasurementType]:
        """Get all active measurement types for a user."""
        try:
            logger.debug(f"Fetching measurement types for user {user_id}")

            # Use simple SQLAlchemy query with explicit boolean comparison
            result = await session.execute(
                select(UserMeasurementType)
                .options(selectinload(UserMeasurementType.measurement_type))
                .where(UserMeasurementType.user_id == user_id)
                .where(UserMeasurementType.is_active.is_(True))
            )
            user_types = result.scalars().all()

            # Filter and sort in Python to avoid complex SQL
            active_types = [ut for ut in user_types if ut.is_active]
            sorted_types = sorted(
                active_types,
                key=lambda x: x.measurement_type.name if x.measurement_type else "",
            )

            logger.debug(
                f"Found {len(sorted_types)} active measurement types for user {user_id}"
            )
            return sorted_types

        except Exception as e:
            logger.error(
                f"Error fetching user measurement types for user {user_id}: {e}"
            )
            raise

    @staticmethod
    async def add_measurement_type_to_user(
        session: AsyncSession, user_id: int, measurement_type_id: int
    ) -> UserMeasurementType:
        """Add a measurement type to user's tracking list."""
        # Check if already exists
        existing = await session.execute(
            select(UserMeasurementType)
            .where(UserMeasurementType.user_id == user_id)
            .where(UserMeasurementType.measurement_type_id == measurement_type_id)
        )
        user_measurement_type = existing.scalar_one_or_none()

        if user_measurement_type:
            # Reactivate if exists but inactive
            user_measurement_type.is_active = True
        else:
            # Create new
            user_measurement_type = UserMeasurementType(
                user_id=user_id, measurement_type_id=measurement_type_id
            )
            session.add(user_measurement_type)

        await session.flush()
        return user_measurement_type

    @staticmethod
    async def remove_measurement_type_from_user(
        session: AsyncSession, user_id: int, measurement_type_id: int
    ) -> bool:
        """Remove a measurement type from user's tracking list."""
        result = await session.execute(
            select(UserMeasurementType)
            .where(UserMeasurementType.user_id == user_id)
            .where(UserMeasurementType.measurement_type_id == measurement_type_id)
        )
        user_measurement_type = result.scalar_one_or_none()

        if user_measurement_type:
            user_measurement_type.is_active = False
            await session.flush()
            return True
        return False


class MeasurementRepository:
    """Repository for Measurement operations."""

    @staticmethod
    async def create_measurement(
        session: AsyncSession,
        user_id: int,
        measurement_type_id: int,
        value: float,
        measurement_date: datetime = None,
        notes: str = None,
    ) -> Measurement:
        """Create a new measurement."""
        if measurement_date is None:
            measurement_date = datetime.now()

        measurement = Measurement(
            user_id=user_id,
            measurement_type_id=measurement_type_id,
            value=value,
            measurement_date=measurement_date,
            notes=notes,
        )
        session.add(measurement)
        await session.flush()

        # Trigger coach notifications
        await MeasurementRepository._notify_coaches_of_measurement(session, measurement)

        return measurement

    @staticmethod
    async def get_user_measurements(
        session: AsyncSession,
        user_id: int,
        measurement_type_id: int = None,
        limit: int = None,
    ) -> list[Measurement]:
        """Get measurements for a user, optionally filtered by type."""
        try:
            logger.debug(
                f"Fetching measurements for user {user_id}, type: {measurement_type_id}, limit: {limit}"
            )

            query = (
                select(Measurement)
                .options(selectinload(Measurement.measurement_type))
                .where(Measurement.user_id == user_id)
            )

            if measurement_type_id:
                query = query.where(
                    Measurement.measurement_type_id == measurement_type_id
                )

            query = query.order_by(desc(Measurement.measurement_date))

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            measurements = result.scalars().all()

            logger.debug(f"Found {len(measurements)} measurements for user {user_id}")
            return measurements

        except Exception as e:
            logger.error(f"Error fetching measurements for user {user_id}: {e}")
            raise

    @staticmethod
    async def get_latest_measurement(
        session: AsyncSession, user_id: int, measurement_type_id: int
    ) -> Measurement | None:
        """Get the latest measurement for a specific type."""
        try:
            logger.debug(
                f"Fetching latest measurement for user {user_id}, type {measurement_type_id}"
            )

            result = await session.execute(
                select(Measurement)
                .options(selectinload(Measurement.measurement_type))
                .where(Measurement.user_id == user_id)
                .where(Measurement.measurement_type_id == measurement_type_id)
                .order_by(desc(Measurement.measurement_date))
                .limit(1)
            )
            measurement = result.scalar_one_or_none()

            if measurement:
                logger.debug(
                    f"Found latest measurement: {measurement.value} on {measurement.measurement_date}"
                )
            else:
                logger.debug(
                    f"No measurements found for user {user_id}, type {measurement_type_id}"
                )

            return measurement

        except Exception as e:
            logger.error(
                f"Error fetching latest measurement for user {user_id}, type {measurement_type_id}: {e}"
            )
            raise

    @staticmethod
    async def get_measurement_history(
        session: AsyncSession, user_id: int, measurement_type_id: int, days: int = 30
    ) -> list[Measurement]:
        """Get measurement history for a specific type within given days."""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        result = await session.execute(
            select(Measurement)
            .options(selectinload(Measurement.measurement_type))
            .where(Measurement.user_id == user_id)
            .where(Measurement.measurement_type_id == measurement_type_id)
            .where(Measurement.measurement_date >= cutoff_date)
            .order_by(Measurement.measurement_date)
        )
        return result.scalars().all()

    @staticmethod
    async def get_measurement_stats(
        session: AsyncSession, user_id: int, measurement_type_id: int
    ) -> dict:
        """Get basic stats for a measurement type."""
        result = await session.execute(
            select(
                func.count(Measurement.id).label("count"),
                func.avg(Measurement.value).label("average"),
                func.min(Measurement.value).label("minimum"),
                func.max(Measurement.value).label("maximum"),
            )
            .where(Measurement.user_id == user_id)
            .where(Measurement.measurement_type_id == measurement_type_id)
        )
        stats = result.first()
        return {
            "count": stats.count or 0,
            "average": round(stats.average, 2) if stats.average else 0,
            "minimum": stats.minimum or 0,
            "maximum": stats.maximum or 0,
        }

    @staticmethod
    async def get_measurements_by_date(
        session: AsyncSession, user_id: int, days: int = 30
    ) -> dict[str, list[Measurement]]:
        """Get all user measurements grouped by date."""
        try:
            logger.debug(
                f"Fetching measurements by date for user {user_id}, last {days} days"
            )

            if days > 0:
                cutoff_date = datetime.now(UTC) - timedelta(days=days)
                cutoff_date = cutoff_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # All time
                cutoff_date = datetime(2000, 1, 1)

            result = await session.execute(
                select(Measurement)
                .options(selectinload(Measurement.measurement_type))
                .where(Measurement.user_id == user_id)
                .where(Measurement.measurement_date >= cutoff_date)
                .order_by(desc(Measurement.measurement_date))
            )
            measurements = result.scalars().all()

            # Group measurements by date
            grouped_measurements = {}
            for measurement in measurements:
                date_key = measurement.measurement_date.strftime("%d.%m.%Y")
                if date_key not in grouped_measurements:
                    grouped_measurements[date_key] = []
                grouped_measurements[date_key].append(measurement)

            logger.debug(f"Found measurements for {len(grouped_measurements)} dates")
            return grouped_measurements

        except Exception as e:
            logger.error(f"Error fetching measurements by date for user {user_id}: {e}")
            raise

    @staticmethod
    async def get_athlete_measurements_for_coach(
        session: AsyncSession,
        coach_id: int,
        athlete_id: int,
        measurement_type_id: int = None,
        limit: int = None,
    ) -> list[Measurement]:
        """Get athlete measurements if coach has permission."""
        try:
            # Import here to avoid circular imports
            from .coach_repository import CoachAthleteRepository

            # Check if coach has permission to view athlete's data
            has_permission = await CoachAthleteRepository.is_coach_of_athlete(
                session, coach_id, athlete_id
            )

            if not has_permission:
                logger.warning(
                    f"Coach {coach_id} attempted to access athlete {athlete_id} data without permission"
                )
                return []

            # Get measurements using existing method
            return await MeasurementRepository.get_user_measurements(
                session, athlete_id, measurement_type_id, limit
            )

        except Exception as e:
            logger.error(
                f"Error fetching athlete measurements for coach {coach_id}, athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_recent_measurements_for_coach_athletes(
        session: AsyncSession, coach_id: int, days: int = 7
    ) -> list[Measurement]:
        """Get recent measurements from all coach's athletes."""
        try:
            # Import here to avoid circular imports
            from .coach_repository import CoachAthleteRepository

            logger.debug(
                f"Fetching recent measurements for coach {coach_id} athletes, last {days} days"
            )

            # Get all coach's athletes
            athletes = await CoachAthleteRepository.get_coach_athletes(
                session, coach_id
            )

            if not athletes:
                logger.debug(f"Coach {coach_id} has no athletes")
                return []

            athlete_ids = [athlete.id for athlete in athletes]

            # Calculate cutoff date
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            cutoff_date = cutoff_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Get recent measurements from all athletes
            result = await session.execute(
                select(Measurement)
                .options(
                    selectinload(Measurement.measurement_type),
                    selectinload(Measurement.user),
                )
                .where(Measurement.user_id.in_(athlete_ids))
                .where(Measurement.measurement_date >= cutoff_date)
                .order_by(desc(Measurement.measurement_date))
            )
            measurements = result.scalars().all()

            logger.debug(
                f"Found {len(measurements)} recent measurements for coach {coach_id}"
            )
            return measurements

        except Exception as e:
            logger.error(
                f"Error fetching recent measurements for coach {coach_id}: {e}"
            )
            raise

    @staticmethod
    async def get_athlete_latest_measurements(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> list[Measurement]:
        """Get latest measurements for each type for a specific athlete."""
        try:
            # Import here to avoid circular imports
            from .coach_repository import CoachAthleteRepository

            # Check permission
            has_permission = await CoachAthleteRepository.is_coach_of_athlete(
                session, coach_id, athlete_id
            )

            if not has_permission:
                logger.warning(
                    f"Coach {coach_id} attempted to access athlete {athlete_id} data without permission"
                )
                return []

            # Get athlete's measurement types
            athlete_measurement_types = (
                await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, athlete_id
                )
            )

            latest_measurements = []
            for umt in athlete_measurement_types:
                latest = await MeasurementRepository.get_latest_measurement(
                    session, athlete_id, umt.measurement_type_id
                )
                if latest:
                    latest_measurements.append(latest)

            logger.debug(
                f"Found {len(latest_measurements)} latest measurements for athlete {athlete_id}"
            )
            return latest_measurements

        except Exception as e:
            logger.error(
                f"Error fetching latest measurements for athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def _notify_coaches_of_measurement(
        session: AsyncSession, measurement: Measurement
    ):
        """Notify coaches when athlete adds a measurement."""
        try:
            # Import here to avoid circular imports
            from .coach_notification_repository import CoachNotificationRepository
            from .coach_repository import CoachAthleteRepository
            from .i18n import translator

            # Get all coaches for this athlete
            coaches = await CoachAthleteRepository.get_athlete_coaches(
                session, measurement.user_id
            )

            if not coaches:
                return

            # Get measurement type and user info
            measurement_type = await session.get(
                MeasurementType, measurement.measurement_type_id
            )
            athlete = await session.get(User, measurement.user_id)

            if not measurement_type or not athlete:
                logger.error(
                    f"Could not find measurement type or athlete for measurement {measurement.id}"
                )
                return

            athlete_name = athlete.first_name or athlete.username or "Unknown"

            # Queue notifications for each coach
            for coach in coaches:
                # Check if coach has this notification type enabled
                is_enabled = await CoachNotificationRepository.is_notification_enabled(
                    session, coach.id, CoachNotificationType.ATHLETE_MEASUREMENT_ADDED
                )

                if is_enabled:
                    # Get coach's language preference
                    coach_user = await session.get(User, coach.id)
                    coach_lang = coach_user.language if coach_user else "en"

                    # Create notification message with proper translation
                    if measurement.notes:
                        message = translator.get(
                            "coach.notifications.measurement_with_notes",
                            coach_lang,
                            name=athlete_name,
                            type=measurement_type.name,
                            value=measurement.value,
                            unit=measurement_type.unit,
                            date=measurement.measurement_date.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            notes=measurement.notes,
                        )
                    else:
                        message = translator.get(
                            "coach.notifications.measurement_notification",
                            coach_lang,
                            name=athlete_name,
                            type=measurement_type.name,
                            value=measurement.value,
                            unit=measurement_type.unit,
                            date=measurement.measurement_date.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                        )

                    await CoachNotificationRepository.queue_notification(
                        session=session,
                        coach_id=coach.id,
                        athlete_id=measurement.user_id,
                        notification_type=CoachNotificationType.ATHLETE_MEASUREMENT_ADDED,
                        message=message,
                        measurement_id=measurement.id,
                    )
                    logger.debug(
                        f"Queued measurement notification for coach {coach.id}"
                    )

        except Exception as e:
            logger.error(f"Error notifying coaches of measurement: {e}")
            # Don't raise the error to avoid breaking measurement creation


class NotificationScheduleRepository:
    """Repository for NotificationSchedule operations."""

    @staticmethod
    async def create_schedule(
        session: AsyncSession,
        user_id: int,
        day_of_week: int | None,
        notification_time: time,
        timezone: str = "UTC",
    ) -> NotificationSchedule:
        """Create a new notification schedule."""
        schedule = NotificationSchedule(
            user_id=user_id,
            day_of_week=day_of_week,
            notification_time=notification_time,
            timezone=timezone,
        )
        session.add(schedule)
        await session.flush()
        return schedule

    @staticmethod
    async def get_user_schedules(
        session: AsyncSession, user_id: int
    ) -> list[NotificationSchedule]:
        """Get all notification schedules for a user."""
        result = await session.execute(
            select(NotificationSchedule)
            .where(NotificationSchedule.user_id == user_id)
            .order_by(NotificationSchedule.created_at)
        )
        return result.scalars().all()

    @staticmethod
    async def get_active_user_schedules(
        session: AsyncSession, user_id: int
    ) -> list[NotificationSchedule]:
        """Get active notification schedules for a user."""
        result = await session.execute(
            select(NotificationSchedule)
            .where(
                NotificationSchedule.user_id == user_id,
                NotificationSchedule.is_active.is_(True),
            )
            .order_by(NotificationSchedule.created_at)
        )
        return result.scalars().all()

    @staticmethod
    async def get_schedule_by_id(
        session: AsyncSession, schedule_id: int
    ) -> NotificationSchedule | None:
        """Get notification schedule by ID."""
        result = await session.execute(
            select(NotificationSchedule).where(NotificationSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_schedule_status(
        session: AsyncSession, schedule_id: int, is_active: bool
    ) -> bool:
        """Update notification schedule active status."""
        schedule = await NotificationScheduleRepository.get_schedule_by_id(
            session, schedule_id
        )
        if schedule:
            schedule.is_active = is_active
            await session.flush()
            return True
        return False

    @staticmethod
    async def delete_schedule(session: AsyncSession, schedule_id: int) -> bool:
        """Delete notification schedule."""
        schedule = await NotificationScheduleRepository.get_schedule_by_id(
            session, schedule_id
        )
        if schedule:
            await session.delete(schedule)
            await session.flush()
            return True
        return False

    @staticmethod
    async def get_all_active_schedules(
        session: AsyncSession,
    ) -> list[NotificationSchedule]:
        """Get all active notification schedules for the scheduler."""
        result = await session.execute(
            select(NotificationSchedule)
            .options(selectinload(NotificationSchedule.user))
            .where(NotificationSchedule.is_active.is_(True))
            .order_by(NotificationSchedule.notification_time)
        )
        return result.scalars().all()

    @staticmethod
    async def get_schedules_for_time(
        session: AsyncSession,
        current_time: time,
        current_day_of_week: int,
    ) -> list[NotificationSchedule]:
        """Get schedules that should trigger at the given time and day."""
        result = await session.execute(
            select(NotificationSchedule)
            .options(selectinload(NotificationSchedule.user))
            .where(
                NotificationSchedule.is_active.is_(True),
                NotificationSchedule.notification_time == current_time,
                (
                    (NotificationSchedule.day_of_week == current_day_of_week)
                    | (NotificationSchedule.day_of_week.is_(None))
                ),
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_schedules_for_time_and_timezone(
        session: AsyncSession,
        current_time: time,
        current_day_of_week: int,
        timezone: str,
    ) -> list[NotificationSchedule]:
        """Get schedules for specific time, day, and timezone."""
        result = await session.execute(
            select(NotificationSchedule)
            .options(selectinload(NotificationSchedule.user))
            .where(
                NotificationSchedule.is_active.is_(True),
                NotificationSchedule.notification_time == current_time,
                NotificationSchedule.timezone == timezone,
                (
                    (NotificationSchedule.day_of_week == current_day_of_week)
                    | (NotificationSchedule.day_of_week.is_(None))
                ),
            )
        )
        return result.scalars().all()
