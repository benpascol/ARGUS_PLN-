/**
 * Module: audit_engine.js
 * Deskripsi: Mesin inferensi batch AI GPU, evaluasi selisih kWh,
 *            serta penanganan koreksi manual Human-in-the-Loop.
 * Lead Engineer: Pascol
 */

/**
 * Ekstraksi angka bulat stan meter (kWh) bersih dari karakter desimal.
 * Standar PLN: Digit setelah titik atau koma (seperti '201.63' atau '201,63')
 * adalah angka putaran desimal (koma), yang diabaikan dalam komparasi stan kwh.
 */
function extractIntegerStand(rawVal) {
    if (rawVal === undefined || rawVal === null) return null;
    let s = String(rawVal).trim();
    if (s === '' || s === '-' || s.toLowerCase() === 'null') return null;

    // Jika mengandung titik atau koma desimal, potong hanya bagian integer di depan
    if (s.includes('.') || s.includes(',')) {
        s = s.split(/[.,]/)[0];
    }
    // Hapus karakter non-digit
    s = s.replace(/\D/g, '');
    if (s === '') return null;
    return parseInt(s, 10);
}

async function imageToBase64(url, fallbackFilename) {
    try {
        if (!url || url.startsWith('blob:null')) throw new Error("Invalid blob URL");
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    } catch (err) {
        // Fallback tangguh ke server endpoint jika blob URL hangus setelah reload (F5 / Ctrl+F5)
        if (fallbackFilename) {
            const fbUrl = `/sample-photo/${encodeURIComponent(fallbackFilename)}`;
            const fbResp = await fetch(fbUrl);
            if (fbResp.ok) {
                const blob = await fbResp.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }
        }
        throw err;
    }
}

