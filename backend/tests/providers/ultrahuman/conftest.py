"""
Ultrahuman-specific test fixtures.

These fixtures provide mock data and utilities for testing Ultrahuman provider integrations.
"""

import pytest


@pytest.fixture
def sample_ultrahuman_sleep() -> dict:
    """Sample Ultrahuman sleep JSON data."""
    return {
        "type": "Sleep",
        "object": {
            "bedtime_start": 1705309200,  # 2024-01-15T08:00:00
            "bedtime_end": 1705338000,  # 2024-01-15T16:00:00
            "quick_metrics": [
                {"type": "time_in_bed", "value": 28800},  # 8 hours
                {"type": "sleep_efic", "value": 85.5},
            ],
            "sleep_stages": [
                {"type": "deep_sleep", "stage_time": 5400},  # 1.5 hours
                {"type": "rem_sleep", "stage_time": 7200},  # 2 hours
                {"type": "light_sleep", "stage_time": 12600},  # 3.5 hours
                {"type": "awake", "stage_time": 3600},  # 1 hour
            ],
            "sleep_efficiency": 87.5,
        },
    }


@pytest.fixture
def sample_ultrahuman_recovery() -> dict:
    """Sample Ultrahuman recovery JSON data."""
    return {
        "type": "recovery_index",
        "object": {
            "recovery_index": {"value": 78, "unit": "score"},
        },
    }


@pytest.fixture
def sample_ultrahuman_movement_index() -> dict:
    """Sample Ultrahuman movement index JSON data."""
    return {
        "type": "movement_index",
        "object": {
            "movement_index": {"value": 65, "unit": "score"},
        },
    }


@pytest.fixture
def sample_ultrahuman_metabolic_score() -> dict:
    """Sample Ultrahuman metabolic score JSON data."""
    return {
        "type": "metabolic_score",
        "object": {
            "metabolic_score": {"value": 82, "unit": "score"},
        },
    }


@pytest.fixture
def sample_ultrahuman_hr_samples_raw() -> dict:
    """Sample Ultrahuman heart rate samples JSON data for normalize_activity_samples."""
    return {
        "type": "hr",
        "values": [
            {"timestamp": 1705309260, "value": 68},  # 2024-01-15T08:01:00
            {"timestamp": 1705309320, "value": 72},
            {"timestamp": 1705309380, "value": 75},
            {"timestamp": 1705309440, "value": 71},
        ],
    }


@pytest.fixture
def sample_ultrahuman_hr_samples() -> dict:
    """Sample Ultrahuman heart rate samples JSON data (API format)."""
    return {
        "type": "hr",
        "object": {
            "values": [
                {"timestamp": 1705309260, "value": 68},  # 2024-01-15T08:01:00
                {"timestamp": 1705309320, "value": 72},
                {"timestamp": 1705309380, "value": 75},
                {"timestamp": 1705309440, "value": 71},
            ]
        },
    }


@pytest.fixture
def sample_ultrahuman_hrv_samples_raw() -> dict:
    """Sample Ultrahuman HRV samples JSON data for normalize_activity_samples."""
    return {
        "type": "hrv",
        "values": [
            {"timestamp": 1705309260, "value": 45},
            {"timestamp": 1705309320, "value": 52},
            {"timestamp": 1705309380, "value": 48},
        ],
    }


@pytest.fixture
def sample_ultrahuman_hrv_samples() -> dict:
    """Sample Ultrahuman HRV samples JSON data (API format)."""
    return {
        "type": "hrv",
        "object": {
            "values": [
                {"timestamp": 1705309260, "value": 45},
                {"timestamp": 1705309320, "value": 52},
                {"timestamp": 1705309380, "value": 48},
            ]
        },
    }


@pytest.fixture
def sample_ultrahuman_temp_samples_raw() -> dict:
    """Sample Ultrahuman temperature samples JSON data for normalize_activity_samples."""
    return {
        "type": "temp",
        "values": [
            {"timestamp": 1705309260, "value": 36.6},
            {"timestamp": 1705309320, "value": 36.7},
            {"timestamp": 1705309380, "value": 36.5},
        ],
    }


@pytest.fixture
def sample_ultrahuman_temp_samples() -> dict:
    """Sample Ultrahuman temperature samples JSON data (API format)."""
    return {
        "type": "temp",
        "object": {
            "values": [
                {"timestamp": 1705309260, "value": 36.6},
                {"timestamp": 1705309320, "value": 36.7},
                {"timestamp": 1705309380, "value": 36.5},
            ]
        },
    }


@pytest.fixture
def sample_ultrahuman_steps_samples_raw() -> dict:
    """Sample Ultrahuman steps samples JSON data for normalize_activity_samples."""
    return {
        "type": "steps",
        "values": [
            {"timestamp": 1705309260, "value": 100},
            {"timestamp": 1705309320, "value": 150},
            {"timestamp": 1705309380, "value": 120},
        ],
    }


@pytest.fixture
def sample_ultrahuman_steps_samples() -> dict:
    """Sample Ultrahuman steps samples JSON data (API format)."""
    return {
        "type": "steps",
        "object": {
            "values": [
                {"timestamp": 1705309260, "value": 100},
                {"timestamp": 1705309320, "value": 150},
                {"timestamp": 1705309380, "value": 120},
            ]
        },
    }


@pytest.fixture
def sample_ultrahuman_daily_metrics_response() -> dict:
    """Sample complete Ultrahuman daily metrics response."""
    return {
        "data": {
            "metric_data": [
                {
                    "type": "Sleep",
                    "object": {
                        "bedtime_start": 1705309200,
                        "bedtime_end": 1705338000,
                        "quick_metrics": [
                            {"type": "time_in_bed", "value": 28800},
                            {"type": "sleep_efic", "value": 85.5},
                        ],
                        "sleep_stages": [
                            {"type": "deep_sleep", "stage_time": 5400},
                            {"type": "rem_sleep", "stage_time": 7200},
                            {"type": "light_sleep", "stage_time": 12600},
                            {"type": "awake", "stage_time": 3600},
                        ],
                        "sleep_efficiency": 87.5,
                    },
                },
                {
                    "type": "recovery_index",
                    "object": {
                        "recovery_index": {"value": 78, "unit": "score"},
                    },
                },
                {
                    "type": "hr",
                    "object": {
                        "values": [
                            {"timestamp": 1705309260, "value": 68},
                            {"timestamp": 1705309320, "value": 72},
                        ]
                    },
                },
                {
                    "type": "steps",
                    "object": {
                        "values": [
                            {"timestamp": 1705309260, "value": 100},
                            {"timestamp": 1705309320, "value": 150},
                        ]
                    },
                },
            ]
        }
    }


@pytest.fixture
def mock_ultrahuman_user_info() -> dict:
    """Mock Ultrahuman user info response."""
    return {
        "user_id": "ultrahuman_user_12345",
        "username": "test_user",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_oauth_token_response() -> dict:
    """Mock OAuth token exchange response."""
    return {
        "access_token": "test_access_token_abc123",
        "refresh_token": "test_refresh_token_xyz789",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "metrics:read profile:read",
    }
