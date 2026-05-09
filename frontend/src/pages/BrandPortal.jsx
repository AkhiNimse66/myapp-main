import React, { useEffect, useState } from "react";
import { api, money } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { AthanniLogo } from "../components/AthanniLogo";

// Status chip reused from the design system
function StatusChip({ status }) {
  const map = {
    uploaded:         "chip",
    scored:           "chip chip-warn",
    disbursed:        "chip chip-brand",
    awaiting_payment: "chip chip-warn",
    repaid:           "chip chip-ok",
    rejected:         "chip chip-bad",
  };
  return <span className={map[status] || "chip"}>{status?.replace("_", " ")}</span>;
}

export default function BrandPortal() {
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);        // { brand, deals }
  const [bankDetails, setBankDetails] = useState(null);
  const [confirming, setConfirming] = useState(null); // deal being confirmed
  const [utr, setUtr] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    api.get("/brands/my-deals")
      .then(r => setData(r.data))
      .catch(() => setData({ brand: null, deals: [] }));
    api.get("/deals/bank-details")
      .then(r => setBankDetails(r.data))
      .catch(() => {});
  };

  useEffect(load, []);

  const openConfirm = (deal) => {
    setConfirming(deal);
    setUtr("");
  };

  const submitPayment = async (e) => {
    e.preventDefault();
    if (!utr.trim()) { toast.error("UTR / reference number is required."); return; }
    setSubmitting(true);
    try {
      await api.post(`/deals/${confirming.id}/brand-confirm-payment`, { utr_number: utr });
      toast.success("Payment confirmation received. Athanni will verify and settle.");
      setConfirming(null);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to confirm payment.");
    } finally {
      setSubmitting(false);
    }
  };

  const brand   = data?.brand;
  const deals   = data?.deals || [];
  const open    = deals.filter(d => ["disbursed", "awaiting_payment"].includes(d.status));
  const settled = deals.filter(d => ["repaid", "rejected"].includes(d.status));

  if (!data) return <div className="p-12 mono text-sm text-zinc-400">Loading…</div>;

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* ── Header ────────────────────────────────────────────────── */}
      <header className="bg-white border-b hair px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AthanniLogo size="sm" dark={false} />
          <span className="mono text-xs text-zinc-400 ml-1">· Brand Portal</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="mono text-xs text-zinc-500">{user?.name}</span>
          <button onClick={logout} className="mono text-xs underline-ink text-zinc-500">Log out</button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-8 py-12">
        {/* ── Page title ──────────────────────────────────────────── */}
        <span className="label-xs">Brand Portal · Invoice Dashboard</span>
        <h1 className="serif text-5xl tracking-tight mt-2">
          {brand?.name || user?.name || "Brand account"}.
        </h1>
        {brand && (
          <div className="flex items-center gap-4 mt-3 flex-wrap">
            {brand.industry && <span className="chip">{brand.industry}</span>}
            {brand.company_type && <span className="chip">{brand.company_type}</span>}
            {brand.verified
              ? <span className="chip chip-ok">verified</span>
              : <span className="chip chip-warn">verification pending</span>
            }
          </div>
        )}

        {/* ── Summary stats ───────────────────────────────────────── */}
        <section className="grid md:grid-cols-3 gap-px bg-zinc-200 border hair mt-10 mb-10">
          <div className="bg-white p-8">
            <div className="label-xs">Open Invoices</div>
            <div className="serif text-5xl mt-3 tracking-tight">{open.length}</div>
          </div>
          <div className="bg-white p-8">
            <div className="label-xs">Total Outstanding</div>
            <div className="serif text-5xl mt-3 tracking-tight">
              {money(open.reduce((s, d) => s + (d.deal_amount || 0), 0))}
            </div>
          </div>
          <div className="bg-white p-8">
            <div className="label-xs">Total Deals</div>
            <div className="serif text-5xl mt-3 tracking-tight">{deals.length}</div>
          </div>
        </section>

        {/* ── Bank details callout ─────────────────────────────────── */}
        {bankDetails && open.length > 0 && (
          <section className="card-flat p-8 mb-10 bg-zinc-950 text-white">
            <span className="label-xs text-zinc-400">Settlement · Wire to Athanni</span>
            <div className="serif text-2xl mt-2 mb-6">Bank details for NEFT / RTGS / IMPS</div>
            <div className="grid md:grid-cols-2 gap-x-12 gap-y-3">
              {[
                ["Account Name",   bankDetails.account_name],
                ["Bank",           bankDetails.bank_name],
                ["Account Number", bankDetails.account_number],
                ["IFSC Code",      bankDetails.ifsc],
                ["Account Type",   bankDetails.account_type],
                ["UPI ID",         bankDetails.upi_id],
              ].map(([label, val]) => (
                <div key={label} className="flex items-baseline justify-between border-b border-zinc-800 pb-2">
                  <span className="label-xs text-zinc-500">{label}</span>
                  <span className="mono text-sm text-white">{val || "—"}</span>
                </div>
              ))}
            </div>
            <p className="mono text-xs text-zinc-500 mt-6">
              Wire the deal amount to the above account and click "Confirm payment" on the relevant invoice below.
              Quote the UTR/reference number when confirming.
            </p>
          </section>
        )}

        {/* ── Open invoices ────────────────────────────────────────── */}
        {open.length > 0 && (
          <section className="mb-10">
            <span className="label-xs">Open invoices requiring settlement</span>
            <div className="card-flat overflow-x-auto mt-3">
              <table className="dense w-full">
                <thead>
                  <tr>
                    <th>Deal</th>
                    <th>Status</th>
                    <th className="num">Amount</th>
                    <th>Maturity</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {open.map(d => (
                    <tr key={d.id} className="row-hover">
                      <td>
                        <div className="font-medium">{d.deal_title || "Untitled deal"}</div>
                        <div className="mono text-xs text-zinc-400">{d.id.slice(0, 8)}</div>
                      </td>
                      <td><StatusChip status={d.status} /></td>
                      <td className="num mono">{money(d.deal_amount)}</td>
                      <td className="mono text-xs text-zinc-500">
                        {d.maturity_date ? new Date(d.maturity_date).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td>
                        {d.status === "disbursed" ? (
                          <button
                            onClick={() => openConfirm(d)}
                            className="btn-primary text-xs py-2 px-4"
                          >
                            Confirm payment →
                          </button>
                        ) : d.status === "awaiting_payment" ? (
                          <span className="chip chip-warn mono text-xs">awaiting verification</span>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── Settled / history ───────────────────────────────────── */}
        {settled.length > 0 && (
          <section>
            <span className="label-xs text-zinc-400">Settled deals</span>
            <div className="card-flat overflow-x-auto mt-3">
              <table className="dense w-full">
                <thead>
                  <tr>
                    <th>Deal</th>
                    <th>Status</th>
                    <th className="num">Amount</th>
                    <th>Settled</th>
                  </tr>
                </thead>
                <tbody>
                  {settled.map(d => (
                    <tr key={d.id} className="row-hover opacity-70">
                      <td>
                        <div className="font-medium">{d.deal_title || "Untitled deal"}</div>
                        <div className="mono text-xs text-zinc-400">{d.id.slice(0, 8)}</div>
                      </td>
                      <td><StatusChip status={d.status} /></td>
                      <td className="num mono">{money(d.deal_amount)}</td>
                      <td className="mono text-xs text-zinc-500">
                        {d.repaid_at ? new Date(d.repaid_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── Empty state ──────────────────────────────────────────── */}
        {deals.length === 0 && (
          <div className="card-flat p-16 text-center mt-10">
            <div className="serif text-3xl text-zinc-300">No deals yet.</div>
            <p className="mono text-xs text-zinc-400 mt-3">
              Deals will appear here when a creator submits a contract that names your brand.
            </p>
          </div>
        )}
      </div>

      {/* ── Confirm payment modal ────────────────────────────────── */}
      {confirming && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setConfirming(null)}>
          <div className="bg-white card-flat max-w-lg w-full p-8 mx-4" onClick={e => e.stopPropagation()}>
            <span className="label-xs">Confirm Payment · Settlement</span>
            <h2 className="serif text-3xl mt-2">{confirming.deal_title}</h2>
            <div className="mono text-xs text-zinc-500 mt-1">{money(confirming.deal_amount)}</div>

            <p className="text-sm text-zinc-600 mt-6">
              Confirm that you've wired <strong>{money(confirming.deal_amount)}</strong> to the Athanni account.
              Enter your bank reference (UTR number) below — we'll verify and mark the deal settled.
            </p>

            <form onSubmit={submitPayment} className="mt-6 space-y-5">
              <div>
                <label className="label-xs">UTR / Reference Number <span className="text-red-500">*</span></label>
                <input
                  autoFocus
                  className="input-hair mt-1 mono"
                  placeholder="e.g. HDFC00012345678901"
                  value={utr}
                  onChange={e => setUtr(e.target.value)}
                  required
                />
                <p className="text-xs text-zinc-400 mt-1">
                  Find this in your bank's transaction history or payment confirmation email.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setConfirming(null)} className="btn-ghost text-sm">Cancel</button>
                <button type="submit" disabled={submitting} className="btn-primary text-sm">
                  {submitting ? "Confirming…" : "Confirm transfer →"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
