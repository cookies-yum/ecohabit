# EcoHabit 🌿

A sustainable-habit tracking web app — Flask + SQLite backend, HTML/CSS/JS
frontend, with Claude (Anthropic API) powering photo verification, honesty
check-ins, and an in-app AI assistant.

## Setup

```bash
pip install flask anthropic openai
export ANTHROPIC_API_KEY=sk-ant-...      # powers photo verification + check-ins
export OPENAI_API_KEY=sk-proj-...        # powers the "ask me anything" chat widget
python app.py
```

Both API keys are optional and independent — the app runs and degrades
gracefully without either (each feature clearly labels when it's in
fallback mode). You can run with just one, both, or neither.

Open **http://localhost:5000**. The SQLite database (`ecohabit.db`) is
created automatically on first run.

**Without an API key**, the app still runs fully — photo-verified habits
auto-approve and check-ins pass a basic length check, so you can develop
and demo the UI. This is clearly labeled in the responses ("AI verification
unavailable... auto-approved for demo purposes") so you always know when
you're in fallback mode. **Don't ship it to real users in that mode** —
the whole point of the verification system is the AI check.

## Getting an API key

1. Go to **console.anthropic.com** and create an account.
2. Under **API Keys**, generate a new key.
3. Set it as an environment variable (`ANTHROPIC_API_KEY`) — never hardcode
   it in a source file, especially if this is going in a public repo.
4. API usage costs money (separate from a claude.ai subscription). Check
   **anthropic.com/pricing** for current rates before going live.

## How the AI verification works

Every habit is tagged `"verify": "photo"` or `"verify": "checkin"` in
`carbon_data.py`:

- **Photo habits** (recycling, reusable cups, bike commutes, veggie meals,
  etc.) — the user uploads a photo, and Claude's vision capability judges
  whether it plausibly matches the habit. Lenient by design: it's not
  trying to catch every fake, just filter out obviously wrong/blank photos.

- **Check-in habits** (shorter shower, lights off, unplugging devices,
  cold-water wash, fixing a leak) — these can't be meaningfully
  photographed, so instead: Claude generates a short, specific follow-up
  question ("Which room's lights?"), the user answers in a sentence, and
  Claude judges whether the answer is a genuine, specific response versus
  empty/spam/nonsense. This isn't a lie detector — it's a light friction
  layer that's harder to spam through than a single button tap.

- **Trust score**: every user starts at 50/100. Accepted check-ins nudge it
  up slightly; rejected ones drop it by 15. Below 20, check-in habits are
  paused for that user until they rebuild trust by logging photo-verified
  habits — so a low-effort mass "shorter shower" farm gets shut off, while
  a normal user basically never notices this system exists.

- **Rate limiting**: one log per habit per user per calendar day, regardless
  of verification method — this is the main anti-farming lever, independent
  of AI.

## Two separate AI providers, on purpose

The app uses **two different AI providers for two different jobs**, kept in
separate files so you can swap either one independently:

- **`ai_client.py`** (Anthropic/Claude) — handles photo verification and
  honesty check-ins for habit logging. Kept narrow and structured (JSON
  in, JSON out) because it's making an accept/reject decision.

- **`openai_client.py`** (OpenAI) — powers the floating chat widget
  (bottom-right bubble). This one is a general-purpose, open-ended
  assistant — like talking to ChatGPT or Gemini. Ask it anything, not
  just sustainability questions. It's also handed the app's real habit
  list, recycling locations, and your current stats, so when the
  conversation *does* turn to habits or recycling, it recommends real
  things from the app instead of generic answers.

There's no technical reason both providers are needed — you could run the
whole app on just one. They're split here because that's what was asked
for, and it also means the verification logic and the chat feature can be
tuned, swapped, or debugged completely independently of each other.

## Which model, and why

`ai_client.py` uses **`claude-sonnet-5`** for everything — it's Anthropic's
current mid-tier model and supports vision, which the photo-verification
feature needs. All Claude models (Opus, Sonnet, Haiku) share the same API,
so if you want to cut costs you can swap the check-in question/evaluation
calls (text-only, no vision needed) to a cheaper model like
`claude-haiku-4-5-20251001` and leave photo verification on Sonnet or
better for accuracy. Model names and pricing change over time — check
**docs.claude.com** for the current lineup before you ship.

`openai_client.py` uses **`gpt-5.5`** for the chat widget — OpenAI's
current flagship model, chosen because this feature is open-ended
conversation and benefits from the strongest general reasoning. If you
want lower cost/latency instead, swap `MODEL` in that file to
`gpt-5.4-mini`. It's built on OpenAI's newer **Responses API**
(`client.responses.create(...)`), which is what OpenAI now recommends for
new projects over the older Chat Completions API. Check
**platform.openai.com/docs** for the current model lineup and pricing
before you ship.

## "Training" the AI — what that actually means here

You don't fine-tune Claude's weights for something like this (that's an
expensive, enterprise-scale process, not what you want for a habit app).
What you're actually doing — and what's already set up in `ai_client.py`
— is **prompt engineering**:

1. **System instructions** — each function sends Claude a clear job
   description (e.g. "you are the photo-verification system for a
   sustainability app... be lenient... reject only if clearly unrelated").
   This is the main lever. Loosen or tighten the language in the prompts
   inside `ai_client.py` to change behavior — no retraining needed.

2. **Grounding with real data** — the AI assistant is fed the app's actual
   habit list and recycling locations in its prompt every time (see
   `assistant_reply()`), so it recommends real things from your catalog
   instead of hallucinating generic advice. This pattern is sometimes
   called lightweight RAG (retrieval-augmented generation).

3. **Structured output** — verification functions ask Claude to reply with
   strict JSON (`{"verified": true, "reason": "..."}`), which the backend
   parses. If you see malformed JSON coming back occasionally, tightening
   the prompt (or adding a couple of example outputs directly in the
   prompt — "few-shot examples") is the fix.

4. **Iterate on real outputs** — the best way to "teach" it is to run it,
   look at where it's too strict or too lenient, and adjust the wording in
   the prompt accordingly. Keep a few tricky example photos/answers around
   and re-test them after each prompt change.

If you ever outgrow prompting alone (e.g. you have thousands of labeled
verification examples and want a specialized, cheaper model), Anthropic
does offer enterprise fine-tuning — but that's a distinct, self-serve-free
product, and not something this project needs.

## Project structure

```
ecohabit_web/
├── app.py            # Flask routes — the web layer
├── database.py       # SQLite persistence — all business logic
├── ai_client.py       # Claude (Anthropic) — photo verification + check-ins
├── openai_client.py   # OpenAI — general-purpose chat widget
├── carbon_data.py     # Habits, plants, store items, recycling locations, comparisons
├── templates/index.html
└── static/
    ├── style.css      # Pastel green theme
    └── app.js         # Frontend routing + rendering + API calls
```

## Notes

- Passwords are hashed with sha256 for this learning project — use
  bcrypt/argon2 if this ever goes to real users.
- The Settings page saves a language preference but doesn't yet translate
  the interface — flagged in the UI as a good next feature.
- Recycling locations are a static demo list for Israel with approximate
  coordinates — swap in a real dataset or Google Places API for production.
