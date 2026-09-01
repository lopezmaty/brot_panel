function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function borrarLista(listaId) {

    const confirmado = await confirmarAccion('¿Estás seguro que querés borrar esta lista de precios?');
    if (confirmado !== true) {
        return;
    }

    const url = `/api/lista_precios/lista_precios/${listaId}/`;

    const response = await fetch(url, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
    if (response.ok) {
        location.reload();
    } else {
        alert('No se pudo borrar la lista de precios');
    }
}

document.querySelectorAll('.btn-delete[data-lista-id]').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const listaId = boton.dataset.listaId;
    borrarLista(listaId);
  });
});