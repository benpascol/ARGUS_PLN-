/**
 * Module: feedback_vault.js
 * Deskripsi: Penghubung Celengan Feedback AI persisten di backend (/api/feedback/*).
 *            Menyimpan otomatis setiap koreksi & Catatan Model AI ke harddisk lokal
 *            sehingga aman dari Refresh browser (F5) maupun tombol Reset Tabel.
 *            Otomatis dikemas menjadi paket rilis ZIP saat genap 1.000 kasus.
 * Lead Engineer: Benedictus Pascal
 */

let currentVaultCount = 0;
let currentVaultTarget = 1000;
let latestVaultReleases = [];

const pendingVaultUpserts = new Map(); // key -> row element
const pendingVaultRemovals = new Set(); // key string
let vaultSyncTimer = null;

function buildVaultKey(idpel, filename) {
    const cleanId = String(idpel || 'NOID').replace(/[^a-zA-Z0-9_-]/g, '');
    const baseName = String(filename || 'unknown.jpg').split(/[\\/]/).pop();
    const cleanName = baseName.replace(/[^a-zA-Z0-9._-]/g, '');
    return `${cleanId}__${cleanName}`;
}

function updateVaultHeaderBadge(count, target, releases = null) {
    currentVaultCount = Number(count) || 0;
    currentVaultTarget = Number(target) || 1000;
    if (Array.isArray(releases)) {
        latestVaultReleases = releases;
    }

    const textEl = document.getElementById('ai-vault-count-text');
    const pillEl = document.getElementById('ai-vault-badge');
    if (textEl) {
        textEl.textContent = `Celengan AI: ${currentVaultCount} / ${currentVaultTarget}`;
    }
    if (pillEl) {
        if (latestVaultReleases.length > 0 && currentVaultCount === 0) {
            pillEl.classList.add('milestone-ready');
        } else {
            pillEl.classList.remove('milestone-ready');
        }
    }
}

async function fetchVaultStatus() {
    try {
        const resp = await fetch('/api/feedback/status');
        if (!resp.ok) return;
        const data = await resp.json();
        updateVaultHeaderBadge(data.staging_count, data.target, data.releases);
    } catch (err) {
        console.warn('Gagal memeriksa status Celengan AI:', err);
    }
}

async function buildFeedbackItemPayload(row) {
    const idpel = row.getAttribute('data-idpel') || '';
    const filename = row.getAttribute('data-photo') || '';
    const nama = row.querySelector('strong') ? row.querySelector('strong').textContent.trim() : '';
    const tarifDaya = row.cells[3] ? row.cells[3].textContent.trim() : '';
    const stanLapInput = row.querySelectorAll('.input-table')[0];
    const stanArgusInput = row.querySelector('.cell-argus');
    const statusSelect = row.querySelector('.select-status');

    const stanLap = stanLapInput ? stanLapInput.value.trim() : '';
    const correctedArgus = stanArgusInput ? stanArgusInput.value.trim() : '-';
    const correctedStatus = row.getAttribute('data-status') || (statusSelect ? statusSelect.value : 'PENDING');

    const origArgus = row.getAttribute('data-orig-argus') || '-';
    const origStatus = row.getAttribute('data-orig-status') || 'PENDING';
    const aiNotes = (row.getAttribute('data-ai-notes') || '').trim();

    const blurScore = parseFloat(row.getAttribute('data-blur')) || 0.0;
    const glareRatio = parseFloat(row.getAttribute('data-glare')) || 0.0;

    let imageBase64 = null;
    if (row._photoBlob && typeof imageToBase64 === 'function') {
        try {
            const imgEl = row.querySelector('.photo-thumbnail');
            imageBase64 = await imageToBase64(imgEl ? imgEl.src : '', filename);
        } catch (e) {
            imageBase64 = null;
        }
    }

    const meta = row._aiPrelabelMeta || {};
    return {
        idpel,
        nama,
        tarif_daya: tarifDaya,
        filename,
        stan_lapangan: stanLap,
        orig_argus: origArgus,
        corrected_argus: correctedArgus,
        orig_status: origStatus,
        corrected_status: correctedStatus,
        ai_notes: aiNotes,
        blur_score: blurScore,
        glare_ratio: glareRatio,
        counter_box: meta.counter_box || null,
        crop_shape: meta.crop_shape || null,
        digits_detail: meta.digits_detail || null,
        image_base64: imageBase64
    };
}

function queueFeedbackSyncForRow(row, isEditedOrHasAiNote) {
    if (!row) return;
    const idpel = row.getAttribute('data-idpel') || '';
    const filename = row.getAttribute('data-photo') || '';
    if (!filename) return;

    const key = buildVaultKey(idpel, filename);
    if (isEditedOrHasAiNote) {
        pendingVaultRemovals.delete(key);
        pendingVaultUpserts.set(key, row);
    } else {
        pendingVaultUpserts.delete(key);
        pendingVaultRemovals.add(key);
    }

    if (vaultSyncTimer) clearTimeout(vaultSyncTimer);
    vaultSyncTimer = setTimeout(() => {
        flushPendingVaultSync();
    }, 650);
}

