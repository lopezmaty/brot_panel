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
function mesAnterior() {
  const hoy = new Date();
  const anterior = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
  return `${anterior.getFullYear()}-${String(anterior.getMonth() + 1).padStart(2, '0')}`;
}

/* Objetivos de referencia (pestaña "01 Parametros" del Excel original).
   El Excel no define bandas verde/amarillo/rojo para estos dos, así que
   se usa una tolerancia de 5 puntos porcentuales antes de pasar a rojo. */
const OBJETIVO_MARGEN_BRUTO = 0.40;
const OBJETIVO_RESULTADO_OPERATIVO = 0.12;

function semaforoVsObjetivo(valor, objetivo) {
  if (valor == null) return 'gris';
  if (valor >= objetivo) return 'verde';
  if (valor >= objetivo - 0.05) return 'amarillo';
  return 'rojo';
}

/* =========================================================
   NAVEGACION
========================================================= */
const inputMesEERR = document.getElementById('mesActivoEERR');
inputMesEERR.value = mesAnterior();

document.querySelectorAll('.eerr-nav-btn').forEach(function (boton) {
  boton.addEventListener('click', function () {
    activarTabEERR(boton.dataset.tab);
  });
});

function activarTabEERR(tab) {
  document.querySelectorAll('.eerr-nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.eerr-tab').forEach(t => t.classList.toggle('active', t.id === `tab-eerr-${tab}`));
  if (tab === 'resumen') renderResumenEERR();
  if (tab === 'compras') cargarComprasEERR();
  if (tab === 'ventas') cargarVentasEERR();
  if (tab === 'mapeo') cargarMapeoEERR();
  if (tab === 'plan-cuentas') cargarPlanCuentasEERR();
  if (tab === 'historico') renderHistoricoEERR();
}

inputMesEERR.addEventListener('change', function () {
  const tabActiva = document.querySelector('.eerr-nav-btn.active').dataset.tab;
  activarTabEERR(tabActiva);
});

/* =========================================================
   TRAER DE XUBIO (ventas + compras en un solo botón)
========================================================= */
document.getElementById('btnTraerXubioEERR').addEventListener('click', async function () {
  const mes = inputMesEERR.value;
  if (!mes) { alert('Elegí un mes primero.'); return; }

  const btn = this;
  const spinner = document.getElementById('importandoEERR');
  const resultado = document.getElementById('importarResultadoEERR');

  btn.disabled = true;
  spinner.style.display = 'inline';
  resultado.innerHTML = '';

  try {
    const respCompras = await fetch('/api/gestion_gerencial/eerr/importar-compras/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ mes }),
    });
    const dataCompras = await respCompras.json();
    if (!respCompras.ok) {
      resultado.innerHTML = `<div class="eerr-alert warn">${dataCompras.error || 'No se pudieron importar las compras.'}</div>`;
      return;
    }

    const respVentas = await fetch('/api/gestion_gerencial/eerr/importar-ventas/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ mes }),
    });
    const dataVentas = await respVentas.json();
    if (!respVentas.ok) {
      resultado.innerHTML = `<div class="eerr-alert warn">${dataVentas.error || 'No se pudieron importar las ventas.'}</div>`;
      return;
    }

    let mensaje = `Compras: <strong>${dataCompras.importadas}</strong> líneas`;
    if (dataCompras.sin_categorizar > 0) mensaje += ` (<strong>${dataCompras.sin_categorizar}</strong> sin categorizar)`;
    mensaje += `. Ventas: <strong>${dataVentas.importadas}</strong> líneas día+producto`;
    if (dataVentas.sin_mapeo_costeo > 0) mensaje += ` (<strong>${dataVentas.sin_mapeo_costeo}</strong> sin costeo asociado)`;
    mensaje += '.';

    const hayPendientes = dataCompras.sin_categorizar > 0 || dataVentas.sin_mapeo_costeo > 0;
    resultado.innerHTML = `<div class="eerr-alert ${hayPendientes ? 'warn' : 'ok'}">${mensaje}</div>`;

    actualizarBadge('badge-compras', dataCompras.sin_categorizar);
    actualizarBadge('badge-mapeo', dataVentas.sin_mapeo_costeo);

    const tabActiva = document.querySelector('.eerr-nav-btn.active').dataset.tab;
    activarTabEERR(tabActiva);
  } catch (error) {
    resultado.innerHTML = `<div class="eerr-alert warn">Error de conexión: ${error}</div>`;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
});

