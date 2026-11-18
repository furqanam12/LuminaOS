"""LuminaOS system API.

A small HTTP + Server-Sent-Events hub that the shell UI and every Lumina app
talk to.  Runs inside the lumina-shell process on 127.0.0.1:7700.
"""
import json, os, sys, time, threading, queue, subprocess, shutil, mimetypes, re, glob, pwd, socket, shlex, zipfile, tarfile
import urllib.parse, configparser, ctypes, ctypes.util, signal, uuid, html, hmac, secrets, base64, functools
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import psutil

ROOT = os.environ.get("LUMINA_ROOT", "/usr/share/lumina")
UI = os.path.join(ROOT, "ui")
HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(HOME, ".config", "lumina")
CACHE = os.path.join(HOME, ".cache", "lumina")
SETTINGS_FILE = os.path.join(CONF_DIR, "settings.json")
NOTIF_FILE = os.path.join(CONF_DIR, "notifications.json")
SETUP_DONE = os.path.join(CONF_DIR, "setup-complete")
os.makedirs(CONF_DIR, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

DEFAULTS = {
    "theme": "dark",            # dark | light
    "accent": "#ff375f",
    "wallpaper": "aurora.jpg",
    "reduceMotion": False,
    "transparency": True,
    "dockSize": 44,
    "dockMagnify": True,
    "clock24": True,
    "focus": False,
    "focusUntil": 0,
    "quietStart": "",
    "quietEnd": "",
    "notificationRules": {},
    "widgets": False,
    "pinned": ["lumina-files.desktop", "firefox-esr.desktop", "lumina-store.desktop", "lumina-notepad.desktop",
               "lumina-calculator.desktop", "lumina-taskmgr.desktop", "lumina-settings.desktop"],
    "startPinned": ["lumina-files.desktop", "lumina-store.desktop", "lumina-notepad.desktop",
                    "lumina-calculator.desktop", "lumina-settings.desktop", "lumina-taskmgr.desktop",
                    "firefox-esr.desktop", "lumina-terminal.desktop", "lumina-snip.desktop",
                    "lumina-photos.desktop", "lumina-welcome.desktop", "lumina-about.desktop"],
    "brightness": 100,
    "nightLight": False,
    "uiScale": 100,
    "highContrast": False,
    "strongFocus": False,
    "performancePreset": "custom",
    "perfShadows": True,
}

PERFORMANCE_PRESETS = {
    "balanced": {"reduceMotion": False, "transparency": True, "dockMagnify": True, "perfShadows": True},
    "low-power": {"reduceMotion": True, "transparency": False, "dockMagnify": False, "perfShadows": False},
}
PERFORMANCE_KEYS = frozenset(PERFORMANCE_PRESETS["balanced"])

# ----------------------------------------------------------------- simple API auth
# A per-boot token is written to ~/.cache/lumina/api-token on first shell start.
# Local UI pages read it from /api/auth/token and send it as X-Lumina-Token on
# mutating (POST) requests.  Read-only GETs remain open for local tools.
TOKEN_FILE = os.path.join(CACHE, "api-token")


def api_token() -> str | None:
    """Retrieve the per-boot API token from cached file.
    
    Returns:
        Token string if found, None if not configured.
        Token is stored in ~/.cache/lumina/api-token with mode 0600.
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token = f.read().strip()
            return token if token else None
    except Exception:
        return None


def ensure_token() -> str:
    """Generate and persist a per-boot API token if one doesn't exist.
    
    Returns:
        The API token string, freshly generated or cached.
        Token is written to ~/.cache/lumina/api-token with mode 0600 for security.
    """
    tok = api_token()
    if not tok:
        tok = secrets.token_urlsafe(32)
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(tok)
            os.chmod(TOKEN_FILE, 0o600)
        except Exception:
            pass  # Best-effort; open system continues without file protection
    return tok


def token_ok(headers) -> bool:
    """Validate API token from request headers.
    
    Checks for a valid X-Lumina-Token header against the cached per-boot token.
    Read-only GET endpoints remain open; mutating POST endpoints require validation.
    
    Args:
        headers: HTTP request headers dict
        
    Returns:
        True if token is valid or not configured; False if required but missing/invalid.
    """
    tok = api_token()
    if not tok:
        return True  # No token configured -> open GETs stay open
    provided = headers.get("X-Lumina-Token") or headers.get("X-Lumina-Token", "".lower())
    return bool(provided) and hmac.compare_digest(provided, tok)

# ----------------------------------------------------------------- rate limiting
# Per-client (IP) request counters with a sliding window.
# 60 requests / 10s by default; mutating endpoints are stricter at 30 / 10s.
# Auth endpoints are strictest at 10 / 60s to prevent brute-force.
# Usage: rate_check(client_ip, "mutating") before processing POST requests.
RATE_LIMITS = {
    "default": {"max_requests": 60, "window_secs": 10},
    "mutating": {"max_requests": 30, "window_secs": 10},
    "auth": {"max_requests": 10, "window_secs": 60},
}
_rate_state: dict = {}  # ip -> {"default": [...], "mutating": [...], "auth": [...]}
_rate_lock = threading.Lock()


def rate_check(ip: str, category: str = "default") -> bool:
    """Check if a client IP is within rate limits for the given category.
    
    Uses a sliding window algorithm: tracks timestamps of recent requests
    and rejects if the count exceeds the limit within the window.
    
    Args:
        ip: Client IP address string
        category: Rate limit category: "default", "mutating", or "auth"
        
    Returns:
        True if the request is allowed, False if rate limited (HTTP 429)
        
    Example:
        >>> rate_check("127.0.0.1", "mutating")
        True  # allowed
        >>> rate_check("127.0.0.1", "mutating")  # 31st call in 10s
        False # rate limited
    """
    now = time.time()
    lim = RATE_LIMITS.get(category, RATE_LIMITS["default"])
    with _rate_lock:
        stamps = _rate_state.setdefault(ip, {}).setdefault(category, [])
        cutoff = now - lim["window_secs"]
        # Remove timestamps outside the window
        stamps[:] = [t for t in stamps if t > cutoff]
        if len(stamps) >= lim["max_requests"]:
            return False  # Rate exceeded
        stamps.append(now)  # Record this request
        return True  # Allowed


# ----------------------------------------------------------------- audit logging
AUDIT_FILE = os.path.join(CACHE, "audit.log")


def audit_log(ip: str, method: str, path: str, ok: bool, detail: str = "") -> None:
    """Log an API access event to the audit file for security monitoring.
    
    Writes a structured log entry with timestamp, client IP, HTTP method,
    endpoint path, success/failure status, and optional detail string.
    Log file is rotated implicitly by size (append-only, no rotation here).
    
    Args:
        ip: Client IP address as string (e.g. "127.0.0.1")
        method: HTTP method as string (e.g. "GET", "POST")
        path: Requested endpoint path as string (e.g. "/api/settings")
        ok: Boolean True if the request succeeded, False if it failed
        detail: Optional additional detail string (error message, reason, etc.)
        
    Log Format (space-separated):
        %Y-%m-%dT%H:%M:%S.ip.method.path.OK/FAIL.detail
        
    Example:
        audit_log("192.168.1.100", "POST", "/api/password", True, "changed successfully")
    """
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write("%s %s %s %s %s %s\n" % (
                time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                ip, method, path, "OK" if ok else "FAIL", detail))
    except Exception:
        pass  # Best-effort; logging failure shouldn't break the API


# ----------------------------------------------------------------- error wrapper for API functions
def api_endpoint(fn):
    """Decorator that wraps API handler functions to catch exceptions and
    return structured JSON error responses instead of crashing or exposing
    stack traces to connected clients.
    
    The decorator ensures that all API endpoints return consistent JSON
    format: {"ok": True/False, "error": "description"} or the normal
    return value when ok=True.
    
    Error handling priorities:
    1. ValueError → returns {"ok": False, "error": str(e)}
    2. Other exceptions → logs traceback to server stdout, returns
       {"ok": False, "error": "internal error: %s" % type(e).__name__}
    3. Successful return → returns the function's normal return value
    
    The decorator is designed for use on route handler functions that
    return dicts or None. It does NOT modify the response format for
    successful calls.
    
    Example:
        @api_endpoint
        def set_settings(body: dict) -> dict:
            # May raise ValueError for invalid patches
            return set_settings(body)
    
    Note:
        This decorator should be applied to ALL route handler functions
        in the Handler.route_post and Handler.route_get methods to
        ensure consistent error handling across the entire API.
    """
    @functools.wraps(fn)
    def _wrapped(*a, **k):
        try:
            result = fn(*a, **k)
            # Successful return - pass through normally
            return result
        except ValueError as e:
            # Client input validation failure - return 400-style error
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: broad except for maximum robustness
            # Unexpected error - log to server console, return generic message
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": "internal error: %s" % type(e).__name__}
    return _wrapped


# ----------------------------------------------------------------- error wrapper for API functions
def api_endpoint(fn):
    """Decorator: catch exceptions, return JSON error dict instead of raising."""
    @functools.wraps(fn)
    def _wrapped(*a, **k):
        try:
            return fn(*a, **k)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa
            import traceback; traceback.print_exc()
            return {"ok": False, "error": "internal error: %s" % type(e).__name__}
    return _wrapped


def performance_patch(patch, current):
    """Expand an explicit preset; individual effect changes become custom."""
    if not isinstance(patch, dict):
        raise ValueError("Settings must be a JSON object")
    patch = dict(patch)
    for key in PERFORMANCE_KEYS:
        if key in patch and not isinstance(patch[key], bool):
            raise ValueError(key + " must be a boolean")
    if "performancePreset" in patch:
        preset = patch["performancePreset"]
        if not isinstance(preset, str) or preset not in ("custom", "balanced", "low-power"):
            raise ValueError("Unknown performance preset")
        if preset in PERFORMANCE_PRESETS:
            patch.update(PERFORMANCE_PRESETS[preset])
    elif any(key in patch and patch[key] != current.get(key) for key in PERFORMANCE_KEYS):
        patch["performancePreset"] = "custom"
    return patch

# ----------------------------------------------------------------- helpers
def sh(cmd, timeout=10, inp=None):
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                           timeout=timeout, input=inp)
        return r.stdout.strip()
    except Exception:
        return ""

def sh_rc(cmd, timeout=20, inp=None):
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                           timeout=timeout, input=inp)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)

def spawn(argv, cwd=None):
    env = dict(os.environ)
    subprocess.Popen(argv, cwd=cwd or HOME, env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)

# ----------------------------------------------------------------- event hub
class Hub:
    def __init__(self):
        self.clients = set()
        self.lock = threading.Lock()

    def add(self):
        q = queue.Queue(maxsize=500)
        with self.lock:
            self.clients.add(q)
        return q

    def remove(self, q):
        with self.lock:
            self.clients.discard(q)

    def emit(self, event, data=None):
        msg = json.dumps({"event": event, "data": data})
        with self.lock:
            for q in list(self.clients):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

HUB = Hub()

# ----------------------------------------------------------------- settings
_settings_lock = threading.Lock()

def get_settings():
    s = dict(DEFAULTS)
    s.update(read_json(SETTINGS_FILE, {}))
    return s

def set_settings(patch):
    with _settings_lock:
        cur = read_json(SETTINGS_FILE, {})
        current = dict(DEFAULTS, **cur)
        patch = performance_patch(patch, current)
        changed = {key: value for key, value in patch.items() if current.get(key) != value}
        if not changed:
            return current
        cur.update(changed)
        write_json(SETTINGS_FILE, cur)
        s = dict(DEFAULTS, **cur)
    apply_native_theme(s, changed)
    HUB.emit("settings", s)
    return s


_shadow_lock = threading.Lock()


def apply_window_shadows():
    """Restore saved shadow settings without disabling the compositor."""
    if not shutil.which("xfconf-query"):
        return
    with _shadow_lock:
        value = "true" if get_settings().get("perfShadows", True) else "false"
        for prop in ("show_frame_shadow", "show_popup_shadow", "show_dock_shadow"):
            sh(["xfconf-query", "-c", "xfwm4", "-p", "/general/" + prop,
                "-n", "-t", "bool", "-s", value], timeout=2)

def apply_native_theme(s, patch):
    """Keep GTK / xfwm4 (native apps) in sync with the Lumina theme."""
    if "theme" in patch:
        dark = s["theme"] == "dark"
        cmds = [
            ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-n", "-t", "string", "-s",
             "Adwaita-dark" if dark else "Adwaita"],
            ["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-n", "-t", "string", "-s",
             "Papirus-Dark" if dark else "Papirus-Light"],
            ["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-n", "-t", "string", "-s",
             "Lumina-Dark" if dark else "Lumina-Light"],
        ]
        for c in cmds:
            threading.Thread(target=sh, args=(c,), daemon=True).start()
        sh(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme",
            "prefer-dark" if dark else "prefer-light"])
    if "perfShadows" in patch:
        apply_window_shadows()
    if "brightness" in patch or "nightLight" in patch:
        threading.Thread(target=apply_brightness, args=(s,), daemon=True).start()

def apply_brightness(s):
    b = max(0.3, min(1.0, float(s.get("brightness", 100)) / 100.0))
    gamma = "1.0:0.88:0.72" if s.get("nightLight") else "1.0:1.0:1.0"
    for out in connected_outputs():
        sh(["xrandr", "--output", out, "--brightness", "%.2f" % b, "--gamma", gamma])

def connected_outputs():
    out = sh(["xrandr", "--query"])
    return [l.split()[0] for l in out.splitlines() if " connected" in l]

# ----------------------------------------------------------------- notifications
_notifs = read_json(NOTIF_FILE, [])
_notif_lock = threading.Lock()

def in_quiet_hours(settings):
    now = time.localtime()
    current = "%02d:%02d" % (now.tm_hour, now.tm_min)
    start, end = settings.get("quietStart", ""), settings.get("quietEnd", "")
    if not start or not end:
        return False
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def notify(title, body="", icon="", app="LuminaOS", actions=None, urgency=1):
    settings = get_settings()
    now = time.time()
    rule = (settings.get("notificationRules") or {}).get(app, "normal")
    if rule == "off":
        return {"id": "", "suppressed": True}
    silent = (rule == "silent" or bool(settings.get("focus")) or
              float(settings.get("focusUntil") or 0) > now or in_quiet_hours(settings))
    if isinstance(actions, (list, tuple)) and all(isinstance(a, dict) for a in actions):
        actions = [{"id": str(a.get("id", "")), "label": str(a.get("label", "")),
                    "cmd": str(a.get("cmd", ""))} for a in actions if a.get("label")]
    elif isinstance(actions, (list, tuple)):
        clean = []
        for i in range(0, len(actions) - 1, 2):
            clean.append({"id": str(actions[i]), "label": str(actions[i + 1])})
        actions = clean
    else:
        actions = []
    n = {"id": uuid.uuid4().hex[:10], "title": title, "body": body, "icon": icon,
         "app": app, "time": now, "urgency": urgency, "actions": actions, "silent": silent}
    with _notif_lock:
        _notifs.insert(0, n)
        del _notifs[60:]
        write_json(NOTIF_FILE, _notifs)
    HUB.emit("notification", {"n": n, "silent": silent})
    return n

# ----------------------------------------------------------------- PAM auth
class _PamMessage(ctypes.Structure):
    _fields_ = [("msg_style", ctypes.c_int), ("msg", ctypes.c_char_p)]

class _PamResponse(ctypes.Structure):
    _fields_ = [("resp", ctypes.c_char_p), ("resp_retcode", ctypes.c_int)]

_CONV = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(_PamMessage)),
                         ctypes.POINTER(ctypes.POINTER(_PamResponse)), ctypes.c_void_p)

class _PamConv(ctypes.Structure):
    _fields_ = [("conv", _CONV), ("appdata_ptr", ctypes.c_void_p)]

def pam_auth(user, password, service="login"):
    try:
        libpam = ctypes.CDLL(ctypes.util.find_library("pam"))
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
    except Exception:
        return False
    libc.calloc.restype = ctypes.c_void_p
    libc.strdup.restype = ctypes.c_void_p
    pw = password.encode()

    @_CONV
    def conv(n, msgs, resp, _):
        addr = libc.calloc(n, ctypes.sizeof(_PamResponse))
        resp[0] = ctypes.cast(addr, ctypes.POINTER(_PamResponse))
        for i in range(n):
            if msgs[i].contents.msg_style == 1:  # PAM_PROMPT_ECHO_OFF
                p = libc.strdup(pw)
                resp.contents[i].resp = ctypes.cast(p, ctypes.c_char_p)
                resp.contents[i].resp_retcode = 0
        return 0

    handle = ctypes.c_void_p()
    c = _PamConv(conv, 0)
    libpam.pam_start.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(_PamConv),
                                 ctypes.POINTER(ctypes.c_void_p)]
    r = libpam.pam_start(service.encode(), user.encode(), ctypes.byref(c), ctypes.byref(handle))
    if r != 0:
        return False
    r = libpam.pam_authenticate(handle, 0)
    libpam.pam_end(handle, r)
    return r == 0

# ----------------------------------------------------------------- system info
_prev_io = {"t": 0}

def sysinfo():
    u = pwd.getpwuid(os.getuid())
    osr = {}
    try:
        for l in open("/etc/os-release"):
            if "=" in l:
                k, v = l.rstrip().split("=", 1)
                osr[k] = v.strip('"')
    except Exception:
        pass
    cpu = ""
    try:
        for l in open("/proc/cpuinfo"):
            if l.startswith("model name"):
                cpu = l.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    def dmi(k):
        try:
            return open("/sys/class/dmi/id/" + k).read().strip()
        except Exception:
            return ""
    gpu = ""
    for l in sh("lspci 2>/dev/null").splitlines():
        if re.search(r"VGA|3D|Display", l):
            gpu = l.split(":", 2)[-1].strip()
            break
    du = shutil.disk_usage("/")
    return {
        "user": u.pw_name, "fullname": (u.pw_gecos.split(",")[0] or u.pw_name),
        "hostname": socket.gethostname(), "os": osr.get("PRETTY_NAME", "LuminaOS"),
        "version": osr.get("LUMINA_VERSION", "1.0"), "codename": osr.get("LUMINA_CODENAME", ""),
        "kernel": os.uname().release, "cpu": cpu, "cores": psutil.cpu_count(),
        "mem": psutil.virtual_memory().total, "disk": du.total, "diskFree": du.free,
        "vendor": dmi("sys_vendor"), "product": dmi("product_name"), "gpu": gpu,
        "uptime": time.time() - psutil.boot_time(), "live": os.path.exists("/run/live/medium"),
        "arch": os.uname().machine,
    }


def session_user():
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return os.environ.get("USER", "user")


def is_live_session():
    return os.path.exists("/run/live/medium")


def first_run_status():
    """Status for the installed-system setup wizard."""
    try:
        hostname = open("/etc/hostname").read().strip()
    except Exception:
        hostname = socket.gethostname()
    zone = sh(["timedatectl", "show", "--property=Timezone", "--value"], 5)
    return {"live": is_live_session(), "complete": os.path.exists(SETUP_DONE),
            "user": session_user(), "hostname": hostname, "timezone": zone}


def complete_first_run():
    try:
        with open(SETUP_DONE, "w") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S\n"))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def installed_boot_checks():
    """Read-only checks shown at the end of first-run setup."""
    checks = []
    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
    user = session_user()
    add("Installed system", not is_live_session(),
        "Running from an installed disk" if not is_live_session() else "Still running the live ISO")
    add("User home", os.path.isdir(HOME) and os.access(HOME, os.W_OK), HOME)
    add("Desktop session", os.path.exists("/usr/share/xsessions/lumina.desktop"), "/usr/share/xsessions/lumina.desktop")
    add("Lumina shell", os.path.exists("/usr/bin/lumina-shell"), "/usr/bin/lumina-shell")
    add("Installer helper", os.path.exists("/usr/bin/lumina-install"), "/usr/bin/lumina-install")
    add("Calamares", bool(shutil.which("calamares")), shutil.which("calamares") or "calamares not found")
    add("GRUB theme", os.path.exists("/boot/grub/themes/lumina/theme.txt"), "/boot/grub/themes/lumina/theme.txt")
    add("Safe-graphics recovery", os.path.exists("/etc/grub.d/45_lumina_recovery"),
        "/etc/grub.d/45_lumina_recovery")
    try:
        boot = open("/boot/grub/grub.cfg", errors="ignore").read()
        add("Bootloader configuration", "safe graphics" in boot.lower(),
            "Recovery entry present" if "safe graphics" in boot.lower() else "Run sudo update-grub")
    except Exception:
        add("Bootloader configuration", False, "/boot/grub/grub.cfg unavailable")
    add("Account", bool(user), user)
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


_stats_lock = threading.Lock()
_stats_cache = None
_stats_time = 0.0
_cpu_previous = None


def cpu_load(previous, current):
    """CPU-time deltas are shared across short-lived HTTP handler threads."""
    if previous is None:
        return 0.0
    fields = [key for key in current._fields if key not in ("guest", "guest_nice")]
    deltas = {key: max(0.0, getattr(current, key) - getattr(previous, key, 0.0)) for key in fields}
    total = sum(deltas.values())
    idle = deltas.get("idle", 0.0) + deltas.get("iowait", 0.0)
    return round(max(0.0, min(100.0, 100.0 * (total - idle) / total)), 1) if total else 0.0


def stats():
    global _stats_cache, _stats_time, _cpu_previous
    with _stats_lock:
        now = time.monotonic()
        if _stats_cache is not None and now - _stats_time < 1.0:
            return _stats_cache
        cpu = psutil.cpu_times()
        cores = psutil.cpu_times(percpu=True)
        previous_cpu, previous_cores = _cpu_previous or (None, [])
        d = {"cpu": cpu_load(previous_cpu, cpu),
             "percpu": [cpu_load(previous_cores[i] if i < len(previous_cores) else None, core)
                        for i, core in enumerate(cores)]}
        _cpu_previous = (cpu, cores)
        io = psutil.disk_io_counters()
        net = psutil.net_io_counters()
        vm = psutil.virtual_memory()
        d["mem"] = {"used": vm.total - vm.available, "total": vm.total, "percent": vm.percent}
        sw = psutil.swap_memory()
        d["swap"] = {"used": sw.used, "total": sw.total}
        if _prev_io.get("t"):
            dt = max(0.1, now - _prev_io["t"])
            d["diskRead"] = max(0, io.read_bytes - _prev_io["r"]) / dt if io else 0
            d["diskWrite"] = max(0, io.write_bytes - _prev_io["w"]) / dt if io else 0
            d["netRecv"] = max(0, net.bytes_recv - _prev_io["nr"]) / dt if net else 0
            d["netSent"] = max(0, net.bytes_sent - _prev_io["ns"]) / dt if net else 0
        else:
            d.update(diskRead=0, diskWrite=0, netRecv=0, netSent=0)
        _prev_io.update(t=now, r=io.read_bytes if io else 0, w=io.write_bytes if io else 0,
                        nr=net.bytes_recv if net else 0, ns=net.bytes_sent if net else 0)
        du = shutil.disk_usage("/")
        d["disk"] = {"used": du.used, "total": du.total}
        d["procs"] = len(psutil.pids())
        d["uptime"] = time.time() - psutil.boot_time()
        try:
            d["freq"] = psutil.cpu_freq().current
        except Exception:
            d["freq"] = 0
        _stats_cache, _stats_time = d, now
        return d

_proc_cache = {}

def processes(window_pids):
    out = []
    cores = max(1, psutil.cpu_count() or 1)
    for p in psutil.process_iter(["pid", "name", "username", "memory_info", "status", "cmdline", "nice", "ppid"]):
        try:
            info = p.info
            cpu = _proc_cache.get(p.pid)
            if cpu is None:
                _proc_cache[p.pid] = p
                c = p.cpu_percent(None)
            else:
                c = cpu.cpu_percent(None)
            try:
                io = p.io_counters()
                dio = io.read_bytes + io.write_bytes
            except Exception:
                dio = 0
            out.append({
                "pid": info["pid"], "name": info["name"], "user": info["username"],
                "mem": info["memory_info"].rss if info["memory_info"] else 0,
                "cpu": round(c / cores, 1), "status": info["status"],
                "cmd": " ".join(info["cmdline"] or [])[:300], "nice": info["nice"],
                "ppid": info["ppid"], "io": dio, "app": info["pid"] in window_pids,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    alive = {p["pid"] for p in out}
    for k in list(_proc_cache):
        if k not in alive:
            _proc_cache.pop(k, None)
    return out

def services():
    raw = sh(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"], 10)
    res = []
    for l in raw.splitlines():
        parts = l.split(None, 4)
        if len(parts) >= 4:
            res.append({"name": parts[0], "load": parts[1], "active": parts[2], "sub": parts[3],
                        "desc": parts[4] if len(parts) > 4 else ""})
    return res

# ----------------------------------------------------------------- autostart
def autostart_list():
    items = {}
    dirs = ["/etc/xdg/autostart", os.path.join(HOME, ".config/autostart")]
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.desktop")):
            cp = configparser.RawConfigParser(strict=False)
            try:
                cp.read(f, encoding="utf-8")
                e = cp["Desktop Entry"]
            except Exception:
                continue
            b = os.path.basename(f)
            it = items.get(b, {"id": b})
            it["name"] = e.get("Name", it.get("name", b))
            it["icon"] = e.get("Icon", it.get("icon", ""))
            it["comment"] = e.get("Comment", it.get("comment", ""))
            hidden = e.get("Hidden", "false").lower() == "true"
            it["enabled"] = not hidden
            only = e.get("OnlyShowIn", "")
            it["system"] = d.startswith("/etc")
            if only and "XFCE" not in only and "Lumina" not in only:
                continue
            items[b] = it
    return sorted(items.values(), key=lambda x: x["name"].lower())

def autostart_set(fid, enabled):
    user_dir = os.path.join(HOME, ".config/autostart")
    os.makedirs(user_dir, exist_ok=True)
    src = os.path.join(user_dir, fid)
    if not os.path.exists(src):
        sysf = os.path.join("/etc/xdg/autostart", fid)
        if os.path.exists(sysf):
            shutil.copy(sysf, src)
        else:
            return False
    lines = [l for l in open(src).read().splitlines() if not l.startswith("Hidden=")]
    out = []
    for l in lines:
        out.append(l)
        if l.strip() == "[Desktop Entry]":
            out.append("Hidden=%s" % ("false" if enabled else "true"))
    open(src, "w").write("\n".join(out) + "\n")
    return True

# ----------------------------------------------------------------- files
XDG_DIRS = ["DESKTOP", "DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS"]

def places():
    res = [{"name": "Home", "path": HOME, "icon": "home"}]
    names = {"DESKTOP": "Desktop", "DOCUMENTS": "Documents", "DOWNLOAD": "Downloads",
             "PICTURES": "Pictures", "MUSIC": "Music", "VIDEOS": "Videos"}
    for k in XDG_DIRS:
        p = sh(["xdg-user-dir", k])
        if not p or p.rstrip("/") == HOME:
            p = os.path.join(HOME, names[k])
        if p:
            os.makedirs(p, exist_ok=True)
            res.append({"name": names[k], "path": p, "icon": k.lower()})
    trash = os.path.join(HOME, ".local/share/Trash/files")
    os.makedirs(trash, exist_ok=True)
    res.append({"name": "Trash", "path": trash, "icon": "trash"})
    return res

def drives():
    out = []
    raw = sh(["lsblk", "-J", "-b", "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT,RM,HOTPLUG,PARTTYPENAME"])
    try:
        data = json.loads(raw)
    except Exception:
        data = {"blockdevices": []}
    def walk(devs):
        for d in devs:
            if d.get("type") in ("part", "rom") or (d.get("type") == "disk" and d.get("fstype")):
                fs = d.get("fstype") or ""
                mp = d.get("mountpoint")
                if fs in ("", "swap", "squashfs") or (mp or "").startswith(("/boot", "/run/live", "/usr/lib/live")):
                    if not (d.get("type") == "rom" and fs):
                        pass
                if fs and fs not in ("swap", "squashfs", "LVM2_member", "crypto_LUKS") and mp != "[SWAP]":
                    label = d.get("label") or ""
                    windows = fs in ("ntfs", "ntfs3") and os.path.isdir(os.path.join(mp or "/nonexistent", "Windows"))
                    if mp == "/":
                        name = "System"
                    elif fs in ("ntfs", "ntfs3"):
                        name = (label or "Windows") + (" (C:)" if windows or not label else "")
                    else:
                        name = label or (os.path.basename(mp) if mp else d["name"])
                    used = free = 0
                    if mp:
                        try:
                            u = shutil.disk_usage(mp)
                            used, free = u.used, u.free
                        except Exception:
                            pass
                    if (mp or "").startswith(("/boot", "/run/live", "/usr/lib/live")):
                        continue
                    out.append({"name": name, "dev": d["path"], "fs": fs, "size": int(d.get("size") or 0),
                                "mount": mp, "used": used, "free": free, "removable": bool(d.get("rm") or d.get("hotplug"))})
            walk(d.get("children") or [])
    walk(data.get("blockdevices", []))
    return out

def mount_dev(dev):
    rc, out = sh_rc(["udisksctl", "mount", "-b", dev, "--no-user-interaction"], 30)
    if rc != 0:
        rc, out = sh_rc(["udisksctl", "mount", "-b", dev], 60)
    m = re.search(r" at (.+?)\.?$", out)
    return {"ok": rc == 0, "path": m.group(1) if m else None, "msg": out}

def safe_path(p):
    p = os.path.abspath(os.path.expanduser(p or HOME))
    return p

def list_dir(path, hidden=False):
    path = safe_path(path)
    res = []
    try:
        with os.scandir(path) as it:
            for e in it:
                if not hidden and e.name.startswith("."):
                    continue
                try:
                    st = e.stat(follow_symlinks=True)
                    isdir = e.is_dir(follow_symlinks=True)
                except Exception:
                    continue
                mime = "inode/directory" if isdir else (mimetypes.guess_type(e.name)[0] or "application/octet-stream")
                desktop = desktop_entry(e.path) if e.name.lower().endswith(".desktop") else None
                res.append({"name": desktop["name"] if desktop else e.name, "path": e.path, "dir": isdir,
                            "size": st.st_size, "mtime": st.st_mtime, "mime": mime, "link": e.is_symlink(),
                            "desktopApp": desktop})
    except PermissionError:
        return {"error": "Permission denied", "path": path, "items": []}
    except FileNotFoundError:
        return {"error": "Folder not found", "path": path, "items": []}
    res.sort(key=lambda x: (not x["dir"], x["name"].lower()))
    du = None
    try:
        u = shutil.disk_usage(path)
        du = {"free": u.free, "total": u.total}
    except Exception:
        pass
    return {"path": path, "items": res, "parent": os.path.dirname(path) if path != "/" else None, "usage": du}

def recent_files(limit=12):
    f = os.path.join(HOME, ".local/share/recently-used.xbel")
    items = []
    try:
        data = open(f, encoding="utf-8").read()
        for m in re.finditer(r'<bookmark href="([^"]+)"[^>]*modified="([^"]+)"', data):
            u = urllib.parse.unquote(m.group(1))
            if u.startswith("file://"):
                p = u[7:]
                if os.path.exists(p) and not os.path.isdir(p):
                    items.append({"path": p, "name": os.path.basename(p), "modified": m.group(2),
                                  "mime": mimetypes.guess_type(p)[0] or ""})
    except Exception:
        pass
    items.sort(key=lambda x: x["modified"], reverse=True)
    seen, out = set(), []
    for i in items:
        if i["path"] in seen:
            continue
        seen.add(i["path"])
        out.append(i)
    return out[:limit]

def add_recent(path):
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib
        def _add():
            Gtk.RecentManager.get_default().add_item("file://" + urllib.parse.quote(path))
            return False
        GLib.idle_add(_add)
    except Exception:
        pass

def search_files(q, limit=40):
    q = q.lower()
    out = []
    start = time.time()
    for root, dirs, files in os.walk(HOME):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for n in dirs + files:
            if q in n.lower():
                p = os.path.join(root, n)
                out.append({"name": n, "path": p, "dir": os.path.isdir(p),
                            "mime": mimetypes.guess_type(n)[0] or ""})
                if len(out) >= limit:
                    return out
        if time.time() - start > 1.5:
            break
    return out

def desktop_entry(path):
    """Read a .desktop file for the custom desktop and Files app."""
    cp = configparser.RawConfigParser(strict=False)
    try:
        cp.read(path, encoding="utf-8")
        e = cp["Desktop Entry"]
        if e.get("Type", "Application") != "Application":
            return None
        name = e.get("Name", os.path.basename(path))
        icon = e.get("Icon", "")
        program = e.get("Exec", "").replace(" %f", "").replace(" %F", "").replace(" %u", "").replace(" %U", "")
        return {"id": os.path.basename(path), "name": name, "icon": icon, "exec": program.strip()}
    except Exception:
        return None


def open_path(path):
    path = safe_path(path)
    low = path.lower()
    if low.endswith(".desktop"):
        entry = desktop_entry(path)
        if entry and entry["exec"]:
            try:
                spawn(shlex.split(entry["exec"]), cwd=os.path.dirname(path))
                return {"ok": True, "via": "desktop"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    if low.endswith((".exe", ".msi", ".bat")):
        if shutil.which("wine"):
            argv = ["wine", "start", "/unix", path] if low.endswith(".msi") else ["wine", path]
            spawn(argv, cwd=os.path.dirname(path))
            notify("Starting Windows program", os.path.basename(path), "lumina-windows", "Windows programs")
            return {"ok": True, "via": "wine"}
        notify("Windows programs aren't set up", "Install Wine from the Lumina Store to open .exe files.",
               "lumina-windows", "Windows programs")
        return {"ok": False, "error": "wine missing"}
    if low.endswith(".apk"):
        if shutil.which("waydroid"):
            spawn(["waydroid", "app", "install", path])
            return {"ok": True, "via": "waydroid"}
        notify("Android apps aren't set up", "Open Settings > Windows programs & Android to set up Android support.",
               "lumina-android", "Android")
        return {"ok": False, "error": "waydroid missing"}
    if low.endswith((".deb", ".flatpakref")):
        spawn(["lumina-app", "store", "--install-file", path])
        return {"ok": True, "via": "store"}
    if os.path.isdir(path):
        spawn(["lumina-app", "files", path])
        return {"ok": True}
    add_recent(path)
    spawn(["xdg-open", path])
    return {"ok": True}

def trash(paths):
    ok = True
    for p in paths:
        rc, _ = sh_rc(["gio", "trash", p])
        ok = ok and rc == 0
    return ok

def empty_trash():
    sh(["gio", "trash", "--empty"])


def trash_restore(original):
    """Restore an item trashed by gio using its .trashinfo metadata."""
    original = os.path.abspath(safe_path(original))
    info_dir = os.path.join(HOME, ".local/share/Trash/info")
    files_dir = os.path.join(HOME, ".local/share/Trash/files")
    try:
        names = os.listdir(info_dir)
    except Exception:
        return False
    for name in names:
        if not name.endswith(".trashinfo"):
            continue
        try:
            data = open(os.path.join(info_dir, name), encoding="utf-8", errors="ignore").read()
            line = next((l for l in data.splitlines() if l.startswith("Path=")), "")
            if urllib.parse.unquote(line[5:]) == original:
                src = os.path.join(files_dir, name[:-10])
                os.makedirs(os.path.dirname(original), exist_ok=True)
                shutil.move(src, original)
                os.remove(os.path.join(info_dir, name))
                return True
        except Exception:
            continue
    return False

def copy_paths(paths, dest, move=False, conflict="rename"):
    dest = safe_path(dest)
    done = []
    for p in paths:
        name = os.path.basename(p.rstrip("/"))
        target = os.path.join(dest, name)
        base, ext = os.path.splitext(name)
        exists = os.path.exists(target) and os.path.abspath(p) != os.path.abspath(target)
        if conflict == "skip" and exists:
            continue
        i = 2
        while exists and conflict != "replace":
            target = os.path.join(dest, "%s (%d)%s" % (base, i, ext))
            i += 1
            exists = os.path.exists(target)
        if os.path.abspath(p) == os.path.abspath(target):
            if move:
                continue
            target = os.path.join(dest, "%s - Copy%s" % (base, ext))
        if move:
            shutil.move(p, target)
        elif os.path.isdir(p):
            shutil.copytree(p, target, symlinks=True, dirs_exist_ok=(conflict == "replace"))
        else:
            shutil.copy2(p, target)
        done.append(target)
    return done


def archive_extract(path, dest):
    path, dest = safe_path(path), safe_path(dest)
    if not os.path.isfile(path):
        raise ValueError("Archive not found")
    os.makedirs(dest, exist_ok=True)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for member in z.namelist():
                target = os.path.abspath(os.path.join(dest, member))
                if not target.startswith(os.path.abspath(dest) + os.sep) and target != os.path.abspath(dest):
                    raise ValueError("Archive contains an unsafe path")
            z.extractall(dest)
        return True
    try:
        with tarfile.open(path) as t:
            root = os.path.abspath(dest)
            for member in t.getmembers():
                target = os.path.abspath(os.path.join(root, member.name))
                if (member.issym() or member.islnk() or target != root and
                        not target.startswith(root + os.sep)):
                    raise ValueError("Archive contains an unsafe path")
            t.extractall(dest)
        return True
    except tarfile.TarError:
        raise ValueError("Unsupported archive format")


def archive_create(paths, dest, name):
    dest = safe_path(dest)
    name = os.path.basename(str(name or "Archive.zip"))
    if not name.lower().endswith(".zip"):
        name += ".zip"
    target = os.path.join(dest, name)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            p = safe_path(p)
            if os.path.isdir(p):
                for root, _dirs, files in os.walk(p):
                    for f in files:
                        full = os.path.join(root, f)
                        z.write(full, os.path.relpath(full, os.path.dirname(p)))
            elif os.path.isfile(p):
                z.write(p, os.path.basename(p))
    return target


def file_permissions(path):
    path = safe_path(path)
    st = os.stat(path)
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except Exception:
        owner = str(st.st_uid)
    return {"path": path, "mode": st.st_mode & 0o777, "octal": "%03o" % (st.st_mode & 0o777),
            "owner": owner, "uid": st.st_uid, "gid": st.st_gid}


def set_file_permissions(path, mode):
    path = safe_path(path)
    value = int(str(mode), 8) if isinstance(mode, str) else int(mode)
    if value < 0 or value > 0o777:
        raise ValueError("Permission mode must be between 000 and 777")
    os.chmod(path, value)
    return file_permissions(path)

# ----------------------------------------------------------------- audio / net / display
def audio_get():
    out = sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r"Volume:\s*([\d.]+)", out)
    if m:
        return {"available": True, "volume": round(float(m.group(1)) * 100), "muted": "MUTED" in out}
    out = sh("pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null")
    m = re.search(r"(\d+)%", out)
    if m:
        mute = "yes" in sh("pactl get-sink-mute @DEFAULT_SINK@")
        return {"available": True, "volume": int(m.group(1)), "muted": mute}
    return {"available": False, "volume": 0, "muted": True}

def audio_set(volume=None, muted=None):
    if volume is not None:
        v = max(0, min(100, int(volume)))
        if sh_rc(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "%d%%" % v])[0] != 0:
            sh(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "%d%%" % v])
    if muted is not None:
        if sh_rc(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"])[0] != 0:
            sh(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"])
    a = audio_get()
    HUB.emit("audio", a)
    return a

def net_get():
    res = {"available": bool(shutil.which("nmcli")), "devices": [], "wifi": [], "enabled": True, "primary": None}
    if not res["available"]:
        return res
    res["enabled"] = sh(["nmcli", "networking"]) == "enabled"
    for l in sh(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"]).splitlines():
        p = l.split(":")
        if len(p) >= 4 and p[1] in ("ethernet", "wifi"):
            d = {"device": p[0], "type": p[1], "state": p[2], "connection": p[3]}
            res["devices"].append(d)
            if p[2] == "connected" and not res["primary"]:
                res["primary"] = d
    if any(d["type"] == "wifi" for d in res["devices"]):
        for l in sh(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], 8).splitlines():
            p = l.split(":")
            if len(p) >= 4 and p[1]:
                res["wifi"].append({"active": p[0] == "*", "ssid": p[1], "signal": int(p[2] or 0), "secure": bool(p[3])})
    ip = sh("ip -4 -o addr show scope global | awk '{print $4}' | head -1")
    res["ip"] = ip
    return res

def bt_get():
    has = os.path.isdir("/sys/class/bluetooth") and bool(os.listdir("/sys/class/bluetooth"))
    return {"available": has}

def display_get():
    out = sh(["xrandr", "--query"])
    outputs = []
    cur = None
    for l in out.splitlines():
        if " connected" in l:
            m = re.search(r"(\d+)x(\d+)\+", l)
            cur = {"name": l.split()[0], "current": "%sx%s" % m.groups() if m else "", "modes": [],
                   "primary": " primary" in l}
            outputs.append(cur)
        elif cur and re.match(r"^\s+\d+x\d+", l):
            mode = l.split()[0]
            if mode not in cur["modes"]:
                cur["modes"].append(mode)
        elif not l.startswith(" "):
            cur = None
    return {"outputs": outputs}

def display_set(output, mode):
    rc, out = sh_rc(["xrandr", "--output", output, "--mode", mode])
    return {"ok": rc == 0, "msg": out}

# ----------------------------------------------------------------- store
STORE_JOBS = {}

def store_catalog():
    cat = read_json(os.path.join(ROOT, "data", "store.json"), {"apps": [], "categories": []})
    pkgs = [a["pkg"] for a in cat["apps"] if a.get("kind") == "apt"]
    installed = set()
    if pkgs:
        out = sh(["dpkg-query", "-W", "-f=${Package} ${Status}\n"] + pkgs)
        for l in out.splitlines():
            p = l.split()
            if len(p) >= 4 and p[-1] == "installed":
                installed.add(p[0])
    flat = set()
    if shutil.which("flatpak"):
        flat = set(sh(["flatpak", "list", "--app", "--columns=application"]).split())
    for a in cat["apps"]:
        if a.get("kind") == "apt":
            a["installed"] = a["pkg"] in installed
        elif a.get("kind") == "flatpak":
            a["installed"] = a["pkg"] in flat
        elif a.get("kind") == "android":
            a["installed"] = bool(shutil.which("waydroid"))
        else:
            a["installed"] = False
    return cat

def store_install(ids, remove=False, file=None, pkgs=None):
    cat = {a["id"]: a for a in store_catalog()["apps"]}
    apt, flat, names, android = [], [], [], False
    for pk in pkgs or []:
        if re.fullmatch(r"[a-zA-Z0-9.+_-]+", pk):
            (flat if pk.count(".") >= 2 else apt).append(pk); names.append(pk)
    for i in ids:
        a = cat.get(i)
        if not a:
            continue
        names.append(a["name"])
        if a["kind"] == "android":
            if remove:
                apt.append("waydroid")
            else:
                android = True
            continue
        (apt if a["kind"] == "apt" else flat).append(a["pkg"])
    jid = uuid.uuid4().hex[:8]
    log = os.path.join(CACHE, "job-%s.log" % jid)
    job = {"id": jid, "names": names, "state": "running", "progress": 0, "log": log, "remove": remove,
           "started": time.time()}
    STORE_JOBS[jid] = job
    def run():
        helper = "/usr/libexec/lumina/lumina-pkg"
        steps = []
        if file:
            steps.append(["install-file", file])
        if android:
            steps.append(["android-setup"])
        if apt:
            steps.append(["remove" if remove else "install"] + apt)
        if flat:
            steps.append(["flatpak-remove" if remove else "flatpak-install"] + flat)
        rc = 0
        with open(log, "w") as lf:
            for st in steps:
                argv = (["sudo", "-n", helper] if sh_rc(["sudo", "-n", "true"])[0] == 0 else ["pkexec", helper]) + st
                p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout:
                    lf.write(line); lf.flush()
                    m = re.search(r"(\d+(?:\.\d+)?)%", line)
                    if m:
                        job["progress"] = float(m.group(1))
                    job["last"] = line.strip()[-160:]
                    HUB.emit("job", {k: v for k, v in job.items() if k != "log"})
                rc = p.wait() or rc
        job["state"] = "done" if rc == 0 else "failed"
        job["progress"] = 100 if rc == 0 else job["progress"]
        HUB.emit("job", {k: v for k, v in job.items() if k != "log"})
        HUB.emit("apps-changed", None)
        verb = "removed" if remove else "installed"
        if rc == 0:
            notify("%s %s" % (", ".join(names) or os.path.basename(file or "Package"), verb),
                   "Find it in Start and Launchpad." if not remove else "", "lumina-store", "Lumina Store")
        else:
            notify("Couldn't finish: %s" % ", ".join(names or [os.path.basename(file or "")]),
                   job.get("last", "Check your internet connection and try again."), "lumina-store", "Lumina Store")
    threading.Thread(target=run, daemon=True).start()
    return job

def updates_check():
    jid = uuid.uuid4().hex[:8]
    job = {"id": jid, "names": ["System update"], "state": "running", "progress": 0, "kind": "update"}
    STORE_JOBS[jid] = job
    def run():
        argv_pre = ["sudo", "-n"] if sh_rc(["sudo", "-n", "true"])[0] == 0 else ["pkexec"]
        p = subprocess.Popen(argv_pre + ["/usr/libexec/lumina/lumina-pkg", "check"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        out = p.communicate()[0]
        ups = [l for l in out.splitlines() if l.startswith("Inst ")]
        job["state"] = "done" if p.returncode == 0 else "failed"
        job["updates"] = [l.split()[1] for l in ups]
        job["progress"] = 100
        HUB.emit("job", job)
    threading.Thread(target=run, daemon=True).start()
    return job

def updates_install():
    jid = uuid.uuid4().hex[:8]
    job = {"id": jid, "names": ["System update"], "state": "running", "progress": 0, "kind": "update"}
    STORE_JOBS[jid] = job
    def run():
        argv_pre = ["sudo", "-n"] if sh_rc(["sudo", "-n", "true"])[0] == 0 else ["pkexec"]
        p = subprocess.Popen(argv_pre + ["/usr/libexec/lumina/lumina-pkg", "upgrade"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:
            m = re.search(r"(\d+(?:\.\d+)?)%", line)
            if m:
                job["progress"] = float(m.group(1))
            job["last"] = line.strip()[-160:]
            HUB.emit("job", job)
        rc = p.wait()
        job["state"] = "done" if rc == 0 else "failed"
        HUB.emit("job", job)
        notify("Updates installed" if rc == 0 else "Update failed", "" if rc == 0 else job.get("last", ""),
               "lumina-settings", "Update & drivers")
    threading.Thread(target=run, daemon=True).start()
    return job

# ----------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "LuminaAPI/1.0"
    shell = None  # set by lumina-shell

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)) or body is None:
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype == "application/json" else "max-age=60")
        self.send_header("Access-Control-Allow-Origin", "*")
        if ctype == "text/html":
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                             "connect-src 'self'; font-src 'self';")
        elif ctype == "application/json":
            self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _file(self, path, ctype=None, cache=True):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception:
            return self._send(404, {"error": "not found"})
        ctype = ctype or mimetypes.guess_type(path)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            pass

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        p = u.path
        ip = self.client_address[0]
        if not rate_check(ip, "default"):
            audit_log(ip, "GET", p, False, "rate limited")
            return self._send(429, {"error": "rate limited"})
        if p == "/" or p == "":
            p = "/ui/desktop.html"
        if p.startswith("/ui/"):
            f = os.path.normpath(os.path.join(UI, p[4:]))
            if not f.startswith(UI):
                audit_log(ip, "GET", p, False, "forbidden")
                return self._send(403, {"error": "forbidden"})
            return self._file(f, cache=False)
        try:
            result = self.route_get(p, q)
            audit_log(ip, "GET", p, True, "")
            return result
        except Exception as e:
            import traceback; traceback.print_exc()
            audit_log(ip, "GET", p, False, str(e))
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        ip = self.client_address[0]
        p = u.path
        if not rate_check(ip, "mutating"):
            audit_log(ip, "POST", p, False, "rate limited")
            return self._send(429, {"error": "rate limited"})
        try:
            result = self.route_post(u.path, self._body())
            audit_log(ip, "POST", p, True, "")
            return result
        except Exception as e:
            import traceback; traceback.print_exc()
            audit_log(ip, "POST", p, False, str(e))
            return self._send(500, {"error": str(e)})

    # ---- GET routes
    def route_get(self, p, q):
        S = Handler.shell
        if p == "/api/health":
            return self._send(200, {"ok": True, "service": "lumina-api", "version": "1.0"})
        if p == "/api/auth/token":
            return self._send(200, {"token": ensure_token()})
        if p == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            qq = HUB.add()
            try:
                self.wfile.write(b": hello\n\n"); self.wfile.flush()
                while True:
                    try:
                        msg = qq.get(timeout=15)
                        self.wfile.write(("data: %s\n\n" % msg).encode())
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                HUB.remove(qq)
            return
        if p == "/api/settings":
            return self._send(200, get_settings())
        if p == "/api/first-run/status":
            return self._send(200, first_run_status())
        if p == "/api/system/check":
            return self._send(200, installed_boot_checks())
        if p == "/api/sys":
            return self._send(200, sysinfo())
        if p == "/api/stats":
            return self._send(200, stats())
        if p == "/api/apps":
            return self._send(200, S.apps() if S else [])
        if p == "/api/icon":
            f = S.icon_file(q.get("name", ""), int(q.get("size", 64))) if S else None
            if f:
                return self._file(f)
            return self._file(os.path.join(UI, "img", "app-generic.svg"))
        if p == "/api/windows":
            return self._send(200, S.windows() if S else [])
        if p == "/api/winicon":
            data = S.window_icon_png(int(q.get("xid", 0))) if S else None
            if data:
                return self._send(200, data, "image/png")
            return self._file(os.path.join(UI, "img", "app-generic.svg"))
        if p == "/api/winthumb":
            xid = q.get("xid", "0")
            out = subprocess.run(["import", "-silent", "-window", xid, "-resize", q.get("w", "480") + "x", "jpg:-"],
                                 capture_output=True, timeout=6).stdout
            if out:
                return self._send(200, out, "image/jpeg")
            return self._send(404, {"error": "no thumb"})
        if p == "/api/workspaces":
            return self._send(200, S.workspaces() if S else {"count": 1, "active": 0})
        if p == "/api/procs":
            pids = S.window_pids() if S else set()
            return self._send(200, processes(pids))
        if p == "/api/services":
            return self._send(200, services())
        if p == "/api/startup":
            return self._send(200, autostart_list())
        if p == "/api/users":
            users = []
            for u in psutil.users():
                users.append({"name": u.name, "terminal": u.terminal, "host": u.host, "started": u.started})
            me = pwd.getpwuid(os.getuid()).pw_name
            if not any(x["name"] == me for x in users):
                users.insert(0, {"name": me, "terminal": "Lumina session", "host": "", "started": psutil.boot_time()})
            for u in users:
                ps = [x for x in psutil.process_iter(["username", "memory_info"]) if x.info["username"] == u["name"]]
                u["mem"] = sum((x.info["memory_info"].rss if x.info["memory_info"] else 0) for x in ps)
                u["procs"] = len(ps)
            return self._send(200, users)
        if p == "/api/fs/list":
            return self._send(200, list_dir(q.get("path"), q.get("hidden") == "1"))
        if p == "/api/fs/places":
            return self._send(200, {"places": places(), "drives": drives(), "home": HOME})
        if p == "/api/fs/recent":
            return self._send(200, recent_files(int(q.get("limit", 12))))
        if p == "/api/fs/search":
            return self._send(200, search_files(q.get("q", "")))
        if p == "/api/fs/raw":
            return self._file(safe_path(q.get("path")), cache=False)
        if p == "/api/fs/thumb":
            src = safe_path(q.get("path"))
            key = re.sub(r"[^A-Za-z0-9]", "_", src)[-120:] + "_%d" % int(os.path.getmtime(src))
            dst = os.path.join(CACHE, "thumbs", key + ".jpg")
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                sh(["convert", src + "[0]", "-thumbnail", "256x256", "-quality", "80", dst], 15)
            return self._file(dst if os.path.exists(dst) else os.path.join(UI, "img", "app-generic.svg"))
        if p == "/api/fs/read":
            path = safe_path(q.get("path"))
            if os.path.getsize(path) > 8 * 1024 * 1024:
                return self._send(413, {"error": "File too large"})
            with open(path, "rb") as f:
                data = f.read()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin-1")
            add_recent(path)
            return self._send(200, {"path": path, "text": text})
        if p == "/api/audio":
            return self._send(200, audio_get())
        if p == "/api/net":
            return self._send(200, net_get())
        if p == "/api/bt":
            return self._send(200, bt_get())
        if p == "/api/display":
            return self._send(200, display_get())
        if p == "/api/notifications":
            return self._send(200, _notifs)
        if p == "/api/wallpapers":
            d = os.path.join(UI, "img", "wallpapers")
            user_d = os.path.join(HOME, ".local/share/lumina/wallpapers")
            items = [{"name": f, "url": "/ui/img/wallpapers/" + f} for f in sorted(os.listdir(d)) if f.endswith(".jpg")]
            if os.path.isdir(user_d):
                items += [{"name": "user:" + f, "url": "/api/fs/raw?path=" + urllib.parse.quote(os.path.join(user_d, f))}
                          for f in sorted(os.listdir(user_d))]
            return self._send(200, {"items": items, "credits": read_json(os.path.join(d, "credits.json"), [])})
        if p == "/api/wallpaper/blur":
            name = q.get("name") or get_settings()["wallpaper"]
            src = self.wall_path(name)
            key = re.sub(r"[^A-Za-z0-9]", "_", name)
            dst = os.path.join(CACHE, "blur-%s.jpg" % key)
            if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                sh(["convert", src, "-resize", "640x", "-blur", "0x14", "-modulate", "100,125", "-quality", "85", dst], 20)
            return self._file(dst if os.path.exists(dst) else src)
        if p == "/api/wallpaper/file":
            return self._file(self.wall_path(q.get("name") or get_settings()["wallpaper"]))
        if p == "/api/store":
            return self._send(200, store_catalog())
        if p == "/api/store/owner":
            d = q.get("desktop", "")
            info = {"desktop": d, "pkg": None, "kind": None, "name": d}
            for base in ["/usr/share/applications", "/usr/local/share/applications", os.path.join(HOME, ".local/share/applications"),
                         "/var/lib/flatpak/exports/share/applications"]:
                f = os.path.join(base, d)
                if os.path.exists(f):
                    for l in open(f, errors="ignore"):
                        if l.startswith("Name="):
                            info["name"] = l[5:].strip(); break
                    if "flatpak" in base:
                        info.update(pkg=d[:-8], kind="flatpak")
                    else:
                        out = sh(["dpkg-query", "-S", os.path.realpath(f)])
                        if ":" in out:
                            info.update(pkg=out.split(":")[0].strip(), kind="apt")
                    break
            return self._send(200, info)
        if p == "/api/store/jobs":
            return self._send(200, [{k: v for k, v in j.items() if k != "log"} for j in STORE_JOBS.values()])
        if p == "/api/timezones":
            zones = sh(["timedatectl", "list-timezones"]).split()
            cur = sh(["timedatectl", "show", "-p", "Timezone", "--value"]) or time.tzname[0]
            return self._send(200, {"zones": zones, "current": cur})
        if p == "/api/compat":
            return self._send(200, {
                "wine": bool(shutil.which("wine")),
                "wineVersion": sh(["wine", "--version"]) if shutil.which("wine") else "",
                "winePrefix": os.path.isdir(os.path.join(HOME, ".wine")),
                "waydroid": bool(shutil.which("waydroid")),
                "binder": os.path.exists("/dev/binder") or "binder" in sh("cat /proc/filesystems"),
                "flatpak": bool(shutil.which("flatpak")),
            })
        if p == "/api/power/profile/get":
            return self._send(200, {"profile": get_settings().get("performancePreset", "balanced")})
        if p == "/api/display/brightness/get":
            return self._send(200, {"level": get_settings().get("brightness", 100)})
        if p == "/api/audio/input":
            return self._send(200, {"devices": audio_inputs()})
        if p == "/api/firewall/status":
            try:
                import subprocess as _sp
                r = _sp.run(["ufw", "status"], capture_output=True, text=True)
                return self._send(200, {"enabled": "Status: active" in r.stdout, "rules": r.stdout})
            except Exception as e:
                return self._send(200, {"enabled": False, "error": str(e)})
        if p == "/api/update/auto/get":
            try:
                import subprocess as _sp
                r = _sp.run(["systemctl", "is-enabled", "unattended-upgrades"], capture_output=True, text=True)
                return self._send(200, {"enabled": r.stdout.strip() == "enabled"})
            except Exception:
                return self._send(200, {"enabled": False})
        if p == "/api/users/list":
            users = []
            try:
                import pwd as _pwd
                for ent in _pwd.getpwall():
                    if ent.pw_uid >= 1000:
                        users.append({"name": ent.pw_name, "uid": ent.pw_uid, "home": ent.pw_dir, "shell": ent.pw_shell})
            except Exception:
                pass
            return self._send(200, {"users": users})
        if p == "/api/printers/list":
            printers = []
            try:
                import subprocess as _sp
                r = _sp.run(["lpstat", "-p"], capture_output=True, text=True)
                for line in r.stdout.splitlines():
                    if line.startswith("printer "):
                        printers.append({"name": line.split()[1]})
            except Exception:
                pass
            return self._send(200, {"printers": printers})
        if p == "/api/clipboard/history":
            return self._send(200, {"items": clipboard_history()})
        return self._send(404, {"error": "unknown endpoint " + p})

    def wall_path(self, name):
        if name.startswith("user:"):
            return os.path.join(HOME, ".local/share/lumina/wallpapers", name[5:])
        if name.startswith("/"):
            return name
        return os.path.join(UI, "img", "wallpapers", name)

    # ---- POST routes
    def route_post(self, p, b):
        S = Handler.shell
        # Mutating endpoints require a valid API token (local UI pages fetch it
        # from /api/auth/token on startup).  Read-only GETs stay open.
        SENSITIVE_POST = {
            "/api/settings", "/api/window", "/api/workspace", "/api/power",
            "/api/fs/write", "/api/fs/mkdir", "/api/fs/newfile", "/api/fs/rename",
            "/api/fs/trash", "/api/fs/delete", "/api/fs/emptytrash", "/api/fs/restore",
            "/api/fs/copy", "/api/fs/archive/extract", "/api/fs/archive/create",
            "/api/fs/permissions", "/api/fs/mount", "/api/audio", "/api/net",
            "/api/display", "/api/proc/kill", "/api/proc/efficiency", "/api/startup",
            "/api/service", "/api/store/install", "/api/update/install",
            "/api/timezone", "/api/hostname", "/api/compat/setup", "/api/password",
            "/api/auth", "/api/run", "/api/snip", "/api/wallpaper/upload",
        }
        if p in SENSITIVE_POST and not token_ok(self.headers):
            return self._send(401, {"error": "authentication required"})
        if p == "/api/settings":
            try:
                return self._send(200, set_settings(b))
            except ValueError as e:
                return self._send(400, {"error": str(e)})
        if p == "/api/first-run/complete":
            if is_live_session():
                return self._send(200, {"ok": False, "error": "Setup is available only after installation."})
            return self._send(200, complete_first_run())
        if p == "/api/launch":
            ok = S.launch(b.get("id"), b.get("args") or []) if S else False
            return self._send(200, {"ok": ok})
        if p == "/api/run":
            cmd = b.get("cmd", "").strip()
            if cmd:
                spawn(["sh", "-c", cmd])
            return self._send(200, {"ok": bool(cmd)})
        if p == "/api/window":
            return self._send(200, {"ok": S.window_action(int(b.get("xid", 0)), b.get("action")) if S else False})
        if p == "/api/workspace":
            S.set_workspace(int(b.get("n", 0)))
            return self._send(200, {"ok": True})
        if p == "/api/ui":
            HUB.emit("ui", b)
            return self._send(200, {"ok": True})
        if p == "/api/proc/kill":
            try:
                pr = psutil.Process(int(b["pid"]))
                pr.terminate() if not b.get("force") else pr.kill()
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/proc/efficiency":
            try:
                pr = psutil.Process(int(b["pid"]))
                pr.nice(19 if b.get("on", True) else 0)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/startup":
            return self._send(200, {"ok": autostart_set(b["id"], bool(b["enabled"]))})
        if p == "/api/service":
            rc, out = sh_rc(["systemctl", b.get("action", "status"), b["name"]], 30)
            return self._send(200, {"ok": rc == 0, "msg": out})
        if p == "/api/fs/open":
            return self._send(200, open_path(b.get("path")))
        if p == "/api/fs/write":
            path = safe_path(b["path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(b.get("text", ""))
            add_recent(path)
            return self._send(200, {"ok": True, "path": path})
        if p == "/api/fs/mkdir":
            base = safe_path(b["path"])
            name = b.get("name") or "New folder"
            target = os.path.join(base, name)
            i = 2
            while os.path.exists(target):
                target = os.path.join(base, "%s (%d)" % (name, i)); i += 1
            os.makedirs(target)
            return self._send(200, {"ok": True, "path": target})
        if p == "/api/fs/newfile":
            base = safe_path(b["path"])
            name = b.get("name") or "New text document.txt"
            target = os.path.join(base, name)
            stem, ext = os.path.splitext(name)
            i = 2
            while os.path.exists(target):
                target = os.path.join(base, "%s (%d)%s" % (stem, i, ext)); i += 1
            open(target, "w").close()
            return self._send(200, {"ok": True, "path": target})
        if p == "/api/fs/rename":
            src = safe_path(b["path"])
            dst = os.path.join(os.path.dirname(src), b["name"])
            if os.path.exists(dst):
                return self._send(200, {"ok": False, "error": "A file with that name already exists."})
            os.rename(src, dst)
            return self._send(200, {"ok": True, "path": dst})
        if p == "/api/fs/trash":
            return self._send(200, {"ok": trash([safe_path(x) for x in b["paths"]])})
        if p == "/api/fs/delete":
            for x in b["paths"]:
                x = safe_path(x)
                shutil.rmtree(x) if os.path.isdir(x) and not os.path.islink(x) else os.remove(x)
            return self._send(200, {"ok": True})
        if p == "/api/fs/emptytrash":
            empty_trash()
            return self._send(200, {"ok": True})
        if p == "/api/fs/restore":
            try:
                return self._send(200, {"ok": trash_restore(b["path"])})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/fs/copy":
            try:
                return self._send(200, {"ok": True, "paths": copy_paths(b["paths"], b["dest"], b.get("move"), b.get("conflict", "rename"))})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/fs/archive/extract":
            try:
                return self._send(200, {"ok": archive_extract(b["path"], b.get("dest", os.path.dirname(safe_path(b["path"]))))})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/fs/archive/create":
            try:
                target = archive_create(b["paths"], b.get("dest"), b.get("name", "Archive.zip"))
                return self._send(200, {"ok": True, "path": target})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/fs/permissions":
            try:
                if "mode" in b:
                    return self._send(200, {"ok": True, "info": set_file_permissions(b["path"], b["mode"])})
                return self._send(200, {"ok": True, "info": file_permissions(b["path"])})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/fs/mount":
            return self._send(200, mount_dev(b["dev"]))
        if p == "/api/audio":
            return self._send(200, audio_set(b.get("volume"), b.get("muted")))
        if p == "/api/net":
            if "enabled" in b:
                sh(["nmcli", "networking", "on" if b["enabled"] else "off"])
            if b.get("connect"):
                args = ["nmcli", "dev", "wifi", "connect", b["connect"]]
                if b.get("password"):
                    args += ["password", b["password"]]
                rc, out = sh_rc(args, 40)
                return self._send(200, {"ok": rc == 0, "msg": out})
            r = net_get()
            HUB.emit("net", r)
            return self._send(200, r)
        if p == "/api/display":
            return self._send(200, display_set(b["output"], b["mode"]))
        if p == "/api/power":
            a = b.get("action")
            if a == "lock":
                HUB.emit("ui", {"cmd": "lock"})
            elif a == "shutdown":
                spawn(["systemctl", "poweroff"])
            elif a == "reboot":
                spawn(["systemctl", "reboot"])
            elif a == "suspend":
                HUB.emit("ui", {"cmd": "lock"})
                spawn(["sh", "-c", "sleep 1; systemctl suspend"])
            elif a == "logout":
                spawn(["sh", "-c", "loginctl terminate-session ${XDG_SESSION_ID:-} || pkill -u $(id -u) lumina-session"])
            return self._send(200, {"ok": True})
        if p == "/api/auth":
            user = pwd.getpwuid(os.getuid()).pw_name
            ok = pam_auth(user, b.get("password", ""))
            if not ok and (os.path.exists("/run/live/medium") or os.environ.get("LUMINA_DEV")) and b.get("password", "") in ("live", ""):
                ok = True
            return self._send(200, {"ok": ok})
        if p == "/api/password":
            user = pwd.getpwuid(os.getuid()).pw_name
            if not pam_auth(user, b.get("old", "")):
                return self._send(200, {"ok": False, "error": "Current password is wrong."})
            rc, out = sh_rc(["passwd"], 20, "%s\n%s\n%s\n" % (b["old"], b["new"], b["new"]))
            return self._send(200, {"ok": rc == 0, "error": out if rc else ""})
        if p == "/api/notify":
            return self._send(200, notify(b.get("title", ""), b.get("body", ""), b.get("icon", ""), b.get("app", "LuminaOS")))
        if p == "/api/clipboard/copy":
            return self._send(200, clipboard_copy(b.get("index", 0)))
        if p == "/api/clipboard/clear":
            return self._send(200, {"ok": clipboard_clear(b.get("index"), b.get("all", False))})
        if p == "/api/notifications/action":
            HUB.emit("notification-action", b)
            if b.get("cmd"):
                try:
                    spawn(shlex.split(b["cmd"]))
                except Exception:
                    pass
            return self._send(200, {"ok": True})
        if p == "/api/notifications/snooze":
            minutes = max(1, min(1440, int(b.get("minutes", 15))))
            set_settings({"focusUntil": time.time() + minutes * 60})
            return self._send(200, {"ok": True, "until": get_settings().get("focusUntil")})
        if p == "/api/notifications/clear":
            with _notif_lock:
                if b.get("id"):
                    _notifs[:] = [n for n in _notifs if n["id"] != b["id"]]
                else:
                    _notifs.clear()
                write_json(NOTIF_FILE, _notifs)
            HUB.emit("notifications-changed", None)
            return self._send(200, {"ok": True})
        if p == "/api/snip":
            return self._send(200, S.snip(b.get("mode", "full"), float(b.get("delay", 0))) if S else {})
        if p == "/api/wallpaper/upload":
            src = safe_path(b["path"])
            d = os.path.join(HOME, ".local/share/lumina/wallpapers")
            os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, os.path.basename(src))
            shutil.copy(src, dst)
            set_settings({"wallpaper": "user:" + os.path.basename(src)})
            return self._send(200, {"ok": True})
        if p == "/api/store/install":
            return self._send(200, store_install(b.get("ids", []), b.get("remove", False), b.get("file"), b.get("pkgs")))
        if p == "/api/update/check":
            return self._send(200, updates_check())
        if p == "/api/update/install":
            return self._send(200, updates_install())
        if p == "/api/timezone":
            rc, out = sh_rc(["timedatectl", "set-timezone", b["zone"]], 30)
            return self._send(200, {"ok": rc == 0, "msg": out})
        if p == "/api/hostname":
            rc, out = sh_rc(["hostnamectl", "set-hostname", b["name"]], 30)
            return self._send(200, {"ok": rc == 0, "msg": out})
        if p == "/api/compat/setup":
            what = b.get("what")
            if what == "wine":
                spawn(["sh", "-c", "WINEDEBUG=-all wineboot -u && notify-send -i lumina-windows 'Windows programs are ready' 'Double-click any .exe file to run it.'"])
            elif what == "winecfg":
                spawn(["winecfg"])
            elif what == "android":
                spawn(["lumina-app", "store", "--android"])
            return self._send(200, {"ok": True})
        # ---------------------------------------------------------------- power profiles (5.1)
        if p == "/api/power/profile":
            prof = b.get("profile", "balanced")
            target = {"powersaver": "low-power", "performance": "custom"}.get(prof, prof)
            if target not in ("custom", "balanced", "low-power"):
                return self._send(200, {"ok": False, "error": "unknown profile"})
            patch = {"performancePreset": target}
            if prof == "performance":
                patch.update({"reduceMotion": False, "transparency": True,
                              "dockMagnify": True, "perfShadows": True})
            set_settings(patch)
            try:
                import subprocess as _sp
                gov = {"powersaver": "powersave", "low-power": "powersave",
                       "performance": "performance", "balanced": "schedutil"}[prof]
                _sp.run(["cpupower", "frequency-set", "-g", gov], capture_output=True)
            except Exception:
                pass
            HUB.emit("power-profile", {"profile": prof})
            return self._send(200, {"ok": True, "profile": prof})
        # ---------------------------------------------------------------- display brightness (5.3)
        if p == "/api/display/brightness":
            level = max(0, min(100, int(b.get("level", 100))))
            try:
                import subprocess as _sp
                _sp.run(["xbacklight", "-set", str(level)], capture_output=True)
            except Exception:
                pass
            set_settings({"brightness": level})
            HUB.emit("brightness", {"level": level})
            return self._send(200, {"ok": True, "level": level})
        # ---------------------------------------------------------------- sound input devices (5.2)
        if p == "/api/audio/input/set":
            name = b.get("device", "")
            try:
                import subprocess as _sp
                _sp.run(["pactl", "set-default-source", name], capture_output=True)
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True})
        # ---------------------------------------------------------------- firewall (5.4)
        if p == "/api/firewall/toggle":
            on = bool(b.get("on", True))
            try:
                import subprocess as _sp
                _sp.run(["ufw"] + (["enable"] if on else ["disable"]), capture_output=True)
                return self._send(200, {"ok": True, "enabled": on})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---------------------------------------------------------------- backup / restore (5.5)
        if p == "/api/backup/create":
            dest = b.get("dest", os.path.join(HOME, "lumina-backup.tar.gz"))
            try:
                import tarfile as _tf
                with _tf.open(dest, "w:gz") as tf:
                    for d in (CONF_DIR, os.path.join(HOME, ".local"), os.path.join(HOME, ".config")):
                        if os.path.isdir(d):
                            tf.add(d, arcname=os.path.basename(d))
                return self._send(200, {"ok": True, "dest": dest})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/backup/restore":
            src = safe_path(b.get("src", ""))
            if not src or not os.path.isfile(src):
                return self._send(200, {"ok": False, "error": "backup file not found"})
            try:
                import tarfile as _tf
                with _tf.open(src, "r:gz") as tf:
                    tf.extractall(HOME)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---------------------------------------------------------------- auto-updates (5.6)
        if p == "/api/update/auto":
            enable = bool(b.get("enable", True))
            try:
                import subprocess as _sp
                if enable:
                    _sp.run(["systemctl", "enable", "--now", "unattended-upgrades"], capture_output=True)
                else:
                    _sp.run(["systemctl", "disable", "--now", "unattended-upgrades"], capture_output=True)
                return self._send(200, {"ok": True, "enabled": enable})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---------------------------------------------------------------- user accounts (5.7)
        if p == "/api/users/add":
            name = b.get("name", "")
            if not re.fullmatch(r"[a-z_][a-z0-9_-]*", name):
                return self._send(200, {"ok": False, "error": "invalid username"})
            try:
                import subprocess as _sp
                _sp.run(["useradd", "-m", name], capture_output=True)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/users/remove":
            name = b.get("name", "")
            try:
                import subprocess as _sp
                _sp.run(["userdel", "-r", name], capture_output=True)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---------------------------------------------------------------- printers (5.8)
        if p == "/api/printers/add":
            uri = b.get("uri", "")
            name = b.get("name", "Printer")
            try:
                import subprocess as _sp
                _sp.run(["lpadmin", "-p", name, "-v", uri, "-E"], capture_output=True)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        return self._send(404, {"error": "unknown endpoint " + p})

# ----------------------------------------------------------------- clipboard history (4.5)
CLIP_DIR = os.path.join(CACHE, "clipboard")
CLIP_FILE = os.path.join(CLIP_DIR, "history")
CLIP_MAX = 100
os.makedirs(CLIP_DIR, exist_ok=True)
if not os.path.exists(CLIP_FILE):
    open(CLIP_FILE, "w").close()


def clipboard_history():
    try:
        with open(CLIP_FILE, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
            return [{"text": l} for l in lines[-CLIP_MAX:]]
    except Exception:
        return []


def clipboard_add(text):
    try:
        with open(CLIP_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        # Trim
        with open(CLIP_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if len(lines) > CLIP_MAX:
            with open(CLIP_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines[-CLIP_MAX:]) + "\n")
    except Exception:
        pass


def clipboard_clear(index=None, all=False):
    try:
        with open(CLIP_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if all:
            lines = []
        elif index is not None and 0 <= index < len(lines):
            lines = lines[:index] + lines[index + 1:]
        with open(CLIP_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception:
        return False


def clipboard_copy(index=0):
    try:
        with open(CLIP_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if 0 <= index < len(lines):
            import subprocess
            subprocess.run(["xclip", "-selection", "clipboard"], input=lines[index], text=True, capture_output=True)
            return {"ok": True, "text": lines[index]}
        return {"ok": False, "error": "index out of range"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------------------------------- clipboard history end
def audio_inputs():
    """List PulseAudio/PipeWire input sources."""
    try:
        import subprocess as _sp
        r = _sp.run(["pactl", "list", "short", "sources"], capture_output=True, text=True)
        srcs = []
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                srcs.append({"name": parts[1], "description": parts[0]})
        return srcs
    except Exception:
        return []


def serve(shell, port=7700):
    Handler.shell = shell
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
