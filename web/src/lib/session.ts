const KEY = "inkling.session_token";

export function readSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function writeSessionToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, token);
}

export function clearSessionToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
}

export function newSessionToken(): string {
  return crypto.randomUUID();
}
