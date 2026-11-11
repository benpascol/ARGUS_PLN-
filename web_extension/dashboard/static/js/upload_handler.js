/**
 * Module: upload_handler.js
 * Deskripsi: Penanganan unggah berkas dual-mode (folder/file), ekstraksi IDPEL,
 *            dan jaring pengaman anti-duplikasi foto (Deduplication Guard).
 * Lead Engineer: Pascol
 */

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
            const objectUrl = URL.createObjectURL(item.file);
            photoImg.src = objectUrl;
            r.setAttribute('data-photo', item.file.name);
            r.setAttribute('data-status', 'PENDING');
            r.querySelector('.cell-raw').textContent = '-';
            r.querySelector('.cell-argus').value = '-';
            r.querySelector('.cell-diff').textContent = '-';
            r.querySelector('.cell-lat').textContent = '-';
            const sel = r.querySelector('.select-status');
            sel.value = 'PENDING';
            if (typeof updateSelectStyle === 'function') updateSelectStyle(sel);
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
    let currentCount = tbody.querySelectorAll('tr').length;

    const fragment = document.createDocumentFragment();

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const rowIdx = currentCount + i;
        const idpel = extractIdpelFromFilename(file.name);
        const objectUrl = URL.createObjectURL(file);

        const newRow = document.createElement('tr');
        newRow.id = `row-${rowIdx}`;
        newRow.setAttribute('data-idpel', idpel);
        newRow.setAttribute('data-photo', file.name);
        newRow.setAttribute('data-status', 'PENDING');

        newRow.innerHTML = `
            <td>${rowIdx + 1}</td>
            <td class="idpel-code">${idpel}</td>
            <td><strong>${file.name.replace(/\.[^/.]+$/, "").substring(0, 20)}</strong></td>
            <td>R1 / 900 VA</td>
            <td><input type="text" class="input-table" value="0" oninput="onFieldChange(${rowIdx})"></td>
            <td>
                <img class="photo-thumbnail" src="${objectUrl}" onclick="inspectPhoto(${rowIdx})">
            </td>
            <td class="cell-raw" style="font-family:'JetBrains Mono';">-</td>
            <td>
                <input type="text" class="input-table ai-field cell-argus" value="-" oninput="onArgusChange(${rowIdx})">
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
            <td><input type="text" class="input-notes" placeholder="Catatan auditor..." oninput="onFieldChange(${rowIdx})"></td>
            <td class="cell-lat" style="font-family:'JetBrains Mono'; font-size:11.5px;">-</td>
            <td><button class="btn-row-audit" onclick="auditSingleRow(${rowIdx})"><i class="fas fa-bolt"></i> Audit</button></td>
        `;
        fragment.appendChild(newRow);
    }

    tbody.appendChild(fragment);
    if (typeof updateKPIs === 'function') updateKPIs();
}
