/* =========================================================
   Brot Panel — comportamiento común del panel (base.html)
========================================================= */

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

function bpCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function bpEscape(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ---------- Avisos flotantes (toasts) ---------- */
function bpToast(mensaje, icono) {
  const cont = document.getElementById('bpToasts');
  if (!cont) return;
  const el = document.createElement('div');
  el.className = 'bp-toast';
  el.innerHTML = `<i class="ti ${icono || 'ti-info-circle'}"></i>${bpEscape(mensaje)}`;
  cont.appendChild(el);
  setTimeout(() => { el.classList.add('out'); el.addEventListener('animationend', () => el.remove()); }, 2800);
}

/* ---------- Tema claro / oscuro ---------- */
function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  document.body.classList.toggle('dark-mode', tema === 'dark');
  const icono = document.getElementById('themeIcon');
  if (icono) icono.className = tema === 'dark' ? 'ti ti-sun' : 'ti ti-moon';
}

(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
  const leer = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };

  aplicarTema(document.documentElement.dataset.theme || 'light');

  /* ---------- Tablas con scroll lateral ----------
     Muchas tablas viven dentro de tarjetas con overflow:hidden; en pantallas
     chicas no se podían deslizar. Se envuelven en un contenedor con scroll,
     también las que los módulos dibujan después por JS. */
  function envolverTablas(raiz) {
    raiz.querySelectorAll('table').forEach(t => {
      const padre = t.parentElement;
      if (!padre || padre.classList.contains('bp-table-scroll') || padre.closest('table')) return;
      const ox = getComputedStyle(padre).overflowX;
      if (ox === 'auto' || ox === 'scroll') return;
      const envoltura = document.createElement('div');
      envoltura.className = 'bp-table-scroll';
      padre.insertBefore(envoltura, t);
      envoltura.appendChild(t);
    });
  }
  const contenido = document.querySelector('.content');
  if (contenido) {
    envolverTablas(contenido);
    let pendiente = false;
    new MutationObserver(() => {
      if (pendiente) return;
      pendiente = true;
      requestAnimationFrame(() => { pendiente = false; envolverTablas(contenido); });
    }).observe(contenido, { childList: true, subtree: true });
  }

  $('#themeToggle').addEventListener('click', function (e) {
    const nuevo = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    guardar('tema', nuevo);
    if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) return aplicarTema(nuevo);
    const x = e.clientX, y = e.clientY;
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    document.documentElement.classList.add('bp-no-vt');
    const vt = document.startViewTransition(() => aplicarTema(nuevo));
    vt.ready.then(() => {
      document.documentElement.animate(
        { clipPath: [`circle(0 at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
        { duration: 550, easing: 'cubic-bezier(.2,.8,.2,1)', pseudoElement: '::view-transition-new(root)' });
    }).catch(() => {});
    vt.finished.finally(() => document.documentElement.classList.remove('bp-no-vt'));
  });

  /* ---------- Link activo + migas de pan ---------- */
  const path = location.pathname;
  let activo = null, largo = -1;
  $$('#bpNav a.bp-nav-link[href], #userDropdown a[data-label]').forEach(a => {
    const rutas = [a.getAttribute('href'), a.dataset.also].filter(Boolean);
    rutas.forEach(r => {
      if (path.startsWith(r) && r.length > largo) { activo = a; largo = r.length; }
    });
  });
  if (activo) {
    activo.classList.add('active');
    const grupo = activo.closest('.bp-nav-group');
    const seccion = grupo ? grupo.querySelector('.bp-nav-group-btn span').textContent : '';
    const titulo = activo.dataset.label;
    $('#bpCrumbs').innerHTML = activo.getAttribute('href') === '/dashboard/'
      ? '<strong>Inicio</strong>'
      : `<a href="/dashboard/" class="bp-crumb-extra">Inicio</a><i class="ti ti-chevron-right bp-crumb-extra"></i>${seccion ? `<span class="bp-crumb-extra">${bpEscape(seccion)}</span><i class="ti ti-chevron-right bp-crumb-extra"></i>` : ''}<strong>${bpEscape(titulo)}</strong>`;
    if (activo.getAttribute('href') !== path && !activo.dataset.also?.startsWith(path)) {
      // Estamos en una sub-página (ej. /clientes/12/): el título del módulo vuelve al listado
      $('#bpCrumbs strong').outerHTML = `<a href="${activo.getAttribute('href')}">${bpEscape(titulo)}</a>`;
      const h = document.querySelector('.content .page-title');
      if (h) $('#bpCrumbs').insertAdjacentHTML('beforeend', `<i class="ti ti-chevron-right"></i><strong>${bpEscape(h.textContent.trim())}</strong>`);
    }
  }

  /* ---------- Grupos del menú ---------- */
  let cerrados = [];
  try { cerrados = JSON.parse(leer('panel.gruposCerrados') || '[]'); } catch (e) {}
  $$('.bp-nav-group').forEach(g => {
    if (cerrados.includes(g.dataset.g) && !g.querySelector('.active')) g.classList.add('closed');
  });
  $$('.bp-nav-group-btn').forEach(b => b.addEventListener('click', () => {
    b.parentElement.classList.toggle('closed');
    guardar('panel.gruposCerrados', JSON.stringify($$('.bp-nav-group.closed').map(x => x.dataset.g)));
  }));

  /* ---------- Menú colapsable / móvil ---------- */
  function setColapsado(v) {
    document.documentElement.classList.toggle('bp-colapsado', v);
    $('#sidebarToggle i').className = 'ti ' + (v ? 'ti-layout-sidebar-left-expand' : 'ti-layout-sidebar-left-collapse');
    guardar('panel.colapsado', v ? '1' : '0');
  }
  setColapsado(document.documentElement.classList.contains('bp-colapsado'));
  $('#sidebarToggle').addEventListener('click', () => setColapsado(!document.documentElement.classList.contains('bp-colapsado')));
  $('#bpMobileBtn').addEventListener('click', () => $('#bpApp').classList.add('mobile-open'));
  $('#bpScrim').addEventListener('click', () => $('#bpApp').classList.remove('mobile-open'));
  $('#bpSubnav').addEventListener('click', e => { if (e.target.closest('button')) $('#bpApp').classList.remove('mobile-open'); });

  /* ---------- Menú de usuario ---------- */
  $('#userMenuToggle').addEventListener('click', e => { e.stopPropagation(); $('#userDropdown').classList.toggle('open'); });
  document.addEventListener('click', e => {
    if (!e.target.closest('#userDropdown')) $('#userDropdown').classList.remove('open');
    if (!e.target.closest('.bp-notif')) $('#bpNotifPanel').classList.remove('open');
  });

  /* ---------- Barra superior con blur al scrollear ---------- */
  const topbar = $('#bpTopbar');
  addEventListener('scroll', () => topbar.classList.toggle('scrolled', scrollY > 8), { passive: true });

  /* ---------- Notificaciones ---------- */
  const NIVEL_COLOR = { info: '#3AAFE4', exito: '#22B07D', alerta: '#F59E0B', error: '#E5484D' };
  let noLeidasPrevias = null;

  function pintarNotificaciones(data) {
    const badge = $('#bpNotifCount');
    badge.hidden = !data.no_leidas;
    badge.textContent = data.no_leidas > 99 ? '99+' : data.no_leidas;
    if (noLeidasPrevias !== null && data.no_leidas > noLeidasPrevias) {
      badge.classList.remove('pulse'); void badge.offsetWidth; badge.classList.add('pulse');
      const nueva = data.items.find(n => !n.leida);
      if (nueva) bpToast(nueva.titulo, nueva.icono);
    }
    noLeidasPrevias = data.no_leidas;
    $('#bpNotifAll').hidden = !data.no_leidas;
    $('#bpNotifList').innerHTML = data.items.length ? data.items.map(n => `
      <a class="bp-notif-item ${n.leida ? '' : 'unread'}" data-id="${n.id}" href="${n.url ? bpEscape(n.url) : '#'}" style="--c:${NIVEL_COLOR[n.nivel] || NIVEL_COLOR.info}">
        <span class="bp-notif-ic"><i class="ti ${bpEscape(n.icono)}"></i></span>
        <span class="bp-notif-txt">
          <strong>${bpEscape(n.titulo)}</strong>
          ${n.mensaje ? `<p>${bpEscape(n.mensaje)}</p>` : ''}
          <small>${bpEscape(n.hace)}</small>
        </span>
      </a>`).join('')
      : '<div class="bp-notif-empty"><i class="ti ti-bell-check"></i>No tenés notificaciones.</div>';
  }

  function cargarNotificaciones() {
    return fetch('/notificaciones/', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) pintarNotificaciones(d); })
      .catch(() => {});
  }

  function postNotif(url) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': bpCookie('csrftoken') || '' } }).catch(() => {});
  }

  $('#bpNotifBtn').addEventListener('click', e => {
    e.stopPropagation();
    const panel = $('#bpNotifPanel');
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) cargarNotificaciones();
  });
  $('#bpNotifList').addEventListener('click', e => {
    const item = e.target.closest('.bp-notif-item');
    if (!item) return;
    const href = item.getAttribute('href');
    if (item.classList.contains('unread')) {
      e.preventDefault();
      item.classList.remove('unread');
      postNotif(`/notificaciones/${item.dataset.id}/leer/`).then(() => {
        if (href && href !== '#') location.href = href; else cargarNotificaciones();
      });
    } else if (href === '#') e.preventDefault();
  });
  $('#bpNotifAll').addEventListener('click', e => {
    e.stopPropagation();
    postNotif('/notificaciones/leer-todas/').then(cargarNotificaciones);
  });

  cargarNotificaciones();
  setInterval(() => { if (!document.hidden) cargarNotificaciones(); }, 60000);

  /* ---------- Buscador (Ctrl+K) ---------- */
  const modulos = $$('#bpNav a.bp-nav-link[href], #userDropdown a[data-label]').map(a => {
    const grupo = a.closest('.bp-nav-group');
    return {
      t: a.dataset.label,
      href: a.getAttribute('href'),
      i: a.dataset.icon || 'ti-point',
      c: a.dataset.c || '#8A9BB8',
      g: grupo ? grupo.querySelector('.bp-nav-group-btn span').textContent : 'Panel',
    };
  });
  const acciones = [
    { t: 'Cambiar tema claro / oscuro', g: 'Acción', i: 'ti-contrast', c: '#8A9BB8', run: () => $('#themeToggle').click() },
    { t: 'Colapsar / expandir menú', g: 'Acción', i: 'ti-layout-sidebar', c: '#8A9BB8', run: () => $('#sidebarToggle').click() },
    { t: 'Ver notificaciones', g: 'Acción', i: 'ti-bell', c: '#F07030', run: () => setTimeout(() => $('#bpNotifBtn').click(), 50) },
  ];
  let recientes = [];
  try { recientes = JSON.parse(leer('panel.recientes') || '[]'); } catch (e) {}
  if (activo && activo.getAttribute('href') !== '/dashboard/') {
    recientes = [activo.getAttribute('href'), ...recientes.filter(h => h !== activo.getAttribute('href'))].slice(0, 4);
    guardar('panel.recientes', JSON.stringify(recientes));
  }

  let resultados = [], sel = 0;
  const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  function resaltar(texto, q) {
    if (!q) return bpEscape(texto);
    const i = norm(texto).indexOf(norm(q));
    if (i < 0) return bpEscape(texto);
    return bpEscape(texto.slice(0, i)) + '<mark>' + bpEscape(texto.slice(i, i + q.length)) + '</mark>' + bpEscape(texto.slice(i + q.length));
  }
  function pintarPaleta() {
    const q = $('#bpPaletteInput').value.trim();
    let secciones;
    if (!q) {
      const rec = recientes.map(h => modulos.find(m => m.href === h)).filter(Boolean);
      secciones = [...(rec.length ? [['Recientes', rec]] : []), ['Módulos', modulos.filter(m => !rec.includes(m))], ['Acciones', acciones]];
    } else {
      const nq = norm(q);
      const coincide = x => norm(x.t + ' ' + x.g).includes(nq);
      secciones = [['Módulos', modulos.filter(coincide)], ['Acciones', acciones.filter(coincide)]].filter(s => s[1].length);
    }
    resultados = secciones.flatMap(s => s[1]);
    sel = Math.min(sel, Math.max(resultados.length - 1, 0));
    let k = 0;
    $('#bpPaletteList').innerHTML = resultados.length ? secciones.map(([nombre, arr]) => `
      <div class="bp-palette-section">${nombre}</div>
      ${arr.map(x => `
        <div class="bp-palette-item ${k === sel ? 'sel' : ''}" data-k="${k++}" style="--c:${x.c}">
          <span class="pi-icon"><i class="ti ${x.i}"></i></span>
          <span class="pi-text"><strong>${resaltar(x.t, q)}</strong><small>${bpEscape(x.g)}</small></span>
          <i class="ti ti-corner-down-left pi-enter"></i>
        </div>`).join('')}`).join('')
      : `<div class="bp-palette-empty">Sin resultados para “${bpEscape(q)}”</div>`;
  }
  function marcarSel() {
    $$('.bp-palette-item').forEach(el => el.classList.toggle('sel', +el.dataset.k === sel));
    const s = $('.bp-palette-item.sel'); if (s) s.scrollIntoView({ block: 'nearest' });
  }
  function ejecutar() {
    const x = resultados[sel];
    if (!x) return;
    cerrarPaleta();
    if (x.run) x.run(); else location.href = x.href;
  }
  function abrirPaleta() {
    $('#bpOverlay').classList.add('open');
    $('#bpPaletteInput').value = '';
    sel = 0;
    pintarPaleta();
    $('#bpPaletteInput').focus();
  }
  function cerrarPaleta() { $('#bpOverlay').classList.remove('open'); }

  $$('[data-bp-palette]').forEach(b => b.addEventListener('click', abrirPaleta));
  $('#bpOverlay').addEventListener('click', e => { if (e.target.id === 'bpOverlay') cerrarPaleta(); });
  $('#bpPaletteList').addEventListener('mousemove', e => {
    const it = e.target.closest('.bp-palette-item');
    if (it && +it.dataset.k !== sel) { sel = +it.dataset.k; marcarSel(); }
  });
  $('#bpPaletteList').addEventListener('click', e => { if (e.target.closest('.bp-palette-item')) ejecutar(); });
  $('#bpPaletteInput').addEventListener('input', () => { sel = 0; pintarPaleta(); });
  $('#bpPaletteInput').addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = (sel + 1) % resultados.length; marcarSel(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); sel = (sel - 1 + resultados.length) % resultados.length; marcarSel(); }
    if (e.key === 'Enter') { e.preventDefault(); ejecutar(); }
  });

  const escribiendo = () => /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $('#bpOverlay').classList.contains('open') ? cerrarPaleta() : abrirPaleta();
    }
    if (e.key === 'Escape') {
      cerrarPaleta();
      $('#userDropdown').classList.remove('open');
      $('#bpNotifPanel').classList.remove('open');
      $('#bpApp').classList.remove('mobile-open');
    }
    if (e.key === '[' && !escribiendo() && !$('.modal-overlay.open')) $('#sidebarToggle').click();
  });
})();
