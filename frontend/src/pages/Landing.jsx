import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Zap, ShieldCheck, LineChart, CheckCircle } from "lucide-react";
import { AthanniLogo } from "../components/AthanniLogo";

const NAVY  = "#0D1B3E";
const BLUE  = "#2646B0";
const COPPER = "#B87333";

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-zinc-900">

      {/* ── Dark navy top bar ── */}
      <header style={{ background: NAVY }} className="sticky top-0 z-20">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AthanniLogo size="md" dark={true} />
            <span className="label-xs hidden md:inline" style={{ color: "rgba(255,255,255,0.35)" }}>
              / creator receivables desk
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              data-testid="landing-login"
              to="/login"
              className="text-sm font-medium text-white/60 hover:text-white transition-colors"
            >
              Log in
            </Link>
            <Link data-testid="landing-register" to="/register" className="btn-copper text-sm">
              Get funded <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 py-20 lg:py-28 grid lg:grid-cols-12 gap-10 items-center">

          {/* Left: copy */}
          <div className="lg:col-span-6">
            <span className="label-xs" style={{ color: BLUE }}>
              Creator Receivables · AR Financing
            </span>
            <h1 className="serif text-5xl md:text-6xl lg:text-[68px] leading-[0.95] tracking-tight mt-4" style={{ color: NAVY }}>
              Get paid today.
              <br />
              <span className="italic" style={{ color: BLUE }}>Not in 60 days.</span>
            </h1>
            <p className="mt-7 text-lg text-zinc-500 max-w-lg leading-relaxed">
              Upload your brand deal contract. We verify, score, and wire up to{" "}
              <span className="mono font-semibold" style={{ color: NAVY }}>80%</span>{" "}
              — in hours.
            </p>

            <div className="mt-10 flex flex-wrap gap-3">
              <Link data-testid="hero-cta" to="/register" className="btn-brand">
                Open account <ArrowUpRight className="w-4 h-4" />
              </Link>
              <Link to="/login" className="btn-ghost text-sm">
                Log in
              </Link>
            </div>

            <div className="mt-8 flex flex-wrap gap-5">
              {["No lock-in contracts", "Same-day wire on approval", "ISO 20022 compliant"].map(s => (
                <span key={s} className="flex items-center gap-1.5 text-xs text-zinc-400">
                  <CheckCircle className="w-3.5 h-3.5" style={{ color: BLUE }} />
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Right: live credit memo card */}
          <div className="lg:col-span-6">
            <div className="border border-zinc-200 bg-white">
              <div className="p-6 border-b border-zinc-100">
                <div className="flex items-center justify-between">
                  <span className="label-xs" style={{ color: BLUE }}>
                    Credit Memo · 2026-Q1-0042
                  </span>
                  <span className="chip chip-ok">Verified</span>
                </div>
                <div className="serif text-2xl mt-3" style={{ color: NAVY }}>Priya Sharma × boAt</div>
                <div className="mono text-xs text-zinc-400 mt-0.5">@priyasharma · 1.2M · IG</div>
              </div>

              <div className="grid grid-cols-2 border-b border-zinc-100">
                <div className="p-5 border-r border-zinc-100">
                  <div className="label-xs" style={{ color: BLUE }}>Brand Score</div>
                  <div className="serif text-4xl mt-1" style={{ color: NAVY }}>88</div>
                  <div className="mono text-xs text-zinc-400 mt-1">AA · Enterprise</div>
                </div>
                <div className="p-5">
                  <div className="label-xs" style={{ color: BLUE }}>Creator Health</div>
                  <div className="serif text-4xl mt-1" style={{ color: NAVY }}>76</div>
                  <div className="mono text-xs text-zinc-400 mt-1">ER 4.2%</div>
                </div>
              </div>

              <div className="p-5 border-b border-zinc-100">
                <div className="label-xs" style={{ color: BLUE }}>Advance</div>
                <div className="serif text-4xl mt-1" style={{ color: NAVY }}>₹3.6L</div>
                <div className="mono text-xs text-zinc-400 mt-1">80% of ₹4.5L · fee 3%</div>
              </div>

              <div className="p-4">
                <button
                  className="w-full py-4 text-white font-semibold flex items-center justify-center gap-2"
                  style={{ background: NAVY }}
                >
                  Accept offer · Get ₹3.6L <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="border-b border-zinc-100" style={{ background: "#F7F8FC" }}>
        <div className="max-w-[1400px] mx-auto px-6 py-10 grid grid-cols-3 divide-x divide-zinc-200">
          {[
            { k: "$18.4M", v: "Advanced YTD" },
            { k: "1,240",  v: "Deals underwritten" },
            { k: "0.42%",  v: "Default rate" },
          ].map(s => (
            <div key={s.v} className="px-8 first:pl-0 last:pr-0">
              <div className="serif text-3xl" style={{ color: BLUE }}>{s.k}</div>
              <div className="label-xs mt-1">{s.v}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 py-16">
          <div className="flex items-end justify-between mb-10">
            <div>
              <span className="label-xs" style={{ color: BLUE }}>Module · 01</span>
              <h2 className="serif text-4xl lg:text-5xl mt-2 tracking-tight" style={{ color: NAVY }}>
                The underwriting loop.
              </h2>
            </div>
            <Link to="/register" className="btn-brand-ghost hidden md:inline-flex text-sm">
              Start now <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid md:grid-cols-4 divide-x divide-zinc-200 border border-zinc-200">
            {[
              { n: "01", t: "Upload contract", d: "PDF or image. OCR extracts deliverables, payment terms, exclusivity." },
              { n: "02", t: "Verify brand",    d: "Solvency score, credit rating, days-to-pay across 1,800+ advertisers." },
              { n: "03", t: "Score creator",   d: "Followers, engagement authenticity, audience trust — weighted 40%." },
              { n: "04", t: "Disburse",        d: "Up to 80% advanced. Brand settles directly with Athanni on Net-X." },
            ].map((s, i) => (
              <div key={s.n} className="p-6 bg-white relative">
                {i === 3 && (
                  <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: COPPER }} />
                )}
                <div className="mono text-xs" style={{ color: BLUE }}>{s.n}</div>
                <div className="serif text-2xl mt-2" style={{ color: NAVY }}>{s.t}</div>
                <div className="text-sm text-zinc-500 mt-2 leading-relaxed">{s.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pillars ── */}
      <section className="border-b border-zinc-100" style={{ background: "#F7F8FC" }}>
        <div className="max-w-[1400px] mx-auto px-6 py-16">
          <span className="label-xs" style={{ color: BLUE }}>Module · 02</span>
          <h2 className="serif text-4xl mt-2 tracking-tight mb-10" style={{ color: NAVY }}>Why Athanni.</h2>
          <div className="grid md:grid-cols-3 gap-px bg-zinc-200 border border-zinc-200">
            {[
              { icon: <Zap className="w-5 h-5" />,          t: "Same-day liquidity",        d: "We wire within 4 business hours of verification. Net-60 becomes Net-0." },
              { icon: <ShieldCheck className="w-5 h-5" />,  t: "Risk priced, not rationed", d: "Transparent discount-fee ladder from 2.5% to 8.0% based on brand tier + creator health." },
              { icon: <LineChart className="w-5 h-5" />,    t: "Revolving credit line",     d: "Repay on brand payment, capital recycles. Limit grows as your history compounds." },
            ].map(p => (
              <div key={p.t} className="p-8 bg-white">
                <div className="w-10 h-10 border border-zinc-200 flex items-center justify-center" style={{ color: BLUE }}>
                  {p.icon}
                </div>
                <div className="serif text-2xl mt-4" style={{ color: NAVY }}>{p.t}</div>
                <div className="text-sm text-zinc-500 mt-2 leading-relaxed">{p.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Fee ladder ── */}
      <section className="border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 py-16">
          <span className="label-xs" style={{ color: BLUE }}>Module · 03</span>
          <h2 className="serif text-4xl mt-2 tracking-tight mb-10" style={{ color: NAVY }}>Transparent pricing.</h2>
          <div className="grid md:grid-cols-4 gap-px bg-zinc-200 border border-zinc-200">
            {[
              { tier: "AAA Brand + Elite Creator",  fee: "2.5%",     advance: "Up to 95%", label: "Best rate", hi: true },
              { tier: "AA Brand + Strong Creator",  fee: "3.5%",     advance: "Up to 90%", label: "Standard",  hi: false },
              { tier: "A Brand + Emerging Creator", fee: "5.0%",     advance: "Up to 80%", label: "Growth",    hi: false },
              { tier: "Unrated / New",              fee: "Up to 8%", advance: "Up to 70%", label: "Entry",     hi: false },
            ].map(r => (
              <div key={r.tier} className="relative p-6 bg-white">
                {r.hi && <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: COPPER }} />}
                <div className="label-xs mb-3">{r.label}</div>
                <div className="serif text-4xl" style={{ color: r.hi ? BLUE : NAVY }}>{r.fee}</div>
                <div className="text-xs text-zinc-400 mt-1">discount fee</div>
                <div className="mono text-sm mt-4 font-semibold" style={{ color: NAVY }}>{r.advance}</div>
                <div className="text-xs text-zinc-400">advance rate</div>
                <div className="mt-4 pt-4 border-t border-zinc-100 text-xs text-zinc-400 leading-relaxed">{r.tier}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA strip — navy bg, copper button ── */}
      <section style={{ background: NAVY }}>
        <div className="max-w-[1400px] mx-auto px-6 py-20 flex flex-col md:flex-row items-start md:items-end justify-between gap-8">
          <div>
            <span className="label-xs" style={{ color: "rgba(255,255,255,0.4)" }}>Open the desk</span>
            <h3 className="serif text-4xl md:text-5xl mt-2 tracking-tight text-white max-w-2xl leading-[1.0]">
              Deal signed this week?<br />Get paid before Friday.
            </h3>
          </div>
          <Link data-testid="footer-cta" to="/register" className="btn-copper shrink-0">
            Start underwriting <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-zinc-100 bg-white">
        <div className="max-w-[1400px] mx-auto px-6 py-6 flex flex-wrap justify-between items-center gap-4">
          <span className="label-xs">© Athanni 2026 · AR Financing for the Creator Economy</span>
          <div className="flex items-center gap-6">
            <span className="mono text-xs text-zinc-400">v0.1</span>
            <span className="mono text-xs text-zinc-400">ISO 20022</span>
            <Link to="/login" className="mono text-xs text-zinc-400 underline-ink">Log in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
