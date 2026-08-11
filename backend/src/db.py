"""
Persistent caller memory using SQLite.

Stores caller profiles so the agent can recognise returning customers,
greet them by name, and recall past orders / preferences.
"""

import json
import logging
import os
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger("agent.db")

# Database lives in backend/data/callers.db
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DB_PATH = os.path.join(_DB_DIR, "callers.db")

_CREATE_TABLE_CALLERS = """
CREATE TABLE IF NOT EXISTS callers (
    user_id          TEXT PRIMARY KEY,
    name             TEXT,
    language_pref    TEXT DEFAULT 'hi',
    facts            TEXT DEFAULT '{}',
    last_interaction TEXT
);
"""

_CREATE_TABLE_ESCALATIONS = """
CREATE TABLE IF NOT EXISTS escalations (
    escalation_id    TEXT PRIMARY KEY,
    user_id          TEXT,
    summary          TEXT,
    urgency          TEXT,
    language         TEXT,
    status           TEXT DEFAULT 'open',
    created_at       TEXT
);
"""

async def init_db() -> None:
    """Create the data directory and callers table if they don't exist."""
    os.makedirs(_DB_DIR, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(_CREATE_TABLE_CALLERS)
        await db.execute(_CREATE_TABLE_ESCALATIONS)
        await db.commit()
    logger.info("Caller database initialised at %s", _DB_PATH)


async def lookup_caller(user_id: str) -> dict | None:
    """Look up a caller by their ID.

    Returns a dict with keys: user_id, name, language_pref, facts,
    last_interaction — or None if the caller is not found.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM callers WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

    if row is None:
        logger.info("Caller %s not found in database", user_id)
        return None

    caller = {
        "user_id": row["user_id"],
        "name": row["name"],
        "language_pref": row["language_pref"],
        "facts": json.loads(row["facts"]) if row["facts"] else {},
        "last_interaction": row["last_interaction"],
    }
    logger.info("Found returning caller: %s (%s)", caller["name"], user_id)
    return caller


async def save_caller(
    user_id: str,
    name: str,
    language_pref: str = "hi",
    facts: dict | None = None,
) -> dict:
    """Insert or update a caller profile.

    Args:
        user_id: Unique caller identifier (participant identity / phone number).
        name: Caller's name.
        language_pref: Preferred language code (hi / en / hinglish).
        facts: Dict of facts to save — past_orders, usual_quantities,
               preferred_delivery_slot, area, etc.

    Returns:
        The saved caller profile as a dict.
    """
    now = datetime.now(timezone.utc).isoformat()
    facts_json = json.dumps(facts or {}, ensure_ascii=False)

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO callers (user_id, name, language_pref, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name             = excluded.name,
                language_pref    = excluded.language_pref,
                facts            = excluded.facts,
                last_interaction = excluded.last_interaction
            """,
            (user_id, name, language_pref, facts_json, now),
        )
        await db.commit()

    saved = {
        "user_id": user_id,
        "name": name,
        "language_pref": language_pref,
        "facts": facts or {},
        "last_interaction": now,
    }
    logger.info("Saved caller profile: %s (%s)", name, user_id)
    return saved


async def create_escalation_record(
    escalation_id: str,
    user_id: str,
    summary: str,
    urgency: str,
    language: str
) -> dict:
    """Insert a new escalation record for human help."""
    now = datetime.now(timezone.utc).isoformat()
    
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO escalations (escalation_id, user_id, summary, urgency, language, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?)
            """,
            (escalation_id, user_id, summary, urgency, language, now),
        )
        await db.commit()
    
    logger.info("Created escalation %s for user %s", escalation_id, user_id)
    return {
        "escalation_id": escalation_id,
        "status": "open",
    }
