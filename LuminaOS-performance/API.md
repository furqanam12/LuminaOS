# LuminaOS API Reference

LuminaOS exposes a local HTTP + Server-Sent-Events API on `127.0.0.1:7700` (port configurable via `LUMINA_PORT`). The shell UI and all built-in apps communicate through it.

## Base URL

```
http://127.0.0.1:7700
```

All JSON endpoints return `application/json`. HTML UI pages are served under `/ui/`.

## Authentication

Mutating POST endpoints require an `X-Lumina-Token` header. The token is a per-boot random string stored in `~/.cache/lumina/api-token` (mode `0600`).

- `GET /api/auth/token` — returns `{"token": "..."}`; call this once on page load and cache the value (e.g. in `localStorage`).
- The JS client (`lumina.js`) `L.post()` automatically sends `X-Lumina-Token` from `localStorage.lumina-token`, and on a `401` response it fetches a fresh token and retries.

Read-only GET endpoints do not require authentication.

## Events (SSE)

- `GET /api/events` — text/event-stream. Emits JSON messages like `data: {"event":"settings","data":{...}}\n\n`. Also sends `: ping\n\n` every 15 seconds as a keep-alive.

## Health

- `GET /api/health` — returns `{"ok":true,"service":"lumina-api","version":"1.0"}`. Use for liveness checks.

## System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sys` | GET | System info (vendor, product, os, version, kernel, cpu, cores, mem, disk, gpu, arch, hostname) |
| `/api/stats` | GET | Live stats (cpu percent, memory, disk, net IO, top processes) |
| `/api/apps` | GET | List installed applications |
| `/api/first-run/status` | GET | First-run setup status |

## Settings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Get all user settings |
| `/api/settings` | POST | Update settings (body: JSON object). Validated via `performance_patch()`. |

Known settings keys: `theme`, `accent`, `wallpaper`, `reduceMotion`, `transparency`, `dockSize`, `dockMagnify`, `clock24`, `focus`, `focusUntil`, `quietStart`, `quietEnd`, `notificationRules`, `widgets`, `pinned`, `startPinned`, `brightness`, `nightLight`, `uiScale`, `highContrast`, `strongFocus`, `performancePreset`, `perfShadows`, `blank` (screen-off seconds), `autolock`.

## Windows & Workspaces

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/windows` | GET | List open windows (xid, title, class, geometry, state) |
| `/api/winicon` | GET | Window icon PNG (`?xid=...`) |
| `/api/winthumb` | GET | Window thumbnail JPEG (`?xid=...&w=480`) |
| `/api/workspaces` | GET | Workspace list (`{count, active}`) |
| `/api/window` | POST | Window action (body: `{xid, action}` where action is move/resize/minimize/maximize/close/snap/present) |
| `/api/workspace` | POST | Switch workspace (body: `{n}`) |

## Processes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/procs` | GET | List processes (pid, name, cpu, mem, user) |
| `/api/proc/kill` | POST | Terminate/kill a process (body: `{pid, force?}`) |
| `/api/proc/efficiency` | POST | Set process nice level (body: `{pid, on?}`) |

## Audio

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audio` | GET | Get volume/muted state |
| `/api/audio` | POST | Set volume/muted (body: `{volume?, muted?}`) |

## Network

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/net` | GET | Network devices, Wi-Fi scan, connectivity |
| `/api/net` | POST | Toggle networking (`{enabled}`) or connect to Wi-Fi (`{connect: SSID, password?}`) |

## Bluetooth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bt` | GET | Bluetooth availability |

## Display

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/display` | GET | Connected outputs, current mode, available modes |
| `/api/display` | POST | Set output mode (body: `{output, mode}`) |

## Power

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/power` | POST | Power action (body: `{action}` where action is `lock`, `shutdown`, `reboot`, `suspend`, `logout`) |

## Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users` | GET | List logged-in users with memory/process counts |
| `/api/auth` | POST | Verify password (body: `{password}`) |
| `/api/password` | POST | Change password (body: `{old, new}`) |

