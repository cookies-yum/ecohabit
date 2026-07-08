"""
ai_client.py
------------
All calls to the Anthropic API (Claude) live here, isolated from the rest
of the backend. If ANTHROPIC_API_KEY isn't set, every function returns a
clearly-labeled fallback so the rest of the app still runs (useful for
demoing without an API key — see README).

Model: claude-sonnet-5 — Anthropic's current mid-tier model. It supports
vision (needed for photo verification) and is well-suited for short,
structured tasks like the ones below. Swap to "claude-haiku-4-5-20251001"
for a cheaper/faster model on the check-in question/answer calls if you
want to cut costs — vision verification should stay on Sonnet or better
for accuracy.
"""

import os
import json
import base64

MODEL = "claude-sonnet-5"
_client = None


def _get_client():
    """Lazily create the Anthropic client. Returns None if no API key is set."""
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except ImportError:
        return None


def ai_available():
    return _get_client() is not None


def _extract_json(text):
    """Claude sometimes wraps JSON in prose or code fences — pull the object out."""
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        text = text.replace("json", "", 1).strip() if text.lower().startswith("json") else text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Photo verification (for habits with verify == "photo")
# ---------------------------------------------------------------------------
def verify_habit_photo(habit, image_bytes, media_type="image/jpeg"):
    """
    Returns (verified: bool, reason: str).
    If AI is unavailable, falls back to auto-approving with a note — so the
    app is still usable without an API key, but you should treat that mode
    as demo-only, not production-safe.
    """
    client = _get_client()
    if client is None:
        return True, "AI verification unavailable (no ANTHROPIC_API_KEY set) — auto-approved for demo purposes."

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = (
        "You are the photo-verification system for a sustainability habit-tracking app called EcoHabit. "
        f"A user claims they just did this habit: \"{habit['name']}\" — {habit['desc']}. "
        "Look at the attached photo and judge whether it plausibly shows evidence of that specific habit "
        "(it does not need to be perfect proof — just reasonably consistent with the claim, not obviously "
        "unrelated, reused, or a screenshot of something else). Be reasonably lenient but reject photos that "
        "are clearly unrelated, blank, or nonsensical for this habit.\n\n"
        "Respond with ONLY a JSON object, no other text: "
        '{"verified": true or false, "reason": "one short, friendly sentence explaining the decision"}'
    )
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        result = _extract_json(response.content[0].text)
        return bool(result.get("verified", False)), result.get("reason", "")
    except Exception as e:
        return False, f"Verification failed due to a technical error: {e}"


# ---------------------------------------------------------------------------
# Check-in flow (for habits with verify == "checkin", e.g. "Shorter Shower")
# ---------------------------------------------------------------------------
def generate_checkin_question(habit):
    """Generates a short, specific follow-up question as a lightweight honesty check."""
    client = _get_client()
    if client is None:
        return f"Quick check — what made you do '{habit['name']}' today?"

    prompt = (
        "You are a friendly honesty check-in for a sustainability app. A user says they just did this habit, "
        f"which can't be verified with a photo: \"{habit['name']}\" — {habit['desc']}. "
        "Write ONE short, casual, specific follow-up question (max 15 words) that someone who actually did the "
        "habit could answer naturally and easily, but someone making it up would find slightly awkward to fake "
        "convincingly. Do not make it interrogating or suspicious in tone — keep it light and friendly. "
        "Respond with ONLY the question text, nothing else."
    )
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip().strip('"')
    except Exception:
        return f"Quick check — what made you do '{habit['name']}' today?"


def evaluate_checkin_answer(habit, question, answer):
    """Returns (accepted: bool, reason: str)."""
    client = _get_client()
    if client is None:
        accepted = len(answer.strip()) >= 3
        return accepted, "AI unavailable — accepted based on a basic length check." if accepted else "Answer too short."

    prompt = (
        "You are a lightweight honesty check for a sustainability habit-tracking app — NOT a strict lie detector. "
        f"Habit claimed: \"{habit['name']}\" — {habit['desc']}.\n"
        f"Question asked: \"{question}\"\n"
        f"User's answer: \"{answer}\"\n\n"
        "Accept the answer unless it is empty, obvious gibberish, clearly copy-pasted from the question, or "
        "completely unrelated to the question. Give people the benefit of the doubt — this is meant to filter "
        "out spam/bot-like logging, not to interrogate genuine users.\n\n"
        "Respond with ONLY a JSON object: "
        '{"accepted": true or false, "reason": "one short, friendly sentence"}'
    )
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _extract_json(response.content[0].text)
        return bool(result.get("accepted", False)), result.get("reason", "")
    except Exception as e:
        return False, f"Check failed due to a technical error: {e}"


# ---------------------------------------------------------------------------
# AI Assistant — recycling + habit recommendations, grounded in app data
# ---------------------------------------------------------------------------
def assistant_reply(user_message, context, history=None):
    """
    context: dict with keys 'habits', 'recycling_locations', 'user_stats',
             'category_breakdown' — all pulled from the app's real data so
             answers are grounded rather than generic.
    history: list of {"role": "user"/"assistant", "content": str}, optional.
    """
    client = _get_client()
    if client is None:
        return ("The AI assistant needs an ANTHROPIC_API_KEY set on the server to work — "
                "see the README for setup. In the meantime, check the Log Habit and "
                "Recycling Map pages directly!")

    habits_summary = "\n".join(
        f"- {h['name']} ({h['category']}): {h['desc']} — {h['ecobits']} ecobits, {h['co2']}kg CO2 saved"
        for h in context["habits"]
    )
    locations_summary = "\n".join(
        f"- {loc['name']} ({loc['type']})" for loc in context["recycling_locations"]
    )
    stats = context["user_stats"]
    breakdown = context.get("category_breakdown", {})
    breakdown_summary = ", ".join(f"{k}: {v:.1f}kg" for k, v in breakdown.items()) or "no habits logged yet"

    system_prompt = (
        "You are the in-app AI assistant for EcoHabit, a sustainable-habit tracking app. "
        "You help users with two things: (1) recommending which sustainable habits from the app's catalog "
        "they should try next, personalized to what they've already logged, and (2) helping them find "
        "recycling locations from the app's own list. "
        "Always ground your answers in the data provided below — recommend actual habits and actual "
        "locations from these lists, don't invent new ones. Keep answers short, warm, and encouraging "
        "(3-5 sentences max unless the user asks for a list). If asked something unrelated to sustainability, "
        "habits, or recycling, gently redirect back to what you can help with.\n\n"
        f"User's current stats: {stats['ecobits']} ecobits, {stats['total_co2_saved']:.1f}kg CO2 saved total, "
        f"habits logged by category so far: {breakdown_summary}.\n\n"
        f"Available habits in the app:\n{habits_summary}\n\n"
        f"Available recycling locations:\n{locations_summary}"
    )

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model=MODEL, max_tokens=400,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Sorry, I ran into an error reaching the AI service: {e}"
