# ContextFS Migrations & Tests Plan

## Executive Summary

This plan covers database migrations and test coverage for both:
- **Backend (contextfs)**: Python sync service with PostgreSQL
- **Frontend (contextfs-web)**: Next.js dashboard with React

**CRITICAL**: Existing users have OLD tier limits stored in database. Migrations must UPDATE existing records, not just add new columns.

---

## Part 1: Database Migrations

### CRITICAL: Database Architecture

| Component | Database | Purpose |
|-----------|----------|---------|
| **Local CLI** (`src/contextfs/`) | SQLite | Local memory storage, caching |
| **Cloud Service** (`service/`) | PostgreSQL | Source of truth for ALL user data |

**NEVER use SQLite for hosted services.**

### What Needs Migration Where

**SQLite (Local Client)** - Migrations 011-015:
- 011: Fix cached subscription limits
- 012-014: Team tables for future local caching (optional)
- 015: Normalize devices for sync compatibility

**PostgreSQL (Cloud Service)** - Already has correct schema in models.py:
- Teams tables already defined ✓
- Subscription team fields already defined ✓
- Correct tier limits need DATA migration only (done via SQL)

### Current State (SQLite - Local Client)

10 migrations exist in `src/contextfs/migrations/versions/`:
- 001-007: Core schema (memories, sessions, edges, sync, structured data)
- 008-010: Auth tables (users, api_keys, subscriptions, password_reset, devices)

### Correct Tier Limits (Reference)

| Tier | device_limit | memory_limit |
|------|--------------|--------------|
| free | 2 | 5,000 |
| pro | 5 | 50,000 |
| team | 10 | -1 (unlimited) |
| enterprise | -1 (unlimited) | -1 (unlimited) |
| admin | -1 (unlimited) | -1 (unlimited) |

**OLD incorrect values**: free was 3/10000, pro was 10/100000

---

### Migration 011: Fix Existing Subscription Limits (DATA MIGRATION)

**Purpose**: Update ALL existing subscriptions to correct tier limits

```python
# 011_fix_subscription_tier_limits.py
"""Fix existing subscription tier limits.

Revision ID: 011
Revises: 010
"""

TIER_LIMITS = {
    "free": {"device_limit": 2, "memory_limit": 5000},
    "pro": {"device_limit": 5, "memory_limit": 50000},
    "team": {"device_limit": 10, "memory_limit": -1},
    "enterprise": {"device_limit": -1, "memory_limit": -1},
    "admin": {"device_limit": -1, "memory_limit": -1},
}

def upgrade():
    # Update each tier to correct limits
    for tier, limits in TIER_LIMITS.items():
        op.execute(f"""
            UPDATE subscriptions
            SET device_limit = {limits['device_limit']},
                memory_limit = {limits['memory_limit']}
            WHERE tier = '{tier}'
        """)

def downgrade():
    # Revert to old incorrect values (for rollback)
    op.execute("UPDATE subscriptions SET device_limit = 3, memory_limit = 10000 WHERE tier = 'free'")
    op.execute("UPDATE subscriptions SET device_limit = 10, memory_limit = 100000 WHERE tier = 'pro'")
```

**PostgreSQL equivalent** (run directly or via Alembic):
```sql
-- Fix free tier
UPDATE subscriptions SET device_limit = 2, memory_limit = 5000 WHERE tier = 'free';
-- Fix pro tier
UPDATE subscriptions SET device_limit = 5, memory_limit = 50000 WHERE tier = 'pro';
-- Fix team tier
UPDATE subscriptions SET device_limit = 10, memory_limit = -1 WHERE tier = 'team';
-- Fix enterprise tier
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'enterprise';
-- Fix admin tier
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'admin';
```

---

### Migration 012: Add Team Tables (SCHEMA MIGRATION)

```python
# 012_add_teams_tables.py
"""Add team collaboration tables.

Revision ID: 012
Revises: 011

Tables created:
- teams: Team definitions
- team_members: User-team membership with roles
- team_invitations: Pending email invitations
"""

def upgrade():
    # Teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Team members table
    op.create_table(
        'team_members',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, default='member'),  # owner, admin, member
        sa.Column('joined_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member'),
    )

    # Team invitations table
    op.create_table(
        'team_invitations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, default='member'),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('invited_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Indexes for performance
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_invitations_email', 'team_invitations', ['email'])
    op.create_index('ix_team_invitations_token', 'team_invitations', ['token'])

def downgrade():
    op.drop_table('team_invitations')
    op.drop_table('team_members')
    op.drop_table('teams')
```

---

### Migration 013: Add Team/Visibility to Memories & Sessions (SCHEMA MIGRATION)

