import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Zap, ShieldCheck, LineChart } from "lucide-react";

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-zinc-950">
      {/* Top bar */}
      <header className="border-b hair">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="serif text-3xl">My Pay</span>
            <span className="label-xs hidden md:inline">/ creator receivables desk</span>
          </div>
          <div className="flex items-center gap-3">
            <Link data-testid="landing-login" to="/login" className="text-sm text-zinc-700 hover:text-zinc-950 underline-ink">Login</Link>
            <Link data-testid="landing-register" to="/register" className="btn-primary text-sm">Open Account <ArrowUpRight className="w-4 h-4" /></Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b hair">
        <div className="max-w-[1400px] mx-auto px-6 py-20 lg:py-28 grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-7">
            <span className="label-xs">Inv. №2026-001 / AR Financing</span>
            <h1 className="serif text-5xl md:text-6xl lg:text-7xl leading-[0.95] tracking-tight mt-4">
              Stop waiting <span className="italic">ninety days</span> <br/>
              for the cheque to clear.
            </h1>
            <p className="mt-8 text-lg text-zinc-600 max-w-xl leading-relaxed">
              My Pay is an underwriting desk for the creator economy. Upload a signed brand deal,
              we verify the counterparty, score your creator health, and wire you up to{" "}
              <span className="mono text-zinc-950">95%</span> of the invoice — in minutes, not months.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link data-testid="hero-cta" to="/register" className="btn-primary">Get your credit limit <ArrowUpRight className="w-4 h-4" /></Link>
              <Link to="/login" className="btn-ghost text-sm">Log in to dashboard</Link>
            </div>

            <div className="mt-14 grid grid-cols-3 gap-px bg-zinc-200 border hair">
              {[
                { k: "$18.4M", v: "Advanced YTD" },
                { k: "1,240", v: "Deals underwritten" },
                { k: "0.42%", v: "Default rate" },
              ].map((s) => (
                <div key={s.v} className="bg-white p-5">
                  <div className="serif text-3xl">{s.k}</div>
                  <div className="label-xs mt-1">{s.v}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-5">
            <div className="card-flat p-6 relative">
              <div className="flex justify-between items-start">
                <span className="label-xs">Credit Memo / Ref 2026-Q1-0042</span>
                <span className="chip chip-ok">Verified</span>
              </div>
              <div className="serif text-2xl mt-3">Ava Stone × Gymshark</div>
              <div className="mono text-xs text-zinc-500">@avastone · 487k · IG</div>

              <div className="grid grid-cols-2 gap-px bg-zinc-200 mt-6 border hair">
                <div className="bg-white p-4">
                  <div className="label-xs">Brand Solvency</div>
                  <div className="serif text-3xl mt-1">91<span className="text-zinc-400 text-xl">/100</span></div>
                  <div className="mono text-xs text-zinc-500">AA · Enterprise</div>
                </div>
                <div className="bg-white p-4">
                  <div className="label-xs">Creator Health</div>
                  <div className="serif text-3xl mt-1">88<span className="text-zinc-400 text-xl">/100</span></div>
                  <div className="mono text-xs text-zinc-500">ER 4.8% · Auth 92</div>
                </div>
                <div className="bg-white p-4">
                  <div className="label-xs">Deal Value</div>
                  <div className="serif text-3xl mt-1">$12,000</div>
                  <div className="mono text-xs text-zinc-500">Net 60</div>
                </div>
                <div className="bg-white p-4">
                  <div className="label-xs">Advance</div>
                  <div className="serif text-3xl mt-1">$10,800</div>
                  <div className="mono text-xs text-zinc-500">90% · fee 3.5%</div>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <span className="mono text-xs">Risk Score</span>
                <span className="mono text-sm">91.4 / 100</span>
              </div>
              <div className="h-1 bg-zinc-100 mt-2">
                <div className="h-1 bg-green-600" style={{ width: "91.4%" }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-b hair">
        <div className="max-w-[1400px] mx-auto px-6 py-16">
          <span className="label-xs">Module · 01</span>
          <h2 className="serif text-4xl lg:text-5xl mt-2 tracking-tight">The underwriting loop.</h2>
          <div className="grid md:grid-cols-4 gap-px bg-zinc-200 mt-10 border hair">
            {[
              { n: "01", t: "Upload contract", d: "PDF or image. OCR extracts deliverables, payment terms, exclusivity." },
              { n: "02", t: "Verify brand", d: "Solvency score, credit rating, historical days-to-pay across 1,800+ advertisers." },
              { n: "03", t: "Score creator", d: "Followers, engagement authenticity, audience trust — weighted 40%." },
              { n: "04", t: "Disburse", d: "Up to 95% advanced. Brand settles directly with My Pay on Net-X." },
            ].map(s => (
              <div key={s.n} className="bg-white p-6">
                <div className="mono text-xs text-zinc-400">{s.n}</div>
                <div className="serif text-2xl mt-2">{s.t}</div>
                <div className="text-sm text-zinc-600 mt-2 leading-relaxed">{s.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="border-b hair">
        <div className="max-w-[1400px] mx-auto px-6 py-16 grid md:grid-cols-3 gap-px bg-zinc-200 border hair">
          {[
            { icon: <Zap className="w-5 h-5" />, t: "Same-day liquidity", d: "We wire within 4 business hours of verification. Net-60 becomes Net-0." },
            { icon: <ShieldCheck className="w-5 h-5" />, t: "Risk priced, not rationed", d: "Transparent discount-fee ladder from 2.5% to 8.0% based on brand tier + creator health." },
            { icon: <LineChart className="w-5 h-5" />, t: "Revolving credit line", d: "Repay on brand payment, capital recycles. Limit grows as your history compounds." },
          ].map((p) => (
            <div key={p.t} className="bg-white p-8">
              <div className="w-10 h-10 border hair flex items-center justify-center">{p.icon}</div>
              <div className="serif text-2xl mt-4">{p.t}</div>
              <div className="text-sm text-zinc-600 mt-2 leading-relaxed">{p.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="max-w-[1400px] mx-auto px-6 py-20 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
          <div>
            <span className="label-xs">Open the desk</span>
            <h3 className="serif text-4xl md:text-5xl mt-2 tracking-tight max-w-2xl">Deal signed this week? Get paid before Friday.</h3>
          </div>
          <Link data-testid="footer-cta" to="/register" className="btn-primary">Start underwriting <ArrowUpRight className="w-4 h-4" /></Link>
        </div>
      </section>
    </div>
  );
}
