"""Sync service FastAPI application.

Main entry point for the ContextFS sync server.
Run with: uvicorn service.api.main:app --host 0.0.0.0 --port 8766

Admin user created on startup if ADMIN_EMAIL and ADMIN_PASSWORD env vars are set.
"""

import hashlib
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextfs.auth import generate_api_key, hash_api_key, init_auth_middleware
from service.api.auth_routes import router as auth_router
from service.api.billing_routes import router as billing_router
from service.api.sync_routes import router as sync_router
from service.db.session import close_db, create_tables, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ADMIN_USER_ID = "admin-00000000-0000-0000-0000-000000000001"


def _hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def init_auth_db(db_path: str) -> None:
    """Initialize auth database tables (SQLite)."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                provider TEXT NOT NULL DEFAULT 'api_key',
                provider_id TEXT,
                password_hash TEXT,
                email_verified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                key_prefix TEXT NOT NULL,
                encryption_salt TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def ensure_admin_user(db_path: str) -> str | None:
    """Create admin user from env vars if not exists. Returns API key if created."""
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        logger.info("Admin not configured (set ADMIN_EMAIL + ADMIN_PASSWORD)")
        return None

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Check if admin exists with active key
        cursor = await db.execute(
            "SELECT u.id, k.key_prefix FROM users u LEFT JOIN api_keys k ON u.id = k.user_id AND k.is_active = 1 WHERE u.id = ?",
            (ADMIN_USER_ID,),
        )
        row = await cursor.fetchone()
        if row and row["key_prefix"]:
            logger.info(f"Admin exists with key prefix: {row['key_prefix']}...")
            return None

        # Create or update admin user
        password_hash = _hash_password(admin_password)
        if not row:
            await db.execute(
                "INSERT INTO users (id, email, name, provider, password_hash, email_verified, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (
                    ADMIN_USER_ID,
                    admin_email,
                    "Admin",
                    "system",
                    password_hash,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            logger.info(f"Created admin: {admin_email}")

        # Create API key
        env_key = os.environ.get("ADMIN_API_KEY")
        if env_key and env_key.startswith("ctxfs_"):
            full_key, key_prefix = env_key, env_key[6:14]
        else:
            full_key, key_prefix = generate_api_key()

        await db.execute(
            "INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
            (
                str(uuid4()),
                ADMIN_USER_ID,
                "Admin Key",
                hash_api_key(full_key),
                key_prefix,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
        return full_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    logger.info("Starting ContextFS Sync Service...")

    # Initialize sync database (Postgres)
    await init_db()
    await create_tables()
    logger.info("Sync database initialized")

    # Initialize auth database (SQLite)
    db_path = os.environ.get("CONTEXTFS_DB_PATH", "contextfs.db")
    await init_auth_db(db_path)

    # Create admin if configured
    admin_key = await ensure_admin_user(db_path)
    if admin_key:
        logger.info("=" * 50)
        logger.info(f"ADMIN API KEY: {admin_key}")
        logger.info("=" * 50)

    init_auth_middleware(db_path)
    logger.info("Auth initialized")

    yield

    logger.info("Shutting down...")
    await close_db()


app = FastAPI(
    title="ContextFS Sync Service",
    description="Multi-device memory synchronization service with vector clock conflict resolution",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync_router)
app.include_router(auth_router)
app.include_router(billing_router)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "contextfs-sync",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "ContextFS Sync Service",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "sync": {
                "register": "POST /api/sync/register",
                "push": "POST /api/sync/push",
                "pull": "POST /api/sync/pull",
                "status": "POST /api/sync/status",
            },
            "auth": {
                "me": "GET /api/auth/me",
                "api_keys": "GET /api/auth/api-keys",
                "create_key": "POST /api/auth/api-keys",
                "oauth_init": "POST /api/auth/oauth/init",
                "oauth_callback": "POST /api/auth/oauth/callback",
            },
            "billing": {
                "checkout": "POST /api/billing/checkout",
                "portal": "POST /api/billing/portal",
                "subscription": "GET /api/billing/subscription",
                "usage": "GET /api/billing/usage",
                "webhook": "POST /api/billing/webhook",
            },
        },
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("CONTEXTFS_SYNC_PORT", "8766"))
    host = os.environ.get("CONTEXTFS_SYNC_HOST", "0.0.0.0")

    uvicorn.run(
        "service.api.main:app",
        host=host,
        port=port,
        reload=os.environ.get("CONTEXTFS_DEV", "").lower() == "true",
    )
