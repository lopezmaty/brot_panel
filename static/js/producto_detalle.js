function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function actualizarCamposMedida() {
  const tipoMedida = document.getElementById('inputTipoMedida').value;
  const medida2 = document.getElementById('inputMedida2');
  const medida3 = document.getElementById('inputMedida3');

  if (tipoMedida === 'diametro') {
    medida2.disabled = true;
    medida3.disabled = true;
  } else if (tipoMedida === 'largo_ancho') {
    medida2.disabled = false;
    medida3.disabled = true;
  } else if (tipoMedida === 'largo_ancho_alto') {
    medida2.disabled = false;
    medida3.disabled = false;
  }
}

document.getElementById('inputTipoMedida').addEventListener('change', actualizarCamposMedida);
actualizarCamposMedida();

async function crearOEditarProducto() {
    const nombre = document.getElementById('inputNombre').value;
    const variedad = document.getElementById('inputVariedad').value;
    const tamaño = document.getElementById('inputTamaño').value;
    const familia = document.getElementById('inputFamilia').value;
    const unidadesPaquete = document.getElementById('inputUnidadesPaquete').value;
    const tipoMedida = document.getElementById('inputTipoMedida').value;
    const medida1 = document.getElementById('inputMedida1').value;
    const medida2 = document.getElementById('inputMedida2').value;
    const medida3 = document.getElementById('inputMedida3').value;
    const activo = document.getElementById('inputActivo').checked;
    const xubioProductoId = document.getElementById('inputXubioProductoId').value;

    const productoId = document.getElementById('formProducto').dataset.productoId;

    const metodo = productoId === '' ? 'POST' : 'PUT';
    const url = productoId === '' ? '/api/lista_precios/productos/' : `/api/lista_precios/productos/${productoId}/`;

    const response = await fetch(url, {
        method: metodo,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            nombre,
            variedad,
            tamaño,
            familia,
            unidades_paquete: unidadesPaquete,
            tipo_medida: tipoMedida,
            medida_1: medida1 || null,
            medida_2: medida2 || null,
            medida_3: medida3 || null,
            activo,
            xubio_producto_id: xubioProductoId || null,
        })
    });

    if (response.ok) {
        window.location.href = '/panel/producto/';
    } else {
        alert('No se pudo guardar el producto');
    }
}

document.getElementById('formProducto').addEventListener('submit', function (evento) {
    evento.preventDefault();
    crearOEditarProducto();
});