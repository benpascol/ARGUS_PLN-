/**
 * Module: upload_handler.js
 * Deskripsi: Penanganan unggah berkas dual-mode (folder/file), ekstraksi IDPEL,
 *            jaring pengaman anti-duplikasi foto (Deduplication Guard),
 *            serta mekanisme pemasangan otomatis rekap ACMT Excel (Auto-Pairing).
 * Lead Engineer: Benedictus Pascal
 */

// Global State
let excelRecordsMap = new Map(); // Map IDPEL -> { nama, tarif, daya, tarif_daya, stan_lapangan, nama_file, alamat }
let currentAuditMode = 'AUTO'; // 'AUTO', 'MANDIRI', 'KOMPARASI'

// Object URL Tracking & Memory Optimization (Anti-Memory Leak)
window._activeObjectUrls = window._activeObjectUrls || new Set();

function createTrackedObjectURL(blob) {
    const url = URL.createObjectURL(blob);
    window._activeObjectUrls.add(url);
    return url;
}

function revokeAllObjectURLs() {
    if (window._activeObjectUrls && window._activeObjectUrls.size > 0) {
        window._activeObjectUrls.forEach(url => {
            try { URL.revokeObjectURL(url); } catch (e) {}
        });
        window._activeObjectUrls.clear();
    }
}

// Toast Notification System
function showToast(message, type = 'info') {
    const box = document.getElementById('toast-box');
    if (!box) return;
    const item = document.createElement('div');
    item.className = `toast-item toast-${type}`;
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    else if (type === 'warning') icon = 'exclamation-triangle';
    else if (type === 'danger') icon = 'times-circle';
    item.innerHTML = `<i class="fas fa-${icon}" style="font-size:15px;"></i><span>${message}</span>`;
    box.appendChild(item);
    setTimeout(() => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(100%)';
        item.style.transition = 'all 0.3s ease';
        setTimeout(() => item.remove(), 300);
    }, 3500);
}

// Helper to extract clean IDPEL from filename (bukan random number)
function extractIdpelFromFilename(filename) {
    // Pattern 1: match 5145 followed by 7-8 digits (standard PLN UP3 Mojokerto)
    const m = filename.match(/(?:^|\D)(5145\d{7,8})(?:\D|$)/);
    if (m) return m[1];
    // Pattern 2: any 11-12 consecutive digits
    const m2 = filename.match(/\b\d{11,12}\b/);
    if (m2) return m2[0];
    // Fallback: sanitized clean base filename
    return filename.replace(/\.[^/.]+$/, "").substring(0, 16);
}

// SOLUSI 2: Engine Impor Rekap ACMT & Auto-Pairing
async function handleExcelUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const btn = document.getElementById('btn-upload-excel');
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Mengimpor ACMT...';
    }

    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/parse-acmt-excel', {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `Gagal membaca berkas Excel (HTTP ${resp.status})`);
        }

        const data = await resp.json();
        const records = data.records || [];

        let matchedPhotos = 0;
        records.forEach(rec => {
            if (rec.idpel) excelRecordsMap.set(rec.idpel, rec);
            if (rec.nama_file) excelRecordsMap.set(rec.nama_file, rec);
        });

        // Auto-pairing dengan foto yang sudah ada di tabel
        const rows = document.querySelectorAll('#table-body tr');
        rows.forEach(row => {
            const idpel = row.getAttribute('data-idpel');
            const photoName = row.getAttribute('data-photo') || '';
            const rec = excelRecordsMap.get(idpel) || excelRecordsMap.get(photoName.replace(/\.[^/.]+$/, ""));

            if (rec) {
                matchedPhotos++;
                // Update nama pelanggan
                const strong = row.querySelector('strong');
                if (strong && rec.nama) strong.textContent = rec.nama;

                // Update tarif / daya (kolom ke-4)
                if (row.cells[3] && rec.tarif_daya) {
                    row.cells[3].textContent = rec.tarif_daya;
                }

                // Update Stan Lapangan & perbarui baseline asli agar impor Excel tidak dianggap koreksi auditor
                const stanInput = row.querySelectorAll('.input-table')[0];
                if (stanInput && rec.stan_lapangan) {
                    stanInput.value = rec.stan_lapangan;
                    row.setAttribute('data-orig-stan-lap', rec.stan_lapangan);
                }

                // Jika baris sudah pernah diaudit, hitung ulang selisih dan evaluasi baseline
                if (row.getAttribute('data-status') !== 'PENDING' && typeof recalculateRowDiffAndStatus === 'function') {
                    recalculateRowDiffAndStatus(row);
                    if (typeof evaluateRowEditedState === 'function') {
                        evaluateRowEditedState(row, false);
                    }
                }
            }
        });

        showToast(`Berhasil membaca ${records.length} data ACMT. ${matchedPhotos} foto berhasil dipasangkan otomatis!`, "success");
        
        // Tampilkan modal hasil impor Excel yang informatif (UX 3)
        const resFn = document.getElementById('excel-res-filename');
        const resTot = document.getElementById('excel-res-total');
        const resMat = document.getElementById('excel-res-matched');
        const resModal = document.getElementById('modal-excel-result');

        if (resFn) resFn.textContent = `Berkas: ${file.name}`;
        if (resTot) resTot.textContent = `${records.length.toLocaleString('id-ID')} Baris Data`;
        if (resMat) resMat.textContent = `${matchedPhotos} Foto Terpasang`;
        if (resModal) resModal.style.display = 'flex';

        if (typeof updateKPIs === 'function') updateKPIs();
        if (typeof persistCurrentSession === 'function') persistCurrentSession();
    } catch (err) {
        console.error('Error importing ACMT Excel:', err);
        showToast(`Gagal impor ACMT: ${err.message}`, "danger");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
        event.target.value = '';
    }
}

