/**
 * Module: audit_engine.js
 * Deskripsi: Mesin inferensi batch AI GPU, evaluasi selisih kWh,
 *            serta penanganan koreksi manual Human-in-the-Loop.
 * Lead Engineer: Pascol
 */

async function imageToBase64(url) {
    const response = await fetch(url);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function auditSingleRow(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    const photoImg = row.querySelector('.photo-thumbnail');
    const stanLapInput = row.querySelectorAll('.input-table')[0];
    const stanArgusInput = row.querySelector('.cell-argus');
    const cellRaw = row.querySelector('.cell-raw');
    const cellDiff = row.querySelector('.cell-diff');
    const statusSelect = row.querySelector('.select-status');
    const cellLat = row.querySelector('.cell-lat');
    const btnAudit = row.querySelector('.btn-row-audit');

    btnAudit.disabled = true;
    btnAudit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Audit...';

    try {
        const b64 = await imageToBase64(photoImg.src);
        const resp = await fetch('/predict-base64', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: b64,
                filename: row.getAttribute('data-photo')
            })
        });

        const data = await resp.json();

        cellRaw.textContent = data.raw_display || '-';
        const isAlreadyEdited = row.getAttribute('data-edited') === 'true';

        // Lindungi hasil koreksi manual auditor: Jangan timpa stanArgus jika sudah diedit manual
        if (!isAlreadyEdited) {
            stanArgusInput.value = data.stand_baca || '-';
        }
        cellLat.textContent = `${data.latency_ms || 0} ms`;

        row.setAttribute('data-blur', data.blur_score || 0);
        row.setAttribute('data-glare', data.glare_percentage || 0);
        row.setAttribute('data-tier', data.tier_color || 'GREEN');

        const stanPlnRaw = stanLapInput.value.trim();
        const stanPlnVal = stanPlnRaw.replace(/\D/g, '');
        const stanAiVal = (isAlreadyEdited ? stanArgusInput.value : (data.stand_baca || '')).trim().replace(/\D/g, '');
        const isMandiriMode = (typeof currentAuditMode !== 'undefined' && currentAuditMode === 'MANDIRI') ||
                              (stanPlnVal === '' || stanPlnRaw === '-');

        if (isAlreadyEdited) {
            // Jika sudah dikoreksi auditor, pertahankan koreksi dan hitung ulang selisihnya
            recalculateRowDiffAndStatus(row);
        } else if (data.status === 'FAIL_COUNTER_NOT_FOUND') {
            cellDiff.textContent = '-';
            statusSelect.value = 'NIHIL';
            row.setAttribute('data-status', 'NIHIL');
        } else if (data.status === 'FOTO_BURAM') {
            cellDiff.textContent = '-';
            statusSelect.value = 'TRIAGE';
            row.setAttribute('data-status', 'TRIAGE');
        } else if (data.stand_baca) {
            if (isMandiriMode) {
                // Mode Ekstraksi Mandiri (Murni AI): Tidak ada vonis salah 'BEDA STAND' karena tidak membandingkan dengan 0
                cellDiff.textContent = '-';
                statusSelect.value = 'MATCH';
                row.setAttribute('data-status', 'MATCH');
            } else {
                // Mode Komparasi Lapangan: Hitung selisih angka riil terhadap stan lapangan
                const numPln = parseInt(stanPlnVal) || 0;
                const numAi = parseInt(stanAiVal) || 0;
                const diff = numAi - numPln;
                cellDiff.textContent = diff === 0 ? '0' : diff;

                if (diff === 0) {
                    statusSelect.value = 'MATCH';
                    row.setAttribute('data-status', 'MATCH');
                } else if (Math.abs(diff) <= 2) {
                    statusSelect.value = 'ROLLING';
                    row.setAttribute('data-status', 'ROLLING');
                } else {
                    statusSelect.value = 'DIFF';
                    row.setAttribute('data-status', 'DIFF');
                }
            }
        } else {
            cellDiff.textContent = '-';
            statusSelect.value = 'TRIAGE';
            row.setAttribute('data-status', 'TRIAGE');
        }

        updateSelectStyle(statusSelect);
        updateRowStyle(row);
        if (typeof updateKPIs === 'function') updateKPIs();
    } catch (err) {
        console.error(err);
        statusSelect.value = 'TRIAGE';
        updateSelectStyle(statusSelect);
    } finally {
        btnAudit.disabled = false;
        btnAudit.innerHTML = '<i class="fas fa-redo-alt"></i> Re-Audit';
    }
}

