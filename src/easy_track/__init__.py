"""
EasySize - Telegram Bot for Body Measurement Tracking

A powerful and scalable Telegram bot for athletes to track their body measurements
with a clean database design and modern async architecture.
"""

__version__ = "1.0.0"
__author__ = "EasySize Team"
__email__ = "contact@EasySize.bot"
__description__ = "Telegram bot for tracking body measurements"

# Package metadata
__all__ = [
    "__author__",
    "__description__",
    "__email__",
    "__version__",
]

# Import main components for easy access
from .database import DatabaseManager, close_db, init_db
from .models import Base, Measurement, MeasurementType, User, UserMeasurementType
from .repositories import (
    MeasurementRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
    UserRepository,
)

# Make key components available at package level
__all__.extend(
    [
        "Base",
        "DatabaseManager",
        "Measurement",
        "MeasurementRepository",
        "MeasurementType",
        "MeasurementTypeRepository",
        "User",
        "UserMeasurementType",
        "UserMeasurementTypeRepository",
        "UserRepository",
        "close_db",
        "init_db",
    ]
)
