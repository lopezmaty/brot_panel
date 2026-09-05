// costeo_precios.js — Brot Panel
// Port directo del HTML original Precios_y_Costos_3.html
// Los datos vienen del backend Django en vez de localStorage
'use strict';

// ============================================================
// CONFIG
// ============================================================
const CO_API = '/api/gestion_gerencial/costeo/';
const IVA_RATE = 0.105;
const TOLERANCIA_DESCUENTO = 0.02;

// ============================================================
// ESTADO (equivalente al STATE del HTML original)
// ============================================================
let STATE = {
  productos: [], insumos: [], recetas: {}, manoObra: {},
  sueldosProductivos: 0, horasDisponibles: 0,
  indirectos: { energia:0, mantenimiento:0, limpieza:0, sueldosIndirectos:0, resto:0, aguinaldos:0, alquiler:0, muni:0, iva:0, ganancias:0, contador:0 },
  equipos: [], margenObjetivo: {}, margenMinimo: 0.10, descuentoObjetivo: {},
  historialPrecios: [], historialSnapshots: [],
};

let LOADING = false;
let TAB_ACTIVA = 'resumen';
let RECETA_PRODUCTO_ACTIVO = null;
let FILTRO_PRIORIDAD = 'todas';

// ============================================================
// UTILS
// ============================================================
function fmtMoney(n){ if(n===undefined||n===null||isNaN(n)) return '$ 0'; return '$ ' + Number(n).toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function fmtMoney0(n){ if(n===undefined||n===null||isNaN(n)) return '$ 0'; return '$ ' + Number(n).toLocaleString('es-AR',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function fmtPct(n, dec){ if(n===undefined||n===null||isNaN(n)) return '0,0%'; return (Number(n)*100).toLocaleString('es-AR',{minimumFractionDigits:dec===undefined?1:dec,maximumFractionDigits:dec===undefined?1:dec}) + '%'; }
function fmtNum(n, dec){ if(n===undefined||n===null||isNaN(n)) return '0'; return Number(n).toLocaleString('es-AR',{minimumFractionDigits:dec||0,maximumFractionDigits:dec===undefined?2:dec}); }
function fmtFecha(iso){ const d = new Date(iso); return d.toLocaleDateString('es-AR',{day:'2-digit',month:'short',year:'numeric'}) + ' ' + d.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'}); }
function formatMoneyInputValue(n){ if(n===undefined||n===null||isNaN(n)) return '0,00'; return Number(n).toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function leerMoneda(str){ if(str===undefined||str===null||str==='') return 0; const limpio = String(str).replace(/\$/g,'').trim().replace(/\./g,'').replace(',','.'); const n = parseFloat(limpio); return isNaN(n) ? 0 : n; }
function leerNumero(v){ if(v===''||v===null||v===undefined) return 0; const n = Number(String(v).replace(',','.')); return isNaN(n) ? 0 : n; }
function esc(s){ if(s===undefined||s===null) return ''; return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function uid(){ return 'x' + Math.random().toString(36).slice(2,9); }
function estadoIcono(cls){ return {verde:'🟢', azul:'🔵', amarillo:'🟡', rojo:'🔴', gris:'⚪'}[cls] || ''; }

function showToast(msg){
  const t = document.getElementById('co-toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(()=>t.classList.remove('show'), 2400);
}

function csrfToken(){
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

async function apiFetch(path, opts={}){
  const res = await fetch(CO_API + path, {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), ...(opts.headers||{}) },
    ...opts,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.json();
}

// ============================================================
// CÁLCULOS (port del HTML original — operan sobre STATE)
// ============================================================
function getInsumoPrecio(nombreInsumo){
  const ins = STATE.insumos.find(i => i.nombre === nombreInsumo);
  return ins ? (Number(ins.precio) || 0) : 0;
}

function calcMPUnitario(codigo){
  const prod = STATE.productos.find(p=>p.codigo===codigo);
  const receta = STATE.recetas[codigo] || [];
  if(!prod || !prod.unidadesLote) return 0;
  const rendimiento = Number(prod.unidadesLote) || 0;
  let total = 0;
  for(const ing of receta){
    const merma = Number(ing.merma) || 0;
    const unidadesVendibles = rendimiento * (1 - merma);
    if(!unidadesVendibles) continue;
    const precio = getInsumoPrecio(ing.insumo);
    const costoIngrediente = (Number(ing.cantidad) || 0) * precio;
    total += costoIngrediente / unidadesVendibles;
  }
  return total;
}

function calcManoDeObra(){
  const costoHora = STATE.horasDisponibles ? (STATE.sueldosProductivos / STATE.horasDisponibles) : 0;
  const rows = [];
  let totalHorasActivas = 0;
  for(const prod of STATE.productos){
    const mo = STATE.manoObra[prod.codigo] || {};
    const lotesMes = prod.unidadesLote ? (Number(prod.unidadesMes)||0) / Number(prod.unidadesLote) : 0;
    const personas = Number(mo.personas) || 0;
    const tiempo = Number(mo.tiempoMinLote) || 0;
    const horasActivas = personas * (tiempo/60) * lotesMes;
    totalHorasActivas += horasActivas;
    rows.push({codigo: prod.codigo, lotesMes, horasActivas, unidadesVendibles: Number(prod.unidadesMes)||0});
  }
  const saldoHoras = (Number(STATE.horasDisponibles)||0) - totalHorasActivas;
  const result = {};
  for(const row of rows){
    const share = totalHorasActivas ? row.horasActivas / totalHorasActivas : 0;
    const incremento = saldoHoras * share;
    const nuevoTotalHoras = row.horasActivas + incremento;
    const costoTotalMO = nuevoTotalHoras * costoHora;
    const costoMOUnitario = row.unidadesVendibles ? costoTotalMO / row.unidadesVendibles : 0;
    result[row.codigo] = {lotesMes: row.lotesMes, horasActivas: row.horasActivas, nuevoTotalHoras, costoMOUnitario, costoTotalMO};
  }
  return {costoHora, totalHorasActivas, saldoHoras, porProducto: result};
}

function calcAmortizacionMensual(){
  return (STATE.equipos||[]).reduce((acc,eq)=>{
    const anios = Number(eq.vidaUtilAnios)||0;
    if(!anios) return acc;
    return acc + (Number(eq.valorReposicion)||0)/anios/12;
  }, 0);
}

function calcIndirectosTotal(){
  const ind = STATE.indirectos;
  const amortizacion = calcAmortizacionMensual();
  const otrosIndirectos = (Number(ind.sueldosIndirectos)||0) + (Number(ind.resto)||0) + (Number(ind.aguinaldos)||0) + (Number(ind.alquiler)||0);
  const impuestos = (Number(ind.muni)||0) + (Number(ind.iva)||0) + (Number(ind.ganancias)||0) + (Number(ind.contador)||0);
  const total = (Number(ind.energia)||0) + (Number(ind.mantenimiento)||0) + (Number(ind.limpieza)||0) + amortizacion + otrosIndirectos + impuestos;
  return {amortizacion, otrosIndirectos, impuestos, total};
}

function calcIndirectosPorProducto(moResult){
  const {total} = calcIndirectosTotal();
  const totalHorasMO = Object.values(moResult.porProducto).reduce((acc,r)=>acc+r.nuevoTotalHoras, 0);
  const result = {};
  for(const prod of STATE.productos){
    const r = moResult.porProducto[prod.codigo];
    const horas = r ? r.nuevoTotalHoras : 0;
    const pct = totalHorasMO ? horas/totalHorasMO : 0;
    const indirectosAsignados = total * pct;
    const unidadesMes = Number(prod.unidadesMes)||0;
    const indirectoUnitario = unidadesMes ? indirectosAsignados/unidadesMes : 0;
    result[prod.codigo] = {pctUtilizacion: pct, indirectosAsignados, indirectoUnitario, horas};
  }
  return {total, totalHorasMO, porProducto: result};
}

function calcMatriz(){
  const mo = calcManoDeObra();
  const indirectos = calcIndirectosPorProducto(mo);
  const piso = Number(STATE.margenMinimo)||0;
  const filas = [];
  for(const prod of STATE.productos){
    const mpUnit = calcMPUnitario(prod.codigo);
    const moRow = mo.porProducto[prod.codigo] || {costoMOUnitario:0};
    const indRow = indirectos.porProducto[prod.codigo] || {indirectoUnitario:0};
    const moUnit = moRow.costoMOUnitario;
    const indUnit = indRow.indirectoUnitario;
    const costoTotal = mpUnit + moUnit + indUnit;
    const precio = Number(prod.precioActual)||0;
    const margenD = precio - costoTotal;
    const margenPct = precio ? margenD/precio : 0;
    let objetivo = STATE.margenObjetivo[prod.codigo];
    if(objetivo===undefined||objetivo===null) objetivo = margenPct;
    if(objetivo < piso) objetivo = piso;
    const precioMinimo = (1-objetivo)!==0 ? costoTotal/(1-objetivo) : 0;
    let precioSugerido;
    if(precio >= precioMinimo - 1){ precioSugerido = precio; }
    else { precioSugerido = Math.ceil(precioMinimo/10)*10; }
    const diferenciaPrecio = precioSugerido - precio;
    let estado, estadoClass;
    if(!precio){ estado='Sin precio'; estadoClass='gris'; }
    else if(!mpUnit && !moUnit){ estado='Pendiente costeo'; estadoClass='gris'; }
    else if(Math.abs(margenPct-objetivo)<0.001){ estado='En objetivo'; estadoClass='verde'; }
    else if(margenPct>objetivo){ estado='Margen mejoró'; estadoClass='azul'; }
    else if(margenPct>=objetivo-0.05){ estado='Cerca del objetivo'; estadoClass='amarillo'; }
    else { estado='Bajo objetivo'; estadoClass='rojo'; }
    filas.push({
      codigo:prod.codigo, nombre:prod.nombre, familia:prod.familia,
      precioActual:precio, precioConIVA:Number(prod.precioConIVA)||0,
      unidadesMes:Number(prod.unidadesMes)||0,
      mpUnit, moUnit, indUnit, costoTotal, margenD, margenPct,
      margenObjetivo:objetivo, precioMinimo, precioSugerido, diferenciaPrecio,
      estado, estadoClass, ventas: precio*(Number(prod.unidadesMes)||0),
    });
  }
  return {filas, mo, indirectos, piso};
}

function calcRanking(){
  const {filas} = calcMatriz();
  const conVentas = filas.slice().sort((a,b)=>b.ventas-a.ventas);
  const totalVentas = conVentas.reduce((a,f)=>a+f.ventas, 0);
  return conVentas.map((f,i)=>{
    const rank = i+1;
    const ajusteRequerido = Math.max(0, f.precioSugerido-f.precioActual);
    const ajustePct = f.precioActual ? ajusteRequerido/f.precioActual : 0;
    let prioridad;
    if(f.estadoClass==='rojo') prioridad='Alta';
    else if(rank<=15 && ajustePct>=0.05) prioridad='Alta';
    else if(f.estadoClass==='amarillo') prioridad='Media';
    else if(ajustePct>=0.01 && rank<=25) prioridad='Media';
    else prioridad='Baja';
    return {...f, rank, pctVentas: totalVentas?f.ventas/totalVentas:0, ajusteRequerido, ajustePct, prioridad};
  });
}

function calcListaPrecios(){
  const {filas} = calcMatriz();
  const prodPorCodigo = {};
  STATE.productos.forEach(p=>{ prodPorCodigo[p.codigo]=p; });
  return filas.map(f=>{
    const prod = prodPorCodigo[f.codigo];
    const tienePrecio = prod.precioDistribuidor!==null && prod.precioDistribuidor!==undefined;
    const precioDistribuidor = tienePrecio ? Number(prod.precioDistribuidor) : 0;
    const precioDistribuidorNeto = precioDistribuidor / (1+IVA_RATE);
    const descuentoActual = tienePrecio && f.precioConIVA ? (f.precioConIVA-precioDistribuidor)/f.precioConIVA : null;
    let descuentoObjetivo = STATE.descuentoObjetivo ? STATE.descuentoObjetivo[f.codigo] : undefined;
    if(descuentoObjetivo===undefined||descuentoObjetivo===null) descuentoObjetivo=descuentoActual;
    const fueraDeObjetivo = (descuentoActual!==null && descuentoObjetivo!==null) ? Math.abs(descuentoActual-descuentoObjetivo)>TOLERANCIA_DESCUENTO : false;
    const margenDistribuidor = (tienePrecio && precioDistribuidorNeto) ? (precioDistribuidorNeto-f.costoTotal)/precioDistribuidorNeto : null;
    const precioSugeridoGastronomico = f.precioSugerido*(1+IVA_RATE);
    const precioSugeridoDistribuidor = (descuentoObjetivo!==null && descuentoObjetivo!==undefined) ? precioSugeridoGastronomico*(1-descuentoObjetivo) : null;
    return {
      codigo:f.codigo, nombre:f.nombre, familia:f.familia, costoTotal:f.costoTotal,
      precioGastronomico:f.precioConIVA, margenGastronomico:f.margenPct,
      precioSugeridoGastronomico,
      precioDistribuidor: tienePrecio ? precioDistribuidor : null,
      descuentoActual, descuentoObjetivo, fueraDeObjetivo,
      precioSugeridoDistribuidor, margenDistribuidor,
    };
  });
}

// ============================================================
// CARGA DE DATOS DESDE BACKEND
// ============================================================
async function cargarDatos(){
  if(LOADING) return;
  LOADING = true;
  const wrap = document.getElementById('co-content');
  if(wrap) wrap.style.opacity = '0.5';
  try {
    const [productos, insumos, config, equipos, historial] = await Promise.all([
      apiFetch('productos/'),
      apiFetch('insumos/'),
      apiFetch('config/'),
      apiFetch('equipos/'),
      apiFetch('historial/'),
    ]);

    // Armar STATE igual al HTML original
    STATE.productos = productos.map(p=>({
      codigo: p.codigo, nombre: p.nombre, familia: p.familia,
      peso: p.peso, precioActual: p.precio_actual, precioConIVA: p.precio_con_iva,
      precioDistribuidor: p.precio_distribuidor, unidadesMes: p.unidades_mes,
      unidadesLote: p.unidades_lote,
    }));
    STATE.insumos = insumos.map(i=>({ nombre:i.nombre, unidad:i.unidad, precio:i.precio, comentario:i.comentario }));
    STATE.recetas = {};
    productos.forEach(p=>{
      STATE.recetas[p.codigo] = (p.receta||[]).map(l=>({
        insumo:l.insumo_nombre, categoria:l.categoria, unidad:l.unidad,
        cantidad:l.cantidad, merma:l.merma,
      }));
    });
    STATE.manoObra = {};
    productos.forEach(p=>{
      if(p.mano_obra) STATE.manoObra[p.codigo] = {
        proceso: p.mano_obra.proceso, personas: p.mano_obra.personas,
        tiempoMinLote: p.mano_obra.tiempo_min_lote,
      };
    });
    STATE.sueldosProductivos = config.sueldos_productivos;
    STATE.horasDisponibles = config.horas_disponibles;
    STATE.margenMinimo = config.margen_minimo;
    STATE.indirectos = {
      energia: config.energia, mantenimiento: config.mantenimiento,
      limpieza: config.limpieza, sueldosIndirectos: config.sueldos_indirectos,
      resto: config.resto, aguinaldos: config.aguinaldos, alquiler: config.alquiler,
      muni: config.muni, iva: config.iva, ganancias: config.ganancias, contador: config.contador,
    };
    STATE.equipos = equipos.map(e=>({ id:e.id, nombre:e.nombre, valorReposicion:e.valor_reposicion, vidaUtilAnios:e.vida_util_anios }));
    STATE.margenObjetivo = {};
    STATE.descuentoObjetivo = {};
    productos.forEach(p=>{
      if(p.margen_objetivo!=null) STATE.margenObjetivo[p.codigo] = p.margen_objetivo;
      if(p.descuento_objetivo!=null) STATE.descuentoObjetivo[p.codigo] = p.descuento_objetivo;
    });
    STATE.historialPrecios = (historial||[]).map(h=>({
      id: h.id, fecha: h.fecha, tipo: h.tipo, item: h.item,
      valorAnterior: h.valor_anterior, valorNuevo: h.valor_nuevo,
    }));

    render();
    actualizarBadges();
  } catch(e) {
    showToast('Error cargando datos: ' + e.message);
    console.error(e);
  } finally {
    LOADING = false;
    if(wrap) wrap.style.opacity = '1';
  }
}

async function guardarProductos(){
  const cambios = STATE.productos.map(p=>({
    codigo: p.codigo,
    precio_con_iva: p.precioConIVA,
    precio_distribuidor: p.precioDistribuidor,
    unidades_mes: p.unidadesMes,
    unidades_lote: p.unidadesLote,
    margen_objetivo: STATE.margenObjetivo[p.codigo],
    descuento_objetivo: STATE.descuentoObjetivo[p.codigo],
  }));
  await apiFetch('productos/bulk-update/', {method:'POST', body:JSON.stringify({cambios})});
}

async function guardarInsumos(){
  const cambios = STATE.insumos.map(i=>({ nombre:i.nombre, precio:i.precio }));
  await apiFetch('insumos/bulk-update/', {method:'POST', body:JSON.stringify({cambios})});
}

async function guardarManoObra(){
  const cambios = Object.entries(STATE.manoObra).map(([codigo,mo])=>({
    codigo, proceso:mo.proceso, personas:mo.personas, tiempo_min_lote:mo.tiempoMinLote,
  }));
  await apiFetch('mano-obra/bulk-update/', {method:'POST', body:JSON.stringify({cambios})});
}

async function guardarConfig(){
  const data = {
    sueldos_productivos: STATE.sueldosProductivos,
    horas_disponibles: STATE.horasDisponibles,
    margen_minimo: STATE.margenMinimo,
    energia: STATE.indirectos.energia, mantenimiento: STATE.indirectos.mantenimiento,
    limpieza: STATE.indirectos.limpieza, sueldos_indirectos: STATE.indirectos.sueldosIndirectos,
    resto: STATE.indirectos.resto, aguinaldos: STATE.indirectos.aguinaldos,
    alquiler: STATE.indirectos.alquiler, muni: STATE.indirectos.muni,
    iva: STATE.indirectos.iva, ganancias: STATE.indirectos.ganancias, contador: STATE.indirectos.contador,
  };
  await apiFetch('config/', {method:'PATCH', body:JSON.stringify(data)});
}

async function guardarEquipos(){
  const cambios = STATE.equipos.map(e=>({
    id: e.id, nombre: e.nombre, valor_reposicion: e.valorReposicion, vida_util_anios: e.vidaUtilAnios,
  }));
  await apiFetch('equipos/bulk-update/', {method:'POST', body:JSON.stringify({cambios})});
}

function registrarCambioPrecio(tipo, item, valorAnterior, valorNuevo){
  if(valorAnterior === valorNuevo) return;
  STATE.historialPrecios.unshift({
    id:uid(), fecha:new Date().toISOString(), tipo, item,
    valorAnterior: Number(valorAnterior)||0, valorNuevo: Number(valorNuevo)||0,
  });
}

// ============================================================
// NAVEGACIÓN
// ============================================================
function activarTab(tab){
  TAB_ACTIVA = tab;
  document.querySelectorAll('.co-nav-btn').forEach(b=>b.classList.toggle('active', b.dataset.tab===tab));
  render();
  const content = document.getElementById('co-content');
  if(content) content.scrollTop = 0;
}

function render(){
  const content = document.getElementById('co-content');
  if(!content) return;
  const renders = {
    resumen: renderResumen, productos: renderProductos, insumos: renderInsumos,
    recetas: renderRecetas, manoobra: renderManoObra, indirectos: renderIndirectos,
    matriz: renderMatriz, ranking: renderRanking, listaprecios: renderListaPrecios,
    historico: renderHistorico,
  };
  if(renders[TAB_ACTIVA]){
    content.innerHTML = renders[TAB_ACTIVA]();
    wireTab(TAB_ACTIVA);
  }
  document.querySelectorAll('[data-goto]').forEach(b=>{
    b.addEventListener('click', ()=>activarTab(b.dataset.goto));
  });
}

function wireTab(tab){
  if(tab==='productos') wireProductos();
  if(tab==='insumos') wireInsumos();
  if(tab==='recetas') wireRecetas();
  if(tab==='manoobra') wireManoObra();
  if(tab==='indirectos') wireIndirectos();
  if(tab==='matriz') wireMatriz();
  if(tab==='ranking') wireRankingFilters();
  if(tab==='listaprecios') wireListaPrecios();
  if(tab==='historico') wireHistorico();
}

function actualizarBadges(){
  const {filas} = calcMatriz();
  const problemas = filas.filter(f=>f.estadoClass==='rojo').length;
  const badge = document.getElementById('badge-matriz');
  if(badge){ badge.style.display = problemas>0?'inline-flex':'none'; badge.textContent=problemas; }
}

// ============================================================
// RENDER: RESUMEN
// ============================================================
function renderResumen(){
  const {filas, mo} = calcMatriz();
  const indTotal = calcIndirectosTotal();
  const totalVentas = filas.reduce((a,f)=>a+f.ventas,0);
  const rojos = filas.filter(f=>f.estadoClass==='rojo');
  const amarillos = filas.filter(f=>f.estadoClass==='amarillo');
  const azules = filas.filter(f=>f.estadoClass==='azul');
  const verdes = filas.filter(f=>f.estadoClass==='verde');
  const sinPrecio = filas.filter(f=>f.estadoClass==='gris');
  const margenProm = filas.length ? filas.reduce((a,f)=>a+f.margenPct,0)/filas.length : 0;
  const top5 = filas.slice().sort((a,b)=>b.ventas-a.ventas).slice(0,5);
  const maxVenta = top5.length ? top5[0].ventas : 1;

  let alertasHtml = '';
  if(rojos.length>0) alertasHtml += `<div class="alert warn">🔴 <div><b>${rojos.length} producto${rojos.length>1?'s':''}</b> por debajo del margen objetivo. <button class="link" data-goto="matriz">Ver en Costo y precio →</button></div></div>`;
  if(sinPrecio.length>0) alertasHtml += `<div class="alert info">ℹ️ <div><b>${sinPrecio.length} producto${sinPrecio.length>1?'s':''}</b> sin precio o receta cargada todavía.</div></div>`;
  if(rojos.length===0 && sinPrecio.length===0) alertasHtml += `<div class="alert ok">✅ Todos los productos están en objetivo o por encima.</div>`;

  return `
    <div class="co-panel">
      <h1>Resumen general</h1>
      <p class="lede">Estado actual del costeo — todo se recalcula en vivo con los datos cargados en cada pestaña. Método de asignación de indirectos: % de utilización de mano de obra.</p>
      <div class="grid-cards">
        <div class="card acento"><div class="label">Productos activos</div><div class="value">${filas.length}</div></div>
        <div class="card"><div class="label">Ventas mensuales (a precio actual)</div><div class="value">${fmtMoney0(totalVentas)}</div></div>
        <div class="card"><div class="label">Indirectos totales / mes</div><div class="value">${fmtMoney0(indTotal.total)}</div></div>
        <div class="card"><div class="label">Sueldos productivos / mes</div><div class="value">${fmtMoney0(STATE.sueldosProductivos)}</div></div>
        <div class="card"><div class="label">Margen promedio</div><div class="value">${fmtPct(margenProm)}</div></div>
        <div class="card"><div class="label">Horas MO disponibles</div><div class="value">${fmtNum(STATE.horasDisponibles)} hs</div><div class="sub">${fmtNum(mo.totalHorasActivas,1)} hs activas hoy</div></div>
      </div>
    </div>
    <div class="co-panel">
      <div class="co-panel-title">Importar precios desde Xubio</div>
      <p class="lede">Actualiza el precio gastronómico (c/IVA) y el precio de distribuidor de todos los productos contra las listas de Xubio.</p>
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
        <button class="btn btn-primary" id="btn-importar-precios">📥 Importar precios desde Xubio</button>
        <span id="importar-status" style="font-size:.8rem;color:var(--gray600)"></span>
      </div>
    </div>
    <div class="co-panel">
      <div class="co-panel-title">Alertas</div>
      ${alertasHtml}
    </div>
    <div class="co-panel">
      <div class="co-panel-title">Estado de márgenes</div>
      <div class="grid-cards">
        <div class="card"><div class="label">🟢 En objetivo</div><div class="value">${verdes.length}</div></div>
        <div class="card"><div class="label">🔵 Margen mejoró</div><div class="value">${azules.length}</div></div>
        <div class="card"><div class="label">🟡 Cerca del objetivo</div><div class="value">${amarillos.length}</div></div>
        <div class="card"><div class="label">🔴 Bajo objetivo</div><div class="value">${rojos.length}</div></div>
      </div>
    </div>
    <div class="co-panel">
      <div class="co-panel-title">Top 5 productos por venta mensual</div>
      ${top5.map(f=>`
        <div class="bar-row">
          <div class="bar-label" title="${esc(f.nombre)}">${esc(f.nombre)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${(f.ventas/maxVenta*100).toFixed(1)}%;background:var(--sky)"></div></div>
          <div class="bar-val">${fmtMoney0(f.ventas)}</div>
        </div>
      `).join('')}
    </div>
  `;
}

// ============================================================
// RENDER: PRODUCTOS
// ============================================================
function renderProductos(){
  const familias = [...new Set(STATE.productos.map(p=>p.familia).filter(Boolean))];
  const rows = STATE.productos.map((p,i)=>`
    <tr data-idx="${i}">
      <td><input type="text" class="prod-in" data-field="codigo" value="${esc(p.codigo)}" style="width:70px"></td>
      <td><input type="text" class="prod-in" data-field="nombre" value="${esc(p.nombre)}" style="min-width:230px"></td>
      <td><input type="text" class="prod-in" data-field="familia" value="${esc(p.familia)}" list="familias-list" style="min-width:130px"></td>
      <td class="num"><input type="number" class="prod-in num-in" data-field="peso" value="${p.peso||0}" style="width:70px"></td>
      <td class="num"><span class="money-input-wrap"><span class="cur">$</span><input type="text" inputmode="decimal" class="prod-in money-in precio-iva-in" data-field="precioConIVA" value="${formatMoneyInputValue(p.precioConIVA)}"></span></td>
      <td class="num">${p.precioDistribuidor!==null && p.precioDistribuidor!==undefined
            ? `<span class="money-input-wrap"><span class="cur">$</span><input type="text" inputmode="decimal" class="prod-in money-in precio-dist-prod-in" data-field="precioDistribuidor" value="${formatMoneyInputValue(p.precioDistribuidor)}"></span>`
            : `<span class="money-input-wrap"><span class="cur">$</span><input type="text" inputmode="decimal" class="prod-in money-in precio-dist-prod-in" data-field="precioDistribuidor" value="" placeholder="completar"></span>`}</td>
      <td class="num"><input type="number" class="prod-in num-in" data-field="unidadesMes" value="${p.unidadesMes||0}" style="width:90px"></td>
      <td class="num"><input type="number" class="prod-in num-in" data-field="unidadesLote" value="${p.unidadesLote||0}" style="width:90px"></td>
      <td style="text-align:center"><button class="icon-btn btn-del-prod" title="Eliminar producto">🗑</button></td>
    </tr>
  `).join('');

  return `
    <div class="co-panel">
      <h1>Productos</h1>
      <p class="lede">Base de productos: peso, precio de venta, unidades vendidas por mes y unidades que rinde cada lote de producción. Cargá el <b>precio gastronómico</b> y el <b>precio de distribuidor</b> con IVA.</p>
      <div class="filters">
        <button class="btn btn-primary btn-sm" id="btnAddProducto">+ Agregar producto</button>
        <span class="hint">${STATE.productos.length} productos cargados</span>
      </div>
      <datalist id="familias-list">${familias.map(f=>`<option value="${esc(f)}">`).join('')}</datalist>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Código</th><th>Producto</th><th>Familia</th><th class="num">Peso (g)</th>
            <th class="num">Precio gastronómico (c/IVA)</th><th class="num">Precio distribuidor (c/IVA)</th>
            <th class="num">Unid. / mes</th><th class="num">Unid. / lote</th><th></th>
          </tr></thead>
          <tbody id="productosBody">${rows}</tbody>
        </table>
      </div>
      <div class="filters" style="margin-top:16px">
        <button class="btn btn-primary btn-sm" id="btn-guardar-productos">💾 Guardar cambios</button>
      </div>
    </div>
  `;
}

function wireProductos(){
  const body = document.getElementById('productosBody');
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.prod-in');
    if(!input) return;
    const tr = input.closest('tr');
    const idx = Number(tr.dataset.idx);
    const field = input.dataset.field;
    const prod = STATE.productos[idx];
    if(field==='precioConIVA'){
      const nuevo = leerMoneda(input.value);
      registrarCambioPrecio('producto', prod.codigo+' — '+prod.nombre+' (c/IVA)', prod.precioConIVA, nuevo);
      prod.precioConIVA = nuevo;
      prod.precioActual = Math.round((nuevo/(1+IVA_RATE))*100)/100;
    } else if(field==='precioDistribuidor'){
      const nuevo = leerMoneda(input.value);
      registrarCambioPrecio('distribuidor', prod.codigo+' — '+prod.nombre+' (distribuidor)', prod.precioDistribuidor||0, nuevo);
      prod.precioDistribuidor = nuevo;
    } else if(['peso','unidadesMes','unidadesLote'].includes(field)){
      prod[field] = leerNumero(input.value);
    } else {
      prod[field] = input.value;
    }
    render();
    actualizarBadges();
  });

  body.addEventListener('click', (e)=>{
    const btn = e.target.closest('.btn-del-prod');
    if(!btn) return;
    const idx = Number(btn.closest('tr').dataset.idx);
    const prod = STATE.productos[idx];
    if(!confirm('¿Eliminar "'+prod.nombre+'"?')) return;
    delete STATE.recetas[prod.codigo];
    delete STATE.margenObjetivo[prod.codigo];
    delete STATE.descuentoObjetivo[prod.codigo];
    delete STATE.manoObra[prod.codigo];
    STATE.productos.splice(idx,1);
    render();
  });

  document.getElementById('btnAddProducto').addEventListener('click', ()=>{
    let n = STATE.productos.length+1;
    let codigo = 'P'+String(n).padStart(3,'0');
    while(STATE.productos.some(p=>p.codigo===codigo)){ n++; codigo='P'+String(n).padStart(3,'0'); }
    STATE.productos.push({codigo, nombre:'Nuevo producto', familia:'', peso:0, precioConIVA:0, precioActual:0, unidadesMes:0, unidadesLote:1, precioDistribuidor:null});
    STATE.recetas[codigo] = [];
    STATE.manoObra[codigo] = {proceso:'', personas:1, tiempoMinLote:0};
    render();
    showToast('Producto agregado — completá su receta en "Costeo MP".');
  });

  document.getElementById('btn-guardar-productos').addEventListener('click', async()=>{
    const btn = document.getElementById('btn-guardar-productos');
    btn.disabled = true; btn.textContent = 'Guardando…';
    try {
      await guardarProductos();
      showToast('Productos guardados.');
    } catch(e){ showToast('Error: '+e.message); }
    finally { btn.disabled=false; btn.textContent='💾 Guardar cambios'; }
  });
}

// ============================================================
// RENDER: INSUMOS
// ============================================================
function renderInsumos(){
  const rows = STATE.insumos.map((ins,i)=>{
    const usadoEn = Object.entries(STATE.recetas).filter(([,rec])=>rec.some(r=>r.insumo===ins.nombre)).length;
    return `
    <tr data-idx="${i}">
      <td><input type="text" class="ins-in" data-field="nombre" value="${esc(ins.nombre)}" style="min-width:200px"></td>
      <td><input type="text" class="ins-in" data-field="unidad" value="${esc(ins.unidad)}" style="width:80px"></td>
      <td class="num"><span class="money-input-wrap"><span class="cur">$</span><input type="text" inputmode="decimal" class="ins-in money-in" data-field="precio" value="${formatMoneyInputValue(ins.precio)}"></span></td>
      <td class="num">${usadoEn ? `<span class="badge gris">${usadoEn} prod.</span>` : `<span class="badge amarillo">sin usar</span>`}</td>
      <td style="text-align:center"><button class="icon-btn btn-del-ins" title="Eliminar insumo">🗑</button></td>
    </tr>`;
  }).join('');

  return `
    <div class="co-panel">
      <h1>Precios de insumos</h1>
      <p class="lede">Cargá el precio de cada insumo acá — todas las recetas de "Costeo MP" lo toman automáticamente. Actualizar un precio recalcula el costo de todos los productos que lo usan.</p>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Insumo</th><th>Unidad</th><th class="num">Precio neto</th><th class="num">Uso</th><th></th></tr></thead>
          <tbody id="insumosBody">${rows}</tbody>
        </table>
      </div>
      <div class="filters" style="margin-top:16px">
        <button class="btn btn-primary btn-sm" id="btnAddInsumo">+ Agregar insumo</button>
        <button class="btn btn-primary btn-sm" id="btn-guardar-insumos">💾 Guardar precios</button>
      </div>
    </div>
  `;
}

function wireInsumos(){
  const body = document.getElementById('insumosBody');
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.ins-in');
    if(!input) return;
    const tr = input.closest('tr');
    const idx = Number(tr.dataset.idx);
    const field = input.dataset.field;
    const ins = STATE.insumos[idx];
    if(field==='precio'){
      const nuevo = leerMoneda(input.value);
      registrarCambioPrecio('insumo', ins.nombre, ins.precio, nuevo);
      ins.precio = nuevo;
    } else if(field==='nombre'){
      const nombreViejo = ins.nombre;
      const nombreNuevo = input.value;
      Object.values(STATE.recetas).forEach(rec=>rec.forEach(r=>{ if(r.insumo===nombreViejo) r.insumo=nombreNuevo; }));
      ins.nombre = nombreNuevo;
    } else { ins[field] = input.value; }
    render();
    actualizarBadges();
  });

  body.addEventListener('click', (e)=>{
    const btn = e.target.closest('.btn-del-ins');
    if(!btn) return;
    const idx = Number(btn.closest('tr').dataset.idx);
    const ins = STATE.insumos[idx];
    const usadoEn = Object.values(STATE.recetas).filter(rec=>rec.some(r=>r.insumo===ins.nombre)).length;
    if(usadoEn>0 && !confirm(`"${ins.nombre}" se usa en ${usadoEn} producto(s). ¿Eliminar igual?`)) return;
    STATE.insumos.splice(idx,1);
    render();
  });

  document.getElementById('btnAddInsumo').addEventListener('click', ()=>{
    STATE.insumos.push({nombre:'Nuevo insumo', unidad:'kg', precio:0, comentario:''});
    render();
  });

  document.getElementById('btn-guardar-insumos').addEventListener('click', async()=>{
    const btn = document.getElementById('btn-guardar-insumos');
    btn.disabled=true; btn.textContent='Guardando…';
    try {
      await guardarInsumos();
      showToast('Precios de insumos guardados.');
      await cargarDatos();
    } catch(e){ showToast('Error: '+e.message); }
    finally { btn.disabled=false; btn.textContent='💾 Guardar precios'; }
  });
}

// ============================================================
// RENDER: COSTEO MP (recetas)
// ============================================================
function renderRecetas(){
  if(!RECETA_PRODUCTO_ACTIVO && STATE.productos.length) RECETA_PRODUCTO_ACTIVO = STATE.productos[0].codigo;
  const prod = STATE.productos.find(p=>p.codigo===RECETA_PRODUCTO_ACTIVO);
  const receta = prod ? (STATE.recetas[prod.codigo]||[]) : [];

  const chips = STATE.productos.map(p=>`
    <div class="chip ${p.codigo===RECETA_PRODUCTO_ACTIVO?'active':''}" data-codigo="${esc(p.codigo)}">${esc(p.codigo)} · ${esc(p.nombre)}</div>
  `).join('');

  let tablaHtml = '';
  let resumenHtml = '';
  if(prod){
    const rendimiento = Number(prod.unidadesLote)||0;
    let totalCosto = 0;
    const filas = receta.map((ing,i)=>{
      const merma = Number(ing.merma)||0;
      const unidVend = rendimiento*(1-merma);
      const precioIns = getInsumoPrecio(ing.insumo);
      const costoIng = (Number(ing.cantidad)||0)*precioIns;
      const costoUnit = unidVend ? costoIng/unidVend : 0;
      totalCosto += costoUnit;
      return `
        <tr data-idx="${i}">
          <td>
            <select class="rec-in" data-field="insumo" style="min-width:170px">
              ${STATE.insumos.map(o=>`<option value="${esc(o.nombre)}" ${o.nombre===ing.insumo?'selected':''}>${esc(o.nombre)}</option>`).join('')}
            </select>
          </td>
          <td><input type="text" class="rec-in" data-field="categoria" value="${esc(ing.categoria||'')}" style="width:110px"></td>
          <td><input type="text" class="rec-in" data-field="unidad" value="${esc(ing.unidad||'')}" style="width:70px"></td>
          <td class="num"><input type="number" step="0.001" class="rec-in num-in" data-field="cantidad" value="${ing.cantidad||0}" style="width:90px"></td>
          <td class="num">${fmtMoney(precioIns)}</td>
          <td class="num"><input type="number" step="0.001" class="rec-in num-in" data-field="merma" value="${ing.merma||0}" style="width:70px"></td>
          <td class="num">${fmtMoney(costoUnit)}</td>
          <td style="text-align:center"><button class="icon-btn btn-del-ing" title="Quitar ingrediente">🗑</button></td>
        </tr>
      `;
    }).join('');

    tablaHtml = `
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Insumo</th><th>Categoría</th><th>Unidad</th><th class="num">Cantidad / lote</th>
            <th class="num">Precio unit.</th><th class="num">Merma</th><th class="num">Costo unit.</th><th></th>
          </tr></thead>
          <tbody id="recetaBody">${filas||'<tr><td colspan="8" class="hint" style="padding:16px">Sin ingredientes todavía.</td></tr>'}</tbody>
        </table>
      </div>
      <div class="filters" style="margin-top:14px">
        <button class="btn btn-secondary btn-sm" id="btnAddIngrediente">+ Agregar ingrediente</button>
      </div>
    `;
    resumenHtml = `
      <div class="grid-cards" style="margin-bottom:20px">
        <div class="card acento"><div class="label">Costo MP unitario</div><div class="value">${fmtMoney(totalCosto)}</div><div class="sub">por unidad vendible</div></div>
        <div class="card"><div class="label">Unidades por lote</div><div class="value">${fmtNum(rendimiento)}</div></div>
        <div class="card"><div class="label">Precio de venta actual</div><div class="value">${fmtMoney(prod.precioActual)}</div></div>
      </div>
    `;
  }

  return `
    <div class="co-panel">
      <h1>Costeo de materia prima</h1>
      <p class="lede">Elegí un producto y cargá su receta: qué insumos lleva, cuánto de cada uno por lote de producción, y la merma esperada.</p>
      <div class="chip-row" id="recetaChips">${chips}</div>
      ${prod ? resumenHtml+tablaHtml : '<div class="empty-state"><div class="big">No hay productos cargados</div></div>'}
    </div>
  `;
}

function wireRecetas(){
  const chipsWrap = document.getElementById('recetaChips');
  if(chipsWrap) chipsWrap.addEventListener('click', (e)=>{
    const chip = e.target.closest('.chip');
    if(!chip) return;
    RECETA_PRODUCTO_ACTIVO = chip.dataset.codigo;
    render();
  });
  const body = document.getElementById('recetaBody');
  if(!body) return;
  const receta = STATE.recetas[RECETA_PRODUCTO_ACTIVO];
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.rec-in');
    if(!input) return;
    const idx = Number(input.closest('tr').dataset.idx);
    const field = input.dataset.field;
    if(field==='cantidad'||field==='merma') receta[idx][field]=leerNumero(input.value);
    else receta[idx][field]=input.value;
    render();
  });
  body.addEventListener('click', (e)=>{
    const btn = e.target.closest('.btn-del-ing');
    if(!btn) return;
    receta.splice(Number(btn.closest('tr').dataset.idx),1);
    render();
  });
  const btnAdd = document.getElementById('btnAddIngrediente');
  if(btnAdd) btnAdd.addEventListener('click', ()=>{
    const primero = STATE.insumos[0];
    receta.push({insumo:primero?primero.nombre:'',categoria:'Insumo',unidad:primero?primero.unidad:'kg',cantidad:0,merma:0.03});
    render();
  });
}

// ============================================================
// RENDER: MANO DE OBRA
// ============================================================
function renderManoObra(){
  const mo = calcManoDeObra();
  const pctUsado = STATE.horasDisponibles ? (mo.totalHorasActivas/STATE.horasDisponibles*100) : 0;
  const rows = STATE.productos.map(p=>{
    const m = STATE.manoObra[p.codigo] || {proceso:'',personas:1,tiempoMinLote:0};
    const r = mo.porProducto[p.codigo] || {lotesMes:0,horasActivas:0,nuevoTotalHoras:0,costoMOUnitario:0};
    return `
      <tr data-codigo="${esc(p.codigo)}">
        <td><b>${esc(p.codigo)}</b><div class="hint">${esc(p.nombre)}</div></td>
        <td><input type="text" class="mo-in" data-field="proceso" value="${esc(m.proceso||'')}" style="min-width:220px"></td>
        <td class="num"><input type="number" class="mo-in num-in" data-field="personas" value="${m.personas||0}" style="width:70px"></td>
        <td class="num"><input type="number" step="0.1" class="mo-in num-in" data-field="tiempoMinLote" value="${m.tiempoMinLote||0}" style="width:90px"></td>
        <td class="num">${fmtNum(r.lotesMes,2)}</td>
        <td class="num">${fmtNum(r.horasActivas,2)}</td>
        <td class="num">${fmtNum(r.nuevoTotalHoras,2)}</td>
        <td class="num"><b>${fmtMoney(r.costoMOUnitario)}</b></td>
      </tr>
    `;
  }).join('');

  return `
    <div class="co-panel">
      <h1>Mano de obra</h1>
      <p class="lede">Cargá el tiempo activo que insume cada lote. Las horas "ociosas" se reparten proporcionalmente entre todos los productos.</p>
      <div class="co-form-grid">
        <div class="field"><label>Sueldos productivos / mes</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="inSueldos" value="${formatMoneyInputValue(STATE.sueldosProductivos)}"></span></div>
        <div class="field"><label>Horas hombre disponibles / mes</label><input type="number" id="inHorasDisp" value="${STATE.horasDisponibles||0}"></div>
        <div class="field"><label>Costo por hora (calculado)</label><input type="text" value="${fmtMoney(mo.costoHora)}" disabled></div>
      </div>
      <div class="grid-cards" style="margin-bottom:20px">
        <div class="card"><div class="label">Horas activas usadas</div><div class="value">${fmtNum(mo.totalHorasActivas,1)}</div><div class="sub">${fmtPct(pctUsado/100)} de las disponibles</div></div>
        <div class="card"><div class="label">Horas ociosas a repartir</div><div class="value">${fmtNum(mo.saldoHoras,1)}</div><div class="sub">levado, enfriado, tiempos muertos</div></div>
        <div class="card acento"><div class="label">Total sueldos asignado</div><div class="value">${fmtMoney0(STATE.sueldosProductivos)}</div><div class="sub">100% repartido entre productos</div></div>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Producto</th><th>Proceso</th><th class="num">Personas</th><th class="num">Min. / lote</th>
            <th class="num">Lotes / mes</th><th class="num">Hs. activas</th><th class="num">Hs. totales*</th><th class="num">Costo MO unit.</th>
          </tr></thead>
          <tbody id="manoObraBody">${rows}</tbody>
        </table>
      </div>
      <footer class="tabfoot">*Hs. totales = horas activas + porción proporcional de horas ociosas repartidas.</footer>
      <div class="filters" style="margin-top:16px">
        <button class="btn btn-primary btn-sm" id="btn-guardar-mo">💾 Guardar mano de obra</button>
      </div>
    </div>
  `;
}

function wireManoObra(){
  document.getElementById('inSueldos').addEventListener('change', (e)=>{ STATE.sueldosProductivos=leerMoneda(e.target.value); render(); });
  document.getElementById('inHorasDisp').addEventListener('change', (e)=>{ STATE.horasDisponibles=leerNumero(e.target.value); render(); });
  const body = document.getElementById('manoObraBody');
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.mo-in');
    if(!input) return;
    const codigo = input.closest('tr').dataset.codigo;
    if(!STATE.manoObra[codigo]) STATE.manoObra[codigo]={proceso:'',personas:1,tiempoMinLote:0};
    const field = input.dataset.field;
    if(field==='proceso') STATE.manoObra[codigo][field]=input.value;
    else STATE.manoObra[codigo][field]=leerNumero(input.value);
    render();
  });
  document.getElementById('btn-guardar-mo').addEventListener('click', async()=>{
    const btn = document.getElementById('btn-guardar-mo');
    btn.disabled=true; btn.textContent='Guardando…';
    try {
      await guardarManoObra();
      await guardarConfig();
      showToast('Mano de obra guardada.');
      await cargarDatos();
    } catch(e){ showToast('Error: '+e.message); }
    finally { btn.disabled=false; btn.textContent='💾 Guardar mano de obra'; }
  });
}

// ============================================================
// RENDER: INDIRECTOS
// ============================================================
function renderIndirectos(){
  const ind = STATE.indirectos;
  const amortizacion = calcAmortizacionMensual();
  const totales = calcIndirectosTotal();

  const equiposRows = STATE.equipos.map((eq,i)=>{
    const anios = Number(eq.vidaUtilAnios)||0;
    const amortMensual = anios ? (Number(eq.valorReposicion)||0)/anios/12 : 0;
    return `
      <tr data-idx="${i}">
        <td><input type="text" class="eq-in" data-field="nombre" value="${esc(eq.nombre)}" style="min-width:150px"></td>
        <td class="num"><span class="money-input-wrap"><span class="cur">$</span><input type="text" inputmode="decimal" class="eq-in money-in" data-field="valorReposicion" value="${formatMoneyInputValue(eq.valorReposicion)}"></span></td>
        <td class="num"><input type="number" step="0.5" class="eq-in num-in" data-field="vidaUtilAnios" value="${eq.vidaUtilAnios||0}" style="width:80px"></td>
        <td class="num">${fmtMoney0(amortMensual)}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="co-panel">
      <h1>Gastos indirectos</h1>
      <p class="lede">Costos que no se pueden asignar directo a un producto. Se reparten entre los productos según qué % de horas de mano de obra consume cada uno.</p>
      <div class="co-form-grid">
        <div class="field"><label>Energía eléctrica / gas</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-energia" value="${formatMoneyInputValue(ind.energia)}"></span></div>
        <div class="field"><label>Mantenimiento productivo</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-mantenimiento" value="${formatMoneyInputValue(ind.mantenimiento)}"></span></div>
        <div class="field"><label>Limpieza e higiene</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-limpieza" value="${formatMoneyInputValue(ind.limpieza)}"></span></div>
        <div class="field"><label>Sueldos indirectos</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-sueldosIndirectos" value="${formatMoneyInputValue(ind.sueldosIndirectos)}"></span></div>
        <div class="field"><label>Resto</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-resto" value="${formatMoneyInputValue(ind.resto)}"></span></div>
        <div class="field"><label>Aguinaldos</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-aguinaldos" value="${formatMoneyInputValue(ind.aguinaldos)}"></span></div>
        <div class="field"><label>Alquiler</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-alquiler" value="${formatMoneyInputValue(ind.alquiler)}"></span></div>
        <div class="field"><label>Municipal</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-muni" value="${formatMoneyInputValue(ind.muni)}"></span></div>
        <div class="field"><label>IVA</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-iva" value="${formatMoneyInputValue(ind.iva)}"></span></div>
        <div class="field"><label>Impuesto a las Ganancias</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-ganancias" value="${formatMoneyInputValue(ind.ganancias)}"></span></div>
        <div class="field"><label>Contador / balance</label><span class="money-input-wrap" style="display:flex"><span class="cur">$</span><input type="text" inputmode="decimal" id="ind-contador" value="${formatMoneyInputValue(ind.contador)}"></span></div>
      </div>
      <div class="grid-cards" style="margin-bottom:8px">
        <div class="card"><div class="label">Amortización (equipos)</div><div class="value">${fmtMoney0(amortizacion)}</div></div>
        <div class="card"><div class="label">Otros indirectos</div><div class="value">${fmtMoney0(totales.otrosIndirectos)}</div></div>
        <div class="card"><div class="label">Impuestos</div><div class="value">${fmtMoney0(totales.impuestos)}</div></div>
        <div class="card acento"><div class="label">TOTAL INDIRECTOS / mes</div><div class="value">${fmtMoney0(totales.total)}</div></div>
      </div>
    </div>
    <div class="co-panel">
      <h2>Amortización de equipos</h2>
      <p class="lede">Amortización mensual = valor de reposición ÷ vida útil (años) ÷ 12.</p>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Equipo</th><th class="num">Valor de reposición</th><th class="num">Vida útil (años)</th><th class="num">Amortización / mes</th></tr></thead>
          <tbody id="equiposBody">${equiposRows}</tbody>
        </table>
      </div>
      <div class="filters" style="margin-top:16px">
        <button class="btn btn-primary btn-sm" id="btn-guardar-indirectos">💾 Guardar indirectos y equipos</button>
      </div>
    </div>
  `;
}

function wireIndirectos(){
  const campos = ['energia','mantenimiento','limpieza','sueldosIndirectos','resto','aguinaldos','alquiler','muni','iva','ganancias','contador'];
  campos.forEach(c=>{
    const el = document.getElementById('ind-'+c);
    if(el) el.addEventListener('change', ()=>{ STATE.indirectos[c]=leerMoneda(el.value); render(); });
  });
  const body = document.getElementById('equiposBody');
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.eq-in');
    if(!input) return;
    const idx = Number(input.closest('tr').dataset.idx);
    const field = input.dataset.field;
    if(field==='nombre') STATE.equipos[idx][field]=input.value;
    else if(field==='valorReposicion') STATE.equipos[idx][field]=leerMoneda(input.value);
    else STATE.equipos[idx][field]=leerNumero(input.value);
    render();
  });
  document.getElementById('btn-guardar-indirectos').addEventListener('click', async()=>{
    const btn = document.getElementById('btn-guardar-indirectos');
    btn.disabled=true; btn.textContent='Guardando…';
    try {
      await guardarConfig();
      await guardarEquipos();
      showToast('Indirectos y equipos guardados.');
      await cargarDatos();
    } catch(e){ showToast('Error: '+e.message); }
    finally { btn.disabled=false; btn.textContent='💾 Guardar indirectos y equipos'; }
  });
}

// ============================================================
// RENDER: MATRIZ COSTO Y PRECIO
// ============================================================
function renderMatriz(){
  const {filas, piso} = calcMatriz();
  const promedioActual = filas.length ? filas.reduce((a,f)=>a+f.margenPct,0)/filas.length : 0;
  const promedioObjetivo = filas.length ? filas.reduce((a,f)=>a+f.margenObjetivo,0)/filas.length : 0;
  const rojos = filas.filter(f=>f.estadoClass==='rojo').length;

  const rows = filas.map(f=>{
    const rowClass = f.estadoClass==='rojo'?'row-rojo':(f.estadoClass==='amarillo'?'row-amarillo':'');
    return `
      <tr class="${rowClass}" data-codigo="${esc(f.codigo)}">
        <td class="col-prod"><b>${esc(f.codigo)}</b><span class="prod-nombre">${esc(f.nombre)}</span></td>
        <td class="num">${fmtMoney(f.precioConIVA)}</td>
        <td class="num">${fmtMoney(f.mpUnit)}</td>
        <td class="num">${fmtMoney(f.moUnit)}</td>
        <td class="num">${fmtMoney(f.indUnit)}</td>
        <td class="num"><b>${fmtMoney(f.costoTotal)}</b></td>
        <td class="num">${fmtPct(f.margenPct)}</td>
        <td class="num"><span class="pct-input-wrap"><input type="number" step="0.001" class="obj-in num-in" value="${(f.margenObjetivo*100).toFixed(2)}">%</span></td>
        <td style="text-align:center"><span class="badge ${f.estadoClass}">${estadoIcono(f.estadoClass)} ${f.estado}</span></td>
        <td class="num">${fmtMoney(f.precioSugerido*(1+IVA_RATE))}</td>
        <td class="num" style="${f.diferenciaPrecio>0.5?'color:var(--error);font-weight:700':''}">${f.diferenciaPrecio>0.5?fmtMoney((f.precioSugerido*(1+IVA_RATE))-f.precioConIVA):'—'}</td>
        <td style="text-align:center"><button class="icon-btn btn-fijar-obj" title="Fijar objetivo = margen actual">🎯</button></td>
      </tr>
    `;
  }).join('');

  return `
    <div class="co-panel">
      <h1>Costo y precio</h1>
      <p class="lede">Costo total (materia prima + mano de obra + indirectos), margen actual contra el margen objetivo, y precio sugerido cuando hace falta subirlo.</p>
      <div class="co-form-grid" style="max-width:260px">
        <div class="field"><label>Piso mínimo de margen (%)</label><input type="number" step="0.5" id="inPiso" value="${(piso*100).toFixed(1)}"></div>
      </div>
      <div class="grid-cards" style="margin-bottom:18px">
        <div class="card acento"><div class="label">Promedio margen actual</div><div class="value">${fmtPct(promedioActual)}</div></div>
        <div class="card acento"><div class="label">Promedio margen objetivo</div><div class="value">${fmtPct(promedioObjetivo)}</div></div>
      </div>
      ${rojos>0?`<div class="alert warn">🔴 ${rojos} producto${rojos>1?'s':''} por debajo de su margen objetivo.</div>`:''}
      <div class="tbl-wrap">
        <table class="tbl-sticky">
          <thead><tr>
            <th class="col-prod">Producto</th><th class="num">Precio actual (c/IVA)</th><th class="num">MP unit.</th><th class="num">MO unit.</th><th class="num">Indirecto unit.</th>
            <th class="num">Costo total</th><th class="num">Margen actual</th><th class="num">Margen objetivo</th><th class="center">Estado</th>
            <th class="num">Precio sugerido (c/IVA)</th><th class="num">Ajuste (c/IVA)</th><th></th>
          </tr></thead>
          <tbody id="matrizBody">${rows}</tbody>
        </table>
      </div>
      <div class="filters" style="margin-top:16px">
        <button class="btn btn-primary btn-sm" id="btn-guardar-matriz">💾 Guardar márgenes objetivo</button>
      </div>
      <footer class="tabfoot">🎯 = fija el margen objetivo de ese producto en su margen actual.</footer>
    </div>
  `;
}

function wireMatriz(){
  document.getElementById('inPiso').addEventListener('change', (e)=>{ STATE.margenMinimo=leerNumero(e.target.value)/100; render(); });
  const body = document.getElementById('matrizBody');
  body.addEventListener('change', (e)=>{
    const input = e.target.closest('.obj-in');
    if(!input) return;
    const codigo = input.closest('tr').dataset.codigo;
    STATE.margenObjetivo[codigo] = leerNumero(input.value)/100;
    render();
  });
  body.addEventListener('click', (e)=>{
    const btn = e.target.closest('.btn-fijar-obj');
    if(!btn) return;
    const codigo = btn.closest('tr').dataset.codigo;
    const {filas} = calcMatriz();
    const f = filas.find(x=>x.codigo===codigo);
    STATE.margenObjetivo[codigo] = Math.max(f.margenPct, STATE.margenMinimo);
    render();
    showToast('Objetivo de '+codigo+' fijado en '+fmtPct(STATE.margenObjetivo[codigo]));
  });
  document.getElementById('btn-guardar-matriz').addEventListener('click', async()=>{
    const btn = document.getElementById('btn-guardar-matriz');
    btn.disabled=true; btn.textContent='Guardando…';
    try {
      await guardarProductos();
      await guardarConfig();
      showToast('Márgenes guardados.');
    } catch(e){ showToast('Error: '+e.message); }
    finally { btn.disabled=false; btn.textContent='💾 Guardar márgenes objetivo'; }
  });
}

// ============================================================
// RENDER: RANKING
// ============================================================
function renderRanking(){
  let ranking = calcRanking();
  const counts = {Alta:0, Media:0, Baja:0};
  ranking.forEach(r=>counts[r.prioridad]++);
  if(FILTRO_PRIORIDAD!=='todas') ranking = ranking.filter(r=>r.prioridad===FILTRO_PRIORIDAD);
  const prioClass = {Alta:'rojo', Media:'amarillo', Baja:'verde'};

  const rows = ranking.map(f=>`
    <tr class="${f.prioridad==='Alta'?'row-rojo':(f.prioridad==='Media'?'row-amarillo':'')}">
      <td class="num">#${f.rank}</td>
      <td class="col-prod"><b>${esc(f.codigo)}</b><span class="prod-nombre">${esc(f.nombre)}</span></td>
      <td class="num">${fmtMoney0(f.ventas)}</td>
      <td class="num">${fmtPct(f.pctVentas)}</td>
      <td class="num">${fmtPct(f.margenPct)}</td>
      <td class="num">${fmtPct(f.margenObjetivo)}</td>
      <td style="text-align:center"><span class="badge ${f.estadoClass}">${estadoIcono(f.estadoClass)} ${f.estado}</span></td>
      <td class="num">${f.ajusteRequerido>0.5?fmtMoney(f.precioSugerido*(1+IVA_RATE)):'—'}</td>
      <td class="num" style="${f.ajusteRequerido>0.5?'color:var(--error);font-weight:700':''}">${f.ajusteRequerido>0.5?fmtMoney(f.ajusteRequerido*(1+IVA_RATE)):'—'}</td>
      <td class="num">${f.ajusteRequerido>0.5?fmtPct(f.ajustePct):'—'}</td>
      <td style="text-align:center"><span class="badge ${prioClass[f.prioridad]}">${f.prioridad}</span></td>
    </tr>
  `).join('');

  return `
    <div class="co-panel">
      <h1>Ranking y prioridades de ajuste</h1>
      <p class="lede">Productos ordenados por venta mensual, con la prioridad de ajuste de precio.</p>
      <div class="grid-cards" style="margin-bottom:18px">
        <div class="card acento" style="border-left-color:var(--error)"><div class="label">Prioridad alta</div><div class="value">${counts.Alta}</div></div>
        <div class="card acento" style="border-left-color:var(--amber)"><div class="label">Prioridad media</div><div class="value">${counts.Media}</div></div>
        <div class="card acento" style="border-left-color:var(--success)"><div class="label">Prioridad baja</div><div class="value">${counts.Baja}</div></div>
      </div>
      <div class="chip-row">
        <div class="chip ${FILTRO_PRIORIDAD==='todas'?'active':''}" data-filtro="todas">Todas</div>
        <div class="chip ${FILTRO_PRIORIDAD==='Alta'?'active':''}" data-filtro="Alta">🔴 Alta</div>
        <div class="chip ${FILTRO_PRIORIDAD==='Media'?'active':''}" data-filtro="Media">🟡 Media</div>
        <div class="chip ${FILTRO_PRIORIDAD==='Baja'?'active':''}" data-filtro="Baja">🟢 Baja</div>
      </div>
      <div class="tbl-wrap">
        <table class="tbl-sticky">
          <thead><tr>
            <th class="num">#</th><th class="col-prod">Producto</th><th class="num">Ventas $/mes</th><th class="num">% ventas</th><th class="num">Margen actual</th>
            <th class="num">Margen objetivo</th><th class="center">Estado</th><th class="num">Precio sugerido (c/IVA)</th><th class="num">Ajuste (c/IVA)</th><th class="num">Ajuste %</th><th class="center">Prioridad</th>
          </tr></thead>
          <tbody>${rows||'<tr><td colspan="11" class="hint" style="padding:16px">No hay productos con esta prioridad.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  `;
}

function wireRankingFilters(){
  document.querySelectorAll('[data-filtro]').forEach(chip=>{
    chip.addEventListener('click', ()=>{ FILTRO_PRIORIDAD=chip.dataset.filtro; render(); });
  });
}

// ============================================================
// RENDER: LISTA DE PRECIOS
// ============================================================
function renderListaPrecios(){
  const filas = calcListaPrecios();
  const conPrecio = filas.filter(f=>f.precioDistribuidor!==null);
  const promedioGastro = filas.length ? filas.reduce((a,f)=>a+f.margenGastronomico,0)/filas.length : 0;
  const promedioDistrib = conPrecio.length ? conPrecio.reduce((a,f)=>a+(f.margenDistribuidor||0),0)/conPrecio.length : 0;
  const sinCompletar = filas.filter(f=>f.precioDistribuidor===null).length;
  const fueraDeObjetivo = filas.filter(f=>f.fueraDeObjetivo).length;

  const rows = filas.map(f=>{
    const sinDato = f.precioDistribuidor===null;
    const rowClass = f.fueraDeObjetivo?'row-rojo':'';
    return `
    <tr class="${rowClass}" data-codigo="${esc(f.codigo)}">
      <td class="col-prod"><b>${esc(f.codigo)}</b><span class="prod-nombre">${esc(f.nombre)}</span></td>
      <td class="num">${fmtMoney(f.precioGastronomico)}</td>
      <td class="num">${sinDato?'<span class="badge amarillo">completar en Productos</span>':fmtMoney(f.precioDistribuidor)}</td>
      <td class="num">${fmtPct(f.margenGastronomico)}</td>
      <td class="num" style="${f.fueraDeObjetivo?'color:var(--error);font-weight:700':''}">${sinDato?'—':fmtPct(f.descuentoActual)}</td>
      <td class="num">${sinDato?'—':`<span class="pct-input-wrap"><input type="number" step="0.01" class="descuento-obj-in num-in" value="${(f.descuentoObjetivo*100).toFixed(2)}">%</span>`}</td>
      <td class="num" style="text-align:center;${f.precioSugeridoGastronomico>f.precioGastronomico+1?'color:var(--error);font-weight:700':'color:var(--success)'}">${fmtMoney0(f.precioSugeridoGastronomico)}</td>
      <td class="num" style="text-align:center;${sinDato?'':(f.precioSugeridoDistribuidor>f.precioDistribuidor+1?'color:var(--error);font-weight:700':'color:var(--success)')}">${sinDato?'—':fmtMoney0(f.precioSugeridoDistribuidor)}</td>
      <td class="num">${sinDato?'—':fmtPct(f.margenDistribuidor)}</td>
      <td style="text-align:center">${sinDato?'':'<button class="icon-btn btn-fijar-descuento" title="Fijar objetivo = descuento actual">🎯</button>'}</td>
    </tr>`;
  }).join('');

  return `
    <div class="co-panel">
      <h1>Listas de precios</h1>
      <p class="lede">El precio de distribuidor es un valor propio — no se mueve solo si cambiás el precio gastronómico. El % de descuento actual se marca en rojo cuando se aleja más de 2 puntos del descuento objetivo.</p>
      <div class="grid-cards" style="margin-bottom:18px">
        <div class="card acento"><div class="label">Margen promedio gastronómico</div><div class="value">${fmtPct(promedioGastro)}</div></div>
        <div class="card acento"><div class="label">Margen promedio distribuidor</div><div class="value">${fmtPct(promedioDistrib)}</div><div class="sub">${conPrecio.length} de ${filas.length} productos con precio cargado</div></div>
      </div>
      ${sinCompletar>0?`<div class="alert warn">🟡 ${sinCompletar} producto${sinCompletar>1?'s':''} sin precio de distribuidor todavía.</div>`:''}
      ${fueraDeObjetivo>0?`<div class="alert warn">🔴 ${fueraDeObjetivo} producto${fueraDeObjetivo>1?'s':''} con descuento a más de 2 puntos de su objetivo.</div>`:''}
      <div class="tbl-wrap">
        <table class="tbl-sticky">
          <thead><tr>
            <th class="col-prod">Producto</th><th class="num">Precio gastronómico (c/IVA)</th><th class="num">Precio distribuidor (c/IVA)</th>
            <th class="num">Margen gastronómico</th><th class="num">Descuento actual</th><th class="num">Descuento objetivo</th>
            <th class="center">Precio sugerido gastro. (c/IVA)</th><th class="center">Precio sugerido distrib. (c/IVA)</th>
            <th class="num">Margen distribuidor</th><th></th>
          </tr></thead>
          <tbody id="listaPreciosBody">${rows}</tbody>
        </table>
      </div>
      <footer class="tabfoot">🎯 = fija el descuento objetivo de ese producto en su descuento actual.</footer>
    </div>
  `;
}

function wireListaPrecios(){
  const body = document.getElementById('listaPreciosBody');
  body.addEventListener('change', (e)=>{
    const codigo = e.target.closest('tr').dataset.codigo;
    const input = e.target.closest('.descuento-obj-in');
    if(input){ STATE.descuentoObjetivo[codigo]=leerNumero(input.value)/100; render(); }
  });
  body.addEventListener('click', (e)=>{
    const btn = e.target.closest('.btn-fijar-descuento');
    if(!btn) return;
    const codigo = btn.closest('tr').dataset.codigo;
    const f = calcListaPrecios().find(x=>x.codigo===codigo);
    STATE.descuentoObjetivo[codigo] = f.descuentoActual;
    render();
    showToast('Descuento objetivo de '+codigo+' fijado en '+fmtPct(STATE.descuentoObjetivo[codigo]));
  });
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('.co-nav-btn').forEach(b=>{
    b.addEventListener('click', ()=>activarTab(b.dataset.tab));
  });

  // Importar precios desde Xubio (delegado porque el botón se renderiza en el content)
  document.getElementById('co-content').addEventListener('click', async(e)=>{
    const btn = e.target.closest('#btn-importar-precios');
    if(!btn) return;
    const status = document.getElementById('importar-status');
    btn.disabled=true; btn.innerHTML='<span style="display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:co-spin .7s linear infinite;vertical-align:middle;margin-right:6px"></span>Importando…';
    status.textContent='';
    try {
      const res = await fetch('/api/gestion_gerencial/costeo/importar-precios/', {
        method:'POST', headers:{'X-CSRFToken':csrfToken()},
      });
      const data = await res.json();
      status.textContent = `✅ ${data.actualizados} precios actualizados`;
      showToast(`${data.actualizados} precios importados desde Xubio.`);
      await cargarDatos();
    } catch(ex){
      status.textContent='❌ Error al importar';
      showToast('Error: '+ex.message);
    } finally {
      btn.disabled=false;
      btn.innerHTML='📥 Importar precios desde Xubio';
    }
  });

  cargarDatos();
});

