# AI Automation Architecture — Gamified Classroom Assistant

## Overview
The system integrates automation at three layers: **content generation**,
**engagement intelligence**, and **operations**.

```
                    ┌─────────────────────────────────┐
                    │        AI LAYER (ai.py)         │
                    │  OpenRouter (free) -> Gemini    │
                    │  -> local-bank fallback         │
                    └───────┬─────────────┬───────────┘
                            │ questions   │ feedback/tips
                            v             v
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

## API-key resolution
Keys resolve in this order (first hit wins):
1. **Database** — `AIProvider` rows, editable at
   `/classroom/staff/ai-settings/` (staff only, keys shown masked).
2. **Environment variables** — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`,
   `GEMINI_API_KEY`.
3. **`.env` file** — same names (see `.env.example`). `.env` is git-ignored.

Disable a provider by unchecking *Enabled* in AI settings or removing its key.

## Automations (all key-powered, all with safe fallbacks)
| Feature | Entry | Function |
|---|---|---|
| Quiz generation | `/classroom/staff/ai-quiz/` | `ai.ai_generate_quiz_questions` |
| Quiz feedback | quiz result page (automatic) | `ai.ai_quiz_feedback` |
| Study assistant | `/classroom/ai-study/` | `ai.ai_study_guide` |
| Assignment generator | `/classroom/staff/ai-assignment/` | `ai.ai_assignment_idea` |
| Class insights | `/classroom/staff/ai-insights/` | `ai.ai_class_insights` |
| Architecture status | `/classroom/ai-architecture/` | `ai.provider_status` |

Every call is logged to `AILog` (feature, provider, success, latency) and
visible on the insights + architecture pages and in Django admin.

## Layers
1. **Content automation** — quiz questions, feedback, study guides,
   assignments, insights via `apps/classroom/ai.py` (single place to swap
   models or add providers).
2. **Engagement automation** — points, levels, badges, streaks handled by
   `services.award_points()` / `touch_streak()`; triggered automatically by
   quiz results, submissions, and attendance.
3. **Operations automation** — GitHub Actions CI runs migrations + the full
   test suite on every push; `seed_classroom` command bootstraps demo data.

## Extension points
- Add a provider by adding `_call_<name>` in `ai.py` and inserting it into
  `ai_chat`.
- Add a nightly job (cron or Celery) that resets streaks and computes
  weekly leaderboards.
- Never commit real keys: keep them in `.env` (git-ignored) or the DB.
