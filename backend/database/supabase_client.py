"""
Supabase & PostgreSQL Connection Management
Provides unified client access with automatic fallback when credentials are absent.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv, find_dotenv

# Automatically load .env from project root
load_dotenv(find_dotenv())

logger = logging.getLogger("supabase_client")

_supabase_client = None
_client_initialized = False


def get_supabase_client():
    """
    Returns an initialized Supabase Python client using SUPABASE_URL and SUPABASE_KEY.
    Returns None if credentials are not configured or library is not available.
    """
    global _supabase_client, _client_initialized

    if _client_initialized:
        return _supabase_client

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_KEY", "").strip()

    if not supabase_url or not supabase_key:
        if os.environ.get("DATABASE_URL", "").strip():
            logger.info("Supabase REST key not provided; using direct PostgreSQL connection (DATABASE_URL) for database operations.")
        else:
            logger.info("SUPABASE_URL or SUPABASE_KEY not set. Using in-memory fallback storage.")
        _client_initialized = True
        _supabase_client = None
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(supabase_url, supabase_key)
        _client_initialized = True
        logger.info(f"Connected to Supabase client at: {supabase_url[:28]}...")
        return _supabase_client
    except ImportError:
        logger.warning(
            "supabase package is not installed. "
            "Install with 'pip install supabase'. Falling back to in-memory mode."
        )
        _client_initialized = True
        _supabase_client = None
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        _client_initialized = True
        _supabase_client = None
        return None


def get_db_connection():
    """
    Returns a live psycopg2 PostgreSQL connection using DATABASE_URL.
    Returns None if DATABASE_URL is not set or connection fails.
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        return None

    try:
        import psycopg2
        return psycopg2.connect(db_url)
    except Exception as e:
        logger.warning(f"Direct PostgreSQL connection failed: {e}")
        return None


def is_supabase_connected() -> bool:
    """Checks if Supabase REST client or direct PostgreSQL connection is active."""
    client = get_supabase_client()
    if client is not None:
        try:
            # Quick ping query
            client.table("cadastral_regions").select("id").limit(1).execute()
            return True
        except Exception:
            pass

    conn = get_db_connection()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
            conn.close()
            return True
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    return False


def get_database_status() -> Dict[str, Any]:
    """
    Returns status metadata for health checks and API inspection.
    """
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    has_sb_key = bool(os.environ.get("SUPABASE_KEY", "").strip())
    has_db_url = bool(os.environ.get("DATABASE_URL", "").strip())

    connected = is_supabase_connected()

    table_stats = {}
    conn = get_db_connection()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                for table in ["cadastral_buildings", "cadastral_units", "cadastral_parties", "cadastral_disputes"]:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table};")
                        table_stats[table] = cur.fetchone()[0]
                    except Exception:
                        table_stats[table] = "table not created (run migrations)"
            conn.close()
        except Exception:
            pass

    return {
        "is_connected": connected,
        "mode": "supabase_cloud" if connected else "in_memory_fallback",
        "has_supabase_url": bool(sb_url),
        "has_supabase_key": has_sb_key,
        "has_database_url": has_db_url,
        "supabase_project_url": sb_url[:35] + "..." if sb_url else None,
        "table_counts": table_stats
    }
