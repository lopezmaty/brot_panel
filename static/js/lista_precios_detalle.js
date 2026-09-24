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

// --- Programar nuevos precios (importar de Xubio con fecha de vigencia) ---

const bloqueProgramar = document.getElementById('bloqueProgramarPrecios');

if (bloqueProgramar) {
  const btnProgramar = document.getElementById('btnProgramarPrecios');
  const panelFecha = document.getElementById('panelFechaVigencia');
  const inputFechaVigencia = document.getElementById('inputVigenteDesde');
  const btnConfirmarVigencia = document.getElementById('btnConfirmarVigencia');
  const btnCancelarFechaVigencia = document.getElementById('btnCancelarFechaVigencia');
  const importandoTexto = document.getElementById('importandoTexto');
  const btnCancelarProgramada = document.getElementById('btnCancelarProgramada');
  const listaId = document.getElementById('formListaPrecios').dataset.listaId;

  if (btnProgramar) {
    btnProgramar.addEventListener('click', function () {
      const manana = new Date();
      manana.setDate(manana.getDate() + 1);
      inputFechaVigencia.min = manana.toISOString().slice(0, 10);
      panelFecha.style.display = 'block';
      btnProgramar.style.display = 'none';
    });
  }

  if (btnCancelarFechaVigencia) {
    btnCancelarFechaVigencia.addEventListener('click', function () {
      panelFecha.style.display = 'none';
      btnProgramar.style.display = 'inline-flex';
      inputFechaVigencia.value = '';
    });
  }

  if (btnConfirmarVigencia) {
    btnConfirmarVigencia.addEventListener('click', async function () {
      const vigenteDesde = inputFechaVigencia.value;
      if (!vigenteDesde) {
        alert('Elegí la fecha de vigencia.');
        return;
      }

      btnConfirmarVigencia.disabled = true;
      btnCancelarFechaVigencia.disabled = true;
      importandoTexto.style.display = 'inline';

      try {
        const response = await fetch(`/api/lista_precios/lista_precios/${listaId}/importar-precios-xubio/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            vigente_desde: vigenteDesde,
            avisar_clientes: document.getElementById('checkAvisarClientes').checked,
          })
        });

        const data = await response.json();

        if (!response.ok) {
          alert(data.error || 'No se pudo programar la actualización de precios.');
          return;
        }

        let mensaje = `Se programaron ${data.cantidad_cambios} cambio${data.cantidad_cambios === 1 ? '' : 's'} de precio para el ${vigenteDesde.split('-').reverse().join('/')}.`;
        if (data.aviso_enviado) {
          mensaje += `\nSe avisó a ${data.clientes_avisados} cliente${data.clientes_avisados === 1 ? '' : 's'} de esta lista.`;
        } else {
          mensaje += '\nNo se avisó a los clientes (quedó destildado). El precio va a cambiar igual el día programado.';
        }
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
        btnConfirmarVigencia.disabled = false;
        btnCancelarFechaVigencia.disabled = false;
        importandoTexto.style.display = 'none';
      }
    });
  }

  if (btnCancelarProgramada) {
    btnCancelarProgramada.addEventListener('click', async function () {
      if (!confirm('¿Cancelar la actualización de precios programada? Se avisará a los clientes que se canceló.')) {
        return;
      }

      const actualizacionId = bloqueProgramar.dataset.actualizacionId;
      btnCancelarProgramada.disabled = true;

      try {
        const response = await fetch(`/api/lista_precios/actualizaciones/${actualizacionId}/cancelar/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken')
          }
        });

        const data = await response.json();

        if (!response.ok) {
          alert(data.error || 'No se pudo cancelar la actualización.');
          btnCancelarProgramada.disabled = false;
          return;
        }

        window.location.reload();
      } catch (error) {
        alert('Ocurrió un error al cancelar la actualización.');
        console.error(error);
        btnCancelarProgramada.disabled = false;
      }
    });
  }
}