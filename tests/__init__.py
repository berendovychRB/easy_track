"""
Test package for EasySize - Telegram Bot for Body Measurement Tracking

This package contains all test files for the EasySize application.
"""

import sys
from pathlib import Path

# Add src directory to Python path for testing
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Test configuration
TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5433/easy_track_test"
TEST_BOT_TOKEN = "test_token_123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"

__all__ = [
    "TEST_DATABASE_URL",
    "TEST_BOT_TOKEN",
]
