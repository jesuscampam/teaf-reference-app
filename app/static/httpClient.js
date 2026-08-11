"use strict";

// The single place in the UI that talks to the network.
//
// Everything else imports `taskApi` from here and never calls `fetch`
// itself, so request shape, error translation, and the base path are
// defined once. Native ES modules — the browser loads this directly, so
// there is still no bundler, no npm, and no build step in this project.
//
// No business rules live here either: this layer knows URLs and status
// codes, and nothing about what makes a task valid or which transitions
// are allowed. Those answers come from TaskService, over the wire.

const API_BASE = "/tasks";

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

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (cause) {
    // fetch only rejects on a transport failure: offline, DNS, refused.
    throw new ApiError(0, "Cannot reach the server.");
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.status === 204 ? null : response.json();
}

function jsonRequest(path, method, payload) {
  return request(path, {
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
