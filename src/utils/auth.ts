/**
 * Dashboard authentication client.
 * Works against the backend auth endpoints. When the server has no
 * DASHBOARD_LOGIN_USERNAME / DASHBOARD_LOGIN_PASSWORD configured, the API
 * reports auth_required = false and the app stays open.
 */

export interface AuthStatus {
  auth_required: boolean;
  authenticated: boolean;
  username: string | null;
}

const FALLBACK: AuthStatus = { auth_required: false, authenticated: true, username: null };

export async function fetchAuthStatus(): Promise<AuthStatus> {
  try {
    const res = await fetch('/api/auth/status', {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    if (!res.ok) return FALLBACK;
    const data = (await res.json()) as AuthStatus;
    return {
      auth_required: Boolean(data?.auth_required),
      authenticated: Boolean(data?.authenticated),
      username: data?.username ?? null,
    };
  } catch {
    // If the API is unreachable, do not lock the user out of the UI shell.
    return FALLBACK;
  }
}

export async function login(
  username: string,
  password: string
): Promise<{ ok: boolean; error?: 'invalid' | 'network' }> {
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) return { ok: true };
    if (res.status === 401) return { ok: false, error: 'invalid' };
    return { ok: false, error: 'network' };
  } catch {
    return { ok: false, error: 'network' };
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
  } catch {
    /* ignore */
  }
}
