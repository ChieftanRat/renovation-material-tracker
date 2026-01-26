const API_BASE = window.location.origin;

const API_KEY_STORAGE = "rmt_api_key";

const RESOURCES = [
  {
    key: "tasks",
    title: "Tasks",
    endpoint: "/tasks",
    projectScoped: true,
    editable: true,
    emptyMessage: "Add tasks to break your project into steps.",
    modalDescription: "Define the work plan and key dates for this project.",
    columns: [
      { key: "id", label: "ID" },
      { key: "name", label: "Task" },
      { key: "status", label: "Status", type: "badge" },
      { key: "start_datetime", label: "Start" },
      { key: "end_datetime", label: "End" },
    ],
    filters: [
      { name: "start_date", label: "Start date", type: "date" },
      { name: "end_date", label: "End date", type: "date" },
    ],
    createFields: [
      { name: "project_id", label: "Project", type: "select", required: true },
      { name: "name", label: "Task name", type: "text", required: true },
      {
        name: "start_datetime",
        label: "Start datetime",
        type: "datetime-local",
        required: true,
        emphasis: true,
      },
      {
        name: "end_datetime",
        label: "End datetime",
        type: "datetime-local",
        required: true,
        emphasis: true,
      },
    ],
  },
  {
    key: "material-purchases",
    title: "Purchases",
    endpoint: "/material-purchases",
    projectScoped: true,
    editable: true,
    emptyMessage: "Log materials to track costs.",
    modalDescription: "Capture materials and costs. Totals update automatically.",
    columns: [
      { key: "id", label: "ID" },
      { key: "material_description", label: "Material" },
      { key: "vendor_name", label: "Vendor" },
      { key: "task_name", label: "Task" },
      { key: "unit_cost", label: "Unit", type: "number" },
      { key: "quantity", label: "Qty", type: "number" },
      { key: "total_material_cost", label: "Material total", type: "number" },
      { key: "delivery_cost", label: "Delivery", type: "number" },
      { key: "purchase_date", label: "Date" },
    ],
    filters: [
      { name: "vendor_id", label: "Vendor", type: "select" },
      { name: "task_id", label: "Task", type: "select" },
      { name: "start_date", label: "Start date", type: "date" },
      { name: "end_date", label: "End date", type: "date" },
    ],
    createFields: [
      { name: "project_id", label: "Project", type: "select", required: true },
      { name: "task_id", label: "Task", type: "select", required: true },
      { name: "vendor_id", label: "Vendor", type: "select", required: true },
      {
        name: "material_description",
        label: "Material",
        type: "text",
        required: true,
      },
      {
        name: "unit_cost",
        label: "Unit cost",
        type: "number",
        required: true,
        emphasis: true,
        min: 0,
      },
      {
        name: "quantity",
        label: "Quantity",
        type: "number",
        required: true,
        emphasis: true,
        min: 0,
      },
      { name: "delivery_cost", label: "Delivery cost", type: "number", min: 0 },
      {
        name: "purchase_date",
        label: "Purchase date",
        type: "date",
        required: true,
        emphasis: true,
      },
    ],
  },
  {
    key: "work-sessions",
    title: "Work Sessions",
    endpoint: "/work-sessions",
    projectScoped: true,
    editable: true,
    emptyMessage: "Log labor time to calculate labor costs.",
    modalDescription:
      "Add one or more labor entries for the selected task and date.",
    columns: [
      { key: "task_name", label: "Task" },
      { key: "work_date", label: "Date" },
      { key: "laborer_names", label: "Laborers" },
      { key: "hours_worked", label: "Total hours", type: "number" },
      { key: "status", label: "Status", type: "badge" },
    ],
    filters: [
      { name: "laborer_id", label: "Laborer", type: "select" },
      { name: "task_id", label: "Task", type: "select" },
      { name: "start_date", label: "Start date", type: "date" },
      { name: "end_date", label: "End date", type: "date" },
    ],
    createFields: [
      { name: "project_id", label: "Project", type: "select", required: true },
      { name: "task_id", label: "Task", type: "select", required: true },
      {
        name: "work_date",
        label: "Work date",
        type: "date",
        required: true,
      },
    ],
  },
];

const state = {
  selectedProjectId: null,
  selectedProject: null,
  activeTab: "tasks",
  filters: {},
  pagination: {},
  lastRows: {},
  lookups: {
    projects: [],
    tasks: [],
    vendors: [],
    laborers: [],
  },
};

const ui = {
  serverBase: document.getElementById("server-base"),
  apiKeyInput: document.getElementById("api-key"),
  projectList: document.getElementById("project-list"),
  projectSearch: document.getElementById("project-search"),
  projectTitle: document.getElementById("project-title"),
  projectMeta: document.getElementById("project-meta"),
  projectGuidance: document.getElementById("project-guidance"),
  breadcrumb: document.getElementById("breadcrumb"),
  totalMaterials: document.getElementById("total-materials"),
  totalLabor: document.getElementById("total-labor"),
  totalCombined: document.getElementById("total-combined"),
  progressStrip: document.getElementById("progress-strip"),
  tabs: document.getElementById("tabs"),
  filterToggle: document.getElementById("filter-toggle"),
  filterPanel: document.getElementById("filter-panel"),
  tableWrap: document.getElementById("table-wrap"),
  tableMeta: document.getElementById("table-meta"),
  pageInput: document.getElementById("page-input"),
  pageSizeInput: document.getElementById("page-size-input"),
  pageApply: document.getElementById("page-apply"),
  addToggle: document.getElementById("add-toggle"),
  showArchived: document.getElementById("show-archived"),
  refreshAll: document.getElementById("refresh-all"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modal-title"),
  modalBody: document.getElementById("modal-body"),
  modalClose: document.getElementById("modal-close"),
  modalCancel: document.getElementById("modal-cancel"),
  modalSave: document.getElementById("modal-save"),
  modalStatus: document.getElementById("modal-status"),
  projectAdd: document.getElementById("project-add"),
  projectEdit: document.getElementById("project-edit"),
  projectArchive: document.getElementById("project-archive"),
  projectDelete: document.getElementById("project-delete"),
  backupNow: document.getElementById("backup-now"),
  backupStatus: document.getElementById("backup-status"),
  migrationStatus: document.getElementById("migration-status"),
  manageEntities: document.getElementById("manage-entities"),
  manageModal: document.getElementById("manage-modal"),
  manageBody: document.getElementById("manage-body"),
  manageStatus: document.getElementById("manage-status"),
  manageClose: document.getElementById("manage-close"),
  toastContainer: document.getElementById("toast-container"),
};

ui.serverBase.textContent = API_BASE;

function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE) || "";
}

