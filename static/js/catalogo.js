const TOKEN = document.getElementById('catalogo-token').dataset.token;
const POSEE_DEUDA = document.getElementById('catalogo-token').dataset.deuda === '1';
const carrito = {};

function mostrarModalDeuda() {
  document.getElementById('modalDeuda').style.display = 'flex';
}

// El modal de deuda no tiene botón de cerrar a propósito: mientras el cliente
// tenga boletas vencidas, no debe poder volver a interactuar con el catálogo.
if (POSEE_DEUDA) {
  mostrarModalDeuda();
}

function formatearPrecio(numero) {
  return '$' + numero.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function actualizarCarrito() {
  const items = Object.values(carrito).filter(i => i.cantidad > 0);
  const contenedor = document.getElementById('carritoItems');
  const totalEl = document.getElementById('carritoTotal');
  const totalPrecioEl = document.getElementById('totalPrecio');
  const formPedido = document.getElementById('formPedido');
  const badge = document.getElementById('badgeCantidad');

  if (items.length === 0) {
    contenedor.innerHTML = '<p class="carrito-vacio">Todavía no agregaste productos.</p>';
    totalEl.style.display = 'none';
    formPedido.style.display = 'none';
    badge.style.display = 'none';
    return;
  }

  let html = '';
  let total = 0;
  let totalUnidades = 0;
  items.forEach(item => {
    const subtotal = item.cantidad * item.precio;
    total += subtotal;
    totalUnidades += item.cantidad;
    html += `<div class="carrito-item-fila"><span>${item.nombre} x${item.cantidad}</span><span>${formatearPrecio(subtotal)}</span></div>`;
  });

  contenedor.innerHTML = html;
  totalPrecioEl.textContent = formatearPrecio(total);
  totalEl.style.display = 'flex';
  formPedido.style.display = 'block';
  badge.textContent = totalUnidades;
  badge.style.display = 'inline';
}

function actualizarDesdeInput(input) {
  const id = input.dataset.id;
  if (!id) return;
  const cantidad = Math.max(0, parseInt(input.value.replace(/[^0-9]/g, ''), 10) || 0);
  input.value = cantidad;
  if (!carrito[id]) {
    carrito[id] = {
      id: parseInt(id),
      nombre: input.dataset.nombre,
      precio: parseFloat(input.dataset.precio),
      cantidad: 0,
    };
  }
  carrito[id].cantidad = cantidad;
  actualizarCarrito();
}

document.querySelectorAll('.input-cantidad').forEach(input => {
  input.addEventListener('change', function () { actualizarDesdeInput(input); });
  input.addEventListener('input', function () {
    this.value = this.value.replace(/[^0-9]/g, '');
    actualizarDesdeInput(input);
  });
});

document.getElementById('toggleCarrito').addEventListener('click', function () {
  const body = document.getElementById('carritoBody');
  const icon = document.getElementById('iconCarrito');
  const abierto = body.classList.contains('open');
  body.classList.toggle('open', !abierto);
  icon.className = abierto ? 'ti ti-chevron-down' : 'ti ti-chevron-up';
});

document.getElementById('btnEnviarPedido').addEventListener('click', function () {
  if (POSEE_DEUDA) {
    mostrarModalDeuda();
    return;
  }

  const items = Object.values(carrito).filter(i => i.cantidad > 0);
  if (items.length === 0) {
    alert('Agregá al menos un producto.');
    return;
  }

  const metodo = document.getElementById('selectMetodo');
  const metodoTexto = metodo.options[metodo.selectedIndex].text;
  const observaciones = document.getElementById('inputObservaciones').value;

  let resumenHtml = '<div style="border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-bottom: 12px;">';
  let total = 0;
  items.forEach(item => {
    const subtotal = item.cantidad * item.precio;
    total += subtotal;
    resumenHtml += `<div class="carrito-item-fila" style="padding: 8px 14px;">`
      + `<span>${item.nombre} x${item.cantidad}</span>`
      + `<span>${formatearPrecio(subtotal)}</span></div>`;
  });
  resumenHtml += `<div class="carrito-item-fila" style="padding: 8px 14px; font-weight: 700;">`
    + `<span>Total</span><span>${formatearPrecio(total)}</span></div>`;
  resumenHtml += '</div>';
  resumenHtml += `<p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Método de entrega: <strong>${metodoTexto}</strong></p>`;
  if (observaciones) {
    resumenHtml += `<p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0;">Observaciones: <strong>${observaciones}</strong></p>`;
  }

  document.getElementById('modalResumen').innerHTML = resumenHtml;
  const modal = document.getElementById('modalConfirmar');
  modal.style.display = 'flex';
});

document.getElementById('btnCancelarConfirmar').addEventListener('click', function () {
  document.getElementById('modalConfirmar').style.display = 'none';
});

document.getElementById('modalConfirmar').addEventListener('click', function (e) {
  if (e.target === this) this.style.display = 'none';
});

document.getElementById('btnConfirmarPedido').addEventListener('click', async function () {
  const items = Object.values(carrito).filter(i => i.cantidad > 0 && i.id);
  const metodo = document.getElementById('selectMetodo').value;
  const observaciones = document.getElementById('inputObservaciones').value;

  const btn = document.getElementById('btnConfirmarPedido');
  btn.textContent = 'Enviando...';
  btn.disabled = true;

  try {
    const response = await fetch(`/catalogo/${TOKEN}/confirmar/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map(i => ({ producto_id: i.id, cantidad: i.cantidad })),
        metodo_entrega: metodo,
        observaciones: observaciones,
      })
    });

    if (response.ok) {
      document.getElementById('modalConfirmar').style.display = 'none';
      document.body.insertAdjacentHTML('beforeend', `
        <div id="modalExito" style="position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:300; display:flex; align-items:center; justify-content:center; padding:24px;">
          <div style="background:#ffffff; border-radius:20px; padding:40px 32px; max-width:380px; width:100%; text-align:center; font-family:'DM Sans',sans-serif;">
            <div style="font-size:56px; margin-bottom:16px;">✅</div>
            <h2 style="font-size:22px; font-weight:700; color:#16213E; margin:0 0 8px;">¡Pedido enviado!</h2>
            <p style="color:#4A5D7A; font-size:14px; margin:0 0 28px;">Nos pondremos en contacto para confirmar la entrega.</p>
            <a href="/catalogo/${TOKEN}/perfil/?pedido=ok"
               style="background:#16213E; color:white; text-decoration:none; padding:14px 28px; border-radius:12px; font-size:15px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; gap:8px; width:100%; box-sizing:border-box;">
              📋 Ir a mis pedidos
            </a>
          </div>
        </div>
      `);
    } else {
      alert('No se pudo enviar el pedido. Intentá de nuevo.');
      btn.textContent = 'Confirmar pedido';
      btn.disabled = false;
      document.getElementById('modalConfirmar').style.display = 'none';
    }
  } catch (e) {
    alert('Error de conexión.');
    btn.textContent = 'Confirmar pedido';
    btn.disabled = false;
    document.getElementById('modalConfirmar').style.display = 'none';
  }
});

window.addEventListener('load', function () {
  const carritoPrecargado = sessionStorage.getItem('carrito_precargado');
  if (!carritoPrecargado) return;
  sessionStorage.removeItem('carrito_precargado');

  const items = JSON.parse(carritoPrecargado);
  items.forEach(function (item) {
    const input = document.getElementById(`cantidad-${item.producto_id}`);
    if (input) {
      input.value = item.cantidad;
      actualizarDesdeInput(input);
    }
  });

  const body = document.getElementById('carritoBody');
  const icon = document.getElementById('iconCarrito');
  body.classList.add('open');
  icon.className = 'ti ti-chevron-up';
});

// --- Avisos / comunicaciones pendientes (popup con "Confirmar lectura") ---

let colaAvisos = [];

function mostrarSiguienteAviso() {
  const modal = document.getElementById('modalAviso');
  if (colaAvisos.length === 0) {
    modal.style.display = 'none';
    return;
  }

  const aviso = colaAvisos[0];
  document.getElementById('avisoTitulo').textContent = aviso.titulo;
  document.getElementById('avisoMensaje').textContent = aviso.mensaje;

  const vigenciaEl = document.getElementById('avisoVigencia');
  if (aviso.vigente_desde) {
    vigenciaEl.textContent = `Vigente desde el ${aviso.vigente_desde}.`;
    vigenciaEl.style.display = 'block';
  } else {
    vigenciaEl.style.display = 'none';
  }

  modal.style.display = 'flex';
}

document.getElementById('btnConfirmarLecturaAviso').addEventListener('click', async function () {
  if (colaAvisos.length === 0) return;
  const aviso = colaAvisos[0];
  const btn = this;
  btn.disabled = true;

  try {
    await fetch(`/api/sistema_pedidos/catalogo/${TOKEN}/comunicaciones/${aviso.id}/confirmar/`, {
      method: 'POST',
    });
  } catch (e) {
    // si falla la confirmación, igual dejamos avanzar para no trabar al cliente;
    // el aviso va a volver a aparecer la próxima vez que entre.
  }

  colaAvisos.shift();
  btn.disabled = false;
  mostrarSiguienteAviso();
});

async function cargarAvisosPendientes() {
  try {
    const response = await fetch(`/api/sistema_pedidos/catalogo/${TOKEN}/comunicaciones/pendientes/`);
    if (!response.ok) return;
    const data = await response.json();
    colaAvisos = data.comunicaciones || [];
    mostrarSiguienteAviso();
  } catch (e) {
    // sin conexión: no mostramos avisos, no bloqueamos el catálogo
  }
}

cargarAvisosPendientes();