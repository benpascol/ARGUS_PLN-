/**
 * Module: audit_engine.js
 * Deskripsi: Mesin inferensi batch AI GPU, evaluasi selisih kWh,
 *            serta penanganan koreksi manual Human-in-the-Loop.
 * Lead Engineer: Benedictus Pascal
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

window.isBatchAuditRunning = false;

async function auditSingleRow(rowIndex, opts = {}) {
    const batchMode = Boolean(opts && opts.batchMode);
    const row = (opts && opts.rowEl) || document.getElementById(`row-${rowIndex}`);
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
        let resp;
        // Fast-path biner (Anti-OOM): kirim File/Blob langsung via FormData ke /predict tanpa alokasi string Base64
        if (row._photoBlob instanceof Blob) {
            const formData = new FormData();
            formData.append('file', row._photoBlob, photoName || 'meter.jpg');
            resp = await fetch('/predict', {
                method: 'POST',
                body: formData
            });
        } else {
            const b64 = await imageToBase64(photoImg ? photoImg.src : '', photoName);
            resp = await fetch('/predict-base64', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_base64: b64,
                    filename: photoName
                })
            });
        }

        if (!resp.ok) {
            throw new Error(`Server AI mengembalikan HTTP ${resp.status}`);
        }
        const data = await resp.json();

        cellRaw.textContent = data.raw_display || '-';
        const isAlreadyEdited = row.getAttribute('data-edited') === 'true';

        // Lindungi hasil koreksi manual auditor: Jangan timpa stanArgus jika sudah diedit manual
        if (!isAlreadyEdited) {
            stanArgusInput.value = data.stand_baca || '-';
        }
        // Simpan metadata pre-labeling YOLO (bounding box kotak & digit) untuk Celengan AI
        row._aiPrelabelMeta = {
            counter_box: data.counter_box || null,
            crop_shape: data.crop_shape || null,
            digits_detail: data.digits_detail || []
        };

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
            row.setAttribute('data-orig-argus', data.stand_baca || '-');
            recalculateRowDiffAndStatus(row);
        } else {
            if (data.status === 'FAIL_COUNTER_NOT_FOUND' || data.status === 'TIDAK_TERDETEKSI_KWH') {
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

            // Rekam snapshot baseline asli AI untuk Smart Baseline Comparison ("Dikoreksi Auditor")
            row.setAttribute('data-orig-stan-lap', stanLapInput.value.trim());
            row.setAttribute('data-orig-argus', stanArgusInput.value.trim());
            row.setAttribute('data-orig-status', statusSelect.value);
            evaluateRowEditedState(row, false);
        }

        updateSelectStyle(statusSelect);
        updateRowStyle(row);
        if (!batchMode) {
            if (typeof updateKPIs === 'function') updateKPIs();
            if (typeof persistCurrentSession === 'function') persistCurrentSession();
        }
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
    if (window.isBatchAuditRunning) return;
    const btn = document.getElementById('btn-run-all');
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    if (rows.length === 0) {
        if (typeof showToast === 'function') {
            showToast("Tidak ada antrean foto untuk diaudit. Silakan unggah folder atau file foto terlebih dahulu.", "warning");
        }
        return;
    }

    // SOLUSI 5: CONCURRENT WORKER POOL (AKSELERASI MULTI-WORKER DENGAN AUTO-HARDWARE TUNING)
    const CONCURRENCY = window.BATCH_CONCURRENCY || 4;
    const hwInfo = window.ARGUS_HARDWARE_INFO || {};
    const hwLabel = hwInfo.device_name || 'Local Engine';

    window.isBatchAuditRunning = true;
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-bolt" style="color:var(--pln-yellow);"></i> Memproses Batch (${CONCURRENCY}x Worker)...`;

    const pWrapper = document.getElementById('batch-progress-wrapper');
    const pFill = document.getElementById('batch-progress-fill');
    const pEta = document.getElementById('batch-eta-badge');
    const pTitle = document.getElementById('batch-progress-label');
    if (pWrapper) pWrapper.style.display = 'block';
    if (pFill) pFill.style.width = '0%';
    if (pTitle) pTitle.textContent = `Memproses Batch AI (${CONCURRENCY}x Worker Pool — ${hwLabel})...`;
    if (pEta) pEta.innerHTML = `<i class="fas fa-bolt" style="color:var(--pln-yellow);"></i> Mengaktifkan ${CONCURRENCY} worker paralel...`;

    let processedCount = 0;
    let protectedCount = 0;
    let completedCount = 0;
    const totalCount = rows.length;
    const tBatchStart = performance.now();
    let lastKpiRefreshAt = tBatchStart;
    let nextIndex = 0;

    function updateBatchProgress(done) {
        const progressPct = Math.min(100, Math.round((done / totalCount) * 100));
        if (pFill) pFill.style.width = `${progressPct}%`;

        const now = performance.now();
        if (pEta) {
            if (done <= CONCURRENCY) {
                pEta.innerHTML = `<i class="fas fa-bolt" style="color:var(--pln-yellow);"></i> ${CONCURRENCY}x Worker Aktif: Memproses ${done} dari ${totalCount}...`;
            } else {
                const elapsedSec = (now - tBatchStart) / 1000;
                const avgSecPerPhoto = elapsedSec / done;
                const remainingPhotos = totalCount - done;
                const estRemainingSec = Math.max(1, Math.round(avgSecPerPhoto * remainingPhotos));
                pEta.innerHTML = `<i class="fas fa-bolt" style="color:var(--pln-yellow);"></i> ${CONCURRENCY}x Worker: Selesai ${done}/${totalCount} (Sisa ~${estRemainingSec} detik)`;
            }
        }

        // Throttle updateKPIs agar tidak memindai 7.000 baris DOM di setiap 1 foto (maks 1x per 600ms)
        if (now - lastKpiRefreshAt >= 600) {
            lastKpiRefreshAt = now;
            if (typeof updateKPIs === 'function') updateKPIs();
        }
    }

    async function worker(workerId) {
        while (nextIndex < totalCount) {
            const currentIdx = nextIndex++;
            const row = rows[currentIdx];
            if (!row) break;

            // Human-in-the-Loop Guard: Jangan menimpa baris yang telah dikoreksi manual oleh auditor
            if (row.getAttribute('data-edited') === 'true') {
                protectedCount++;
                completedCount++;
                updateBatchProgress(completedCount);
                continue;
            }

            try {
                await auditSingleRow(currentIdx, { batchMode: true, rowEl: row });
                processedCount++;
            } catch (err) {
                console.error(`[Worker ${workerId}] Error audit baris ${currentIdx}:`, err);
            } finally {
                completedCount++;
                updateBatchProgress(completedCount);
            }
        }
    }

    try {
        // Eksekusi paralel worker serentak
        const activeWorkers = Math.min(CONCURRENCY, totalCount);
        const workerPromises = [];
        for (let w = 1; w <= activeWorkers; w++) {
            workerPromises.push(worker(w));
        }
        await Promise.all(workerPromises);
    } finally {
        window.isBatchAuditRunning = false;
    }

    const totalBatchDuration = ((performance.now() - tBatchStart) / 1000).toFixed(1);
    const avgLatency = (totalBatchDuration / Math.max(1, processedCount)).toFixed(2);
    if (pFill) pFill.style.width = '100%';
    if (pEta) {
        pEta.innerHTML = `<i class="fas fa-check-circle" style="color:#16A34A;"></i> Selesai ${totalCount} foto dalam ${totalBatchDuration}s (Rerata ~${avgLatency}s/foto)`;
    }

    setTimeout(() => {
        if (pWrapper) pWrapper.style.display = 'none';
        if (pFill) pFill.style.width = '0%';
    }, 1500);

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-check-double"></i> Selesai Diaudit';

    // POP-UP MODAL SELESAI AUDIT BATCH (UX 6)
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

    const mTotal = document.getElementById('batch-modal-total');
    const mMatch = document.getElementById('batch-modal-match');
    const mRolling = document.getElementById('batch-modal-rolling');
    const mDiff = document.getElementById('batch-modal-diff');
    const mTriage = document.getElementById('batch-modal-triage');
    const mNihil = document.getElementById('batch-modal-nihil');
    const mEdited = document.getElementById('batch-modal-edited');
    const mNotes = document.getElementById('batch-modal-notes');
    const modalComplete = document.getElementById('modal-batch-complete');

    if (mTotal) mTotal.textContent = totalCount;
    if (mMatch) mMatch.textContent = `${match} (${totalCount ? Math.round(match/totalCount*100) : 0}%)`;
    if (mRolling) mRolling.textContent = `${rolling} (${totalCount ? Math.round(rolling/totalCount*100) : 0}%)`;
    if (mDiff) mDiff.textContent = `${diff} (${totalCount ? Math.round(diff/totalCount*100) : 0}%)`;
    if (mTriage) mTriage.textContent = `${triage} (${totalCount ? Math.round(triage/totalCount*100) : 0}%)`;
    if (mNihil) mNihil.textContent = nihil;
    if (mEdited) mEdited.textContent = edited;
    if (mNotes) {
        const hwInfo = window.ARGUS_HARDWARE_INFO || {};
        const concurrency = hwInfo.concurrency || window.BATCH_CONCURRENCY || 4;
        const deviceName = hwInfo.device_name || 'Local Engine';
        let noteMsg = `Total waktu: ${totalBatchDuration} detik (Akselerasi ${concurrency}x Worker • ${deviceName}).`;
        if (protectedCount > 0) {
            noteMsg += ` ${protectedCount} baris hasil koreksi auditor tetap aman terlindungi.`;
        }
        mNotes.textContent = noteMsg;
    }

    if (modalComplete) modalComplete.style.display = 'flex';

    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof refreshTableDisplay === 'function') refreshTableDisplay();
    if (typeof persistCurrentSession === 'function') persistCurrentSession(true);

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

    recalculateRowDiffAndStatus(row);
    evaluateRowEditedState(row, true);
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

function onFieldChange(rowIndex, fieldKind = 'stan_lap') {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row) return;

    // Catatan operasional PLN (kolom Excel) tidak mengubah status/selisih AI ataupun memicu "Dikoreksi"
    if (fieldKind === 'notes') {
        if (typeof persistCurrentSession === 'function') persistCurrentSession();
        return;
    }

    recalculateRowDiffAndStatus(row);
    evaluateRowEditedState(row, true);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function applyStatusChangeToRow(row, newStatus, pulseOnEdit = true) {
    if (!row) return;
    const selectElem = row.querySelector('.select-status');
    if (selectElem) selectElem.value = newStatus;

    row.setAttribute('data-status', newStatus);

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

    if (selectElem) updateSelectStyle(selectElem);
    updateRowStyle(row);
    evaluateRowEditedState(row, pulseOnEdit);
    if (typeof updateKPIs === 'function') updateKPIs();
    if (typeof persistCurrentSession === 'function') persistCurrentSession();
}

function onStatusSelectChange(rowIndex, selectElem) {
    const row = document.getElementById(`row-${rowIndex}`);
    if (!row || !selectElem) return;
    applyStatusChangeToRow(row, selectElem.value, true);
}

function normalizeArgusBaselineVal(val) {
    const trimmed = String(val ?? '').trim();
    return trimmed === '' ? '-' : trimmed;
}

/**
 * Mengevaluasi secara cerdas apakah baris masih menyimpang dari nilai asli AI/baseline
 * (atau memiliki catatan evaluasi model AI). Jika dikembalikan persis ke nilai asli dan
 * tidak ada catatan AI, status "Dikoreksi" otomatis dihapus.
 */
