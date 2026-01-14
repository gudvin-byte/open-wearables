"""
Tests for Ultrahuman 24/7 data implementation.

Tests the Ultrahuman247Data class for sleep, recovery, and activity data handling.
"""

from sqlalchemy.orm import Session

from app.services.providers.ultrahuman.data_247 import Ultrahuman247Data
from app.services.providers.ultrahuman.oauth import UltrahumanOAuth
from tests.factories import UserFactory


class TestUltrahuman247Data:
    """Test suite for Ultrahuman247Data."""

    def test_ultrahuman_247_initialization(self, db: Session) -> None:
        """Should initialize Ultrahuman247Data successfully."""
        # Arrange
        from app.models import User
        from app.repositories.user_connection_repository import UserConnectionRepository
        from app.repositories.user_repository import UserRepository

        user_repo = UserRepository(User)
        connection_repo = UserConnectionRepository()
        oauth = UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
        )

        # Act
        data_247 = Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
            oauth=oauth,
        )

        # Assert
        assert data_247.provider_name == "ultrahuman"
        assert data_247.api_base_url == "https://partner.ultrahuman.com"
        assert data_247.oauth is not None


class TestUltrahumanSleepData:
    """Tests for Ultrahuman sleep data handling."""

    def test_normalize_sleep_with_complete_data(self, db: Session) -> None:
        """Test normalizing sleep data with all fields present."""
        # Arrange
        from app.models import User
        from app.repositories.user_connection_repository import UserConnectionRepository
        from app.repositories.user_repository import UserRepository

        user = UserFactory()
        user_repo = UserRepository(User)
        connection_repo = UserConnectionRepository()
        oauth = UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
        )

        data_247 = Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
            oauth=oauth,
        )

        raw_sleep = {
            "date": "2025-01-14",
            "bed_time": "2025-01-14T22:00:00Z",
            "wake_time": "2025-01-15T06:00:00Z",
            "total_sleep_duration": 28800,  # 8 hours in seconds
            "deep_sleep_duration": 3600,  # 1 hour
            "rem_sleep_duration": 5400,  # 1.5 hours
            "light_sleep_duration": 19800,  # 5.5 hours
            "sleep_efficiency": 90,
            "is_nap": False,
        }

        # Act
        normalized = data_247.normalize_sleep(raw_sleep, user.id)

        # Assert
        assert normalized["user_id"] == user.id
        assert normalized["provider"] == "ultrahuman"
        assert normalized["ultrahuman_date"] == "2025-01-14"
        assert normalized["start_time"] == "2025-01-14T22:00:00Z"
        assert normalized["end_time"] == "2025-01-15T06:00:00Z"
        assert normalized["duration_seconds"] == 28800
        assert normalized["efficiency_percent"] == 90
        assert normalized["is_nap"] is False
        assert normalized["stages"]["deep_seconds"] == 3600
        assert normalized["stages"]["rem_seconds"] == 5400
        assert normalized["stages"]["light_seconds"] == 19800

    def test_normalize_sleep_with_minimal_data(self, db: Session) -> None:
        """Test normalizing sleep data with minimal fields."""
        # Arrange
        from app.models import User
        from app.repositories.user_connection_repository import UserConnectionRepository
        from app.repositories.user_repository import UserRepository

        user = UserFactory()
        user_repo = UserRepository(User)
        connection_repo = UserConnectionRepository()
        oauth = UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
        )

        data_247 = Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
            oauth=oauth,
        )

        raw_sleep = {
            "date": "2025-01-14",
        }

        # Act
        normalized = data_247.normalize_sleep(raw_sleep, user.id)

        # Assert
        assert normalized["user_id"] == user.id
        assert normalized["provider"] == "ultrahuman"
        assert normalized["ultrahuman_date"] == "2025-01-14"
        assert normalized["duration_seconds"] == 0
        assert normalized["efficiency_percent"] is None


class TestUltrahumanRecoveryData:
    """Tests for Ultrahuman recovery data handling."""

    def test_normalize_recovery_with_complete_data(self, db: Session) -> None:
        """Test normalizing recovery data with all fields present."""
        # Arrange
        from app.models import User
        from app.repositories.user_connection_repository import UserConnectionRepository
        from app.repositories.user_repository import UserRepository

        user = UserFactory()
        user_repo = UserRepository(User)
        connection_repo = UserConnectionRepository()
        oauth = UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
        )

        data_247 = Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
            oauth=oauth,
        )

        raw_recovery = {
            "date": "2025-01-14",
            "recovery_index": 85,
            "movement_index": 72,
            "metabolic_score": 78,
        }

        # Act
        normalized = data_247.normalize_recovery(raw_recovery, user.id)

        # Assert
        assert normalized["user_id"] == user.id
        assert normalized["provider"] == "ultrahuman"
        assert normalized["date"] == "2025-01-14"
        assert normalized["recovery_index"] == 85
        assert normalized["movement_index"] == 72
        assert normalized["metabolic_score"] == 78


class TestUltrahumanActivitySamples:
    """Tests for Ultrahuman activity samples handling."""

    def test_normalize_activity_samples(self, db: Session) -> None:
        """Test normalizing activity samples."""
        # Arrange
        from app.models import User
        from app.repositories.user_connection_repository import UserConnectionRepository
        from app.repositories.user_repository import UserRepository

        user = UserFactory()
        user_repo = UserRepository(User)
        connection_repo = UserConnectionRepository()
        oauth = UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
        )

        data_247 = Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com",
            oauth=oauth,
        )

        raw_samples = [
            {
                "date": "2025-01-14",
                "heart_rate": [{"value": 72}, {"value": 75}],
                "hrv": [{"value": 45}, {"value": 50}],
                "temperature": [{"value": 36.5}, {"value": 36.6}],
                "steps": 8500,
            }
        ]

        # Act
        normalized = data_247.normalize_activity_samples(raw_samples, user.id)

        # Assert
        assert "heart_rate" in normalized
        assert "hrv" in normalized
        assert "temperature" in normalized
        assert "steps" in normalized
        assert len(normalized["heart_rate"]) == 2
        assert len(normalized["hrv"]) == 2
        assert len(normalized["temperature"]) == 2
        assert len(normalized["steps"]) == 1
        assert normalized["heart_rate"][0]["value"] == 72
        assert normalized["hrv"][0]["value"] == 45
        assert normalized["temperature"][0]["value"] == 36.5
        assert normalized["steps"][0]["value"] == 8500
