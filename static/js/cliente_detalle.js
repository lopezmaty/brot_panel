function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

document.getElementById('btnBuscarXubio').addEventListener('click', async function () {
    const cuit = document.getElementById('inputCuit').value.trim();
    if (!cuit) {
        alert('Ingresá el CUIT primero.');
        return;
    }

    const btn = document.getElementById('btnBuscarXubio');
    btn.textContent = 'Buscando...';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/sistema_pedidos/clientes/buscar-xubio/?cuit=${encodeURIComponent(cuit)}`, {
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });

        if (response.status === 404) {
            alert('No se encontró el cliente en Xubio con ese CUIT.');
            return;
        }

        if (!response.ok) {
            alert('Error al consultar Xubio.');
            return;
        }

        const data = await response.json();

        if (data.razon_social) document.getElementById('inputRazonSocial').value = data.razon_social;
        if (data.direccion) document.getElementById('inputDireccion').value = data.direccion;
        if (data.mail) document.getElementById('inputMail').value = data.mail;
        if (data.telefono) document.getElementById('inputTelefono').value = data.telefono;
        if (data.condicion_iva) document.getElementById('inputCondicionIva').value = data.condicion_iva;
        if (data.provincia) document.getElementById('inputProvincia').value = data.provincia;
        if (data.xubio_cliente_id) {
            document.getElementById('formCliente').dataset.xubioClienteId = data.xubio_cliente_id;
        }

        alert(`Cliente encontrado: ${data.razon_social}`);

    } catch (e) {
        alert('Error de conexión.');
    } finally {
        btn.textContent = 'Buscar en Xubio';
        btn.disabled = false;
    }
});

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
    const listaPrecios = document.getElementById('inputListaPrecios').value;
    const xubioPuntoVenta = document.getElementById('inputXubioPuntoVenta').value;
    const xubioTipoComprobante = document.getElementById('inputXubioTipoComprobante').value;
    const diasCC = document.getElementById('inputDiasCC').value;
    const xubioClienteId = document.getElementById('formCliente').dataset.xubioClienteId || null;

    const clienteId = document.getElementById('formCliente').dataset.clienteId;

    const metodo = clienteId === '' ? 'POST' : 'PUT';
    const url = clienteId === '' ? '/api/sistema_pedidos/clientes/' : `/api/sistema_pedidos/clientes/${clienteId}/`;

    const response = await fetch(url, {
        method: metodo,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            nombre,
            razon_social: razonSocial,
            cuit,
            nombre_comercio: nombreComercio,
            direccion,
            ciudad,
            provincia,
            telefono,
            mail,
            condicion_iva: condicionIva,
            tipo_cliente: tipoCliente,
            lista_precios: listaPrecios,
            activo,
            posee_deuda: poseeDeuda,
            xubio_cliente_id: xubioClienteId,
            xubio_punto_venta_id: xubioPuntoVenta || null,
            xubio_tipo_comprobante: xubioTipoComprobante || null,
            dias_cc: diasCC || 0,
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

const btnCopiar = document.getElementById('btnCopiarLink');
if (btnCopiar) {
  btnCopiar.addEventListener('click', function () {
    const link = document.getElementById('magicLinkInput').value;
    navigator.clipboard.writeText(link);
    btnCopiar.textContent = '¡Copiado!';
    setTimeout(function () {
      btnCopiar.textContent = 'Copiar';
    }, 2000);
  });
}