async function flushPendingVaultSync() {
    if (vaultSyncTimer) {
        clearTimeout(vaultSyncTimer);
        vaultSyncTimer = null;
    }
    if (pendingVaultUpserts.size === 0 && pendingVaultRemovals.size === 0) {
        return null;
    }

    const rowsToSync = Array.from(pendingVaultUpserts.values());
    const keysToRemove = Array.from(pendingVaultRemovals.values());
    pendingVaultUpserts.clear();
    pendingVaultRemovals.clear();

    const upsertPayloads = [];
    for (const r of rowsToSync) {
        if (document.body.contains(r)) {
            upsertPayloads.push(await buildFeedbackItemPayload(r));
        }
    }

    if (upsertPayloads.length === 0 && keysToRemove.length === 0) {
        return null;
    }

    try {
        const resp = await fetch('/api/feedback/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                upsert: upsertPayloads,
                remove_keys: keysToRemove
            })
        });
        if (!resp.ok) return null;
        const result = await resp.json();
        updateVaultHeaderBadge(result.staging_count, result.target, result.releases);

        if (result.milestone_triggered && typeof showToast === 'function') {
            showToast(
                `Target 1.000 Kasus Tercapai! Paket Rilis AI (${result.release_zip_name}) siap di folder data/feedback_releases/.`,
                'success'
            );
        }
        return result;
    } catch (err) {
        console.warn('Gagal menyinkronkan ke Celengan Feedback AI:', err);
        return null;
    }
}

async function flushAllEditedFeedbackToVault() {
    const rows = document.querySelectorAll('#table-body tr:not(#empty-state-row)');
    rows.forEach((r) => {
        const isEdited = r.getAttribute('data-edited') === 'true';
        const hasAiNotes = (r.getAttribute('data-ai-notes') || '').trim().length > 0;
        if (isEdited || hasAiNotes) {
            const key = buildVaultKey(r.getAttribute('data-idpel'), r.getAttribute('data-photo'));
            pendingVaultRemovals.delete(key);
            pendingVaultUpserts.set(key, r);
        }
    });
    return await flushPendingVaultSync();
}

function renderVaultManagerModal() {
    const pct = Math.min(100, Math.round((currentVaultCount / Math.max(1, currentVaultTarget)) * 100));
    const counterEl = document.getElementById('vault-modal-counter');
    const fillEl = document.getElementById('vault-modal-progress-fill');
    const countLabelEl = document.getElementById('vault-releases-count');
    const listEl = document.getElementById('vault-releases-list');
    const pkgBtn = document.getElementById('btn-vault-package-now');

    if (counterEl) {
        counterEl.textContent = `${currentVaultCount} / ${currentVaultTarget} (${pct}%)`;
    }
    if (fillEl) {
        fillEl.style.width = `${pct}%`;
    }
    if (pkgBtn) {
        pkgBtn.disabled = currentVaultCount <= 0;
    }
    if (countLabelEl) {
        countLabelEl.textContent = `${latestVaultReleases.length} paket`;
    }
    if (listEl) {
        if (!latestVaultReleases.length) {
            listEl.innerHTML = '<div class="vault-release-empty">Belum ada paket rilis ZIP yang terbentuk.</div>';
        } else {
            listEl.innerHTML = latestVaultReleases.map((rel) => {
                const safeName = String(rel.filename || '').replace(/[<>&"']/g, '');
                const sizeKb = Number(rel.size_kb || 0);
                const dlUrl = `/api/feedback/download/${encodeURIComponent(rel.filename)}`;
                return `
                    <div class="vault-release-item">
                        <div class="vault-release-meta">
                            <span class="vault-release-name" title="${safeName}">${safeName}</span>
                            <span class="vault-release-size">${sizeKb} KB</span>
                        </div>
                        <a class="btn btn-secondary" style="padding:4px 10px; font-size:11.5px; text-decoration:none;" href="${dlUrl}" target="_blank" rel="noopener">
                            <i class="fas fa-download"></i> Unduh
                        </a>
                    </div>
                `;
            }).join('');
        }
    }
}

function closeVaultManagerModal() {
    const modal = document.getElementById('modal-vault-manager');
    if (modal) modal.style.display = 'none';
}

async function triggerManualVaultPackage() {
    if (currentVaultCount <= 0) return;
    const btn = document.getElementById('btn-vault-package-now');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Mengemas ZIP...';
    }
    try {
        await flushAllEditedFeedbackToVault();
        const resp = await fetch('/api/feedback/package-now', { method: 'POST' });
        const result = await resp.json();
        updateVaultHeaderBadge(result.staging_count, result.target, result.releases);
        renderVaultManagerModal();
        if (typeof showToast === 'function') {
            if (result.packaged) {
                showToast(`Paket ZIP (${result.release_zip_name}) berhasil dibuat dari ${result.packaged_count} kasus.`, 'success');
            } else {
                showToast(result.message || 'Belum ada data di staging untuk dikemas.', 'info');
            }
        }
    } catch (err) {
        console.warn('Gagal mengemas paket Celengan AI:', err);
        if (typeof showToast === 'function') {
            showToast('Gagal mengemas paket Celengan AI.', 'error');
        }
    } finally {
        if (btn) {
            btn.innerHTML = '<i class="fas fa-file-zipper"></i> Kemas Paket Sekarang';
            btn.disabled = currentVaultCount <= 0;
        }
    }
}

function showVaultInfo() {
    const modal = document.getElementById('modal-vault-manager');
    if (modal) {
        renderVaultManagerModal();
        modal.style.display = 'flex';
    }
    fetchVaultStatus().then(() => {
        renderVaultManagerModal();
    });
}

