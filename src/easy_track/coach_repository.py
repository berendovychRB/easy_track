import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    AthleteCoachRequest,
    AthleteCoachRequestStatus,
    CoachAthleteRelationship,
    User,
)

logger = logging.getLogger(__name__)


class CoachAthleteRepository:
    """Repository for CoachAthleteRelationship operations."""

    @staticmethod
    async def add_athlete_to_coach(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> CoachAthleteRelationship:
        """Add athlete to coach's supervision."""
        try:
            logger.debug(f"Adding athlete {athlete_id} to coach {coach_id}")

            # Check if relationship already exists
            existing = await CoachAthleteRepository.get_relationship(
                session, coach_id, athlete_id
            )

            if existing:
                if existing.is_active:
                    logger.debug("Relationship already exists and is active")
                    return existing
                # Reactivate existing relationship
                existing.is_active = True
                await session.flush()
                logger.debug("Reactivated existing relationship")
                return existing

            # Create new relationship
            relationship = CoachAthleteRelationship(
                coach_id=coach_id, athlete_id=athlete_id, is_active=True
            )
            session.add(relationship)
            await session.flush()

            logger.debug(f"Created new coach-athlete relationship: {relationship.id}")
            return relationship

        except Exception as e:
            logger.error(f"Error adding athlete {athlete_id} to coach {coach_id}: {e}")
            raise

    @staticmethod
    async def remove_athlete_from_coach(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> bool:
        """Remove athlete from coach's supervision."""
        try:
            logger.debug(f"Removing athlete {athlete_id} from coach {coach_id}")

            relationship = await CoachAthleteRepository.get_relationship(
                session, coach_id, athlete_id
            )

            if relationship and relationship.is_active:
                relationship.is_active = False
                await session.flush()
                logger.debug(
                    f"Deactivated coach-athlete relationship: {relationship.id}"
                )
                return True

            logger.debug("No active relationship found to remove")
            return False

        except Exception as e:
            logger.error(
                f"Error removing athlete {athlete_id} from coach {coach_id}: {e}"
            )
            raise

    @staticmethod
    async def get_coach_athletes(
        session: AsyncSession, coach_id: int, active_only: bool = True
    ) -> list[User]:
        """Get all athletes supervised by coach."""
        try:
            logger.debug(
                f"Fetching athletes for coach {coach_id}, active_only={active_only}"
            )

            query = (
                select(User)
                .join(
                    CoachAthleteRelationship,
                    User.id == CoachAthleteRelationship.athlete_id,
                )
                .where(CoachAthleteRelationship.coach_id == coach_id)
            )

            if active_only:
                query = query.where(CoachAthleteRelationship.is_active.is_(True))

            query = query.order_by(User.first_name, User.username)

            result = await session.execute(query)
            athletes = result.scalars().all()

            logger.debug(f"Found {len(athletes)} athletes for coach {coach_id}")
            return athletes

        except Exception as e:
            logger.error(f"Error fetching athletes for coach {coach_id}: {e}")
            raise

    @staticmethod
    async def get_athlete_coaches(
        session: AsyncSession, athlete_id: int, active_only: bool = True
    ) -> list[User]:
        """Get all coaches supervising athlete."""
        try:
            logger.debug(
                f"Fetching coaches for athlete {athlete_id}, active_only={active_only}"
            )

            query = (
                select(User)
                .join(
                    CoachAthleteRelationship,
                    User.id == CoachAthleteRelationship.coach_id,
                )
                .where(CoachAthleteRelationship.athlete_id == athlete_id)
            )

            if active_only:
                query = query.where(CoachAthleteRelationship.is_active.is_(True))

            query = query.order_by(User.first_name, User.username)

            result = await session.execute(query)
            coaches = result.scalars().all()

            logger.debug(f"Found {len(coaches)} coaches for athlete {athlete_id}")
            return coaches

        except Exception as e:
            logger.error(f"Error fetching coaches for athlete {athlete_id}: {e}")
            raise

    @staticmethod
    async def is_coach_of_athlete(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> bool:
        """Check if coach supervises athlete."""
        try:
            relationship = await CoachAthleteRepository.get_relationship(
                session, coach_id, athlete_id
            )
            return relationship is not None and relationship.is_active

        except Exception as e:
            logger.error(
                f"Error checking if coach {coach_id} supervises athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_relationship(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> CoachAthleteRelationship | None:
        """Get specific coach-athlete relationship."""
        try:
            result = await session.execute(
                select(CoachAthleteRelationship).where(
                    CoachAthleteRelationship.coach_id == coach_id,
                    CoachAthleteRelationship.athlete_id == athlete_id,
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Error fetching relationship between coach {coach_id} and athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_all_relationships(
        session: AsyncSession, active_only: bool = True
    ) -> list[CoachAthleteRelationship]:
        """Get all coach-athlete relationships."""
        try:
            query = select(CoachAthleteRelationship).options(
                selectinload(CoachAthleteRelationship.coach),
                selectinload(CoachAthleteRelationship.athlete),
            )

            if active_only:
                query = query.where(CoachAthleteRelationship.is_active.is_(True))

            query = query.order_by(CoachAthleteRelationship.added_at)

            result = await session.execute(query)
            relationships = result.scalars().all()

            logger.debug(f"Found {len(relationships)} coach-athlete relationships")
            return relationships

        except Exception as e:
            logger.error(f"Error fetching all coach-athlete relationships: {e}")
            raise

    @staticmethod
    async def get_coach_athlete_count(session: AsyncSession, coach_id: int) -> int:
        """Get number of athletes supervised by coach."""
        try:
            result = await session.execute(
                select(func.count(CoachAthleteRelationship.id)).where(
                    CoachAthleteRelationship.coach_id == coach_id,
                    CoachAthleteRelationship.is_active.is_(True),
                )
            )
            count = result.scalar()

            logger.debug(f"Coach {coach_id} supervises {count} athletes")
            return count

        except Exception as e:
            logger.error(f"Error counting athletes for coach {coach_id}: {e}")
            raise

    @staticmethod
    async def get_athlete_coach_count(session: AsyncSession, athlete_id: int) -> int:
        """Get number of coaches supervising athlete."""
        try:
            result = await session.execute(
                select(func.count(CoachAthleteRelationship.id)).where(
                    CoachAthleteRelationship.athlete_id == athlete_id,
                    CoachAthleteRelationship.is_active.is_(True),
                )
            )
            count = result.scalar()

            logger.debug(f"Athlete {athlete_id} has {count} coaches")
            return count

        except Exception as e:
            logger.error(f"Error counting coaches for athlete {athlete_id}: {e}")
            raise


class AthleteCoachRequestRepository:
    """Repository for AthleteCoachRequest operations."""

    @staticmethod
    async def create_request(
        session: AsyncSession,
        coach_id: int,
        athlete_id: int,
        message: str | None = None,
        expires_in_days: int = 7,
    ) -> AthleteCoachRequest:
        """Create a new coach-athlete relationship request."""
        try:
            logger.debug(
                f"Creating request from coach {coach_id} to athlete {athlete_id}"
            )

            # Check if there's already a pending request
            existing = await AthleteCoachRequestRepository.get_pending_request(
                session, coach_id, athlete_id
            )
            if existing:
                logger.debug(f"Request already exists: {existing.id}")
                return existing

            # Check if there's already an accepted request (coach-athlete relationship exists)
            relationship_exists = await CoachAthleteRepository.is_coach_of_athlete(
                session, coach_id, athlete_id
            )
            if relationship_exists:
                logger.debug("Coach-athlete relationship already exists")
                # Return a mock request object indicating already connected
                mock_request = AthleteCoachRequest(
                    coach_id=coach_id,
                    athlete_id=athlete_id,
                    status=AthleteCoachRequestStatus.ACCEPTED,
                )
                return mock_request

            # Create new request
            expires_at = datetime.now() + timedelta(days=expires_in_days)
            request = AthleteCoachRequest(
                coach_id=coach_id,
                athlete_id=athlete_id,
                message=message,
                expires_at=expires_at,
                status=AthleteCoachRequestStatus.PENDING,
            )
            session.add(request)
            await session.flush()

            logger.debug(f"Created request: {request.id}")
            return request

        except Exception as e:
            logger.error(
                f"Error creating request from coach {coach_id} to athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_pending_request(
        session: AsyncSession, coach_id: int, athlete_id: int
    ) -> AthleteCoachRequest | None:
        """Get pending request between coach and athlete."""
        try:
            result = await session.execute(
                select(AthleteCoachRequest).where(
                    AthleteCoachRequest.coach_id == coach_id,
                    AthleteCoachRequest.athlete_id == athlete_id,
                    AthleteCoachRequest.status == AthleteCoachRequestStatus.PENDING,
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Error fetching pending request between coach {coach_id} and athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_request_by_id(
        session: AsyncSession, request_id: int
    ) -> AthleteCoachRequest | None:
        """Get request by ID."""
        try:
            result = await session.execute(
                select(AthleteCoachRequest)
                .options(
                    selectinload(AthleteCoachRequest.coach),
                    selectinload(AthleteCoachRequest.athlete),
                )
                .where(AthleteCoachRequest.id == request_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error fetching request {request_id}: {e}")
            raise

    @staticmethod
    async def get_athlete_pending_requests(
        session: AsyncSession, athlete_id: int
    ) -> list[AthleteCoachRequest]:
        """Get all pending requests for athlete."""
        try:
            result = await session.execute(
                select(AthleteCoachRequest)
                .options(
                    selectinload(AthleteCoachRequest.coach),
                    selectinload(AthleteCoachRequest.athlete),
                )
                .where(
                    AthleteCoachRequest.athlete_id == athlete_id,
                    AthleteCoachRequest.status == AthleteCoachRequestStatus.PENDING,
                )
                .order_by(AthleteCoachRequest.created_at.desc())
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(
                f"Error fetching pending requests for athlete {athlete_id}: {e}"
            )
            raise

    @staticmethod
    async def get_coach_pending_requests(
        session: AsyncSession, coach_id: int
    ) -> list[AthleteCoachRequest]:
        """Get all pending requests from coach."""
        try:
            result = await session.execute(
                select(AthleteCoachRequest)
                .options(
                    selectinload(AthleteCoachRequest.coach),
                    selectinload(AthleteCoachRequest.athlete),
                )
                .where(
                    AthleteCoachRequest.coach_id == coach_id,
                    AthleteCoachRequest.status == AthleteCoachRequestStatus.PENDING,
                )
                .order_by(AthleteCoachRequest.created_at.desc())
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching pending requests from coach {coach_id}: {e}")
            raise

    @staticmethod
    async def accept_request(
        session: AsyncSession, request_id: int
    ) -> AthleteCoachRequest | None:
        """Accept a coach-athlete relationship request."""
        try:
            request = await AthleteCoachRequestRepository.get_request_by_id(
                session, request_id
            )
            if not request or request.status != AthleteCoachRequestStatus.PENDING:
                return None

            # Update request status
            request.status = AthleteCoachRequestStatus.ACCEPTED
            request.responded_at = datetime.now()
            await session.flush()

            # Create coach-athlete relationship
            await CoachAthleteRepository.add_athlete_to_coach(
                session, request.coach_id, request.athlete_id
            )

            logger.debug(f"Accepted request {request_id}")
            return request

        except Exception as e:
            logger.error(f"Error accepting request {request_id}: {e}")
            raise

    @staticmethod
    async def reject_request(
        session: AsyncSession, request_id: int
    ) -> AthleteCoachRequest | None:
        """Reject a coach-athlete relationship request."""
        try:
            request = await AthleteCoachRequestRepository.get_request_by_id(
                session, request_id
            )
            if not request or request.status != AthleteCoachRequestStatus.PENDING:
                return None

            # Update request status
            request.status = AthleteCoachRequestStatus.REJECTED
            request.responded_at = datetime.now()
            await session.flush()

            logger.debug(f"Rejected request {request_id}")
            return request

        except Exception as e:
            logger.error(f"Error rejecting request {request_id}: {e}")
            raise

    @staticmethod
    async def expire_old_requests(session: AsyncSession) -> int:
        """Expire old pending requests."""
        try:
            now = datetime.now()
            result = await session.execute(
                select(AthleteCoachRequest).where(
                    AthleteCoachRequest.status == AthleteCoachRequestStatus.PENDING,
                    AthleteCoachRequest.expires_at < now,
                )
            )
            expired_requests = result.scalars().all()

            count = 0
            for request in expired_requests:
                request.status = AthleteCoachRequestStatus.EXPIRED
                count += 1

            await session.flush()
            logger.debug(f"Expired {count} old requests")
            return count

        except Exception as e:
            logger.error(f"Error expiring old requests: {e}")
            raise

    @staticmethod
    async def delete_request(session: AsyncSession, request_id: int) -> bool:
        """Delete a request."""
        try:
            request = await AthleteCoachRequestRepository.get_request_by_id(
                session, request_id
            )
            if not request:
                return False

            await session.delete(request)
            await session.flush()

            logger.debug(f"Deleted request {request_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting request {request_id}: {e}")
            raise