async function auditSingleRow(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    const photoImg = row.querySelector('.photo-thumbnail');
    const photoName = row.getAttribute('data-photo') || '';
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
        const b64 = await imageToBase64(photoImg ? photoImg.src : '', photoName);
        const resp = await fetch('/predict-base64', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: b64,
                filename: photoName
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
        const numPln = extractIntegerStand(stanPlnRaw);
        const stanAiRaw = isAlreadyEdited ? stanArgusInput.value : (data.stand_baca || '');
        const numAi = extractIntegerStand(stanAiRaw);
        const isMandiriMode = (typeof currentAuditMode !== 'undefined' && currentAuditMode === 'MANDIRI') || (numPln === null);

        if (isAlreadyEdited) {
            // Jika sudah dikoreksi auditor, pertahankan koreksi dan hitung ulang selisihnya
            recalculateRowDiffAndStatus(row);
        } else if (data.status === 'FAIL_COUNTER_NOT_FOUND' || data.status === 'TIDAK_TERDETEKSI_KWH') {
            cellDiff.textContent = '-';
            statusSelect.value = 'NIHIL';
            row.setAttribute('data-status', 'NIHIL');
        } else if (data.status === 'FOTO_BURAM' || data.status === 'ANOMALI_GLARE_TERHALANG') {
            cellDiff.textContent = '-';
            statusSelect.value = 'TRIAGE';
            row.setAttribute('data-status', 'TRIAGE');
        } else if (numAi !== null) {
            if (isMandiriMode) {
                // Mode Ekstraksi Mandiri (Murni AI): Tidak ada komparasi terhadap 0
                cellDiff.textContent = '-';
                statusSelect.value = 'MATCH';
                row.setAttribute('data-status', 'MATCH');
            } else {
                // Mode Komparasi Lapangan: Hitung selisih angka riil terhadap stan lapangan
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
            // Kotak tidak terbaca atau stan kosong: Selisih wajib '-'
            cellDiff.textContent = '-';
            statusSelect.value = 'TRIAGE';
            row.setAttribute('data-status', 'TRIAGE');
        }

        updateSelectStyle(statusSelect);
        updateRowStyle(row);
        if (typeof updateKPIs === 'function') updateKPIs();
        if (typeof persistCurrentSession === 'function') persistCurrentSession();
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
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    if (rows.length === 0) {
        if (typeof showToast === 'function') {
            showToast("Tidak ada antrean foto untuk diaudit. Silakan unggah folder atau file foto terlebih dahulu.", "warning");
        }
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses Batch...';

    const pWrapper = document.getElementById('batch-progress-wrapper');
    const pFill = document.getElementById('batch-progress-fill');
    const pEta = document.getElementById('batch-eta-badge');
    if (pWrapper) pWrapper.style.display = 'block';
    if (pFill) pFill.style.width = '0%';
    if (pEta) pEta.innerHTML = '<i class="fas fa-hourglass-half"></i> Menyiapkan antrean...';

    let processedCount = 0;
    let protectedCount = 0;
    const totalCount = rows.length;
    const tBatchStart = performance.now();

    for (let i = 0; i < totalCount; i++) {
        const row = rows[i];
        const currentPhotoNum = i + 1;
        const progressPct = Math.round((currentPhotoNum / totalCount) * 100);
        if (pFill) pFill.style.width = `${progressPct}%`;

        // Update Live ETA Counter
        if (pEta) {
            if (i === 0) {
                pEta.innerHTML = `<i class="fas fa-hourglass-half"></i> Memproses foto 1 dari ${totalCount} (Menghitung estimasi...)`;
            } else {
                const elapsedSec = (performance.now() - tBatchStart) / 1000;
                const avgSecPerPhoto = elapsedSec / i;
                const remainingPhotos = totalCount - i;
                const estRemainingSec = Math.max(1, Math.round(avgSecPerPhoto * remainingPhotos));
                pEta.innerHTML = `<i class="fas fa-hourglass-half"></i> Memproses foto ${currentPhotoNum} dari ${totalCount} (Sisa ~${estRemainingSec} detik)`;
            }
        }

        // Human-in-the-Loop Guard: Jangan menimpa baris yang telah dikoreksi manual oleh auditor
        if (row.getAttribute('data-edited') === 'true') {
            protectedCount++;
            continue;
        }
        await auditSingleRow(i);
        processedCount++;
    }

    const totalBatchDuration = ((performance.now() - tBatchStart) / 1000).toFixed(1);
    if (pFill) pFill.style.width = '100%';
    if (pEta) {
        pEta.innerHTML = `<i class="fas fa-check-circle" style="color:#16A34A;"></i> Selesai ${totalCount} foto (${totalBatchDuration}s)`;
    }

    setTimeout(() => {
        if (pWrapper) pWrapper.style.display = 'none';
        if (pFill) pFill.style.width = '0%';
    }, 1200);

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-check-double"></i> Selesai Diaudit';

    // POP-UP MODAL SELESAI AUDIT BATCH (UX 6)
    let match = 0, rolling = 0, diff = 0, nihil = 0, edited = 0;
    rows.forEach(r => {
        const st = r.getAttribute('data-status');
        if (st === 'MATCH') match++;
        else if (st === 'ROLLING') rolling++;
        else if (st === 'DIFF') diff++;
        else if (st === 'NIHIL' || st === 'TRIAGE') nihil++;
        if (r.getAttribute('data-edited') === 'true') edited++;
    });

    const mTotal = document.getElementById('batch-modal-total');
    const mMatch = document.getElementById('batch-modal-match');
    const mRolling = document.getElementById('batch-modal-rolling');
    const mDiff = document.getElementById('batch-modal-diff');
    const mNihil = document.getElementById('batch-modal-nihil');
    const mEdited = document.getElementById('batch-modal-edited');
    const mNotes = document.getElementById('batch-modal-notes');
    const modalComplete = document.getElementById('modal-batch-complete');

    if (mTotal) mTotal.textContent = totalCount;
    if (mMatch) mMatch.textContent = `${match} (${totalCount ? Math.round(match/totalCount*100) : 0}%)`;
    if (mRolling) mRolling.textContent = `${rolling} (${totalCount ? Math.round(rolling/totalCount*100) : 0}%)`;
    if (mDiff) mDiff.textContent = `${diff} (${totalCount ? Math.round(diff/totalCount*100) : 0}%)`;
    if (mNihil) mNihil.textContent = nihil;
    if (mEdited) mEdited.textContent = edited;
    if (mNotes && protectedCount > 0) {
        mNotes.textContent = `${processedCount} foto selesai diproses AI. ${protectedCount} hasil koreksi manual Anda tetap terlindungi aman.`;
    }

    if (modalComplete) modalComplete.style.display = 'flex';

    if (typeof persistCurrentSession === 'function') persistCurrentSession();

    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-play"></i> Mulai Audit Batch';
    }, 3000);
}

function closeBatchCompleteModal() {
    const modal = document.getElementById('modal-batch-complete');
    if (modal) modal.style.display = 'none';
}

/**
 * Penanganan Tombol Keyboard (Enter) ala Excel:
 * Menyelesaikan edit, menghitung selisih & vonis seketika,
 * lalu otomatis memindahkan fokus kursor ke baris berikutnya.
 */
function handleRowKeydown(event, rowIndex, fieldType) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const target = event.target;
        target.blur(); // Blur otomatis memicu event onchange jika ada perubahan

        if (fieldType === 'argus') {
            onArgusChange(rowIndex);
        } else {
            onFieldChange(rowIndex);
        }

        // Pindahkan fokus ke baris berikutnya (Excel-like experience)
        const nextRow = document.getElementById(`row-${rowIndex + 1}`);
        if (nextRow) {
            let nextInput = null;
            if (fieldType === 'argus') {
                nextInput = nextRow.querySelector('.cell-argus');
            } else if (fieldType === 'stan_lap') {
                nextInput = nextRow.querySelectorAll('.input-table')[0];
            } else if (fieldType === 'notes') {
                nextInput = nextRow.querySelector('.input-notes');
            }
            if (nextInput) {
                nextInput.focus();
                nextInput.select();
            }
        }
    }
}

