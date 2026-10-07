# AI Automation Architecture — Gamified Classroom Assistant

## Overview
The system integrates automation at three layers: **content generation**,
**engagement intelligence**, and **operations**.

```
┌─────────────┐   questions   ┌──────────────┐
│ Staff UI    │──────────────>│ AI Quiz Gen  │
└─────┬───────┘               └──────┬───────┘
      │                              │ Quiz/Question rows
      v                              v
┌─────────────┐  points/XP    ┌──────────────┐
│ Student Hub │<──────────────│ Points Engine│
└─────┬───────┘               └──────┬───────┘
      │ answers/submissions          │ badges/levels
      v                              v
┌─────────────┐  analytics   ┌──────────────┐
│ Dashboard   │─────────────>│ Leaderboard  │
└─────────────┘              └──────────────┘
```

## Layers
1. **Content automation** — `services.generate_quiz_questions(topic, count)`
   produces ready-to-use `Question` rows (rule-based now; swap the function
   body for an LLM API call later without touching views).
2. **Engagement automation** — points, levels, badges, streaks handled by
   `services.award_points()` / `touch_streak()`; triggered automatically by
   quiz results, submissions, and attendance.
3. **Operations automation** — GitHub Actions CI runs migrations + the full
   test suite on every push; `seed_classroom` command bootstraps demo data.

## Extension points
- Replace `generate_quiz_questions` with an LLM (OpenAI/etc.) call.
- Gemini support: set `GEMINI_API_KEY` in a `.env` file (see
  `.env.example`); `generate_quiz_questions_gemini` falls back to the local
  bank when no key is set or the API call fails.
- OpenRouter support (free models): set `OPENROUTER_API_KEY` and
  `OPENROUTER_MODEL` (default `openrouter/free`). `generate_quiz_questions_ai`
  prefers OpenRouter, then Gemini, then the local bank.
- Add a nightly job (cron or Celery) that resets streaks and computes
  weekly leaderboards.
- Add feedback copy in `quiz_result.html` generated from score bands.
