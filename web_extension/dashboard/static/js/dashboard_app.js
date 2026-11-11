/**
 * Module: dashboard_app.js
 * Deskripsi: State management, filtering kartu KPI, pencarian tabel,
 *            modal inspector, dan inisialisasi antarmuka utama.
 * Lead Engineer: Pascol
 */

let currentFilter = 'ALL';

function updateKPIs() {
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    let match = 0, rolling = 0, diff = 0, nihil = 0, edited = 0;

    rows.forEach(r => {
        const st = r.getAttribute('data-status');
        if (st === 'MATCH') match++;
        else if (st === 'ROLLING') rolling++;
        else if (st === 'DIFF') diff++;
        else if (st === 'NIHIL' || st === 'TRIAGE') nihil++;

        if (r.getAttribute('data-edited') === 'true') edited++;
    });

    const total = rows.length;
    const statTotal = document.getElementById('stat-total');
    if (statTotal) statTotal.textContent = total;

    const statMatch = document.getElementById('stat-match');
    if (statMatch) {
        statMatch.innerHTML = `${match} <span class="kpi-pct-badge">(${total ? Math.round(match/total*100) : 0}%)</span>`;
    }

    const statRolling = document.getElementById('stat-rolling');
    if (statRolling) {
        statRolling.innerHTML = `${rolling} <span class="kpi-pct-badge">(${total ? Math.round(rolling/total*100) : 0}%)</span>`;
    }

    const statDiff = document.getElementById('stat-diff');
    if (statDiff) {
        statDiff.innerHTML = `${diff} <span class="kpi-pct-badge">(${total ? Math.round(diff/total*100) : 0}%)</span>`;
    }

    const statNihil = document.getElementById('stat-nihil');
    if (statNihil) statNihil.textContent = nihil;

    const statEdited = document.getElementById('stat-edited');
    if (statEdited) statEdited.textContent = edited;
}

function filterByStatus(statusType) {
    currentFilter = statusType;
    document.querySelectorAll('.kpi-card').forEach(c => {
        c.classList.remove('active');
        const badgeIcon = c.querySelector('.kpi-click-badge i');
        if (badgeIcon) {
            badgeIcon.className = 'fas fa-arrow-pointer';
        }
        const badge = c.querySelector('.kpi-click-badge');
        if (badge) badge.title = "Klik untuk memfilter";
    });

    const kpiAll = document.getElementById('kpi-all');
    const kpiMatch = document.getElementById('kpi-match');
    const kpiRolling = document.getElementById('kpi-rolling');
    const kpiDiff = document.getElementById('kpi-diff');
    const kpiNihil = document.getElementById('kpi-nihil');
    const kpiEdited = document.getElementById('kpi-edited');

    let activeCard = null;
    if (statusType === 'ALL') activeCard = kpiAll;
    else if (statusType === 'MATCH') activeCard = kpiMatch;
    else if (statusType === 'ROLLING') activeCard = kpiRolling;
    else if (statusType === 'DIFF') activeCard = kpiDiff;
    else if (statusType === 'NIHIL') activeCard = kpiNihil;
    else if (statusType === 'EDITED') activeCard = kpiEdited;

    if (activeCard) {
        activeCard.classList.add('active');
        const activeIcon = activeCard.querySelector('.kpi-click-badge i');
        if (activeIcon) {
            activeIcon.className = 'fas fa-check';
        }
        const badge = activeCard.querySelector('.kpi-click-badge');
        if (badge) badge.title = "Filter Aktif";
    }

    const emptyRow = document.getElementById('empty-state-row');
    if (emptyRow) emptyRow.style.display = (statusType === 'ALL') ? '' : 'none';

    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    rows.forEach(r => {
        const st = r.getAttribute('data-status');
        const isEdited = r.getAttribute('data-edited') === 'true';

        if (statusType === 'ALL') r.style.display = '';
        else if (statusType === 'EDITED') r.style.display = isEdited ? '' : 'none';
        else if (statusType === 'NIHIL') r.style.display = (st === 'NIHIL' || st === 'TRIAGE') ? '' : 'none';
        else r.style.display = (st === statusType) ? '' : 'none';
    });
}

