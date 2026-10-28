"use strict";

const state = {
  config: null,
  lastCampusResult: null,
  lastGridResult: null,
  activeMissionStepIndex: 0,
  missionTimer: null,
  gridSelection: "start",
  activeBenchmarkMetric: "time",
  grid: {
    rows: 10,
    cols: 10,
    density: 0.2,
    seed: 42,
    start: [0, 0],
    goal: [9, 9],
    obstacles: [],
  },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function showToast(message, type = "info") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast visible ${type}`;
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove("visible"), 4000);
}

function showLoading(text = "Calculating...") {
  const overlay = $("#loading-overlay");
  const textEl = $("#loading-text");
  if (textEl) textEl.textContent = text;
  if (overlay) overlay.classList.add("active");
}

function hideLoading() {
  const overlay = $("#loading-overlay");
  if (overlay) overlay.classList.remove("active");
}

async function api(path, payload, method = "POST") {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (payload && method !== "GET") {
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(path, options);
  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function setBusy(element, busy, label) {
  if (!element) return;
  if (!element.dataset.label) element.dataset.label = element.textContent;
  element.disabled = busy;
  element.textContent = busy ? label : element.dataset.label;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function algorithmName(value) {
  return ({
    "A*": "Balanced route (A*)",
    BFS: "Fewest steps (BFS)",
    Greedy: "Greedy Best-First Search",
    astar: "Balanced route (A*)",
    bfs: "Fewest steps (BFS)",
    greedy: "Greedy Best-First Search",
  })[value] || value || "Unknown";
}

function algorithmShortName(value) {
  return ({ "A*": "A* Search", BFS: "BFS", Greedy: "Greedy BFS" })[value] || value;
}

function heuristicName(value) {
  if (!value || value.toLowerCase() === "none") return "No estimate (Dijkstra baseline)";
  if (value.toLowerCase().includes("euclidean")) return "Euclidean straight-line estimate";
  if (value.toLowerCase().includes("manhattan")) return "Manhattan grid distance estimate";
  return value;
}

function optionMarkup(value, label = value) {
  return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
}

function populateSelect(selector, values, selected) {
  const select = $(selector);
  if (!select) return;
  select.innerHTML = values.map((value) => optionMarkup(value)).join("");
  if (selected && values.includes(selected)) {
    select.value = selected;
  }
}

function checkedValues(container) {
  return $$(`${container} input:checked`).map((input) => input.value);
}

function renderChecks(container, values, checked = [], prefix = "option") {
  const el = $(container);
  if (!el) return;
  const selected = new Set(checked);
  el.innerHTML = values.map((value, index) => `
    <label class="check-option">
      <input type="checkbox" value="${escapeHtml(value)}" id="${prefix}-${index}" ${selected.has(value) ? "checked" : ""}>
      <span>${escapeHtml(value)}</span>
    </label>`).join("");
}

/* --------------------------------------------------------------------------
   Theme Handling
--------------------------------------------------------------------------- */
function initTheme() {
  const saved = localStorage.getItem("lost_item_agent_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);

  $("#theme-toggle")?.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("lost_item_agent_theme", next);
    updateThemeIcon(next);
    renderCampusMap();
  });
}

function updateThemeIcon(theme) {
  const icon = $("#theme-icon");
  const text = $("#theme-text");
  if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
  if (text) text.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
}

/* --------------------------------------------------------------------------
   Campus Map SVG Renderer
--------------------------------------------------------------------------- */
function renderCampusMap(result = state.lastCampusResult, containerId = "#campus-map", highlightLeg = null) {
  const container = $(containerId);
  if (!container || !state.config) return;

  const config = state.config;
  const nodes = config.nodes || [];
  const edges = config.edges || [];

  const startName = $("#current-location")?.value || "Main Entrance";
  const lastSeenName = $("#last-seen")?.value || "Library";
  const candidates = new Set(result?.candidate_results?.map((item) => item.candidate) || checkedValues("#candidate-options"));
  const blockedEdges = new Set((result?.blocked_edges || checkedValues("#blocked-options").map((idx) => {
    const e = config.edges[Number(idx)];
    return e ? [e.source, e.target] : null;
  }).filter(Boolean)).map(([s, t]) => `${s}---${t}`));

  // Highlighted path
  const path = highlightLeg || result?.path || [];
  const activeLegSet = new Set();
  for (let i = 0; i < path.length - 1; i++) {
    activeLegSet.add(`${path[i]}---${path[i + 1]}`);
    activeLegSet.add(`${path[i + 1]}---${path[i]}`);
  }

  // Calculate coordinates
  const minX = Math.min(...nodes.map(n => n.x), 0);
  const maxX = Math.max(...nodes.map(n => n.x), 8);
  const minY = Math.min(...nodes.map(n => n.y), 0);
  const maxY = Math.max(...nodes.map(n => n.y), 9);

  const paddingX = 40;
  const paddingY = 40;
  const svgWidth = 720;
  const svgHeight = 460;

  const scaleX = (svgWidth - paddingX * 2) / Math.max(maxX - minX, 1);
  const scaleY = (svgHeight - paddingY * 2) / Math.max(maxY - minY, 1);

  const getSvgPos = (nodeName) => {
    const n = nodes.find(item => item.name === nodeName);
    if (!n) return { x: svgWidth / 2, y: svgHeight / 2 };
    return {
      x: paddingX + (n.x - minX) * scaleX,
      y: svgHeight - (paddingY + (n.y - minY) * scaleY),
    };
  };

  // Build Edge Lines
  const edgeSvgElements = edges.map((e) => {
    const p1 = getSvgPos(e.source);
    const p2 = getSvgPos(e.target);
    const isBlocked = blockedEdges.has(`${e.source}---${e.target}`) || blockedEdges.has(`${e.target}---${e.source}`);
    const isRoute = activeLegSet.has(`${e.source}---${e.target}`) || activeLegSet.has(`${e.target}---${e.source}`);

    let stroke = "rgba(148, 163, 184, 0.4)";
    let strokeWidth = 2.5;
    let strokeDash = "";

    if (isBlocked) {
      stroke = "#ef4444";
      strokeWidth = 3;
      strokeDash = "5,4";
    } else if (isRoute) {
      stroke = "#10b981";
      strokeWidth = 5;
    }

    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;

    return `
      <g class="campus-edge">
        <line x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}"
          stroke="${stroke}" stroke-width="${strokeWidth}" stroke-dasharray="${strokeDash}" stroke-linecap="round" />
        ${isBlocked ? `<circle cx="${midX}" cy="${midY}" r="7" fill="#ef4444" stroke="#fff" stroke-width="1.5"/>
          <text x="${midX}" y="${midY + 3.5}" text-anchor="middle" font-size="9" fill="#fff" font-weight="bold">✕</text>` : ""}
      </g>
    `;
  }).join("");

  // Build Node Circles
  const nodeSvgElements = nodes.map((n) => {
    const pos = getSvgPos(n.name);
    const isStart = n.name === startName;
    const isLastSeen = n.name === lastSeenName;
    const isCandidate = candidates.has(n.name);
    const isRecovered = result?.recovered_location === n.name;

    let fill = "#ffffff";
    let stroke = "#94a3b8";
    let radius = 10;
    let ring = "";

    if (isRecovered) {
      fill = "#10b981";
      stroke = "#059669";
      radius = 14;
      ring = `<circle cx="${pos.x}" cy="${pos.y}" r="20" fill="rgba(16, 185, 129, 0.25)" class="pulse-ring" />`;
    } else if (isStart && isLastSeen) {
      fill = "#0284c7";
      stroke = "#7c3aed";
      radius = 13;
      ring = `<circle cx="${pos.x}" cy="${pos.y}" r="18" fill="none" stroke="#7c3aed" stroke-width="2.5" stroke-dasharray="3,3" />`;
    } else if (isStart) {
      fill = "#0284c7";
      stroke = "#0369a1";
      radius = 13;
      ring = `<circle cx="${pos.x}" cy="${pos.y}" r="18" fill="rgba(2, 132, 199, 0.2)" />`;
    } else if (isLastSeen) {
      fill = "#7c3aed";
      stroke = "#6d28d9";
      radius = 13;
      ring = `<circle cx="${pos.x}" cy="${pos.y}" r="18" fill="rgba(124, 58, 237, 0.2)" />`;
    } else if (isCandidate) {
      fill = "#f59e0b";
      stroke = "#d97706";
      radius = 11;
    }

    return `
      <g class="campus-node" data-name="${escapeHtml(n.name)}" tabindex="0" role="button">
        ${ring}
        <circle cx="${pos.x}" cy="${pos.y}" r="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="2.5" />
        <text x="${pos.x}" y="${pos.y + 19}" text-anchor="middle" font-family="'Plus Jakarta Sans', sans-serif"
          font-size="11" font-weight="600" fill="currentColor" class="node-label">${escapeHtml(n.name)}</text>
        <title>${escapeHtml(n.name)} (${escapeHtml(n.floor || n.type)} · Search Effort: ${n.search_cost})</title>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${svgWidth} ${svgHeight}" style="width:100%; height:100%; display:block;" role="img" aria-label="Campus graph layout">
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <!-- Floor dividing guideline -->
      <line x1="20" y1="${svgHeight / 2 - 15}" x2="${svgWidth - 20}" y2="${svgHeight / 2 - 15}"
        stroke="rgba(148, 163, 184, 0.25)" stroke-width="1" stroke-dasharray="6,4" />
      <text x="28" y="${svgHeight / 2 - 22}" font-size="11" fill="var(--text-muted)" font-weight="600">FIRST FLOOR (UPSTAIRS)</text>
      <text x="28" y="${svgHeight / 2 - 4}" font-size="11" fill="var(--text-muted)" font-weight="600">GROUND FLOOR (ENTRY)</text>
      ${edgeSvgElements}
      ${nodeSvgElements}
    </svg>
  `;
}

/* --------------------------------------------------------------------------
   Search & Payload Preparation
--------------------------------------------------------------------------- */
function probabilities() {
  return Object.fromEntries(
    $$("#belief-options input").map((input) => [input.dataset.candidate, Number(input.value)])
  );
}

function searchPayload(mode) {
  const category = $("#item-category")?.value || "laptop";
  const description = category === "other / custom" ? ($("#custom-item")?.value.trim() || "custom item") : category;
  const candidates = checkedValues("#candidate-options");
  const visited = checkedValues("#visited-options");
  const lastSeen = $("#last-seen")?.value;
  const start = $("#current-location")?.value;

  const blocked = checkedValues("#blocked-options").map((val) => {
    const edge = state.config.edges[Number(val)];
    return edge ? [edge.source, edge.target] : null;
  }).filter(Boolean);

  return {
    mode,
    item_description: description,
    start,
    last_seen: lastSeen,
    candidates,
    visited,
    probabilities: probabilities(),
    algorithm: $("#search-algorithm")?.value || "astar",
    heuristic: $("#search-heuristic")?.value || "euclidean",
    actual_location: $("#actual-location")?.value,
    blocked_edges: blocked,
  };
}

/* --------------------------------------------------------------------------
   Results Visualizations: KPIs, Candidate Cards & Stepper
--------------------------------------------------------------------------- */
function renderKpiCards(search, heading = "Route Execution Metrics") {
  if (!search) return "";
  const cost = search.success ? formatNumber(search.path_cost) : "Unreachable";
  const algo = algorithmName(search.algorithm);
  const time = formatNumber(search.execution_time_ms, 3);
  const hops = search.path_length;
  const expanded = search.nodes_expanded;
  const generated = search.nodes_generated;

  return `
    <div class="card result-panel">
      <div class="card-heading">
        <div>
          <h3>${escapeHtml(heading)}</h3>
          <p>${escapeHtml(algo)} · ${escapeHtml(heuristicName(search.heuristic_used))}</p>
        </div>
        <span class="badge ${search.success ? "emerald" : "rose"}">
          ${search.success ? "✓ Route Found" : "✕ Unreachable Destination"}
        </span>
      </div>

      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-title">Travel Cost</span>
            <span class="metric-icon">📏</span>
          </div>
          <div class="metric-value">${cost}</div>
          <span class="metric-subtitle">Sum of edge walking weights</span>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-title">Execution Time</span>
            <span class="metric-icon">⚡</span>
          </div>
          <div class="metric-value">${time} <span style="font-size:14px; font-weight:normal;">ms</span></div>
          <span class="metric-subtitle">Algorithm wall-clock compute</span>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-title">Nodes Expanded</span>
            <span class="metric-icon">🔍</span>
          </div>
          <div class="metric-value">${expanded}</div>
          <span class="metric-subtitle">States popped from frontier</span>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-title">Nodes Generated</span>
            <span class="metric-icon">📦</span>
          </div>
          <div class="metric-value">${generated}</div>
          <span class="metric-subtitle">Frontier enqueued states</span>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-title">Route Hops</span>
            <span class="metric-icon">🚶</span>
          </div>
          <div class="metric-value">${hops}</div>
          <span class="metric-subtitle">Corridor segments traversed</span>
        </div>
      </div>

      ${search.path?.length ? `
        <div style="margin-top: 14px;">
          <strong style="display:block; margin-bottom: 6px; font-size:12.5px; color:var(--text-secondary);">Optimal Corridor Path:</strong>
          <div class="route-strip">
            ${search.path.map((node, i) => `
              <span class="route-hop">${escapeHtml(node)}</span>
              ${i < search.path.length - 1 ? '<span class="route-arrow">→</span>' : ''}
            `).join("")}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

function renderCandidateCards(candidates) {
  if (!candidates || !candidates.length) {
    return '<p class="field-help">No candidates selected.</p>';
  }

  const maxScore = Math.max(...candidates.filter(c => c.reachable).map(c => c.priority_score), 10);

  const cards = candidates.map((c) => {
    const isTop = c.rank === 1 && c.reachable;
    const pct = c.reachable ? Math.max(10, Math.min(100, 100 - (c.priority_score / maxScore) * 85)) : 0;
    const beliefPct = Math.round(Number(c.probability_weight) * 100);

    return `
      <div class="candidate-card ${isTop ? "top-priority" : ""} ${c.is_last_seen ? "is-last-seen" : ""} ${!c.reachable ? "unreachable" : ""}">
        <div class="candidate-top">
          <span class="candidate-rank-badge ${c.rank === 1 ? "rank-1" : "rank-other"}">
            ${c.rank === 1 ? "★ Top Recommendation" : `Rank #${c.rank}`}
          </span>
          <div class="candidate-badges">
            ${c.is_last_seen ? '<span class="badge purple">📍 Last Seen</span>' : ''}
            <span class="badge ${c.reachable ? "emerald" : "rose"}">
              ${c.reachable ? "Reachable" : "Blocked"}
            </span>
          </div>
        </div>

        <h4 class="candidate-name">${escapeHtml(c.candidate)}</h4>

        <div class="candidate-meter-wrap">
          <div class="candidate-meter-label">
            <span>Priority Index</span>
            <strong>${c.reachable ? formatNumber(c.priority_score) : "∞"}</strong>
          </div>
          <div class="candidate-meter-bar">
            <div class="candidate-meter-fill" style="width: ${pct}%;"></div>
          </div>
        </div>

        <div class="candidate-breakdown">
          <div class="candidate-breakdown-item">
            <span>Travel</span>
            <strong>${formatNumber(c.pathfinding_cost)}</strong>
          </div>
          <div class="candidate-breakdown-item">
            <span>Search</span>
            <strong>${formatNumber(c.search_cost)}</strong>
          </div>
          <div class="candidate-breakdown-item">
            <span>Belief</span>
            <strong>${beliefPct}%</strong>
          </div>
        </div>

        <div class="candidate-formula">
          score = (${formatNumber(c.pathfinding_cost)} + ${formatNumber(c.search_cost)}) × (1 − ${formatNumber(c.probability_weight)}) = ${formatNumber(c.priority_score)}
        </div>

        <button class="button secondary" style="width:100%; padding: 6px;" type="button"
          onclick="highlightCandidateRoute('${escapeHtml(c.candidate)}')">
          Highlight Path
        </button>
      </div>
    `;
  }).join("");

  return `
    <div class="card result-panel">
      <div class="card-heading">
        <div>
          <h3>Ranked Candidate Locations</h3>
          <p>Scored by (Travel Cost + Inspection Effort) × (1 − Prior Belief). Lower score = search sooner.</p>
        </div>
      </div>
      <div class="candidates-grid">${cards}</div>
    </div>
  `;
}

window.highlightCandidateRoute = function(candidateName) {
  const result = state.lastCampusResult;
  if (!result) return;
  const candidateResult = result.candidate_results?.find(c => c.candidate === candidateName);
  if (candidateResult && candidateResult.path) {
    renderCampusMap(result, "#campus-map", candidateResult.path);
    showToast(`Highlighting route to ${candidateName}`, "info");
  }
};

/* --------------------------------------------------------------------------
   Step-by-Step Interactive Recovery Player
--------------------------------------------------------------------------- */
function renderRecoveryStepper(steps, recoveredLocation, itemDescription) {
  if (!steps || !steps.length) return "";

  const cardsHtml = steps.map((s, idx) => {
    const isCurrent = idx === state.activeMissionStepIndex;
    return `
      <div class="mission-step-card ${isCurrent ? "active-step" : ""} ${s.found ? "found-step" : ""}"
        id="step-card-${idx}">
        <div class="step-card-header">
          <span class="step-number">Step ${idx + 1} of ${steps.length}</span>
          <span class="step-outcome ${s.found ? "badge emerald" : s.search.success ? "badge slate" : "badge rose"}">
            ${s.found ? "🎉 Found!" : s.search.success ? "Not here" : "Unreachable"}
          </span>
        </div>
        <strong style="display:block; font-size:15px; margin-bottom:4px; color:var(--text-primary);">
          ${escapeHtml(s.from_location)} → ${escapeHtml(s.candidate)}
        </strong>
        <span style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:8px;">
          Travel Cost: ${formatNumber(s.search.path_cost)} · Expanded: ${s.search.nodes_expanded} nodes
        </span>
        <button class="button secondary" style="width:100%; padding:4px 8px; font-size:12px;" type="button"
          onclick="jumpToMissionStep(${idx})">
          View Step on Map
        </button>
      </div>
    `;
  }).join("");

  const activeStep = steps[state.activeMissionStepIndex];
  const progressPct = ((state.activeMissionStepIndex + 1) / steps.length) * 100;

  return `
    <div class="mission-stepper-wrap">
      <div class="stepper-header">
        <div>
          <h3 style="margin:0 0 4px;">Simulated Step-by-Step Recovery Player</h3>
          <p style="margin:0; font-size:12.5px; color:var(--text-muted);">
            The agent travels to each room in prioritized order, inspects it, and replans upon a negative finding.
          </p>
        </div>
        <div class="stepper-controls">
          <button class="button secondary" type="button" onclick="stepMission(-1)" ${state.activeMissionStepIndex === 0 ? "disabled" : ""}>◀ Prev</button>
          <button class="button primary" id="auto-play-btn" type="button" onclick="toggleAutoPlayMission()">▶ Auto Play</button>
          <button class="button secondary" type="button" onclick="stepMission(1)" ${state.activeMissionStepIndex >= steps.length - 1 ? "disabled" : ""}>Next ▶</button>
        </div>
      </div>

      <div class="stepper-progress-bar">
        <div class="stepper-progress-fill" style="width: ${progressPct}%;"></div>
      </div>

      <div class="stepper-cards-track">${cardsHtml}</div>

      <div style="margin-top: 16px; padding: 12px 16px; border-radius: var(--radius-sm); background: ${recoveredLocation ? "var(--accent-recovered-light)" : "var(--accent-candidate-light)"}; color: ${recoveredLocation ? "var(--accent-recovered)" : "var(--accent-candidate)"};">
        <strong>${recoveredLocation ? "🎉 Mission Success:" : "⚠️ Mission Notice:"}</strong>
        ${recoveredLocation
          ? `${escapeHtml(itemDescription)} successfully located at <strong>${escapeHtml(recoveredLocation)}</strong> in step ${steps.length}!`
          : "Mission completed without recovery. The target item was not at any reached candidates."}
      </div>
    </div>
  `;
}

window.jumpToMissionStep = function(index) {
  const result = state.lastCampusResult;
  if (!result || !result.mission || !result.mission[index]) return;
  state.activeMissionStepIndex = index;
  const step = result.mission[index];
  renderCampusMap(result, "#campus-map", step.search.path);
  renderCampusResults(result);
};

window.stepMission = function(delta) {
  const result = state.lastCampusResult;
  if (!result || !result.mission) return;
  const nextIdx = state.activeMissionStepIndex + delta;
  if (nextIdx >= 0 && nextIdx < result.mission.length) {
    jumpToMissionStep(nextIdx);
  }
};

window.toggleAutoPlayMission = function() {
  const btn = $("#auto-play-btn");
  if (state.missionTimer) {
    clearInterval(state.missionTimer);
    state.missionTimer = null;
    if (btn) btn.textContent = "▶ Auto Play";
  } else {
    if (btn) btn.textContent = "⏸ Pause";
    state.missionTimer = setInterval(() => {
      const result = state.lastCampusResult;
      if (!result || !result.mission) {
        clearInterval(state.missionTimer);
        state.missionTimer = null;
        return;
      }
      if (state.activeMissionStepIndex < result.mission.length - 1) {
        stepMission(1);
      } else {
        clearInterval(state.missionTimer);
        state.missionTimer = null;
        if (btn) btn.textContent = "▶ Auto Play";
      }
    }, 1500);
  }
};

function renderCampusResults(result) {
  state.lastCampusResult = result;
  renderCampusMap(result);
  const container = $("#search-results");
  if (!container) return;

  const tourRoute = result.tour ? result.tour.map(escapeHtml).join(" → ") : "";

  container.innerHTML = `
    ${renderKpiCards(result.selected_search, result.mode === "mission" ? "Active Mission Leg Route Metrics" : "Route to Top-Priority Candidate")}
    ${renderCandidateCards(result.candidate_results)}
    <div class="card result-panel">
      <h3>Recommended Multi-Candidate Visit Order</h3>
      <p class="field-help">Computed via Greedy Nearest-Neighbor approximation over reachable candidates.</p>
      <div class="route-strip" style="margin-top: 10px;">
        ${tourRoute || "No reachable candidate sequence"}
      </div>
    </div>
    ${result.mode === "mission" ? renderRecoveryStepper(result.mission, result.recovered_location, result.item_description) : ""}
  `;
}

async function runCampusSearch(mode, button) {
  const candidates = checkedValues("#candidate-options");
  const visited = checkedValues("#visited-options");
  if (!candidates.length && !visited.length) {
    showToast("Please select at least one candidate location to inspect.", "warning");
    return;
  }

  state.activeMissionStepIndex = 0;
  setBusy(button, true, "Planning route...");
  showLoading(mode === "mission" ? "Simulating recovery mission..." : "Calculating priority plan...");

  try {
    const payload = searchPayload(mode);
    const result = await api("/api/search/campus", payload);
    renderCampusResults(result);
    $("#search-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast(mode === "mission" ? "Recovery mission simulation complete." : "Candidate plan generated.", "success");
    loadHistory();
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    setBusy(button, false);
    hideLoading();
  }
}

/* --------------------------------------------------------------------------
   Practice Grid Map
--------------------------------------------------------------------------- */
function gridPositionName([r, c]) {
  return `(${r},${c})`;
}

function renderGridBoard() {
  const { rows, cols, start, goal, obstacles } = state.grid;
  const obstacleSet = new Set(obstacles.map(([r, c]) => `${r},${c}`));
  const search = state.lastGridResult?.search;
  const matches = search && search.start === gridPositionName(start) && search.goal === gridPositionName(goal);
  const path = new Set(matches ? (search.path || []).map(n => n.replace(/[()]/g, "")) : []);
  const explored = new Set(matches ? (search.explored_nodes || []).map(n => n.replace(/[()]/g, "")) : []);
  const startKey = start.join(",");
  const goalKey = goal.join(",");

  const cells = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const key = `${r},${c}`;
      const classes = ["grid-cell"];
      const isObs = obstacleSet.has(key);
      if (isObs) classes.push("obstacle");
      else if (key === startKey) classes.push("start");
      else if (key === goalKey) classes.push("goal");
      else if (path.has(key)) classes.push("path");
      else if (explored.has(key)) classes.push("explored");

      cells.push(`
        <button class="${classes.join(" ")}" type="button" data-row="${r}" data-col="${c}"
          aria-label="Row ${r+1}, Col ${c+1}" ${isObs ? "disabled" : ""}></button>
      `);
    }
  }

  const mapEl = $("#grid-map");
  if (mapEl) {
    mapEl.innerHTML = `
      <div class="card-heading">
        <div>
          <h3>Practice Map (${rows} × ${cols})</h3>
          <p>Click open cells to position Start (Blue) and Goal (Amber).</p>
        </div>
      </div>
      <div class="map-legend">
        <span><i class="legend-dot current"></i> Start Point</span>
        <span><i class="legend-dot candidate"></i> Destination</span>
        <span><i class="legend-dot recovered" style="background:#86efac"></i> Path</span>
        <span><i class="legend-dot" style="background:#475569"></i> Obstacle</span>
      </div>
      <div class="grid-board" style="grid-template-columns: repeat(${cols}, minmax(0, 1fr));">
        ${cells.join("")}
      </div>
    `;
  }

  const resultsEl = $("#grid-results");
  if (resultsEl) {
    resultsEl.innerHTML = matches ? renderKpiCards(search, "Grid Search Results") : "";
  }
}

function selectGridPoint(e) {
  const cell = e.target.closest(".grid-cell");
  if (!cell || cell.disabled || !state.gridSelection) return;
  const point = [Number(cell.dataset.row), Number(cell.dataset.col)];

  if (state.gridSelection === "start") {
    if (point.join(",") === state.grid.goal.join(",")) {
      showToast("Start position cannot equal destination.", "warning");
      return;
    }
    state.grid.start = point;
    state.gridSelection = "goal";
  } else {
    if (point.join(",") === state.grid.start.join(",")) {
      showToast("Destination cannot equal start position.", "warning");
      return;
    }
    state.grid.goal = point;
    state.gridSelection = null;
  }
  state.lastGridResult = null;
  updateGridSelectionHelp();
  renderGridBoard();
}

function updateGridSelectionHelp() {
  const text = state.gridSelection === "start"
    ? "Click a clear cell to set the Starting Point."
    : state.gridSelection === "goal"
      ? "Now click another clear cell to set the Destination."
      : "Endpoints configured. Click 'Find Route' to solve.";
  const helpEl = $("#grid-selection-help");
  if (helpEl) helpEl.textContent = text;

  $$(".point-button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.point === state.gridSelection);
  });
}

function resetGridMap(randomize = true) {
  const size = Number($("#grid-size")?.value || 10);
  state.grid.rows = size;
  state.grid.cols = size;
  state.grid.density = Number($("#grid-obstacles")?.value || 0.2);
  if (randomize) state.grid.seed = Math.floor(Math.random() * 2 ** 31);
  state.grid.start = [0, 0];
  state.grid.goal = [size - 1, size - 1];
  state.grid.obstacles = [];
  state.lastGridResult = null;
  state.gridSelection = "start";
  updateGridSelectionHelp();
  renderGridBoard();
}

async function runGridSearch(e) {
  e?.preventDefault();
  const btn = $("#grid-form button[type=submit]");
  setBusy(btn, true, "Searching...");
  showLoading("Solving grid pathfinding...");

  try {
    const payload = {
      rows: state.grid.rows,
      cols: state.grid.cols,
      density: state.grid.density,
      seed: state.grid.seed,
      algorithm: $("#grid-algorithm")?.value || "astar",
      start: gridPositionName(state.grid.start),
      goal: gridPositionName(state.grid.goal),
    };
    const result = await api("/api/search/grid", payload);
    state.grid.obstacles = result.obstacles;
    state.lastGridResult = result;
    renderGridBoard();
    showToast("Grid pathfinding completed.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    setBusy(btn, false);
    hideLoading();
  }
}

/* --------------------------------------------------------------------------
   Comparison Section
--------------------------------------------------------------------------- */
function comparisonTable(results) {
  const names = [
    "Path Travel Cost",
    "Route Hops (Length)",
    "Nodes Expanded",
    "Nodes Generated",
    "Execution Time (ms)",
    "Heuristic Function",
    "Cost Optimality Guarantee",
  ];

  const values = results.map((r) => [
    r.success ? formatNumber(r.path_cost) : "Unreachable",
    r.path_length,
    r.nodes_expanded,
    r.nodes_generated,
    formatNumber(r.execution_time_ms, 3),
    heuristicName(r.heuristic_used),
    r.algorithm === "A*" ? "Guaranteed Optimal" : r.algorithm === "BFS" ? "Fewest Edges (Uninformed)" : "Suboptimal (Greedy)",
  ]);

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            ${results.map(r => `<th>${escapeHtml(algorithmName(r.algorithm))}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${names.map((name, i) => `
            <tr>
              <td><strong>${name}</strong></td>
              ${values.map(col => `<td>${escapeHtml(col[i])}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function runComparison(e) {
  e?.preventDefault();
  const btn = $("#comparison-form button[type=submit]");
  setBusy(btn, true, "Running Comparison...");
  showLoading("Benchmarking BFS, Greedy, and A*...");

  try {
    const data = await api("/api/compare", {
      start: $("#compare-start").value,
      goal: $("#compare-goal").value,
    });
    const resultsEl = $("#comparison-results");
    if (resultsEl) {
      resultsEl.innerHTML = `
        <div class="card result-panel">
          <h3>Algorithm Comparison Results</h3>
          <p class="field-help">Evaluated on identical start and goal endpoints on the campus graph.</p>
          ${comparisonTable(data.results)}
        </div>
        ${data.results.map(r => renderKpiCards(r, `${algorithmName(r.algorithm)} Route Details`)).join("")}
      `;
    }
    showToast("Route finders compared.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    setBusy(btn, false);
    hideLoading();
  }
}

/* --------------------------------------------------------------------------
   Benchmarks & Multi-Metric Charts
--------------------------------------------------------------------------- */
function drawBenchmarkSvgChart(summary, metricKey = "mean_execution_time_ms") {
  const rows = summary.filter(r => Number.isFinite(Number(r[metricKey])));
  if (!rows.length) return "";

  const width = 760;
  const rowHeight = 32;
  const height = Math.max(120, rows.length * rowHeight + 30);
  const maxVal = Math.max(...rows.map(r => Number(r[metricKey])), 0.001);
  const colors = { BFS: "#3b82f6", Greedy: "#f59e0b", "A*": "#10b981" };

  const barRows = rows.map((r, i) => {
    const y = 20 + i * rowHeight;
    const label = `${r.scenario_name} · ${algorithmShortName(r.algorithm)}`;
    const barWidth = Math.max(3, (380 * Number(r[metricKey])) / maxVal);
    const displayVal = metricKey.includes("time") ? `${formatNumber(r[metricKey], 3)} ms` : formatNumber(r[metricKey], 1);

    return `
      <text x="0" y="${y + 14}" fill="var(--text-secondary)" font-size="12" font-family="'Plus Jakarta Sans', sans-serif">${escapeHtml(label)}</text>
      <rect x="260" y="${y}" width="${barWidth}" height="18" rx="4" fill="${colors[r.algorithm] || "#10b981"}"></rect>
      <text x="${Math.min(670, 268 + barWidth)}" y="${y + 14}" fill="var(--text-primary)" font-size="11.5" font-family="'JetBrains Mono', monospace">${displayVal}</text>
    `;
  }).join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" style="width:100%; height:auto;" role="img">
      ${barRows}
    </svg>
  `;
}

function renderBenchmarkResults(data) {
  const container = $("#benchmark-results");
  if (!container) return;

  const summary = data.summary || [];
  const metricLabels = {
    time: "Execution Time (ms)",
    nodes: "Nodes Expanded (Search Effort)",
    cost: "Path Travel Cost (Optimality)",
  };
  const metricKeys = {
    time: "mean_execution_time_ms",
    nodes: "mean_nodes_expanded",
    cost: "mean_path_cost",
  };

  const chartHtml = `
    <div class="card result-panel">
      <div class="card-heading">
        <div>
          <h3>Benchmark Metric Comparison Chart</h3>
          <p>Switch metric views below to compare runtime, search effort, or path optimality.</p>
        </div>
      </div>
      <div class="chart-tabs">
        <button class="tab-btn ${state.activeBenchmarkMetric === "time" ? "active" : ""}" type="button" onclick="switchBenchmarkMetric('time')">⚡ Execution Time</button>
        <button class="tab-btn ${state.activeBenchmarkMetric === "nodes" ? "active" : ""}" type="button" onclick="switchBenchmarkMetric('nodes')">🔍 Nodes Expanded</button>
        <button class="tab-btn ${state.activeBenchmarkMetric === "cost" ? "active" : ""}" type="button" onclick="switchBenchmarkMetric('cost')">📏 Path Cost</button>
      </div>
      <div id="benchmark-chart-container">
        ${drawBenchmarkSvgChart(summary, metricKeys[state.activeBenchmarkMetric])}
      </div>
    </div>
  `;

  // Summary Table
  const tableRows = summary.map((r) => `
    <tr>
      <td><strong>${escapeHtml(r.scenario_name)}</strong></td>
      <td>${escapeHtml(algorithmName(r.algorithm))}</td>
      <td>${r.total_trials}</td>
      <td>${r.success_rate !== null ? `${(r.success_rate * 100).toFixed(0)}%` : "—"}</td>
      <td>${formatNumber(r.mean_execution_time_ms, 3)}</td>
      <td>${formatNumber(r.mean_nodes_expanded, 1)}</td>
      <td>${formatNumber(r.mean_nodes_generated, 1)}</td>
      <td>${formatNumber(r.mean_path_cost, 2)}</td>
    </tr>
  `).join("");

  const tableHtml = `
    <div class="card result-panel">
      <div class="card-heading">
        <div>
          <h3>Experimental Benchmark Data</h3>
          <p>Scenarios evaluated: ${data.scenarios.map(escapeHtml).join(" · ")}</p>
        </div>
        <div class="form-actions" style="margin-top:0;">
          <button class="button secondary" id="dl-raw-csv" type="button">Download Raw CSV</button>
          <button class="button secondary" id="dl-summary-csv" type="button">Download Summary CSV</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Scenario</th><th>Algorithm</th><th>Trials</th><th>Success</th>
              <th>Avg Time (ms)</th><th>Avg Expanded</th><th>Avg Generated</th><th>Avg Cost</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;

  // Charts gallery
  const galleryHtml = `
    <div class="card result-panel">
      <div class="card-heading">
        <div>
          <h3>Generated High-Resolution Submission Charts</h3>
          <p>Rendered with Matplotlib and saved to output/submission_evidence/</p>
        </div>
      </div>
      <div class="chart-gallery">
        <div class="chart-thumbnail">
          <img src="/output/submission_evidence/chart_execution_time.png?t=${Date.now()}" alt="Execution time comparison chart" onerror="this.parentElement.style.display='none'">
          <div class="chart-thumbnail-caption">Execution Time Comparison</div>
        </div>
        <div class="chart-thumbnail">
          <img src="/output/submission_evidence/chart_expanded_nodes.png?t=${Date.now()}" alt="Nodes expanded comparison chart" onerror="this.parentElement.style.display='none'">
          <div class="chart-thumbnail-caption">Nodes Expanded (Search Space Exploration)</div>
        </div>
        <div class="chart-thumbnail">
          <img src="/output/submission_evidence/chart_path_cost.png?t=${Date.now()}" alt="Path cost comparison chart" onerror="this.parentElement.style.display='none'">
          <div class="chart-thumbnail-caption">Path Travel Cost (Optimality)</div>
        </div>
        <div class="chart-thumbnail">
          <img src="/output/submission_evidence/chart_scaling.png?t=${Date.now()}" alt="Grid scaling comparison chart" onerror="this.parentElement.style.display='none'">
          <div class="chart-thumbnail-caption">Scaling vs Grid Size</div>
        </div>
      </div>
    </div>
  `;

  container.innerHTML = `${chartHtml}${tableHtml}${galleryHtml}`;

  $("#dl-raw-csv")?.addEventListener("click", () => {
    downloadText(data.raw_csv, "lost_item_agent_benchmark_raw.csv", "text/csv");
  });
  $("#dl-summary-csv")?.addEventListener("click", () => {
    downloadText(data.summary_csv, "lost_item_agent_benchmark_summary.csv", "text/csv");
  });
}

window.switchBenchmarkMetric = function(metric) {
  state.activeBenchmarkMetric = metric;
  const result = state.lastBenchmarkData;
  if (result) renderBenchmarkResults(result);
};

function downloadText(text, filename, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function runBenchmarks(e) {
  e?.preventDefault();
  const btn = $("#benchmark-form button[type=submit]");
  setBusy(btn, true, "Running Benchmark Suite...");
  showLoading("Executing multi-scenario benchmark trials...");

  try {
    const suite = $("#benchmark-suite")?.value || "fast";
    const payload = {
      suite,
      trials: Number($("#benchmark-trials")?.value || 3),
    };
    if (suite === "custom") {
      const size = Number($("#benchmark-size")?.value || 10);
      payload.rows = size;
      payload.cols = size;
      payload.density = Number($("#benchmark-obstacles")?.value || 0.2);
      payload.seed = Math.floor(Math.random() * 2 ** 31);
    }
    const data = await api("/api/benchmarks", payload);
    state.lastBenchmarkData = data;
    renderBenchmarkResults(data);
    showToast("Benchmark experiments completed and saved to output/.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    setBusy(btn, false);
    hideLoading();
  }
}

/* --------------------------------------------------------------------------
   Campus Configurator & Heuristic Verification
--------------------------------------------------------------------------- */
async function handleAddRoom(e) {
  e?.preventDefault();
  const name = $("#room-name")?.value.trim();
  const type = $("#room-type")?.value || "generic";
  const floor = $("#room-floor")?.value || "Ground floor";
  const searchCost = Number($("#room-search-cost")?.value || 2.0);

  if (!name) {
    showToast("Please enter a location name.", "warning");
    return;
  }

  showLoading("Adding campus location...");
  try {
    const currentConfig = state.config;
    const isGround = floor.toLowerCase().includes("ground");
    const row = isGround ? 1 : 4;
    const col = 3;

    const newNodes = [
      ...(currentConfig.nodes || []).map(n => ({
        name: n.name,
        row: n.y ? Math.round(n.y / 1.5) : 1,
        col: n.x ? Math.round(n.x / 2.0) : 1,
        node_type: n.type || "generic",
        search_cost: n.search_cost || 1.0,
        x: n.x,
        y: n.y,
        floor: n.floor,
      })),
      {
        name,
        row,
        col,
        node_type: type,
        search_cost: searchCost,
        x: 7.5,
        y: isGround ? 3.5 : 7.5,
        floor,
      },
    ];

    const currentEdges = (currentConfig.edges || []).map(edge => ({
      source: edge.source,
      target: edge.target,
      weight: edge.weight,
      blocked: edge.blocked,
    }));

    const updated = await api("/api/campus/custom", { nodes: newNodes, edges: currentEdges });
    initialize(updated);
    showToast(`Added location "${name}" to campus map.`, "success");
    $("#room-name").value = "";
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function handleAddCorridor(e) {
  e?.preventDefault();
  const source = $("#corridor-source")?.value;
  const target = $("#corridor-target")?.value;
  const weight = Number($("#corridor-weight")?.value || 1.5);

  if (!source || !target || source === target) {
    showToast("Please choose two different rooms to connect.", "warning");
    return;
  }

  showLoading("Connecting campus corridor...");
  try {
    const currentConfig = state.config;
    const currentNodes = (currentConfig.nodes || []).map(n => ({
      name: n.name,
      row: n.y ? Math.round(n.y / 1.5) : 1,
      col: n.x ? Math.round(n.x / 2.0) : 1,
      node_type: n.type || "generic",
      search_cost: n.search_cost || 1.0,
      x: n.x,
      y: n.y,
      floor: n.floor,
    }));

    const currentEdges = [
      ...(currentConfig.edges || []).map(edge => ({
        source: edge.source,
        target: edge.target,
        weight: edge.weight,
        blocked: edge.blocked,
      })),
      { source, target, weight, blocked: false },
    ];

    const updated = await api("/api/campus/custom", { nodes: currentNodes, edges: currentEdges });
    initialize(updated);
    showToast(`Connected ${source} ↔ ${target} (Cost: ${weight}).`, "success");
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function handleVerifyHeuristic() {
  showLoading("Verifying heuristic admissibility and consistency...");
  try {
    const report = await api("/api/campus/verify_heuristic", {});
    const container = $("#heuristic-verification-result");
    if (container) {
      container.innerHTML = `
        <div style="padding:16px; border-radius:var(--radius-sm); border:1px solid ${report.admissible && report.consistent ? "var(--primary-border)" : "var(--accent-blocked)"}; background: ${report.admissible && report.consistent ? "var(--primary-light)" : "var(--accent-blocked-light)"};">
          <strong style="display:block; font-size:14px; margin-bottom:6px; color: ${report.admissible && report.consistent ? "var(--primary)" : "var(--accent-blocked)"};">
            ${report.admissible && report.consistent ? "✓ Mathematical Guarantee Verified: Heuristic is Admissible & Consistent" : "✕ Heuristic Violations Detected"}
          </strong>
          <span style="font-size:12.5px; color:var(--text-secondary); display:block;">
            Tested ${report.pairs_tested} node pairs and ${report.edges_tested} edge transitions. Goal condition h(g,g)=0 is ${report.goal_condition_valid ? "valid" : "violated"}.
          </span>
          ${report.consistency_violations.length ? `
            <div style="margin-top:8px; font-size:11.5px; font-family:var(--font-mono); color:var(--accent-blocked);">
              First violation: Edge (${report.consistency_violations[0].u} → ${report.consistency_violations[0].v}) exceeds step cost by ${report.consistency_violations[0].violation}.
            </div>
          ` : ""}
        </div>
      `;
    }
    showToast(report.admissible && report.consistent ? "Heuristic is 100% admissible and consistent." : "Heuristic violations found.", report.admissible ? "success" : "warning");
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function handleResetCampus() {
  if (!confirm("Reset campus map back to the default 20-node layout?")) return;
  showLoading("Resetting campus layout...");
  try {
    const updated = await api("/api/campus/reset", {});
    initialize(updated);
    showToast("Campus map reset to default 20-node layout.", "success");
    const container = $("#heuristic-verification-result");
    if (container) container.innerHTML = "";
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

/* --------------------------------------------------------------------------
   Search & Mission History
--------------------------------------------------------------------------- */
async function loadHistory() {
  const container = $("#history-container");
  if (!container) return;

  try {
    const data = await api("/api/history", {}, "GET");
    const history = data.history || [];

    if (!history.length) {
      container.innerHTML = '<p class="field-help">No search history recorded yet. Run a search to create an auditable log.</p>';
      return;
    }

    const cards = history.map((item, idx) => `
      <div class="card" style="padding:16px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <strong style="font-size:15px; color:var(--text-primary);">${escapeHtml(item.item || "Lost Item")}</strong>
            <span class="badge ${item.recovered_location ? "emerald" : "slate"}">
              ${item.recovered_location ? `Recovered at ${escapeHtml(item.recovered_location)}` : item.mode === "mission" ? "Unreached" : "Planned"}
            </span>
            <span style="font-size:11.5px; color:var(--text-muted);">${escapeHtml(item.timestamp || "")}</span>
          </div>
          <span style="font-size:12.5px; color:var(--text-secondary);">
            From <strong>${escapeHtml(item.start)}</strong> · Last seen at <strong>${escapeHtml(item.last_seen)}</strong> · ${escapeHtml(algorithmName(item.algorithm))}
            ${item.path_cost ? ` · Cost: ${formatNumber(item.path_cost)}` : ""}
            ${item.execution_time_ms ? ` · Time: ${formatNumber(item.execution_time_ms, 3)} ms` : ""}
          </span>
        </div>
        <button class="button secondary" type="button" onclick="replayHistorySearch('${escapeHtml(item.start)}', '${escapeHtml(item.last_seen)}', '${escapeHtml(item.item)}')">
          Load Search
        </button>
      </div>
    `).join("");

    container.innerHTML = cards;
  } catch {
    container.innerHTML = '<p class="field-help">Unable to retrieve history.</p>';
  }
}

window.replayHistorySearch = function(start, lastSeen, item) {
  if ($("#current-location")) $("#current-location").value = start;
  if ($("#last-seen")) $("#last-seen").value = lastSeen;
  switchPage("search");
  renderCampusMap();
  showToast(`Loaded query: ${item} from ${start}`, "info");
};

async function handleClearHistory() {
  if (!confirm("Clear all search history?")) return;
  try {
    await api("/api/history", {}, "DELETE");
    loadHistory();
    showToast("Search history cleared.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function handleExportHistory() {
  try {
    const data = await api("/api/history", {}, "GET");
    downloadText(JSON.stringify(data.history || [], null, 2), "lost_item_search_history.json", "application/json");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

/* --------------------------------------------------------------------------
   App Initialization & Navigation
--------------------------------------------------------------------------- */
function switchPage(name) {
  $$(".nav-button").forEach((btn) => btn.classList.toggle("active", btn.dataset.page === name));
  $$(".page-section").forEach((sec) => sec.classList.toggle("active", sec.id === `page-${name}`));

  if (name === "grid" && !state.lastGridResult) $("#grid-form")?.requestSubmit();
  if (name === "comparison" && !$("#comparison-results")?.innerHTML) $("#comparison-form")?.requestSubmit();
  if (name === "search") renderCampusMap();
  if (name === "config") renderCampusMap(null, "#config-campus-map");
  if (name === "history") loadHistory();
}

function candidateOptionsChanged() {
  const category = $("#item-category")?.value || "laptop";
  const defaultList = state.config?.item_candidates?.[category] || state.config?.locations?.slice(0, 4) || [];
  renderChecks("#candidate-options", state.config?.locations || [], defaultList, "candidate");
  renderBeliefs();
  populateActualLocation();
  renderCampusMap();
}

function renderBeliefs() {
  const candidates = checkedValues("#candidate-options");
  const visited = checkedValues("#visited-options");
  const lastSeen = $("#last-seen")?.value;
  const pool = [...new Set([...candidates, ...visited])];

  const container = $("#belief-options");
  if (!container) return;

  if (!pool.length) {
    container.innerHTML = '<p class="field-help">Select candidate locations first to adjust likelihood guesses.</p>';
    return;
  }

  container.innerHTML = pool.map((cand) => {
    const isLastSeen = cand === lastSeen;
    const defaultVal = isLastSeen ? 0.75 : 0.50;
    return `
      <div class="belief-row">
        <span>${escapeHtml(cand)} ${isLastSeen ? '<span class="field-badge last-seen">Last Seen</span>' : ''}</span>
        <input type="range" min="0.05" max="0.95" step="0.05" value="${defaultVal}" data-candidate="${escapeHtml(cand)}">
        <output>${Math.round(defaultVal * 100)}%</output>
      </div>
    `;
  }).join("");
}

function populateActualLocation() {
  const candidates = checkedValues("#candidate-options");
  const visited = checkedValues("#visited-options");
  const pool = [...new Set([...candidates, ...visited])];
  const lastSeen = $("#last-seen")?.value;
  populateSelect("#actual-location", pool.length ? pool : state.config?.locations || [], lastSeen && pool.includes(lastSeen) ? lastSeen : pool[0]);
}

function updateApproachHelp() {
  const algo = $("#search-algorithm")?.value;
  const helpEl = $("#approach-help");
  if (!helpEl) return;
  const descriptions = {
    astar: "Balanced route (A*) evaluates g(n) + h(n). Guaranteed cost-optimal with admissible Euclidean heuristic.",
    bfs: "Fewest steps (BFS) returns the path with minimal edge count. Uninformed, ignores corridor travel costs.",
    greedy: "Greedy Best-First orders purely by h(n). Fast heuristic chase, but frequently takes longer paths around dead-ends.",
  };
  helpEl.textContent = descriptions[algo] || descriptions.astar;
}

function initialize(config) {
  state.config = config;

  const locs = config.locations || [];
  populateSelect("#last-seen", locs, "Library");
  populateSelect("#current-location", locs, "Main Entrance");
  populateSelect("#compare-start", locs, "Main Entrance");
  populateSelect("#compare-goal", locs, "Classroom-102");
  populateSelect("#corridor-source", locs, locs[0]);
  populateSelect("#corridor-target", locs, locs[1] || locs[0]);

  const catSelect = $("#item-category");
  if (catSelect && config.item_candidates) {
    catSelect.innerHTML = [
      ...Object.keys(config.item_candidates),
      "other / custom",
    ].map(item => optionMarkup(item)).join("");
    catSelect.value = "laptop";
  }

  renderChecks("#visited-options", locs, [], "visited");
  renderChecks("#blocked-options", (config.edges || []).map(e => `${e.source} ↔ ${e.target}`), [], "blocked");
  $$("#blocked-options input").forEach((input, idx) => { input.value = String(idx); });

  const pill = $("#campus-status-pill");
  if (pill) {
    pill.textContent = config.is_custom_campus
      ? `Custom campus layout active (${locs.length} rooms, ${config.edges?.length || 0} corridors).`
      : "Default 20-node campus layout active.";
  }

  candidateOptionsChanged();
  renderCampusMap();
  renderCampusMap(null, "#config-campus-map");
  resetGridMap(false);
  updateApproachHelp();
}

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();

  // Navigation handlers
  $$(".nav-button").forEach((btn) => btn.addEventListener("click", () => switchPage(btn.dataset.page)));

  // Form handlers
  $("#item-category")?.addEventListener("change", () => {
    const isCustom = $("#item-category").value === "other / custom";
    $("#custom-item-wrap")?.classList.toggle("hidden", !isCustom);
    candidateOptionsChanged();
  });

  $("#candidate-options")?.addEventListener("change", () => {
    renderBeliefs();
    populateActualLocation();
    renderCampusMap();
  });

  $("#visited-options")?.addEventListener("change", () => {
    renderBeliefs();
    populateActualLocation();
    renderCampusMap();
  });

  $("#blocked-options")?.addEventListener("change", () => renderCampusMap());

  $("#belief-options")?.addEventListener("input", (e) => {
    if (e.target.matches("input[type=range]")) {
      e.target.nextElementSibling.value = `${Math.round(Number(e.target.value) * 100)}%`;
    }
  });

  ["#current-location", "#last-seen"].forEach((sel) => {
    $(sel)?.addEventListener("change", () => {
      renderBeliefs();
      populateActualLocation();
      renderCampusMap();
    });
  });

  $("#search-algorithm")?.addEventListener("change", () => {
    const isBfs = $("#search-algorithm").value === "bfs";
    const heur = $("#search-heuristic");
    if (heur) heur.disabled = isBfs;
    updateApproachHelp();
  });

  // Action Buttons
  $("#plan-button")?.addEventListener("click", (e) => runCampusSearch("plan", e.currentTarget));
  $("#mission-button")?.addEventListener("click", (e) => runCampusSearch("mission", e.currentTarget));

  // Grid Map
  $("#grid-form")?.addEventListener("submit", runGridSearch);
  $("#grid-map")?.addEventListener("click", selectGridPoint);
  $$(".point-button").forEach((btn) => btn.addEventListener("click", () => {
    state.gridSelection = btn.dataset.point;
    updateGridSelectionHelp();
  }));
  $("#grid-size")?.addEventListener("change", () => resetGridMap(false));
  $("#grid-obstacles")?.addEventListener("change", () => resetGridMap(false));
  $("#new-map-button")?.addEventListener("click", () => resetGridMap(true));

  // Comparison & Benchmarks
  $("#comparison-form")?.addEventListener("submit", runComparison);
  $("#benchmark-form")?.addEventListener("submit", runBenchmarks);
  $("#benchmark-suite")?.addEventListener("change", () => {
    $("#custom-benchmark-fields")?.classList.toggle("hidden", $("#benchmark-suite").value !== "custom");
  });

  // Campus Configurator
  $("#add-room-form")?.addEventListener("submit", handleAddRoom);
  $("#add-corridor-form")?.addEventListener("submit", handleAddCorridor);
  $("#verify-heuristic-btn")?.addEventListener("click", handleVerifyHeuristic);
  $("#reset-campus-btn")?.addEventListener("click", handleResetCampus);

  // History
  $("#clear-history-btn")?.addEventListener("click", handleClearHistory);
  $("#export-history-btn")?.addEventListener("click", handleExportHistory);

  // Initial config load
  try {
    const config = await api("/api/config", {}, "GET");
    initialize(config);
  } catch (err) {
    showToast(err.message, "danger");
  }
});
