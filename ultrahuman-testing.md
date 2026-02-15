# Ultrahuman Integration Testing Guide

This guide covers testing the Ultrahuman Ring Air provider integration for Open Wearables.

## Overview

The Ultrahuman provider tests are located in `backend/tests/providers/ultrahuman/` and provide comprehensive coverage of:

- **Strategy Configuration** - Provider registration, API endpoints, component initialization
- **OAuth Flow** - Authorization, token exchange, user profile fetching, token refresh
- **24/7 Data Sync** - Sleep sessions, recovery metrics, activity samples (HR, HRV, temperature, steps)

## Test Structure

```
backend/tests/providers/ultrahuman/
├── __init__.py                      # Test module initialization
├── conftest.py                      # Provider-specific fixtures
├── test_ultrahuman_strategy.py       # Strategy configuration tests (13 tests)
├── test_ultrahuman_oauth.py          # OAuth flow tests (13 tests)
└── test_ultrahuman_data_247.py     # 24/7 data sync tests (23 tests)
```

## Running Tests

### Prerequisites

Ensure PostgreSQL is running and test database is created:

```bash
# Start PostgreSQL
docker compose up db -d

# Create test database (if not exists)
docker compose exec db psql -U open-wearables -c "CREATE DATABASE open_wearables_test;"
```

### Running All Tests

```bash
cd backend
uv run pytest tests/providers/ultrahuman/ -v
```

### Running Specific Test Files

```bash
# Strategy tests only
uv run pytest tests/providers/ultrahuman/test_ultrahuman_strategy.py -v

# OAuth tests only
uv run pytest tests/providers/ultrahuman/test_ultrahuman_oauth.py -v

# 24/7 data tests only
uv run pytest tests/providers/ultrahuman/test_ultrahuman_data_247.py -v
```

### Running Specific Tests

```bash
# Single test
uv run pytest tests/providers/ultrahuman/test_ultrahuman_strategy.py::TestUltrahumanStrategy::test_name_is_ultrahuman -v

# Tests matching a pattern
uv run pytest tests/providers/ultrahuman/ -k "oauth" -v
uv run pytest tests/providers/ultrahuman/ -k "sleep" -v
```

## Writing New Tests

### 1. Define Mock Data in `conftest.py`

Use fixtures for reusable mock data following Ultrahuman's API structure:

```python
@pytest.fixture
def sample_ultrahuman_sleep() -> dict:
    """Sample Ultrahuman sleep JSON data."""
    return {
        "type": "Sleep",
        "object": {
            "bedtime_start": 1705309200,  # Unix timestamp
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
        },
    }
```

**Guidelines for mock data:**
- Use realistic timestamps (Unix format in seconds since epoch)
- Include all required fields and optional fields that affect logic
- Use consistent date patterns (e.g., 2024-01-15 for all samples)
- Include edge cases: missing fields, zero values, invalid formats

### 2. Use Test Patterns

#### Strategy Tests

Test configuration and initialization:

```python
class TestUltrahumanStrategy:
    """Tests for UltrahumanStrategy class."""

    def test_name_is_ultrahuman(self) -> None:
        """Strategy name should be 'ultrahuman'."""
        strategy = UltrahumanStrategy()
        assert strategy.name == "ultrahuman"

    def test_api_base_url(self) -> None:
        """API base URL should be Ultrahuman's API endpoint."""
        strategy = UltrahumanStrategy()
        assert strategy.api_base_url == "https://partner.ultrahuman.com/api/partners/v1"
```

#### OAuth Tests

Mock network calls with `unittest.mock.patch`:

```python
@patch("httpx.get")
def test_get_provider_user_info_success(
    self,
    mock_httpx_get: MagicMock,
    ultrahuman_oauth: UltrahumanOAuth,
) -> None:
    """Test fetching Ultrahuman user info successfully."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "user_id": "ultrahuman_user_12345",
        "username": "test_user",
    }
    mock_response.raise_for_status.return_value = None
    mock_httpx_get.return_value = mock_response

    # Act
    user_info = ultrahuman_oauth._get_provider_user_info(token_response, "internal_user_id")

    # Assert
    assert user_info["user_id"] == "ultrahuman_user_12345"
    mock_httpx_get.assert_called_once_with(
        "https://partner.ultrahuman.com/api/partners/v1/user_data/user_info",
        headers={"Authorization": "Bearer test_access_token"},
        timeout=30.0,
    )
```

#### Data Sync Tests

Test normalization and saving logic:

```python
@patch("app.services.providers.ultrahuman.data_247.make_authenticated_request")
def test_fetch_daily_metrics_success(
    self,
    mock_request: MagicMock,
    ultrahuman_data_247: Ultrahuman247Data,
    db: Session,
) -> None:
    """Test fetching daily metrics successfully."""
    # Arrange
    user = UserFactory()
    UserConnectionFactory(user=user, provider="ultrahuman")
    test_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

    mock_request.return_value = sample_metrics_response

    # Act
    result = ultrahuman_data_247._fetch_daily_metrics(db, user.id, test_date)

    # Assert
    assert len(result) == 4  # Sleep, recovery, hr, steps
    mock_request.assert_called_once()
```

### 3. Use Correct Data Types

#### For `normalize_activity_samples`

When testing with raw samples, use the **API format** (without "object" wrapper):

```python
# ✅ Correct - for normalize_activity_samples
samples = [
    {
        "type": "hr",
        "values": [
            {"timestamp": 1705309260, "value": 68},
        ]
    },
]

# ❌ Incorrect - this has "object" wrapper
samples = [
    {
        "type": "hr",
        "object": {
            "values": [
                {"timestamp": 1705309260, "value": 68},
            ]
        }
    },
]
```

