from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Float,
    ForeignKey,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user_measurement_types: Mapped[List["UserMeasurementType"]] = relationship(
        "UserMeasurementType", back_populates="user", cascade="all, delete-orphan"
    )
    measurements: Mapped[List["Measurement"]] = relationship(
        "Measurement", back_populates="user", cascade="all, delete-orphan"
    )


class MeasurementType(Base):
    __tablename__ = "measurement_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # cm, kg, inches, etc.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
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
    user_measurement_types: Mapped[List["UserMeasurementType"]] = relationship(
        "UserMeasurementType", back_populates="measurement_type"
    )
    measurements: Mapped[List["Measurement"]] = relationship(
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
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
