"use strict";

// The single place in the UI that talks to the network.
//
// Everything else imports `taskApi`/`authApi` from here and never calls
// `fetch` itself, so request shape, error translation, the base path, and
// — since Sprint A3 — the `Authorization` header are defined once. Native
// ES modules; still no bundler, no npm, no build step.
//
// Authentication lives here rather than in the callers for two reasons:
// the token is attached in exactly one place, and a `401` from any request
// means the same thing everywhere (the session is gone), so it is handled
// once, here, by clearing the session and returning to the login page.
//
// No business rules live here: this layer knows URLs and status codes, and
// nothing about what makes a task valid or which transitions are allowed.

import { redirectToLogin, session } from "./session.js";

const API_BASE = "/tasks";
const AUTH_BASE = "/auth";

/** An error response from the API, carrying the status and the server's message. */
export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * The API's error body is `{"detail": "..."}` for handled errors and
 * FastAPI's validation array for 422s. Both are reduced to one sentence;
 * if the body is neither (a proxy error page, say), fall back to the
 * status code rather than showing the user raw HTML.
 */
async function readErrorDetail(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((item) => item.msg).join("; ");
    }
  } catch {
    // Body was absent or not JSON — fall through to the generic message.
  }
  return `Request failed with status ${response.status}`;
}

/**
 * `authenticated: false` is for the two calls that must work without a
 * token — logging in, and the login page checking whether a stale session
 * is still valid. Everything else carries the bearer token.
 *
 * `onUnauthorized: false` suppresses the automatic bounce to /login, so a
 * failed login renders "invalid credentials" on the form instead of
 * reloading the page the user is already on.
 */
async function request(path, { authenticated = true, onUnauthorized = true, ...options } = {}) {
  const headers = { ...(options.headers ?? {}) };
  if (authenticated) {
    const token = session.token();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    // fetch only rejects on a transport failure: offline, DNS, refused.
    throw new ApiError(0, "Cannot reach the server.");
  }

  if (response.status === 401 && onUnauthorized) {
    // The token is missing, expired, or was revoked. Whichever it is, the
    // session is over: drop it and start again rather than leaving the
    // page half-working with a credential the server rejects.
    session.clear();
    redirectToLogin();
    throw new ApiError(401, "Your session has ended. Please sign in again.");
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.status === 204 ? null : response.json();
}

function jsonRequest(path, method, payload, extra = {}) {
  return request(path, {
    ...extra,
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Every Task Manager endpoint the UI uses, one method each. */
export const taskApi = {
  list: () => request(API_BASE),
  stats: () => request(`${API_BASE}/stats`),
  get: (id) => request(`${API_BASE}/${id}`),
  create: (title, description) => jsonRequest(API_BASE, "POST", { title, description }),
  update: (id, title, description) =>
    jsonRequest(`${API_BASE}/${id}`, "PUT", { title, description }),
  changeStatus: (id, status) => jsonRequest(`${API_BASE}/${id}/status`, "PATCH", { status }),
  remove: (id) => request(`${API_BASE}/${id}`, { method: "DELETE" }),
};

/** Authentication endpoints. */
export const authApi = {
  // No token yet, and a wrong password must not bounce the page.
  login: (username, password) =>
    jsonRequest(AUTH_BASE + "/login", "POST", { username, password }, {
      authenticated: false,
      onUnauthorized: false,
    }),

  // Revokes the token server-side, so logging out means more than
  // forgetting it locally.
  logout: () => request(`${AUTH_BASE}/logout`, { method: "POST", onUnauthorized: false }),

  // Used to restore a session on load: a 401 here means the stored token
  // is no longer good.
  me: (options = {}) => request(`${AUTH_BASE}/me`, options),
};
