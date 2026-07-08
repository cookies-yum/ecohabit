"""
database.py
------------
All persistence for EcoHabit. SQLite via the stdlib sqlite3 module.
The Flask routes in app.py never write raw SQL — they only call methods
on EcoDatabase, keeping backend logic separate from the web layer.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta, date

from carbon_data import get_habit, get_store_item, get_plant_catalog, GROWTH_STAGES, ECOBITS_PER_STAGE

TRUST_START = 50
TRUST_MAX = 100
TRUST_MIN = 0
TRUST_GATE = 20  # below this, checkin-type habits require rebuilding trust via photo habits first


class EcoDatabase:
    def __init__(self, db_path="ecohabit.db"):
        self.db_path = db_path
        self._create_tables()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _create_tables(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            ecobits INTEGER NOT NULL DEFAULT 0,
            total_co2_saved REAL NOT NULL DEFAULT 0,
            trust_score INTEGER NOT NULL DEFAULT 50,
            language TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            co2_saved REAL NOT NULL,
            ecobits_earned INTEGER NOT NULL,
            verify_method TEXT NOT NULL,
            logged_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS user_plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            catalog_id INTEGER NOT NULL,
            growth_progress REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            cost INTEGER NOT NULL,
            purchased_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            post_type TEXT NOT NULL DEFAULT 'Progress',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )""")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _hash(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def register_user(self, username, email, password):
        username = username.strip()
        if not username or not password:
            return False, "Username and password are required."
        if len(password) < 4:
            return False, "Password must be at least 4 characters."
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, email.strip(), self._hash(password), datetime.now().isoformat()),
            )
            conn.commit()
            user_id = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"]
            # give every new user a free Baby Cactus starter plant
            conn.execute(
                "INSERT INTO user_plants (user_id, catalog_id, growth_progress, created_at) VALUES (?, 1, 0, ?)",
                (user_id, datetime.now().isoformat()),
            )
            conn.commit()
            return True, "Account created!"
        except sqlite3.IntegrityError:
            return False, "That username is already taken."
        finally:
            conn.close()

    def login(self, username, password):
        conn = self._connect()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and row["password_hash"] == self._hash(password):
            return dict(row)
        return None

    def get_user(self, user_id):
        conn = self._connect()
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def set_language(self, user_id, lang_code):
        conn = self._connect()
        conn.execute("UPDATE users SET language=? WHERE id=?", (lang_code, user_id))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Habit logging (with verification bookkeeping)
    # ------------------------------------------------------------------
    def already_logged_today(self, user_id, habit_id):
        today = date.today().isoformat()
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM habit_logs WHERE user_id=? AND habit_id=? AND logged_at LIKE ?",
            (user_id, habit_id, today + "%"),
        ).fetchone()
        conn.close()
        return row["n"] > 0

    def get_trust_score(self, user_id):
        return self.get_user(user_id)["trust_score"]

    def adjust_trust(self, user_id, delta):
        conn = self._connect()
        row = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
        new_score = max(TRUST_MIN, min(TRUST_MAX, row["trust_score"] + delta))
        conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_score, user_id))
        conn.commit()
        conn.close()
        return new_score

    def trust_gated(self, user_id):
        """True if this user's checkin habits are currently gated behind photo-only mode."""
        return self.get_trust_score(user_id) < TRUST_GATE

    def commit_habit_log(self, user_id, habit_id, verify_method):
        habit = get_habit(habit_id)
        conn = self._connect()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO habit_logs (user_id, habit_id, co2_saved, ecobits_earned, verify_method, logged_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, habit_id, habit["co2"], habit["ecobits"], verify_method, now),
        )
        conn.execute(
            "UPDATE users SET ecobits = ecobits + ?, total_co2_saved = total_co2_saved + ? WHERE id=?",
            (habit["ecobits"], habit["co2"], user_id),
        )
        conn.commit()
        conn.close()
        return {"ecobits_earned": habit["ecobits"], "co2_saved": habit["co2"]}

    def get_user_logs(self, user_id, limit=20):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM habit_logs WHERE user_id=? ORDER BY logged_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        out = []
        for r in rows:
            row = dict(r)
            h = get_habit(row["habit_id"])
            row["habit_name"] = h["name"] if h else "Unknown"
            row["category"] = h["category"] if h else ""
            row["icon"] = h["icon"] if h else "🌿"
            out.append(row)
        return out

    def get_habits_logged_count(self, user_id):
        conn = self._connect()
        row = conn.execute("SELECT COUNT(*) as n FROM habit_logs WHERE user_id=?", (user_id,)).fetchone()
        conn.close()
        return row["n"]

    def get_current_streak(self, user_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT DISTINCT date(logged_at) as d FROM habit_logs WHERE user_id=? ORDER BY d DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        days = [r["d"] for r in rows]
        if not days:
            return 0
        streak = 0
        cursor = date.today()
        day_set = set(days)
        if cursor.isoformat() not in day_set:
            cursor = cursor - timedelta(days=1)
        while cursor.isoformat() in day_set:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def get_weekly_co2(self, user_id):
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        conn = self._connect()
        row = conn.execute(
            "SELECT COALESCE(SUM(co2_saved),0) as t FROM habit_logs WHERE user_id=? AND logged_at>=?",
            (user_id, cutoff),
        ).fetchone()
        conn.close()
        return round(row["t"], 2)

    def get_category_breakdown(self, user_id):
        logs = self.get_user_logs(user_id, limit=10000)
        out = {}
        for log in logs:
            out[log["category"]] = out.get(log["category"], 0) + log["co2_saved"]
        return out

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------
    def get_leaderboard(self, limit=10):
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, username, ecobits, total_co2_saved FROM users ORDER BY ecobits DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        out = []
        for r in rows:
            row = dict(r)
            row["streak"] = self.get_current_streak(row["id"])
            out.append(row)
        return out

    def get_user_rank(self, user_id):
        conn = self._connect()
        rows = conn.execute("SELECT id FROM users ORDER BY ecobits DESC").fetchall()
        conn.close()
        for i, r in enumerate(rows, start=1):
            if r["id"] == user_id:
                return i
        return None

    # ------------------------------------------------------------------
    # My Plants
    # ------------------------------------------------------------------
    def get_user_plants(self, user_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM user_plants WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        conn.close()
        out = []
        for r in rows:
            row = dict(r)
            cat = get_plant_catalog(row["catalog_id"])
            row["name"] = cat["name"] if cat else "Unknown"
            row["rarity"] = cat["rarity"] if cat else "Common"
            row["emoji"] = cat["emoji"] if cat else "🌱"
            row["stage"] = min(GROWTH_STAGES, int(row["growth_progress"] // ECOBITS_PER_STAGE) + 1)
            row["max_ecobits"] = GROWTH_STAGES * ECOBITS_PER_STAGE
            row["pct"] = min(100, round(100 * row["growth_progress"] / (GROWTH_STAGES * ECOBITS_PER_STAGE)))
            out.append(row)
        return out

    def buy_plant(self, user_id, catalog_id):
        cat = get_plant_catalog(catalog_id)
        if not cat:
            return {"success": False, "message": "Plant not found."}
        user = self.get_user(user_id)
        if not cat["free_starter"] and user["ecobits"] < cat["cost"]:
            return {"success": False, "message": f"Not enough ecobits — need {cat['cost'] - user['ecobits']} more."}
        conn = self._connect()
        if not cat["free_starter"]:
            conn.execute("UPDATE users SET ecobits = ecobits - ? WHERE id=?", (cat["cost"], user_id))
        conn.execute(
            "INSERT INTO user_plants (user_id, catalog_id, growth_progress, created_at) VALUES (?, ?, 0, ?)",
            (user_id, catalog_id, datetime.now().isoformat()),
        )
        conn.execute(
            "INSERT INTO purchases (user_id, item_id, item_type, cost, purchased_at) VALUES (?, ?, 'plant', ?, ?)",
            (user_id, catalog_id, 0 if cat["free_starter"] else cat["cost"], datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"'{cat['name']}' added to My Plants!"}

    def water_plant(self, user_id, plant_id, cost=10):
        conn = self._connect()
        plant = conn.execute(
            "SELECT * FROM user_plants WHERE id=? AND user_id=?", (plant_id, user_id)
        ).fetchone()
        if not plant:
            conn.close()
            return {"success": False, "message": "Plant not found."}
        user = self.get_user(user_id)
        max_growth = GROWTH_STAGES * ECOBITS_PER_STAGE
        if plant["growth_progress"] >= max_growth:
            conn.close()
            return {"success": False, "message": "This plant is already fully grown!"}
        if user["ecobits"] < cost:
            conn.close()
            return {"success": False, "message": f"Not enough ecobits — need {cost}."}
        new_growth = min(max_growth, plant["growth_progress"] + cost)
        conn.execute("UPDATE user_plants SET growth_progress=? WHERE id=?", (new_growth, plant_id))
        conn.execute("UPDATE users SET ecobits = ecobits - ? WHERE id=?", (cost, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Plant watered! 💧"}

    # ------------------------------------------------------------------
    # EcoStore (non-plant items)
    # ------------------------------------------------------------------
    def get_owned_item_ids(self, user_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT item_id FROM purchases WHERE user_id=? AND item_type='store'", (user_id,)
        ).fetchall()
        conn.close()
        return {r["item_id"] for r in rows}

    def purchase_store_item(self, user_id, item_id):
        item = get_store_item(item_id)
        if not item:
            return {"success": False, "message": "Item not found."}
        if item_id in self.get_owned_item_ids(user_id):
            return {"success": False, "message": "You already own this."}
        user = self.get_user(user_id)
        if user["ecobits"] < item["cost"]:
            return {"success": False, "message": f"Not enough ecobits — need {item['cost'] - user['ecobits']} more."}
        conn = self._connect()
        conn.execute("UPDATE users SET ecobits = ecobits - ? WHERE id=?", (item["cost"], user_id))
        conn.execute(
            "INSERT INTO purchases (user_id, item_id, item_type, cost, purchased_at) VALUES (?, ?, 'store', ?, ?)",
            (user_id, item_id, item["cost"], datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Purchased '{item['name']}'!"}

    def get_user_purchases(self, user_id):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM purchases WHERE user_id=? ORDER BY purchased_at DESC", (user_id,)
        ).fetchall()
        conn.close()
        out = []
        for r in rows:
            row = dict(r)
            if row["item_type"] == "store":
                item = get_store_item(row["item_id"])
            else:
                item = get_plant_catalog(row["item_id"])
            row["name"] = item["name"] if item else "Unknown"
            out.append(row)
        return out

    # ------------------------------------------------------------------
    # Social feed
    # ------------------------------------------------------------------
    def create_post(self, user_id, content, post_type="Progress"):
        conn = self._connect()
        conn.execute(
            "INSERT INTO posts (user_id, content, post_type, created_at) VALUES (?, ?, ?, ?)",
            (user_id, content.strip(), post_type, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_feed(self, limit=30, viewer_id=None):
        conn = self._connect()
        rows = conn.execute(
            "SELECT posts.*, users.username FROM posts JOIN users ON posts.user_id = users.id "
            "ORDER BY posts.created_at DESC LIMIT ?", (limit,),
        ).fetchall()
        out = []
        for r in rows:
            row = dict(r)
            likes = conn.execute("SELECT COUNT(*) as n FROM post_likes WHERE post_id=?", (row["id"],)).fetchone()["n"]
            comments = conn.execute(
                "SELECT post_comments.*, users.username FROM post_comments "
                "JOIN users ON post_comments.user_id = users.id "
                "WHERE post_id=? ORDER BY post_comments.created_at ASC", (row["id"],),
            ).fetchall()
            liked_by_viewer = False
            if viewer_id:
                liked_by_viewer = conn.execute(
                    "SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?", (row["id"], viewer_id)
                ).fetchone() is not None
            row["likes"] = likes
            row["liked_by_viewer"] = liked_by_viewer
            row["comments"] = [dict(c) for c in comments]
            out.append(row)
        conn.close()
        return out

    def toggle_like(self, post_id, user_id):
        conn = self._connect()
        existing = conn.execute(
            "SELECT id FROM post_likes WHERE post_id=? AND user_id=?", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM post_likes WHERE id=?", (existing["id"],))
        else:
            conn.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
        conn.commit()
        conn.close()

    def add_comment(self, post_id, user_id, content):
        conn = self._connect()
        conn.execute(
            "INSERT INTO post_comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, user_id, content.strip(), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
