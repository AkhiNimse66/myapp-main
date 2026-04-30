// AuthContext moved to AuthContext.jsx — Vite resolves .jsx before .js (see vite.config.js).

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On mount — restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem("mypay_token");
    if (!token) { setLoading(false); return; }
    api.get("/auth/me")
      .then(r => setUser(r.data))
      .catch(() => localStorage.removeItem("mypay_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    // New API: POST /api/auth/login → { access_token, user_id, role, name }
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("mypay_token", r.data.access_token);
    // Hydrate full user profile
    const me = await api.get("/auth/me");
    setUser(me.data);
    return me.data;
  };

  const register = async (payload) => {
    // Normalise: frontend sends full_name + handle, API expects name + instagram_handle
    const body = {
      email: payload.email,
      password: payload.password,
      name: payload.full_name || payload.name,
      role: payload.role || "creator",
      instagram_handle: payload.handle || payload.instagram_handle,
    };
    // New API: POST /api/auth/register → { access_token, user_id, role, name }
    const r = await api.post("/auth/register", body);
    localStorage.setItem("mypay_token", r.data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
    return me.data;
  };

  const logout = () => {
    localStorage.removeItem("mypay_token");
    setUser(null);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