function setApiKey(value) {
  const trimmed = value.trim();
  if (trimmed) {
    localStorage.setItem(API_KEY_STORAGE, trimmed);
  } else {
    localStorage.removeItem(API_KEY_STORAGE);
  }
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  ui.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

function showSkeleton() {
  ui.tableWrap.innerHTML = "";
  const skeleton = document.createElement("div");
  skeleton.className = "skeleton";
  for (let i = 0; i < 7; i += 1) {
    const row = document.createElement("div");
    row.className = "skeleton-row";
    skeleton.appendChild(row);
  }
  ui.tableWrap.appendChild(skeleton);
}

async function fetchJson(url, options = {}) {
  const requestOptions = { ...options };
  const method = (requestOptions.method || "GET").toUpperCase();
  const headers = new Headers(requestOptions.headers || {});
  if (method !== "GET") {
    const apiKey = getApiKey();
    if (apiKey) {
      headers.set("X-API-Key", apiKey);
    }
  }
  requestOptions.headers = headers;
  const response = await fetch(url, requestOptions);
  const payload = await response.json();
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      showToast(payload.error || "Authentication failed.", "error");
    }
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

function formatValue(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value;
}

function hoursBetween(date, start, end) {
  if (!date || !start || !end) {
    return 0;
  }
  const startTime = new Date(`${date}T${start}`);
  const endTime = new Date(`${date}T${end}`);
  const diff = (endTime - startTime) / 36e5;
  return diff > 0 ? diff : 0;
}

function renderTable(resource, columns, rows) {
  ui.tableWrap.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = resource.emptyMessage || "No results yet.";
    ui.tableWrap.appendChild(empty);
    return;
  }

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    if (col.type === "number") {
      th.classList.add("numeric");
    }
    headRow.appendChild(th);
  });
  if (resource.editable) {
    if (ui.showArchived.checked) {
      const thStatus = document.createElement("th");
      thStatus.textContent = "Archived";
      headRow.appendChild(thStatus);
    }
    const th = document.createElement("th");
    th.textContent = "Actions";
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    if (row._rowClass) {
      tr.classList.add(row._rowClass);
    }
    columns.forEach((col) => {
      const td = document.createElement("td");
      const value = row[col.key];
      if (col.type === "badge") {
        const badge = document.createElement("span");
        badge.className = `badge ${value?.state || ""}`;
        badge.textContent = value?.label || "-";
        td.appendChild(badge);
      } else {
        td.textContent = formatValue(value);
      }
      if (col.type === "number") {
        td.classList.add("numeric");
      }
      tr.appendChild(td);
    });
    if (resource.editable && ui.showArchived.checked) {
      const badgeCell = document.createElement("td");
      if (row.archived_at) {
        const badge = document.createElement("span");
        badge.className = "badge archived";
        badge.textContent = "Archived";
        badgeCell.appendChild(badge);
      }
      tr.appendChild(badgeCell);
    }
    if (resource.editable) {
      const td = document.createElement("td");
      const menu = createRowMenu(resource, row);
      td.appendChild(menu);
      tr.appendChild(td);
    }
    if (resource.key === "work-sessions") {
      tr.classList.add("clickable-row");
      tr.addEventListener("click", (event) => {
        if (event.target.closest(".row-menu")) {
          return;
        }
        openModal(resource, { mode: "edit", data: row });
      });
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  ui.tableWrap.appendChild(table);
}

function getResource() {
  return RESOURCES.find((resource) => resource.key === state.activeTab);
}

function getFiltersForResource(resource) {
  const currentFilters = state.filters[resource.key] || {};
  if (resource.projectScoped && state.selectedProjectId) {
    return { ...currentFilters, project_id: state.selectedProjectId };
  }
  return currentFilters;
}

function buildQueryParams(resource) {
  const pagination = state.pagination[resource.key] || { page: 1, page_size: 25 };
  const params = { ...pagination };
  const filters = getFiltersForResource(resource);
  Object.keys(filters).forEach((key) => {
    if (filters[key]) {
      params[key] = filters[key];
    }
  });
  if (ui.showArchived.checked) {
    params.include_archived = "true";
  }
  return params;
}

function buildLookupMap(items) {
  const map = new Map();
  items.forEach((item) => {
    map.set(item.id, item.name || item.material_description);
  });
  return map;
}

function enrichRows(resource, rows) {
  const taskMap = buildLookupMap(state.lookups.tasks);
  const vendorMap = buildLookupMap(state.lookups.vendors);
  const laborerMap = buildLookupMap(state.lookups.laborers);
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const totals = rows.map(
    (row) => (row.total_material_cost || 0) + (row.delivery_cost || 0)
  );
  const maxTotal = totals.length ? Math.max(...totals) : 0;

  return rows.map((row) => {
    const updated = { ...row };
    if (resource.key === "material-purchases") {
      updated.task_name = taskMap.get(row.task_id) || "-";
      updated.vendor_name = vendorMap.get(row.vendor_id) || "-";
      const total = (row.total_material_cost || 0) + (row.delivery_cost || 0);
      if (maxTotal > 0 && total >= maxTotal * 0.75) {
        updated._rowClass = "row-highlight";
      }
    }
    if (resource.key === "work-sessions") {
      updated.task_name = taskMap.get(row.task_id) || "-";
      const entries = row.entries || [];
      const laborerNames = [];
      const seen = new Set();
      for (const entry of entries) {
        const name = laborerMap.get(entry.laborer_id) || "-";
        if (!name || name == "-" || seen.has(name)) {
          continue;
        }
        seen.add(name);
        laborerNames.push(name);
      }
      if (laborerNames.length <= 2) {
        updated.laborer_names = laborerNames.length
          ? laborerNames.join(", ")
          : "-";
      } else {
        updated.laborer_names = `${laborerNames[0]} +${laborerNames.length - 1} more`;
      }
      updated.hours_worked = entries.reduce(
        (sum, entry) =>
          sum +
          hoursBetween(row.work_date, entry.clock_in_time, entry.clock_out_time),
        0
      );
      const status =
        row.work_date === today
          ? { label: "Today", state: "active" }
          : { label: "Logged", state: "done" };
      updated.status = status;
    }
    if (resource.key === "tasks") {
      const end = row.end_datetime ? new Date(row.end_datetime) : null;
      const completed = end && end < now;
      updated.status = completed
        ? { label: "Completed", state: "done" }
        : { label: "Upcoming", state: "active" };
      if (completed) {
        updated._rowClass = "row-faded";
      }
    }
    return updated;
  });
}

async function loadList() {
  const resource = getResource();
  if (resource.projectScoped && !state.selectedProjectId) {
    ui.tableMeta.textContent = "Select a project to view details.";
    renderTable(resource, resource.columns, []);
    return;
  }
  showSkeleton();
  ui.tableMeta.textContent = "Loading...";
  const params = buildQueryParams(resource);
  const query = new URLSearchParams(params).toString();
  try {
    const payload = await fetchJson(`${resource.endpoint}?${query}`);
    const rows = enrichRows(resource, payload.data || []);
    state.lastRows[resource.key] = payload.data || [];
    renderTable(resource, resource.columns, rows);
    ui.tableMeta.textContent = `Total ${payload.total} | Page ${payload.page} of ${payload.total_pages}`;
  } catch (err) {
    ui.tableMeta.textContent = `Error: ${err.message}`;
    renderTable(resource, resource.columns, []);
  }
}

async function refreshLookups() {
  const [projects, tasks, vendors, laborers] = await Promise.all([
    fetchJson("/projects?page=1&page_size=200").then((payload) => payload.data),
    fetchJson("/tasks?page=1&page_size=200").then((payload) => payload.data),
    fetchJson("/vendors?page=1&page_size=200").then((payload) => payload.data),
    fetchJson("/laborers?page=1&page_size=200").then((payload) => payload.data),
  ]);
  state.lookups = { projects, tasks, vendors, laborers };
  if (state.selectedProjectId) {
    const updated = projects.find(
      (project) => project.id === state.selectedProjectId
    );
    if (updated) {
      state.selectedProject = updated;
      ui.projectTitle.textContent = updated.name;
      ui.projectMeta.textContent =
        updated.description || "No description provided.";
    }
  }
  renderProjects();
  updateProjectArchiveLabel();
}

function renderProjects() {
  const search = ui.projectSearch.value.trim().toLowerCase();
  ui.projectList.innerHTML = "";
  const projects = state.lookups.projects.filter((project) =>
    project.name.toLowerCase().includes(search)
  );
  projects.forEach((project) => {
    const card = document.createElement("div");
    card.className = "project-card";
    if (state.selectedProjectId === project.id) {
      card.classList.add("active");
    }
    const title = document.createElement("h3");
    title.textContent = project.name;
    const meta = document.createElement("p");
    meta.textContent = project.start_date
      ? `${project.start_date} -> ${project.end_date || "Open"}`
      : "No dates";
    card.appendChild(title);
    card.appendChild(meta);
    card.addEventListener("click", () => setProject(project));
    ui.projectList.appendChild(card);
  });
}

function updateBreadcrumb() {
  const resource = getResource();
  if (state.selectedProject) {
    ui.breadcrumb.textContent = `Projects > ${state.selectedProject.name} > ${resource.title}`;
  } else {
    ui.breadcrumb.textContent = "Projects";
  }
}

async function updateProjectSummary() {
  if (!state.selectedProjectId) {
    ui.totalMaterials.textContent = "-";
    ui.totalLabor.textContent = "-";
    ui.totalCombined.textContent = "-";
    ui.progressStrip.innerHTML = "";
    ui.projectGuidance.textContent = "";
    return;
  }

  const [tasksPayload, purchasesPayload, sessionsPayload] = await Promise.all([
    fetchJson(`/tasks?project_id=${state.selectedProjectId}&page=1&page_size=200`),
    fetchJson(
      `/material-purchases?project_id=${state.selectedProjectId}&page=1&page_size=200`
    ),
    fetchJson(
      `/work-sessions?project_id=${state.selectedProjectId}&page=1&page_size=200`
    ),
  ]);

  const tasksCount = tasksPayload.total || tasksPayload.data.length;
  const purchases = purchasesPayload.data || [];
  const sessions = sessionsPayload.data || [];

  const materialTotal = purchases.reduce(
    (sum, row) => sum + (row.total_material_cost || 0) + (row.delivery_cost || 0),
    0
  );

  const laborerMap = state.lookups.laborers.reduce((map, laborer) => {
    map[laborer.id] = laborer;
    return map;
  }, {});

  const laborTotal = sessions.reduce((sum, session) => {
    const entries = session.entries || [];
    return (
      sum +
      entries.reduce((entrySum, entry) => {
        const laborer = laborerMap[entry.laborer_id];
        if (!laborer) {
          return entrySum;
        }
        if (laborer.hourly_rate) {
          const hours = hoursBetween(
            session.work_date,
            entry.clock_in_time,
            entry.clock_out_time
          );
          return entrySum + hours * laborer.hourly_rate;
        }
        if (laborer.daily_rate) {
          return entrySum + laborer.daily_rate;
        }
        return entrySum;
      }, 0)
    );
  }, 0);

  const hasLaborRateForSessions = sessions.some((session) =>
    (session.entries || []).some((entry) => {
      const laborer = laborerMap[entry.laborer_id];
      return laborer && (laborer.hourly_rate || laborer.daily_rate);
    })
  );

  ui.totalMaterials.textContent = `$${materialTotal.toFixed(2)}`;
  ui.totalLabor.textContent = `$${laborTotal.toFixed(2)}`;
  ui.totalCombined.textContent = `$${(materialTotal + laborTotal).toFixed(2)}`;

  const progress = [
    { label: "Tasks added", done: tasksCount > 0 },
    { label: "Purchases logged", done: purchases.length > 0 },
    { label: "Labor scheduled", done: sessions.length > 0 },
  ];

  ui.progressStrip.innerHTML = "";
  progress.forEach((item) => {
    const pill = document.createElement("span");
    pill.className = `progress-item ${item.done ? "done" : ""}`;
    pill.textContent = item.label;
    ui.progressStrip.appendChild(pill);
  });

  let guidance = "";
  if (tasksCount === 0) {
    guidance = "Start by adding tasks to outline the work.";
  } else if (purchases.length === 0) {
    guidance = "Log materials to track costs.";
  } else if (sessions.length === 0) {
    guidance = "Log labor time to calculate labor costs.";
  } else if (!hasLaborRateForSessions) {
    guidance = "Add labor rates to calculate totals.";
  }
  ui.projectGuidance.textContent = guidance;
}

function rememberTab(projectId, tabKey) {
  if (!projectId) {
    return;
  }
  localStorage.setItem(`rmt_last_tab_${projectId}`, tabKey);
}

function getRememberedTab(projectId) {
  if (!projectId) {
    return null;
  }
  return localStorage.getItem(`rmt_last_tab_${projectId}`);
}

function setProject(project) {
  state.selectedProjectId = project.id;
  state.selectedProject = project;
  ui.projectTitle.textContent = project.name;
  ui.projectMeta.textContent = project.description || "No description provided.";
  const remembered = getRememberedTab(project.id);
  if (remembered) {
    state.activeTab = remembered;
  }
  renderProjects();
  renderTabs();
  renderFilterPanel();
  updateFilterToggle();
  updateBreadcrumb();
  updateProjectSummary();
  updateAddButton();
  updateProjectEditButton();
  updateProjectArchiveLabel();
  loadList();
}

function renderTabs() {
  ui.tabs.innerHTML = "";
  RESOURCES.forEach((resource) => {
    const tab = document.createElement("button");
    tab.className = "tab";
    if (resource.key === state.activeTab) {
      tab.classList.add("active");
    }
    tab.textContent = resource.title;
    tab.addEventListener("click", () => {
      state.activeTab = resource.key;
      rememberTab(state.selectedProjectId, resource.key);
      ui.pageInput.value = 1;
      renderTabs();
      renderFilterPanel();
      updateFilterToggle();
      updateBreadcrumb();
      updateAddButton();
      updateProjectEditButton();
      loadList();
    });
    ui.tabs.appendChild(tab);
  });
}

function updateAddButton() {
  const resource = getResource();
  ui.addToggle.disabled = resource.projectScoped && !state.selectedProjectId;
}

function updateProjectEditButton() {
  ui.projectEdit.disabled = !state.selectedProjectId;
  ui.projectArchive.disabled = !state.selectedProjectId;
  ui.projectDelete.disabled = !state.selectedProjectId;
}

function updateProjectArchiveLabel() {
  if (!state.selectedProject) {
    ui.projectArchive.textContent = "Archive";
    return;
  }
  ui.projectArchive.textContent = state.selectedProject.archived_at
    ? "Restore"
    : "Archive";
}

function createRowMenu(resource, row) {
  const wrapper = document.createElement("div");
  wrapper.className = "row-menu";
  const toggle = document.createElement("button");
  toggle.className = "btn ghost";
  toggle.textContent = "...";
  const menu = document.createElement("div");
  menu.className = "row-menu-panel";

  const editButton = document.createElement("button");
  editButton.className = "btn ghost";
  editButton.textContent = "Edit";
  editButton.addEventListener("click", () => {
    openModal(resource, { mode: "edit", data: row });
    menu.classList.remove("open");
  });

  const archiveButton = document.createElement("button");
  archiveButton.className = "btn ghost";
  const isArchived = Boolean(row.archived_at);
  archiveButton.textContent = isArchived ? "Restore" : "Archive";
  archiveButton.addEventListener("click", () => {
    if (isArchived) {
      restoreRecord(resource, row.id);
    } else {
      archiveRecord(resource, row.id);
    }
    menu.classList.remove("open");
  });

  const deleteButton = document.createElement("button");
  deleteButton.className = "btn ghost";
  deleteButton.textContent = "Delete";
  deleteButton.addEventListener("click", () => {
    deleteRecord(resource, row.id);
    menu.classList.remove("open");
  });

  menu.appendChild(editButton);
  menu.appendChild(archiveButton);
  menu.appendChild(deleteButton);

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.classList.toggle("open");
  });

  document.addEventListener("click", () => {
    menu.classList.remove("open");
  });

  wrapper.appendChild(toggle);
  wrapper.appendChild(menu);
  return wrapper;
}

