import React, { useEffect, useState } from "react";
import { api, pct, compact, money } from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Instagram, Youtube, Twitter, Music2, Link2, Clock, TrendingUp, Landmark, Smartphone, CheckCircle2 } from "lucide-react";

export default function Profile() {
  const { user } = useAuth();
  const [form, setForm] = useState({ handle: "", platform: "instagram", followers: 0, engagement_rate: 0, authenticity_score: 0 });
  const [loading, setLoading] = useState(false);
  const [connectStatus, setConnectStatus] = useState(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [creditPreview, setCreditPreview] = useState(null);
  const [summary, setSummary] = useState(null);

  // Payout method state
  const [payoutTab, setPayoutTab] = useState("upi"); // "upi" | "bank"
  const [payoutForm, setPayoutForm] = useState({ upi_id: "", account_name: "", account_number: "", ifsc: "", bank_name: "" });
  const [savedPayout, setSavedPayout] = useState(null); // masked version from API
  const [payoutLoading, setPayoutLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/creator/profile"),
      api.get("/dashboard/summary"),
      api.get("/creator/payout-method"),
    ]).then(([profile, dash, payout]) => {
      const r = profile.data;
      if (r) {
        setForm({
          handle: r.handle || "",
          platform: r.platform || "instagram",
          followers: r.followers || 0,
          engagement_rate: r.engagement_rate || 0,
          authenticity_score: r.authenticity_score || 0,
        });
        if (r.provider_connected_requested) {
          setConnectStatus({ status: "pending_meta_review", at: r.provider_connected_requested_at });
        }
      }
      setSummary(dash.data);
      if (payout.data?.registered) {
        setSavedPayout(payout.data);
        setPayoutTab(payout.data.method_type || "upi");
      }
    });
  }, []);

  // Live credit limit preview as user types metrics
  const previewCredit = (updated) => {
    const f = Number(updated.followers || 0);
    const e = Number(updated.engagement_rate || 0);
    const a = Number(updated.authenticity_score || 0);
    if (f === 0 && e === 0 && a === 0) { setCreditPreview(null); return; }
    // Mirror the backend formula client-side for instant feedback
    const fScore = f <= 0 ? 0 : Math.min(100, (Math.log10(Math.max(f, 1)) / Math.log10(5_000_000)) * 100);
    const eScore = Math.min(100, (e / 6.0) * 100);
    const aScore = Math.min(100, Math.max(0, a));
    const health = (0.40 * fScore) + (0.35 * eScore) + (0.25 * aScore);
    const tiers = [
      [85, 2_500_000, "Elite · ₹25L"],
      [70, 1_000_000, "Premium · ₹10L"],
      [50, 400_000,   "Growth · ₹4L"],
      [30, 150_000,   "Rising · ₹1.5L"],
      [0,  50_000,    "Starter · ₹50K"],
    ];
    const [, limit, tier] = tiers.find(([t]) => health >= t) || tiers[tiers.length - 1];
    setCreditPreview({ health: health.toFixed(1), limit, tier });
  };

  const save = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await api.patch("/creator/profile", {
        ...form,
        followers: Number(form.followers),
        engagement_rate: Number(form.engagement_rate),
        authenticity_score: Number(form.authenticity_score),
      });
      if (r.data?.credit_limit) {
        toast.success(`Profile updated · credit limit set to ${money(r.data.credit_limit)}`);
        // Refresh dashboard summary
        api.get("/dashboard/summary").then(d => setSummary(d.data));
      } else {
        toast.success("Profile updated.");
      }
      setCreditPreview(null);
    } catch (e) { toast.error("Update failed"); }
    finally { setLoading(false); }
  };

  const savePayout = async (e) => {
    e.preventDefault();
    setPayoutLoading(true);
    try {
      const payload = payoutTab === "upi"
        ? { method_type: "upi", upi_id: payoutForm.upi_id }
        : {
            method_type: "bank",
            account_name: payoutForm.account_name,
            account_number: payoutForm.account_number,
            ifsc: payoutForm.ifsc.toUpperCase(),
            bank_name: payoutForm.bank_name,
          };
      await api.patch("/creator/payout-method", payload);
      // Refetch masked version
      const r = await api.get("/creator/payout-method");
      setSavedPayout(r.data);
      toast.success("Payout method saved. Advances will be sent here.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not save payout method.");
    } finally { setPayoutLoading(false); }
  };

  const connectSocial = async (platform) => {
    setConnectLoading(true);
    try {
      const r = await api.post("/creator/social/connect", { platform });
      toast.info(r.data.message, { duration: 7000 });
      setConnectStatus({ status: r.data.status, at: new Date().toISOString() });
    } catch (e) {
      toast.error("Could not queue connection");
    } finally { setConnectLoading(false); }
  };

  const PLATFORMS = [
    { k: "instagram", label: "Instagram", icon: Instagram },
    { k: "tiktok", label: "TikTok", icon: Music2 },
    { k: "youtube", label: "YouTube", icon: Youtube },
    { k: "x", label: "X / Twitter", icon: Twitter },
  ];

  return (
    <div data-testid="profile-root" className="max-w-4xl">
      <span className="label-xs">Creator Profile · Metrics</span>
      <h1 className="serif text-5xl tracking-tight mt-2">{user?.name}</h1>
      <div className="mono text-sm text-zinc-500 mt-1">{user?.email}</div>

      {/* Social Connection Panel */}
      <section className="card-flat mt-10 p-8" data-testid="social-connect-panel">
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="label-xs">Social Graph · Live Metrics</span>
            <h2 className="serif text-3xl mt-1">Connect your accounts</h2>
          </div>
          {connectStatus && (
            <span className="chip chip-warn" data-testid="connect-status-chip">
              <Clock className="w-3 h-3" /> Pending Meta review
            </span>
          )}
        </div>

        <p className="text-sm text-zinc-600 max-w-xl leading-relaxed">
          We pull live follower / engagement / authenticity data via the Meta Graph API and TikTok Business
          to replace synthetic scoring with real metrics. Integration is pending Meta developer-app review —
          tap <span className="mono">Connect</span> to queue your account; we&apos;ll auto-sync once approved.
        </p>

        <div className="grid md:grid-cols-4 gap-px bg-zinc-200 border hair mt-6">
          {PLATFORMS.map(({ k, label, icon: Icon }) => (
            <button
              key={k}
              data-testid={`connect-${k}`}
              type="button"
              onClick={() => connectSocial(k)}
              disabled={connectLoading}
              className="bg-white p-5 text-left hover:bg-zinc-50 transition-colors flex flex-col gap-3 group"
            >
              <Icon className="w-5 h-5 text-zinc-700" />
              <div>
                <div className="serif text-xl">{label}</div>
                <div className="mono text-xs text-zinc-500 mt-1 flex items-center gap-1">
                  <Link2 className="w-3 h-3" /> Queue connection
                </div>
              </div>
            </button>
          ))}
        </div>

        {connectStatus && (
          <div className="mono text-xs text-zinc-600 border-l-2 border-yellow-500 pl-4 mt-6" data-testid="connect-status-note">
            Queued {connectStatus.at && new Date(connectStatus.at).toLocaleString()}. Meta review
            typically takes 5-10 business days. Synthetic scoring remains active meanwhile.
          </div>
        )}
      </section>

      {/* Current credit limit panel */}
      {summary && (
        <section className="grid grid-cols-3 gap-px bg-zinc-200 border hair mt-10">
          <div className="bg-white p-6">
            <div className="label-xs">Current Credit Limit</div>
            <div className="serif text-4xl tracking-tight mt-2">{money(summary.credit_limit)}</div>
            <div className="mono text-xs text-zinc-400 mt-1">{summary.credit_tier}</div>
          </div>
          <div className="bg-white p-6">
            <div className="label-xs">Available</div>
            <div className="serif text-4xl tracking-tight mt-2">{money(summary.available)}</div>
            <div className="mono text-xs text-zinc-400 mt-1">Used {pct(summary.used_pct)}</div>
          </div>
          <div className="bg-white p-6">
            <div className="label-xs">Creator Health Score</div>
            <div className="serif text-4xl tracking-tight mt-2">
              {Number(summary.creator_health?.health_score || 0).toFixed(1)}
            </div>
            <div className="mono text-xs text-zinc-400 mt-1">/ 100 · updates on save</div>
          </div>
        </section>
      )}

      <form onSubmit={save} className="mt-12 space-y-8" data-testid="profile-form">
        <div className="flex items-end justify-between">
          <div>
            <span className="label-xs">Manual override · live metrics</span>
            <h2 className="serif text-3xl mt-1">Social metrics</h2>
          </div>
          {creditPreview && (
            <div className="text-right border hair px-5 py-3 bg-zinc-50">
              <div className="label-xs flex items-center gap-1.5 justify-end">
                <TrendingUp className="w-3 h-3" /> Credit preview
              </div>
              <div className="serif text-2xl mt-1">{money(creditPreview.limit)}</div>
              <div className="mono text-xs text-zinc-500">{creditPreview.tier} · score {creditPreview.health}</div>
            </div>
          )}
        </div>
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <label className="label-xs">Handle</label>
            <input data-testid="profile-handle" value={form.handle} onChange={e => setForm({ ...form, handle: e.target.value })} className="input-hair mt-1" placeholder="@yourhandle" />
          </div>
          <div>
            <label className="label-xs">Platform</label>
            <select data-testid="profile-platform" value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })} className="input-hair mt-1">
              {["instagram", "tiktok", "youtube", "x"].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="label-xs">Followers</label>
            <input
              data-testid="profile-followers"
              type="number"
              value={form.followers}
              onChange={e => {
                const updated = { ...form, followers: e.target.value };
                setForm(updated);
                previewCredit(updated);
              }}
              className="input-hair mt-1"
            />
            <div className="mono text-xs text-zinc-400 mt-1">{compact(Number(form.followers))}</div>
          </div>
          <div>
            <label className="label-xs">Engagement Rate (%)</label>
            <input
              data-testid="profile-er"
              type="number"
              step="0.1"
              value={form.engagement_rate}
              onChange={e => {
                const updated = { ...form, engagement_rate: e.target.value };
                setForm(updated);
                previewCredit(updated);
              }}
              className="input-hair mt-1"
            />
            <div className="mono text-xs text-zinc-400 mt-1">{pct(Number(form.engagement_rate), 2)}</div>
          </div>
          <div className="md:col-span-2">
            <label className="label-xs">Authenticity Score (0–100)</label>
            <input
              data-testid="profile-auth"
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={form.authenticity_score}
              onChange={e => {
                const updated = { ...form, authenticity_score: e.target.value };
                setForm(updated);
                previewCredit(updated);
              }}
              className="input-hair mt-1"
            />
            <div className="mono text-xs text-zinc-400 mt-1">
              Higher authenticity = fewer bot followers = higher limit
            </div>
          </div>
        </div>
        <button data-testid="profile-save" type="submit" disabled={loading} className="btn-primary">
          {loading ? "Saving…" : "Save & recompute credit limit"}
        </button>
      </form>

      {/* Payout Method */}
      <section className="card-flat mt-12 p-8" data-testid="payout-method-section">
        <div className="flex items-start justify-between mb-6">
          <div>
            <span className="label-xs">Payouts · Disbursement Account</span>
            <h2 className="serif text-3xl mt-1">Where we send your advance</h2>
            <p className="text-sm text-zinc-500 mt-1 max-w-lg">
              When you accept a deal offer, Athanni sends the advance directly to this account. Add your UPI ID or bank account below.
            </p>
          </div>
          {savedPayout?.registered && (
            <span className="chip chip-ok flex items-center gap-1.5">
              <CheckCircle2 className="w-3 h-3" /> Registered
            </span>
          )}
        </div>

        {savedPayout?.registered && (
          <div className="card-flat p-5 mb-6 bg-zinc-50 mono text-xs space-y-1.5">
            <div className="label-xs mb-2">Current payout method</div>
            {savedPayout.method_type === "upi" ? (
              <div className="flex items-center gap-2">
                <Smartphone className="w-3.5 h-3.5 text-zinc-600" />
                <span>UPI · {savedPayout.upi_id}</span>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <Landmark className="w-3.5 h-3.5 text-zinc-600" />
                  <span>{savedPayout.bank_name} · {savedPayout.account_number}</span>
                </div>
                <div className="text-zinc-500">IFSC {savedPayout.ifsc} · {savedPayout.account_name}</div>
              </>
            )}
          </div>
        )}

        {/* Method tabs */}
        <div className="flex border-b hair mb-6">
          {[["upi", "UPI", Smartphone], ["bank", "Bank Account", Landmark]].map(([k, label, Icon]) => (
            <button
              key={k}
              type="button"
              onClick={() => setPayoutTab(k)}
              className={`flex items-center gap-2 px-5 py-3 mono text-xs border-b-2 transition-colors ${
                payoutTab === k ? "border-zinc-950 text-zinc-950" : "border-transparent text-zinc-400 hover:text-zinc-700"
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        <form onSubmit={savePayout} className="space-y-6">
          {payoutTab === "upi" ? (
            <div>
              <label className="label-xs">UPI ID</label>
              <input
                data-testid="payout-upi-id"
                value={payoutForm.upi_id}
                onChange={e => setPayoutForm({ ...payoutForm, upi_id: e.target.value })}
                className="input-hair mt-1"
                placeholder="yourname@okaxis"
                required={payoutTab === "upi"}
              />
              <div className="mono text-xs text-zinc-400 mt-1">Any UPI-enabled bank app — Paytm, PhonePe, Google Pay, BHIM</div>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="label-xs">Account Holder Name</label>
                <input
                  data-testid="payout-account-name"
                  value={payoutForm.account_name}
                  onChange={e => setPayoutForm({ ...payoutForm, account_name: e.target.value })}
                  className="input-hair mt-1"
                  placeholder="Exactly as on bank account"
                  required={payoutTab === "bank"}
                />
              </div>
              <div>
                <label className="label-xs">Account Number</label>
                <input
                  data-testid="payout-account-number"
                  value={payoutForm.account_number}
                  onChange={e => setPayoutForm({ ...payoutForm, account_number: e.target.value })}
                  className="input-hair mt-1"
                  placeholder="XXXXXXXXXXXX"
                  required={payoutTab === "bank"}
                />
              </div>
              <div>
                <label className="label-xs">IFSC Code</label>
                <input
                  data-testid="payout-ifsc"
                  value={payoutForm.ifsc}
                  onChange={e => setPayoutForm({ ...payoutForm, ifsc: e.target.value.toUpperCase() })}
                  className="input-hair mt-1 font-mono"
                  placeholder="HDFC0001234"
                  maxLength={11}
                  required={payoutTab === "bank"}
                />
              </div>
              <div>
                <label className="label-xs">Bank Name</label>
                <input
                  data-testid="payout-bank-name"
                  value={payoutForm.bank_name}
                  onChange={e => setPayoutForm({ ...payoutForm, bank_name: e.target.value })}
                  className="input-hair mt-1"
                  placeholder="HDFC Bank"
                />
              </div>
            </div>
          )}

          <button type="submit" disabled={payoutLoading} className="btn-primary">
            {payoutLoading ? "Saving…" : savedPayout?.registered ? "Update payout method" : "Register payout method"}
          </button>
        </form>
      </section>
    </div>
  );
}
