import { NextResponse } from "next/server";
import Database from "better-sqlite3";
import path from "path";

// Path to the backend's SQLite DB
const DB_PATH = path.resolve(process.cwd(), "../backend/data/callers.db");

export async function GET() {
  try {
    const db = new Database(DB_PATH, { readonly: true });
    
    // Check if escalations table exists
    const tableCheck = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='escalations'").get();
    
    if (!tableCheck) {
      return NextResponse.json({ escalations: [] });
    }

    const escalations = db.prepare("SELECT * FROM escalations ORDER BY created_at DESC").all();
    db.close();

    return NextResponse.json({ escalations });
  } catch (error) {
    console.error("Failed to fetch escalations:", error);
    return NextResponse.json(
      { error: "Failed to fetch escalations" },
      { status: 500 }
    );
  }
}
