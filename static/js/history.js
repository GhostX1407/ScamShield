/**
 * ScamShield — History Controller
 * Loads scans log from SQLite API, updates statistics, handles filtering,
 * and manages individual or bulk record deletion.
 */

(function () {
  'use strict';

  // ── Elements ────────────────────────────────────────────────────────────
  const statTotal = document.getElementById('statTotal');
  const statSafe = document.getElementById('statSafe');
  const statSuspicious = document.getElementById('statSuspicious');
  const statDangerous = document.getElementById('statDangerous');

  const filterVerdict = document.getElementById('filterVerdict');
  const filterType = document.getElementById('filterType');
  const filterDate = document.getElementById('filterDate');
  const applyFilterBtn = document.getElementById('applyFilterBtn');
  const clearFilterBtn = document.getElementById('clearFilterBtn');

  const historyTable = document.getElementById('historyTable');
  const historyTableBody = document.getElementById('historyTableBody');
  const historyEmptyState = document.getElementById('historyEmptyState');

  const deleteAllBtn = document.getElementById('deleteAllBtn');
  const deleteAllModal = document.getElementById('deleteAllModal');
  const delModalConfirmBtn = document.getElementById('delModalConfirmBtn');
  const delModalCancelBtn = document.getElementById('delModalCancelBtn');
  const delModalCancelCross = document.getElementById('delModalCancelCross');

  // ── Fetch & Render Statistics ───────────────────────────────────────────
  async function loadStats() {
    try {
      const resp = await fetch('/api/history/stats');
      if (!resp.ok) return;
      const stats = await resp.json();

      statTotal.textContent = stats.total || 0;
      const byVerdict = stats.by_verdict || {};
      statSafe.textContent = byVerdict.safe || 0;
      statSuspicious.textContent = byVerdict.suspicious || 0;
      statDangerous.textContent = byVerdict.dangerous || 0;
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }

  // ── Fetch & Render History Rows ─────────────────────────────────────────
  async function loadHistory() {
    try {
      const params = new URLSearchParams();
      if (filterVerdict.value) params.set('verdict', filterVerdict.value);
      if (filterType.value) params.set('type', filterType.value);
      if (filterDate.value) params.set('date', filterDate.value);

      const url = `/api/history${params.toString() ? '?' + params.toString() : ''}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('Failed to load scan history');

      const scans = await resp.json();
      renderTable(scans);
    } catch (err) {
      console.error(err);
      window.showToast('Could not load history.', 'error');
    }
  }

  function renderTable(scans) {
    historyTableBody.innerHTML = '';

    if (!scans || scans.length === 0) {
      historyTable.style.display = 'none';
      historyEmptyState.style.display = 'flex';
      return;
    }

    historyTable.style.display = 'table';
    historyEmptyState.style.display = 'none';

    scans.forEach((scan) => {
      const tr = document.createElement('tr');
      tr.id = `scan-row-${scan.id}`;

      const formattedTime = formatTimestamp(scan.timestamp);
      const typeLabel = window.i18n.t(`type_${scan.type}`, scan.type || 'message');
      const verdict = scan.verdict || 'safe';
      const verdictLabel = window.i18n.t(`result_verdict_${verdict}`, verdict);

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted);">${window.escapeHtml(formattedTime)}</td>
        <td><span class="badge-type">${window.escapeHtml(typeLabel)}</span></td>
        <td class="preview-cell" title="${window.escapeHtml(scan.preview || '')}">${window.escapeHtml(scan.preview || '—')}</td>
        <td><span class="badge-verdict badge-${verdict}">${window.escapeHtml(verdictLabel)}</span></td>
        <td style="font-weight: 700; font-family: var(--font-mono);">${scan.score} / 100</td>
        <td>
          <button type="button" class="btn btn-outline" style="padding: 0.3rem 0.65rem; font-size: 0.78rem;" data-id="${scan.id}">
            🗑️ <span data-i18n="history_btn_delete">${window.i18n.t('history_btn_delete', 'Delete')}</span>
          </button>
        </td>
      `;

      // Delete single scan handler
      const deleteBtn = tr.querySelector('button[data-id]');
      deleteBtn.addEventListener('click', () => deleteSingleScan(scan.id));

      historyTableBody.appendChild(tr);
    });
  }

  function formatTimestamp(ts) {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts;
      return d.toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return ts;
    }
  }

  // ── Delete Operations ───────────────────────────────────────────────────
  async function deleteSingleScan(id) {
    const confirmMsg = window.i18n.t('history_delete_confirm', 'Delete this scan from history?');
    if (!confirm(confirmMsg)) return;

    try {
      const resp = await fetch(`/api/history/${id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('Deletion failed');

      const row = document.getElementById(`scan-row-${id}`);
      if (row) {
        row.style.transition = 'opacity 0.25s, transform 0.25s';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(() => {
          row.remove();
          if (historyTableBody.children.length === 0) {
            historyTable.style.display = 'none';
            historyEmptyState.style.display = 'flex';
          }
        }, 250);
      }

      window.showToast('Scan deleted from history.', 'success');
      loadStats();
    } catch (err) {
      window.showToast('Failed to delete scan.', 'error');
    }
  }

  async function handleDeleteAll() {
    try {
      const resp = await fetch('/api/history', { method: 'DELETE' });
      if (!resp.ok) throw new Error('Bulk deletion failed');
      const data = await resp.json();

      window.closeModal('deleteAllModal');
      window.showToast(`Deleted ${data.deleted_count || 0} scans from history.`, 'success');

      await loadStats();
      await loadHistory();
    } catch (err) {
      window.showToast('Failed to delete all scans.', 'error');
    }
  }

  // ── Event Bindings ──────────────────────────────────────────────────────
  function bindEvents() {
    applyFilterBtn.addEventListener('click', loadHistory);

    clearFilterBtn.addEventListener('click', () => {
      filterVerdict.value = '';
      filterType.value = '';
      filterDate.value = '';
      loadHistory();
    });

    deleteAllBtn.addEventListener('click', () => {
      window.openModal('deleteAllModal');
    });

    delModalCancelBtn.addEventListener('click', () => window.closeModal('deleteAllModal'));
    delModalCancelCross.addEventListener('click', () => window.closeModal('deleteAllModal'));
    delModalConfirmBtn.addEventListener('click', handleDeleteAll);

    // Language changed event re-translates labels
    document.addEventListener('scamshield:langchange', () => {
      loadHistory();
    });
  }

  // Initialize
  function init() {
    bindEvents();
    loadStats();
    loadHistory();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