```python
# 013_add_team_visibility_columns.py
"""Add team sharing and visibility columns to memories and sessions.

Revision ID: 013
Revises: 012

Columns added:
- team_id: FK to teams table (nullable)
- owner_id: Original creator (for shared memories)
- visibility: private | team_read | team_write
"""

def upgrade():
    # Add to memories table
    op.add_column('memories', sa.Column('team_id', sa.String(36), nullable=True))
    op.add_column('memories', sa.Column('owner_id', sa.String(36), nullable=True))
    op.add_column('memories', sa.Column('visibility', sa.String(20), server_default='private'))
    op.create_foreign_key('fk_memories_team', 'memories', 'teams', ['team_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_memories_team_id', 'memories', ['team_id'])
    op.create_index('ix_memories_visibility', 'memories', ['visibility'])

    # Add to sessions table
    op.add_column('sessions', sa.Column('team_id', sa.String(36), nullable=True))
    op.add_column('sessions', sa.Column('owner_id', sa.String(36), nullable=True))
    op.add_column('sessions', sa.Column('visibility', sa.String(20), server_default='private'))
    op.create_foreign_key('fk_sessions_team', 'sessions', 'teams', ['team_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_sessions_team_id', 'sessions', ['team_id'])

def downgrade():
    # Remove from sessions
    op.drop_index('ix_sessions_team_id', 'sessions')
    op.drop_constraint('fk_sessions_team', 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'visibility')
    op.drop_column('sessions', 'owner_id')
    op.drop_column('sessions', 'team_id')

    # Remove from memories
    op.drop_index('ix_memories_visibility', 'memories')
    op.drop_index('ix_memories_team_id', 'memories')
    op.drop_constraint('fk_memories_team', 'memories', type_='foreignkey')
    op.drop_column('memories', 'visibility')
    op.drop_column('memories', 'owner_id')
    op.drop_column('memories', 'team_id')
```

---

### Migration 014: Add Team Seats to Subscriptions (SCHEMA + DATA)

```python
# 014_add_subscription_team_fields.py
"""Add team seat tracking to subscriptions.

Revision ID: 014
Revises: 013

Columns added:
- team_id: Link subscription to team (for team billing)
- seats_included: Number of seats in plan
- seats_used: Current seat usage
"""

def upgrade():
    op.add_column('subscriptions', sa.Column('team_id', sa.String(36), nullable=True))
    op.add_column('subscriptions', sa.Column('seats_included', sa.Integer, server_default='1'))
    op.add_column('subscriptions', sa.Column('seats_used', sa.Integer, server_default='1'))
    op.create_foreign_key('fk_subscriptions_team', 'subscriptions', 'teams', ['team_id'], ['id'], ondelete='SET NULL')

    # Set default seats for existing team subscriptions
    op.execute("UPDATE subscriptions SET seats_included = 5, seats_used = 1 WHERE tier = 'team'")

def downgrade():
    op.drop_constraint('fk_subscriptions_team', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'seats_used')
    op.drop_column('subscriptions', 'seats_included')
    op.drop_column('subscriptions', 'team_id')
```

---

### Migration 015: Normalize Device Schema (SCHEMA MIGRATION)

```python
# 015_normalize_devices_schema.py
"""Normalize devices table to match service model.

Revision ID: 015
Revises: 014

Changes:
- Rename columns to match service model
- Add missing columns (client_version, registered_at, sync_cursor, metadata)
"""

def upgrade():
    # Rename existing columns
    op.alter_column('devices', 'name', new_column_name='device_name')
    op.alter_column('devices', 'device_type', new_column_name='platform')

    # Add missing columns
    op.add_column('devices', sa.Column('client_version', sa.String(50), nullable=True))
    op.add_column('devices', sa.Column('registered_at', sa.DateTime, server_default=sa.func.now()))
    op.add_column('devices', sa.Column('sync_cursor', sa.DateTime, nullable=True))
    op.add_column('devices', sa.Column('metadata', sa.JSON, nullable=True))

    # Drop columns not in service model
    op.drop_column('devices', 'os')
    op.drop_column('devices', 'os_version')

def downgrade():
    op.add_column('devices', sa.Column('os', sa.String(50), nullable=True))
    op.add_column('devices', sa.Column('os_version', sa.String(50), nullable=True))
    op.drop_column('devices', 'metadata')
    op.drop_column('devices', 'sync_cursor')
    op.drop_column('devices', 'registered_at')
    op.drop_column('devices', 'client_version')
    op.alter_column('devices', 'platform', new_column_name='device_type')
    op.alter_column('devices', 'device_name', new_column_name='name')
```

