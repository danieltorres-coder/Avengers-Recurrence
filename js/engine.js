/* ================================================================
   AVENGERS RECURRENCE — ENGINE v4.0
   Modular: State → DataEngine → HistoryEngine → ImporterEngine → Render
   ================================================================ */
'use strict';

// ────────────────────────────────────────────────────────────────
//  CONSTANTS
// ────────────────────────────────────────────────────────────────
const VERSION     = '4.0';
const ADMIN_PASS  = '2187';
const LS          = 'avr4_';  // localStorage namespace

const DOW_EN   = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const DOW_ES   = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'];
const DOW_FULL = {Monday:'Lunes',Tuesday:'Martes',Wednesday:'Miercoles',Thursday:'Jueves',Friday:'Viernes',Saturday:'Sabado',Sunday:'Domingo'};
const MES_ES   = {'2026-01':'Enero','2026-02':'Febrero','2026-03':'Marzo','2026-04':'Abril','2026-05':'Mayo','2026-06':'Junio','2026-07':'Julio','2026-08':'Agosto','2026-09':'Septiembre','2026-10':'Octubre','2026-11':'Noviembre','2026-12':'Diciembre'};

// ────────────────────────────────────────────────────────────────
//  APP_STATE — single source of truth
// ────────────────────────────────────────────────────────────────
const APP_STATE = {
  currentView:        'overview',
  currentPeriod:      'month',
  viewMode:           'agent',
  currentAgent:       null,
  currentSupervisor:  null,
  currentMonth:       null,
  currentWeek:        null,
  dataReady:          false,
  adminAuth:          false,
};

// ────────────────────────────────────────────────────────────────
//  STORAGE ENGINE
// ────────────────────────────────────────────────────────────────
const Store = {
  get(k, fb = null)  { try { const r = localStorage.getItem(LS+k); return r ? JSON.parse(r) : fb; } catch { return fb; } },
  set(k, v)          { try { localStorage.setItem(LS+k, JSON.stringify(v)); return true; } catch { return false; } },
  del(k)             { localStorage.removeItem(LS+k); },
  keys()             { const o=[]; for(let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); if(k?.startsWith(LS)) o.push(k.slice(LS.length)); } return o; },
  sizeKB()           { return Math.round(this.keys().reduce((s,k)=>{ const r=localStorage.getItem(LS+k); return s+(r?r.length:0); },0)/1024); },
  clearImported()    { this.keys().filter(k=>!['goals','links_config','state_agent','state_sup','state_month','state_period'].includes(k)).forEach(k=>this.del(k)); },
};

// ────────────────────────────────────────────────────────────────
//  DATA ENGINE
// ────────────────────────────────────────────────────────────────
const DataEngine = {
  _agents:   null,
  _rows:     [],
  _erRows:   [],
  _erCols:   [],
  _erShort:  {},
  _adherencia: {},
  _commissions: {},
  _linksConfig: {},

  // Accessors
  get agents()       { return this._agents?.agents_meta || {}; },
  get agentList()    { return this._agents?.agents || []; },
  get supervisors()  { return this._agents?.supervisors || {}; },
  get supList()      { return this._agents?.supervisor_list || []; },
  get months()       { return this._agents?.months || []; },
  get weeks()        { return this._agents?.weeks || []; },
  get ranking()      { return this._agents?.ranking_ytd || []; },
  get erCols()       { return this._erCols; },
  get erShort()      { return this._erShort; },
  get rows()         { return this._rows; },
  get erRows()       { return this._erRows; },
  get adherencia()   { return this._adherencia; },
  get commissions()  { return this._commissions; },
  get linksConfig()  { return this._linksConfig; },

  // ── LOAD ALL ──
  async loadAll() {
    await Promise.all([
      this._loadAgents(),
      this._loadHistory(),
      this._loadER(),
      this._loadAdherencia(),
      this._loadCommissions(),
      this._loadLinksConfig(),
    ]);
    APP_STATE.dataReady = true;
    console.log(`[DataEngine v${VERSION}] Ready. Rows:${this._rows.length} ER:${this._erRows.length}`);
  },

  async _loadAgents() {
    // Priority: localStorage (imported) → embedded RAW → fetch /data/agents_meta.json
    const cached = Store.get('agents_meta');
    if (cached) { this._agents = cached; return; }
    if (typeof RAW !== 'undefined') {
      this._agents = {
        version:'4.0', updated: RAW.meta?.updated || '2026-05-13',
        agents:          RAW.agents || [],
        agents_meta:     RAW.agents_meta || {},
        supervisors:     RAW.supervisors || {},
        supervisor_list: RAW.supervisor_list || [],
        months:          RAW.months || [],
        weeks:           RAW.weeks || [],
        ranking_ytd:     RAW.ranking_ytd || [],
      };
      return;
    }
    // Fetch from /data/
    try {
      const r = await fetch('./data/agents_meta.json');
      if (r.ok) this._agents = await r.json();
    } catch(e) { console.warn('[DataEngine] agents_meta.json not found:', e.message); }
  },

  async _loadHistory() {
    const cached = Store.get('history_2026');
    if (cached) { this._expandRows(cached); return; }
    if (typeof RAW !== 'undefined') { this._expandRows({ keys: RAW.keys, rows: RAW.rows }); return; }
    try {
      const r = await fetch('./data/history_2026.json');
      if (r.ok) {
        const h = await r.json();
        this._agents = { ...this._agents, months: h.months, weeks: h.weeks };
        this._expandRows(h);
      }
    } catch(e) { console.warn('[DataEngine] history_2026.json not found'); }
  },

  async _loadER() {
    const cached = Store.get('er_2026');
    if (cached) { this._expandERRows(cached); return; }
    if (typeof ER_RAW !== 'undefined') { this._expandERRows(ER_RAW); return; }
    try {
      const r = await fetch('./data/er_2026.json');
      if (r.ok) this._expandERRows(await r.json());
    } catch(e) { console.warn('[DataEngine] er_2026.json not found'); }
  },

  async _loadAdherencia() {
    this._adherencia = Store.get('adherencia', {});
    if (!Object.keys(this._adherencia).length) {
      try { const r = await fetch('./data/adherencia.json'); if(r.ok) this._adherencia = (await r.json()).months || {}; } catch {}
    }
  },

  async _loadCommissions() {
    this._commissions = Store.get('commissions', {});
    if (!Object.keys(this._commissions).length) {
      try { const r = await fetch('./data/commissions.json'); if(r.ok) this._commissions = (await r.json()).months || {}; } catch {}
    }
  },

  async _loadLinksConfig() {
    this._linksConfig = Store.get('links_config', {});
    if (!Object.keys(this._linksConfig).length) {
      try { const r = await fetch('./data/links_config.json'); if(r.ok) this._linksConfig = (await r.json()).months || {}; } catch {}
    }
  },

  _expandRows(h) {
    if (!h?.keys || !h?.rows) return;
    const K = h.keys;
    this._rows = h.rows.map(r => { const o = {}; K.forEach((k,i)=>o[k]=r[i]); return o; });
  },

  _expandERRows(er) {
    if (!er?.cols || !er?.rows) return;
    this._erCols  = er.cols;
    this._erShort = er.short || {};
    const C = er.cols;
    this._erRows = er.rows.map(r => {
      const o = { agent:r[0], date:r[1], month:r[2], week:r[3], dow:r[4] };
      C.forEach((c,i) => { o[c] = r[5][String(i)] || 0; });
      o.total_errors = C.slice(1).reduce((s,c)=>s+(o[c]||0), 0);
      return o;
    });
  },

  // ── MERGE new month data (from importer) ──
  mergeMonth(monthStr, newRows, type = 'ops') {
    if (type === 'ops') {
      // Remove existing rows for that month
      this._rows = this._rows.filter(r => r.month !== monthStr);
      this._rows.push(...newRows);
      // Save to localStorage
      const keys = this._rows.length ? Object.keys(this._rows[0]) : [];
      const compressed = { keys, rows: this._rows.map(r => keys.map(k=>r[k])) };
      // Rebuild months & weeks
      const months = [...new Set(this._rows.map(r=>r.month))].sort();
      const weeks  = [...new Set(this._rows.map(r=>r.week_of_year||r.week).filter(Boolean))].sort();
      compressed.months = months; compressed.weeks = weeks;
      Store.set('history_2026', compressed);
      if (this._agents) {
        this._agents.months = months;
        this._agents.weeks  = weeks;
        this._rebuildRanking();
        Store.set('agents_meta', this._agents);
      }
      console.log(`[DataEngine] Merged ${newRows.length} rows for ${monthStr}`);
    } else if (type === 'adherencia') {
      this._adherencia[monthStr] = newRows;
      Store.set('adherencia', this._adherencia);
    } else if (type === 'commissions') {
      this._commissions[monthStr] = newRows;
      Store.set('commissions', this._commissions);
    }
  },

  saveLinksConfig() {
    Store.set('links_config', this._linksConfig);
  },

  _rebuildRanking() {
    const byAgent = groupBy(this._rows, 'agent');
    this._agents.ranking_ytd = Object.entries(byAgent).map(([ag, rows]) => {
      const a = aggAll(rows);
      const meta = this.agents[ag] || {};
      return { agent:ag, supervisor:meta.supervisor||'--', segmento:meta.segmento||'--',
        tenure_seg:meta.tenure_seg||'--', meses:meta.meses||0, fecha_ingreso:meta.fecha_ingreso||'', score:meta.score||null,
        ...a, cr:sd(a.sales,a.calls_2m), asp:sd(a.revenue,a.sales), sph:sd(a.sales,a.staff_h),
        rev_per_call:sd(a.revenue,a.calls_2m), rev_per_staff:sd(a.revenue,a.staff_h), occupancy:sd(a.oncall,a.staff_h) };
    }).sort((a,b) => b.revenue - a.revenue);
  },

  // ── Agent history structure ──
  buildAgentHistory(agName) {
    const all = this._rows.filter(r => r.agent === agName);
    const byM = groupBy(all,'month'), byW = groupBy(all, r=>r.week_of_year||r.week), byD = groupBy(all,'date'), byDOW = groupBy(all,'dow');
    const mk = rows => { const a=aggAll(rows); return {...a, cr:sd(a.sales,a.calls_2m), occ:sd(a.oncall,a.staff_h), asp:sd(a.revenue,a.sales), sph:sd(a.sales,a.staff_h), aht:sd(a.talk_time,a.calls_2m) }; };
    const monthly = Object.entries(byM).sort(([a],[b])=>a.localeCompare(b)).map(([month,rows])=>({month,...mk(rows)}));
    const weekly  = Object.entries(byW).sort(([a],[b])=>a.localeCompare(b)).map(([week,rows])=>({week,...mk(rows)}));
    const daily   = Object.entries(byD).sort(([a],[b])=>a.localeCompare(b)).map(([date,rows])=>({date,dow:rows[0]?.dow,week:rows[0]?.week_of_year||rows[0]?.week,month:rows[0]?.month,...mk(rows)}));
    const dow     = DOW_EN.map(d=>{ const rows=byDOW[d]||[]; const a=aggAll(rows); const n=[...new Set(rows.map(r=>r.date))].length; return {dow:d,n_days:n,...a,cr:sd(a.sales,a.calls_2m),avg_revenue:sd(a.revenue,n)}; });
    return { monthly, weekly, daily, dow };
  },

  // ── Adherence for an agent/month ──
  getAdherencia(agName, month) {
    const mData = this._adherencia[month];
    if (!mData) return null;
    return Array.isArray(mData) ? mData.find(r => r.agent === agName || r.Agent_Name === agName) : null;
  },

  // ── Commission for an agent/month ──
  getCommission(agName, month) {
    const mData = this._commissions[month];
    if (!mData) return null;
    return Array.isArray(mData) ? mData.find(r => r.agent === agName) : null;
  },
};

