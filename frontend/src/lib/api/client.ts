import { ApiError } from "./errors";
import { tokenStore } from "./tokenStore";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean; // default true — pass false only for /v1/auth/* endpoints
  idempotencyKey?: string; // see docs/API.md §8 — required on retryable mutations
}

let refreshInFlight: Promise<void> | null = null;

async function refreshTokens(): Promise<void> {
  const tokens = tokenStore.get();
  if (!tokens) throw new ApiError(401, { error_code: "unauthenticated", message: "Not signed in.", request_id: "" });

  const res = await fetch(`${BASE_URL}/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refreshToken }),
  });

  if (!res.ok) {
    tokenStore.clear();
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body ?? { error_code: "token_invalid", message: "Session expired.", request_id: "" });
  }

  const body = (await res.json()) as { access_token: string; refresh_token: string };
  tokenStore.set({ accessToken: body.access_token, refreshToken: body.refresh_token });
}

/** Core request function. Auto-refreshes once on a 401 token_expired and
 * retries the original request — see docs/API.md §2 (refresh flow). Every
 * mutation that can be safely retried should pass idempotencyKey, per
 * docs/API.md §8's Idempotency-Key list; this is a scaffold placeholder —
 * confirm the exact endpoint list against API.md as new mutations are added. */
export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, idempotencyKey } = opts;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    if (auth) {
      const tokens = tokenStore.get();
      if (tokens) headers.Authorization = `Bearer ${tokens.accessToken}`;
    }
    return fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && auth) {
    const errorBody = await res.clone().json().catch(() => null);
    if (errorBody?.error_code === "token_expired") {
      refreshInFlight ??= refreshTokens().finally(() => {
        refreshInFlight = null;
      });
      await refreshInFlight;
      res = await doFetch();
    }
  }

  if (res.status === 204) return undefined as T;

  const responseBody = await res.json().catch(() => null);

  if (!res.ok) {
    throw new ApiError(
      res.status,
      responseBody ?? { error_code: "unknown_error", message: "Something went wrong.", request_id: "" },
    );
  }

  return responseBody as T;
}
