"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Phone,
  CheckCircle,
  XCircle,
  RefreshCw,
  Percent,
  Clock,
  Globe,
  PhoneCall,
} from "lucide-react";

type RecentCall = {
  call_id: string;
  channel: string;
  outcome: string;
  failure_reason: string;
  duration_seconds: number;
  started_at: string;
};

type Analytics = {
  total: number;
  successful: number;
  failed: number;
  successRate: number;
  avgDuration: number;
  failureBreakdown: Record<string, number>;
  channelBreakdown: Record<string, number>;
  successCriteria: string;
  recent: RecentCall[];
  generatedAt: string;
};

const FAILURE_LABELS: Record<string, string> = {
  no_engagement: "Hung up / no engagement",
  item_not_found: "Item not in stock",
  incomplete: "Incomplete enquiry",
  unspecified: "Unspecified",
};

function fmtDuration(seconds: number): string {
  if (!seconds || seconds < 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function DashboardPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch("/api/calls", { cache: "no-store" });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const json = (await res.json()) as Analytics;
      setData(json);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setRefreshing(false);
    }
  }, []);

  // Initial load.
  useEffect(() => {
    load();
  }, [load]);

  // Live auto-refresh every 5s so the dashboard updates when a call ends.
  useEffect(() => {
    if (!live) return;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [live, load]);

  const total = data?.total ?? 0;
  const successful = data?.successful ?? 0;
  const failed = data?.failed ?? 0;

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <Link
              href="/"
              className="inline-flex items-center text-sm text-neutral-400 hover:text-white mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to App
            </Link>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-amber-200 bg-clip-text text-transparent">
              Call Analytics Dashboard
            </h1>
            <p className="text-neutral-400 mt-2">
              Live performance of Dukaan Sathi — from real browser & SIP calls
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/escalations"
              className="text-sm text-neutral-400 hover:text-white transition-colors"
            >
              Escalations →
            </Link>
            <button
              onClick={() => setLive((v) => !v)}
              className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border transition-colors ${
                live
                  ? "border-green-500/40 text-green-400 bg-green-500/10"
                  : "border-neutral-700 text-neutral-400"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  live ? "bg-green-400 animate-pulse" : "bg-neutral-500"
                }`}
              />
              {live ? "Live" : "Paused"}
            </button>
            <button
              onClick={load}
              className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border border-neutral-700 text-neutral-300 hover:bg-neutral-800 transition-colors"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
        </header>

        {/* Success definition banner */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl px-5 py-4 mb-6">
          <p className="text-xs uppercase tracking-wider text-neutral-500 mb-1">
            What counts as a successful call
          </p>
          <p className="text-neutral-200 text-sm">
            {data?.successCriteria ??
              "Caller found a product or completed an enquiry"}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl px-5 py-4 mb-6 text-sm">
            {error}. Make sure the backend has recorded at least one call.
          </div>
        )}

        {/* The three required metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
          <MetricCard
            label="Total Calls"
            value={total}
            icon={<Phone className="w-5 h-5" />}
            accent="text-blue-400"
            ring="border-blue-500/30"
          />
          <MetricCard
            label="Successful Calls"
            value={successful}
            icon={<CheckCircle className="w-5 h-5" />}
            accent="text-green-400"
            ring="border-green-500/30"
          />
          <MetricCard
            label="Failed Calls"
            value={failed}
            icon={<XCircle className="w-5 h-5" />}
            accent="text-red-400"
            ring="border-red-500/30"
          />
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <SmallStat
            label="Success Rate"
            value={`${data?.successRate ?? 0}%`}
            icon={<Percent className="w-4 h-4" />}
          />
          <SmallStat
            label="Avg. Duration"
            value={fmtDuration(data?.avgDuration ?? 0)}
            icon={<Clock className="w-4 h-4" />}
          />
          <SmallStat
            label="Browser Calls"
            value={String(data?.channelBreakdown?.browser ?? 0)}
            icon={<Globe className="w-4 h-4" />}
          />
          <SmallStat
            label="SIP / Phone Calls"
            value={String(data?.channelBreakdown?.sip ?? 0)}
            icon={<PhoneCall className="w-4 h-4" />}
          />
        </div>

        {/* Success rate bar */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 mb-8">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-neutral-300">Success vs. Failed</span>
            <span className="text-neutral-500">
              {successful} success · {failed} failed
            </span>
          </div>
          <div className="w-full h-3 rounded-full bg-neutral-800 overflow-hidden flex">
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${total ? (successful / total) * 100 : 0}%` }}
            />
            <div
              className="h-full bg-red-500 transition-all duration-500"
              style={{ width: `${total ? (failed / total) * 100 : 0}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Failure breakdown */}
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-neutral-200 mb-4">
              Failure Types
            </h3>
            {data && Object.keys(data.failureBreakdown).length > 0 ? (
              <ul className="space-y-3">
                {Object.entries(data.failureBreakdown)
                  .sort((a, b) => b[1] - a[1])
                  .map(([reason, count]) => (
                    <li
                      key={reason}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-neutral-400">
                        {FAILURE_LABELS[reason] || reason}
                      </span>
                      <span className="text-neutral-200 font-medium">
                        {count}
                      </span>
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="text-neutral-500 text-sm">No failed calls yet. 🎉</p>
            )}
          </div>

          {/* Recent calls */}
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-neutral-200 mb-4">
              Recent Calls
            </h3>
            {data && data.recent.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-neutral-500 border-b border-neutral-800">
                      <th className="pb-2 font-medium">Time</th>
                      <th className="pb-2 font-medium">Channel</th>
                      <th className="pb-2 font-medium">Duration</th>
                      <th className="pb-2 font-medium">Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent.map((c) => (
                      <tr
                        key={c.call_id}
                        className="border-b border-neutral-800/60 last:border-0"
                      >
                        <td className="py-2.5 text-neutral-400">
                          {new Date(c.started_at).toLocaleString()}
                        </td>
                        <td className="py-2.5">
                          <span className="capitalize text-neutral-300">
                            {c.channel}
                          </span>
                        </td>
                        <td className="py-2.5 text-neutral-400">
                          {fmtDuration(c.duration_seconds)}
                        </td>
                        <td className="py-2.5">
                          {c.outcome === "success" ? (
                            <span className="inline-flex items-center gap-1 text-green-400">
                              <CheckCircle className="w-3.5 h-3.5" /> Success
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-red-400">
                              <XCircle className="w-3.5 h-3.5" />
                              {FAILURE_LABELS[c.failure_reason] || "Failed"}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-neutral-500 text-sm">
                No calls recorded yet. Make a call to see it appear here.
              </p>
            )}
          </div>
        </div>

        <p className="text-xs text-neutral-600 mt-6">
          No transcripts, OTPs, PINs, or caller identities are stored or shown —
          only anonymous call outcome metadata.
          {data?.generatedAt &&
            ` Updated ${new Date(data.generatedAt).toLocaleTimeString()}.`}
        </p>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
  accent,
  ring,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  accent: string;
  ring: string;
}) {
  return (
    <div
      className={`bg-neutral-900 border ${ring} rounded-xl p-6 shadow-lg`}
    >
      <div className={`flex items-center gap-2 ${accent} mb-3`}>
        {icon}
        <span className="text-sm text-neutral-400">{label}</span>
      </div>
      <div className="text-4xl font-bold text-white tabular-nums">{value}</div>
    </div>
  );
}

function SmallStat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: ReactNode;
}) {
  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-4">
      <div className="flex items-center gap-2 text-neutral-500 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-neutral-100 tabular-nums">
        {value}
      </div>
    </div>
  );
}
