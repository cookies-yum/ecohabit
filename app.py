"""
app.py
------
EcoHabit backend — Flask + SQLite + Claude (Anthropic API).

Run with:
    pip install flask anthropic
    export ANTHROPIC_API_KEY=sk-ant-...   (optional but needed for AI features)
    python app.py
Then open http://localhost:5000
"""

import os
import secrets
from functools import wraps
from flask import Flask, request, jsonify, session, render_template

from database import EcoDatabase, TRUST_GATE
from carbon_data import (
    HABITS, CATEGORIES, COMPARISONS, PLANTS_CATALOG, STORE_ITEMS, STORE_CATEGORIES,
    RECYCLING_LOCATIONS, LANGUAGES, get_habit,
)
import ai_client
import openai_client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))
db = EcoDatabase("ecohabit.db")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not logged in."}), 401
        return f(*args, **kwargs)
    return wrapper


def current_user():
    return db.get_user(session["user_id"])


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    ok, msg = db.register_user(data.get("username", ""), data.get("email", ""), data.get("password", ""))
    return jsonify({"success": ok, "message": msg})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    user = db.login(data.get("username", ""), data.get("password", ""))
    if user:
        session["user_id"] = user["id"]
        return jsonify({"success": True, "user": {"username": user["username"]}})
    return jsonify({"success": False, "message": "Incorrect username or password."}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/session")
def get_session():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    user = current_user()
    if not user:
        session.clear()
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "username": user["username"]})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/api/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    user = current_user()
    return jsonify({
        "user": {"username": user["username"], "email": user["email"], "ecobits": user["ecobits"],
                  "total_co2_saved": user["total_co2_saved"], "trust_score": user["trust_score"]},
        "habits_logged": db.get_habits_logged_count(uid),
        "streak": db.get_current_streak(uid),
        "weekly_co2": db.get_weekly_co2(uid),
        "rank": db.get_user_rank(uid),
        "category_breakdown": db.get_category_breakdown(uid),
        "recent_logs": db.get_user_logs(uid, limit=5),
        "verification_ai_available": ai_client.ai_available(),
        "chat_ai_available": openai_client.ai_available(),
    })


# ---------------------------------------------------------------------------
# Habits / Log Habit / AI verification
# ---------------------------------------------------------------------------
@app.route("/api/habits")
@login_required
def habits():
    return jsonify({"habits": HABITS, "categories": CATEGORIES, "trust_gated": db.trust_gated(session["user_id"])})


@app.route("/api/habits/<int:habit_id>/checkin-question", methods=["POST"])
@login_required
def checkin_question(habit_id):
    """Step 1 of a checkin-type (non-photo) habit: get the AI's honesty-check question."""
    habit = get_habit(habit_id)
    if not habit or habit["verify"] != "checkin":
        return jsonify({"error": "This habit isn't a check-in type."}), 400
    if db.already_logged_today(session["user_id"], habit_id):
        return jsonify({"error": "You've already logged this today — come back tomorrow!"}), 400
    if db.trust_gated(session["user_id"]):
        return jsonify({
            "error": "Your trust score is low right now, so check-in habits are paused. "
                     "Log a few photo-verified habits to rebuild trust."
        }), 403
    question = ai_client.generate_checkin_question(habit)
    session[f"checkin_q_{habit_id}"] = question
    return jsonify({"question": question})


@app.route("/api/habits/<int:habit_id>/log", methods=["POST"])
@login_required
def log_habit(habit_id):
    uid = session["user_id"]
    habit = get_habit(habit_id)
    if not habit:
        return jsonify({"success": False, "message": "Habit not found."}), 404
    if db.already_logged_today(uid, habit_id):
        return jsonify({"success": False, "message": "You've already logged this today — nice work, come back tomorrow!"}), 400

    if habit["verify"] == "photo":
        image_b64 = (request.json or {}).get("image_base64")
        media_type = (request.json or {}).get("media_type", "image/jpeg")
        if not image_b64:
            return jsonify({"success": False, "message": "A photo is required for this habit."}), 400
        import base64
        image_bytes = base64.b64decode(image_b64.split(",")[-1])
        verified, reason = ai_client.verify_habit_photo(habit, image_bytes, media_type)
        if not verified:
            return jsonify({"success": False, "message": f"Photo not accepted: {reason}"}), 400
        result = db.commit_habit_log(uid, habit_id, "photo")
        return jsonify({"success": True, "message": f"Verified! {reason}", **result})

    else:  # checkin
        if db.trust_gated(uid):
            return jsonify({"success": False, "message": "Trust score too low for check-in habits right now."}), 403
        question = session.get(f"checkin_q_{habit_id}")
        answer = (request.json or {}).get("answer", "")
        if not question:
            return jsonify({"success": False, "message": "Request a check-in question first."}), 400
        accepted, reason = ai_client.evaluate_checkin_answer(habit, question, answer)
        session.pop(f"checkin_q_{habit_id}", None)
        if not accepted:
            db.adjust_trust(uid, -15)
            return jsonify({"success": False, "message": f"Not accepted: {reason}", "trust_score": db.get_trust_score(uid)}), 400
        db.adjust_trust(uid, +2)
        result = db.commit_habit_log(uid, habit_id, "checkin")
        return jsonify({"success": True, "message": f"Logged! {reason}", "trust_score": db.get_trust_score(uid), **result})


