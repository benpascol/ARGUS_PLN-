/**
 * Module: session_store.js
 * Deskripsi: Manajemen persistensi sesi audit lokal via IndexedDB & jaring pengaman anti-refresh.
 *            Mencegah data antrean foto dan hasil koreksi hilang saat browser di-refresh,
 *            sekaligus dilengkapi perlindungan Anti-OOM untuk antrean massal (>500 hingga 7.500+ foto).
 * Lead Engineer: Benedictus Pascal
 */

const DB_NAME = 'ARGUS_LOCAL_SESSION_DB_V2';
const LEGACY_DB_NAME = 'ARGUS_LOCAL_SESSION_DB';
const DB_VERSION = 1;
const STORE_NAME = 'audit_session_data';

// Batas aman penyimpanan Blob foto biner di IndexedDB:
// <= 500 foto: simpan Blob agar thumbnail instan saat refresh (F5).
// > 500 foto : simpan metadata hasil audit saja (~2 MB untuk 7.000 baris) agar RAM browser tidak OOM.
const MAX_BLOB_PERSIST_ROWS = 500;

// Jaring Pengaman Instan: Peringatan jika pengguna tidak sengaja menekan F5 / Tutup Tab
window.addEventListener('beforeunload', (e) => {
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    if (rows.length > 0) {
        e.preventDefault();
        e.returnValue = 'Antrean foto audit Anda sedang aktif. Yakin ingin memuat ulang halaman?';
        return e.returnValue;
    }
});

function openSessionDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME);
            }
        };
        req.onsuccess = (e) => resolve(e.target.result);
        req.onerror = (e) => reject(e.target.error);
    });
}

let persistDebounceTimer = null;
let isPersistingSession = false;
let persistQueuedAgain = false;

function persistCurrentSession(immediate = false) {
    // Anti-OOM Guard: Jangan tulis ulang seluruh tabel ke IndexedDB di tengah proses Audit Batch ribuan foto!
    if (window.isBatchAuditRunning && !immediate) {
        return;
    }
    if (immediate) {
        if (persistDebounceTimer) clearTimeout(persistDebounceTimer);
        persistDebounceTimer = null;
        return doPersistCurrentSession();
    }
    if (persistDebounceTimer) clearTimeout(persistDebounceTimer);
    persistDebounceTimer = setTimeout(() => {
        persistDebounceTimer = null;
        doPersistCurrentSession();
    }, 600);
}

async function doPersistCurrentSession() {
    if (isPersistingSession) {
        persistQueuedAgain = true;
        return;
    }
    isPersistingSession = true;
    let db = null;
    try {
        const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
        const totalRows = rows.length;
        const includeBlobs = totalRows <= MAX_BLOB_PERSIST_ROWS;
        const sessionData = new Array(totalRows);

        for (let i = 0; i < totalRows; i++) {
            const r = rows[i];
            const img = r.querySelector('.photo-thumbnail');
            const photoName = r.getAttribute('data-photo') || '';
            const stanInput = r.querySelectorAll('.input-table')[0];
            const argusInput = r.querySelector('.cell-argus');
            const currStanLap = stanInput ? stanInput.value : '';
            const currArgus = argusInput ? argusInput.value : '-';
            const currStatus = r.getAttribute('data-status') || 'PENDING';
            const rawEl = r.querySelector('.cell-raw');
            const diffEl = r.querySelector('.cell-diff');
            const selEl = r.querySelector('.select-status');
            const notesEl = r.querySelector('.input-notes');
            const latEl = r.querySelector('.cell-lat');
            const strongEl = r.querySelector('strong');

            sessionData[i] = {
                index: i,
                idpel: r.getAttribute('data-idpel') || '',
                photo_name: photoName,
                photo_blob: includeBlobs ? (r._photoBlob || null) : null,
                photo_src: (img && img.src && !img.src.startsWith('blob:')) ? img.src : `/sample-photo/${encodeURIComponent(photoName)}`,
                nama: strongEl ? strongEl.textContent : '',
                tarif_daya: r.cells[3] ? r.cells[3].textContent : '',
                stan_lapangan: currStanLap,
                raw_display: rawEl ? rawEl.textContent : '-',
                stan_argus: currArgus,
                selisih: diffEl ? diffEl.textContent : '-',
                status: currStatus,
                verdict_select: selEl ? selEl.value : 'PENDING',
                is_edited: r.getAttribute('data-edited') === 'true',
                orig_stan_lap: r.hasAttribute('data-orig-stan-lap') ? r.getAttribute('data-orig-stan-lap') : currStanLap,
                orig_argus: r.hasAttribute('data-orig-argus') ? r.getAttribute('data-orig-argus') : currArgus,
                orig_status: r.hasAttribute('data-orig-status') ? r.getAttribute('data-orig-status') : currStatus,
                notes: notesEl ? notesEl.value : '',
                ai_notes: r.getAttribute('data-ai-notes') || '',
                ai_prelabel_meta: r._aiPrelabelMeta || null,
                latensi: latEl ? latEl.textContent : '-',
                blur: r.getAttribute('data-blur') || '0',
                glare: r.getAttribute('data-glare') || '0',
                tier: r.getAttribute('data-tier') || 'GREEN'
            };
        }

        db = await openSessionDB();
        await new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            store.put(sessionData, 'active_session_rows');

            // Simpan juga kamus excel & mode audit aktif
            const excelArr = Array.from(excelRecordsMap.entries());
            store.put(excelArr, 'excel_records_map');
            store.put(currentAuditMode, 'current_audit_mode');

            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
            tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'));
        });
    } catch (err) {
        console.warn('Gagal menyimpan sesi ke IndexedDB:', err);
    } finally {
        if (db) {
            try { db.close(); } catch (e) {}
        }
        isPersistingSession = false;
        if (persistQueuedAgain && !window.isBatchAuditRunning) {
            persistQueuedAgain = false;
            setTimeout(() => doPersistCurrentSession(), 300);
        } else {
            persistQueuedAgain = false;
        }
    }
}