---

### PostgreSQL Service Migrations

The service (`service/db/`) uses SQLAlchemy models with `create_all()`.
Need to add proper Alembic migration support OR run SQL directly.

**Option A: Direct SQL Script** (Quick fix for existing deployments)

```sql
-- File: service/migrations/001_fix_tier_limits.sql
-- Run: psql $DATABASE_URL -f 001_fix_tier_limits.sql

BEGIN;

-- Fix subscription tier limits for existing users
UPDATE subscriptions SET device_limit = 2, memory_limit = 5000 WHERE tier = 'free';
UPDATE subscriptions SET device_limit = 5, memory_limit = 50000 WHERE tier = 'pro';
UPDATE subscriptions SET device_limit = 10, memory_limit = -1 WHERE tier = 'team';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'enterprise';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'admin';

-- Verify
SELECT tier, device_limit, memory_limit, COUNT(*)
FROM subscriptions
GROUP BY tier, device_limit, memory_limit;

COMMIT;
```

**Option B: Add Alembic to Service** (Proper long-term solution)

```
service/
├── alembic/
│   ├── versions/
│   │   ├── 001_fix_tier_limits.py
│   │   ├── 002_add_teams_tables.py
│   │   └── ...
│   ├── env.py
│   └── script.py.mako
└── alembic.ini
```

---

## Part 2: Immediate Fix for Existing Users

**Run this NOW to fix the devices page:**

```bash
# Connect to PostgreSQL and fix existing subscriptions
docker exec -it contextfs-sync-db psql -U contextfs -d contextfs -c "
UPDATE subscriptions SET device_limit = 2, memory_limit = 5000 WHERE tier = 'free';
UPDATE subscriptions SET device_limit = 5, memory_limit = 50000 WHERE tier = 'pro';
UPDATE subscriptions SET device_limit = 10, memory_limit = -1 WHERE tier = 'team';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'enterprise';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'admin';
"

# Verify the fix
docker exec -it contextfs-sync-db psql -U contextfs -d contextfs -c "
SELECT tier, device_limit, memory_limit, COUNT(*) as user_count
FROM subscriptions
GROUP BY tier, device_limit, memory_limit
ORDER BY tier;
"
```

---

## Part 3: Backend Tests

### Missing Backend Tests

#### Priority 1: Critical Path Tests

```
tests/integration/test_teams.py
├── test_create_team
├── test_list_teams
├── test_add_team_member
├── test_remove_team_member
├── test_change_member_role
├── test_invite_member_by_email
├── test_accept_invitation
├── test_decline_invitation
├── test_invitation_expiry
├── test_team_owner_permissions
├── test_team_admin_permissions
└── test_team_member_permissions

tests/integration/test_billing.py
├── test_get_subscription_free_tier
├── test_get_subscription_paid_tier
├── test_get_usage_stats
├── test_create_checkout_session
├── test_create_portal_session
├── test_webhook_checkout_completed
├── test_webhook_subscription_updated
├── test_webhook_subscription_deleted
├── test_cancel_subscription
├── test_device_limit_enforcement  # CRITICAL
└── test_memory_limit_enforcement  # CRITICAL

tests/integration/test_auth_service.py
├── test_oauth_google_flow
├── test_oauth_github_flow
├── test_create_api_key
├── test_list_api_keys
├── test_revoke_api_key
├── test_delete_api_key
├── test_password_login
├── test_password_reset_request
├── test_password_reset_complete
└── test_email_verification

tests/integration/test_memory_visibility.py
├── test_private_memory_only_owner_sees
├── test_team_read_memory_team_sees
├── test_team_write_memory_team_can_edit
├── test_scope_filter_mine
├── test_scope_filter_team
├── test_scope_filter_all
└── test_cross_team_isolation
```

#### Priority 2: Unit Tests

```
tests/unit/test_subscription_tiers.py
├── test_free_tier_limits (2 devices, 5K memories)
├── test_pro_tier_limits (5 devices, 50K memories)
├── test_team_tier_limits (10 devices, unlimited memories)
├── test_enterprise_tier_limits (unlimited)
├── test_admin_tier_limits (unlimited)
├── test_device_limit_check
└── test_memory_limit_check

tests/unit/test_team_permissions.py
├── test_owner_can_delete_team
├── test_admin_can_invite
├── test_member_cannot_invite
├── test_owner_can_change_roles
└── test_admin_can_remove_members
```

---

## Part 4: Frontend Tests

### Missing Frontend Tests

#### Priority 1: API Client Tests

