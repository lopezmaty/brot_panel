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
  if (!mes) return '(sin mes)';
  const [y, m] = mes.split('-');
  const nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  return nombres[+m - 1] + ' ' + y;
}
function mesActual() {
  const hoy = new Date();
  return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
}

/* =========================================================
   CONFIGURACION DE RUBROS (viene del backend)
========================================================= */
const RUBROS = JSON.parse(document.getElementById('rubrosData').textContent);
const FUERA_OPERATIVA = JSON.parse(document.getElementById('fueraOperativaData').textContent);
const SIN_CAT = 'sin_categorizar';

function nivelRubro(r, v) { if (v > r.verde_max) return 'rojo'; if (v > r.objetivo) return 'amarillo'; return 'verde'; }
function alertaBajaRubro(r, v) { return v < r.verde_min; }
function semaforoComprasVentas(v) { if (v <= 0.8) return 'verde'; if (v <= 0.9) return 'amarillo'; return 'rojo'; }
function semaforoMargen(v) { if (v >= 0.09) return 'verde'; if (v >= 0.05) return 'amarillo'; return 'rojo'; }

function opcionesRubro(valorActual) {
  let html = `<option value="${SIN_CAT}" ${valorActual === SIN_CAT ? 'selected' : ''}>— Sin categorizar —</option>`;
  RUBROS.forEach(r => {
    html += `<option value="${r.id}" ${valorActual === r.id ? 'selected' : ''}>${r.nombre}</option>`;
  });
  FUERA_OPERATIVA.forEach(f => {
    html += `<option value="${f.id}" ${valorActual === f.id ? 'selected' : ''}>${f.nombre}</option>`;
  });
  return html;
}

const filtroRubroSelect = document.getElementById('filtroRubro');
RUBROS.forEach(r => {
  const opt = document.createElement('option');
  opt.value = r.id;
  opt.textContent = r.nombre;
  filtroRubroSelect.appendChild(opt);
});
FUERA_OPERATIVA.forEach(f => {
  const opt = document.createElement('option');
  opt.value = f.id;
  opt.textContent = f.nombre;
  filtroRubroSelect.appendChild(opt);
});

/* =========================================================
   NAVEGACION
========================================================= */
const inputMes = document.getElementById('mesActivo');
inputMes.value = mesActual();

document.querySelectorAll('.mapa-nav-btn').forEach(function (boton) {
  boton.addEventListener('click', function () {
    activarTab(boton.dataset.tab);
  });
});

function activarTab(tab) {
  document.querySelectorAll('.mapa-nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.mapa-tab').forEach(t => t.classList.toggle('active', t.id === `tab-${tab}`));
  if (tab === 'revisar') cargarRevisar();
  if (tab === 'ventas') cargarDatosMesForm();
  if (tab === 'dashboard') renderDashboard();
  if (tab === 'historico') renderHistorico();
}

inputMes.addEventListener('change', function () {
  const tabActiva = document.querySelector('.mapa-nav-btn.active').dataset.tab;
  activarTab(tabActiva);
});

