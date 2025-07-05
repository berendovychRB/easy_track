import logging

from sqlalchemy.ext.asyncio import AsyncSession

from .coach_repository import CoachAthleteRepository
from .repositories import UserRepository

logger = logging.getLogger(__name__)


class PermissionError(Exception):
    """Custom exception for permission-related errors."""

    pass


class PermissionManager:
    """Utility class for handling coach-athlete permissions."""

    @staticmethod
    async def check_coach_permission(session: AsyncSession, user_id: int) -> bool:
        """Check if user has coach permissions."""
        try:
            return await UserRepository.is_user_coach(session, user_id)
        except Exception as e:
            logger.error(f"Error checking coach permission for user {user_id}: {e}")
            return False

    @staticmethod
    async def check_athlete_access(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> bool:
        """Check if coach has access to athlete's data."""
        try:
            # Check if user is a coach
            if not await PermissionManager.check_coach_permission(session, coach_id):
                return False

            # Check if coach supervises athlete
            return await CoachAthleteRepository.is_coach_of_athlete(
                session, coach_id, athlete_id
            )
        except Exception as e:
            logger.error(
                f"Error checking athlete access for coach {coach_id}, athlete {athlete_id}: {e}"
            )
            return False

    @staticmethod
    async def require_coach_permission(session: AsyncSession, user_id: int) -> None:
        """Require coach permissions or raise PermissionError."""
        if not await PermissionManager.check_coach_permission(session, user_id):
            raise PermissionError(f"User {user_id} does not have coach permissions")

    @staticmethod
    async def require_athlete_access(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> None:
        """Require athlete access or raise PermissionError."""
        if not await PermissionManager.check_athlete_access(
            session, coach_id, athlete_id
        ):
            raise PermissionError(
                f"Coach {coach_id} does not have access to athlete {athlete_id}"
            )

    @staticmethod
    async def can_manage_user_role(
        session: AsyncSession, requester_id: int, target_user_id: int
    ) -> bool:
        """Check if user can manage another user's role."""
        try:
            # For now, only allow self-management
            # In future, could add admin roles
            return requester_id == target_user_id
        except Exception as e:
            logger.error(f"Error checking role management permission: {e}")
            return False

    @staticmethod
    async def get_accessible_athletes(session: AsyncSession, coach_id: int) -> list:
        """Get list of athletes accessible to coach."""
        try:
            if not await PermissionManager.check_coach_permission(session, coach_id):
                return []

            return await CoachAthleteRepository.get_coach_athletes(session, coach_id)
        except Exception as e:
            logger.error(f"Error getting accessible athletes for coach {coach_id}: {e}")
            return []

    @staticmethod
    async def filter_accessible_data(
        session: AsyncSession, coach_id: int, data_with_user_id: list
    ) -> list:
        """Filter data to only include items accessible to coach."""
        try:
            if not await PermissionManager.check_coach_permission(session, coach_id):
                return []

            # Get coach's athletes
            athletes = await CoachAthleteRepository.get_coach_athletes(
                session, coach_id
            )
            accessible_athlete_ids = {athlete.id for athlete in athletes}

            # Filter data
            filtered_data = []
            for item in data_with_user_id:
                # Assume item has user_id attribute
                if hasattr(item, "user_id") and item.user_id in accessible_athlete_ids:
                    filtered_data.append(item)

            return filtered_data
        except Exception as e:
            logger.error(f"Error filtering accessible data for coach {coach_id}: {e}")
            return []

    @staticmethod
    async def log_permission_check(
        session: AsyncSession,
        requester_id: int,
        action: str,
        target_user_id: int | None = None,
        granted: bool = False,
    ) -> None:
        """Log permission check for audit purposes."""
        try:
            log_msg = f"Permission check: User {requester_id} requested '{action}'"
            if target_user_id:
                log_msg += f" for user {target_user_id}"
            log_msg += f" - {'GRANTED' if granted else 'DENIED'}"

            if granted:
                logger.info(log_msg)
            else:
                logger.warning(log_msg)
        except Exception as e:
            logger.error(f"Error logging permission check: {e}")


# Decorator functions for easy permission checking
def require_coach_role(func):
    """Decorator to require coach role for function execution."""

    async def wrapper(session: AsyncSession, user_id: int, *args, **kwargs):
        await PermissionManager.require_coach_permission(session, user_id)
        return await func(session, user_id, *args, **kwargs)

    return wrapper


def require_athlete_access_decorator(func):
    """Decorator to require athlete access for function execution."""

    async def wrapper(
        session: AsyncSession, coach_id: int, athlete_id: int, *args, **kwargs
    ):
        await PermissionManager.require_athlete_access(session, coach_id, athlete_id)
        return await func(session, coach_id, athlete_id, *args, **kwargs)

    return wrapper


# Permission constants
class Permissions:
    """Constants for permission types."""

    VIEW_ATHLETE_MEASUREMENTS = "view_athlete_measurements"
    MANAGE_ATHLETES = "manage_athletes"
    ADD_ATHLETE = "add_athlete"
    REMOVE_ATHLETE = "remove_athlete"
    VIEW_ATHLETE_PROGRESS = "view_athlete_progress"
    RECEIVE_ATHLETE_NOTIFICATIONS = "receive_athlete_notifications"
    MANAGE_USER_ROLES = "manage_user_roles"