function searchRows(query) {
    const q = query.toLowerCase();
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    const emptyRow = document.getElementById('empty-state-row');
    if (emptyRow) emptyRow.style.display = q ? 'none' : '';

    rows.forEach(r => {
        const text = r.textContent.toLowerCase();
        r.style.display = text.includes(q) ? '' : 'none';
    });
}

// INTERACTIVE HD ZOOM & PAN STATE
let currentZoom = 1;
let panX = 0;
let panY = 0;
let isPanning = false;
let startX = 0;
let startY = 0;

function applyTransform() {
    const img = document.getElementById('modal-photo-src');
    const badge = document.getElementById('zoom-badge');
    if (!img) return;
    img.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    if (badge) badge.textContent = `${Math.round(currentZoom * 100)}%`;
}

function zoomIn() {
    currentZoom = Math.min(5, Math.round((currentZoom + 0.3) * 10) / 10);
    applyTransform();
}

function zoomOut() {
    currentZoom = Math.max(0.5, Math.round((currentZoom - 0.3) * 10) / 10);
    if (currentZoom <= 1) { panX = 0; panY = 0; }
    applyTransform();
}

function resetZoom() {
    currentZoom = 1;
    panX = 0;
    panY = 0;
    applyTransform();
}

function handleWheelZoom(event) {
    event.preventDefault();
    if (event.deltaY < 0) {
        currentZoom = Math.min(5, Math.round((currentZoom + 0.2) * 10) / 10);
    } else {
        currentZoom = Math.max(0.5, Math.round((currentZoom - 0.2) * 10) / 10);
        if (currentZoom <= 1) { panX = 0; panY = 0; }
    }
    applyTransform();
}

function startPan(event) {
    if (event.button !== 0) return; // Left click only
    if (currentZoom <= 1) return;
    isPanning = true;
    startX = event.clientX - panX;
    startY = event.clientY - panY;
    const vp = document.getElementById('zoom-viewport');
    if (vp) vp.classList.add('grabbing');
}

window.addEventListener('mousemove', (event) => {
    if (!isPanning) return;
    panX = event.clientX - startX;
    panY = event.clientY - startY;
    applyTransform();
});

window.addEventListener('mouseup', () => {
    if (isPanning) {
        isPanning = false;
        const vp = document.getElementById('zoom-viewport');
        if (vp) vp.classList.remove('grabbing');
    }
});

function inspectPhoto(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    resetZoom();

    const photoImg = row.querySelector('.photo-thumbnail');
    const idpel = row.querySelector('.idpel-code').textContent;
    const nama = row.querySelector('strong').textContent;
    const stanLap = row.querySelectorAll('.input-table')[0].value;
    const stanAi = row.querySelector('.cell-argus').value;
    const statusSel = row.querySelector('.select-status');

    document.getElementById('modal-photo-src').src = photoImg.src;
    document.getElementById('modal-idpel').textContent = `${idpel} - ${nama}`;
    document.getElementById('modal-stan-lap').textContent = stanLap || '-';
    document.getElementById('modal-stan-ai').textContent = stanAi || '-';
    document.getElementById('modal-status-text').textContent = statusSel.options[statusSel.selectedIndex].text;
    document.getElementById('modal-inspector').style.display = 'flex';
}

function closeInspector() {
    const modal = document.getElementById('modal-inspector');
    if (modal) modal.style.display = 'none';
}

// GLOBAL KEYBOARD SHORTCUTS (ESC TO CLOSE INSPECTOR & MODALS)
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' || e.key === 'Esc') {
        const inspector = document.getElementById('modal-inspector');
        if (inspector && inspector.style.display !== 'none' && getComputedStyle(inspector).display !== 'none') {
            closeInspector();
            return;
        }

        const otherModals = [
            'modal-batch-complete',
            'modal-excel-result',
            'modal-duplicate',
            'modal-reset-confirm'
        ];
        otherModals.forEach(id => {
            const m = document.getElementById(id);
            if (m && m.style.display !== 'none' && getComputedStyle(m).display !== 'none') {
                m.style.display = 'none';
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', () => {
    updateKPIs();
});