function closeExcelModal() {
    const modal = document.getElementById('modal-excel-result');
    if (modal) modal.style.display = 'none';
}

// SOLUSI 3: Pemilihan Mode Audit
function changeAuditMode(mode) {
    currentAuditMode = mode;
    let label = 'Auto (Sesuai Ketersediaan Data)';
    if (mode === 'MANDIRI') label = 'Ekstraksi Mandiri (Murni AI - Tanpa Rekap Lapangan)';
    else if (mode === 'KOMPARASI') label = 'Komparasi Rekap ACMT Lapangan';

    showToast(`Mode audit beralih ke: ${label}`, "info");

    // Hitung ulang baris yang sudah terisi stan ARGUS
    const rows = document.querySelectorAll('#table-body tr');
    rows.forEach(row => {
        if (row.getAttribute('data-status') !== 'PENDING' && typeof recalculateRowDiffAndStatus === 'function') {
            recalculateRowDiffAndStatus(row);
        }
    });
    if (typeof updateKPIs === 'function') updateKPIs();
}

let pendingUploadData = null;

function handleFolderUpload(event) {
    const files = Array.from(event.target.files || []);
    processIncomingFiles(files, "folder");
    event.target.value = '';
}

function handleFileUpload(event) {
    const files = Array.from(event.target.files || []);
    processIncomingFiles(files, "file");
    event.target.value = '';
}

function processIncomingFiles(files, source) {
    // Filter image files only
    const imageFiles = files.filter(f => f.type.startsWith('image/') || /\.(jpe?g|png|webp|bmp)$/i.test(f.name));
    if (imageFiles.length === 0) {
        showToast("Tidak ada berkas gambar yang valid ditemukan.", "warning");
        return;
    }

    // Map existing photos in table
    const existingRows = document.querySelectorAll('#table-body tr');
    const existingPhotoMap = new Map();
    existingRows.forEach(r => {
        const photoName = r.getAttribute('data-photo');
        if (photoName) existingPhotoMap.set(photoName, r);
    });

    const newFiles = [];
    const duplicateFiles = [];

    imageFiles.forEach(file => {
        if (existingPhotoMap.has(file.name)) {
            duplicateFiles.push({ file, existingRow: existingPhotoMap.get(file.name) });
        } else {
            newFiles.push(file);
        }
    });

    if (duplicateFiles.length > 0) {
        pendingUploadData = { newFiles, duplicateFiles };
        const desc = document.getElementById('dup-modal-desc');
        if (desc) {
            desc.textContent = `Terdeteksi ${duplicateFiles.length} foto duplikat dan ${newFiles.length} foto baru.`;
        }
        const modal = document.getElementById('modal-duplicate');
        if (modal) modal.style.display = 'flex';
    } else {
        appendFilesToTable(newFiles);
        showToast(`Berhasil menambahkan ${newFiles.length} foto ke antrean audit.`, "success");
    }
}

