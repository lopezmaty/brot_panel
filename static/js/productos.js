function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function borrarProducto(productoId) {

    const confirmado = await confirmarAccion('¿Estás seguro que querés borrar este producto?');
    if (confirmado !== true) {
        return;
    }

    const url = `/api/lista_precios/productos/${productoId}/`;

    const response = await fetch(url, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
    if (response.ok) {
        location.reload();
    } else {
        alert('No se pudo borrar el producto');
    }
}

document.querySelectorAll('.btn-delete').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const productoId = boton.dataset.productoId;
    borrarProducto(productoId);
  });
});

document.getElementById('filtroFamilia').addEventListener('change', function () {
  const familiaElegida = this.value;
  const filas = document.querySelectorAll('tbody tr');

  filas.forEach(function (fila) {
    const familiaDeLaFila = fila.dataset.familia;
    if (familiaElegida === 'todos' || familiaDeLaFila === familiaElegida) {
      fila.style.display = '';
    } else {
      fila.style.display = 'none';
    }
  });
});