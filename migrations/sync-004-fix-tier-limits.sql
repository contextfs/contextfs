-- ContextFS Sync Service - Fix Tier Limits Migration
-- Corrects subscription tier limits to official values
--
-- TIER LIMITS:
-- | Tier       | device_limit | memory_limit |
-- |------------|--------------|--------------|
-- | free       | 2            | 5,000        |
-- | pro        | 5            | 50,000       |
-- | team       | 10           | unlimited(-1)|
-- | enterprise | unlimited(-1)| unlimited(-1)|
-- | admin      | unlimited(-1)| unlimited(-1)|
--
-- OLD INCORRECT VALUES: free was 3/10000, pro was 10/100000

-- =============================================================================
-- Fix column defaults for NEW subscriptions
-- =============================================================================
ALTER TABLE subscriptions ALTER COLUMN device_limit SET DEFAULT 2;
ALTER TABLE subscriptions ALTER COLUMN memory_limit SET DEFAULT 5000;

-- =============================================================================
-- Fix existing subscription data
-- =============================================================================
UPDATE subscriptions SET device_limit = 2, memory_limit = 5000 WHERE tier = 'free';
UPDATE subscriptions SET device_limit = 5, memory_limit = 50000 WHERE tier = 'pro';
UPDATE subscriptions SET device_limit = 10, memory_limit = -1 WHERE tier = 'team';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'enterprise';
UPDATE subscriptions SET device_limit = -1, memory_limit = -1 WHERE tier = 'admin';

-- =============================================================================
-- Set default seats for team tier subscriptions
-- =============================================================================
UPDATE subscriptions SET seats_included = 5 WHERE tier = 'team';
