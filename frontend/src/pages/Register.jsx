import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { AthanniLogo } from "../components/AthanniLogo";
import { Eye, EyeOff } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", handle: "" });
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await register({ ...form, role: "creator" });
      toast.success(`Account opened · welcome, ${u.name}`);
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="p-8 lg:p-16 flex flex-col">
        <Link to="/" className="flex items-center gap-2">
          <AthanniLogo size="sm" dark={false} />
        </Link>
        <div className="flex-1 flex items-center">
          <form onSubmit={onSubmit} className="w-full max-w-md" data-testid="register-form">
            <span className="label-xs">Onboarding · New Creator</span>
            <h1 className="serif text-5xl mt-3 tracking-tight">Open an account.</h1>
            <p className="text-zinc-600 mt-3 text-sm">Two minutes. No credit card. Your first credit limit is computed within the next screen.</p>

            <div className="mt-10 space-y-6">
              <div>
                <label className="label-xs">Full Name</label>
                <input data-testid="register-name" name="full_name" value={form.full_name} onChange={onChange} className="input-hair mt-1" required />
              </div>
              <div>
                <label className="label-xs">Creator Handle</label>
                <input data-testid="register-handle" name="handle" value={form.handle} onChange={onChange} placeholder="@yourhandle" className="input-hair mt-1" />
              </div>
              <div>
                <label className="label-xs">Email</label>
                <input data-testid="register-email" type="email" name="email" value={form.email} onChange={onChange} className="input-hair mt-1" required />
              </div>
              <div>
                <label className="label-xs">Password</label>
                <div className="relative mt-1">
                  <input
                    data-testid="register-password"
                    type={showPw ? "text" : "password"}
                    name="password"
                    value={form.password}
                    onChange={onChange}
                    minLength={6}
                    className="input-hair w-full pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 transition-colors"
                    tabIndex={-1}
                    aria-label={showPw ? "Hide password" : "Show password"}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </div>

            <button data-testid="register-submit" type="submit" disabled={loading} className="btn-primary mt-10 w-full justify-center">
              {loading ? "Provisioning desk…" : "Open account →"}
            </button>

            <div className="mt-6 text-sm text-zinc-600">
              Already a client? <Link to="/login" className="underline-ink text-zinc-950">Log in</Link>
            </div>
          </form>
        </div>
      </div>
      {/* ── Right: luxury ink panel ── */}
      <div className="hidden lg:flex flex-col bg-zinc-950 text-white relative overflow-hidden">
        {/* Subtle grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />

        <div className="relative z-10 flex flex-col h-full p-14 justify-between">
          {/* Top: brand mark */}
          <div className="flex items-center gap-3">
            <AthanniLogo size="sm" dark={true} />
            <div className="label-xs text-zinc-500 mt-0.5">Receivables Desk</div>
          </div>

          {/* Middle: onboarding steps */}
          <div>
            <div
              className="text-4xl leading-[1.1] tracking-tight font-light mb-10"
              style={{ fontFamily: "’Instrument Serif’, serif" }}
            >
              Three steps to
              <br />
              <span className="italic text-zinc-400">instant liquidity.</span>
            </div>

            <ol className="space-y-8 max-w-sm">
              {[
                ["Upload your contract", "PDF or image of the signed brand deal."],
                ["We verify the brand", "Solvency check, credit rating, pay history."],
                ["Accept the offer", "See advance rate + fee. Accept, get wired."],
              ].map(([t, d], i) => (
                <li key={t} className="flex gap-5 items-start">
                  <div
                    className="mono text-xs text-zinc-600 pt-1 shrink-0 w-6 text-right"
                  >
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="border-l border-zinc-700 pl-5">
                    <div
                      className="text-xl text-white leading-tight"
                      style={{ fontFamily: "’Instrument Serif’, serif" }}
                    >
                      {t}
                    </div>
                    <div className="text-zinc-500 text-sm mt-1 leading-relaxed">{d}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {/* Bottom: legal note */}
          <div className="mono text-xs text-zinc-600 border-t border-zinc-800 pt-6">
            By registering you agree to Athanni’s Master Factoring Agreement.
          </div>
        </div>
      </div>
    </div>
  );
}