// ============================================================
// RENDER: HISTÓRICO
// ============================================================
let HIST_SUBTAB = 'precios';
let HIST_FILTRO_TIPO = 'todos';
let HIST_FILTRO_TEXTO = '';

function guardarSnapshot(nota){
  const {filas} = calcMatriz();
  const ind = calcIndirectosTotal();
  const rojos = filas.filter(f=>f.estadoClass==='rojo').length;
  const amarillos = filas.filter(f=>f.estadoClass==='amarillo').length;
  const margenProm = filas.length ? filas.reduce((a,f)=>a+f.margenPct,0)/filas.length : 0;
  if(!STATE.historialSnapshots) STATE.historialSnapshots = [];
  STATE.historialSnapshots.unshift({
    fecha: new Date().toISOString(), nota: nota||'',
    resumen: {
      totalProductos: filas.length, totalIndirectos: ind.total,
      sueldosProductivos: STATE.sueldosProductivos, margenPromedio: margenProm,
      productosEnRojo: rojos, productosEnAmarillo: amarillos,
    },
    snapshot: JSON.parse(JSON.stringify({
      productos: STATE.productos, insumos: STATE.insumos, recetas: STATE.recetas,
      manoObra: STATE.manoObra, indirectos: STATE.indirectos, equipos: STATE.equipos,
      margenObjetivo: STATE.margenObjetivo, sueldosProductivos: STATE.sueldosProductivos,
      horasDisponibles: STATE.horasDisponibles,
    })),
  });
}

