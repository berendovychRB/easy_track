"""
Test package structure and imports for EasySize application.

This module contains tests to verify that the package structure is correct
and all modules can be imported properly.
"""

import sys
from pathlib import Path

import pytest

# Ensure we can import from the package
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


class TestPackageStructure:
    """Test package structure and basic imports."""

    def test_package_import(self):
        """Test that the main package can be imported."""
        import easy_track

        assert hasattr(easy_track, "__version__")
        assert easy_track.__version__ == "1.0.0"

    def test_models_import(self):
        """Test that models can be imported."""
        from easy_track.models import (
            Base,
            Measurement,
            MeasurementType,
            User,
            UserMeasurementType,
        )

        # Verify all model classes exist
        assert Base is not None
        assert User is not None
        assert MeasurementType is not None
        assert UserMeasurementType is not None
        assert Measurement is not None

    def test_database_import(self):
        """Test that database module can be imported."""
        from easy_track.database import DatabaseManager, close_db, init_db

        assert DatabaseManager is not None
        assert init_db is not None
        assert close_db is not None

    def test_repositories_import(self):
        """Test that repository classes can be imported."""
        from easy_track.repositories import (
            MeasurementRepository,
            MeasurementTypeRepository,
            UserMeasurementTypeRepository,
            UserRepository,
        )

        assert UserRepository is not None
        assert MeasurementTypeRepository is not None
        assert UserMeasurementTypeRepository is not None
        assert MeasurementRepository is not None

    def test_bot_import(self):
        """Test that bot module can be imported."""
        from easy_track import bot

        assert hasattr(bot, "main")
        assert callable(bot.main)

    def test_main_import(self):
        """Test that main module can be imported."""
        from easy_track import main

        assert hasattr(main, "setup_logging")
        assert callable(main.setup_logging)

    def test_package_exports(self):
        """Test that package exports are available."""
        import easy_track

        # Test that key components are exported at package level
        expected_exports = [
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
        ]

        for export in expected_exports:
            assert hasattr(easy_track, export), f"Package should export {export}"

    def test_model_relationships(self):
        """Test that model relationships are properly defined."""
        from easy_track.models import (
            Measurement,
            MeasurementType,
            User,
            UserMeasurementType,
        )

        # Test User model
        user = User()
        assert hasattr(user, "user_measurement_types")
        assert hasattr(user, "measurements")

        # Test MeasurementType model
        measurement_type = MeasurementType()
        assert hasattr(measurement_type, "user_measurement_types")
        assert hasattr(measurement_type, "measurements")

        # Test UserMeasurementType model
        user_measurement_type = UserMeasurementType()
        assert hasattr(user_measurement_type, "user")
        assert hasattr(user_measurement_type, "measurement_type")

        # Test Measurement model
        measurement = Measurement()
        assert hasattr(measurement, "user")
        assert hasattr(measurement, "measurement_type")

    def test_repository_methods(self):
        """Test that repository classes have expected methods."""
        from easy_track.repositories import UserRepository

        # Test that static methods exist
        assert hasattr(UserRepository, "create_user")
        assert hasattr(UserRepository, "get_user_by_telegram_id")
        assert hasattr(UserRepository, "get_user_by_id")
        assert hasattr(UserRepository, "update_user")

        # Verify they are static methods
        assert callable(UserRepository.create_user)
        assert callable(UserRepository.get_user_by_telegram_id)

    def test_database_manager_methods(self):
        """Test that DatabaseManager has expected methods."""
        from easy_track.database import DatabaseManager

        assert hasattr(DatabaseManager, "get_session")
        assert hasattr(DatabaseManager, "execute_with_session")
        assert callable(DatabaseManager.get_session)
        assert callable(DatabaseManager.execute_with_session)

    def test_package_metadata(self):
        """Test package metadata is correctly set."""
        import easy_track

        assert hasattr(easy_track, "__author__")
        assert hasattr(easy_track, "__email__")
        assert hasattr(easy_track, "__description__")

        assert easy_track.__author__ == "EasySize Team"
        assert easy_track.__email__ == "contact@EasySize.bot"
        assert (
            easy_track.__description__ == "Telegram bot for tracking body measurements"
        )


class TestFileStructure:
    """Test that required files exist in the project structure."""

    def test_required_files_exist(self):
        """Test that all required files exist."""
        project_root = Path(__file__).parent.parent

        required_files = [
            "src/easy_track/__init__.py",
            "src/easy_track/main.py",
            "src/easy_track/bot.py",
            "src/easy_track/models.py",
            "src/easy_track/database.py",
            "src/easy_track/repositories.py",
            "setup.py",
            "requirements.txt",
            "requirements-dev.txt",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "alembic.ini",
            "README.md",
            ".env.example",
            ".gitignore",
            ".dockerignore",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required file {file_path} does not exist"

    def test_directory_structure(self):
        """Test that required directories exist."""
        project_root = Path(__file__).parent.parent

        required_dirs = [
            "src",
            "src/easy_track",
            "alembic",
            "alembic/versions",
            "tests",
        ]

        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert (
                full_path.exists() and full_path.is_dir()
            ), f"Required directory {dir_path} does not exist"


if __name__ == "__main__":
    pytest.main([__file__])
