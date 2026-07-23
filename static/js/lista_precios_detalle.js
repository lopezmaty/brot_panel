const datosPrecios = JSON.parse(document.getElementById('datosPrecios').textContent);

document.querySelectorAll('.input-precio-producto').forEach(function (input) {
  const productoId = input.dataset.productoId;
  if (datosPrecios[productoId] !== undefined) {
    input.value = datosPrecios[productoId];
  }
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function guardarListaPrecios() {
  const nombre = document.getElementById('inputNombre').value;
  const fecha = document.getElementById('inputFecha').value;
  const listaId = document.getElementById('formListaPrecios').dataset.listaId;

  const preciosCargados = [];
  document.querySelectorAll('.input-precio-producto').forEach(function (input) {
    if (input.value !== '') {
      preciosCargados.push({
        producto: input.dataset.productoId,
        precio: input.value
      });
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
      nombre: nombre,
      fecha: fecha,
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