function createDirectoryMenu(activeKey, item) {
  const wrapper = document.createElement("div");
  wrapper.className = "row-menu";
  const toggle = document.createElement("button");
  toggle.className = "btn ghost";
  toggle.textContent = "...";
  const menu = document.createElement("div");
  menu.className = "row-menu-panel";

  const editButton = document.createElement("button");
  editButton.className = "btn ghost";
  editButton.textContent = "Edit";
  editButton.addEventListener("click", () => {
    openManageEdit(activeKey, item);
    menu.classList.remove("open");
  });

  const archiveButton = document.createElement("button");
  archiveButton.className = "btn ghost";
  const isArchived = Boolean(item.archived_at);
  archiveButton.textContent = isArchived ? "Restore" : "Archive";
  archiveButton.addEventListener("click", () => {
    const resource = {
      title: activeKey === "vendors" ? "Vendor" : "Laborer",
      endpoint: `/${activeKey}`,
    };
    if (isArchived) {
      restoreRecord(resource, item.id);
    } else {
      archiveRecord(resource, item.id);
    }
    menu.classList.remove("open");
  });

  const deleteButton = document.createElement("button");
  deleteButton.className = "btn ghost";
  deleteButton.textContent = "Delete";
  deleteButton.addEventListener("click", () => {
    deleteRecord(
      { title: activeKey === "vendors" ? "Vendor" : "Laborer", endpoint: `/${activeKey}` },
      item.id
    );
    menu.classList.remove("open");
  });

  menu.appendChild(editButton);
  menu.appendChild(archiveButton);
  menu.appendChild(deleteButton);

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.classList.toggle("open");
  });

  document.addEventListener("click", () => {
    menu.classList.remove("open");
  });

  wrapper.appendChild(toggle);
  wrapper.appendChild(menu);
  return wrapper;
}

