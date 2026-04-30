import React, { useEffect, useState, useRef } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { api, money, pct } from "../lib/api";
import RiskGauge from "../components/RiskGauge";
import { StatusChip } from "./Dashboard";
import { toast } from "sonner";
import { CheckCircle2, Circle, AlertTriangle, FileText, ArrowUpRight, Wallet, Landmark, Smartphone, Copy } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const STEPS = [
  { k: "uploaded", t: "Uploaded" },
  { k: "scored", t: "Verified & Scored" },
  { k: "disbursed", t: "Disbursed" },
  { k: "repaid", t: "Repaid · Credit Recycled" },
];

export default function DealDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [deal, setDeal] = useState(null);
  const [brand, setBrand] = useState(null);
  const [social, setSocial] = useState(null);
  const [bankDetails, setBankDetails] = useState(null);
  const [disbursing, setDisbursing] = useState(false);
  const [repaying, setRepaying] = useState(false);
  const [confirmingPayment, setConfirmingPayment] = useState(false);
  const [utrNumber, setUtrNumber] = useState("");
  const [pollMsg, setPollMsg] = useState("");
  const pollRef = useRef(null);

  const load = async () => {
    const r = await api.get(`/deals/${id}`);
    setDeal(r.data);
    const [b, s] = await Promise.all([
      api.get(`/brands/${r.data.brand_id}`),
      api.get(`/creator/profile`).catch(() => ({ data: null })),
    ]);
    setBrand(b.data);
    setSocial(s.data);
    // Load My Pay bank details when deal is disbursed (brand needs to pay)
    if (["disbursed", "awaiting_payment"].includes(r.data.status)) {
      api.get(`/deals/bank-details`).then(bd => setBankDetails(bd.data)).catch(() => {});
    }
  };

  useEffect(() => { load(); }, [id]);

  // Stripe return — poll status
  useEffect(() => {
    const sid = params.get("session_id");
    const repay = params.get("repay");
    if (!sid && !repay) return;
    if (repay === "cancelled") {
      toast.info("Repayment cancelled.");
      setParams({}, { replace: true });
      return;
    }
    if (!sid) return;

    let attempts = 0;
    const maxAttempts = 10;
    setPollMsg("Confirming payment with Stripe…");
    const poll = async () => {
      attempts += 1;
      try {
        const r = await api.get(`/payments/status/${sid}`);
        if (r.data.payment_status === "paid") {
          setPollMsg("");
          toast.success("Brand paid. Credit recycled to your limit.");
          setParams({}, { replace: true });
          load();
          return;
        }
        if (r.data.status === "expired") {
          setPollMsg("Session expired.");
          setParams({}, { replace: true });
          return;
        }
        if (attempts >= maxAttempts) {
          setPollMsg("Still processing — refresh in a moment.");
          return;
        }
        pollRef.current = setTimeout(poll, 2000);
      } catch {
        setPollMsg("Could not verify payment.");
      }
    };
    poll();
    return () => pollRef.current && clearTimeout(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  if (!deal) return <div className="mono text-sm">Loading deal…</div>;

  const stepIdx = ({
    uploaded: 0, scored: 1, disbursed: 2, awaiting_payment: 2, repaid: 3,
  })[deal.status] ?? 0;
  const isScored = !!deal.risk;

  const advance = async () => {
    setDisbursing(true);
    try {
      await api.post(`/deals/${id}/advance`);
      toast.success("Funds wired — they will appear in 2-4 hours.");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Disbursement failed"); }
    finally { setDisbursing(false); }
  };

  const initiateRepay = async () => {
    setRepaying(true);
    try {
      const r = await api.post(`/deals/${id}/repay-checkout`, { origin_url: window.location.origin });
      window.location.href = r.data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start Stripe checkout");
      setRepaying(false);
    }
  };

  const confirmBrandPayment = async () => {
    setConfirmingPayment(true);
    try {
      await api.post(`/deals/${id}/brand-confirm-payment`, { utr_number: utrNumber });
      toast.success("Payment confirmed. My Pay team will verify and mark as repaid.");
      setUtrNumber("");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Confirmation failed"); }
    finally { setConfirmingPayment(false); }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => toast.info("Copied to clipboard."));
  };

  const reanalyze = async () => {
    toast.info("Re-running underwriting…");
    try {
      await api.post(`/deals/${id}/analyze`);
      toast.success("Scored.");
      load();
    } catch (e) { toast.error("Analysis failed"); }
  };

  return (
    <div data-testid="deal-detail-root">
      <div className="flex items-start justify-between mb-8">
        <div>
          <Link to="/deals" className="mono text-xs text-zinc-500 underline-ink">← Ledger</Link>
          <div className="flex items-center gap-3 mt-3">
            <span className="label-xs">Credit Memo · {deal.id.slice(0,8).toUpperCase()}</span>
            <StatusChip status={deal.status} />
          </div>
          <h1 className="serif text-5xl tracking-tight mt-2">{deal.deal_title}</h1>
          <div className="mono text-sm text-zinc-500 mt-1">{deal.brand_name} · Net {deal.payment_terms_days} · {money(deal.deal_amount)}</div>
        </div>
        <div className="flex gap-3">
          {!isScored && (
            <button data-testid="analyze-btn" onClick={reanalyze} className="btn-ghost text-sm">Run underwriting</button>
          )}
          {isScored && deal.status === "scored" && (
            <button data-testid="disburse-btn" onClick={advance} disabled={disbursing} className="btn-primary text-sm">
              {disbursing ? "Wiring…" : `Accept & Receive ${money(deal.advance_amount)}`} <ArrowUpRight className="w-4 h-4" />
            </button>
          )}
          {(deal.status === "disbursed" || deal.status === "awaiting_payment") && (
            <button data-testid="repay-btn" onClick={initiateRepay} disabled={repaying} className="btn-primary text-sm">
              <Wallet className="w-4 h-4" /> {repaying ? "Opening Stripe…" : `Brand: Pay ${money(deal.deal_amount)}`}
            </button>
          )}
          {deal.status === "repaid" && <span className="chip chip-ok">Repaid · credit recycled</span>}
        </div>
      </div>

      {pollMsg && (
        <div data-testid="repay-poll-msg" className="card-flat px-5 py-3 mb-6 flex items-center gap-3">
          <div className="w-3 h-3 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin" />
          <span className="mono text-xs">{pollMsg}</span>
        </div>
      )}

      {/* Timeline */}
      <section className="grid grid-cols-4 gap-px bg-zinc-200 border hair mb-10">
        {STEPS.map((s, i) => {
          const active = i <= stepIdx;
          return (
            <div key={s.k} className="bg-white p-5">
              <div className="flex items-center gap-2">
                {active ? <CheckCircle2 className="w-4 h-4 text-zinc-950" /> : <Circle className="w-4 h-4 text-zinc-300" />}
                <span className="label-xs">{String(i+1).padStart(2,"0")}</span>
              </div>
              <div className={`serif text-xl mt-2 ${active ? "text-zinc-950" : "text-zinc-400"}`}>{s.t}</div>
              <div className="mono text-xs text-zinc-500 mt-1">
                {i === 0 && new Date(deal.created_at).toLocaleString()}
                {i === 1 && deal.risk && "Score computed"}
                {i === 2 && deal.disbursed_at && new Date(deal.disbursed_at).toLocaleString()}
                {i === 3 && deal.repaid_at && new Date(deal.repaid_at).toLocaleString()}
                {i === 2 && !deal.disbursed_at && deal.maturity_date && `Matures ${new Date(deal.maturity_date).toLocaleDateString()}`}
              </div>
            </div>
          );
        })}
      </section>

      {!isScored && (
        <div className="card-flat p-8 text-center">
          <div className="serif text-3xl">Pending underwriting</div>
          <div className="text-sm text-zinc-600 mt-2">Click “Run underwriting” to score this deal.</div>
        </div>
      )}

      {isScored && (
        <div className="grid lg:grid-cols-12 gap-px bg-zinc-200 border hair mb-10">
          {/* Risk Gauge */}
          <div className="bg-white p-8 lg:col-span-4 flex flex-col items-center justify-center">
            <RiskGauge value={deal.risk.risk_score} testId="risk-gauge" />
            <div className="mt-6 w-full border-t hair pt-4 space-y-2">
              {deal.risk.factors.map((f) => (
                <div key={f.label} className="flex justify-between text-sm">
                  <span className="text-zinc-500">{f.label}</span>
                  <span className="mono">{f.value}{f.weight > 0 ? ` · w${f.weight}` : ""}</span>
                </div>
              ))}
              {deal.risk.ml && (
                <div className="mt-3 pt-3 border-t hair" data-testid="ml-prediction">
                  <div className="flex justify-between items-baseline">
                    <span className="label-xs">ML Default Prob.</span>
                    <span className="mono text-sm">{(deal.risk.ml.default_prob * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="label-xs">ML Survival Score</span>
                    <span className="mono text-sm">{deal.risk.ml.ml_score}</span>
                  </div>
                  <div className="mono text-xs text-zinc-400 mt-1">Model AUC {deal.risk.ml.model_auc}</div>
                </div>
              )}
            </div>
          </div>

          {/* Credit Offer */}
          <div className="bg-white p-8 lg:col-span-4">
            <span className="label-xs">Credit Offer</span>
            <div className="serif text-5xl mt-3" data-testid="advance-amount">{money(deal.advance_amount)}</div>
            <div className="mono text-xs text-zinc-500 mt-1">Advance · {pct(deal.risk.advance_rate, 0)} of face value</div>

            <div className="grid grid-cols-2 gap-4 mt-8">
              <div>
                <div className="label-xs">Discount Fee</div>
                <div className="serif text-2xl">{money(deal.discount_fee)}</div>
                <div className="mono text-xs text-zinc-500">{pct(deal.risk.discount_fee_rate)}</div>
              </div>
              <div>
                <div className="label-xs">APR Equivalent</div>
                <div className="serif text-2xl">{pct(deal.risk.apr_equivalent, 1)}</div>
                <div className="mono text-xs text-zinc-500">annualised</div>
              </div>
              <div>
                <div className="label-xs">Net to You</div>
                <div className="serif text-2xl">{money(deal.advance_amount)}</div>
                <div className="mono text-xs text-zinc-500">wired T+0</div>
              </div>
              <div>
                <div className="label-xs">Brand pays</div>
                <div className="serif text-2xl">{money(deal.deal_amount)}</div>
                <div className="mono text-xs text-zinc-500">Net {deal.payment_terms_days} to My Pay</div>
              </div>
            </div>

            {deal.admin_override && (
              <div className="mt-6 border-t hair pt-4">
                <span className="chip chip-warn">Admin Override Applied</span>
                <div className="mono text-xs text-zinc-500 mt-2">By {deal.admin_override.by}</div>
                {deal.admin_override.notes && <div className="text-sm text-zinc-700 mt-1">{deal.admin_override.notes}</div>}
              </div>
            )}
          </div>

          {/* Brand + Creator side by side */}
          <div className="bg-white p-8 lg:col-span-4 space-y-6">
            <div>
              <span className="label-xs">Brand Solvency</span>
              <div className="flex items-baseline gap-3 mt-2">
                <span className="serif text-4xl">{deal.risk.brand_component}</span>
                <span className="mono text-xs text-zinc-500">/ 100</span>
                <span className="chip chip-brand ml-auto">{brand?.credit_rating}</span>
              </div>
              <div className="mt-4 space-y-1.5 mono text-xs">
                <Row l="Tier" v={brand?.tier} />
                <Row l="Solvency" v={brand?.solvency_score} />
                <Row l="Pay history" v={brand?.payment_history_score} />
                <Row l="Avg days-to-pay" v={brand?.avg_payment_days} />
                <Row l="Industry" v={brand?.industry} />
              </div>
            </div>
            <div className="border-t hair pt-6">
              <span className="label-xs">Creator Health</span>
              <div className="flex items-baseline gap-3 mt-2">
                <span className="serif text-4xl">{deal.risk.creator_component}</span>
                <span className="mono text-xs text-zinc-500">/ 100</span>
              </div>
              <div className="mt-4 space-y-1.5 mono text-xs">
                <Row l="Followers" v={(social?.followers || 0).toLocaleString()} />
                <Row l="Engagement" v={pct(social?.engagement_rate, 2)} />
                <Row l="Authenticity" v={social?.authenticity_score} />
                <Row l="Platform" v={social?.platform} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI analysis */}
      {deal.ai_analysis && (
        <section className="card-flat p-8 mb-10" data-testid="ai-analysis-panel">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="label-xs">Underwriter memo · AI-assisted</span>
              <h2 className="serif text-3xl mt-1">Contract analysis</h2>
            </div>
            <span className={`chip ${
              deal.ai_analysis.verification_status === "verified" ? "chip-ok" :
              deal.ai_analysis.verification_status === "rejected" ? "chip-bad" : "chip-warn"
            }`}>
              {deal.ai_analysis.verification_status} · {deal.ai_analysis.confidence_pct}%
            </span>
          </div>

          <p className="text-zinc-700 leading-relaxed border-l-2 border-zinc-950 pl-4">
            {deal.ai_analysis.underwriter_note}
          </p>

          <div className="grid md:grid-cols-2 gap-px bg-zinc-200 border hair mt-6">
            <div className="bg-white p-5">
              <div className="label-xs mb-3">Key terms</div>
              <div className="space-y-1.5 mono text-xs">
                {Object.entries(deal.ai_analysis.key_terms || {}).map(([k, v]) => (
                  <Row key={k} l={k.replace(/_/g, " ")} v={String(v)} />
                ))}
              </div>
            </div>
            <div className="bg-white p-5">
              <div className="label-xs mb-3 flex items-center gap-2"><AlertTriangle className="w-3 h-3 text-red-600" /> Red flags</div>
              <ul className="text-sm space-y-1 text-red-700">
                {(deal.ai_analysis.red_flags || []).length === 0 && <li className="text-zinc-400">None flagged.</li>}
                {(deal.ai_analysis.red_flags || []).map((r, i) => <li key={i}>— {r}</li>)}
              </ul>
              <div className="label-xs mt-4 mb-3">Green flags</div>
              <ul className="text-sm space-y-1 text-green-700">
                {(deal.ai_analysis.green_flags || []).length === 0 && <li className="text-zinc-400">—</li>}
                {(deal.ai_analysis.green_flags || []).map((r, i) => <li key={i}>+ {r}</li>)}
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* Repayment ledger */}
      {(deal.status === "disbursed" || deal.status === "awaiting_payment" || deal.status === "repaid") && (
        <section className="card-flat p-8 mb-10" data-testid="repayment-ledger">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="label-xs">Repayment · Ledger</span>
              <h2 className="serif text-3xl mt-1">Brand settlement</h2>
            </div>
            {deal.status === "repaid" && <span className="chip chip-ok">Settled</span>}
            {deal.status === "awaiting_payment" && <span className="chip chip-warn">Awaiting Stripe confirmation</span>}
          </div>

          <div className="grid md:grid-cols-4 gap-px bg-zinc-200 border hair">
            <LedgerCell label="Advance (to you)" value={money(deal.advance_amount)} sub={deal.disbursed_at && new Date(deal.disbursed_at).toLocaleDateString()} />
            <LedgerCell label="Discount Fee" value={money(deal.discount_fee)} sub={pct(deal.risk?.discount_fee_rate)} />
            <LedgerCell label="Maturity" value={deal.maturity_date ? new Date(deal.maturity_date).toLocaleDateString() : "—"} sub={`Net ${deal.payment_terms_days}`} />
            <LedgerCell label="Brand owes" value={money(deal.deal_amount)} sub={deal.status === "repaid" ? "Paid ✓" : "Outstanding"} highlight={deal.status === "repaid"} />
          </div>

          {deal.status === "repaid" && (
            <div className="mt-6 mono text-xs text-zinc-600 border-l-2 border-green-600 pl-4">
              Repaid {deal.repaid_at && new Date(deal.repaid_at).toLocaleString()}.
              Credit line restored · {money(deal.advance_amount)} returned to available limit.
            </div>
          )}
          {deal.status !== "repaid" && (
            <div className="mt-6 text-sm text-zinc-600">
              Send the Stripe invoice link to the brand&apos;s finance team, or use the test-mode button above to simulate settlement.
            </div>
          )}
        </section>
      )}

      {/* Creator payout status — shown when disbursed */}
      {deal.payout && (
        <section className="card-flat p-8 mb-10" data-testid="payout-status-section">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="label-xs">Advance · Payout Status</span>
              <h2 className="serif text-3xl mt-1">Your funds</h2>
            </div>
            <span className={`chip ${
              deal.payout.status === "completed" ? "chip-ok" :
              deal.payout.status === "failed" ? "chip-bad" : "chip-warn"
            }`}>
              {deal.payout.status}
            </span>
          </div>

          <div className="grid md:grid-cols-3 gap-px bg-zinc-200 border hair">
            <div className="bg-white p-5">
              <div className="label-xs">Amount</div>
              <div className="serif text-3xl mt-2">{money(deal.payout.amount)}</div>
              <div className="mono text-xs text-zinc-500 mt-1">{deal.payout.currency}</div>
            </div>
            <div className="bg-white p-5">
              <div className="label-xs">Method</div>
              <div className="flex items-center gap-2 mt-2">
                {deal.payout.method_type === "upi"
                  ? <Smartphone className="w-4 h-4" />
                  : <Landmark className="w-4 h-4" />
                }
                <span className="serif text-xl capitalize">{deal.payout.method_type}</span>
              </div>
              <div className="mono text-xs text-zinc-500 mt-1">{deal.payout.mode}</div>
            </div>
            <div className="bg-white p-5">
              <div className="label-xs">Reference</div>
              <div className="mono text-sm mt-2 break-all">{deal.payout.payout_ref}</div>
              <div className="mono text-xs text-zinc-500 mt-1">
                {deal.payout.initiated_at && new Date(deal.payout.initiated_at).toLocaleString()}
              </div>
            </div>
          </div>

          {deal.payout.status === "completed" && (
            <div className="mono text-xs text-green-700 border-l-2 border-green-600 pl-4 mt-4">
              Funds credited — check your {deal.payout.method_type === "upi" ? "UPI-linked account" : "bank account"}.
            </div>
          )}
          {deal.payout.status === "pending" && (
            <div className="mono text-xs text-zinc-600 border-l-2 border-yellow-500 pl-4 mt-4">
              Payout initiated — typically credited within 2 hours via IMPS / UPI.
            </div>
          )}
          {deal.payout.failure_reason && (
            <div className="mono text-xs text-red-700 border-l-2 border-red-500 pl-4 mt-4">
              {deal.payout.failure_reason}
            </div>
          )}
          {!user?.payout_registered && deal.payout.status !== "completed" && (
            <div className="mt-4 p-4 bg-yellow-50 border hair">
              <div className="text-sm text-yellow-800">
                No payout method registered — go to <Link to="/profile" className="underline">Profile</Link> to add your UPI ID or bank account before accepting deals.
              </div>
            </div>
          )}
        </section>
      )}

      {/* Brand bank payment panel — shown to brand when deal is disbursed */}
      {(deal.status === "disbursed" || deal.status === "awaiting_payment") && (
        <section className="card-flat p-8 mb-10" data-testid="brand-payment-section">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="label-xs">Settlement · Manual Bank Transfer</span>
              <h2 className="serif text-3xl mt-1">Pay My Pay</h2>
            </div>
            {deal.status === "awaiting_payment" && deal.brand_payment_confirmed_at ? (
              <span className="chip chip-warn">Payment confirmed — verifying receipt</span>
            ) : (
              <span className="chip">Transfer pending</span>
            )}
          </div>

          <p className="text-sm text-zinc-600 mb-6 max-w-xl">
            Wire the full invoice amount to My Pay&apos;s current account via NEFT, RTGS, or IMPS.
            Once confirmed, click the button below — our team will verify and mark the deal as repaid.
          </p>

          {/* My Pay bank details */}
          {bankDetails ? (
            <div className="grid md:grid-cols-2 gap-px bg-zinc-200 border hair mb-6">
              {[
                ["Account Name", bankDetails.account_name],
                ["Bank", bankDetails.bank_name],
                ["Account Number", bankDetails.account_number],
                ["IFSC", bankDetails.ifsc],
                ["Account Type", bankDetails.account_type],
                ["UPI ID", bankDetails.upi_id],
              ].map(([label, value]) => (
                <div key={label} className="bg-white p-4 flex items-center justify-between">
                  <div>
                    <div className="label-xs">{label}</div>
                    <div className="mono text-sm mt-1">{value}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(value)}
                    className="text-zinc-400 hover:text-zinc-950 p-1"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="card-flat p-5 mb-6 bg-zinc-50 mono text-xs text-zinc-500">
              Loading bank details…
            </div>
          )}

          <div className="mono text-xs text-zinc-600 border-l-2 border-zinc-300 pl-4 mb-6">
            Include Deal ID <span className="font-medium">{id}</span> in the payment narration / reference.
          </div>

          {/* Confirmation form */}
          {deal.status !== "awaiting_payment" || !deal.brand_payment_confirmed_at ? (
            <div className="space-y-4">
              <div>
                <label className="label-xs">UTR / Transaction Reference (optional but recommended)</label>
                <input
                  data-testid="utr-input"
                  value={utrNumber}
                  onChange={e => setUtrNumber(e.target.value)}
                  className="input-hair mt-1"
                  placeholder="UTR12345678901234"
                />
              </div>
              <button
                data-testid="confirm-payment-btn"
                type="button"
                onClick={confirmBrandPayment}
                disabled={confirmingPayment}
                className="btn-primary"
              >
                <Wallet className="w-4 h-4" />
                {confirmingPayment ? "Confirming…" : `I've transferred ${money(deal.deal_amount)} to My Pay`}
              </button>
            </div>
          ) : (
            <div className="mono text-xs text-zinc-600 border-l-2 border-green-600 pl-4">
              Payment confirmed {new Date(deal.brand_payment_confirmed_at).toLocaleString()}.
              {deal.brand_payment_utr && <span> UTR: {deal.brand_payment_utr}</span>}
              {" "}My Pay team is verifying receipt.
            </div>
          )}
        </section>
      )}

      {/* Contract preview */}
      {(deal.contract_text || deal.contract_file_name || deal.contract_file_id) && (
        <section className="card-flat p-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <FileText className="w-4 h-4" />
              <span className="label-xs">Contract · Source document</span>
            </div>
            {deal.contract_file_id && (
              <a
                data-testid="contract-download"
                href={`${import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"}/api/contracts/${deal.contract_file_id}/download?auth=${localStorage.getItem("mypay_token")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="underline-ink mono text-xs"
              >
                Download ({Math.round((deal.contract_file_size || 0) / 1024)} KB) →
              </a>
            )}
          </div>
          {deal.contract_file_name && (
            <div className="mono text-xs text-zinc-500 mb-3">{deal.contract_file_name}</div>
          )}
          {deal.contract_text && (
            <pre className="mono text-xs text-zinc-700 whitespace-pre-wrap max-h-64 overflow-auto border-l-2 border-zinc-300 pl-4">{deal.contract_text}</pre>
          )}
        </section>
      )}
    </div>
  );
}

function Row({ l, v }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-zinc-500 capitalize">{l}</span>
      <span className="text-zinc-950 text-right">{v ?? "—"}</span>
    </div>
  );
}

function LedgerCell({ label, value, sub, highlight }) {
  return (
    <div className={`bg-white p-5 ${highlight ? "bg-green-50" : ""}`}>
      <div className="label-xs">{label}</div>
      <div className="serif text-2xl mt-2">{value}</div>
      {sub && <div className="mono text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}