# ---------------------------------------------------------------------------
# Compare page (carbon comparisons)
# ---------------------------------------------------------------------------
@app.route("/api/compare")
@login_required
def compare():
    return jsonify({"comparisons": COMPARISONS})


# ---------------------------------------------------------------------------
# My Plants
# ---------------------------------------------------------------------------
@app.route("/api/plants")
@login_required
def plants():
    uid = session["user_id"]
    owned_catalog_ids = {p["catalog_id"] for p in db.get_user_plants(uid)}
    user = current_user()
    catalog = []
    for p in PLANTS_CATALOG:
        entry = dict(p)
        entry["owned"] = p["id"] in owned_catalog_ids and p["free_starter"]  # only hide starter once owned
        entry["can_afford"] = user["ecobits"] >= p["cost"]
        catalog.append(entry)
    return jsonify({"my_plants": db.get_user_plants(uid), "catalog": catalog})


@app.route("/api/plants/buy/<int:catalog_id>", methods=["POST"])
@login_required
def buy_plant(catalog_id):
    return jsonify(db.buy_plant(session["user_id"], catalog_id))


@app.route("/api/plants/<int:plant_id>/water", methods=["POST"])
@login_required
def water_plant(plant_id):
    return jsonify(db.water_plant(session["user_id"], plant_id))


# ---------------------------------------------------------------------------
# EcoStore
# ---------------------------------------------------------------------------
@app.route("/api/store")
@login_required
def store():
    uid = session["user_id"]
    user = current_user()
    owned = db.get_owned_item_ids(uid)
    items = []
    for i in STORE_ITEMS:
        entry = dict(i)
        entry["owned"] = i["id"] in owned
        entry["can_afford"] = user["ecobits"] >= i["cost"]
        items.append(entry)
    return jsonify({"items": items, "categories": STORE_CATEGORIES, "ecobits": user["ecobits"]})


@app.route("/api/store/buy/<int:item_id>", methods=["POST"])
@login_required
def buy_store_item(item_id):
    return jsonify(db.purchase_store_item(session["user_id"], item_id))


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------
@app.route("/api/leaderboard")
@login_required
def leaderboard():
    return jsonify({"leaderboard": db.get_leaderboard(10), "me": current_user()["username"]})


# ---------------------------------------------------------------------------
# Social feed
# ---------------------------------------------------------------------------
@app.route("/api/social/posts", methods=["GET"])
@login_required
def get_posts():
    return jsonify({"posts": db.get_feed(viewer_id=session["user_id"])})


@app.route("/api/social/posts", methods=["POST"])
@login_required
def create_post():
    data = request.json or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"success": False, "message": "Post can't be empty."}), 400
    db.create_post(session["user_id"], content, data.get("post_type", "Progress"))
    return jsonify({"success": True})


@app.route("/api/social/posts/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    db.toggle_like(post_id, session["user_id"])
    return jsonify({"success": True})


@app.route("/api/social/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def comment_post(post_id):
    content = (request.json or {}).get("content", "").strip()
    if not content:
        return jsonify({"success": False, "message": "Comment can't be empty."}), 400
    db.add_comment(post_id, session["user_id"], content)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Recycling map
# ---------------------------------------------------------------------------
@app.route("/api/recycling")
@login_required
def recycling():
    return jsonify({"locations": RECYCLING_LOCATIONS})


# ---------------------------------------------------------------------------
# Profile / Settings
# ---------------------------------------------------------------------------
@app.route("/api/profile")
@login_required
def profile():
    uid = session["user_id"]
    return jsonify({
        "user": current_user(),
        "habits_logged": db.get_habits_logged_count(uid),
        "streak": db.get_current_streak(uid),
        "weekly_co2": db.get_weekly_co2(uid),
        "logs": db.get_user_logs(uid, limit=50),
        "purchases": db.get_user_purchases(uid),
    })


@app.route("/api/settings/language", methods=["POST"])
@login_required
def set_language():
    lang = (request.json or {}).get("language", "en")
    db.set_language(session["user_id"], lang)
    return jsonify({"success": True})


@app.route("/api/languages")
def languages():
    return jsonify({"languages": LANGUAGES})


# ---------------------------------------------------------------------------
# AI Assistant (chat widget)
# ---------------------------------------------------------------------------
@app.route("/api/assistant", methods=["POST"])
@login_required
def assistant():
    uid = session["user_id"]
    message = (request.json or {}).get("message", "").strip()
    if not message:
        return jsonify({"reply": "Ask me anything about habits to try or where to recycle!"})

    history = session.get("assistant_history", [])
    context = {
        "habits": HABITS,
        "recycling_locations": RECYCLING_LOCATIONS,
        "user_stats": current_user(),
        "category_breakdown": db.get_category_breakdown(uid),
    }
    reply = openai_client.chat_reply(message, context, history)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    session["assistant_history"] = history[-10:]  # keep last 10 turns

    return jsonify({"reply": reply, "ai_available": openai_client.ai_available()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
