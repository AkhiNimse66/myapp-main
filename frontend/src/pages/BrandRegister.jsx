import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

const INDUSTRIES = [
  "Beauty & Wellness", "Fashion & Apparel", "Consumer Electronics",
  "Food & Beverage", "Fitness & Sports", "Travel & Hospitality",
  "Finance & Fintech", "Education & EdTech", "D2C Personal Care",
  "Entertainment & Media", "Gaming", "Health & Pharma",
  "Automotive", "Real Estate", "FMCG", "Other",
];

const COMPANY_TYPES = ["Startup", "SME", "Mid-market", "Enterprise", "MNC", "Other"];

export default function BrandRegister() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();

  const [form, setForm] = useState({
    // Auth fields
    signup_token:        searchParams.get("token") || "",
    contact_name:        "",
    email:               "",
    password:            "",
    // Business identity
    brand_company_name:  "",
    brand_website:       "",
    brand_industry:      "",
    brand_company_type:  "",
    // KYC / compliance
    brand_gst_number:    "",
    brand_pan_number:    "",
    brand_phone:         "",
    brand_billing_email: "",
  });
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // 1 = token + basics, 2 = business details

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const onNext = (e) => {
    e.preventDefault();
    if (!form.signup_token.trim()) { toast.error("Signup token is required."); return; }
    if (!form.contact_name.trim()) { toast.error("Contact name is required."); return; }
    if (!form.email.trim())        { toast.error("Email is required."); return; }
    if (form.password.length < 8)  { toast.error("Password must be at least 8 characters."); return; }
    setStep(2);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({
        role:                "brand",
        name:                form.contact_name,
        email:               form.email,
        password:            form.password,
        signup_token:        form.signup_token.trim(),
        brand_company_name:  form.brand_company_name  || undefined,
        brand_website:       form.brand_website       || undefined,
        brand_industry:      form.brand_industry      || undefined,
        brand_company_type:  form.brand_company_type  || undefined,
        brand_gst_number:    form.brand_gst_number    || undefined,
        brand_pan_number:    form.brand_pan_number    || undefined,
        brand_phone:         form.brand_phone         || undefined,
        brand_billing_email: form.brand_billing_email || undefined,
      });
      toast.success("Brand account created. Welcome to My Pay.");
      nav("/brand-portal");
    } catch (err) {
      const msg = err?.response?.data?.detail;
      if (typeof msg === "string") toast.error(msg);
      else toast.error("Registration failed. Check your token and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* ── Left: form ─────────────────────────────────────────────── */}
      <div className="p-8 lg:p-16 flex flex-col">
        <Link to="/" className="serif text-3xl">My Pay</Link>

        <div className="flex-1 flex items-center">
          <div className="w-full max-w-md">
            {/* Step indicator */}
            <div className="flex items-center gap-3 mb-8">
              {[1, 2].map(s => (
                <React.Fragment key={s}>
                  <div className={`w-6 h-6 flex items-center justify-center text-xs mono border
                    ${step >= s ? "bg-zinc-950 text-white border-zinc-950" : "border-zinc-300 text-zinc-400"}`}>
                    {s}
                  </div>
                  {s < 2 && <div className={`flex-1 h-px ${step > s ? "bg-zinc-950" : "bg-zinc-200"}`} />}
                </React.Fragment>
              ))}
            </div>

            {step === 1 ? (
              <form onSubmit={onNext} data-testid="brand-register-step1">
                <span className="label-xs">Brand Onboarding · Step 1 of 2</span>
                <h1 className="serif text-5xl mt-3 tracking-tight">Access credentials.</h1>
                <p className="text-zinc-500 mt-2 text-sm">
                  You'll need a signup token from My Pay. Contact us if you don't have one.
                </p>

                <div className="mt-8 space-y-6">
                  <div>
                    <label className="label-xs">Signup Token <span className="text-red-500">*</span></label>
                    <input
                      data-testid="brand-token"
                      className="input-hair mt-1 font-mono text-sm"
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      value={form.signup_token}
                      onChange={set("signup_token")}
                      required
                    />
                    <p className="text-xs text-zinc-400 mt-1">Issued by the My Pay team. One-time use.</p>
                  </div>
                  <div>
                    <label className="label-xs">Contact Person's Name <span className="text-red-500">*</span></label>
                    <input data-testid="brand-contact-name" className="input-hair mt-1" value={form.contact_name} onChange={set("contact_name")} required />
                  </div>
                  <div>
                    <label className="label-xs">Work Email <span className="text-red-500">*</span></label>
                    <input data-testid="brand-email" type="email" className="input-hair mt-1" value={form.email} onChange={set("email")} required />
                  </div>
                  <div>
                    <label className="label-xs">Password <span className="text-red-500">*</span></label>
                    <input data-testid="brand-password" type="password" minLength={8} className="input-hair mt-1" value={form.password} onChange={set("password")} required />
                    <p className="text-xs text-zinc-400 mt-1">Minimum 8 characters.</p>
                  </div>
                </div>

                <button type="submit" className="btn-primary mt-10 w-full justify-center">
                  Continue →
                </button>
                <div className="mt-6 text-sm text-zinc-500">
                  Already registered? <Link to="/login" className="underline-ink text-zinc-950">Log in</Link>
                </div>
              </form>
            ) : (
              <form onSubmit={onSubmit} data-testid="brand-register-step2">
                <span className="label-xs">Brand Onboarding · Step 2 of 2</span>
                <h1 className="serif text-5xl mt-3 tracking-tight">Company details.</h1>
                <p className="text-zinc-500 mt-2 text-sm">
                  Used for invoice reconciliation and compliance. Fields marked optional can be filled later from your profile.
                </p>

                <div className="mt-8 space-y-6">
                  <div>
                    <label className="label-xs">Legal Company Name</label>
                    <input className="input-hair mt-1" placeholder="e.g. Nykaa Fashion Pvt Ltd" value={form.brand_company_name} onChange={set("brand_company_name")} />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="label-xs">Industry</label>
                      <select className="input-hair mt-1 bg-white" value={form.brand_industry} onChange={set("brand_industry")}>
                        <option value="">Select…</option>
                        {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="label-xs">Company Type</label>
                      <select className="input-hair mt-1 bg-white" value={form.brand_company_type} onChange={set("brand_company_type")}>
                        <option value="">Select…</option>
                        {COMPANY_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="label-xs">Website</label>
                    <input className="input-hair mt-1" placeholder="https://yourcompany.com" type="url" value={form.brand_website} onChange={set("brand_website")} />
                  </div>
                  <div className="border-t hair pt-6">
                    <div className="label-xs mb-4 text-zinc-400">Tax & Compliance — required for invoice reconciliation</div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="label-xs">GST Number</label>
                        <input className="input-hair mt-1 mono text-xs" placeholder="22AAAAA0000A1Z5" value={form.brand_gst_number} onChange={set("brand_gst_number")} maxLength={20} />
                      </div>
                      <div>
                        <label className="label-xs">PAN Number</label>
                        <input className="input-hair mt-1 mono text-xs" placeholder="AAAAA0000A" value={form.brand_pan_number} onChange={set("brand_pan_number")} maxLength={15} />
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="label-xs">Phone</label>
                      <input className="input-hair mt-1" type="tel" placeholder="+91 98765 43210" value={form.brand_phone} onChange={set("brand_phone")} />
                    </div>
                    <div>
                      <label className="label-xs">Billing Email</label>
                      <input className="input-hair mt-1" type="email" placeholder="accounts@company.com" value={form.brand_billing_email} onChange={set("brand_billing_email")} />
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 mt-10">
                  <button type="button" onClick={() => setStep(1)} className="btn-ghost flex-1 justify-center">← Back</button>
                  <button data-testid="brand-register-submit" type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
                    {loading ? "Creating account…" : "Complete registration →"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      {/* ── Right: luxury ink panel ────────────────────────────────── */}
      <div className="hidden lg:flex flex-col bg-zinc-950 text-white relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div className="relative z-10 flex flex-col h-full p-14 justify-between">
          <div className="label-xs text-zinc-500">My Pay · Brand Portal</div>

          <div>
            <div className="text-4xl leading-[1.1] tracking-tight font-light mb-10" style={{ fontFamily: "'Instrument Serif', serif" }}>
              Creator payments,<br />
              <span className="italic text-zinc-400">handled for you.</span>
            </div>
            <ol className="space-y-8 max-w-sm">
              {[
                ["Invoice visibility", "See every active deal your brand is a counterparty on."],
                ["Simple settlement", "Wire NEFT/RTGS to My Pay once. We handle the creator."],
                ["Single point of contact", "One account, one dashboard, all your creator partners."],
              ].map(([t, d], i) => (
                <li key={t} className="flex gap-5 items-start">
                  <div className="mono text-xs text-zinc-600 pt-1 shrink-0 w-6 text-right">{String(i + 1).padStart(2, "0")}</div>
                  <div className="border-l border-zinc-700 pl-5">
                    <div className="text-xl text-white leading-tight" style={{ fontFamily: "'Instrument Serif', serif" }}>{t}</div>
                    <div className="text-zinc-500 text-sm mt-1 leading-relaxed">{d}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="mono text-xs text-zinc-600 border-t border-zinc-800 pt-6">
            By registering you agree to My Pay's Brand Partner Agreement.
          </div>
        </div>
      </div>
    </div>
  );
}
