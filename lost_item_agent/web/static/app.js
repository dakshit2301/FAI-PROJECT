"use strict";

const state = {
  config: null,
  lastCampusResult: null,
  lastGridResult: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove("visible"), 4000);
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function setBusy(element, busy, label) {
  if (!element.dataset.label) element.dataset.label = element.textContent;
  element.disabled = busy;
  element.textContent = busy ? label : element.dataset.label;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function optionMarkup(value, label = value) {
  return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
}

function populateSelect(selector, values, selected) {
  const select = $(selector);
  select.innerHTML = values.map((value) => optionMarkup(value)).join("");
  if (selected) select.value = selected;
}

function checkedValues(container) {
  return $$(`${container} input:checked`).map((input) => input.value);
}

function renderChecks(container, values, checked = [], prefix = "option") {
  const selected = new Set(checked);
  $(container).innerHTML = values.map((value, index) => `
    <label class="check-option">
      <input type="checkbox" value="${escapeHtml(value)}" id="${prefix}-${index}" ${selected.has(value) ? "checked" : ""}>
      <span>${escapeHtml(value)}</span>
    </label>`).join("");
}

function campusCoordinates(node) {
  return {
    x: 58 + node.x * 82,
    y: 695 - node.y * 72,
  };
}

function renderCampusMap(result = state.lastCampusResult) {
  const config = state.config;
  const candidates = new Set(result?.candidate_results?.map((item) => item.candidate) || checkedValues("#candidate-options"));
  const visited = new Set(checkedValues("#visited-options"));
  const path = new Set(result?.path || []);
  const blocked = new Set((result?.blocked_edges || checkedValues("#blocked-options").map((index) => config.edges[Number(index)]?.source ? [config.edges[Number(index)].source, config.edges[Number(index)].target] : []))
    .map((edge) => [...edge].sort().join("|")));
  const recovered = result?.recovered_location || "";
  const current = $("#current-location").value;
  const lastSeen = $("#last-seen").value;
  const nodeByName = new Map(config.nodes.map((node) => [node.name, node]));

  const edgeMarkup = config.edges.map((edge) => {
    const source = nodeByName.get(edge.source);
    const target = nodeByName.get(edge.target);
    if (!source || !target) return "";
    const from = campusCoordinates(source);
    const to = campusCoordinates(target);
    const key = [edge.source, edge.target].sort().join("|");
    const isBlocked = blocked.has(key);
    const isRoute = !isBlocked && path.has(edge.source) && path.has(edge.target)
      && (result?.path || []).some((name, index, list) =>
        index < list.length - 1
        && ((name === edge.source && list[index + 1] === edge.target)
          || (name === edge.target && list[index + 1] === edge.source)));
    const labelX = (from.x + to.x) / 2;
    const labelY = (from.y + to.y) / 2 - 4;
    return `<g><line class="edge${isBlocked ? " blocked" : ""}${isRoute ? " route" : ""}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"></line>
      <text class="edge-label" x="${labelX}" y="${labelY}" text-anchor="middle">${formatNumber(edge.weight, 1)}</text></g>`;
  }).join("");

  const nodeMarkup = config.nodes.map((node) => {
    const { x, y } = campusCoordinates(node);
    const classes = ["node"];
    if (node.name === current) classes.push("current");
    else if (node.name === recovered) classes.push("recovered");
    else if (node.name === lastSeen) classes.push("last-seen");
    else if (candidates.has(node.name)) classes.push("candidate");
    else classes.push("normal");
    if (visited.has(node.name)) classes.push("visited");
    if (path.has(node.name)) classes.push("route");
    const overlapRing = node.name === current && node.name === lastSeen
      ? `<circle class="node last-seen-ring" cx="${x}" cy="${y}" r="13"></circle>`
      : "";
    return `<g>${overlapRing}<circle class="${classes.join(" ")}" cx="${x}" cy="${y}" r="8"></circle>
      <text class="node-label" x="${x + 12}" y="${y + 3}">${escapeHtml(node.name)}</text></g>`;
  }).join("");

  $("#campus-map").innerHTML = `
    <svg viewBox="0 0 790 760" role="img" aria-label="Schematic campus map showing current positions, candidates, and the search route">
      <rect class="floor-panel" x="35" y="365" width="675" height="355" rx="14"></rect>
      <rect class="floor-panel" x="125" y="38" width="555" height="300" rx="14"></rect>
      <text class="floor-title" x="55" y="390">GROUND FLOOR</text>
      <text class="floor-title" x="145" y="65">FIRST FLOOR</text>
      <text class="floor-title" x="74" y="300">STAIR CONNECTOR</text>
      ${edgeMarkup}${nodeMarkup}
    </svg>`;
}

function candidateOptionsChanged() {
  const category = $("#item-category").value;
  const defaults = state.config.item_candidates[category] || state.config.item_candidates.laptop;
  renderChecks("#candidate-options", state.config.locations, defaults, "candidate");
  renderBeliefs();
  populateActualLocation();
  renderCampusMap();
}

function populateActualLocation() {
  const candidates = [...new Set([...checkedValues("#candidate-options"), ...checkedValues("#visited-options")])];
  const actual = $("#actual-location");
  const previous = actual.value;
  actual.innerHTML = candidates.map((value) => optionMarkup(value)).join("");
  if (candidates.includes(previous)) actual.value = previous;
  else if (candidates.length) actual.value = candidates[0];
}

function renderBeliefs() {
  const candidates = [...new Set([...checkedValues("#candidate-options"), ...checkedValues("#visited-options")])];
  $("#belief-options").innerHTML = candidates.length
    ? candidates.map((candidate, index) => `
      <label class="belief-row" for="belief-${index}">
        <span>${escapeHtml(candidate)}</span>
        <input id="belief-${index}" type="range" min="0.05" max="0.95" step="0.05" value="0.5" data-candidate="${escapeHtml(candidate)}">
        <output>0.50</output>
      </label>`).join("")
    : '<p class="field-help">Choose at least one location to adjust beliefs.</p>';
}

function probabilities() {
  return Object.fromEntries($$("#belief-options input").map((input) => [input.dataset.candidate, Number(input.value)]));
}

function searchPayload(mode) {
  const category = $("#item-category").value;
  const description = category === "other / custom" ? ($("#custom-item").value.trim() || "custom item") : category;
  const candidates = checkedValues("#candidate-options");
  const visited = checkedValues("#visited-options");
  return {
    mode,
    item_description: description,
    start: $("#current-location").value,
    last_seen: $("#last-seen").value,
    candidates,
    visited,
    probabilities: probabilities(),
    algorithm: $("#search-algorithm").value,
    heuristic: $("#search-heuristic").value,
    actual_location: $("#actual-location").value,
    blocked_edges: checkedValues("#blocked-options").map((value) => {
      const edge = state.config.edges[Number(value)];
      return edge ? [edge.source, edge.target] : null;
    }).filter(Boolean),
  };
}

function metricsMarkup(search, heading) {
  if (!search) return "";
  const cost = search.success ? formatNumber(search.path_cost) : "No route";
  return `<div class="card result-panel">
    <h3>${escapeHtml(heading)}</h3>
    <div class="metric-grid">
      <div class="metric"><span>Status</span><strong>${search.success ? "Found" : "Unreachable"}</strong></div>
      <div class="metric"><span>Path cost</span><strong>${cost}</strong></div>
      <div class="metric"><span>Path length</span><strong>${search.path_length}</strong></div>
      <div class="metric"><span>Nodes expanded</span><strong>${search.nodes_expanded}</strong></div>
      <div class="metric"><span>Nodes generated</span><strong>${search.nodes_generated}</strong></div>
      <div class="metric"><span>Runtime</span><strong>${formatNumber(search.execution_time_ms, 3)} ms</strong></div>
      <div class="metric"><span>Algorithm</span><strong>${escapeHtml(search.algorithm)}</strong></div>
      <div class="metric"><span>Heuristic</span><strong>${escapeHtml(search.heuristic_used || "None")}</strong></div>
    </div>
    ${search.path?.length ? `<div class="route-strip">${search.path.map(escapeHtml).join(" → ")}</div>` : ""}
  </div>`;
}

function candidateTable(results) {
  if (!results.length) return '<p class="empty">No candidates selected.</p>';
  const rows = results.map((row) => `<tr>
    <td>${row.rank}</td><td>${escapeHtml(row.candidate)}</td><td>${row.reachable ? "Yes" : "No"}</td>
    <td>${formatNumber(row.pathfinding_cost)}</td><td>${formatNumber(row.search_cost)}</td>
    <td>${formatNumber(row.probability_weight, 2)}</td><td>${formatNumber(row.priority_score)}</td>
    <td>${row.nodes_expanded}</td>
  </tr>`).join("");
  return `<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Candidate</th><th>Reachable</th><th>Travel cost</th><th>Search effort</th><th>Belief</th><th>Priority</th><th>Expanded</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function missionTable(steps) {
  const rows = steps.map((step) => `<tr>
    <td>${escapeHtml(step.from_location)}</td><td>${escapeHtml(step.candidate)}</td>
    <td>${escapeHtml(step.status)}</td><td>${step.search.success ? formatNumber(step.search.path_cost) : "—"}</td>
    <td>${step.search.nodes_expanded}</td><td>${formatNumber(step.search.execution_time_ms, 3)}</td>
  </tr>`).join("");
  return `<div class="table-wrap"><table><thead><tr><th>From</th><th>Inspected location</th><th>Outcome</th><th>Route cost</th><th>Expanded</th><th>Runtime</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderCampusResults(result) {
  state.lastCampusResult = result;
  renderCampusMap(result);
  const results = $("#search-results");
  const route = result.tour.map(escapeHtml).join(" → ");
  const recovery = result.mode === "mission"
    ? `<div class="status-box${result.recovered_location ? "" : " warning"}">
        ${result.recovered_location
          ? `${escapeHtml(result.item_description)} recovered at <strong>${escapeHtml(result.recovered_location)}</strong>.`
          : `Mission ended without recovery. The selected simulation location may not be reachable.`}
      </div>`
    : "";
  results.innerHTML = `
    <div class="card result-panel">
      <h3>Candidate priority</h3>
      <p class="field-help">Priority = (movement cost + inspection effort) × (1 − stated belief).</p>
      ${candidateTable(result.candidate_results)}
      <p class="route-strip" style="margin-top:12px"><strong>Recommended tour:</strong> ${route || "No reachable candidates"}</p>
      <p class="field-help" style="margin:10px 0 0">Visit order uses a greedy nearest-neighbor approximation, not an optimal TSP solution.</p>
    </div>
    ${result.mode === "plan" ? metricsMarkup(result.selected_search, "Route to the highest-priority reachable candidate") : ""}
    ${result.mode === "mission" ? `<div class="card result-panel"><h3>Candidate inspection results</h3>${missionTable(result.mission)}${recovery}</div>` : ""}
    ${result.mode === "mission" && result.selected_search ? metricsMarkup(result.selected_search, "Final mission leg") : ""}`;
}

async function runCampusSearch(mode, button) {
  if (!checkedValues("#candidate-options").length && !checkedValues("#visited-options").length) {
    showToast("Select at least one likely or visited location.");
    return;
  }
  setBusy(button, true, "Calculating…");
  $("#search-form").classList.add("loading");
  try {
    const result = await api("/api/search/campus", searchPayload(mode));
    renderCampusResults(result);
    $("#search-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false);
    $("#search-form").classList.remove("loading");
  }
}

function renderGridBoard(result) {
  const search = result.search;
  const obstacles = new Set(result.obstacles.map(([row, col]) => `${row},${col}`));
  const path = new Set((search.path || []).map((name) => name.replace(/[()]/g, "")));
  const explored = new Set((search.explored_nodes || []).map((name) => name.replace(/[()]/g, "")));
  const start = search.start.replace(/[()]/g, "");
  const goal = search.goal.replace(/[()]/g, "");
  const cells = [];
  for (let row = 0; row < result.rows; row += 1) {
    for (let col = 0; col < result.cols; col += 1) {
      const key = `${row},${col}`;
      const classes = ["grid-cell"];
      if (obstacles.has(key)) classes.push("obstacle");
      else if (key === start) classes.push("start");
      else if (key === goal) classes.push("goal");
      else if (path.has(key)) classes.push("path");
      else if (explored.has(key)) classes.push("explored");
      cells.push(`<span class="${classes.join(" ")}" title="(${row}, ${col})"></span>`);
    }
  }
  const details = metricsMarkup(search, "Grid search result");
  $("#grid-results").innerHTML = `${details}<div class="card result-panel"><h3>Generated grid · seed ${result.seed}</h3>
    <div class="map-legend"><span><i class="legend-dot current"></i>Start</span><span><i class="legend-dot candidate"></i>Goal</span><span><i class="legend-dot recovered" style="background:#a6d2bb"></i>Path</span><span><i class="legend-dot" style="background:#77837d"></i>Obstacle</span></div>
    <div class="grid-board" style="grid-template-columns:repeat(${result.cols}, minmax(0,1fr))">${cells.join("")}</div></div>`;
}

async function runGridSearch(event) {
  event.preventDefault();
  const button = $("#grid-form button[type=submit]");
  setBusy(button, true, "Searching…");
  try {
    const result = await api("/api/search/grid", {
      rows: Number($("#grid-rows").value),
      cols: Number($("#grid-cols").value),
      density: Number($("#grid-density").value),
      seed: Number($("#grid-seed").value),
      algorithm: $("#grid-algorithm").value,
      start: $("#grid-start").value,
      goal: $("#grid-goal").value,
    });
    state.lastGridResult = result;
    renderGridBoard(result);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function comparisonTable(results) {
  const names = ["Path Cost", "Path Length", "Nodes Expanded", "Nodes Generated", "Runtime (ms)", "Heuristic"];
  const values = results.map((result) => [
    result.success ? formatNumber(result.path_cost) : "Unreachable",
    result.path_length,
    result.nodes_expanded,
    result.nodes_generated,
    formatNumber(result.execution_time_ms, 3),
    result.heuristic_used || "None",
  ]);
  return `<div class="table-wrap"><table><thead><tr><th>Metric</th>${results.map((result) => `<th>${escapeHtml(result.algorithm)}</th>`).join("")}</tr></thead>
    <tbody>${names.map((name, index) => `<tr><td>${name}</td>${values.map((column) => `<td>${escapeHtml(column[index])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

async function runComparison(event) {
  event.preventDefault();
  const button = $("#comparison-form button[type=submit]");
  setBusy(button, true, "Comparing…");
  try {
    const data = await api("/api/compare", {
      start: $("#compare-start").value,
      goal: $("#compare-goal").value,
    });
    $("#comparison-results").innerHTML = `
      <div class="card result-panel"><h3>Results on the same campus graph</h3>${comparisonTable(data.results)}</div>
      ${data.results.map((result) => metricsMarkup(result, `${result.algorithm} route`)).join("")}`;
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function drawBenchmarkChart(summary) {
  const rows = summary.filter((row) => Number.isFinite(Number(row.mean_execution_time_ms)));
  if (!rows.length) return "";
  const width = 760;
  const rowHeight = 31;
  const height = Math.max(100, rows.length * rowHeight + 25);
  const maximum = Math.max(...rows.map((row) => Number(row.mean_execution_time_ms)), 0.001);
  const colors = { BFS: "#537c68", Greedy: "#bd7b32", "A*": "#536b9b" };
  const barRows = rows.map((row, index) => {
    const y = 15 + index * rowHeight;
    const label = `${row.scenario_name} · ${row.algorithm}`;
    const barWidth = Math.max(2, 330 * Number(row.mean_execution_time_ms) / maximum);
    return `<text x="0" y="${y + 14}" fill="#45544e" font-size="12">${escapeHtml(label)}</text>
      <rect x="255" y="${y}" width="${barWidth}" height="18" rx="3" fill="${colors[row.algorithm] || "#537c68"}"></rect>
      <text x="${Math.min(590, 263 + barWidth)}" y="${y + 14}" fill="#586861" font-size="11">${formatNumber(row.mean_execution_time_ms, 3)} ms</text>`;
  }).join("");
  return `<div class="card result-panel"><h3>Mean search runtime</h3><p class="field-help">Lower is faster for these trials; timings vary between runs.</p>
    <svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Average search runtime by scenario and algorithm">${barRows}</svg></div>`;
}

function renderBenchmarkResults(data) {
  const columns = ["scenario_name", "algorithm", "total_trials", "success_rate", "mean_execution_time_ms", "mean_nodes_expanded", "mean_nodes_generated", "mean_path_cost", "mean_path_length"];
  const labels = ["Scenario", "Algorithm", "Trials", "Success rate", "Mean runtime (ms)", "Mean expanded", "Mean generated", "Mean path cost", "Mean path length"];
  const rows = data.summary.map((row) => `<tr>${columns.map((column, index) => {
    let value = row[column];
    if (column === "success_rate" && value !== null) value = `${(Number(value) * 100).toFixed(1)}%`;
    else if (column.startsWith("mean_") && value !== null) value = formatNumber(value, column.includes("time") ? 3 : 2);
    return `<td>${escapeHtml(value ?? "—")}</td>`;
  }).join("")}</tr>`).join("");
  $("#benchmark-results").innerHTML = `
    ${drawBenchmarkChart(data.summary)}
    <div class="card result-panel"><div class="card-heading"><div><h3>Summary statistics</h3><p>${data.scenarios.map(escapeHtml).join(" · ")}</p></div>
      <div class="form-actions"><button class="button secondary" id="download-benchmark">Download raw CSV</button>
      <button class="button secondary" id="download-benchmark-summary">Download summary CSV</button></div>
    </div>
    <div class="table-wrap"><table><thead><tr>${labels.map((label) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></div>`;
  $("#download-benchmark").addEventListener("click", () => {
    downloadText(data.raw_csv, "lost_item_agent_benchmark_results.csv", "text/csv");
  });
  $("#download-benchmark-summary").addEventListener("click", () => {
    downloadText(data.summary_csv, "lost_item_agent_benchmark_summary.csv", "text/csv");
  });
}

function downloadText(text, filename, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function runBenchmarks(event) {
  event.preventDefault();
  const button = $("#benchmark-form button[type=submit]");
  setBusy(button, true, "Running trials…");
  try {
    const suite = $("#benchmark-suite").value;
    const payload = { suite, trials: Number($("#benchmark-trials").value) };
    if (suite === "custom") {
      payload.rows = Number($("#benchmark-rows").value);
      payload.cols = Number($("#benchmark-cols").value);
      payload.density = Number($("#benchmark-density").value);
      payload.seed = Number($("#benchmark-seed").value);
    }
    const result = await api("/api/benchmarks", payload);
    renderBenchmarkResults(result);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function switchPage(name) {
  $$(".nav-button").forEach((button) => button.classList.toggle("active", button.dataset.page === name));
  $$(".page-section").forEach((section) => section.classList.toggle("active", section.id === `page-${name}`));
  if (name === "grid" && !state.lastGridResult) $("#grid-form").requestSubmit();
  if (name === "comparison" && !$("#comparison-results").innerHTML) $("#comparison-form").requestSubmit();
  if (name === "search") renderCampusMap();
}

function initialize(config) {
  state.config = config;
  populateSelect("#last-seen", config.locations, "Main Entrance");
  populateSelect("#current-location", config.locations, "Main Entrance");
  populateSelect("#compare-start", config.locations, "Main Entrance");
  populateSelect("#compare-goal", config.locations, "Classroom-102");
  $("#item-category").innerHTML = [
    ...Object.keys(config.item_candidates),
    "other / custom",
  ].map((item) => optionMarkup(item)).join("");
  $("#item-category").value = "laptop";
  renderChecks("#visited-options", config.locations, [], "visited");
  renderChecks("#blocked-options", config.edges.map((edge) => `${edge.source} ↔ ${edge.target}`), [], "blocked");
  $$("#blocked-options input").forEach((input, index) => { input.value = String(index); });
  candidateOptionsChanged();
  renderCampusMap();

  $$(".nav-button").forEach((button) => button.addEventListener("click", () => switchPage(button.dataset.page)));
  $("#item-category").addEventListener("change", () => {
    const custom = $("#item-category").value === "other / custom";
    $("#custom-item-wrap").classList.toggle("hidden", !custom);
    candidateOptionsChanged();
  });
  $("#candidate-options").addEventListener("change", () => {
    renderBeliefs();
    populateActualLocation();
    renderCampusMap();
  });
  $("#visited-options").addEventListener("change", () => {
    renderBeliefs();
    populateActualLocation();
    renderCampusMap();
  });
  $("#blocked-options").addEventListener("change", () => renderCampusMap());
  $("#belief-options").addEventListener("input", (event) => {
    if (event.target.matches("input[type=range]")) event.target.nextElementSibling.value = Number(event.target.value).toFixed(2);
  });
  ["#current-location", "#last-seen"].forEach((selector) => $(selector).addEventListener("change", () => renderCampusMap()));
  $("#search-algorithm").addEventListener("change", () => {
    $("#search-heuristic").disabled = $("#search-algorithm").value === "bfs";
  });
  $("#plan-button").addEventListener("click", (event) => runCampusSearch("plan", event.currentTarget));
  $("#mission-button").addEventListener("click", (event) => runCampusSearch("mission", event.currentTarget));
  $("#grid-form").addEventListener("submit", runGridSearch);
  $("#comparison-form").addEventListener("submit", runComparison);
  $("#benchmark-form").addEventListener("submit", runBenchmarks);
  $("#benchmark-suite").addEventListener("change", () => $("#custom-benchmark-fields").classList.toggle("hidden", $("#benchmark-suite").value !== "custom"));
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error("Could not load the campus configuration.");
    initialize(await response.json());
  } catch (error) {
    showToast(error.message);
  }
});
