// ============================================================================
// Comisión Líderes · lee los esquemas del mes (pestañas «RevOps Esquemas_Comision_Lideres» y «Daniel Torres»)
// Uso: ...exec?token=...&action=comlideres            → mes en curso
//      ...exec?token=...&action=comlideres&mes=2026-10 → otro mes
// Devuelve la sección del mes de cada pestaña tal como está en el Sheet; la página la interpreta.
// ============================================================================
const COM_TABS_ = { lideres: 'RevOps Esquemas_Comision_Lideres', gerente: 'Daniel Torres' };

function comLideresWeb_(p) {
  const ss = getTargetSpreadsheet_();
  const tz = ss.getSpreadsheetTimeZone() || 'America/Bogota';
  const mes = (p && /^\d{4}-\d{2}$/.test(p.mes || '')) ? p.mes : Utilities.formatDate(new Date(), tz, 'yyyy-MM');
  const out = { ok: true, action: 'comlideres', mes: mes, generatedAt: new Date().toISOString(), meses: {}, warnings: [] };
  Object.keys(COM_TABS_).forEach(k => {
    const sh = comHoja_(ss, COM_TABS_[k]);
    if (!sh) { out.warnings.push('No encontré la pestaña «' + COM_TABS_[k] + '».'); out[k] = null; return; }
    const vals = sh.getDataRange().getValues().map(r => r.map(v => v instanceof Date ? Utilities.formatDate(v, tz, 'yyyy-MM-dd') : v));
    const fechas = [];
    vals.forEach((r, i) => { const c = r.find(v => typeof v === 'string' && /^\d{4}-\d{2}-01$/.test(v)); if (c) fechas.push({ i: i, mes: c.slice(0, 7) }); });
    out.meses[k] = fechas.map(f => f.mes);
    const j = fechas.findIndex(f => f.mes === mes);
    if (j < 0) { out.warnings.push('«' + COM_TABS_[k] + '» no tiene el esquema de ' + mes + '.'); out[k] = null; return; }
    const fin = j + 1 < fechas.length ? fechas[j + 1].i : vals.length;
    out[k] = vals.slice(fechas[j].i, fin).map(r => { r = r.slice(); while (r.length && (r[r.length - 1] === '' || r[r.length - 1] === null)) r.pop(); return r; });
  });
  return out;
}

// Busca la pestaña sin importar mayúsculas, espacios, tildes ni signos (el nombre puede venir recortado).
function comHoja_(ss, nombre) {
  const n = s => String(s).toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, '');   // sin espacios, tildes ni signos («RevOps: …» = «RevOps …»)
  const b = n(nombre);
  return ss.getSheets().find(sh => n(sh.getName()) === b) || ss.getSheets().find(sh => b.indexOf(n(sh.getName())) === 0 || n(sh.getName()).indexOf(b) === 0) || null;
}
