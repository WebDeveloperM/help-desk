const TOKEN_KEY = 'helpdesk_access_token';
const REFRESH_KEY = 'helpdesk_refresh_token';
const ID_TOKEN_KEY = 'helpdesk_id_token';
const EXPIRES_AT_KEY = 'helpdesk_expires_at';

export const AUTH_SESSION_UPDATED_EVENT = 'helpdesk:auth-session-updated';

const BROADCAST_CHANNEL_NAME = 'helpdesk-auth';

export type AuthSessionEventDetail = {
  token: string | undefined;
  source: 'local' | 'remote';
};

type BroadcastMessage = { type: 'cleared' };

function readStorageValue(key: string): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const sessionValue = sessionStorage.getItem(key);
  if (sessionValue) return sessionValue;
  const legacyLocalValue = localStorage.getItem(key);
  return legacyLocalValue ?? undefined;
}

let broadcastChannel: BroadcastChannel | null | undefined;

function getBroadcastChannel(): BroadcastChannel | null {
  if (broadcastChannel !== undefined) return broadcastChannel;
  if (typeof window === 'undefined' || typeof BroadcastChannel === 'undefined') {
    broadcastChannel = null;
    return null;
  }
  broadcastChannel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
  broadcastChannel.addEventListener('message', (event: MessageEvent<BroadcastMessage>) => {
    if (event.data?.type === 'cleared') {
      // Another tab logged out — clear our own session and notify listeners.
      clearStorageSilent();
      dispatchLocal(undefined, 'remote');
    }
  });
  return broadcastChannel;
}

function dispatchLocal(token: string | undefined, source: 'local' | 'remote'): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent<AuthSessionEventDetail>(AUTH_SESSION_UPDATED_EVENT, {
      detail: { token, source },
    })
  );
}

export function getStoredAccessToken(): string | undefined {
  return readStorageValue(TOKEN_KEY);
}

export function getStoredRefreshToken(): string | undefined {
  return readStorageValue(REFRESH_KEY);
}

export function getStoredIdToken(): string | undefined {
  return readStorageValue(ID_TOKEN_KEY);
}

export function getStoredExpiresAt(): number | undefined {
  const raw = readStorageValue(EXPIRES_AT_KEY);
  if (!raw) return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function isAccessTokenExpiring(bufferMs = 0): boolean {
  const expiresAt = getStoredExpiresAt();
  if (expiresAt === undefined) return false;
  return Date.now() + bufferMs >= expiresAt;
}

export function storeTokens(
  accessToken: string,
  refreshToken: string | undefined,
  expiresInSeconds: number,
  idToken?: string
): void {
  if (typeof window === 'undefined') return;
  const expiresIn =
    Number.isFinite(expiresInSeconds) && expiresInSeconds > 0
      ? expiresInSeconds
      : 300;

  sessionStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    sessionStorage.setItem(REFRESH_KEY, refreshToken);
  } else {
    sessionStorage.removeItem(REFRESH_KEY);
  }
  // OIDC refresh responses don't include id_token, so an undefined argument
  // means "no change" — preserve what login stored. We still need it later for
  // Keycloak logout (id_token_hint). Only an explicit empty string clears.
  if (idToken !== undefined) {
    if (idToken) {
      sessionStorage.setItem(ID_TOKEN_KEY, idToken);
    } else {
      sessionStorage.removeItem(ID_TOKEN_KEY);
    }
  }
  sessionStorage.setItem(
    EXPIRES_AT_KEY,
    String(Date.now() + expiresIn * 1000)
  );

  // Cleanup legacy keys from localStorage so stale tokens are never reused.
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ID_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);

  dispatchLocal(accessToken, 'local');
}

function clearStorageSilent(): void {
  if (typeof window === 'undefined') return;

  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(ID_TOKEN_KEY);
  sessionStorage.removeItem(EXPIRES_AT_KEY);

  // Cleanup legacy keys from localStorage as well.
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ID_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

export function clearStoredTokens(): void {
  if (typeof window === 'undefined') return;
  clearStorageSilent();
  // Notify other tabs so cross-tab logout converges.
  getBroadcastChannel()?.postMessage({ type: 'cleared' } satisfies BroadcastMessage);
  dispatchLocal(undefined, 'local');
}

// Set up the cross-tab listener eagerly so remote logouts reach this tab even
// before the AuthProvider has mounted.
getBroadcastChannel();
