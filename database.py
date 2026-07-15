"""
database.py
------------
All persistence for EcoHabit, via SQLAlchemy Core (so the same code works
against SQLite locally and Postgres in production — same queries, no
per-database SQL differences to maintain).

Which database gets used is controlled by the DATABASE_URL environment
variable:
  - Not set  -> local SQLite file (ecohabit.db) — fine for local dev, but
                gets wiped on most hosting platforms' free tiers on redeploy.
  - Set      -> uses that Postgres connection (e.g. from Neon, Render
                Postgres, Supabase, etc.) — this is what makes data
                actually persistent when deployed. See README for setup.
"""

import os
import hashlib
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, text

from carbon_data import get_habit, get_store_item, get_plant_catalog, GROWTH_STAGES, ECOBITS_PER_STAGE

TRUST_START = 50
TRUST_MAX = 100
TRUST_MIN = 0
TRUST_GATE = 20  # below this, checkin-type habits require rebuilding trust via photo habits first


def _build_engine(db_path):
    url = os.environ.get("DATABASE_URL")
    if url:
        # Some providers hand out "postgres://" URLs; SQLAlchemy needs "postgresql://"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return create_engine(url, pool_pre_ping=True)
    return create_engine(f"sqlite:///{db_path}")


def _row_to_dict(row):
    return dict(row._mapping) if row is not None else None


