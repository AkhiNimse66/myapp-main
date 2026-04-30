import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, LayoutGrid, FileText, UploadCloud, ShieldCheck, UserCircle } from "lucide-react";

export default function AppShell() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const linkCls = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2 text-sm transition-colors ${isActive ? "bg-zinc-950 text-white" : "text-zinc-700 hover:bg-zinc-100"}`;

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b hair sticky top-0 z-20 bg-white">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-baseline gap-2" data-testid="app-logo">
              <span className="serif text-3xl leading-none">My Pay</span>
              <span className="label-xs">/ creator receivables</span>
            </div>
            <nav className="hidden md:flex items-center gap-1">
              <NavLink data-testid="nav-dashboard" to="/dashboard" className={linkCls}><LayoutGrid className="w-4 h-4" /> Dashboard</NavLink>
              <NavLink data-testid="nav-deals" to="/deals" className={linkCls}><FileText className="w-4 h-4" /> Deals</NavLink>
              <NavLink data-testid="nav-new-deal" to="/deals/new" className={linkCls}><UploadCloud className="w-4 h-4" /> New Deal</NavLink>
              {user?.role === "admin" && (
                <NavLink data-testid="nav-admin" to="/admin" className={linkCls}><ShieldCheck className="w-4 h-4" /> Risk Ops</NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <NavLink data-testid="nav-profile" to="/profile" className="flex items-center gap-2 text-sm text-zinc-700 hover:text-zinc-950">
              <UserCircle className="w-5 h-5" />
              <span className="mono text-xs">{user?.email}</span>
            </NavLink>
            <button data-testid="logout-btn" onClick={() => { logout(); nav("/login"); }} className="btn-ghost text-xs px-3 py-2">
              <LogOut className="w-3.5 h-3.5 inline-block mr-1" /> Logout
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-[1400px] mx-auto px-6 py-8">
        <Outlet />
      </main>
      <footer className="border-t hair">
        <div className="max-w-[1400px] mx-auto px-6 py-6 flex justify-between items-center">
          <span className="label-xs">© My Pay 2026 / AR Financing for the Creator Economy</span>
          <span className="mono text-xs text-zinc-400">v0.1 · ISO 20022 compliant</span>
        </div>
      </footer>
    </div>
  );
}
