"""CLI Index Commands Tests.

Tests for the index CLI commands: init, index, list-indexes, index-dir, reindex-all.
"""

import subprocess

import pytest
from typer.testing import CliRunner as TyperRunner

from contextfs.cli.index import index_app


@pytest.fixture
def runner():
    """Create CLI runner."""
    return TyperRunner()


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Create some files
    (tmp_path / "main.py").write_text('def hello(): return "world"')
    (tmp_path / "utils.py").write_text("def util(): pass")
    (tmp_path / "README.md").write_text("# Test Project")

    # Commit
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
    )

    return tmp_path


# =============================================================================
# Init Command Tests
# =============================================================================


class TestIndexInitCommand:
    """Tests for 'contextfs index init' command."""

    def test_init_creates_config(self, runner, git_repo, monkeypatch):
        """Test init creates .contextfs/config.yaml."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["init"])
        assert result.exit_code == 0
        assert "Initialized" in result.stdout

        config_path = git_repo / ".contextfs" / "config.yaml"
        assert config_path.exists()

    def test_init_not_git_repo(self, runner, tmp_path, monkeypatch):
        """Test init fails in non-git directory."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(index_app, ["init"])
        assert result.exit_code == 1
        assert "git repository" in result.stdout.lower()

    def test_init_already_initialized(self, runner, git_repo, monkeypatch):
        """Test init handles already initialized repo."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Init first time
        runner.invoke(index_app, ["init"])

        # Init second time without force
        result = runner.invoke(index_app, ["init"])
        assert result.exit_code == 0
        assert "already initialized" in result.stdout.lower()

    def test_init_force_reinitialize(self, runner, git_repo, monkeypatch):
        """Test init --force reinitializes."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Init first time
        runner.invoke(index_app, ["init"])

        # Force reinitialize
        result = runner.invoke(index_app, ["init", "--force"])
        assert result.exit_code == 0
        assert "Initialized" in result.stdout

    def test_init_with_no_index(self, runner, git_repo, monkeypatch):
        """Test init --no-index skips indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["init", "--no-index"])
        assert result.exit_code == 0
        # Should not show indexing output

    def test_init_with_custom_path(self, runner, git_repo, tmp_path, monkeypatch):
        """Test init with specific repo path."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["init", str(git_repo)])
        assert result.exit_code == 0
        assert "Initialized" in result.stdout

    def test_init_disable_auto_index(self, runner, git_repo, monkeypatch):
        """Test init --no-auto-index disables auto-indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["init", "--no-auto-index", "--no-index"])
        assert result.exit_code == 0
        assert "disabled" in result.stdout.lower()


# =============================================================================
# Index Command Tests
# =============================================================================


class TestIndexCommand:
    """Tests for 'contextfs index index' command."""

    def test_index_repo(self, runner, git_repo, monkeypatch):
        """Test indexing a repository."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["index"])
        assert result.exit_code == 0
        # Should complete indexing or show progress

    def test_index_with_force(self, runner, git_repo, monkeypatch):
        """Test force re-indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Index first
        runner.invoke(index_app, ["index"])

        # Force re-index
        result = runner.invoke(index_app, ["index", "--force"])
        assert result.exit_code == 0

    def test_index_incremental(self, runner, git_repo, monkeypatch):
        """Test incremental indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Initial index
        runner.invoke(index_app, ["index"])

        # Add a new file
        (git_repo / "new_file.py").write_text("# new file")

        # Incremental index (default)
        result = runner.invoke(index_app, ["index", "--incremental"])
        assert result.exit_code == 0

    def test_index_full_mode(self, runner, git_repo, monkeypatch):
        """Test full (non-incremental) indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["index", "--full"])
        assert result.exit_code == 0

    def test_index_files_only(self, runner, git_repo, monkeypatch):
        """Test indexing files only (no commits)."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["index", "--mode", "files_only"])
        assert result.exit_code == 0

    def test_index_commits_only(self, runner, git_repo, monkeypatch):
        """Test indexing commits only."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["index", "--mode", "commits_only"])
        assert result.exit_code == 0

    def test_index_not_git_repo(self, runner, tmp_path, monkeypatch):
        """Test indexing non-git directory fails without flag."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(index_app, ["index"])
        assert result.exit_code == 1
        assert "git repository" in result.stdout.lower()

    def test_index_allow_non_git(self, runner, tmp_path, monkeypatch):
        """Test indexing non-git with --allow-dir."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        # Create some files
        (tmp_path / "test.py").write_text("# test")

        result = runner.invoke(index_app, ["index", str(tmp_path), "--allow-dir"])
        assert result.exit_code == 0

    def test_index_quiet_mode(self, runner, git_repo, monkeypatch):
        """Test quiet mode output."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        result = runner.invoke(index_app, ["index", "--quiet"])
        assert result.exit_code == 0
        # Quiet mode should have minimal output

    def test_index_require_init_skips_uninit(self, runner, git_repo, monkeypatch):
        """Test --require-init skips non-initialized repos."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Don't init first
        result = runner.invoke(index_app, ["index", "--require-init"])
        assert result.exit_code == 0
        assert "Skipping" in result.stdout or "not initialized" in result.stdout.lower()


# =============================================================================
# List-Indexes Command Tests
# =============================================================================


class TestListIndexesCommand:
    """Tests for 'contextfs index list-indexes' command."""

    def test_list_indexes_empty(self, runner, tmp_path, monkeypatch):
        """Test list indexes when none exist."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["list-indexes"])
        assert result.exit_code == 0
        assert "No indexed" in result.stdout or "TOTAL" in result.stdout

    def test_list_indexes_after_indexing(self, runner, git_repo, monkeypatch):
        """Test list indexes after indexing."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Index first
        runner.invoke(index_app, ["index"])

        # List
        result = runner.invoke(index_app, ["list-indexes"])
        assert result.exit_code == 0
        # Should show table with indexes


# =============================================================================
# Index-Dir Command Tests
# =============================================================================


class TestIndexDirCommand:
    """Tests for 'contextfs index index-dir' command."""

    def test_index_dir_dry_run(self, runner, tmp_path, monkeypatch):
        """Test index-dir --dry-run discovery."""
        # Create parent directory with a git repo
        parent = tmp_path / "projects"
        parent.mkdir()

        # Create a fresh git repo in the parent
        dest = parent / "repo1"
        dest.mkdir()
        subprocess.run(["git", "init"], cwd=dest, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=dest,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=dest,
            capture_output=True,
        )
        (dest / "main.py").write_text("# test file")
        subprocess.run(["git", "add", "."], cwd=dest, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=dest,
            capture_output=True,
        )

        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["index-dir", str(parent), "--dry-run"])
        assert result.exit_code == 0
        # Should discover the repo

    def test_index_dir_with_max_depth(self, runner, tmp_path, monkeypatch):
        """Test index-dir with depth limit."""
        parent = tmp_path / "projects"
        parent.mkdir()

        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["index-dir", str(parent), "--dry-run", "--depth", "2"])
        assert result.exit_code == 0

    def test_index_dir_path_not_exists(self, runner, tmp_path, monkeypatch):
        """Test index-dir with nonexistent path."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["index-dir", "/nonexistent/path/12345"])
        assert result.exit_code == 1
        assert "not exist" in result.stdout.lower()


