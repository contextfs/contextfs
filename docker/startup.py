#!/usr/bin/env python
"""Startup script that runs migrations before starting the server."""

import asyncio
import glob
import os
import sys


async def run_migrations():
    """Run SQL migrations against PostgreSQL."""
    postgres_url = os.environ.get("CONTEXTFS_POSTGRES_URL")
    if not postgres_url:
        print("CONTEXTFS_POSTGRES_URL not set, skipping migrations")
        return

    try:
        import asyncpg
    except ImportError:
        print("asyncpg not available, skipping migrations")
        return

    print("Running database migrations...")

    try:
        conn = await asyncpg.connect(postgres_url)

        # Get list of migration files sorted by name
        migration_dir = "/app/migrations"
        if not os.path.exists(migration_dir):
            migration_dir = "migrations"

        migration_files = sorted(glob.glob(f"{migration_dir}/sync-*.sql"))
        print(f"Found {len(migration_files)} migration files")

        for migration_file in migration_files:
            filename = os.path.basename(migration_file)
            print(f"  Running {filename}...")

            with open(migration_file) as f:
                sql = f.read()

            # Execute migration (idempotent with IF NOT EXISTS)
            try:
                await conn.execute(sql)
                print(f"  ✓ {filename} completed")
            except Exception as e:
                # Log but continue - migrations are idempotent
                print(f"  ⚠ {filename}: {e}")

        await conn.close()
        print("Migrations complete!")

    except Exception as e:
        print(f"Migration error (continuing anyway): {e}")


def main():
    """Run migrations then start the server."""
    # Run migrations
    asyncio.run(run_migrations())

    # Start uvicorn
    port = os.environ.get("PORT", "8766")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "service.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        port,
    ]
    print(f"Starting server on port {port}...")
    os.execvp(sys.executable, cmd)


if __name__ == "__main__":
    main()