```typescript
// src/lib/api.test.ts (40+ methods to test)
describe('ApiClient', () => {
  describe('Auth', () => {
    test('getCurrentUser returns user data')
    test('getCurrentUser handles 401')
    test('createApiKey returns key and encryption key')
    test('listApiKeys returns array')
    test('revokeApiKey succeeds')
    test('deleteApiKey succeeds')
  })

  describe('Billing', () => {
    test('getSubscription returns tier info')
    test('getUsage returns correct limits')  // CRITICAL
    test('createCheckout returns checkout URL')
    test('createPortal returns portal URL')
  })

  describe('Teams', () => {
    test('listTeams returns user teams')
    test('createTeam succeeds')
    test('getTeamMembers returns members')
    test('inviteTeamMember sends invite')
    test('acceptInvitation joins team')
  })

  describe('Error handling', () => {
    test('handles network errors')
    test('handles 500 errors')
    test('handles rate limiting')
  })
})
```

#### Priority 2: E2E Tests

```typescript
// e2e/billing.spec.ts
test('free user sees 0/2 device limit')
test('pro user sees 0/5 device limit')
test('team user sees 0/10 device limit')
test('upgrade button creates checkout')

// e2e/devices.spec.ts
test('displays correct device limit per tier')
test('shows warning when at limit')
test('blocks device registration at limit')
```

---

## Part 5: CI/CD Updates

### Backend CI Updates

```yaml
# Add migration validation job
migration-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Check migrations are sequential
      run: python scripts/validate_migrations.py
    - name: Test migrations up/down
      run: |
        python -m contextfs.cli migrate up
        python -m contextfs.cli migrate down
        python -m contextfs.cli migrate up
```

### Frontend CI Updates

```yaml
# Add coverage reporting
test:
  steps:
    - run: npm run test:coverage
    - uses: codecov/codecov-action@v4

# Add E2E for multiple browsers
test-e2e:
  strategy:
    matrix:
      browser: [chromium, firefox, webkit]
```

---

## Part 6: Implementation Order

### Phase 0: IMMEDIATE FIX (Do Now)
1. [x] Run SQL to fix existing subscription limits in PostgreSQL
2. [x] Verify all tiers show correct limits

### Phase 1: SQLite Migrations (Local Client)
1. [x] 011_fix_subscription_tier_limits.py (DATA)
2. [x] 012_add_teams_tables.py (SCHEMA)
3. [x] 013_add_team_visibility_columns.py (SCHEMA)
4. [x] 014_add_subscription_team_fields.py (SCHEMA + DATA)
5. [x] 015_normalize_devices_schema.py (SCHEMA)
6. [x] Test all migrations locally (up/down/up)

### Phase 2: PostgreSQL Migrations (Cloud Service)
1. [x] SQL migration scripts in `migrations/sync-004-fix-tier-limits.sql`
2. [x] PostgreSQL models already up-to-date in `service/db/models.py`
3. [x] Fixed column defaults in PostgreSQL
4. [x] Fixed existing user data in PostgreSQL

### Phase 3: Backend Tests
1. [x] test_billing.py - Tier limits and enforcement
2. [x] test_teams.py - Team CRUD and permissions
3. [ ] test_auth_service.py - Auth flows (future)
4. [ ] test_memory_visibility.py - Team sharing (future)

### Phase 4: Frontend Tests
1. [x] api.test.ts - API client unit tests
2. [ ] E2E billing/tier tests (future)
3. [ ] E2E team tests (future)

### Phase 5: CI Updates
1. [x] Add migration validation to backend CI
2. [x] Add coverage reporting to frontend CI

---

## Estimated Effort

| Task | Effort | Priority |
|------|--------|----------|
| **Phase 0: Fix existing data** | 15 min | P0 - NOW |
| Phase 1: SQLite migrations | 4-6 hours | P0 |
| Phase 2: PostgreSQL migrations | 2-4 hours | P0 |
| Phase 3: Backend tests | 8-12 hours | P1 |
| Phase 4: Frontend tests | 8-12 hours | P1 |
| Phase 5: CI updates | 2-4 hours | P2 |

**Total Estimated**: 25-40 hours

---

## Success Criteria

- [x] Existing users have correct tier limits (after Phase 0)
- [x] All 5 SQLite migrations apply cleanly (up and down)
- [x] PostgreSQL migration script created (sync-004-fix-tier-limits.sql)
- [x] Backend tests created (test_billing.py, test_teams.py)
- [x] Frontend tests created (api.test.ts)
- [x] CI updated with migration validation and coverage
- [ ] All E2E critical paths pass (future)
- [ ] CI runs green on all PRs (to verify)
- [ ] No regressions in existing tests (to verify)
