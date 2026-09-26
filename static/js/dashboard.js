/* =========================================================
   Inicio: widgets, favoritos y filtros del acceso rápido
========================================================= */
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const leer = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
  const guardar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };

  /* ---------- Saludo según la hora ---------- */
  const h = new Date().getHours();
  $('#bpSaludo').textContent = h < 13 ? 'Buen día' : h < 20 ? 'Buenas tardes' : 'Buenas noches';

  /* ---------- Mini gráficos de los últimos 7 días ---------- */
  $$('.bp-spark[data-serie]').forEach((svg, n) => {
    const nodo = document.getElementById(svg.dataset.serie);
    if (!nodo) return;
    const serie = JSON.parse(nodo.textContent).map(Number);
    const max = Math.max(...serie), min = Math.min(...serie);
    if (max === 0) { svg.remove(); return; }
    const pts = serie.map((v, i) => [i * (120 / (serie.length - 1)), 40 - ((v - min) / ((max - min) || 1)) * 30]);
    const linea = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    const color = svg.dataset.color;
    svg.innerHTML = `
      <defs><linearGradient id="bpg${n}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".25"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
      <path d="${linea} L120 46 L0 46Z" fill="url(#bpg${n})"/>
      <path class="line" d="${linea}" stroke="${color}"/>`;
  });

  /* ---------- Números que cuentan hacia arriba ---------- */
  $$('[data-count]').forEach(el => {
    const fin = +el.dataset.count || 0, pre = el.dataset.prefix || '';
    if (!fin) return;
    const t0 = performance.now(), dur = 1100;
    const paso = ahora => {
      const p = Math.min((ahora - t0) / dur, 1);
      el.textContent = pre + Math.round(fin * (1 - Math.pow(1 - p, 4))).toLocaleString('es-AR');
      if (p < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  });

  /* ---------- Aparición escalonada ---------- */
  const io = new IntersectionObserver(entries => entries.forEach(en => {
    if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
  }), { threshold: .06 });
  const observar = () => $$('.bp-reveal:not(.in)').forEach(el => io.observe(el));

  /* ---------- Favoritos ---------- */
  let favoritos = leer('panel.favoritos', ['centro_pedidos', 'control_caja']);
  const tarjetas = $$('.bp-mod[data-mod]');
  tarjetas.forEach(t => { t._grid = t.parentElement; });

  function ubicarTarjetas() {
    const favGrid = $('#bpFavGrid');
    tarjetas.forEach(t => {
      const fav = favoritos.includes(t.dataset.mod);
      const pin = t.querySelector('.bp-pin');
      pin.classList.toggle('on', fav);
      pin.title = fav ? 'Quitar de favoritos' : 'Fijar en favoritos';
      pin.querySelector('i').className = 'ti ' + (fav ? 'ti-star-filled' : 'ti-star');
      if (!fav && t.parentElement !== t._grid) t._grid.appendChild(t);
    });
    favoritos.forEach(id => { const t = tarjetas.find(x => x.dataset.mod === id); if (t) favGrid.appendChild(t); });
    // Devolver el orden original dentro de cada grupo
    new Set(tarjetas.map(t => t._grid)).forEach(g => tarjetas.filter(t => t._grid === g && t.parentElement === g).forEach(t => g.appendChild(t)));
    const disabled = $$('.bp-mod.disabled');
    disabled.forEach(d => d.parentElement.appendChild(d));
    let vacio = favGrid.querySelector('.bp-fav-empty');
    if (!favGrid.querySelector('.bp-mod')) {
      if (!vacio) favGrid.insertAdjacentHTML('beforeend', '<div class="bp-fav-empty"><i class="ti ti-star"></i>Fijá los módulos que más usás con la estrella para tenerlos siempre acá arriba.</div>');
    } else if (vacio) vacio.remove();
    $$('.bp-group[data-group]').forEach(g => { g.hidden = !g.querySelector('.bp-mod') || (filtro !== 'todos' && g.dataset.group !== filtro); });
    $('[data-fav-group]').hidden = filtro !== 'todos';
  }

  $$('.bp-pin').forEach(b => b.addEventListener('click', e => {
    e.preventDefault(); e.stopPropagation();
    const id = b.dataset.pin;
    const agregar = !favoritos.includes(id);
    favoritos = agregar ? [...favoritos, id] : favoritos.filter(x => x !== id);
    guardar('panel.favoritos', favoritos);
    const titulo = b.closest('.bp-mod').querySelector('h3').textContent;
    if (document.startViewTransition) {
      document.documentElement.classList.add('bp-no-vt');
      document.startViewTransition(ubicarTarjetas).finished.finally(() => document.documentElement.classList.remove('bp-no-vt'));
    } else ubicarTarjetas();
    if (window.bpToast) bpToast(agregar ? `${titulo} fijado en favoritos` : `${titulo} quitado de favoritos`, agregar ? 'ti-star-filled' : 'ti-star-off');
  }));

  /* ---------- Spotlight que sigue al mouse ---------- */
  tarjetas.forEach(t => t.addEventListener('pointermove', e => {
    const r = t.getBoundingClientRect();
    t.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    t.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }));

  /* ---------- Filtro por categoría ---------- */
  let filtro = 'todos';
  const grupos = $$('.bp-group[data-group]').map(g => g.dataset.group);
  $('#bpChips').insertAdjacentHTML('beforeend', ['todos', ...grupos].map(g =>
    `<button type="button" class="bp-chip ${g === filtro ? 'active' : ''}" data-f="${g}">${g === 'todos' ? 'Todos' : g}</button>`).join(''));
  function moverPill() {
    const a = $('.bp-chip.active');
    if (!a) return;
    $('#bpChipPill').style.left = a.offsetLeft + 'px';
    $('#bpChipPill').style.width = a.offsetWidth + 'px';
  }
  $$('.bp-chip').forEach(c => c.addEventListener('click', () => {
    filtro = c.dataset.f;
    $$('.bp-chip').forEach(x => x.classList.toggle('active', x === c));
    moverPill();
    // Al filtrar, los favoritos vuelven a su grupo para que la categoría se vea completa
    if (filtro !== 'todos') tarjetas.forEach(t => { if (t.parentElement !== t._grid) t._grid.appendChild(t); });
    ubicarTarjetas();
    if (filtro !== 'todos') tarjetas.forEach(t => { if (t.parentElement !== t._grid) t._grid.appendChild(t); });
    $$('.bp-group[data-group]').forEach(g => { g.hidden = filtro !== 'todos' && g.dataset.group !== filtro; });
  }));
  requestAnimationFrame(moverPill);
  if (document.fonts) document.fonts.ready.then(moverPill);
  addEventListener('resize', moverPill);

  $$('.bp-mod').forEach((t, i) => { t.classList.add('bp-reveal'); t.style.setProperty('--i', Math.min(i, 10)); });
  ubicarTarjetas();
  observar();
})();
