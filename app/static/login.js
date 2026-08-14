"use strict";

// The login page. Its only jobs: send credentials, store the session, and
// get out of the way. No task logic here.

import { ApiError, authApi } from "./httpClient.js";
import { redirectToApp, session } from "./session.js";

const formEl = document.getElementById("login-form");
const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const submitEl = document.getElementById("login-submit");
const errorEl = document.getElementById("login-error");

/**
 * Guards against a second submit while the first is in flight — a double
 * click would otherwise mint two tokens and race two redirects. The
 * button is disabled too, but a flag is what actually makes this safe:
 * Enter in a text field can submit a form whose button is disabled.
 */
let submitting = false;

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

function setBusy(busy) {
  submitting = busy;
  submitEl.disabled = busy;
  submitEl.textContent = busy ? "Signing in…" : "Sign in";
  usernameEl.disabled = busy;
  passwordEl.disabled = busy;
}

async function signIn(username, password) {
  setBusy(true);
  clearError();
  try {
    const response = await authApi.login(username, password);
    session.save({
      accessToken: response.access_token,
      username: response.username,
      roles: response.roles,
      permissions: response.permissions,
    });
    redirectToApp();
  } catch (error) {
    // The server answers the same way for an unknown user and a wrong
    // password, and this shows exactly what it said — no guessing, and
    // nothing added that would distinguish the two cases.
    const message =
      error instanceof ApiError && error.status === 401
        ? "Invalid username or password."
        : error instanceof ApiError
          ? error.detail
          : "Unable to sign in right now.";
    showError(message);
    passwordEl.value = "";
    setBusy(false);
    passwordEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  if (submitting) {
    return;
  }
  const username = usernameEl.value.trim();
  const password = passwordEl.value;
  if (!username || !password) {
    showError("Enter a username and a password.");
    return;
  }
  // The password is read straight into the request and never logged,
  // stored, or put in the URL.
  signIn(username, password);
});

// Someone who is already signed in has no business on this page. The
// stored token is checked against the server rather than trusted, so an
// expired or revoked one lands here instead of bouncing into an app that
// would immediately throw the user back out.
if (session.isAuthenticated()) {
  authApi
    .me({ onUnauthorized: false })
    .then(() => redirectToApp())
    .catch(() => session.clear());
}
