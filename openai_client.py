"""
openai_client.py
-----------------
General-purpose chat assistant, powered by OpenAI (separate from the
Anthropic-powered habit verification in ai_client.py). This is the
"ask me anything" chat — like talking to ChatGPT or Gemini — not
restricted to sustainability topics, though it's aware of the app's
data so it can also give grounded recommendations when relevant.

Model: gpt-5.5 — OpenAI's current flagship model as of writing. Swap to
"gpt-5.4-mini" in MODEL below for a cheaper/faster option; quality will
dip a bit but it's a reasonable trade for a hobby app with light usage.
Model names change over time — check platform.openai.com/docs for the
current lineup before shipping.
"""

import os

MODEL = "gpt-5.5"
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key)
        return _client
    except ImportError:
        return None


def ai_available():
    return _get_client() is not None


def chat_reply(user_message, context=None, history=None):
    """
    General-purpose conversational reply.
    context: optional dict with 'habits', 'recycling_locations', 'user_stats',
             'category_breakdown' — used to make app-related answers grounded,
             but the assistant will happily answer anything else too.
    history: list of {"role": "user"/"assistant", "content": str}
    """
    client = _get_client()
    if client is None:
        return ("This chat needs an OPENAI_API_KEY set on the server to work — "
                "see the README for setup instructions.")

    instructions = (
        "You are the AI assistant built into EcoHabit, a sustainable-habit tracking app. "
        "You work like a general assistant (similar to ChatGPT or Gemini) — the user can ask you "
        "anything at all, not just sustainability questions, and you should answer normally and "
        "conversationally. When the conversation touches on habits to try or recycling locations, "
        "prefer recommending real ones from the app data below rather than generic answers. "
        "Keep responses reasonably concise unless the user asks for more detail."
    )

    if context:
        habits_summary = "\n".join(
            f"- {h['name']} ({h['category']}): {h['desc']} — {h['ecobits']} ecobits, {h['co2']}kg CO2 saved"
            for h in context.get("habits", [])
        )
        locations_summary = "\n".join(
            f"- {loc['name']} ({loc['type']})" for loc in context.get("recycling_locations", [])
        )
        stats = context.get("user_stats", {})
        breakdown = context.get("category_breakdown", {})
        breakdown_summary = ", ".join(f"{k}: {v:.1f}kg" for k, v in breakdown.items()) or "no habits logged yet"
        instructions += (
            f"\n\nApp context — user has {stats.get('ecobits', 0)} ecobits, "
            f"{stats.get('total_co2_saved', 0):.1f}kg CO2 saved, logged by category: {breakdown_summary}.\n"
            f"Available habits:\n{habits_summary}\n\nAvailable recycling locations:\n{locations_summary}"
        )

    input_items = list(history or [])
    input_items.append({"role": "user", "content": user_message})

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=input_items,
        )
        return response.output_text.strip()
    except Exception as e:
        return f"Sorry, I ran into an error reaching OpenAI: {e}"
