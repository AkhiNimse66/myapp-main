// App moved to App.jsx — Vite resolves .jsx before .js (see vite.config.js resolve.extensions).
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import DealsList from "./pages/DealsList";
import DealNew from "./pages/DealNew";
import DealDetail from "./pages/DealDetail";
import Profile from "./pages/Profile";
import AdminPanel from "./pages/AdminPanel";
import AppShell from "./components/AppShell";
import "./App.css";

function Protected({ children, adminOnly }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-12 mono text-sm">Authenticating…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ style: { borderRadius: 0, border: "1px solid #E4E4E7" } }} />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<Protected><AppShell /></Protected>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/deals" element={<DealsList />} />
            <Route path="/deals/new" element={<DealNew />} />
            <Route path="/deals/:id" element={<DealDetail />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/admin" element={<Protected adminOnly><AdminPanel /></Protected>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
