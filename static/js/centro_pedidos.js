document.querySelectorAll('.btn-expandir').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const pedidoId = boton.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);
    const icono = boton.querySelector('i');
    if (filaDetalle.style.display === 'none') {
      filaDetalle.style.display = 'table-row';
      icono.className = 'ti ti-chevron-down';
    } else {
      filaDetalle.style.display = 'none';
      icono.className = 'ti ti-chevron-right';
    }
  });
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function cambiarEstado(pedidoId, nuevoEstado, observaciones = null) {
  const body = { estado: nuevoEstado };
  if (observaciones !== null) body.observaciones = observaciones;

  const response = await fetch(`/api/sistema_pedidos/pedidos/${pedidoId}/`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify(body)
  });

  if (response.ok) {
    location.reload();
  } else {
    alert('No se pudo actualizar el estado');
  }
}

function confirmarAccion(mensaje) {
  return new Promise((resolve) => {
    resolve(window.confirm(mensaje));
  });
}

function toggleDesplegable(botonId, desplegableId) {
  const boton = document.getElementById(botonId);
  const desplegable = document.getElementById(desplegableId);
  boton.addEventListener('click', function (evento) {
    evento.stopPropagation();
    const yaEstaAbierto = desplegable.classList.contains('open');
    document.querySelectorAll('.filtro-desplegable').forEach(function (d) { d.classList.remove('open'); });
    document.querySelectorAll('.filtro-icono-btn').forEach(function (b) { b.classList.remove('activo'); });
    if (!yaEstaAbierto) {
      desplegable.classList.add('open');
      boton.classList.add('activo');
    }
  });
}

toggleDesplegable('btnFiltroFecha', 'desplegableFecha');
toggleDesplegable('btnFiltroEstado', 'desplegableEstado');
toggleDesplegable('btnFiltroEntrega', 'desplegableEntrega');

document.addEventListener('click', function (evento) {
  if (!evento.target.closest('.filtro-icono-wrap')) {
    document.querySelectorAll('.filtro-desplegable').forEach(function (d) { d.classList.remove('open'); });
    document.querySelectorAll('.filtro-icono-btn').forEach(function (b) { b.classList.remove('activo'); });
  }
});

function aplicarFiltrosLocales() {
  const textoBusqueda = document.getElementById('buscarRazonSocial').value.toLowerCase();
  const entregaElegida = document.getElementById('selectFiltroEntrega').value;
  document.querySelectorAll('.fila-pedido').forEach(function (fila) {
    const razonSocial = fila.dataset.razonSocial;
    const metodoEntrega = fila.dataset.metodoEntrega;
    const coincideTexto = razonSocial.includes(textoBusqueda);
    const coincideEntrega = entregaElegida === 'todos' || metodoEntrega === entregaElegida;
    const pedidoId = fila.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);
    if (coincideTexto && coincideEntrega) {
      fila.style.display = '';
    } else {
      fila.style.display = 'none';
      if (filaDetalle) filaDetalle.style.display = 'none';
    }
  });
}

document.getElementById('buscarRazonSocial').addEventListener('input', aplicarFiltrosLocales);
document.getElementById('selectFiltroEntrega').addEventListener('change', aplicarFiltrosLocales);

function actualizarContadorSeleccionados() {
  const cantidad = document.querySelectorAll('.checkbox-pedido:checked').length;
  document.getElementById('cantidadSeleccionados').textContent = `${cantidad} pedidos seleccionados`;
}

document.querySelectorAll('.checkbox-pedido').forEach(function (checkbox) {
  checkbox.addEventListener('change', actualizarContadorSeleccionados);
});

document.getElementById('seleccionarTodos').addEventListener('change', function () {
  const estaMarcado = this.checked;
  document.querySelectorAll('.checkbox-pedido').forEach(function (checkbox) {
    checkbox.checked = estaMarcado;
  });
  actualizarContadorSeleccionados();
});

document.querySelectorAll('[data-avanzar-id]').forEach(function (boton) {
  boton.addEventListener('click', async function () {
    const pedidoId = boton.dataset.avanzarId;
    const nuevoEstado = boton.dataset.nuevoEstado;
    const textoEstado = nuevoEstado === 'en_proceso' ? 'En proceso' : 'Completado';
    const confirmado = await confirmarAccion(`¿Querés cambiar el estado de este pedido a "${textoEstado}"?`);
    if (!confirmado) return;
    await cambiarEstado(pedidoId, nuevoEstado);
  });
});

