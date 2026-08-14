"use strict";

// UI-only concerns: rendering, view state, and event wiring. No task
// business rules live here — validation, allowed transitions, and the
// metric counts all come from the server. Network access goes through
// `taskApi` (httpClient.js); nothing in this file calls `fetch`.

import { ApiError, authApi, taskApi } from "./httpClient.js";
import { redirectToLogin, session } from "./session.js";

const STATUS_LABELS = {
  TODO: "To do",
  IN_PROGRESS: "In progress",
  DONE: "Done",
};

/** Which status each task's primary button moves it to. */
const NEXT_STATUS = {
  TODO: "IN_PROGRESS",
  IN_PROGRESS: "DONE",
  DONE: "TODO",
};

const NEXT_STATUS_LABELS = {
  TODO: "Start",
  IN_PROGRESS: "Complete",
  DONE: "Reopen",
};

const taskListEl = document.getElementById("task-list");
const statusMessageEl = document.getElementById("status-message");
const createFormEl = document.getElementById("create-form");
const createTitleEl = document.getElementById("create-title");
const createDescriptionEl = document.getElementById("create-description");
const sessionUsernameEl = document.getElementById("session-username");
const sessionRolesEl = document.getElementById("session-roles");
const logoutButtonEl = document.getElementById("logout-button");
const statTotalEl = document.getElementById("stat-total");
const statTodoEl = document.getElementById("stat-todo");
const statInProgressEl = document.getElementById("stat-in-progress");
const statDoneEl = document.getElementById("stat-done");

/** The one piece of view state the server does not own: which row is open for editing. */
let editingTaskId = null;

function showStatus(message, isError) {
  statusMessageEl.textContent = message;
  statusMessageEl.hidden = false;
  statusMessageEl.classList.toggle("error", Boolean(isError));
}

function hideStatus() {
  statusMessageEl.hidden = true;
  statusMessageEl.classList.remove("error");
}

/** Prefer the server's own message; fall back to ours for anything unexpected. */
function reportError(error, fallback) {
  showStatus(error instanceof ApiError ? error.detail : fallback, true);
}

function renderStats(stats) {
  statTotalEl.textContent = String(stats.total);
  statTodoEl.textContent = String(stats.todo);
  statInProgressEl.textContent = String(stats.in_progress);
  statDoneEl.textContent = String(stats.done);
}

function renderTasks(tasks) {
  taskListEl.replaceChildren();

  if (tasks.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "No tasks yet. Create your first task.";
    taskListEl.appendChild(empty);
    return;
  }

  for (const task of tasks) {
    taskListEl.appendChild(task.id === editingTaskId ? buildEditItem(task) : buildTaskItem(task));
  }
}

function buildStatusBadge(status) {
  const badge = document.createElement("span");
  badge.className = `task-status status-${status.toLowerCase()}`;
  badge.textContent = STATUS_LABELS[status] ?? status;
  return badge;
}

function buildTaskItem(task) {
  const li = document.createElement("li");
  li.className = "task-item" + (task.status === "DONE" ? " completed" : "");

  const body = document.createElement("div");
  body.className = "task-body";

  const title = document.createElement("div");
  title.className = "task-title";
  title.textContent = task.title;

  const description = document.createElement("div");
  description.className = "task-description";
  description.textContent = task.description;

  body.append(title, description, buildStatusBadge(task.status));

  const actions = document.createElement("div");
  actions.className = "task-actions";

  const advanceButton = document.createElement("button");
  advanceButton.type = "button";
  advanceButton.textContent = NEXT_STATUS_LABELS[task.status];
  advanceButton.addEventListener("click", () => changeStatus(task.id, NEXT_STATUS[task.status]));

  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "secondary";
  editButton.textContent = "Edit";
  editButton.addEventListener("click", () => {
    editingTaskId = task.id;
    loadTasks();
  });

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "danger";
  deleteButton.textContent = "Delete";
  deleteButton.addEventListener("click", () => deleteTask(task.id));

  actions.append(advanceButton, editButton, deleteButton);
  li.append(body, actions);
  return li;
}