/* =========================================================
   CARGAR COMPRAS
========================================================= */
document.getElementById('btnImportarCompras').addEventListener('click', async function () {
  const mes = inputMes.value;
  if (!mes) { alert('Elegí un mes primero.'); return; }

  const btn = this;
  const spinner = document.getElementById('importandoCompras');
  const resultado = document.getElementById('cargaResultado');

  btn.disabled = true;
  spinner.style.display = 'inline';
  resultado.innerHTML = '';

  try {
    const response = await fetch('/api/gestion_gerencial/importar-compras-xubio/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ mes }),
    });
    const data = await response.json();

    if (!response.ok) {
      resultado.innerHTML = `<div class="mapa-alert warn">${data.error || 'No se pudo importar.'}</div>`;
      return;
    }

    let claseAlerta = 'ok';
    let mensaje = `Se importaron <strong>${data.importadas}</strong> líneas de compras.`;
    if (data.sin_categorizar > 0) {
      claseAlerta = 'warn';
      mensaje += ` <strong>${data.sin_categorizar}</strong> quedaron sin categorizar — revisalas en la pestaña "Revisar categorías".`;
    }
    resultado.innerHTML = `<div class="mapa-alert ${claseAlerta}">${mensaje}</div>`;

    const badge = document.getElementById('badge-revisar');
    if (data.sin_categorizar > 0) {
      badge.textContent = data.sin_categorizar;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  } catch (error) {
    resultado.innerHTML = `<div class="mapa-alert warn">Error de conexión: ${error}</div>`;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
});

/* =========================================================
   REVISAR CATEGORÍAS
========================================================= */
async function cargarRevisar() {
  const mes = inputMes.value;
  const soloSin = document.getElementById('soloSinCategorizar').checked;
  const rubroFiltro = filtroRubroSelect.value;
  const wrap = document.getElementById('tablaRevisarWrap');
  wrap.innerHTML = '<p class="mapa-hint">Cargando...</p>';

  try {
    let url = `/api/gestion_gerencial/compras/?mes=${mes}&solo_sin_categorizar=${soloSin ? '1' : '0'}`;
    if (!soloSin && rubroFiltro) url += `&rubro=${rubroFiltro}`;

    const response = await fetch(url, { headers: { 'X-CSRFToken': getCookie('csrftoken') } });
    const compras = await response.json();

    if (!response.ok) {
      wrap.innerHTML = `<div class="mapa-alert warn">${compras.error || 'Error al cargar.'}</div>`;
      return;
    }
    if (compras.length === 0) {
      wrap.innerHTML = '<div class="mapa-empty-state"><div class="big">No hay líneas para mostrar.</div></div>';
      return;
    }

    let html = '<table><thead><tr><th>Proveedor</th><th>Producto</th><th class="mapa-num">Importe</th><th>Rubro</th><th>Recordar</th><th></th></tr></thead><tbody>';
    compras.forEach(c => {
      const sinCat = c.rubro === SIN_CAT;
      html += `<tr class="${sinCat ? 'mapa-row-uncat' : ''}" data-compra-id="${c.id}">
        <td>${c.proveedor}</td>
        <td>${c.producto}</td>
        <td class="mapa-num">${money(parseFloat(c.importe))}</td>
        <td><select class="mapa-rubro-select">${opcionesRubro(c.rubro)}</select></td>
        <td style="text-align:center;white-space:nowrap;">
          <input type="checkbox" class="chk-recordar" checked>
          <select class="alcance-select" style="width:auto;min-width:auto;margin-left:6px;font-size:.76rem;padding:4px 6px;">
            <option value="producto">Solo este producto</option>
            <option value="proveedor">Todo el proveedor</option>
          </select>
        </td>
        <td><button class="mapa-btn mapa-btn-secondary mapa-btn-sm btn-guardar-fila">Guardar</button></td>
      </tr>`;
    });
    html += '</tbody></table>';
    wrap.innerHTML = html;

    wrap.querySelectorAll('.btn-guardar-fila').forEach(btn => {
      btn.addEventListener('click', async function () {
        const fila = btn.closest('tr');
        const compraId = fila.dataset.compraId;
        const rubro = fila.querySelector('.mapa-rubro-select').value;
        const recordar = fila.querySelector('.chk-recordar').checked;
        const alcance = fila.querySelector('.alcance-select').value;

        btn.disabled = true;
        btn.textContent = 'Guardando...';

        try {
          const resp = await fetch('/api/gestion_gerencial/asignar-rubro-compra/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ compra_id: compraId, rubro, recordar, alcance }),
          });
          if (resp.ok) {
            fila.classList.remove('mapa-row-uncat');
            btn.textContent = '✓ Guardado';
            setTimeout(() => {
              btn.textContent = 'Guardar';
              btn.disabled = false;
              cargarRevisar();
            }, 700);
          } else {
            alert('No se pudo guardar.');
            btn.disabled = false;
            btn.textContent = 'Guardar';
          }
        } catch (e) {
          alert('Error de conexión.');
          btn.disabled = false;
          btn.textContent = 'Guardar';
        }
      });
    });
  } catch (e) {
    wrap.innerHTML = `<div class="mapa-alert warn">Error de conexión: ${e}</div>`;
  }
}

