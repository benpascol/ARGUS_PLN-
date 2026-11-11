/**
 * Module: session_store.js
 * Deskripsi: Manajemen persistensi sesi audit lokal via IndexedDB & jaring pengaman anti-refresh.
 *            Mencegah data antrean foto dan hasil koreksi hilang saat browser di-refresh.
 * Lead Engineer: Pascol
 */

const DB_NAME = 'ARGUS_LOCAL_SESSION_DB';
const DB_VERSION = 1;
const STORE_NAME = 'audit_session_data';

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

async function persistCurrentSession() {
    try {
        const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
        const sessionData = [];

        for (let i = 0; i < rows.length; i++) {
            const r = rows[i];
            const img = r.querySelector('.photo-thumbnail');
            const photoName = r.getAttribute('data-photo') || '';
            sessionData.push({
                index: i,
                idpel: r.getAttribute('data-idpel') || '',
                photo_name: photoName,
                photo_blob: r._photoBlob || null,
                photo_src: (img && img.src && !img.src.startsWith('blob:')) ? img.src : `/sample-photo/${encodeURIComponent(photoName)}`,
                nama: r.querySelector('strong') ? r.querySelector('strong').textContent : '',
                tarif_daya: r.cells[3] ? r.cells[3].textContent : '',
                stan_lapangan: r.querySelectorAll('.input-table')[0] ? r.querySelectorAll('.input-table')[0].value : '',
                raw_display: r.querySelector('.cell-raw') ? r.querySelector('.cell-raw').textContent : '-',
                stan_argus: r.querySelector('.cell-argus') ? r.querySelector('.cell-argus').value : '-',
                selisih: r.querySelector('.cell-diff') ? r.querySelector('.cell-diff').textContent : '-',
                status: r.getAttribute('data-status') || 'PENDING',
                verdict_select: r.querySelector('.select-status') ? r.querySelector('.select-status').value : 'PENDING',
                is_edited: r.getAttribute('data-edited') === 'true',
                notes: r.querySelector('.input-notes') ? r.querySelector('.input-notes').value : '',
                latensi: r.querySelector('.cell-lat') ? r.querySelector('.cell-lat').textContent : '-',
                blur: r.getAttribute('data-blur') || '0',
                glare: r.getAttribute('data-glare') || '0',
                tier: r.getAttribute('data-tier') || 'GREEN'
            });
        }

        const db = await openSessionDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.put(sessionData, 'active_session_rows');
        
        // Simpan juga kamus excel
        const excelArr = Array.from(excelRecordsMap.entries());
        store.put(excelArr, 'excel_records_map');
        store.put(currentAuditMode, 'current_audit_mode');
    } catch (err) {
        console.warn('Gagal menyimpan sesi ke IndexedDB:', err);
    }
}

async function restoreSessionOnStartup() {
    try {
        const db = await openSessionDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);

        const getRowsReq = store.get('active_session_rows');
        const getExcelReq = store.get('excel_records_map');
        const getModeReq = store.get('current_audit_mode');

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
                            resolvedSrc = URL.createObjectURL(data.photo_blob);
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
                        <td><img class="photo-thumbnail" src="${resolvedSrc}" onerror="if(!this.src.includes('/sample-photo/')){this.src='/sample-photo/' + encodeURIComponent('${data.photo_name}')}" onclick="inspectPhoto(${i})" alt="Foto Meter"></td>
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
                        <td><input type="text" class="input-notes" placeholder="Catatan auditor..." value="${data.notes || ''}" onchange="onFieldChange(${i})" onkeydown="handleRowKeydown(event, ${i}, 'notes')"></td>
                        <td class="cell-lat" style="font-family:'JetBrains Mono'; font-size:11.5px;">${data.latensi}</td>
                        <td><button class="btn-row-audit" onclick="auditSingleRow(${i})"><i class="fas fa-bolt"></i> Audit</button></td>
                    `;
                    fragment.appendChild(tr);

                    const sel = tr.querySelector('.select-status');
                    if (sel && typeof updateSelectStyle === 'function') updateSelectStyle(sel);
                    if (typeof updateRowStyle === 'function') updateRowStyle(tr);
                });

                tbody.appendChild(fragment);
                if (typeof updateKPIs === 'function') updateKPIs();
                showToast(`Sesi audit aktif (${rows.length} foto) berhasil dipulihkan otomatis dari memori lokal.`, 'info');
            }
        };
    } catch (err) {
        console.warn('Tidak ada sesi yang dipulihkan:', err);
    }
}

async function clearPersistedSession() {
    try {
        const db = await openSessionDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME).clear();
    } catch (err) {
        console.warn('Gagal membersihkan IndexedDB:', err);
    }
}

