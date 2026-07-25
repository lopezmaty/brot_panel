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

async function aplicarListaATodos(listaId) {

    const confirmado = await confirmarAccion('¿Aplicar esta lista a todos los clientes que ya tenían una lista de esta categoría?');
    if (confirmado !== true) {
        return;
    }

    const response = await fetch('/api/sistema_pedidos/aplicar-lista-a-todos/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ lista_id: listaId })
    });

    if (response.ok) {
        const datos = await response.json();
        alert(`Se actualizaron ${datos.clientes_a_actualizar} clientes.`);
    } else {
        alert('No se pudo aplicar la lista a los clientes');
    }
}

document.querySelectorAll('[data-aplicar-lista-id]').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const listaId = boton.dataset.aplicarListaId;
    aplicarListaATodos(listaId);
  });
});