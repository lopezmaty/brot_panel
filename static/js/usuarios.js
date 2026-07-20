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
            rol: rol
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