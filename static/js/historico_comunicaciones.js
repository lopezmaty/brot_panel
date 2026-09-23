function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

const OPCIONES_URL = '/api/sistema_pedidos/comunicaciones/opciones/';
const ENVIAR_URL = '/api/sistema_pedidos/comunicaciones/enviar/';

const modal = document.getElementById('modalNuevaComunicacion');
const btnAbrir = document.getElementById('btnNuevaComunicacion');
const btnCancelar = document.getElementById('btnCancelarComunicacion');
const btnEnviar = document.getElementById('btnEnviarComunicacion');
const checkTodos = document.getElementById('checkTodosClientes');
const bloqueDestinatarios = document.getElementById('bloqueDestinatarios');
const listasEl = document.getElementById('listasComunicacion');
const tiposEl = document.getElementById('tiposComunicacion');
const clientesEl = document.getElementById('clientesComunicacion');
const buscarCliente = document.getElementById('buscarClienteComunicacion');
const resumenEl = document.getElementById('resumenDestinatariosComunicacion');
const errorEl = document.getElementById('errorComunicacion');
const inputTitulo = document.getElementById('inputTituloComunicacion');
const inputMensaje = document.getElementById('inputMensajeComunicacion');

let opciones = null;

function crearCheckbox(contenedor, valor, texto, nombreDataset) {
  const label = document.createElement('label');
  label.style.cssText = 'display:inline-flex; align-items:center; gap:6px; cursor:pointer;';
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.value = valor;
  input.dataset.grupo = nombreDataset;
  input.addEventListener('change', actualizarResumen);
  const span = document.createElement('span');
  span.textContent = texto;
  label.appendChild(input);
  label.appendChild(span);
  contenedor.appendChild(label);
  return label;
}

function idsSeleccionados(contenedor) {
  return Array.from(contenedor.querySelectorAll('input[type="checkbox"]:checked')).map(i => parseInt(i.value, 10));
}

function calcularDestinatarios() {
  if (!opciones) return [];
  if (checkTodos.checked) return opciones.clientes;

  const listaIds = idsSeleccionados(listasEl);
  const tipoIds = idsSeleccionados(tiposEl);
  const clienteIds = idsSeleccionados(clientesEl);

  if (listaIds.length === 0 && tipoIds.length === 0 && clienteIds.length === 0) return [];

  return opciones.clientes.filter(c =>
    clienteIds.includes(c.id) || listaIds.includes(c.lista_id) || tipoIds.includes(c.tipo_id)
  );
}

function actualizarResumen() {
  const destinatarios = calcularDestinatarios();
  if (destinatarios.length === 0) {
    resumenEl.textContent = 'Todavía no elegiste destinatarios.';
    return;
  }
  const sinMail = destinatarios.filter(c => !c.tiene_mail).length;
  let texto = `Se va a avisar a ${destinatarios.length} cliente${destinatarios.length === 1 ? '' : 's'}.`;
  if (sinMail > 0) {
    texto += ` ${sinMail} sin mail cargado (solo verán el aviso en el catálogo).`;
  }
  resumenEl.textContent = texto;
}

function poblarOpciones() {
  listasEl.innerHTML = '';
  tiposEl.innerHTML = '';
  clientesEl.innerHTML = '';

  opciones.listas.forEach(l => crearCheckbox(listasEl, l.id, l.nombre, 'lista'));
  opciones.tipos.forEach(t => crearCheckbox(tiposEl, t.id, t.nombre, 'tipo'));
  opciones.clientes.forEach(c => {
    const label = crearCheckbox(clientesEl, c.id, c.nombre, 'cliente');
    label.dataset.nombreBusqueda = c.nombre.toLowerCase();
  });
}

function toggleTodos() {
  const deshabilitar = checkTodos.checked;
  bloqueDestinatarios.style.opacity = deshabilitar ? '0.5' : '1';
  bloqueDestinatarios.querySelectorAll('input').forEach(i => { i.disabled = deshabilitar; });
  actualizarResumen();
}

function mostrarError(mensaje) {
  if (!mensaje) {
    errorEl.style.display = 'none';
    errorEl.textContent = '';
    return;
  }
  errorEl.textContent = mensaje;
  errorEl.style.display = 'block';
}

function limpiarFormulario() {
  inputTitulo.value = '';
  inputMensaje.value = '';
  checkTodos.checked = false;
  bloqueDestinatarios.style.opacity = '1';
  bloqueDestinatarios.querySelectorAll('input').forEach(i => { i.disabled = false; i.checked = false; });
  buscarCliente.value = '';
  clientesEl.querySelectorAll('label').forEach(l => { l.style.display = 'inline-flex'; });
  mostrarError('');
  resumenEl.textContent = '';
}

async function abrirModal() {
  mostrarError('');
  modal.style.display = 'flex';
  if (opciones) {
    actualizarResumen();
    return;
  }
  try {
    const response = await fetch(OPCIONES_URL, { credentials: 'same-origin' });
    if (!response.ok) {
      mostrarError('No se pudieron cargar los clientes.');
      return;
    }
    opciones = await response.json();
    poblarOpciones();
    actualizarResumen();
  } catch (e) {
    mostrarError('Error de conexión al cargar los clientes.');
  }
}

function cerrarModal() {
  modal.style.display = 'none';
}

btnAbrir.addEventListener('click', abrirModal);
btnCancelar.addEventListener('click', cerrarModal);
modal.addEventListener('click', function (e) {
  if (e.target === modal) cerrarModal();
});

checkTodos.addEventListener('change', toggleTodos);

buscarCliente.addEventListener('input', function () {
  const texto = this.value.trim().toLowerCase();
  clientesEl.querySelectorAll('label').forEach(label => {
    const coincide = !texto || label.dataset.nombreBusqueda.includes(texto);
    label.style.display = coincide ? 'inline-flex' : 'none';
  });
});

btnEnviar.addEventListener('click', async function () {
  const titulo = inputTitulo.value.trim();
  const mensaje = inputMensaje.value.trim();
  mostrarError('');

  if (!titulo || !mensaje) {
    mostrarError('Completá el título y el mensaje.');
    return;
  }

  const destinatarios = calcularDestinatarios();
  if (destinatarios.length === 0) {
    mostrarError('Elegí al menos un destinatario.');
    return;
  }

  const payload = checkTodos.checked
    ? { titulo, mensaje, todos: true }
    : {
        titulo, mensaje,
        listas: idsSeleccionados(listasEl),
        tipos: idsSeleccionados(tiposEl),
        clientes: idsSeleccionados(clientesEl),
      };

  btnEnviar.disabled = true;
  btnEnviar.textContent = 'Enviando...';

  try {
    const response = await fetch(ENVIAR_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      mostrarError(data.error || 'No se pudo enviar la comunicación.');
      return;
    }

    limpiarFormulario();
    cerrarModal();
    window.location.reload();
  } catch (e) {
    mostrarError('Error de conexión.');
  } finally {
    btnEnviar.disabled = false;
    btnEnviar.textContent = 'Enviar';
  }
});