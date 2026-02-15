"""Script to test Ultrahuman integration with real data.

This script allows you to:
1. Test OAuth flow with real Ultrahuman credentials
2. Fetch real sleep, recovery, and activity samples
3. Validate data normalization

WARNING: This script requires valid Ultrahuman developer credentials.
Never commit credentials to the repository.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal
from app.models import DataPointSeries, EventRecord, User, UserConnection
from app.repositories.event_record_repository import EventRecordRepository
from app.repositories.user_connection_repository import UserConnectionRepository
from app.repositories.user_repository import UserRepository
from app.schemas import OAuthTokenResponse
from app.services.providers.ultrahuman.data_247 import Ultrahuman247Data
from app.services.providers.ultrahuman.strategy import UltrahumanStrategy


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def check_credentials() -> bool:
    """Check if Ultrahuman credentials are configured."""
    print_section("Checking Ultrahuman Credentials")

    has_creds = bool(
        settings.ultrahuman_client_id and settings.ultrahuman_client_secret and settings.ultrahuman_redirect_uri
    )

    if has_creds:
        print("✓ Ultrahuman credentials found:")
        print(f"  - Client ID: {settings.ultrahuman_client_id[:10]}...")
        print(f"  - Redirect URI: {settings.ultrahuman_redirect_uri}")
    else:
        print("✗ Ultrahuman credentials not found!")
        print("\nPlease set the following environment variables:")
        print("  ULTRAHUMAN_CLIENT_ID")
        print("  ULTRAHUMAN_CLIENT_SECRET")
        print("  ULTRAHUMAN_REDIRECT_URI")
        print("\nNote: Ultrahuman requires HTTPS redirect URLs.")
        print("For local testing, use ngrok: https://your-ngrok-url.ngrok.io/...")

    return has_creds


def get_authorization_url() -> str:
    """Generate the OAuth authorization URL."""
    print_section("Generate Authorization URL")

    strategy = UltrahumanStrategy()
    oauth = strategy.oauth

    auth_url = oauth.get_authorization_url(state="test_state")
    print("Authorization URL generated:")
    print(f"\n{auth_url}\n")
    print("1. Open this URL in your browser")
    print("2. Authorize the application")
    print("3. Copy the authorization code from the redirect URL")

    return auth_url


def exchange_token(authorization_code: str) -> OAuthTokenResponse:
    """Exchange authorization code for access token."""
    print_section("Exchange Authorization Code for Token")

    strategy = UltrahumanStrategy()
    oauth = strategy.oauth

    token_response = oauth.exchange_token(authorization_code=authorization_code)

    print("✓ Token exchange successful!")
    print(f"  - Access Token: {token_response.access_token[:20]}...")
    print(f"  - Refresh Token: {token_response.refresh_token[:20]}...")
    print(f"  - Expires In: {token_response.expires_in}s")
    if token_response.refresh_token:
        print("  - Has Refresh Token: Yes")

    return token_response


def fetch_user_profile(access_token: str) -> dict:
    """Fetch user profile from Ultrahuman API."""
    print_section("Fetch User Profile")

    url = f"{settings.ultrahuman_api_base_url}/user_data/user_info"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = httpx.get(url, headers=headers, timeout=30.0)
    response.raise_for_status()

    profile = response.json()

    print("✓ User profile fetched:")
    print(f"  - User ID: {profile.get('user_id')}")
    print(f"  - Username: {profile.get('username')}")
    print(f"  - Email: {profile.get('email')}")
    print("\nFull profile data:")
    print(json.dumps(profile, indent=2))

    return profile


def fetch_daily_metrics(access_token: str, date: datetime) -> dict:
    """Fetch daily metrics for a specific date."""
    print_section(f"Fetch Daily Metrics for {date.strftime('%Y-%m-%d')}")

    url = f"{settings.ultrahuman_api_base_url}/user_data/metrics"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"date": date.strftime("%Y-%m-%d")}

    response = httpx.get(url, headers=headers, params=params, timeout=30.0)
    response.raise_for_status()

    data = response.json()

    print("✓ Daily metrics fetched:")
    if "data" in data and "metric_data" in data["data"]:
        metric_types = [m.get("type") for m in data["data"]["metric_data"]]
        print(f"  - Available metric types: {', '.join(metric_types)}")
        print("\nFull response (first 500 chars):")
        print(json.dumps(data, indent=2)[:500] + "...")
    else:
        print("  - No data available for this date")

    return data


def create_test_user(email: str = "ultrahuman-test@example.com") -> User:
    """Create a test user in the database."""
    print_section("Create Test User")

    with SessionLocal() as db:
        user_repo = UserRepository()

        existing_user = user_repo.get_by_email(db, email)
        if existing_user:
            print(f"✓ Using existing test user: {existing_user.email}")
            return existing_user

        from app.schemas import UserCreate

        user_create = UserCreate(
            email=email,
            first_name="Test",
            last_name="User",
        )

        user = user_repo.create(db, user_create)
        db.commit()
        db.refresh(user)

        print(f"✓ Created test user: {user.email}")
        print(f"  - User ID: {user.id}")

        return user


def save_test_connection(user: User, token_response: OAuthTokenResponse) -> UserConnection:
    """Save test connection to database."""
    print_section("Save Test Connection")

    with SessionLocal() as db:
        connection_repo = UserConnectionRepository()

        existing = connection_repo.get_user_connection_by_provider(db, user.id, "ultrahuman")
        if existing:
            print("✓ Updating existing connection...")
            existing.access_token = token_response.access_token
            existing.refresh_token = token_response.refresh_token
            existing.expires_at = (
                datetime.now(timezone.utc).replace(microsecond=0) + token_response.expires_in
                if token_response.expires_in
                else None
            )
            db.commit()
            db.refresh(existing)
            return existing

        connection = UserConnection(
            user_id=user.id,
            provider="ultrahuman",
            provider_user_id="test_user",
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            expires_at=datetime.now(timezone.utc).replace(microsecond=0) + token_response.expires_in
            if token_response.expires_in
            else None,
            token_type="Bearer",
        )

        db.add(connection)
        db.commit()
        db.refresh(connection)

        print("✓ Saved connection:")
        print(f"  - Connection ID: {connection.id}")
        print(f"  - Provider: {connection.provider}")

        return connection


def test_full_sync(user: User) -> dict:
    """Test full data sync using the strategy."""
    print_section("Test Full Data Sync")

    strategy = UltrahumanStrategy()
    data_247 = strategy.data_247

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=3)

    print(f"Syncing data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")

    with SessionLocal() as db:
        try:
            results = data_247.load_and_save_all(
                db=db,
                user_id=user.id,
                start_time=start_time,
                end_time=end_time,
            )

            print("✓ Sync completed!")
            print(f"  - Sleep sessions synced: {results['sleep_sessions_synced']}")
            print(f"  - Activity samples saved: {results['activity_samples']}")
            print(f"  - Recovery days synced: {results['recovery_days_synced']}")
            print(f"  - Failed days: {results['failed_days']}")

            if results["errors"]:
                print("\nErrors encountered:")
                for error in results["errors"]:
                    print(f"  - {error['date']}: {error['error']}")

            return results

        except Exception as e:
            print(f"✗ Sync failed: {e}")
            import traceback

            traceback.print_exc()
            return {}


def query_saved_data(user: User) -> None:
    """Query and display saved data from database."""
    print_section("Query Saved Data")

    with SessionLocal() as db:
        sleep_records = (
            db.query(EventRecord)
            .filter(
                EventRecord.user_id == user.id,
                EventRecord.category == "sleep",
                EventRecord.provider_name == "ultrahuman",
            )
            .order_by(EventRecord.start_datetime.desc())
            .limit(5)
            .all()
        )

        print(f"Sleep records found: {len(sleep_records)}")
        for record in sleep_records:
            print(f"\n  - Date: {record.start_datetime.strftime('%Y-%m-%d')}")
            print(f"    Duration: {record.duration_seconds // 3600}h {(record.duration_seconds % 3600) // 60}m")
            print(f"    External ID: {record.external_id}")

        hr_samples = (
            db.query(DataPointSeries)
            .filter(
                DataPointSeries.user_id == user.id,
                DataPointSeries.provider_name == "ultrahuman",
                DataPointSeries.series_type == "heart_rate",
            )
            .order_by(DataPointSeries.recorded_at.desc())
            .limit(5)
            .all()
        )

        print(f"\nHeart rate samples found: {len(hr_samples)}")
        for sample in hr_samples:
            print(f"\n  - Time: {sample.recorded_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Value: {sample.value} bpm")


def interactive_mode() -> None:
    """Run interactive OAuth flow and data sync."""
    print_section("Ultrahuman Real Data Testing")

    if not check_credentials():
        sys.exit(1)

    get_authorization_url()

    print("\nAfter authorization, you'll be redirected to your redirect URI.")
    print("The URL will contain an 'code' parameter.")
    print("\nPaste the authorization code here (or press Enter to skip):")

    authorization_code = input("> ").strip()

    if not authorization_code:
        print("\n⚠ Skipping OAuth flow. You can provide an existing token instead.")
        print("\nPaste your access token here (or press Enter to exit):")
        access_token = input("> ").strip()

        if not access_token:
            print("\nNo token provided. Exiting.")
            return

        fetch_user_profile(access_token)

        from app.schemas import OAuthTokenResponse

        token_response = OAuthTokenResponse(
            access_token=access_token,
            refresh_token="",
            expires_in=3600,
            token_type="Bearer",
        )
    else:
        token_response = exchange_token(authorization_code)
        fetch_user_profile(token_response.access_token)

    print("\nWould you like to fetch daily metrics? (y/n):")
    choice = input("> ").strip().lower()

    if choice == "y":
        date_str = input("\nEnter date to fetch (YYYY-MM-DD, or press Enter for yesterday): ").strip()
        if date_str:
            try:
                test_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                print("Invalid date format. Using yesterday.")
                test_date = datetime.now(timezone.utc) - timedelta(days=1)
        else:
            test_date = datetime.now(timezone.utc) - timedelta(days=1)

        fetch_daily_metrics(token_response.access_token, test_date)

    print("\nWould you like to save to database and test full sync? (y/n):")
    choice = input("> ").strip().lower()

    if choice == "y":
        user = create_test_user()
        save_test_connection(user, token_response)
        test_full_sync(user)
        query_saved_data(user)

    print_section("Testing Complete")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Ultrahuman integration with real data")
    parser.add_argument(
        "--mode",
        choices=["interactive", "check-creds", "fetch-only"],
        default="interactive",
        help="Test mode: interactive, check-creds (check credentials only), "
        "fetch-only (fetch data using existing token)",
    )
    parser.add_argument(
        "--token",
        help="Existing access token for fetch-only mode",
    )
    parser.add_argument(
        "--date",
        help="Date to fetch metrics (YYYY-MM-DD), defaults to yesterday",
    )

    args = parser.parse_args()

    if args.mode == "check-creds":
        if not check_credentials():
            sys.exit(1)
        print("\n✓ All checks passed!")

    elif args.mode == "fetch-only":
        if not check_credentials():
            sys.exit(1)

        if not args.token:
            print("Error: --token is required for fetch-only mode")
            sys.exit(1)

        if args.date:
            try:
                test_date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
                sys.exit(1)
        else:
            test_date = datetime.now(timezone.utc) - timedelta(days=1)

        fetch_user_profile(args.token)
        fetch_daily_metrics(args.token, test_date)

    else:
        interactive_mode()


if __name__ == "__main__":
    main()
