import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";

type ProtectedRouteProps = {
  children: React.ReactNode;
};

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { authenticated, loading } = useAuth();
  const location = useLocation();
  const { t } = useTranslation("auth");

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <div className="space-y-2 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-muted border-t-accent mx-auto" />
          <p className="text-sm text-muted-foreground">{t("session.loading")}</p>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
