import React, { useEffect, useState } from "react";
import { api, money, pct } from "../lib/api";
import { toast } from "sonner";
import { StatusChip } from "./Dashboard";
import { Activity, Brain, Mail, RefreshCw, Copy, Check, Building2, Trash2, Users, ChevronDown } from "lucide-react";

export default function AdminPanel() {
  const [stats, setStats] = useState(null);
  const [deals, setDeals] = useState([]);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState(null);
  const [over, setOver] = useState({ advance_rate: "", discount_fee_rate: "", notes: "" });
  const [ml, setMl] = useState(null);
  const [drift, setDrift] = useState(null);
  const [emails, setEmails] = useState([]);
  const [retraining, setRetraining] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const [tab, setTab] = useState("portfolio");

  // Brands tab state
  const [brands, setBrands] = useState([]);
  const [tokens, setTokens] = useState([]);
  const [tokenForm, setTokenForm] = useState({ brand_name: "", notes: "" });
  const [creatingToken, setCreatingToken] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);

  // Creators tab state
  const [creators, setCreators] = useState([]);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  const [limitModal, setLimitModal] = useState(null);   // { creator } | null
  const [limitForm, setLimitForm] = useState({ amount: "", notes: "" });
  const [savingLimit, setSavingLimit] = useState(false);
  const [expandedCreator, setExpandedCreator] = useState(null);

  const load = () => {
    api.get("/admin/stats").then(r => setStats(r.data));
    api.get("/admin/deals" + (filter ? `?status=${filter}` : "")).then(r => setDeals(r.data));
    api.get("/ml/status").then(r => setMl(r.data)).catch(() => setMl(null));
    api.get("/admin/emails").then(r => setEmails(r.data)).catch(() => setEmails([]));
  };

  useEffect(load, [filter]);

  useEffect(() => {
    if (tab === "ml" && !drift) {
      api.get("/admin/ml/drift").then(r => setDrift(r.data)).catch(() => {});
    }
    if (tab === "brands") {
      api.get("/admin/brands").then(r => setBrands(r.data)).catch(() => {});
      api.get("/admin/brand-tokens").then(r => setTokens(r.data)).catch(() => {});
    }
    if (tab === "creators") {
      setCreatorsLoading(true);
      api.get("/admin/creators").then(r => setCreators(r.data)).catch(() => {}).finally(() => setCreatorsLoading(false));
    }
  }, [tab, drift]);

  const openLimitModal = (creator) => {
    setLimitModal(creator);
    setLimitForm({ amount: creator.credit_limit || "", notes: "" });
  };

  const submitLimit = async (e) => {
    e.preventDefault();
    setSavingLimit(true);
    try {
      await api.patch(`/admin/creators/${limitModal.id}/credit-limit`, {
        amount: Number(limitForm.amount),
        notes: limitForm.notes,
      });
      toast.success(`Credit limit set to ${money(Number(limitForm.amount))} for ${limitModal.name}`);
      setLimitModal(null);
      // Refresh creators list
      api.get("/admin/creators").then(r => setCreators(r.data)).catch(() => {});
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to set limit");
    } finally {
      setSavingLimit(false);
    }
  };

  const createToken = async (e) => {
    e.preventDefault();
    setCreatingToken(true);
    try {
      const r = await api.post("/admin/brand-tokens", tokenForm);
      setTokens(prev => [r.data, ...prev]);
      setTokenForm({ brand_name: "", notes: "" });
      toast.success(`Token generated for ${r.data.brand_name || "brand"}`);
    } catch { toast.error("Failed to generate token"); }
    finally { setCreatingToken(false); }
  };

  const copyToken = (token) => {
    navigator.clipboard.writeText(token);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
    toast.success("Token copied to clipboard");
  };

  const revokeToken = async (token) => {
    if (!window.confirm("Revoke this unused token?")) return;
    try {
      await api.delete(`/admin/brand-tokens/${token}`);
      setTokens(prev => prev.filter(t => t.token !== token));
      toast.success("Token revoked.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to revoke"); }
  };

  const retrain = async () => {
    setRetraining(true);
    try {
      const r = await api.post("/admin/ml/retrain");
      toast.success(`Retrained · AUC ${r.data.report.roc_auc.toFixed(3)} · ${r.data.report.n_production} production rows`);
      setMl({ available: true, ...r.data.report });
      setDrift(null);
    } catch (e) { toast.error("Retrain failed"); }
    finally { setRetraining(false); }
  };

  const runMaturitySweep = async () => {
    setSweeping(true);
    try {
      const r = await api.post("/admin/maturity-sweep");
      toast.success(`${r.data.reminders_sent} maturity reminders queued.`);
      api.get("/admin/emails").then(r => setEmails(r.data)).catch(() => {});
    } catch (e) { toast.error("Sweep failed"); }
    finally { setSweeping(false); }
  };

  const openOverride = (d) => {
    setEditing(d);
    setOver({
      advance_rate: d.risk?.advance_rate || 80,
      discount_fee_rate: d.risk?.discount_fee_rate || 5,
      notes: "",
    });
  };

  const submitOverride = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/admin/deals/${editing.id}/override`, {
        advance_rate: Number(over.advance_rate),
        discount_fee_rate: Number(over.discount_fee_rate),
        notes: over.notes,
      });
      toast.success("Override applied.");
      setEditing(null);
      load();
    } catch (e) { toast.error("Override failed"); }
  };

  const markRepaid = async (d) => {
    if (!window.confirm(`Mark ${d.brand_name} · ${d.deal_title} as REPAID? This will recycle ${money(d.advance_amount)} of credit.`)) return;
    try {
      await api.post(`/admin/deals/${d.id}/mark-repaid`);
      toast.success("Marked repaid · credit recycled.");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const markDefault = async (d) => {
    if (!window.confirm(`Flag ${d.brand_name} · ${d.deal_title} as DEFAULTED? This labels it for ML retraining.`)) return;
    try {
      await api.post(`/admin/deals/${d.id}/mark-default`);
      toast.success("Flagged for training data.");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (!stats) return <div className="mono text-sm">Loading…</div>;

  return (
    <div data-testid="admin-root">
      <span className="label-xs">Risk Operations · Portfolio Control Room</span>
      <h1 className="serif text-5xl tracking-tight mt-2">Underwriting desk.</h1>

      {/* Tabs */}
      <div className="flex gap-1 mt-8 border-b hair">
        {[
          { k: "portfolio", l: "Portfolio" },
          { k: "creators", l: "Creators" },
          { k: "brands", l: "Brands" },
          { k: "ml", l: "ML Ops" },
          { k: "emails", l: "Notifications" },
        ].map(t => (
          <button
            key={t.k}
            data-testid={`admin-tab-${t.k}`}
            onClick={() => setTab(t.k)}
            className={`px-5 py-3 text-sm transition-colors ${tab === t.k ? "border-b-2 border-zinc-950 -mb-px text-zinc-950 font-medium" : "text-zinc-500 hover:text-zinc-800"}`}
          >
            {t.l}
          </button>
        ))}
      </div>

      {tab === "portfolio" && (<>
      {/* Portfolio stats */}
      <section className="grid md:grid-cols-4 gap-px bg-zinc-200 border hair mt-10 mb-10">
        <Stat label="Total Deals" v={stats.total_deals} />
        <Stat label="Disbursed" v={stats.disbursed_deals} />
        <Stat label="Volume Underwritten" v={money(stats.total_volume)} />
        <Stat label="Fees Collected" v={money(stats.total_fees)} />
      </section>

      {/* ML status card */}
      {ml?.available && (
        <section className="card-flat p-6 mb-10 flex items-center justify-between" data-testid="ml-status-card">
          <div>
            <span className="label-xs">Default-Rate Model · Synthetic Pipeline</span>
            <div className="serif text-2xl mt-1">Logistic Regression · {ml.n_train.toLocaleString()} training samples</div>
          </div>
          <div className="flex gap-6">
            <div className="text-right">
              <div className="label-xs">Observed default rate</div>
              <div className="mono text-lg">{(ml.default_rate * 100).toFixed(1)}%</div>
            </div>
            <div className="text-right">
              <div className="label-xs">ROC-AUC</div>
              <div className="mono text-lg">{ml.roc_auc.toFixed(3)}</div>
            </div>
          </div>
        </section>
      )}

      {/* Tier breakdown */}
      {stats.by_tier?.length > 0 && (
        <section className="card-flat p-8 mb-10" data-testid="tier-breakdown">
          <span className="label-xs">Portfolio by brand tier</span>
          <div className="grid grid-cols-4 gap-px bg-zinc-200 border hair mt-4">
            {stats.by_tier.map(t => (
              <div key={t.tier} className="bg-white p-5">
                <div className="label-xs">{t.tier}</div>
                <div className="serif text-3xl mt-1">{t.count}</div>
                <div className="mono text-xs text-zinc-500">{money(t.volume)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {["", "uploaded", "scored", "disbursed"].map(s => (
          <button key={s || "all"} data-testid={`admin-filter-${s || "all"}`} onClick={() => setFilter(s)}
            className={`chip cursor-pointer ${filter === s ? "border-zinc-950 text-zinc-950" : "text-zinc-500"}`}>
            {s || "all"}
          </button>
        ))}
      </div>

      <div className="card-flat overflow-x-auto">
        <table className="dense w-full">
          <thead>
            <tr>
              <th>Ref</th>
              <th>Creator</th>
              <th>Brand</th>
              <th>Title</th>
              <th>Status</th>
              <th className="num">Deal</th>
              <th className="num">Advance</th>
              <th className="num">Risk</th>
              <th></th>
            </tr>
          </thead>
          <tbody data-testid="admin-deals-table">
            {deals.map(d => (
              <tr key={d.id} className="row-hover">
                <td className="mono text-xs text-zinc-500">{d.id.slice(0,8)}</td>
                <td className="mono text-xs">{d.user_id.slice(0,6)}</td>
                <td>{d.brand_name}</td>
                <td className="max-w-xs truncate">{d.deal_title}</td>
                <td><StatusChip status={d.status} /></td>
                <td className="num">{money(d.deal_amount)}</td>
                <td className="num">{money(d.advance_amount)}</td>
                <td className="num">{d.risk ? d.risk.risk_score.toFixed(1) : "—"}</td>
                <td>
                  <div className="flex gap-3">
                    <button data-testid={`override-${d.id}`} onClick={() => openOverride(d)} className="underline-ink mono text-xs">Override</button>
                    {(d.status === "disbursed" || d.status === "awaiting_payment") && (
                      <button data-testid={`mark-repaid-${d.id}`} onClick={() => markRepaid(d)} className="underline-ink mono text-xs text-green-700">Mark Repaid</button>
                    )}
                    {(d.status === "disbursed" || d.status === "awaiting_payment") && (
                      <button data-testid={`mark-default-${d.id}`} onClick={() => markDefault(d)} className="underline-ink mono text-xs text-red-700">Flag Default</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {deals.length === 0 && <tr><td colSpan={9} className="text-center py-10 text-zinc-400 mono text-xs">No deals.</td></tr>}
          </tbody>
        </table>
      </div>
      </>)}

      {tab === "creators" && (
        <section className="mt-10 space-y-6" data-testid="admin-creators-tab">
          <div className="flex items-center justify-between">
            <div>
              <span className="label-xs">Creator Management · Phase 2</span>
              <h2 className="serif text-3xl mt-1 flex items-center gap-2">
                <Users className="w-5 h-5" /> All creators
              </h2>
              <div className="mono text-xs text-zinc-500 mt-1">{creators.length} registered</div>
            </div>
            <button
              onClick={() => { setCreatorsLoading(true); api.get("/admin/creators").then(r => setCreators(r.data)).catch(() => {}).finally(() => setCreatorsLoading(false)); }}
              className="btn-ghost text-sm flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${creatorsLoading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>

          {creatorsLoading && <div className="mono text-xs text-zinc-400 py-10 text-center">Loading creators…</div>}

          {!creatorsLoading && creators.length === 0 && (
            <div className="card-flat p-12 text-center">
              <div className="mono text-sm text-zinc-400">No creator accounts yet.</div>
              <div className="text-xs text-zinc-400 mt-1">Share the registration link to onboard creators.</div>
            </div>
          )}

          {!creatorsLoading && creators.length > 0 && (
            <div className="card-flat overflow-x-auto">
              <table className="dense w-full">
                <thead>
                  <tr>
                    <th></th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>KYC</th>
                    <th className="num">Credit Limit</th>
                    <th className="num">Used</th>
                    <th>Tier</th>
                    <th className="num">Score</th>
                    <th className="num">Deals</th>
                    <th>Registered</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {creators.map(c => (
                    <>
                      <tr key={c.id} className="row-hover">
                        <td>
                          <button
                            onClick={() => setExpandedCreator(expandedCreator === c.id ? null : c.id)}
                            className="text-zinc-400 hover:text-zinc-800"
                          >
                            <ChevronDown className={`w-4 h-4 transition-transform ${expandedCreator === c.id ? "rotate-180" : ""}`} />
                          </button>
                        </td>
                        <td className="font-medium">{c.name}</td>
                        <td className="mono text-xs text-zinc-500">{c.email || "—"}</td>
                        <td>
                          <span className={`chip ${c.kyc_status === "verified" ? "chip-ok" : c.kyc_status === "failed" ? "chip-bad" : "chip-warn"}`}>
                            {c.kyc_status}
                          </span>
                        </td>
                        <td className="num mono text-sm font-medium" style={{ color: "var(--accent)" }}>
                          {money(c.credit_limit)}
                        </td>
                        <td className="num mono text-xs text-zinc-500">{money(c.used_credit || 0)}</td>
                        <td>
                          <span className="chip chip-brand text-xs">{c.credit_tier || "Starter"}</span>
                        </td>
                        <td className="num mono text-xs">{c.creator_score ? c.creator_score.toFixed(1) : "—"}</td>
                        <td className="num mono text-xs">{c.total_deals}</td>
                        <td className="mono text-xs text-zinc-500">
                          {c.registered_at ? new Date(c.registered_at).toLocaleDateString("en-IN") : "—"}
                        </td>
                        <td>
                          <button
                            onClick={() => openLimitModal(c)}
                            className="btn-primary text-xs px-3 py-1 whitespace-nowrap"
                          >
                            Set Limit
                          </button>
                        </td>
                      </tr>
                      {expandedCreator === c.id && (
                        <tr key={`${c.id}-expand`} className="bg-zinc-50">
                          <td colSpan={11} className="px-8 py-5">
                            <div className="grid md:grid-cols-4 gap-6 text-sm">
                              <div>
                                <div className="label-xs mb-2">Social</div>
                                <div className="mono text-xs">{c.instagram_handle || "Not connected"}</div>
                                <div className="text-zinc-500 text-xs mt-1">{c.followers ? c.followers.toLocaleString("en-IN") + " followers" : "—"}</div>
                                <div className="text-zinc-500 text-xs">{c.engagement_rate ? c.engagement_rate.toFixed(1) + "% engagement" : "—"}</div>
                              </div>
                              <div>
                                <div className="label-xs mb-2">Deals by status</div>
                                {Object.entries(c.deal_counts || {}).length === 0
                                  ? <div className="mono text-xs text-zinc-400">No deals yet</div>
                                  : Object.entries(c.deal_counts).map(([s, n]) => (
                                      <div key={s} className="flex justify-between items-center mono text-xs py-0.5">
                                        <StatusChip status={s} />
                                        <span className="ml-2 text-zinc-500">{n}</span>
                                      </div>
                                    ))
                                }
                              </div>
                              <div>
                                <div className="label-xs mb-2">Credit limit audit</div>
                                {c.credit_limit_set_by ? (
                                  <>
                                    <div className="mono text-xs">Set by {c.credit_limit_set_by}</div>
                                    <div className="text-zinc-500 text-xs mt-1">{c.credit_limit_set_at ? new Date(c.credit_limit_set_at).toLocaleString("en-IN") : ""}</div>
                                    {c.credit_limit_notes && <div className="text-zinc-500 text-xs mt-1 italic">"{c.credit_limit_notes}"</div>}
                                  </>
                                ) : (
                                  <div className="mono text-xs text-zinc-400">Auto-computed from social score</div>
                                )}
                              </div>
                              <div>
                                <div className="label-xs mb-2">Payout</div>
                                <span className={`chip ${c.payout_registered ? "chip-ok" : "chip-warn"}`}>
                                  {c.payout_registered ? "registered" : "not set"}
                                </span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "brands" && (
        <section className="mt-10 space-y-10" data-testid="admin-brands-tab">

          {/* ── Token generation ─────────────────────────────────────── */}
          <div className="card-flat p-8">
            <span className="label-xs">Brand Access · Signup Tokens</span>
            <h2 className="serif text-3xl mt-1 flex items-center gap-2">
              <Building2 className="w-5 h-5" /> Issue brand invite
            </h2>
            <p className="text-sm text-zinc-500 mt-2 max-w-lg">
              Generate a one-time token for a brand to self-register.
              Copy the token and send it to the brand's contact — they'll need it to sign up at <span className="mono">/brand/register</span>.
            </p>

            <form onSubmit={createToken} className="mt-8 grid md:grid-cols-3 gap-4 items-end">
              <div>
                <label className="label-xs">Brand Name</label>
                <input
                  className="input-hair mt-1"
                  placeholder="e.g. Nykaa, boAt…"
                  value={tokenForm.brand_name}
                  onChange={e => setTokenForm({ ...tokenForm, brand_name: e.target.value })}
                />
              </div>
              <div>
                <label className="label-xs">Notes (optional)</label>
                <input
                  className="input-hair mt-1"
                  placeholder="e.g. referred via Akhi"
                  value={tokenForm.notes}
                  onChange={e => setTokenForm({ ...tokenForm, notes: e.target.value })}
                />
              </div>
              <button type="submit" disabled={creatingToken} className="btn-primary text-sm h-10">
                {creatingToken ? "Generating…" : "Generate token →"}
              </button>
            </form>
          </div>

          {/* ── Tokens list ──────────────────────────────────────────── */}
          <div>
            <span className="label-xs">Issued tokens · {tokens.length} total</span>
            <div className="card-flat overflow-x-auto mt-3">
              <table className="dense w-full">
                <thead>
                  <tr>
                    <th>Brand</th>
                    <th>Token</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Notes</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tokens.length === 0 && (
                    <tr><td colSpan={6} className="text-center py-10 text-zinc-400 mono text-xs">No tokens issued yet.</td></tr>
                  )}
                  {tokens.map(t => (
                    <tr key={t.token} className="row-hover">
                      <td className="font-medium">{t.brand_name || <span className="text-zinc-400">—</span>}</td>
                      <td className="mono text-xs text-zinc-500">{t.token.slice(0, 8)}…{t.token.slice(-4)}</td>
                      <td>
                        <span className={`chip ${t.used ? "chip-bad" : "chip-ok"}`}>
                          {t.used ? "used" : "pending"}
                        </span>
                      </td>
                      <td className="mono text-xs text-zinc-500">
                        {t.created_at ? new Date(t.created_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td className="text-sm text-zinc-500 max-w-xs truncate">{t.notes || "—"}</td>
                      <td>
                        <div className="flex gap-2">
                          {!t.used && (
                            <>
                              <button
                                onClick={() => copyToken(t.token)}
                                className="underline-ink mono text-xs flex items-center gap-1"
                                title="Copy full token"
                              >
                                {copiedToken === t.token
                                  ? <><Check className="w-3 h-3 text-green-600" /> copied</>
                                  : <><Copy className="w-3 h-3" /> copy</>
                                }
                              </button>
                              <button
                                onClick={() => revokeToken(t.token)}
                                className="underline-ink mono text-xs text-red-600 flex items-center gap-1"
                                title="Revoke token"
                              >
                                <Trash2 className="w-3 h-3" /> revoke
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Brands list ──────────────────────────────────────────── */}
          <div>
            <span className="label-xs">Registered brands · {brands.length} total</span>
            <div className="card-flat overflow-x-auto mt-3">
              <table className="dense w-full">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Industry</th>
                    <th>Tier</th>
                    <th>Credit Rating</th>
                    <th className="num">Solvency</th>
                    <th className="num">Deals</th>
                    <th>Verified</th>
                  </tr>
                </thead>
                <tbody>
                  {brands.length === 0 && (
                    <tr><td colSpan={7} className="text-center py-10 text-zinc-400 mono text-xs">No brands yet. Seed demo brands or register a brand account.</td></tr>
                  )}
                  {brands.map(b => (
                    <tr key={b.id} className="row-hover">
                      <td className="font-medium">{b.name}</td>
                      <td className="text-sm text-zinc-600">{b.industry || "—"}</td>
                      <td>{b.tier ? <span className="chip chip-brand">{b.tier}</span> : "—"}</td>
                      <td className="mono text-xs">{b.credit_rating || "—"}</td>
                      <td className="num mono text-xs">{b.solvency_score != null ? b.solvency_score.toFixed(1) : "—"}</td>
                      <td className="num mono text-xs">{b.deal_count ?? 0}</td>
                      <td>
                        <span className={`chip ${b.verified ? "chip-ok" : "chip-warn"}`}>
                          {b.verified ? "verified" : "pending"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {tab === "ml" && (
        <section data-testid="admin-ml-tab" className="mt-10 space-y-6">
          <div className="card-flat p-8">
            <div className="flex items-start justify-between">
              <div>
                <span className="label-xs">Active model</span>
                <h2 className="serif text-3xl mt-1 flex items-center gap-2"><Brain className="w-5 h-5" /> Default-rate classifier</h2>
              </div>
              <button data-testid="retrain-btn" onClick={retrain} disabled={retraining} className="btn-primary text-sm">
                <RefreshCw className={`w-4 h-4 ${retraining ? "animate-spin" : ""}`} />
                {retraining ? "Retraining…" : "Retrain on production"}
              </button>
            </div>
            {ml?.available && (
              <div className="grid md:grid-cols-4 gap-px bg-zinc-200 border hair mt-6">
                <MiniStat label="Training rows" v={ml.n_train?.toLocaleString?.() || ml.n_train} />
                <MiniStat label="Production rows" v={(ml.n_production ?? 0).toLocaleString?.() || 0} />
                <MiniStat label="ROC-AUC" v={ml.roc_auc?.toFixed?.(3) || ml.roc_auc} />
                <MiniStat label="Default rate" v={((ml.default_rate || 0) * 100).toFixed(1) + "%"} />
              </div>
            )}
          </div>

          {drift && (
            <div className="card-flat p-8" data-testid="drift-report">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="label-xs">Population Stability</span>
                  <h2 className="serif text-3xl mt-1 flex items-center gap-2"><Activity className="w-5 h-5" /> Drift monitor</h2>
                </div>
                <div className="text-right">
                  <div className="label-xs">Global PSI</div>
                  <div className="serif text-3xl">{drift.global_psi?.toFixed(3)}</div>
                  <span className={`chip mt-2 ${
                    drift.verdict === "stable" ? "chip-ok" :
                    drift.verdict === "watch" ? "chip-warn" : "chip-bad"
                  }`}>{drift.verdict}</span>
                </div>
              </div>
              <div className="mono text-xs text-zinc-600 border-l-2 border-zinc-400 pl-4 mb-4">
                {drift.message} · comparing {drift.n_production} production vs {drift.n_training} training rows.
              </div>
              {drift.features?.length > 0 && (
                <table className="dense w-full" data-testid="drift-features">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>PSI</th>
                      <th>Verdict</th>
                      <th className="num">Train mean</th>
                      <th className="num">Prod mean</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drift.features.map(f => (
                      <tr key={f.name}>
                        <td className="mono text-xs">{f.name}</td>
                        <td className="mono text-xs">{f.psi}</td>
                        <td>
                          <span className={`chip text-xs ${f.verdict === "stable" ? "chip-ok" : f.verdict === "watch" ? "chip-warn" : "chip-bad"}`}>{f.verdict}</span>
                        </td>
                        <td className="num">{f.training_mean}</td>
                        <td className="num">{f.production_mean}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          <div className="card-flat p-6 text-sm text-zinc-600">
            <div className="label-xs mb-2">How labelling works</div>
            <ul className="list-disc pl-5 space-y-1">
              <li>When a deal is marked <b>Repaid</b> (via webhook or Mark Repaid), it&apos;s labelled <span className="mono">default=0</span>.</li>
              <li>Use <b>Flag Default</b> on the portfolio tab to mark a defaulted deal as <span className="mono">default=1</span>.</li>
              <li>Click <b>Retrain on production</b> once you have ≥50 labelled production deals for reliable weighting.</li>
            </ul>
          </div>
        </section>
      )}

      {tab === "emails" && (
        <section data-testid="admin-emails-tab" className="mt-10 space-y-6">
          <div className="card-flat p-8">
            <div className="flex items-start justify-between">
              <div>
                <span className="label-xs">Notifications · Resend</span>
                <h2 className="serif text-3xl mt-1 flex items-center gap-2"><Mail className="w-5 h-5" /> Email log</h2>
                <div className="mono text-xs text-zinc-500 mt-1">Provider: {emails[0]?.provider || "mock"} · {emails.length} events</div>
              </div>
              <button data-testid="maturity-sweep-btn" onClick={runMaturitySweep} disabled={sweeping} className="btn-ghost text-sm">
                {sweeping ? "Scanning…" : "Run maturity sweep"}
              </button>
            </div>
            <div className="mono text-xs text-zinc-600 border-l-2 border-yellow-500 pl-4 mt-5 bg-yellow-50 py-2" data-testid="email-mock-note">
              RESEND_API_KEY is <b>not configured</b> — emails are MOCKED and persisted to the log only.
              Paste your Resend key into <span className="mono">/app/backend/.env</span> and restart to go live.
            </div>
          </div>

          <div className="card-flat overflow-x-auto">
            <table className="dense w-full">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>To</th>
                  <th>Template</th>
                  <th>Subject</th>
                  <th>Status</th>
                  <th>Provider</th>
                </tr>
              </thead>
              <tbody data-testid="email-log-table">
                {emails.length === 0 && <tr><td colSpan={6} className="text-center py-10 text-zinc-400 mono text-xs">No emails yet.</td></tr>}
                {emails.map(e => (
                  <tr key={e.id}>
                    <td className="mono text-xs text-zinc-500">{new Date(e.created_at).toLocaleString()}</td>
                    <td className="mono text-xs">{e.to}</td>
                    <td className="mono text-xs">{e.template}</td>
                    <td className="max-w-md truncate">{e.subject}</td>
                    <td>
                      <span className={`chip ${
                        e.status === "sent" ? "chip-ok" :
                        e.status === "mocked" ? "chip-warn" : e.status === "error" ? "chip-bad" : ""
                      }`}>{e.status}</span>
                    </td>
                    <td className="mono text-xs text-zinc-500">{e.provider}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Credit Limit Modal */}
      {limitModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setLimitModal(null)}>
          <div className="bg-white card-flat max-w-md w-full p-8" onClick={e => e.stopPropagation()}>
            <span className="label-xs">Admin · Credit Limit Override</span>
            <h2 className="serif text-3xl mt-2">{limitModal.name}</h2>
            <div className="mono text-xs text-zinc-500 mt-1">{limitModal.email}</div>

            <div className="grid grid-cols-2 gap-4 mt-6 mb-6 p-4 bg-zinc-50 border hair">
              <div>
                <div className="label-xs">Current limit</div>
                <div className="mono text-lg" style={{ color: "var(--accent)" }}>{money(limitModal.credit_limit)}</div>
              </div>
              <div>
                <div className="label-xs">Used</div>
                <div className="mono text-lg">{money(limitModal.used_credit || 0)}</div>
              </div>
              <div>
                <div className="label-xs">Tier</div>
                <div className="mono text-sm">{limitModal.credit_tier || "Starter"}</div>
              </div>
              <div>
                <div className="label-xs">AI Score</div>
                <div className="mono text-sm">{limitModal.creator_score ? limitModal.creator_score.toFixed(1) : "—"}</div>
              </div>
            </div>

            <form onSubmit={submitLimit} className="space-y-5">
              <div>
                <label className="label-xs">New Credit Limit (₹)</label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  className="input-hair mt-1"
                  placeholder="e.g. 500000"
                  value={limitForm.amount}
                  onChange={e => setLimitForm({ ...limitForm, amount: e.target.value })}
                  required
                  autoFocus
                />
                <div className="mono text-xs text-zinc-400 mt-1">
                  Quick: &nbsp;
                  {[50000, 150000, 400000, 1000000, 2500000].map(v => (
                    <button key={v} type="button" onClick={() => setLimitForm({ ...limitForm, amount: v })}
                      className="underline-ink mr-3">{money(v)}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="label-xs">Notes (optional)</label>
                <input
                  className="input-hair mt-1"
                  placeholder="e.g. verified Instagram metrics, 200K followers"
                  value={limitForm.notes}
                  onChange={e => setLimitForm({ ...limitForm, notes: e.target.value })}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setLimitModal(null)} className="btn-ghost text-sm">Cancel</button>
                <button type="submit" disabled={savingLimit} className="btn-primary text-sm">
                  {savingLimit ? "Saving…" : "Set limit →"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setEditing(null)}>
          <div className="bg-white card-flat max-w-lg w-full p-8" onClick={(e) => e.stopPropagation()} data-testid="override-modal">
            <span className="label-xs">Override · Risk Ops</span>
            <h2 className="serif text-3xl mt-2">{editing.deal_title}</h2>
            <div className="mono text-xs text-zinc-500">{editing.brand_name} · {money(editing.deal_amount)}</div>

            <form onSubmit={submitOverride} className="mt-8 space-y-6">
              <div>
                <label className="label-xs">Advance Rate (%)</label>
                <input data-testid="override-advance-rate" type="number" step="0.1" value={over.advance_rate} onChange={e => setOver({ ...over, advance_rate: e.target.value })} className="input-hair mt-1" required />
              </div>
              <div>
                <label className="label-xs">Discount Fee Rate (%)</label>
                <input data-testid="override-fee-rate" type="number" step="0.1" value={over.discount_fee_rate} onChange={e => setOver({ ...over, discount_fee_rate: e.target.value })} className="input-hair mt-1" required />
              </div>
              <div>
                <label className="label-xs">Underwriter Notes</label>
                <textarea data-testid="override-notes" rows={3} value={over.notes} onChange={e => setOver({ ...over, notes: e.target.value })} className="input-hair mt-1 resize-y" />
              </div>

              <div className="mono text-xs text-zinc-600 border-t hair pt-4">
                New Advance: {money((editing.deal_amount * Number(over.advance_rate || 0)) / 100)} · Fee: {money((editing.deal_amount * Number(over.discount_fee_rate || 0)) / 100)}
              </div>

              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setEditing(null)} className="btn-ghost text-sm">Cancel</button>
                <button data-testid="override-submit" type="submit" className="btn-primary text-sm">Apply override</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, v }) {
  return (
    <div className="bg-white p-8">
      <div className="label-xs">{label}</div>
      <div className="serif text-5xl mt-3 tracking-tight">{v}</div>
    </div>
  );
}

function MiniStat({ label, v }) {
  return (
    <div className="bg-white p-5">
      <div className="label-xs">{label}</div>
      <div className="serif text-2xl mt-2">{v}</div>
    </div>
  );
}
