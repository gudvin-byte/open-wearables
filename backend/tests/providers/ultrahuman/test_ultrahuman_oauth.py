"""Tests for Ultrahuman OAuth implementation."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

from app.repositories.user_connection_repository import UserConnectionRepository
from app.repositories.user_repository import UserRepository
from app.schemas import AuthenticationMethod, OAuthTokenResponse, ProviderCredentials, ProviderEndpoints
from app.services.providers.ultrahuman.oauth import UltrahumanOAuth
from tests.factories import UserConnectionFactory, UserFactory


class TestUltrahumanOAuth:
    """Tests for UltrahumanOAuth class."""

    @pytest.fixture
    def ultrahuman_oauth(self, db: Session) -> UltrahumanOAuth:
        """Create UltrahumanOAuth instance for testing."""
        user_repo = UserRepository(UserFactory._meta.model)
        connection_repo = UserConnectionRepository()
        return UltrahumanOAuth(
            user_repo=user_repo,
            connection_repo=connection_repo,
            provider_name="ultrahuman",
            api_base_url="https://partner.ultrahuman.com/api/partners/v1",
        )

    def test_endpoints_configuration(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Test OAuth endpoints are correctly configured."""
        endpoints = ultrahuman_oauth.endpoints
        assert isinstance(endpoints, ProviderEndpoints)
        assert endpoints.authorize_url == "https://auth.ultrahuman.com/authorise"
        assert endpoints.token_url == "https://partner.ultrahuman.com/api/partners/oauth/token"

    def test_credentials_configuration(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Test OAuth credentials are correctly configured."""
        credentials = ultrahuman_oauth.credentials
        assert isinstance(credentials, ProviderCredentials)
        assert credentials.client_id is not None
        assert credentials.client_secret is not None
        assert credentials.redirect_uri is not None
        assert credentials.default_scope is not None

    def test_uses_pkce(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Ultrahuman should NOT use PKCE for OAuth flow."""
        assert ultrahuman_oauth.use_pkce is False

    def test_auth_method_is_body(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Ultrahuman should use body authentication method."""
        assert ultrahuman_oauth.auth_method == AuthenticationMethod.BODY

    @patch("app.integrations.redis_client.get_redis_client")
    def test_get_authorization_url(self, mock_redis: MagicMock, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Test generating authorization URL without PKCE."""
        # Arrange
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client
        ultrahuman_oauth.redis_client = mock_redis_client

        from uuid import uuid4

        user_id = uuid4()

        # Act
        auth_url, state = ultrahuman_oauth.get_authorization_url(user_id)

        # Assert
        assert "https://auth.ultrahuman.com/authorise" in auth_url
        assert "client_id=" in auth_url
        assert f"state={state}" in auth_url
        assert len(state) > 0
        mock_redis_client.setex.assert_called_once()

    @patch("httpx.get")
    def test_get_provider_user_info_success(
        self,
        mock_httpx_get: MagicMock,
        ultrahuman_oauth: UltrahumanOAuth,
        mock_ultrahuman_user_info: dict,
    ) -> None:
        """Test fetching Ultrahuman user info successfully."""
        # Arrange
        token_response = OAuthTokenResponse(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = mock_ultrahuman_user_info
        mock_response.raise_for_status.return_value = None
        mock_httpx_get.return_value = mock_response

        # Act
        user_info = ultrahuman_oauth._get_provider_user_info(token_response, "internal_user_id")

        # Assert
        assert user_info["user_id"] == "ultrahuman_user_12345"
        assert user_info["username"] == "test_user"
        mock_httpx_get.assert_called_once_with(
            "https://partner.ultrahuman.com/api/partners/v1/user_data/user_info",
            headers={"Authorization": "Bearer test_access_token"},
            timeout=30.0,
        )

    @patch("httpx.get")
    def test_get_provider_user_info_http_error(
        self,
        mock_httpx_get: MagicMock,
        ultrahuman_oauth: UltrahumanOAuth,
    ) -> None:
        """Test fetching Ultrahuman user info handles HTTP errors gracefully."""
        # Arrange
        token_response = OAuthTokenResponse(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
        )

        mock_httpx_get.side_effect = httpx.HTTPError("API Error")

        # Act
        user_info = ultrahuman_oauth._get_provider_user_info(token_response, "internal_user_id")

        # Assert - should return None values on error
        assert user_info["user_id"] is None
        assert user_info["username"] is None

    @patch("httpx.get")
    def test_get_provider_user_info_no_username_fallback_to_email(
        self,
        mock_httpx_get: MagicMock,
        ultrahuman_oauth: UltrahumanOAuth,
    ) -> None:
        """Test fetching Ultrahuman user info falls back to email when username is missing."""
        # Arrange
        token_response = OAuthTokenResponse(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "user_id": "user_123",
            "email": "user@example.com",
        }
        mock_response.raise_for_status.return_value = None
        mock_httpx_get.return_value = mock_response

        # Act
        user_info = ultrahuman_oauth._get_provider_user_info(token_response, "internal_user_id")

        # Assert
        assert user_info["user_id"] == "user_123"
        assert user_info["username"] == "user@example.com"

    @patch("httpx.post")
    @patch("app.integrations.redis_client.get_redis_client")
    def test_exchange_token_without_pkce(
        self,
        mock_redis: MagicMock,
        mock_httpx_post: MagicMock,
        ultrahuman_oauth: UltrahumanOAuth,
    ) -> None:
        """Test token exchange does NOT include PKCE verifier."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status.return_value = None
        mock_httpx_post.return_value = mock_response

        code = "auth_code_123"
        code_verifier = "test_verifier_abc123"

        # Act
        token_response = ultrahuman_oauth._exchange_token(code, code_verifier)

        # Assert
        assert token_response.access_token == "new_access_token"
        assert token_response.refresh_token == "new_refresh_token"

        # Verify PKCE verifier was NOT included in request (Ultrahuman doesn't use PKCE)
        call_args = mock_httpx_post.call_args
        assert "code_verifier" not in call_args[1]["data"]

    @patch("httpx.post")
    def test_refresh_access_token(
        self,
        mock_httpx_post: MagicMock,
        ultrahuman_oauth: UltrahumanOAuth,
        db: Session,
    ) -> None:
        """Test refreshing access token."""
        # Arrange
        user = UserFactory()
        UserConnectionFactory(
            user=user,
            provider="ultrahuman",
            access_token="old_access_token",
            refresh_token="old_refresh_token",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status.return_value = None
        mock_httpx_post.return_value = mock_response

        # Act
        token_response = ultrahuman_oauth.refresh_access_token(db, user.id, "old_refresh_token")

        # Assert
        assert token_response.access_token == "new_access_token"
        assert token_response.refresh_token == "new_refresh_token"

    def test_prepare_token_request_uses_body_auth(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Test token request preparation uses body authentication."""
        # Act
        data, headers = ultrahuman_oauth._prepare_token_request("auth_code", "verifier")

        # Assert
        assert "client_id" in data
        assert "client_secret" in data
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == "auth_code"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert "Authorization" not in headers  # Body auth, not Basic auth

    def test_prepare_refresh_request_uses_body_auth(self, ultrahuman_oauth: UltrahumanOAuth) -> None:
        """Test refresh token request preparation uses body authentication."""
        # Act
        data, headers = ultrahuman_oauth._prepare_refresh_request("test_refresh_token")

        # Assert
        assert "client_id" in data
        assert "client_secret" in data
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "test_refresh_token"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert "Authorization" not in headers  # Body auth, not Basic auth
