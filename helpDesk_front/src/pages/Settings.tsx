import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type React from "react";
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from "@/components/ui/sidebar";
import { authorizedFetch, getApiBase } from "@/api/client";
import { ThemeProvider } from "../contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import Sidebar from "../components/dashboard/Sidebar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Shield,
  Mail,
  Phone,
  User,
  Hash,
  RefreshCw,
  LogOut,
  KeyRound,
  Building2,
  CheckCircle2,
  AlertCircle,
  Calendar,
} from "lucide-react";

type UserRoleResponse = {
  user_id: string;
  role: string;
  department_id: string | null;
  created_at: string;
  updated_at: string;
};

type UserResponse = {
  id: string;
  keycloak_id: string;
  email: string;
  full_name: string;
  full_name_uz?: string | null;
  ad_username?: string | null;
  department_id?: string | null;
  position?: string | null;
  position_uz?: string | null;
  phone?: string | null;
  ad_guid?: string | null;
  ad_distinguished_name?: string | null;
  email_verified: boolean;
  is_active: boolean;
  last_sync_at?: string | null;
  roles: UserRoleResponse[];
  created_at: string;
  updated_at: string;
};

const InfoRow = ({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | null | undefined;
  icon: React.ReactNode;
}) => (
  <div className="flex items-start gap-3 rounded-xl border border-border bg-card px-3.5 py-2.5" role="listitem">
    <div className="mt-0.5 text-accent shrink-0" aria-hidden>{icon}</div>
    <div>
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="text-[15px] font-medium text-foreground">
        {value && value.trim() ? value : "—"}
      </div>
    </div>
  </div>
);