function actualizarBadge(id, cantidad) {
  const badge = document.getElementById(id);
  if (cantidad > 0) {
    badge.textContent = cantidad;
    badge.style.display = 'inline-block';
  } else {
    badge.style.display = 'none';
  }
}

/* =========================================================
   RESUMEN
========================================================= */
async function renderResumenEERR() {
  const mes = inputMesEERR.value;
  const cont = document.getElementById('resumenEERRContenido');
  cont.innerHTML = '<div class="eerr-panel"><p class="eerr-hint">Cargando...</p></div>';

  let d;
  try {
    const response = await fetch(`/api/gestion_gerencial/eerr/calcular/?mes=${mes}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    d = await response.json();
    if (d.costeo_cerrado === false) {
      cont.innerHTML = `<div class="eerr-panel"><div class="eerr-alert warn">El mes <b>${labelMes(mes)}</b> todavía no está cerrado en Centro de Costos. Cerralo ahí (pestaña Histórico → Meses cerrados) para poder calcular el Estado de Resultados de este mes.</div></div>`;
      return;
    }
    if (!response.ok) {
      cont.innerHTML = `<div class="eerr-panel"><div class="eerr-alert warn">${d.error || 'Error al cargar.'}</div></div>`;
      return;
    }
  } catch (e) {
    cont.innerHTML = `<div class="eerr-panel"><div class="eerr-alert warn">Error de conexión: ${e}</div></div>`;
    return;
  }

  let html = '';

  if (d.ventas_sin_costeo_asociado > 0) {
    html += `<div class="eerr-panel"><div class="eerr-alert warn">Hay <b>${d.ventas_sin_costeo_asociado}</b> líneas de venta sin costeo asociado este mes — no están incluidas en el CMV. <button class="link" onclick="activarTabEERR('mapeo')">Asignarlas →</button></div></div>`;
  }

  const nivelMargenBruto = semaforoVsObjetivo(d.margen_bruto_pct, OBJETIVO_MARGEN_BRUTO);
  const nivelResultadoOp = semaforoVsObjetivo(d.resultado_operativo_pct, OBJETIVO_RESULTADO_OPERATIVO);

  html += `<div class="eerr-panel"><h1>Estado de Resultados — ${labelMes(mes)}</h1>
    <div class="eerr-grid-cards">
      <div class="eerr-card"><div class="label">Ventas netas</div><div class="value">${money(d.ventas_netas)}</div></div>
      <div class="eerr-card"><div class="label">Margen bruto</div><div class="value">${money(d.margen_bruto)}</div><div class="sub"><span class="eerr-badge ${nivelMargenBruto}">${pct(d.margen_bruto_pct)}</span> objetivo ${pct(OBJETIVO_MARGEN_BRUTO)}</div></div>
      <div class="eerr-card"><div class="label">Resultado operativo</div><div class="value">${money(d.resultado_operativo)}</div><div class="sub"><span class="eerr-badge ${nivelResultadoOp}">${pct(d.resultado_operativo_pct)}</span> objetivo ${pct(OBJETIVO_RESULTADO_OPERATIVO)}</div></div>
    </div></div>`;

  function fila(label, valor, pctVal, indent) {
    return `<tr${indent ? ' style="color:var(--gray600)"' : ''}><td${indent ? ' style="padding-left:24px"' : ''}>${label}</td><td class="eerr-num">${money(valor)}</td><td class="eerr-num">${pctVal != null ? pct(pctVal) : ''}</td></tr>`;
  }

  html += `<div class="eerr-panel"><h2>Detalle</h2>
  <table>
    <thead><tr><th>Línea</th><th class="eerr-num">Monto</th><th class="eerr-num">% sobre ventas</th></tr></thead>
    <tbody>
      ${fila('Ventas netas', d.ventas_netas, null)}
      ${fila('Costo mercadería vendida (CMV)', -d.cmv, null, true)}
      <tr class="eerr-row-total"><td>Margen bruto</td><td class="eerr-num">${money(d.margen_bruto)}</td><td class="eerr-num">${pct(d.margen_bruto_pct)}</td></tr>
      ${fila('Gastos variables', -d.gastos_variables, null, true)}
      <tr class="eerr-row-total"><td>Margen de contribución</td><td class="eerr-num">${money(d.margen_contribucion)}</td><td class="eerr-num">${pct(d.margen_contribucion_pct)}</td></tr>
      ${fila('Mano de obra directa', -d.mano_obra_directa, null, true)}
      ${fila('Indirectos productivos', -d.indirectos_productivos, null, true)}
      ${fila('Amortizaciones', -d.amortizaciones, null, true)}
      ${fila('Gastos administración', -d.gastos_administracion, null, true)}
      ${fila('Gastos financieros', -d.gastos_financieros, null, true)}
      ${fila('Impuestos', -d.impuestos, null, true)}
      ${fila('Otros resultados', d.otros_resultados, null, true)}
      <tr class="eerr-row-total"><td>Resultado operativo</td><td class="eerr-num">${money(d.resultado_operativo)}</td><td class="eerr-num">${pct(d.resultado_operativo_pct)}</td></tr>
    </tbody>
  </table>
  <footer class="eerr-tabfoot">Todos los montos son netos de IVA. Amortizaciones tomadas en vivo del módulo Costeo y Precios. "Otros resultados" suma (no resta), igual que en la planilla original.</footer>
  </div>`;

  cont.innerHTML = html;
}

/* =========================================================
   COMPRAS
========================================================= */
let planCuentasCache = null;

async function obtenerPlanCuentas() {
  if (planCuentasCache) return planCuentasCache;
  const response = await fetch('/api/gestion_gerencial/eerr/plan-cuentas/', {
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  });
  planCuentasCache = await response.json();
  return planCuentasCache;
}

function opcionesCuenta(cuentas, cuentaIdActual) {
  let html = `<option value="">— Sin categorizar —</option>`;
  cuentas.forEach(c => {
    const etiqueta = c.incluir_eerr ? c.cuenta : `${c.cuenta} (no suma al EERR)`;
    html += `<option value="${c.id}" ${cuentaIdActual === c.id ? 'selected' : ''}>${etiqueta}</option>`;
  });
  return html;
}

async function cargarComprasEERR() {
  const mes = inputMesEERR.value;
  const soloSin = document.getElementById('soloSinCategorizarEERR').checked;
  const filtroCuenta = document.getElementById('filtroCuentaEERR');
  const wrap = document.getElementById('tablaComprasEERRWrap');
  wrap.innerHTML = '<p class="eerr-hint">Cargando...</p>';

  const cuentas = await obtenerPlanCuentas();

  if (filtroCuenta.options.length === 1) {
    cuentas.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.cuenta;
      filtroCuenta.appendChild(opt);
    });
  }

  try {
    let url = `/api/gestion_gerencial/eerr/compras/?mes=${mes}&solo_sin_categorizar=${soloSin ? '1' : '0'}`;
    if (!soloSin && filtroCuenta.value) url += `&cuenta_id=${filtroCuenta.value}`;

    const response = await fetch(url, { headers: { 'X-CSRFToken': getCookie('csrftoken') } });
    const compras = await response.json();

    if (!response.ok) {
      wrap.innerHTML = `<div class="eerr-alert warn">${compras.error || 'Error al cargar.'}</div>`;
      return;
    }
    if (compras.length === 0) {
      wrap.innerHTML = '<div class="eerr-empty-state"><div class="big">No hay líneas para mostrar.</div></div>';
      return;
    }

    let html = '<table><thead><tr><th>Proveedor</th><th>Producto</th><th class="eerr-num">Importe</th><th>Cuenta</th><th>Recordar</th><th></th></tr></thead><tbody>';
    compras.forEach(c => {
      const sinCat = c.cuenta_id === null;
      const excluida = c.incluir_eerr === false;
      const clases = [sinCat ? 'eerr-row-uncat' : '', excluida ? 'eerr-row-excluida' : ''].filter(Boolean).join(' ');
      html += `<tr class="${clases}" data-compra-id="${c.id}">
        <td>${c.proveedor}</td>
        <td>${c.producto}</td>
        <td class="eerr-num">${money(parseFloat(c.importe))}</td>
        <td><select class="eerr-cuenta-select">${opcionesCuenta(cuentas, c.cuenta_id)}</select></td>
        <td style="text-align:center;white-space:nowrap;">
          <input type="checkbox" class="chk-recordar-eerr" checked>
          <select class="alcance-select-eerr" style="width:auto;min-width:auto;margin-left:6px;font-size:.76rem;padding:4px 6px;">
            <option value="producto">Solo este producto</option>
            <option value="proveedor">Todo el proveedor</option>
          </select>
        </td>
        <td><button class="eerr-btn eerr-btn-secondary eerr-btn-sm btn-guardar-fila-eerr">Guardar</button></td>
      </tr>`;
    });
    html += '</tbody></table>';
    wrap.innerHTML = html;

    wrap.querySelectorAll('.btn-guardar-fila-eerr').forEach(btn => {
      btn.addEventListener('click', async function () {
        const fila = btn.closest('tr');
        const compraId = fila.dataset.compraId;
        const cuentaId = fila.querySelector('.eerr-cuenta-select').value;
        const recordar = fila.querySelector('.chk-recordar-eerr').checked;
        const alcance = fila.querySelector('.alcance-select-eerr').value;

        if (!cuentaId) { alert('Elegí una cuenta antes de guardar.'); return; }

        btn.disabled = true;
        btn.textContent = 'Guardando...';

        try {
          const resp = await fetch('/api/gestion_gerencial/eerr/asignar-cuenta-compra/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ compra_id: compraId, cuenta_id: cuentaId, recordar, alcance }),
          });
          if (resp.ok) {
            fila.classList.remove('eerr-row-uncat');
            btn.textContent = '✓ Guardado';
            setTimeout(() => {
              btn.textContent = 'Guardar';
              btn.disabled = false;
              cargarComprasEERR();
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
    wrap.innerHTML = `<div class="eerr-alert warn">Error de conexión: ${e}</div>`;
  }
}

document.getElementById('btnRefrescarComprasEERR').addEventListener('click', cargarComprasEERR);
document.getElementById('soloSinCategorizarEERR').addEventListener('change', function () {
  document.getElementById('filtroCuentaEERR').disabled = this.checked;
  cargarComprasEERR();
});
document.getElementById('filtroCuentaEERR').addEventListener('change', cargarComprasEERR);

/* =========================================================
   VENTAS
========================================================= */
async function cargarVentasEERR() {
  const mes = inputMesEERR.value;
  const wrap = document.getElementById('tablaVentasEERRWrap');
  wrap.innerHTML = '<p class="eerr-hint">Cargando...</p>';

  try {
    const response = await fetch(`/api/gestion_gerencial/eerr/ventas/?mes=${mes}`, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    const ventas = await response.json();

    if (!response.ok) {
      wrap.innerHTML = `<div class="eerr-alert warn">${ventas.error || 'Error al cargar.'}</div>`;
      return;
    }
    if (ventas.length === 0) {
      wrap.innerHTML = '<div class="eerr-empty-state"><div class="big">No hay ventas cargadas para este mes.</div></div>';
      return;
    }

    let avisoNoCerrado = '';
    if (ventas.length && ventas[0].costeo_cerrado === false) {
      avisoNoCerrado = `<div class="eerr-alert warn">Este mes no está cerrado en Centro de Costos — las columnas de costo van a aparecer vacías hasta que lo cierres.</div>`;
    }

    let html = avisoNoCerrado + '<table><thead><tr><th>Fecha</th><th>Producto</th><th class="eerr-num">Cantidad</th><th class="eerr-num">Importe</th><th>Costeo asociado</th><th class="eerr-num">Costo unit. (CMV)</th><th class="eerr-num">CMV línea</th></tr></thead><tbody>';
    ventas.forEach(v => {
      html += `<tr class="${v.sin_costeo_asociado ? 'eerr-row-uncat' : ''}">
        <td>${v.fecha}</td>
        <td>${v.producto}</td>
        <td class="eerr-num">${v.cantidad}</td>
        <td class="eerr-num">${money(parseFloat(v.importe))}</td>
        <td>${v.sin_costeo_asociado ? '<span class="eerr-badge amarillo">Sin costeo</span>' : v.producto_costeo}</td>
        <td class="eerr-num">${v.costo_unitario_mp != null ? money(v.costo_unitario_mp) : '—'}</td>
        <td class="eerr-num">${v.cmv_linea != null ? money(v.cmv_linea) : '—'}</td>
      </tr>`;
    });
    html += '</tbody></table>';
    wrap.innerHTML = html;
  } catch (e) {
    wrap.innerHTML = `<div class="eerr-alert warn">Error de conexión: ${e}</div>`;
  }
}

/* =========================================================
   MAPEO PRODUCTO XUBIO -> COSTEO
========================================================= */
async function cargarMapeoEERR() {
  const wrapPendientes = document.getElementById('tablaMapeoEERRWrap');
  const wrapExistentes = document.getElementById('tablaMapeosExistentesEERRWrap');
  wrapPendientes.innerHTML = '<p class="eerr-hint">Cargando...</p>';
  wrapExistentes.innerHTML = '';

  try {
    const response = await fetch('/api/gestion_gerencial/eerr/mapeos-producto-costeo/', {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    const data = await response.json();

    if (!response.ok) {
      wrapPendientes.innerHTML = `<div class="eerr-alert warn">${data.error || 'Error al cargar.'}</div>`;
      return;
    }

    actualizarBadge('badge-mapeo', data.sin_mapear.length);

    if (data.sin_mapear.length === 0) {
      wrapPendientes.innerHTML = '<div class="eerr-empty-state"><div class="big">No hay productos pendientes de vincular.</div></div>';
    } else {
      const opcionesProductoCosteo = data.productos_costeo
        .map(p => `<option value="${p.id}">${p.nombre} (${p.codigo})</option>`)
        .join('');

      let html = '<table><thead><tr><th>Producto en Xubio</th><th>Producto de Costeo</th><th></th></tr></thead><tbody>';
      data.sin_mapear.forEach(s => {
        html += `<tr data-xubio-id="${s.xubio_producto_id}" data-xubio-nombre="${s.producto}">
          <td>${s.producto}</td>
          <td><select class="select-producto-costeo-eerr"><option value="">— Elegir —</option>${opcionesProductoCosteo}</select></td>
          <td><button class="eerr-btn eerr-btn-secondary eerr-btn-sm btn-guardar-mapeo-eerr">Vincular</button></td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrapPendientes.innerHTML = html;

      wrapPendientes.querySelectorAll('.btn-guardar-mapeo-eerr').forEach(btn => {
        btn.addEventListener('click', async function () {
          const fila = btn.closest('tr');
          const xubioId = fila.dataset.xubioId;
          const xubioNombre = fila.dataset.xubioNombre;
          const productoCosteoId = fila.querySelector('.select-producto-costeo-eerr').value;

          if (!productoCosteoId) { alert('Elegí un producto de Costeo.'); return; }

          btn.disabled = true;
          btn.textContent = 'Guardando...';

          try {
            const resp = await fetch('/api/gestion_gerencial/eerr/asignar-mapeo-producto-costeo/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
              body: JSON.stringify({
                xubio_producto_id: xubioId,
                xubio_producto_nombre: xubioNombre,
                producto_costeo_id: productoCosteoId,
              }),
            });
            if (resp.ok) {
              cargarMapeoEERR();
            } else {
              alert('No se pudo guardar.');
              btn.disabled = false;
              btn.textContent = 'Vincular';
            }
          } catch (e) {
            alert('Error de conexión.');
            btn.disabled = false;
            btn.textContent = 'Vincular';
          }
        });
      });
    }

    if (data.mapeos.length === 0) {
      wrapExistentes.innerHTML = '<p class="eerr-hint">Todavía no hay mapeos guardados.</p>';
    } else {
      let html = '<table><thead><tr><th>Producto en Xubio</th><th>Producto de Costeo</th></tr></thead><tbody>';
      data.mapeos.forEach(m => {
        html += `<tr><td>${m.xubio_producto_nombre || m.xubio_producto_id}</td><td>${m.producto_costeo_nombre}</td></tr>`;
      });
      html += '</tbody></table>';
      wrapExistentes.innerHTML = html;
    }
  } catch (e) {
    wrapPendientes.innerHTML = `<div class="eerr-alert warn">Error de conexión: ${e}</div>`;
  }
}

