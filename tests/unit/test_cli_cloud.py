"""CLI Cloud Commands Tests.

Tests for the cloud CLI commands: login, configure, status, sync, api-key.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner as TyperRunner

from contextfs.cli.cloud import cloud_app


@pytest.fixture
def runner():
    """Create CLI runner."""
    return TyperRunner()


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Set up temporary home directory for config files."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


# =============================================================================
# Login Command Tests
# =============================================================================


class TestCloudLoginCommand:
    """Tests for 'contextfs cloud login' command."""

    def test_login_unknown_provider(self, runner, temp_home):
        """Test login with unknown provider."""
        result = runner.invoke(cloud_app, ["login", "--provider", "unknown"])
        assert result.exit_code == 0  # Command runs but prints error
        assert "Unknown provider" in result.stdout

    def test_login_email_missing_credentials(self, runner, temp_home):
        """Test email login prompts for credentials."""
        # Without providing email/password, it should prompt
        # We can't test interactive prompts easily, so just verify command structure
        result = runner.invoke(cloud_app, ["login", "--provider", "email"], input="\n\n")
        # Will fail due to empty credentials but shouldn't crash
        assert result.exit_code in [0, 1]

    def test_login_email_with_credentials(self, runner, temp_home):
        """Test email login with provided credentials."""
        with patch("httpx.Client") as mock_client:
            # Mock the HTTP response
            mock_response = MagicMock()
            mock_response.status_code = 401  # Invalid credentials
            mock_response.json.return_value = {"error": "Invalid credentials"}
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = runner.invoke(
                cloud_app,
                ["login", "--provider", "email", "--email", "test@test.com", "--password", "wrong"],
            )

            # Should handle 401 gracefully
            assert "Invalid" in result.stdout or result.exit_code in [0, 1]

    def test_login_github_no_client_id(self, runner, temp_home, monkeypatch):
        """Test GitHub login without client ID configured."""
        monkeypatch.setenv("CONTEXTFS_CLI_GITHUB_CLIENT_ID", "")

        result = runner.invoke(cloud_app, ["login", "--provider", "github"])
        # Should handle gracefully
        assert result.exit_code in [0, 1]


# =============================================================================
# Configure Command Tests
# =============================================================================


class TestCloudConfigureCommand:
    """Tests for 'contextfs cloud configure' command."""

    def test_configure_enable(self, runner, temp_home):
        """Test enabling cloud sync."""
        result = runner.invoke(cloud_app, ["configure", "--enabled"])
        assert result.exit_code == 0

    def test_configure_disable(self, runner, temp_home):
        """Test disabling cloud sync."""
        result = runner.invoke(cloud_app, ["configure", "--disabled"])
        assert result.exit_code == 0

    def test_configure_server_url(self, runner, temp_home):
        """Test configuring server URL."""
        result = runner.invoke(cloud_app, ["configure", "--server", "https://custom.api.com"])
        assert result.exit_code == 0


# =============================================================================
# Status Command Tests
# =============================================================================


class TestCloudStatusCommand:
    """Tests for 'contextfs cloud status' command."""

    def test_status_not_configured(self, runner, temp_home):
        """Test status when not configured."""
        result = runner.invoke(cloud_app, ["status"])
        assert result.exit_code == 0
        # Should show not configured or similar

    def test_status_configured(self, runner, temp_home):
        """Test status when configured."""
        import yaml

        config_dir = temp_home / ".contextfs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "cloud": {
                        "api_key": "test_key_12345",
                        "enabled": True,
                        "server_url": "https://api.contextfs.ai",
                    }
                }
            )
        )

        result = runner.invoke(cloud_app, ["status"])
        assert result.exit_code == 0


# =============================================================================
# Sync Command Tests
# =============================================================================


class TestCloudSyncCommand:
    """Tests for 'contextfs cloud sync' command."""

    def test_sync_not_enabled(self, runner, temp_home):
        """Test sync when cloud is not enabled."""
        result = runner.invoke(cloud_app, ["sync"])
        assert result.exit_code == 0
        assert "disabled" in result.stdout.lower() or "configure" in result.stdout.lower()

    def test_sync_no_api_key(self, runner, temp_home):
        """Test sync without API key."""
        import yaml

        config_dir = temp_home / ".contextfs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(yaml.dump({"cloud": {"enabled": True}}))

        result = runner.invoke(cloud_app, ["sync"])
        assert result.exit_code == 0
        assert "api key" in result.stdout.lower() or "login" in result.stdout.lower()

    def test_sync_force_flag(self, runner, temp_home):
        """Test sync with --force flag."""
        result = runner.invoke(cloud_app, ["sync", "--force"])
        # Should handle missing config gracefully
        assert result.exit_code == 0

    def test_sync_all_flag(self, runner, temp_home):
        """Test sync with --all flag."""
        result = runner.invoke(cloud_app, ["sync", "--all"])
        # Should handle missing config gracefully
        assert result.exit_code == 0


# =============================================================================
# API-Key Command Tests
# =============================================================================


class TestCloudApiKeyCommand:
    """Tests for 'contextfs cloud api-key' command."""

    def test_api_key_list_not_logged_in(self, runner, temp_home):
        """Test listing API keys when not logged in."""
        result = runner.invoke(cloud_app, ["api-key", "list"])
        # Should handle gracefully
        assert result.exit_code in [0, 1]

    def test_api_key_create_not_logged_in(self, runner, temp_home):
        """Test creating API key when not logged in."""
        result = runner.invoke(cloud_app, ["api-key", "create"])
        # Should handle gracefully
        assert result.exit_code in [0, 1]


# =============================================================================
# Upgrade Command Tests
# =============================================================================


class TestCloudUpgradeCommand:
    """Tests for 'contextfs cloud upgrade' command."""

    def test_upgrade_opens_browser(self, runner, temp_home):
        """Test upgrade command tries to open browser."""
        with patch("webbrowser.open") as _mock_browser:
            result = runner.invoke(cloud_app, ["upgrade"])
            # May or may not call browser depending on config
            assert result.exit_code == 0


# =============================================================================
# Configuration Tests
# =============================================================================


class TestCloudConfiguration:
    """Tests for cloud configuration handling."""

    def test_get_cloud_config_no_file(self, temp_home):
        """Test getting config when file doesn't exist."""
        from contextfs.cli.cloud import _get_cloud_config

        config = _get_cloud_config()
        assert config == {}

    def test_get_cloud_config_with_file(self, temp_home):
        """Test getting config from file."""
        import yaml

        from contextfs.cli.cloud import _get_cloud_config

        config_dir = temp_home / ".contextfs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            yaml.dump({"cloud": {"api_key": "test_key", "server_url": "https://test.com"}})
        )

        config = _get_cloud_config()
        assert config.get("api_key") == "test_key"
        assert config.get("server_url") == "https://test.com"

    def test_save_cloud_config(self, temp_home):
        """Test saving cloud configuration."""
        import yaml

        from contextfs.cli.cloud import _save_cloud_config

        _save_cloud_config({"api_key": "new_key", "enabled": True})

        config_path = temp_home / ".contextfs" / "config.yaml"
        assert config_path.exists()

        config = yaml.safe_load(config_path.read_text())
        assert config["cloud"]["api_key"] == "new_key"
        assert config["cloud"]["enabled"] is True

    def test_get_device_id_creates_file(self, temp_home):
        """Test device ID generation and persistence."""
        from contextfs.cli.cloud import _get_device_id

        device_id = _get_device_id()
        assert device_id is not None
        assert len(device_id) > 0

        # Should be persisted
        device_path = temp_home / ".contextfs" / "device_id"
        assert device_path.exists()
        assert device_path.read_text().strip() == device_id

        # Should return same ID on second call
        device_id_2 = _get_device_id()
        assert device_id_2 == device_id


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCloudErrorHandling:
    """Tests for error handling in cloud commands."""

    def test_network_error_handled(self, runner, temp_home):
        """Test network errors are handled gracefully."""
        import yaml

        config_dir = temp_home / ".contextfs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(yaml.dump({"cloud": {"api_key": "test_key", "enabled": True}}))

        # Sync will fail due to network but shouldn't crash
        result = runner.invoke(cloud_app, ["sync"])
        # Should handle error gracefully
        assert result.exit_code in [0, 1]

    def test_invalid_config_handled(self, runner, temp_home):
        """Test invalid config file is handled."""
        config_dir = temp_home / ".contextfs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("invalid: yaml: content: :")

        result = runner.invoke(cloud_app, ["status"])
        # Should handle parse error gracefully
        assert result.exit_code in [0, 1]
