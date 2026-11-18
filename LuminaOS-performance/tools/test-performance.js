'use strict';
// Run with node; only actual source scripts execute, in offline VM sandboxes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const tests = [], sandboxes = [];
const source = file => fs.readFileSync(path.join(ROOT, file), 'utf8');
const sourceLine = (file, needle) => {
  const text = source(file), index = text.indexOf(needle);
  assert.notEqual(index, -1, `Missing source marker ${file}: ${needle}`);
  return `${file}:${text.slice(0, index).split('\n').length}`;
};
function test(name, file, needle, fn) {
  const stack = new Error().stack;
  const line = stack.split('\n').find(line => /test-performance\.js:\d+/.test(line) && !/at test /.test(line));
  tests.push({ name, at: sourceLine(file, needle), testAt: line && line.trim(), fn });
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
const plain = value => JSON.parse(JSON.stringify(value));

class Timers {
  constructor() {
    this.now = Date.UTC(2024, 0, 1, 12, 34, 56, 789);
    this.next = 1; this.jobs = new Map(); this.frames = new Map(); this.frameRequests = 0;
  }
  add(fn, ms, kind) {
    const id = this.next++;
    this.jobs.set(id, { fn, ms, kind, due: this.now + ms });
    return id;
  }
  timeout(fn, ms) { return this.add(fn, ms, 'timeout'); }
  interval(fn, ms) { return this.add(fn, ms, 'interval'); }
  clear(id) { this.jobs.delete(id); }
  raf(fn) { const id = this.next++; this.frames.set(id, fn); this.frameRequests++; return id; }
  cancel(id) { this.frames.delete(id); }
  runFrames() {
    const frames = [...this.frames.values()]; this.frames.clear();
    frames.forEach(fn => fn(this.now));
  }
  async run(id) {
    const job = this.jobs.get(id);
    assert.ok(job, `Timer ${id} exists`);
    this.now = job.due;
    if (job.kind === 'timeout') this.jobs.delete(id);
    else job.due += job.ms;
    const result = job.fn();
    await flush();
    return result;
  }
  withDelay(ms) { return [...this.jobs.entries()].filter(([, job]) => job.ms === ms); }
}

function sandbox() {
  const timers = new Timers(), layout = [], elements = new Map(), errors = [];
  function record(kind, element, property = '') {
    const product = (new Error().stack.match(/src\/ui\/[\w/.\-]+:\d+:\d+/) || [])[0];
    layout.push({ kind, element: element.id || element.className, property, at: product || 'test fixture' });
  }
  class Events {
    constructor() { this.listeners = {}; }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    removeEventListener(name, fn) { this.listeners[name] = (this.listeners[name] || []).filter(x => x !== fn); }
    dispatch(name, extra = {}) {
      const event = { target: this, currentTarget: this, preventDefault() {}, stopPropagation() {}, ...extra };
      for (const fn of this.listeners[name] || []) fn(event);
    }
  }
  class Element extends Events {
    constructor(tag = 'div', id = '') {
      super(); this.tagName = tag; this.id = id; this.children = []; this.parentNode = null;
      this.dataset = {}; this.attributes = {}; this._classes = new Set();
      this._text = ''; this._html = ''; this.textWrites = 0; this.htmlWrites = 0;
      this.rect = { left: 0, top: 0, width: 50, height: 50, right: 50, bottom: 50 };
      this.offsetParent = {}; this.scrollTop = 0;
      this.classList = {
        add: (...names) => names.forEach(n => this._classes.add(n)),
        remove: (...names) => names.forEach(n => this._classes.delete(n)),
        contains: name => this._classes.has(name),
        toggle: (name, on) => {
          on = on === undefined ? !this._classes.has(name) : !!on;
          on ? this._classes.add(name) : this._classes.delete(name); return on;
        },
      };
      const values = {};
      this.style = new Proxy({
        setProperty: (key, value) => { record('write', this, key); values[key] = String(value); },
        getPropertyValue: key => values[key] || '',
      }, {
        set: (target, key, value) => { record('write', this, key); target[key] = value; return true; },
      });
    }
    get className() { return [...this._classes].join(' '); }
    set className(value) { this._classes = new Set(value.split(/\s+/).filter(Boolean)); }
    get textContent() { return this._text; }
    set textContent(value) { this._text = String(value); this.textWrites++; }
    get innerHTML() { return this._html; }
    set innerHTML(value) {
      this._html = value; this.htmlWrites++;
      this.children.forEach(child => { child.parentNode = null; }); this.children = [];
    }
    get firstChild() { return this.children[0] || null; }
    get nextSibling() {
      return this.parentNode ? this.parentNode.children[this.parentNode.children.indexOf(this) + 1] || null : null;
    }
    appendChild(child) { child.remove(); child.parentNode = this; this.children.push(child); return child; }
    prepend(child) { child.remove(); child.parentNode = this; this.children.unshift(child); }
    after(child) {
      const parent = this.parentNode; child.remove(); child.parentNode = parent;
      parent.children.splice(parent.children.indexOf(this) + 1, 0, child);
    }
    remove() {
      if (this.parentNode) this.parentNode.children.splice(this.parentNode.children.indexOf(this), 1);
      this.parentNode = null;
    }
    insertAdjacentHTML(where, text) { this._html += text; this.htmlWrites++; }
    setAttribute(key, value) { this.attributes[key] = value; }
    getBoundingClientRect() { record('read', this); return this.rect; }
    querySelectorAll(selector) { return descendants(this).filter(el => matches(el, selector)); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  }
  function descendants(element) { return element.children.flatMap(child => [child, ...descendants(child)]); }
  function matches(el, selector) {
    if (selector === '[data-hit]') return 'data-hit' in el.attributes;
    if (selector[0] === '#') return el.id === selector.slice(1);
    if (selector[0] === '.') return selector.slice(1).split('.').every(c => el.classList.contains(c));
    return el.tagName === selector;
  }
  const document = new Events(); document.hidden = false;
  document.documentElement = new Element('html', 'root'); document.body = new Element('body', 'body');
  document.createElement = tag => new Element(tag);
  document.getElementById = id => elements.get(id) || null;
  document.querySelectorAll = selector => [...new Set([...elements.values(), ...descendants(document.body)])].filter(el => matches(el, selector));
  document.querySelector = selector => document.querySelectorAll(selector)[0] || null;
  function addElement(id, className = '', parent = document.body) {
    const el = new Element('div', id); el.className = className;
    elements.set(id, el); parent.appendChild(el); return el;
  }
  class FakeDate extends Date {
    constructor(...args) { super(...(args.length ? args : [timers.now])); }
    static now() { return timers.now; }
  }
  const windowEvents = new Events();
  const context = vm.createContext({
    console: { log() {}, error: e => errors.push(e) }, document, Date: FakeDate,
    URL, URLSearchParams, location: { search: '', origin: 'http://127.0.0.1:7700' },
    screen: { width: 1280, height: 720 }, innerWidth: 1280, innerHeight: 400,
    setTimeout: (fn, ms) => timers.timeout(fn, ms), clearTimeout: id => timers.clear(id),
    setInterval: (fn, ms) => timers.interval(fn, ms), clearInterval: id => timers.clear(id),
    requestAnimationFrame: fn => timers.raf(fn), cancelAnimationFrame: id => timers.cancel(id),
    getComputedStyle: el => ({ position: 'fixed', getPropertyValue: key => el.style.getPropertyValue(key) || '44px' }),
    addEventListener: windowEvents.addEventListener.bind(windowEvents),
    removeEventListener: windowEvents.removeEventListener.bind(windowEvents),
    Image: class { set src(value) { this._src = value; } },
    ResizeObserver: class { observe() {} },
    fetch: () => { throw new Error('Real network access is forbidden'); },
    EventSource: class { constructor() { throw new Error('Real event connections are forbidden'); } },
  });
  context.window = context;
  vm.runInContext(source('src/ui/js/lumina.js'), context, { filename: 'src/ui/js/lumina.js' });
  const L = context.Lumina;
  L.settings = { theme: 'dark', accent: '#ff375f', wallpaper: 'fixture.jpg', reduceMotion: false,
    transparency: true, perfShadows: true, dockMagnify: true, widgets: false, performancePreset: 'balanced', clock24: true };
  const calls = [], unexpected = [], init = deferred(), windowInit = deferred();
  const env = { context, L, document, timers, layout, errors, elements, addElement, calls, unexpected, init,
    respondGet: endpoint => { unexpected.push(endpoint); throw new Error('Unexpected mocked GET'); },
    respondPost: endpoint => { unexpected.push(endpoint); throw new Error('Unexpected mocked POST'); } };
  sandboxes.push(env);
  L.get = async (endpoint, params) => { calls.push({ method: 'GET', endpoint, params }); return env.respondGet(endpoint, params); };
  L.post = async (endpoint, body) => { calls.push({ method: 'POST', endpoint, body }); return env.respondPost(endpoint, body); };
  L.init = () => init.promise;
  context.LWin = { minimized: false, args: [], init: () => windowInit.promise };
  env.eval = code => vm.runInContext(code, context, { filename: 'test-performance-fixture.js' });
  env.start = async () => { init.resolve(L.settings); await flush(); };
  env.load = file => {
    const text = source(file);
    // Fixtures need only literal IDs/classes; they never parse user filesystem data.
    for (const match of text.matchAll(/<([\w-]+)\b([^>]*\bid=["']([^"']+)["'][^>]*)>/g)) {
      const classes = (match[2].match(/\bclass=["']([^"']*)["']/) || [])[1] || '';
      const element = addElement(match[3], classes);
      if (/\bdata-hit\b/.test(match[2])) element.setAttribute('data-hit', '');
    }
    let count = 0;
    for (const match of text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
      if (/\bsrc\s*=/.test(match[1])) continue;
      const bodyStart = match.index + match[0].indexOf('>') + 1;
      const lineOffset = text.slice(0, bodyStart).split('\n').length - 1;
      vm.runInContext(match[2], context, { filename: file, lineOffset }); count++;
    }
    assert.ok(count > 0, `Actual inline scripts loaded from ${file}`);
  };
  return env;
}
const sample = () => ({ cpu: 37, mem: { percent: 42, used: 420, total: 1000 }, percpu: [37, 37],
  diskRead: 1, diskWrite: 2, netRecv: 3, netSent: 4, freq: 2400, uptime: 100, procs: 2,
  disk: { total: 1000, used: 100 }, swap: { total: 100, used: 0 } });
function fixtureDock() {
  const env = sandbox(); env.load('src/ui/dock.html');
  env.respondPost = (endpoint, body) => {
    assert.equal(endpoint, '/api/ui'); assert.equal(body.cmd, 'dockrect'); return { ok: true };
  };
  const dock = env.elements.get('dock');
  for (let i = 0; i < 4; i++) {
    const element = env.addElement(`item${i}`, 'it', dock);
    element.rect = { left: i * 50, top: 10, width: 50, height: 50, right: (i + 1) * 50, bottom: 60 };
  }
  return env;
}
function mockStatus(env) {
  env.respondGet = endpoint => {
    if (endpoint === '/api/audio') return { available: true, volume: 50, muted: false };
    if (endpoint === '/api/net') return { primary: { type: 'wifi' } };
    if (endpoint === '/api/windows') return [];
    throw new Error(`Unexpected endpoint ${endpoint}`);
  };
}

const SHARED = 'src/ui/js/lumina.js', DESKTOP = 'src/ui/desktop.html', DOCK = 'src/ui/dock.html';
const TOPBAR = 'src/ui/topbar.html', TASK = 'src/ui/apps/taskmgr.html';

test('preset response replaces optimism with authoritative server effects', SHARED, 'async setSettings(patch)', async () => {
  const env = sandbox(), pending = deferred();
  env.respondPost = () => pending.promise;
  const events = []; env.L.on('settings', s => events.push(s));
  const response = { ...env.L.settings, performancePreset: 'low-power', reduceMotion: true,
    transparency: false, dockMagnify: false, perfShadows: false };
  const result = env.L.setSettings({ performancePreset: 'low-power' });
  assert.equal(env.L.settings.performancePreset, 'low-power');
  assert.equal(env.L.settings.transparency, true, 'optimistic patch does not invent server expansion');
  pending.resolve(response);
  assert.strictEqual(await result, response);
  assert.strictEqual(env.L.settings, response);
  assert.deepEqual(plain(env.calls), [{ method: 'POST', endpoint: '/api/settings', body: { performancePreset: 'low-power' } }]);
  assert.deepEqual(events, [response]);
  assert.ok(env.document.documentElement.classList.contains('no-transparency'));
  assert.ok(env.document.documentElement.classList.contains('no-shadows'));
});

test('network errors roll back settings and classes without emitting success', SHARED, 'if (this.settings === optimistic)', async () => {
  const env = sandbox(), previous = env.L.settings, pending = deferred(), events = [];
  env.respondPost = () => pending.promise; env.L.on('settings', s => events.push(s));
  const result = env.L.setSettings({ transparency: false, perfShadows: false, reduceMotion: true });
  assert.equal(env.document.documentElement.style.getPropertyValue('--wall-blur'), 'none');
  pending.reject(new Error('offline'));
  await assert.rejects(result, /offline/);
  assert.strictEqual(env.L.settings, previous);
  for (const name of ['no-transparency', 'no-shadows', 'reduce-motion']) assert.ok(!env.document.documentElement.classList.contains(name));
  assert.match(env.document.documentElement.style.getPropertyValue('--wall-blur'), /\/api\/wallpaper\/blur/);
  assert.equal(events.length, 0);
});

test('invalid or error responses roll back instead of reporting a save', SHARED, "if (!s || s.error", async () => {
  for (const response of [null, {}, { error: 'invalid preset' }, { theme: false }]) {
    const env = sandbox(), previous = env.L.settings;
    env.respondPost = () => response;
    await assert.rejects(env.L.setSettings({ performancePreset: 'low-power' }));
    assert.strictEqual(env.L.settings, previous);
  }
});

test('failed older save cannot overwrite a newer authoritative settings event', SHARED, 'if (this.settings === optimistic)', async () => {
  const env = sandbox(), pending = deferred(); env.respondPost = () => pending.promise;
  const result = env.L.setSettings({ transparency: false });
  const newer = { ...env.L.settings, theme: 'light', performancePreset: 'custom' };
  env.L.settings = newer; env.L.applySettings();
  pending.reject(new Error('older failure'));
  await assert.rejects(result, /older failure/);
  assert.strictEqual(env.L.settings, newer);
  assert.ok(env.document.documentElement.classList.contains('light'));
});

test('applySettings removes blur and toggles shadows/motion both directions', SHARED, '    applySettings() {', () => {
  const env = sandbox(), h = env.document.documentElement;
  Object.assign(env.L.settings, { transparency: false, perfShadows: false, reduceMotion: true });
  env.L.applySettings();
  assert.equal(h.style.getPropertyValue('--wall-blur'), 'none');
  assert.ok(!h.style.getPropertyValue('--wall-blur').includes('/blur'));
  for (const name of ['no-transparency', 'no-shadows', 'reduce-motion']) assert.ok(h.classList.contains(name));
  Object.assign(env.L.settings, { transparency: true, perfShadows: true, reduceMotion: false });
  env.L.applySettings();
  assert.match(h.style.getPropertyValue('--wall-blur'), /\/api\/wallpaper\/blur/);
  for (const name of ['no-transparency', 'no-shadows', 'reduce-motion']) assert.ok(!h.classList.contains(name));
  assert.equal(env.calls.length, 0);
});

test('reduced-motion CSS caps animation iteration count at one', 'src/ui/css/lumina.css', '.reduce-motion *', () => {
  const css = source('src/ui/css/lumina.css').replace(/\/\*[\s\S]*?\*\//g, '');
  const rule = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].find(m => m[1].trim().startsWith('.reduce-motion *'));
  assert.ok(rule);
  for (const selector of ['.reduce-motion *', '.reduce-motion *::before', '.reduce-motion *::after']) assert.ok(rule[1].split(',').map(s => s.trim()).includes(selector));
  const declarations = Object.fromEntries(rule[2].split(';').filter(d => d.includes(':')).map(d => {
    const colon = d.indexOf(':'); return [d.slice(0, colon).trim(), d.slice(colon + 1).trim()];
  }));
  assert.equal(declarations['animation-iteration-count'], '1 !important');
  assert.equal(declarations['animation-duration'], '1ms !important');
  assert.equal(declarations['transition-duration'], '1ms !important');
});

test('two unchanged desktop reloads preserve exact DOM identity and resolve places once', DESKTOP, 'async function loadIcons', async () => {
  const env = sandbox(); env.load(DESKTOP);
  let items = [{ name: 'fixture.txt', path: '/fixture/Desktop/fixture.txt', size: 10, mtime: 20, mime: 'text/plain', dir: false }];
  env.respondGet = endpoint => {
    if (endpoint === '/api/fs/places') return { places: [{ icon: 'desktop', path: '/fixture/Desktop' }] };
    if (endpoint === '/api/fs/list') return { items };
    throw new Error(`Unexpected endpoint ${endpoint}`);
  };
  await env.eval('loadIcons()');
  const box = env.elements.get('icons'), first = [...box.children], writes = box.htmlWrites;
  assert.equal(first.length, 3, 'actual renderer constructed desktop icons');
  first[2].classList.add('sel');
  await env.eval('loadIcons()'); await env.eval('loadIcons()');
  assert.equal(box.htmlWrites, writes);
  assert.ok(first.every((el, i) => box.children[i] === el));
  assert.ok(box.children[2].classList.contains('sel'));
  assert.equal(env.calls.filter(c => c.endpoint === '/api/fs/places').length, 1);
  assert.equal(env.calls.filter(c => c.endpoint === '/api/fs/list').length, 3);
  items = [{ ...items[0], mtime: 21 }];
  await env.eval('loadIcons()');
  assert.equal(box.htmlWrites, writes + 1, 'changed metadata actually rebuilds icons');
  assert.notStrictEqual(box.children[2], first[2]);
  await env.eval('loadIcons(true)');
  assert.equal(box.htmlWrites, writes + 2, 'explicit force refresh rebuilds unchanged icons');
  assert.equal(env.calls.filter(c => c.endpoint === '/api/fs/places').length, 1);
});

test('desktop caches absence of a desktop place and serializes overlapping reloads', DESKTOP, 'if (iconsLoading)', async () => {
  const env = sandbox(), pending = deferred(); env.load(DESKTOP);
  env.respondGet = endpoint => { assert.equal(endpoint, '/api/fs/places'); return pending.promise; };
  const initial = env.eval('loadIcons()');
  await env.eval('loadIcons()'); await env.eval('loadIcons(true)');
  assert.equal(env.calls.length, 1);
  pending.resolve({ places: [] }); await initial; await flush();
  assert.equal(env.elements.get('icons').children.length, 2);
  await env.eval('loadIcons()');
  assert.equal(env.calls.length, 1, 'missing place is resolved once, not on every reload');
});

test('disabled widget has no timers; enable/disable and preset changes avoid duplicates', DESKTOP, 'function apply(s)', async () => {
  const env = sandbox(); env.load(DESKTOP); env.respondGet = endpoint => { assert.equal(endpoint, '/api/stats'); return sample(); };
  env.eval('apply(L.settings)'); env.eval('apply(L.settings)');
  assert.equal(env.timers.jobs.size, 0);
  await env.eval('stats()'); assert.equal(env.calls.length, 0);
  env.L.settings.widgets = true;
  env.eval('apply(L.settings)'); await flush();
  assert.equal(env.timers.jobs.size, 2);
  assert.equal(env.timers.withDelay(1000).length, 1); assert.equal(env.timers.withDelay(3000).length, 1);
  const ids = [...env.timers.jobs.keys()];
  env.eval('apply(L.settings)'); env.eval('apply(L.settings)'); await flush();
  assert.deepEqual([...env.timers.jobs.keys()], ids);
  assert.equal(env.calls.length, 1);
  env.L.settings.performancePreset = 'low-power'; env.eval('apply(L.settings)'); await flush();
  assert.equal(env.timers.jobs.size, 2); assert.equal(env.timers.withDelay(3000).length, 0);
  assert.equal(env.timers.withDelay(10000).length, 1);
  env.L.settings.widgets = false; env.eval('apply(L.settings)');
  assert.equal(env.timers.jobs.size, 0);
  env.L.settings.widgets = true; env.eval('apply(L.settings)'); await flush();
  assert.equal(env.timers.jobs.size, 2);
  env.L.settings.widgets = false; env.eval('apply(L.settings)'); assert.equal(env.timers.jobs.size, 0);
});

test('desktop startup with widgets disabled only schedules icon reload', DESKTOP, 'L.init().then', async () => {
  const env = sandbox(); env.load(DESKTOP);
  env.respondGet = endpoint => { assert.equal(endpoint, '/api/fs/places'); return { places: [] }; };
  await env.start();
  assert.equal(env.timers.jobs.size, 1); assert.equal(env.timers.withDelay(15000).length, 1);
  assert.ok(!env.calls.some(c => c.endpoint === '/api/stats'));
});

test('dock coalesces 100 mousemoves into exactly one animation frame using latest position', DOCK, "addEventListener('mousemove'", () => {
  const env = fixtureDock(), dock = env.elements.get('dock');
  // Isolate the magnification phase; full-frame ordering is checked separately.
  env.eval('updateGlass = () => {}'); env.layout.length = 0;
  for (let i = 0; i < 100; i++) dock.dispatch('mousemove', { clientX: i });
  assert.equal(env.timers.frameRequests, 1); assert.equal(env.timers.frames.size, 1);
  assert.equal(env.layout.length, 0, 'no synchronous geometry or writes per event');
  assert.equal(env.eval('mx'), 99);
  env.timers.runFrames();
  const reads = env.layout.filter(x => x.kind === 'read'), writes = env.layout.filter(x => x.kind === 'write');
  assert.equal(reads.length, 4); assert.equal(writes.length, 4);
  const firstWrite = env.layout.findIndex(x => x.kind === 'write');
  assert.ok(env.layout.slice(firstWrite).every(x => x.kind === 'write'), 'all icon geometry reads precede scale writes');
  assert.equal(env.timers.frames.size, 0);
  dock.dispatch('mousemove', { clientX: 120 }); assert.equal(env.timers.frameRequests, 2);
});

test('dock schedules zero frames when reduced motion or magnification disabled', DOCK, 'function magnifyEnabled()', () => {
  for (const settings of [{ reduceMotion: true, dockMagnify: true }, { reduceMotion: false, dockMagnify: false }]) {
    const env = fixtureDock(), dock = env.elements.get('dock'); Object.assign(env.L.settings, settings);
    env.layout.length = 0;
    for (let i = 0; i < 100; i++) dock.dispatch('mousemove', { clientX: i });
    dock.dispatch('mouseleave');
    assert.equal(env.timers.frameRequests, 0); assert.equal(env.timers.jobs.size, 0); assert.equal(env.layout.length, 0);
  }
});

test('dock reset cancels pending magnification and restores unit scales', DOCK, 'function resetMagnify()', () => {
  const env = fixtureDock(), dock = env.elements.get('dock'); env.eval('updateGlass = () => {}');
  dock.dispatch('mousemove', { clientX: 25 }); env.timers.runFrames();
  assert.notEqual(dock.children[0].style.getPropertyValue('--k'), '1.000');
  dock.dispatch('mousemove', { clientX: 100 }); assert.equal(env.timers.frames.size, 1);
  env.L.settings.reduceMotion = true; env.eval('resetMagnify()');
  assert.equal(env.timers.frames.size, 0);
  for (const el of dock.children) assert.equal(el.style.getPropertyValue('--k'), '1.000');
});

test('full dock frame performs all geometry reads before any style write', DOCK, 'function magnify()', () => {
  const env = fixtureDock(), dock = env.elements.get('dock');
  env.layout.length = 0; dock.dispatch('mousemove', { clientX: 99 }); env.timers.runFrames();
  const firstWrite = env.layout.findIndex(x => x.kind === 'write');
  assert.ok(firstWrite >= 0);
  const laterRead = env.layout.slice(firstWrite + 1).find(x => x.kind === 'read');
  assert.ok(!laterRead, `Read after style write: ${JSON.stringify(env.layout[firstWrite])} -> ${JSON.stringify(laterRead)}`);
});

test('updateGlass batches dock and bell geometry before style mutations', DOCK, 'function updateGlass()', () => {
  const env = fixtureDock(); env.layout.length = 0; env.eval('updateGlass()');
  const firstWrite = env.layout.findIndex(x => x.kind === 'write');
  const laterRead = env.layout.slice(firstWrite + 1).find(x => x.kind === 'read');
  assert.ok(!laterRead, `Read after style write: ${JSON.stringify(env.layout[firstWrite])} -> ${JSON.stringify(laterRead)}`);
});

test('topbar clock schedules exact minute boundaries and avoids unchanged text writes', TOPBAR, 'function tick()', async () => {
  const env = sandbox(); env.load(TOPBAR); mockStatus(env); await env.start();
  const date = env.elements.get('date'), clock = env.elements.get('time');
  const expected = 60000 - env.timers.now % 60000;
  assert.equal(env.timers.withDelay(expected).length, 1);
  const writes = [date.textWrites, clock.textWrites];
  env.eval('tick()'); env.eval('tick()');
  assert.deepEqual([date.textWrites, clock.textWrites], writes);
  assert.equal(env.timers.withDelay(expected).length, 1, 'rescheduling does not duplicate clock timers');
  await env.timers.run(env.timers.withDelay(expected)[0][0]);
  assert.equal(clock.textWrites, writes[1] + 1);
  assert.equal(date.textWrites, writes[0]);
  assert.equal(env.timers.withDelay(60000).length, 1);
});

test('topbar stops both timers and polling while hidden, resumes on visibility', TOPBAR, 'function refreshTimers()', async () => {
  const env = sandbox(); env.load(TOPBAR); mockStatus(env); await env.start();
  assert.equal(env.timers.jobs.size, 2);
  env.document.hidden = true; env.document.dispatch('visibilitychange');
  assert.equal(env.timers.jobs.size, 0);
  const calls = env.calls.length;
  await env.eval('refresh()'); env.eval('tick()');
  assert.equal(env.calls.length, calls); assert.equal(env.timers.jobs.size, 0);
  env.document.hidden = false; env.document.dispatch('visibilitychange'); await flush();
  assert.equal(env.timers.jobs.size, 2); assert.equal(env.calls.length, calls + 2);
});

test('topbar status timer waits for both requests, avoids overlap and recovers rejection', TOPBAR, 'async function refresh()', async () => {
  const env = sandbox(), requests = []; env.load(TOPBAR);
  let active = 0, maxActive = 0;
  env.respondGet = endpoint => {
    if (endpoint === '/api/windows') return [];
    assert.ok(['/api/audio', '/api/net'].includes(endpoint));
    const pending = deferred(); requests.push({ endpoint, pending }); active++; maxActive = Math.max(maxActive, active);
    return pending.promise.finally(() => { active--; });
  };
  await env.start();
  assert.equal(requests.length, 2); assert.equal(env.timers.withDelay(20000).length, 0);
  await env.eval('refresh()'); await env.eval('refresh()');
  assert.equal(requests.length, 2);
  requests[0].pending.reject(new Error('temporary audio failure')); await flush();
  assert.equal(requests.length, 2, 'no new cycle before network settles');
  assert.equal(env.timers.withDelay(20000).length, 0);
  requests[1].pending.resolve({ primary: { type: 'wifi' } }); await flush();
  assert.equal(requests.length, 4, 'coalesced pending refresh runs once after prior requests settle');
  assert.equal(maxActive, 2, 'two endpoints per cycle, never two overlapping cycles');
  requests[2].pending.resolve({ available: true, volume: 50 }); requests[3].pending.resolve({ primary: { type: 'wifi' } }); await flush();
  assert.equal(env.timers.withDelay(20000).length, 1);
  const timer = env.timers.withDelay(20000)[0][0];
  const running = env.timers.run(timer); await flush();
  assert.equal(requests.length, 6); assert.equal(env.timers.withDelay(20000).length, 0);
  requests[4].pending.reject(new Error('audio down')); requests[5].pending.reject(new Error('network down')); await running;
  assert.equal(env.timers.withDelay(20000).length, 1, 'rejections schedule recovery, not a stuck loading flag');
  assert.equal(env.eval('statusLoading'), false);
});

test('topbar low-power uses sixty-second awaited status interval without duplicates', TOPBAR, "performancePreset === 'low-power' ? 60000", async () => {
  const env = sandbox(); env.load(TOPBAR); mockStatus(env); await env.start();
  assert.equal(env.timers.withDelay(20000).length, 1);
  env.L.settings.performancePreset = 'low-power'; env.L.emit('settings', env.L.settings); await flush();
  assert.equal(env.timers.withDelay(20000).length, 0);
  assert.equal(env.timers.withDelay(60000).length, 1);
  const statusId = env.eval('statusTimer'); assert.equal(env.timers.jobs.get(statusId).ms, 60000);
  env.L.emit('settings', env.L.settings); env.L.emit('settings', env.L.settings); await flush();
  assert.equal(env.timers.jobs.size, 2); assert.equal(env.timers.withDelay(60000).length, 1);
});

test('topbar unchanged tray icons have no repeated innerHTML writes and events beat stale responses', TOPBAR, 'function setIcon(id, icon)', async () => {
  const env = sandbox(); env.load(TOPBAR); mockStatus(env); await env.start();
  const vol = env.elements.get('vol'), net = env.elements.get('net');
  const writes = [vol.htmlWrites, net.htmlWrites];
  await env.eval('refresh()'); assert.deepEqual([vol.htmlWrites, net.htmlWrites], writes);
  const audio = deferred(), network = deferred();
  env.respondGet = endpoint => endpoint === '/api/audio' ? audio.promise : network.promise;
  const refresh = env.eval('refresh()');
  env.L.emit('audio', { available: true, volume: 0, muted: true });
  env.L.emit('net', { primary: { type: 'ethernet' } });
  const eventIcons = [vol.innerHTML, net.innerHTML];
  audio.resolve({ available: true, volume: 80 }); network.resolve({ primary: { type: 'wifi' } }); await refresh;
  assert.deepEqual([vol.innerHTML, net.innerHTML], eventIcons);
});

test('topbar hiding in-flight status suppresses stale DOM and resuming still refreshes', TOPBAR, 'if (generation !== statusGeneration', async () => {
  const env = sandbox(), audio = deferred(), network = deferred(); env.load(TOPBAR);
  env.respondGet = endpoint => endpoint === '/api/windows' ? [] : endpoint === '/api/audio' ? audio.promise : network.promise;
  await env.start(); env.document.hidden = true; env.document.dispatch('visibilitychange');
  audio.resolve({ available: true, volume: 80 }); network.resolve({ primary: { type: 'wifi' } }); await flush();
  assert.equal(env.elements.get('vol').htmlWrites, 0); assert.equal(env.elements.get('net').htmlWrites, 0);
  assert.equal(env.timers.jobs.size, 0); assert.equal(env.eval('statusLoading'), false);
  mockStatus(env); env.document.hidden = false; env.document.dispatch('visibilitychange'); await flush();
  assert.equal(env.elements.get('vol').htmlWrites, 1); assert.equal(env.timers.jobs.size, 2);
});

function taskFixture() {
  const env = sandbox(); env.load(TASK); env.context.renders = [];
  // Rendering is not under test here; preserve actual poll/refreshProcs execution.
  env.eval("R.proc = () => renders.push('proc'); R.det = () => renders.push('det'); R.perf = () => renders.push('perf');");
  env.respondGet = endpoint => {
    if (endpoint === '/api/stats') return sample();
    if (endpoint === '/api/procs') return [{ pid: 10, name: 'fixture', cpu: 1, mem: 10 }];
    throw new Error(`Unexpected endpoint ${endpoint}`);
  };
  return env;
}

test('taskmgr poll skips hidden, minimized and every non-monitoring page', TASK, 'async function poll()', async () => {
  const env = taskFixture();
  env.document.hidden = true; await env.eval('poll()');
  env.document.hidden = false; env.context.LWin.minimized = true; await env.eval('poll()');
  env.context.LWin.minimized = false;
  for (const page of ['hist', 'start', 'users', 'svc']) { env.eval(`page = ${JSON.stringify(page)}`); await env.eval('poll()'); }
  assert.equal(env.calls.length, 0); assert.equal(env.eval('tick'), 0); assert.equal(env.eval('hist.cpu.length'), 0);
  for (const page of ['proc', 'perf', 'det']) {
    env.eval(`page = ${JSON.stringify(page)}`); await env.eval('poll()');
  }
  assert.equal(env.calls.filter(c => c.endpoint === '/api/stats').length, 3);
  assert.equal(env.eval('tick'), 3);
});

test('taskmgr ignores concurrent polls including awaited process fetches', TASK, 'if (pollBusy', async () => {
  const env = taskFixture(), stats = deferred(), procs = deferred();
  env.respondGet = endpoint => endpoint === '/api/stats' ? stats.promise : procs.promise;
  const first = env.eval('poll()');
  for (let i = 0; i < 100; i++) await env.eval('poll()');
  assert.equal(env.calls.length, 1); assert.equal(env.eval('pollBusy'), true);
  stats.resolve(sample()); await first;
  assert.equal(env.eval('pollBusy'), false);
  const second = env.eval('poll()'); await flush();
  assert.equal(env.calls.filter(c => c.endpoint === '/api/procs').length, 1);
  assert.equal(env.eval('pollBusy'), true);
  await env.eval('poll()'); await env.eval('poll()');
  assert.equal(env.calls.filter(c => c.endpoint === '/api/stats').length, 2);
  procs.resolve([{ pid: 10 }]); await second;
  assert.equal(env.eval('pollBusy'), false); assert.deepEqual(env.context.renders, ['proc']);
});

test('taskmgr rejection releases poll lock and state/visibility resume monitoring', TASK, "L.on('state'", async () => {
  const env = taskFixture();
  env.respondGet = () => Promise.reject(new Error('temporary stats failure'));
  await env.eval('poll()'); assert.equal(env.eval('pollBusy'), false); assert.equal(env.eval('tick'), 0);
  env.respondGet = endpoint => endpoint === '/api/stats' ? sample() : [{ pid: 10 }];
  env.context.LWin.minimized = true; env.L.emit('state', { minimized: true }); await flush();
  assert.equal(env.calls.length, 1);
  env.context.LWin.minimized = false; env.L.emit('state', { minimized: false }); await flush();
  assert.equal(env.eval('tick'), 1);
  env.document.hidden = true; env.document.dispatch('visibilitychange'); await flush();
  assert.equal(env.eval('tick'), 1);
  env.document.hidden = false; env.document.dispatch('visibilitychange'); await flush();
  assert.equal(env.eval('tick'), 2); assert.equal(env.eval('pollBusy'), false);
});

test('taskmgr history remains capped at sixty actual samples', TASK, 'if (hist[k].length > N)', async () => {
  const env = taskFixture(); env.eval("page = 'perf'");
  for (let i = 0; i < 75; i++) await env.eval('poll()');
  for (const key of ['cpu', 'mem', 'disk', 'net']) assert.equal(env.eval(`hist.${key}.length`), 60);
  assert.equal(env.eval('coreHist.length'), 60); assert.equal(env.calls.length, 75);
});

(async () => {
  let passed = 0, failed = 0;
  for (const entry of tests) {
    const sandboxStart = sandboxes.length;
    try {
      await entry.fn(); await flush();
      for (const env of sandboxes.slice(sandboxStart)) {
        assert.deepEqual(env.errors, [], 'source event handlers must not swallow test failures');
        assert.deepEqual(env.unexpected, [], 'source must not make unexpected mocked API calls');
      }
      passed++;
      process.stdout.write(`PASS ${entry.name} [${entry.at}]\n`);
    } catch (error) {
      failed++;
      process.stderr.write(`FAIL ${entry.name} [${entry.at}]\n${entry.testAt || ''}\n${error.stack}\n`);
    }
  }
  process.stdout.write(`JS SUMMARY: ${tests.length} tests, ${passed} passed, ${failed} failed\n`);
  process.exitCode = failed ? 1 : 0;
})().catch(error => { process.stderr.write(`${error.stack}\n`); process.exitCode = 1; });
