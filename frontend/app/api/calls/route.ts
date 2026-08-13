import { NextResponse } from "next/server";
import Database from "better-sqlite3";
import path from "path";

// Same SQLite DB the backend agent writes call outcomes to.
const DB_PATH = path.resolve(process.cwd(), "../backend/data/callers.db");

// Always compute fresh numbers — never cache the dashboard data.
export const dynamic = "force-dynamic";

type CallRow = {
  call_id: string;
  channel: string;
  outcome: string;
  failure_reason: string;
  duration_seconds: number;
  started_at: string;
  ended_at: string;
};

export async function GET() {
  try {
    const db = new Database(DB_PATH, { readonly: true });

    // The table may not exist yet if no call has completed.
    const tableCheck = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='calls'"
      )
      .get();

    if (!tableCheck) {
      db.close();
      return NextResponse.json(emptyPayload());
    }

    // NOTE: user_id is intentionally NOT selected — the dashboard must not
    // expose caller identities / phone numbers. We only read outcome metadata.
    const rows = db
      .prepare(
        `SELECT call_id, channel, outcome, failure_reason,
                duration_seconds, started_at, ended_at
         FROM calls
         ORDER BY started_at DESC`
      )
      .all() as CallRow[];

    const successCriteria =
      (
        db
          .prepare(
            "SELECT success_criteria FROM calls WHERE success_criteria != '' ORDER BY started_at DESC LIMIT 1"
          )
          .get() as { success_criteria?: string } | undefined
      )?.success_criteria || "Caller found a product or completed an enquiry";

    db.close();

    const total = rows.length;
    const successful = rows.filter((r) => r.outcome === "success").length;
    const failed = rows.filter((r) => r.outcome === "failed").length;

    // Failure reason breakdown (advanced metric).
    const failureBreakdown: Record<string, number> = {};
    for (const r of rows) {
      if (r.outcome === "failed") {
        const key = r.failure_reason || "unspecified";
        failureBreakdown[key] = (failureBreakdown[key] || 0) + 1;
      }
    }

    // Channel breakdown (browser vs SIP).
    const channelBreakdown: Record<string, number> = {};
    for (const r of rows) {
      const key = r.channel || "unknown";
      channelBreakdown[key] = (channelBreakdown[key] || 0) + 1;
    }

    const successRate = total > 0 ? Math.round((successful / total) * 100) : 0;

    const avgDuration =
      total > 0
        ? Math.round(
            rows.reduce((sum, r) => sum + (r.duration_seconds || 0), 0) / total
          )
        : 0;

    // Recent calls — privacy-safe fields only.
    const recent = rows.slice(0, 25).map((r) => ({
      call_id: r.call_id,
      channel: r.channel,
      outcome: r.outcome,
      failure_reason: r.failure_reason,
      duration_seconds: r.duration_seconds,
      started_at: r.started_at,
    }));

    return NextResponse.json({
      total,
      successful,
      failed,
      successRate,
      avgDuration,
      failureBreakdown,
      channelBreakdown,
      successCriteria,
      recent,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Failed to fetch call analytics:", error);
    return NextResponse.json(
      { error: "Failed to fetch call analytics" },
      { status: 500 }
    );
  }
}

function emptyPayload() {
  return {
    total: 0,
    successful: 0,
    failed: 0,
    successRate: 0,
    avgDuration: 0,
    failureBreakdown: {},
    channelBreakdown: {},
    successCriteria: "Caller found a product or completed an enquiry",
    recent: [],
    generatedAt: new Date().toISOString(),
  };
}
