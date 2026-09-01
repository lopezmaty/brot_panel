const datosPrecios = JSON.parse(document.getElementById('datosPrecios').textContent);

function formatearPrecio(valor) {
  if (!valor && valor !== 0) return '';
  return parseFloat(valor).toLocaleString('es-AR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function parsearPrecio(texto) {
  if (!texto) return '';
  return texto.replace(/\./g, '').replace(',', '.');
}

document.querySelectorAll('.input-precio-producto').forEach(function (input) {
  const productoId = input.dataset.productoId;
  if (datosPrecios[productoId] !== undefined) {
    input.value = formatearPrecio(datosPrecios[productoId]);
  }

  input.addEventListener('blur', function () {
    const valor = parsearPrecio(input.value);
    if (valor !== '' && !isNaN(parseFloat(valor))) {
      input.value = formatearPrecio(parseFloat(valor));
    }
  });

  input.addEventListener('focus', function () {
    const valor = parsearPrecio(input.value);
    input.value = valor;
  });
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function guardarListaPrecios() {
  const fecha = `${document.getElementById('inputFecha').value}-01`;
  const tipoCliente = document.getElementById('inputTipoCliente').value;
  const listaId = document.getElementById('formListaPrecios').dataset.listaId;
  const xubioListaId = document.getElementById('inputXubioListaId').value.trim();

  const preciosCargados = [];
  document.querySelectorAll('.input-precio-producto').forEach(function (input) {
    const valorRaw = input.value.trim();
    if (valorRaw !== '') {
      const valorParsed = parsearPrecio(valorRaw);
      const numero = parseFloat(valorParsed);
      if (!isNaN(numero)) {
        preciosCargados.push({
          producto: input.dataset.productoId,
          precio: numero
        });
      }
    }
  });

  const response = await fetch('/api/lista_precios/guardar-lista-completa/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      lista_id: listaId,
      fecha: fecha,
      tipo_cliente: tipoCliente,
      xubio_lista_precio_id: xubioListaId || null,
      precios: preciosCargados
    })
  });

  if (response.ok) {
    window.location.href = '/panel/lista_precios/';
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

      let mensaje = `Se importaron ${data.importados} precios desde Xubio.`;
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