class EcoDatabase:
    def __init__(self, db_path="ecohabit.db"):
        self.engine = _build_engine(db_path)
        self.is_postgres = self.engine.dialect.name == "postgresql"
        self._create_tables()

    def _pk(self):
        return "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"

    def _create_tables(self):
        pk = self._pk()
        statements = [
            f"""CREATE TABLE IF NOT EXISTS users (
                id {pk},
                username TEXT UNIQUE NOT NULL,
                email TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                ecobits INTEGER NOT NULL DEFAULT 0,
                total_co2_saved REAL NOT NULL DEFAULT 0,
                trust_score INTEGER NOT NULL DEFAULT 50,
                language TEXT NOT NULL DEFAULT 'en',
                created_at TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS habit_logs (
                id {pk},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                habit_id INTEGER NOT NULL,
                co2_saved REAL NOT NULL,
                ecobits_earned INTEGER NOT NULL,
                verify_method TEXT NOT NULL,
                logged_at TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS user_plants (
                id {pk},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                catalog_id INTEGER NOT NULL,
                growth_progress REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS purchases (
                id {pk},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                item_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                cost INTEGER NOT NULL,
                purchased_at TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS posts (
                id {pk},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                post_type TEXT NOT NULL DEFAULT 'Progress',
                created_at TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS post_likes (
                id {pk},
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                UNIQUE(post_id, user_id)
            )""",
            f"""CREATE TABLE IF NOT EXISTS post_comments (
                id {pk},
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
        ]
        with self.engine.begin() as conn:
            if not self.is_postgres:
                conn.execute(text("PRAGMA foreign_keys = ON"))
            for stmt in statements:
                conn.execute(text(stmt))

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
        with self.engine.begin() as conn:
            existing = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
            if existing:
                return False, "That username is already taken."
            conn.execute(
                text("INSERT INTO users (username, email, password_hash, created_at) "
                     "VALUES (:u, :e, :p, :c)"),
                {"u": username, "e": email.strip(), "p": self._hash(password), "c": datetime.now().isoformat()},
            )
            user_id = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()[0]
            conn.execute(
                text("INSERT INTO user_plants (user_id, catalog_id, growth_progress, created_at) "
                     "VALUES (:uid, 1, 0, :c)"),
                {"uid": user_id, "c": datetime.now().isoformat()},
            )
        return True, "Account created!"

    def login(self, username, password):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM users WHERE username=:u"), {"u": username}).fetchone()
        row = _row_to_dict(row)
        if row and row["password_hash"] == self._hash(password):
            return row
        return None

    def get_user(self, user_id):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).fetchone()
        return _row_to_dict(row)

    def set_language(self, user_id, lang_code):
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE users SET language=:l WHERE id=:id"), {"l": lang_code, "id": user_id})

    # ------------------------------------------------------------------
    # Habit logging (with verification bookkeeping)
    # ------------------------------------------------------------------
    def already_logged_today(self, user_id, habit_id):
        today = date.today().isoformat()
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT COUNT(*) FROM habit_logs WHERE user_id=:uid AND habit_id=:hid AND logged_at LIKE :d"),
                {"uid": user_id, "hid": habit_id, "d": today + "%"},
            ).fetchone()
        return row[0] > 0

    def get_trust_score(self, user_id):
        return self.get_user(user_id)["trust_score"]

    def adjust_trust(self, user_id, delta):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT trust_score FROM users WHERE id=:id"), {"id": user_id}).fetchone()
            new_score = max(TRUST_MIN, min(TRUST_MAX, row[0] + delta))
            conn.execute(text("UPDATE users SET trust_score=:t WHERE id=:id"), {"t": new_score, "id": user_id})
        return new_score

    def trust_gated(self, user_id):
        return self.get_trust_score(user_id) < TRUST_GATE

    def commit_habit_log(self, user_id, habit_id, verify_method):
        habit = get_habit(habit_id)
        now = datetime.now().isoformat()
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO habit_logs (user_id, habit_id, co2_saved, ecobits_earned, verify_method, logged_at) "
                     "VALUES (:uid, :hid, :co2, :eco, :vm, :t)"),
                {"uid": user_id, "hid": habit_id, "co2": habit["co2"], "eco": habit["ecobits"],
                 "vm": verify_method, "t": now},
            )
            conn.execute(
                text("UPDATE users SET ecobits = ecobits + :eco, total_co2_saved = total_co2_saved + :co2 WHERE id=:uid"),
                {"eco": habit["ecobits"], "co2": habit["co2"], "uid": user_id},
            )
        return {"ecobits_earned": habit["ecobits"], "co2_saved": habit["co2"]}

    def get_user_logs(self, user_id, limit=20):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT * FROM habit_logs WHERE user_id=:uid ORDER BY logged_at DESC LIMIT :lim"),
                {"uid": user_id, "lim": limit},
            ).fetchall()
        out = []
        for r in rows:
            row = _row_to_dict(r)
            h = get_habit(row["habit_id"])
            row["habit_name"] = h["name"] if h else "Unknown"
            row["category"] = h["category"] if h else ""
            row["icon"] = h["icon"] if h else "🌿"
            out.append(row)
        return out

    def get_habits_logged_count(self, user_id):
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM habit_logs WHERE user_id=:uid"), {"uid": user_id}).fetchone()
        return row[0]

    def get_current_streak(self, user_id):
        """Computed in Python (not SQL date functions) so it works identically on SQLite and Postgres."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT logged_at FROM habit_logs WHERE user_id=:uid"), {"uid": user_id}
            ).fetchall()
        if not rows:
            return 0
        day_set = set()
        for r in rows:
            try:
                day_set.add(datetime.fromisoformat(r[0]).date())
            except ValueError:
                continue
        if not day_set:
            return 0
        streak = 0
        cursor = date.today()
        if cursor not in day_set:
            cursor = cursor - timedelta(days=1)
        while cursor in day_set:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def get_weekly_co2(self, user_id):
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT COALESCE(SUM(co2_saved),0) FROM habit_logs WHERE user_id=:uid AND logged_at>=:c"),
                {"uid": user_id, "c": cutoff},
            ).fetchone()
        return round(row[0], 2)

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
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, username, ecobits, total_co2_saved FROM users ORDER BY ecobits DESC LIMIT :lim"),
                {"lim": limit},
            ).fetchall()
        out = []
        for r in rows:
            row = _row_to_dict(r)
            row["streak"] = self.get_current_streak(row["id"])
            out.append(row)
        return out

    def get_user_rank(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT id FROM users ORDER BY ecobits DESC")).fetchall()
        for i, r in enumerate(rows, start=1):
            if r[0] == user_id:
                return i
        return None

    # ------------------------------------------------------------------
    # My Plants
    # ------------------------------------------------------------------
    def get_user_plants(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT * FROM user_plants WHERE user_id=:uid ORDER BY created_at DESC"), {"uid": user_id}
            ).fetchall()
        out = []
        for r in rows:
            row = _row_to_dict(r)
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
        with self.engine.begin() as conn:
            if not cat["free_starter"]:
                conn.execute(text("UPDATE users SET ecobits = ecobits - :c WHERE id=:uid"),
                             {"c": cat["cost"], "uid": user_id})
            conn.execute(
                text("INSERT INTO user_plants (user_id, catalog_id, growth_progress, created_at) VALUES (:uid, :cid, 0, :t)"),
                {"uid": user_id, "cid": catalog_id, "t": datetime.now().isoformat()},
            )
            conn.execute(
                text("INSERT INTO purchases (user_id, item_id, item_type, cost, purchased_at) "
                     "VALUES (:uid, :cid, 'plant', :cost, :t)"),
                {"uid": user_id, "cid": catalog_id, "cost": 0 if cat["free_starter"] else cat["cost"],
                 "t": datetime.now().isoformat()},
            )
        return {"success": True, "message": f"'{cat['name']}' added to My Plants!"}

    def water_plant(self, user_id, plant_id, cost=10):
        with self.engine.begin() as conn:
            plant = conn.execute(
                text("SELECT * FROM user_plants WHERE id=:pid AND user_id=:uid"), {"pid": plant_id, "uid": user_id}
            ).fetchone()
            if not plant:
                return {"success": False, "message": "Plant not found."}
            plant = _row_to_dict(plant)
            user = self.get_user(user_id)
            max_growth = GROWTH_STAGES * ECOBITS_PER_STAGE
            if plant["growth_progress"] >= max_growth:
                return {"success": False, "message": "This plant is already fully grown!"}
            if user["ecobits"] < cost:
                return {"success": False, "message": f"Not enough ecobits — need {cost}."}
            new_growth = min(max_growth, plant["growth_progress"] + cost)
            conn.execute(text("UPDATE user_plants SET growth_progress=:g WHERE id=:pid"),
                         {"g": new_growth, "pid": plant_id})
            conn.execute(text("UPDATE users SET ecobits = ecobits - :c WHERE id=:uid"), {"c": cost, "uid": user_id})
        return {"success": True, "message": "Plant watered! 💧"}

    # ------------------------------------------------------------------
    # EcoStore (non-plant items)
    # ------------------------------------------------------------------
    def get_owned_item_ids(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT item_id FROM purchases WHERE user_id=:uid AND item_type='store'"), {"uid": user_id}
            ).fetchall()
        return {r[0] for r in rows}

    def purchase_store_item(self, user_id, item_id):
        item = get_store_item(item_id)
        if not item:
            return {"success": False, "message": "Item not found."}
        if item_id in self.get_owned_item_ids(user_id):
            return {"success": False, "message": "You already own this."}
        user = self.get_user(user_id)
        if user["ecobits"] < item["cost"]:
            return {"success": False, "message": f"Not enough ecobits — need {item['cost'] - user['ecobits']} more."}
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE users SET ecobits = ecobits - :c WHERE id=:uid"), {"c": item["cost"], "uid": user_id})
            conn.execute(
                text("INSERT INTO purchases (user_id, item_id, item_type, cost, purchased_at) "
                     "VALUES (:uid, :iid, 'store', :cost, :t)"),
                {"uid": user_id, "iid": item_id, "cost": item["cost"], "t": datetime.now().isoformat()},
            )
        return {"success": True, "message": f"Purchased '{item['name']}'!"}

    def get_user_purchases(self, user_id):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT * FROM purchases WHERE user_id=:uid ORDER BY purchased_at DESC"), {"uid": user_id}
            ).fetchall()
        out = []
        for r in rows:
            row = _row_to_dict(r)
            item = get_store_item(row["item_id"]) if row["item_type"] == "store" else get_plant_catalog(row["item_id"])
            row["name"] = item["name"] if item else "Unknown"
            out.append(row)
        return out

    # ------------------------------------------------------------------
    # Social feed
    # ------------------------------------------------------------------
    def create_post(self, user_id, content, post_type="Progress"):
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO posts (user_id, content, post_type, created_at) VALUES (:uid, :c, :pt, :t)"),
                {"uid": user_id, "c": content.strip(), "pt": post_type, "t": datetime.now().isoformat()},
            )

    def get_feed(self, limit=30, viewer_id=None):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT posts.*, users.username FROM posts JOIN users ON posts.user_id = users.id "
                     "ORDER BY posts.created_at DESC LIMIT :lim"), {"lim": limit},
            ).fetchall()
            out = []
            for r in rows:
                row = _row_to_dict(r)
                likes = conn.execute(text("SELECT COUNT(*) FROM post_likes WHERE post_id=:pid"),
                                      {"pid": row["id"]}).fetchone()[0]
                comments = conn.execute(
                    text("SELECT post_comments.*, users.username FROM post_comments "
                         "JOIN users ON post_comments.user_id = users.id "
                         "WHERE post_id=:pid ORDER BY post_comments.created_at ASC"), {"pid": row["id"]},
                ).fetchall()
                liked_by_viewer = False
                if viewer_id:
                    liked_by_viewer = conn.execute(
                        text("SELECT 1 FROM post_likes WHERE post_id=:pid AND user_id=:uid"),
                        {"pid": row["id"], "uid": viewer_id}
                    ).fetchone() is not None
                row["likes"] = likes
                row["liked_by_viewer"] = liked_by_viewer
                row["comments"] = [_row_to_dict(c) for c in comments]
                out.append(row)
        return out

    def toggle_like(self, post_id, user_id):
        with self.engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM post_likes WHERE post_id=:pid AND user_id=:uid"),
                {"pid": post_id, "uid": user_id}
            ).fetchone()
            if existing:
                conn.execute(text("DELETE FROM post_likes WHERE id=:id"), {"id": existing[0]})
            else:
                conn.execute(text("INSERT INTO post_likes (post_id, user_id) VALUES (:pid, :uid)"),
                             {"pid": post_id, "uid": user_id})

    def add_comment(self, post_id, user_id, content):
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO post_comments (post_id, user_id, content, created_at) VALUES (:pid, :uid, :c, :t)"),
                {"pid": post_id, "uid": user_id, "c": content.strip(), "t": datetime.now().isoformat()},
            )
