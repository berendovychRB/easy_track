"""
EasyTrack - Telegram Bot for Body Measurement Tracking

A powerful and scalable Telegram bot for athletes to track their body measurements
with a clean database design and modern async architecture.
"""

__version__ = "1.0.0"
__author__ = "EasyTrack Team"
__email__ = "contact@easytrack.bot"
__description__ = "Telegram bot for tracking body measurements"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]

# Import main components for easy access
from .models import Base, User, MeasurementType, UserMeasurementType, Measurement
from .database import DatabaseManager, init_db, close_db
from .repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
    MeasurementRepository
)

# Make key components available at package level
__all__.extend([
    "Base",
    "User",
    "MeasurementType",
    "UserMeasurementType",
    "Measurement",
    "DatabaseManager",
    "init_db",
    "close_db",
    "UserRepository",
    "MeasurementTypeRepository",
    "UserMeasurementTypeRepository",
    "MeasurementRepository",
])
