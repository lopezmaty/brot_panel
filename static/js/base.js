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