#### For `_fetch_daily_metrics`

The `_fetch_daily_metrics` method adds the "object" wrapper. Use fixtures that include it:

```python
@pytest.fixture
def sample_ultrahuman_daily_metrics_response() -> dict:
    """Sample complete Ultrahuman daily metrics response."""
    return {
        "data": {
            "metric_data": [
                {
                    "type": "hr",
                    "object": {
                        "values": [
                            {"timestamp": 1705309260, "value": 68},
                        ]
                    },
                },
            ]
        }
    }
```

## Common Pitfalls

### 1. Mutable Mock Data

**Problem:** Using the same mock data in multiple calls causes mutation issues.

**Solution:** Use `copy.deepcopy()` in test setup or patch functions:

```python
# ✅ Correct
def fresh_response(*args, **kwargs):
    return copy.deepcopy(sample_metrics_response)

mock_request.side_effect = fresh_response

# ❌ Incorrect
mock_request.return_value = sample_metrics_response
```

### 2. Incorrect Data Format

**Problem:** Using wrong data format for the method being tested.

**Solution:** Check the method's expected input format:
- `_fetch_daily_metrics`: Expects API response with "object" wrapper
- `normalize_activity_samples`: Expects raw list without "object" wrapper

### 3. Mocking Side Effects

**Problem:** Mock methods without tracking how they were called.

**Solution:** Use `side_effect` to track calls:

```python
call_count = [0]

def track_call(*args, **kwargs):
    call_count[0] += 1
    return original_function(*args, **kwargs)

with patch.object(sut, 'method', side_effect=track_call):
    sut.method()
    assert call_count[0] == expected_calls
```

### 4. Database Isolation

**Problem:** Tests interfere with each other's database state.

**Solution:** Always use the `db` fixture which provides transaction rollback:

```python
def test_example(self, db: Session) -> None:
    """Test with database isolation."""
    # db fixture handles automatic rollback after test
    user = UserFactory()
    # ... test code ...
```

## Test Coverage Areas

### Must-Have Coverage

- [ ] Strategy initialization and configuration
- [ ] OAuth endpoints configuration
- [ ] Authorization URL generation
- [ ] Token exchange (with and without PKCE)
- [ ] Token refresh flow
- [ ] User profile fetching
- [ ] Error handling (401, 403, 500)
- [ ] Sleep data normalization (complete, partial, missing data)
- [ ] Recovery metrics normalization
- [ ] Activity samples normalization (HR, HRV, temperature, steps)
- [ ] Daily metrics fetching and date injection
- [ ] Saving data to database
- [ ] Multi-day range iteration
- [ ] Default behavior (30-day range)

### Optional Coverage

- [ ] Edge cases in data (empty values, negative values, far future dates)
- [ ] Concurrent request handling
- [ ] Performance benchmarks for bulk operations

## Debugging Tests

### Enable Verbose Output

```bash
uv run pytest tests/providers/ultrahuman/ -vv --tb=long
```

### Add Debug Prints

For complex tests, add debug output that's disabled by default:

```python
import os

def test_complex_flow(self) -> None:
    """Test complex integration flow."""
    if os.getenv("DEBUG_TESTS"):
        print(f"DEBUG: Starting complex flow test")

    # ... test code ...
```

Run with debug enabled:
```bash
DEBUG_TESTS=1 uv run pytest tests/providers/ultrahuman/test_ultrahuman_data_247.py::test_complex_flow -v -s
```

### Use pdb for Interactive Debugging

```bash
# Run with debugger on first failure
uv run pytest tests/providers/ultrahuman/ --pdb
```

## Code Quality

### Type Hints

All test functions must have return type annotations:

```python
def test_name_is_ultrahuman(self) -> None:
    """Strategy name should be 'ultrahuman'."""
    strategy = UltrahumanStrategy()
    assert strategy.name == "ultrahuman"
```

### Lint and Format

Always run linting and formatting after adding tests:

```bash
cd backend

# Run linting
uv run ruff check tests/providers/ultrahuman/

# Auto-fix linting issues
uv run ruff check tests/providers/ultrahuman/ --fix

# Format code
uv run ruff format tests/providers/ultrahuman/

# Type checking
uv run ty check tests/providers/ultrahuman/
```

## Reference: Existing Test Patterns

For more patterns and examples, see:

- **Garmin Tests:** `backend/tests/providers/garmin/` - Similar OAuth and data sync patterns
- **Base Templates:** `backend/tests/providers/templates/test_base_templates.py` - Abstract class testing
- **Test Factories:** `backend/tests/factories.py` - Database test data creation

## Continuous Integration

The Ultrahuman tests run as part of the full test suite:

```bash
# Run all backend tests
uv run pytest

# Run all provider tests
uv run pytest tests/providers/

# Run with coverage
uv run pytest tests/providers/ultrahuman/ --cov=app/services/providers/ultrahuman --cov-report=html
```

## Summary

The Ultrahuman test suite provides comprehensive coverage of the provider integration following project best practices. When adding new tests:

1. Add mock data to `conftest.py`
2. Follow existing test patterns for the type of test
3. Use proper mocking for external dependencies
4. Ensure type hints and descriptive docstrings
5. Run linting and formatting before committing
6. Verify tests pass in isolation and as a suite

Total test count: **49 tests**
- Strategy tests: 13
- OAuth tests: 13
- 24/7 Data tests: 23
