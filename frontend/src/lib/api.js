import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("mypay_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const money = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
};

// Compact INR: ₹2.5L, ₹10L, ₹1.2Cr
export const moneyCompact = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const v = Number(n);
  if (v >= 10_000_000) return `₹${(v / 10_000_000).toFixed(2)}Cr`;
  if (v >= 100_000)    return `₹${(v / 100_000).toFixed(1)}L`;
  if (v >= 1_000)      return `₹${(v / 1_000).toFixed(0)}K`;
  return `₹${v}`;
};

export const pct = (n, d = 1) => (n === null || n === undefined || isNaN(n) ? "—" : `${Number(n).toFixed(d)}%`);
export const compact = (n) => {
  if (!n) return "0";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
};