function onArgusChange(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    markRowAsEdited(row);
    recalculateRowDiffAndStatus(row);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function triggerRowPulseHighlight(row) {
    if (!row) return;
    row.classList.remove('row-just-edited');
    void row.offsetWidth; // Force CSS reflow to restart animation reliably
    row.classList.add('row-just-edited');
    if (row._pulseTimer) clearTimeout(row._pulseTimer);
    row._pulseTimer = setTimeout(() => {
        row.classList.remove('row-just-edited');
        delete row._pulseTimer;
    }, 1250);
}

function onFieldChange(rowIndex) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    markRowAsEdited(row);
    recalculateRowDiffAndStatus(row);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function onStatusSelectChange(rowIndex, selectElem) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    const newStatus = selectElem.value;
    row.setAttribute('data-status', newStatus);
    markRowAsEdited(row);

    const cellDiff = row.querySelector('.cell-diff');
    // Aturan Permintaan User:
    // Jika vonis dinyatakan Bukan kwh/nihil atau Perlu tinjau ulang, selisih by default dihilangkan jadi '-'
    if (newStatus === 'NIHIL' || newStatus === 'TRIAGE' || newStatus === 'PENDING') {
        if (cellDiff) cellDiff.textContent = '-';
    } else if (newStatus === 'MATCH') {
        // Vonis Cocok / Sesuai Match: Selisih ideal 0
        if (cellDiff) cellDiff.textContent = '0';
    } else {
        // ROLLING / DIFF: Hitung selisih angka riil jika kedua data numerik ada
        const stanLapInput = row.querySelectorAll('.input-table')[0];
        const stanArgusInput = row.querySelector('.cell-argus');
        const numPln = extractIntegerStand(stanLapInput ? stanLapInput.value : '');
        const numAi = extractIntegerStand(stanArgusInput ? stanArgusInput.value : '');
        if (cellDiff) {
            if (numPln !== null && numAi !== null) {
                const diff = numAi - numPln;
                cellDiff.textContent = diff === 0 ? '0' : diff;
            } else {
                cellDiff.textContent = '-';
            }
        }
    }

    updateSelectStyle(selectElem);
    updateRowStyle(row);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function markRowAsEdited(row) {
    row.setAttribute('data-edited', 'true');
    row.classList.add('row-edited');
    const slot = row.querySelector('.edit-badge-slot');
    if (slot && !slot.innerHTML) {
        slot.innerHTML = '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>';
    }
    triggerRowPulseHighlight(row);
}

function recalculateRowDiffAndStatus(row) {
    const stanLapInput = row.querySelectorAll('.input-table')[0];
    const stanArgusInput = row.querySelector('.cell-argus');
    const cellDiff = row.querySelector('.cell-diff');
    const statusSelect = row.querySelector('.select-status');

    const numPln = extractIntegerStand(stanLapInput ? stanLapInput.value : '');
    const numAi = extractIntegerStand(stanArgusInput ? stanArgusInput.value : '');
    const isMandiri = (typeof currentAuditMode !== 'undefined' && currentAuditMode === 'MANDIRI') || (numPln === null);

    // KASUS 1: Jika Stan ARGUS kosong / null / tidak terbaca
    if (numAi === null) {
        cellDiff.textContent = '-';
        if (statusSelect.value !== 'NIHIL') {
            statusSelect.value = 'TRIAGE';
            row.setAttribute('data-status', 'TRIAGE');
        }
        updateSelectStyle(statusSelect);
        updateRowStyle(row);
        return;
    }

    // KASUS 2: Mode Mandiri (tidak membandingkan dengan stan lapangan)
    if (isMandiri) {
        cellDiff.textContent = '-';
        statusSelect.value = 'MATCH';
        row.setAttribute('data-status', 'MATCH');
        updateSelectStyle(statusSelect);
        updateRowStyle(row);
        return;
    }

    // KASUS 3: Mode Komparasi Lapangan (Otomatis hitung selisih & vonis dari angka riil)
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
    row.classList.remove('row-match', 'row-rolling', 'row-diff', 'row-nihil', 'row-triage');
    if (st === 'MATCH') row.classList.add('row-match');
    else if (st === 'ROLLING') row.classList.add('row-rolling');
    else if (st === 'DIFF') row.classList.add('row-diff');
    else if (st === 'NIHIL') row.classList.add('row-nihil');
    else if (st === 'TRIAGE') row.classList.add('row-triage');
}
