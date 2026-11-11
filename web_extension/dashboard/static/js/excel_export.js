/**
 * Module: excel_export.js
 * Deskripsi: Penarikan berkas laporan audit Excel resmi ber-hyperlink
 *            langsung ke backend openpyxl di /api/export-audit-excel.
 * Lead Engineer: Pascol
 */

async function exportOfficialExcel() {
    const btn = document.getElementById('btn-export-excel');
    if (!btn) return;
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyusun Excel Resmi...';

    const rows = document.querySelectorAll('#table-body tr');
    const payloadRows = [];

    rows.forEach((r, idx) => {
        const idpel = r.querySelector('.idpel-code').textContent.trim();
        const nama = r.querySelector('strong').textContent.trim();
        const tarif = r.cells[3].textContent.trim();
        const stanLap = r.querySelectorAll('.input-table')[0].value.trim();
        const rawAi = r.querySelector('.cell-raw').textContent.trim();
        const stanArgus = r.querySelector('.cell-argus').value.trim();
        const diff = r.querySelector('.cell-diff').textContent.trim();
        const sel = r.querySelector('.select-status');
        const verdict = sel.value;
        const isEdited = r.getAttribute('data-edited') === 'true';
        const notes = r.querySelector('.input-notes').value.trim();
        const lat = parseFloat(r.querySelector('.cell-lat').textContent) || 0.0;
        const blur = parseFloat(r.getAttribute('data-blur')) || 0.0;
        const glare = parseFloat(r.getAttribute('data-glare')) || 0.0;
        const tier = r.getAttribute('data-tier') || 'GREEN';
        const photoFile = r.getAttribute('data-photo');

        payloadRows.push({
            no: idx + 1,
            idpel: idpel,
            nama: nama,
            tarif_daya: tarif,
            kdbaca: "F",
            stan_lapangan: stanLap,
            raw_display: rawAi,
            stan_argus: stanArgus,
            selisih: diff,
            verdict: verdict,
            diagnosa_detail: notes || (verdict === 'MATCH' ? 'SESUAI IDEAL (5 Digit)' : 'Audit Dashboard'),
            tier_color: tier,
            latency_ms: lat,
            blur_score: blur,
            glare_ratio: glare,
            filename: photoFile,
            is_edited: isEdited,
            notes: notes
        });
    });

    try {
        const resp = await fetch('/api/export-audit-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows: payloadRows })
        });

        if (!resp.ok) throw new Error("Gagal mengekspor laporan Excel");

        const blob = await resp.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `Audit_LBKB_Result_ARGUS_V5_Official_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
        if (typeof showToast === 'function') {
            showToast("Laporan Excel resmi berhasil diunduh.", "success");
        }
    } catch (err) {
        alert("Gagal mengunduh Excel resmi: " + err.message);
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}
