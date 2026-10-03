"""
Automated Database Migration Runner for Supabase / PostgreSQL
Applies LADM SQL migrations idempotently and tracks version state.
"""

import os
import sys
import glob
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_runner")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(ROOT_DIR, "migrations")


def get_database_url() -> str:
    """Retrieves PostgreSQL DATABASE_URL from environment or .env file."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        env_file = os.path.join(ROOT_DIR, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                            url = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    return url


def run_all_migrations(database_url: str = None) -> dict:
    """
    Executes all unapplied .sql migrations in alphanumeric order.
    Returns summary dict of results.
    """
    db_url = database_url if database_url is not None else get_database_url()

    if not db_url:
        logger.warning(
            "No DATABASE_URL found in environment. "
            "To run migrations against Supabase, set DATABASE_URL in .env"
        )
        return {
            "status": "SKIPPED",
            "message": "DATABASE_URL not configured. Set DATABASE_URL in .env to run Supabase migrations.",
            "applied_migrations": []
        }

    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 is not installed. Install with 'pip install psycopg2-binary'")
        return {
            "status": "ERROR",
            "message": "psycopg2-binary not installed. Please install dependencies.",
            "applied_migrations": []
        }

    sql_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    if not sql_files:
        logger.warning(f"No SQL migration files found in {MIGRATIONS_DIR}")
        return {
            "status": "SUCCESS",
            "message": "No migration files found.",
            "applied_migrations": []
        }

    applied = []
    conn = None
    try:
        logger.info("Connecting to Supabase / PostgreSQL...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cur = conn.cursor()

        # Create migration tracking table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()

        # Check existing migrations
        cur.execute("SELECT version FROM schema_migrations;")
        executed_versions = set(row[0] for row in cur.fetchall())

        for file_path in sql_files:
            filename = os.path.basename(file_path)
            if filename in executed_versions:
                logger.info(f"Migration {filename} already applied. Skipping.")
                continue

            logger.info(f"Applying migration: {filename} ...")
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            cur.execute(sql_content)
            cur.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s);",
                (filename,)
            )
            conn.commit()
            applied.append(filename)
            logger.info(f"Successfully applied {filename}")

        cur.close()
        conn.close()

        return {
            "status": "SUCCESS",
            "message": f"Successfully applied {len(applied)} migration(s).",
            "applied_migrations": applied
        }

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "message": str(e),
            "applied_migrations": applied
        }


if __name__ == "__main__":
    print("=" * 60)
    print(" 3D Cadastral Registry - Supabase Migration Runner")
    print("=" * 60)
    result = run_all_migrations()
    print(f"Result: {result['status']} - {result['message']}")
    if result["applied_migrations"]:
        print(f"Applied: {', '.join(result['applied_migrations'])}")
    sys.exit(0 if result["status"] in ("SUCCESS", "SKIPPED") else 1)
