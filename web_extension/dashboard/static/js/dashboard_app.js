/**
 * Module: dashboard_app.js
 * Deskripsi: State management, filtering kartu KPI, pencarian tabel,
 *            Enterprise Pagination & Virtual Slicing, modal inspector verifikasi HD,
 *            dan inisialisasi antarmuka utama.
 * Lead Engineer: Benedictus Pascal
 */

let currentFilter = 'ALL';
let currentSearchQuery = '';
let currentPage = 1;
let pageSize = 50;
let currentInspectedRowIndex = -1;

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

    currentPage = 1;
    refreshTableDisplay();
}

function searchRows(query) {
    currentSearchQuery = query;
    currentPage = 1;
    refreshTableDisplay();
}

function handleSearchInput(query) {
    const clearBtn = document.getElementById('btn-search-clear');
    if (clearBtn) {
        clearBtn.style.display = query ? 'inline-flex' : 'none';
    }
    searchRows(query);
}

function clearSearchInput() {
    const input = document.getElementById('search-input');
    if (input) {
        input.value = '';
        input.focus();
    }
    const clearBtn = document.getElementById('btn-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    searchRows('');
}

function handlePageJumpKeydown(event, inputEl) {
    if (event.key === 'Enter') {
        const targetPage = parseInt(inputEl.value, 10);
        if (!isNaN(targetPage)) {
            goToPage(targetPage);
        }
        inputEl.blur();
    }
}

function handlePageJumpChange(inputEl) {
    const targetPage = parseInt(inputEl.value, 10);
    if (!isNaN(targetPage)) {
        goToPage(targetPage);
    }
}

/**
 * Enterprise Virtual Slicing & Pagination
 * Menggabungkan filter status kartu KPI, kata kunci pencarian,
 * dan pembagian halaman (pagination) dalam 1 alur terpadu secepat kilat (<1ms).
 */
function refreshTableDisplay() {
    const allRows = Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
    const totalRows = allRows.length;
    const emptyRow = document.getElementById('empty-state-row');

    if (totalRows === 0) {
        if (emptyRow) emptyRow.style.display = '';
        updatePaginationUI(0, 0, 0, 1, 1);
        return;
    }

    if (emptyRow) emptyRow.style.display = 'none';

    // 1. Tentukan baris yang lolos filter status dan kata kunci pencarian
    const q = (currentSearchQuery || '').trim().toLowerCase();
    const matchingRows = [];

    for (let i = 0; i < totalRows; i++) {
        const r = allRows[i];
        const st = r.getAttribute('data-status') || '';
        const isEdited = r.getAttribute('data-edited') === 'true';

        // Filter status matching
        let passFilter = false;
        if (currentFilter === 'ALL') {
            passFilter = true;
        } else if (currentFilter === 'EDITED') {
            passFilter = isEdited;
        } else if (currentFilter === 'NIHIL') {
            passFilter = (st === 'NIHIL' || st === 'TRIAGE');
        } else {
            passFilter = (st === currentFilter);
        }

        if (!passFilter) {
            r.style.display = 'none';
            continue;
        }

        // Search text matching
        if (q) {
            const text = r.textContent.toLowerCase();
            if (!text.includes(q)) {
                r.style.display = 'none';
                continue;
            }
        }

        matchingRows.push(r);
    }

    const totalMatching = matchingRows.length;
    const effectivePageSize = (pageSize === 'ALL' || pageSize >= 999999) ? (totalMatching || 1) : parseInt(pageSize, 10);
    const totalPages = Math.max(1, Math.ceil(totalMatching / effectivePageSize));

    // Clamp current page
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIndex = (currentPage - 1) * effectivePageSize;
    const endIndex = Math.min(startIndex + effectivePageSize, totalMatching);

    // 2. Terapkan Virtual Slicing: Hanya baris pada slice halaman aktif yang di-render (display: '')
    for (let m = 0; m < totalMatching; m++) {
        const row = matchingRows[m];
        if (m >= startIndex && m < endIndex) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }

    const startDisplay = totalMatching === 0 ? 0 : startIndex + 1;
    const endDisplay = endIndex;
    updatePaginationUI(startDisplay, endDisplay, totalMatching, currentPage, totalPages);
}

function updatePaginationUI(start, end, total, page, totalPages) {
    const elStart = document.getElementById('page-start');
    const elEnd = document.getElementById('page-end');
    const elTotal = document.getElementById('page-total');
    const elCurrentPage = document.getElementById('current-page-num');
    const elTotalPages = document.getElementById('total-pages-num');

    if (elStart) elStart.textContent = start;
    if (elEnd) elEnd.textContent = end;
    if (elTotal) elTotal.textContent = total;
    if (elCurrentPage) elCurrentPage.textContent = page;
    if (elTotalPages) elTotalPages.textContent = totalPages;

    const jumpInput = document.getElementById('page-jump-input');
    if (jumpInput) {
        jumpInput.value = page;
        jumpInput.max = totalPages;
        jumpInput.disabled = (total === 0);
    }

    const btnFirst = document.getElementById('btn-page-first');
    const btnPrev = document.getElementById('btn-page-prev');
    const btnNext = document.getElementById('btn-page-next');
    const btnLast = document.getElementById('btn-page-last');

    if (btnFirst) btnFirst.disabled = (page <= 1 || total === 0);
    if (btnPrev) btnPrev.disabled = (page <= 1 || total === 0);
    if (btnNext) btnNext.disabled = (page >= totalPages || total === 0);
    if (btnLast) btnLast.disabled = (page >= totalPages || total === 0);

    // Update filter badge info
    const badge = document.getElementById('pagination-filter-badge');
    if (badge) {
        if (currentFilter !== 'ALL' || currentSearchQuery) {
            let filterLabel = currentFilter;
            if (currentFilter === 'MATCH') filterLabel = 'Sesuai Match';
            else if (currentFilter === 'ROLLING') filterLabel = 'Rolling Digit';
            else if (currentFilter === 'DIFF') filterLabel = 'Beda Stand';
            else if (currentFilter === 'NIHIL') filterLabel = 'Bukan KWH / Nihil';
            else if (currentFilter === 'EDITED') filterLabel = 'Dikoreksi';

            let text = `Filter: ${filterLabel}`;
            if (currentSearchQuery) text += ` • Cari: "${currentSearchQuery}"`;
            badge.textContent = text;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function goToPage(action) {
    const allRows = Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
    const q = (currentSearchQuery || '').trim().toLowerCase();
    let matchingCount = 0;
    for (let i = 0; i < allRows.length; i++) {
        const r = allRows[i];
        const st = r.getAttribute('data-status') || '';
        const isEdited = r.getAttribute('data-edited') === 'true';
        let passFilter = (currentFilter === 'ALL') ||
                         (currentFilter === 'EDITED' && isEdited) ||
                         (currentFilter === 'NIHIL' && (st === 'NIHIL' || st === 'TRIAGE')) ||
                         (st === currentFilter);
        if (!passFilter) continue;
        if (q && !r.textContent.toLowerCase().includes(q)) continue;
        matchingCount++;
    }

    const effectivePageSize = (pageSize === 'ALL' || pageSize >= 999999) ? (matchingCount || 1) : parseInt(pageSize, 10);
    const totalPages = Math.max(1, Math.ceil(matchingCount / effectivePageSize));

    if (action === 'first') {
        currentPage = 1;
    } else if (action === 'prev') {
        if (currentPage > 1) currentPage--;
    } else if (action === 'next') {
        if (currentPage < totalPages) currentPage++;
    } else if (action === 'last') {
        currentPage = totalPages;
    } else if (typeof action === 'number') {
        currentPage = Math.max(1, Math.min(action, totalPages));
    }

    refreshTableDisplay();

    // Scroll table container smoothly to top when page changes
    const scrollBox = document.querySelector('.table-scroll');
    if (scrollBox) scrollBox.scrollTop = 0;
}

function changePageSize(newSize) {
    pageSize = (newSize === 'ALL') ? 'ALL' : parseInt(newSize, 10);
    currentPage = 1;
    refreshTableDisplay();

    const scrollBox = document.querySelector('.table-scroll');
    if (scrollBox) scrollBox.scrollTop = 0;
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
    const allRows = Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
    const totalCount = allRows.length;
    if (totalCount === 0) return;

    // Clamp index
    if (rowIndex < 0) rowIndex = 0;
    if (rowIndex >= totalCount) rowIndex = totalCount - 1;

    currentInspectedRowIndex = rowIndex;
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    resetZoom();

    const photoImg = row.querySelector('.photo-thumbnail');
    const idpel = row.querySelector('.idpel-code') ? row.querySelector('.idpel-code').textContent.trim() : '-';
    const nama = row.querySelector('strong') ? row.querySelector('strong').textContent.trim() : '-';
    const tarifDaya = row.cells[3] ? row.cells[3].textContent.trim() : '-';
    const stanLap = row.querySelectorAll('.input-table')[0] ? row.querySelectorAll('.input-table')[0].value.trim() : '';
    const rawAi = row.querySelector('.cell-raw') ? row.querySelector('.cell-raw').textContent.trim() : '-';
    const stanAi = row.querySelector('.cell-argus') ? row.querySelector('.cell-argus').value.trim() : '';
    const diff = row.querySelector('.cell-diff') ? row.querySelector('.cell-diff').textContent.trim() : '-';
    const statusSel = row.querySelector('.select-status');
    const notesInput = row.querySelector('.input-notes');
    const isEdited = row.getAttribute('data-edited') === 'true';

    // 1. Tampilkan Foto Resolusi Penuh
    const modalPhoto = document.getElementById('modal-photo-src');
    if (modalPhoto && photoImg) modalPhoto.src = photoImg.src;

    // 2. Tampilkan Info Pelanggan
    const elIdpel = document.getElementById('modal-idpel');
    if (elIdpel) elIdpel.textContent = `${idpel} • ${nama}`;

    const elTarif = document.getElementById('modal-tarif-daya');
    if (elTarif) elTarif.textContent = `Tarif / Daya: ${tarifDaya}`;

    // 3. Stan Lapangan (Editable)
    const inputStanLap = document.getElementById('modal-stan-lap');
    if (inputStanLap) inputStanLap.value = (stanLap === '-' ? '' : stanLap);

    // 4. Raw AI & Stan Baca AI (Editable)
    const elRaw = document.getElementById('modal-raw-display');
    if (elRaw) elRaw.textContent = rawAi;

    const inputStanAi = document.getElementById('modal-stan-ai');
    if (inputStanAi) inputStanAi.value = (stanAi === '-' ? '' : stanAi);

    const elTagSlot = document.getElementById('modal-edit-tag-slot');
    if (elTagSlot) {
        elTagSlot.innerHTML = isEdited ? '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>' : '';
    }

    // 5. Selisih kWh & Vonis Audit (Editable)
    const elDiff = document.getElementById('modal-diff-display');
    if (elDiff) {
        elDiff.textContent = (diff === '-' || diff === '' ? '-' : `${diff} kWh`);
        if (diff === '0') elDiff.style.color = '#16A34A';
        else if (diff !== '-' && diff !== '') elDiff.style.color = '#DC2626';
        else elDiff.style.color = 'var(--text-heading)';
    }

    const modalStatusSel = document.getElementById('modal-select-status');
    if (modalStatusSel && statusSel) {
        modalStatusSel.value = statusSel.value;
    }

    // 6. Catatan Auditor (Editable)
    const inputNotes = document.getElementById('modal-input-notes');
    if (inputNotes && notesInput) {
        inputNotes.value = notesInput.value;
    }

    // 7. Update Navigasi & Counter Modal
    const counterBadge = document.getElementById('modal-counter-badge');
    if (counterBadge) counterBadge.textContent = `Foto #${rowIndex + 1} dari ${totalCount}`;

    const rowNum = document.getElementById('modal-current-row-num');
    if (rowNum) rowNum.textContent = rowIndex + 1;

    const totalRowNum = document.getElementById('modal-total-rows-num');
    if (totalRowNum) totalRowNum.textContent = totalCount;

    const btnPrev = document.getElementById('btn-modal-prev');
    const btnNext = document.getElementById('btn-modal-next');
    if (btnPrev) btnPrev.disabled = (rowIndex <= 0);
    if (btnNext) btnNext.disabled = (rowIndex >= totalCount - 1);

    const modal = document.getElementById('modal-inspector');
    if (modal) modal.style.display = 'flex';
}

function navigateInspector(delta) {
    if (currentInspectedRowIndex < 0) return;
    const allRows = Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
    const targetIdx = currentInspectedRowIndex + delta;
    if (targetIdx >= 0 && targetIdx < allRows.length) {
        inspectPhoto(targetIdx);
    }
}

function onModalFieldChange(fieldType, val) {
    if (currentInspectedRowIndex < 0) return;
    const row = document.getElementById(`row-${currentInspectedRowIndex}`);
    if (!row) return;

    if (fieldType === 'stan_lap') {
        const input = row.querySelectorAll('.input-table')[0];
        if (input) input.value = val.trim();
        if (typeof recalculateRowDiffAndStatus === 'function') {
            recalculateRowDiffAndStatus(row);
        }
    } else if (fieldType === 'stan_ai') {
        const input = row.querySelector('.cell-argus');
        if (input) input.value = val.trim();
        if (typeof markRowAsEdited === 'function') {
            markRowAsEdited(row);
        }
        if (typeof recalculateRowDiffAndStatus === 'function') {
            recalculateRowDiffAndStatus(row);
        }
    } else if (fieldType === 'status') {
        const sel = row.querySelector('.select-status');
        if (sel) {
            sel.value = val;
            if (typeof updateSelectStyle === 'function') updateSelectStyle(sel);
            if (typeof markRowAsEdited === 'function') markRowAsEdited(row);
            if (typeof updateRowStyle === 'function') updateRowStyle(row);
        }
    } else if (fieldType === 'notes') {
        const notesInput = row.querySelector('.input-notes');
        if (notesInput) notesInput.value = val.trim();
    }

    // Sinkronisasi balik tampilan in-modal secara real-time
    const diff = row.querySelector('.cell-diff') ? row.querySelector('.cell-diff').textContent.trim() : '-';
    const elDiff = document.getElementById('modal-diff-display');
    if (elDiff) {
        elDiff.textContent = (diff === '-' || diff === '' ? '-' : `${diff} kWh`);
        if (diff === '0') elDiff.style.color = '#16A34A';
        else if (diff !== '-' && diff !== '') elDiff.style.color = '#DC2626';
        else elDiff.style.color = 'var(--text-heading)';
    }

    const isEdited = row.getAttribute('data-edited') === 'true';
    const elTagSlot = document.getElementById('modal-edit-tag-slot');
    if (elTagSlot) {
        elTagSlot.innerHTML = isEdited ? '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>' : '';
    }

    const statusSel = row.querySelector('.select-status');
    const modalStatusSel = document.getElementById('modal-select-status');
    if (modalStatusSel && statusSel && modalStatusSel.value !== statusSel.value) {
        modalStatusSel.value = statusSel.value;
    }

    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function handleModalKeydown(event, fieldType) {
    if (event.key === 'Enter') {
        event.target.blur();
    }
}

function closeInspector() {
    const modal = document.getElementById('modal-inspector');
    if (modal) modal.style.display = 'none';
}

// GLOBAL KEYBOARD SHORTCUTS (ESC TO CLOSE INSPECTOR & MODALS, ARROW KEYS TO NAVIGATE)
document.addEventListener('keydown', (e) => {
    const inspector = document.getElementById('modal-inspector');
    const isInspectorOpen = (inspector && inspector.style.display !== 'none' && getComputedStyle(inspector).display !== 'none');

    if (e.key === 'Escape' || e.key === 'Esc') {
        if (isInspectorOpen) {
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
        return;
    }

    // Keyboard Arrow navigation di dalam Modal Inspector
    if (isInspectorOpen) {
        const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditingInput = (tag === 'input' || tag === 'textarea' || tag === 'select');

        if (e.key === 'ArrowLeft' && (!isEditingInput || e.altKey)) {
            e.preventDefault();
            navigateInspector(-1);
        } else if (e.key === 'ArrowRight' && (!isEditingInput || e.altKey)) {
            e.preventDefault();
            navigateInspector(1);
        }
    }
});

// DETEKSI OTOMATIS HARDWARE GPU / CPU RIIL DARI BACKEND
async function fetchSystemHardwareInfo() {
    try {
        const resp = await fetch('/api/system-info');
        if (resp.ok) {
            const data = await resp.json();
            const hw = data.hardware;
            if (hw) {
                const badge = document.getElementById('engine-hardware-badge');
                if (badge) {
                    badge.textContent = hw.engine_label || `ENGINE: ARGUS AI V5 (${hw.type})`;
                }
                const batchLabel = document.getElementById('batch-progress-label');
                if (batchLabel) {
                    batchLabel.textContent = `Memproses Batch AI (${hw.device_name})...`;
                }
                if (hw.concurrency) {
                    window.BATCH_CONCURRENCY = hw.concurrency;
                }
            }
        }
    } catch (e) {
        console.warn('Gagal memuat info hardware dari API:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateKPIs();
    if (typeof refreshTableDisplay === 'function') refreshTableDisplay();
    fetchSystemHardwareInfo();
});