document.getElementById('btnRefrescarRevisar').addEventListener('click', cargarRevisar);
document.getElementById('soloSinCategorizar').addEventListener('change', function () {
  filtroRubroSelect.disabled = this.checked;
  cargarRevisar();
});
filtroRubroSelect.addEventListener('change', cargarRevisar);

/* =========================================================
   VENTAS DEL MES
========================================================= */
document.getElementById('btnImportarVentas').addEventListener('click', async function () {
  const mes = inputMes.value;
  if (!mes) { alert('Elegí un mes primero.'); return; }

  const btn = this;
  const spinner = document.getElementById('importandoVentas');
  const resultado = document.getElementById('ventasResultado');

  btn.disabled = true;
  spinner.style.display = 'inline';
  resultado.innerHTML = '';

  try {
    const response = await fetch('/api/gestion_gerencial/importar-ventas-xubio/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ mes }),
    });
    const data = await response.json();

    if (!response.ok) {
      resultado.innerHTML = `<div class="mapa-alert warn">${data.error || 'No se pudo importar.'}</div>`;
      return;
    }

    resultado.innerHTML = `<div class="mapa-alert ok">Ventas netas: <strong>${money(data.ventas_netas)}</strong> · Unidades: <strong>${data.unidades}</strong> · Clientes activos: <strong>${data.clientes_activos}</strong></div>`;
    cargarDatosMesForm();
  } catch (error) {
    resultado.innerHTML = `<div class="mapa-alert warn">Error de conexión: ${error}</div>`;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
});