document.querySelectorAll('[data-detalle-id]').forEach(function (boton) {
  boton.addEventListener('click', function (evento) {
    evento.preventDefault();
    const fila = boton.closest('.fila-pedido');
    if (!fila) return;

    document.getElementById('detNumero').textContent = fila.dataset.numero;
    document.getElementById('detCliente').textContent = `${fila.dataset.clienteNombre} (${fila.dataset.razonSocial})`;
    document.getElementById('detLocal').textContent = fila.dataset.nombreComercio;
    document.getElementById('detFecha').textContent = fila.dataset.fechaTexto;
    document.getElementById('detEntrega').textContent = fila.dataset.metodoTexto;
    document.getElementById('detTelefono').textContent = fila.dataset.telefono;
    document.getElementById('detDireccion').textContent = fila.dataset.direccion;
    document.getElementById('detObservaciones').textContent = fila.dataset.observaciones || 'Sin observaciones';
    document.getElementById('motivoCancelacion').value = '';
    document.getElementById('modalDetallePedido').dataset.pedidoIdActual = fila.dataset.pedidoId;
    document.getElementById('modalDetallePedido').dataset.observacionesActuales = fila.dataset.observaciones;

    const pedidoId = fila.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);
    const tablaOrigen = filaDetalle ? filaDetalle.querySelector('.tabla-items tbody') : null;
    const detItemsTbody = document.getElementById('detItems');
    if (detItemsTbody) detItemsTbody.innerHTML = tablaOrigen ? tablaOrigen.innerHTML : '';

    document.getElementById('modalDetallePedido').classList.add('open');
  });
});

document.getElementById('btnCerrarDetalle').addEventListener('click', function () {
  document.getElementById('modalDetallePedido').classList.remove('open');
});

document.getElementById('btnCancelarPedido').addEventListener('click', async function () {
  const motivo = document.getElementById('motivoCancelacion').value.trim();
  if (!motivo) {
    alert('Por favor ingresá el motivo de cancelación antes de continuar.');
    return;
  }

  const pedidoId = document.getElementById('modalDetallePedido').dataset.pedidoIdActual;
  const observacionesActuales = document.getElementById('modalDetallePedido').dataset.observacionesActuales;

  const observacionesFinal = observacionesActuales
    ? `${observacionesActuales} — Cancelado: ${motivo}`
    : `Cancelado: ${motivo}`;

  await cambiarEstado(pedidoId, 'cancelado', observacionesFinal);
});

document.querySelectorAll('.btn-imprimir').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const pedidoId = boton.dataset.imprimirId;
    window.open(`/pedidos/${pedidoId}/comanda/`, '_blank', 'width=900,height=800');
  });
});