function createField(field, options = [], config = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";
  if (field.emphasis) {
    wrapper.classList.add("emphasis");
  }
  const label = document.createElement("label");
  label.textContent = field.label;
  const error = document.createElement("div");
  error.className = "field-error muted";
  error.style.display = "none";
  let input;
  const initialValue = config.initialValue || "";
  if (field.type === "select") {
    input = document.createElement("select");
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select";
    input.appendChild(placeholder);
    options.forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      input.appendChild(option);
    });
  } else {
    input = document.createElement("input");
    input.type = field.type;
  }
  input.name = field.name;
  if (initialValue) {
    input.value = initialValue;
  }
  if (field.type === "number") {
    input.step = "any";
    if (field.min !== undefined) {
      input.min = String(field.min);
    }
  }
  wrapper.appendChild(label);
  wrapper.appendChild(input);
  wrapper.appendChild(error);
  return { wrapper, input, error };
}

function getOptions(fieldName) {
  if (fieldName === "project_id") {
    return state.lookups.projects.map((item) => ({
      value: item.id,
      label: item.name,
    }));
  }
  if (fieldName === "task_id") {
    const tasks = state.selectedProjectId
      ? state.lookups.tasks.filter(
          (task) => task.project_id === state.selectedProjectId
        )
      : state.lookups.tasks;
    return tasks.map((item) => ({
      value: item.id,
      label: item.name,
    }));
  }
  if (fieldName === "vendor_id") {
    return state.lookups.vendors.map((item) => ({
      value: item.id,
      label: item.name,
    }));
  }
  if (fieldName === "laborer_id") {
    return state.lookups.laborers.map((item) => ({
      value: item.id,
      label: item.name,
    }));
  }
  return [];
}

