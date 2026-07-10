import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import type { Location } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Loader2,
  Lock,
  ScanFace,
  User,
} from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { getApiBase } from "@/api/client";

const BNPZID_ENABLED = import.meta.env.VITE_BNPZID_ENABLED === "true";

const KNOWN_AUTH_ERROR_KEYS = [
  "invalid_credentials",
  "network",
  "bnpzid_failed",
  "generic",
] as const;

type KnownAuthErrorKey = (typeof KNOWN_AUTH_ERROR_KEYS)[number];

const isKnownAuthError = (key: string): key is KnownAuthErrorKey =>
  (KNOWN_AUTH_ERROR_KEYS as readonly string[]).includes(key);

const Login = () => {
  const { authenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation(["auth", "common"]);

  const redirectTo =
    (location.state as { from?: Location })?.from?.pathname || "/dashboard";

  const [authErrorKey, setAuthErrorKey] = useState<KnownAuthErrorKey | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Surface bnpzID callback failures redirected as /login?error=bnpzid_*
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const error = params.get("error");
    if (!error) return;
    const key = error.startsWith("bnpzid")
      ? "bnpzid_failed"
      : isKnownAuthError(error)
        ? error
        : "generic";
    setAuthErrorKey(key);
    params.delete("error");
    const next = params.toString()
      ? `${location.pathname}?${params.toString()}`
      : location.pathname;
    window.history.replaceState(null, "", next);
  }, [location.search, location.pathname]);

  useEffect(() => {
    if (authenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [authenticated, navigate, redirectTo]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;
    setAuthErrorKey(null);
    setSubmitting(true);
    const result = await login(username.trim(), password);
    if (result.ok) {
      navigate(redirectTo, { replace: true });
      return;
    }
    const key =
      result.error && isKnownAuthError(result.error) ? result.error : "generic";
    setAuthErrorKey(key);
    setSubmitting(false);
  };

  const handleBnpzid = () => {
    const base = getApiBase().replace(/\/$/, "");
    window.location.href = `${base}/auth/bnpzid/login?next=${encodeURIComponent(
      redirectTo
    )}`;
  };

  const authError = authErrorKey
    ? t(`login.errors.${authErrorKey}`, { ns: "auth" })
    : null;

  const points = [
    t("login.point1", { ns: "auth" }),
    t("login.point2", { ns: "auth" }),
    t("login.point3", { ns: "auth" }),
  ];

  return (
    <ThemeProvider>
      <div className="relative min-h-screen w-full bg-background text-foreground">
        <div className="absolute right-4 top-4 z-20 flex items-center gap-2 sm:right-6 sm:top-6">
          <LanguageSwitcher variant="compact" align="right" />
          <ThemeToggle />
        </div>

        <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 lg:grid-cols-2">
          {/* Hero — warm emerald welcome (desktop) */}
          <aside className="relative hidden p-8 lg:flex xl:p-12">
            <div
              className="relative flex w-full flex-col justify-between overflow-hidden rounded-[2rem] p-10 text-white xl:p-14"
              style={{
                background:
                  "linear-gradient(155deg, hsl(160 70% 32%) 0%, hsl(168 72% 24%) 55%, hsl(174 68% 18%) 100%)",
              }}
            >
              <div
                className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl"
                aria-hidden
              />
              <div
                className="pointer-events-none absolute -bottom-24 -left-10 h-72 w-72 rounded-full bg-black/10 blur-3xl"
                aria-hidden
              />

              <div className="relative flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 text-lg font-bold backdrop-blur-sm">
                  HD
                </span>
                <span className="text-lg font-semibold tracking-tight">HelpDesk</span>
              </div>

              <div className="relative">
                <h1 className="font-display text-[2.75rem] leading-[1.05] tracking-tight xl:text-[3.25rem]">
                  {t("login.welcomeTitle", { ns: "auth" })}
                </h1>
                <p className="mt-5 max-w-sm text-[15px] leading-relaxed text-white/85">
                  {t("login.welcomeText", { ns: "auth" })}
                </p>

                <ul className="mt-9 flex flex-col gap-3.5">
                  {points.map((point) => (
                    <li key={point} className="flex items-center gap-3 text-[15px] text-white/90">
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-white/20">
                        <Check className="h-3.5 w-3.5" aria-hidden />
                      </span>
                      {point}
                    </li>
                  ))}
                </ul>
              </div>

              <p className="relative text-[13px] text-white/70">
                {t("login.footerNotice", { ns: "auth" })}
              </p>
            </div>
          </aside>

          {/* Form */}
          <main className="flex items-center justify-center px-6 py-12 sm:px-10">
            <div className="w-full max-w-md">
              {/* Brand on mobile */}
              <div className="mb-8 flex items-center gap-3 lg:hidden">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-accent text-lg font-bold text-accent-foreground">
                  HD
                </span>
                <span className="text-lg font-semibold tracking-tight">HelpDesk</span>
              </div>

              <div className="rounded-2xl border border-border bg-card p-7 shadow-lg sm:p-9">
                <h2 className="font-display text-3xl tracking-tight text-foreground">
                  {t("login.heading", { ns: "auth" })}
                </h2>
                <p className="mt-2.5 text-[14.5px] leading-relaxed text-muted-foreground">
                  {t("login.subheading", { ns: "auth" })}
                </p>

                {authError && (
                  <div
                    role="alert"
                    aria-live="assertive"
                    className="mt-5 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-[13.5px] leading-snug text-destructive"
                  >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                    <span>{authError}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor="login-username"
                      className="text-[13px] font-medium text-foreground"
                    >
                      {t("login.form.username", { ns: "auth" })}
                    </label>
                    <div className="relative">
                      <User
                        className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden
                      />
                      <input
                        id="login-username"
                        name="username"
                        type="text"
                        autoComplete="username"
                        required
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder={t("login.form.usernamePlaceholder", { ns: "auth" })}
                        className="h-12 w-full rounded-xl border border-input bg-background pl-11 pr-4 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor="login-password"
                      className="text-[13px] font-medium text-foreground"
                    >
                      {t("login.form.password", { ns: "auth" })}
                    </label>
                    <div className="relative">
                      <Lock
                        className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden
                      />
                      <input
                        id="login-password"
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder={t("login.form.passwordPlaceholder", { ns: "auth" })}
                        className="h-12 w-full rounded-xl border border-input bg-background pl-11 pr-4 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="mt-1 inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-accent text-[15px] font-semibold text-accent-foreground shadow-sm transition-[filter,transform] hover:brightness-[1.06] active:scale-[0.99] focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/25 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                        {t("login.form.submitting", { ns: "auth" })}
                      </>
                    ) : (
                      <>
                        {t("login.form.submit", { ns: "auth" })}
                        <ArrowRight className="h-4 w-4" aria-hidden />
                      </>
                    )}
                  </button>
                </form>

                {BNPZID_ENABLED && (
                  <>
                    <div
                      className="my-6 flex items-center gap-3 text-[12px] text-muted-foreground"
                      aria-hidden
                    >
                      <span className="h-px flex-1 bg-border" />
                      {t("login.bnpzid.divider", { ns: "auth" })}
                      <span className="h-px flex-1 bg-border" />
                    </div>
                    <button
                      type="button"
                      onClick={handleBnpzid}
                      className="inline-flex h-12 w-full items-center justify-center gap-2.5 rounded-xl border border-border bg-background text-[14.5px] font-medium text-foreground transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                      aria-label={t("login.bnpzid.buttonAria", { ns: "auth" })}
                    >
                      <ScanFace className="h-5 w-5 text-accent" aria-hidden />
                      {t("login.bnpzid.button", { ns: "auth" })}
                    </button>
                  </>
                )}
              </div>

              <p className="mt-6 text-center text-[12.5px] text-muted-foreground">
                {t("login.footerNotice", { ns: "auth" })}
              </p>
            </div>
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
};

export default Login;
