import {
  apiErrorMessage,
  authorizedFetch,
  getApiBase,
  networkErrorMessage,
} from '@/api/client';
import i18n from '@/i18n';

const tErr = (key: string): string => i18n.t(key, { ns: 'errors' });

export type CurrentUser = {
  id: string;
  keycloak_id: string;
  email: string;
  full_name: string;
  department_id?: string | null;
  [key: string]: unknown;
};

export type GetCurrentUserResult =
  | { ok: true; data: CurrentUser }
  | { ok: false; error: string; status?: number };

export async function getCurrentUser(options?: { signal?: AbortSignal }): Promise<GetCurrentUserResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/users/me`, { signal: options?.signal });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          fallback: tErr('users.load_profile'),
        }),
        status: response.status,
      };
    }
    const data: CurrentUser = await response.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.load_profile')) };
  }
}

export type UserRole = 'user' | 'department_head' | 'executor' | 'admin';

const USER_ROLES: readonly UserRole[] = ['user', 'department_head', 'executor', 'admin'];

const parseRole = (value: unknown): UserRole =>
  USER_ROLES.includes(value as UserRole) ? (value as UserRole) : 'user';

export type AdminUser = {
  id: string;
  keycloak_id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  tabel_number?: string | null;
  department_id?: string | null;
  position?: string | null;
  phone?: string | null;
  is_active: boolean;
};

export type AdminUserListResponse = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type ListUsersResult =
  | { ok: true; data: AdminUserListResponse }
  | { ok: false; error: string; status?: number };

const parseAdminUser = (u: Record<string, unknown>): AdminUser => ({
  id: String(u?.id ?? ''),
  keycloak_id: String(u?.keycloak_id ?? ''),
  username: String(u?.username ?? ''),
  email: String(u?.email ?? ''),
  full_name: String(u?.full_name ?? ''),
  role: parseRole(u?.role),
  tabel_number: u?.tabel_number != null ? String(u.tabel_number) : null,
  department_id: u?.department_id != null ? String(u.department_id) : null,
  position: u?.position != null ? String(u.position) : null,
  phone: u?.phone != null ? String(u.phone) : null,
  is_active: Boolean(u?.is_active ?? true),
});

export async function listUsers(
  params?: { page?: number; page_size?: number; is_active?: boolean; signal?: AbortSignal }
): Promise<ListUsersResult> {
  const base = getApiBase();
  const sp = new URLSearchParams();
  sp.set('page', String(params?.page ?? 1));
  sp.set('page_size', String(params?.page_size ?? 100));
  if (params?.is_active !== undefined) sp.set('is_active', String(params.is_active));

  try {
    const response = await authorizedFetch(`${base}/users?${sp.toString()}`, {
      signal: params?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.list_forbidden'),
          fallback: tErr('users.load_list'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const list = Array.isArray(raw) ? raw : raw?.items ?? [];
    const data: AdminUserListResponse = {
      items: list.map(parseAdminUser),
      total: typeof raw?.total === 'number' ? raw.total : list.length,
      page: typeof raw?.page === 'number' ? raw.page : 1,
      page_size: typeof raw?.page_size === 'number' ? raw.page_size : 100,
      pages: typeof raw?.pages === 'number' ? raw.pages : 1,
    };
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.load_list')) };
  }
}

export type AdminCreateUserInput = {
  username: string;
  email: string;
  full_name: string;
  full_name_uz?: string | null;
  password: string;
  role: 'user' | 'department_head' | 'executor' | 'admin';
  tabel_number?: string | null;
  department_id?: string | null;
  position?: string | null;
  position_uz?: string | null;
  phone?: string | null;
};

export type UserMutationResult =
  | { ok: true; data: AdminUser }
  | { ok: false; error: string; status?: number };

export async function adminCreateUser(
  input: AdminCreateUserInput,
  options?: { signal?: AbortSignal }
): Promise<UserMutationResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.create_forbidden'),
          400: tErr('users.email_taken'),
          502: tErr('users.keycloak_sync_failed'),
          fallback: tErr('users.create_failed'),
        }),
        status: response.status,
      };
    }
    return { ok: true, data: parseAdminUser(await response.json()) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.create_failed')) };
  }
}

export type ResetPasswordResult =
  | { ok: true; data: { password: string } }
  | { ok: false; error: string; status?: number };

export async function resetUserPassword(
  userId: string,
  password: string,
  options?: { signal?: AbortSignal }
): Promise<ResetPasswordResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(
      `${base}/users/${encodeURIComponent(userId)}/reset-password`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
        signal: options?.signal,
      }
    );
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.update_forbidden'),
          404: tErr('users.not_found'),
          502: tErr('users.keycloak_sync_failed'),
          fallback: tErr('users.reset_password_failed'),
        }),
        status: response.status,
      };
    }
    const json = await response.json();
    return { ok: true, data: { password: String(json?.password ?? password) } };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.reset_password_failed')) };
  }
}

export async function updateUserDepartment(
  userId: string,
  departmentId: string | null,
  options?: { signal?: AbortSignal }
): Promise<UserMutationResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/users/${encodeURIComponent(userId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ department_id: departmentId }),
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.update_forbidden'),
          404: tErr('users.not_found'),
          502: tErr('users.keycloak_sync_failed'),
          fallback: tErr('users.update_failed'),
        }),
        status: response.status,
      };
    }
    return { ok: true, data: parseAdminUser(await response.json()) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.update_failed')) };
  }
}

export type UpdateUserInput = {
  full_name?: string;
  email?: string;
  role?: UserRole;
  tabel_number?: string | null;
  department_id?: string | null;
  position?: string | null;
  phone?: string | null;
  is_active?: boolean;
};

export async function updateUser(
  userId: string,
  input: UpdateUserInput,
  options?: { signal?: AbortSignal }
): Promise<UserMutationResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/users/${encodeURIComponent(userId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.update_forbidden'),
          404: tErr('users.not_found'),
          409: tErr('users.already_exists'),
          fallback: tErr('users.update_failed'),
        }),
        status: response.status,
      };
    }
    return { ok: true, data: parseAdminUser(await response.json()) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.update_failed')) };
  }
}

export type DeleteUserResult =
  | { ok: true }
  | { ok: false; error: string; status?: number };

export async function deleteUser(
  userId: string,
  options?: { signal?: AbortSignal }
): Promise<DeleteUserResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.delete_forbidden'),
          404: tErr('users.not_found'),
          fallback: tErr('users.delete_failed'),
        }),
        status: response.status,
      };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.delete_failed')) };
  }
}

export type UserActivity = { created: number; active: number; completed: number };
export type UserActivityMap = Record<string, UserActivity>;
export type GetUserActivityResult =
  | { ok: true; data: UserActivityMap }
  | { ok: false; error: string; status?: number };

/** Per-user ticket activity across all tickets (admin only). */
export async function getUserActivity(options?: {
  signal?: AbortSignal;
}): Promise<GetUserActivityResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/tickets/user-activity`, {
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('users.list_forbidden'),
          fallback: tErr('users.load_list'),
        }),
        status: response.status,
      };
    }
    const raw = (await response.json()) as Record<string, Partial<UserActivity>>;
    const data: UserActivityMap = {};
    for (const [id, v] of Object.entries(raw ?? {})) {
      data[id] = {
        created: Number(v?.created ?? 0),
        active: Number(v?.active ?? 0),
        completed: Number(v?.completed ?? 0),
      };
    }
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('users.load_list')) };
  }
}
