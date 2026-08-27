document.querySelectorAll('.btn-expandir').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const pedidoId = boton.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);

    if (filaDetalle.style.display === 'none') {
      filaDetalle.style.display = 'table-row';
      boton.classList.add('rotado');
    } else {
      filaDetalle.style.display = 'none';
      boton.classList.remove('rotado');
    }
  });
});

function toggleDesplegable(botonId, desplegableId) {
  const boton = document.getElementById(botonId);
  const desplegable = document.getElementById(desplegableId);

  boton.addEventListener('click', function (evento) {
    evento.stopPropagation();
    const yaEstaAbierto = desplegable.classList.contains('open');

    document.querySelectorAll('.filtro-desplegable').forEach(function (d) {
      d.classList.remove('open');
    });
    document.querySelectorAll('.filtro-icono-btn').forEach(function (b) {
      b.classList.remove('activo');
    });

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
    document.querySelectorAll('.filtro-desplegable').forEach(function (d) {
      d.classList.remove('open');
    });
    document.querySelectorAll('.filtro-icono-btn').forEach(function (b) {
      b.classList.remove('activo');
    });
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
      if (filaDetalle) {
        filaDetalle.style.display = 'none';
      }
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

document.querySelectorAll('[data-detalle-id]').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const fila = boton.closest('.fila-pedido');

    document.getElementById('detNumero').textContent = fila.dataset.numero;
    document.getElementById('detCliente').textContent = `${fila.dataset.clienteNombre} (${fila.dataset.razonSocial})`;
    document.getElementById('detLocal').textContent = fila.dataset.nombreComercio;
    document.getElementById('detFecha').textContent = fila.dataset.fechaTexto;
    document.getElementById('detEntrega').textContent = fila.dataset.metodoTexto;
    document.getElementById('detTelefono').textContent = fila.dataset.telefono;
    document.getElementById('detDireccion').textContent = fila.dataset.direccion;
    document.getElementById('detObservaciones').textContent = fila.dataset.observaciones || 'Sin observaciones';

    const pedidoId = fila.dataset.pedidoId;
    const filaDetalle = document.getElementById(`detalle-${pedidoId}`);
    const tablaOrigen = filaDetalle.querySelector('.tabla-items tbody');
    document.querySelector('#detItems tbody').innerHTML = tablaOrigen ? tablaOrigen.innerHTML : '';

    document.getElementById('modalDetallePedido').classList.add('open');
  });
});

document.getElementById('btnCerrarDetalle').addEventListener('click', function () {
  document.getElementById('modalDetallePedido').classList.remove('open');
});