async function auditAllRows() {
    const btn = document.getElementById('btn-run-all');
    const rows = document.querySelectorAll('#table-body tr');
    if (rows.length === 0) {
        if (typeof showToast === 'function') {
            showToast("Tidak ada antrean foto untuk diaudit. Silakan unggah folder atau file foto terlebih dahulu.", "warning");
        }
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses Batch...';

    let processedCount = 0;
    let protectedCount = 0;

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        // Human-in-the-Loop Guard: Jangan menimpa baris yang telah dikoreksi manual oleh auditor
        if (row.getAttribute('data-edited') === 'true') {
            protectedCount++;
            continue;
        }
        await auditSingleRow(i);
        processedCount++;
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-check-double"></i> Selesai Diaudit';
    if (typeof showToast === 'function') {
        if (protectedCount > 0) {
            showToast(`Batch audit selesai: ${processedCount} diproses, ${protectedCount} hasil koreksi manual tetap terlindungi.`, "success");
        } else {
            showToast(`Proses batch audit berhasil diselesaikan (${processedCount} data).`, "success");
        }
    }
    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-play"></i> Mulai Audit Batch';
    }, 3000);
}

function onArgusChange(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    markRowAsEdited(row);
    recalculateRowDiffAndStatus(row);
    if (typeof updateKPIs === 'function') updateKPIs();
}

function onFieldChange(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    recalculateRowDiffAndStatus(row);
    if (typeof updateKPIs === 'function') updateKPIs();
}

function onStatusSelectChange(rowIndex, selectElem) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    row.setAttribute('data-status', selectElem.value);
    markRowAsEdited(row);
    updateSelectStyle(selectElem);
    updateRowStyle(row);
    if (typeof updateKPIs === 'function') updateKPIs();
}

function markRowAsEdited(row) {
    row.setAttribute('data-edited', 'true');
    row.classList.add('row-edited');
    const slot = row.querySelector('.edit-badge-slot');
    if (slot && !slot.innerHTML) {
        slot.innerHTML = '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>';
    }
}

function recalculateRowDiffAndStatus(row) {
    const stanLapInput = row.querySelectorAll('.input-table')[0];
    const stanArgusInput = row.querySelector('.cell-argus');
    const cellDiff = row.querySelector('.cell-diff');
    const statusSelect = row.querySelector('.select-status');

    const pRaw = stanLapInput.value.trim();
    const pStr = pRaw.replace(/\D/g, '');
    const aStr = stanArgusInput.value.trim().replace(/\D/g, '');
    const isMandiri = (typeof currentAuditMode !== 'undefined' && currentAuditMode === 'MANDIRI') ||
                      (pStr === '' || pRaw === '-');

    if (aStr !== '') {
        if (isMandiri) {
            cellDiff.textContent = '-';
            statusSelect.value = 'MATCH';
            row.setAttribute('data-status', 'MATCH');
        } else {
            const numPln = parseInt(pStr) || 0;
            const numAi = parseInt(aStr) || 0;
            const diff = numAi - numPln;
            cellDiff.textContent = diff === 0 ? '0' : diff;

            if (diff === 0) {
                statusSelect.value = 'MATCH';
                row.setAttribute('data-status', 'MATCH');
            } else if (Math.abs(diff) <= 2) {
                statusSelect.value = 'ROLLING';
                row.setAttribute('data-status', 'ROLLING');
            } else {
                statusSelect.value = 'DIFF';
                row.setAttribute('data-status', 'DIFF');
            }
        }
    }
    updateSelectStyle(statusSelect);
    updateRowStyle(row);
}

function updateSelectStyle(sel) {
    sel.className = 'select-status';
    if (sel.value === 'MATCH') sel.classList.add('status-match');
    else if (sel.value === 'ROLLING') sel.classList.add('status-rolling');
    else if (sel.value === 'DIFF') sel.classList.add('status-diff');
    else if (sel.value === 'NIHIL') sel.classList.add('status-nihil');
    else if (sel.value === 'TRIAGE') sel.classList.add('status-triage');
}

function updateRowStyle(row) {
    const st = row.getAttribute('data-status');
    row.classList.remove('row-match', 'row-rolling', 'row-diff');
    if (st === 'MATCH') row.classList.add('row-match');
    else if (st === 'ROLLING') row.classList.add('row-rolling');
    else if (st === 'DIFF' || st === 'NIHIL') row.classList.add('row-diff');
}
