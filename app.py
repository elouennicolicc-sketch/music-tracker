import os
import sqlite3
from flask import Flask, redirect, request, session, render_template, url_for
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-please")

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3000/callback")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

SCOPES = "user-read-recently-played user-read-email"

DB_PATH = os.path.join(os.path.dirname(__file__), "tracker.db")

CHRISTIAN_KEYWORDS = [
    "christian", "gospel", "worship", "ccm", "praise",
    "hymn", "chretien", "louange", "adoration", "christ",
    "catholic", "catholique", "gregorian", "gregorien",
]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            display_name TEXT,
            email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            track_name TEXT,
            artist_name TEXT,
            played_at TEXT,
            category TEXT,
            UNIQUE(user_id, track_name, played_at)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artist_cache (
            artist_id TEXT PRIMARY KEY,
            artist_name TEXT,
            category TEXT
        )
    """)
    conn.commit()
    conn.close()


def classify_artist(conn, artist_id, artist_name, access_token):
    row = conn.execute(
        "SELECT category FROM artist_cache WHERE artist_id = ?", (artist_id,)
    ).fetchone()
    if row:
        return row["category"]

    resp = requests.get(
        f"{API_BASE}/artists/{artist_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    category = "mondain"
    if resp.status_code == 200:
        genres = resp.json().get("genres", [])
        genres_text = " ".join(genres).lower()
        if any(k in genres_text for k in CHRISTIAN_KEYWORDS):
            category = "chretien"

    if category == "mondain":
        name_lower = artist_name.lower()
        if any(k in name_lower for k in CHRISTIAN_KEYWORDS):
            category = "chretien"

    conn.execute(
        "INSERT OR REPLACE INTO artist_cache (artist_id, artist_name, category) VALUES (?, ?, ?)",
        (artist_id, artist_name, category),
    )
    return category


@app.route("/")
def index():
    if "access_token" not in session:
        return render_template("login.html")
    return redirect(url_for("dashboard"))


@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "show_dialog": "true",
    }
    query = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
    return redirect(f"{AUTH_URL}?{query}")


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Erreur: pas de code retourné par Spotify", 400

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    if resp.status_code != 200:
        return f"Erreur d'authentification: {resp.text}", 400

    token_data = resp.json()
    session["access_token"] = token_data["access_token"]
    session["refresh_token"] = token_data.get("refresh_token")

    profile = requests.get(
        f"{API_BASE}/me",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    ).json()

    session["user_id"] = profile["id"]
    session["display_name"] = profile.get("display_name", profile["id"])

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO users (id, display_name, email) VALUES (?, ?, ?)",
        (profile["id"], profile.get("display_name"), profile.get("email")),
    )
    conn.commit()
    conn.close()

    sync_recent_plays()

    return redirect(url_for("dashboard"))


def sync_recent_plays():
    access_token = session["access_token"]
    user_id = session["user_id"]

    resp = requests.get(
        f"{API_BASE}/me/player/recently-played?limit=50",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if resp.status_code != 200:
        return

    items = resp.json().get("items", [])
    conn = get_db()
    for item in items:
        track = item["track"]
        played_at = item["played_at"]
        track_name = track["name"]
        artist = track["artists"][0]
        artist_id = artist["id"]
        artist_name = artist["name"]

        category = classify_artist(conn, artist_id, artist_name, access_token)

        try:
            conn.execute(
                """INSERT OR IGNORE INTO plays
                   (user_id, track_name, artist_name, played_at, category)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, track_name, artist_name, played_at, category),
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


@app.route("/sync")
def sync():
    if "access_token" not in session:
        return redirect(url_for("index"))
    sync_recent_plays()
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "access_token" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM plays WHERE user_id = ? GROUP BY category",
        (user_id,),
    ).fetchall()
    conn.close()

    counts = {"chretien": 0, "mondain": 0}
    for row in rows:
        counts[row["category"]] = row["count"]

    total = counts["chretien"] + counts["mondain"]
    pct_chretien = round((counts["chretien"] / total) * 100, 1) if total else 0
    pct_mondain = round((counts["mondain"] / total) * 100, 1) if total else 0

    return render_template(
        "dashboard.html",
        display_name=session.get("display_name"),
        counts=counts,
        pct_chretien=pct_chretien,
        pct_mondain=pct_mondain,
        total=total,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False) 