function resolveDuplicateAction(action) {
    const modal = document.getElementById('modal-duplicate');
    if (modal) modal.style.display = 'none';
    if (!pendingUploadData) return;

    const { newFiles, duplicateFiles } = pendingUploadData;

    if (action === 'overwrite') {
        // Update duplicates
        duplicateFiles.forEach(item => {
            const r = item.existingRow;
            const photoImg = r.querySelector('.photo-thumbnail');
            if (r._trackedUrl) {
                try { URL.revokeObjectURL(r._trackedUrl); } catch (e) {}
                window._activeObjectUrls.delete(r._trackedUrl);
            }
            const objectUrl = createTrackedObjectURL(item.file);
            r._trackedUrl = objectUrl;
            r._photoBlob = item.file;
            photoImg.src = objectUrl;
            photoImg.loading = "lazy";
            photoImg.setAttribute('onerror', `if(!this.src.includes('/sample-photo/')){this.src='/sample-photo/' + encodeURIComponent('${item.file.name}')}`);
            r.setAttribute('data-photo', item.file.name);
            r.setAttribute('data-status', 'PENDING');
            r.setAttribute('data-orig-stan-lap', stanInputVal);
            r.setAttribute('data-orig-argus', '-');
            r.setAttribute('data-orig-status', 'PENDING');
            r.setAttribute('data-ai-notes', '');
            r.removeAttribute('data-edited');
            r.classList.remove('row-edited');
            r._aiPrelabelMeta = null;
            r.querySelector('.cell-raw').textContent = '-';
            r.querySelector('.cell-argus').value = '-';
            r.querySelector('.cell-diff').textContent = '-';
            r.querySelector('.cell-lat').textContent = '-';
            const editSlot = r.querySelector('.edit-badge-slot');
            if (editSlot) editSlot.innerHTML = '';
            const aiSlot = r.querySelector('.ai-note-badge-slot');
            if (aiSlot) aiSlot.innerHTML = '';
            const sel = r.querySelector('.select-status');
            sel.value = 'PENDING';
            if (typeof updateSelectStyle === 'function') updateSelectStyle(sel);
            if (typeof updateRowStyle === 'function') updateRowStyle(r);
        });
        appendFilesToTable(newFiles);
        showToast(`Berhasil menimpa ${duplicateFiles.length} foto dan menambahkan ${newFiles.length} foto baru.`, "success");
    } else {
        // Skip duplicates
        appendFilesToTable(newFiles);
        showToast(`Berhasil menambahkan ${newFiles.length} foto baru (${duplicateFiles.length} duplikat dilewati).`, "info");
    }

    pendingUploadData = null;
}

