import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { AthanniLogo } from "../components/AthanniLogo";
import { Eye, EyeOff } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await login(email, password);
      toast.success(`Welcome back, ${u.name}`);
      nav(u.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">

      {/* ── Left: form ── */}
      <div className="p-8 lg:p-16 flex flex-col bg-white">
        <Link to="/" className="flex items-center gap-2">
          <AthanniLogo size="sm" dark={false} />
        </Link>

        <div className="flex-1 flex items-center">
          <form onSubmit={onSubmit} className="w-full max-w-md" data-testid="login-form">
            <span className="label-xs">Session · Authentication</span>
            <h1 className="serif text-5xl mt-3 tracking-tight leading-none">Log in.</h1>
            <p className="text-zinc-500 mt-4 text-sm leading-relaxed">
              Access your creator receivables desk.
            </p>

            <div className="mt-10 space-y-7">
              <div>
                <label className="label-xs">Email address</label>
                <input
                  data-testid="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-hair mt-1"
                  placeholder="you@example.com"
                  required
                />
              </div>
              <div>
                <label className="label-xs">Password</label>
                <div className="relative mt-1">
                  <input
                    data-testid="login-password"
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
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

            <button
              data-testid="login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary mt-10 w-full justify-center text-sm"
            >
              {loading ? "Authenticating…" : "Log in →"}
            </button>

            <div className="mt-6 text-sm text-zinc-500">
              New to Athanni?{" "}
              <Link to="/register" className="underline-ink text-zinc-950 font-medium">
                Open an account
              </Link>
            </div>
          </form>
        </div>

        <div className="mono text-xs text-zinc-400">
          © Athanni 2026 · AR Financing for the Creator Economy
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

          {/* Middle: pull quote */}
          <div>
            <div
              className="text-5xl leading-[1.05] tracking-tight font-light mb-8"
              style={{ fontFamily: "'Instrument Serif', serif" }}
            >
              Stop waiting
              <br />
              <span className="italic text-zinc-400">90 days</span>
              <br />
              for the wire.
            </div>
            <p className="text-zinc-400 text-sm leading-relaxed max-w-xs">
              Upload a signed brand deal, we verify the counterparty and wire you
              up to <span className="text-white font-medium mono">90%</span> of the
              invoice — within 24 hours.
            </p>
          </div>

          {/* Bottom: live stats grid */}
          <div className="grid grid-cols-3 gap-px bg-zinc-800 border border-zinc-800">
            {[
              { k: "90%", v: "Max advance" },
              { k: "24 hr", v: "Median wire" },
              { k: "2.5%", v: "Floor fee" },
            ].map((s) => (
              <div key={s.v} className="bg-zinc-950 p-5">
                <div
                  className="text-2xl text-white"
                  style={{ fontFamily: "'Instrument Serif', serif" }}
                >
                  {s.k}
                </div>
                <div className="label-xs mt-1 text-zinc-500">{s.v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
