// ==UserScript==
// @name         Dashboard Evaluasi Foto KWH Meter + AI OCR (Enterprise Edition)
// @namespace    http://BWX.net/
// @version      89.00
// @description  High-Performance, Modular Dashboard with ARGUS 100% Local AI Vision Engine
// @author       703703 & Benedictus Pascal (Tim ARGUS PLN UP3 Mojokerto)
// @match        https://portalapp.iconpln.co.id/*
// @match        http://127.0.0.1:8000/simulator*
// @match        http://localhost:8000/simulator*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      portalapp.iconpln.co.id
// @connect      127.0.0.1
// @connect      localhost
// @connect      cdn.jsdelivr.net
// @connect      cdnjs.cloudflare.com
// @connect      fonts.googleapis.com
// @connect      fonts.gstatic.com
// @connect      upload.wikimedia.org
// @require      https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js
// @require      https://cdn.jsdelivr.net/npm/chart.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function() {
    'use strict';

    const currentPath = window.location.pathname.toLowerCase();
    if (currentPath === '/' || currentPath === '/acmt/' || currentPath.includes('/login') || currentPath.includes('/logon')) {
        console.log('[Dashboard] Halaman login terdeteksi, script tidak aktif.');
        return;
    }

    // ==========================================
    // 1. CONFIG & STATE MANAGEMENT
    // ==========================================
    const Config = {
        PING_INTERVAL: 120000,
        PING_URL: 'https://portalapp.iconpln.co.id/acmt/main/Main.html',
        OCR_MAX_RETRIES: 1,
        OCR_CONCURRENCY: 5,
        CACHE_MAX_AGE: 86400000
    };

    const State = {
        theme: GM_getValue('PLN_THEME', 'light'),
        apiKey: (function() { const k = GM_getValue('API_KEY', 'http://127.0.0.1:8000'); return (k && !k.startsWith('nvapi-')) ? k : 'http://127.0.0.1:8000'; })(),
        userLogin: GM_getValue('ACMT_USER_LOGIN', ''),
        pdfData: GM_getValue('PDF_DATA', { uid: '', up3: '', ulp: '', koor: '', manager: '', tl: '' }),
        ocrCache: GM_getValue('OCR_CACHE', {}),
        photoCache: GM_getValue('PHOTO_CACHE', {}),
        customerData: {},
        customPhotos: {},
        charts: {},
        sortState: { col: null, dir: 'a' },
        dragMode: null,
        isAutoOcrRunning: false
    };

    // ==========================================
    // 2. UTILITY CLASS
    // ==========================================
    class Utils {
        static debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        }

        static isCacheValid(entry) {
            return !!(entry && entry.ts && (Date.now() - entry.ts) < Config.CACHE_MAX_AGE);
        }

        static cleanupCache() {
            let changed = false;
            Object.keys(State.ocrCache).forEach(key => {
                const entry = State.ocrCache[key];
                if (!this.isCacheValid(entry) || entry.validasi_ocr !== 'Valid') {
                    delete State.ocrCache[key];
                    changed = true;
                }
            });
            
            const photoKeys = Object.keys(State.photoCache);
            if (photoKeys.length > 150) {
                for(let i = 0; i < 50; i++) {
                    delete State.photoCache[photoKeys[i]];
                }
                GM_setValue('PHOTO_CACHE', State.photoCache);
            }
            
            if (changed) GM_setValue('OCR_CACHE', State.ocrCache);
        }

        static getMonthLabel(b) {
            if (!b || b.length !== 6) return b;
            return ['JAN','FEB','MAR','APR','MEI','JUN','JUL','AGS','SEP','OKT','NOV','DES'][parseInt(b.substring(4,6))-1] + ' ' + b.substring(0,4);
        }
    }

    // ==========================================
    // 3. API MANAGER (GWT-RPC & NVIDIA OCR)
    // ==========================================
    class APIManager {
        static async fetchCustomerData(id) {
            const u = State.userLogin ? State.userLogin.split('.')[0] : id.substring(0, 5);
            const b = `7|0|15|https://portalapp.iconpln.co.id/acmt/main/|58DED5E133887EABD5AC8356EC9D20CD|id.co.iconpln.client.app.service.IpamService|getUtilDao|java.lang.String/2004016611|java.util.Map||com.extjs.gxt.ui.client.core.FastMap/3488076414|code|idpel|${id}|unitup|${u}|func_name|FG_INFOPELANGGAN|1|2|3|4|2|5|6|7|8|4|5|9|5|7|5|10|5|11|5|12|5|13|5|14|5|15|`;
            
            return new Promise((res, rej) => {
                GM_xmlhttpRequest({
                    method: "POST", url: "https://portalapp.iconpln.co.id/acmt/main/c",
                    headers: { "Content-Type": "text/x-gwt-rpc; charset=UTF-8", "X-GWT-Module-Base": "https://portalapp.iconpln.co.id/acmt/main/", "X-GWT-Permutation": "B9E26BF22D1498A28BFA7AA5E0A41AF6" },
                    data: b,
                    onload: function(r) { if(r.status !== 200) rej(new Error("HTTP " + r.status)); else if(r.responseText.startsWith("//EX")) rej(new Error("GWT Exception")); else res(r.responseText); },
                    onerror: function() { rej(new Error("Network Error")); },
                    ontimeout: function() { rej(new Error("Request Timeout")); }
                });
            }).then(rs => APIManager.parseGwtResponse(rs)).catch(() => null);
        }

        static parseGwtResponse(rs) {
            try {
                if(!rs || !rs.startsWith("//OK")) return null;
                const pm = rs.match(/\[\s*".*?"\s*\]/); if(!pm) return null;
                const sp = JSON.parse(pm[0]);
                const gv = (k) => { const i = sp.indexOf(k); if(i !== -1 && i + 1 < sp.length) { let v = sp[i + 1]; const ak = ["idpel","nama","tarif","daya","stand_lalu","stan_baca","stan_meter","jamnyala","petugas","kdbaca_ver","kdbaca2","kdbaca3","blth","nomor_meter","kode_rbm","gardu","tiang","pemkwh","unitup","pakai_bln_lalu","pemkwhlalu","pakailalu","pakai_lalu"]; if(v && !ak.includes(v)) return v; } return "-"; };
                
                const idpel=gv("idpel"), nama=gv("nama"), tarif=gv("tarif"), daya=gv("daya"), stand_lalu=gv("stand_lalu"), stan_baca=gv("stan_baca"), jamnyala=gv("jamnyala"), petugas=gv("petugas"), nomor_meter=gv("nomor_meter"), kode_rbm=gv("kode_rbm"), gardu=gv("gardu"), tiang=gv("tiang"), pemkwh=gv("pemkwh"), unitup=gv("unitup");
                let lbkb=gv("kdbaca2"); if(lbkb==="-")lbkb=gv("kdbaca_ver"); if(lbkb==="-")lbkb=gv("kdbaca3"); if(lbkb==="-")lbkb=gv("kdbaca");
                
                let pakai_bln_lalu = gv("pakai_bln_lalu"); if (pakai_bln_lalu === "-") pakai_bln_lalu = gv("pemkwhlalu"); if (pakai_bln_lalu === "-") pakai_bln_lalu = gv("pakailalu");
                
                if (pakai_bln_lalu === "-") {
                    pakai_bln_lalu = 0; 
                    const idxStanMeter = sp.indexOf("stan_meter");
                    if (idxStanMeter !== -1) {
                        // FIX DEFINITIF: Cari index blth historis (format 6 digit angka) setelah "stan_meter"
                        // untuk menghindari kesalahan offset karena ada/tidak adanya URL foto historis
                        let idxPrevBlth = -1;
                        for (let i = idxStanMeter + 1; i < sp.length; i++) {
                            if (/^\d{6}$/.test(sp[i])) {
                                idxPrevBlth = i;
                                break;
                            }
                        }
                        
                        // Stan Baca bulan lalu (9744) selalu berada 2 index sebelum blth (202607)
                        if (idxPrevBlth !== -1 && (idxPrevBlth - 2) >= 0) {
                            const histStanBaca = parseInt(sp[idxPrevBlth - 2]) || 0; 
                            const sl = parseInt(stand_lalu) || 0; 
                            if (sl > 0 && histStanBaca > 0 && sl >= histStanBaca) { 
                                pakai_bln_lalu = sl - histStanBaca; 
                            } 
                        }
                    }
                }
                
                return {
                    idpel: idpel!=="-"?idpel:(sp.find(s=>s.length===12&&/^\d+$/.test(s))||"-"), 
                    nama: nama!=="-"?nama:(sp.find(s=>s.includes("   ")&&s.trim().length>3)?.trim()||"-"),
                    tarif: tarif!=="-"?tarif:"R1", daya: daya!=="-"?daya:"-", stand_lalu: stand_lalu!=="-"?stand_lalu:"0", stan_baca: stan_baca!=="-"?stan_baca:"0", jamnyala: jamnyala!=="-"?jamnyala:"0", petugas: petugas!=="-"?petugas:"-",
                    nomor_meter: nomor_meter!=="-"?nomor_meter:"-", kode_rbm: kode_rbm!=="-"?kode_rbm:"-", gardu: gardu!=="-"?gardu:"-", tiang: tiang!=="-"?tiang:"-",
                    lbkb: lbkb, pemkwh: pemkwh, pakai_bln_lalu: pakai_bln_lalu, unitup: unitup!=="-"?unitup:"-", 
                    hasil_ocr: "-", validasi_ocr: "-", validasi_manual: "Valid", original_ocr_status: "-"
                };
            } catch(e) { console.error('[Dashboard] Parse Error:', e); return null; }
        }

        static async fetchImage(url) {
            return new Promise((resolve) => {
                GM_xmlhttpRequest({
                    method: "GET",
                    url: url,
                    responseType: "blob",
                    onload: function(response) {
                        try {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(response.response);
                        } catch (e) {
                            resolve(null);
                        }
                    },
                    onerror: function() { resolve(null); },
                    ontimeout: function() { resolve(null); }
                });
            });
        }

        static async runArgusOCR(base64Image) {
            const apiBase = (State.apiKey && State.apiKey.startsWith('http')) ? State.apiKey : 'http://127.0.0.1:8000';
            const endpoint = apiBase.replace(/\/+$/, '') + '/predict-base64';
            
            const payload = {
                image_base64: base64Image,
                filename: "web_evaluator.jpg"
            };
            
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: "POST", 
                    url: endpoint, 
                    headers: { "Content-Type": "application/json" }, 
                    data: JSON.stringify(payload),
                    timeout: 20000,
                    onload: function(response) { 
                        try { 
                            const resJson = JSON.parse(response.responseText); 
                            if (resJson.error || resJson.detail) {
                                reject(new Error("ARGUS API Error: " + (resJson.error || resJson.detail))); 
                            } else {
                                resolve(resJson); 
                            }
                        } catch (e) { 
                            reject(new Error("Gagal parse respons JSON ARGUS: " + e.message)); 
                        } 
                    },
                    onerror: function() { 
                        reject(new Error("Koneksi gagal ke ARGUS Engine (Pastikan server.py aktif di http://127.0.0.1:8000)")); 
                    },
                    ontimeout: function() { 
                        reject(new Error("ARGUS Engine Timeout (20s)")); 
                    }
                });
            });
        }

        static async runNvidiaOCR(base64Image) {
            return this.runArgusOCR(base64Image);
        }

        static async submitBacaUlang(data) {
            const aktifVal = data.jenis === 'TEMPAT' ? '1' : '0';
            const payload = `7|0|23|https://portalapp.iconpln.co.id/acmt/main/|58DED5E133887EABD5AC8356EC9D20CD|id.co.iconpln.client.app.service.IpamService|getUtilDao|java.lang.String/2004016611|java.util.Map||com.extjs.gxt.ui.client.core.FastMap/3488076414|code|unitup|${data.unitup}|blth|${data.blth}|idpel|${data.idpel}|transaksiby|${data.transaksiby}|nama_ptgs|${data.nama_ptgs}|aktif|${aktifVal}|func_name|FS_BACAULANG|1|2|3|4|2|5|6|7|8|8|5|9|5|7|5|10|5|11|5|12|5|13|5|14|5|15|5|16|5|17|5|18|5|19|5|20|5|21|5|22|5|23|`;
            
            return new Promise((resolve) => {
                GM_xmlhttpRequest({
                    method: "POST", url: "https://portalapp.iconpln.co.id/acmt/main/c",
                    headers: { "Content-Type": "text/x-gwt-rpc; charset=UTF-8", "X-GWT-Module-Base": "https://portalapp.iconpln.co.id/acmt/main/", "X-GWT-Permutation": "B9E26BF22D1498A28BFA7AA5E0A41AF6" },
                    data: payload,
                    onload: function(r) { resolve(r.responseText.includes("berhasil disimpan")); },
                    onerror: function() { resolve(false); },
                    ontimeout: function() { resolve(false); }
                });
            });
        }
    }

    // ==========================================
    // 4. UI CONTROLLER (RENDERING & EVENTS)
    // ==========================================
    class UIController {
        constructor() {
            this.injectStyles();
            this.injectHTML();
            this.cacheDOM();
            this.initEvents();
            this.initCharts();
            this.initYearSelect();
        }

        injectStyles() {
            const styles = `
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
                <style>
                    :root { --pln-blue: #00A2E9; --pln-blue-dark: #007BB5; --pln-yellow: #FDB913; --primary: var(--pln-blue); --primary-dark: var(--pln-blue-dark); --primary-tint: rgba(0, 162, 233, 0.25); --accent: var(--pln-yellow); --success: #30d158; --success-tint: rgba(48,209,88,0.15); --danger: #ff3b30; --danger-text: #d70015; --danger-tint: rgba(255,59,48,0.15); --warning: #ff9500; --info: #8e8e93; --glass-bg: rgba(255, 255, 255, 0.45); --glass-surface: rgba(255, 255, 255, 0.55); --glass-well: rgba(255, 255, 255, 0.65); --glass-border: rgba(255, 255, 255, 0.8); --glass-border-strong: rgba(255, 255, 255, 1); --text: #1d1d1f; --text-muted: #4a4a4f; --header-bg: linear-gradient(135deg, #00A2E9 0%, #007BB5 100%); --table-head-bg: linear-gradient(135deg, var(--pln-blue) 0%, var(--pln-blue-dark) 100%); --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); --radius-sm: 8px; --radius-md: 12px; --radius-lg: 18px; --radius-pill: 980px; --ease: cubic-bezier(0.22, 1, 0.36, 1); }
                    [data-pln-theme="dark"] { --glass-bg: rgba(18, 18, 22, 0.65); --glass-surface: rgba(30, 30, 35, 0.55); --glass-well: rgba(10, 10, 15, 0.45); --glass-border: rgba(255, 255, 255, 0.12); --glass-border-strong: rgba(255, 255, 255, 0.2); --text: #f5f5f7; --text-muted: #a1a1a6; --header-bg: linear-gradient(135deg, #00A2E9 0%, #005A85 100%); --glass-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.6); --danger-text: #ff453a; }
                    #pln-wrapper * { box-sizing: border-box; }
                    #pln-wrapper { position: fixed; width: min(92vw, 1450px); height: min(88vh, 820px); min-width: 700px; min-height: 450px; background: var(--glass-bg); backdrop-filter: blur(25px) saturate(180%); -webkit-backdrop-filter: blur(25px) saturate(180%); z-index: 99999; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif; -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; display: none; flex-direction: column; overflow: hidden; color: var(--text); border-radius: 20px; box-shadow: var(--glass-shadow); border: 1px solid var(--glass-border); }
                    #pln-wrapper.is-max { width: 100vw !important; height: 100vh !important; left: 0 !important; top: 0 !important; border-radius: 0; }
                    #pln-wrapper.is-dragging { transition: none !important; opacity: 0.96; box-shadow: 0 25px 70px rgba(0,0,0,0.4); }
                    #pln-wrapper .drag-header { background: var(--header-bg); color: white; padding: 13px 20px; display: flex; justify-content: space-between; align-items: center; font-weight: 600; letter-spacing: -0.01em; border-bottom: 1px solid rgba(255,255,255,0.15); cursor: grab; user-select: none; flex-shrink: 0; backdrop-filter: blur(10px); position: relative; overflow: hidden; }
                    #pln-wrapper .drag-header::after { content: ''; position: absolute; top: -50%; right: -10%; width: 200px; height: 200px; pointer-events: none; background: radial-gradient(circle, rgba(253,185,19,0.12) 0%, transparent 70%); }
                    #pln-wrapper .drag-header:active { cursor: grabbing; }
                    #pln-wrapper .header-left { display: flex; align-items: center; gap: 10px; font-size: 14.5px; pointer-events: none; }
                    #pln-wrapper .header-left i { color: var(--pln-yellow); font-size: 16px; filter: drop-shadow(0 0 8px rgba(253,185,19,0.7)); }
                    #pln-wrapper .header-right { display: flex; gap: 6px; }
                    #pln-wrapper .hdr-btn { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.25); border-radius: var(--radius-pill); cursor: pointer; padding: 6px 14px; font-weight: 600; font-size: 12px; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all .18s var(--ease); }
                    #pln-wrapper .hdr-btn:hover { background: rgba(255,255,255,0.35); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                    #pln-wrapper .hdr-btn:active { transform: scale(0.95); }
                    #pln-wrapper .hdr-btn.btn-close { background: rgba(255,59,48,0.7); border-color: rgba(255,59,48,0.5); }
                    #pln-wrapper .hdr-btn.btn-close:hover { background: #ff3b30; }
                    #btn-theme-toggle { padding: 6px 10px; }
                    #pln-wrapper .inner-container { padding: 14px 18px; overflow-y: auto; flex-grow: 1; display: flex; flex-direction: column; gap: 14px; }
                    #pln-wrapper .control-panel { background: var(--glass-surface); padding: 16px; border-radius: var(--radius-lg); border: 1px solid var(--glass-border); display: flex; flex-wrap: wrap; gap: 20px; align-items: center; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.2); }
                    #pln-wrapper .ctrl-section { display: flex; gap: 12px; align-items: flex-end; padding: 10px 14px; background: var(--glass-well); border-radius: var(--radius-md); border: 1px solid var(--glass-border-strong); flex-wrap: wrap; }
                    #pln-wrapper .ctrl-section.btn-section { background: transparent; border: none; padding: 0; gap: 8px; align-items: center; }
                    #pln-wrapper .ctrl-section.full-width { width: 100%; background: transparent; border: none; padding: 0; align-items: flex-start; }
                    #pln-wrapper .control-group { display: flex; flex-direction: column; gap: 5px; }
                    #pln-wrapper .control-group label { font-size: 10px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--text-muted); display: flex; align-items: center; }
                    #pln-wrapper select, #pln-wrapper textarea, #pln-wrapper input { padding: 8px 11px; border-radius: 9px; border: 1px solid var(--glass-border-strong); font-family: inherit; font-size: 13px; outline: none; background: var(--glass-well); color: var(--text); transition: all .18s var(--ease); }
                    #pln-wrapper select:focus, #pln-wrapper textarea:focus, #pln-wrapper input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-tint); background: var(--glass-surface); }
                    #pln-wrapper textarea { width: 200px; height: 36px; resize: none; font-family: 'SF Mono', monospace; font-size: 12px; }
                    #pln-wrapper input { width: 160px; height: 36px; font-size: 12px; }
                    .api-key-toggle-btn { background: var(--primary); color: white; border: none; border-radius: 4px; padding: 2px 6px; font-size: 9px; cursor: pointer; margin-left: 6px; transition: all .15s var(--ease); display: inline-flex; align-items: center; gap: 3px; font-weight: 700; letter-spacing: 0.02em; }
                    .api-key-toggle-btn:hover { filter: brightness(1.15); transform: scale(1.05); }
                    .api-key-content { overflow: hidden; max-height: 0; opacity: 0; transition: max-height 0.3s var(--ease), opacity 0.2s var(--ease); }
                    .api-key-content.is-open { max-height: 50px; opacity: 1; }
                    .api-key-content input { margin-top: 3px; }
                    #pln-wrapper .btn { color: white; border: none; padding: 0 16px; border-radius: var(--radius-pill); font-weight: 600; cursor: pointer; font-size: 11.5px; letter-spacing: 0.01em; height: 36px; display: flex; align-items: center; gap: 6px; transition: transform .16s var(--ease), filter .16s var(--ease), box-shadow .16s var(--ease); box-shadow: 0 4px 10px rgba(0,0,0,0.15); text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
                    #pln-wrapper .btn:hover { filter: brightness(1.15); transform: translateY(-1px); box-shadow: 0 6px 15px rgba(0,0,0,0.2); }
                    #pln-wrapper .btn:active { transform: translateY(0) scale(0.97); }
                    #pln-wrapper .btn-danger { background: var(--danger); }
                    #pln-wrapper .btn-pdf { background: #8e44ad; }
                    #pln-wrapper .btn-export { background: var(--success); }
                    #pln-wrapper .btn-ocr { background: var(--pln-blue); }
                    .chart-inline-container { display: flex; align-items: center; gap: 16px; background: var(--glass-well); padding: 6px 16px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-strong); height: 46px; }
                    .chart-box-item { display: flex; align-items: center; gap: 8px; height: 36px; }
                    .chart-box-item canvas { width: 36px !important; height: 36px !important; max-width: 36px; max-height: 36px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
                    .chart-info-text { display: flex; flex-direction: column; font-size: 10px; line-height: 1.25; font-weight: 600; color: var(--text-muted); }
                    .chart-info-text span.val-count { font-size: 12.5px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
                    #pln-wrapper .col-toggle-group { display: grid; grid-template-columns: repeat(auto-fill, minmax(125px, 1fr)); gap: 6px 10px; padding: 12px; border: 1px dashed var(--glass-border-strong); border-radius: var(--radius-md); width: 100%; background: var(--glass-surface); }
                    #pln-wrapper .col-toggle-item { display: flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 600; color: var(--text-muted); cursor: pointer; white-space: nowrap; }
                    #pln-wrapper .col-toggle-item input { accent-color: var(--primary); cursor: pointer; width: 13px; height: 13px; flex-shrink: 0; }
                    #pln-wrapper .table-wrapper { background: var(--glass-surface); border-radius: var(--radius-lg); overflow: hidden; border: 1px solid var(--glass-border); width: 100%; flex-grow: 1; display: flex; flex-direction: column; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.1); min-height: 0; }
                    #pln-wrapper .table-scroll { overflow-x: auto; overflow-y: auto; width: 100%; flex-grow: 1; min-height: 0; }
                    #pln-wrapper table { width: 100%; border-collapse: collapse; font-size: 12px; table-layout: auto; }
                    #pln-wrapper thead { background: var(--table-head-bg); color: white; position: sticky; top: 0; z-index: 10; backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); }
                    #pln-wrapper th { padding: 11px 7px; text-align: center; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; font-size: 9.5px; white-space: nowrap; border: 1px solid rgba(255,255,255,0.08); cursor: pointer; }
                    #pln-wrapper th .sort-icon { font-size: 9px; margin-left: 3px; opacity: 0.55; }
                    #pln-wrapper td { padding: 8px 5px; border: 1px solid var(--glass-border-strong); text-align: center; vertical-align: middle; font-size: 12px; color: var(--text); background: transparent; }
                    #pln-wrapper tbody tr { transition: background .15s ease; }
                    #pln-wrapper tbody tr:hover { background-color: var(--primary-tint); }
                    #pln-wrapper .photo-container { position: relative; width: 200px; height: 200px; margin: 0 auto; background: rgba(0,0,0,0.15); border-radius: var(--radius-md); overflow: hidden; cursor: zoom-in; border: 1px solid var(--glass-border-strong); transition: all .18s var(--ease); }
                    #pln-wrapper .photo-container:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.25); }
                    #pln-wrapper .reset-photo-btn, #pln-wrapper .ocr-photo-btn, #pln-wrapper .crop-photo-btn { position: absolute; z-index: 10; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: bold; display: none; backdrop-filter: blur(6px); box-shadow: 0 2px 8px rgba(0,0,0,0.35); }
                    #pln-wrapper .reset-photo-btn { top: 6px; right: 6px; background: rgba(255,59,48,0.88); color: white; width: 24px; height: 24px; border-radius: 50%; font-size: 15px; }
                    #pln-wrapper .crop-photo-btn { top: 6px; left: 6px; background: rgba(0,162,233,0.88); color: white; width: 24px; height: 24px; border-radius: 50%; font-size: 12px; }
                    #pln-wrapper .ocr-photo-btn { bottom: 6px; right: 6px; background: rgba(0,162,233,0.88); color: white; padding: 4px 10px; font-size: 10px; border-radius: var(--radius-pill); }
                    #pln-wrapper .photo-container:hover .reset-photo-btn, #pln-wrapper .photo-container:hover .ocr-photo-btn, #pln-wrapper .photo-container:hover .crop-photo-btn { display: flex; align-items: center; justify-content: center; }
                    #pln-wrapper .col-photo-box { width: 100%; height: 100%; object-fit: contain; background: transparent; pointer-events: none; transition: transform 0.2s ease; }
                    #pln-wrapper select.sel-validasi { padding: 5px 10px; border-radius: var(--radius-pill); border: 1px solid var(--glass-border-strong); font-size: 11px; font-weight: 700; cursor: pointer; color: var(--text); transition: all .18s var(--ease); }
                    #pln-wrapper select.sel-validasi.val-valid { background: var(--success-tint); color: #1c8b3f; border-color: rgba(48,209,88,0.4); }
                    [data-pln-theme="dark"] #pln-wrapper select.sel-validasi.val-valid { color: #30d158; }
                    #pln-wrapper select.sel-validasi.val-tidak { background: var(--danger-tint); color: var(--danger-text); border-color: rgba(255,59,48,0.35); }
                    #pln-wrapper #resize-handle { position: absolute; bottom: 0; right: 0; width: 20px; height: 20px; cursor: nwse-resize; z-index: 100000; }
                    #pln-modal-zoom, #pln-bu-overlay, #pln-pdf-overlay, #pln-crop-overlay { font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; }
                    #pln-modal-zoom { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); backdrop-filter: blur(10px); z-index: 9999999; cursor: none; }
                    #pln-modal-zoom #modal-img { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-width: 90vw; max-height: 90vh; object-fit: contain; background: transparent; border-radius: 8px; pointer-events: none; }
                    #pln-modal-zoom #modal-close { position: absolute; top: 20px; right: 30px; color: white; font-size: 30px; cursor: pointer; z-index: 99999999; }
                    #pln-modal-zoom #modal-loupe { position: fixed; width: 250px; height: 250px; border-radius: 50%; overflow: hidden; border: 5px solid rgba(255,255,255,0.9); pointer-events: none; display: none; z-index: 99999998; background: #000; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
                    #pln-modal-zoom #loupe-img { position: absolute; object-fit: contain; background: #000; }
                    #pln-bu-overlay, #pln-pdf-overlay, #pln-crop-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); z-index: 1000000; display: none; justify-content: center; align-items: center; }
                    
                    #pln-bu-overlay #bu-modal, #pln-pdf-overlay #pdf-modal, #pln-crop-overlay #crop-modal { background: var(--glass-bg); padding: 0; border-radius: var(--radius-lg); width: 500px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.4); overflow: hidden; border: 1px solid var(--glass-border); transform: scale(0.95); animation: modalPopIn 0.2s var(--ease) forwards; color: var(--text); }
                    #pln-crop-overlay #crop-modal { width: 600px; }
                    @keyframes modalPopIn { to { transform: scale(1); } }
                    #pln-bu-overlay h3, #pln-pdf-overlay h3, #pln-crop-overlay h3 { margin: 0; padding: 18px 24px; color: white; display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.15); background: linear-gradient(135deg, var(--pln-blue) 0%, var(--pln-blue-dark) 100%); position: relative; overflow: hidden; }
                    #pln-bu-overlay h3::after, #pln-pdf-overlay h3::after, #pln-crop-overlay h3::after { content: ''; position: absolute; top: -50%; right: -5%; width: 150px; height: 150px; pointer-events: none; background: radial-gradient(circle, rgba(253,185,19,0.1) 0%, transparent 70%); }
                    #pln-bu-overlay h3 i, #pln-pdf-overlay h3 i, #pln-crop-overlay h3 i { color: var(--pln-yellow); filter: drop-shadow(0 0 6px rgba(253,185,19,0.6)); }
                    #pln-bu-overlay .modal-content, #pln-pdf-overlay .modal-content, #pln-crop-overlay .modal-content { padding: 24px; color: var(--text); }
                    #pln-bu-overlay .modal-content > div { color: var(--text); }
                    #pln-bu-overlay .modal-content > div strong { color: var(--text); }
                    #pln-bu-overlay .bu-form-group, #pln-pdf-overlay .pdf-form-group { margin-bottom: 18px; display: flex; flex-direction: column; }
                    #pln-bu-overlay .bu-form-group label, #pln-pdf-overlay .pdf-form-group label { font-size: 11px; font-weight: 700; margin-bottom: 8px; color: var(--text-muted); text-transform: uppercase; }
                    #pln-bu-overlay .bu-form-group input, #pln-bu-overlay .bu-form-group select, #pln-pdf-overlay .pdf-form-group input { width: 100%; padding: 11px 13px; border: 1px solid var(--glass-border-strong); border-radius: 10px; font-size: 14px; font-family: inherit; transition: all 0.18s var(--ease); background: var(--glass-well); color: var(--text); }
                    #pln-bu-overlay .bu-form-group input:focus, #pln-bu-overlay .bu-form-group select:focus, #pln-pdf-overlay .pdf-form-group input:focus { border-color: var(--primary); box-shadow: 0 0 0 4px var(--primary-tint); background: var(--glass-surface); }
                    #pln-pdf-overlay .pdf-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
                    #pln-pdf-overlay .pdf-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 18px; }
                    #pln-pdf-overlay .pdf-divider { border: none; border-top: 1px solid var(--glass-border-strong); margin: 20px 0; }
                    #pln-pdf-overlay .pdf-subtitle { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin: 0 0 15px; font-weight: 700; }
                    #pln-bu-overlay .bu-btn-group, #pln-pdf-overlay .pdf-btn-group, #pln-crop-overlay .crop-btn-group { display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px; }
                    #pln-bu-overlay .bu-btn, #pln-pdf-overlay .pdf-btn, #pln-crop-overlay .crop-btn { padding: 11px 22px; border: none; border-radius: var(--radius-pill); cursor: pointer; font-weight: 600; font-size: 14px; color: white; transition: all .16s var(--ease); text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
                    #pln-bu-overlay .bu-btn:hover, #pln-pdf-overlay .pdf-btn:hover, #pln-crop-overlay .crop-btn:hover { filter: brightness(1.15); transform: translateY(-1px); }
                    #pln-bu-overlay .bu-btn-cancel, #pln-pdf-overlay .pdf-btn-cancel, #pln-crop-overlay .crop-btn-cancel { background: var(--danger); box-shadow: 0 4px 12px rgba(255,59,48,0.3); }
                    #pln-bu-overlay .bu-btn-cancel:hover, #pln-pdf-overlay .pdf-btn-cancel:hover, #pln-crop-overlay .crop-btn-cancel:hover { filter: brightness(1.1); box-shadow: 0 6px 18px rgba(255,59,48,0.5); }
                    #pln-bu-overlay .bu-btn-submit, #pln-pdf-overlay .pdf-btn-submit, #pln-crop-overlay .crop-btn-submit { background: linear-gradient(135deg, var(--pln-blue) 0%, var(--pln-blue-dark) 100%); box-shadow: 0 4px 12px rgba(0,162,233,0.3); }
                    #pln-bu-overlay .bu-btn-submit:hover, #pln-pdf-overlay .pdf-btn-submit:hover, #pln-crop-overlay .crop-btn-submit:hover { filter: brightness(1.1); box-shadow: 0 6px 18px rgba(0,162,233,0.5); }
                    #pln-crop-overlay .crop-img-container { width: 100%; max-height: 60vh; overflow: hidden; background: #000; border-radius: 8px; }
                    #pln-crop-overlay #crop-img { max-width: 100%; display: block; }
                    #btn-toggle-dashboard { position: fixed; bottom: 24px; right: 24px; z-index: 99998; background: linear-gradient(135deg, var(--pln-yellow) 0%, #D49800 100%); color: #1A1A1A; border: none; padding: 15px 24px; border-radius: var(--radius-pill); cursor: pointer; font-weight: 800; font-family: inherit; font-size: 13px; letter-spacing: 0.02em; box-shadow: 0 10px 30px rgba(253, 185, 19, 0.45); display: flex; align-items: center; gap: 8px; transition: all .2s var(--ease); }
                    #btn-toggle-dashboard:hover { transform: translateY(-3px) scale(1.03); box-shadow: 0 15px 40px rgba(253, 185, 19, 0.6); }
                    #pln-print-area { display: none; }
                    @media print { body * { visibility: hidden; } #pln-print-area, #pln-print-area * { visibility: visible; } #pln-print-area { display: block; position: absolute; left: 0; top: 0; width: 100%; padding: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; } @page { size: A4 landscape; margin: 8mm; } .print-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--pln-blue); padding-bottom: 15px; margin-bottom: 20px; } .print-header-left { display: flex; align-items: center; gap: 20px; } .print-header-left img { height: 60px; width: auto; } .print-header-left .portal-text { font-size: 16px; color: var(--pln-blue); line-height: 1.4; border-left: 3px solid var(--pln-blue); padding-left: 20px; font-weight: bold; } .print-header-left .portal-text span { font-size: 12px; color: #555; font-weight: normal; } .print-header-right { text-align: right; font-size: 14px; line-height: 1.6; font-weight: bold; } .print-title { text-align: center; font-size: 16px; font-weight: bold; margin: 20px 0; text-transform: uppercase; } .print-summary { display: flex; align-items: center; justify-content: space-between; border: 1.5px solid #111; border-radius: 10px; padding: 12px 20px; margin: 0 0 18px 0; background: #fafafa; -webkit-print-color-adjust: exact; print-color-adjust: exact; } .print-summary-text { flex: 1; } .print-summary-title { font-size: 11px; font-weight: bold; text-transform: uppercase; color: #555; margin-bottom: 8px; } .print-summary-legend { display: flex; gap: 30px; flex-wrap: wrap; } .print-summary-item { display: flex; align-items: center; gap: 8px; font-size: 12px; } .print-summary-dot { width: 12px; height: 12px; border-radius: 4px; display: inline-block; -webkit-print-color-adjust: exact; print-color-adjust: exact; } .print-summary-charts { display: flex; gap: 25px; align-items: center; justify-content: flex-end; padding-left: 20px; border-left: 1px solid #ccc; } .print-chart-item { display: flex; flex-direction: column; align-items: center; gap: 3px; width: 80px; } .print-chart-item img { width: 65px; height: 65px; object-fit: contain; } .print-chart-item span { font-size: 9px; font-weight: bold; color: #555; text-align: center; line-height: 1.2; } .print-chart-item .chart-val { font-size: 10px; color: #111; } .print-table-container { width: 100%; border: 1.5px solid #111; border-radius: 10px; overflow: hidden; } .print-table { width: 100%; border-collapse: collapse; table-layout: auto; margin: 0 auto; } .print-table thead th { background-color: var(--pln-blue-dark) !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; border: 1px solid #333 !important; padding: 8px 5px; font-size: 11px !important; text-align: center; } .print-table td { border: 1px solid #ccc !important; padding: 6px 4px; font-size: 11px !important; text-align: center; -webkit-print-color-adjust: exact; print-color-adjust: exact; } .print-table .sort-icon, .print-table .reset-photo-btn, .print-table .ocr-photo-btn, .print-table .crop-photo-btn { display: none !important; } #pln-print-area .photo-container { width: 100px !important; height: 100px !important; border: none !important; background: #fff !important; border-radius: 0 !important; cursor: default !important; overflow: hidden !important; } #pln-print-area .col-photo-box { width: 100% !important; height: 100% !important; object-fit: contain !important; } .print-signatures { display: flex; justify-content: space-between; margin-top: 50px; width: 100%; padding: 0 40px; align-items: stretch; } .sig-col { text-align: center; width: 30%; font-size: 12px; display: flex; flex-direction: column; justify-content: space-between; min-height: 150px; } .sig-title { line-height: 1.5; margin-bottom: 15px; } .sig-name { text-decoration: underline; font-weight: bold; margin-top: auto; padding-bottom: 5px; } }
                </style>
            `;
            document.head.insertAdjacentHTML('beforeend', styles);
            document.documentElement.setAttribute('data-pln-theme', State.theme);
        }

        injectHTML() {
            const html = `
            <div id="pln-wrapper">
                <div class="drag-header" id="drag-header">
                    <div class="header-left"><i class="fas fa-bolt"></i> Dashboard Evaluasi Foto KWH Meter + AI OCR</div>
                    <div class="header-right">
                        <button class="hdr-btn" id="btn-theme-toggle" title="Ubah Tema (Dark/Light)"></button>
                        <button class="hdr-btn" id="btn-maximize" title="Maximize"><i class="fas fa-expand"></i></button>
                        <button class="hdr-btn btn-close" id="btn-close-dashboard"><i class="fas fa-times"></i> Tutup</button>
                    </div>
                </div>
                <div class="inner-container">
                    <div class="control-panel">
                        <div class="ctrl-section">
                            <div class="control-group"><label>Bulan</label><select id="sel-bulan"><option value="01">JAN</option><option value="02">FEB</option><option value="03">MAR</option><option value="04">APR</option><option value="05">MEI</option><option value="06">JUN</option><option value="07">JUL</option><option value="08">AGS</option><option value="09">SEP</option><option value="10">OKT</option><option value="11">NOV</option><option value="12">DES</option></select></div>
                            <div class="control-group"><label>Tahun</label><select id="sel-tahun"></select></div>
                            <div class="control-group"><label>Jml Foto</label><select id="sel-jml-foto"><option value="1" selected>1</option><option value="2">2</option><option value="3">3</option></select></div>
                        </div>
                        <div class="ctrl-section">
                            <div class="control-group"><label>IDPEL (Auto)</label><textarea id="input-idpel" placeholder="Paste IDPEL..."></textarea></div>
                            <div class="control-group"><label>User ACMT</label><input type="text" id="input-user-login" placeholder="Cth: 51671.vendor"></div>
                            <div class="control-group api-key-control">
                                <label>ARGUS Engine <button type="button" id="btn-toggle-api-key" class="api-key-toggle-btn"><i class="fas fa-chevron-down"></i> Buka</button></label>
                                <div class="api-key-content" id="api-key-content">
                                    <input type="text" id="input-api-key" placeholder="http://127.0.0.1:8000">
                                </div>
                            </div>
                        </div>
                        <div class="ctrl-section btn-section">
                            <button id="btn-clear-data" class="btn btn-danger"><i class="fas fa-trash-alt"></i> Hapus Data</button>
                            <button id="btn-ocr-all" class="btn btn-ocr"><i class="fas fa-robot"></i> OCR Semua</button>
                            <button id="btn-export-excel" class="btn btn-export"><i class="fas fa-file-excel"></i> Export .xlsx</button>
                            <button id="btn-export-pdf" class="btn btn-pdf"><i class="fas fa-file-pdf"></i> Cetak PDF</button>
                            
                            <div class="chart-inline-container">
                                <div class="chart-box-item" title="Valid vs Tidak Valid">
                                    <canvas id="chartValidVsTidak"></canvas>
                                    <div class="chart-info-text">
                                        <span>Valid/Tidak</span>
                                        <span class="val-count" id="txt-val-tidak">0 / 0</span>
                                    </div>
                                </div>
                                <div class="chart-box-item" title="Persentase Keberhasilan & Kegagalan OCR">
                                    <canvas id="chartSuccessOcr"></canvas>
                                    <div class="chart-info-text">
                                        <span>OCR Sukses/Gagal</span>
                                        <span class="val-count" id="txt-ocr-success">0% / 0%</span>
                                    </div>
                                </div>
                                <div class="chart-box-item" title="Prosentase Valid vs Tidak Valid">
                                    <canvas id="chartPercentValidTidak"></canvas>
                                    <div class="chart-info-text">
                                        <span>% Valid/Tidak</span>
                                        <span class="val-count" id="txt-percent-val-tidak">0% / 0%</span>
                                    </div>
                                </div>
                                <div class="chart-box-item" title="Total Jumlah Data">
                                    <i class="fas fa-database" style="font-size:18px;color:var(--primary);"></i>
                                    <div class="chart-info-text">
                                        <span>Jumlah Data</span>
                                        <span class="val-count" id="txt-total-data">0</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="ctrl-section full-width"><div class="col-toggle-group" id="col-toggles"></div></div>
                    </div>
                    <div id="loading-indicator" style="display:none; text-align:center; padding:10px;"><i class="fas fa-circle-notch fa-spin"></i> Mengambil data...</div>
                    <div class="table-wrapper"><div class="table-scroll"><table id="resultTable"><thead id="tabel-head-result"></thead><tbody id="tabel-body-result"></tbody></table></div></div>
                </div>
                <div id="resize-handle"></div>
            </div>
            <div id="pln-bu-overlay">
                <div id="bu-modal">
                    <h3><i class="fas fa-sync-alt"></i> Proses Baca Ulang</h3>
                    <div class="modal-content">
                        <div style="margin-bottom:18px; padding:15px; background:var(--glass-well); border-radius:12px; border:1px solid var(--glass-border-strong);">
                            <strong>IDPEL:</strong> <span id="bu-idpel">-</span><br>
                            <strong>BLTH:</strong> <span id="bu-blth">-</span>
                        </div>
                        <div class="bu-form-group">
                            <label>Jenis Baca Ulang</label>
                            <select id="bu-jenis"><option value="TEMPAT">Baca di Tempat</option><option value="LAPANGAN">Baca di Lapangan</option></select>
                        </div>
                        <div class="bu-form-group">
                            <label>User ACMT (Transaksi By)</label>
                            <input type="text" id="bu-transaksiby" readonly>
                        </div>
                        <div class="bu-form-group">
                            <label>Petugas Baca Ulang</label>
                            <input type="text" id="bu-petugas" placeholder="Cth: 51671.novi">
                        </div>
                        <div class="bu-btn-group">
                            <button class="bu-btn bu-btn-cancel" id="bu-cancel"><i class="fas fa-times"></i> Batal</button>
                            <button class="bu-btn bu-btn-submit" id="bu-submit"><i class="fas fa-paper-plane"></i> Kirim Baca Ulang</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="pln-pdf-overlay">
                <div id="pdf-modal">
                    <h3><i class="fas fa-file-pdf"></i> Pengaturan Cetak PDF</h3>
                    <div class="modal-content">
                        <div class="pdf-grid-2">
                            <div class="pdf-form-group"><label>UID</label><input type="text" id="pdf-uid" placeholder="Cth: JAWA TIMUR"></div>
                            <div class="pdf-form-group"><label>UP3</label><input type="text" id="pdf-up3" placeholder="Cth: BANYUWANGI"></div>
                        </div>
                        <div class="pdf-form-group"><label>ULP</label><input type="text" id="pdf-ulp" placeholder="Cth: BANYUWANGI KOTA"></div>
                        <hr class="pdf-divider">
                        <h4 class="pdf-subtitle">Tanda Tangan</h4>
                        <div class="pdf-grid-3">
                            <div class="pdf-form-group"><label>Koordinator</label><input type="text" id="pdf-nama-koor" placeholder="Nama Lengkap"></div>
                            <div class="pdf-form-group"><label>TL Transaksi Energi</label><input type="text" id="pdf-nama-tl" placeholder="Nama Lengkap"></div>
                            <div class="pdf-form-group"><label>Manager ULP</label><input type="text" id="pdf-nama-manager" placeholder="Nama Lengkap"></div>
                        </div>
                        <div class="pdf-btn-group">
                            <button class="pdf-btn pdf-btn-cancel" id="pdf-cancel"><i class="fas fa-times"></i> Batal</button>
                            <button class="pdf-btn pdf-btn-submit" id="pdf-submit"><i class="fas fa-print"></i> Cetak Sekarang</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="pln-crop-overlay">
                <div id="crop-modal">
                    <h3><i class="fas fa-crop"></i> Crop Foto & OCR</h3>
                    <div class="modal-content">
                        <div class="crop-img-container">
                            <img id="crop-img" src="">
                        </div>
                        <div class="crop-btn-group">
                            <button class="crop-btn crop-btn-cancel" id="crop-cancel"><i class="fas fa-times"></i> Batal</button>
                            <button class="crop-btn crop-btn-submit" id="crop-submit"><i class="fas fa-crop"></i> Crop & OCR</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="pln-modal-zoom">
                <span id="modal-close">&times;</span>
                <img id="modal-img" src="">
                <div id="modal-loupe"><img id="loupe-img" src=""></div>
            </div>
            <div id="pln-print-area"></div>
            <canvas id="chartPrintValid" width="200" height="200" style="position:fixed; top:-9999px; left:-9999px;"></canvas>
            <canvas id="chartPrintOcr" width="200" height="200" style="position:fixed; top:-9999px; left:-9999px;"></canvas>
            <canvas id="chartPrintPercent" width="200" height="200" style="position:fixed; top:-9999px; left:-9999px;"></canvas>
            <button id="btn-toggle-dashboard"><i class="fas fa-desktop"></i> Dashboard Evaluasi</button>
            `;
            document.body.insertAdjacentHTML('beforeend', html);
        }

        cacheDOM() {
            this.el = {
                wrapper: document.getElementById('pln-wrapper'),
                dragHeader: document.getElementById('drag-header'),
                resizeHandle: document.getElementById('resize-handle'),
                btnMaximize: document.getElementById('btn-maximize'),
                btnToggle: document.getElementById('btn-toggle-dashboard'),
                btnClose: document.getElementById('btn-close-dashboard'),
                themeBtn: document.getElementById('btn-theme-toggle'),
                tableHead: document.getElementById('tabel-head-result'),
                tableBody: document.getElementById('tabel-body-result'),
                inputIdpel: document.getElementById('input-idpel'),
                loading: document.getElementById('loading-indicator'),
                inputApiKey: document.getElementById('input-api-key'),
                inputUserLogin: document.getElementById('input-user-login'),
                apiKeyToggle: document.getElementById('btn-toggle-api-key'),
                apiKeyContent: document.getElementById('api-key-content'),
                selBulan: document.getElementById('sel-bulan'),
                selTahun: document.getElementById('sel-tahun'),
                selJmlFoto: document.getElementById('sel-jml-foto'),
                toggleContainer: document.getElementById('col-toggles'),
                btnClearData: document.getElementById('btn-clear-data'),
                btnOcrAll: document.getElementById('btn-ocr-all'),
                btnExportExcel: document.getElementById('btn-export-excel'),
                btnExportPdf: document.getElementById('btn-export-pdf'),
                photoModal: document.getElementById('pln-modal-zoom'),
                modalImg: document.getElementById('modal-img'),
                modalLoupe: document.getElementById('modal-loupe'),
                loupeImg: document.getElementById('loupe-img'),
                modalClose: document.getElementById('modal-close'),
                buOverlay: document.getElementById('pln-bu-overlay'),
                buIdpel: document.getElementById('bu-idpel'),
                buBlth: document.getElementById('bu-blth'),
                buJenis: document.getElementById('bu-jenis'),
                buTransaksiby: document.getElementById('bu-transaksiby'),
                buPetugas: document.getElementById('bu-petugas'),
                buCancel: document.getElementById('bu-cancel'),
                buSubmit: document.getElementById('bu-submit'),
                pdfOverlay: document.getElementById('pln-pdf-overlay'),
                pdfCancel: document.getElementById('pdf-cancel'),
                pdfSubmit: document.getElementById('pdf-submit'),
                cropOverlay: document.getElementById('pln-crop-overlay'),
                cropImg: document.getElementById('crop-img'),
                cropCancel: document.getElementById('crop-cancel'),
                cropSubmit: document.getElementById('crop-submit'),
                txtValTidak: document.getElementById('txt-val-tidak'),
                txtOcrSuccess: document.getElementById('txt-ocr-success'),
                txtPercentValTidak: document.getElementById('txt-percent-val-tidak'),
                txtTotalData: document.getElementById('txt-total-data')
            };
        }

        initEvents() {
            this.updateThemeIcon();
            this.el.themeBtn.addEventListener('click', () => {
                State.theme = State.theme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-pln-theme', State.theme);
                GM_setValue('PLN_THEME', State.theme);
                this.updateThemeIcon();
            });

            this.el.inputApiKey.value = State.apiKey;
            const saveApiKey = () => {
                State.apiKey = this.el.inputApiKey.value.trim();
                GM_setValue('API_KEY', State.apiKey);
            };
            this.el.inputApiKey.addEventListener('input', saveApiKey);
            this.el.inputApiKey.addEventListener('change', saveApiKey);
            this.el.inputApiKey.addEventListener('blur', saveApiKey);
            window.addEventListener('beforeunload', saveApiKey);

            this.el.inputUserLogin.value = State.userLogin;
            this.el.inputUserLogin.addEventListener('input', () => { State.userLogin = this.el.inputUserLogin.value.trim(); GM_setValue('ACMT_USER_LOGIN', State.userLogin); });

            this.el.apiKeyToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = this.el.apiKeyContent.classList.toggle('is-open');
                this.el.apiKeyToggle.innerHTML = isOpen ? '<i class="fas fa-chevron-up"></i> Tutup' : '<i class="fas fa-chevron-down"></i> Buka';
            });

            this.initDragResize();

            this.el.tableBody.addEventListener('click', (e) => this.handleTableClick(e));
            this.el.tableBody.addEventListener('change', (e) => this.handleTableChange(e));
            this.el.tableHead.addEventListener('click', (e) => this.handleSort(e));

            this.el.inputIdpel.addEventListener('input', Utils.debounce(() => this.fetchAndRenderData(), 500));
            this.el.selJmlFoto.addEventListener('change', () => { this.renderTableHead(); this.renderTableBody(); });
            this.el.toggleContainer.addEventListener('change', () => { this.renderTableHead(); this.renderTableBody(); });
            this.el.selBulan.addEventListener('change', () => this.fetchAndRenderData());
            this.el.selTahun.addEventListener('change', () => this.fetchAndRenderData());
            
            this.el.btnClearData.addEventListener('click', () => this.clearData());
            this.el.btnOcrAll.addEventListener('click', () => this.runBulkOCR());
            this.el.btnExportExcel.addEventListener('click', () => ExportManager.exportToExcel());
            this.el.btnExportPdf.addEventListener('click', () => this.openPdfModal());

            this.el.btnToggle.addEventListener('click', () => this.toggleDashboard());
            this.el.btnClose.addEventListener('click', () => this.el.wrapper.style.display = 'none');
            this.el.btnMaximize.addEventListener('click', () => this.toggleMaximize());
            this.el.dragHeader.addEventListener('dblclick', (e) => { if (!e.target.closest('.hdr-btn')) this.toggleMaximize(); });

            this.el.buCancel.addEventListener('click', () => this.el.buOverlay.style.display = 'none');
            this.el.buSubmit.addEventListener('click', () => this.submitBacaUlang());

            this.el.pdfCancel.addEventListener('click', () => this.el.pdfOverlay.style.display = 'none');
            this.el.pdfSubmit.addEventListener('click', () => ExportManager.exportToPDF());

            // Events for Crop Modal
            this.el.cropCancel.addEventListener('click', () => this.closeCropModal());
            this.el.cropSubmit.addEventListener('click', () => this.applyCrop());

            this.initPhotoZoom();
            this.initPdfInputs();
        }

        initYearSelect() {
            const cY = new Date().getFullYear();
            for(let y = cY - 1; y <= cY + 1; y++){ const o = document.createElement("option"); o.value = y; o.textContent = y; this.el.selTahun.appendChild(o); }
            let dDate = new Date(); dDate.setMonth(dDate.getMonth() + 1);
            this.el.selTahun.value = dDate.getFullYear();
            this.el.selBulan.value = String(dDate.getMonth() + 1).padStart(2, '0');
        }

        initPdfInputs() {
            document.getElementById('pdf-uid').value = State.pdfData.uid;
            document.getElementById('pdf-up3').value = State.pdfData.up3;
            document.getElementById('pdf-ulp').value = State.pdfData.ulp;
            document.getElementById('pdf-nama-koor').value = State.pdfData.koor;
            document.getElementById('pdf-nama-tl').value = State.pdfData.tl;
            document.getElementById('pdf-nama-manager').value = State.pdfData.manager;
            
            ['pdf-uid', 'pdf-up3', 'pdf-ulp', 'pdf-nama-koor', 'pdf-nama-tl', 'pdf-nama-manager'].forEach(id => {
                document.getElementById(id).addEventListener('input', (e) => {
                    const keyMap = { 'pdf-uid': 'uid', 'pdf-up3': 'up3', 'pdf-ulp': 'ulp', 'pdf-nama-koor': 'koor', 'pdf-nama-tl': 'tl', 'pdf-nama-manager': 'manager' };
                    State.pdfData[keyMap[id]] = e.target.value;
                    GM_setValue('PDF_DATA', State.pdfData);
                });
            });
        }

        initCharts() {
            if (typeof Chart === 'undefined') {
                console.error('[Dashboard] Chart.js tidak dimuat! Chart tidak akan berfungsi.');
                return;
            }

            const doughnut3DPlugin = {
                id: 'doughnut3D',
                beforeDatasetsDraw(chart) {
                    if (chart.config.type !== 'doughnut') return;
                    const { ctx } = chart;
                    const meta = chart.getDatasetMeta(0);
                    if (!meta || !meta.data || !meta.data.length) return;
                    const arc = meta.data[0];
                    if (!arc || !arc.outerRadius || arc.outerRadius <= 0) return;
                    const cx = arc.x, cy = arc.y;
                    const outerR = Math.max(0.1, arc.outerRadius);
                    const innerR = Math.max(0.1, arc.innerRadius);
                    const thickness = Math.max(2, Math.floor(outerR / 8));
                    ctx.save();
                    for (let i = thickness; i > 0; i--) {
                        const alpha = 0.04 + (thickness - i) * 0.014;
                        ctx.beginPath();
                        ctx.arc(cx, cy + i, outerR, 0, Math.PI * 2);
                        ctx.arc(cx, cy + i, innerR, 0, Math.PI * 2, true);
                        ctx.fillStyle = `rgba(0, 0, 0, ${alpha})`;
                        ctx.fill();
                    }
                    ctx.restore();
                }
            };
            Chart.register(doughnut3DPlugin);

            const chartOpts = (tooltipCb) => ({
                responsive: false, maintainAspectRatio: false, cutout: '60%', layout: { padding: 3 },
                plugins: { legend: { display: false }, tooltip: { enabled: true, callbacks: tooltipCb || {} } }
            });

            State.charts.valid = new Chart(document.getElementById('chartValidVsTidak').getContext('2d'), { type: 'doughnut', data: { labels: ['Valid', 'Tidak Valid'], datasets: [{ data: [0, 0], backgroundColor: ['#30d158', '#ff3b30'], borderColor: 'rgba(255,255,255,0.6)', borderWidth: 1, borderRadius: 4, spacing: 1, hoverOffset: 3 }] }, options: chartOpts() });
            State.charts.ocr = new Chart(document.getElementById('chartSuccessOcr').getContext('2d'), { type: 'doughnut', data: { labels: ['Berhasil', 'Gagal'], datasets: [{ data: [0, 100], backgroundColor: ['#00A2E9', '#8e8e93'], borderColor: 'rgba(255,255,255,0.6)', borderWidth: 1, borderRadius: 4, spacing: 1, hoverOffset: 3 }] }, options: chartOpts() });
            State.charts.percent = new Chart(document.getElementById('chartPercentValidTidak').getContext('2d'), { type: 'doughnut', data: { labels: ['% Valid', '% Tidak Valid'], datasets: [{ data: [0, 0], backgroundColor: ['#30d158', '#ff3b30'], borderColor: 'rgba(255,255,255,0.6)', borderWidth: 1, borderRadius: 4, spacing: 1, hoverOffset: 3 }] }, options: chartOpts({ label: (ctx) => `${ctx.label}: ${ctx.raw}%` }) });

            const printOpts = { responsive: false, maintainAspectRatio: false, animation: false, cutout: '60%', layout: { padding: 8 }, plugins: { legend: { display: false }, tooltip: { enabled: false } } };
            const ctxP1 = document.getElementById('chartPrintValid').getContext('2d');
            const gradValidP = ctxP1.createLinearGradient(0, 0, 0, 200); gradValidP.addColorStop(0, '#5ee08a'); gradValidP.addColorStop(1, '#1c8b3f');
            const gradTidakP = ctxP1.createLinearGradient(0, 0, 0, 200); gradTidakP.addColorStop(0, '#ff6b6b'); gradTidakP.addColorStop(1, '#d70015');
            State.charts.printValid = new Chart(ctxP1, { type: 'doughnut', data: { labels: ['Valid', 'Tidak Valid'], datasets: [{ data: [0, 0], backgroundColor: [gradValidP, gradTidakP], borderWidth: 2, borderColor: '#fff', borderRadius: 8, spacing: 3 }] }, options: printOpts });

            const ctxP2 = document.getElementById('chartPrintOcr').getContext('2d');
            const gradOcrOk = ctxP2.createLinearGradient(0, 0, 0, 200); gradOcrOk.addColorStop(0, '#5ec8f5'); gradOcrOk.addColorStop(1, '#007BB5');
            const gradOcrFail = ctxP2.createLinearGradient(0, 0, 0, 200); gradOcrFail.addColorStop(0, '#b0b0b0'); gradOcrFail.addColorStop(1, '#6e6e6e');
            State.charts.printOcr = new Chart(ctxP2, { type: 'doughnut', data: { labels: ['Berhasil', 'Gagal'], datasets: [{ data: [0, 100], backgroundColor: [gradOcrOk, gradOcrFail], borderWidth: 2, borderColor: '#fff', borderRadius: 8, spacing: 3 }] }, options: printOpts });

            const ctxP3 = document.getElementById('chartPrintPercent').getContext('2d');
            const gradPercValid = ctxP3.createLinearGradient(0, 0, 0, 200); gradPercValid.addColorStop(0, '#5ee08a'); gradPercValid.addColorStop(1, '#1c8b3f');
            const gradPercTidak = ctxP3.createLinearGradient(0, 0, 0, 200); gradPercTidak.addColorStop(0, '#ff6b6b'); gradPercTidak.addColorStop(1, '#d70015');
            State.charts.printPercent = new Chart(ctxP3, { type: 'doughnut', data: { labels: ['% Valid', '% Tidak Valid'], datasets: [{ data: [0, 0], backgroundColor: [gradPercValid, gradPercTidak], borderWidth: 2, borderColor: '#fff', borderRadius: 8, spacing: 3 }] }, options: printOpts });
        }

        updateCharts() {
            if (!State.charts.valid) return;
            let totalValid = 0, totalTidakValid = 0, totalOcrBerhasil = 0, totalRows = 0;
            const rows = this.el.tableBody.querySelectorAll('tr');
            totalRows = rows.length;

            rows.forEach(row => {
                const valOcrCell = row.querySelector('td[data-col="validasi_ocr"]');
                const status = valOcrCell ? valOcrCell.textContent.trim() : '-';
                if (status === 'Valid') totalValid++; 
                else if (status === 'Tidak Valid') totalTidakValid++;

                const ocrCell = row.querySelector('td[data-col="hasil_ocr"]');
                const ocrVal = ocrCell ? ocrCell.textContent.trim() : '-';
                if (ocrVal !== '-' && ocrVal !== 'Error' && ocrVal !== 'Kosong' && ocrVal !== '') totalOcrBerhasil++;
            });

            State.charts.valid.data.datasets[0].data = [totalValid, totalTidakValid]; State.charts.valid.update();
            this.el.txtValTidak.textContent = `${totalValid} / ${totalTidakValid}`;

            let successPercent = totalRows > 0 ? Math.round((totalOcrBerhasil / totalRows) * 100) : 0;
            let failPercent = 100 - successPercent;
            State.charts.ocr.data.datasets[0].data = [totalOcrBerhasil, Math.max(0, totalRows - totalOcrBerhasil)]; State.charts.ocr.update();
            this.el.txtOcrSuccess.textContent = `${successPercent}% / ${failPercent}%`;

            const totalValidTidak = totalValid + totalTidakValid;
            const persenValid = totalValidTidak > 0 ? Math.round((totalValid / totalValidTidak) * 100) : 0;
            const persenTidak = totalValidTidak > 0 ? 100 - persenValid : 0;
            State.charts.percent.data.datasets[0].data = [persenValid, persenTidak]; State.charts.percent.update();
            this.el.txtPercentValTidak.textContent = `${persenValid}% / ${persenTidak}%`;
            this.el.txtTotalData.textContent = totalRows;
        }

        getActiveColumns() { return this.columns.filter(c => document.getElementById(`chk-${c.id}`).checked); }
        countCols() {
            const ac = this.getActiveColumns(), j = parseInt(this.el.selJmlFoto.value);
            let tc = ac.length + j;
            if(document.getElementById('chk-foto_bln_terakhir').checked) tc += 1;
            return tc;
        }

        renderTableHead() {
            const ac = this.getActiveColumns(), j = parseInt(this.el.selJmlFoto.value);
            const bl = this.el.selTahun.value + this.el.selBulan.value;
            let h = ac.map(c => `<th data-col="${c.id}" data-type="${c.type}">${c.label} <span class="sort-icon"><i class="fas fa-sort"></i></span></th>`).join('');
            h += `<th>FOTO ${Utils.getMonthLabel(bl)}</th>`;
            if(document.getElementById('chk-foto_bln_terakhir').checked) { h += `<th>FOTO 2 ${Utils.getMonthLabel(bl)}</th>`; }
            for(let f = 1; f < j; f++) { h += `<th>FOTO ${Utils.getMonthLabel(String(parseInt(bl) - f))}</th>`; }
            this.el.tableHead.innerHTML = `<tr>${h}</tr>`;
        }

        renderTableBody() {
            const idpels = Object.keys(State.customerData);
            if(!idpels.length) { this.el.tableBody.innerHTML = ''; return; }
            this.el.tableBody.innerHTML = '';
            idpels.forEach((id, i) => {
                const row = this.el.tableBody.insertRow();
                row.innerHTML = this.generateRowHTML(State.customerData[id], i + 1);
            });
            this.updateCharts();
            this.cacheImages();
        }

        generateRowHTML(d, idx) {
            const ac = this.getActiveColumns(), j = parseInt(this.el.selJmlFoto.value);
            const bl = this.el.selTahun.value + this.el.selBulan.value;
            const sb = parseInt(d.stan_baca) || 0, sl = parseInt(d.stand_lalu) || 0;
            const pk = d.pemkwh !== "-" ? parseInt(d.pemkwh) : (sb - sl);
            const pkL = parseInt(d.pakai_bln_lalu) || 0;
            const selisih = pk - pkL;
            let warnaSelisih = 'var(--text)', beratTeks = 'normal';
            if (selisih >= 100) { warnaSelisih = '#30d158'; beratTeks = 'bold'; } else if (selisih <= -100) { warnaSelisih = '#ff3b30'; beratTeks = 'bold'; }
            
            const wrapStyle = 'word-break:break-word;white-space:normal;line-height:1.2;max-width:80px;';
            const wrapStyleNum = 'word-break:break-all;white-space:normal;line-height:1.2;max-width:70px;';
            
            const dm = {
                'no': `<td data-col="no">${idx}</td>`,
                'idpel': `<td data-col="idpel" style="font-weight:bold;color:var(--pln-blue)">${d.idpel}</td>`,
                'nama': `<td data-col="nama" style="text-align:left;font-weight:600;white-space:nowrap">${d.nama}</td>`,
                'nomor_meter': `<td data-col="nomor_meter">${d.nomor_meter}</td>`,
                'tarif': `<td data-col="tarif">${d.tarif}</td>`,
                'daya': `<td data-col="daya">${d.daya}</td>`,
                'koduk': `<td data-col="koduk" style="font-weight:600;color:var(--pln-yellow)">${d.kode_rbm}</td>`,
                'gardu_tiang': `<td data-col="gardu_tiang" style="text-align:left;font-size:11px;max-width:200px;white-space:normal;line-height:1.3">${[d.gardu, d.tiang].filter(v => v && v !== '-').join('<br>')}</td>`,
                'lbkb': `<td data-col="lbkb">${d.lbkb}</td>`,
                'stan_lalu': `<td data-col="stan_lalu" style="${wrapStyleNum}">${d.stand_lalu}</td>`,
                'stan_baca': `<td data-col="stan_baca" style="font-weight:bold;color:var(--text);${wrapStyleNum}">${d.stan_baca}</td>`,
                'hasil_ocr': `<td data-col="hasil_ocr" style="font-weight:bold;color:var(--pln-blue);">${d.hasil_ocr || '-'}</td>`,
                'validasi_ocr': `<td data-col="validasi_ocr" data-ocr-status="${d.original_ocr_status || '-'}" style="font-weight:bold;color:${d.validasi_ocr === 'Valid' ? 'var(--pln-blue)' : (d.validasi_ocr === 'Tidak Valid' ? 'var(--danger-text)' : 'var(--text)')};${wrapStyle}">${d.validasi_ocr || '-'}</td>`,
                'pemakaian': `<td data-col="pemakaian" style="font-weight:bold;color:${pk < 0 ? '#ff3b30' : 'var(--text)'}">${pk}</td>`,
                'pakai_bln_lalu': `<td data-col="pakai_bln_lalu" style="font-weight:bold;color:${pkL < 0 ? '#ff3b30' : 'var(--text)'};${wrapStyleNum}">${pkL}</td>`,
                'selisih_kwh': `<td data-col="selisih_kwh" style="font-weight:${beratTeks};color:${warnaSelisih};">${selisih > 0 ? '+' + selisih : selisih}</td>`,
                'jamnyala': `<td data-col="jamnyala" style="${wrapStyle}">${d.jamnyala}</td>`,
                'petugas': `<td data-col="petugas">${d.petugas}</td>`,
                'validasi': `<td data-col="validasi"><select class="sel-validasi ${d.validasi_manual === 'Tidak' ? 'val-tidak' : 'val-valid'}"><option value="Valid" ${d.validasi_manual !== 'Tidak' ? 'selected' : ''}>Valid</option><option value="Tidak" ${d.validasi_manual === 'Tidak' ? 'selected' : ''}>Tidak</option></select></td>`
            };

            let rc = ac.map(c => dm[c.id]).join('');
            rc += this.photoTD(d.idpel, 'foto_0', `https://portalapp.iconpln.co.id/acmt/DisplayBlobServlet1?idpel=${d.idpel}&nomor_meter=null&fotoke=0&blth=${bl}&isPhoto=null`);
            if(document.getElementById('chk-foto_bln_terakhir').checked) { rc += this.photoTD(d.idpel, 'foto_s2', `https://portalapp.iconpln.co.id/acmt/DisplayBlobServlet2?idpel=${d.idpel}&nomor_meter=null&fotoke=null&blth=${bl}&isPhoto=null`); }
            for(let f = 1; f < j; f++) { let tb = String(parseInt(bl) - f); rc += this.photoTD(d.idpel, `foto_${f}`, `https://portalapp.iconpln.co.id/acmt/DisplayBlobServlet1?idpel=${d.idpel}&nomor_meter=null&fotoke=${f}&blth=${tb}&isPhoto=null`); }
            return rc;
        }

        photoTD(idpel, photoKey, defaultSrc) {
            const cachedSrc = State.photoCache[defaultSrc];
            const actualSrc = State.customPhotos[`${idpel}_${photoKey}`] || cachedSrc || defaultSrc;
            const isCustom = !!State.customPhotos[`${idpel}_${photoKey}`];
            const resetHtml = isCustom ? `<div class="reset-photo-btn" data-idpel="${idpel}" data-key="${photoKey}" title="Hapus foto">&times;</div>` : '';
            const cropHtml = `<div class="crop-photo-btn" data-idpel="${idpel}" data-key="${photoKey}" title="Crop Foto"><i class="fas fa-crop"></i></div>`;
            const ocrHtml = `<div class="ocr-photo-btn" data-idpel="${idpel}" data-key="${photoKey}" title="Baca OCR">OCR AI</div>`;
            const cachedAttr = cachedSrc ? 'data-cached="true"' : '';
            return `<td data-photo-key="${photoKey}"><div class="photo-container">${resetHtml}${cropHtml}${ocrHtml}<img class="col-photo-box" data-original-src="${defaultSrc}" src="${actualSrc}" ${cachedAttr} onerror="this.src='https://via.placeholder.com/200x200/37474f/ffffff?text=Kosong'"></div></td>`;
        }

        async cacheImages() {
            const imgs = this.el.tableBody.querySelectorAll('img.col-photo-box:not([data-cached="true"])');
            if (imgs.length === 0) {
                if (State.apiKey) this.runAutoOCR();
                return;
            }
            
            const promises = [];
            imgs.forEach(img => {
                const originalSrc = img.dataset.originalSrc;
                if (!originalSrc || originalSrc.startsWith('data:')) {
                    img.dataset.cached = "true";
                    return;
                }
                
                if (State.photoCache[originalSrc]) {
                    img.src = State.photoCache[originalSrc];
                    img.dataset.cached = "true";
                } else {
                    img.dataset.cached = "true"; 
                    promises.push(
                        APIManager.fetchImage(originalSrc).then(base64 => {
                            if (base64) {
                                State.photoCache[originalSrc] = base64;
                                img.src = base64;
                            }
                        }).catch(() => {})
                    );
                }
            });
            
            if (promises.length > 0) {
                await Promise.all(promises);
                try {
                    const keys = Object.keys(State.photoCache);
                    if (keys.length > 150) {
                        for(let i=0; i<50; i++) delete State.photoCache[keys[i]];
                    }
                    GM_setValue('PHOTO_CACHE', State.photoCache);
                } catch (e) {
                    console.error("Photo cache quota exceeded, clearing cache.", e);
                    State.photoCache = {};
                    GM_setValue('PHOTO_CACHE', {});
                }
            }
            
            if (State.apiKey) this.runAutoOCR();
        }

        async fetchAndRenderData() {
            const iv = this.el.inputIdpel.value;
            const is = iv.split(/[\n,]+/).map(id => id.trim()).filter(id => id !== '');
            this.el.tableBody.innerHTML = ''; State.customerData = {};
            if(!is.length) { this.updateCharts(); return; }
            
            this.el.loading.style.display = 'block';
            const bl = this.el.selTahun.value + this.el.selBulan.value;
            const tc = this.countCols();

            for(let i = 0; i < is.length; i++) {
                const id = is[i];
                const row = this.el.tableBody.insertRow();
                row.innerHTML = `<td colspan="${tc}" style="text-align:center;color:var(--pln-blue);font-weight:bold"><i class="fas fa-circle-notch fa-spin"></i> Fetching ${id}...</td>`;
                
                try {
                    const d = await APIManager.fetchCustomerData(id);
                    if(d && d.idpel) { 
                        const ocrKey = `${d.idpel}_${bl}`;
                        if (Utils.isCacheValid(State.ocrCache[ocrKey])) { 
                            d.hasil_ocr = State.ocrCache[ocrKey].hasil_ocr; 
                            d.validasi_ocr = State.ocrCache[ocrKey].validasi_ocr; 
                            d.original_ocr_status = State.ocrCache[ocrKey].validasi_ocr; 
                        }
                        State.customerData[id] = d; 
                        row.innerHTML = this.generateRowHTML(d, i + 1); 
                    } else { 
                        row.innerHTML = `<td colspan="${tc}" style="text-align:center;color:#d70015;font-weight:bold">❌ ${id} Tidak Ditemukan</td>`; 
                    }
                } catch(e) { 
                    row.innerHTML = `<td colspan="${tc}" style="text-align:center;color:#d70015;font-weight:bold">❌ Error (${e.message})</td>`; 
                }
                await new Promise(r => setTimeout(r, 100));
            }
            
            this.el.loading.style.display = 'none'; 
            this.updateCharts();
            await this.cacheImages();
        }

        handleTableClick(e) {
            if (e.target.classList.contains('reset-photo-btn')) {
                e.stopPropagation();
                const idpel = e.target.dataset.idpel, key = e.target.dataset.key;
                delete State.customPhotos[`${idpel}_${key}`];
                const pc = e.target.closest('.photo-container'); const img = pc ? pc.querySelector('.col-photo-box') : null;
                if (img && img.dataset.originalSrc) img.src = img.dataset.originalSrc;
                if (e.target.parentNode) e.target.remove();
            } else if (e.target.classList.contains('ocr-photo-btn') || e.target.closest('.ocr-photo-btn')) {
                e.stopPropagation();
                const btn = e.target.closest('.ocr-photo-btn');
                const pc = btn.closest('.photo-container'); 
                const img = pc ? pc.querySelector('.col-photo-box') : null; 
                const row = pc ? pc.closest('tr') : null;
                if (img && row) this.runOCR(img, row, false);
            } else if (e.target.classList.contains('crop-photo-btn') || e.target.closest('.crop-photo-btn')) {
                e.stopPropagation();
                const btn = e.target.closest('.crop-photo-btn');
                const pc = btn.closest('.photo-container'); 
                const img = pc ? pc.querySelector('.col-photo-box') : null; 
                const row = pc ? pc.closest('tr') : null;
                if (img && row) this.openCropModal(img, row);
            } else if (e.target.closest('.photo-container')) {
                const pc = e.target.closest('.photo-container');
                const img = pc.querySelector('.col-photo-box');
                if(img) { this.el.modalImg.src = img.src; this.el.photoModal.style.display = 'block'; }
            }
        }

        handleTableChange(e) {
            if (e.target.classList.contains('sel-validasi')) { 
                e.target.classList.remove('val-valid', 'val-tidak'); 
                e.target.classList.add(e.target.value === 'Valid' ? 'val-valid' : 'val-tidak'); 
                
                const row = e.target.closest('tr');
                const valOcrCell = row.querySelector('td[data-col="validasi_ocr"]');
                const idpel = row.querySelector('td[data-col="idpel"]').textContent.trim();
                
                if (e.target.value === 'Tidak') {
                    if (valOcrCell) {
                        valOcrCell.textContent = 'Tidak Valid';
                        valOcrCell.style.color = 'var(--danger-text)';
                    }
                    if (State.customerData[idpel]) {
                        State.customerData[idpel].validasi_ocr = 'Tidak Valid';
                        State.customerData[idpel].validasi_manual = 'Tidak';
                    }
                    if (row && row.parentNode) row.parentNode.prepend(row);
                    
                    const petugasCol = row.querySelector('td[data-col="petugas"]')?.textContent.trim();
                    const data = State.customerData[idpel];
                    if(data) {
                        this.currentBuData = { 
                            idpel: idpel, 
                            blth: this.el.selTahun.value + this.el.selBulan.value, 
                            unitup: data.unitup !== "-" ? data.unitup : idpel.substring(0, 5) 
                        };
                        this.el.buIdpel.textContent = idpel; 
                        this.el.buBlth.textContent = this.currentBuData.blth; 
                        this.el.buJenis.value = "TEMPAT"; 
                        this.el.buTransaksiby.value = State.userLogin; 
                        this.el.buPetugas.value = petugasCol && petugasCol !== "-" ? petugasCol : "";
                        this.el.buOverlay.style.display = 'flex';
                    }
                } else {
                    const originalStatus = valOcrCell?.dataset.ocrStatus || '-';
                    if (valOcrCell) {
                        valOcrCell.textContent = originalStatus;
                        valOcrCell.style.color = originalStatus === 'Valid' ? 'var(--pln-blue)' : (originalStatus === 'Tidak Valid' ? 'var(--danger-text)' : 'var(--text)');
                    }
                    if (State.customerData[idpel]) {
                        State.customerData[idpel].validasi_ocr = originalStatus;
                        State.customerData[idpel].validasi_manual = 'Valid';
                    }
                }
                
                this.updateCharts();
            }
        }

        async submitBacaUlang() {
            const transaksiby = this.el.buTransaksiby.value.trim(); 
            const nama_ptgs = this.el.buPetugas.value.trim(); 
            const jenisBaca = this.el.buJenis.value;
            if (!transaksiby) { alert('User ACMT belum diatur! Silakan isi di panel atas.'); return; }
            if (!nama_ptgs) { alert('Petugas Baca Ulang wajib diisi!'); return; }

            const btnSubmit = this.el.buSubmit;
            btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Mengirim...'; btnSubmit.disabled = true;
            
            try {
                const success = await APIManager.submitBacaUlang({ ...this.currentBuData, transaksiby, nama_ptgs, jenis: jenisBaca });
                if(success) {
                    alert(`Baca Ulang untuk ${this.currentBuData.idpel} berhasil dikirim!`);
                    this.el.buOverlay.style.display = 'none';
                    
                    let currentIdpels = this.el.inputIdpel.value.split(/[\n,]+/).map(id => id.trim()).filter(id => id !== '');
                    currentIdpels = currentIdpels.filter(id => id !== this.currentBuData.idpel);
                    this.el.inputIdpel.value = currentIdpels.join('\n');
                    
                    if (State.customerData[this.currentBuData.idpel]) delete State.customerData[this.currentBuData.idpel];
                    const rows = document.querySelectorAll('#tabel-body-result tr');
                    rows.forEach(row => { 
                        const idpelCell = row.querySelector('td[data-col="idpel"]'); 
                        if (idpelCell && idpelCell.textContent.trim() === this.currentBuData.idpel) row.remove(); 
                    });
                    document.querySelectorAll('#tabel-body-result tr').forEach((row, index) => { 
                        const noCell = row.querySelector('td[data-col="no"]'); 
                        if (noCell) noCell.textContent = index + 1; 
                    });
                    this.updateCharts();
                } else { alert("Gagal/Respons tidak dikenal."); }
            } catch(e) { alert("Error: " + e.message); }
            btnSubmit.innerHTML = '<i class="fas fa-paper-plane"></i> Kirim Baca Ulang'; btnSubmit.disabled = false;
        }

        async runOCR(imgElement, rowElement, isBulk = false) {
            if (!State.apiKey) { State.apiKey = 'http://127.0.0.1:8000'; }
            
            let base64Img = imgElement.src;
            if (!base64Img.startsWith('data:')) {
                if (!imgElement.complete || imgElement.naturalWidth === 0) { await new Promise(res => { imgElement.onload = res; imgElement.onerror = res; setTimeout(res, 3000); }); }
                if (imgElement.naturalWidth === 0) { if(!isBulk) alert("Gagal memuat gambar untuk OCR."); return; }

                const MAX_DIM = 768; let tW = imgElement.naturalWidth, tH = imgElement.naturalHeight;
                if (Math.max(tW, tH) > MAX_DIM) { const scale = MAX_DIM / Math.max(tW, tH); tW = Math.round(tW * scale); tH = Math.round(tH * scale); }
                const canvas = document.createElement('canvas'); canvas.width = tW; canvas.height = tH; canvas.getContext('2d').drawImage(imgElement, 0, 0, tW, tH);
                base64Img = canvas.toDataURL('image/jpeg', 0.75);
            }
            
            const base64 = base64Img.split(',')[1];

            const ocrCell = rowElement.querySelector('td[data-col="hasil_ocr"]');
            const idpelCell = rowElement.querySelector('td[data-col="idpel"]'); const idpel = idpelCell ? idpelCell.textContent.trim() : null;
            const stanBacaCell = rowElement.querySelector('td[data-col="stan_baca"]');
            const sbText = stanBacaCell ? stanBacaCell.textContent.trim() : '0';
            const targetLength = sbText.replace(/\D/g, '').length || 5;
            const sb = parseInt(sbText.replace(/[^0-9.-]/g, '')) || 0;

            let finalNum = "", finalStatus = "Tidak Valid";
            if(ocrCell) ocrCell.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            for (let attempt = 1; attempt <= Config.OCR_MAX_RETRIES; attempt++) {
                if(ocrCell && isBulk) ocrCell.innerHTML = `<i class="fas fa-spinner fa-spin"></i> (${attempt}/${Config.OCR_MAX_RETRIES})`;
                try {
                    const argusRes = await APIManager.runArgusOCR(base64);
                    const rawReading = (argusRes.stand_baca || argusRes.reading || "").trim();
                    const numbers = rawReading.match(/\d+/g); let bestNum = "";
                    if (numbers) for (let num of numbers) if (num.length > bestNum.length) bestNum = num;
                    let procNum = bestNum.replace(/^0+/, '');
                    if (procNum === '') procNum = '0';
                    if (procNum.length > targetLength) procNum = procNum.slice(0, targetLength);

                    if (procNum !== '') {
                        const ho = parseInt(procNum) || 0;
                        if (sb === ho && argusRes.tier_color === 'GREEN') {
                            finalNum = procNum;
                            finalStatus = 'Valid';
                            if (ocrCell) ocrCell.title = `ARGUS OK: ${argusRes.status} (${argusRes.latency_ms}ms)`;
                            break;
                        } else {
                            finalNum = procNum;
                            finalStatus = 'Tidak Valid';
                            if (ocrCell) ocrCell.title = `ARGUS Triage: ${argusRes.status} (${argusRes.latency_ms}ms)`;
                        }
                    } else {
                        if (argusRes.status === 'FAIL_COUNTER_NOT_FOUND') {
                            finalNum = "Bukan Meter";
                        } else if (argusRes.status === 'REJECTED_BLUR') {
                            finalNum = "Buram";
                        } else if (argusRes.status === 'ANOMALI_GLARE_TERHALANG') {
                            finalNum = "Silau";
                        } else {
                            finalNum = "Kosong";
                        }
                        finalStatus = '-';
                        if (ocrCell) ocrCell.title = `ARGUS: ${argusRes.status}`;
                    }
                } catch (error) { 
                    finalNum = "Error"; 
                    finalStatus = '-';
                    if (ocrCell) ocrCell.title = error.message;
                    console.error("[ARGUS API Error]:", error);
                }
                if (attempt < Config.OCR_MAX_RETRIES) await new Promise(r => setTimeout(r, 300));
            }

            let valColor = 'var(--danger-text)', ocrColor = 'var(--pln-blue)';
            if (finalStatus === 'Valid') { valColor = 'var(--pln-blue)'; if (stanBacaCell) stanBacaCell.style.color = 'var(--text)'; } 
            else if (finalStatus === 'Tidak Valid') { if (stanBacaCell) stanBacaCell.style.color = 'var(--danger-text)'; }

            if (ocrCell) { ocrCell.textContent = finalNum; ocrCell.style.color = ocrColor; }
            const valOcrCell = rowElement.querySelector('td[data-col="validasi_ocr"]');
            const manualSel = rowElement.querySelector('select.sel-validasi');
            const manualStatus = manualSel ? manualSel.value : 'Valid';
            
            if (valOcrCell) { 
                valOcrCell.dataset.ocrStatus = finalStatus; 
                if (manualStatus !== 'Tidak') {
                    valOcrCell.textContent = finalStatus; 
                    valOcrCell.style.color = valColor; 
                }
            }

            if (idpel && State.customerData[idpel]) {
                State.customerData[idpel].hasil_ocr = finalNum;
                State.customerData[idpel].original_ocr_status = finalStatus;
                if (manualStatus !== 'Tidak') {
                    State.customerData[idpel].validasi_ocr = finalStatus;
                }
                
                if (finalStatus === 'Valid') {
                    const bl = this.el.selTahun.value + this.el.selBulan.value;
                    const ocrKey = `${idpel}_${bl}`;
                    State.ocrCache[ocrKey] = { hasil_ocr: finalNum, validasi_ocr: finalStatus, ts: Date.now() };
                    GM_setValue('OCR_CACHE', State.ocrCache);
                }
            }

            if (manualStatus !== 'Tidak' && finalStatus === 'Tidak Valid') {
                const tbody = rowElement.parentNode;
                if (tbody && tbody.tagName === 'TBODY') tbody.prepend(rowElement);
            }
            this.updateCharts();
        }

        async runAutoOCR() {
            if (State.isAutoOcrRunning) return;
            
            const rows = this.el.tableBody.querySelectorAll('tr');
            if (rows.length === 0) return;

            const bl = this.el.selTahun.value + this.el.selBulan.value;
            const rowsToProcess = [];

            rows.forEach(row => {
                const tdFoto0 = row.querySelector('td[data-photo-key="foto_0"]'); 
                if (!tdFoto0) return;
                const img = tdFoto0.querySelector('.col-photo-box'); 
                if (!img) return;
                
                const idpelCell = row.querySelector('td[data-col="idpel"]'); 
                const idpel = idpelCell ? idpelCell.textContent.trim() : null;
                const ocrKey = idpel ? `${idpel}_${bl}` : null; 
                
                const valOcrCellCheck = row.querySelector('td[data-col="validasi_ocr"]');
                const existingStatus = valOcrCellCheck ? valOcrCellCheck.textContent.trim() : '-';
                
                const isAlreadyValid = (ocrKey && Utils.isCacheValid(State.ocrCache[ocrKey])) || (existingStatus === 'Valid');
                const isSpinner = valOcrCellCheck ? valOcrCellCheck.innerHTML.includes('spinner') : false;
                
                if (isAlreadyValid || isSpinner) return;
                
                rowsToProcess.push({ row, img });
            });

            if (rowsToProcess.length === 0) return;

            State.isAutoOcrRunning = true;
            let cursor = 0;
            let successCount = 0, failCount = 0;
            const totalToProcess = rowsToProcess.length; 
            const skippedCount = rows.length - totalToProcess;
            const startTime = Date.now();

            const ocrWorker = async () => {
                while (cursor < rowsToProcess.length) {
                    const { row, img } = rowsToProcess[cursor++];
                    try {
                        await this.runOCR(img, row, true);
                        const ocrCell = row.querySelector('td[data-col="hasil_ocr"]'); const newVal = ocrCell ? ocrCell.textContent : "";
                        if (newVal !== "-" && newVal !== "Error" && newVal !== "Kosong" && newVal !== "") successCount++; else failCount++;
                    } catch(e) { failCount++; console.error('[Auto OCR] Error:', e); }
                }
            };
            
            await Promise.all(Array.from({ length: Math.min(Config.OCR_CONCURRENCY, rowsToProcess.length) }, () => ocrWorker()));
            State.isAutoOcrRunning = false;

            const endTime = Date.now(); const elapsedMs = endTime - startTime;
            const mins = Math.floor(elapsedMs / 60000); const secs = Math.floor((elapsedMs % 60000) / 1000);
            const timeStr = `${String(mins).padStart(2, '0')} Menit ${String(secs).padStart(2, '0')} Detik`;

            alert(`Proses Auto OCR Selesai!\nBerhasil: ${successCount}\nGagal: ${failCount}\nDilewati (Sudah Valid): ${skippedCount}\n\nWaktu Penyelesaian: ${timeStr}`);
        }

        async runBulkOCR() {
            if (!State.apiKey) { State.apiKey = 'http://127.0.0.1:8000'; }
            const rows = this.el.tableBody.querySelectorAll('tr');
            if (rows.length === 0) { alert('Tidak ada data untuk di-OCR.'); return; }

            const btn = this.el.btnOcrAll; const originalBtnHtml = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Proses OCR...'; btn.disabled = true;

            let successCount = 0, failCount = 0, skippedCount = 0, doneCount = 0;
            const bl = this.el.selTahun.value + this.el.selBulan.value;
            const rowsToProcess = [];

            rows.forEach(row => {
                const tdFoto0 = row.querySelector('td[data-photo-key="foto_0"]'); if (!tdFoto0) return;
                const img = tdFoto0.querySelector('.col-photo-box'); if (!img) return;
                const idpelCell = row.querySelector('td[data-col="idpel"]'); const idpel = idpelCell ? idpelCell.textContent.trim() : null;
                const ocrKey = idpel ? `${idpel}_${bl}` : null; 
                const valOcrCellCheck = row.querySelector('td[data-col="validasi_ocr"]');
                const existingStatus = valOcrCellCheck ? valOcrCellCheck.textContent.trim() : '-';
                
                const isAlreadyValid = (ocrKey && Utils.isCacheValid(State.ocrCache[ocrKey])) || (existingStatus === 'Valid');
                if (isAlreadyValid) { skippedCount++; return; }
                
                rowsToProcess.push({ row, img });
            });

            const totalToProcess = rowsToProcess.length; 
            const startTime = Date.now();
            let cursor = 0;

            const ocrWorker = async () => {
                while (cursor < rowsToProcess.length) {
                    const { row, img } = rowsToProcess[cursor++];
                    await this.runOCR(img, row, true); doneCount++;
                    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> OCR (${doneCount}/${totalToProcess})`;
                    const ocrCell = row.querySelector('td[data-col="hasil_ocr"]'); const newVal = ocrCell ? ocrCell.textContent : "";
                    if (newVal !== "-" && newVal !== "Error" && newVal !== "Kosong" && newVal !== "") successCount++; else failCount++;
                }
            };
            await Promise.all(Array.from({ length: Math.min(Config.OCR_CONCURRENCY, rowsToProcess.length) }, () => ocrWorker()));

            const endTime = Date.now(); const elapsedMs = endTime - startTime;
            const mins = Math.floor(elapsedMs / 60000); const secs = Math.floor((elapsedMs % 60000) / 1000);
            const timeStr = `${String(mins).padStart(2, '0')} Menit ${String(secs).padStart(2, '0')} Detik`;

            btn.innerHTML = originalBtnHtml; btn.disabled = false; this.updateCharts();
            alert(`Proses OCR Semua Foto Selesai!\nBerhasil: ${successCount}\nGagal: ${failCount}\nDilewati (Sudah Valid): ${skippedCount}\n\nWaktu Penyelesaian: ${timeStr}`);
        }

        // ==========================================
        // CROP MODAL LOGIC
        // ==========================================
        openCropModal(img, row) {
            if (typeof Cropper === 'undefined') {
                alert('Library Cropper.js gagal dimuat. Periksa koneksi internet Anda.');
                return;
            }
            this.currentCropData = { img, row };
            this.el.cropOverlay.style.display = 'flex';
            
            this.el.cropImg.onload = () => {
                if (this.cropper) this.cropper.destroy();
                this.cropper = new Cropper(this.el.cropImg, {
                    viewMode: 1,
                    autoCropArea: 0.8,
                    responsive: true,
                    background: false
                });
            };
            this.el.cropImg.src = img.src;
        }

        closeCropModal() {
            this.el.cropOverlay.style.display = 'none';
            if (this.cropper) {
                this.cropper.destroy();
                this.cropper = null;
            }
        }

        async applyCrop() {
            if (!this.cropper || !this.currentCropData) return;
            
            const canvas = this.cropper.getCroppedCanvas({
                maxWidth: 1024,
                maxHeight: 1024,
                imageSmoothingQuality: 'high'
            });
            
            if (!canvas) {
                alert('Gagal melakukan crop gambar.');
                return;
            }
            
            const base64 = canvas.toDataURL('image/jpeg', 0.85);
            const { img, row } = this.currentCropData;
            const idpel = row.querySelector('td[data-col="idpel"]').textContent.trim();
            const td = img.closest('td[data-photo-key]');
            const photoKey = td ? td.dataset.photoKey : null;
            
            if (idpel && photoKey) {
                State.customPhotos[`${idpel}_${photoKey}`] = base64;
                img.src = base64;
                img.dataset.cached = "true"; 
                
                const pc = img.closest('.photo-container');
                let resetBtn = pc.querySelector('.reset-photo-btn');
                if (!resetBtn) {
                    resetBtn = document.createElement('div');
                    resetBtn.className = 'reset-photo-btn';
                    resetBtn.dataset.idpel = idpel;
                    resetBtn.dataset.key = photoKey;
                    resetBtn.title = "Hapus foto";
                    resetBtn.innerHTML = '&times;';
                    pc.insertBefore(resetBtn, pc.firstChild);
                }
            }
            
            this.closeCropModal();
            
            // AUTO OCR USING CROPPED IMAGE
            this.runOCR(img, row, false);
        }

        clearData() { this.el.inputIdpel.value = ''; this.el.tableBody.innerHTML = ''; State.customerData = {}; this.updateCharts(); }

        handleSort(e) {
            const t = e.target.closest('th'); if(!t) return;
            const ci = t.dataset.col, ct = t.dataset.type;
            if(!ci) return;
            if(State.sortState.col === ci) State.sortState.dir = State.sortState.dir === 'a' ? 'd' : 'a'; 
            else { State.sortState.col = ci; State.sortState.dir = 'a'; }
            const tb = this.el.tableBody;
            Array.from(tb.querySelectorAll("tr")).sort((a, b) => {
                let va = a.querySelector(`td[data-col="${ci}"]`)?.textContent || '';
                let vb = b.querySelector(`td[data-col="${ci}"]`)?.textContent || '';
                if(ct === 'num') { va = parseFloat(va.replace(/[^0-9.-]/g, '')) || 0; vb = parseFloat(vb.replace(/[^0-9.-]/g, '')) || 0; }
                else { va = va.toLowerCase(); vb = vb.toLowerCase(); }
                return va < vb ? (State.sortState.dir === 'a' ? -1 : 1) : (va > vb ? (State.sortState.dir === 'a' ? 1 : -1) : 0);
            }).forEach(tr => tb.appendChild(tr));
        }

        centerDashboard() {
            const w = Math.min(window.innerWidth * 0.92, 1450), h = Math.min(window.innerHeight * 0.88, 820);
            this.el.wrapper.style.width = w + 'px'; this.el.wrapper.style.height = h + 'px';
            this.el.wrapper.style.left = Math.max(0, (window.innerWidth - w) / 2) + 'px';
            this.el.wrapper.style.top = Math.max(0, (window.innerHeight - h) / 2) + 'px';
        }

        toggleDashboard() {
            if (this.el.wrapper.style.display === 'flex') { this.el.wrapper.style.display = 'none'; } 
            else { if (!this.el.wrapper.style.left || this.el.wrapper.style.left === '0px') this.centerDashboard(); this.el.wrapper.style.display = 'flex'; this.updateCharts(); }
        }

        toggleMaximize() {
            if (!this.el.wrapper.classList.contains('is-max')) { 
                this.savedPos = { left: this.el.wrapper.style.left, top: this.el.wrapper.style.top, width: this.el.wrapper.style.width, height: this.el.wrapper.style.height }; 
                this.el.wrapper.classList.add('is-max'); this.el.btnMaximize.innerHTML = '<i class="fas fa-compress"></i>'; 
            } else { 
                this.el.wrapper.classList.remove('is-max'); Object.assign(this.el.wrapper.style, this.savedPos); this.el.btnMaximize.innerHTML = '<i class="fas fa-expand"></i>'; 
            }
        }

        initDragResize() {
            const startDrag = (e) => {
                if (e.target.closest('.hdr-btn') || this.el.wrapper.classList.contains('is-max')) return;
                const pt = e.touches ? e.touches[0] : e;
                State.dragMode = 'drag'; State.dragStartX = pt.clientX; State.dragStartY = pt.clientY; State.startLeft = this.el.wrapper.offsetLeft; State.startTop = this.el.wrapper.offsetTop;
                this.el.wrapper.classList.add('is-dragging');
                if(!e.touches) e.preventDefault();
            };
            const startResize = (e) => {
                if (this.el.wrapper.classList.contains('is-max')) return;
                const pt = e.touches ? e.touches[0] : e;
                State.dragMode = 'resize'; State.dragStartX = pt.clientX; State.dragStartY = pt.clientY; State.startWidth = this.el.wrapper.offsetWidth; State.startHeight = this.el.wrapper.offsetHeight;
                if(!e.touches) e.preventDefault();
            };
            const onMove = (e) => {
                if (!State.dragMode) return;
                const pt = e.touches ? e.touches[0] : e;
                if (State.dragMode === 'drag') { 
                    this.el.wrapper.style.left = Math.max(-this.el.wrapper.offsetWidth + 200, Math.min(State.startLeft + (pt.clientX - State.dragStartX), window.innerWidth - 150)) + 'px'; 
                    this.el.wrapper.style.top = Math.max(0, Math.min(State.startTop + (pt.clientY - State.dragStartY), window.innerHeight - 50)) + 'px'; 
                }
                if (State.dragMode === 'resize') { 
                    this.el.wrapper.style.width = Math.max(700, State.startWidth + (pt.clientX - State.dragStartX)) + 'px'; 
                    this.el.wrapper.style.height = Math.max(450, State.startHeight + (pt.clientY - State.dragStartY)) + 'px'; 
                }
            };
            const endDrag = () => { if (State.dragMode) { State.dragMode = null; this.el.wrapper.classList.remove('is-dragging'); } };

            this.el.dragHeader.addEventListener('mousedown', startDrag);
            this.el.dragHeader.addEventListener('touchstart', startDrag, { passive: true });
            this.el.resizeHandle.addEventListener('mousedown', startResize);
            this.el.resizeHandle.addEventListener('touchstart', startResize, { passive: true });
            document.addEventListener('mousemove', onMove);
            document.addEventListener('touchmove', onMove, { passive: true });
            document.addEventListener('mouseup', endDrag);
            document.addEventListener('touchend', endDrag);
        }

        initPhotoZoom() {
            this.el.wrapper.addEventListener('mouseover', e => {
                const pc = e.target.closest('.photo-container');
                if (pc && !pc.classList.contains('drag-over')) {
                    const img = pc.querySelector('.col-photo-box');
                    if(img) { img.style.transform = 'scale(3.5)'; img.style.borderRadius = '50%'; img.style.boxShadow = '0 15px 35px rgba(0,0,0,0.7), 0 0 0 4px #fff'; img.style.border = '2px solid #fff'; img.style.zIndex = '999'; }
                }
            });
            this.el.wrapper.addEventListener('mousemove', e => {
                const pc = e.target.closest('.photo-container');
                if (pc) {
                    const img = pc.querySelector('.col-photo-box');
                    if(img) { const r = pc.getBoundingClientRect(); img.style.transformOrigin = `${e.clientX - r.left}px ${e.clientY - r.top}px`; }
                }
            });
            this.el.wrapper.addEventListener('mouseout', e => {
                const pc = e.target.closest('.photo-container');
                if (pc) {
                    const img = pc.querySelector('.col-photo-box');
                    if(img) { img.style.transform = 'scale(1)'; img.style.borderRadius = '8px'; img.style.boxShadow = 'none'; img.style.border = 'none'; img.style.zIndex = '1'; }
                }
            });

            this.el.photoModal.addEventListener('mousemove', e => {
                let r = this.el.modalImg.getBoundingClientRect(); let x = e.clientX - r.left, y = e.clientY - r.top;
                if (x > 0 && x < r.width && y > 0 && y < r.height) {
                    this.el.modalLoupe.style.display = 'block'; this.el.modalLoupe.style.left = (e.clientX - 125) + 'px'; this.el.modalLoupe.style.top = (e.clientY - 125) + 'px';
                    this.el.loupeImg.src = this.el.modalImg.src; this.el.loupeImg.style.width = (r.width * 3) + 'px'; this.el.loupeImg.style.height = (r.height * 3) + 'px';
                    this.el.loupeImg.style.left = -(x * 3 - 125) + 'px'; this.el.loupeImg.style.top = -(y * 3 - 125) + 'px';
                } else { this.el.modalLoupe.style.display = 'none'; }
            });
            this.el.photoModal.addEventListener('mouseleave', () => this.el.modalLoupe.style.display = 'none');

            const closeModal = () => {
                this.el.photoModal.style.display = 'none';
                this.el.modalLoupe.style.display = 'none';
            };

            this.el.modalClose.addEventListener('click', (e) => {
                e.stopPropagation();
                closeModal();
            });

            this.el.photoModal.addEventListener('click', (e) => {
                if (e.target === this.el.photoModal) {
                    closeModal();
                }
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.el.photoModal.style.display === 'block') {
                    closeModal();
                }
            });
        }

        updateThemeIcon() { this.el.themeBtn.innerHTML = State.theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>'; }
        openPdfModal() {
            if (document.querySelectorAll('#tabel-body-result tr').length === 0) { alert('Tidak ada data untuk dicetak.'); return; }
            this.el.pdfOverlay.style.display = 'flex';
        }
    }

    // ==========================================
    // 5. EXPORT MANAGER (EXCEL & PDF)
    // ==========================================
    class ExportManager {
        static colLetter(num) { let s = '', n = num; while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); } return s; }

        static async exportToExcel() {
            const t = document.getElementById('resultTable');
            if (!t || t.rows.length <= 1) { alert('Tidak ada data untuk di-export.'); return; }
            if (typeof ExcelJS === 'undefined') { alert('ExcelJS belum dimuat. Periksa koneksi internet.'); return; }

            const ui = window._UI; 
            const ac = ui.getActiveColumns(), j = parseInt(ui.el.selJmlFoto.value);
            const bl = ui.el.selTahun.value + ui.el.selBulan.value;
            const wb = new ExcelJS.Workbook(); wb.creator = 'Dashboard Evaluasi Foto KWH Meter'; wb.created = new Date();
            const ws = wb.addWorksheet('Data PLN', { views: [{ state: 'frozen', ySplit: 1 }] });

            const numColIds = new Set(['no','daya','stan_lalu','stan_baca','hasil_ocr','pemakaian','pakai_bln_lalu','selisih_kwh','jamnyala']);
            const widthMap = { no:5, idpel:14, nama:24, nomor_meter:16, tarif:8, daya:8, koduk:14, gardu_tiang:28, lbkb:22, stan_lalu:12, stan_baca:12, hasil_ocr:14, validasi_ocr:16, pemakaian:14, pakai_bln_lalu:16, selisih_kwh:14, jamnyala:12, petugas:18, validasi:12 };

            const colDefs = [];
            ac.forEach(c => colDefs.push({ header: c.label, key: c.id, width: widthMap[c.id] || 15 }));
            colDefs.push({ header: `FOTO ${Utils.getMonthLabel(bl)}`, key: 'foto_0', width: 22 });
            if (document.getElementById('chk-foto_bln_terakhir').checked) colDefs.push({ header: `FOTO 2 ${Utils.getMonthLabel(bl)}`, key: 'foto_s2', width: 22 });
            for (let f = 1; f < j; f++) colDefs.push({ header: `FOTO ${Utils.getMonthLabel(String(parseInt(bl) - f))}`, key: `foto_${f}`, width: 22 });
            ws.columns = colDefs;

            const hdrRow = ws.getRow(1); hdrRow.height = 30;
            hdrRow.eachCell((cell) => { cell.font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 10, name: 'Arial' }; cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF007BB5' } }; cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true }; cell.border = { top: { style: 'thin', color: { argb: 'FF455A64' } }, bottom: { style: 'thin', color: { argb: 'FF455A64' } }, left: { style: 'thin', color: { argb: 'FF455A64' } }, right: { style: 'thin', color: { argb: 'FF455A64' } } }; });
            try { ws.autoFilter = { from: 'A1', to: `${this.colLetter(colDefs.length)}1` }; } catch(e) {}

            const baseBorder = { top: { style: 'thin', color: { argb: 'FFB0BEC5' } }, bottom: { style: 'thin', color: { argb: 'FFB0BEC5' } }, left: { style: 'thin', color: { argb: 'FFB0BEC5' } }, right: { style: 'thin', color: { argb: 'FFB0BEC5' } } };
            const bodyRows = t.querySelectorAll('#tabel-body-result tr');
            bodyRows.forEach((tr, rowIdx) => {
                const tds = tr.querySelectorAll('td'); const rowData = {};
                ac.forEach((c, ci) => {
                    const td = tds[ci]; if (!td) { rowData[c.id] = ''; return; }
                    if (c.id === 'validasi') { const sel = td.querySelector('select.sel-validasi'); rowData[c.id] = sel ? sel.options[sel.selectedIndex].text : td.textContent.trim(); }
                    else if (numColIds.has(c.id)) { const raw = td.textContent.trim().replace(/[^0-9.\-]/g, ''); rowData[c.id] = raw !== '' ? parseFloat(raw) : 0; }
                    else if (c.id === 'gardu_tiang') { rowData[c.id] = td.textContent.trim().replace(/[\n\r]+/g, ' / '); } else { rowData[c.id] = td.textContent.trim(); }
                });

                let photoIdx = ac.length; const photoKeys = ['foto_0'];
                if (document.getElementById('chk-foto_bln_terakhir').checked) photoKeys.push('foto_s2');
                for (let f = 1; f < j; f++) photoKeys.push(`foto_${f}`);
                const idpelRow = Object.values(rowData).find(v => typeof v === 'string' && v.length === 12 && /^\d+$/.test(v)) || '';
                photoKeys.forEach(pk => { if (tds[photoIdx]) { const img = tds[photoIdx].querySelector('.col-photo-box'); rowData[pk] = (idpelRow && State.customPhotos[`${idpelRow}_${pk}`]) ? '[FOTO CUSTOM]' : (img ? img.src : '-'); } photoIdx++; });

                const excelRow = ws.addRow(rowData); excelRow.height = 22;
                excelRow.eachCell({ includeEmpty: false }, (cell) => { cell.font = { size: 10, color: { argb: 'FF263238' }, name: 'Arial' }; cell.alignment = { horizontal: 'center', vertical: 'middle' }; cell.border = { ...baseBorder }; });
                if (rowIdx % 2 === 1) { excelRow.eachCell({ includeEmpty: false }, (cell) => { if (!cell.fill || !cell.fill.fgColor || cell.fill.fgColor.argb === 'FFFFFFFF') cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F8F9' } }; }); }
            });

            try {
                const buffer = await wb.xlsx.writeBuffer(); const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `Data_PLN_${new Date().toLocaleDateString('id-ID').replace(/\//g, '-')}.xlsx`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(a.href);
            } catch (err) { alert('Gagal membuat file .xlsx: ' + err.message); }
        }

        static exportToPDF() {
            const ui = window._UI;
            const uid = document.getElementById('pdf-uid').value.trim();
            const up3 = document.getElementById('pdf-up3').value.trim();
            const ulp = document.getElementById('pdf-ulp').value.trim();
            const namaKoor = document.getElementById('pdf-nama-koor').value.trim();
            const namaManager = document.getElementById('pdf-nama-manager').value.trim();
            const namaTl = document.getElementById('pdf-nama-tl').value.trim();

            if (!uid || !up3 || !ulp || !namaKoor || !namaManager || !namaTl) { alert('Semua isian wajib diisi!'); return; }
            
            State.pdfData = { uid, up3, ulp, koor: namaKoor, manager: namaManager, tl: namaTl };
            GM_setValue('PDF_DATA', State.pdfData);

            const tglObj = new Date();
            const strTanggalHarian = String(tglObj.getDate()).padStart(2, '0') + ' ' + 
                ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'][tglObj.getMonth()] + ' ' + 
                tglObj.getFullYear();
            const strUlpCapitalized = ulp.charAt(0).toUpperCase() + ulp.slice(1).toLowerCase();

            const bulanVal = ui.el.selBulan.value;
            const tahunVal = ui.el.selTahun.value;
            const bulanFull = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'][parseInt(bulanVal)-1];

            const originalTable = document.getElementById('resultTable'); const clonedTable = originalTable.cloneNode(true);
            clonedTable.removeAttribute('id'); clonedTable.classList.add('print-table');

            clonedTable.querySelectorAll('select.sel-validasi').forEach(sel => { const td = sel.closest('td'); td.innerHTML = sel.options[sel.selectedIndex].text; });
            clonedTable.querySelectorAll('.sort-icon, .reset-photo-btn, .ocr-photo-btn, .crop-photo-btn').forEach(el => el.remove());

            let printTotalValid = 0, printTotalTidak = 0, printTotalOcrBerhasil = 0; 
            const printAllRows = document.querySelectorAll('#tabel-body-result tr'); 
            const printTotalKeseluruhan = printAllRows.length;
            printAllRows.forEach(row => {
                const valCell = row.querySelector('td[data-col="validasi_ocr"]'); 
                const status = valCell ? valCell.textContent.trim() : '-';
                if (status === 'Valid') printTotalValid++; 
                else if (status === 'Tidak Valid') printTotalTidak++;

                const ocrCell = row.querySelector('td[data-col="hasil_ocr"]');
                const ocrVal = ocrCell ? ocrCell.textContent.trim() : '-';
                if (ocrVal !== '-' && ocrVal !== 'Error' && ocrVal !== 'Kosong' && ocrVal !== '') printTotalOcrBerhasil++;
            });

            const printTotalVT = printTotalValid + printTotalTidak; 
            const printBelumValidasi = printTotalKeseluruhan - printTotalVT;
            const persenValidPdf = printTotalVT > 0 ? Math.round((printTotalValid / printTotalVT) * 100) : 0;
            const persenTidakPdf = printTotalVT > 0 ? 100 - persenValidPdf : 0;
            const persenOcrPdf = printTotalKeseluruhan > 0 ? Math.round((printTotalOcrBerhasil / printTotalKeseluruhan) * 100) : 0;
            const persenOcrGagalPdf = 100 - persenOcrPdf;

            let imgValid = '', imgOcr = '', imgPercent = '';
            if (State.charts.printValid) {
                State.charts.printValid.data.datasets[0].data = [printTotalValid, printTotalTidak];
                State.charts.printValid.update('none'); 
                imgValid = State.charts.printValid.toBase64Image();
            }
            if (State.charts.printOcr) {
                State.charts.printOcr.data.datasets[0].data = [printTotalOcrBerhasil, Math.max(0, printTotalKeseluruhan - printTotalOcrBerhasil)];
                State.charts.printOcr.update('none'); 
                imgOcr = State.charts.printOcr.toBase64Image();
            }
            if (State.charts.printPercent) {
                State.charts.printPercent.data.datasets[0].data = [persenValidPdf, persenTidakPdf];
                State.charts.printPercent.update('none'); 
                imgPercent = State.charts.printPercent.toBase64Image();
            }

            const printArea = document.getElementById('pln-print-area');
            printArea.innerHTML = `
                <div class="print-header">
                    <div class="print-header-left">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/9/97/Logo_PLN.png">
                        <div class="portal-text">PORTAL ACMT<br><span>EVALUASI FOTO METER</span></div>
                    </div>
                    <div class="print-header-right">
                        UID ${uid.toUpperCase()}<br>
                        UP3 ${up3.toUpperCase()}<br>
                        ULP ${ulp.toUpperCase()}
                    </div>
                </div>
                <div class="print-title">
                    EVALUASI FOTO METER ACMT<br>
                    BULAN ${bulanFull.toUpperCase()} ${tahunVal}
                </div>
                <div class="print-summary">
                    <div class="print-summary-text">
                        <div class="print-summary-title">Ringkasan &amp; Keterangan Jumlah Data</div>
                        <div class="print-summary-legend">
                            <div class="print-summary-item">Total Keseluruhan Data: <b>${printTotalKeseluruhan}</b></div>
                            <div class="print-summary-item"><span class="print-summary-dot" style="background:#1c8b3f"></span> Valid: <b>${printTotalValid}</b> data (${persenValidPdf}%)</div>
                            <div class="print-summary-item"><span class="print-summary-dot" style="background:#d70015"></span> Tidak Valid: <b>${printTotalTidak}</b> data (${persenTidakPdf}%)</div>
                            ${printBelumValidasi > 0 ? `<div class="print-summary-item"><span class="print-summary-dot" style="background:#90a4ae"></span> Belum Tervalidasi: <b>${printBelumValidasi}</b> data</div>` : ''}
                        </div>
                    </div>
                    <div class="print-summary-charts">
                        ${imgValid ? `<div class="print-chart-item"><img src="${imgValid}" alt="Valid vs Tidak"><span>Valid / Tidak</span><span class="chart-val">${printTotalValid} / ${printTotalTidak} data</span></div>` : ''}
                        ${imgOcr ? `<div class="print-chart-item"><img src="${imgOcr}" alt="OCR Sukses/Gagal"><span>OCR Sukses / Gagal</span><span class="chart-val">${persenOcrPdf}% / ${persenOcrGagalPdf}%</span></div>` : ''}
                        ${imgPercent ? `<div class="print-chart-item"><img src="${imgPercent}" alt="% Valid/Tidak"><span>% Valid / Tidak</span><span class="chart-val">${persenValidPdf}% / ${persenTidakPdf}%</span></div>` : ''}
                    </div>
                </div>
                <div class="print-table-container">
                    ${clonedTable.outerHTML}
                </div>
                <div class="print-signatures">
                    <div class="sig-col">
                        <div class="sig-title"><br>Koordinator</div>
                        <div class="sig-name">${namaKoor}</div>
                    </div>
                    <div class="sig-col">
                        <div class="sig-title"><br>TL Transaksi Energi</div>
                        <div class="sig-name">${namaTl}</div>
                    </div>
                    <div class="sig-col">
                        <div class="sig-title">${strUlpCapitalized}, ${strTanggalHarian}<br>Mengetahui,<br>Manager ULP</div>
                        <div class="sig-name">${namaManager}</div>
                    </div>
                </div>
            `;

            ui.el.pdfOverlay.style.display = 'none';
            setTimeout(() => { window.print(); }, 500);
        }
    }

    // ==========================================
    // 6. MAIN INITIALIZATION
    // ==========================================
    function initKeepAlive() {
        const ping = () => { GM_xmlhttpRequest({ method: 'GET', url: Config.PING_URL, headers: { 'Cache-Control': 'no-cache' }, onload: function(r) { if (r.status === 401 || r.status === 302) clearInterval(timer); } }); };
        const timer = setInterval(ping, Config.PING_INTERVAL);
        setTimeout(() => { ping(); }, 60000);
        setInterval(() => document.body.dispatchEvent(new MouseEvent('mousemove', { bubbles: true })), 60000);
    }

    function init() {
        try {
            console.log('[Dashboard] Memulai inisialisasi...');
            
            Utils.cleanupCache();
            initKeepAlive();
            
            UIController.prototype.columns = [
                { id: 'no', label: 'NO', type: 'num' }, { id: 'idpel', label: 'IDPEL', type: 'text' }, { id: 'nama', label: 'NAMA', type: 'text' },
                { id: 'nomor_meter', label: 'NO METER', type: 'text' }, { id: 'tarif', label: 'TARIF', type: 'text' }, { id: 'daya', label: 'DAYA', type: 'num' },
                { id: 'koduk', label: 'KODUK', type: 'text' }, { id: 'gardu_tiang', label: 'GARDU & TIANG', type: 'text' }, { id: 'lbkb', label: 'LBKB', type: 'text' },
                { id: 'stan_lalu', label: 'STAN LALU', type: 'num' }, { id: 'stan_baca', label: 'STAN BACA', type: 'num' },
                { id: 'hasil_ocr', label: 'HASIL OCR', type: 'text' }, { id: 'validasi_ocr', label: 'VALIDASI OCR', type: 'text' },
                { id: 'pemakaian', label: 'PAKAI (kWh)', type: 'num' },
                { id: 'pakai_bln_lalu', label: 'PAKAI BLN LALU', type: 'num' }, { id: 'selisih_kwh', label: 'SELISIH (kWh)', type: 'num' }, { id: 'jamnyala', label: 'JAM NYALA', type: 'num' },
                { id: 'petugas', label: 'PETUGAS', type: 'text' }, { id: 'validasi', label: 'VALIDASI', type: 'text' }
            ];

            const ui = new UIController();
            window._UI = ui;

            const uncheckedCols = ['nomor_meter', 'koduk', 'gardu_tiang'];
            ui.columns.forEach(c => { 
                const i = document.createElement('label'); 
                i.className = 'col-toggle-item'; 
                const isChecked = !uncheckedCols.includes(c.id);
                i.innerHTML = `<input type="checkbox" id="chk-${c.id}" ${isChecked ? 'checked' : ''}> ${c.label}`; 
                ui.el.toggleContainer.appendChild(i); 
            });
            const fotoBlnToggle = document.createElement('label'); 
            fotoBlnToggle.className = 'col-toggle-item'; 
            fotoBlnToggle.innerHTML = `<input type="checkbox" id="chk-foto_bln_terakhir"> FOTO 2`; 
            ui.el.toggleContainer.appendChild(fotoBlnToggle);

            ui.centerDashboard();
            ui.renderTableHead();

            console.log('%c🚀 Dashboard Evaluasi Foto v88.14 Loaded Successfully', 'color: #00A2E9; font-weight: bold; font-size: 14px;');
        } catch(e) {
            console.error('[Dashboard] Error saat inisialisasi:', e);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(init, 1500));
    } else {
        setTimeout(init, 1500);
    }

})();