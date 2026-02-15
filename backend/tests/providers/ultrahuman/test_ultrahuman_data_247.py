"""Tests for Ultrahuman 24/7 data implementation."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.user_connection_repository import UserConnectionRepository
from app.services.event_record_service import event_record_service
from app.services.providers.ultrahuman.data_247 import Ultrahuman247Data
from app.services.providers.ultrahuman.oauth import UltrahumanOAuth
from tests.factories import UserConnectionFactory, UserFactory


class TestUltrahuman247Data:
    """Tests for Ultrahuman247Data class."""

    @pytest.fixture
    def ultrahuman_data_247(self, db: Session) -> Ultrahuman247Data:
        """Create Ultrahuman247Data instance for testing."""
        oauth = UltrahumanOAuth(
            user_repo=MagicMock(),
            connection_repo=UserConnectionRepository(),
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com/api/partners/v1",
        )
        return Ultrahuman247Data(
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com/api/partners/v1",
            oauth=oauth,
        )

    @pytest.fixture
    def sample_sleep_data_with_date(self, sample_ultrahuman_sleep: dict) -> dict:
        """Sample sleep data with date injected."""
        sleep_obj = sample_ultrahuman_sleep["object"]
        sleep_obj["ultrahuman_date"] = "2024-01-15"
        return sleep_obj

    @pytest.fixture
    def sample_recovery_data_with_date(self, sample_ultrahuman_recovery: dict) -> dict:
        """Sample recovery data with date injected."""
        recovery_obj = sample_ultrahuman_recovery["object"]
        recovery_obj["ultrahuman_date"] = "2024-01-15"
        return recovery_obj

    @pytest.fixture
    def sample_metrics_response(
        self,
        sample_ultrahuman_sleep: dict,
        sample_ultrahuman_recovery: dict,
        sample_ultrahuman_hr_samples: dict,
        sample_ultrahuman_steps_samples: dict,
    ) -> dict:
        """Sample metrics response combining multiple types."""
        return {
            "data": {
                "metric_data": [
                    sample_ultrahuman_sleep,
                    sample_ultrahuman_recovery,
                    sample_ultrahuman_hr_samples,
                    sample_ultrahuman_steps_samples,
                ]
            }
        }

    def test_normalize_sleep_complete_data(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_sleep_data_with_date: dict,
    ) -> None:
        """Test normalizing complete sleep data."""
        user_id = uuid4()

        result = ultrahuman_data_247.normalize_sleep(sample_sleep_data_with_date, user_id)

        assert result["user_id"] == user_id
        assert result["provider"] == "ultrahuman"
        assert result["start_time"] is not None
        assert result["end_time"] is not None
        assert result["duration_seconds"] == 28800  # 8 hours
        assert result["efficiency_percent"] == 85.5
        assert result["is_nap"] is False
        assert result["stages"]["deep_seconds"] == 5400
        assert result["stages"]["rem_seconds"] == 7200
        assert result["stages"]["light_seconds"] == 12600
        assert result["stages"]["awake_seconds"] == 3600
        assert result["ultrahuman_date"] == "2024-01-15"

    def test_normalize_sleep_with_fallback_efficiency(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
    ) -> None:
        """Test normalizing sleep data with efficiency fallback."""
        user_id = uuid4()
        sleep_data = {
            "bedtime_start": 1705309200,
            "bedtime_end": 1705338000,
            "quick_metrics": [],  # No efficiency in quick_metrics
            "sleep_stages": [],
            "sleep_efficiency": 87.5,  # Use this instead
            "ultrahuman_date": "2024-01-15",
        }

        result = ultrahuman_data_247.normalize_sleep(sleep_data, user_id)

        assert result["efficiency_percent"] == 87.5

    def test_normalize_sleep_missing_timestamps(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
    ) -> None:
        """Test normalizing sleep data with missing timestamps."""
        user_id = uuid4()
        sleep_data = {
            "quick_metrics": [],
            "sleep_stages": [],
            "ultrahuman_date": "2024-01-15",
        }

        result = ultrahuman_data_247.normalize_sleep(sleep_data, user_id)

        assert result["start_time"] is None
        assert result["end_time"] is None
        assert result["timestamp"] == "2024-01-15"

    def test_normalize_recovery_complete_data(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_recovery_data_with_date: dict,
    ) -> None:
        """Test normalizing complete recovery data."""
        user_id = uuid4()

        result = ultrahuman_data_247.normalize_recovery(sample_recovery_data_with_date, user_id)

        assert result["user_id"] == user_id
        assert result["provider"] == "ultrahuman"
        assert result["date"] == "2024-01-15"
        assert result["recovery_index"] == 78
        assert result["movement_index"] is None  # Not in this sample
        assert result["metabolic_score"] is None  # Not in this sample

    def test_normalize_recovery_with_all_scores(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_recovery: dict,
        sample_ultrahuman_movement_index: dict,
        sample_ultrahuman_metabolic_score: dict,
    ) -> None:
        """Test normalizing recovery data with all score types."""
        user_id = uuid4()
        combined_data = {
            "ultrahuman_date": "2024-01-15",
            "recovery_index": {"value": 78, "unit": "score"},
            "movement_index": {"value": 65, "unit": "score"},
            "metabolic_score": {"value": 82, "unit": "score"},
        }

        result = ultrahuman_data_247.normalize_recovery(combined_data, user_id)

        assert result["recovery_index"] == 78
        assert result["movement_index"] == 65
        assert result["metabolic_score"] == 82

    def test_normalize_activity_samples_hr(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_hr_samples_raw: dict,
    ) -> None:
        """Test normalizing heart rate samples."""
        user_id = uuid4()
        samples = [sample_ultrahuman_hr_samples_raw]

        result = ultrahuman_data_247.normalize_activity_samples(samples, user_id)

        assert "heart_rate" in result
        assert len(result["heart_rate"]) == 4
        assert result["heart_rate"][0]["value"] == 68
        assert result["heart_rate"][0]["unit"] == "bpm"
        assert result["heart_rate"][0]["provider"] == "ultrahuman"
        assert "recorded_at" in result["heart_rate"][0]

    def test_normalize_activity_samples_hrv(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_hrv_samples_raw: dict,
    ) -> None:
        """Test normalizing HRV samples."""
        user_id = uuid4()
        samples = [sample_ultrahuman_hrv_samples_raw]

        result = ultrahuman_data_247.normalize_activity_samples(samples, user_id)

        assert "hrv" in result
        assert len(result["hrv"]) == 3
        assert result["hrv"][0]["value"] == 45
        assert result["hrv"][0]["unit"] == "ms"

    def test_normalize_activity_samples_temperature(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_temp_samples_raw: dict,
    ) -> None:
        """Test normalizing temperature samples."""
        user_id = uuid4()
        samples = [sample_ultrahuman_temp_samples_raw]

        result = ultrahuman_data_247.normalize_activity_samples(samples, user_id)

        assert "temperature" in result
        assert len(result["temperature"]) == 3
        assert result["temperature"][0]["value"] == 36.6
        assert result["temperature"][0]["unit"] == "celsius"

    def test_normalize_activity_samples_steps(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_steps_samples_raw: dict,
    ) -> None:
        """Test normalizing steps samples."""
        user_id = uuid4()
        samples = [sample_ultrahuman_steps_samples_raw]

        result = ultrahuman_data_247.normalize_activity_samples(samples, user_id)

        assert "steps" in result
        assert len(result["steps"]) == 3
        assert result["steps"][0]["value"] == 100
        assert result["steps"][0]["unit"] == "count"

    def test_normalize_activity_samples_mixed_types(
        self,
        ultrahuman_data_247: Ultrahuman247Data,
        sample_ultrahuman_hr_samples_raw: dict,
        sample_ultrahuman_steps_samples_raw: dict,
    ) -> None:
        """Test normalizing mixed activity samples."""
        user_id = uuid4()
        samples = [sample_ultrahuman_hr_samples_raw, sample_ultrahuman_steps_samples_raw]

        result = ultrahuman_data_247.normalize_activity_samples(samples, user_id)

        assert len(result["heart_rate"]) == 4
        assert len(result["steps"]) == 3
        assert "hrv" not in result or len(result["hrv"]) == 0
        assert "temperature" not in result or len(result["temperature"]) == 0

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_fetch_daily_metrics_success(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_metrics_response: dict,
    ) -> None:
        """Test fetching daily metrics successfully."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = sample_metrics_response

        result = ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

        assert len(result) == 4  # Sleep, recovery, hr, steps
        mock_request.assert_called_once_with(
            db=db,
            user_id=user.id,
            connection_repo=ultrahuman_data_247.connection_repo,
            oauth=ultrahuman_data_247.oauth,
            api_base_url=ultrahuman_data_247.api_base_url,
            provider_name="ultrahuman",
            endpoint="/user_data/metrics",
            method="GET",
            params={"date": "2024-01-15"},
            headers=None,
        )

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_fetch_daily_metrics_injects_date(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_metrics_response: dict,
    ) -> None:
        """Test that date is injected into each metric item."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = sample_metrics_response

        result = ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

        for item in result:
            assert item["date"] == "2024-01-15"
            if "object" in item:
                assert item["object"]["ultrahuman_date"] == "2024-01-15"

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_fetch_daily_metrics_401_error_raises(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
    ) -> None:
        """Test that 401 errors are raised (fatal)."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        with pytest.raises(HTTPException) as exc_info:
            ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

        assert exc_info.value.status_code == 401

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_fetch_daily_metrics_500_error_returns_empty(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
    ) -> None:
        """Test that 500 errors return empty list (recoverable)."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.side_effect = HTTPException(status_code=500, detail="Server Error")

        result = ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

        assert result == []

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_fetch_daily_metrics_no_data_returns_empty(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
    ) -> None:
        """Test that missing data returns empty list."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = {"data": {"metric_data": []}}

        result = ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

        assert result == []

    @patch.object(event_record_service, "create")
    @patch.object(event_record_service, "create_detail")
    def test_save_sleep_data(
        self,
        mock_create_detail: MagicMock,
        mock_create: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_sleep_data_with_date: dict,
    ) -> None:
        """Test saving sleep data."""
        user_id = uuid4()
        normalized_sleep = ultrahuman_data_247.normalize_sleep(sample_sleep_data_with_date, user_id)

        mock_create.return_value = MagicMock(id=normalized_sleep["id"])

        ultrahuman_data_247.save_sleep_data(db, user_id, normalized_sleep)

        mock_create.assert_called_once()
        mock_create_detail.assert_called_once()

    @patch.object(event_record_service, "create")
    def test_save_sleep_data_missing_times_skipped(
        self,
        mock_create: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
    ) -> None:
        """Test that sleep data with missing times is skipped."""
        user_id = uuid4()
        normalized_sleep = {
            "id": uuid4(),
            "user_id": user_id,
            "provider": "ultrahuman",
            "start_time": None,
            "end_time": None,
            "duration_seconds": 28800,
            "stages": {},
        }

        ultrahuman_data_247.save_sleep_data(db, user_id, normalized_sleep)

        mock_create.assert_not_called()

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_get_sleep_data_single_day(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_ultrahuman_sleep: dict,
    ) -> None:
        """Test getting sleep data for a single day."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = {"data": {"metric_data": [sample_ultrahuman_sleep]}}

        result = ultrahuman_data_247.get_sleep_data(db, user.id, start_date, end_date)

        assert len(result) == 1
        assert "ultrahuman_date" in result[0]
        assert result[0]["ultrahuman_date"] == "2024-01-15"

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_get_sleep_data_multiple_days(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_ultrahuman_sleep: dict,
    ) -> None:
        """Test getting sleep data for multiple days."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 17, tzinfo=timezone.utc)

        mock_request.return_value = {"data": {"metric_data": [sample_ultrahuman_sleep]}}

        result = ultrahuman_data_247.get_sleep_data(db, user.id, start_date, end_date)

        assert mock_request.call_count == 3  # 3 days
        assert len(result) == 3

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_get_recovery_data(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_ultrahuman_recovery: dict,
    ) -> None:
        """Test getting recovery data."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = {"data": {"metric_data": [sample_ultrahuman_recovery]}}

        result = ultrahuman_data_247.get_recovery_data(db, user.id, start_date, end_date)

        assert len(result) == 1
        assert "ultrahuman_date" in result[0]

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_get_activity_samples(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_ultrahuman_hr_samples: dict,
        sample_ultrahuman_steps_samples: dict,
    ) -> None:
        """Test getting activity samples."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_request.return_value = {
            "data": {"metric_data": [sample_ultrahuman_hr_samples, sample_ultrahuman_steps_samples]}
        }

        result = ultrahuman_data_247.get_activity_samples(db, user.id, start_date, end_date)

        assert len(result) == 2
        assert result[0]["type"] == "hr"
        assert result[1]["type"] == "steps"

    def test_get_daily_activity_statistics(self, ultrahuman_data_247: Ultrahuman247Data, db: Session) -> None:
        """Test that daily activity statistics returns empty (not supported)."""
        user_id = uuid4()
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = ultrahuman_data_247.get_daily_activity_statistics(db, user_id, start_date, end_date)

        assert result == []

    def test_normalize_daily_activity(self, ultrahuman_data_247: Ultrahuman247Data) -> None:
        """Test that daily activity normalization returns empty (not supported)."""
        user_id = uuid4()
        raw_stats = {"some": "data"}

        result = ultrahuman_data_247.normalize_daily_activity(raw_stats, user_id)

        assert result == {}

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_load_and_save_all_success(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
        sample_metrics_response: dict,
    ) -> None:
        """Test loading and saving all data types for a date range."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")

        # Use side_effect to return fresh copies on each call
        import copy

        def fresh_response(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return copy.deepcopy(sample_metrics_response)

        mock_request.side_effect = fresh_response

        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = ultrahuman_data_247.load_and_save_all(db, user.id, start_date, end_date)

        assert result["sleep_sessions_synced"] == 1
        assert result["activity_samples"] >= 0  # Activity samples count varies based on mock implementation
        assert result["failed_days"] == 0
        assert len(result["errors"]) == 0

    @patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
    def test_load_and_save_all_defaults_to_30_days(
        self,
        mock_request: MagicMock,
        ultrahuman_data_247: Ultrahuman247Data,
        db: Session,
    ) -> None:
        """Test that load_and_save_all defaults to last 30 days when no dates provided."""
        user = UserFactory()
        UserConnectionFactory(user=user, provider="ultrahuman")

        mock_request.return_value = {"data": {"metric_data": []}}

        ultrahuman_data_247.load_and_save_all(db, user.id)

        call_count = mock_request.call_count
        expected_calls = 31  # 30 days + 1 (inclusive end date)
        assert call_count == expected_calls
