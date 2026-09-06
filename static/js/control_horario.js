'use strict';

const CH_API = '/api/control_horario/';
function csrfToken(){
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

async function chFetch(path, opts={}){
  const res = await fetch(CH_API + path, {
    headers: {'Content-Type':'application/json','X-CSRFToken':csrfToken(),...(opts.headers||{})},
    ...opts,
  });
  if(!res.ok){ const t = await res.text(); throw new Error(res.status+': '+t); }
  return res.json();
}

/* ── Utils ── */
function pad(n){ return String(n).padStart(2,'0'); }
function fmtDec(n){ return (Math.round(n*100)/100).toFixed(2).replace('.',','); }
function fmtHorasEtq(n){ return (n>0?'+':'')+fmtDec(n)+' h'; }
function fmtFechaCorta(iso){ const [y,m,d]=iso.split('-'); return d+'/'+m+'/'+y; }
function esc(s){ return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function todayISO(){ const d=new Date(); return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate()); }
function mesAnterior(){ const h=new Date(); const a=new Date(h.getFullYear(),h.getMonth()-1,1); return a.getFullYear()+'-'+pad(a.getMonth()+1); }
function labelMes(mk){ const [y,m]=mk.split('-'); const n=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']; return n[+m-1]+' '+y; }

function sello(estado){
  if(estado.indexOf('manualmente')!==-1) return '<span class="ch-badge amarillo">Error (manual)</span>';
  if(estado.indexOf('Error')!==-1) return '<span class="ch-badge rojo">Error de fichada</span>';
  if(estado.indexOf('sin descanso')!==-1||estado.indexOf('descontó')!==-1) return '<span class="ch-badge amarillo">Sin descanso marcado</span>';
  return '<span class="ch-badge verde">OK</span>';
}

function selloResumen(estado){
  const cls = estado==='OK'?'verde':(estado==='Faltan horas'?'rojo':'amarillo');
  return '<span class="ch-badge '+cls+'">'+esc(estado)+'</span>';
}

const DIAS_SEMANA = [{v:1,l:'Lunes'},{v:2,l:'Martes'},{v:3,l:'Miércoles'},{v:4,l:'Jueves'},{v:5,l:'Viernes'}];

function diasDropdown(nombre, campo, seleccionados, label, prefix=''){
  const count = (seleccionados||[]).length;
  const id = 'dd_'+(prefix||'')+nombre.replace(/\s/g,'_')+'_'+campo;
  const opts = DIAS_SEMANA.map(d=>{
    const chk = (seleccionados||[]).includes(d.v)?'checked':'';
    return '<label><input type="checkbox" value="'+d.v+'" '+chk+' data-campo="'+campo+'" data-prefix="'+esc(prefix)+'"> '+d.l+'</label>';
  }).join('');
  return '<details class="ch-dias-dropdown" id="'+id+'"><summary>'+esc(label)+(count?' ('+count+')':'')+'</summary><div class="ch-dias-panel">'+opts+'</div></details>';
}

function conteoDiasDropdown(nombre, campo, conteo, label, prefix=''){
  conteo = conteo||{};
  const total = DIAS_SEMANA.reduce((s,d)=>s+(Number(conteo[d.v])||0),0);
  const filas = DIAS_SEMANA.map(d=>{
    const val = Number(conteo[d.v])||0;
    return '<label style="justify-content:space-between;gap:10px"><span>'+d.l+'</span><input type="number" min="0" step="1" style="width:52px" value="'+val+'" data-campo="'+campo+'" data-dia="'+d.v+'" data-prefix="'+esc(prefix)+'"></label>';
  }).join('');
  return '<details class="ch-dias-dropdown"><summary>'+esc(label)+(total?' ('+total+')':'')+'</summary><div class="ch-dias-panel">'+filas+'</div></details>';
}

function exportCSV(filename, headers, rows){
  const csv=[headers.join(';'),...rows.map(r=>r.map(v=>{ const s=String(v??''); return /[;\"\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; }).join(';'))];
  const blob=new Blob(['\uFEFF'+csv.join('\r\n')],{type:'text/csv;charset=utf-8;'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

function emptyState(msg){ return '<div class="ch-empty"><div class="big">Sin datos</div>'+esc(msg)+'</div>'; }

/* ── Estado global ── */
let chEmpleados = [];
let chMeses = [];
let chAjustesPendientes = {}; // nombre -> {faltas,feriados,vacaciones,observacion}
let chTextoArchivo = '';

/* ── Cargar datos base ── */
async function chInit(){
  try{
    [chEmpleados, chMeses] = await Promise.all([chFetch('empleados/'), chFetch('meses/')]);
    chPoblateFilters();
    chRenderDataSummary();
  } catch(e){ console.error('Error init CH:', e); }
}

function chRenderDataSummary(){
  const el = document.getElementById('chDataSummary');
  if(!el) return;
  const cerrados = chMeses.filter(m=>m.cerrado).length;
  el.textContent = chEmpleados.length+' empleados · '+chMeses.length+' meses'+(cerrados?' · '+cerrados+' cerrados':'');
}

function chPoblateFilters(){
  const mesesOpts = chMeses.map(m=>'<option value="'+m.mes+'"'+(m.cerrado?' title="Cerrado"':'')+'>'+labelMes(m.mes)+(m.cerrado?' 🔒':'')+' </option>').join('');
  const empOpts = '<option value="">Todos</option>'+chEmpleados.map(e=>'<option value="'+esc(e.nombre)+'">'+esc(e.nombre_display)+'</option>').join('');

  ['chFiltroMesDetalle','chFiltroMesResumen'].forEach(id=>{
    const el = document.getElementById(id);
    if(el){ el.innerHTML = mesesOpts; if(chMeses.length) el.value=chMeses[chMeses.length-1].mes; }
  });
  ['chFiltroEmpDetalle','chFiltroEmpEvolucion'].forEach(id=>{
    const el = document.getElementById(id);
    if(el) el.innerHTML = empOpts;
  });
}

/* ── Navegación ── */
document.querySelectorAll('.ch-nav-btn').forEach(btn=>{
  btn.addEventListener('click', ()=>activarTabCH(btn.dataset.tab));
});

function activarTabCH(tab){
  document.querySelectorAll('.ch-nav-btn').forEach(b=>b.classList.toggle('active', b.dataset.tab===tab));
  document.querySelectorAll('.ch-tab').forEach(t=>t.classList.toggle('active', t.id==='ch-tab-'+tab));
  if(tab==='detalle') renderDetalle();
  if(tab==='resumen') renderResumen();
  if(tab==='evolucion') renderEvolucion();
  if(tab==='config') renderConfig();
}

/* ══════════════════════════════════════════
   IMPORTAR
══════════════════════════════════════════ */
const mesImportar = document.getElementById('chMesImportar');
mesImportar.value = mesAnterior();

/* Dropzone */
const dropzone = document.getElementById('chFileDrop');
const fileInput = document.getElementById('chFileInput');

dropzone.addEventListener('click', ()=>fileInput.click());
dropzone.addEventListener('dragover', e=>{e.preventDefault(); dropzone.classList.add('drag');});
dropzone.addEventListener('dragleave', ()=>dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', e=>{
  e.preventDefault(); dropzone.classList.remove('drag');
  const file = e.dataTransfer.files[0];
  if(file) leerArchivo(file);
});
fileInput.addEventListener('change', ()=>{ if(fileInput.files[0]) leerArchivo(fileInput.files[0]); });

function leerArchivo(file){
  const reader = new FileReader();
  reader.onload = e=>{
    chTextoArchivo = e.target.result;
    document.getElementById('chPasteArea').value = chTextoArchivo;
    dropzone.querySelector('.big').textContent = '✓ '+file.name;
  };
  reader.readAsText(file, 'utf-8');
}

document.getElementById('chBtnClearArea').addEventListener('click', ()=>{
  document.getElementById('chPasteArea').value = '';
  chTextoArchivo = '';
  dropzone.querySelector('.big').textContent = 'Hacé clic para elegir un archivo';
  document.getElementById('chPreviewEmpleados').innerHTML = '';
  document.getElementById('chBtnImportar').disabled = true;
});

document.getElementById('chPasteArea').addEventListener('input', function(){
  chTextoArchivo = this.value;
});

document.getElementById('chBtnPreview').addEventListener('click', async ()=>{
  const mes = mesImportar.value;
  const texto = chTextoArchivo || document.getElementById('chPasteArea').value;
  if(!mes){ alert('Elegí un mes primero.'); return; }
  if(!texto.trim()){ alert('Subí un archivo o pegá los datos primero.'); return; }
  try{
    const data = await chFetch('preview-empleados/', {method:'POST', body:JSON.stringify({mes, texto})});
    renderPreviewEmpleados(data, mes);
    document.getElementById('chBtnImportar').disabled = false;
  } catch(e){
    document.getElementById('chPreviewEmpleados').innerHTML = '<div class="ch-alert-card">'+esc(e.message)+'</div>';
  }
});

function renderPreviewEmpleados(data, mes){
  const cont = document.getElementById('chPreviewEmpleados');
  chAjustesPendientes = {};
  data.empleados.forEach(n=>{ chAjustesPendientes[n] = data.ajustes[n]||{faltas:[],feriados:[],vacaciones:{},observacion:''}; });

  let html = '<div class="ch-alert-card info" style="margin-bottom:16px">Se encontraron <strong>'+data.total_marcas+'</strong> marcas para <strong>'+data.empleados.length+'</strong> empleados en '+labelMes(mes)+'. Configurá los ajustes y luego hacé clic en "Importar datos".</div>';

  data.empleados.forEach(nombre=>{
    const aj = chAjustesPendientes[nombre];
    html += '<div class="ch-emp-ajuste" data-nombre="'+esc(nombre)+'">';
    html += '<div class="emp-nombre">'+esc(nombre)+'</div>';
    html += '<div class="ajuste-row">';
    html += diasDropdown(nombre, 'feriados', aj.feriados, 'Feriados no trabajados', 'imp_');
    html += diasDropdown(nombre, 'faltas', aj.faltas, 'Faltas justificadas', 'imp_');
    html += conteoDiasDropdown(nombre, 'vacaciones', aj.vacaciones, 'Vacaciones', 'imp_');
    html += '</div>';
    html += '<textarea class="ch-obs-input" placeholder="Observaciones (opcional)..." data-nombre="'+esc(nombre)+'" data-campo="observacion">'+esc(aj.observacion||'')+'</textarea>';
    html += '</div>';
  });
  cont.innerHTML = html;

  // Wire checkboxes
  cont.querySelectorAll('input[type=checkbox][data-campo]').forEach(chk=>{
    chk.addEventListener('change', ()=>{
      const emp = chk.closest('.ch-emp-ajuste').dataset.nombre;
      const campo = chk.dataset.campo;
      const dd = chk.closest('.ch-dias-dropdown');
      const seleccionados = Array.from(dd.querySelectorAll('input:checked')).map(c=>Number(c.value));
      chAjustesPendientes[emp][campo] = seleccionados;
      dd.querySelector('summary').textContent = (campo==='feriados'?'Feriados no trabajados':'Faltas justificadas')+(seleccionados.length?' ('+seleccionados.length+')':'');
    });
  });
  cont.querySelectorAll('input[type=number][data-campo=vacaciones]').forEach(inp=>{
    inp.addEventListener('input', ()=>{
      const emp = inp.closest('.ch-emp-ajuste').dataset.nombre;
      const dia = inp.dataset.dia;
      if(!chAjustesPendientes[emp].vacaciones) chAjustesPendientes[emp].vacaciones={};
      chAjustesPendientes[emp].vacaciones[dia] = Number(inp.value)||0;
      const dd = inp.closest('.ch-dias-dropdown');
      const total = Object.values(chAjustesPendientes[emp].vacaciones).reduce((s,v)=>s+Number(v),0);
      dd.querySelector('summary').textContent = 'Vacaciones'+(total?' ('+total+')':'');
    });
  });
  cont.querySelectorAll('textarea.ch-obs-input').forEach(ta=>{
    ta.addEventListener('input', ()=>{
      const emp = ta.dataset.nombre;
      chAjustesPendientes[emp].observacion = ta.value;
    });
  });
}

document.getElementById('chBtnImportar').addEventListener('click', async ()=>{
  const mes = mesImportar.value;
  const texto = chTextoArchivo || document.getElementById('chPasteArea').value;
  if(!mes||!texto.trim()){ alert('Falta el mes o los datos.'); return; }
  const btn = document.getElementById('chBtnImportar');
  btn.disabled = true; btn.textContent = 'Importando...';
  try{
    const data = await chFetch('importar/', {method:'POST', body:JSON.stringify({mes, texto, ajustes:chAjustesPendientes})});
    document.getElementById('chImportReport').innerHTML = '<div class="ch-alert-card ok">✓ Importación completa — <strong>'+data.nuevas+'</strong> marcas nuevas, <strong>'+data.duplicadas+'</strong> ya existían.</div>';
    // Refresh
    [chEmpleados, chMeses] = await Promise.all([chFetch('empleados/'), chFetch('meses/')]);
    chPoblateFilters();
    chRenderDataSummary();
  } catch(e){
    document.getElementById('chImportReport').innerHTML = '<div class="ch-alert-card">Error: '+esc(e.message)+'</div>';
  } finally{
    btn.disabled = false; btn.textContent = '⤓ Importar datos';
  }
});

/* ══════════════════════════════════════════
   DETALLE DIARIO
══════════════════════════════════════════ */
document.getElementById('chFiltroMesDetalle').addEventListener('change', renderDetalle);
document.getElementById('chFiltroEmpDetalle').addEventListener('change', renderDetalle);
document.getElementById('chBtnExportDetalle').addEventListener('click', exportarDetalle);

async function renderDetalle(){
  const cont = document.getElementById('chDetalleContainer');
  const mes = document.getElementById('chFiltroMesDetalle').value;
  const emp = document.getElementById('chFiltroEmpDetalle').value;
  cont.innerHTML = '<p class="ch-hint">Cargando...</p>';
  try{
    let url = 'detalle/?';
    if(mes) url+='mes='+mes+'&';
    if(emp) url+='empleado='+encodeURIComponent(emp);
    const rows = await chFetch(url);
    if(!rows.length){ cont.innerHTML = emptyState('No hay fichadas para este filtro.'); return; }
    let html = '<div class="ch-tbl-wrap"><table><thead><tr><th>Empleado</th><th>Fecha</th><th style="text-align:right">Marca 1</th><th style="text-align:right">Marca 2</th><th style="text-align:right">Marca 3</th><th style="text-align:right">Marca 4</th><th style="text-align:right">Horas (bruto)</th><th>Estado</th><th style="text-align:right">A liquidar</th></tr></thead><tbody>';
    rows.forEach(r=>{
      html+='<tr><td class="nombre-cell">'+esc(r.nombre)+'</td><td>'+fmtFechaCorta(r.fecha)+'</td>'
        +'<td style="text-align:right">'+(r.h1||'—')+'</td><td style="text-align:right">'+(r.h2||'—')+'</td><td style="text-align:right">'+(r.h3||'—')+'</td><td style="text-align:right">'+(r.h4||'—')+'</td>'
        +'<td style="text-align:right">'+(r.horas!==null?fmtDec(r.horas)+' h':'—')+'</td>'
        +'<td>'+sello(r.estado)+'</td>'
        +'<td style="text-align:right;font-weight:700">'+fmtDec(r.a_liquidar)+' h</td></tr>';
    });
    html+='</tbody></table></div>';
    cont.innerHTML = html;
  } catch(e){ cont.innerHTML = '<div class="ch-alert-card">Error: '+esc(e.message)+'</div>'; }
}

function exportarDetalle(){
  const cont = document.getElementById('chDetalleContainer');
  const rows = cont.querySelectorAll('tbody tr');
  if(!rows.length) return;
  const headers = ['Empleado','Fecha','Marca 1','Marca 2','Marca 3','Marca 4','Horas bruto','Estado','A liquidar'];
  const data = Array.from(rows).map(r=>Array.from(r.querySelectorAll('td')).map(td=>td.textContent.trim()));
  exportCSV('detalle_horario.csv', headers, data);
}

/* ══════════════════════════════════════════
   RESUMEN MENSUAL
══════════════════════════════════════════ */
document.getElementById('chFiltroMesResumen').addEventListener('change', renderResumen);
document.getElementById('chBtnExportResumen').addEventListener('click', exportarResumen);

let resumenData = null;

async function renderResumen(){
  const cont = document.getElementById('chResumenContainer');
  const mes = document.getElementById('chFiltroMesResumen').value;
  if(!mes){ cont.innerHTML = emptyState('Elegí un mes.'); return; }
  cont.innerHTML = '<p class="ch-hint">Cargando...</p>';
  try{
    const data = await chFetch('resumen/?mes='+mes);
    resumenData = data;
    if(data.cerrado){
      renderResumenSnapshot(data);
    } else {
      renderResumenVivo(data, mes);
    }
  } catch(e){ cont.innerHTML = '<div class="ch-alert-card">Error: '+esc(e.message)+'</div>'; }
}

function renderResumenSnapshot(data){
  const cont = document.getElementById('chResumenContainer');
  let html = '<div class="ch-alert-card ok" style="margin-bottom:16px">Este mes está cerrado ('+new Date(data.cerrado_el).toLocaleDateString('es-AR')+'). Los datos son del snapshot.</div>';
  html += '<div class="ch-tbl-wrap"><table><thead><tr><th>Empleado</th><th class="num">Total horas</th><th class="num">Esperadas</th><th class="num">Diferencia</th></tr></thead><tbody>';
  for(const [nombre, snap] of Object.entries(data.snapshot)){
    const dif = snap.diferencia||0;
    const color = dif<-0.01?'var(--error)':(dif>0.01?'var(--good)':'');
    html+='<tr><td class="nombre-cell">'+esc(nombre)+'</td><td style="font-family:var(--font-mono);text-align:right">'+(snap.total?fmtDec(snap.total)+' h':'—')+'</td><td style="font-family:var(--font-mono);text-align:right">'+(snap.esperadas?fmtDec(snap.esperadas)+' h':'—')+'</td><td style="font-family:var(--font-mono);text-align:right;font-weight:700;color:'+color+'">'+fmtHorasEtq(dif)+'</td></tr>';
  }
  html+='</tbody></table></div>';
  cont.innerHTML = html;
}

function renderResumenVivo(data, mes){
  const cont = document.getElementById('chResumenContainer');
  const total = data.total_general;
  const ok = data.resumenes.filter(r=>r.estado==='OK').length;
  const faltan = data.resumenes.filter(r=>r.estado==='Faltan horas').length;
  const errores = data.resumenes.reduce((s,r)=>s+r.dias_con_error,0);

  let html = '<div class="ch-grid-cards">'
    +'<div class="ch-card"><div class="label">Total horas</div><div class="value">'+fmtDec(total)+' h</div></div>'
    +'<div class="ch-card"><div class="label">Empleados OK</div><div class="value">'+ok+'</div></div>'
    +'<div class="ch-card"><div class="label">Con horas faltantes</div><div class="value">'+faltan+'</div></div>'
    +'<div class="ch-card"><div class="label">Días con error</div><div class="value">'+errores+'</div></div>'
    +'</div>';

  html += '<div class="ch-tbl-wrap"><table><thead><tr>'
    +'<th>Empleado</th>'
    +'<th title="Feriados no trabajados">Feriados</th>'
    +'<th title="Faltas justificadas">Faltas</th>'
    +'<th title="Vacaciones">Vac.</th>'
    +'<th class="num">Total h.</th><th class="num">Esperadas</th>'
    +'<th class="num">Días err.</th>'
    +'<th class="num">Diferencia</th><th>Estado</th>'
    +'</tr></thead><tbody>';

  data.resumenes.forEach(r=>{
    const dif = r.diferencia;
    const color = dif<-0.01?'var(--error)':(dif>0.01?'var(--good)':'');
    let difCell = '<span style="font-weight:700;color:'+color+'">'+fmtHorasEtq(dif)+'</span>';
    if(r.bono_compensado>0) difCell+='<div style="font-size:10.5px;color:var(--gray600)">Bono: -'+fmtDec(r.bono_compensado)+' de '+fmtDec(r.bono_extra)+' h</div>';

    const ferDisplay = (r.feriados||[]).length?DIAS_SEMANA.filter(d=>(r.feriados).includes(d.v)).map(d=>d.l.slice(0,3)).join(', '):'—';
    const faltDisplay = (r.faltas||[]).length?DIAS_SEMANA.filter(d=>(r.faltas).includes(d.v)).map(d=>d.l.slice(0,3)).join(', '):'—';
    const vacTotal = r.vacaciones?Object.values(r.vacaciones).reduce((s,v)=>s+Number(v),0):0;

    html+='<tr>'
      +'<td class="nombre-cell">'+esc(r.nombre)+'</td>'
      +'<td style="font-size:12px">'+esc(ferDisplay)+'</td>'
      +'<td style="font-size:12px">'+esc(faltDisplay)+'</td>'
      +'<td style="text-align:center">'+vacTotal+'</td>'
      +'<td style="font-family:var(--font-mono);text-align:right">'+fmtDec(r.total_horas_mes)+' h</td>'
      +'<td style="font-family:var(--font-mono);text-align:right">'+fmtDec(r.horas_esperadas)+' h</td>'
      +'<td style="text-align:center">'+r.dias_con_error+'</td>'
      +'<td style="text-align:right">'+difCell+'</td>'
      +'<td>'+selloResumen(r.estado)+'</td>'
      +'</tr>';
    if(r.observacion) html+='<tr><td colspan="9" style="font-size:12px;color:var(--gray600);padding-left:20px;font-style:italic">📝 '+esc(r.observacion)+'</td></tr>';
  });
  html+='</tbody></table></div>';

  // Advertencias
  const conAdv = data.resumenes.filter(r=>r.advertencia&&r.advertencia.length>0);
  if(conAdv.length){
    html+='<div style="margin-top:24px;padding-top:18px;border-top:1px solid var(--gray100)"><h2 style="color:var(--error);font-size:1.05rem;margin-bottom:14px">⚠ Advertencias</h2>';
    conAdv.forEach(r=>{
      html+='<div class="ch-alert-card"><strong>'+esc(r.nombre)+'</strong> — tiene menos días que el resto del equipo. Días faltantes: '+r.advertencia.map(d=>'<span style="font-family:var(--font-mono);font-size:11px;background:var(--gray100);padding:1px 6px;border-radius:4px;margin:2px">'+fmtFechaCorta(d)+'</span>').join(' ')+'</div>';
    });
    html+='</div>';
  }

  cont.innerHTML = html;
}

function exportarResumen(){
  if(!resumenData||!resumenData.resumenes) return;
  const headers = ['Empleado','Total horas','Esperadas','Diferencia','Estado'];
  const rows = resumenData.resumenes.map(r=>[r.nombre,fmtDec(r.total_horas_mes).replace(',','.'),fmtDec(r.horas_esperadas).replace(',','.'),fmtDec(r.diferencia).replace(',','.'),r.estado]);
  exportCSV('resumen_mensual.csv', headers, rows);
}

/* ══════════════════════════════════════════
   EVOLUCIÓN
══════════════════════════════════════════ */
document.getElementById('chFiltroEmpEvolucion').addEventListener('change', renderEvolucion);

document.getElementById('chBtnCerrarMes').addEventListener('click', async ()=>{
  const mes = document.getElementById('chFiltroMesResumen').value || (chMeses.length ? chMeses[chMeses.length-1].mes : '');
  if(!mes){ alert('No hay mes activo.'); return; }
  if(!confirm('¿Cerrar '+labelMes(mes)+'? No se va a poder reimportar ni modificar ajustes de ese mes.')) return;
  try{
    await chFetch('cerrar-mes/', {method:'POST', body:JSON.stringify({mes})});
    [chEmpleados, chMeses] = await Promise.all([chFetch('empleados/'), chFetch('meses/')]);
    chPoblateFilters();
    renderEvolucion();
    alert('Mes cerrado.');
  } catch(e){ alert('Error: '+e.message); }
});

if(ES_ADMIN){
  const btnAbrir = document.getElementById('chBtnAbrirMes');
  if(btnAbrir) btnAbrir.addEventListener('click', async ()=>{
    const mes = prompt('¿Qué mes querés abrir? (formato YYYY-MM)');
    if(!mes) return;
    if(!confirm('¿Abrir '+mes+'? Los datos de cierre se van a borrar.')) return;
    try{
      await chFetch('abrir-mes/', {method:'POST', body:JSON.stringify({mes})});
      [chEmpleados, chMeses] = await Promise.all([chFetch('empleados/'), chFetch('meses/')]);
      chPoblateFilters();
      renderEvolucion();
      alert('Mes abierto.');
    } catch(e){ alert('Error: '+e.message); }
  });
}

async function renderEvolucion(){
  const cont = document.getElementById('chEvolucionContainer');
  const empFiltro = document.getElementById('chFiltroEmpEvolucion').value;
  cont.innerHTML = '<p class="ch-hint">Cargando...</p>';
  try{
    let url = 'evolucion/';
    if(empFiltro) url+='?empleado='+encodeURIComponent(empFiltro);
    const data = await chFetch(url);
    if(!data.meses.length){ cont.innerHTML = emptyState('No hay datos todavía. Importá fichadas primero.'); return; }

    // Tabla de evolución
    let head = '<th>Empleado</th>'+data.meses.map(m=>'<th>'+labelMes(m)+(chMeses.find(x=>x.mes===m&&x.cerrado)?' 🔒':'')+'</th>').join('')+'<th>Saldo bruto</th>';
    let rows = data.empleados.map(emp=>{
      let totalBruto=0;
      const cells = data.meses.map(m=>{
        const d = data.datos[m]&&data.datos[m][emp.nombre];
        if(!d) return '<td>—</td>';
        totalBruto += d.diferencia;
        const color = d.diferencia<-0.01?'var(--error)':(d.diferencia>0.01?'var(--good)':'var(--gray600)');
        return '<td style="font-weight:600;color:'+color+'">'+fmtHorasEtq(d.diferencia)+'</td>';
      }).join('');
      const liqs = data.liquidaciones[emp.nombre]||[];
      const totalLiq = liqs.reduce((s,l)=>s+Number(l.monto),0);
      const saldo = totalBruto - totalLiq;
      const saldoColor = saldo<-0.01?'var(--error)':(saldo>0.01?'var(--good)':'#5B655E');
      const etiqueta = saldo<-0.01?'Debe recuperar':(saldo>0.01?'Horas extra':'Al día');
      let liqExtra = '';
      if(Math.abs(totalLiq)>0.01){
        liqExtra = '<div style="font-size:9.5px;color:var(--gray400);margin-top:2px">Bruto '+fmtHorasEtq(totalBruto)+' · Liquidado '+fmtDec(totalLiq)+' h</div>';
      }
      let totalCell = '<td><div style="font-weight:700;color:'+saldoColor+'">'+fmtHorasEtq(saldo)+'</div><div style="font-size:10px;text-transform:uppercase;letter-spacing:0.3px;color:'+saldoColor+'">'+etiqueta+'</div>'+liqExtra+'</td>';
      return '<tr><td class="nombre-cell">'+esc(emp.nombre_display)+'</td>'+cells+totalCell+'</tr>';
    }).join('');

    let html = '<div class="ch-tbl-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+rows+'</tbody></table></div>';

    // Si hay un empleado filtrado: gráfico + liquidaciones
    if(empFiltro){
      const emp = data.empleados.find(e=>e.nombre===empFiltro);
      if(emp){
        // Gráfico de barras SVG
        const points = data.meses.map(m=>({
          label: labelMes(m).slice(0,3),
          value: data.datos[m]&&data.datos[m][emp.nombre] ? data.datos[m][emp.nombre].diferencia : 0,
        }));
        html += buildBarChartCH(points);

        // Liquidaciones
        const liqs = data.liquidaciones[emp.nombre]||[];
        const totalLiq = liqs.reduce((s,l)=>s+Number(l.monto),0);
        html += '<div class="ch-liq-form">';
        html += '<h2 style="margin-bottom:12px">Liquidaciones — '+esc(emp.nombre_display)+'</h2>';
        if(liqs.length){
          html += '<div class="ch-liq-historial">';
          liqs.forEach(l=>{
            html+='<div class="ch-liq-item"><span class="monto">'+fmtDec(l.monto)+' h</span><span class="meta">'+fmtFechaCorta(l.fecha)+(l.comentario?' · '+esc(l.comentario):'')+'</span>'
              +(ES_ADMIN?'<button class="ch-btn ch-btn-danger ch-btn-sm" onclick="eliminarLiquidacion('+l.id+')">🗑</button>':'')+'</div>';
          });
          html += '</div>';
          html += '<div style="margin-top:10px;font-size:12.5px;color:var(--gray600)">Total liquidado: <strong style="font-family:var(--font-mono)">'+fmtDec(totalLiq)+' h</strong></div>';
        } else {
          html += '<p class="ch-hint">Sin liquidaciones registradas.</p>';
        }
        html += '<div class="ch-row" style="margin-top:14px;gap:10px">'
          +'<div><label class="ch-label">Fecha</label><input type="date" id="chLiqFecha" value="'+todayISO()+'"></div>'
          +'<div><label class="ch-label">Horas a liquidar</label><input type="number" id="chLiqMonto" min="0" step="0.01" style="width:100px" placeholder="0,00"></div>'
          +'<div style="flex:1"><label class="ch-label">Comentario (opcional)</label><input type="text" id="chLiqComentario" style="width:100%" placeholder="ej. Pago en efectivo"></div>'
          +'<div style="margin-top:22px"><button class="ch-btn ch-btn-primary ch-btn-sm" id="chBtnLiquidar">Registrar liquidación</button></div>'
          +'</div>';
        html += '</div>';

        // Wire liquidar button
        setTimeout(()=>{
          const btn = document.getElementById('chBtnLiquidar');
          if(btn) btn.addEventListener('click', ()=>registrarLiquidacion(emp.nombre));
        }, 0);
      }
    }
    cont.innerHTML = html;
  } catch(e){ cont.innerHTML = '<div class="ch-alert-card">Error: '+esc(e.message)+'</div>'; }
}

function buildBarChartCH(points){
  const w=Math.max(560,points.length*70), h=220, pad=32;
  const max=Math.max(1,...points.map(p=>Math.abs(p.value)));
  const zeroY=pad+(h-2*pad)/2;
  const bw=(w-2*pad)/points.length;
  const bars=points.map((p,i)=>{
    const x=pad+i*bw+bw*.2, bh=(Math.abs(p.value)/max)*(h/2-pad*.6);
    const y=p.value>=0?zeroY-bh:zeroY;
    const color=p.value<0?'var(--error)':(p.value>0?'var(--good)':'var(--gray200)');
    return '<rect x="'+x+'" y="'+y+'" width="'+(bw*.6)+'" height="'+Math.max(bh,1)+'" fill="'+color+'" rx="2"></rect>'
      +'<text x="'+(x+bw*.3)+'" y="'+(h-8)+'" text-anchor="middle" font-size="10" font-family="ui-monospace,monospace" fill="var(--gray600)">'+esc(p.label)+'</text>';
  }).join('');
  return '<svg viewBox="0 0 '+w+' '+h+'" style="width:100%;max-width:'+w+'px;height:'+h+'px;margin:16px 0">'
    +'<line x1="'+pad+'" y1="'+zeroY+'" x2="'+(w-pad)+'" y2="'+zeroY+'" stroke="var(--gray200)" stroke-width="1"></line>'
    +bars+'</svg>';
}

async function registrarLiquidacion(nombre){
  const fecha=document.getElementById('chLiqFecha').value;
  const monto=document.getElementById('chLiqMonto').value;
  const comentario=document.getElementById('chLiqComentario').value;
  if(!fecha||!monto){ alert('Completá fecha y horas.'); return; }
  try{
    await chFetch('liquidar/', {method:'POST', body:JSON.stringify({empleado:nombre, fecha, monto:Number(monto), comentario})});
    renderEvolucion();
  } catch(e){ alert('Error: '+e.message); }
}

async function eliminarLiquidacion(id){
  if(!confirm('¿Eliminar esta liquidación?')) return;
  try{
    await chFetch('liquidacion/'+id+'/eliminar/', {method:'DELETE'});
    renderEvolucion();
  } catch(e){ alert('Error: '+e.message); }
}

/* ══════════════════════════════════════════
   CONFIGURACIÓN (solo admin)
══════════════════════════════════════════ */
let configLocal = [];

async function renderConfig(){
  if(!ES_ADMIN) return;
  const cont = document.getElementById('chConfigContainer');
  cont.innerHTML = '<p class="ch-hint">Cargando...</p>';
  try{
    const empleados = await chFetch('empleados/');
    configLocal = empleados.map(e=>({...e}));
    let html = '<div class="ch-tbl-wrap"><table><thead><tr>'
      +'<th>Empleado</th><th>Alias (nombre completo)</th><th title="Media jornada">½ Jornada</th>'
      +'<th title="No descontar descanso si marca 2 veces">Sin desc. descanso</th>'
      +'<th title="Bono mensual de horas extra compensadas">Bono h. extra/mes</th>'
      +'</tr></thead><tbody>';
    configLocal.forEach((e,i)=>{
      html+='<tr>'
        +'<td class="nombre-cell">'+esc(e.nombre)+'</td>'
        +'<td><input type="text" data-idx="'+i+'" data-campo="alias" value="'+esc(e.alias||'')+'" placeholder="Nombre completo..." style="width:220px"></td>'
        +'<td style="text-align:center"><input type="checkbox" data-idx="'+i+'" data-campo="medio_jornada"'+(e.medio_jornada?' checked':'')+'></td>'
        +'<td style="text-align:center"><input type="checkbox" data-idx="'+i+'" data-campo="sin_descuento_descanso"'+(e.sin_descuento_descanso?' checked':'')+'></td>'
        +'<td><input type="number" data-idx="'+i+'" data-campo="bono_horas_extra" value="'+e.bono_horas_extra+'" min="0" step="0.5" style="width:80px"></td>'
        +'</tr>';
    });
    html+='</tbody></table></div>';
    cont.innerHTML = html;

    cont.querySelectorAll('input').forEach(inp=>{
      inp.addEventListener('change', ()=>{
        const idx = Number(inp.dataset.idx);
        const campo = inp.dataset.campo;
        if(inp.type==='checkbox') configLocal[idx][campo]=inp.checked;
        else if(inp.type==='number') configLocal[idx][campo]=Number(inp.value);
        else configLocal[idx][campo]=inp.value;
      });
    });
  } catch(e){ cont.innerHTML = '<div class="ch-alert-card">Error: '+esc(e.message)+'</div>'; }
}

document.getElementById('chBtnGuardarConfig')?.addEventListener('click', async ()=>{
  const btn = document.getElementById('chBtnGuardarConfig');
  btn.disabled=true; btn.textContent='Guardando...';
  try{
    await chFetch('empleados/update/', {method:'POST', body:JSON.stringify({cambios:configLocal})});
    chEmpleados = await chFetch('empleados/');
    chPoblateFilters();
    btn.textContent='✓ Guardado';
    setTimeout(()=>{ btn.disabled=false; btn.textContent='Guardar cambios'; }, 1500);
  } catch(e){ alert('Error: '+e.message); btn.disabled=false; btn.textContent='Guardar cambios'; }
});

/* ── Arranque ── */
chInit().then(()=>{
  if(chMeses.length){
    const mesDefault = chMeses[chMeses.length-1].mes;
    document.getElementById('chFiltroMesDetalle').value = mesDefault;
    document.getElementById('chFiltroMesResumen').value = mesDefault;
  }
});