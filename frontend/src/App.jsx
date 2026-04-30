import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import BrandRegister from "./pages/BrandRegister";
import Dashboard from "./pages/Dashboard";
import DealsList from "./pages/DealsList";
import DealNew from "./pages/DealNew";
import DealDetail from "./pages/DealDetail";
import Profile from "./pages/Profile";
import AdminPanel from "./pages/AdminPanel";
import BrandPortal from "./pages/BrandPortal";
import AppShell from "./components/AppShell";
import "./App.css";

/**
 * Protected — gates a route behind authentication.
 *
 * Props:
 *   role       → require an exact role ("admin" | "brand" | "creator")
 *   adminOnly  → legacy shorthand for role="admin"
 *
 * After login, users land on the right home for their role:
 *   admin   → /admin
 *   brand   → /brand-portal
 *   creator → /dashboard
 */
function Protected({ children, role, adminOnly }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-12 mono text-sm text-zinc-400">Authenticating…</div>;
  if (!user)   return <Navigate to="/login" replace />;

  // Resolve required role
  const requiredRole = role || (adminOnly ? "admin" : null);
  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to={roleHome(user.role)} replace />;
  }

  return children;
}

/** Default home path for each role after login. */
function roleHome(role) {
  if (role === "admin") return "/admin";
  if (role === "brand") return "/brand-portal";
  return "/dashboard";
}

/**
 * RoleRedirect — used on /login and /register to forward an already-logged-in
 * user to their correct home page instead of showing the auth form again.
 */
function RoleRedirect({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user)    return <Navigate to={roleHome(user.role)} replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{ style: { borderRadius: 0, border: "1px solid #E4E4E7" } }}
        />
        <Routes>
          {/* ── Public ──────────────────────────────────────────── */}
          <Route path="/" element={<Landing />} />

          <Route path="/login" element={
            <RoleRedirect><Login /></RoleRedirect>
          } />
          <Route path="/register" element={
            <RoleRedirect><Register /></RoleRedirect>
          } />
          <Route path="/brand/register" element={
            <RoleRedirect><BrandRegister /></RoleRedirect>
          } />

          {/* ── Creator routes (AppShell layout) ────────────────── */}
          <Route element={<Protected role="creator"><AppShell /></Protected>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/deals"     element={<DealsList />} />
            <Route path="/deals/new" element={<DealNew />} />
            <Route path="/deals/:id" element={<DealDetail />} />
            <Route path="/profile"   element={<Profile />} />
          </Route>

          {/* ── Admin (AppShell layout) ──────────────────────────── */}
          <Route element={<Protected role="admin"><AppShell /></Protected>}>
            <Route path="/admin" element={<AdminPanel />} />
          </Route>

          {/* ── Brand portal (standalone layout — no AppShell) ───── */}
          <Route path="/brand-portal" element={
            <Protected role="brand"><BrandPortal /></Protected>
          } />

          {/* ── Fallback ─────────────────────────────────────────── */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