function evaluateRowEditedState(row, pulseOnEdit = true) {
    if (!row) return false;

    const stanLapInput = row.querySelectorAll('.input-table')[0];
    const stanArgusInput = row.querySelector('.cell-argus');

    const currStanLap = (stanLapInput ? stanLapInput.value : '').trim();
    const currArgus = normalizeArgusBaselineVal(stanArgusInput ? stanArgusInput.value : '-');
    const currStatus = (row.getAttribute('data-status') || 'PENDING').trim();
    const aiNotes = (row.getAttribute('data-ai-notes') || '').trim();

    const origStanLap = (row.hasAttribute('data-orig-stan-lap') ? row.getAttribute('data-orig-stan-lap') : currStanLap).trim();
    const origArgus = normalizeArgusBaselineVal(row.hasAttribute('data-orig-argus') ? row.getAttribute('data-orig-argus') : currArgus);
    const origStatus = (row.hasAttribute('data-orig-status') ? row.getAttribute('data-orig-status') : currStatus).trim();

    const isEdited = (
        currStanLap !== origStanLap ||
        currArgus !== origArgus ||
        currStatus !== origStatus ||
        aiNotes.length > 0
    );

    const wasEdited = row.getAttribute('data-edited') === 'true';
    const editSlot = row.querySelector('.edit-badge-slot');

    if (isEdited) {
        row.setAttribute('data-edited', 'true');
        row.classList.add('row-edited');
        if (editSlot && !editSlot.innerHTML) {
            editSlot.innerHTML = '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>';
        }
        if (!wasEdited && pulseOnEdit) {
            triggerRowPulseHighlight(row);
        }
    } else {
        row.removeAttribute('data-edited');
        row.classList.remove('row-edited');
        if (editSlot) editSlot.innerHTML = '';
    }

    // Perbarui logo khusus Catatan AI di baris tabel utama (tetap 13 kolom)
    const aiSlot = row.querySelector('.ai-note-badge-slot');
    if (aiSlot) {
        aiSlot.innerHTML = '';
        if (aiNotes.length > 0) {
            const badge = document.createElement('span');
            badge.className = 'tag-ai-note';
            badge.title = aiNotes;
            badge.innerHTML = '<i class="fas fa-robot"></i> Catatan AI';
            aiSlot.appendChild(badge);
        }
    }

    // Sinkronkan tag modal jika baris ini sedang dibuka di modal pratinjau
    if (typeof currentInspectedRowIndex !== 'undefined' && row.id === `row-${currentInspectedRowIndex}`) {
        const modalTagSlot = document.getElementById('modal-edit-tag-slot');
        if (modalTagSlot) {
            modalTagSlot.innerHTML = isEdited ? '<span class="tag-manual"><i class="fas fa-pen"></i> Dikoreksi</span>' : '';
        }
    }

    // Sinkronkan ke Celengan Feedback AI persisten di backend
    if (typeof queueFeedbackSyncForRow === 'function') {
        queueFeedbackSyncForRow(row, isEdited);
    }

    return isEdited;
}

function markRowAsEdited(row) {
    return evaluateRowEditedState(row, true);
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