function renderHistorico(){
  const precios = STATE.historialPrecios || [];
  const snapshots = STATE.historialSnapshots || [];
  return `
    <div class="co-panel">
      <h1>Histórico</h1>
      <p class="lede">Cada vez que cambiás un precio (de producto o de insumo) queda registrado acá solo. Además podés guardar una "foto" completa del costeo cuando quieras, para poder volver a ese momento más adelante.</p>
      <div class="chip-row">
        <div class="chip ${HIST_SUBTAB==='precios'?'active':''}" data-sub="precios">Cambios de precio (${precios.length})</div>
        <div class="chip ${HIST_SUBTAB==='snapshots'?'active':''}" data-sub="snapshots">Fotos guardadas (${snapshots.length})</div>
      </div>
      <div id="histContent">${HIST_SUBTAB==='precios' ? renderHistPrecios(precios) : renderHistSnapshots(snapshots)}</div>
    </div>
  `;
}

function renderHistPrecios(precios){
  const filtros = `
    <div class="filters">
      <div class="chip-row" style="margin-bottom:0" id="histTipoChips">
        <div class="chip ${HIST_FILTRO_TIPO==='todos'?'active':''}" data-tipo="todos">Todos</div>
        <div class="chip ${HIST_FILTRO_TIPO==='producto'?'active':''}" data-tipo="producto">Precio venta</div>
        <div class="chip ${HIST_FILTRO_TIPO==='insumo'?'active':''}" data-tipo="insumo">Insumo</div>
        <div class="chip ${HIST_FILTRO_TIPO==='distribuidor'?'active':''}" data-tipo="distribuidor">Distribuidor</div>
      </div>
      <input type="text" id="histBuscar" placeholder="Buscar producto o insumo…" value="${esc(HIST_FILTRO_TEXTO)}" style="min-width:220px">
      ${(HIST_FILTRO_TIPO!=='todos'||HIST_FILTRO_TEXTO) ? '<button class="btn btn-secondary btn-sm" id="btnLimpiarFiltroHist">Limpiar filtro</button>' : ''}
    </div>
  `;
  const filtrados = precios.filter(h=>{
    if(HIST_FILTRO_TIPO!=='todos' && h.tipo!==HIST_FILTRO_TIPO) return false;
    if(HIST_FILTRO_TEXTO && !h.item.toLowerCase().includes(HIST_FILTRO_TEXTO.toLowerCase())) return false;
    return true;
  });
  if(!precios.length) return filtros + `<div class="empty-state"><div class="big">Todavía no hay cambios de precio registrados</div>Aparecen acá apenas edites un precio en Productos o en Precios insumos.</div>`;
  if(!filtrados.length) return filtros + `<div class="empty-state"><div class="big">Ningún cambio coincide con el filtro</div></div>`;
  return filtros + `
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Fecha</th><th>Tipo</th><th>Ítem</th><th class="num">Antes</th><th class="num">Después</th><th class="num">Variación</th><th></th></tr></thead>
        <tbody>
          ${filtrados.map(h=>{
            const variacion = h.valorAnterior ? (h.valorNuevo-h.valorAnterior)/h.valorAnterior : 0;
            const color = variacion>0 ? 'var(--error)' : (variacion<0 ? 'var(--success)' : 'var(--gray600)');
            return `<tr data-id="${esc(h.id)}">
              <td class="hint">${fmtFecha(h.fecha)}</td>
              <td><span class="badge gris">${h.tipo==='producto'?'Precio venta':(h.tipo==='distribuidor'?'Distribuidor':'Insumo')}</span></td>
              <td>${esc(h.item)}</td>
              <td class="num">${fmtMoney(h.valorAnterior)}</td>
              <td class="num">${fmtMoney(h.valorNuevo)}</td>
              <td class="num" style="color:${color};font-weight:700">${variacion>=0?'+':''}${fmtPct(variacion)}</td>
              <td style="text-align:center"><button class="icon-btn btn-del-precio-hist" title="Eliminar este cambio">🗑</button></td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderHistSnapshots(snapshots){
  const nuevoBtn = `
    <div class="filters">
      <input type="text" id="notaSnapshot" placeholder="Nota (opcional, ej: 'cierre de mes agosto')" style="min-width:280px">
      <button class="btn btn-primary btn-sm" id="btnGuardarSnapshot">📸 Guardar foto ahora</button>
    </div>
  `;
  if(!snapshots.length) return nuevoBtn + `<div class="empty-state"><div class="big">Todavía no guardaste ninguna foto del costeo</div>Usá esto al cerrar cada mes, para poder comparar más adelante.</div>`;
  const rows = snapshots.map((s,i)=>`
    <tr>
      <td class="hint">${fmtFecha(s.fecha)}</td>
      <td>${esc(s.nota)||'<span class="hint">sin nota</span>'}</td>
      <td class="num">${s.resumen.totalProductos}</td>
      <td class="num">${fmtMoney0(s.resumen.totalIndirectos)}</td>
      <td class="num">${fmtMoney0(s.resumen.sueldosProductivos)}</td>
      <td class="num">${fmtPct(s.resumen.margenPromedio)}</td>
      <td class="num">${s.resumen.productosEnRojo}</td>
      <td style="text-align:center">
        <button class="icon-btn btn-restaurar-snap" data-idx="${i}" title="Restaurar este estado">↺</button>
        <button class="icon-btn btn-del-snap" data-idx="${i}" title="Eliminar foto">🗑</button>
      </td>
    </tr>
  `).join('');
  return nuevoBtn + `
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Fecha</th><th>Nota</th><th class="num">Prod.</th><th class="num">Indirectos</th><th class="num">Sueldos</th><th class="num">Margen prom.</th><th class="num">En rojo</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function wireHistorico(){
  document.querySelectorAll('[data-sub]').forEach(chip=>{
    chip.addEventListener('click', ()=>{ HIST_SUBTAB=chip.dataset.sub; render(); });
  });
  const chipsTipo = document.getElementById('histTipoChips');
  if(chipsTipo) chipsTipo.addEventListener('click', (e)=>{
    const chip = e.target.closest('.chip');
    if(!chip) return;
    HIST_FILTRO_TIPO = chip.dataset.tipo;
    render();
  });
  const buscar = document.getElementById('histBuscar');
  if(buscar){
    buscar.addEventListener('input', ()=>{
      HIST_FILTRO_TEXTO = buscar.value;
      render();
      const nuevo = document.getElementById('histBuscar');
      if(nuevo){ nuevo.focus(); nuevo.setSelectionRange(nuevo.value.length, nuevo.value.length); }
    });
  }
  const btnLimpiar = document.getElementById('btnLimpiarFiltroHist');
  if(btnLimpiar) btnLimpiar.addEventListener('click', ()=>{ HIST_FILTRO_TIPO='todos'; HIST_FILTRO_TEXTO=''; render(); });
  document.querySelectorAll('.btn-del-precio-hist').forEach(b=>{
    b.addEventListener('click', ()=>{
      const id = b.closest('tr').dataset.id;
      STATE.historialPrecios = STATE.historialPrecios.filter(h=>h.id!==id);
      render();
      showToast('Cambio eliminado del histórico.');
    });
  });
  const btnSnap = document.getElementById('btnGuardarSnapshot');
  if(btnSnap) btnSnap.addEventListener('click', ()=>{
    const nota = document.getElementById('notaSnapshot').value;
    guardarSnapshot(nota);
    showToast('Foto guardada.');
    render();
  });
  document.querySelectorAll('.btn-restaurar-snap').forEach(b=>{
    b.addEventListener('click', ()=>{
      const idx = Number(b.dataset.idx);
      const snap = STATE.historialSnapshots[idx];
      if(!confirm('¿Restaurar el estado del '+fmtFecha(snap.fecha)+'? Se reemplazan productos, recetas, mano de obra e indirectos actuales.')) return;
      Object.assign(STATE, JSON.parse(JSON.stringify(snap.snapshot)));
      showToast('Estado restaurado.');
      activarTab('resumen');
    });
  });
  document.querySelectorAll('.btn-del-snap').forEach(b=>{
    b.addEventListener('click', ()=>{
      const idx = Number(b.dataset.idx);
      STATE.historialSnapshots.splice(idx,1);
      render();
    });
  });
}