function appendFilesToTable(files) {
    if (!files || files.length === 0) return;
    const tbody = document.getElementById('table-body');

    // Hapus empty state row jika masih ada
    const emptyRow = document.getElementById('empty-state-row');
    if (emptyRow) emptyRow.remove();

    let currentCount = tbody.querySelectorAll('tr:not(#empty-state-row)').length;

    const fragment = document.createDocumentFragment();

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const rowIdx = currentCount + i;
        const idpel = extractIdpelFromFilename(file.name);
        const objectUrl = createTrackedObjectURL(file);

        // Auto-pairing jika file Excel ACMT sudah pernah diunggah lebih dulu
        const excelData = excelRecordsMap.get(idpel) || excelRecordsMap.get(file.name.replace(/\.[^/.]+$/, ""));
        const namaDisplay = excelData && excelData.nama ? excelData.nama : file.name.replace(/\.[^/.]+$/, "").substring(0, 20);
        const tarifDayaDisplay = excelData && excelData.tarif_daya ? excelData.tarif_daya : 'R1 / 900 VA';
        const stanLapValue = (excelData && excelData.stan_lapangan !== undefined && excelData.stan_lapangan !== '') ? excelData.stan_lapangan : '-';

        const newRow = document.createElement('tr');
        newRow.id = `row-${rowIdx}`;
        newRow._photoBlob = file;
        newRow._trackedUrl = objectUrl;
        newRow.setAttribute('data-idpel', idpel);
        newRow.setAttribute('data-photo', file.name);
        newRow.setAttribute('data-status', 'PENDING');
        newRow.setAttribute('data-orig-stan-lap', stanLapValue);
        newRow.setAttribute('data-orig-argus', '-');
        newRow.setAttribute('data-orig-status', 'PENDING');
        newRow.setAttribute('data-ai-notes', '');

        newRow.innerHTML = `
            <td>${rowIdx + 1}</td>
            <td class="idpel-code">${idpel}</td>
            <td><strong>${namaDisplay}</strong></td>
            <td>${tarifDayaDisplay}</td>
            <td><input type="text" class="input-table" value="${stanLapValue}" onchange="onFieldChange(${rowIdx}, 'stan_lap')" onkeydown="handleRowKeydown(event, ${rowIdx}, 'stan_lap')"></td>
            <td>
                <img class="photo-thumbnail" loading="lazy" src="${objectUrl}" onerror="if(!this.src.includes('/sample-photo/')){this.src='/sample-photo/' + encodeURIComponent('${file.name}')}" onclick="inspectPhoto(${rowIdx})" alt="Foto Meter">
            </td>
            <td class="cell-raw" style="font-family:'JetBrains Mono';">-</td>
            <td>
                <input type="text" class="input-table ai-field cell-argus" value="-" onchange="onArgusChange(${rowIdx})" onkeydown="handleRowKeydown(event, ${rowIdx}, 'argus')">
                <div class="edit-badge-slot"></div>
            </td>
            <td class="cell-diff" style="font-family:'JetBrains Mono'; font-weight:700;">-</td>
            <td>
                <select class="select-status" onchange="onStatusSelectChange(${rowIdx}, this)">
                    <option value="PENDING" selected>Belum Diaudit</option>
                    <option value="MATCH">Sesuai Match</option>
                    <option value="ROLLING">Rolling Digit</option>
                    <option value="DIFF">Beda Stand</option>
                    <option value="NIHIL">Bukan KWH / Nihil</option>
                    <option value="TRIAGE">Perlu Tinjau Ulang</option>
                </select>
            </td>
            <td>
                <input type="text" class="input-notes" placeholder="Catatan auditor..." onchange="onFieldChange(${rowIdx}, 'notes')" onkeydown="handleRowKeydown(event, ${rowIdx}, 'notes')">
                <div class="ai-note-badge-slot"></div>
            </td>
            <td class="cell-lat" style="font-family:'JetBrains Mono'; font-size:11.5px;">-</td>
            <td><button class="btn-row-audit" onclick="auditSingleRow(${rowIdx})"><i class="fas fa-bolt"></i> Audit</button></td>
        `;
        fragment.appendChild(newRow);
    }

    tbody.appendChild(fragment);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof refreshTableDisplay === 'function') refreshTableDisplay();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

// Reset Table dengan Konfirmasi Aman
function resetTable() {
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    if (rows.length === 0) {
        showToast("Tabel antrean audit sudah kosong.", "info");
        return;
    }
    const modal = document.getElementById('modal-reset-confirm');
    if (modal) modal.style.display = 'flex';
    else executeResetTable();
}

