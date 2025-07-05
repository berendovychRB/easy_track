from datetime import datetime, time
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User roles in the system."""

    ATHLETE = "athlete"
    COACH = "coach"
    BOTH = "both"  # Can be both coach and athlete


class CoachNotificationType(str, Enum):
    """Types of coach notifications."""

    ATHLETE_MEASUREMENT_ADDED = "athlete_measurement_added"
    ATHLETE_GOAL_ACHIEVED = "athlete_goal_achieved"
    ATHLETE_INACTIVE = "athlete_inactive"
    DAILY_SUMMARY = "daily_summary"


class AthleteCoachRequestStatus(str, Enum):
    """Status of athlete-coach relationship requests."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_role: Mapped[str] = mapped_column(
        String(20), default=UserRole.ATHLETE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user_measurement_types: Mapped[list["UserMeasurementType"]] = relationship(
        "UserMeasurementType", back_populates="user", cascade="all, delete-orphan"
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        "Measurement", back_populates="user", cascade="all, delete-orphan"
    )
    notification_schedules: Mapped[list["NotificationSchedule"]] = relationship(
        "NotificationSchedule", back_populates="user", cascade="all, delete-orphan"
    )
    coached_athletes: Mapped[list["CoachAthleteRelationship"]] = relationship(
        "CoachAthleteRelationship",
        foreign_keys="CoachAthleteRelationship.coach_id",
        back_populates="coach",
        cascade="all, delete-orphan",
    )
    coaches: Mapped[list["CoachAthleteRelationship"]] = relationship(
        "CoachAthleteRelationship",
        foreign_keys="CoachAthleteRelationship.athlete_id",
        back_populates="athlete",
        cascade="all, delete-orphan",
    )


class MeasurementType(Base):
    __tablename__ = "measurement_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # cm, kg, inches, etc.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Add unique constraint for name per user (global for system types, per-user for custom types)
    __table_args__ = (
        UniqueConstraint(
            "name", "created_by_user_id", name="uq_measurement_type_name_user"
        ),
    )

    # Relationships
    user_measurement_types: Mapped[list["UserMeasurementType"]] = relationship(
        "UserMeasurementType", back_populates="measurement_type"
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        "Measurement", back_populates="measurement_type"
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )


class UserMeasurementType(Base):
    __tablename__ = "user_measurement_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    measurement_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("measurement_types.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Unique constraint to prevent duplicate user-measurement_type combinations
    __table_args__ = (
        UniqueConstraint(
            "user_id", "measurement_type_id", name="uq_user_measurement_type"
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_measurement_types")
    measurement_type: Mapped["MeasurementType"] = relationship(
        "MeasurementType", back_populates="user_measurement_types"
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    measurement_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("measurement_types.id"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    measurement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Index for efficient querying by user and measurement type
    __table_args__ = (
        # Index for common query patterns
        {"extend_existing": True}
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="measurements")
    measurement_type: Mapped["MeasurementType"] = relationship(
        "MeasurementType", back_populates="measurements"
    )


class NotificationSchedule(Base):
    __tablename__ = "notification_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    day_of_week: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,  # 0=Monday, 1=Tuesday, ..., 6=Sunday, None=Daily
    )
    notification_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), default="UTC", nullable=False
    )  # Store user's timezone
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Unique constraint to prevent duplicate schedules for same user
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "day_of_week",
            "notification_time",
            name="uq_user_notification_schedule",
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_schedules")


class CoachAthleteRelationship(Base):
    """Represents coach-athlete relationships."""

    __tablename__ = "coach_athlete_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete"),
        CheckConstraint("coach_id != athlete_id", name="check_no_self_coaching"),
    )

    # Relationships
    coach: Mapped["User"] = relationship(
        "User", foreign_keys=[coach_id], back_populates="coached_athletes"
    )
    athlete: Mapped["User"] = relationship(
        "User", foreign_keys=[athlete_id], back_populates="coaches"
    )


class CoachNotificationPreference(Base):
    """Coach notification preferences for different event types."""

    __tablename__ = "coach_notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "coach_id", "notification_type", name="uq_coach_notification_type"
        ),
    )

    # Relationships
    coach: Mapped["User"] = relationship("User", foreign_keys=[coach_id])


class CoachNotificationQueue(Base):
    """Queue for pending coach notifications."""

    __tablename__ = "coach_notification_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("measurements.id"), nullable=True
    )
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    coach: Mapped["User"] = relationship("User", foreign_keys=[coach_id])
    athlete: Mapped["User"] = relationship("User", foreign_keys=[athlete_id])
    measurement: Mapped[Optional["Measurement"]] = relationship(
        "Measurement", foreign_keys=[measurement_id]
    )


class AthleteCoachRequest(Base):
    """Model for athlete-coach relationship requests."""

    __tablename__ = "athlete_coach_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=AthleteCoachRequestStatus.PENDING, nullable=False
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("coach_id != athlete_id", name="check_no_self_request"),
    )

    # Relationships
    coach: Mapped["User"] = relationship("User", foreign_keys=[coach_id])
    athlete: Mapped["User"] = relationship("User", foreign_keys=[athlete_id])
