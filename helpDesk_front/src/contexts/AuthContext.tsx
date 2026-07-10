import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { authorizedFetch, getApiBase, getValidAccessToken } from "@/api/client";
import {
  AUTH_SESSION_UPDATED_EVENT,
  type AuthSessionEventDetail,
  clearStoredTokens,
  getStoredAccessToken,
  storeTokens,
} from "@/lib/authSession";

export type AuthProfile = {
  sub: string;
  email: string;
  name: string | null;
  preferred_username: string;
  username?: string; // alias for preferred_username
  roles: string[];
};

export type LoginResult = { ok: boolean; error?: string };

type AuthContextValue = {
  authenticated: boolean;
  loading: boolean;
  token: string | undefined;
  profile: AuthProfile | undefined;
  login: (username: string, password: string) => Promise<LoginResult>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const normalizeExpiresIn = (raw: unknown): number => {
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) return 43200;
  return Math.floor(value);
};

// Parse `#access_token=...&expires_in=...` from a redirect-based SSO callback
// (bnpzID). Returns the access token if present, after storing tokens.
const consumeHashTokens = (): string | undefined => {
  if (typeof window === "undefined") return undefined;
  const hash = window.location.hash;
  if (!hash || !hash.includes("access_token")) return undefined;

  const params: Record<string, string> = {};
  for (const pair of hash.slice(1).split("&")) {
    const [k, v] = pair.split("=");
    if (k && v) params[decodeURIComponent(k)] = decodeURIComponent(v);
  }

  const accessToken = params.access_token;
  // Clean the token out of the URL regardless, so it isn't left in history.
  window.history.replaceState(
    null,
    "",
    window.location.pathname + window.location.search
  );

  if (!accessToken) return undefined;
  storeTokens(accessToken, undefined, normalizeExpiresIn(params.expires_in));
  return accessToken;
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | undefined>();
  const [profile, setProfile] = useState<AuthProfile | undefined>();

  const resetAuthState = useCallback(() => {
    setAuthenticated(false);
    setToken(undefined);
    setProfile(undefined);
  }, []);

  const fetchProfile = useCallback(async (accessToken: string) => {
    const res = await authorizedFetch(`${getApiBase()}/auth/me`, {
      token: accessToken,
    });
    if (!res.ok) return undefined;
    const data = await res.json();
    const username = data.preferred_username ?? data.email ?? "";
    return {
      sub: data.sub,
      email: data.email ?? "",
      name: data.name ?? null,
      preferred_username: username,
      username,
      roles: data.roles ?? [],
    } satisfies AuthProfile;
  }, []);

  const init = useCallback(async () => {
    if (typeof window === "undefined") return;

    // Pick up a token delivered via URL hash by the bnpzID SSO callback.
    consumeHashTokens();

    try {
      const validToken = await getValidAccessToken();
      if (!validToken) {
        clearStoredTokens();
        resetAuthState();
        return;
      }

      const p = await fetchProfile(validToken);
      if (!p) {
        clearStoredTokens();
        resetAuthState();
        return;
      }

      setToken(validToken);
      setAuthenticated(true);
      setProfile(p);
    } catch {
      clearStoredTokens();
      resetAuthState();
    } finally {
      setLoading(false);
    }
  }, [fetchProfile, resetAuthState]);

  useEffect(() => {
    void init();
  }, [init]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleSessionUpdate = (event: Event) => {
      const detail = (event as CustomEvent<AuthSessionEventDetail>).detail;
      const nextToken = detail?.token ?? getStoredAccessToken();
      if (!nextToken) {
        resetAuthState();
        return;
      }
      setToken(nextToken);
      setAuthenticated(true);
    };

    window.addEventListener(
      AUTH_SESSION_UPDATED_EVENT,
      handleSessionUpdate as EventListener
    );
    return () => {
      window.removeEventListener(
        AUTH_SESSION_UPDATED_EVENT,
        handleSessionUpdate as EventListener
      );
    };
  }, [resetAuthState]);

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      try {
        const res = await fetch(`${getApiBase()}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        if (res.status === 401) {
          return { ok: false, error: "invalid_credentials" };
        }
        if (!res.ok) {
          return { ok: false, error: "generic" };
        }

        const data = await res.json();
        if (!data.access_token) {
          return { ok: false, error: "generic" };
        }

        storeTokens(
          data.access_token,
          undefined,
          normalizeExpiresIn(data.expires_in)
        );

        const p = await fetchProfile(data.access_token);
        if (!p) {
          clearStoredTokens();
          resetAuthState();
          return { ok: false, error: "generic" };
        }

        setToken(data.access_token);
        setAuthenticated(true);
        setProfile(p);
        return { ok: true };
      } catch {
        return { ok: false, error: "network" };
      }
    },
    [fetchProfile, resetAuthState]
  );

  const logout = useCallback(() => {
    clearStoredTokens();
    resetAuthState();
    window.location.href = "/login";
  }, [resetAuthState]);

  const value = useMemo(
    () => ({
      authenticated,
      loading,
      token,
      profile,
      login,
      logout,
    }),
    [authenticated, loading, login, logout, profile, token]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
