"use strict";

// The browser's authentication state, in one place.
//
// **Storage choice: `sessionStorage`.** The options and the trade-off,
// stated plainly because this is a reference application:
//
//   httpOnly cookie  — the only option JavaScript cannot read, so XSS
//                      cannot steal the token. Costs a CSRF defence and
//                      server-set cookies; not what this demo does.
//   localStorage     — survives browser restarts. Readable by any script
//                      on the origin, and outlives the session for no
//                      reason this app needs.
//   sessionStorage   — what this uses. Readable by scripts on the origin
//                      (same XSS exposure as localStorage), but scoped to
//                      the tab and cleared when it closes, so a token
//                      cannot outlive the window it was issued to.
//
// The page ships a strict `default-src 'self'` CSP with no inline scripts
// and no external origins, which is what makes the XSS exposure small
// enough to accept for a demo. A production app handling real accounts
// should use an httpOnly, SameSite cookie plus CSRF protection — see the
// README's "Authentication" section.

const STORAGE_KEY = "teaf.session";

/** Reads the stored session, tolerating anything that isn't valid JSON. */
function read() {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed?.accessToken === "string" ? parsed : null;
  } catch {
    // Corrupt or hand-edited value: treat as no session rather than
    // letting a parse error break every page load from then on.
    return null;
  }
}

export const session = {
  /** The stored session, or null. Reading it is how a page restores state. */
  current() {
    return read();
  },

  isAuthenticated() {
    return read() !== null;
  },

  /** The bearer token, or null — used by httpClient.js and nowhere else. */
  token() {
    return read()?.accessToken ?? null;
  },

  save({ accessToken, username, roles, permissions }) {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken, username, roles, permissions }),
    );
  },

  clear() {
    sessionStorage.removeItem(STORAGE_KEY);
  },

  /** Whether the current session carries a permission (drives the UI only). */
  can(permission) {
    return (read()?.permissions ?? []).includes(permission);
  },
};

/** Send an unauthenticated visitor to the login page. */
export function redirectToLogin() {
  // `replace`, not `assign`: a protected page the user was bounced off
  // should not be sitting in history for the Back button to return to.
  window.location.replace("/login");
}

/** Send an authenticated visitor to the application. */
export function redirectToApp() {
  window.location.replace("/");
}
