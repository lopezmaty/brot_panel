function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function borrarCliente(clienteId) {

    const confirmado = await confirmarAccion('¿Estás seguro que querés borrar este cliente?');
    if (confirmado !== true) {
        return;
    }

    const url = `/api/sistema_pedidos/clientes/${clienteId}/`;

    const response = await fetch(url, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
    if (response.ok) {
        location.reload();
    } else {
        alert('No se pudo borrar el cliente');
    }
}

document.querySelectorAll('.btn-delete').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const clienteId = boton.dataset.clienteId;
    borrarCliente(clienteId);
  });
});

document.getElementById('filtroTipoCliente').addEventListener('change', function () {
  const tipoElegido = this.value;
  const filas = document.querySelectorAll('tbody tr');

  filas.forEach(function (fila) {
    const tipoDeLaFila = fila.dataset.tipoCliente;
    if (tipoElegido === 'todos' || tipoDeLaFila === tipoElegido) {
      fila.style.display = '';
    } else {
      fila.style.display = 'none';
    }
  });
});