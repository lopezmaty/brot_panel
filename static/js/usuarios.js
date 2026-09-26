function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function borrarUsuario(userId) {

    const confirmado = await confirmarAccion('¿Estás seguro que querés borrar este usuario?');
    if (confirmado !== true) {
        return;
    }

    const url = `/api/users/usuarios/${userId}/`;

    const response = await fetch(url, {
        method: 'DELETE', 
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
    if (response.ok)  {
        location.reload();
    } else {
        alert('No se pudo borrar el usuario');
    }
}

document.querySelectorAll('.btn-delete').forEach(function (boton) {
  boton.addEventListener('click', function () {
    const userId = boton.dataset.userId;
    borrarUsuario(userId)
  });
});

document.getElementById('btnCrearUsuario').addEventListener('click', function () {
  document.getElementById('modalCrear').classList.add('open');
});

document.getElementById('btnCancelarCrear').addEventListener('click', function () {
  document.getElementById('modalCrear').classList.remove('open');
});

async function crearUsuario() {
    const username = document.getElementById('inputUsername').value;
    const email = document.getElementById('inputEmail').value;
    const rol = document.getElementById('inputRol').value;
    const nombre = document.getElementById('inputNombre').value.trim();

    const url = '/api/users/usuarios/';

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            username: username,
            email: email,
            rol: rol,
            nombre: nombre
        })
    });

    if (response.ok) {
        location.reload();
    } else {
        alert('No se pudo crear el usuario');
    }
}

document.getElementById('formCrearUsuario').addEventListener('submit', function (evento) {
    evento.preventDefault();
    crearUsuario();
});

async function guardarNombre(input, boton) {
    const nombre = input.value.trim();
    if (nombre === input.dataset.guardado) return;

    boton.disabled = true;
    boton.innerHTML = '<i class="ti ti-loader-2"></i> Guardando...';

    const response = await fetch(`/api/users/usuarios/${input.dataset.userId}/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ nombre: nombre })
    });

    if (response.ok) {
        input.value = nombre;
        input.dataset.guardado = nombre;
        boton.innerHTML = '<i class="ti ti-check"></i> Guardado';
        bpToast(nombre ? `Nombre guardado: ${nombre}` : 'Nombre borrado', 'ti-check');
        setTimeout(function () { boton.innerHTML = '<i class="ti ti-device-floppy"></i> Guardar'; }, 1800);
    } else {
        alert('No se pudo guardar el nombre');
        boton.disabled = false;
        boton.innerHTML = '<i class="ti ti-device-floppy"></i> Guardar';
    }
}

document.querySelectorAll('.input-nombre').forEach(function (input) {
    const boton = input.parentElement.querySelector('.btn-guardar-nombre');
    input.dataset.guardado = input.value;

    input.addEventListener('input', function () {
        boton.disabled = input.value.trim() === input.dataset.guardado;
        boton.innerHTML = '<i class="ti ti-device-floppy"></i> Guardar';
    });
    input.addEventListener('keydown', function (evento) {
        if (evento.key === 'Enter' && !boton.disabled) guardarNombre(input, boton);
    });
    boton.addEventListener('click', function () { guardarNombre(input, boton); });
});