function renderFilterPanel() {
  const resource = getResource();
  ui.filterPanel.innerHTML = "";
  const filters = resource.filters;
  const current = state.filters[resource.key] || {};
  filters.forEach((field) => {
    const options = field.type === "select" ? getOptions(field.name) : [];
    const { wrapper, input } = createField(field, options, {
      allowClear: true,
      initialValue: current[field.name],
    });
    input.addEventListener("change", () => {
      const value = input.value.trim();
      if (!state.filters[resource.key]) {
        state.filters[resource.key] = {};
      }
      state.filters[resource.key][field.name] = value || null;
      updateFilterToggle();
    });
    ui.filterPanel.appendChild(wrapper);
  });

  const apply = document.createElement("button");
  apply.className = "btn ghost";
  apply.textContent = "Apply filters";
  apply.addEventListener("click", () => {
    const filters = state.filters[resource.key] || {};
    if (filters.start_date && filters.end_date) {
      if (filters.start_date > filters.end_date) {
        showToast("Start date must be before end date.", "error");
        return;
      }
    }
    ui.pageInput.value = 1;
    setPaginationForTab();
    loadList();
  });
  ui.filterPanel.appendChild(apply);
}

function updateFilterToggle() {
  const resource = getResource();
  const filters = state.filters[resource.key] || {};
  const active = Object.values(filters).some((value) => value);
  ui.filterToggle.classList.toggle("primary", active);
}

function setPaginationForTab() {
  const page = Number(ui.pageInput.value || 1);
  const pageSize = Number(ui.pageSizeInput.value || 25);
  state.pagination[state.activeTab] = { page, page_size: pageSize };
}