async function executeResetTable() {
    const modal = document.getElementById('modal-reset-confirm');
    if (modal) modal.style.display = 'none';

    // 0. Pastikan seluruh koreksi/catatan AI yang ada masuk aman ke Celengan Feedback AI di disk sebelum tabel dihapus!
    if (typeof flushAllEditedFeedbackToVault === 'function') {
        try {
            await flushAllEditedFeedbackToVault();
        } catch (err) {
            console.warn('Flush feedback AI sebelum reset tabel gagal:', err);
        }
    }

    // 1. Kosongkan antrean baris tabel di DOM
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = `
        <tr id="empty-state-row">
            <td colspan="13" class="empty-state-td" style="white-space: normal !important; text-align: center !important; padding: 48px 20px !important;">
                <div class="empty-dropzone" id="empty-dropzone" onclick="document.getElementById('folder-input').click()" style="text-align: center !important; margin: 0 auto !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;">
                    <div class="empty-icon-circle" style="margin: 0 auto 16px auto !important; display: flex !important; align-items: center !important; justify-content: center !important;">
                        <i class="fas fa-cloud-upload-alt" style="margin: 0 !important; line-height: 1 !important;"></i>
                    </div>
                    <h3 class="empty-title" style="text-align: center !important; width: 100% !important; margin: 0 auto 8px auto !important;">Antrean Audit Masih Kosong</h3>
                    <p class="empty-subtitle" style="text-align: center !important; width: 100% !important; max-width: 580px !important; margin: 0 auto 20px auto !important; white-space: normal !important; display: block !important;">
                        Seret dan jatuhkan (<strong>Drag & Drop</strong>) berkas foto ke sini, atau klik tombol di bawah untuk memulai:
                    </p>
                    <div class="empty-actions" style="display: flex !important; justify-content: center !important; align-items: center !important; gap: 10px !important; margin: 0 auto 16px auto !important; width: 100% !important;">
                        <button type="button" class="btn btn-upload-folder" onclick="event.stopPropagation(); document.getElementById('folder-input').click()">
                            <i class="fas fa-folder-plus"></i> Unggah Folder Foto
                        </button>
                        <button type="button" class="btn btn-upload-file" onclick="event.stopPropagation(); document.getElementById('file-input').click()">
                            <i class="fas fa-file-image"></i> Tambah File Foto
                        </button>
                        <button type="button" class="btn btn-upload-excel" onclick="event.stopPropagation(); document.getElementById('excel-input').click()">
                            <i class="fas fa-file-excel"></i> Impor Rekap ACMT
                        </button>
                    </div>
                    <div class="empty-hint" style="display: inline-flex !important; justify-content: center !important; align-items: center !important; margin: 0 auto !important; text-align: center !important;">
                        <i class="fas fa-shield-alt" style="color:var(--pln-blue);"></i> Dilengkapi Jaring Pengaman Anti-Duplikasi Foto & Auto-Pairing Data Pelanggan
                    </div>
                </div>
            </td>
        </tr>
    `;

    // 2. Bersihkan Total Memori Kamus Excel Rekap ACMT (RAM) & Revoke Seluruh Object URL
    if (typeof excelRecordsMap !== 'undefined' && excelRecordsMap.clear) {
        excelRecordsMap.clear();
    }
    revokeAllObjectURLs();

    // 3. Reset Seluruh Nilai Input Form Berkas & Pencarian
    const folderInput = document.getElementById('folder-input');
    if (folderInput) folderInput.value = '';
    const fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';
    const excelInput = document.getElementById('excel-input');
    if (excelInput) excelInput.value = '';
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = '';

    // 4. Reset Mode Audit ke Default
    const modeSelect = document.getElementById('audit-mode-select');
    if (modeSelect) modeSelect.value = 'AUTO';
    currentAuditMode = 'AUTO';

    // 5. Reset Status Filter Kartu KPI ke 'ALL' & Reset Pagination
    if (typeof currentPage !== 'undefined') currentPage = 1;
    if (typeof filterByStatus === 'function') {
        filterByStatus('ALL');
    }
    if (typeof refreshTableDisplay === 'function') {
        refreshTableDisplay();
    }

    // 6. Inisialisasi Ulang Dropzone & Hitung Statistik KPI
    setupDropzoneEvents();
    if (typeof updateKPIs === 'function') updateKPIs();

    // 7. Bersihkan Penyimpanan Database Persisten Lokal (IndexedDB)
    if (typeof clearPersistedSession === 'function') clearPersistedSession();

    showToast("Seluruh tabel, antrean foto, dan data impor Excel ACMT telah dibersihkan total.", "info");
}

// DRAG & DROP SUPPORT (UX ENHANCEMENT)
function setupDropzoneEvents() {
    const dropzone = document.getElementById('empty-dropzone');
    const tableContainer = document.querySelector('.table-container');

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (dropzone) dropzone.classList.add('drag-over');
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (dropzone) dropzone.classList.remove('drag-over');
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (dropzone) dropzone.classList.remove('drag-over');
        const dt = e.dataTransfer;
        const files = Array.from(dt.files || []);
        if (files.length > 0) {
            const excelFile = files.find(f => /\.(xlsx|xls|csv)$/i.test(f.name));
            if (excelFile && files.length === 1) {
                handleExcelUpload({ target: { files: [excelFile], value: '' } });
            } else {
                processIncomingFiles(files, "dragdrop");
            }
        }
    };

    window.addEventListener('dragover', (e) => e.preventDefault());
    window.addEventListener('drop', (e) => e.preventDefault());

    if (dropzone) {
        dropzone.addEventListener('dragover', handleDragOver);
        dropzone.addEventListener('dragleave', handleDragLeave);
        dropzone.addEventListener('drop', handleDrop);
    }
    if (tableContainer) {
        tableContainer.addEventListener('dragover', handleDragOver);
        tableContainer.addEventListener('dragleave', handleDragLeave);
        tableContainer.addEventListener('drop', handleDrop);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setupDropzoneEvents();
    if (typeof restoreSessionOnStartup === 'function') {
        restoreSessionOnStartup();
    }
});
