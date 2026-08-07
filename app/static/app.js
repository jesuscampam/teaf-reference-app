"use strict";

// UI-only concerns: fetch calls, rendering, and state handling. No task
// business rules live here — creation/update payloads are sent exactly as
// the API requires, and all validation/state transitions happen server
// side in TaskService.

const API_BASE = "/tasks";

const taskListEl = document.getElementById("task-list");
const statusMessageEl = document.getElementById("status-message");
const createFormEl = document.getElementById("create-form");
const createTitleEl = document.getElementById("create-title");
const createDescriptionEl = document.getElementById("create-description");
const statTotalEl = document.getElementById("stat-total");
const statPendingEl = document.getElementById("stat-pending");
const statCompletedEl = document.getElementById("stat-completed");

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

async function apiRequest(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function renderStats(tasks) {
  const completed = tasks.filter((task) => task.completed).length;
  statTotalEl.textContent = String(tasks.length);
  statCompletedEl.textContent = String(completed);
  statPendingEl.textContent = String(tasks.length - completed);
}

function renderTasks(tasks) {
  taskListEl.innerHTML = "";

  if (tasks.length === 0) {
    const empty = document.createElement("li");
    empty.className = "status-message";
    empty.textContent = "No tasks yet. Create your first task.";
    taskListEl.appendChild(empty);
    renderStats(tasks);
    return;
  }

  for (const task of tasks) {
    taskListEl.appendChild(task.id === editingTaskId ? buildEditItem(task) : buildTaskItem(task));
  }
  renderStats(tasks);
}

function buildTaskItem(task) {
  const li = document.createElement("li");
  li.className = "task-item" + (task.completed ? " completed" : "");

  const toggle = document.createElement("button");
  toggle.className = "task-toggle";
  toggle.type = "button";
  toggle.setAttribute("aria-label", "Mark as completed");
  toggle.textContent = task.completed ? "✓" : "";
  toggle.disabled = task.completed;
  toggle.addEventListener("click", () => completeTask(task.id));

  const body = document.createElement("div");
  body.className = "task-body";

  const title = document.createElement("div");
  title.className = "task-title";
  title.textContent = task.title;

  const description = document.createElement("div");
  description.className = "task-description";
  description.textContent = task.description;

  body.appendChild(title);
  body.appendChild(description);

  const actions = document.createElement("div");
  actions.className = "task-actions";

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

  actions.appendChild(editButton);
  actions.appendChild(deleteButton);

  li.appendChild(toggle);
  li.appendChild(body);
  li.appendChild(actions);
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

  form.appendChild(titleInput);
  form.appendChild(descriptionInput);
  form.appendChild(saveButton);
  form.appendChild(cancelButton);
  li.appendChild(form);
  return li;
}

async function loadTasks() {
  showStatus("Loading tasks...", false);
  try {
    const tasks = await apiRequest(API_BASE);
    hideStatus();
    renderTasks(tasks);
  } catch (error) {
    showStatus("Unable to load tasks.", true);
    taskListEl.innerHTML = "";
  }
}

async function createTask(title, description) {
  try {
    await apiRequest(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    await loadTasks();
  } catch (error) {
    showStatus("Unable to create the task.", true);
  }
}

async function updateTask(id, title, description) {
  try {
    await apiRequest(`${API_BASE}/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    editingTaskId = null;
    await loadTasks();
  } catch (error) {
    showStatus("Unable to update the task.", true);
  }
}

async function completeTask(id) {
  try {
    await apiRequest(`${API_BASE}/${id}/complete`, { method: "POST" });
    await loadTasks();
  } catch (error) {
    showStatus("Unable to complete the task.", true);
  }
}

async function deleteTask(id) {
  if (!window.confirm("Delete this task?")) {
    return;
  }
  try {
    await apiRequest(`${API_BASE}/${id}`, { method: "DELETE" });
    await loadTasks();
  } catch (error) {
    showStatus("Unable to delete the task.", true);
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

loadTasks();