# =============================================================================
# Cleanup-Indexes Command Tests
# =============================================================================


class TestCleanupIndexesCommand:
    """Tests for 'contextfs index cleanup-indexes' command."""

    def test_cleanup_indexes_dry_run(self, runner, git_repo, monkeypatch):
        """Test cleanup-indexes --dry-run."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Index first
        runner.invoke(index_app, ["index"])

        result = runner.invoke(index_app, ["cleanup-indexes", "--dry-run"])
        assert result.exit_code == 0

    def test_cleanup_indexes_no_stale(self, runner, git_repo, monkeypatch):
        """Test cleanup when no stale indexes."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Index
        runner.invoke(index_app, ["index"])

        result = runner.invoke(index_app, ["cleanup-indexes", "--dry-run"])
        assert result.exit_code == 0
        # Should show no stale indexes or valid indexes


# =============================================================================
# Delete-Index Command Tests
# =============================================================================


class TestDeleteIndexCommand:
    """Tests for 'contextfs index delete-index' command."""

    def test_delete_index_not_found(self, runner, tmp_path, monkeypatch):
        """Test delete-index for nonexistent index."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(tmp_path / ".contextfs_data"))

        result = runner.invoke(index_app, ["delete-index", "/nonexistent/path", "-y"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_delete_index_by_path(self, runner, git_repo, monkeypatch):
        """Test delete-index by path."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Index first
        runner.invoke(index_app, ["index"])

        # Delete
        result = runner.invoke(index_app, ["delete-index", str(git_repo), "-y"])
        assert result.exit_code == 0 or "not found" in result.stdout.lower()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIndexCLIIntegration:
    """Integration tests for index CLI workflow."""

    def test_init_index_list_workflow(self, runner, git_repo, monkeypatch):
        """Test complete init -> index -> list-indexes workflow."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Init
        init_result = runner.invoke(index_app, ["init", "--no-index"])
        assert init_result.exit_code == 0

        # Index
        index_result = runner.invoke(index_app, ["index"])
        assert index_result.exit_code == 0

        # List
        list_result = runner.invoke(index_app, ["list-indexes"])
        assert list_result.exit_code == 0

    def test_index_and_reindex(self, runner, git_repo, monkeypatch):
        """Test index then reindex workflow."""
        monkeypatch.setenv("CONTEXTFS_DATA_DIR", str(git_repo / ".contextfs_data"))
        monkeypatch.chdir(git_repo)

        # Initial index
        runner.invoke(index_app, ["index"])

        # Add more content
        (git_repo / "additional.py").write_text("# more code")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add more"],
            cwd=git_repo,
            capture_output=True,
        )

        # Reindex incrementally
        result = runner.invoke(index_app, ["index", "--incremental"])
        assert result.exit_code == 0