// ────────────────────────────────────────────────────────────────
//  HISTORY ENGINE — insights, coaching, patterns
// ────────────────────────────────────────────────────────────────
const HistoryEngine = {
  analyze(h) {
    return { insights: this._insights(h), coaching: this._coaching(h), patterns: this._patterns(h) };
  },
  _insights(h) {
    const ins=[], {monthly,dow}=h, vd=dow.filter(d=>d.avg_revenue>0);
    if(vd.length){ const b=vd.reduce((a,c)=>c.avg_revenue>a.avg_revenue?c:a); ins.push({t:'i',msg:'Mejor dia revenue: <b>'+DOW_FULL[b.dow]+'</b> — $'+Math.round(b.avg_revenue)+'/dia.'}); if(vd.length>1){const w=vd.reduce((a,c)=>c.avg_revenue<a.avg_revenue?c:a);if(w.dow!==b.dow)ins.push({t:'w',msg:'Menor revenue: <b>'+DOW_FULL[w.dow]+'</b> ($'+Math.round(w.avg_revenue)+'/dia).'});} const bCR=vd.reduce((a,c)=>c.cr>a.cr?c:a);ins.push({t:'i',msg:'Mayor CR los <b>'+DOW_FULL[bCR.dow]+'</b> ('+(bCR.cr*100).toFixed(1)+'%)'});}
    if(monthly.length>=2){const l=monthly[monthly.length-1],p=monthly[monthly.length-2];const d=l.revenue-p.revenue;if(d>0)ins.push({t:'o',msg:'Revenue subio $'+Math.round(d)+' vs '+(MES_ES[p.month]||p.month)+'.'});else if(d<0)ins.push({t:'w',msg:'Revenue bajo $'+Math.round(Math.abs(d))+' vs '+(MES_ES[p.month]||p.month)+'.'});}
    const avgOcc=monthly.filter(m=>m.occ>0).reduce((s,m)=>s+m.occ,0)/(monthly.filter(m=>m.occ>0).length||1);
    if(avgOcc<0.60)ins.push({t:'w',msg:'Occupancy '+(avgOcc*100).toFixed(1)+'% bajo meta 60%.'});else if(avgOcc>=0.80)ins.push({t:'o',msg:'Occupancy excelente: '+(avgOcc*100).toFixed(1)+'%.'});
    return ins.slice(0,6);
  },
  _coaching(h) {
    const tips=[],{monthly}=h,active=monthly.filter(m=>m.calls_2m>0);if(!active.length)return tips;
    const avgCR=active.reduce((s,m)=>s+m.cr,0)/active.length,avgOcc=active.reduce((s,m)=>s+m.occ,0)/active.length;
    const avgCalls=active.reduce((s,m)=>s+m.calls_2m,0)/active.length;
    if(avgCR<0.07)tips.push({t:'b',msg:'CR '+(avgCR*100).toFixed(1)+'% muy bajo. Objetivo 10%+.'});else if(avgCR<0.10)tips.push({t:'w',msg:'CR '+(avgCR*100).toFixed(1)+'% cerca de meta.'});else tips.push({t:'o',msg:'CR '+(avgCR*100).toFixed(1)+'% sobre meta.'});
    if(avgOcc<0.55)tips.push({t:'b',msg:'Occupancy '+(avgOcc*100).toFixed(0)+'% — reduce breaks no programados.'});else if(avgOcc<0.65)tips.push({t:'w',msg:'Occupancy '+(avgOcc*100).toFixed(0)+'% — meta: 65%+.'});
    if(avgCalls<80)tips.push({t:'w',msg:'Promedio '+Math.round(avgCalls)+' calls/mes — volumen bajo.'});
    const good=active.filter(m=>m.cr>=0.10).length;
    if(good/active.length>=0.8)tips.push({t:'o',msg:'Alta consistencia: '+good+'/'+active.length+' meses CR >= 10%.'});else if(good/active.length<0.4)tips.push({t:'w',msg:'Inconsistencia: '+good+'/'+active.length+' meses sobre meta.'});
    return tips.slice(0,5);
  },
  _patterns(h) {
    const pats=[],{monthly,dow}=h,vd=dow.filter(d=>d.avg_revenue>0);
    if(vd.length){const b=vd.reduce((a,c)=>c.avg_revenue>a.avg_revenue?c:a);pats.push({i:'T',t:'Mejor dia semana',m:'Los '+DOW_FULL[b.dow]+' promedian $'+Math.round(b.avg_revenue)+'/dia.',bg:'#f0fdf4',bc:'#86efac',tc:'#166534'});if(vd.length>1){const w=vd.reduce((a,c)=>c.avg_revenue<a.avg_revenue?c:a);if(w.dow!==b.dow)pats.push({i:'W',t:'Dia mas debil',m:'Los '+DOW_FULL[w.dow]+': $'+Math.round(w.avg_revenue)+'/dia.',bg:'#fef2f2',bc:'#fca5a5',tc:'#991b1b'});}}
    if(monthly.length>=2){const l=monthly[monthly.length-1],p=monthly[monthly.length-2];if(l.cr>p.cr)pats.push({i:'CR',t:'CR en alza',m:(p.cr*100).toFixed(1)+'% -> '+(l.cr*100).toFixed(1)+'%',bg:'#f0fdf4',bc:'#86efac',tc:'#166534'});if(l.asp>p.asp)pats.push({i:'$',t:'ASP subio',m:'$'+Math.round(p.asp)+' -> $'+Math.round(l.asp),bg:'#faf5ff',bc:'#ddd6fe',tc:'#5b21b6'});}
    return pats.slice(0,6);
  },
  supervisorAnalysis(allRows) {
    return Object.entries(groupBy(allRows,'agent')).map(([ag,rows])=>{ const a=aggAll(rows); return {agent:ag,...a,cr:sd(a.sales,a.calls_2m),occ:sd(a.oncall,a.staff_h)}; }).sort((a,b)=>b.revenue-a.revenue);
  },
};

