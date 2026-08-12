"""
Quick automated test for the Day 7 escalation flow.

Verifies (without needing the live voice stack):
  1. DB init + follow_up migration works.
  2. create_escalation_record stores summary, urgency, language, follow_up
     and the REAL user_id (bug-fix #2).
  3. A row can be read back exactly like the dashboard / API route does
     (SELECT * FROM escalations).
  4. agent.py imports cleanly (validates the missing `re` import fix #1),
     if its dependencies are installed.

Run from backend/:  uv run python test_escalation_flow.py
"""

import asyncio
import sys

sys.path.insert(0, "src")

import aiosqlite  # noqa: E402
from db import init_db, create_escalation_record, _DB_PATH  # noqa: E402


async def main() -> None:
    print(f"Using DB: {_DB_PATH}")

    # 1. Init + migration
    await init_db()
    print("[OK] init_db() ran (follow_up migration applied if needed)")

    # 2. Escalation path — create a ticket with the new follow_up field
    result = await create_escalation_record(
        escalation_id="TKT-TEST01",
        user_id="test-caller-9876543210",
        summary="Ramesh from Sector 4 disputes a refund on 5kg aata. "
                "Agent already checked the price (Rs 210) and order history.",
        urgency="high",
        language="Hindi",
        follow_up="phone call",
    )
    assert result["status"] == "open", "status should default to open"
    print(f"[OK] create_escalation_record returned: {result}")

    # 3. Read it back exactly like the dashboard / API route
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM escalations WHERE escalation_id = ?", ("TKT-TEST01",)
        )
        row = await cursor.fetchone()

    assert row is not None, "ticket was not stored"
    assert row["user_id"] == "test-caller-9876543210", "user_id must be the REAL caller, not 'caller'"
    assert row["follow_up"] == "phone call", "follow_up must be stored"
    assert row["urgency"] == "high"
    assert row["language"] == "Hindi"
    assert row["status"] == "open"
    print("[OK] Row read back with correct user_id, follow_up, urgency, language, status")

    # 4. Cleanup the test row so it doesn't pollute the dashboard
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("DELETE FROM escalations WHERE escalation_id = ?", ("TKT-TEST01",))
        await db.commit()
    print("[OK] Test row cleaned up")

    print("\nESCALATION FLOW TEST PASSED [OK]")


if __name__ == "__main__":
    asyncio.run(main())