## File System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fs/list` | GET | Directory listing (`?path=`) |
| `/api/fs/places` | GET | Bookmarks and drives |
| `/api/fs/recent` | GET | Recent files (`?limit=12`) |
| `/api/fs/search` | GET | File search (`?q=`) |
| `/api/fs/raw` | GET | Download a file (`?path=`) |
| `/api/fs/thumb` | GET | Thumbnail JPEG (`?path=`) |
| `/api/fs/read` | GET | Read text file (`?path=`) |
| `/api/fs/open` | POST | Open a path with the default app (body: `{path}`) |
| `/api/fs/write` | POST | Write text to a file (body: `{path, text}`) |
| `/api/fs/mkdir` | POST | Create a directory (body: `{path, name?}`) |
| `/api/fs/newfile` | POST | Create a new file (body: `{path, name?}`) |
| `/api/fs/rename` | POST | Rename (body: `{path, name}`) |
| `/api/fs/trash` | POST | Move to trash (body: `{paths: [...]}`) |
| `/api/fs/delete` | POST | Permanently delete (body: `{paths: [...]}`) |
| `/api/fs/emptytrash` | POST | Empty trash |
| `/api/fs/restore` | POST | Restore from trash (body: `{path}`) |
| `/api/fs/copy` | POST | Copy/move (body: `{paths, dest, move?, conflict?}`) |
| `/api/fs/archive/extract` | POST | Extract archive (body: `{path, dest?}`) |
| `/api/fs/archive/create` | POST | Create zip (body: `{paths, dest, name?}`) |
| `/api/fs/permissions` | GET/POST | Get/set file permissions (body: `{path, mode?}`) |
| `/api/fs/mount` | POST | Mount a device (body: `{dev}`) |

## Wallpapers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wallpapers` | GET | List available wallpapers with credits |
| `/api/wallpaper/file` | GET | Serve wallpaper image (`?name=`) |
| `/api/wallpaper/blur` | GET | Blurred wallpaper variant (`?name=`) |
| `/api/wallpaper/upload` | POST | Copy a user image into wallpapers and set it (body: `{path}`) |

## Store / Package Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/store` | GET | Store catalog (apps, categories, install status) |
| `/api/store/owner` | GET | Package/desktop-file ownership info (`?desktop=`) |
| `/api/store/install` | POST | Install/remove packages or flatpaks (body: `{ids, remove?, file?, pkgs?}`) |
| `/api/update/check` | POST | Check for system updates (returns a job) |
| `/api/update/install` | POST | Install system updates (returns a job) |
| `/api/compat` | GET | Wine/Waydroid/flatpak availability |
| `/api/compat/setup` | POST | Setup Wine / Android (body: `{what: "wine|winecfg|android"}`) |

Jobs are tracked under `STORE_JOBS` and announced via the SSE hub as `job` events. Progress is emitted as percentages.

## Notifications

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications` | GET | List current notifications |
| `/api/notify` | POST | Show a notification (body: `{title, body, icon, app}`) |
| `/api/notifications/action` | POST | Handle a notification action (body: `{cmd, ...}`) |
| `/api/notifications/snooze` | POST | Snooze notifications (body: `{minutes}`) |
| `/api/notifications/clear` | POST | Clear notifications (body: `{id?}`) |

## Snip (Screenshot)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/snip` | POST | Take a screenshot (body: `{mode: "full\|region\|window", delay?: number}`) |

## Misc

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | POST | Run a shell command (body: `{cmd}`) |
| `/api/launch` | POST | Launch a Lumina app (body: `{id, args?}`) |
| `/api/ui` | POST | Send a UI command to the shell (body: `{cmd, arg?}`) |
| `/api/service` | POST | systemctl action (body: `{action, name}`) |
| `/api/startup` | GET/POST | Autostart app list / enable-disable (body: `{id, enabled}`) |
| `/api/timezone` | GET/POST | List/set time zones (POST body: `{zone}`) |
| `/api/hostname` | POST | Set hostname (body: `{name}`) |

## Errors

All endpoints return JSON. Errors use standard HTTP status codes:
- `400` — bad request (validation error)
- `401` — authentication required (mutating endpoints without valid token)
- `403` — forbidden (path traversal attempt on `/ui/`)
- `404` — unknown endpoint or resource not found
- `413` — file too large (`/api/fs/read` > 8 MB)
- `500` — internal server error (with stack trace printed to shell log)

## CORS

`Access-Control-Allow-Origin: *` is set on all responses. HTML pages also get a Content-Security-Policy header; JSON responses get `X-Content-Type-Options: nosniff`.