/* =========================================================
   PLAN DE CUENTAS (referencia)
========================================================= */
async function cargarPlanCuentasEERR() {
  const wrap = document.getElementById('tablaPlanCuentasEERRWrap');
  wrap.innerHTML = '<p class="eerr-hint">Cargando...</p>';

  const cuentas = await obtenerPlanCuentas();

  let html = '<table><thead><tr><th>Cuenta</th><th>Tipo</th><th>Línea EERR</th><th>Rubro</th><th>Incluye EERR</th><th class="eerr-num">Signo</th></tr></thead><tbody>';
  cuentas.forEach(c => {
    html += `<tr class="${c.incluir_eerr ? '' : 'eerr-row-excluida'}">
      <td>${c.cuenta}</td>
      <td>${c.tipo === 'ingreso' ? 'Ingreso' : 'Egreso'}</td>
      <td>${c.linea_eerr}</td>
      <td>${c.rubro}</td>
      <td>${c.incluir_eerr ? '<span class="eerr-badge verde">Sí</span>' : '<span class="eerr-badge gris">No</span>'}</td>
      <td class="eerr-num">${c.signo}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  wrap.innerHTML = html;
}

/* =========================================================
   HISTORICO ACUMULADO
========================================================= */
async function renderHistoricoEERR() {
  const cont = document.getElementById('historicoEERRContenido');
  cont.innerHTML = '<p class="eerr-hint">Cargando...</p>';

  let filas;
  try {
    const response = await fetch('/api/gestion_gerencial/eerr/historico/', {
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    filas = await response.json();
    if (!response.ok) {
      cont.innerHTML = `<div class="eerr-alert warn">${filas.error || 'Error al cargar.'}</div>`;
      return;
    }
  } catch (e) {
    cont.innerHTML = `<div class="eerr-alert warn">Error de conexión: ${e}</div>`;
    return;
  }

  if (!filas.length) { cont.innerHTML = '<div class="eerr-empty-state">Todavía no hay meses cargados.</div>'; return; }

  let html = `<table><thead><tr><th>Mes</th><th class="eerr-num">Ventas netas</th><th class="eerr-num">CMV</th><th class="eerr-num">Margen bruto</th><th class="eerr-num">Margen %</th><th class="eerr-num">Resultado operativo</th><th class="eerr-num">Result. %</th></tr></thead><tbody>`;
  let accVentas = 0, accCmv = 0, accResultado = 0;
  filas.forEach(f => {
    if (f.costeo_cerrado === false) {
      html += `<tr><td>${labelMes(f.mes)}</td><td class="eerr-num" colspan="6" style="text-align:left;color:var(--gray400)">Mes no cerrado en Centro de Costos</td></tr>`;
      return;
    }
    accVentas += f.ventas_netas;
    accCmv += f.cmv;
    accResultado += f.resultado_operativo;
    const nivelMargen = semaforoVsObjetivo(f.margen_bruto_pct, OBJETIVO_MARGEN_BRUTO);
    const nivelResultado = semaforoVsObjetivo(f.resultado_operativo_pct, OBJETIVO_RESULTADO_OPERATIVO);
    html += `<tr><td>${labelMes(f.mes)}</td>
      <td class="eerr-num">${money(f.ventas_netas)}</td>
      <td class="eerr-num">${money(f.cmv)}</td>
      <td class="eerr-num">${money(f.margen_bruto)}</td>
      <td class="eerr-num"><span class="eerr-badge ${nivelMargen}">${pct(f.margen_bruto_pct)}</span></td>
      <td class="eerr-num">${money(f.resultado_operativo)}</td>
      <td class="eerr-num"><span class="eerr-badge ${nivelResultado}">${pct(f.resultado_operativo_pct)}</span></td></tr>`;
  });
  html += `</tbody></table>`;

  const filasConDatos = filas.filter(f => f.costeo_cerrado !== false);

  html += `<h2 style="margin-top:26px">Acumulado</h2><div class="eerr-grid-cards">
    <div class="eerr-card"><div class="label">Ventas acumuladas</div><div class="value">${money(accVentas)}</div></div>
    <div class="eerr-card"><div class="label">CMV acumulado</div><div class="value">${money(accCmv)}</div></div>
    <div class="eerr-card"><div class="label">Resultado operativo acumulado</div><div class="value">${money(accResultado)}</div><div class="sub">${accVentas ? pct(accResultado / accVentas) : '—'}</div></div>
  </div>`;

  html += `<h2 style="margin-top:26px">Evolución del resultado operativo</h2>`;
  const maxV = Math.max(...filasConDatos.map(f => Math.abs(f.resultado_operativo_pct || 0)), 0.15);
  html += filasConDatos.map(f => {
    const w = Math.min(100, Math.abs(f.resultado_operativo_pct) / maxV * 100);
    const nivel = semaforoVsObjetivo(f.resultado_operativo_pct, OBJETIVO_RESULTADO_OPERATIVO);
    const color = nivel === 'verde' ? 'var(--success)' : nivel === 'amarillo' ? 'var(--amber)' : nivel === 'rojo' ? 'var(--error)' : 'var(--gray200)';
    return `<div class="eerr-bar-row"><div class="eerr-bar-label">${labelMes(f.mes)}</div><div class="eerr-bar-track"><div class="eerr-bar-fill" style="width:${w}%;background:${color}"></div></div><div class="eerr-bar-val">${pct(f.resultado_operativo_pct)}</div></div>`;
  }).join('');

  cont.innerHTML = html;
}

/* Cargar el resumen al entrar a la página */
renderResumenEERR();