function confirmarAccion(mensaje) {
  document.getElementById('confirmMessage').textContent = mensaje;
  document.getElementById('modalConfirm').classList.add('open');

  return new Promise(function (resolve) {
    document.getElementById('btnConfirmAccept').onclick = function () {
      document.getElementById('modalConfirm').classList.remove('open');
      resolve(true);
    };
    document.getElementById('btnConfirmCancel').onclick = function () {
      document.getElementById('modalConfirm').classList.remove('open');
      resolve(false);
    };
  });
}

function aplicarTema(tema) {
  const icono = document.getElementById('themeIcon');
  if (tema === 'dark') {
    document.body.classList.add('dark-mode');
    if (icono) icono.className = 'ti ti-sun';
  } else {
    document.body.classList.remove('dark-mode');
    if (icono) icono.className = 'ti ti-moon';
  }
}

const temaGuardado = localStorage.getItem('tema') || 'light';
aplicarTema(temaGuardado);

document.getElementById('themeToggle').addEventListener('click', function () {
  const esOscuro = document.body.classList.contains('dark-mode');
  const nuevoTema = esOscuro ? 'light' : 'dark';
  aplicarTema(nuevoTema);
  localStorage.setItem('tema', nuevoTema);
});