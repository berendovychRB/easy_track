#!/usr/bin/env python3
"""
Demo script for testing coach request functionality.
This script demonstrates the new coach-athlete request system.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta, timezone

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.easy_track.coach_repository import (
    AthleteCoachRequestRepository,
    CoachAthleteRepository,
)
from src.easy_track.database import DatabaseManager, init_db
from src.easy_track.models import (
    AthleteCoachRequest,
    AthleteCoachRequestStatus,
    User,
    UserRole,
)
from src.easy_track.repositories import UserRepository


async def create_test_users():
    """Create test users for the demo."""
    print("🔄 Creating test users...")

    async def _create_users(session):
        # Try to get existing users first
        coach = await UserRepository.get_user_by_telegram_id(session, 123456789)
        athlete = await UserRepository.get_user_by_telegram_id(session, 987654321)

        if not coach:
            # Create coach user
            coach = await UserRepository.create_user(
                session,
                telegram_id=123456789,
                username="demo_coach",
                first_name="Demo",
                last_name="Coach",
                language="en",
            )
            coach.user_role = UserRole.COACH

        if not athlete:
            # Create athlete user
            athlete = await UserRepository.create_user(
                session,
                telegram_id=987654321,
                username="demo_athlete",
                first_name="Demo",
                last_name="Athlete",
                language="en",
            )

        await session.commit()
        return coach, athlete

    return await DatabaseManager.execute_with_session(_create_users)


async def demo_coach_request_flow():
    """Demonstrate the complete coach request flow."""
    print("🚀 Starting Coach Request Demo")
    print("=" * 50)

    # Initialize database
    await init_db()

    # Create test users
    coach, athlete = await create_test_users()
    print(f"✅ Created coach: {coach.first_name} (@{coach.username})")
    print(f"✅ Created athlete: {athlete.first_name} (@{athlete.username})")
    print()

    # Step 1: Coach sends request to athlete
    print("📩 Step 1: Coach sends request to athlete")
    print("-" * 40)

    async def _send_request(session):
        return await AthleteCoachRequestRepository.create_request(
            session,
            coach_id=coach.id,
            athlete_id=athlete.id,
            message="Hi! I'd like to be your coach and help you track your fitness progress. Would you like to work together?",
            expires_in_days=7,
        )

    request = await DatabaseManager.execute_with_session(_send_request)
    print(f"✅ Request created with ID: {request.id}")
    print(f"   Status: {request.status}")
    print(f"   Expires: {request.expires_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Message: {request.message}")
    print()

    # Step 2: Check pending requests for athlete
    print("📋 Step 2: Check pending requests for athlete")
    print("-" * 40)

    async def _get_athlete_requests(session):
        return await AthleteCoachRequestRepository.get_athlete_pending_requests(
            session, athlete.id
        )

    pending_requests = await DatabaseManager.execute_with_session(_get_athlete_requests)
    print(f"✅ Found {len(pending_requests)} pending request(s) for athlete")

    for req in pending_requests:
        print(
            f"   Request #{req.id} from coach: {req.coach.first_name} (@{req.coach.username})"
        )
        print(f"   Created: {req.created_at.strftime('%Y-%m-%d %H:%M')}")
    print()

    # Step 3: Athlete accepts the request
    print("✅ Step 3: Athlete accepts the request")
    print("-" * 40)

    async def _accept_request(session):
        return await AthleteCoachRequestRepository.accept_request(session, request.id)

    accepted_request = await DatabaseManager.execute_with_session(_accept_request)
    print("✅ Request accepted!")
    print(f"   Status: {accepted_request.status}")
    print(
        f"   Responded at: {accepted_request.responded_at.strftime('%Y-%m-%d %H:%M')}"
    )
    print()

    # Step 4: Verify coach-athlete relationship was created
    print("🔗 Step 4: Verify coach-athlete relationship")
    print("-" * 40)

    async def _check_relationship(session):
        return await CoachAthleteRepository.is_coach_of_athlete(
            session, coach.id, athlete.id
        )

    is_coach = await DatabaseManager.execute_with_session(_check_relationship)
    print(f"✅ Coach-athlete relationship established: {is_coach}")

    # Get coach's athletes
    async def _get_coach_athletes(session):
        return await CoachAthleteRepository.get_coach_athletes(session, coach.id)

    coach_athletes = await DatabaseManager.execute_with_session(_get_coach_athletes)
    print(f"✅ Coach now has {len(coach_athletes)} athlete(s):")
    for athlete_user in coach_athletes:
        print(f"   - {athlete_user.first_name} (@{athlete_user.username})")
    print()

    # Step 5: Test rejection scenario with a new request
    print("❌ Step 5: Test rejection scenario")
    print("-" * 40)

    # Create another athlete
    async def _create_second_athlete(session):
        athlete2 = await UserRepository.get_user_by_telegram_id(session, 555666777)
        if not athlete2:
            athlete2 = await UserRepository.create_user(
                session,
                telegram_id=555666777,
                username="demo_athlete_2",
                first_name="Second",
                last_name="Athlete",
                language="en",
            )
        return athlete2

    athlete2 = await DatabaseManager.execute_with_session(_create_second_athlete)
    print(f"✅ Created second athlete: {athlete2.first_name} (@{athlete2.username})")

    # Send request to second athlete
    async def _send_second_request(session):
        return await AthleteCoachRequestRepository.create_request(
            session,
            coach_id=coach.id,
            athlete_id=athlete2.id,
            message="Would you like me to be your coach?",
            expires_in_days=3,
        )

    request2 = await DatabaseManager.execute_with_session(_send_second_request)
    print(f"✅ Second request created with ID: {request2.id}")

    # Reject the request
    async def _reject_request(session):
        return await AthleteCoachRequestRepository.reject_request(session, request2.id)

    rejected_request = await DatabaseManager.execute_with_session(_reject_request)
    print("✅ Request rejected!")
    print(f"   Status: {rejected_request.status}")
    print(
        f"   Responded at: {rejected_request.responded_at.strftime('%Y-%m-%d %H:%M')}"
    )
    print()

    # Step 6: Test expiration of old requests
    print("⏰ Step 6: Test request expiration")
    print("-" * 40)

    # Create an expired request (manually set expiration date)
    async def _create_expired_request(session):
        # Create third athlete
        athlete3 = await UserRepository.get_user_by_telegram_id(session, 888999111)
        if not athlete3:
            athlete3 = await UserRepository.create_user(
                session,
                telegram_id=888999111,
                username="demo_athlete_3",
                first_name="Third",
                last_name="Athlete",
                language="en",
            )

        # Create request with past expiration
        request3 = await AthleteCoachRequestRepository.create_request(
            session,
            coach_id=coach.id,
            athlete_id=athlete3.id,
            message="Old request",
            expires_in_days=7,
        )

        # Manually set expiration to past
        request3.expires_at = datetime.now(UTC) - timedelta(days=1)
        await session.commit()

        return request3

    expired_request = await DatabaseManager.execute_with_session(
        _create_expired_request
    )
    print(f"✅ Created expired request with ID: {expired_request.id}")
    print(f"   Expires: {expired_request.expires_at.strftime('%Y-%m-%d %H:%M')}")

    # Expire old requests
    async def _expire_old_requests(session):
        return await AthleteCoachRequestRepository.expire_old_requests(session)

    expired_count = await DatabaseManager.execute_with_session(_expire_old_requests)
    print(f"✅ Expired {expired_count} old request(s)")
    print()

    # Summary
    print("📊 Demo Summary")
    print("=" * 50)
    print("✅ Successfully demonstrated:")
    print("   - Creating coach requests")
    print("   - Retrieving pending requests")
    print("   - Accepting requests")
    print("   - Rejecting requests")
    print("   - Automatic relationship creation")
    print("   - Request expiration")
    print()
    print("🎉 Coach request system is working correctly!")

    # Clean up - DatabaseManager doesn't have a close method
    print("✅ Demo completed successfully!")


if __name__ == "__main__":
    print("🔧 EasyTrack Coach Request System Demo")
    print("=" * 50)
    print("This demo will test the new coach-athlete request system")
    print("Make sure you have a running PostgreSQL database configured")
    print()

    try:
        asyncio.run(demo_coach_request_flow())
    except KeyboardInterrupt:
        print("\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