const SettingsContent = () => {
  const { open } = useSidebar();
  const { logout, token, profile } = useAuth();
  const { t } = useTranslation("settings");
  const { t: tCommon } = useTranslation("common");
  const { t: tErr } = useTranslation("errors");

  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const checkDesktop = () => {
      setIsDesktop(window.innerWidth >= 768);
    };
    checkDesktop();
    window.addEventListener("resize", checkDesktop);
    return () => window.removeEventListener("resize", checkDesktop);
  }, []);

  const fetchUser = useCallback(async () => {
    if (!token) {
      setError(tCommon("states.noToken"));
      setLoading(false);
      return;
    }

    setRefreshing(true);
    setError(null);

    try {
      const response = await authorizedFetch(`${getApiBase()}/users/me`, {
        token,
      });

      if (!response.ok) {
        const message = response.status === 401 ? tErr("session_expired") : tErr("users.load_profile");
        throw new Error(message);
      }

      const data: UserResponse = await response.json();
      setUser(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("unknownError");
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, t, tCommon, tErr]);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  const roleLabels = useMemo(
    () =>
      user?.roles?.map((r) => (r.department_id ? `${r.role} ${t("sections.roles.departmentSuffix", { id: r.department_id })}` : r.role)) || [],
    [user?.roles, t],
  );

  const layoutWidth = useMemo(
    () => ({
      width: isDesktop ? `calc(100vw - ${open ? "300px" : "80px"})` : "100%",
      marginLeft: isDesktop ? (open ? "300px" : "80px") : "0",
    }),
    [isDesktop, open],
  );

  return (
    <div className="flex min-h-screen bg-background font-sans w-full">
      {/* Sidebar - Desktop only */}
      <div className="hidden md:block">
        <ShadcnSidebar>
          <Sidebar activeNav="Settings" onNavChange={() => {}} />
        </ShadcnSidebar>
      </div>

      {/* Main Content */}
      <main
        className={cn(
          "p-4 md:p-6 overflow-auto transition-all duration-300 pt-14 md:pt-6 min-h-screen pb-20 md:pb-6",
        )}
        style={layoutWidth}
        aria-label={t("page.aria")}
      >
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="font-display text-3xl font-bold text-foreground mb-1" id="settings-heading">{t("page.title")}</h1>
              <p className="text-[15px] text-muted-foreground" id="settings-description">
                {t("page.description")}
              </p>
            </div>
            <div className="flex flex-wrap gap-2" role="group" aria-label={t("actions.groupAria")}>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 h-10 rounded-xl border border-border bg-card px-4 text-sm font-semibold hover:bg-secondary transition-colors disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                onClick={() => void fetchUser()}
                disabled={refreshing}
                aria-label={t("actions.refreshAria")}
              >
                <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} aria-hidden />
                {t("actions.refresh")}
              </button>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 h-10 rounded-xl bg-destructive text-destructive-foreground px-4 text-sm font-semibold shadow-sm hover:opacity-90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
                onClick={() => void logout()}
                aria-label={t("actions.logoutAria")}
              >
                <LogOut className="h-4 w-4" aria-hidden />
                {t("actions.logout")}
              </button>
            </div>
          </div>

          {loading ? (
            <Card role="status" aria-live="polite">
              <CardContent className="py-10 text-center text-muted-foreground">
                <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-4 border-muted border-t-accent" aria-hidden />
                {t("loading")}
              </CardContent>
            </Card>
          ) : error ? (
            <Card className="border-destructive/40 bg-destructive/10" role="alert">
              <CardContent className="py-6 flex items-start gap-3 text-destructive">
                <AlertCircle className="h-5 w-5 mt-1 shrink-0" aria-hidden />
                <div>
                  <div className="font-semibold">{t("loadFailed")}</div>
                  <div className="text-sm text-destructive/90">{error}</div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <User className="h-5 w-5 text-accent" />
                    <CardTitle>{t("sections.main.title")}</CardTitle>
                  </div>
                  <CardDescription>{t("sections.main.description")}</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3" role="list">
                  <InfoRow label={t("fields.fullName")} value={user?.full_name} icon={<User className="h-4 w-4" />} />
                  <InfoRow label={t("fields.email")} value={user?.email} icon={<Mail className="h-4 w-4" />} />
                  <InfoRow label={t("fields.keycloakId")} value={user?.keycloak_id} icon={<KeyRound className="h-4 w-4" />} />
                  <InfoRow label={t("fields.adUsername")} value={user?.ad_username} icon={<Hash className="h-4 w-4" />} />
                  <InfoRow label={t("fields.phone")} value={user?.phone} icon={<Phone className="h-4 w-4" />} />
                  <InfoRow label={t("fields.position")} value={user?.position} icon={<Shield className="h-4 w-4" />} />
                  <InfoRow label={t("fields.departmentId")} value={user?.department_id} icon={<Building2 className="h-4 w-4" />} />
                  <InfoRow
                    label={t("fields.emailVerified")}
                    value={user?.email_verified ? t("fields.emailVerifiedYes") : t("fields.emailVerifiedNo")}
                    icon={user?.email_verified ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-accent" />
                    <CardTitle>{t("sections.roles.title")}</CardTitle>
                  </div>
                  <CardDescription>{t("sections.roles.description")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {roleLabels.length === 0 ? (
                    <div className="text-sm text-muted-foreground">{t("sections.roles.none")}</div>
                  ) : (
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {roleLabels.map((role) => (
                        <li key={role} className="rounded-xl border border-border bg-card px-3.5 py-2.5 text-[15px] font-medium">
                          {role}
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-accent" />
                    <CardTitle>{t("sections.service.title")}</CardTitle>
                  </div>
                  <CardDescription>{t("sections.service.description")}</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3" role="list">
                  <InfoRow
                    label={t("fields.createdAt")}
                    value={user?.created_at ? new Date(user.created_at).toLocaleString() : undefined}
                    icon={<CalendarIcon />}
                  />
                  <InfoRow
                    label={t("fields.updatedAt")}
                    value={user?.updated_at ? new Date(user.updated_at).toLocaleString() : undefined}
                    icon={<CalendarIcon />}
                  />
                  <InfoRow
                    label={t("fields.lastSync")}
                    value={user?.last_sync_at ? new Date(user.last_sync_at).toLocaleString() : "—"}
                    icon={<RefreshCw className="h-4 w-4" />}
                  />
                  <InfoRow
                    label={t("fields.status")}
                    value={user?.is_active ? t("fields.statusActive") : t("fields.statusInactive")}
                    icon={<Shield className="h-4 w-4" />}
                  />
                  <InfoRow
                    label={t("fields.tokenEmail")}
                    value={profile?.email}
                    icon={<Mail className="h-4 w-4" />}
                  />
                  <InfoRow
                    label={t("fields.tokenUsername")}
                    value={profile?.username}
                    icon={<User className="h-4 w-4" />}
                  />
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

const CalendarIcon = () => <Calendar className="h-4 w-4" />;

const Settings = () => {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <SettingsContent />
      </SidebarProvider>
    </ThemeProvider>
  );
};

export default Settings;
