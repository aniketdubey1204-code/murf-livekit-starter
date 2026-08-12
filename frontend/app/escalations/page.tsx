import Database from "better-sqlite3";
import path from "path";
import Link from "next/link";
import { ArrowLeft, AlertCircle, Clock, CheckCircle } from "lucide-react";

export const dynamic = "force-dynamic";

const DB_PATH = path.resolve(process.cwd(), "../backend/data/callers.db");

function getEscalations() {
  try {
    const db = new Database(DB_PATH, { readonly: true });
    
    const tableCheck = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='escalations'").get();
    if (!tableCheck) return [];

    const escalations = db.prepare("SELECT * FROM escalations ORDER BY created_at DESC").all();
    db.close();
    return escalations as any[];
  } catch (error) {
    console.error("Failed to fetch escalations:", error);
    return [];
  }
}

export default function EscalationsPage() {
  const escalations = getEscalations();

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex items-center justify-between mb-8">
          <div>
            <Link href="/" className="inline-flex items-center text-sm text-neutral-400 hover:text-white mb-4 transition-colors">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to App
            </Link>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-amber-200 bg-clip-text text-transparent">
              Human Escalation Dashboard
            </h1>
            <p className="text-neutral-400 mt-2">Manage requests requiring human intervention</p>
          </div>
          <div className="flex space-x-4 text-sm">
            <div className="flex items-center text-orange-400 bg-orange-400/10 px-3 py-1.5 rounded-full">
              <AlertCircle className="w-4 h-4 mr-2" />
              {escalations.filter(e => e.status === 'open').length} Open
            </div>
          </div>
        </header>

        {escalations.length === 0 ? (
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-12 text-center text-neutral-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-xl font-medium text-neutral-300">No Escalations Yet</h3>
            <p className="mt-2">All customer issues have been resolved by the AI agent.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {escalations.map((ticket) => (
              <div key={ticket.escalation_id} className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-lg flex flex-col relative overflow-hidden group hover:border-neutral-700 transition-colors">
                
                {/* Top strip for urgency */}
                <div className={`absolute top-0 left-0 w-full h-1 ${
                  ticket.urgency === 'high' || ticket.urgency === 'emergency' ? 'bg-red-500' :
                  ticket.urgency === 'medium' ? 'bg-orange-500' : 'bg-blue-500'
                }`} />

                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className="text-xs font-mono text-neutral-500">{ticket.escalation_id}</span>
                    <h3 className="text-lg font-semibold text-neutral-200 mt-1 capitalize">
                      {ticket.urgency} Priority
                    </h3>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full uppercase font-bold ${
                    ticket.status === 'open' ? 'bg-orange-500/20 text-orange-400' : 'bg-green-500/20 text-green-400'
                  }`}>
                    {ticket.status}
                  </span>
                </div>
                
                <p className="text-neutral-400 text-sm mb-4 flex-grow leading-relaxed">
                  {ticket.summary}
                </p>

                {ticket.follow_up && (
                  <div className="mb-4 flex items-center text-xs text-neutral-300 bg-neutral-800/60 rounded-lg px-3 py-2">
                    <span className="text-neutral-500 mr-2">Follow-up:</span>
                    <span className="font-medium capitalize">{ticket.follow_up}</span>
                  </div>
                )}
                
                <div className="pt-4 border-t border-neutral-800 flex justify-between items-center text-xs text-neutral-500">
                  <span className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1" />
                    {new Date(ticket.created_at).toLocaleString()}
                  </span>
                  <span className="uppercase tracking-wider">{ticket.language}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
