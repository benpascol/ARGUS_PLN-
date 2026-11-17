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
    let match = 0, rolling = 0, diff = 0, triage = 0, nihil = 0, edited = 0;

    rows.forEach(r => {
        const st = r.getAttribute('data-status');
        if (st === 'MATCH') match++;
        else if (st === 'ROLLING') rolling++;
        else if (st === 'DIFF') diff++;
        else if (st === 'TRIAGE') triage++;
        else if (st === 'NIHIL') nihil++;

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

    const statTriage = document.getElementById('stat-triage');
    if (statTriage) {
        statTriage.innerHTML = `${triage} <span class="kpi-pct-badge">(${total ? Math.round(triage/total*100) : 0}%)</span>`;
    }

    const statNihil = document.getElementById('stat-nihil');
    if (statNihil) {
        statNihil.innerHTML = `${nihil} <span class="kpi-pct-badge">(${total ? Math.round(nihil/total*100) : 0}%)</span>`;
    }

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
    const kpiTriage = document.getElementById('kpi-triage');
    const kpiNihil = document.getElementById('kpi-nihil');
    const kpiEdited = document.getElementById('kpi-edited');

    let activeCard = null;
    if (statusType === 'ALL') activeCard = kpiAll;
    else if (statusType === 'MATCH') activeCard = kpiMatch;
    else if (statusType === 'ROLLING') activeCard = kpiRolling;
    else if (statusType === 'DIFF') activeCard = kpiDiff;
    else if (statusType === 'TRIAGE') activeCard = kpiTriage;
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

// TABLE COLUMN SORTING STATE
let currentSortCol = null;
let currentSortDir = 'asc';

/**
 * Menyortir tabel berdasarkan kolom header yang diklik.
 * Mendukung pengurutan angka (NO, SELISIH, STAN LAP, LATENSI), teks (IDPEL, NAMA), dan prioritas status.
 */
function handleSortTable(colKey) {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr:not(#empty-state-row)'));
    if (rows.length <= 1) return;

    // Tentukan arah sort
    if (currentSortCol === colKey) {
        if (currentSortDir === 'asc') {
            currentSortDir = 'desc';
        } else {
            currentSortCol = 'no';
            currentSortDir = 'asc';
        }
    } else {
        currentSortCol = colKey;
        // Kolom selisih dan latensi default ke 'desc' agar anomali terbesar muncul paling atas
        if (colKey === 'diff' || colKey === 'latency') {
            currentSortDir = 'desc';
        } else {
            currentSortDir = 'asc';
        }
    }

    // Update UI Header Sort Icons
    document.querySelectorAll('.th-sortable').forEach(th => th.classList.remove('sorted-active'));
    document.querySelectorAll('.sort-icon i').forEach(icon => {
        icon.className = 'fas fa-sort';
    });

    const activeIcon = document.getElementById(`sort-icon-${currentSortCol}`);
    if (activeIcon) {
        const iconI = activeIcon.querySelector('i');
        if (iconI) {
            iconI.className = currentSortDir === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
        }
        const parentTh = activeIcon.closest('.th-sortable');
        if (parentTh) parentTh.classList.add('sorted-active');
    }

    // Prioritas Status
    const statusPriority = {
        'DIFF': 5,
        'ROLLING': 4,
        'TRIAGE': 3,
        'NIHIL': 2,
        'MATCH': 1,
        'PENDING': 0
    };

    rows.sort((a, b) => {
        let valA, valB;
        if (currentSortCol === 'no') {
            valA = parseInt(a.cells[0].textContent.trim(), 10) || 0;
            valB = parseInt(b.cells[0].textContent.trim(), 10) || 0;
            return currentSortDir === 'asc' ? valA - valB : valB - valA;
        } else if (currentSortCol === 'idpel') {
            valA = a.querySelector('.idpel-code') ? a.querySelector('.idpel-code').textContent.trim() : '';
            valB = b.querySelector('.idpel-code') ? b.querySelector('.idpel-code').textContent.trim() : '';
            return currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else if (currentSortCol === 'nama') {
            valA = a.querySelector('strong') ? a.querySelector('strong').textContent.trim() : '';
            valB = b.querySelector('strong') ? b.querySelector('strong').textContent.trim() : '';
            return currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else if (currentSortCol === 'stan_lap') {
            const inA = a.querySelectorAll('.input-table')[0];
            const inB = b.querySelectorAll('.input-table')[0];
            valA = inA ? parseFloat(inA.value) || 0 : 0;
            valB = inB ? parseFloat(inB.value) || 0 : 0;
            return currentSortDir === 'asc' ? valA - valB : valB - valA;
        } else if (currentSortCol === 'diff') {
            const elA = a.querySelector('.cell-diff');
            const elB = b.querySelector('.cell-diff');
            const txtA = elA ? elA.textContent.trim() : '-';
            const txtB = elB ? elB.textContent.trim() : '-';
            valA = (txtA === '-' || txtA === '') ? -999999 : Math.abs(parseFloat(txtA) || 0);
            valB = (txtB === '-' || txtB === '') ? -999999 : Math.abs(parseFloat(txtB) || 0);
            return currentSortDir === 'asc' ? valA - valB : valB - valA;
        } else if (currentSortCol === 'status') {
            const stA = a.getAttribute('data-status') || 'PENDING';
            const stB = b.getAttribute('data-status') || 'PENDING';
            valA = statusPriority[stA] !== undefined ? statusPriority[stA] : -1;
            valB = statusPriority[stB] !== undefined ? statusPriority[stB] : -1;
            return currentSortDir === 'asc' ? valA - valB : valB - valA;
        } else if (currentSortCol === 'latency') {
            const elA = a.querySelector('.cell-lat');
            const elB = b.querySelector('.cell-lat');
            valA = elA ? parseFloat(elA.textContent) || 0 : 0;
            valB = elB ? parseFloat(elB.textContent) || 0 : 0;
            return currentSortDir === 'asc' ? valA - valB : valB - valA;
        }
        return 0;
    });

    // Masukkan kembali baris yang sudah terurut ke dalam tabel
    rows.forEach(r => tbody.appendChild(r));

    // Refresh virtual pagination slice
    currentPage = 1;
    refreshTableDisplay();
}

/**
 * Memeriksa apakah baris memenuhi filter KPI dan kata kunci pencarian aktif.
 * Menjadi sumber tunggal untuk paginasi, penyaringan tabel, dan navigasi modal.
 */
function rowMatchesFilterAndSearch(row, filterKey = currentFilter, query = currentSearchQuery) {
    if (!row) return false;
    const st = row.getAttribute('data-status') || '';
    const isEdited = row.getAttribute('data-edited') === 'true';

    let passFilter = false;
    if (filterKey === 'ALL') {
        passFilter = true;
    } else if (filterKey === 'EDITED') {
        passFilter = isEdited;
    } else {
        passFilter = (st === filterKey);
    }

    if (!passFilter) return false;

    const q = (query || '').trim().toLowerCase();
    if (q && !row.textContent.toLowerCase().includes(q)) {
        return false;
    }
    return true;
}

function getMatchingTableRows() {
    const allRows = Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
    return allRows.filter(r => rowMatchesFilterAndSearch(r));
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
    const matchingRows = [];
    for (let i = 0; i < totalRows; i++) {
        const r = allRows[i];
        if (!rowMatchesFilterAndSearch(r)) {
            r.style.display = 'none';
            continue;
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
            else if (currentFilter === 'TRIAGE') filterLabel = 'Perlu Tinjau Ulang';
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
    const matchingCount = getMatchingTableRows().length;

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

function getInspectorOrderedRows(currentRow = null) {
    const filteredRows = getMatchingTableRows();
    if (!currentRow || filteredRows.includes(currentRow)) {
        return filteredRows;
    }
    return Array.from(document.querySelectorAll('#table-body tr:not(#empty-state-row)'));
}

function syncAiFeedbackCardUI(aiNotesText) {
    const cleaned = String(aiNotesText || '').trim();
    const cardAiFeedback = document.getElementById('modal-card-ai-feedback');
    if (cardAiFeedback) {
        cardAiFeedback.classList.toggle('has-ai-note', cleaned.length > 0);
    }
    const aiFeedbackStatus = document.getElementById('modal-ai-feedback-status');
    if (aiFeedbackStatus) {
        aiFeedbackStatus.textContent = cleaned.length > 0 ? 'Tersimpan ke Celengan' : '';
    }
    const clearBtn = document.getElementById('btn-clear-ai-notes');
    if (clearBtn) {
        clearBtn.style.display = cleaned.length > 0 ? 'inline-flex' : 'none';
    }

    const activeTags = cleaned
        ? cleaned.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    document.querySelectorAll('#modal-card-ai-feedback .ai-chip-btn').forEach(btn => {
        const tag = btn.getAttribute('data-ai-tag') || '';
        btn.classList.toggle('active', tag.length > 0 && activeTags.includes(tag));
    });
}

function inspectPhoto(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    const navRows = getInspectorOrderedRows(row);
    const totalCount = navRows.length;
    if (totalCount === 0) return;

    const navPos = Math.max(0, navRows.indexOf(row));
    currentInspectedRowIndex = rowIndex;

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

    // 6. Catatan Auditor (Operasional Excel PLN) & Catatan Evaluasi Model AI (Celengan 1.000)
    const inputNotes = document.getElementById('modal-input-notes');
    if (inputNotes && notesInput) {
        inputNotes.value = notesInput.value;
    }

    const aiNotesVal = row.getAttribute('data-ai-notes') || '';
    const inputAiNotes = document.getElementById('modal-input-ai-notes');
    if (inputAiNotes) {
        inputAiNotes.value = aiNotesVal;
    }
    syncAiFeedbackCardUI(aiNotesVal);

    // 7. Update Navigasi & Counter Modal (mengikuti urutan filter & sortir aktif)
    const counterBadge = document.getElementById('modal-counter-badge');
    if (counterBadge) counterBadge.textContent = `Foto #${navPos + 1} dari ${totalCount}`;

    const rowNum = document.getElementById('modal-current-row-num');
    if (rowNum) rowNum.textContent = navPos + 1;

    const totalRowNum = document.getElementById('modal-total-rows-num');
    if (totalRowNum) totalRowNum.textContent = totalCount;

    const btnPrev = document.getElementById('btn-modal-prev');
    const btnNext = document.getElementById('btn-modal-next');
    if (btnPrev) btnPrev.disabled = (navPos <= 0);
    if (btnNext) btnNext.disabled = (navPos >= totalCount - 1);

    // 8. Terapkan Tema Warna Dinamis In-Modal sesuai Vonis Audit (Neutral jika belum diaudit)
    const currentStatus = row.getAttribute('data-status') || (statusSel ? statusSel.value : 'PENDING');
    updateModalVerdictTheme(currentStatus, diff);

    const modal = document.getElementById('modal-inspector');
    if (modal) modal.style.display = 'flex';
}

/**
 * Memperbarui tema warna visual kartu pratinjau in-modal secara dinamis.
 * Jika status belum diaudit (PENDING): tampil bersih netral (tanpa warna menyolok).
 * Jika status sudah diaudit: tampil elegan sesuai vonis (Match, Rolling, Diff, Triage, Nihil).
 */
function updateModalVerdictTheme(status, diffVal) {
    const cardVerdict = document.getElementById('modal-card-verdict');
    const labelVerdict = document.getElementById('modal-card-verdict-label');
    const pill = document.getElementById('modal-verdict-pill');
    const imgBox = document.getElementById('inspector-image-container');
    const selectStatus = document.getElementById('modal-select-status');
    const diffDisplay = document.getElementById('modal-diff-display');

    const cleanStatus = (status || 'PENDING').toUpperCase();

    // Reset modifier classes
    const statusClasses = ['pending', 'match', 'rolling', 'diff', 'triage', 'nihil'];
    if (cardVerdict) {
        statusClasses.forEach(c => cardVerdict.classList.remove(`verdict-${c}`));
    }
    if (pill) {
        statusClasses.forEach(c => pill.classList.remove(`pill-${c}`));
    }
    if (imgBox) {
        statusClasses.forEach(c => imgBox.classList.remove(`accent-${c}`));
    }
    if (selectStatus) {
        statusClasses.forEach(c => selectStatus.classList.remove(`status-${c}`));
    }

    if (cleanStatus === 'PENDING') {
        if (cardVerdict) cardVerdict.classList.add('verdict-pending');
        if (labelVerdict) {
            labelVerdict.textContent = 'Vonis Audit (Belum Dievaluasi)';
            labelVerdict.style.color = 'var(--text-muted)';
        }
        if (pill) {
            pill.classList.add('pill-pending');
            pill.innerHTML = '<i class="fas fa-clock"></i> Belum Diaudit';
        }
        if (imgBox) imgBox.classList.add('accent-pending');
        if (selectStatus) selectStatus.classList.add('status-pending');
        if (diffDisplay) diffDisplay.style.color = 'var(--text-muted)';
    } else if (cleanStatus === 'MATCH') {
        if (cardVerdict) cardVerdict.classList.add('verdict-match');
        if (labelVerdict) {
            labelVerdict.textContent = 'Selisih (0 kWh) • Match Presisi';
            labelVerdict.style.color = '#166534';
        }
        if (pill) {
            pill.classList.add('pill-match');
            pill.innerHTML = '<i class="fas fa-check-circle"></i> Sesuai Match';
        }
        if (imgBox) imgBox.classList.add('accent-match');
        if (selectStatus) selectStatus.classList.add('status-match');
        if (diffDisplay) diffDisplay.style.color = '#16A34A';
    } else if (cleanStatus === 'ROLLING') {
        if (cardVerdict) cardVerdict.classList.add('verdict-rolling');
        if (labelVerdict) {
            labelVerdict.textContent = 'Selisih Transisi • Rolling Digit';
            labelVerdict.style.color = '#92400E';
        }
        if (pill) {
            pill.classList.add('pill-rolling');
            pill.innerHTML = '<i class="fas fa-sync-alt"></i> Rolling Digit';
        }
        if (imgBox) imgBox.classList.add('accent-rolling');
        if (selectStatus) selectStatus.classList.add('status-rolling');
        if (diffDisplay) diffDisplay.style.color = '#D97706';
    } else if (cleanStatus === 'DIFF') {
        if (cardVerdict) cardVerdict.classList.add('verdict-diff');
        if (labelVerdict) {
            labelVerdict.textContent = 'Anomali Angka • Beda Stand KWH';
            labelVerdict.style.color = '#991B1B';
        }
        if (pill) {
            pill.classList.add('pill-diff');
            pill.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Beda Stand';
        }
        if (imgBox) imgBox.classList.add('accent-diff');
        if (selectStatus) selectStatus.classList.add('status-diff');
        if (diffDisplay) diffDisplay.style.color = '#DC2626';
    } else if (cleanStatus === 'TRIAGE') {
        if (cardVerdict) cardVerdict.classList.add('verdict-triage');
        if (labelVerdict) {
            labelVerdict.textContent = 'Kualitas Rendah • Perlu Tinjau Ulang';
            labelVerdict.style.color = '#6B21A8';
        }
        if (pill) {
            pill.classList.add('pill-triage');
            pill.innerHTML = '<i class="fas fa-microscope"></i> Perlu Tinjau Ulang';
        }
        if (imgBox) imgBox.classList.add('accent-triage');
        if (selectStatus) selectStatus.classList.add('status-triage');
        if (diffDisplay) diffDisplay.style.color = '#7C3AED';
    } else if (cleanStatus === 'NIHIL') {
        if (cardVerdict) cardVerdict.classList.add('verdict-nihil');
        if (labelVerdict) {
            labelVerdict.textContent = 'Foto Non-Meteran • Bukan KWH / Nihil';
            labelVerdict.style.color = '#475569';
        }
        if (pill) {
            pill.classList.add('pill-nihil');
            pill.innerHTML = '<i class="fas fa-times-circle"></i> Bukan KWH / Nihil';
        }
        if (imgBox) imgBox.classList.add('accent-nihil');
        if (selectStatus) selectStatus.classList.add('status-nihil');
        if (diffDisplay) diffDisplay.style.color = '#64748B';
    }
}

function commitFocusedModalFieldIfNeeded() {
    const active = document.activeElement;
    if (!active) return;
    const fieldMap = {
        'modal-stan-lap': 'stan_lap',
        'modal-stan-ai': 'stan_ai',
        'modal-input-notes': 'notes',
        'modal-input-ai-notes': 'ai_notes'
    };
    const fieldType = fieldMap[active.id];
    if (fieldType) {
        onModalFieldChange(fieldType, active.value);
    }
}

function navigateInspector(delta) {
    if (currentInspectedRowIndex < 0) return;
    commitFocusedModalFieldIfNeeded();
    const currentRow = document.getElementById(`row-${currentInspectedRowIndex}`);
    if (!currentRow) return;

    const navRows = getInspectorOrderedRows(currentRow);
    const currentPos = navRows.indexOf(currentRow);
    if (currentPos < 0) return;

    const targetRow = navRows[currentPos + delta];
    if (!targetRow || !targetRow.id) return;

    const targetIdx = parseInt(targetRow.id.replace('row-', ''), 10);
    if (!isNaN(targetIdx)) {
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
        if (typeof evaluateRowEditedState === 'function') {
            evaluateRowEditedState(row, true);
        }
    } else if (fieldType === 'stan_ai') {
        const input = row.querySelector('.cell-argus');
        const normalized = val.trim() || '-';
        if (input) input.value = normalized;
        if (typeof recalculateRowDiffAndStatus === 'function') {
            recalculateRowDiffAndStatus(row);
        }
        if (typeof evaluateRowEditedState === 'function') {
            evaluateRowEditedState(row, true);
        }
    } else if (fieldType === 'status') {
        if (typeof applyStatusChangeToRow === 'function') {
            applyStatusChangeToRow(row, val, true);
        } else {
            const sel = row.querySelector('.select-status');
            if (sel) sel.value = val;
            row.setAttribute('data-status', val);
        }
    } else if (fieldType === 'notes') {
        const notesInput = row.querySelector('.input-notes');
        if (notesInput) notesInput.value = val.trim();
    } else if (fieldType === 'ai_notes') {
        const cleanedAiNotes = val.trim();
        row.setAttribute('data-ai-notes', cleanedAiNotes);
        syncAiFeedbackCardUI(cleanedAiNotes);
        if (typeof evaluateRowEditedState === 'function') {
            evaluateRowEditedState(row, true);
        }
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

    // Update tema visual in-modal secara real-time
    const currentStatus = row.getAttribute('data-status') || (statusSel ? statusSel.value : 'PENDING');
    updateModalVerdictTheme(currentStatus, diff);

    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function appendAiFeedbackTag(tagText) {
    const inputEl = document.getElementById('modal-input-ai-notes');
    if (!inputEl) return;

    const current = inputEl.value.trim();
    let parts = current ? current.split(',').map(s => s.trim()).filter(Boolean) : [];
    if (parts.includes(tagText)) {
        parts = parts.filter(p => p !== tagText);
    } else {
        parts.push(tagText);
    }
    inputEl.value = parts.join(', ');
    onModalFieldChange('ai_notes', inputEl.value);
}

function clearAiFeedbackNotes() {
    const inputEl = document.getElementById('modal-input-ai-notes');
    if (!inputEl) return;
    inputEl.value = '';
    onModalFieldChange('ai_notes', '');
}

function handleModalKeydown(event, fieldType) {
    if (event.key === 'Enter') {
        event.target.blur();
    }
}

function closeInspector() {
    commitFocusedModalFieldIfNeeded();
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
            'modal-reset-confirm',
            'modal-vault-manager'
        ];
        otherModals.forEach(id => {
            const m = document.getElementById(id);
            if (m && m.style.display !== 'none' && getComputedStyle(m).display !== 'none') {
                m.style.display = 'none';
            }
        });
        return;
    }

    // Keyboard Arrow navigation & Fast Verdict di dalam Modal Inspector
    if (isInspectorOpen) {
        const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditingInput = (tag === 'input' || tag === 'textarea');

        if (e.key === 'ArrowLeft' && (!isEditingInput || e.altKey)) {
            e.preventDefault();
            navigateInspector(-1);
        } else if (e.key === 'ArrowRight' && (!isEditingInput || e.altKey)) {
            e.preventDefault();
            navigateInspector(1);
        } else if (!isEditingInput && !e.ctrlKey && !e.altKey && !e.metaKey) {
            // Fast 1-click verdict hotkeys: 1=MATCH, 2=ROLLING, 3=DIFF, 4=TRIAGE, 5=NIHIL
            let targetStatus = null;
            let statusLabel = '';
            if (e.key === '1') { targetStatus = 'MATCH'; statusLabel = 'Sesuai Match'; }
            else if (e.key === '2') { targetStatus = 'ROLLING'; statusLabel = 'Rolling Digit'; }
            else if (e.key === '3') { targetStatus = 'DIFF'; statusLabel = 'Beda Stand'; }
            else if (e.key === '4') { targetStatus = 'TRIAGE'; statusLabel = 'Perlu Tinjau Ulang'; }
            else if (e.key === '5') { targetStatus = 'NIHIL'; statusLabel = 'Bukan KWH / Nihil'; }

            if (targetStatus) {
                e.preventDefault();
                onModalFieldChange('status', targetStatus);
                if (typeof showToast === 'function') {
                    showToast(`Hotkey [${e.key}]: Vonis diset ke [${statusLabel}]`, "info");
                }
            }
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
                window.ARGUS_HARDWARE_INFO = hw;
                const badge = document.getElementById('engine-hardware-badge');
                if (badge) {
                    const cleanLabel = (hw.engine_label || '').replace(/^ENGINE:\s*/i, '');
                    badge.textContent = cleanLabel || `ARGUS AI V5 (${hw.type})`;
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
    if (typeof fetchVaultStatus === 'function') fetchVaultStatus();
});
