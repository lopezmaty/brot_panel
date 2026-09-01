function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function guardarListaPrecios() {
  const nombre = document.getElementById('inputNombre').value;
  const fecha = `${document.getElementById('inputFecha').value}-01`;
  const listaId = document.getElementById('formListaPrecios').dataset.listaId;
  const xubioListaId = document.getElementById('inputXubioListaId').value.trim();

  const response = await fetch('/api/lista_precios/guardar-lista-completa/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      lista_id: listaId,
      nombre: nombre,
      fecha: fecha,
      xubio_lista_precio_id: xubioListaId || null,
    })
  });

  if (response.ok) {
    window.location.href = '/lista_precios/';
  } else {
    alert('No se pudo guardar la lista de precios');
  }
}

document.getElementById('formListaPrecios').addEventListener('submit', function (evento) {
  evento.preventDefault();
  guardarListaPrecios();
});

const btnImportarXubio = document.getElementById('btnImportarXubio');
if (btnImportarXubio) {
  btnImportarXubio.addEventListener('click', async function () {
    const listaId = document.getElementById('formListaPrecios').dataset.listaId;
    const importandoTexto = document.getElementById('importandoTexto');

    btnImportarXubio.disabled = true;
    importandoTexto.style.display = 'inline';

    try {
      const response = await fetch(`/api/lista_precios/lista_precios/${listaId}/importar-precios-xubio/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken')
        }
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.error || 'No se pudo importar. Revisá que la lista tenga el código de Xubio cargado y guardado.');
        return;
      }

      let mensaje = `Se importaron ${data.importados} precios desde Xubio (${data.con_cambio_de_precio} con cambio de precio registrado en el historial).`;
      if (data.sin_match && data.sin_match.length > 0) {
        mensaje += `\n\n${data.sin_match.length} productos de Xubio no matchearon con ningún producto de tu panel (revisá la consola para el detalle).`;
        console.log('Productos de Xubio sin match:', data.sin_match);
      }
      alert(mensaje);

      window.location.reload();
    } catch (error) {
      alert('Ocurrió un error al importar desde Xubio.');
      console.error(error);
    } finally {
      btnImportarXubio.disabled = false;
      importandoTexto.style.display = 'none';
    }
  });
}