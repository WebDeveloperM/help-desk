const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export const authConfig = {
  get apiBase() {
    return typeof window !== "undefined" && !API_BASE.startsWith("http")
      ? `${window.location.origin}${API_BASE}`
      : API_BASE;
  },
  get loginUrl() {
    return `${this.apiBase}/auth/login`;
  },
};
