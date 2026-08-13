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
    follow_up        TEXT,
    status           TEXT DEFAULT 'open',
    created_at       TEXT
);
"""

# Day 8 – Call analytics. Every completed call is recorded here so the
# dashboard can show total / successful / failed counts from real data.
# NOTE: we deliberately DO NOT store transcripts, OTPs, PINs, or any
# sensitive caller content here — only outcome metadata.
_CREATE_TABLE_CALLS = """
CREATE TABLE IF NOT EXISTS calls (
    call_id          TEXT PRIMARY KEY,
    user_id          TEXT,
    channel          TEXT DEFAULT 'browser',
    outcome          TEXT,
    failure_reason   TEXT DEFAULT '',
    success_criteria TEXT DEFAULT '',
    duration_seconds INTEGER DEFAULT 0,
    started_at       TEXT,
    ended_at         TEXT
);
"""

async def _migrate_escalations(db: aiosqlite.Connection) -> None:
    """Add newer columns to an existing escalations table (safe to re-run)."""
    cursor = await db.execute("PRAGMA table_info(escalations)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "follow_up" not in columns:
        await db.execute("ALTER TABLE escalations ADD COLUMN follow_up TEXT")
        logger.info("Migrated escalations table: added 'follow_up' column")


async def init_db() -> None:
    """Create the data directory and callers table if they don't exist."""
    os.makedirs(_DB_DIR, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(_CREATE_TABLE_CALLERS)
        await db.execute(_CREATE_TABLE_ESCALATIONS)
        await db.execute(_CREATE_TABLE_CALLS)
        await _migrate_escalations(db)
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
    language: str,
    follow_up: str = "",
) -> dict:
    """Insert a new escalation record for human help.

    Args:
        follow_up: The caller's preferred follow-up method (e.g. "phone call",
            "WhatsApp", "SMS", "visit store").
    """
    now = datetime.now(timezone.utc).isoformat()
    
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO escalations (escalation_id, user_id, summary, urgency, language, follow_up, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (escalation_id, user_id, summary, urgency, language, follow_up, now),
        )
        await db.commit()
    
    logger.info("Created escalation %s for user %s", escalation_id, user_id)
    return {
        "escalation_id": escalation_id,
        "status": "open",
    }


async def record_call(
    call_id: str,
    user_id: str,
    channel: str,
    outcome: str,
    started_at: str,
    ended_at: str,
    duration_seconds: int = 0,
    failure_reason: str = "",
    success_criteria: str = "",
) -> dict:
    """Record the outcome of a completed call (Day 8 analytics).

    Args:
        call_id: Unique identifier for this call.
        user_id: The caller's identity (stored for internal linking only —
            never exposed on the public dashboard).
        channel: "browser" or "sip".
        outcome: "success" or "failed". A failed call does not mean something
            broke — it means the call did not reach the defined success
            condition (caller did not find a product / complete an enquiry).
        started_at / ended_at: ISO timestamps.
        duration_seconds: Total call length in seconds.
        failure_reason: For failed calls, a category such as "no_engagement",
            "item_not_found", "incomplete", or "tool_error".
        success_criteria: Human-readable definition of success that was applied.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO calls (
                call_id, user_id, channel, outcome, failure_reason,
                success_criteria, duration_seconds, started_at, ended_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                outcome          = excluded.outcome,
                failure_reason   = excluded.failure_reason,
                success_criteria = excluded.success_criteria,
                duration_seconds = excluded.duration_seconds,
                ended_at         = excluded.ended_at
            """,
            (
                call_id,
                user_id,
                channel,
                outcome,
                failure_reason,
                success_criteria,
                duration_seconds,
                started_at,
                ended_at,
            ),
        )
        await db.commit()

    logger.info(
        "Recorded call %s: outcome=%s channel=%s duration=%ss reason=%s",
        call_id,
        outcome,
        channel,
        duration_seconds,
        failure_reason or "-",
    )
    return {"call_id": call_id, "outcome": outcome}
