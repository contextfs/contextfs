-- ContextFS Sync Service - Teams Migration
-- Implements team-based memory sharing for Team tier

-- =============================================================================
-- Teams Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_owner ON teams(owner_id);

-- =============================================================================
-- Team Members Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS team_members (
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',  -- 'owner', 'admin', 'member'
    invited_by TEXT REFERENCES users(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);

-- =============================================================================
-- Team Invitations Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS team_invitations (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    invited_by TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_team_invitations_team ON team_invitations(team_id);
CREATE INDEX IF NOT EXISTS idx_team_invitations_email ON team_invitations(email);

-- =============================================================================
-- Add team columns to memories table
-- =============================================================================
ALTER TABLE memories ADD COLUMN IF NOT EXISTS owner_id TEXT REFERENCES users(id);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS team_id TEXT REFERENCES teams(id);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private';
-- visibility values: 'private', 'team_read', 'team_write'

CREATE INDEX IF NOT EXISTS idx_memories_owner ON memories(owner_id);
CREATE INDEX IF NOT EXISTS idx_memories_team ON memories(team_id);
CREATE INDEX IF NOT EXISTS idx_memories_visibility ON memories(visibility);

-- =============================================================================
-- Add team columns to sessions table
-- =============================================================================
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS owner_id TEXT REFERENCES users(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS team_id TEXT REFERENCES teams(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private';

CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_sessions_team ON sessions(team_id);

-- =============================================================================
-- Update subscriptions with team limits
-- =============================================================================
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS team_id TEXT REFERENCES teams(id);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS seats_included INTEGER DEFAULT 1;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS seats_used INTEGER DEFAULT 1;

-- =============================================================================
-- Update triggers
-- =============================================================================
DROP TRIGGER IF EXISTS teams_updated_at ON teams;
CREATE TRIGGER teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- Migrate existing data: Set owner_id from user_id where missing
-- =============================================================================
UPDATE memories SET owner_id = user_id WHERE owner_id IS NULL AND user_id IS NOT NULL;
UPDATE sessions SET owner_id = user_id WHERE owner_id IS NULL AND user_id IS NOT NULL;

-- =============================================================================
-- Grants
-- =============================================================================
GRANT ALL PRIVILEGES ON teams TO contextfs;
GRANT ALL PRIVILEGES ON team_members TO contextfs;
GRANT ALL PRIVILEGES ON team_invitations TO contextfs;