async function cargarDatosMesForm() {
  const mes = inputMes.value;
  try {
    const response = await fetch(`/api/gestion_gerencial/datos-mes/?mes=${mes}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    const datos = await response.json();
    document.getElementById('fVentasNetas').value = datos.ventas_netas;
    document.getElementById('fUnidades').value = datos.unidades;
    document.getElementById('fClientesActivos').value = datos.clientes_activos;
    document.getElementById('fClientes80').value = datos.clientes_80;
    document.getElementById('fProductos80').value = datos.productos_80;
    document.getElementById('fObservaciones').value = datos.observaciones;
  } catch (e) {
    console.error('Error cargando datos del mes:', e);
  }
  cargarDetalleVentas();
}

document.getElementById('btnGuardarMes').addEventListener('click', async function () {
  const mes = inputMes.value;
  const ok = document.getElementById('guardarMesOk');
  this.disabled = true;

  try {
    const response = await fetch('/api/gestion_gerencial/guardar-datos-mes/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({
        mes,
        ventas_netas: document.getElementById('fVentasNetas').value || 0,
        unidades: document.getElementById('fUnidades').value || 0,
        clientes_activos: document.getElementById('fClientesActivos').value || 0,
        clientes_80: document.getElementById('fClientes80').value || 0,
        productos_80: document.getElementById('fProductos80').value || 0,
        observaciones: document.getElementById('fObservaciones').value || '',
      }),
    });
    if (response.ok) {
      ok.textContent = '✓ Guardado';
      setTimeout(() => { ok.textContent = ''; }, 2000);
    } else {
      alert('No se pudo guardar.');
    }
  } catch (e) {
    alert('Error de conexión.');
  } finally {
    this.disabled = false;
  }
});

async function cargarDetalleVentas() {
  const mes = inputMes.value;
  const panel = document.getElementById('panelDetalleVentas');
  const cont = document.getElementById('detalleVentasContenido');

  try {
    const response = await fetch(`/api/gestion_gerencial/ventas-detalle/?mes=${mes}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    const datos = await response.json();

    if (!datos.clientes || (datos.clientes.length === 0 && datos.productos.length === 0)) {
      panel.style.display = 'none';
      return;
    }
    panel.style.display = 'block';

    let html = '<h2 style="font-size:1rem">Top clientes</h2><table><thead><tr><th>Cliente</th><th class="mapa-num">Importe</th><th class="mapa-num">Cantidad</th></tr></thead><tbody>';
    datos.clientes.slice(0, 20).forEach(c => {
      html += `<tr><td>${c.cliente}</td><td class="mapa-num">${money(parseFloat(c.importe))}</td><td class="mapa-num">${c.cantidad}</td></tr>`;
    });
    html += '</tbody></table>';

    html += '<h2 style="font-size:1rem;margin-top:22px">Top productos</h2><table><thead><tr><th>Producto</th><th class="mapa-num">Importe</th><th class="mapa-num">Cantidad</th></tr></thead><tbody>';
    datos.productos.slice(0, 20).forEach(p => {
      html += `<tr><td>${p.producto}</td><td class="mapa-num">${money(parseFloat(p.importe))}</td><td class="mapa-num">${p.cantidad}</td></tr>`;
    });
    html += '</tbody></table>';

    cont.innerHTML = html;
  } catch (e) {
    panel.style.display = 'none';
  }
}

/* =========================================================
   DASHBOARD
========================================================= */
async function renderDashboard() {
  const mes = inputMes.value;
  const cont = document.getElementById('dashboardContenido');
  cont.innerHTML = '<div class="mapa-panel"><p class="mapa-hint">Cargando...</p></div>';

  let d;
  try {
    const response = await fetch(`/api/gestion_gerencial/dashboard-mes/?mes=${mes}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    d = await response.json();
    if (!response.ok) {
      cont.innerHTML = `<div class="mapa-panel"><div class="mapa-alert warn">${d.error || 'Error al cargar.'}</div></div>`;
      return;
    }
  } catch (e) {
    cont.innerHTML = `<div class="mapa-panel"><div class="mapa-alert warn">Error de conexión: ${e}</div></div>`;
    return;
  }

  const ventas = d.ventas_netas;
  const compras = d.compras_operativas;
  const tot = d.totales_por_rubro;
  const margen = d.margen;
  const margenPct = d.margen_pct;
  const comprasVentas = d.compras_ventas_pct;

  let html = '';
  if (!ventas) html += `<div class="mapa-panel"><div class="mapa-alert warn">Todavía no cargaste las <b>Ventas netas</b> de ${labelMes(mes)}. Andá a "Ventas del mes".</div></div>`;
  if (d.sin_categorizar_n > 0) html += `<div class="mapa-panel"><div class="mapa-alert warn">Hay <b>${d.sin_categorizar_n}</b> gastos por <b>${money(d.sin_categorizar_monto)}</b> sin categorizar este mes, no incluidos abajo. <button class="link" onclick="activarTab('revisar')">Revisarlos →</button></div></div>`;

  html += `<div class="mapa-panel"><h1>Dashboard — ${labelMes(mes)}</h1>
    <div class="mapa-grid-cards">
      <div class="mapa-card"><div class="label">Ventas netas</div><div class="value">${money(ventas)}</div>${d.unidades ? `<div class="sub">${d.unidades} unidades · ${d.clientes_activos || 0} clientes</div>` : ''}</div>
      <div class="mapa-card"><div class="label">Compras operativas</div><div class="value">${money(compras)}</div><div class="sub"><span class="mapa-badge ${ventas ? semaforoComprasVentas(comprasVentas) : 'gris'}">${ventas ? pct(comprasVentas) : '—'} de ventas</span></div></div>
      <div class="mapa-card"><div class="label">Margen operativo</div><div class="value">${money(margen)}</div><div class="sub"><span class="mapa-badge ${ventas ? semaforoMargen(margenPct) : 'gris'}">${ventas ? pct(margenPct) : '—'}</span></div></div>
      <div class="mapa-card"><div class="label">Fuera de la operativa</div><div class="value">${money(d.total_fuera_operativa)}</div><div class="sub">Capex + retiros + otros</div></div>
    </div></div>`;

  html += `<div class="mapa-panel"><h2>Cómo se reparte cada peso de venta</h2>`;
  if (ventas > 0) {
    const escala = Math.max(ventas, compras);
    let segs = '';
    RUBROS.forEach(r => {
      const monto = tot[r.id] || 0, w = (monto / escala) * 100, p = monto / ventas;
      const nivel = nivelRubro(r, p);
      if (w > 0.3) segs += `<div class="mapa-estante-seg ${nivel || ''}" style="width:${w}%" title="${r.nombre}: ${money(monto)} (${pct(p)})">${w > 7 ? pct(p) : ''}</div>`;
    });
    const margenW = Math.max(0, (escala - compras) / escala * 100);
    if (margenW > 0.3) segs += `<div class="mapa-estante-seg margen" style="width:${margenW}%" title="Margen operativo: ${money(margen)}">${margenW > 7 ? 'Margen' : ''}</div>`;
    html += `<div class="mapa-estante">${segs}</div><div class="mapa-estante-leyenda">${RUBROS.map(r => `<span><span class="mapa-leyenda-dot"></span>${r.nombre}</span>`).join('')}</div>`;
  } else {
    html += `<div class="mapa-empty-state">Cargá las ventas netas del mes para ver este gráfico.</div>`;
  }
  html += `</div>`;

  html += `<div class="mapa-panel"><h2>Detalle por rubro / agrupador</h2><table><thead><tr><th>Rubro</th><th class="mapa-num">Monto</th><th class="mapa-num">% ventas</th><th class="mapa-num">Objetivo</th><th>Rango saludable</th><th>Estado</th></tr></thead><tbody>`;
  RUBROS.forEach(r => {
    const monto = tot[r.id] || 0, p = ventas ? monto / ventas : null;
    const nivel = ventas ? nivelRubro(r, p) : 'gris';
    const alertaBaja = ventas ? alertaBajaRubro(r, p) : false;
    const iconos = { verde: '🟢', amarillo: '🟡', rojo: '🔴', gris: '⚪' };
    const etiquetas = { verde: 'Dentro del objetivo', amarillo: 'Cerca del límite', rojo: 'Supera el rango', gris: 'Sin datos' };
    const alertaHtml = alertaBaja ? `<span class="mapa-alerta-baja" title="Gasto bien por debajo del rango sano. Revisá si no te faltó cargar algún gasto de este rubro este mes.">⚠ revisar carga</span>` : '';
    html += `<tr><td>${r.nombre}</td><td class="mapa-num">${money(monto)}</td><td class="mapa-num">${p != null ? pct(p) : '—'}</td><td class="mapa-num">${pct(r.objetivo)}</td><td>${r.rango_txt}</td><td><span class="mapa-badge ${nivel}">${iconos[nivel]} ${etiquetas[nivel]}</span> ${alertaHtml}</td></tr>`;
  });
  html += `</tbody></table></div>`;

  html += `<div class="mapa-panel"><h2>Fuera de la operativa (no cuentan en los % de rubros)</h2><table><thead><tr><th>Concepto</th><th class="mapa-num">Monto</th></tr></thead><tbody>`;
  FUERA_OPERATIVA.forEach(f => html += `<tr><td>${f.nombre}</td><td class="mapa-num">${money(tot[f.id] || 0)}</td></tr>`);
  html += `</tbody></table></div>`;

  html += `<div class="mapa-panel"><h2>Reconciliación del mes</h2><table><tbody>
    <tr><td>Compras operativas (8 rubros)</td><td class="mapa-num">${money(compras)}</td></tr>
    <tr><td>Fuera de la operativa</td><td class="mapa-num">${money(d.total_fuera_operativa)}</td></tr>
    <tr><td>Sin categorizar</td><td class="mapa-num">${money(d.sin_categorizar_monto)}</td></tr>
    <tr style="font-weight:700"><td>Total facturado del mes</td><td class="mapa-num">${money(d.total_facturado)}</td></tr>
  </tbody></table><footer class="mapa-tabfoot">Todos los montos son netos de IVA.</footer></div>`;

  cont.innerHTML = html;
}

/* =========================================================
   HISTORICO
========================================================= */
async function renderHistorico() {
  const cont = document.getElementById('historicoContenido');
  cont.innerHTML = '<p class="mapa-hint">Cargando...</p>';

  let filas;
  try {
    const response = await fetch('/api/gestion_gerencial/historico/', {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    filas = await response.json();
  } catch (e) {
    cont.innerHTML = `<div class="mapa-alert warn">Error de conexión: ${e}</div>`;
    return;
  }

  if (!filas.length) { cont.innerHTML = '<div class="mapa-empty-state">Todavía no hay meses cargados.</div>'; return; }

  let html = `<table><thead><tr><th>Mes</th><th class="mapa-num">Ventas netas</th><th class="mapa-num">Unidades</th><th class="mapa-num">Clientes</th><th class="mapa-num">Compras operativas</th><th class="mapa-num">Compras/Ventas</th><th class="mapa-num">Margen operativo</th><th class="mapa-num">Margen %</th></tr></thead><tbody>`;
  let accVentas = 0, accCompras = 0;
  filas.forEach(f => {
    accVentas += f.ventas_netas; accCompras += f.compras_operativas;
    html += `<tr><td>${labelMes(f.mes)}</td><td class="mapa-num">${f.ventas_netas ? money(f.ventas_netas) : '—'}</td><td class="mapa-num">${f.unidades || '—'}</td><td class="mapa-num">${f.clientes_activos || '—'}</td>
      <td class="mapa-num">${money(f.compras_operativas)}</td>
      <td class="mapa-num">${f.compras_ventas_pct != null ? `<span class="mapa-badge ${semaforoComprasVentas(f.compras_ventas_pct)}">${pct(f.compras_ventas_pct)}</span>` : '—'}</td>
      <td class="mapa-num">${f.margen != null ? money(f.margen) : '—'}</td>
      <td class="mapa-num">${f.margen_pct != null ? `<span class="mapa-badge ${semaforoMargen(f.margen_pct)}">${pct(f.margen_pct)}</span>` : '—'}</td></tr>`;
  });
  html += `</tbody></table>`;

  html += `<h2 style="margin-top:26px">Acumulado</h2><div class="mapa-grid-cards">
    <div class="mapa-card"><div class="label">Ventas acumuladas</div><div class="value">${money(accVentas)}</div></div>
    <div class="mapa-card"><div class="label">Compras acumuladas</div><div class="value">${money(accCompras)}</div></div>
    <div class="mapa-card"><div class="label">Margen acumulado</div><div class="value">${money(accVentas - accCompras)}</div><div class="sub">${accVentas ? pct((accVentas - accCompras) / accVentas) : '—'}</div></div>
  </div>`;

  html += `<h2 style="margin-top:26px">Evolución del margen operativo</h2>`;
  const maxV = Math.max(...filas.map(f => Math.abs(f.margen_pct || 0)), 0.15);
  html += filas.map(f => {
    const w = f.margen_pct != null ? Math.min(100, Math.abs(f.margen_pct) / maxV * 100) : 0;
    const nivel = f.margen_pct == null ? null : semaforoMargen(f.margen_pct);
    const color = nivel === 'verde' ? 'var(--success)' : nivel === 'amarillo' ? 'var(--amber)' : nivel === 'rojo' ? 'var(--error)' : 'var(--gray200)';
    return `<div class="mapa-bar-row"><div class="mapa-bar-label">${labelMes(f.mes)}</div><div class="mapa-bar-track"><div class="mapa-bar-fill" style="width:${w}%;background:${color}"></div></div><div class="mapa-bar-val">${f.margen_pct != null ? pct(f.margen_pct) : '—'}</div></div>`;
  }).join('');

  cont.innerHTML = html;
}