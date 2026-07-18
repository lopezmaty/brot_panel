function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function borrarUsuario(userId) {
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