import logging
from sqlalchemy import text
from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)


async def run_async_migrations():
    """
    Safely adds missing columns to PostgreSQL or SQLite tables without dropping existing data.
    """
    raw_url = settings.DATABASE_URL.lower()

    if "postgresql" in raw_url or "postgres" in raw_url:
        logger.info("Checking PostgreSQL schema migrations...")
        async with engine.begin() as conn:
            pg_migrations = [
                # Agents table migrations
                "ALTER TABLE agents ALTER COLUMN purpose TYPE VARCHAR(1024);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS description TEXT;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS system_prompt TEXT;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS default_language VARCHAR(64) DEFAULT 'English';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS supported_languages JSON DEFAULT '[]';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS concurrency INTEGER DEFAULT 1;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS provider VARCHAR(32) DEFAULT 'vobiz';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS avatar VARCHAR(255);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS questionnaire_id VARCHAR(36);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS stt_config JSON DEFAULT '{}';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS tts_config JSON DEFAULT '{}';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS llm_config JSON DEFAULT '{}';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS company_name VARCHAR(255);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS company_description TEXT;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS greeting_message TEXT;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS predefined_faqs JSON DEFAULT '[]';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS telephony_provider VARCHAR(64) DEFAULT 'workspace_default';",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS telephony_from_number VARCHAR(32);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS telephony_auth_id VARCHAR(128);",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS telephony_auth_token VARCHAR(255);",

                # Calls table migrations
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36);",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS campaign_id VARCHAR(36);",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS contact_id VARCHAR(36);",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS direction VARCHAR(16) DEFAULT 'outbound';",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS telephony_call_id VARCHAR(64);",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS termination_reason VARCHAR(64);",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS answered_at TIMESTAMPTZ;",
                "ALTER TABLE calls ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
            ]
            for stmt in pg_migrations:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    logger.warning(f"PG migration warning ({stmt[:40]}...): {e}")

            logger.info("PostgreSQL schema migrations complete.")

    elif "sqlite" in raw_url:
        import os
        import sqlite3
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        if not os.path.exists(db_path):
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(agents)")
            agent_cols = [row[1] for row in cursor.fetchall()]
            sqlite_agent_migrations = [
                ("tenant_id", "VARCHAR(36)"),
                ("description", "TEXT"),
                ("system_prompt", "TEXT"),
                ("default_language", "VARCHAR(64) DEFAULT 'English'"),
                ("supported_languages", "TEXT DEFAULT '[]'"),
                ("concurrency", "INTEGER DEFAULT 1"),
                ("provider", "VARCHAR(32) DEFAULT 'vobiz'"),
                ("avatar", "VARCHAR(255)"),
                ("questionnaire_id", "VARCHAR(36)"),
                ("stt_config", "TEXT DEFAULT '{}'"),
                ("tts_config", "TEXT DEFAULT '{}'"),
                ("llm_config", "TEXT DEFAULT '{}'"),
                ("company_name", "VARCHAR(255)"),
                ("company_description", "TEXT"),
                ("greeting_message", "TEXT"),
                ("predefined_faqs", "TEXT DEFAULT '[]'"),
                ("telephony_provider", "VARCHAR(64) DEFAULT 'workspace_default'"),
                ("telephony_from_number", "VARCHAR(32)"),
                ("telephony_auth_id", "VARCHAR(128)"),
                ("telephony_auth_token", "VARCHAR(255)"),
            ]
            for col_name, col_def in sqlite_agent_migrations:
                if col_name not in agent_cols:
                    cursor.execute(f"ALTER TABLE agents ADD COLUMN {col_name} {col_def}")

            cursor.execute("PRAGMA table_info(calls)")
            call_cols = [row[1] for row in cursor.fetchall()]
            sqlite_call_migrations = [
                ("tenant_id", "VARCHAR(36)"),
                ("campaign_id", "VARCHAR(36)"),
                ("contact_id", "VARCHAR(36)"),
                ("direction", "VARCHAR(16) DEFAULT 'outbound'"),
                ("telephony_call_id", "VARCHAR(64)"),
                ("termination_reason", "VARCHAR(64)"),
                ("answered_at", "DATETIME"),
                ("updated_at", "DATETIME"),
            ]
            for col_name, col_def in sqlite_call_migrations:
                if col_name not in call_cols:
                    cursor.execute(f"ALTER TABLE calls ADD COLUMN {col_name} {col_def}")

            # Ensure invoices table exists in SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id VARCHAR(36) PRIMARY KEY,
                    invoice_number VARCHAR(64) UNIQUE NOT NULL,
                    business_id VARCHAR(36),
                    status VARCHAR(32) NOT NULL DEFAULT 'ISSUED',
                    subtotal FLOAT NOT NULL DEFAULT 0.0,
                    tax FLOAT NOT NULL DEFAULT 0.0,
                    total FLOAT NOT NULL DEFAULT 0.0,
                    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                    issue_date DATETIME NOT NULL,
                    due_date DATETIME NOT NULL,
                    notes VARCHAR(512),
                    line_items TEXT DEFAULT '[]',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)

            conn.commit()
        except Exception as e:
            logger.error(f"SQLite migration error: {e}")
        finally:
            conn.close()


def run_migrations():
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(run_async_migrations())
        else:
            loop.run_until_complete(run_async_migrations())
    except RuntimeError:
        asyncio.run(run_async_migrations())