document.getElementById('btnCalcularTotal').addEventListener('click', function () {
  const seleccionados = document.querySelectorAll('.checkbox-pedido:checked');

  if (seleccionados.length === 0) {
    alert('Seleccioná al menos un pedido.');
    return;
  }

  const totales = {};
  const sinXubioId = new Set();

  seleccionados.forEach(function (checkbox) {
    const pedidoId = checkbox.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);
    if (!filaDetalle) return;

    const estabaOculto = filaDetalle.style.display === 'none';
    filaDetalle.style.display = 'table-row';

    const filas = filaDetalle.querySelectorAll('.tabla-items tbody tr');
    filas.forEach(function (fila) {
      const celdas = fila.querySelectorAll('td');
      if (celdas.length < 2) return;

      const xubioId = celdas[0].dataset.xubioId || '';
      const nombreProducto = celdas[0].textContent.trim();
      const cantidad = parseInt(celdas[1].textContent.trim(), 10);
      if (isNaN(cantidad) || cantidad <= 0) return;

      if (!xubioId) sinXubioId.add(nombreProducto);

      const clave = xubioId ? `id:${xubioId}` : `nombre:${nombreProducto}`;
      if (!totales[clave]) {
        totales[clave] = { nombre: nombreProducto, xubioId: xubioId || null, cantidad: 0 };
      }
      totales[clave].cantidad += cantidad;
    });

    if (estabaOculto) filaDetalle.style.display = 'none';
  });

  const tbody = document.getElementById('tablaTotalProductos');
  tbody.innerHTML = '';
  const entradas = Object.values(totales).sort((a, b) => a.nombre.localeCompare(b.nombre));
  entradas.forEach(function (item) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${item.nombre}</td><td>${item.cantidad}</td>`;
    tbody.appendChild(tr);
  });

  document.getElementById('modalTotalProductos').dataset.totales = JSON.stringify(entradas);
  document.getElementById('modalTotalProductos').classList.add('open');

  if (sinXubioId.size > 0) {
    console.warn('Productos sin xubio_producto_id cargado (no se exportan bien a la calculadora):', [...sinXubioId]);
  }
});

document.getElementById('btnCerrarTotal').addEventListener('click', function () {
  document.getElementById('modalTotalProductos').classList.remove('open');
});

document.getElementById('btnIrCalculadora').addEventListener('click', function () {
  const entradas = JSON.parse(document.getElementById('modalTotalProductos').dataset.totales);
  const ventasDia = {};
  entradas.forEach(function (item) {
    if (item.xubioId) {
      ventasDia[item.xubioId] = item.cantidad;
    }
  });
  sessionStorage.setItem('calculadora_ventas_dia', JSON.stringify(ventasDia));
  window.location.href = '/produccion/calculadora/';
});

document.getElementById('btnExportarExcel').addEventListener('click', function () {
  const entradas = JSON.parse(document.getElementById('modalTotalProductos').dataset.totales);
  const filas = [['Producto', 'Cantidad total'], ...entradas.map(item => [item.nombre, item.cantidad])];
  const libro = XLSX.utils.book_new();
  const hoja = XLSX.utils.aoa_to_sheet(filas);
  XLSX.utils.book_append_sheet(libro, hoja, 'Totales');
  XLSX.writeFile(libro, 'total_productos.xlsx');
});

document.getElementById('btnFacturar').addEventListener('click', async function () {
  const seleccionados = document.querySelectorAll('.checkbox-pedido:checked');

  if (seleccionados.length === 0) {
    alert('Seleccioná al menos un pedido.');
    return;
  }

  const confirmado = await confirmarAccion(`¿Querés facturar ${seleccionados.length} pedido${seleccionados.length > 1 ? 's' : ''} en Xubio?`);
  if (!confirmado) return;

  const btn = document.getElementById('btnFacturar');
  btn.textContent = 'Facturando...';
  btn.disabled = true;

  const pedidoIds = [...seleccionados].map(cb => parseInt(cb.dataset.pedidoId, 10));

  try {
    const response = await fetch('/api/sistema_pedidos/pedidos/facturar/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ pedido_ids: pedidoIds })
    });

    const resultados = await response.json();

    const tbody = document.getElementById('tablaFacturacion');
    tbody.innerHTML = '';
    resultados.forEach(function (r) {
      const tr = document.createElement('tr');
      const ok = r.ok;
      const detalle = ok ? 'OK' : (typeof r.detalle === 'string' ? r.detalle : JSON.stringify(r.detalle));
      tr.innerHTML = `
        <td>#${String(r.pedido_id).padStart(4, '0')}</td>
        <td style="color: ${ok ? 'var(--color-success, green)' : '#DC2626'}; font-weight: 600;">
          ${ok ? '✓ Facturado' : '✗ Error'}
        </td>
        <td style="font-size: 12px; color: var(--text-secondary);">${detalle}</td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById('modalFacturacion').classList.add('open');

  } catch (e) {
    alert('Error de conexión al facturar.');
  } finally {
    btn.textContent = 'Facturar seleccionados';
    btn.disabled = false;
  }
});

document.getElementById('btnCerrarFacturacion').addEventListener('click', function () {
  document.getElementById('modalFacturacion').classList.remove('open');
});

(function () {
  const filasPedido = document.querySelectorAll('.fila-pedido');
  if (filasPedido.length === 0) return;

  const ultimoId = Math.max(...[...filasPedido].map(f => parseInt(f.dataset.pedidoId, 10)));
  const btnActualizar = document.getElementById('btnActualizar');

  function beep() {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const oscilador = ctx.createOscillator();
    const ganancia = ctx.createGain();
    oscilador.connect(ganancia);
    ganancia.connect(ctx.destination);
    oscilador.type = 'sine';
    oscilador.frequency.setValueAtTime(880, ctx.currentTime);
    ganancia.gain.setValueAtTime(0.3, ctx.currentTime);
    ganancia.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
    oscilador.start(ctx.currentTime);
    oscilador.stop(ctx.currentTime + 0.8);
  }

  async function verificarNuevos() {
    try {
      const response = await fetch(`/api/sistema_pedidos/pedidos/nuevos/?ultimo_id=${ultimoId}`, {
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
      });
      const data = await response.json();
      if (data.cantidad > 0) {
        btnActualizar.textContent = `⚠️ ${data.cantidad} pedido${data.cantidad > 1 ? 's' : ''} nuevo${data.cantidad > 1 ? 's' : ''} — Actualizar`;
        btnActualizar.classList.add('btn-primary');
        btnActualizar.classList.remove('btn-secondary');
        beep();
      }
    } catch (e) {
      // silencioso
    }
  }

  setInterval(verificarNuevos, 30000);
})();