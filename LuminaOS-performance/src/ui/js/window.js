/* LuminaOS app window chrome: Win11 caption buttons + snap layouts, macOS-style motion */
(function () {
  const L = window.Lumina;
  const M = parseInt(L.qs.get('m') || '16', 10);
  let ARGS = [];
  try { ARGS = JSON.parse(L.qs.get('args') || '[]'); } catch (e) { }
  const SNAP = [
    { cols: '1fr 1fr', rows: '1fr', cells: [['left', '1/2', '1/2'], ['right', '2/3', '1/2']] },
    { cols: '2fr 1fr', rows: '1fr', cells: [['left', '1/2', '1/2'], ['right', '2/3', '1/2']] },
    { cols: '1fr 1fr 1fr', rows: '1fr', cells: [['left3', '1/2', '1/2'], ['center3', '2/3', '1/2'], ['right3', '3/4', '1/2']] },
    { cols: '1fr 1fr', rows: '1fr 1fr', cells: [['tl', '1/2', '1/2'], ['tr', '2/3', '1/2'], ['bl', '1/2', '2/3'], ['br', '2/3', '2/3']] },
    { cols: '1fr 1fr', rows: '1fr 1fr', cells: [['left', '1/2', '1/3'], ['tr', '2/3', '1/2'], ['br', '2/3', '2/3']] },
    { cols: '1fr', rows: '1fr', cells: [['max', '1/2', '1/2']] },
  ];

  const W = window.LWin = {
    args: ARGS, maximized: false, focused: true,
    init(opts) {
      opts = opts || {};
      document.documentElement.style.setProperty('--m', M + 'px');
      const body = document.body;
      const content = Array.from(body.childNodes);
      body.innerHTML = `<div id="win"><div class="titlebar" id="tb">
          ${opts.icon !== false ? `<img class="ti" src="${opts.icon || ''}">` : ''}<span class="tt" id="tt">${L.esc(opts.title || document.title)}</span>
          <div id="tbslot" style="display:contents"></div><div class="drag"></div>
          <div class="caps"><button class="mn" title="Minimise">${L.icon('minus')}</button><button class="mx" title="Maximise">${L.icon('max')}</button><button class="cl" title="Close">${L.icon('x')}</button></div>
          <div class="snapfly" id="snapfly"></div>
        </div><div class="win-body" id="wb"></div></div>
        <div id="rzwrap">${['n', 's', 'e', 'w', 'nw', 'ne', 'sw', 'se'].map(e => `<div class="rz ${e}" data-e="${e}"></div>`).join('')}</div>`;
      const wb = document.getElementById('wb');
      content.forEach(n => wb.appendChild(n));
      if (opts.titlebar) document.getElementById('tbslot').innerHTML = opts.titlebar;

      const tb = document.getElementById('tb');
      tb.addEventListener('mousedown', e => {
        if (e.button !== 0 || e.target.closest('button,input,.caps,.snapfly,.tab,.nodrag')) return;
        if (e.detail === 2) { L.native('maximize'); return; }
        L.native('move', { x: e.screenX, y: e.screenY });
      });
      tb.addEventListener('dblclick', e => { if (!e.target.closest('button,input,.caps,.tab,.nodrag')) L.native('maximize'); });
      tb.querySelector('.mn').onclick = () => W.minimize();
      tb.querySelector('.mx').onclick = () => L.native('maximize');
      tb.querySelector('.cl').onclick = () => W.close();
      document.querySelectorAll('.rz').forEach(r => r.addEventListener('mousedown', e => {
        if (e.button === 0) { e.preventDefault(); L.native('resize', { edge: r.dataset.e, x: e.screenX, y: e.screenY }); }
      }));

      // snap layouts flyout (Win11)
      const fly = document.getElementById('snapfly');
      fly.innerHTML = SNAP.map(s => `<div class="lay" style="grid-template-columns:${s.cols};grid-template-rows:${s.rows}">${s.cells.map(c => `<i data-z="${c[0]}" style="grid-column:${c[1]};grid-row:${c[2]}"></i>`).join('')}</div>`).join('');
      fly.querySelectorAll('i').forEach(i => i.onclick = () => { fly.classList.remove('on'); L.native('snap', { zone: i.dataset.z }); });
      let ht, ot;
      const mx = tb.querySelector('.mx');
      const show = () => { clearTimeout(ot); ht = setTimeout(() => !W.maximized && fly.classList.add('on'), 450); };
      const hide = () => { clearTimeout(ht); ot = setTimeout(() => fly.classList.remove('on'), 300); };
      mx.addEventListener('mouseenter', show); mx.addEventListener('mouseleave', hide);
      fly.addEventListener('mouseenter', () => clearTimeout(ot)); fly.addEventListener('mouseleave', hide);

      L.on('state', s => {
        W.maximized = !!s.maximized; W.focused = s.focused !== false; W.minimized = !!s.minimized;
        document.documentElement.classList.toggle('maximized', W.maximized);
        document.documentElement.classList.toggle('inactive', !W.focused);
        mx.innerHTML = L.icon(W.maximized ? 'restore' : 'max');
        mx.title = W.maximized ? 'Restore down' : 'Maximise';
      });
      L.on('closing', () => W.close());
      L.on('restored', () => {
        const w = document.getElementById('win');
        w.classList.remove('minimizing'); void w.offsetWidth; w.classList.add('restoring');
        setTimeout(() => w.classList.remove('restoring'), 450);
      });
      L.on('args', a => { W.args = a || []; opts.onArgs && opts.onArgs(W.args); });
      document.addEventListener('keydown', e => {
        if (e.key === 'F11') { e.preventDefault(); L.native('maximize'); }
        if (e.ctrlKey && e.key.toLowerCase() === 'w' && opts.ctrlW !== false) { e.preventDefault(); W.close(); }
      });
      return L.init().then(s => { opts.onReady && opts.onReady(W.args); return s; });
    },
    setTitle(t) { document.getElementById('tt').textContent = t; L.native('title', { title: t }); },
    close() {
      if (W._closing) return; W._closing = true;
      const w = document.getElementById('win'); w.classList.add('closing');
      setTimeout(() => L.native('close-now'), L.settings && L.settings.reduceMotion ? 0 : 190);
    },
    minimize() {
      const w = document.getElementById('win'); w.classList.remove('restoring'); w.classList.add('minimizing');
      setTimeout(() => { L.native('minimize'); }, L.settings && L.settings.reduceMotion ? 0 : 280);
    },
  };
})();
