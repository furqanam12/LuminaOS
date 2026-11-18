/* LuminaOS client library (shared by shell and apps) */
(function () {
  const P = {
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    taskview: '<rect x="3" y="6" width="13" height="13" rx="2.5"/><path d="M8 3h10.5A2.5 2.5 0 0 1 21 5.5V16"/>',
    bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 21h4"/>',
    belloff: '<path d="M6 16V11a6 6 0 0 1 9.5-4.9M18 11v5l1.5 2H8"/><path d="M10 21h4M3 3l18 18"/>',
    wifi: '<path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.5a9.5 9.5 0 0 1 13 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.3" r=".9" fill="currentColor"/>',
    ethernet: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4M7 9h1M11 9h2M16 9h1"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    volume: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4.2 4.2 0 0 1 0 6M18.2 6.5a8 8 0 0 1 0 11"/>',
    volumex: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M16 9.5l5 5M21 9.5l-5 5"/>',
    volumelow: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4.2 4.2 0 0 1 0 6"/>',
    monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    contrast: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>',
    bluetooth: '<path d="M7 7l10 10-5 4V3l5 4L7 17"/>',
    focus: '<path d="M12 3a9 9 0 1 0 9 9"/><path d="M15 3.5l2 2 3.5-3.5"/>',
    scissors: '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8 16.5L19 4M16 16.5L5 4"/>',
    snip: '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><rect x="8" y="8" width="8" height="8" rx="1"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 0 1-4 0v-.1A1.7 1.7 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 1.2 14H1a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 2.6 7a1.6 1.6 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 5 2.3l.1.1a1.6 1.6 0 0 0 1.8.3H7a1.7 1.7 0 0 0 1-1.5V1a2 2 0 0 1 4 0v.1A1.7 1.7 0 0 0 16.9 2.6a1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V7a1.7 1.7 0 0 0 1.5 1H23a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" transform="translate(1.2 1.2) scale(.9)"/>',
    lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    power: '<path d="M12 3v8"/><path d="M6.6 6.6a8 8 0 1 0 10.8 0"/>',
    restart: '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3 4v4.5h4.5"/>',
    sleep: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    logout: '<path d="M14 4h4.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14"/><path d="M10 8l-4 4 4 4M6 12h10"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 20.5a8 8 0 0 1 16 0"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14a6.5 6.5 0 0 1 3.5 6"/>',
    chevr: '<path d="M9 5l7 7-7 7"/>', chevl: '<path d="M15 5l-7 7 7 7"/>', chevd: '<path d="M5 9l7 7 7-7"/>', chevu: '<path d="M5 15l7-7 7 7"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>', minus: '<path d="M5 12h14"/>', plus: '<path d="M12 5v14M5 12h14"/>',
    max: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    restore: '<rect x="4.5" y="8" width="11.5" height="11.5" rx="2"/><path d="M8 5h9.5A2.5 2.5 0 0 1 20 7.5V16"/>',
    folder: '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2.5h7.5A2.5 2.5 0 0 1 21 10v7.5a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z"/>',
    file: '<path d="M6 3h8l5 5v11.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19.5v-15A1.5 1.5 0 0 1 6.5 3z"/><path d="M14 3v5h5"/>',
    filetext: '<path d="M6 3h8l5 5v11.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19.5v-15A1.5 1.5 0 0 1 6.5 3z"/><path d="M14 3v5h5M8.5 13h7M8.5 16.5h7"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="9.5" r="1.8"/><path d="M21 15.5l-5-5L5 20"/>',
    music: '<path d="M9 18V5.5l11-2V16"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
    video: '<rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="M16 10.5l5-3v9l-5-3"/>',
    download: '<path d="M12 4v11M7 10.5l5 5 5-5M4.5 20h15"/>',
    desktop: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    home: '<path d="M3.5 10.5L12 3.5l8.5 7V19a1.5 1.5 0 0 1-1.5 1.5h-4.5v-6h-5v6H5A1.5 1.5 0 0 1 3.5 19z"/>',
    star: '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 16.9l-5.2 2.8 1-5.9-4.3-4.1 5.9-.8z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    trash: '<path d="M4 6.5h16M9.5 6.5V4.5h5v2M6 6.5l1 13a1.5 1.5 0 0 0 1.5 1.5h7a1.5 1.5 0 0 0 1.5-1.5l1-13"/>',
    copy: '<rect x="8.5" y="8.5" width="12" height="12" rx="2"/><path d="M15.5 8.5V5A1.5 1.5 0 0 0 14 3.5H5A1.5 1.5 0 0 0 3.5 5v9A1.5 1.5 0 0 0 5 15.5h3.5"/>',
    cut: '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8 16.5L19 4M16 16.5L5 4"/>',
    paste: '<rect x="5" y="4.5" width="14" height="16.5" rx="2"/><rect x="9" y="3" width="6" height="3.5" rx="1"/>',
    rename: '<path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="M14.5 7.5l3 3"/>',
    edit: '<path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z"/>',
    share: '<circle cx="18" cy="5.5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="18.5" r="2.5"/><path d="M8.2 10.8l7.6-4M8.2 13.2l7.6 4"/>',
    sort: '<path d="M7 4v16M3.5 16.5L7 20l3.5-3.5M17 20V4M13.5 7.5L17 4l3.5 3.5"/>',
    grid: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>',
    list: '<path d="M8.5 6h12M8.5 12h12M8.5 18h12"/><circle cx="4.2" cy="6" r=".9" fill="currentColor"/><circle cx="4.2" cy="12" r=".9" fill="currentColor"/><circle cx="4.2" cy="18" r=".9" fill="currentColor"/>',
    more: '<circle cx="5.5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="18.5" cy="12" r="1.2" fill="currentColor"/>',
    refresh: '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20.5 4v4.5H16"/>',
    left: '<path d="M19 12H5M11 6l-6 6 6 6"/>', right: '<path d="M5 12h14M13 6l6 6-6 6"/>', up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    drive: '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M5 13l2.2-7.2A1.5 1.5 0 0 1 8.6 4.7h6.8a1.5 1.5 0 0 1 1.4 1.1L19 13"/><circle cx="16.5" cy="16.5" r=".9" fill="currentColor"/>',
    usb: '<rect x="7" y="9" width="10" height="12" rx="2"/><path d="M9 9V3.5h6V9M10.5 6h0M13.5 6h0"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r=".9" fill="currentColor"/>',
    apps: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="3.25"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>',
    shield: '<path d="M12 3l7.5 3v5.5c0 4.5-3.2 8.2-7.5 9.5-4.3-1.3-7.5-5-7.5-9.5V6z"/>',
    palette: '<path d="M12 3a9 9 0 0 0 0 18c1.2 0 1.8-.8 1.8-1.7 0-1.1-.9-1.4-.9-2.5 0-.9.7-1.6 1.7-1.6H17a4 4 0 0 0 4-4C21 6.6 17 3 12 3z"/><circle cx="7.5" cy="11.5" r="1.1" fill="currentColor"/><circle cx="10" cy="7.5" r="1.1" fill="currentColor"/><circle cx="15" cy="7.5" r="1.1" fill="currentColor"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
    memory: '<rect x="3" y="7" width="18" height="10" rx="1.5"/><path d="M7 7v10M11 7v10M15 7v10M5 20v-3M19 20v-3"/>',
    disk: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    rocket: '<path d="M12 15l-3-3c1.5-4.5 4.5-8 10-9-1 5.5-4.5 8.5-9 10z"/><path d="M9 12H5l2.5-3.5H11M12 15v4l3.5-2.5V13"/><path d="M6 16c-1.5 1-2 3.5-2 4 .5 0 3-.5 4-2"/>',
    puzzle: '<path d="M10 4a2 2 0 0 1 4 0v1.5h4.5V10H17a2 2 0 0 0 0 4h1.5v4.5H14V17a2 2 0 0 0-4 0v1.5H5.5V14H7a2 2 0 0 0 0-4H5.5V5.5H10z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    battery: '<rect x="2.5" y="7" width="17" height="10" rx="2.5"/><path d="M21.5 10.5v3"/><rect x="5" y="9.5" width="9" height="5" rx="1" fill="currentColor"/>',
    keyboard: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6 10h0M9.5 10h0M13 10h0M16.5 10h0M7 14h10"/>',
    mouse: '<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v3"/>',
    printer: '<path d="M6.5 9V3.5h11V9"/><rect x="3" y="9" width="18" height="8" rx="2"/><rect x="6.5" y="14" width="11" height="6.5" rx="1"/>',
    android: '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    windows: '<rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.2"/><rect x="13" y="3.5" width="7.5" height="7.5" rx="1.2"/><rect x="3.5" y="13" width="7.5" height="7.5" rx="1.2"/><rect x="13" y="13" width="7.5" height="7.5" rx="1.2"/>',
    update: '<path d="M20 12a8 8 0 0 1-14.3 4.9M4 12a8 8 0 0 1 14.3-4.9"/><path d="M18.5 3v4.5H14M5.5 21v-4.5H10"/>',
    bag: '<path d="M5 8h14l-1.2 11.5A1.7 1.7 0 0 1 16.1 21H7.9a1.7 1.7 0 0 1-1.7-1.5z"/><path d="M9 10V6.5a3 3 0 0 1 6 0V10"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    play: '<path d="M7 4.5v15l12.5-7.5z"/>', pause: '<path d="M8 5v14M16 5v14"/>',
    sparkle: '<path d="M12 3c.8 4.6 2.4 6.2 7 7-4.6.8-6.2 2.4-7 7-.8-4.6-2.4-6.2-7-7 4.6-.8 6.2-2.4 7-7z"/>',
    calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    layout: '<rect x="3.5" y="4" width="17" height="16" rx="2.5"/><path d="M12 4v16M12 12h8.5"/>',
    access: '<circle cx="12" cy="4.5" r="1.8"/><path d="M5 8.5l7 1.5 7-1.5M12 10v4.5l-3.5 6.5M12 14.5l3.5 6.5"/>',
    language: '<path d="M4 5h8M8 3v2M5.5 5c.5 3.5 3 6.5 6.5 8M10.5 5c-.5 3.5-2.5 6-6.5 8"/><path d="M12.5 21l4-10 4 10M14 17.5h5"/>',
    pin: '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    sliders: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    leaf: '<path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15z"/><path d="M5 19l7-7"/>',
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M7 9l3 3-3 3M12.5 15h4.5"/>',
    hdd: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 14h18"/><circle cx="17" cy="16.5" r=".9" fill="currentColor"/>',
    pinned: '<path d="M9 4h6l-1 6 3 3H7l3-3zM12 13v8"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    zoomin: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M8 11h6M11 8v6"/>',
    zoomout: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M8 11h6"/>',
    rotate: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 3.5V8h4.5"/>',
    bolt: '<path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z"/>',
    send: '<path d="M21 3L10 14M21 3l-7 18-4-7-7-4z"/>',
    save: '<path d="M5 3.5h11l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 19V5a1.5 1.5 0 0 1 1-1.5z"/><path d="M8 3.5V8h7V3.5M7.5 20.5v-6h9v6"/>',
    undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    redo: '<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    bold: '<path d="M7 4.5h6a3.75 3.75 0 0 1 0 7.5H7zM7 12h7a4 4 0 0 1 0 8H7z"/>',
    tab: '<rect x="3" y="5" width="18" height="15" rx="2.5"/><path d="M3 9.5h8V5"/>',
    timer: '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 9.5v4l2.5 1.5M10 2.5h4"/>',
    window: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3 8.5h18"/>',
    region: '<rect x="4" y="4" width="16" height="16" rx="1.5" stroke-dasharray="3 2.5"/>',
    fullscreen: '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/>',
    note: '<rect x="4.5" y="3" width="15" height="18" rx="2.5"/><path d="M8.5 8h7M8.5 12h7M8.5 16h4"/>',
    calc: '<rect x="5" y="2.5" width="14" height="19" rx="2.5"/><rect x="8" y="5.5" width="8" height="4" rx="1"/><path d="M8.5 13h0M12 13h0M15.5 13h0M8.5 17h0M12 17h0M15.5 17h0"/>',
  };
  function icon(name, cls) {
    const p = P[name] || P.apps;
    return `<svg class="${cls || 'ic'}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  }

  const qs = new URLSearchParams(location.search);
  const L = window.Lumina = {
    icon, icons: P, qs, settings: null, sys: null, geom: null, listeners: {}, ready: false,
    win: qs.get('win') || '',
    async get(path, params) {
      const u = new URL(path, location.origin);
      if (params) Object.entries(params).forEach(([k, v]) => v != null && u.searchParams.set(k, v));
      const r = await fetch(u);
      const ct = r.headers.get('content-type') || '';
      return ct.includes('json') ? r.json() : r.text();
    },
    async post(path, body) {
      const h = { 'Content-Type': 'application/json' };
      const tok = localStorage.getItem('lumina-token');
      if (tok) h['X-Lumina-Token'] = tok;
      const r = await fetch(path, { method: 'POST', headers: h, body: JSON.stringify(body || {}) });
      if (r.status === 401) {
        try { const j = await r.json(); if (j.error === 'authentication required') { const t = await this.get('/api/auth/token'); if (t.token) { localStorage.setItem('lumina-token', t.token); h['X-Lumina-Token'] = t.token; return this.post(path, body); } } } catch (_) {}
      }
      return r.json().catch(() => ({}));
    },
    on(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },
    emit(ev, data) { (this.listeners[ev] || []).forEach(f => { try { f(data); } catch (e) { console.error(e); } }); },
    native(cmd, extra) {
      try { window.webkit.messageHandlers.lumina.postMessage(JSON.stringify(Object.assign({ cmd }, extra || {}))); } catch (e) { }
    },
    _native(m) { if (m.event === 'geom') { this.geom = m.data; this.applyGeom(); } this.emit(m.event, m.data); },
    launch(id, args) { return this.post('/api/launch', { id, args: args || [] }); },
    app(name, args) { return this.post('/api/run', { cmd: 'lumina-app ' + name + (args ? ' ' + args.map(a => "'" + String(a).replace(/'/g, "'\\''") + "'").join(' ') : '') }); },
    ui(cmd, extra) { return this.post('/api/ui', Object.assign({ cmd }, extra || {})); },
    notify(title, body, icon, app) { return this.post('/api/notify', { title, body, icon, app }); },
    async setSettings(patch) {
      const previous = this.settings, optimistic = Object.assign({}, previous, patch);
      this.settings = optimistic; this.applySettings();
      try {
        const s = await this.post('/api/settings', patch);
        if (!s || s.error || typeof s.theme !== 'string') throw new Error(s && s.error || 'Could not save settings');
        this.settings = s; this.applySettings(); this.emit('settings', s);
        return s;
      } catch (e) {
        if (this.settings === optimistic) { this.settings = previous; this.applySettings(); }
        throw e;
      }
    },

    applyGeom() {
      const g = this.geom || { w: screen.width, h: screen.height };
      const r = document.documentElement.style;
      r.setProperty('--scr-w', g.w + 'px'); r.setProperty('--scr-h', g.h + 'px');
    },
    applySettings() {
      const s = this.settings; if (!s) return;
      const h = document.documentElement;
      h.classList.toggle('reduce-motion', s.reduceMotion === true);
      h.classList.toggle('dark', s.theme !== 'light');
      h.classList.toggle('light', s.theme === 'light');
      h.classList.toggle('reduce-motion', !!s.reduceMotion);
      h.classList.toggle('no-transparency', s.transparency === false);
      h.classList.toggle('no-shadows', s.perfShadows === false);
      h.classList.toggle('high-contrast', !!s.highContrast);
      h.classList.toggle('strong-focus', !!s.strongFocus);
      const scale = Math.max(80, Math.min(150, Number(s.uiScale) || 100)) / 100;
      h.style.setProperty('--ui-scale', String(scale));
      // Scale app windows only. Shell windows are positioned with screen
      // coordinates, so zooming them would invalidate hit regions.
      if (document.body && L.qs.has('m')) document.body.style.zoom = scale === 1 ? '' : String(scale);
      const a = s.accent || '#ff375f';
      const rgb = [1, 3, 5].map(i => parseInt(a.substr(i, 2), 16));
      h.style.setProperty('--accent', a);
      h.style.setProperty('--accent-rgb', rgb.join(','));
      h.style.setProperty('--accent-2', `rgb(${rgb.map(c => Math.min(255, c + 40)).join(',')})`);
      const wv = encodeURIComponent(s.wallpaper);
      h.style.setProperty('--wall-blur', s.transparency === false ? 'none' : `url("/api/wallpaper/blur?name=${wv}&theme=${s.theme}")`);
      h.style.setProperty('--wall', `url("/api/wallpaper/file?name=${wv}")`);
      this.applyGeom();
    },
    appIcon(app) {
      if (!app) return '/ui/img/apps/launchpad.svg';
      const id = typeof app === 'string' ? app : app.id;
      if (id && id.startsWith('lumina-')) return '/ui/img/apps/' + id.replace('lumina-', '').replace('.desktop', '') + '.svg';
      const map = { 'firefox-esr.desktop': 'browser', 'firefox.desktop': 'browser' };
      if (map[id]) return '/ui/img/apps/' + map[id] + '.svg';
      const ic = typeof app === 'string' ? '' : app.icon;
      return ic ? '/api/icon?size=128&name=' + encodeURIComponent(ic) : '/ui/img/apps/launchpad.svg';
    },
    connect() {
      const es = new EventSource('/api/events');
      es.onmessage = (e) => {
        let m; try { m = JSON.parse(e.data); } catch (_) { return; }
        if (m.event === 'settings') { this.settings = m.data; this.applySettings(); }
        this.emit(m.event, m.data);
      };
      es.onerror = () => { es.close(); setTimeout(() => this.connect(), 1500); this.emit('disconnected'); };
      es.onopen = () => this.emit('connected');
    },
    async init() {
      for (let i = 0; i < 60; i++) {
        try { this.settings = await this.get('/api/settings'); break; } catch (e) { await new Promise(r => setTimeout(r, 300)); }
      }
      this.applySettings();
      this.connect();
      this.native('ready');
      this.ready = true;
      this.get('/api/sys').then(s => { this.sys = s; this.emit('sys', s); });
      return this.settings;
    },

    /* hit-testing for shell windows: send rectangles of interactive regions */
    hit(sel) {
      const rects = [];
      document.querySelectorAll(sel || '[data-hit]').forEach(el => {
        if (el.offsetParent === null && getComputedStyle(el).position !== 'fixed') return;
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) rects.push([Math.floor(r.left), Math.floor(r.top), Math.ceil(r.width), Math.ceil(r.height)]);
      });
      const key = JSON.stringify(rects);
      if (key !== this._lastHit) { this._lastHit = key; this.native('input', { rects }); }
    },

    /* formatting */
    bytes(b, d = 1) {
      if (b == null) return '';
      const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0;
      while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
      return (i ? b.toFixed(b < 10 ? d : (b < 100 ? 1 : 0)) : b) + ' ' + u[i];
    },
    rel(t) {
      const s = (Date.now() / 1000) - t;
      if (s < 60) return 'now';
      if (s < 3600) return Math.floor(s / 60) + ' min ago';
      if (s < 86400) return Math.floor(s / 3600) + ' h ago';
      return new Date(t * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    },
    time(d, sec) {
      d = d || new Date();
      const h24 = !this.settings || this.settings.clock24 !== false;
      return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: sec ? '2-digit' : undefined, hour12: !h24 });
    },
    esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]); },
    debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; },

    /* context menu */
    menu(x, y, items, onClose) {
      L.closeMenu();
      const m = document.createElement('div');
      m.className = 'menu';
      items.forEach(it => {
        if (it === '-') { m.insertAdjacentHTML('beforeend', '<div class="sep"></div>'); return; }
        const d = document.createElement('div');
        d.className = 'mi' + (it.danger ? ' danger' : '') + (it.disabled ? ' dis' : '');
        d.innerHTML = (it.icon ? icon(it.icon) : '<span style="width:15px"></span>') + `<span>${L.esc(it.label)}</span>` + (it.kbd ? `<kbd>${it.kbd}</kbd>` : '');
        d.onclick = (e) => { e.stopPropagation(); L.closeMenu(); it.action && it.action(); };
        m.appendChild(d);
      });
      document.body.appendChild(m);
      const r = m.getBoundingClientRect();
      if (x + r.width > innerWidth - 6) { x = Math.max(6, x - r.width); m.style.transformOrigin = 'top right'; }
      if (y + r.height > innerHeight - 6) { y = Math.max(6, y - r.height); }
      m.style.left = x + 'px'; m.style.top = y + 'px';
      L._menu = m; L._menuClose = onClose;
      setTimeout(() => document.addEventListener('mousedown', L._menuOut = (e) => { if (!m.contains(e.target)) L.closeMenu(); }), 0);
      return m;
    },
    closeMenu() {
      if (L._menu) { L._menu.remove(); L._menu = null; document.removeEventListener('mousedown', L._menuOut); L._menuClose && L._menuClose(); }
    },

    /* modal dialog inside the current page */
    dialog({ title, text, buttons, input, value, parent, index }) {
      return new Promise(res => {
        const bg = document.createElement('div');
        bg.className = 'modal-bg';
        bg.innerHTML = `<div class="modal"><h3>${L.esc(title || '')}</h3>${text ? `<p>${L.esc(text)}</p>` : ''}
          ${input ? `<input class="input" style="width:100%" value="${L.esc(value || '')}" type="${input === 'password' ? 'password' : 'text'}">` : ''}
          <div class="acts"></div></div>`;
        const acts = bg.querySelector('.acts');
        (buttons || ['OK']).forEach((b, i, arr) => {
          const btn = document.createElement('button');
          btn.className = 'btn' + (i === 0 ? ' primary' : '');
          btn.textContent = b;
          btn.onclick = () => { close(i === 0 ? (input ? bg.querySelector('input').value : true) : (index ? i : null)); };
          acts.appendChild(btn);
        });
        function close(v) { bg.style.animation = 'fadeIn 120ms reverse forwards'; setTimeout(() => bg.remove(), 120); res(v); }
        (parent || document.querySelector('.win-body') || document.body).appendChild(bg);
        const inp = bg.querySelector('input');
        if (inp) { inp.focus(); inp.select(); inp.onkeydown = (e) => { if (e.key === 'Enter') close(inp.value); if (e.key === 'Escape') close(null); }; }
      });
    },
    ripple(el, e) {
      const r = el.getBoundingClientRect(); const s = Math.max(r.width, r.height);
      const d = document.createElement('i'); d.className = 'ripple';
      d.style.cssText = `width:${s}px;height:${s}px;left:${e.clientX - r.left - s / 2}px;top:${e.clientY - r.top - s / 2}px`;
      el.appendChild(d); setTimeout(() => d.remove(), 600);
    },

    /* quick settings panel (topbar) */
    quickSettings() {
      const p = document.getElementById('qs-panel');
      const b = document.getElementById('qs-btn');
      if (!p || !b) return;
      const show = () => {
        p.classList.add('show');
        L.get('/api/net').then(n => { const el = document.getElementById('qs-wifi'); if (el) el.textContent = n.primary ? 'Connected' : 'Off'; });
        L.get('/api/audio').then(a => { const el = document.getElementById('qs-vol'); if (el) el.value = a.volume; });
      };
      const hide = () => p.classList.remove('show');
      b.onclick = e => { e.stopPropagation(); p.classList.toggle('show'); if (p.classList.contains('show')) show(); };
      document.getElementById('qs-open').onclick = () => { L.app('settings'); hide(); };
      document.getElementById('qs-vol').oninput = e => L.post('/api/audio', { volume: +e.target.value });
      document.getElementById('qs-night').onchange = e => L.setSettings({ nightLight: e.target.checked });
      document.addEventListener('click', e => { if (p && !p.contains(e.target) && e.target !== b) hide(); });
    },

    /* keyboard shortcut hints: show a small overlay with common shortcuts */
    shortcuts() {
      const d = document.createElement('div');
      d.className = 'shortcuts';
      d.innerHTML = `
        <div class="sc-panel">
          <h3>Keyboard shortcuts</h3>
          <table>
            <tr><td><kbd>Super</kbd></td><td>Start / overlay</td></tr>
            <tr><td><kbd>Super</kbd> + <kbd>A</kbd></td><td>All apps (Launchpad)</td></tr>
            <tr><td><kbd>Super</kbd> + <kbd>D</kbd></td><td>Show desktop</td></tr>
            <tr><td><kbd>Super</kbd> + <kbd>L</kbd></td><td>Lock screen</td></tr>
            <tr><td><kbd>Super</kbd> + <kbd>Tab</kbd></td><td>Switch window</td></tr>
            <tr><td><kbd>Alt</kbd> + <kbd>F4</kbd></td><td>Close window</td></tr>
            <tr><td><kbd>F11</kbd></td><td>Maximise window</td></tr>
            <tr><td><kbd>Esc</kbd></td><td>Close menus / dialogs</td></tr>
          </table>
          <button class="btn primary" onclick="this.closest('.shortcuts').remove()">Got it</button>
        </div>`;
      document.body.appendChild(d);
      setTimeout(() => d.classList.add('on'), 10);
    },
  };

  /* Global keyboard shortcuts (work in every shell page) */
  (function () {
    let ignoring = false;
    document.addEventListener('keydown', e => {
      if (ignoring || e.repeat) return;
      const s = e.metaKey || e.ctrlKey;
      if (e.key === 'Escape') { L.closeMenu(); return; }
      if (s && e.key.toLowerCase() === 'k') { e.preventDefault(); L.shortcuts(); return; }
      if (e.metaKey && e.key.toLowerCase() === 'l') { e.preventDefault(); L.native('lock'); return; }
      if (e.metaKey && e.key.toLowerCase() === 'd') { e.preventDefault(); L.native('desktop'); return; }
      if (e.metaKey && e.key === 'Tab') { e.preventDefault(); L.native('taskview', { show: true }); return; }
    });
  })();

  /* Alt+Tab window switcher */
  (function () {
    let switcher = null, tabs = [], idx = 0;
    function open() {
      if (switcher) return;
      L.get('/api/windows').then(ws => {
        tabs = (ws || []).filter(w => w.title && w.title !== 'Lumina Shell');
        if (!tabs.length) return;
        idx = 0;
        switcher = document.createElement('div');
        switcher.className = 'switcher';
        render();
        document.body.appendChild(switcher);
        setTimeout(() => switcher.classList.add('on'), 10);
      });
    }
    function render() {
      switcher.innerHTML = `<div class="switcher-panel">${tabs.map((w, i) => `
        <div class="switch-item ${i === idx ? 'on' : ''}">
          <img src="/api/winicon?xid=${w.xid}&size=48" class="switch-ic">
          <div class="switch-title">${L.esc(w.title)}</div>
        </div>`).join('')}</div>`;
    }
    function next(d) { idx = (idx + d + tabs.length) % tabs.length; render(); }
    function close(activate = true) {
      if (!switcher) return;
      switcher.classList.remove('on');
      setTimeout(() => { switcher.remove(); switcher = null; }, 200);
      if (activate && tabs[idx]) L.post('/api/window', { xid: tabs[idx].xid, action: 'present' });
    }
    document.addEventListener('keydown', e => {
      if (e.key === 'Tab' && e.altKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        if (switcher) next(1); else open();
      }
      if (switcher && e.key === 'Escape') { e.preventDefault(); close(false); }
      if (switcher && e.key === 'ArrowRight') { e.preventDefault(); next(1); }
      if (switcher && e.key === 'ArrowLeft') { e.preventDefault(); next(-1); }
      if (switcher && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); close(true); }
      if (e.key === 'Alt' && !e.altKey && switcher) close(true);
    });
  })();
  document.addEventListener('keydown', e => { if (e.key === 'Escape') L.closeMenu(); });

  /* Keyboard accessibility: expose common clickable surfaces to Tab and
     activate them with Enter or Space. Native controls keep their own behavior. */
  const KEY_CLASSES = ['nav', 'tile', 'opt', 'swatch', 'wall', 'gi', 'pitem', 'it', 'di', 'ai', 'tab', 'gi'];
  function enhanceKeyboard(root) {
    if (!root || !root.querySelectorAll) return;
    KEY_CLASSES.forEach(cls => {
      root.querySelectorAll('.' + cls).forEach(el => {
        const native = ['INPUT', 'BUTTON', 'SELECT', 'TEXTAREA', 'A'].indexOf(el.tagName) >= 0;
        if (native || !el.setAttribute || el.hasAttribute('tabindex')) return;
        el.setAttribute('tabindex', '0');
        if (!el.hasAttribute('role')) el.setAttribute('role', 'button');
      });
    });
  }
  function initKeyboardNav() {
    enhanceKeyboard(document);
    document.addEventListener('keydown', e => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const el = document.activeElement;
      if (!el || ['INPUT', 'BUTTON', 'SELECT', 'TEXTAREA', 'A'].indexOf(el.tagName) >= 0) return;
      if (el.hasAttribute && el.getAttribute('role') === 'button' && typeof el.click === 'function') {
        e.preventDefault(); el.click();
      }
    });
    if (typeof MutationObserver !== 'undefined' && document.body) {
      let pending = null;
      new MutationObserver(() => {
        if (pending) clearTimeout(pending);
        pending = setTimeout(() => { pending = null; enhanceKeyboard(document.body); }, 80);
      }).observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initKeyboardNav);
  else initKeyboardNav();
})();
/* forward page errors to the host log */
window.addEventListener('error', e => { try { window.webkit.messageHandlers.lumina.postMessage(JSON.stringify({ cmd: 'log', msg: 'JS error: ' + e.message + ' @' + (e.filename || '').split('/').pop() + ':' + e.lineno })); } catch (x) { } });
window.addEventListener('unhandledrejection', e => { try { window.webkit.messageHandlers.lumina.postMessage(JSON.stringify({ cmd: 'log', msg: 'Unhandled: ' + (e.reason && (e.reason.stack || e.reason.message) || e.reason) })); } catch (x) { } });
