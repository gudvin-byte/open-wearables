"""Tests for Ultrahuman strategy."""

from app.services.providers.ultrahuman.data_247 import Ultrahuman247Data
from app.services.providers.ultrahuman.oauth import UltrahumanOAuth
from app.services.providers.ultrahuman.strategy import UltrahumanStrategy


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

    def test_display_name(self) -> None:
        """Display name should be capitalized provider name."""
        strategy = UltrahumanStrategy()
        assert strategy.display_name == "Ultrahuman"

    def test_has_cloud_api(self) -> None:
        """Ultrahuman should have cloud API support."""
        strategy = UltrahumanStrategy()
        assert strategy.has_cloud_api is True

    def test_icon_url(self) -> None:
        """Icon URL should point to Ultrahuman SVG icon."""
        strategy = UltrahumanStrategy()
        assert strategy.icon_url == "/static/provider-icons/ultrahuman.svg"

    def test_oauth_component_initialized(self) -> None:
        """OAuth component should be initialized."""
        strategy = UltrahumanStrategy()
        assert strategy.oauth is not None
        assert isinstance(strategy.oauth, UltrahumanOAuth)

    def test_data_247_component_initialized(self) -> None:
        """Data_247 component should be initialized."""
        strategy = UltrahumanStrategy()
        assert strategy.data_247 is not None
        assert isinstance(strategy.data_247, Ultrahuman247Data)

    def test_oauth_has_correct_provider_name(self) -> None:
        """OAuth component should have correct provider name."""
        strategy = UltrahumanStrategy()
        assert strategy.oauth is not None
        assert strategy.oauth.provider_name == "ultrahuman"

    def test_oauth_has_correct_api_base_url(self) -> None:
        """OAuth component should have correct API base URL."""
        strategy = UltrahumanStrategy()
        assert strategy.oauth is not None
        assert strategy.oauth.api_base_url == "https://partner.ultrahuman.com/api/partners/v1"

    def test_data_247_has_correct_provider_name(self) -> None:
        """Data_247 component should have correct provider name."""
        strategy = UltrahumanStrategy()
        assert strategy.data_247 is not None
        assert strategy.data_247.provider_name == "ultrahuman"

    def test_data_247_has_correct_api_base_url(self) -> None:
        """Data_247 component should have correct API base URL."""
        strategy = UltrahumanStrategy()
        assert strategy.data_247 is not None
        assert strategy.data_247.api_base_url == "https://partner.ultrahuman.com/api/partners/v1"

    def test_repositories_initialized(self) -> None:
        """All required repositories should be initialized."""
        strategy = UltrahumanStrategy()
        assert strategy.user_repo is not None
        assert strategy.connection_repo is not None
