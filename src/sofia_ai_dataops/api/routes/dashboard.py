"""Dashboard operativo de Sofia AI DataOps.

Objetivo: ofrecer una primera consola visual para explorar incidentes y memoria sin agregar
frontend pesado.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sofia AI DataOps</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #20242c;
      --muted: #6a7280;
      --line: #d9dee8;
      --blue: #2764d8;
      --green: #16825d;
      --red: #b42318;
      --amber: #b54708;
      --violet: #6d3fc8;
      --shadow: 0 16px 36px rgba(26, 31, 44, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      letter-spacing: 0;
      overflow-x: hidden;
    }

    button, input, select { font: inherit; }

    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .topbar {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 0 24px;
      background: #111827;
      color: #f9fafb;
      border-bottom: 1px solid #0f172a;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 240px;
    }

    .brand-mark {
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: #2f6fed;
      color: #fff;
      font-weight: 800;
    }

    .brand-title {
      display: grid;
      gap: 2px;
    }

    .brand-title strong { font-size: 15px; }
    .brand-title span { color: #b8c0cc; font-size: 12px; }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .icon-button, .text-button {
      height: 36px;
      border: 1px solid #3a4658;
      background: #1f2937;
      color: #f9fafb;
      border-radius: 6px;
      cursor: pointer;
    }

    .icon-button {
      width: 36px;
      display: grid;
      place-items: center;
      padding: 0;
    }

    .text-button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0 12px;
    }

    .icon-button:hover, .text-button:hover { background: #273345; }
    .icon { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 2; }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 20px;
      padding: 20px;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
    }

    .main, .side {
      display: grid;
      align-content: start;
      gap: 16px;
      min-width: 0;
    }

    .side {
      grid-template-columns: minmax(320px, 0.35fr) minmax(0, 1fr);
      align-items: start;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
    }

    @media (max-width: 1200px) {
      .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }

    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .metric {
      min-height: 92px;
      padding: 14px;
      display: grid;
      align-content: space-between;
      gap: 10px;
    }

    .metric span {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }

    .metric strong { font-size: 26px; line-height: 1; }

    .panel-header {
      min-height: 54px;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      border-bottom: 1px solid var(--line);
    }

    .panel-header h2 {
      margin: 0;
      font-size: 15px;
      line-height: 1.2;
    }

    .filters {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .filters select {
      height: 34px;
      min-width: 136px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 0 10px;
    }

    .table-wrap {
      width: 100%;
      overflow-x: auto;
      overflow-y: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      min-width: 760px;
    }

    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid #edf0f5;
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      background: #fbfcfe;
    }

    tr[data-analysis-id] { cursor: pointer; }
    tr[data-analysis-id]:hover { background: #f2f6ff; }
    tr.selected { background: #eaf1ff; }

    .mono-cell {
      font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 13px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
    }

    .critical { color: #8a1c12; background: #fee4df; border-color: #f9b8ad; }
    .high { color: #8a3a00; background: #ffedd5; border-color: #fdba74; }
    .medium { color: #184b8f; background: #dbeafe; border-color: #93c5fd; }
    .low { color: #166534; background: #dcfce7; border-color: #86efac; }
    .unknown { color: #5f6673; background: #eef1f5; border-color: #d7dce4; }

    .context-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 32px;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      color: #374151;
      background: #f3f4f6;
      border: 1px solid #d1d5db;
      font-size: 12px;
      font-weight: 700;
    }

    .context-count.has-context {
      color: #155e75;
      background: #cffafe;
      border-color: #67e8f9;
    }

    .detail-body {
      padding: 16px;
      display: grid;
      gap: 16px;
    }

    .kv {
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
    }

    .kv span {
      color: var(--muted);
      font-size: 12px;
    }

    .kv strong, .kv code {
      min-width: 0;
      overflow-wrap: anywhere;
    }

    .section-title {
      margin: 0 0 8px;
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0;
    }

    .list {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }

    .context-item {
      padding: 10px;
      background: #f8fafc;
      border: 1px solid #e3e8ef;
      border-radius: 6px;
      overflow-wrap: anywhere;
    }

    .context-item.match {
      background: #f0fdf4;
      border-color: #86efac;
    }

    .context-item.mismatch {
      background: #fff7ed;
      border-color: #fdba74;
    }

    .context-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 6px;
    }

    .context-label {
      flex: 1;
      min-width: 0;
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .context-status {
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      height: 22px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
    }

    .context-status.match {
      color: #166534;
      background: #dcfce7;
      border: 1px solid #86efac;
    }

    .context-status.mismatch {
      color: #9a3412;
      background: #ffedd5;
      border: 1px solid #fdba74;
    }

    .context-meta {
      color: var(--muted);
      font-size: 12px;
    }

    pre {
      margin: 0;
      padding: 12px;
      background: #111827;
      color: #e5e7eb;
      border-radius: 6px;
      overflow: auto;
      max-height: 220px;
      font-size: 12px;
    }

    .empty {
      padding: 32px 16px;
      color: var(--muted);
      text-align: center;
    }

    .status-line {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid #edf0f5;
    }

    .status-line:last-child { border-bottom: 0; }

    .status-line span { color: var(--muted); }
    .status-line strong { font-size: 18px; }

    .sync-ok { color: var(--green); }
    .sync-warn { color: var(--amber); }
    .error { color: var(--red); }

    .toast {
      position: fixed;
      right: 20px;
      bottom: 20px;
      max-width: 380px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      box-shadow: var(--shadow);
      display: none;
      z-index: 10;
    }

    .toast.show { display: block; }

    @media (max-width: 980px) {
      .layout { padding: 14px; }
      .side { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .topbar { padding: 0 14px; }
      .brand-title span { display: none; }
      table { min-width: 820px; }
    }

    @media (max-width: 620px) {
      .metrics { grid-template-columns: 1fr; }
      .panel-header { align-items: stretch; flex-direction: column; }
      .filters { width: 100%; }
      .filters select { flex: 1; min-width: 0; }
      .layout { padding: 10px; }
      .topbar { height: auto; padding: 12px; align-items: flex-start; }
      .top-actions { flex-wrap: wrap; justify-content: flex-end; }
      th:nth-child(5), td:nth-child(5) { display: none; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div class="brand-title">
          <strong>Sofia AI DataOps</strong>
          <span>Airflow Incident Console</span>
        </div>
      </div>
      <div class="top-actions">
        <button class="icon-button" id="refreshButton" title="Actualizar">
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 12a9 9 0 1 1-2.64-6.36"></path><path d="M21 3v7h-7"></path>
          </svg>
        </button>
        <button class="text-button" id="reindexButton">
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 3v18"></path><path d="M17 8l-5-5-5 5"></path><path d="M19 21H5"></path>
          </svg>
          Reindexar
        </button>
      </div>
    </header>

    <main class="layout">
      <section class="main">
        <div class="metrics">
          <div class="metric">
            <span>Incidentes (24h)</span><strong id="metricTotal">0</strong>
          </div>
          <div class="metric">
            <span>Criticos/Altos (24h)</span><strong id="metricHigh">0</strong>
          </div>
          <div class="metric">
            <span>Con contexto</span><strong id="metricContext">0</strong>
          </div>
          <div class="metric">
            <span>Qdrant</span><strong id="metricQdrant">0</strong>
          </div>
          <div class="metric">
            <span>Fallbacks (24h)</span><strong id="metricFallback">0</strong>
          </div>
        </div>

        <section class="panel">
          <div class="panel-header">
            <h2>Incidentes recientes</h2>
            <div class="filters">
              <select id="severityFilter" aria-label="Filtrar por severidad">
                <option value="">Todas las severidades</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select id="typeFilter" aria-label="Filtrar por tipo">
                <option value="">Todos los tipos</option>
                <option value="connectivity">Connectivity</option>
                <option value="permissions">Permissions</option>
                <option value="infrastructure">Infrastructure</option>
                <option value="upstream">Upstream</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style="width: 21%">DAG</th>
                  <th style="width: 17%">Task</th>
                  <th style="width: 12%">Sev</th>
                  <th style="width: 16%">Tipo</th>
                  <th style="width: 7%">Ctx</th>
                  <th>Resumen</th>
                  <th style="width: 13%">Fecha</th>
                </tr>
              </thead>
              <tbody id="incidentRows">
                <tr><td colspan="7" class="empty">Cargando incidentes...</td></tr>
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <aside class="side">
        <section class="panel">
          <div class="panel-header">
            <h2>Memoria</h2>
            <span id="memorySync" class="unknown">Sin datos</span>
          </div>
          <div>
            <div class="status-line">
              <span>PostgreSQL</span><strong id="postgresCount">0</strong>
            </div>
            <div class="status-line"><span>Qdrant</span><strong id="qdrantCount">0</strong></div>
            <div class="status-line"><span>Estado</span><strong id="syncState">-</strong></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header"><h2>Detalle</h2></div>
          <div class="detail-body" id="detail">
            <div class="empty">Seleccioná un incidente para ver recomendaciones y contexto.</div>
          </div>
        </section>
      </aside>
    </main>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    const state = { incidents: [], selectedId: null, memory: null, metrics: null };

    const qs = (selector) => document.querySelector(selector);
    const rows = qs("#incidentRows");
    const detail = qs("#detail");

    function badge(value) {
      const css = value || "unknown";
      return `<span class="badge ${css}">${value || "unknown"}</span>`;
    }

    function contextCountBadge(count) {
      const css = count > 0 ? "context-count has-context" : "context-count";
      return `<span class="${css}">${count}</span>`;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function showToast(message, isError = false) {
      const toast = qs("#toast");
      toast.textContent = message;
      toast.className = `toast show${isError ? " error" : ""}`;
      window.setTimeout(() => { toast.className = "toast"; }, 3200);
    }

    function parseContextItem(value) {
      const match = String(value).match(/^(.*?):\\s*([^/]+)\\/\\s*([^\\s]+)\\s*-\\s*(.*)$/);
      if (!match) {
        return { label: value, failureType: "unknown", severity: "unknown", summary: value };
      }
      return {
        label: match[1].trim(),
        failureType: match[2].trim(),
        severity: match[3].trim(),
        summary: match[4].trim(),
      };
    }

    async function fetchJson(url, options = {}) {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    }

    function filteredIncidents() {
      const severity = qs("#severityFilter").value;
      const type = qs("#typeFilter").value;
      return state.incidents.filter((incident) => {
        return (!severity || incident.severity === severity)
          && (!type || incident.failure_type === type);
      });
    }

    function renderMetrics() {
      // Contadores 24h desde /api/v1/metrics (fuente de verdad para total, high y fallbacks).
      const m = state.metrics;
      if (m) {
        const highCount = (m.by_severity?.critical ?? 0) + (m.by_severity?.high ?? 0);
        qs("#metricTotal").textContent = m.total_analyses ?? 0;
        qs("#metricHigh").textContent = highCount;
        qs("#metricFallback").textContent = m.fallback_triggered ?? 0;
      } else {
        // Fallback local mientras carga /metrics.
        const highCount = state.incidents
          .filter((item) => ["critical", "high"].includes(item.severity)).length;
        qs("#metricTotal").textContent = state.incidents.length;
        qs("#metricHigh").textContent = highCount;
        qs("#metricFallback").textContent = "-";
      }
      // Context y Qdrant se calculan de los datos de incidents/memory (no estan en /metrics).
      const contextCount = state.incidents
        .filter((item) => (item.retrieved_context || []).length > 0).length;
      qs("#metricContext").textContent = contextCount;
      qs("#metricQdrant").textContent = state.memory?.qdrant_points ?? 0;
    }

    function renderMemory() {
      const memory = state.memory;
      if (!memory) return;

      qs("#postgresCount").textContent = memory.postgres_analyses;
      qs("#qdrantCount").textContent = memory.qdrant_points;
      qs("#syncState").textContent = memory.is_in_sync ? "Sincronizada" : "Requiere reindexado";
      qs("#syncState").className = memory.is_in_sync ? "sync-ok" : "sync-warn";
      qs("#memorySync").textContent = memory.is_in_sync ? "OK" : "Revisar";
      qs("#memorySync").className = memory.is_in_sync ? "sync-ok" : "sync-warn";
    }

    function renderTable() {
      const incidents = filteredIncidents();
      if (incidents.length === 0) {
        rows.innerHTML = `
          <tr><td colspan="7" class="empty">Sin incidentes para este filtro.</td></tr>
        `;
        return;
      }

      rows.innerHTML = incidents.map((incident) => {
        const selected = incident.analysis_id === state.selectedId ? " selected" : "";
        const date = new Date(incident.created_at).toLocaleString();
        const contextCount = (incident.retrieved_context || []).length;
        return `
          <tr class="${selected}" data-analysis-id="${escapeHtml(incident.analysis_id)}">
            <td class="mono-cell" title="${escapeHtml(incident.dag_id)}">
              ${escapeHtml(incident.dag_id)}
            </td>
            <td class="mono-cell" title="${escapeHtml(incident.task_id)}">
              ${escapeHtml(incident.task_id)}
            </td>
            <td>${badge(incident.severity)}</td>
            <td>${badge(incident.failure_type)}</td>
            <td>${contextCountBadge(contextCount)}</td>
            <td title="${escapeHtml(incident.summary)}">${escapeHtml(incident.summary)}</td>
            <td>${escapeHtml(date)}</td>
          </tr>
        `;
      }).join("");

      document.querySelectorAll("tr[data-analysis-id]").forEach((row) => {
        row.addEventListener("click", () => selectIncident(row.dataset.analysisId));
      });
    }

    function selectIncident(id) {
      state.selectedId = id;
      renderTable();
      renderDetail();
    }

    function renderDetail() {
      const incident = state.incidents.find((item) => item.analysis_id === state.selectedId);
      if (!incident) {
        detail.innerHTML = `
          <div class="empty">Seleccioná un incidente para ver recomendaciones y contexto.</div>
        `;
        return;
      }

      const recommendations = (incident.recommendations || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      const context = (incident.retrieved_context || []);
      const contextHtml = context.length
        ? context.map((item) => {
          const parsed = parseContextItem(item);
          const isMatch = parsed.failureType === incident.failure_type;
          const css = isMatch ? "match" : "mismatch";
          const status = isMatch ? "match" : "revisar";
          return `
            <div class="context-item ${css}">
              <div class="context-head">
                <div class="context-label">${escapeHtml(parsed.label)}</div>
                <span class="context-status ${css}">${status}</span>
              </div>
              <div class="context-meta">
                ${escapeHtml(parsed.failureType)} / ${escapeHtml(parsed.severity)}
              </div>
              <div>${escapeHtml(parsed.summary)}</div>
            </div>
          `;
        }).join("")
        : `<div class="empty">Sin contexto recuperado.</div>`;

      detail.innerHTML = `
        <div class="kv"><span>DAG</span><strong>${escapeHtml(incident.dag_id)}</strong></div>
        <div class="kv"><span>Task</span><strong>${escapeHtml(incident.task_id)}</strong></div>
        <div class="kv"><span>Run</span><code>${escapeHtml(incident.run_id)}</code></div>
        <div class="kv"><span>Severidad</span><div>${badge(incident.severity)}</div></div>
        <div class="kv"><span>Tipo</span><div>${badge(incident.failure_type)}</div></div>
        <div>
          <p class="section-title">Causa raíz</p>
          <div>${escapeHtml(incident.root_cause)}</div>
        </div>
        <div>
          <p class="section-title">Recomendaciones</p>
          <ol class="list">${recommendations}</ol>
        </div>
        <div>
          <p class="section-title">Contexto recuperado</p>
          ${contextHtml}
        </div>
        <div>
          <p class="section-title">Metadata</p>
          <pre>${escapeHtml(JSON.stringify(incident.metadata || {}, null, 2))}</pre>
        </div>
      `;
    }

    async function loadDashboard() {
      try {
        const [incidents, memory, metricsData] = await Promise.all([
          fetchJson("/api/v1/incidents?limit=100"),
          fetchJson("/api/v1/memory/status"),
          fetchJson("/api/v1/metrics").catch(() => null),  // no bloquea si falla
        ]);
        state.incidents = incidents;
        state.memory = memory;
        state.metrics = metricsData;
        if (!state.selectedId && incidents.length > 0) {
          state.selectedId = incidents[0].analysis_id;
        }
        renderMetrics();
        renderMemory();
        renderTable();
        renderDetail();
      } catch (error) {
        rows.innerHTML = `
          <tr><td colspan="7" class="empty error">No se pudieron cargar datos.</td></tr>
        `;
        showToast(`No se pudieron cargar datos: ${error.message}`, true);
      }
    }

    async function reindex() {
      const button = qs("#reindexButton");
      button.disabled = true;
      try {
        const result = await fetchJson("/api/v1/memory/reindex?limit=1000", { method: "POST" });
        showToast(`Reindexados ${result.indexed}/${result.total_available} análisis.`);
        await loadDashboard();
      } catch (error) {
        showToast(`No se pudo reindexar: ${error.message}`, true);
      } finally {
        button.disabled = false;
      }
    }

    qs("#refreshButton").addEventListener("click", loadDashboard);
    qs("#reindexButton").addEventListener("click", reindex);
    qs("#severityFilter").addEventListener("change", () => { renderTable(); renderDetail(); });
    qs("#typeFilter").addEventListener("change", () => { renderTable(); renderDetail(); });

    loadDashboard();
  </script>
</body>
</html>
"""
