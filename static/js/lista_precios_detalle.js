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

  console.log('precios a enviar:', preciosCargados);

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