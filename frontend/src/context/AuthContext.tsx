import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import axios from 'axios';

const API = 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────
interface CommanderProfile {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

interface AuthContextValue {
  commander: CommanderProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

// ── Context ───────────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [commander, setCommander] = useState<CommanderProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true); // true until we've checked localStorage

  // On mount, restore session from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('db_token');
    const storedCommander = localStorage.getItem('db_commander');
    if (storedToken && storedCommander) {
      try {
        const parsed = JSON.parse(storedCommander);
        setToken(storedToken);
        setCommander(parsed);
        // Set default axios auth header for all subsequent requests
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      } catch {
        // Corrupted storage — clear it
        localStorage.removeItem('db_token');
        localStorage.removeItem('db_commander');
      }
    }
    setIsLoading(false);

    // Global 401 interceptor — if any request returns 401 (expired/invalid token),
    // clear the session so the user sees the login page instead of a broken UI
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          // Clear stale session
          localStorage.removeItem('db_token');
          localStorage.removeItem('db_commander');
          delete axios.defaults.headers.common['Authorization'];
          setToken(null);
          setCommander(null);
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await axios.post(`${API}/api/auth/login`, { email, password });
    const { access_token, commander: profile } = res.data;

    // Persist to localStorage so refresh keeps you logged in
    localStorage.setItem('db_token', access_token);
    localStorage.setItem('db_commander', JSON.stringify(profile));

    // Set axios default auth header
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

    setToken(access_token);
    setCommander(profile);
  }, []);

  const logout = useCallback(() => {
    // Fire the logout endpoint (best-effort, don't block on it)
    axios.post(`${API}/api/auth/logout`).catch(() => {});

    localStorage.removeItem('db_token');
    localStorage.removeItem('db_commander');
    delete axios.defaults.headers.common['Authorization'];

    setToken(null);
    setCommander(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        commander,
        token,
        isAuthenticated: !!token && !!commander,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
