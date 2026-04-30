import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money } from "../lib/api";
import { StatusChip } from "./Dashboard";

export default function DealsList() {
  const [deals, setDeals] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => { api.get("/deals").then(r => setDeals(r.data)); }, []);

  const filtered = filter === "all" ? deals : deals.filter(d => d.status === filter);

  return (
    <div data-testid="deals-list-root">
      <div className="flex items-end justify-between mb-8">
        <div>
          <span className="label-xs">Portfolio / Receivables</span>
          <h1 className="serif text-5xl tracking-tight mt-2">All deals.</h1>
        </div>
        <Link data-testid="deals-list-new" to="/deals/new" className="btn-primary">New deal →</Link>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {["all", "uploaded", "scored", "disbursed", "awaiting_payment", "repaid"].map(s => (
          <button
            key={s}
            data-testid={`filter-${s}`}
            onClick={() => setFilter(s)}
            className={`chip ${filter === s ? "border-zinc-950 text-zinc-950" : "text-zinc-500"} cursor-pointer`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="card-flat overflow-x-auto">
        <table className="dense w-full">
          <thead>
            <tr>
              <th>Ref</th>
              <th>Brand</th>
              <th>Title</th>
              <th>Status</th>
              <th className="num">Deal</th>
              <th className="num">Advance</th>
              <th className="num">Fee</th>
              <th className="num">Risk</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={10} className="text-center py-10 text-zinc-400 mono text-xs">No deals match filter.</td></tr>
            )}
            {filtered.map(d => (
              <tr key={d.id} className="row-hover">
                <td className="mono text-xs text-zinc-500">{d.id.slice(0, 8)}</td>
                <td>{d.brand_name}</td>
                <td className="max-w-xs truncate">{d.deal_title}</td>
                <td><StatusChip status={d.status} /></td>
                <td className="num">{money(d.deal_amount)}</td>
                <td className="num">{money(d.advance_amount)}</td>
                <td className="num">{money(d.discount_fee)}</td>
                <td className="num">{d.risk ? d.risk.risk_score.toFixed(1) : "—"}</td>
                <td className="mono text-xs text-zinc-500">{new Date(d.created_at).toLocaleDateString()}</td>
                <td><Link data-testid={`deal-open-${d.id}`} to={`/deals/${d.id}`} className="underline-ink mono text-xs">Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
