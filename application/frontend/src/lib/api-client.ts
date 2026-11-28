export interface ApiErrorItem {
  code?: string;
  field?: string | null;
  message?: string;
  detail?: string;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  meta?: {
    pagination?: {
      page: number;
      page_size: number;
      total_count: number;
      total_pages: number;
    };
    timestamp?: string;
    count?: number;
    engine?: string;
  };
  errors: ApiErrorItem[] | Record<string, unknown> | null;
  detail?: string;
}

export class ApiRequestError extends Error {
  status: number;
  errors: ApiErrorItem[] | Record<string, unknown> | null;

  constructor(
    message: string,
    status: number,
    errors: ApiErrorItem[] | Record<string, unknown> | null = null
  ) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

const STORAGE_KEY = "bonyan_auth_v2";
let refreshPromise: Promise<string | null> | null = null;
let apiRequestCount = 0;
function notifyApiRequestCount() {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("bonyan-api-request-count", { detail: { count: apiRequestCount } }));
}

/** درخواست‌های هم‌زمان تازه‌سازی را در یک Promise مشترک هماهنگ می‌کند. */
async function tryRefreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed?.refresh) return null;

      const res = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: parsed.refresh }),
      });
      if (!res.ok) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
      const env = await res.json();
      if (!env?.success || !env?.data?.access) return null;

      const updated = {
        ...parsed,
        access: env.data.access,
        refresh: env.data.refresh || parsed.refresh,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      window.dispatchEvent(new CustomEvent("bonyan-token-refreshed", { detail: updated }));
      return env.data.access as string;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

function extractErrorMessage(json: unknown, status: number): string {
  if (json && typeof json === "object") {
    const obj = json as Record<string, unknown>;
    if (typeof obj.detail === "string" && obj.detail.trim()) return obj.detail;
    if (Array.isArray(obj.errors) && obj.errors.length > 0) {
      const first = obj.errors[0] as Record<string, unknown>;
      if (typeof first?.message === "string") return first.message;
    }
    if (obj.errors && typeof obj.errors === "object") {
      const errObj = obj.errors as Record<string, unknown>;
      if (typeof errObj.detail === "string") return errObj.detail;
    }
  }
  return `خطا در ارتباط با سرویس API (${status})`;
}

/** خطای HTTP و پاسخ پوشش‌دار API را به قرارداد مشترک رابط تبدیل می‌کند. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string | null; agencyId?: string | null; skipRefresh?: boolean } = {}
): Promise<ApiEnvelope<T>> {
  const { token, agencyId, headers, skipRefresh, ...rest } = options;
  const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const buildHeaders = (authToken?: string | null) => {
    const finalHeaders: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(headers as Record<string, string> | undefined),
    };
    if (authToken) {
      finalHeaders["Authorization"] = `Bearer ${authToken}`;
    }
    if (agencyId) {
      finalHeaders["X-Agency-ID"] = agencyId;
    }
    return finalHeaders;
  };

  apiRequestCount += 1;
  notifyApiRequestCount();
  try {
    let res = await fetch(path, {
      ...rest,
      headers: buildHeaders(token),
    });

    if (res.status === 401 && token && !skipRefresh && !path.includes("/auth/login")) {
      const newToken = await tryRefreshAccessToken();
      if (newToken) {
        res = await fetch(path, {
          ...rest,
          headers: buildHeaders(newToken),
        });
      }
    }

    const json = await res.json().catch(() => null);
    const isEnvelope =
      json !== null && typeof json === "object" && "success" in json && typeof json.success === "boolean";

    if (!res.ok) {
      const env = isEnvelope ? (json as ApiEnvelope<T>) : null;
      throw new ApiRequestError(extractErrorMessage(json, res.status), res.status, env?.errors ?? null);
    }

    if (isEnvelope) {
      const env = json as ApiEnvelope<T>;
      if (!env.success) {
        throw new ApiRequestError(extractErrorMessage(json, res.status), res.status, env.errors ?? null);
      }
      return env;
    }

    return {
      success: true,
      data: json as T,
      errors: null,
    };
  } finally {
    apiRequestCount = Math.max(0, apiRequestCount - 1);
    notifyApiRequestCount();
  }
}

/** فایل احراز هویت‌شده را با نشانی موقت مرورگر برای ذخیره آماده می‌کند. */
export async function apiDownloadBlob(
  path: string,
  options: { token?: string | null; agencyId?: string | null; filenameFallback?: string } = {}
): Promise<void> {
  const headers: Record<string, string> = {};
  if (options.token) headers["Authorization"] = `Bearer ${options.token}`;
  if (options.agencyId) headers["X-Agency-ID"] = options.agencyId;

  const res = await fetch(path, { headers });
  if (!res.ok) {
    throw new ApiRequestError(`خطا در دانلود فایل (${res.status})`, res.status);
  }
  const blob = await res.blob();
  const disp = res.headers.get("content-disposition") || "";
  const match = disp.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || options.filenameFallback || "export.xlsx";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export { STORAGE_KEY };