// ────────────────────────────────────────────────────────────────
//  IMPORTER ENGINE — Google Sheets CSV / JSON → DataEngine
// ────────────────────────────────────────────────────────────────
const ImporterEngine = {
  // Convert any Google Sheets URL to a CSV export URL
  toExportURL(url, sheetName = '') {
    if (!url) return null;
    // Already export URL
    if (url.includes('export?format=csv')) return url;
    // Extract spreadsheet ID
    const idMatch = url.match(/\/d\/([a-zA-Z0-9_-]{25,})/);
    if (!idMatch) return null;
    const id = idMatch[1];
    // Extract GID (sheet tab id)
    const gidMatch = url.match(/gid=(\d+)/);
    const gid = gidMatch ? gidMatch[1] : '0';
    return `https://docs.google.com/spreadsheets/d/${id}/export?format=csv&gid=${gid}`;
  },

  // Load a Google Sheet tab by name (gets sheet list first)
  async fetchSheetByName(baseUrl, sheetName) {
    // Build gid from sheet list — requires fetching /pub?output=csv won't give tab list
    // So we use the export URL with the gid the user provides, or we try tab index approach
    const csvUrl = this.toExportURL(baseUrl);
    if (!csvUrl) throw new Error('URL de Google Sheets invalida');
    const resp = await fetch(csvUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} — Verifica que la hoja sea publica`);
    return resp.text();
  },

  async importOps(url, monthStr) {
    updateAdminStatus('Importando Ops: Rec_Agent Performance...', 'loading');
    try {
      const csvUrl = this.toExportURL(url);
      if (!csvUrl) throw new Error('URL invalida');
      const resp  = await fetch(csvUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const text  = await resp.text();
      const rows  = this.parseOpsCSV(text, monthStr);
      if (!rows.length) throw new Error('No se encontraron filas validas');
      DataEngine.mergeMonth(monthStr, rows, 'ops');
      // Update links config
      if (!DataEngine._linksConfig[monthStr]) DataEngine._linksConfig[monthStr] = {};
      DataEngine._linksConfig[monthStr].ops = url;
      DataEngine._linksConfig[monthStr].loaded = true;
      DataEngine._linksConfig[monthStr].updated = new Date().toISOString();
      DataEngine.saveLinksConfig();
      updateAdminStatus(`Ops cargado: ${rows.length} filas para ${MES_ES[monthStr]||monthStr}`, 'ok');
      if (monthStr === APP_STATE.currentMonth) AutoRefresh.start(monthStr, 'ops');
      update();
      return rows.length;
    } catch(e) {
      updateAdminStatus('Error importando Ops: ' + e.message, 'error');
      throw e;
    }
  },

  async importAdherencia(url, monthStr) {
    updateAdminStatus('Importando Adherencia...', 'loading');
    try {
      const csvUrl = this.toExportURL(url);
      if (!csvUrl) throw new Error('URL invalida');
      const resp = await fetch(csvUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const text = await resp.text();
      const rows = this.parseAdherenciaCSV(text, monthStr);
      DataEngine.mergeMonth(monthStr, rows, 'adherencia');
      if (!DataEngine._linksConfig[monthStr]) DataEngine._linksConfig[monthStr] = {};
      DataEngine._linksConfig[monthStr].adherencia = url;
      DataEngine.saveLinksConfig();
      updateAdminStatus(`Adherencia cargada: ${rows.length} registros`, 'ok');
      if (monthStr === APP_STATE.currentMonth) AutoRefresh.start(monthStr, 'adherencia');
      if (APP_STATE.currentView === 'adherencia') update();
      return rows.length;
    } catch(e) {
      updateAdminStatus('Error importando Adherencia: ' + e.message, 'error');
      throw e;
    }
  },

  async importCommissions(url, monthStr) {
    updateAdminStatus('Importando Comisiones (Front Comisiones)...', 'loading');
    try {
      const csvUrl = this.toExportURL(url);
      if (!csvUrl) throw new Error('URL invalida');
      const resp = await fetch(csvUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const text = await resp.text();
      const rows = this.parseCommissionsCSV(text, monthStr);
      DataEngine.mergeMonth(monthStr, rows, 'commissions');
      updateAdminStatus(`Comisiones cargadas: ${rows.length} registros`, 'ok');
      return rows.length;
    } catch(e) {
      updateAdminStatus('Error importando Comisiones: ' + e.message, 'error');
      throw e;
    }
  },

  // ── PARSERS ──
  parseOpsCSV(text, monthStr) {
    const lines = text.trim().split('\n').filter(l=>l.trim());
    if (lines.length < 2) return [];
    const headers = splitLine(lines[0]).map(h=>h.trim().replace(/"/g,'').toLowerCase());
    const MAP = {
      'agent_payment':'agent','agent name':'agent','nombre':'agent',
      'salesforce_payment_date__c':'date','datetimemx':'date',
      'final revenue_cc':'revenue','final_revenue_cc':'revenue','revenue':'revenue',
      'final cash_cc':'cash','final_cash_cc':'cash','cash':'cash',
      'final sales_cc':'sales','final_sales_cc':'sales','sales_cc':'sales',
      'refunds':'refunds',
      'call>2min':'calls_2m','call 2-5 min':'calls_25','call 5-10 min':'calls_510','call>10min':'calls_10',
      'talk time':'talk_time','talk_time':'talk_time',
      'staffhours':'staff_h','oncall':'oncall','%oncall':'occupancy',
      'sumnot ready':'not_ready','sumnotready':'not_ready',
      'acw time_cc':'acw','meal_cc':'meal_cc','training_cc':'training','break_cc':'break_t',
    };
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const vals = splitLine(lines[i]);
      if (vals.length < 3) continue;
      const raw = {};
      headers.forEach((h,idx)=>{ const v=(vals[idx]||'').replace(/"/g,'').trim(); raw[MAP[h]||h.replace(/[\s\-]/g,'_')]=(isNaN(v)||v==='')?v:Number(v); });
      if (!raw.agent || !raw.date) continue;
      const dt = new Date(raw.date);
      if (isNaN(dt)) continue;
      const ds = dt.toISOString().slice(0,10), mo = ds.slice(0,7);
      const wn = isoWeek(dt), wk = `2026-W${String(wn).padStart(2,'0')}`;
      rows.push({
        agent:String(raw.agent).trim(), supervisor:'--', date:ds, month:mo, week:wk, week_of_year:wk,
        dow:['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][dt.getDay()], year:String(dt.getFullYear()),
        revenue:+(raw.revenue||0), cash:+(raw.cash||0), sales:+(raw.sales||0), refunds:+(raw.refunds||0),
        calls_2m:+(raw.calls_2m||0), calls_25:+(raw.calls_25||0), calls_510:+(raw.calls_510||0), calls_10:+(raw.calls_10||0),
        talk_time:+(raw.talk_time||0), staff_h:+(raw.staff_h||0), oncall:+(raw.oncall||0),
        not_ready:+(raw.not_ready||0), acw:+(raw.acw||0), training:+(raw.training||0), break_t:+(raw.break_t||0),
        occupancy:+(raw.occupancy||0), cr:0, aht:0,
      });
    }
    // Compute derived fields
    rows.forEach(r => {
      r.cr  = sd(r.sales, r.calls_2m);
      r.aht = sd(r.talk_time, r.calls_2m);
      if (!r.occupancy) r.occupancy = sd(r.oncall, r.staff_h);
    });
    return rows;
  },

  parseAdherenciaCSV(text, monthStr) {
    const lines = text.trim().split('\n').filter(l=>l.trim());
    if (lines.length < 2) return [];
    const headers = splitLine(lines[0]).map(h=>h.trim().replace(/"/g,'').toLowerCase());
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const vals = splitLine(lines[i]);
      const raw = {};
      headers.forEach((h,idx)=>{ const v=(vals[idx]||'').replace(/"/g,'').trim(); raw[h.replace(/[\s\-]/g,'_')]=isNaN(v)||v===''?v:Number(v); });
      if (!raw.supervisor && !raw.agent && !raw.nombre) continue;
      rows.push({
        agent:    raw.agent || raw.nombre || raw.asesor || '--',
        supervisor: raw.supervisor || '--',
        month:    monthStr,
        horas_plan:   +(raw.horas_plan||raw.horas_planificadas||0),
        horas_reales: +(raw.horas_reales||raw.horas_trabajadas||0),
        adh_pct:      +(raw.adh_pct||raw.adherencia||raw['%adh']||0),
        llegadas_tarde:+(raw.llegadas_tarde||raw.tardanzas||0),
        ausencias:    +(raw.ausencias||0),
        oncall:       +(raw.oncall||raw.tiempo_conectado||0),
        occupancy:    +(raw.occupancy||raw.occupancy_pct||0),
        breaks:       +(raw.breaks||raw.break||0),
      });
    }
    return rows;
  },

  parseCommissionsCSV(text, monthStr) {
    const lines = text.trim().split('\n').filter(l=>l.trim());
    if (lines.length < 2) return [];
    const headers = splitLine(lines[0]).map(h=>h.trim().replace(/"/g,'').toLowerCase());
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const vals = splitLine(lines[i]);
      const raw = {};
      headers.forEach((h,idx)=>{ const v=(vals[idx]||'').replace(/"/g,'').trim(); raw[h.replace(/[\s\-]/g,'_')]=isNaN(v)||v===''?v:Number(v); });
      if (!raw.agent && !raw.asesor && !raw.nombre) continue;
      rows.push({
        agent:      raw.agent || raw.asesor || raw.nombre || '--',
        month:      monthStr,
        comision:   +(raw.comision||raw.commission||raw.total_comision||0),
        ventas:     +(raw.ventas||raw.sales||0),
        cash:       +(raw.cash||0),
        tasa:       +(raw.tasa||raw.rate||0),
        bono:       +(raw.bono||raw.bonus||0),
      });
    }
    return rows;
  },
};


// ────────────────────────────────────────────────────────────────
//  AUTO-REFRESH ENGINE — live accumulation from Google Sheets
// ────────────────────────────────────────────────────────────────
const AutoRefresh = {
  // Daily refresh window: 12:00 PM – 1:00 PM every day
  WINDOW_H_START: 12,
  WINDOW_H_END:   13,
  CHECK_MS: 5 * 60 * 1000,    // poll every 5 min to catch the window
  _timers:  {},

  start(monthStr, type) {
    const key = monthStr + '_' + type;
    if (this._timers[key]) return;
    console.log('[AR] Scheduler ON:', key);
    this._tick(monthStr, type);                                         // immediate check
    this._timers[key] = setInterval(() => this._tick(monthStr, type), this.CHECK_MS);
    _showRefreshBadge(monthStr);
  },

  stop(monthStr, type) {
    const key = monthStr + '_' + type;
    if (this._timers[key]) { clearInterval(this._timers[key]); delete this._timers[key]; }
    if (!Object.keys(this._timers).some(k => k.startsWith(monthStr))) {
      const b = $('live-refresh-badge'); if (b) b.style.display = 'none';
    }
  },

  async _tick(monthStr, type) {
    const now   = new Date();
    const h     = now.getHours();
    const today = now.toISOString().slice(0, 10);
    const key   = monthStr + '_' + type;
    // Already fetched today? Skip
    const lastTs = Store.get('ar_last_' + key);
    if (lastTs && new Date(lastTs).toISOString().slice(0, 10) === today) return;
    // Not in the noon window? Skip
    if (h < this.WINDOW_H_START || h >= this.WINDOW_H_END) return;
    await this._run(monthStr, type);
  },

  async _run(monthStr, type) {
    const key = monthStr + '_' + type;
    const cfg = DataEngine.linksConfig[monthStr] || {};
    const url = type === 'ops' ? cfg.ops : cfg.adherencia;
    if (!url) return;
    console.log('[AR] Fetching', key, new Date().toLocaleTimeString());
    _showRefreshBadge(monthStr, 'loading');
    try {
      if (type === 'ops') await ImporterEngine.importOps(url, monthStr);
      else                await ImporterEngine.importAdherencia(url, monthStr);
      Store.set('ar_last_' + key, Date.now());
      _showRefreshBadge(monthStr, 'ok');
      _checkStaleAlert();
    } catch(err) {
      console.warn('[AR] Error', key, err.message);
      _showRefreshBadge(monthStr, 'error');
    }
  },

  restoreFromConfig() {
    const cm = APP_STATE.currentMonth; if (!cm) return;
    const cfg = DataEngine.linksConfig[cm] || {};
    if (cfg.ops)        this.start(cm, 'ops');
    if (cfg.adherencia) this.start(cm, 'adherencia');
  },

  status(monthStr) {
    const fmt = (key) => {
      const t = Store.get('ar_last_' + key);
      if (!t) return '--';
      const d = new Date(t);
      return d.toLocaleDateString('es-MX',{day:'2-digit',month:'2-digit'}) + ' ' + d.toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'});
    };
    const nextWin = () => {
      const h = new Date().getHours();
      if (h < 12) return 'Hoy 12:00 PM';
      if (h < 13) return 'AHORA (ventana activa)';
      return 'Manana 12:00 PM';
    };
    return {
      ops_active: !!this._timers[monthStr + '_ops'],
      adh_active: !!this._timers[monthStr + '_adherencia'],
      ops_status: this._timers[monthStr + '_ops']  ? 'Activo — diario 12 PM' : 'Inactivo',
      adh_status: this._timers[monthStr + '_adherencia'] ? 'Activo — diario 12 PM' : 'Inactivo',
      ops_last:   fmt(monthStr + '_ops'),
      adh_last:   fmt(monthStr + '_adherencia'),
      next_window: nextWin(),
    };
  },
};

function _showRefreshBadge(monthStr, state) {
  const b = $('live-refresh-badge'); if (!b) return;
  b.style.display = 'flex';
  if (state === 'loading') {
    b.style.background='#eff6ff';b.style.color='#1d4ed8';b.style.borderColor='#bfdbfe';
    b.textContent = '↻ Actualizando...';
  } else if (state === 'error') {
    b.style.background='#fef2f2';b.style.color='#991b1b';b.style.borderColor='#fca5a5';
    b.textContent = '⚠ Error al actualizar';
    setTimeout(() => _showRefreshBadge(monthStr), 4000);
  } else {
    b.style.background='#f0fdf4';b.style.color='#166534';b.style.borderColor='#86efac';
    b.textContent = '↻ Live · ' + (MES_ES[monthStr]||monthStr);
  }
}


// ────────────────────────────────────────────────────────────────
//  STALE DATA ALERT
// ────────────────────────────────────────────────────────────────
function _getDaysSinceLastData() {
  const cm = APP_STATE.currentMonth; if (!cm) return null;
  const monthRows = DataEngine.rows.filter(r => r.month === cm);
  if (!monthRows.length) return null;
  const lastDate = monthRows.map(r => r.date).filter(Boolean).sort().pop();
  if (!lastDate) return null;
  const today    = new Date().toISOString().slice(0, 10);
  const diffDays = Math.round((new Date(today) - new Date(lastDate)) / 86400000);
  return { lastDate, diffDays };
}

function _checkStaleAlert() {
  const el = $('stale-alert'); if (!el) return;
  const cm = APP_STATE.currentMonth; if (!cm) { el.style.display='none'; return; }
  const cfg = DataEngine.linksConfig[cm] || {};
  const hasLink = cfg.ops || cfg.adherencia;
  if (!hasLink) { el.style.display='none'; return; }
  const info = _getDaysSinceLastData();
  if (!info) { el.style.display='none'; return; }
  const { lastDate, diffDays } = info;
  el.style.display = 'flex';
  el.style.alignItems = 'center';
  el.style.gap = '10px';
  el.style.padding = '8px 14px';
  el.style.borderRadius = '9px';
  el.style.fontSize = '12px';
  el.style.marginBottom = '12px';
  el.style.border = '1px solid';
  if (diffDays === 0) {
    el.style.background='#f0fdf4';el.style.borderColor='#86efac';el.style.color='#166534';
    el.innerHTML = '<span style="font-size:16px">✅</span><span>Datos <b>actualizados al dia</b> · Ultimo registro: <b>'+lastDate+'</b></span>';
  } else if (diffDays === 1) {
    el.style.background='#fffbeb';el.style.borderColor='#fde68a';el.style.color='#854d0e';
    el.innerHTML = '<span style="font-size:16px">⚠️</span><span>Ultimo registro: <b>'+lastDate+'</b> · <b>1 dia sin actualizar</b> · Proximo refresh hoy 12 PM</span>';
  } else {
    el.style.background='#fef2f2';el.style.borderColor='#fca5a5';el.style.color='#991b1b';
    el.innerHTML = '<span style="font-size:16px">🔴</span><span>Ultimo registro: <b>'+lastDate+'</b> · <b>'+diffDays+' dias sin datos nuevos</b> · Verifica el link en ⚙ Admin</span>';
  }
}

// ────────────────────────────────────────────────────────────────
//  QUERY LAYER
// ────────────────────────────────────────────────────────────────
const Q = {
  agents() {
    if (APP_STATE.viewMode === 'supervisor') return DataEngine.supervisors[APP_STATE.currentSupervisor] || [];
    return APP_STATE.currentAgent ? [APP_STATE.currentAgent] : [];
  },
  _period(r) {
    const mo=APP_STATE.currentMonth, wk=APP_STATE.currentWeek;
    switch(APP_STATE.currentPeriod) {
      case 'month': return r.month===mo;
      case 'week':  return true;
      case 'day':   return r.month===mo && (r.week_of_year||r.week)===wk;
      case 'dow':   return r.month===mo;
      default:      return true;
    }
  },
  rows()      { const ag=this.agents(); return ag.length ? DataEngine.rows.filter(r=>ag.includes(r.agent)&&this._period(r)) : []; },
  allRows()   { const ag=this.agents(); return ag.length ? DataEngine.rows.filter(r=>ag.includes(r.agent)) : []; },
  erRows()    { const ag=this.agents(); return ag.length ? DataEngine.erRows.filter(r=>ag.includes(r.agent)&&this._period(r)) : []; },
  allERRows() { const ag=this.agents(); return DataEngine.erRows.filter(r=>ag.includes(r.agent)); },
};

// ────────────────────────────────────────────────────────────────
//  MATH UTILS
// ────────────────────────────────────────────────────────────────
const sd = (a,b) => (b&&isFinite(b)&&b!==0) ? a/b : 0;
const agg = (rows,k) => rows.reduce((s,r)=>s+(+r[k]||0), 0);
const AGG_FIELDS = ['revenue','cash','sales','refunds','calls_2m','calls_25','calls_510','calls_10','talk_time','staff_h','oncall','not_ready','acw','training','break_t'];
function aggAll(rows) { const o={}; AGG_FIELDS.forEach(k=>{o[k]=rows.reduce((s,r)=>s+(+r[k]||0),0);}); return o; }
function groupBy(rows,k) { const m={}; rows.forEach(r=>{const key=(typeof k==='function'?k(r):r[k])||'-'; if(!m[key])m[key]=[]; m[key].push(r);}); return m; }
function isoWeek(d) { const t=new Date(d); t.setHours(0,0,0,0); t.setDate(t.getDate()+4-(t.getDay()||7)); return Math.ceil((((t-new Date(t.getFullYear(),0,1))/86400000)+1)/7); }
function splitLine(line) { const r=[]; let c='',q=false; for(const ch of line){if(ch==='"')q=!q;else if(ch===','&&!q){r.push(c);c='';}else c+=ch;} r.push(c); return r; }

// ────────────────────────────────────────────────────────────────
//  CHART ENGINE
// ────────────────────────────────────────────────────────────────
const CH = {};
const $ = id => document.getElementById(id);
function dchart(id) { if(CH[id]){try{CH[id].destroy()}catch(e){}delete CH[id];} }

function CD() {
  return { responsive:true,maintainAspectRatio:false,animation:{duration:300},
    plugins:{ legend:{display:false}, tooltip:{backgroundColor:'#1e293b',borderColor:'#334155',borderWidth:1,titleColor:'#f1f5f9',bodyColor:'#94a3b8',padding:10,cornerRadius:8} },
    scales:{ x:{grid:{color:'rgba(226,232,240,.6)',drawBorder:false},ticks:{color:'#94a3b8',font:{size:10},maxRotation:45},border:{display:false}}, y:{grid:{color:'rgba(226,232,240,.6)',drawBorder:false},ticks:{color:'#94a3b8',font:{size:10}},border:{display:false}} } };
}
const DL = { id:'avr_dl', afterDatasetsDraw(chart){ chart.data.datasets.forEach((ds,di)=>{ if(!ds.showLabels)return; const meta=chart.getDatasetMeta(di),ctx=chart.ctx; meta.data.forEach((el,i)=>{ const val=ds.data[i]; if(!val&&val!==0)return; const pos=el.tooltipPosition?el.tooltipPosition():{x:el.x,y:el.y}; ctx.save();ctx.fillStyle='#475569';ctx.font='bold 9px Space Grotesk';ctx.textAlign='center';ctx.textBaseline='bottom'; const lbl=typeof val==='number'?(val>=1000?'$'+Math.round(val/1000)+'k':val<1&&val>0?val.toFixed(2):''+Math.round(val)):String(val); ctx.fillText(lbl,pos.x,pos.y-3);ctx.restore(); }); }); } };
if(typeof Chart!=='undefined') Chart.register(DL);

function mkLine(id,lbl,ds,yCb,leg){ dchart(id);const el=$(id);if(!el)return;const o=CD();if(yCb)o.scales.y.ticks.callback=yCb;if(leg)o.plugins.legend={display:true,labels:{color:'#64748b',font:{size:10},boxWidth:10,padding:8}};CH[id]=new Chart(el,{type:'line',data:{labels:lbl,datasets:ds},options:o}); }
function mkBar(id,lbl,data,color,yCb,horiz){ dchart(id);const el=$(id);if(!el)return;const o=CD();if(horiz)o.indexAxis='y';if(yCb)(horiz?o.scales.x:o.scales.y).ticks.callback=yCb;CH[id]=new Chart(el,{type:'bar',data:{labels:lbl,datasets:[{data,backgroundColor:color+'33',borderColor:color,borderWidth:1.5,borderRadius:4,showLabels:true}]},options:o}); }
function mkStack(id,lbl,ds){ dchart(id);const el=$(id);if(!el)return;const o=CD();o.scales.x.stacked=true;o.scales.y.stacked=true;o.plugins.legend={display:true,labels:{color:'#64748b',font:{size:10},boxWidth:10,padding:8}};CH[id]=new Chart(el,{type:'bar',data:{labels:lbl,datasets:ds},options:o}); }
function mkDonut(id,lbl,vals,colors){ dchart(id);const el=$(id);if(!el)return;CH[id]=new Chart(el,{type:'doughnut',data:{labels:lbl,datasets:[{data:vals,backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'55%',animation:{duration:300},plugins:{legend:{display:true,position:'right',labels:{color:'#64748b',font:{size:10},boxWidth:10,padding:6}},tooltip:{backgroundColor:'#1e293b',borderColor:'#334155',borderWidth:1,titleColor:'#f1f5f9',bodyColor:'#94a3b8'}}}}); }
function mkDual(id,lbl,bDs,lDs,yCb){ dchart(id);const el=$(id);if(!el)return;const o=CD();if(yCb)o.scales.y.ticks.callback=yCb;o.plugins.legend={display:true,labels:{color:'#64748b',font:{size:10},boxWidth:10,padding:8}};o.scales.y1={position:'right',grid:{display:false},border:{display:false},ticks:{color:'#7c3aed',font:{size:10}}};CH[id]=new Chart(el,{type:'bar',data:{labels:lbl,datasets:[Object.assign({type:'bar',yAxisID:'y',borderRadius:4},bDs),Object.assign({type:'line',yAxisID:'y1',pointRadius:4,tension:.3},lDs)]},options:o}); }

// ────────────────────────────────────────────────────────────────
//  SERIES BUILDER
// ────────────────────────────────────────────────────────────────
const Series = {
  get(rows,k){ switch(APP_STATE.currentPeriod){ case'year':return this._byM(rows,k); case'week':return this._byW(rows,k); case'dow':return this._byDOW(rows,k); default:return this._byD(rows,k); } },
  calc(rows,kA,kB){ const a=this.get(rows,kA),b=this.get(rows,kB); return{labels:a.labels,data:a.data.map((v,i)=>sd(v,b.data[i]))}; },
  _byM(rows,k){ const bM=groupBy(rows,'month'),ms=DataEngine.months.filter(m=>bM[m]); return{labels:ms.map(m=>MES_ES[m]||m),data:ms.map(m=>agg(bM[m],k))}; },
  _byW(rows,k){ const ws=[...new Set(rows.map(r=>r.week_of_year||r.week).filter(Boolean))].sort(); return{labels:ws.map(w=>'S'+w.replace('2026-W','')),data:ws.map(w=>agg(rows.filter(r=>(r.week_of_year||r.week)===w),k))}; },
  _byDOW(rows,k){ const bD=groupBy(rows,'dow'); return{labels:DOW_ES,data:DOW_EN.map(d=>agg(bD[d]||[],k))}; },
  _byD(rows,k){ const bD=groupBy(rows,'date'),ds=Object.keys(bD).sort(); return{labels:ds.map(d=>d.slice(5)),data:ds.map(d=>agg(bD[d],k))}; },
};

// ────────────────────────────────────────────────────────────────
//  FORMATTERS
// ────────────────────────────────────────────────────────────────
const F = {
  usd : v => '$'+Math.round(v||0).toLocaleString('en-US'),
  pct : v => v!=null&&isFinite(v)?(v*100).toFixed(1)+'%':'--',
  num : v => Math.round(v||0).toLocaleString('en-US'),
  dec : (v,n=1) => v!=null&&isFinite(v)?Number(v).toFixed(n):'--',
  h   : v => v!=null&&isFinite(v)?Number(v).toFixed(1)+'h':'--',
  mmss: s => { const m=Math.floor((s||0)/60); return m+'m '+Math.round((s||0)%60)+'s'; },
};
const crC  = v => v>=.10?'#16a34a':v>=.07?'#d97706':v>0?'#dc2626':'#94a3b8';
const occC = v => v>=.75?'#16a34a':v>=.60?'#d97706':'#dc2626';
const scC  = v => v>=.70?'#16a34a':v>=.40?'#d97706':'#dc2626';

function kpis(id,items){ const el=$(id);if(!el)return;el.innerHTML=items.map(k=>{const tr=k.trend!=null?'<div class="kt '+(k.trend>=0?'tup':'tdn')+'">'+(k.trend>=0?'▲':'▼')+' '+Math.abs(k.trend).toFixed(1)+'%</div>':'';return '<div class="kpi" style="--kc:'+k.c+'"><div class="kl">'+k.l+'</div><div class="kv">'+k.v+'</div><div class="ks">'+(k.s||'')+'</div>'+tr+'</div>';}).join('');}
function renderDOW(cid,rows,key,fmtFn){ const el=$(cid);if(!el)return;const bD=groupBy(rows,'dow'),vals=DOW_EN.map(d=>({total:agg(bD[d]||[],key),count:(bD[d]||[]).length})),tots=vals.map(v=>v.total),maxV=Math.max(...tots,1);const best=tots.indexOf(Math.max(...tots)),nz=tots.filter(v=>v>0),worst=nz.length>1?tots.indexOf(Math.min(...nz)):-1;el.innerHTML=DOW_EN.map((d,i)=>{const v=vals[i],iB=i===best&&v.total>0,iW=i===worst&&v.total>0;return '<div class="dc '+(iB?'dbest':iW?'dworst':'')+'" style="opacity:'+(0.4+v.total/maxV*0.6)+'"><div class="dn">'+DOW_ES[i]+(iB?' T':iW?' W':'')+'</div><div class="dv">'+(v.total>0?fmtFn(v.total):'--')+'</div><div class="ds">'+v.count+' dias</div></div>';}).join('');}
function pLbl(){ const m=APP_STATE.currentMonth,w=APP_STATE.currentWeek; switch(APP_STATE.currentPeriod){case'month':return MES_ES[m]||m||'--';case'week':return 'Todas las semanas 2026';case'day':return 'Dia S'+(w||'').replace('2026-W','');case'dow':return 'Dia Semana';default:return '2026';} }

// ────────────────────────────────────────────────────────────────
//  HERO CARD
// ────────────────────────────────────────────────────────────────
function updateHero(rows){
  let name,metaStr,initials;
  if(APP_STATE.viewMode==='supervisor'){const sup=APP_STATE.currentSupervisor||'';name=sup;initials=sup.split(' ').map(p=>p[0]).slice(0,2).join('').toUpperCase();metaStr=(DataEngine.supervisors[sup]||[]).length+' agentes · Recurrence · '+pLbl();}
  else{const ag=APP_STATE.currentAgent||'';const mm=DataEngine.agents[ag]||{};name=ag;initials=ag.split(' ').map(p=>p[0]).slice(0,2).join('').toUpperCase();const fi=mm.fecha_ingreso?'Ingreso: '+mm.fecha_ingreso:'';const ant=mm.meses!=null?mm.meses+'m':'';const d=mm.dias!=null?'('+mm.dias+' dias)':'';metaStr=[(mm.supervisor||'--'),(mm.team||'--'),'Turno '+(mm.turno||'--'),fi,'Antiguedad: '+ant+' '+d,pLbl()].filter(Boolean).join(' · ');}
  $('hero-av').textContent=initials;$('hero-nm').textContent=name;$('hero-mt').textContent=metaStr;
  const tR=agg(rows,'revenue'),tCl=agg(rows,'calls_2m'),tS=agg(rows,'sales'),tSt=agg(rows,'staff_h');
  const cr=sd(tS,tCl),asp=sd(tR,tS),sph=sd(tS,tSt),sc=(APP_STATE.viewMode==='agent')?(DataEngine.agents[APP_STATE.currentAgent||'']||{}).score:null;
  $('hero-stats').innerHTML=[{l:'Revenue',v:F.usd(tR)},{l:'CR%',v:F.pct(cr)},{l:'ASP',v:F.usd(asp)},{l:'SPH',v:F.dec(sph,3)},sc!=null?{l:'Score',v:Math.round(sc*100)+'%'}:{l:'Calls>2m',v:F.num(tCl)}].map(s=>'<div class="hs"><div class="hsv">'+s.v+'</div><div class="hsl">'+s.l+'</div></div>').join('');
}

// ────────────────────────────────────────────────────────────────
//  MASTER UPDATE
// ────────────────────────────────────────────────────────────────
function update(){
  if(!APP_STATE.dataReady){console.warn('[update] data not ready');return;}
  const rows=Q.rows(),allRows=Q.allRows();
  updateHero(rows);
  _checkStaleAlert();
  switch(APP_STATE.currentView){
    case'overview':    renderOverview(rows,allRows);    break;
    case'sales':       renderSales(rows,allRows);       break;
    case'calls':       renderCalls(rows,allRows);       break;
    case'staff':       renderStaff(rows,allRows);       break;
    case'adherencia':  renderAdherencia();              break;
    case'compare':     renderCompare(allRows);          break;
    case'er':          renderER(Q.erRows(),Q.allERRows()); break;
    case'coaching':    renderCoaching(allRows);         break;
    case'metas':       renderMetas(rows,allRows);       break;
    case'ranking':     renderRanking();                 break;
    case'admin':       renderAdmin();                   break;
  }
}

// ────────────────────────────────────────────────────────────────
//  CONTROL HANDLERS
// ────────────────────────────────────────────────────────────────
function setView(mode,btn){ APP_STATE.viewMode=mode;document.querySelectorAll('.vt').forEach(b=>b.classList.remove('active'));btn.classList.add('active');$('grp-ag').style.display=mode==='agent'?'flex':'none';$('grp-sup').style.display=mode==='supervisor'?'flex':'none';update(); }
function setPeriod(p,btn){ APP_STATE.currentPeriod=p;document.querySelectorAll('.pb').forEach(b=>b.classList.remove('active'));btn.classList.add('active');$('grp-mo').style.display=(p==='month'||p==='day')?'flex':'none';$('grp-wk').style.display=(p==='day')?'flex':'none';update(); }
function sw(tab,el){ APP_STATE.currentView=tab;document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.tab-panel').forEach(t=>t.classList.remove('active'));el.classList.add('active');$('tab-'+tab).classList.add('active');update(); }
let rankSort='revenue';
function setSortRank(f){ rankSort=f;const s=$('rank-sort');if(s)s.value=f;renderRanking(); }

// ────────────────────────────────────────────────────────────────
//  RENDERERS
// ────────────────────────────────────────────────────────────────
function renderOverview(rows,allRows){
  const tS=agg(rows,'sales'),tC=agg(rows,'cash'),tR=agg(rows,'revenue'),tCl=agg(rows,'calls_2m'),tTk=agg(rows,'talk_time'),tSt=agg(rows,'staff_h'),tOc=agg(rows,'oncall'),tRef=agg(rows,'refunds');
  const cr=sd(tS,tCl),aht=sd(tTk,tCl),asp=sd(tR,tS),sph=sd(tS,tSt),rev2mc=sd(tR,tCl),revSt=sd(tR,tSt);
  // Commission for agent (if available)
  const comm=APP_STATE.viewMode==='agent'?DataEngine.getCommission(APP_STATE.currentAgent,APP_STATE.currentMonth):null;
  kpis('kpi-ov',[
    {l:'Revenue',    v:F.usd(tR),     s:F.usd(tC)+' cash',         c:'#4f46e5'},
    {l:'Ventas',     v:F.num(tS),     s:'Refund cases: '+tRef,       c:'#16a34a'},
    {l:'Calls>2m',   v:F.num(tCl),   s:F.mmss(tTk)+' talk',        c:'#0891b2'},
    {l:'CR%',        v:F.pct(cr),    s:F.num(tS)+'/'+F.num(tCl),    c:crC(cr)},
    {l:'AHT',        v:F.mmss(aht),  s:'promedio/llamada',          c:'#d97706'},
    {l:'ASP',        v:F.usd(asp),   s:'ticket promedio',           c:'#7c3aed'},
    {l:'SPH',        v:F.dec(sph,3), s:'ventas/hora staff',         c:'#0891b2'},
    {l:'Rev/2MC',    v:F.usd(rev2mc),s:'revenue por call>2m',       c:'#16a34a'},
    {l:'Rev/Staff',  v:F.usd(revSt), s:'revenue por hora staff',    c:'#d97706'},
    comm?{l:'Comision',v:F.usd(comm.comision),s:'mes actual',       c:'#7c3aed'}:{l:'Refund Cases',v:String(tRef),s:'eventos cancelacion',c:tRef>5?'#dc2626':'#16a34a'},
  ]);
  const pb=pLbl();
  ['lbl-rv','lbl-cl','lbl-cr','lbl-sph','lbl-rpk'].forEach(id=>{const e=$(id);if(e)e.textContent=pb;});
  const rv=Series.get(rows,'revenue'),cs=Series.get(rows,'cash'),cl=Series.get(rows,'calls_2m');
  const crS=Series.calc(rows,'sales','calls_2m'),sphS=Series.calc(rows,'sales','staff_h'),aspS=Series.calc(rows,'revenue','sales');
  const r2S=Series.calc(rows,'revenue','calls_2m'),rstS=Series.calc(rows,'revenue','staff_h');
  mkLine('c-rv',rv.labels,[{data:rv.data,borderColor:'#4f46e5',backgroundColor:'rgba(79,70,229,.08)',fill:true,tension:.4,pointRadius:3,borderWidth:2,label:'Revenue'},{data:cs.data,borderColor:'#0891b2',tension:.4,pointRadius:2,borderWidth:1.5,borderDash:[4,3],label:'Cash'}],v=>'$'+Math.round(v/1000)+'k',true);
  mkBar('c-cl',cl.labels,cl.data,'#0891b2');
  mkLine('c-cr',crS.labels,[{data:crS.data.map(v=>+(v*100).toFixed(2)),borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.06)',fill:true,tension:.4,pointRadius:3,borderWidth:2,showLabels:true},{data:crS.labels.map(()=>10),borderColor:'#d97706',borderWidth:1.5,borderDash:[5,4],pointRadius:0}],v=>v+'%');
  mkDual('c-sph',sphS.labels,{label:'SPH',data:sphS.data.map(v=>+v.toFixed(3)),backgroundColor:'rgba(8,145,178,.2)',borderColor:'#0891b2',borderWidth:1.5,showLabels:true},{label:'ASP($)',data:aspS.data.map(v=>Math.round(v)),borderColor:'#7c3aed',borderWidth:2});
  mkDual('c-rpk',r2S.labels,{label:'Rev/2MC',data:r2S.data.map(v=>+v.toFixed(2)),backgroundColor:'rgba(22,163,74,.2)',borderColor:'#16a34a',borderWidth:1.5,showLabels:true},{label:'Rev/Staff',data:rstS.data.map(v=>+v.toFixed(2)),borderColor:'#d97706',borderWidth:2});
  const show=APP_STATE.currentPeriod==='month'||APP_STATE.currentPeriod==='dow'||APP_STATE.currentPeriod==='year';
  $('dow-sect').style.display=show?'block':'none';if(show)renderDOW('dow-rv',rows,'revenue',v=>F.usd(v));
}

function renderSales(rows,allRows){
  const tS=agg(rows,'sales'),tC=agg(rows,'cash'),tR=agg(rows,'revenue'),tRef=agg(rows,'refunds'),tCl=agg(rows,'calls_2m'),tSt=agg(rows,'staff_h');
  const cr=sd(tS,tCl),asp=sd(tR,tS),sph=sd(tS,tSt);
  kpis('kpi-sl',[{l:'Ventas brutas',v:F.num(tS),s:F.num(tS-tRef)+' netas',c:'#16a34a'},{l:'Revenue',v:F.usd(tR),s:F.usd(tC)+' cash',c:'#4f46e5'},{l:'ASP',v:F.usd(asp),s:'ticket promedio',c:'#7c3aed'},{l:'CR%',v:F.pct(cr),s:F.num(tS)+'/'+F.num(tCl),c:crC(cr)},{l:'SPH',v:F.dec(sph,3),s:'ventas/hora',c:'#0891b2'},{l:'Refund Cases',v:String(tRef),s:'eventos cancelacion',c:tRef>5?'#dc2626':'#16a34a'}]);
  const rv=Series.get(rows,'revenue'),cs=Series.get(rows,'cash'),sl=Series.get(rows,'sales'),rf=Series.get(rows,'refunds');
  mkLine('c-s-rv',rv.labels,[{data:rv.data,borderColor:'#4f46e5',backgroundColor:'rgba(79,70,229,.08)',fill:true,tension:.4,pointRadius:3,borderWidth:2,label:'Revenue'},{data:cs.data,borderColor:'#16a34a',tension:.4,pointRadius:2,borderWidth:1.5,borderDash:[4,3],label:'Cash'}],v=>'$'+Math.round(v/1000)+'k',true);
  mkStack('c-s-rf',sl.labels,[{label:'Ventas',data:sl.data,backgroundColor:'rgba(22,163,74,.4)',borderColor:'#16a34a',borderWidth:1.5,borderRadius:3,showLabels:true},{label:'Refund Cases',data:rf.data,backgroundColor:'rgba(220,38,38,.4)',borderColor:'#dc2626',borderWidth:1.5,borderRadius:3}]);
  const bDcr=groupBy(rows,'dow'),dowCR=DOW_EN.map(d=>{const r=bDcr[d]||[];return+(sd(agg(r,'sales'),agg(r,'calls_2m'))*100).toFixed(2);});
  const elcr=$('dow-sl-cr');if(elcr){const maxV=Math.max(...dowCR,1),best=dowCR.indexOf(Math.max(...dowCR)),nz=dowCR.filter(v=>v>0),worst=nz.length>1?dowCR.indexOf(Math.min(...nz)):-1;elcr.innerHTML=DOW_EN.map((d,i)=>{const v=dowCR[i],iB=i===best&&v>0,iW=i===worst&&v>0;return '<div class="dc '+(iB?'dbest':iW?'dworst':'')+'" style="opacity:'+(0.4+v/maxV*0.6)+'"><div class="dn">'+DOW_ES[i]+(iB?' T':iW?' W':'')+'</div><div class="dv">'+(v>0?v.toFixed(1)+'%':'--')+'</div><div class="ds">'+((bDcr[d]||[]).length)+' dias</div></div>';}).join('');}
  const bDasp=groupBy(rows,'dow'),dowASP=DOW_EN.map(d=>{const r=bDasp[d]||[];return Math.round(sd(agg(r,'revenue'),agg(r,'sales')));});
  const elasp=$('dow-sl-asp');if(elasp){const maxV=Math.max(...dowASP,1),best=dowASP.indexOf(Math.max(...dowASP)),nz=dowASP.filter(v=>v>0),worst=nz.length>1?dowASP.indexOf(Math.min(...nz)):-1;elasp.innerHTML=DOW_EN.map((d,i)=>{const v=dowASP[i],iB=i===best&&v>0,iW=i===worst&&v>0;return '<div class="dc '+(iB?'dbest':iW?'dworst':'')+'" style="opacity:'+(0.4+v/maxV*0.6)+'"><div class="dn">'+DOW_ES[i]+(iB?' T':iW?' W':'')+'</div><div class="dv">'+(v>0?'$'+v:'--')+'</div><div class="ds">'+((bDasp[d]||[]).length)+' dias</div></div>';}).join('');}
}

function renderCalls(rows,allRows){
  const c2=agg(rows,'calls_2m'),c25=agg(rows,'calls_25'),c510=agg(rows,'calls_510'),c10=agg(rows,'calls_10'),talk=agg(rows,'talk_time'),aht=sd(talk,c2);
  kpis('kpi-cl',[{l:'Calls>2min',v:F.num(c2),s:'calificadas',c:'#0891b2'},{l:'Calls 2-5m',v:F.num(c25),s:F.pct(sd(c25,c2)),c:'#3b82f6'},{l:'Calls 5-10m',v:F.num(c510),s:F.pct(sd(c510,c2)),c:'#7c3aed'},{l:'Calls>10m',v:F.num(c10),s:F.pct(sd(c10,c2)),c:'#16a34a'},{l:'Talk Time',v:F.mmss(talk),s:'total',c:'#d97706'},{l:'AHT',v:F.mmss(aht),s:'promedio/llamada',c:'#d97706'}]);
  mkStack('c-c-vol',Series.get(rows,'calls_2m').labels,[{label:'2-5m',data:Series.get(rows,'calls_25').data,backgroundColor:'rgba(59,130,246,.4)',borderColor:'#3b82f6',borderWidth:1.5,borderRadius:2,showLabels:true},{label:'5-10m',data:Series.get(rows,'calls_510').data,backgroundColor:'rgba(124,58,237,.4)',borderColor:'#7c3aed',borderWidth:1.5,borderRadius:2},{label:'>10m',data:Series.get(rows,'calls_10').data,backgroundColor:'rgba(22,163,74,.4)',borderColor:'#16a34a',borderWidth:1.5,borderRadius:2}]);
  const ahtS=Series.calc(rows,'talk_time','calls_2m');mkLine('c-c-aht',ahtS.labels,[{data:ahtS.data.map(v=>+v.toFixed(0)),borderColor:'#d97706',backgroundColor:'rgba(217,119,6,.08)',fill:true,tension:.4,pointRadius:3,borderWidth:2,showLabels:true}],v=>v+'s');
  mkDonut('c-c-mix',['2-5min','5-10min','>10min'],[Math.max(0,c25),Math.max(0,c510),c10],['rgba(59,130,246,.8)','rgba(124,58,237,.8)','rgba(22,163,74,.8)']);
  renderDOW('dow-cl',rows,'calls_2m',v=>F.num(v));
}

function renderStaff(rows,allRows){
  const sh=agg(rows,'staff_h'),oc=agg(rows,'oncall'),nr=agg(rows,'not_ready'),acw=agg(rows,'acw'),tr=agg(rows,'training'),br=agg(rows,'break_t'),occ=sd(oc,sh);
  kpis('kpi-st',[{l:'Staff Hours',v:F.h(sh),s:'total',c:'#7c3aed'},{l:'OnCall Hrs',v:F.h(oc),s:F.pct(occ)+' del tiempo',c:'#0891b2'},{l:'Occupancy',v:F.pct(occ),s:'meta: 60%+',c:occC(occ)},{l:'Not Ready',v:F.h(nr),s:F.pct(sd(nr,sh))+' tiempo',c:'#dc2626'},{l:'ACW',v:F.h(acw),s:'after call work',c:'#d97706'},{l:'Training',v:F.h(tr),s:'+ Break: '+F.h(br),c:'#3b82f6'}]);
  const shS=Series.get(rows,'staff_h'),ocS=Series.get(rows,'oncall'),ocP=Series.calc(rows,'oncall','staff_h');
  mkLine('c-st-h',shS.labels,[{data:shS.data,borderColor:'#7c3aed',backgroundColor:'rgba(124,58,237,.08)',fill:true,tension:.4,pointRadius:3,borderWidth:2,label:'Staff H'},{data:ocS.data,borderColor:'#0891b2',tension:.4,pointRadius:2,borderWidth:1.5,label:'OnCall H'}],null,true);
  mkDonut('c-st-d',['OnCall','Not Ready','ACW','Training','Break','Otros'],[oc,nr,acw,tr,br,Math.max(0,sh-oc-nr-acw-tr-br)],['rgba(8,145,178,.8)','rgba(220,38,38,.7)','rgba(124,58,237,.7)','rgba(22,163,74,.7)','rgba(217,119,6,.7)','rgba(148,163,184,.5)']);
  mkLine('c-st-oc',ocP.labels,[{data:ocP.data.map(v=>+(v*100).toFixed(1)),borderColor:'#7c3aed',backgroundColor:'rgba(124,58,237,.06)',fill:true,tension:.4,pointRadius:3,borderWidth:2,showLabels:true},{data:ocP.labels.map(()=>60),borderColor:'#d97706',borderWidth:1.5,borderDash:[5,4],pointRadius:0}],v=>v+'%');
}

function renderAdherencia(){
  const el=$('tab-adherencia');if(!el)return;
  const mo=APP_STATE.currentMonth;
  const moData=DataEngine.adherencia[mo];
  const agents=Q.agents();
  let agData=moData?( Array.isArray(moData)?moData.filter(r=>!agents.length||agents.includes(r.agent)):[] ):[];

  if(!agData.length){
    el.querySelector('.kpi-grid') && (el.querySelector('.kpi-grid').innerHTML='');
    const msg=el.querySelector('#adh-msg');
    if(msg)msg.innerHTML='<div style="text-align:center;padding:40px;color:var(--tx3)"><div style="font-size:32px;margin-bottom:10px">📊</div><p style="font-weight:600">No hay datos de Adherencia para '+(MES_ES[mo]||mo)+'</p><p style="font-size:12px;margin-top:6px">Carga el link de Adherencia en ⚙ Administracion</p></div>';
    return;
  }

  const totalHPlan=agData.reduce((s,r)=>s+(r.horas_plan||0),0);
  const totalHReal=agData.reduce((s,r)=>s+(r.horas_reales||0),0);
  const avgAdh=sd(totalHReal,totalHPlan);
  const avgOcc=agData.reduce((s,r)=>s+(r.occupancy||0),0)/(agData.length||1);
  const totalBreaks=agData.reduce((s,r)=>s+(r.breaks||0),0);
  const totalTardanzas=agData.reduce((s,r)=>s+(r.llegadas_tarde||0),0);

  kpis('kpi-adh',[
    {l:'Adherencia prom.',v:F.pct(avgAdh),       s:'horas reales / plan',    c:avgAdh>=.95?'#16a34a':avgAdh>=.85?'#d97706':'#dc2626'},
    {l:'Horas plan total',v:F.h(totalHPlan),      s:'periodo',               c:'#4f46e5'},
    {l:'Horas reales',    v:F.h(totalHReal),      s:'trabajadas',            c:'#0891b2'},
    {l:'Occupancy prom.', v:F.pct(avgOcc),        s:'meta: 60%+',            c:occC(avgOcc)},
    {l:'Breaks totales',  v:F.h(totalBreaks),     s:'tiempo en break',       c:'#d97706'},
    {l:'Llegadas tarde',  v:String(totalTardanzas),s:'registros',            c:totalTardanzas>5?'#dc2626':'#16a34a'},
  ]);

  // Adherencia table
  const tbody=$('adh-tbody');
  if(tbody){
    const sorted=[...agData].sort((a,b)=>(b.adh_pct||0)-(a.adh_pct||0));
    tbody.innerHTML=sorted.map((r,i)=>{
      const adhC=r.adh_pct>=0.95?'#16a34a':r.adh_pct>=0.85?'#d97706':'#dc2626';
      return '<tr><td style="font-weight:600;color:var(--ind)">'+r.agent+'</td>'
        +'<td style="color:var(--tx2)">'+r.supervisor+'</td>'
        +'<td style="font-family:var(--mono)">'+F.h(r.horas_plan)+'</td>'
        +'<td style="font-family:var(--mono)">'+F.h(r.horas_reales)+'</td>'
        +'<td style="font-family:var(--mono);font-weight:700;color:'+adhC+'">'+F.pct(r.adh_pct||sd(r.horas_reales,r.horas_plan))+'</td>'
        +'<td style="font-family:var(--mono);color:'+occC(r.occupancy||0)+'">'+F.pct(r.occupancy)+'</td>'
        +'<td style="font-family:var(--mono)">'+F.h(r.breaks)+'</td>'
        +'<td style="font-family:var(--mono);color:'+(r.llegadas_tarde>0?'#d97706':'#16a34a')+'">'+r.llegadas_tarde+'</td>'
        +'</tr>';
    }).join('');
  }

  // Adherencia bar chart
  const labels=agData.map(r=>r.agent.split(' ')[0]);
  const adhVals=agData.map(r=>+(((r.adh_pct||sd(r.horas_reales,r.horas_plan))*100).toFixed(1)));
  mkBar('c-adh-bar',labels,adhVals,'#4f46e5',v=>v+'%');
  const occVals=agData.map(r=>+((r.occupancy||0)*100).toFixed(1));
  mkBar('c-adh-occ',labels,occVals,'#0891b2',v=>v+'%');
}

function renderCompare(allRows){
  const bM=groupBy(allRows,'month'),ms=DataEngine.months.filter(m=>bM[m]),lbs=ms.map(m=>MES_ES[m]||m);
  const cashByM=ms.map(m=>agg(bM[m],'cash')),crByM=ms.map(m=>+(sd(agg(bM[m],'sales'),agg(bM[m],'calls_2m'))*100).toFixed(2));
  const aspByM=ms.map(m=>+sd(agg(bM[m],'revenue'),agg(bM[m],'sales')).toFixed(2)),sphByM=ms.map(m=>+sd(agg(bM[m],'sales'),agg(bM[m],'staff_h')).toFixed(3));
  const callsByM=ms.map(m=>agg(bM[m],'calls_2m')),occByM=ms.map(m=>+(sd(agg(bM[m],'oncall'),agg(bM[m],'staff_h'))*100).toFixed(1));
  const r2M=ms.map(m=>+sd(agg(bM[m],'revenue'),agg(bM[m],'calls_2m')).toFixed(2)),rstM=ms.map(m=>+sd(agg(bM[m],'revenue'),agg(bM[m],'staff_h')).toFixed(2));
  dchart('c-m-rv');const el=$('c-m-rv');if(el){const o=CD();o.scales.y.ticks.callback=v=>'$'+Math.round(v/1000)+'k';o.plugins.legend={display:true,labels:{color:'#64748b',font:{size:10},boxWidth:10,padding:8}};CH['c-m-rv']=new Chart(el,{type:'bar',data:{labels:lbs,datasets:[{type:'bar',label:'Cash',data:cashByM,backgroundColor:'rgba(8,145,178,.3)',borderColor:'#0891b2',borderWidth:1.5,borderRadius:4,showLabels:true},{type:'line',label:'Tendencia',data:cashByM,borderColor:'#d97706',borderWidth:2,pointRadius:4,tension:.3,backgroundColor:'transparent'}]},options:o});}
  mkLine('c-m-cr',lbs,[{data:crByM,borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.08)',fill:true,tension:.4,pointRadius:5,borderWidth:2,label:'CR%',showLabels:true},{data:lbs.map(()=>10),borderColor:'#d97706',borderWidth:1.5,borderDash:[5,4],pointRadius:0,label:'Meta 10%'}],v=>v+'%',true);
  mkBar('c-m-cl',lbs,callsByM,'#0891b2');
  mkDual('c-m-asp',lbs,{label:'SPH',data:sphByM,backgroundColor:'rgba(8,145,178,.2)',borderColor:'#0891b2',borderWidth:1.5,showLabels:true},{label:'ASP($)',data:aspByM,borderColor:'#7c3aed',borderWidth:2});
  const metrics=[{key:'sales',lbl:'Ventas',vals:ms.map(m=>agg(bM[m],'sales')),fmt:v=>F.num(v)},{key:'cash',lbl:'Cash',vals:ms.map(m=>agg(bM[m],'cash')),fmt:v=>F.usd(v)},{key:'refunds',lbl:'Refund Cases',vals:ms.map(m=>agg(bM[m],'refunds')),fmt:v=>F.num(v)},{key:'calls_2m',lbl:'Calls>2m',vals:ms.map(m=>agg(bM[m],'calls_2m')),fmt:v=>F.num(v)},{key:'calls_10',lbl:'Calls>10m',vals:ms.map(m=>agg(bM[m],'calls_10')),fmt:v=>F.num(v)},{key:'staff_h',lbl:'Staff H',vals:ms.map(m=>agg(bM[m],'staff_h')),fmt:v=>F.h(v)},{key:'__occ',lbl:'OnCall%',vals:occByM,fmt:v=>v+'%'},{key:'__asp',lbl:'ASP',vals:aspByM,fmt:v=>'$'+v},{key:'__sph',lbl:'SPH',vals:sphByM,fmt:v=>v},{key:'__r2mc',lbl:'Rev/2MC',vals:r2M,fmt:v=>'$'+v},{key:'__rst',lbl:'Rev/Staff',vals:rstM,fmt:v=>'$'+v}];
  const hd=$('cmp-h'),bd=$('cmp-b');
  if(hd)hd.innerHTML='<tr><th>Indicador</th>'+ms.map(m=>'<th>'+(MES_ES[m]||m)+'</th>').join('')+'<th>Total</th></tr>';
  if(bd)bd.innerHTML=metrics.map(({key,lbl,vals,fmt})=>{const isC=key.startsWith('__');const tot=isC?'--':fmt(vals.reduce((a,b)=>a+b,0));const cells=vals.map((v,i)=>{const p=i>0?vals[i-1]:null;const cls=(!isC&&p!=null)?(v>p?'pos':v<p?'neg':''):'';return '<td class="'+cls+'">'+fmt(v)+'</td>';});return '<tr><td style="color:var(--tx2);font-weight:500">'+lbl+'</td>'+cells.join('')+'<td style="color:var(--ind);font-weight:700">'+tot+'</td></tr>';}).join('');
}

function renderER(erRows,allERRows){
  const COLS=DataEngine.erCols,SHORT=DataEngine.erShort;
  if(!COLS.length){const el=$('kpi-er');if(el)el.innerHTML='<p style="color:var(--tx3);font-size:12px;padding:12px">No hay datos ER.</p>';return;}
  const erCalls=agg(erRows,COLS[0]),errs=COLS.slice(1).map(c=>({col:c,short:SHORT[c]||c,total:agg(erRows,c)})),totalErr=errs.reduce((s,e)=>s+e.total,0),epc=sd(totalErr,erCalls);
  kpis('kpi-er',[{l:'Calls evaluadas',v:F.num(erCalls),s:'en periodo',c:'#4f46e5'},{l:'Total errores',v:F.num(totalErr),s:'suma etapas',c:totalErr>0?'#dc2626':'#16a34a'},{l:'Errores/call',v:F.dec(epc,2),s:'promedio',c:epc>0.5?'#dc2626':'#d97706'},{l:'Compliance',v:F.pct(Math.max(0,1-epc)),s:'1 - errores/call',c:'#16a34a'}]);
  const ep=$('er-lbl');if(ep)ep.textContent=pLbl();
  const maxE=Math.max(...errs.map(e=>e.total),1);
  const bEl=$('er-bars');if(bEl)bEl.innerHTML=errs.map(e=>{const p=e.total/maxE,cls=p>0.5?'eh':p>0.2?'em':'eo',col=p>0.5?'#dc2626':p>0.2?'#d97706':'#16a34a',pct=erCalls>0?(e.total/erCalls*100).toFixed(1)+'%':'--';return '<div class="erb '+cls+'"><span class="erl">'+e.short+'</span><div class="erw"><div class="erf" style="width:'+(p*100)+'%;background:'+col+'"></div></div><span class="erc" style="color:'+col+'">'+e.total+'</span><span class="erp">'+pct+'</span></div>';}).join('');
  function erSeries(rows,key){switch(APP_STATE.currentPeriod){case'year':{const bM=groupBy(rows,'month');const ms=DataEngine.months.filter(m=>bM[m]);return{labels:ms.map(m=>MES_ES[m]||m),data:ms.map(m=>agg(bM[m],key))};}case'week':{const ws=[...new Set(rows.map(r=>r.week).filter(Boolean))].sort();return{labels:ws.map(w=>'S'+w.replace('2026-W','')),data:ws.map(w=>agg(rows.filter(r=>r.week===w),key))};}case'dow':{const bD=groupBy(rows,'dow');return{labels:DOW_ES,data:DOW_EN.map(d=>agg(bD[d]||[],key))};}default:{const bD=groupBy(rows,'date');const ds=Object.keys(bD).sort();return{labels:ds.map(d=>d.slice(5)),data:ds.map(d=>agg(bD[d],key))};}}}
  const erT=erSeries(erRows,COLS[0]),errT=erSeries(erRows,'total_errors');
  mkLine('c-er-t',erT.labels,[{data:erT.data,borderColor:'#4f46e5',backgroundColor:'rgba(79,70,229,.08)',fill:true,tension:.4,pointRadius:3,borderWidth:2,label:'Calls eval.'},{data:errT.data,borderColor:'#dc2626',tension:.4,pointRadius:2,borderWidth:1.5,label:'Errores',showLabels:true}],null,true);
  const erDg=$('dow-er');if(erDg){const bD=groupBy(erRows,'dow'),vals=DOW_EN.map(d=>({total:agg(bD[d]||[],'total_errors'),count:(bD[d]||[]).length})),tots=vals.map(v=>v.total),maxV=Math.max(...tots,1);const best=tots.indexOf(Math.max(...tots)),nz=tots.filter(v=>v>0),worst=nz.length>1?tots.indexOf(Math.min(...nz)):-1;erDg.innerHTML=DOW_EN.map((d,i)=>{const v=vals[i],iH=i===best&&v.total>0,iL=i===worst&&v.total>0;return '<div class="dc '+(iH?'dworst':iL?'dbest':'')+'" style="opacity:'+(0.4+v.total/maxV*0.6)+'"><div class="dn">'+DOW_ES[i]+(iH?' W':iL?' OK':'')+'</div><div class="dv" style="color:'+(iH?'var(--red)':iL?'var(--grn)':'var(--txt)')+'">'+( v.total>0?v.total:'--')+'</div><div class="ds">'+v.count+' dias</div></div>';}).join('');}
  mkDonut('c-er-d',errs.map(e=>e.short),errs.map(e=>e.total),['rgba(220,38,38,.8)','rgba(217,119,6,.8)','rgba(59,130,246,.8)']);
  const th=$('er-th'),tb=$('er-tb');
  if(th)th.innerHTML='<tr><th>Agente</th><th>Fecha</th>'+COLS.map(c=>'<th>'+(SHORT[c]||c)+'</th>').join('')+'<th>Total</th></tr>';
  if(tb){const srt=[...erRows].sort((a,b)=>b.total_errors-a.total_errors).slice(0,50);tb.innerHTML=srt.map(r=>'<tr><td style="font-weight:600;color:var(--ind)">'+r.agent+'</td><td style="color:var(--tx3)">'+r.date+'</td>'+COLS.map(c=>'<td class="'+(r[c]>0?'neg':'')+'">'+( r[c]>0?r[c]:'--')+'</td>').join('')+'<td style="font-weight:700;color:'+(r.total_errors>0?'#dc2626':'var(--tx3)')+'">'+r.total_errors+'</td></tr>').join('');}
}

function renderCoaching(allRows){
  const agName=APP_STATE.viewMode==='agent'?APP_STATE.currentAgent:'';
  const hist=agName?DataEngine.buildAgentHistory(agName):{monthly:[],weekly:[],daily:[],dow:DOW_EN.map(d=>({dow:d,n_days:0,avg_revenue:0,cr:0}))};
  const analysis=HistoryEngine.analyze(hist);
  $('co-ins').innerHTML=analysis.insights.map(i=>'<div class="ins i'+i.t+'">'+i.msg+'</div>').join('');
  $('co-tips').innerHTML=analysis.coaching.map(t=>'<div class="ins i'+(t.t==='b'?'b':t.t==='o'?'o':'w')+'"> '+t.msg+'</div>').join('');
  $('co-pats').innerHTML=analysis.patterns.map(p=>'<div class="pat" style="background:'+p.bg+';border-color:'+p.bc+'"><div style="font-size:16px;font-weight:700;color:'+p.tc+';margin-bottom:6px">'+p.i+'</div><div style="font-size:11px;font-weight:700;color:'+p.tc+';margin-bottom:4px">'+p.t+'</div><div style="font-size:11px;color:'+p.tc+';opacity:.85;line-height:1.5">'+p.m+'</div></div>').join('');
  const mLbls=hist.monthly.map(m=>MES_ES[m.month]||m.month);
  if(mLbls.length){mkLine('c-co-cr',mLbls,[{data:hist.monthly.map(m=>+(m.cr*100).toFixed(2)),borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.08)',fill:true,tension:.4,pointRadius:5,borderWidth:2,label:'CR%',showLabels:true},{data:mLbls.map(()=>10),borderColor:'#d97706',borderWidth:1.5,borderDash:[5,4],pointRadius:0,label:'Meta 10%'}],v=>v+'%',true);}
  mkBar('c-co-dow',DOW_EN.map(d=>DOW_FULL[d].slice(0,3)),hist.dow.map(d=>d.avg_revenue),'#4f46e5',v=>'$'+Math.round(v));
  const supWrap=$('sup-analysis-wrap');if(APP_STATE.viewMode==='supervisor'&&supWrap){supWrap.style.display='block';_renderSupAnalysis(allRows,'sup-analysis');}else if(supWrap)supWrap.style.display='none';
}

function _renderSupAnalysis(allRows,targetId){
  const el=$(targetId);if(!el)return;
  const agSt=HistoryEngine.supervisorAnalysis(allRows);
  const top=agSt[0],highCR=agSt.filter(a=>a.cr>=0.12),lowCR=agSt.filter(a=>a.cr<0.07&&a.calls_2m>10),lowOcc=agSt.filter(a=>a.occ<0.55&&a.calls_2m>10);
  let html='<div class="cg cg2"><div class="cc"><div class="ct">Lo que va bien</div>';
  if(top)html+='<div class="ins io"> Lider: <b>'+top.agent+'</b> ('+F.usd(top.revenue)+')</div>';
  if(highCR.length)html+='<div class="ins io"> CR &gt;12%: <b>'+highCR.map(a=>a.agent.split(' ')[0]).join(', ')+'</b></div>';
  html+='</div><div class="cc"><div class="ct">Oportunidades</div>';
  if(lowCR.length)html+='<div class="ins iw"> CR &lt;7%: <b>'+lowCR.map(a=>a.agent.split(' ')[0]).join(', ')+'</b></div>';
  if(lowOcc.length)html+='<div class="ins iw"> Occ &lt;55%: <b>'+lowOcc.map(a=>a.agent.split(' ')[0]).join(', ')+'</b></div>';
  if(!lowCR.length&&!lowOcc.length)html+='<div class="ins io"> Todos en parametros.</div>';
  html+='</div></div>';el.innerHTML=html;
}

// rankSort declared above

function goalKey(){return(APP_STATE.viewMode==='agent'?APP_STATE.currentAgent:APP_STATE.currentSupervisor)+'__'+($('meta-mo')?$('meta-mo').value:'');}
function loadMetas(){const g=(Store.get('goals',{})[goalKey()]||{});$('g-cash').value=g.cash||'';$('g-asp').value=g.asp||'';$('g-cr').value=g.cr||'';renderMetas(Q.rows(),Q.allRows());}
function saveMetas(){const g={cash:parseFloat($('g-cash').value)||0,asp:parseFloat($('g-asp').value)||0,cr:parseFloat($('g-cr').value)||0};const all=Store.get('goals',{});all[goalKey()]=g;Store.set('goals',all);const sv=$('meta-saved');if(sv){sv.style.display='inline';setTimeout(()=>sv.style.display='none',2000);}renderMetas(Q.rows(),Q.allRows());}
function renderMetas(rows,allRows){
  const g=(Store.get('goals',{})[goalKey()]||{});
  const mo=$('meta-mo')?$('meta-mo').value:APP_STATE.currentMonth||'2026-05';
  const moRows=allRows.filter(r=>r.month===mo);
  const daysIn=new Date(2026,parseInt(mo.split('-')[1]),0).getDate();
  const daysElapsed=Math.max(1,[...new Set(moRows.map(r=>r.date))].length);
  const totCash=agg(moRows,'cash'),totSales=agg(moRows,'sales'),totCalls=agg(moRows,'calls_2m'),totRev=agg(moRows,'revenue');
  const crActual=sd(totSales,totCalls),aspActual=sd(totRev,totSales),pace=daysElapsed>0?daysIn/daysElapsed:1,projCash=Math.round(totCash*pace);
  function progCard(lbl,actual,goal,projected,fmtFn){if(!goal)return '<div class="goal-card"><div class="goal-lbl">'+lbl+'</div><div class="goal-val" style="color:var(--tx3)">Sin meta configurada</div></div>';const pct=Math.min(100,sd(actual,goal)*100),c=pct>=100?'#16a34a':pct>=70?'#d97706':'#dc2626';return '<div class="goal-card"><div class="goal-lbl">'+lbl+'</div><div class="goal-val" style="color:'+c+'">'+fmtFn(actual)+'</div><div class="prog-wrap"><div class="prog-fill" style="width:'+pct+'%;background:'+c+'"></div></div><div style="display:flex;justify-content:space-between;font-size:10px;margin-top:4px"><span style="color:var(--tx3)">Meta: '+fmtFn(goal)+'</span><span style="font-weight:700;color:'+c+'">'+pct.toFixed(1)+'%</span></div><div style="font-size:10px;color:var(--ind);margin-top:4px">Proyeccion: '+fmtFn(projected)+'</div><div style="font-size:10px;color:var(--tx3)">Falta: '+fmtFn(Math.max(0,goal-actual))+'</div></div>';}
  const prog=$('meta-prog');if(prog)prog.innerHTML=progCard('Cash',totCash,g.cash,projCash,F.usd)+progCard('ASP',aspActual,g.asp,aspActual,F.usd)+progCard('CR%',crActual,g.cr,crActual,v=>F.pct(v));
  const proj=$('meta-proj');if(proj)proj.innerHTML=[{l:'Cash proyectado',v:F.usd(projCash),s:'vs meta '+F.usd(g.cash||0),c:projCash>=(g.cash||0)?'#16a34a':'#d97706'},{l:'Dias restantes',v:String(daysIn-daysElapsed),s:'para cierre de mes',c:'#4f46e5'},{l:'Cash/dia',v:F.usd(sd(totCash,daysElapsed)),s:'ritmo actual',c:'#0891b2'}].map(k=>'<div class="goal-card"><div class="goal-lbl">'+k.l+'</div><div class="goal-val" style="color:'+k.c+'">'+k.v+'</div><div style="font-size:10px;color:var(--tx3)">'+k.s+'</div></div>').join('');
  const supEl=$('meta-sup-analysis');if(supEl)_renderSupAnalysis(allRows,'meta-sup-analysis');
  const ag=APP_STATE.viewMode==='agent'?APP_STATE.currentAgent:APP_STATE.currentSupervisor,meta=DataEngine.agents[ag]||{};
  const pdft=$('pdf-title');if(pdft)pdft.textContent='Compromiso de Metas — '+(MES_ES[mo]||mo);
  const pdfa=$('pdf-agent-nm');if(pdfa)pdfa.textContent=ag||'--';const pdfs=$('pdf-sup-nm');if(pdfs)pdfs.textContent=meta.supervisor||'--';
}
function exportPDF(){const p=$('pdf-preview');if(p)p.style.display='block';setTimeout(()=>window.print(),300);}

function renderRanking(){
  const sortF=($('rank-sort')&&$('rank-sort').value)||rankSort;
  const supF=($('rank-sup')&&$('rank-sup').value)||'';
  let data=[...DataEngine.ranking];if(supF)data=data.filter(r=>r.supervisor===supF);
  data.sort((a,b)=>((b[sortF]||0)-(a[sortF]||0)));
  const lbl=$('rank-lbl');if(lbl)lbl.textContent='YTD 2026 · '+data.length+' asesores';
  const segSt={'VIP+':'background:#ede9fe;color:#5b21b6;border:1px solid #ddd6fe','Black+':'background:#f1f5f9;color:#334155;border:1px solid #e2e8f0','Black':'background:#f8fafc;color:#475569;border:1px solid #e2e8f0','VIP':'background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe'};
  const tenSt={'Antiguo':'background:#dcfce7;color:#166534;border:1px solid #86efac','Medio Nuevo':'background:#fef9c3;color:#854d0e;border:1px solid #fde68a','Nuevo':'background:#fee2e2;color:#991b1b;border:1px solid #fecaca'};
  const body=$('rank-body');if(!body)return;
  body.innerHTML=data.map((r,i)=>{const rank=i+1,rc=rank<=3?'r'+rank:'rn',sc=r.score!=null?Math.round(r.score*100):null,scCol=sc!=null?scC(r.score):'#94a3b8';const sst=segSt[r.segmento]||'background:var(--s2);color:var(--tx3)',tst=tenSt[r.tenure_seg]||'background:var(--s2);color:var(--tx3)';const agEsc=r.agent.replace(/"/g,'&quot;');const comm=DataEngine.getCommission(r.agent,APP_STATE.currentMonth);return '<tr><td><span class="rank-badge '+rc+'">'+rank+'</span></td><td style="font-weight:600;color:var(--ind);cursor:pointer" data-agent="'+agEsc+'" onclick="openAgent(this.dataset.agent)">'+r.agent+'</td><td style="color:var(--tx2)">'+r.supervisor+'</td><td><span class="seg-badge" style="'+sst+'">'+(r.segmento||'--')+'</span></td><td><span class="seg-badge" style="'+tst+'">'+(r.tenure_seg||'--')+' '+r.meses+'m</span></td><td style="font-family:var(--mono);font-size:10px;color:var(--tx3)">'+(r.fecha_ingreso||'--')+'</td><td style="font-family:var(--mono);font-weight:700;color:'+(rank<=3?'#4f46e5':'var(--tx2)')+'">'+F.usd(r.revenue)+'</td><td class="mono">'+F.usd(r.cash)+'</td><td class="mono">'+F.num(r.sales)+'</td><td style="font-family:var(--mono);font-weight:700;color:'+crC(r.cr)+'">'+F.pct(r.cr)+'</td><td class="mono">'+F.usd(r.asp)+'</td><td class="mono">'+F.dec(r.sph,3)+'</td><td class="mono">'+F.usd(r.rev_per_call)+'</td><td class="mono">'+F.usd(r.rev_per_staff)+'</td>'+(comm?'<td class="mono" style="color:#7c3aed;font-weight:700">'+F.usd(comm.comision)+'</td>':'<td class="mono" style="color:var(--tx3)">--</td>')+'<td style="font-family:var(--mono);font-weight:700;color:'+scCol+'">'+(sc!=null?sc+'%':'--')+'</td></tr>';}).join('');
}

function openAgent(nombre){
  APP_STATE.viewMode='agent';APP_STATE.currentAgent=nombre;
  const agSel=$('sel-ag');if(agSel)agSel.value=nombre;
  document.querySelectorAll('.vt').forEach(b=>{b.classList.remove('active');if(b.textContent.trim()==='Agente')b.classList.add('active');});
  $('grp-ag').style.display='flex';$('grp-sup').style.display='none';
  APP_STATE.currentView='overview';
  document.querySelectorAll('.tab').forEach(t=>{t.classList.remove('active');if(t.textContent.trim()==='Resumen')t.classList.add('active');});
  document.querySelectorAll('.tab-panel').forEach(t=>t.classList.remove('active'));
  const ov=$('tab-overview');if(ov)ov.classList.add('active');update();
}

// ────────────────────────────────────────────────────────────────
//  ADMIN PANEL
// ────────────────────────────────────────────────────────────────
function adminToggleLive(monthStr, type) {
  const key = monthStr+'_'+type;
  if (AutoRefresh._timers[key]) {
    AutoRefresh.stop(monthStr, type);
    updateAdminStatus('Auto-refresh pausado.','ok');
  } else {
    AutoRefresh.start(monthStr, type);
    updateAdminStatus('Auto-refresh activo para '+(MES_ES[monthStr]||monthStr)+'. Actualiza cada 4h.','ok');
  }
  renderAdmin();
}

function renderAdmin(){
  const el=$('tab-admin');if(!el)return;
  if(!APP_STATE.adminAuth){
    el.innerHTML='<div style="max-width:360px;margin:60px auto;text-align:center"><div style="font-size:36px;margin-bottom:14px">🔐</div><p style="font-size:15px;font-weight:700;color:var(--txt);margin-bottom:18px">Administracion — Acceso Restringido</p><div style="display:flex;gap:8px;justify-content:center"><input type="password" id="admin-pw" placeholder="Contrasena" style="padding:8px 14px;border:1px solid var(--bd);border-radius:8px;font-size:14px;font-family:var(--font);outline:none;width:190px" onkeydown="if(event.key===\'Enter\')adminLogin()"><button onclick="adminLogin()" class="btn-pdf" style="padding:8px 18px">Entrar</button></div><p id="admin-err" style="color:var(--red);font-size:12px;margin-top:10px;display:none">Contrasena incorrecta</p></div>';
    return;
  }
  const cfg=DataEngine.linksConfig;
  const months=['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06'];

  el.innerHTML=`
  <div class="cg cg2" style="margin-bottom:16px">
    <!-- SISTEMA -->
    <div class="cc">
      <div class="ct">Estado del sistema <span class="cbg">v${VERSION}</span></div>
      <div style="display:grid;gap:5px;margin-top:6px">
        ${[
          {l:'Filas historico',v:DataEngine.rows.length.toLocaleString()},
          {l:'Filas ER',v:DataEngine.erRows.length.toLocaleString()},
          {l:'Agentes',v:DataEngine.agentList.length},
          {l:'Meses cargados',v:DataEngine.months.join(', ')||'--'},
          {l:'Adherencia (meses)',v:Object.keys(DataEngine.adherencia).join(', ')||'ninguno'},
          {l:'Comisiones (meses)',v:Object.keys(DataEngine.commissions).join(', ')||'ninguno'},
          {l:'Storage usado',v:Store.sizeKB()+' KB'},
          ...(()=>{const cm=APP_STATE.currentMonth||'--';const st=AutoRefresh.status(cm);return[
            {l:'Live Ops ('+(MES_ES[cm]||cm)+')',v:st.ops_status},{l:'Proxima ventana',v:st.next_window},
            {l:'Ultima Ops',v:st.ops_last},
            {l:'Live Adherencia',v:st.adh_status},
            {l:'Ultima Adh.',v:st.adh_last},
          ]})(),
        ].map(s=>`<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bd);font-size:12px"><span style="color:var(--tx2)">${s.l}</span><span style="font-family:var(--mono);font-weight:600;color:var(--ind)">${s.v}</span></div>`).join('')}
        <button onclick="adminClearImported()" class="btn-sec" style="margin-top:10px;color:var(--red);border-color:var(--red);width:100%;padding:7px">Limpiar datos importados</button>
        <p style="font-size:10px;color:var(--tx3);margin-top:4px;text-align:center">Los datos base (embebidos) se mantienen</p>
      </div>
    </div>
    <!-- STATUS IMPORT -->
    <div class="cc">
      <div class="ct">Cómo importar desde Google Sheets</div>
      <div style="font-size:12px;color:var(--tx2);line-height:1.7;margin-top:6px">
        <p>1. Abre tu Google Sheet y haz clic en <b>Archivo → Compartir → Publicar en la web</b></p>
        <p>2. Selecciona la pestaña (ej: <em>QS_Sales</em>) y formato <b>CSV</b></p>
        <p>3. Copia el link generado (termina en <code>output=csv</code>)</p>
        <p>4. O puedes pegar el link de <b>edición</b> — el sistema lo convierte automáticamente</p>
        <p style="margin-top:8px;padding:8px;background:var(--s2);border-radius:7px;font-size:11px">⚡ También acepta links con <code>/export?format=csv&gid=</code> para pestañas específicas</p>
      </div>
    </div>
  </div>

  <!-- LINKS POR MES -->
  <div class="cc">
    <div class="ct">Links de Google Sheets por mes</div>
    <p style="font-size:11px;color:var(--tx3);margin-top:4px;margin-bottom:14px">Pega el link público de cada hoja. El sistema parsea CSV automáticamente y guarda el histórico.</p>
    <div id="admin-status" style="display:none;padding:10px 14px;border-radius:9px;font-size:12px;font-weight:600;margin-bottom:12px"></div>
    ${months.map(mo=>{
      const mData=cfg[mo]||{};
      const loaded=mData.loaded?'✓':'-';
      const updated=mData.updated?mData.updated.slice(0,10):'--';
      return `<div style="background:var(--s2);border:1px solid var(--bd);border-radius:10px;padding:14px;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <p style="font-size:13px;font-weight:700;color:var(--txt)">${MES_ES[mo]||mo} 2026</p>
          <span style="font-size:10px;color:${mData.loaded?'var(--grn)':'var(--tx3)'}">${loaded} actualizado: ${updated}</span>
        </div>
        <div style="display:grid;gap:8px">
          <div>
            <div class="kl" style="margin-bottom:3px">Ops: Rec_Agent Performance (QS_Sales + Staff + Calls)</div>
            <div style="display:flex;gap:6px">
              <input type="text" id="lnk-ops-${mo}" value="${mData.ops||''}" placeholder="https://docs.google.com/spreadsheets/d/..." style="flex:1;padding:6px 10px;border:1px solid var(--bd);border-radius:7px;font-size:11px;font-family:var(--font);outline:none">
              <button onclick="adminImportOps('${mo}')" class="btn-pdf" style="padding:5px 12px;font-size:11px;white-space:nowrap">↓ Cargar</button>
            </div>
          </div>
          <div>
            <div class="kl" style="margin-bottom:3px">Adherencia</div>
            <div style="display:flex;gap:6px">
              <input type="text" id="lnk-adh-${mo}" value="${mData.adherencia||''}" placeholder="https://docs.google.com/spreadsheets/d/..." style="flex:1;padding:6px 10px;border:1px solid var(--bd);border-radius:7px;font-size:11px;font-family:var(--font);outline:none">
              <button onclick="adminImportAdh('${mo}')" class="btn-pdf" style="padding:5px 12px;font-size:11px;white-space:nowrap">↓ Cargar</button>
            </div>
          </div>
          <div>
            <div class="kl" style="margin-bottom:3px">Front Comisiones (pestaña comisiones)</div>
            <div style="display:flex;gap:6px">
              <input type="text" id="lnk-com-${mo}" value="${mData.comisiones||''}" placeholder="https://docs.google.com/spreadsheets/d/...&gid=XXX" style="flex:1;padding:6px 10px;border:1px solid var(--bd);border-radius:7px;font-size:11px;font-family:var(--font);outline:none">
              <button onclick="adminImportCom('${mo}')" class="btn-pdf" style="padding:5px 12px;font-size:11px;white-space:nowrap">↓ Cargar</button>
            </div>
          </div>
        </div>
      </div>`;
    }).join('')}
    <button onclick="adminSaveLinks()" class="btn-pdf" style="width:100%;padding:10px;margin-top:4px;font-size:13px">Guardar configuracion de links</button>
    <div id="live-control-grid" style="margin-top:14px"></div>
  </div>`;
  setTimeout(_renderLiveControlGrid, 50);
}

function _renderLiveControlGrid() {
  const el = $('live-control-grid'); if (!el) return;
  const cm = APP_STATE.currentMonth || '2026-05';
  const st = AutoRefresh.status(cm);
  const mn = MES_ES[cm] || cm;
  function card(type, label, active, statusStr, lastStr) {
    return '<div style="padding:12px;background:var(--surface);border-radius:9px;border:2px solid '+(active?'var(--grn)':'var(--bd)')+';margin-bottom:8px">'
      +'<p style="font-size:12px;font-weight:700;color:var(--txt);margin-bottom:6px">'+label+' · '+mn+'</p>'
      +'<p style="font-size:11px;color:'+(active?'var(--grn)':'var(--tx3)')+';margin-bottom:2px">Estado: '+statusStr+'</p>'
      +'<p style="font-size:10px;color:var(--tx3);margin-bottom:2px">Ultima carga: '+lastStr+'</p>'
      +'<p style="font-size:10px;color:var(--ind);margin-bottom:8px">Proxima ventana: '+st.next_window+'</p>'
      +'<button onclick="adminToggleLive(\"'+cm+'\",\"'+type+'\")" class="'+(active?'btn-sec':'btn-pdf')+'" style="width:100%;padding:6px;font-size:11px">'
      +(active?'⏸ Pausar Live':'▶ Activar Live')+'</button></div>';
  }
  el.innerHTML = '<div style="background:var(--s2);border:1px solid var(--bd2);border-radius:10px;padding:14px">'
    +'<div class="ct" style="margin-bottom:8px">&#9889; Live Accumulation — Diario 12:00 PM</div>'
    +'<p style="font-size:11px;color:var(--tx2);margin-bottom:12px;line-height:1.5">'
    +'El dashboard se actualiza <b>automaticamente entre 12:00 y 1:00 PM</b> cada dia, acumulando datos sin borrar el historico.'
    +'</p>'
    +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
    +card('ops','Ops',st.ops_active,st.ops_status,st.ops_last)
    +card('adherencia','Adherencia',st.adh_active,st.adh_status,st.adh_last)
    +'</div></div>';
}


function adminLogin(){
  const pw=$('admin-pw');
  if(pw&&pw.value===ADMIN_PASS){ APP_STATE.adminAuth=true; renderAdmin(); }
  else{ const err=$('admin-err');if(err)err.style.display='block'; }
}

function adminSaveLinks(){
  const months=['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06'];
  months.forEach(mo=>{
    if(!DataEngine._linksConfig[mo]) DataEngine._linksConfig[mo]={};
    const ops=$(`lnk-ops-${mo}`);if(ops)DataEngine._linksConfig[mo].ops=ops.value;
    const adh=$(`lnk-adh-${mo}`);if(adh)DataEngine._linksConfig[mo].adherencia=adh.value;
    const com=$(`lnk-com-${mo}`);if(com)DataEngine._linksConfig[mo].comisiones=com.value;
  });
  DataEngine.saveLinksConfig();
  const _cm=APP_STATE.currentMonth||'';
  const _mc=DataEngine._linksConfig[_cm]||{};
  if(_mc.ops)        AutoRefresh.start(_cm,'ops');
  if(_mc.adherencia) AutoRefresh.start(_cm,'adherencia');
  const _active=AutoRefresh.status(_cm);
  updateAdminStatus('Links guardados. '+(_active.ops_active||_active.adh_active?'Auto-refresh activo para '+( MES_ES[_cm]||_cm)+'.':''),'ok');
}

function adminImportOps(mo){
  const inp=$(`lnk-ops-${mo}`);if(!inp||!inp.value.trim()){updateAdminStatus('Pega un link de Google Sheets primero.','error');return;}
  ImporterEngine.importOps(inp.value.trim(),mo).then(n=>{ renderAdmin(); }).catch(()=>{});
}
function adminImportAdh(mo){
  const inp=$(`lnk-adh-${mo}`);if(!inp||!inp.value.trim()){updateAdminStatus('Pega un link primero.','error');return;}
  ImporterEngine.importAdherencia(inp.value.trim(),mo).then(()=>renderAdmin()).catch(()=>{});
}
function adminImportCom(mo){
  const inp=$(`lnk-com-${mo}`);if(!inp||!inp.value.trim()){updateAdminStatus('Pega un link primero.','error');return;}
  ImporterEngine.importCommissions(inp.value.trim(),mo).then(()=>renderAdmin()).catch(()=>{});
}
function adminClearImported(){
  if(!confirm('Esto borrara los datos importados del almacenamiento. Los datos base se mantienen. Continuar?'))return;
  Store.clearImported();
  DataEngine._agents=null;DataEngine._rows=[];DataEngine._erRows=[];DataEngine._adherencia={};DataEngine._commissions={};
  DataEngine.loadAll().then(()=>{ update(); renderAdmin(); });
}
function updateAdminStatus(msg,state){
  const el=$('admin-status');if(!el)return;
  el.style.display='block';
  el.textContent=msg;
  el.style.background=state==='ok'?'#f0fdf4':state==='error'?'#fef2f2':state==='loading'?'#eff6ff':'#f1f5f9';
  el.style.color=state==='ok'?'#166534':state==='error'?'#991b1b':state==='loading'?'#1d4ed8':'#475569';
  el.style.border='1px solid '+(state==='ok'?'#86efac':state==='error'?'#fca5a5':state==='loading'?'#bfdbfe':'#e2e8f0');
}

// ────────────────────────────────────────────────────────────────
//  INIT
// ────────────────────────────────────────────────────────────────
async function init(){
  // Restore persisted state
  APP_STATE.currentAgent     = Store.get('state_agent', null);
  APP_STATE.currentSupervisor= Store.get('state_sup',   null);
  APP_STATE.currentMonth     = Store.get('state_month', null);
  APP_STATE.currentPeriod    = Store.get('state_period','month');

  await DataEngine.loadAll();

  // Default month
  if(!APP_STATE.currentMonth){
    const ms=DataEngine.months;
    APP_STATE.currentMonth=ms[ms.length-1]||'2026-05';
  }
  // Default agent
  if(!APP_STATE.currentAgent && DataEngine.agentList.length){
    APP_STATE.currentAgent = DataEngine.agentList[0];
  }

  _populateSelects();
  setInterval(()=>{ const cl=$('lclock');if(cl)cl.textContent=new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}); },1000);
  APP_STATE.dataReady=true;
  AutoRefresh.restoreFromConfig();
  update();
  setTimeout(_checkStaleAlert, 600);
}

function _populateSelects(){
  const agSel=$('sel-ag');
  if(agSel){
    agSel.innerHTML='';
    DataEngine.agentList.forEach(a=>{const o=document.createElement('option');o.value=a;o.textContent=a;agSel.appendChild(o);});
    if(APP_STATE.currentAgent)agSel.value=APP_STATE.currentAgent;
    agSel.onchange=()=>{ APP_STATE.currentAgent=agSel.value; Store.set('state_agent',agSel.value); update(); };
  }
  const supSel=$('sel-sup');
  if(supSel){
    supSel.innerHTML='';
    DataEngine.supList.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;supSel.appendChild(o);});
    supSel.onchange=()=>{ APP_STATE.currentSupervisor=supSel.value; Store.set('state_sup',supSel.value); update(); };
  }
  const rsSel=$('rank-sup');
  if(rsSel){rsSel.innerHTML='<option value="">Todos</option>';DataEngine.supList.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;rsSel.appendChild(o);});}
  const mSel=$('sel-mo');
  if(mSel){
    mSel.innerHTML='';
    DataEngine.months.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=MES_ES[m]||m;mSel.appendChild(o);});
    mSel.value=APP_STATE.currentMonth;
    mSel.onchange=()=>{ APP_STATE.currentMonth=mSel.value; Store.set('state_month',mSel.value); update(); };
  }
  const mmSel=$('meta-mo');
  if(mmSel){
    mmSel.innerHTML='';
    DataEngine.months.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=MES_ES[m]||m;mmSel.appendChild(o);});
    mmSel.value=APP_STATE.currentMonth;
    mmSel.onchange=()=>renderMetas(Q.rows(),Q.allRows());
  }
  const wSel=$('sel-wk');
  if(wSel){
    wSel.innerHTML='';
    DataEngine.weeks.forEach(w=>{const o=document.createElement('option');o.value=w;o.textContent='Semana '+w.replace('2026-W','');wSel.appendChild(o);});
    if(DataEngine.weeks.length)wSel.value=DataEngine.weeks[DataEngine.weeks.length-1];
    wSel.onchange=()=>{ APP_STATE.currentWeek=wSel.value; update(); };
    APP_STATE.currentWeek=wSel?.value||null;
    const gw=$('grp-wk');if(gw)gw.style.display='none';
  }
}

window.addEventListener('load', init);
