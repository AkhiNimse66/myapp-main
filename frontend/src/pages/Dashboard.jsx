import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, pct, compact } from "../lib/api";
import {
  ArrowUpRight, TrendingUp, Users, Activity,
  CheckCircle2, Circle, Instagram, Zap, ChevronRight,
} from "lucide-react";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [deals, setDeals]     = useState([]);
  const [error, setError]     = useState(null);

  useEffect(() => {
    Promise.all([api.get("/dashboard/summary"), api.get("/deals")])
      .then(([s, d]) => { setSummary(s.data); setDeals(d.data); })
      .catch((err) => {
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          // Stale token — clear it and bounce to login
          localStorage.removeItem("mypay_token");
          window.location.href = "/login";
        } else {
          setError(err?.response?.data?.detail || "Failed to load dashboard.");
        }
      });
  }, []);

  if (error) return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
      <p className="mono text-sm text-red-500">{error}</p>
      <button className="btn-primary text-sm" onClick={() => window.location.reload()}>
        Retry
      </button>
    </div>
  );

  if (!summary) return (
    <div className="min-h-[60vh] flex items-center justify-center mono text-sm text-zinc-400">
      Loading desk…
    </div>
  );

  const ch = summary.creator_health || {};

  return (
    <div data-testid="dashboard-root" className="space-y-10">

      {/* ── Header ── */}
      <div className="flex items-end justify-between">
        <div>
          <span className="label-xs">Creator Desk / Overview</span>
          <h1 className="serif text-5xl tracking-tight mt-2">Your credit line.</h1>
        </div>
        <Link data-testid="new-deal-cta" to="/deals/new" className="btn-primary">
          New Deal <ArrowUpRight className="w-4 h-4" />
        </Link>
      </div>

      {/* ── Row 1: 4 stat cards ── */}
      <section className="grid lg:grid-cols-4 gap-px bg-zinc-200 border hair">
        {/* Credit limit */}
        <div className="bg-white p-8">
          <div className="label-xs">Revolving Credit Limit</div>
          <div className="serif text-5xl tracking-tight mt-3" data-testid="credit-limit">
            {money(summary.credit_limit)}
          </div>
          <div className="mono text-xs text-zinc-400 mt-1">{summary.credit_tier}</div>
          <div className="mt-4 h-0.5 bg-zinc-100">
            <div className="h-0.5 bg-zinc-950 transition-all"
                 style={{ width: `${Math.min(100, summary.used_pct || 0)}%` }} />
          </div>
          <div className="flex justify-between mt-2 mono text-xs text-zinc-500">
            <span>Used {pct(summary.used_pct)}</span>
            <span>Available {money(summary.available)}</span>
          </div>
        </div>

        {/* Outstanding */}
        <div className="bg-white p-8">
          <div className="label-xs">Outstanding Advance</div>
          <div className="serif text-5xl mt-3" data-testid="total-advanced">
            {money(summary.total_advanced)}
          </div>
          <div className="mono text-xs text-zinc-500 mt-2">Recycles on brand payment</div>
        </div>

        {/* Settled */}
        <div className="bg-white p-8">
          <div className="label-xs">Lifetime Settled</div>
          <div className="serif text-5xl mt-3" data-testid="total-repaid">
            {money(summary.total_repaid)}
          </div>
          <div className="mono text-xs text-zinc-500 mt-2">
            {deals.filter(d => d.status === "repaid").length} deals closed
          </div>
        </div>

        {/* Creator health */}
        <div className="bg-white p-8">
          <div className="label-xs">Creator Health Index</div>
          <div className="serif text-5xl mt-3" data-testid="creator-health-score">
            {Number(ch.health_score || 0).toFixed(1)}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <Mini label="Followers" value={compact(ch.followers)} icon={<Users className="w-3.5 h-3.5"/>} />
            <Mini label="ER"        value={pct(ch.engagement_rate, 1)} icon={<TrendingUp className="w-3.5 h-3.5"/>} />
            <Mini label="Auth"      value={Number(ch.authenticity_score || 0).toFixed(0)} icon={<Activity className="w-3.5 h-3.5"/>} />
          </div>
        </div>
      </section>

      {/* ── Row 2: Tier progression + Deal pipeline ── */}
      <div className="grid lg:grid-cols-2 gap-px bg-zinc-200 border hair">
        <TierProgression summary={summary} />
        <DealPipeline pipeline={summary.pipeline} />
      </div>

      {/* ── Row 3: Social intelligence card (Phyllo-ready) ── */}
      <SocialIntelligenceCard health={ch} />

      {/* ── Row 4: Deals ledger ── */}
      <section className="card-flat">
        <div className="p-6 border-b hair flex justify-between items-center">
          <div>
            <span className="label-xs">Recent activity</span>
            <h2 className="serif text-3xl tracking-tight mt-1">Deals ledger</h2>
          </div>
          <Link to="/deals" className="mono text-xs underline-ink">View all →</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="dense w-full">
            <thead>
              <tr>
                <th>Ref</th><th>Brand</th><th>Title</th><th>Status</th>
                <th className="num">Deal</th><th className="num">Advance</th>
                <th className="num">Fee</th><th className="num">Risk</th><th></th>
              </tr>
            </thead>
            <tbody data-testid="deals-table">
              {deals.length === 0 && (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-zinc-400 mono text-xs">
                    No deals yet. Upload your first contract to start.
                  </td>
                </tr>
              )}
              {deals.slice(0, 8).map(d => (
                <tr key={d.id} className="row-hover">
                  <td className="mono text-xs text-zinc-500">{d.id.slice(0, 8)}</td>
                  <td>{d.brand_name}</td>
                  <td className="max-w-xs truncate">{d.deal_title}</td>
                  <td><StatusChip status={d.status} /></td>
                  <td className="num">{money(d.deal_amount)}</td>
                  <td className="num">{money(d.advance_amount)}</td>
                  <td className="num">{money(d.discount_fee)}</td>
                  <td className="num">{d.risk ? d.risk.risk_score.toFixed(1) : "—"}</td>
                  <td>
                    <Link to={`/deals/${d.id}`} className="underline-ink mono text-xs">Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

// ── Credit tier progression ─────────────────────────────────────────────────

function TierProgression({ summary }) {
  const tierPath  = summary.tier_path  || [];
  const nextTier  = summary.next_tier  || {};
  const healthScore = summary.creator_health?.health_score || 0;

  return (
    <div className="bg-white p-8">
      <span className="label-xs">Credit tier progression</span>
      <h2 className="serif text-3xl tracking-tight mt-1">Your growth path.</h2>

      {/* Step indicators */}
      <div className="mt-8 space-y-0">
        {tierPath.map((tier, i) => (
          <div key={tier.key} className="flex items-stretch gap-4">
            {/* Spine */}
            <div className="flex flex-col items-center w-5 shrink-0">
              <div className={`w-4 h-4 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center
                ${tier.active ? "bg-zinc-950 border-zinc-950"
                  : tier.achieved ? "bg-zinc-300 border-zinc-300"
                  : "bg-white border-zinc-200"}`}>
                {tier.active && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
              {i < tierPath.length - 1 && (
                <div className={`w-px flex-1 mt-1 mb-1 ${tier.achieved ? "bg-zinc-300" : "bg-zinc-100"}`} />
              )}
            </div>

            {/* Content */}
            <div className={`pb-5 flex-1 flex items-start justify-between
              ${tier.active ? "" : "opacity-60"}`}>
              <div>
                <div className={`text-sm font-medium ${tier.active ? "text-zinc-950" : "text-zinc-600"}`}>
                  {tier.label}
                </div>
                <div className="mono text-xs text-zinc-400 mt-0.5">{tier.display}</div>
              </div>
              {tier.active && (
                <span className="chip chip-brand text-xs ml-4 shrink-0">Current</span>
              )}
              {tier.achieved && !tier.active && (
                <CheckCircle2 className="w-4 h-4 text-zinc-400 ml-4 shrink-0 mt-0.5" />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Progress to next tier */}
      {nextTier && nextTier.limit && (
        <div className="mt-6 border-t hair pt-6">
          <div className="flex justify-between items-baseline mb-2">
            <span className="label-xs">Progress to {nextTier.label}</span>
            <span className="mono text-xs text-zinc-500">
              {Number(healthScore).toFixed(1)} / {nextTier.health_needed}
            </span>
          </div>
          <div className="h-1 bg-zinc-100">
            <div
              className="h-1 bg-zinc-950 transition-all"
              style={{ width: `${nextTier.progress_pct || 0}%` }}
            />
          </div>

          {/* Actionable hints */}
          {nextTier.hints?.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="label-xs text-zinc-500">Fastest paths to {nextTier.label}:</div>
              {nextTier.hints.map(h => (
                <div key={h.metric} className="flex items-center gap-2 text-sm">
                  <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="text-zinc-600">
                    Grow {h.label} to{" "}
                    <span className="mono text-zinc-950 font-medium">{h.formatted}</span>
                    <span className="text-zinc-400 mono text-xs ml-2">
                      (now {h.metric === "followers" ? compact(h.current) : pct(h.current, 1)})
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!nextTier?.limit && (
        <div className="mt-6 border-t hair pt-4 flex items-center gap-2 text-sm text-zinc-500">
          <Zap className="w-4 h-4" />
          Maximum tier reached. Elite status unlocked.
        </div>
      )}
    </div>
  );
}

// ── Deal pipeline ───────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { key: "uploaded",         label: "Uploaded",        desc: "Pending underwriting" },
  { key: "scored",           label: "Scored",          desc: "Offer ready to accept" },
  { key: "disbursed",        label: "Disbursed",       desc: "Funds wired" },
  { key: "awaiting_payment", label: "Awaiting",        desc: "Brand to settle" },
  { key: "repaid",           label: "Repaid",          desc: "Credit recycled" },
];

function DealPipeline({ pipeline = {} }) {
  const total = PIPELINE_STAGES.reduce((s, st) => s + (pipeline[st.key]?.count || 0), 0);
  const active = PIPELINE_STAGES.filter(s => (pipeline[s.key]?.count || 0) > 0);

  return (
    <div className="bg-white p-8">
      <span className="label-xs">Deal pipeline</span>
      <h2 className="serif text-3xl tracking-tight mt-1">Live flow.</h2>

      <div className="mt-8 space-y-3">
        {PIPELINE_STAGES.map((stage, i) => {
          const data  = pipeline[stage.key] || { count: 0, value: 0 };
          const hasDeals = data.count > 0;
          const widthPct = total > 0 ? Math.max(4, (data.count / Math.max(total, 1)) * 100) : 4;

          return (
            <div key={stage.key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`mono text-xs ${hasDeals ? "text-zinc-950 font-medium" : "text-zinc-400"}`}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className={`text-sm ${hasDeals ? "text-zinc-950" : "text-zinc-400"}`}>
                    {stage.label}
                  </span>
                </div>
                <div className="flex items-center gap-4 mono text-xs">
                  {hasDeals ? (
                    <>
                      <span className="text-zinc-500">{data.count} deal{data.count !== 1 ? "s" : ""}</span>
                      <span className="text-zinc-950 font-medium">{money(data.value)}</span>
                    </>
                  ) : (
                    <span className="text-zinc-300">—</span>
                  )}
                </div>
              </div>
              <div className="h-0.5 bg-zinc-100">
                <div
                  className={`h-0.5 transition-all ${hasDeals ? "bg-zinc-950" : "bg-zinc-100"}`}
                  style={{ width: hasDeals ? `${widthPct}%` : "0%" }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {total === 0 && (
        <div className="mt-8 text-center">
          <div className="serif text-2xl text-zinc-300">No deals yet.</div>
          <Link to="/deals/new" className="mono text-xs underline-ink text-zinc-500 mt-2 block">
            Submit your first contract →
          </Link>
        </div>
      )}

      {total > 0 && (
        <div className="mt-8 pt-4 border-t hair">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="label-xs">Total pipeline value</div>
              <div className="serif text-2xl mt-1">
                {money(PIPELINE_STAGES.reduce((s, st) => s + (pipeline[st.key]?.value || 0), 0))}
              </div>
            </div>
            <div>
              <div className="label-xs">Active deals</div>
              <div className="serif text-2xl mt-1">{total}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Social intelligence card (Phyllo-ready) ─────────────────────────────────

function SocialIntelligenceCard({ health }) {
  const connected = health.social_connected;

  return (
    <section className="card-flat" data-testid="social-intel-card">
      <div className="p-6 border-b hair flex items-center justify-between">
        <div>
          <span className="label-xs">Creator Intelligence · Social Graph</span>
          <h2 className="serif text-3xl tracking-tight mt-1">Your audience metrics.</h2>
        </div>
        <div className="flex items-center gap-3">
          {connected ? (
            <span className="chip chip-ok flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
              Live · Syncing
            </span>
          ) : (
            <span className="chip chip-warn">Manual · Connect Phyllo for live data</span>
          )}
          <Link to="/profile" className="btn-ghost text-xs px-3 py-2">
            {connected ? "View sync" : "Connect accounts →"}
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-px bg-zinc-200">
        <MetricCell
          label="Followers"
          value={compact(health.followers || 0)}
          sub={health.platform || "instagram"}
          icon={<Instagram className="w-4 h-4" />}
          live={connected}
        />
        <MetricCell
          label="Engagement Rate"
          value={pct(health.engagement_rate || 0, 2)}
          sub={Number(health.engagement_rate || 0) >= 3 ? "Above benchmark" : "Below 3% benchmark"}
          quality={Number(health.engagement_rate || 0) >= 3 ? "good" : "warn"}
          live={connected}
        />
        <MetricCell
          label="Authenticity Score"
          value={Number(health.authenticity_score || 0).toFixed(0)}
          sub={Number(health.authenticity_score || 0) >= 70 ? "Low bot risk" : "Review followers"}
          quality={Number(health.authenticity_score || 0) >= 70 ? "good" : "warn"}
          live={connected}
        />
        <MetricCell
          label="Health Index"
          value={Number(health.health_score || 0).toFixed(1)}
          sub="/ 100 composite"
          live={connected}
        />
      </div>

      {!connected && (
        <div className="p-5 bg-zinc-50 border-t hair flex items-start gap-4">
          <div className="w-8 h-8 border hair flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-medium">Connect via Phyllo for live metrics</div>
            <p className="text-sm text-zinc-500 mt-1 leading-relaxed max-w-2xl">
              Real-time follower counts, post-level engagement, audience demographics, and
              authenticity scoring — pulled daily from Instagram, TikTok, YouTube, and X.
              Your credit limit recalculates automatically as your following grows.{" "}
              <span className="text-zinc-400 mono text-xs">
                · Integration pending API key configuration
              </span>
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function MetricCell({ label, value, sub, icon, live, quality }) {
  return (
    <div className="bg-white p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="label-xs flex items-center gap-1.5">
          {icon}
          {label}
        </div>
        {live && <div className="w-1.5 h-1.5 rounded-full bg-green-500" title="Live data" />}
      </div>
      <div className="serif text-3xl">{value}</div>
      <div className={`mono text-xs mt-1 ${
        quality === "good" ? "text-green-600"
        : quality === "warn" ? "text-amber-600"
        : "text-zinc-400"
      }`}>{sub}</div>
    </div>
  );
}

// ── Shared helpers ──────────────────────────────────────────────────────────

function Mini({ label, value, icon }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-zinc-500">{icon}<span className="label-xs">{label}</span></div>
      <div className="mono text-lg mt-1">{value}</div>
    </div>
  );
}

export function StatusChip({ status }) {
  const m = {
    uploaded:         ["chip",           "Uploaded"],
    scored:           ["chip chip-brand","Scored"],
    disbursed:        ["chip chip-ok",   "Disbursed"],
    awaiting_payment: ["chip chip-warn", "Awaiting Payment"],
    repaid:           ["chip chip-ok",   "Repaid"],
    rejected:         ["chip chip-bad",  "Rejected"],
  };
  const [c, l] = m[status] || ["chip", status];
  return <span className={c}>{l}</span>;
}