async function restoreSessionOnStartup() {
    // Self-Healing Anti-Crash Loop:
    // Hapus paksa database IndexedDB lama v1.0.0 di level storage engine TANPA membacanya ke RAM
    // (mencegah Edge langsung OOM/force-close akibat sisa blob 7.000 foto dari sesi v1.0.0).
    try {
        indexedDB.deleteDatabase(LEGACY_DB_NAME);
    } catch (e) {}

    // Escape hatch darurat: buka /dashboard?reset=1 untuk mengosongkan sesi lokal seketika
    try {
        const params = new URLSearchParams(window.location.search);
        if (params.get('reset') === '1') {
            indexedDB.deleteDatabase(DB_NAME);
            window.history.replaceState({}, document.title, window.location.pathname);
            if (typeof showToast === 'function') {
                showToast('Memori sesi browser berhasil dikosongkan.', 'info');
            }
            return;
        }
    } catch (e) {}

    let db = null;
    try {
        db = await openSessionDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);

        const getRowsReq = store.get('active_session_rows');
        const getExcelReq = store.get('excel_records_map');
        const getModeReq = store.get('current_audit_mode');

        tx.oncomplete = () => {
            if (db) {
                try { db.close(); } catch (e) {}
            }
        };

        getExcelReq.onsuccess = () => {
            const res = getExcelReq.result;
            if (res && Array.isArray(res)) {
                excelRecordsMap = new Map(res);
            }
        };

        getModeReq.onsuccess = () => {
            const m = getModeReq.result;
            if (m) {
                currentAuditMode = m;
                const sel = document.getElementById('audit-mode-select');
                if (sel) sel.value = m;
            }
        };

        getRowsReq.onsuccess = () => {
            const rows = getRowsReq.result;
            if (rows && rows.length > 0) {
                const tbody = document.getElementById('table-body');
                if (!tbody) return;
                tbody.innerHTML = ''; // bersihkan empty state

                const fragment = document.createDocumentFragment();
                rows.forEach((data, i) => {
                    const tr = document.createElement('tr');
                    tr.id = `row-${i}`;
                    tr.setAttribute('data-idpel', data.idpel);
                    tr.setAttribute('data-photo', data.photo_name);
                    tr.setAttribute('data-status', data.status);
                    tr.setAttribute('data-orig-stan-lap', data.orig_stan_lap !== undefined ? data.orig_stan_lap : (data.stan_lapangan || ''));
                    tr.setAttribute('data-orig-argus', data.orig_argus !== undefined ? data.orig_argus : (data.stan_argus || '-'));
                    tr.setAttribute('data-orig-status', data.orig_status !== undefined ? data.orig_status : (data.status || 'PENDING'));
                    tr.setAttribute('data-ai-notes', data.ai_notes || '');
                    tr._aiPrelabelMeta = data.ai_prelabel_meta || null;
                    tr.setAttribute('data-blur', data.blur);
                    tr.setAttribute('data-glare', data.glare);
                    tr.setAttribute('data-tier', data.tier);
                    if (data.is_edited) {
                        tr.setAttribute('data-edited', 'true');
                        tr.classList.add('row-edited');
                    }

                    let resolvedSrc = '';
                    if (data.photo_blob) {
                        try {
                            tr._photoBlob = data.photo_blob;
                            if (typeof createTrackedObjectURL === 'function') {
                                resolvedSrc = createTrackedObjectURL(data.photo_blob);
                            } else {
                                resolvedSrc = URL.createObjectURL(data.photo_blob);
                            }
                            tr._trackedUrl = resolvedSrc;
                        } catch (e) {
                            resolvedSrc = `/sample-photo/${encodeURIComponent(data.photo_name)}`;
                        }
                    } else if (data.photo_src && !data.photo_src.startsWith('blob:')) {
                        resolvedSrc = data.photo_src;
                    } else {
                        resolvedSrc = `/sample-photo/${encodeURIComponent(data.photo_name)}`;
                    }

                    tr.innerHTML = `
                        <td>${i + 1}</td>
                        <td class="idpel-code">${data.idpel}</td>
                        <td><strong>${data.nama}</strong></td>
                        <td>${data.tarif_daya}</td>
                        <td><input type="text" class="input-table" value="${data.stan_lapangan}" onchange="onFieldChange(${i})" onkeydown="handleRowKeydown(event, ${i}, 'stan_lap')"></td>
                        <td><img class="photo-thumbnail" loading="lazy" src="${resolvedSrc}" onerror="if(!this.src.includes('/sample-photo/')){this.src='/sample-photo/' + encodeURIComponent('${data.photo_name}')}" onclick="inspectPhoto(${i})" alt="Foto Meter"></td>
                        <td class="cell-raw" style="font-family:'JetBrains Mono';">${data.raw_display}</td>
                        <td>
                            <input type="text" class="input-table ai-field cell-argus" value="${data.stan_argus}" onchange="onArgusChange(${i})" onkeydown="handleRowKeydown(event, ${i}, 'argus')">
                            <div class="edit-badge-slot">${data.is_edited ? '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>' : ''}</div>
                        </td>
                        <td class="cell-diff" style="font-family:'JetBrains Mono'; font-weight:700;">${data.selisih}</td>
                        <td>
                            <select class="select-status" onchange="onStatusSelectChange(${i}, this)">
                                <option value="PENDING" ${data.verdict_select === 'PENDING' ? 'selected' : ''}>Belum Diaudit</option>
                                <option value="MATCH" ${data.verdict_select === 'MATCH' ? 'selected' : ''}>Sesuai Match</option>
                                <option value="ROLLING" ${data.verdict_select === 'ROLLING' ? 'selected' : ''}>Rolling Digit</option>
                                <option value="DIFF" ${data.verdict_select === 'DIFF' ? 'selected' : ''}>Beda Stand</option>
                                <option value="NIHIL" ${data.verdict_select === 'NIHIL' ? 'selected' : ''}>Bukan KWH / Nihil</option>
                                <option value="TRIAGE" ${data.verdict_select === 'TRIAGE' ? 'selected' : ''}>Perlu Tinjau Ulang</option>
                            </select>
                        </td>
                        <td>
                            <input type="text" class="input-notes" placeholder="Catatan auditor..." value="" onchange="onFieldChange(${i}, 'notes')" onkeydown="handleRowKeydown(event, ${i}, 'notes')">
                            <div class="ai-note-badge-slot"></div>
                        </td>
                        <td class="cell-lat" style="font-family:'JetBrains Mono'; font-size:11.5px;">${data.latensi}</td>
                        <td><button class="btn-row-audit" onclick="auditSingleRow(${i})"><i class="fas fa-bolt"></i> Audit</button></td>
                    `;

                    const restoredStanInput = tr.querySelectorAll('.input-table')[0];
                    if (restoredStanInput) restoredStanInput.value = data.stan_lapangan || '';
                    const restoredArgusInput = tr.querySelector('.cell-argus');
                    if (restoredArgusInput) restoredArgusInput.value = data.stan_argus || '-';
                    const restoredNotesInput = tr.querySelector('.input-notes');
                    if (restoredNotesInput) restoredNotesInput.value = data.notes || '';
                    if (typeof evaluateRowEditedState === 'function') {
                        evaluateRowEditedState(tr, false);
                    }
                    fragment.appendChild(tr);

                    const sel = tr.querySelector('.select-status');
                    if (sel && typeof updateSelectStyle === 'function') updateSelectStyle(sel);
                    if (typeof updateRowStyle === 'function') updateRowStyle(tr);
                });

                tbody.appendChild(fragment);
                if (typeof updateKPIs === 'function') updateKPIs();
                if (typeof refreshTableDisplay === 'function') refreshTableDisplay();
                showToast(`Sesi audit aktif (${rows.length} foto) berhasil dipulihkan otomatis dari memori lokal.`, 'info');
            }
        };
    } catch (err) {
        if (db) {
            try { db.close(); } catch (e) {}
        }
        console.warn('Tidak ada sesi yang dipulihkan:', err);
    }
}

async function clearPersistedSession() {
    let db = null;
    try {
        db = await openSessionDB();
        await new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            tx.objectStore(STORE_NAME).clear();
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    } catch (err) {
        console.warn('Gagal membersihkan IndexedDB:', err);
    } finally {
        if (db) {
            try { db.close(); } catch (e) {}
        }
    }
}
