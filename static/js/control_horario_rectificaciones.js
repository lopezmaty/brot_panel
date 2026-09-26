'use strict';
/* =========================================================
   Control Horario — Rectificaciones de fichada (Anexo I)
   y reporte mensual por empleado.
   Las marcas del reloj nunca se modifican: la rectificación
   queda registrada aparte.
========================================================= */
const CHRect = (() => {
  const API = '/api/control_horario/';
  const TIPOS = [
    ['ingreso', 'Ingreso'], ['salida', 'Salida'], ['descanso', 'Descanso'],
    ['falla_tecnica', 'Falla técnica'], ['otro', 'Otro'],
  ];
  const ESTADO_BADGE = {
    pendiente_firma: ['amarillo', 'Pendiente de firma y foto'],
    pendiente_resolucion: ['azul', 'Pendiente de resolución'],
    resuelta: ['verde', 'Resuelta'],
    anulada: ['gris', 'Anulada'],
  };
  const $ = s => document.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const dec = n => (Math.round((Number(n) || 0) * 100) / 100).toFixed(2).replace('.', ',');
  const fechaCorta = iso => { const [y, m, d] = iso.split('-'); return `${d}/${m}/${y}`; };
  // Las fechas vienen del servidor ya en hora local (con su offset): se muestran tal cual
  const fechaHora = iso => (iso ? ${iso.slice(8, 10)}//  : '');
  const dosDig = n => String(n).padStart(2, '0');
  const ahoraLocal = () => { const d = new Date(); return `${d.getFullYear()}-${dosDig(d.getMonth() + 1)}-${dosDig(d.getDate())}T${dosDig(d.getHours())}:${dosDig(d.getMinutes())}`; };
  const empleadosCH = () => (typeof chEmpleados !== 'undefined' ? chEmpleados : []);
  const mesesCH = () => (typeof chMeses !== 'undefined' ? chMeses : []);
  const esAdminCH = () => (typeof ES_ADMIN !== 'undefined' && ES_ADMIN);
  const toast = (msg, icon) => (window.bpToast ? bpToast(msg, icon || 'ti-check') : null);

  async function api(path, opts = {}) {
    const esForm = opts.body instanceof FormData;
    const res = await fetch(API + path, {
      credentials: 'same-origin',
      ...opts,
      headers: { ...(esForm ? {} : { 'Content-Type': 'application/json' }), 'X-CSRFToken': csrfToken(), ...(opts.headers || {}) },
    });
    let data = null;
    try { data = await res.json(); } catch (err) { /* respuesta vacía */ }
    if (!res.ok) throw new Error((data && (data.error || data.detail)) || ('Error ' + res.status));
    return data;
  }

  function badgeEstado(r) {
    if (r.estado === 'resuelta') {
      if (r.resolucion === 'no_acreditada') return '<span class="badge gris">No acreditada</span>';
      return '<span class="badge verde">Corregida</span>';
    }
    const [cls, txt] = ESTADO_BADGE[r.estado] || ['gris', r.estado];
    return `<span class="badge ${cls}">${e(txt)}</span>`;
  }

  function abrir(id) { document.getElementById(id).classList.add('open'); }
  function cerrar(id) { document.getElementById(id).classList.remove('open'); }

  function mostrarError(cont, msg) {
    const box = cont.querySelector('.rect-error');
    if (!box) return alert(msg);
    box.textContent = msg;
    box.style.display = 'block';
    box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function horasDeclaradas(ent, sd, rd, sal, sinDescanso, emp) {
    const h = v => { if (!v) return null; const [a, b] = v.split(':').map(Number); return a + b / 60; };
    const E = h(ent), SD = h(sd), RD = h(rd), S = h(sal);
    if (E === null || S === null) return null;
    let total = ((S - E) % 24 + 24) % 24;
    if (SD !== null && RD !== null) total -= ((RD - SD) % 24 + 24) % 24;
    else if (!sinDescanso && emp && !emp.sin_descuento_descanso && !emp.medio_jornada) total -= 0.5;
    return Math.max(Math.round(total * 100) / 100, 0);
  }

  function fueraDeTermino(fechaIso, avisoLocal) {
    if (!fechaIso || !avisoLocal) return false;
    const limite = new Date(fechaIso + 'T23:59:59');
    limite.setHours(limite.getHours() + 48);
    return new Date(avisoLocal) > limite;
  }

  async function refrescarPantallas() {
    actualizarBadge();
    const activa = document.querySelector('.ch-tab.active');
    if (activa && activa.id === 'ch-tab-detalle' && typeof renderDetalle === 'function') await renderDetalle();
    if (activa && activa.id === 'ch-tab-rectificaciones') await renderLista();
    if (activa && activa.id === 'ch-tab-resumen' && typeof renderResumen === 'function') await renderResumen();
  }

  /* ─────────────────────────────────────────────
     PASO 1 · Solicitud (declaración del empleado)
  ───────────────────────────────────────────── */
  async function abrirSolicitud(nombre, fecha) {
    const body = $('#chRectSolicitudBody');
    const libre = !nombre || !fecha;
    const empOpts = empleadosCH().map(x => `<option value="${e(x.nombre)}" ${x.nombre === nombre ? 'selected' : ''}>${e(x.nombre_display)}</option>`).join('');
    body.innerHTML = `
      <div class="rect-steps">
        <div class="rect-step cur"><b>1. Declaración</b>Datos que informa el empleado</div>
        <div class="rect-step"><b>2. Firma y foto</b>Se imprime, firman y se sube</div>
        <div class="rect-step"><b>3. Resolución</b>Verificación del encargado</div>
      </div>
      <div class="rect-grid">
        <div><label class="field-label">Empleado</label>
          ${libre ? `<select id="rsEmp"><option value="">Elegí…</option>${empOpts}</select>` : `<input type="text" value="${e((empleadosCH().find(x => x.nombre === nombre) || {}).nombre_display || nombre)}" disabled><input type="hidden" id="rsEmp" value="${e(nombre)}">`}
        </div>
        <div><label class="field-label">Fecha de la incidencia</label>
          <input type="date" id="rsFecha" value="${e(fecha || '')}" ${libre ? '' : 'disabled'} max="${ahoraLocal().slice(0, 10)}">
        </div>
      </div>
      <div id="rsResto" style="margin-top:14px">${libre ? '<p class="hint">Elegí el empleado y la fecha para ver sus marcas.</p>' : '<p class="hint">Cargando marcas del día…</p>'}</div>`;
    abrir('chRectSolicitud');

    const cargar = async () => {
      const emp = $('#rsEmp').value, f = $('#rsFecha').value;
      if (!emp || !f) return;
      $('#rsResto').innerHTML = '<p class="hint">Cargando marcas del día…</p>';
      try {
        const datos = await api(`rectificaciones/datos-dia/?empleado=${encodeURIComponent(emp)}&fecha=${f}`);
        if (datos.rectificacion_existente) {
          cerrar('chRectSolicitud');
          toast(`Ese día ya tiene la rectificación N° ${datos.rectificacion_existente.numero}`, 'ti-info-circle');
          abrirGestion(datos.rectificacion_existente.id);
          return;
        }
        pintarFormulario(datos, f);
      } catch (err) { $('#rsResto').innerHTML = `<div class="alerta-card">${e(err.message)}</div>`; }
    };
    if (libre) { $('#rsEmp').addEventListener('change', cargar); $('#rsFecha').addEventListener('change', cargar); }
    else cargar();
  }

  function pintarFormulario(datos, fecha) {
    const m = datos.marcas.filter(Boolean);
    // Precarga del horario real: se sugieren las marcas existentes
    const sug = { ent: '', sd: '', rd: '', sal: '' };
    if (m.length >= 1) sug.ent = m[0].slice(0, 5);
    if (m.length === 2) sug.sal = m[1].slice(0, 5);
    if (m.length >= 4) { sug.sd = m[1].slice(0, 5); sug.rd = m[2].slice(0, 5); sug.sal = m[3].slice(0, 5); }
    if (m.length === 3) { sug.sd = m[1].slice(0, 5); sug.rd = m[2].slice(0, 5); }

    $('#rsResto').innerHTML = `
      <div class="rect-info">
        <div><b>Marcas originales del reloj:</b> ${e(datos.marcas_originales)}</div>
        <div><b>Cálculo provisional del sistema:</b> ${e(datos.calculo_provisional)}</div>
        ${datos.mes_cerrado ? '<div style="margin-top:6px;color:var(--error)"><b>El mes está cerrado.</b> Podés registrar la solicitud, pero para autorizar la corrección un administrador va a tener que abrir el mes.</div>' : ''}
      </div>
      <div class="rect-grid">
        <div><label class="field-label">DNI</label><input type="text" id="rsDni" value="${e(datos.dni)}" placeholder="Ej: 30.123.456"></div>
        <div><label class="field-label">Sector / turno</label><input type="text" id="rsSector" value="${e(datos.sector_turno)}" placeholder="Ej: Producción - turno mañana"></div>
        <div class="full"><label class="field-label">Tipo de incidencia</label>
          <div class="rect-checks">${TIPOS.map(([v, l]) => `<label><input type="checkbox" name="rsTipo" value="${v}"> ${l}</label>`).join('')}</div>
          <input type="text" id="rsTipoOtro" placeholder="¿Cuál? (si elegiste Otro)" style="display:none;margin-top:6px">
        </div>
        <div class="full"><label class="field-label">Horario real informado por el empleado</label>
          <div class="rect-times">
            <div><span class="hint">Entrada</span><input type="time" id="rsEnt" value="${sug.ent}"></div>
            <div><span class="hint">Salida a descanso</span><input type="time" id="rsSd" value="${sug.sd}"></div>
            <div><span class="hint">Regreso de descanso</span><input type="time" id="rsRd" value="${sug.rd}"></div>
            <div><span class="hint">Salida final</span><input type="time" id="rsSal" value="${sug.sal}"></div>
          </div>
          <label style="display:flex;gap:6px;align-items:center;margin-top:8px;font-size:13px;cursor:pointer"><input type="checkbox" id="rsSinDesc"> No pudo tomar el descanso (no se descuentan los 30 min)</label>
          <div style="margin-top:8px;font-size:13px">Horas que surgen del horario declarado: <span class="rect-horas" id="rsHoras">—</span>
            <span class="hint">(el sistema calculó ${dec(datos.horas_provisionales)} h)</span></div>
        </div>
        <div class="full"><label class="field-label">Aclaración del horario (opcional)</label><input type="text" id="rsHorarioTxt" placeholder="Ej: se quedó hasta las 15 por una entrega"></div>
        <div class="full"><label class="field-label">Motivo de la incidencia *</label><textarea id="rsMotivo" placeholder="Ej: Olvido de realizar la marcación de salida al finalizar la jornada."></textarea></div>
        <div><label class="field-label">Fecha y hora del aviso</label><input type="datetime-local" id="rsAviso" value="${ahoraLocal()}"></div>
        <div><label class="field-label">Medio utilizado para avisar</label><input type="text" id="rsMedio" value="Formulario entregado al responsable designado."></div>
        <div class="full" id="rsTermino"></div>
      </div>
      <div class="alerta-card rect-error"></div>
      <div class="rect-actions">
        <button class="btn btn-secondary" id="rsCancelar">Cancelar</button>
        <button class="btn btn-primary" id="rsGuardar">🖨 Generar formulario para imprimir</button>
      </div>`;

    const emp = { medio_jornada: datos.medio_jornada, sin_descuento_descanso: datos.sin_descuento_descanso };
    const recalcular = () => {
      const h = horasDeclaradas($('#rsEnt').value, $('#rsSd').value, $('#rsRd').value, $('#rsSal').value, $('#rsSinDesc').checked, emp);
      $('#rsHoras').textContent = h === null ? '—' : dec(h) + ' h';
      $('#rsTermino').innerHTML = fueraDeTermino(fecha, $('#rsAviso').value)
        ? '<div class="alerta-card" style="margin:0">⚠ El aviso es posterior a las 48 h de la incidencia: va a quedar registrado como <b>fuera de término</b> (Reglamento §7). Igual se puede tramitar.</div>' : '';
    };
    ['#rsEnt', '#rsSd', '#rsRd', '#rsSal', '#rsSinDesc', '#rsAviso'].forEach(s => $(s).addEventListener('input', recalcular));
    $$('input[name=rsTipo]').forEach(c => c.addEventListener('change', () => {
      $('#rsTipoOtro').style.display = $('input[name=rsTipo][value=otro]').checked ? 'block' : 'none';
      if (c.value === 'descanso' && c.checked && !$('#rsSinDesc').checked && !$('#rsSd').value) recalcular();
    }));
    recalcular();
    $('#rsCancelar').addEventListener('click', () => cerrar('chRectSolicitud'));
    $('#rsGuardar').addEventListener('click', () => guardarSolicitud(fecha));
  }

  async function guardarSolicitud(fecha) {
    const body = $('#chRectSolicitudBody');
    const btn = $('#rsGuardar');
    const payload = {
      empleado: $('#rsEmp').value,
      fecha,
      dni: $('#rsDni').value,
      sector_turno: $('#rsSector').value,
      tipos: $$('input[name=rsTipo]:checked').map(c => c.value),
      tipo_otro: $('#rsTipoOtro').value,
      real_entrada: $('#rsEnt').value,
      real_salida_descanso: $('#rsSd').value,
      real_regreso_descanso: $('#rsRd').value,
      real_salida: $('#rsSal').value,
      sin_descanso_declarado: $('#rsSinDesc').checked,
      horario_real_texto: $('#rsHorarioTxt').value,
      motivo: $('#rsMotivo').value,
      fecha_hora_aviso: $('#rsAviso').value,
      medio_aviso: $('#rsMedio').value,
    };
    if (!payload.tipos.length) return mostrarError(body, 'Elegí al menos un tipo de incidencia.');
    if (!payload.motivo.trim()) return mostrarError(body, 'Completá el motivo de la incidencia.');
    btn.disabled = true; btn.textContent = 'Generando…';
    try {
      const r = await api('rectificaciones/', { method: 'POST', body: JSON.stringify(payload) });
      body.innerHTML = `
        <div class="rect-steps">
          <div class="rect-step done"><b>1. Declaración ✓</b>Registrada como N° ${e(r.numero)}</div>
          <div class="rect-step cur"><b>2. Firma y foto</b>Imprimí y hacé firmar</div>
          <div class="rect-step"><b>3. Resolución</b>Después de subir la foto</div>
        </div>
        <div class="alerta-card ok">La solicitud <b>N° ${e(r.numero)}</b> de <b>${e(r.empleado_display)}</b> para el ${fechaCorta(r.fecha)} quedó registrada${r.fuera_de_termino ? ' (aviso <b>fuera de término</b>)' : ''}.</div>
        <ol style="font-size:13.5px;line-height:1.8;padding-left:18px;margin:8px 0 0">
          <li>Imprimí el formulario (Anexo I) y que el empleado lo firme.</li>
          <li>El encargado completa la verificación interna y firma.</li>
          <li>Sacale una foto y subila acá: el sistema te va a pedir la resolución.</li>
        </ol>
        <div class="rect-actions">
          <button class="btn btn-secondary" id="rsListo">Listo, lo subo después</button>
          <a class="btn btn-secondary" href="${e(r.pdf_url)}" target="_blank" rel="noopener">🖨 Imprimir formulario</a>
          <button class="btn btn-primary" id="rsSubirAhora">📷 Ya está firmado: subir foto</button>
        </div>`;
      $('#rsListo').addEventListener('click', () => cerrar('chRectSolicitud'));
      $('#rsSubirAhora').addEventListener('click', () => { cerrar('chRectSolicitud'); abrirGestion(r.id); });
      toast(`Rectificación N° ${r.numero} registrada`, 'ti-file-plus');
      refrescarPantallas();
    } catch (err) {
      mostrarError(body, err.message);
      btn.disabled = false; btn.textContent = '🖨 Generar formulario para imprimir';
    }
  }

  /* ─────────────────────────────────────────────
     PASOS 2 y 3 · Foto firmada y resolución
  ───────────────────────────────────────────── */
  async function abrirGestion(id) {
    const body = $('#chRectGestionBody');
    body.innerHTML = '<p class="hint">Cargando…</p>';
    abrir('chRectGestion');
    try { pintarGestion(await api(`rectificaciones/${id}/`)); }
    catch (err) { body.innerHTML = `<div class="alerta-card">${e(err.message)}</div><div class="rect-actions"><button class="btn btn-secondary" onclick="document.getElementById('chRectGestion').classList.remove('open')">Cerrar</button></div>`; }
  }

  function parte1(r) {
    const horario = [
      r.real_entrada && `Entrada ${r.real_entrada}`,
      (r.real_salida_descanso || r.real_regreso_descanso) && `Descanso ${r.real_salida_descanso || '—'} a ${r.real_regreso_descanso || '—'}`,
      r.real_salida && `Salida ${r.real_salida}`,
    ].filter(Boolean).join(' · ');
    return `
      <dl class="rect-dl">
        <dt>Trabajador/a</dt><dd>${e(r.empleado_display)}${r.dni ? ' · DNI ' + e(r.dni) : ''}${r.sector_turno ? ' · ' + e(r.sector_turno) : ''}</dd>
        <dt>Tipo de incidencia</dt><dd>${e(r.tipos_label.join(', '))}${r.tipo_otro ? ': ' + e(r.tipo_otro) : ''}</dd>
        <dt>Marcas originales</dt><dd>${e(r.marcas_originales)}</dd>
        <dt>Cálculo provisional</dt><dd>${e(r.calculo_provisional)}</dd>
        <dt>Horario real informado</dt><dd>${e(horario || '—')}${r.sin_descanso_declarado ? ' · <b>no pudo tomar el descanso</b>' : ''}${r.horas_declaradas !== null ? ` <span class="hint">(${dec(r.horas_declaradas)} h)</span>` : ''}${r.horario_real_texto ? '<br>' + e(r.horario_real_texto) : ''}</dd>
        <dt>Motivo</dt><dd>${e(r.motivo)}</dd>
        <dt>Aviso</dt><dd>${e(r.fecha_hora_aviso.replace('T', ' '))} · ${e(r.medio_aviso)} ${r.fuera_de_termino ? '<span class="badge rojo">Fuera de término</span>' : ''}</dd>
        <dt>Cargada por</dt><dd>${e(r.creada_por || '—')}</dd>
      </dl>`;
  }

  function bloqueFoto(r) {
    if (!r.tiene_foto) return '';
    return `<div class="rect-foto">
      ${r.foto_es_pdf ? `<a class="btn btn-secondary btn-sm" href="${e(r.foto_url)}" target="_blank" rel="noopener">📄 Ver formulario firmado (PDF)</a>`
        : `<a href="${e(r.foto_url)}" target="_blank" rel="noopener" title="Ver en grande"><img src="${e(r.foto_url)}" alt="Formulario firmado"></a>`}
      <div class="hint">Formulario firmado subido el ${fechaHora(r.foto_subida_el)}.</div>
    </div>`;
  }

  function sn(v) { return v === true ? 'Sí' : v === false ? 'No' : '—'; }

  function parte2Resumen(r) {
    const cam = { si: 'Sí', no: 'No', no_disponibles: 'No disponibles' }[r.verif_camaras] || '—';
    return `
      <dl class="rect-dl">
        <dt>Verificación</dt><dd>Biométrico: ${sn(r.verif_biometrico)} · Horario programado: ${sn(r.verif_horario_programado)} · Cámaras: ${cam} · Registros: ${sn(r.verif_registros)} · Supervisor/testigos: ${sn(r.verif_supervisor)}</dd>
        ${r.verif_otros ? `<dt>Otros elementos</dt><dd>${e(r.verif_otros)}</dd>` : ''}
        <dt>Resolución</dt><dd><b>${e(r.resolucion_label)}</b></dd>
        ${r.horario_corregido ? `<dt>Horario corregido</dt><dd>${e(r.horario_corregido)}</dd>` : ''}
        <dt>Horas a liquidar ese día</dt><dd>${r.horas_a_liquidar !== null ? `<span class="rect-horas">${dec(r.horas_a_liquidar)} h</span> <span class="hint">(${r.impacto_horas > 0 ? '+' : ''}${dec(r.impacto_horas)} h vs. el cálculo del sistema de ${dec(r.horas_provisionales)} h)</span>` : `Sin cambios: se mantienen ${dec(r.horas_provisionales)} h`}</dd>
        ${r.observaciones ? `<dt>Observaciones</dt><dd>${e(r.observaciones)}</dd>` : ''}
        <dt>Aprobó</dt><dd>${e(r.aprobado_por)} · cargado por ${e(r.resuelta_por)} el ${fechaHora(r.resuelta_el).slice(0, 10)}</dd>
      </dl>`;
  }

  function formularioResolucion(r) {
    const opSN = n => `<select id="${n}"><option value="">—</option><option value="si">Sí</option><option value="no">No</option></select>`;
    const sugHorario = [r.real_entrada && `Entrada ${r.real_entrada}`, r.real_salida_descanso && `Descanso ${r.real_salida_descanso} a ${r.real_regreso_descanso || '—'}`, r.real_salida && `Salida ${r.real_salida}`].filter(Boolean).join(' · ');
    const sugHoras = r.horas_declaradas !== null ? r.horas_declaradas : r.horas_provisionales;
    return `
      <div class="rect-sub">3. Verificación interna y resolución <span class="hint">(pasá lo que completó y firmó el encargado)</span></div>
      <div class="rect-grid">
        <div><label class="field-label">Registro biométrico revisado</label>${opSN('rrBio')}</div>
        <div><label class="field-label">Horario programado revisado</label>${opSN('rrHor')}</div>
        <div><label class="field-label">Cámaras disponibles y pertinentes</label><select id="rrCam"><option value="">—</option><option value="si">Sí</option><option value="no">No</option><option value="no_disponibles">No disponibles</option></select></div>
        <div><label class="field-label">Registros de producción o acceso</label>${opSN('rrReg')}</div>
        <div><label class="field-label">Supervisor / testigos</label>${opSN('rrSup')}</div>
        <div class="full"><label class="field-label">Otros elementos</label><textarea id="rrOtros" placeholder="Ej: Cámaras y supervisor confirman que permaneció en tareas hasta las 15:00."></textarea></div>
        <div class="full"><label class="field-label">Resolución *</label>
          <div class="rect-checks" style="flex-direction:column;gap:8px">
            <label><input type="radio" name="rrRes" value="acreditada"> Incidencia acreditada: se autoriza corrección excepcional</label>
            <label><input type="radio" name="rrRes" value="parcial"> Parcialmente acreditada: se autoriza por el horario comprobado</label>
            <label><input type="radio" name="rrRes" value="no_acreditada"> No acreditada: se mantiene el cálculo del sistema</label>
          </div>
        </div>
        <div class="rr-corr"><label class="field-label">Horario corregido *</label><input type="text" id="rrHorario" value="${e(sugHorario)}"></div>
        <div class="rr-corr"><label class="field-label">Horas a liquidar ese día *</label><input type="number" id="rrHoras" step="0.01" min="0" max="24" value="${sugHoras}">
          <div class="hint" id="rrImpacto"></div></div>
        <div><label class="field-label">Aprobó (responsable que firmó) *</label><input type="text" id="rrAprobo" placeholder="Nombre y cargo"></div>
        <div class="full"><label class="field-label">Observaciones / fundamentos</label><textarea id="rrObs"></textarea></div>
      </div>
      <div class="alerta-card rect-error"></div>`;
  }

  function pintarGestion(r) {
    const body = $('#chRectGestionBody');
    const paso2 = r.tiene_foto, paso3 = r.estado === 'resuelta';
    const puedeResolver = esAdminCH() && r.estado === 'pendiente_resolucion';
    body.innerHTML = `
      <h2 class="modal-title" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">Rectificación N° ${e(r.numero)} ${badgeEstado(r)}</h2>
      <p class="hint" style="margin:-10px 0 14px">${e(r.empleado_display)} · ${fechaCorta(r.fecha)}</p>
      ${r.estado === 'anulada' ? `<div class="alerta-card">Anulada: ${e(r.motivo_anulacion)}</div>` : `
      <div class="rect-steps">
        <div class="rect-step done"><b>1. Declaración ✓</b>Cargada</div>
        <div class="rect-step ${paso2 ? 'done' : 'cur'}"><b>2. Firma y foto ${paso2 ? '✓' : ''}</b>${paso2 ? 'Foto subida' : 'Falta subir la foto'}</div>
        <div class="rect-step ${paso3 ? 'done' : (paso2 ? 'cur' : '')}"><b>3. Resolución ${paso3 ? '✓' : ''}</b>${paso3 ? 'Resuelta' : 'Pendiente'}</div>
      </div>`}
      ${parte1(r)}
      ${r.estado === 'pendiente_firma' ? `
        <div class="rect-sub">2. Subí la foto del formulario firmado</div>
        <p class="section-help" style="margin-bottom:10px">Tiene que tener la firma del empleado y la verificación firmada por el encargado. Podés sacar la foto con el celular o subir un PDF escaneado.</p>
        <div class="row"><input type="file" id="rgFoto" accept="image/*,application/pdf"><button class="btn btn-primary" id="rgSubir">📷 Subir foto</button></div>
        <div class="alerta-card rect-error"></div>` : ''}
      ${paso2 && r.estado !== 'pendiente_firma' ? `<div class="rect-sub">Formulario firmado</div>${bloqueFoto(r)}` : ''}
      ${puedeResolver ? formularioResolucion(r) : ''}
      ${r.estado === 'pendiente_resolucion' && !esAdminCH() ? '<div class="alerta-card info" style="margin-top:12px">Falta que un administrador cargue la verificación y la resolución.</div>' : ''}
      ${paso3 ? `<div class="rect-sub">Verificación y resolución</div>${parte2Resumen(r)}` : ''}
      <div id="rgAnular" style="display:none;margin-top:14px" class="liq-form">
        <label class="field-label">Motivo de la anulación (queda registrado)</label>
        <input type="text" id="rgMotivoAnul" placeholder="Ej: se cargó por error / el empleado desistió">
        <div class="rect-actions" style="margin-top:10px;padding-top:10px"><button class="btn btn-secondary btn-sm" id="rgAnulCancel">Volver</button><button class="btn btn-danger btn-sm" id="rgAnulOk">Anular rectificación</button></div>
      </div>
      <div class="rect-actions">
        ${esAdminCH() && r.estado !== 'anulada' ? '<button class="btn btn-danger btn-sm" id="rgAnularBtn" style="margin-right:auto">Anular</button>' : ''}
        <button class="btn btn-secondary" id="rgCerrar">Cerrar</button>
        <a class="btn btn-secondary" href="${e(r.pdf_url)}" target="_blank" rel="noopener">🖨 ${paso3 ? 'Anexo I completo' : 'Imprimir Anexo I'}</a>
        ${puedeResolver ? '<button class="btn btn-primary" id="rgResolver">Guardar resolución</button>' : ''}
      </div>`;

    $('#rgCerrar').addEventListener('click', () => cerrar('chRectGestion'));
    const anularBtn = $('#rgAnularBtn');
    if (anularBtn) {
      anularBtn.addEventListener('click', () => { $('#rgAnular').style.display = 'block'; $('#rgMotivoAnul').focus(); });
      $('#rgAnulCancel').addEventListener('click', () => { $('#rgAnular').style.display = 'none'; });
      $('#rgAnulOk').addEventListener('click', async () => {
        try {
          const res = await api(`rectificaciones/${r.id}/anular/`, { method: 'POST', body: JSON.stringify({ motivo: $('#rgMotivoAnul').value }) });
          toast(`Rectificación N° ${res.numero} anulada`, 'ti-ban');
          pintarGestion(res); refrescarPantallas();
        } catch (err) { alert(err.message); }
      });
    }

    const subir = $('#rgSubir');
    if (subir) subir.addEventListener('click', async () => {
      const f = $('#rgFoto').files[0];
      if (!f) return mostrarError(body, 'Elegí la foto del formulario firmado.');
      const fd = new FormData(); fd.append('foto', f);
      subir.disabled = true; subir.textContent = 'Subiendo…';
      try {
        const res = await api(`rectificaciones/${r.id}/foto/`, { method: 'POST', body: fd });
        toast('Foto subida. Completá la resolución.', 'ti-photo-check');
        pintarGestion(res); refrescarPantallas();
        const primer = $('#rrBio'); if (primer) primer.scrollIntoView({ block: 'center', behavior: 'smooth' });
      } catch (err) { mostrarError(body, err.message); subir.disabled = false; subir.textContent = '📷 Subir foto'; }
    });

    const resolver = $('#rgResolver');
    if (resolver) {
      const actualizar = () => {
        const val = ($('input[name=rrRes]:checked') || {}).value;
        $$('.rr-corr', body).forEach(x => { x.style.display = val === 'no_acreditada' ? 'none' : ''; });
        const h = Number($('#rrHoras').value);
        const dif = Math.round((h - r.horas_provisionales) * 100) / 100;
        $('#rrImpacto').textContent = isNaN(h) ? '' : `${dif > 0 ? '+' : ''}${dec(dif)} h respecto del cálculo del sistema (${dec(r.horas_provisionales)} h)`;
      };
      $$('input[name=rrRes]').forEach(x => x.addEventListener('change', actualizar));
      $('#rrHoras').addEventListener('input', actualizar);
      actualizar();
      resolver.addEventListener('click', async () => {
        const payload = {
          verif_biometrico: $('#rrBio').value, verif_horario_programado: $('#rrHor').value, verif_camaras: $('#rrCam').value,
          verif_registros: $('#rrReg').value, verif_supervisor: $('#rrSup').value, verif_otros: $('#rrOtros').value,
          resolucion: ($('input[name=rrRes]:checked') || {}).value, horario_corregido: $('#rrHorario').value,
          horas_a_liquidar: $('#rrHoras').value, aprobado_por: $('#rrAprobo').value, observaciones: $('#rrObs').value,
        };
        if (!payload.resolucion) return mostrarError(body, 'Elegí la resolución.');
        resolver.disabled = true; resolver.textContent = 'Guardando…';
        try {
          const res = await api(`rectificaciones/${r.id}/resolver/`, { method: 'POST', body: JSON.stringify(payload) });
          toast(res.resolucion === 'no_acreditada' ? 'Resolución guardada: no acreditada' : `Corrección autorizada: ${dec(res.horas_a_liquidar)} h`, 'ti-circle-check');
          pintarGestion(res); refrescarPantallas();
        } catch (err) { mostrarError(body, err.message); resolver.disabled = false; resolver.textContent = 'Guardar resolución'; }
      });
    }
  }

  /* ─────────────────────────────────────────────
     Integración con "Detalle diario"
  ───────────────────────────────────────────── */
  function celdaDetalle(row) {
    const r = row.rectificacion;
    if (r) return `<button class="btn btn-secondary btn-rect" data-rect-ver="${r.id}" title="Ver rectificación N° ${e(r.numero)}">${badgeEstado(r)}</button>`;
    return `<button class="btn btn-secondary btn-rect" data-rect-solicitar data-nombre="${e(row.nombre_raw)}" data-fecha="${e(row.fecha)}" title="El empleado informa un olvido o error de fichada">✎ Solicitar</button>`;
  }

  function celdaLiquidar(row) {
    const corregido = row.a_liquidar_sistema !== undefined && row.rectificacion && row.rectificacion.estado === 'resuelta' && row.rectificacion.resolucion !== 'no_acreditada';
    return `<td style="text-align:right;font-weight:700" data-export="${dec(row.a_liquidar)} h">${dec(row.a_liquidar)} h${corregido ? `<span class="liq-tachado" title="Cálculo original del sistema">${dec(row.a_liquidar_sistema)} h</span>` : ''}</td>`;
  }

  /* ─────────────────────────────────────────────
     Pestaña "Rectificaciones"
  ───────────────────────────────────────────── */
  async function renderLista() {
    const cont = $('#chRectContainer');
    const mes = $('#chRectFiltroMes').value, estado = $('#chRectFiltroEstado').value, emp = $('#chRectFiltroEmp').value;
    cont.innerHTML = '<p class="hint">Cargando…</p>';
    try {
      let url = 'rectificaciones/?';
      if (mes) url += 'mes=' + mes + '&';
      if (emp) url += 'empleado=' + encodeURIComponent(emp) + '&';
      const todas = await api(url);
      const lista = estado ? todas.filter(r => r.estado === estado) : todas;
      const n = s => todas.filter(r => r.estado === s).length;
      $('#chRectKpis').innerHTML = `
        <div class="card"><div class="label">Pendientes de firma y foto</div><div class="value">${n('pendiente_firma')}</div></div>
        <div class="card"><div class="label">Pendientes de resolución</div><div class="value">${n('pendiente_resolucion')}</div></div>
        <div class="card"><div class="label">Corregidas</div><div class="value">${todas.filter(r => r.estado === 'resuelta' && r.resolucion !== 'no_acreditada').length}</div></div>
        <div class="card"><div class="label">No acreditadas / anuladas</div><div class="value">${todas.filter(r => r.resolucion === 'no_acreditada').length} / ${n('anulada')}</div></div>`;
      if (!lista.length) { cont.innerHTML = emptyState('No hay rectificaciones para este filtro.'); return; }
      cont.innerHTML = `<div class="table-scroll"><table><thead><tr>
          <th>N°</th><th>Empleado</th><th>Fecha</th><th>Tipo</th><th>Aviso</th><th>Estado</th><th style="text-align:right">Horas</th><th></th>
        </tr></thead><tbody>${lista.map(r => `
          <tr>
            <td>${e(r.numero)}</td>
            <td class="nombre-cell">${e(r.empleado_display)}</td>
            <td>${fechaCorta(r.fecha)}</td>
            <td class="nombre-cell" style="font-size:12px">${e(r.tipos_label.join(', '))}</td>
            <td>${e(r.fecha_hora_aviso.slice(8, 10) + '/' + r.fecha_hora_aviso.slice(5, 7) + ' ' + r.fecha_hora_aviso.slice(11))}${r.fuera_de_termino ? ' <span class="badge rojo">Fuera de término</span>' : ''}</td>
            <td>${badgeEstado(r)}</td>
            <td style="text-align:right">${r.horas_a_liquidar !== null ? dec(r.horas_a_liquidar) + ' h' : '—'}</td>
            <td><button class="btn btn-secondary btn-rect" data-rect-ver="${r.id}">${r.estado === 'pendiente_firma' ? '📷 Subir foto' : r.estado === 'pendiente_resolucion' ? '✔ Resolver' : 'Ver'}</button></td>
          </tr>`).join('')}</tbody></table></div>`;
    } catch (err) { cont.innerHTML = `<div class="alerta-card">Error: ${e(err.message)}</div>`; }
  }

  async function actualizarBadge() {
    try {
      const [a, b] = await Promise.all([api('rectificaciones/?estado=pendiente_firma'), api('rectificaciones/?estado=pendiente_resolucion')]);
      const n = a.length + b.length;
      const badge = $('#chRectBadge');
      if (badge) { badge.hidden = !n; badge.textContent = n; }
    } catch (err) { /* sin permisos o sin conexión: no mostrar */ }
  }

  /* ─────────────────────────────────────────────
     Reporte mensual por empleado (PDF)
  ───────────────────────────────────────────── */
  function urlReporte(nombre, mes) {
    return `${API}reporte-mensual/?empleado=${encodeURIComponent(nombre)}&mes=${encodeURIComponent(mes)}`;
  }
  function botonReporte(nombre, mes) {
    return `<a class="btn btn-secondary btn-rect" href="${urlReporte(nombre, mes)}" target="_blank" rel="noopener" title="Reporte mensual para entregar al empleado">⤓ PDF</a>`;
  }
  function celdaIncidencias(n, limite) {
    n = n || 0;
    if (!n) return '<span class="hint">0</span>';
    const cls = limite && n >= limite ? 'rojo' : 'amarillo';
    return `<span class="badge ${cls}" title="${limite && n >= limite ? 'Alcanzó el límite: evaluar apercibimiento' : 'Rectificaciones del mes'}">${n}${limite ? ' / ' + limite : ''}</span>`;
  }

  /* ─────────────────────────────────────────────
     Arranque
  ───────────────────────────────────────────── */
  function poblarFiltros() {
    const meses = mesesCH().map(m => `<option value="${m.mes}">${labelMes(m.mes)}</option>`).join('');
    $('#chRectFiltroMes').innerHTML = '<option value="">Todos</option>' + meses;
    $('#chRectFiltroEmp').innerHTML = '<option value="">Todos</option>' + empleadosCH().map(x => `<option value="${e(x.nombre)}">${e(x.nombre_display)}</option>`).join('');
  }

  async function init() {
    poblarFiltros();
    actualizarBadge();
    ['#chRectFiltroMes', '#chRectFiltroEstado', '#chRectFiltroEmp'].forEach(s => $(s).addEventListener('change', renderLista));

    document.addEventListener('click', ev => {
      const sol = ev.target.closest('[data-rect-solicitar]');
      if (sol) { ev.preventDefault(); abrirSolicitud(sol.dataset.nombre, sol.dataset.fecha); return; }
      const ver = ev.target.closest('[data-rect-ver]');
      if (ver) { ev.preventDefault(); abrirGestion(ver.dataset.rectVer); }
    });
    ['chRectSolicitud', 'chRectGestion'].forEach(id => {
      document.getElementById(id).addEventListener('click', ev => { if (ev.target.id === id) cerrar(id); });
    });
    document.addEventListener('keydown', ev => { if (ev.key === 'Escape') { cerrar('chRectSolicitud'); cerrar('chRectGestion'); } });

    $('#chBtnRectSinMarcas').addEventListener('click', () => abrirSolicitud(null, null));
    $('#chBtnReporteDetalle').addEventListener('click', () => {
      const emp = $('#chFiltroEmpDetalle').value, mes = $('#chFiltroMesDetalle').value;
      if (!emp) return alert('Elegí un empleado en el filtro para descargar su reporte mensual.');
      window.open(urlReporte(emp, mes), '_blank', 'noopener');
    });

    const lim = $('#chLimiteIncidencias');
    if (lim) {
      try { lim.value = (await api('config/')).limite_incidencias_mes; } catch (err) { /* nada */ }
      $('#chBtnGuardarLimite').addEventListener('click', async () => {
        try {
          const res = await api('config/', { method: 'POST', body: JSON.stringify({ limite_incidencias_mes: lim.value }) });
          lim.value = res.limite_incidencias_mes;
          toast(`Límite guardado: ${res.limite_incidencias_mes} rectificaciones por mes`);
        } catch (err) { alert(err.message); }
      });
    }
  }

  return { init, abrirSolicitud, abrirGestion, renderLista, celdaDetalle, celdaLiquidar, botonReporte, celdaIncidencias, actualizarBadge, poblarFiltros };
})();
