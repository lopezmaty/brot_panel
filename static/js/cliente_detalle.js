function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function crearOEditarCliente() {
    const nombre = document.getElementById('inputNombre').value;
    const razonSocial = document.getElementById('inputRazonSocial').value;
    const cuit = document.getElementById('inputCuit').value;
    const nombreComercio = document.getElementById('inputNombreComercio').value;
    const direccion = document.getElementById('inputDireccion').value;
    const ciudad = document.getElementById('inputCiudad').value;
    const provincia = document.getElementById('inputProvincia').value;
    const telefono = document.getElementById('inputTelefono').value;
    const mail = document.getElementById('inputMail').value;
    const condicionIva = document.getElementById('inputCondicionIva').value;
    const tipoCliente = document.getElementById('inputTipoCliente').value;
    const activo = document.getElementById('inputActivo').checked;
    const poseeDeuda = document.getElementById('inputPoseeDeuda').checked;


    const clienteId = document.getElementById('formCliente').dataset.clienteId;

    let metodo;
    let url;

    if (clienteId === "") {
        metodo = 'POST';
        url = '/api/sistema_pedidos/clientes/';
    } else {
        metodo = 'PUT';
        url = `/api/sistema_pedidos/clientes/${clienteId}/`;
}

    const response = await fetch(url, {
        method: metodo,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            nombre: nombre,
            razon_social: razonSocial,
            cuit: cuit,
            nombre_comercio: nombreComercio,
            direccion: direccion,
            ciudad: ciudad,
            provincia: provincia,
            telefono: telefono,
            mail: mail,
            condicion_iva: condicionIva,
            tipo_cliente: tipoCliente,
            activo: activo,
            posee_deuda: poseeDeuda
        })
    });

    if (response.ok) {
        window.location.href = '/panel/clientes/';
    } else {
        alert('No se pudo guardar el cliente');
    }
}

document.getElementById('formCliente').addEventListener('submit', function (evento) {
    evento.preventDefault();
    crearOEditarCliente();
});