function buildEditItem(task) {
  const li = document.createElement("li");
  li.className = "task-item";

  const form = document.createElement("form");
  form.className = "task-edit-form";

  const titleInput = document.createElement("input");
  titleInput.type = "text";
  titleInput.value = task.title;
  titleInput.required = true;
  titleInput.maxLength = 200;

  const descriptionInput = document.createElement("input");
  descriptionInput.type = "text";
  descriptionInput.value = task.description;
  descriptionInput.required = true;
  descriptionInput.maxLength = 500;

  const saveButton = document.createElement("button");
  saveButton.type = "submit";
  saveButton.textContent = "Save";

  const cancelButton = document.createElement("button");
  cancelButton.type = "button";
  cancelButton.className = "secondary";
  cancelButton.textContent = "Cancel";
  cancelButton.addEventListener("click", () => {
    editingTaskId = null;
    loadTasks();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    updateTask(task.id, titleInput.value, descriptionInput.value);
  });

  form.append(titleInput, descriptionInput, saveButton, cancelButton);
  li.appendChild(form);
  return li;
}

/**
 * One round trip for the list and one for the counts. The counts are read
 * from `/tasks/stats` rather than derived here so the numbers on screen are
 * the server's, not a second implementation of the same arithmetic.
 */
async function loadTasks() {
  showStatus("Loading tasks...", false);
  try {
    const [tasks, stats] = await Promise.all([taskApi.list(), taskApi.stats()]);
    hideStatus();
    renderTasks(tasks);
    renderStats(stats);
  } catch (error) {
    reportError(error, "Unable to load tasks.");
    taskListEl.replaceChildren();
  }
}

async function createTask(title, description) {
  try {
    await taskApi.create(title, description);
    await loadTasks();
  } catch (error) {
    reportError(error, "Unable to create the task.");
  }
}

async function updateTask(id, title, description) {
  try {
    await taskApi.update(id, title, description);
    editingTaskId = null;
    await loadTasks();
  } catch (error) {
    reportError(error, "Unable to update the task.");
  }
}

async function changeStatus(id, status) {
  try {
    await taskApi.changeStatus(id, status);
    await loadTasks();
  } catch (error) {
    reportError(error, "Unable to change the task status.");
  }
}

async function deleteTask(id) {
  if (!window.confirm("Delete this task?")) {
    return;
  }
  try {
    await taskApi.remove(id);
    await loadTasks();
  } catch (error) {
    reportError(error, "Unable to delete the task.");
  }
}

async function signOut() {
  logoutButtonEl.disabled = true;
  try {
    // Revokes the token server-side. Even if that fails, the local
    // session must still go — otherwise a network blip would leave the
    // user apparently signed in with a token they cannot use.
    await authApi.logout();
  } catch {
    // Deliberately ignored; the finally block is what matters.
  } finally {
    session.clear();
    redirectToLogin();
  }
}

createFormEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = createTitleEl.value.trim();
  const description = createDescriptionEl.value.trim();
  if (!title || !description) {
    return;
  }
  createTitleEl.value = "";
  createDescriptionEl.value = "";
  createTask(title, description);
});

logoutButtonEl.addEventListener("click", signOut);

/**
 * The protected-route guard.
 *
 * A stored token is not taken at face value: `GET /auth/me` asks the
 * server whether it is still valid, so an expired or revoked token sends
 * the browser to the login page instead of into an application whose
 * every request would fail. With no token at all, the redirect happens
 * immediately and no task request is ever made.
 */
async function start() {
  if (!session.isAuthenticated()) {
    redirectToLogin();
    return;
  }
  let me;
  try {
    me = await authApi.me({ onUnauthorized: false });
  } catch {
    session.clear();
    redirectToLogin();
    return;
  }

  sessionUsernameEl.textContent = me.username;
  sessionRolesEl.textContent = me.roles.length > 0 ? `(${me.roles.join(", ")})` : "";

  // A read-only account never sees the create form, so the restriction is
  // apparent before a click rather than after a 403. The form is hidden
  // before the first load (no flash of a control the account cannot use),
  // but the explanation is shown *after* it — `loadTasks` drives the same
  // status line, and writing the notice first would have it overwritten
  // by "Loading tasks…" a moment later.
  const readOnly = !session.can("task.write");
  createFormEl.hidden = readOnly;

  await loadTasks();

  if (readOnly) {
    showStatus("Read-only account: you can view tasks but not change them.", false);
  }
}

start();
