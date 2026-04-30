import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { UploadCloud, ArrowRight } from "lucide-react";

export default function DealNew() {
  const nav = useNavigate();
  const [brands, setBrands] = useState([]);
  const [form, setForm] = useState({
    brand_id: "",
    deal_title: "",
    deal_amount: "",
    payment_terms_days: 60,
    contract_text: "",
  });
  const [fileMeta, setFileMeta] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.get("/brands").then(r => setBrands(r.data)); }, []);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File too large (max 10 MB).");
      return;
    }
    // Extract preview text for txt files (AI gets a hint)
    if (file.type.startsWith("text/")) {
      try { const t = await file.text(); setForm(f => ({ ...f, contract_text: t.slice(0, 4000) })); } catch {}
    }
    // Upload to object storage
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.post("/contracts/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setFileMeta({ id: r.data.id, name: file.name, mime: r.data.content_type, size: r.data.size });
      toast.success("Contract uploaded to secure storage.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload failed");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.brand_id) return toast.error("Select a brand");
    setLoading(true);
    try {
      const payload = {
        ...form,
        deal_amount: Number(form.deal_amount),
        contract_file_id: fileMeta?.id,
        contract_file_name: fileMeta?.name,
        contract_file_mime: fileMeta?.mime,
      };
      const r = await api.post("/deals", payload);
      toast.success("Deal created. Running underwriting…");
      const dealId = r.data.id;
      await api.post(`/deals/${dealId}/analyze`);
      toast.success("Risk score computed.");
      nav(`/deals/${dealId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Create failed");
    } finally { setLoading(false); }
  };

  return (
    <div data-testid="new-deal-root" className="max-w-3xl">
      <span className="label-xs">Underwriting / New Submission</span>
      <h1 className="serif text-5xl tracking-tight mt-2">Submit a contract.</h1>
      <p className="text-zinc-600 mt-3 text-sm">Upload a signed brand deal or paste the key terms. We score and quote in seconds.</p>

      <form onSubmit={submit} className="mt-10 space-y-8" data-testid="new-deal-form">
        <div>
          <label className="label-xs">Brand / Counterparty</label>
          <select
            data-testid="deal-brand"
            value={form.brand_id}
            onChange={(e) => setForm({ ...form, brand_id: e.target.value })}
            className="input-hair mt-1"
            required
          >
            <option value="">Select brand…</option>
            {brands.map(b => (
              <option key={b.id} value={b.id}>{b.name} · {b.tier} · {b.credit_rating}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label-xs">Deal Title</label>
          <input data-testid="deal-title" value={form.deal_title} onChange={(e) => setForm({ ...form, deal_title: e.target.value })} className="input-hair mt-1" required placeholder="Q1 Summer Campaign — 2x IG Reels" />
        </div>

        <div className="grid grid-cols-2 gap-8">
          <div>
            <label className="label-xs">Deal Amount (INR ₹)</label>
            <input data-testid="deal-amount" type="number" step="0.01" value={form.deal_amount} onChange={(e) => setForm({ ...form, deal_amount: e.target.value })} className="input-hair mt-1" required />
          </div>
          <div>
            <label className="label-xs">Payment Terms (days)</label>
            <select data-testid="deal-terms" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: Number(e.target.value) })} className="input-hair mt-1">
              {[15, 30, 45, 60, 75, 90].map(n => <option key={n} value={n}>Net {n}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="label-xs">Contract Text (optional paste)</label>
          <textarea data-testid="deal-contract-text" rows={5} value={form.contract_text} onChange={(e) => setForm({ ...form, contract_text: e.target.value })} className="input-hair mt-1 resize-y" placeholder="Paste key terms, deliverables, payment schedule…" />
        </div>

        <div>
          <label className="label-xs">Contract File (PDF / image, max 10 MB · stored in secure object storage)</label>
          <label className="mt-2 card-flat flex items-center gap-4 p-5 cursor-pointer hover:bg-zinc-50 transition-colors" data-testid="deal-file-drop">
            <UploadCloud className="w-6 h-6" />
            <div className="flex-1">
              <div className="text-sm">{fileMeta ? fileMeta.name : "Click to upload contract"}</div>
              <div className="mono text-xs text-zinc-500">{fileMeta ? `${(fileMeta.size/1024).toFixed(0)} KB · ${fileMeta.mime}` : "PDF, PNG, JPG, or TXT"}</div>
            </div>
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={onFile} className="hidden" data-testid="deal-file-input" />
          </label>
        </div>

        <button data-testid="deal-submit" type="submit" disabled={loading} className="btn-primary w-full justify-center">
          {loading ? "Underwriting…" : "Submit for underwriting"}
          {!loading && <ArrowRight className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
}