function openModal(resource, context = {}) {
  const isEdit = context.mode === "edit";
  const existing = context.data || {};
  ui.modalTitle.textContent = isEdit ? `Edit ${resource.title}` : `Add ${resource.title}`;
  ui.modalBody.innerHTML = "";
  ui.modalStatus.textContent = "";
  ui.modal.classList.remove("hidden");
  ui.modal.setAttribute("aria-hidden", "false");
  ui.modalSave.disabled = false;
  ui.modalSave.textContent = isEdit ? "Save changes" : "Save";
  ui.modal.querySelector(".modal-card").className = `modal-card ${getModalClass(resource.key)}`;

  if (resource.modalDescription) {
    const description = document.createElement("div");
    description.className = "modal-description";
    description.textContent = resource.modalDescription;
    ui.modalBody.appendChild(description);
  }

  const fields = [];
  resource.createFields.forEach((field) => {
    const options = field.type === "select" ? getOptions(field.name) : [];
    let initialValue =
      existing[field.name] !== undefined && existing[field.name] !== null
        ? String(existing[field.name])
        : "";
    if (field.type === "datetime-local" && initialValue) {
      initialValue = initialValue.replace(" ", "T");
    }
    const fieldNodes = createField(field, options, {
      allowClear: !field.required,
      initialValue,
    });
    if (field.name === "project_id" && state.selectedProjectId) {
      if (!isEdit && !initialValue) {
        fieldNodes.input.value = state.selectedProjectId;
      }
      if (resource.projectScoped && !isEdit) {
        fieldNodes.input.disabled = true;
      }
    }
    fields.push({ field, ...fieldNodes });
    ui.modalBody.appendChild(fieldNodes.wrapper);
    fieldNodes.input.addEventListener("input", () =>
      validateField(field, fieldNodes)
    );

    if (field.name === "vendor_id") {
      attachInlineVendorCreate(fieldNodes.wrapper, fieldNodes.input);
    }
    if (field.name === "laborer_id") {
      attachInlineLaborerLink(fieldNodes.wrapper);
    }
  });

  if (resource.key === "material-purchases") {
    const total = document.createElement("div");
    total.className = "muted";
    total.id = "purchase-total";
    total.textContent = "Total material cost: 0";
    ui.modalBody.appendChild(total);
  }

  if (resource.key === "work-sessions") {
    const entryList = document.createElement("div");
    entryList.className = "entry-list";
    entryList.id = "entry-list";
    ui.modalBody.appendChild(entryList);

    const addEntryButton = document.createElement("button");
    addEntryButton.className = "btn ghost";
    addEntryButton.textContent = "Add labor entry";
    ui.modalBody.appendChild(addEntryButton);

    addEntryButton.addEventListener("click", () => addLaborEntry(entryList));
    const entries = existing.entries || [];
    if (entries.length) {
      entries.forEach((entry) => addLaborEntry(entryList, entry));
    } else {
      addLaborEntry(entryList);
    }

    const taskField = fields.find((item) => item.field.name === "task_id");
    const workDateField = fields.find((item) => item.field.name === "work_date");
    const toggleDependents = () => {
      const enabled = Boolean(taskField?.input.value);
      if (workDateField) {
        workDateField.input.disabled = !enabled;
      }
      addEntryButton.disabled = !enabled;
      entryList.querySelectorAll("input, select, button").forEach((input) => {
        if (input === addEntryButton) {
          return;
        }
        input.disabled = !enabled;
      });
    };
    if (taskField) {
      taskField.input.addEventListener("change", toggleDependents);
      toggleDependents();
    }
  }

  ui.modalSave.onclick = async () => {
    const validation = validateForm(resource, fields);
    if (!validation.valid) {
      ui.modalStatus.textContent = validation.message;
      ui.modalStatus.classList.add("error");
      return;
    }
    ui.modalSave.disabled = true;
    ui.modalStatus.textContent = "Saving...";
    ui.modalStatus.classList.remove("error");
    try {
      const payload = buildPayload(fields);
      if (resource.key === "work-sessions") {
        payload.entries = collectLaborEntries();
      }
      const toastLabel = buildToastLabel(resource, payload, isEdit);
      const method = isEdit ? "PUT" : "POST";
      const url = isEdit ? `${resource.endpoint}/${existing.id}` : resource.endpoint;
      const response = await fetchJson(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showToast(toastLabel || defaultToast(resource, response, isEdit));
      ui.modal.classList.add("hidden");
      await refreshLookups();
      updateProjectSummary();
      loadList();
    } catch (err) {
      ui.modalSave.disabled = false;
      ui.modalStatus.textContent = err.message;
      ui.modalStatus.classList.add("error");
      showToast(err.message, "error");
    }
  };

  fields.forEach(({ input }) => {
    if (resource.key === "material-purchases") {
      input.addEventListener("input", () => updatePurchaseTotal(fields));
    }
  });
}

function getModalClass(resourceKey) {
  if (resourceKey === "projects") {
    return "project";
  }
  if (resourceKey === "material-purchases") {
    return "purchase";
  }
  if (resourceKey === "work-sessions") {
    return "session";
  }
  return "";
}

function attachInlineVendorCreate(wrapper, selectInput) {
  const link = document.createElement("div");
  link.className = "inline-link";
  link.textContent = "Open vendor directory";
  link.addEventListener("click", () => openManageModal("vendors"));
  wrapper.appendChild(link);
}

function attachInlineLaborerLink(wrapper) {
  const hint = document.createElement("div");
  hint.className = "row-muted";
  hint.textContent = "Need a new laborer? Use Manage vendors & labor.";
  wrapper.appendChild(hint);
}

function closeModal() {
  ui.modal.classList.add("hidden");
  ui.modal.setAttribute("aria-hidden", "true");
}

function updatePurchaseTotal(fields) {
  const unit = Number(
    fields.find((item) => item.field.name === "unit_cost")?.input.value || 0
  );
  const quantity = Number(
    fields.find((item) => item.field.name === "quantity")?.input.value || 0
  );
  const total = unit * quantity;
  const label = document.getElementById("purchase-total");
  if (label) {
    label.textContent = `Total material cost: ${total.toFixed(2)}`;
  }
}

function buildPayload(fields) {
  const payload = {};
  fields.forEach(({ field, input }) => {
    let value = input.value;
    if (!value) {
      return;
    }
    if (field.type === "number" || field.type === "select") {
      value = Number(value);
    }
    if (field.type === "datetime-local") {
      value = value.replace("T", " ");
    }
    payload[field.name] = value;
  });
  return payload;
}

function buildToastLabel(resource, payload, isEdit) {
  const name =
    payload.name ||
    payload.material_description ||
    payload.work_date ||
    payload.task_id;
  if (!name) {
    return null;
  }
  const action = isEdit ? "Updated" : "Saved";
  if (resource.key === "material-purchases") {
    return `${action} purchase: ${payload.material_description}`;
  }
  if (resource.key === "work-sessions") {
    const count = payload.entries ? payload.entries.length : 0;
    return `${action} work session (${count} entries)`;
  }
  return `${action} ${resource.title.toLowerCase()}: ${name}`;
}

function defaultToast(resource, response, isEdit) {
  if (isEdit) {
    return `${resource.title} updated.`;
  }
  return `${resource.title} saved.`;
}

function addLaborEntry(entryList, entry = {}) {
  const row = document.createElement("div");
  row.className = "entry-row";

  const laborerOptions = getOptions("laborer_id");
  const laborerField = createField(
    {
      name: "entry_laborer_id",
      label: "Laborer",
      type: "select",
      required: true,
    },
    laborerOptions,
    { allowClear: false, initialValue: entry.laborer_id ? String(entry.laborer_id) : "" }
  );
  const clockInField = createField(
    {
      name: "entry_clock_in",
      label: "Clock in",
      type: "time",
      required: true,
      emphasis: true,
    },
    [],
    {}
  );
  const clockOutField = createField(
    {
      name: "entry_clock_out",
      label: "Clock out",
      type: "time",
      required: true,
      emphasis: true,
    },
    [],
    {}
  );
  if (entry.clock_in_time) {
    clockInField.input.value = entry.clock_in_time;
  }
  if (entry.clock_out_time) {
    clockOutField.input.value = entry.clock_out_time;
  }
  const removeButton = document.createElement("button");
  removeButton.className = "btn ghost";
  removeButton.textContent = "Remove";
  removeButton.type = "button";
  removeButton.addEventListener("click", () => row.remove());

  row.appendChild(laborerField.wrapper);
  row.appendChild(clockInField.wrapper);
  row.appendChild(clockOutField.wrapper);
  row.appendChild(removeButton);

  entryList.appendChild(row);
}

function collectLaborEntries() {
  const entryRows = document.querySelectorAll(".entry-row");
  const entries = [];
  entryRows.forEach((row) => {
    const laborerSelect = row.querySelector('select[name="entry_laborer_id"]');
    const clockIn = row.querySelector('input[name="entry_clock_in"]');
    const clockOut = row.querySelector('input[name="entry_clock_out"]');
    if (!laborerSelect || !clockIn || !clockOut) {
      return;
    }
    if (!laborerSelect.value || !clockIn.value || !clockOut.value) {
      return;
    }
    entries.push({
      laborer_id: Number(laborerSelect.value),
      clock_in_time: clockIn.value,
      clock_out_time: clockOut.value,
    });
  });
  return entries;
}

function validateField(field, fieldNodes) {
  const value = fieldNodes.input.value.trim();
  let message = "";
  if (field.required && !value) {
    message = "Required";
  }
  if (value && field.type === "number" && Number.isNaN(Number(value))) {
    message = "Must be a number";
  }
  if (
    value &&
    field.type === "number" &&
    field.min !== undefined &&
    Number(value) < field.min
  ) {
    message = `Must be at least ${field.min}`;
  }
  if (message) {
    fieldNodes.error.textContent = message;
    fieldNodes.error.style.display = "block";
    return false;
  }
  fieldNodes.error.textContent = "";
  fieldNodes.error.style.display = "none";
  return true;
}

function validateForm(resource, fields) {
  let valid = true;
  fields.forEach((fieldNodes) => {
    if (!validateField(fieldNodes.field, fieldNodes)) {
      valid = false;
    }
  });

  const values = Object.fromEntries(
    fields.map(({ field, input }) => [field.name, input.value.trim()])
  );

  if (resource.key === "projects" && values.start_date && values.end_date) {
    if (values.end_date < values.start_date) {
      valid = false;
      return { valid: false, message: "End date must be after start date." };
    }
  }

  if (resource.key === "tasks" && values.start_datetime && values.end_datetime) {
    if (values.end_datetime <= values.start_datetime) {
      valid = false;
      return { valid: false, message: "End datetime must be after start." };
    }
  }

  if (resource.key === "work-sessions") {
    const entryRows = document.querySelectorAll(".entry-row");
    for (const row of entryRows) {
      const laborerSelect = row.querySelector('select[name="entry_laborer_id"]');
      const clockIn = row.querySelector('input[name="entry_clock_in"]');
      const clockOut = row.querySelector('input[name="entry_clock_out"]');
      const filled = [
        laborerSelect?.value,
        clockIn?.value,
        clockOut?.value,
      ].filter(Boolean).length;
      if (filled > 0 && filled < 3) {
        return { valid: false, message: "Complete or remove each labor entry." };
      }
    }
    const entries = collectLaborEntries();
    if (!entries.length) {
      return { valid: false, message: "Add at least one labor entry." };
    }
    for (const entry of entries) {
      if (entry.clock_out_time <= entry.clock_in_time) {
        return { valid: false, message: "Clock out must be after clock in." };
      }
    }
  }

  return { valid, message: valid ? "" : "Fix validation errors." };
}

function buildProjectModal() {
  openModal({
    key: "projects",
    title: "Project",
    endpoint: "/projects",
    projectScoped: false,
    modalDescription:
      "Define the renovation scope. You can add tasks and purchases after saving.",
    createFields: [
      { name: "name", label: "Project name", type: "text", required: true },
      { name: "description", label: "Description", type: "text" },
      { name: "start_date", label: "Start date", type: "date" },
      { name: "end_date", label: "End date", type: "date" },
    ],
  });
}

function buildProjectEditModal() {
  if (!state.selectedProject) {
    showToast("Select a project first.", "error");
    return;
  }
  openModal(
    {
      key: "projects",
      title: "Project",
      endpoint: "/projects",
      projectScoped: false,
      modalDescription: "Update the project details.",
      createFields: [
        { name: "name", label: "Project name", type: "text", required: true },
        { name: "description", label: "Description", type: "text" },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
      ],
    },
    { mode: "edit", data: state.selectedProject }
  );
}

async function archiveProject() {
  if (!state.selectedProjectId) {
    showToast("Select a project first.", "error");
    return;
  }
  if (state.selectedProject?.archived_at) {
    await restoreRecord(
      { title: "Project", endpoint: "/projects" },
      state.selectedProjectId
    );
  } else {
    await archiveRecord(
      { title: "Project", endpoint: "/projects" },
      state.selectedProjectId
    );
  }
}

async function deleteProject() {
  if (!state.selectedProjectId) {
    showToast("Select a project first.", "error");
    return;
  }
  await deleteRecord({ title: "Project", endpoint: "/projects" }, state.selectedProjectId);
}

async function archiveRecord(resource, recordId) {
  if (!confirm("Archive this record?")) {
    return;
  }
  try {
    await fetchJson(`${resource.endpoint}/${recordId}/archive`, {
      method: "POST",
    });
    showToast(`${resource.title} archived.`);
    await refreshLookups();
    updateProjectSummary();
    loadList();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function restoreRecord(resource, recordId) {
  try {
    await fetchJson(`${resource.endpoint}/${recordId}/restore`, {
      method: "POST",
    });
    showToast(`${resource.title} restored.`);
    await refreshLookups();
    updateProjectSummary();
    loadList();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRecord(resource, recordId) {
  if (!confirm("Delete this record? This cannot be undone.")) {
    return;
  }
  try {
    await fetchJson(`${resource.endpoint}/${recordId}`, { method: "DELETE" });
    showToast(`${resource.title} deleted.`);
    await refreshLookups();
    updateProjectSummary();
    loadList();
  } catch (err) {
    showToast(err.message, "error");
  }
}


function openManageModal(activeKey = "vendors") {
  ui.manageModal.classList.remove("hidden");
  ui.manageModal.setAttribute("aria-hidden", "false");
  ui.manageStatus.textContent = "";
  const tabs = ui.manageModal.querySelectorAll("[data-manage]");
  tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.manage === activeKey);
    tab.addEventListener("click", () => openManageModal(tab.dataset.manage));
  });
  renderManageBody(activeKey);
}

function closeManageModal() {
  ui.manageModal.classList.add("hidden");
  ui.manageModal.setAttribute("aria-hidden", "true");
}

function renderManageBody(activeKey) {
  ui.manageBody.innerHTML = "";
  const heading = document.createElement("div");
  heading.className = "label";
  heading.textContent =
    activeKey === "vendors" ? "Vendor directory" : "Labor directory";
  ui.manageBody.appendChild(heading);
  const list = document.createElement("div");
  list.className = "manage-list";

  const items =
    activeKey === "vendors" ? state.lookups.vendors : state.lookups.laborers;
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "manage-row";
    const details = document.createElement("div");
    const name = document.createElement("span");
    name.textContent = item.name;
    const meta = document.createElement("div");
    meta.className = "row-muted";
    if (activeKey === "laborers") {
      meta.textContent = item.hourly_rate
        ? `$${item.hourly_rate}/hr`
        : item.daily_rate
          ? `$${item.daily_rate}/day`
          : "";
    }
    details.appendChild(name);
    details.appendChild(meta);
    const menu = createDirectoryMenu(activeKey, item);
    row.appendChild(details);
    row.appendChild(menu);
    list.appendChild(row);
  });

  const form = document.createElement("div");
  form.className = "inline-create";
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder =
    activeKey === "vendors" ? "New vendor name" : "New laborer name";
  form.appendChild(input);

  let hourly = null;
  let daily = null;
  if (activeKey === "laborers") {
    hourly = document.createElement("input");
    hourly.type = "number";
    hourly.placeholder = "Hourly rate";
    daily = document.createElement("input");
    daily.type = "number";
    daily.placeholder = "Daily rate";
    form.appendChild(hourly);
    form.appendChild(daily);
  }

  const button = document.createElement("button");
  button.className = "btn ghost";
  button.textContent = "Add";
  form.appendChild(button);

  button.addEventListener("click", async () => {
    const name = input.value.trim();
    if (!name) {
      ui.manageStatus.textContent = "Name is required.";
      ui.manageStatus.classList.add("error");
      return;
    }
    const payload = { name };
    if (activeKey === "laborers") {
      const hourlyValue = hourly.value;
      const dailyValue = daily.value;
      if (hourlyValue) {
        payload.hourly_rate = Number(hourlyValue);
      }
      if (dailyValue) {
        payload.daily_rate = Number(dailyValue);
      }
      if (!payload.hourly_rate && !payload.daily_rate) {
        ui.manageStatus.textContent = "Provide hourly or daily rate.";
        ui.manageStatus.classList.add("error");
        return;
      }
    }
    try {
      await fetchJson(`/${activeKey}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refreshLookups();
      renderManageBody(activeKey);
      ui.manageStatus.textContent = "Saved.";
      ui.manageStatus.classList.remove("error");
    } catch (err) {
      ui.manageStatus.textContent = err.message;
      ui.manageStatus.classList.add("error");
    }
  });

  ui.manageBody.appendChild(list);
  ui.manageBody.appendChild(form);
}

function openManageEdit(activeKey, item) {
  ui.modalTitle.textContent = `Edit ${activeKey === "vendors" ? "Vendor" : "Laborer"}`;
  ui.modalBody.innerHTML = "";
  ui.modalStatus.textContent = "";
  ui.modal.classList.remove("hidden");
  ui.modalSave.textContent = "Save changes";
  ui.modal.querySelector(".modal-card").className = "modal-card";
  const fields = [];
  const nameField = createField(
    { name: "name", label: "Name", type: "text", required: true },
    [],
    { initialValue: item.name }
  );
  fields.push({ field: { name: "name", type: "text", required: true }, ...nameField });
  ui.modalBody.appendChild(nameField.wrapper);

  if (activeKey === "laborers") {
    const hourlyField = createField(
      { name: "hourly_rate", label: "Hourly rate", type: "number", min: 0 },
      [],
      { initialValue: item.hourly_rate ? String(item.hourly_rate) : "" }
    );
    const dailyField = createField(
      { name: "daily_rate", label: "Daily rate", type: "number", min: 0 },
      [],
      { initialValue: item.daily_rate ? String(item.daily_rate) : "" }
    );
    fields.push({ field: { name: "hourly_rate", type: "number", min: 0 }, ...hourlyField });
    fields.push({ field: { name: "daily_rate", type: "number", min: 0 }, ...dailyField });
    ui.modalBody.appendChild(hourlyField.wrapper);
    ui.modalBody.appendChild(dailyField.wrapper);
  }

  ui.modalSave.onclick = async () => {
    const payload = buildPayload(fields);
    if (!payload.name) {
      ui.modalStatus.textContent = "Name is required.";
      ui.modalStatus.classList.add("error");
      return;
    }
    if (activeKey === "laborers") {
      if (!payload.hourly_rate && !payload.daily_rate) {
        ui.modalStatus.textContent = "Provide hourly or daily rate.";
        ui.modalStatus.classList.add("error");
        return;
      }
    }
    try {
      await fetchJson(`/${activeKey}/${item.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showToast(`${activeKey === "vendors" ? "Vendor" : "Laborer"} updated.`);
      closeModal();
      await refreshLookups();
      renderManageBody(activeKey);
    } catch (err) {
      ui.modalStatus.textContent = err.message;
      ui.modalStatus.classList.add("error");
    }
  };
}

function showTipsOnce() {
  if (localStorage.getItem("rmt_tips_seen")) {
    return;
  }
  const tooltip = document.createElement("div");
  tooltip.className = "toast";
  tooltip.textContent = "Tip: Filters and Add actions live here.";
  tooltip.style.position = "absolute";
  tooltip.style.top = "-10px";
  tooltip.style.right = "10px";
  ui.tableWrap.parentElement.prepend(tooltip);
  setTimeout(() => {
    tooltip.remove();
    localStorage.setItem("rmt_tips_seen", "true");
  }, 5000);
}

ui.filterToggle.addEventListener("click", () => {
  ui.filterPanel.classList.toggle("hidden");
});

ui.pageApply.addEventListener("click", () => {
  setPaginationForTab();
  loadList();
});

ui.addToggle.addEventListener("click", () => {
  openModal(getResource());
});

ui.modalClose.addEventListener("click", closeModal);
ui.modalCancel.addEventListener("click", closeModal);
ui.projectAdd.addEventListener("click", buildProjectModal);
ui.projectEdit.addEventListener("click", buildProjectEditModal);
ui.projectArchive.addEventListener("click", archiveProject);
ui.projectDelete.addEventListener("click", deleteProject);
ui.backupNow.addEventListener("click", async () => {
  ui.backupNow.disabled = true;
  try {
    await fetchJson("/backups", { method: "POST" });
    showToast("Backup created.");
    await refreshStatusPanel();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    ui.backupNow.disabled = false;
  }
});
ui.showArchived.addEventListener("change", () => {
  ui.pageInput.value = 1;
  setPaginationForTab();
  loadList();
});
ui.projectSearch.addEventListener("input", renderProjects);
ui.manageEntities.addEventListener("click", () => openManageModal("vendors"));
ui.manageClose.addEventListener("click", closeManageModal);

ui.refreshAll.addEventListener("click", async () => {
  await refreshLookups();
  await refreshStatusPanel();
  updateProjectSummary();
  loadList();
});

if (ui.apiKeyInput) {
  ui.apiKeyInput.value = getApiKey();
  ui.apiKeyInput.addEventListener("change", (event) => {
    setApiKey(event.target.value);
    showToast("API key saved.");
  });
}

async function refreshStatusPanel() {
  try {
    const backup = await fetchJson("/backups");
    const lastBackup = backup.last_backup_at
      ? `${backup.last_backup_at} UTC`
      : "No backups yet";
    ui.backupStatus.textContent = `${lastBackup} (retention ${backup.retention_days}d)`;
  } catch (err) {
    ui.backupStatus.textContent = "Unavailable";
  }

  try {
    const migrations = await fetchJson("/migrations");
    ui.migrationStatus.textContent = `${migrations.count} applied`;
  } catch (err) {
    ui.migrationStatus.textContent = "Unavailable";
  }
}

async function init() {
  renderTabs();
  await refreshLookups();
  await refreshStatusPanel();
  const firstProject = state.lookups.projects[0];
  if (firstProject) {
    setProject(firstProject);
  } else {
    ui.projectTitle.textContent = "No projects found";
    ui.projectMeta.textContent = "Add a project to get started.";
    updateBreadcrumb();
    updateProjectSummary();
  }
  renderFilterPanel();
  updateFilterToggle();
  updateAddButton();
  updateProjectEditButton();
  updateProjectArchiveLabel();
  showTipsOnce();
}

init();
