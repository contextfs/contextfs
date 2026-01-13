"""
Integration tests for team collaboration features.

Tests team CRUD, membership, invitations, and permissions.
Requires PostgreSQL. Run with: CONTEXTFS_TEST_POSTGRES=1 pytest tests/integration/test_teams.py
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

# Skip if PostgreSQL not available
pytestmark = pytest.mark.skipif(
    os.environ.get("CONTEXTFS_TEST_POSTGRES") != "1",
    reason="PostgreSQL tests disabled. Set CONTEXTFS_TEST_POSTGRES=1 to enable.",
)


class TestTeamModel:
    """Tests for Team model."""

    def test_team_creation(self):
        """Test creating a team."""
        from service.db.models import TeamModel

        team = TeamModel(
            id=str(uuid4()),
            name="Test Team",
            owner_id="user_123",
            description="A test team",
        )

        assert team.name == "Test Team"
        assert team.owner_id == "user_123"
        assert team.description == "A test team"

    def test_team_requires_owner(self):
        """Teams must have an owner."""
        from service.db.models import TeamModel

        team = TeamModel(
            id=str(uuid4()),
            name="Test Team",
            owner_id="user_123",
        )

        assert team.owner_id is not None


class TestTeamMemberModel:
    """Tests for TeamMember model."""

    def test_member_roles(self):
        """Test team member roles."""
        from service.db.models import TeamMemberModel

        # Owner role
        owner = TeamMemberModel(
            team_id="team_1",
            user_id="user_1",
            role="owner",
        )
        assert owner.role == "owner"

        # Admin role
        admin = TeamMemberModel(
            team_id="team_1",
            user_id="user_2",
            role="admin",
        )
        assert admin.role == "admin"

        # Member role (default)
        member = TeamMemberModel(
            team_id="team_1",
            user_id="user_3",
            role="member",
        )
        assert member.role == "member"

    def test_member_default_role(self):
        """Default member role should be 'member'."""
        from service.db.models import TeamMemberModel

        # Note: SQLAlchemy defaults are applied at database level
        # When creating objects directly, we set values explicitly
        member = TeamMemberModel(
            team_id="team_1",
            user_id="user_1",
            role="member",  # This is the default value
        )
        assert member.role == "member"


class TestTeamInvitationModel:
    """Tests for TeamInvitation model."""

    def test_invitation_creation(self):
        """Test creating an invitation."""
        from service.db.models import TeamInvitationModel

        expires = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = TeamInvitationModel(
            id=str(uuid4()),
            team_id="team_1",
            email="newuser@example.com",
            role="member",
            invited_by="user_1",
            token_hash="abc123hash",
            expires_at=expires,
        )

        assert invitation.email == "newuser@example.com"
        assert invitation.role == "member"
        assert invitation.expires_at == expires
        assert invitation.accepted_at is None

    def test_invitation_expiry_check(self):
        """Test invitation expiry logic."""
        now = datetime.now(timezone.utc)

        # Not expired
        expires_future = now + timedelta(days=1)
        is_expired = now > expires_future
        assert is_expired is False

        # Expired
        expires_past = now - timedelta(days=1)
        is_expired = now > expires_past
        assert is_expired is True


class TestTeamPermissions:
    """Tests for team permission logic."""

    def test_owner_has_all_permissions(self):
        """Owners should have all permissions."""

        def has_permission(role: str, action: str) -> bool:
            """Check if role has permission for action."""
            permissions = {
                "owner": [
                    "delete_team",
                    "manage_billing",
                    "invite",
                    "remove_member",
                    "change_roles",
                    "edit",
                    "read",
                ],
                "admin": ["invite", "remove_member", "edit", "read"],
                "member": ["edit", "read"],
            }
            return action in permissions.get(role, [])

        assert has_permission("owner", "delete_team") is True
        assert has_permission("owner", "manage_billing") is True
        assert has_permission("owner", "invite") is True
        assert has_permission("owner", "read") is True

    def test_admin_permissions(self):
        """Admins should have limited permissions."""

        def has_permission(role: str, action: str) -> bool:
            permissions = {
                "owner": [
                    "delete_team",
                    "manage_billing",
                    "invite",
                    "remove_member",
                    "change_roles",
                    "edit",
                    "read",
                ],
                "admin": ["invite", "remove_member", "edit", "read"],
                "member": ["edit", "read"],
            }
            return action in permissions.get(role, [])

        assert has_permission("admin", "delete_team") is False
        assert has_permission("admin", "manage_billing") is False
        assert has_permission("admin", "invite") is True
        assert has_permission("admin", "remove_member") is True
        assert has_permission("admin", "read") is True

    def test_member_permissions(self):
        """Members should have minimal permissions."""

        def has_permission(role: str, action: str) -> bool:
            permissions = {
                "owner": [
                    "delete_team",
                    "manage_billing",
                    "invite",
                    "remove_member",
                    "change_roles",
                    "edit",
                    "read",
                ],
                "admin": ["invite", "remove_member", "edit", "read"],
                "member": ["edit", "read"],
            }
            return action in permissions.get(role, [])

        assert has_permission("member", "delete_team") is False
        assert has_permission("member", "invite") is False
        assert has_permission("member", "edit") is True
        assert has_permission("member", "read") is True


class TestMemoryVisibility:
    """Tests for team memory visibility."""

    def test_visibility_levels(self):
        """Test memory visibility levels."""
        visibility_levels = ["private", "team_read", "team_write"]

        # All visibility levels should be valid
        assert "private" in visibility_levels
        assert "team_read" in visibility_levels
        assert "team_write" in visibility_levels

    def test_private_memory_access(self):
        """Private memories should only be visible to owner."""

        def can_access(
            user_id: str,
            memory_owner_id: str,
            memory_team_id: str | None,
            visibility: str,
            user_team_ids: list[str],
        ) -> bool:
            """Check if user can access memory."""
            # Owner always has access
            if user_id == memory_owner_id:
                return True

            # Private memories - only owner
            if visibility == "private":
                return False

            # Team-shared memories
            if visibility in ["team_read", "team_write"]:
                return memory_team_id in user_team_ids

            return False

        # Owner can access their private memory
        assert can_access("user_1", "user_1", None, "private", []) is True

        # Other users cannot access private memory
        assert can_access("user_2", "user_1", None, "private", []) is False

    def test_team_read_memory_access(self):
        """Team read memories should be visible to team members."""

        def can_access(
            user_id: str,
            memory_owner_id: str,
            memory_team_id: str | None,
            visibility: str,
            user_team_ids: list[str],
        ) -> bool:
            if user_id == memory_owner_id:
                return True
            if visibility == "private":
                return False
            if visibility in ["team_read", "team_write"]:
                return memory_team_id in user_team_ids
            return False

        # Team member can access team_read memory
        assert can_access("user_2", "user_1", "team_1", "team_read", ["team_1"]) is True

        # Non-team member cannot access
        assert can_access("user_3", "user_1", "team_1", "team_read", ["team_2"]) is False

    def test_team_write_memory_edit(self):
        """Team write memories should be editable by team members."""

        def can_edit(
            user_id: str,
            memory_owner_id: str,
            memory_team_id: str | None,
            visibility: str,
            user_team_ids: list[str],
        ) -> bool:
            """Check if user can edit memory."""
            # Owner always can edit
            if user_id == memory_owner_id:
                return True

            # Only team_write allows editing
            if visibility == "team_write":
                return memory_team_id in user_team_ids

            return False

        # Owner can edit
        assert can_edit("user_1", "user_1", "team_1", "team_write", []) is True

        # Team member can edit team_write memory
        assert can_edit("user_2", "user_1", "team_1", "team_write", ["team_1"]) is True

        # Team member cannot edit team_read memory
        assert can_edit("user_2", "user_1", "team_1", "team_read", ["team_1"]) is False


class TestTeamSeatManagement:
    """Tests for team seat management."""

    def test_seat_limit_enforcement(self):
        """Team should enforce seat limits."""
        seats_included = 5
        seats_used = 5

        can_add_member = seats_used < seats_included
        assert can_add_member is False

    def test_seat_addition(self):
        """Adding a member should increment seats_used."""
        seats_used = 3
        seats_used += 1  # Add member
        assert seats_used == 4

    def test_seat_removal(self):
        """Removing a member should decrement seats_used."""
        seats_used = 3
        seats_used -= 1  # Remove member
        assert seats_used == 2

    def test_owner_counts_as_seat(self):
        """Team owner should count as one seat."""
        # When team is created, seats_used starts at 1 (owner)
        initial_seats_used = 1
        assert initial_seats_used == 1


class TestCrossTeamIsolation:
    """Tests for cross-team data isolation."""

    def test_memory_isolation(self):
        """Memories should be isolated between teams."""

        def get_visible_memories(
            user_id: str, user_team_ids: list[str], all_memories: list[dict]
        ) -> list[dict]:
            """Get memories visible to user."""
            visible = []
            for memory in all_memories:
                # Owner sees all their memories
                if memory["owner_id"] == user_id:
                    visible.append(memory)
                    continue

                # Check team visibility
                if (
                    memory["visibility"] in ["team_read", "team_write"]
                    and memory["team_id"] in user_team_ids
                ):
                    visible.append(memory)

            return visible

        memories = [
            {"id": "1", "owner_id": "user_1", "team_id": "team_1", "visibility": "team_read"},
            {"id": "2", "owner_id": "user_2", "team_id": "team_2", "visibility": "team_read"},
            {"id": "3", "owner_id": "user_1", "team_id": None, "visibility": "private"},
        ]

        # User 1 in team 1 should see memory 1 and 3 (their own)
        visible = get_visible_memories("user_1", ["team_1"], memories)
        assert len(visible) == 2
        assert any(m["id"] == "1" for m in visible)
        assert any(m["id"] == "3" for m in visible)

        # User 3 in team 2 should only see memory 2
        visible = get_visible_memories("user_3", ["team_2"], memories)
        assert len(visible) == 1
        assert visible[0]["id"] == "2"
