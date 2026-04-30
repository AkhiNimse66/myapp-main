import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

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
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("mypay_token", r.data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
    return me.data;
  };

  const register = async (payload) => {
    const body = {
      email:            payload.email,
      password:         payload.password,
      name:             payload.full_name || payload.name,
      role:             payload.role || "creator",
      // creator-specific
      instagram_handle: payload.handle || payload.instagram_handle,
      // brand-specific (all optional at schema level; backend validates presence)
      signup_token:        payload.signup_token        || undefined,
      brand_website:       payload.brand_website       || undefined,
      brand_company_name:  payload.brand_company_name  || undefined,
      brand_industry:      payload.brand_industry      || undefined,
      brand_company_type:  payload.brand_company_type  || undefined,
      brand_gst_number:    payload.brand_gst_number    || undefined,
      brand_pan_number:    payload.brand_pan_number    || undefined,
      brand_phone:         payload.brand_phone         || undefined,
      brand_billing_email: payload.brand_billing_email || undefined,
    };
    // Strip undefined keys so Pydantic doesn't see null for required brand fields
    Object.keys(body).forEach(k => body[k] === undefined && delete body[k]);
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
