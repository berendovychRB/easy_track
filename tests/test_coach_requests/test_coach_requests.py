import asyncio
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.easy_track.coach_repository import AthleteCoachRequestRepository
from src.easy_track.models import AthleteCoachRequest, AthleteCoachRequestStatus, User


class TestAthleteCoachRequestRepository:
    """Test suite for AthleteCoachRequestRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_request(self):
        """Create a sample request object."""
        coach = User(
            id=1,
            telegram_id=123456,
            username="coach1",
            first_name="Coach",
            last_name="One",
        )
        athlete = User(
            id=2,
            telegram_id=789012,
            username="athlete1",
            first_name="Athlete",
            last_name="One",
        )
        request = AthleteCoachRequest(
            id=1,
            coach_id=1,
            athlete_id=2,
            status=AthleteCoachRequestStatus.PENDING,
            message="I would like to be your coach",
            expires_at=datetime.now() + timedelta(days=7),
            created_at=datetime.now(),
        )
        request.coach = coach
        request.athlete = athlete
        return request

    def test_request_status_enum(self):
        """Test that request status enum has correct values."""
        assert AthleteCoachRequestStatus.PENDING == "pending"
        assert AthleteCoachRequestStatus.ACCEPTED == "accepted"
        assert AthleteCoachRequestStatus.REJECTED == "rejected"
        assert AthleteCoachRequestStatus.EXPIRED == "expired"

    @pytest.mark.asyncio
    async def test_create_request_success(self, mock_session):
        """Test successful request creation."""
        # Mock the get_pending_request to return None (no existing request)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Mock session.add and flush
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Create request
        request = await AthleteCoachRequestRepository.create_request(
            mock_session, coach_id=1, athlete_id=2, message="Test message"
        )

        # Verify request was created with correct values
        assert request.coach_id == 1
        assert request.athlete_id == 2
        assert request.message == "Test message"
        assert request.status == AthleteCoachRequestStatus.PENDING
        assert request.expires_at is not None

        # Verify session methods were called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_request_existing_pending(self, mock_session, sample_request):
        """Test creating request when one already exists."""
        # Mock existing pending request
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_request
        )

        # Create request
        result = await AthleteCoachRequestRepository.create_request(
            mock_session, coach_id=1, athlete_id=2
        )

        # Should return existing request
        assert result == sample_request

        # Should not add new request
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_accept_request_success(self, mock_session, sample_request):
        """Test successful request acceptance."""
        # Mock get_request_by_id to return pending request
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_request
        )
        mock_session.flush = AsyncMock()

        # Mock CoachAthleteRepository.add_athlete_to_coach
        with pytest.MonkeyPatch.context() as m:
            mock_add_athlete = AsyncMock()
            m.setattr(
                "src.easy_track.coach_repository.CoachAthleteRepository.add_athlete_to_coach",
                mock_add_athlete,
            )

            # Accept request
            result = await AthleteCoachRequestRepository.accept_request(
                mock_session, request_id=1
            )

            # Verify request status was updated
            assert result.status == AthleteCoachRequestStatus.ACCEPTED
            assert result.responded_at is not None

            # Verify athlete was added to coach
            mock_add_athlete.assert_called_once_with(mock_session, 1, 2)

    @pytest.mark.asyncio
    async def test_reject_request_success(self, mock_session, sample_request):
        """Test successful request rejection."""
        # Mock get_request_by_id to return pending request
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_request
        )
        mock_session.flush = AsyncMock()

        # Reject request
        result = await AthleteCoachRequestRepository.reject_request(
            mock_session, request_id=1
        )

        # Verify request status was updated
        assert result.status == AthleteCoachRequestStatus.REJECTED
        assert result.responded_at is not None

        # Verify session flush was called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_request_not_found(self, mock_session):
        """Test accepting non-existent request."""
        # Mock get_request_by_id to return None
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Accept request
        result = await AthleteCoachRequestRepository.accept_request(
            mock_session, request_id=999
        )

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_reject_request_not_found(self, mock_session):
        """Test rejecting non-existent request."""
        # Mock get_request_by_id to return None
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Reject request
        result = await AthleteCoachRequestRepository.reject_request(
            mock_session, request_id=999
        )

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_athlete_pending_requests(self, mock_session, sample_request):
        """Test getting pending requests for athlete."""
        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            sample_request
        ]

        # Get pending requests
        requests = await AthleteCoachRequestRepository.get_athlete_pending_requests(
            mock_session, athlete_id=2
        )

        # Verify results
        assert len(requests) == 1
        assert requests[0] == sample_request
        assert requests[0].status == AthleteCoachRequestStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_coach_pending_requests(self, mock_session, sample_request):
        """Test getting pending requests from coach."""
        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            sample_request
        ]

        # Get pending requests
        requests = await AthleteCoachRequestRepository.get_coach_pending_requests(
            mock_session, coach_id=1
        )

        # Verify results
        assert len(requests) == 1
        assert requests[0] == sample_request
        assert requests[0].status == AthleteCoachRequestStatus.PENDING

    @pytest.mark.asyncio
    async def test_expire_old_requests(self, mock_session):
        """Test expiring old requests."""
        # Create expired request
        expired_request = AthleteCoachRequest(
            id=1,
            coach_id=1,
            athlete_id=2,
            status=AthleteCoachRequestStatus.PENDING,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            expired_request
        ]
        mock_session.flush = AsyncMock()

        # Expire old requests
        count = await AthleteCoachRequestRepository.expire_old_requests(mock_session)

        # Verify results
        assert count == 1
        assert expired_request.status == AthleteCoachRequestStatus.EXPIRED
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_request_success(self, mock_session, sample_request):
        """Test successful request deletion."""
        # Mock get_request_by_id to return request
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_request
        )
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        # Delete request
        result = await AthleteCoachRequestRepository.delete_request(
            mock_session, request_id=1
        )

        # Verify deletion
        assert result is True
        mock_session.delete.assert_called_once_with(sample_request)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_request_not_found(self, mock_session):
        """Test deleting non-existent request."""
        # Mock get_request_by_id to return None
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Delete request
        result = await AthleteCoachRequestRepository.delete_request(
            mock_session, request_id=999
        )

        # Should return False
        assert result is False
        mock_session.delete.assert_not_called()
