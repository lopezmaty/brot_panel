/* =========================================================
   UTILIDADES
========================================================= */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}
const fmtARS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
function money(n) { if (n == null || isNaN(n)) return '—'; return fmtARS.format(n); }
function pct(n) { if (n == null || isNaN(n)) return '—'; return (n * 100).toFixed(1) + '%'; }
function labelMes(mes) {
  const [y, m] = mes.split('-');
  const nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  return nombres[+m - 1] + ' ' + y;
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* Colores del backend → clases de badge de EERR */
const BADGE_POR_COLOR = { verde: 'verde', amarillo: 'amarillo', rojo: 'rojo', sin_real: 'gris', informativo: 'gris' };
const ICONO_POR_COLOR = { verde: '🟢', amarillo: '🟡', rojo: '🔴', sin_real: '', informativo: '' };
function badge(fila) {
  const icono = ICONO_POR_COLOR[fila.color] || '';
  return `<span class="eerr-badge ${BADGE_POR_COLOR[fila.color] || 'gris'}">${icono} ${escapeHtml(fila.semaforo)}</span>`;
}

/* Supuestos: mismo orden y textos que la pestaña "08 Presupuesto EERR".
   tipo 'pct' se muestra en % y se envía como fracción (52 → 0.52). */
const SUPUESTOS = [
  { seccion: 'Ventas' },
  { campo: 'ventas_mes_inicial', label: 'Ventas de enero presupuestadas', tipo: 'money', desc: 'Punto de partida del presupuesto anual. Se puede reemplazar por el objetivo comercial definido.' },
  { campo: 'crecimiento_ventas', label: 'Crecimiento mensual ventas', tipo: 'pct', desc: 'Proyecta cada mes siguiente con este crecimiento sobre el anterior.' },
  { seccion: 'Costos sobre ventas' },
  { campo: 'cmv_pct', label: 'CMV % sobre ventas', tipo: 'pct', desc: 'Costo de mercadería vendida proyectado sobre ventas.' },
  { campo: 'gastos_variables_pct', label: 'Gastos variables % ventas', tipo: 'pct', desc: 'Packaging, logística, comisiones u otros variables.' },
  { campo: 'gastos_financieros_pct', label: 'Gastos financieros % ventas', tipo: 'pct', desc: 'Bancos, intereses y comisiones.' },
  { campo: 'impuestos_pct', label: 'Impuestos % ventas', tipo: 'pct', desc: 'Estimación fiscal de gestión.' },
  { seccion: 'Estructura' },
  { campo: 'mo_directa_base', label: 'MO directa base mensual', tipo: 'money', desc: 'Base mensual de mano de obra directa presupuestada.' },
  { campo: 'indirectos_base', label: 'Indirectos productivos base', tipo: 'money', desc: 'Energía, gas, mantenimiento, alquiler, limpieza y estructura productiva.' },
  { campo: 'administracion_base', label: 'Administración base', tipo: 'money', desc: 'Backoffice, honorarios, sistemas y administración.' },
  { campo: 'incremento_estructura', label: 'Incremento mensual estructura', tipo: 'pct', desc: 'Ajusta mano de obra, indirectos y administración mes a mes.' },
  { campo: 'amortizaciones_mensuales', label: 'Amortizaciones mensuales', tipo: 'money', desc: 'Costo económico sin salida de caja directa. Igual todos los meses.' },
  { seccion: 'Lectura gerencial y semáforo' },
  { campo: 'resultado_objetivo_pct', label: 'Resultado operativo objetivo', tipo: 'pct', desc: 'Margen operativo objetivo para lectura gerencial.' },
  { campo: 'tolerancia_ingresos', label: 'Tolerancia semáforo ingresos', tipo: 'pct', desc: 'Ingresos y resultado: amarillo si se alcanza al menos este porcentaje del presupuesto.' },
  { campo: 'tolerancia_egresos', label: 'Tolerancia semáforo egresos', tipo: 'pct', desc: 'Egresos: amarillo si el real no supera este porcentaje del presupuesto.' },
];

/* =========================================================
   ESTADO Y NAVEGACION
========================================================= */
const inputAnio = document.getElementById('anioPpto');
inputAnio.value = new Date().getFullYear() + 1;
let datosPpto = null;

document.querySelectorAll('.eerr-nav-btn').forEach(function (boton) {
  boton.addEventListener('click', function () { activarTabPpto(boton.dataset.tab); });
});

function activarTabPpto(tab) {
  document.querySelectorAll('.eerr-nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.eerr-tab').forEach(t => t.classList.toggle('active', t.id === `tab-ppto-${tab}`));
}

inputAnio.addEventListener('change', cargarPresupuesto);

/* =========================================================
   CARGA
========================================================= */
async function cargarPresupuesto() {
  const anio = inputAnio.value;
  const resumen = document.getElementById('resumenPptoContenido');
  resumen.innerHTML = '<div class="eerr-panel"><p class="eerr-hint">Cargando...</p></div>';

  try {
    const response = await fetch(`/api/gestion_gerencial/presupuesto/?anio=${anio}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    const d = await response.json();
    if (!response.ok) {
      resumen.innerHTML = `<div class="eerr-panel"><div class="eerr-alert warn">${escapeHtml(d.error || 'Error al cargar.')}</div></div>`;
      return;
    }
    datosPpto = d;
  } catch (e) {
    resumen.innerHTML = `<div class="eerr-panel"><div class="eerr-alert warn">Error de conexión: ${escapeHtml(e)}</div></div>`;
    return;
  }

  const anios = (datosPpto.anios || []).slice().sort();
  document.getElementById('aniosCargadosPpto').textContent = anios.length ? `Años cargados: ${anios.join(', ')}` : 'Todavía no hay presupuestos cargados';

  renderSupuestos();
  if (!datosPpto.existe) {
    renderSinPresupuesto();
    activarTabPpto('supuestos');
    return;
  }
  renderResumen();
  renderTablaMensual('tablaPresupuestoPptoWrap', datosPpto.presupuesto_mensual);
  renderTablaMensual('tablaRealPptoWrap', datosPpto.real_mensual);
  renderCumplimiento();
}

function renderSinPresupuesto() {
  const vacio = `<div class="eerr-panel"><div class="eerr-empty-state"><div class="big">No hay presupuesto cargado para ${escapeHtml(inputAnio.value)}.</div>Completá los supuestos para generarlo.<div style="margin-top:14px;"><button class="eerr-btn eerr-btn-primary eerr-btn-sm" onclick="activarTabPpto('supuestos')">✏️ Cargar supuestos</button></div></div></div>`;
  document.getElementById('resumenPptoContenido').innerHTML = vacio;
  ['tablaPresupuestoPptoWrap', 'tablaRealPptoWrap', 'tablaCumplimientoPptoWrap'].forEach(id => {
    document.getElementById(id).innerHTML = '<div class="eerr-empty-state">Sin presupuesto para este año.</div>';
  });
}

/* =========================================================
   PANEL ACUMULADO
========================================================= */
function renderResumen() {
  const d = datosPpto;
  const [ing, egr, res, margen] = d.panel_acumulado;
  const objetivo = d.supuestos.resultado_objetivo_pct;

  function card(label, fila, esPct) {
    const fmt = esPct ? pct : money;
    return `<div class="eerr-card"><div class="label">${label}</div>
      <div class="value">${fmt(fila.real)}</div>
      <div class="sub">Presupuesto ${fmt(fila.presupuesto)}</div>
      <div class="sub" style="margin-top:8px;">${badge(fila)}</div></div>`;
  }

  const mesesConReal = d.real_mensual.filter(r => r !== null).length;
  let html = `<div class="eerr-panel"><h1>Panel acumulado ${d.anio}</h1>
    <p class="eerr-lede">Real acumulado contra el presupuesto de los 12 meses del año. Meses con real: <b>${mesesConReal} de 12</b>.</p>
    <div class="eerr-grid-cards">
      ${card('Ingresos acumulados', ing)}
      ${card('Egresos acumulados', egr)}
      ${card('Resultado operativo', res)}
      ${card('Margen operativo', margen, true)}
    </div></div>`;

  html += `<div class="eerr-panel"><h2>Lectura ejecutiva</h2>
    <div class="eerr-alert ${d.lectura_ejecutiva.startsWith('Prioridad') ? 'warn' : (d.lectura_ejecutiva.startsWith('Evolución') ? 'ok' : 'info')}"><span class="ppto-lectura">${escapeHtml(d.lectura_ejecutiva)}</span></div>
    <p class="eerr-hint">Margen operativo presupuestado: <b>${pct(margen.presupuesto)}</b> · Objetivo gerencial: <b>${pct(objetivo)}</b></p></div>`;

  html += `<div class="eerr-panel"><h2>Detalle del acumulado</h2>
    <table>
      <thead><tr><th>Concepto</th><th class="eerr-num">Presupuesto acumulado</th><th class="eerr-num">Real acumulado</th><th class="eerr-num">Brecha</th><th class="eerr-num">Cumplimiento / ejecución</th><th>Semáforo</th><th>Lectura</th></tr></thead>
      <tbody>
        ${d.panel_acumulado.map(f => {
          const esMargen = f.tipo === 'margen';
          const fmt = esMargen ? pct : money;
          return `<tr><td>${escapeHtml(f.concepto)}</td>
            <td class="eerr-num">${fmt(f.presupuesto)}</td>
            <td class="eerr-num">${fmt(f.real)}</td>
            <td class="eerr-num">${fmt(f.brecha)}</td>
            <td class="eerr-num">${pct(f.cumplimiento)}</td>
            <td>${badge(f)}</td>
            <td class="ppto-desc">${escapeHtml(f.lectura)}</td></tr>`;
        }).join('')}
      </tbody>
    </table></div>`;

  document.getElementById('resumenPptoContenido').innerHTML = html;
}

/* =========================================================
   TABLAS MENSUALES (presupuesto y real)
========================================================= */
function renderTablaMensual(idWrap, valoresPorMes) {
  const d = datosPpto;
  const cabecera = d.meses.map(m => `<th class="eerr-num">${labelMes(m)}</th>`).join('');

  const filas = d.conceptos.map(c => {
    const esResultado = c.clave === 'resultado_operativo';
    let total = 0;
    let hayValor = false;
    const celdas = valoresPorMes.map(mes => {
      if (mes === null) return '<td class="eerr-num ppto-sin-real">—</td>';
      hayValor = true;
      total += mes[c.clave];
      return `<td class="eerr-num">${money(mes[c.clave])}</td>`;
    }).join('');
    return `<tr${esResultado ? ' class="eerr-row-total"' : ''}>
      <td>${escapeHtml(c.nombre)}</td>
      <td class="ppto-tipo">${escapeHtml(c.tipo)}</td>
      ${celdas}
      <td class="eerr-num" style="font-weight:700;">${hayValor ? money(total) : '—'}</td></tr>`;
  }).join('');

  const sinReal = valoresPorMes.every(m => m === null);
  const aviso = sinReal ? '<div class="eerr-alert info">Todavía no hay meses con real para este año. Aparecen acá cuando el mes tiene datos importados en Estado de Resultados y cierre en Centro de Costos.</div>' : '';

  document.getElementById(idWrap).innerHTML = `${aviso}<div class="ppto-scroll"><table>
    <thead><tr><th>Concepto</th><th>Tipo</th>${cabecera}<th class="eerr-num">Total año</th></tr></thead>
    <tbody>${filas}</tbody></table></div>`;
}

/* =========================================================
   CUMPLIMIENTO POR CONCEPTO
========================================================= */
function renderCumplimiento() {
  const filas = datosPpto.cumplimiento.map(f => `<tr${f.tipo === 'resultado' ? ' class="eerr-row-total"' : ''}>
    <td>${escapeHtml(f.concepto)}</td>
    <td class="ppto-tipo">${escapeHtml(f.tipo)}</td>
    <td class="eerr-num">${money(f.presupuesto)}</td>
    <td class="eerr-num">${money(f.real)}</td>
    <td class="eerr-num">${money(f.brecha)}</td>
    <td class="eerr-num">${pct(f.cumplimiento)}</td>
    <td>${badge(f)}</td>
    <td class="ppto-desc">${escapeHtml(f.lectura)}</td></tr>`).join('');

  document.getElementById('tablaCumplimientoPptoWrap').innerHTML = `<div class="ppto-scroll"><table style="min-width:900px;">
    <thead><tr><th>Concepto</th><th>Tipo</th><th class="eerr-num">Presupuesto año</th><th class="eerr-num">Real año</th><th class="eerr-num">Brecha</th><th class="eerr-num">% cumplimiento / ejecución</th><th>Semáforo</th><th>Lectura</th></tr></thead>
    <tbody>${filas}</tbody></table></div>`;
}

/* =========================================================
   SUPUESTOS (formulario)
========================================================= */
function renderSupuestos() {
  const valores = datosPpto && datosPpto.existe ? datosPpto.supuestos : {};
  let html = '<div class="ppto-head">Supuesto</div><div class="ppto-head">Valor</div><div class="ppto-head">Cómo se usa en la proyección</div>';

  SUPUESTOS.forEach(s => {
    if (s.seccion) { html += `<div class="ppto-seccion">${s.seccion}</div>`; return; }
    let valor = valores[s.campo];
    if (valor != null && s.tipo === 'pct') valor = +(valor * 100).toFixed(4);
    const unidad = s.tipo === 'pct' ? '%' : '$';
    html += `<div>${s.label}</div>
      <div class="ppto-input-wrap"><input type="number" step="any" data-campo="${s.campo}" data-tipo="${s.tipo}" value="${valor != null ? valor : ''}" style="padding-right:30px;"><span class="ppto-unit">${unidad}</span></div>
      <div class="ppto-desc">${s.desc}</div>`;
  });

  document.getElementById('formSupuestosPpto').innerHTML = html;
  document.getElementById('alertaSupuestosPpto').innerHTML = (datosPpto && !datosPpto.existe)
    ? `<div class="eerr-alert info">No hay presupuesto para ${escapeHtml(inputAnio.value)}. Completá todos los supuestos y guardá para generarlo.</div>`
    : '';
}

document.getElementById('btnGuardarPpto').addEventListener('click', async function () {
  const payload = { anio: parseInt(inputAnio.value, 10) };
  const inputs = document.querySelectorAll('#formSupuestosPpto input[data-campo]');
  for (const input of inputs) {
    if (input.value === '') {
      alert('Completá todos los supuestos antes de guardar.');
      input.focus();
      return;
    }
    const numero = parseFloat(input.value);
    payload[input.dataset.campo] = input.dataset.tipo === 'pct' ? numero / 100 : numero;
  }

  const btn = this;
  const spinner = document.getElementById('guardandoPpto');
  btn.disabled = true;
  spinner.style.display = 'inline';

  try {
    const response = await fetch('/api/gestion_gerencial/presupuesto/guardar/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify(payload),
    });
    const d = await response.json();
    if (!response.ok) {
      document.getElementById('alertaSupuestosPpto').innerHTML = `<div class="eerr-alert warn">${escapeHtml(d.error || 'Error al guardar.')}</div>`;
      return;
    }
    await cargarPresupuesto();
    document.getElementById('alertaSupuestosPpto').innerHTML = '<div class="eerr-alert ok">Supuestos guardados. El presupuesto se recalculó.</div>';
  } catch (e) {
    document.getElementById('alertaSupuestosPpto').innerHTML = `<div class="eerr-alert warn">Error de conexión: ${escapeHtml(e)}</div>`;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
});

/* =========================================================
   INICIO
========================================================= */
cargarPresupuesto();