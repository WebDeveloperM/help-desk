import {
  apiErrorMessage,
  authorizedFetch,
  getApiBase,
  networkErrorMessage,
} from '@/api/client';
import i18n from '@/i18n';

const tErr = (key: string): string => i18n.t(key, { ns: 'errors' });

export type Department = {
  id: string;
  number: number;
  name: string;
  code: string;
  name_uz?: string | null;
  parent_id?: string | null;
  head_user_id?: string | null;
  ad_path?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type DepartmentListResponse = {
  items: Department[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type ListDepartmentsResult =
  | { ok: true; data: DepartmentListResponse }
  | { ok: false; error: string; status?: number };

const parseDepartment = (d: Record<string, unknown>): Department => ({
  id: String(d?.id ?? ''),
  number: typeof d?.number === 'number' ? d.number : Number(d?.number ?? 0),
  name: String(d?.name ?? ''),
  code: String(d?.code ?? ''),
  name_uz: d?.name_uz != null ? String(d.name_uz) : null,
  parent_id: d?.parent_id != null ? String(d.parent_id) : null,
  head_user_id: d?.head_user_id != null ? String(d.head_user_id) : null,
  ad_path: d?.ad_path != null ? String(d.ad_path) : null,
  is_active: Boolean(d?.is_active ?? true),
  created_at: String(d?.created_at ?? ''),
  updated_at: String(d?.updated_at ?? ''),
});

export async function listDepartments(
  params?: { page?: number; page_size?: number; is_active?: boolean; signal?: AbortSignal }
): Promise<ListDepartmentsResult> {
  const base = getApiBase();
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(params?.page ?? 1));
  searchParams.set('page_size', String(params?.page_size ?? 100));
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));

  try {
    const response = await authorizedFetch(`${base}/departments?${searchParams.toString()}`, {
      signal: params?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          fallback: tErr('departments.load'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const list = Array.isArray(raw) ? raw : raw?.items ?? raw?.data ?? [];
    const items: Department[] = list.map(parseDepartment).filter((d: Department) => d.id && d.name);
    const data: DepartmentListResponse = {
      items,
      total: typeof raw?.total === 'number' ? raw.total : items.length,
      page: typeof raw?.page === 'number' ? raw.page : 1,
      page_size: typeof raw?.page_size === 'number' ? raw.page_size : 100,
      total_pages: typeof raw?.total_pages === 'number' ? raw.total_pages : 1,
    };
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('departments.load')) };
  }
}

export type DepartmentInput = {
  name: string;
  code: string;
  name_uz?: string | null;
  head_user_id?: string | null;
  is_active?: boolean;
};

export type DepartmentMutationResult =
  | { ok: true; data: Department }
  | { ok: false; error: string; status?: number };

export async function createDepartment(
  input: DepartmentInput,
  options?: { signal?: AbortSignal }
): Promise<DepartmentMutationResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/departments`, {
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
          403: tErr('departments.create_forbidden'),
          409: tErr('departments.code_taken'),
          fallback: tErr('departments.create_failed'),
        }),
        status: response.status,
      };
    }
    const data = parseDepartment(await response.json());
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('departments.create_failed')) };
  }
}

export async function updateDepartment(
  id: string,
  input: Partial<DepartmentInput>,
  options?: { signal?: AbortSignal }
): Promise<DepartmentMutationResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/departments/${encodeURIComponent(id)}`, {
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
          403: tErr('departments.update_forbidden'),
          404: tErr('departments.not_found'),
          409: tErr('departments.code_taken'),
          fallback: tErr('departments.update_failed'),
        }),
        status: response.status,
      };
    }
    const data = parseDepartment(await response.json());
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('departments.update_failed')) };
  }
}

export type DeleteResult =
  | { ok: true }
  | { ok: false; error: string; status?: number };

export async function deleteDepartment(
  id: string,
  options?: { signal?: AbortSignal }
): Promise<DeleteResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/departments/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('departments.delete_forbidden'),
          404: tErr('departments.not_found'),
          fallback: tErr('departments.delete_failed'),
        }),
        status: response.status,
      };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('departments.delete_failed')) };
  }
}

export type DepartmentUser = {
  id: string;
  full_name: string;
  email: string;
};

export type ListDepartmentUsersResult =
  | { ok: true; data: DepartmentUser[] }
  | { ok: false; error: string; status?: number };

export async function listUsersByDepartment(
  departmentId: string,
  options?: { signal?: AbortSignal }
): Promise<ListDepartmentUsersResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/departments/${encodeURIComponent(departmentId)}/users`, {
      signal: options?.signal,
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('departments.users_no_access'),
          fallback: tErr('departments.load_users'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const list = Array.isArray(raw) ? raw : raw?.items ?? raw?.data ?? [];
    const data: DepartmentUser[] = list.map(
      (u: { id?: string; full_name?: string; email?: string }) => ({
        id: String(u?.id ?? ''),
        full_name: String(u?.full_name ?? ''),
        email: String(u?.email ?? ''),
      })
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('departments.load_users')) };
  }
}
